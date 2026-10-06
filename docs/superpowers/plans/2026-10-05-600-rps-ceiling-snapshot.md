# 600 req/s Ceiling Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one both-off S2 hold on Paper-C1 at 150/30/150/250/250 users, take the CPU and latency readings at the same time, and score which of the four candidates (master, worker, Envoy threads, shared-path latency) is over its line.

**Architecture:** Reuse `run_scenario.py` and `pull_results.py` unchanged. Add one small SSH-able reading script (`ceiling_reading.sh`) and one small post-hold summary (`ceiling_summary.py`). No new collectors, no changes to the runner, no unit tests. Both scripts are smoke-run once before the hold.

**Tech Stack:** bash over SSH (aliases `topfull-master`, `topfull-worker-1`, `topfull-load`), Python 3 stdlib, existing `experiments/` tooling.

## Global Constraints

Copied from the spec (`docs/superpowers/specs/2026-10-05-600-rps-ceiling-snapshot-design.md`):

- Counts getproduct / postcheckout / getcart / postcart / emptycart = **150 / 30 / 150 / 250 / 250**, `spawn_rate` 50, 600 s hold, slot **run154**.
- TopFull RL off, RetryGuard off, `paper_cpu_reconcile: false`. The Go proxy still starts.
- Paper-C1 pin: frontend 1150 m × 4 (HPA 4/4), checkoutservice 800 m × 1, recommendationservice 1150 m × 1, productcatalogservice 800 m, cartservice 800 m, currencyservice 770 m, shippingservice 770 m, adservice 1150 m, paymentservice 155 m, emailservice 120 m, redis-cart 540 m. Catalog HPA 1/1. Sidecar request 100 m, `proxyCPULimit` absent. If the fourth frontend pod is Pending, use 90 m and put it back to 100 m before the post-hold restore check.
- Reading window: 60 s starting about 120 s after Locust starts.
- Gates: Locust `total.csv` rows ≥ 540; `service_inbound.csv` span 480–900 s; mesh `gap2_pct` ≤ 10; frontend `replica_count` 4 and every other service 1 on the modal `resource_usage.csv` sample; Layer A threshold below 10000 on ≤ 1% of `topfull_throttle.csv` rows.
- Lines: master busy ≥ 7.2 of 8 cores or proxy process ≥ 80% of one core; worker busy ≥ 14.4 of 16 cores or steal > 5%; Envoy threads: a proxy's CPU within 10% of `concurrency × 1000` m (absent `--concurrency` → inconclusive); shared path: `emptycart` P95 > 200 ms.
- Cleared: shared path when `emptycart` P95 < 100 ms and `getproduct` or `getcart` P95 > 1000 ms; master when busy < 6 of 8 and proxy < 50% of one core; worker when busy < 13 of 16 and steal ≤ 2%.
- Ceiling present when the five-tag mean-RPS sum is 450 through 705. Above 705: ceiling did not appear, name nothing. Below 450: collapsed, name nothing.
- Do not stop the VMs. Restore Paper-C1 before the session ends. Do not relaunch into a failed folder; the next free slot is run155.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `experiments/configs/scenario_2_baseline_no_topfull.yaml` | Modify | Counts and description for run154 |
| `experiments/ceiling_reading.sh` | Create | `cpu` mode (busy cores, steal, per-process CPU) and `proxies` mode (sidecar CPU and Envoy threads); run over SSH |
| `experiments/ceiling_summary.py` | Create | Post-hold numbers from a pulled run folder: gates, per-tag RPS and P95, sum, frontend λ, Layer A fraction |
| `Guides and Info/2026-10-05-600-rps-ceiling-snapshot.md` | Create | Readings and verdict |
| `AGENTS.md` | Modify | One bullet in §4 |

---

### Task 1: Set up the config and the cluster

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Produces: a config that launches run154 with the new mix on whatever pin the cluster is on.

- [ ] **Step 1: Edit the config**

Replace the header comment and the description with:

```yaml
# Both-off S2 ceiling snapshot. Slot run154.

scenario_id: 2
scenario_name: sustained_overload
condition: baseline
run_number: 154
description: >
  Both controllers off. Paper-C1 pin. Ceiling snapshot, mix 150/30/150/250/250.
  See docs/superpowers/specs/2026-10-05-600-rps-ceiling-snapshot-design.md.
```

and the `user_counts` block with:

```yaml
  user_counts:
    getproduct:   150
    postcheckout: 30
    getcart:      150
    postcart:     250
    emptycart:    250
```

Leave `spawn_rate: 50`, `paper_cpu_reconcile: false`, the `scale_constraints`, and `log_folder: baseline_no_topfull_sustained_overload_run154` as they are.

- [ ] **Step 2: Check the VMs are up and the cluster is on Paper-C1**

Run (PowerShell):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_restore_check.sh
```

Expected: nodes `Ready`; the restore check prints `ok` lines and exits 0. If the VMs are stopped, start them with `gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb`, refresh `HostName` in `~/.ssh/config` per `Guides and Info/CONNECT-VMS.md`, and wait 3 minutes. If the check fails, run `ssh topfull-master bash -s < experiments\latch_restore_fix.sh`, then run the check again.

- [ ] **Step 3: Commit**

```bash
git add experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "config: S2 ceiling snapshot mix 150/30/150/250/250 at run154"
```

---

### Task 2: Reading script

**Files:**
- Create: `experiments/ceiling_reading.sh`

**Interfaces:**
- Produces: `bash -s -- cpu <seconds> <process-regex>` prints `busy_cores`, `steal_pct`, and per-process CPU lines for processes matching the regex; `bash -s -- proxies` prints `kubectl top` istio-proxy rows plus Envoy thread count and `--concurrency` for the frontend pod and the hottest non-frontend proxy.

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# One-off readings for the 600 req/s ceiling snapshot. Send over ssh as a script on stdin:
#   ssh <alias> bash -s -- cpu 60 'regex'  < experiments/ceiling_reading.sh
#   ssh topfull-master bash -s -- proxies  < experiments/ceiling_reading.sh
mode="$1"
case "$mode" in
  cpu)
    secs="$2"; pat="${3:-NOMATCH}"
    ta=$(mktemp); tb=$(mktemp)
    a=$(head -n1 /proc/stat); ps -eo pid=,cputimes=,args= > "$ta"
    sleep "$secs"
    b=$(head -n1 /proc/stat); ps -eo pid=,cputimes=,args= > "$tb"
    n=$(nproc)
    echo "$a" "$b" | awk -v n="$n" '{
      for (i = 2; i <= 9; i++) { x[i] = $i; y[i] = $(i + 9) }
      ta = 0; tb = 0
      for (i = 2; i <= 9; i++) { ta += x[i]; tb += y[i] }
      d = tb - ta
      idle = (y[5] + y[6]) - (x[5] + x[6])
      printf "nproc %d\nbusy_cores %.2f\nsteal_pct %.2f\n", n, (d - idle) / d * n, (y[9] - x[9]) / d * 100 }'
    echo "### processes matching /$pat/ (percent of one core over ${secs}s)"
    awk -v secs="$secs" -v pat="$pat" 'FNR==NR { ca[$1] = $2; next }
      ($1 in ca) { line = $0; sub(/^ *[0-9]+ +[0-9]+ +/, "", line)
        if (line ~ pat) printf "%6.1f  %s\n", 100 * ($2 - ca[$1]) / secs, substr(line, 1, 100) }' "$ta" "$tb" | sort -rn
    rm -f "$ta" "$tb"
    ;;
  proxies)
    echo "### istio-proxy millicores"
    kubectl top pod --containers -n default | awk 'NR==1 || $2 ~ /istio-proxy/'
    fe=$(kubectl get pod -n default -l app=frontend -o jsonpath='{.items[0].metadata.name}')
    hot=$(kubectl top pod --containers -n default | awk '$2 ~ /istio-proxy/ && $1 !~ /^frontend/ {gsub(/m/,"",$3); print $3, $1}' | sort -rn | head -1 | awk '{print $2}')
    for p in $fe $hot; do
      echo "### $p"
      kubectl exec "$p" -n default -c istio-proxy -- sh -c '
        pid=$(ps -eo pid,args | awk "/[e]nvoy -c/ {print \$1; exit}")
        echo "envoy pid ${pid:-none}"
        [ -n "$pid" ] && echo "envoy threads $(ls /proc/$pid/task | wc -l)"
        ps -eo args | tr " " "\n" | grep -A1 -- "--concurrency" || echo "--concurrency absent (default)"'
    done
    ;;
  *)
    echo "usage: cpu <secs> [regex] | proxies" >&2
    exit 2
    ;;
esac
```

- [ ] **Step 2: Smoke-run it on the idle cluster**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s -- cpu 5 "proxy_online|collector|metric_collector" < experiments\ceiling_reading.sh
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 bash -s -- cpu 5 < experiments\ceiling_reading.sh
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s -- proxies < experiments\ceiling_reading.sh
```

Expected: `nproc 8` and a small `busy_cores` on master; `nproc 16` on the worker; the `proxies` call prints one row per sidecar and, for two pods, an `envoy threads` line and either a `--concurrency` value or `absent (default)`. If `kubectl top` returns an error, wait two minutes for metrics-server and run it again. Fix any awk or shell error in the script before moving on.

- [ ] **Step 3: Commit**

```bash
git add experiments/ceiling_reading.sh
git commit -m "tools: ceiling_reading.sh for the 600 req/s snapshot"
```

---

### Task 3: Post-hold summary script

**Files:**
- Create: `experiments/ceiling_summary.py`

**Interfaces:**
- Produces: `python experiments/ceiling_summary.py <run_dir>` prints the gate results and the numbers the verdict needs. Exit code is 0 when every gate passes.

- [ ] **Step 1: Write the script**

```python
"""Numbers for the 600 req/s ceiling snapshot, from one pulled run folder."""
import csv
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

TAGS = ["getproduct", "postcheckout", "getcart", "postcart", "emptycart"]
DROP_HEAD, DROP_TAIL = 60, 5


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def tag_stats(d, tag):
    rows = list(csv.DictReader(open(d / f"{tag}.csv")))
    rows = rows[DROP_HEAD:-DROP_TAIL]
    rps = statistics.mean(float(r["RPS"]) for r in rows)
    p95 = statistics.mean(float(r["Latency95"]) for r in rows)
    return rps, p95


def main(d):
    d = Path(d)
    gates = []

    total_rows = sum(1 for _ in open(d / "total.csv")) - 1
    gates.append(("total.csv rows >= 540", total_rows >= 540, total_rows))

    inbound = list(csv.DictReader(open(d / "service_inbound.csv")))
    stamps = [ts(r["timestamp"]) for r in inbound]
    span = (max(stamps) - min(stamps)).total_seconds()
    gates.append(("mesh span 480-900 s", 480 <= span <= 900, round(span)))

    fe = [r for r in inbound if r["service"] == "frontend"]
    gaps = [(ts(b["timestamp"]) - ts(a["timestamp"])).total_seconds() for a, b in zip(fe, fe[1:])]
    gap2 = 100 * sum(g >= 2 for g in gaps) / max(len(gaps), 1)
    gates.append(("frontend inbound gap2 <= 10%", gap2 <= 10, round(gap2, 1)))

    modal = {}
    for r in csv.DictReader(open(d / "resource_usage.csv")):
        modal.setdefault(r["service"], Counter())[r["replica_count"]] += 1
    reps = {s: int(c.most_common(1)[0][0]) for s, c in modal.items()}
    bad = {s: n for s, n in reps.items() if n != (4 if s == "frontend" else 1)}
    gates.append(("replica pin (frontend 4, others 1)", not bad, bad or "ok"))

    thr = [float(r["threshold"]) for r in csv.DictReader(open(d / "topfull_throttle.csv"))]
    low = 100 * sum(t < 10000 for t in thr) / max(len(thr), 1)
    gates.append(("Layer A below 10000 on <= 1% of rows", low <= 1, round(low, 2)))

    print("== gates")
    for name, ok, val in gates:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {val}")

    print("== per tag (mean over rows 60..end-5)")
    sums = 0.0
    p95s = {}
    for tag in TAGS:
        rps, p95 = tag_stats(d, tag)
        sums += rps
        p95s[tag] = p95
        print(f"{tag:13s} mean RPS {rps:7.1f}  mean P95 {p95:7.0f} ms")
    print(f"sum of tag mean RPS: {sums:.1f}")

    lam = [
        (int(b["total"]) - int(a["total"])) / (ts(b["timestamp"]) - ts(a["timestamp"])).total_seconds()
        for a, b in zip(fe, fe[1:])
        if ts(b["timestamp"]) > ts(a["timestamp"])
    ]
    print(f"frontend inbound lambda (mean of deltas): {statistics.mean(lam):.1f} req/s")
    return 0 if all(ok for _, ok, _ in gates) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 2: Smoke-run it on an existing folder**

```powershell
python experiments/ceiling_summary.py "experiments/results/new vms/baseline_no_topfull_sustained_overload_run100"
```

Expected: a gates block and a per-tag block print without a traceback, with five tag lines and a sum. Gate results on run100 do not matter (its Layer A, pin, and mix differ); only that the script runs. Fix any `KeyError` or parse error.

- [ ] **Step 3: Commit**

```bash
git add experiments/ceiling_summary.py
git commit -m "tools: ceiling_summary.py for the 600 req/s snapshot"
```

---

### Task 4: Run the hold and take the readings

**Files:**
- Create (by the runner): `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run154/`

**Interfaces:**
- Consumes: Task 1 config, Task 2 script.
- Produces: the pulled run154 folder and the saved reading text in it.

- [ ] **Step 1: Clear stale remote scripts**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

Expected: no output, exit 0.

- [ ] **Step 2: Start the hold in the background**

```powershell
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Run it as a background shell so its output goes to a terminal file you can read. Note the time the log says Locust has launched (the runner prints the Locust launch step). Call that T0.

- [ ] **Step 3: At T0 + 120 s, start the readings in parallel**

Run all four at once, each writing to `$env:TEMP`. Create the folder first if it doesn't exist:

```powershell
$r = "$env:TEMP\ceiling_run154"; New-Item -ItemType Directory -Force $r | Out-Null
Start-Job { ssh -o BatchMode=yes topfull-master bash -s -- cpu 60 "proxy_online|metric_collector|envoy_retry_collector|resource_usage_collector|topfull_throttle_collector" < "$using:PWD\experiments\ceiling_reading.sh" > "$using:r\master_cpu.txt" 2>&1 }
Start-Job { ssh -o BatchMode=yes topfull-worker-1 bash -s -- cpu 60 < "$using:PWD\experiments\ceiling_reading.sh" > "$using:r\worker_cpu.txt" 2>&1 }
Start-Job { ssh -o BatchMode=yes topfull-load bash -s -- cpu 60 "locust" < "$using:PWD\experiments\ceiling_reading.sh" > "$using:r\load_cpu.txt" 2>&1 }
Start-Sleep -Seconds 30
ssh -o BatchMode=yes topfull-master bash -s -- proxies < experiments\ceiling_reading.sh | Out-File -Encoding utf8 "$r\proxies.txt"
Get-Job | Wait-Job | Out-Null; Get-Job | Remove-Job
Get-ChildItem $r
```

`<` redirection inside `Start-Job` is not valid PowerShell; if it errors, run each as `cmd /c "ssh -o BatchMode=yes topfull-master bash -s -- cpu 60 ... < experiments\ceiling_reading.sh > %TEMP%\ceiling_run154\master_cpu.txt"` in a background shell instead. The `proxies` reading is taken at the middle of the 60 s window (the 30 s sleep).

Expected: four non-empty files in `$r`. Open each and check `busy_cores`, `steal_pct`, and the process lines are present. If a file is empty or holds an error, take that reading again while the hold is still running; the hold lasts 600 s, so there is time for one retry.

- [ ] **Step 4: Wait for the runner to finish, then pull**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Copy-Item $r "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run154\readings" -Recurse
```

Expected: the run154 folder exists with `total.csv`, the five tag CSVs, `service_inbound.csv`, `resource_usage.csv`, `topfull_throttle.csv`, and a `readings` folder with four files.

- [ ] **Step 5: Run the summary**

```powershell
python experiments/ceiling_summary.py "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run154"
```

Expected: gates and per-tag numbers print. If any gate FAILs, the hold does not count: record it as a failed folder (do not relaunch into it), bump the config to run155, and go to Task 5 with the verdict "gate failed" only.

---

### Task 5: Score, write up, restore, commit

**Files:**
- Create: `Guides and Info/2026-10-05-600-rps-ceiling-snapshot.md`
- Modify: `AGENTS.md` (§4, one bullet), `experiments/configs/scenario_2_baseline_no_topfull.yaml` (bump to run155)

- [ ] **Step 1: Score each candidate against the lines**

Read the saved files and the summary. For each of the four candidates write down the number and over / under / cleared / inconclusive using the lines in Global Constraints:

- Candidate 1 (master): `busy_cores` from `master_cpu.txt` of 8; the proxy process line (`proxy_online_boutique`, or `go run` plus its child) as percent of one core.
- Candidate 2 (worker): `busy_cores` of 16 and `steal_pct` from `worker_cpu.txt`.
- Candidate 3 (Envoy): the sidecar millicores in `proxies.txt` against `concurrency × 1000` m; `--concurrency absent (default)` → inconclusive.
- Candidate 4 (shared path): `emptycart` mean P95 from the summary, plus `getproduct` and `getcart` P95.

Then apply the ceiling band (450 through 705) to the summed tag RPS and apply the naming rule from the spec §5.

- [ ] **Step 2: Write the guide**

Create `Guides and Info/2026-10-05-600-rps-ceiling-snapshot.md` with: the setup in two sentences (run154, mix, Paper-C1, 600 s, both off), the gate table from the summary, a table of the four candidates (reading, line, status), the per-tag table, the summed RPS and band, and one paragraph with the verdict and which isolation hold in spec §7 comes next. State plainly what was and was not measured, including any retried reading or the 90 m sidecar fallback if it was used.

- [ ] **Step 3: Restore Paper-C1 and check**

If the sidecar was moved to 90 m, set it back to 100 m with `ssh topfull-master bash -s < experiments\latch_restore_fix.sh`. Then:

```powershell
ssh -o BatchMode=yes topfull-master bash -s < experiments\latch_restore_check.sh
```

Expected: exit 0, all `ok`. Do not stop the VMs.

- [ ] **Step 4: Bump the config and update AGENTS.md**

In `experiments/configs/scenario_2_baseline_no_topfull.yaml` set `run_number: 155` and `log_folder: baseline_no_topfull_sustained_overload_run155`, and set the header comment to say run154 was the ceiling snapshot. In `AGENTS.md` §4 add one bullet after the last S2 controller-arms bullet: slot run154, mix, achieved tag-sum, verdict, link to the new guide, next free both-off slot **run155**. Replace each "next free both-off slot run154" mention in §4 and the "Not done yet" callout with run155.

- [ ] **Step 5: Commit**

```bash
git add "Guides and Info/2026-10-05-600-rps-ceiling-snapshot.md" AGENTS.md experiments/configs/scenario_2_baseline_no_topfull.yaml "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run154"
git commit -m "data: 600 req/s ceiling snapshot run154 and verdict"
```

---

## Self-review

- **Spec coverage:** §3 hold → Tasks 1 and 4; §4 readings → Tasks 2 and 4 (candidates 1–3 via `ceiling_reading.sh`, candidate 4 and the "also record" list via `ceiling_summary.py`); §5 verdicts → Task 5 Step 1; §6 gates and bookkeeping → Tasks 3, 4 Step 5, 5; §7 isolation holds are deliberately not planned (spec says next spec); §8 out of scope respected.
- **One deviation from the spec:** per-tag RPS and P95 come from the pulled Locust CSVs over the same window (rows 60 to end − 5), not from a live read of the stats ports. Same data, no extra tooling. Spec §4 "Ceiling, per tag" and "Candidate 4" should be read that way.
- **Names:** `ceiling_reading.sh` modes `cpu` and `proxies`, and `ceiling_summary.py`, are used identically in every task.
