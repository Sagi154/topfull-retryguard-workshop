# S1/S2 Baseline Metric Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two clean, full-duration baseline folders (S1 then S2) that contain every metric we currently collect, then verify those files and values are expected so later scenario analysis can start from a known-good stack.

**Architecture:** No collector code changes. Use the already-landed master-only mesh scrape (`transport: network_prometheus`, HTTP GET `http://<pod_ip>:15020/stats/prometheus`) plus resource-usage and TopFull throttle collectors, both on. Before each launch, inspect leftovers and **notify in chat if dirty before killing anything**. After S1 teardown, wait a 180 s cool-off and re-clean before S2. Pull into `campaign_48/` scenario subfolders and apply a written pass/fail checklist.

**Tech Stack:** `experiments/run_scenario.py`, OpenSSH host aliases (`topfull-master`, `topfull-load`, `topfull-worker-1`), Python 3 on Windows for the verify scripts, existing YAMLs.

## Current stack (locked by latest commits on `main`)

From [Latest mesh collector commits](d914829c-6e46-407a-b492-3d39a8e840ab) (do not re-derive):

- `6264742` — collector rewrite: master HTTP GET `:15020/stats/prometheus`; `kubectl exec` / `docker exec` / worker two-hop pull deleted. `run_scenario.py` seeds `pod_ips` via `discover_service_pod_ips()`, tmux `envoyretry` on master. CSVs land in TopFull `record_path` (`src/logs`) during the run — `record_path` is **not** passed in `/tmp/envoy_retry_params.json`.
- `d3c49a1` — all 16 YAMLs now `transport: network_prometheus`; `exec_mode` and `infra.worker_ssh_host` removed. S1 baseline bumped `run15` → **`run20`** so the HTTP-transport scratch holds are not overwritten.
- S1 YAML jumped **11 → 15 → 20** during 2026-09-13 work. Local `campaign_48/S1_normal_op/` only has run4–10. **run11–19 (including the AGENTS.md run18 both-off / run19 mesh-on +37 ms pair) are likely on master only.** Task 1 must list them and never overwrite.
- Local S2 baseline folders: run4–13, 15–16. **run14 and run17 are not local.** Confirm both on master before launch. YAML S2 is already **run17**.
- Outbound `2xx`/`4xx`/`5xx` on `service_edges.csv` are live on this transport. A run writes mesh files **or** legacy `envoy_retries_*.csv`, never both.
- Not this plan: S6 YAMLs still point at completed `run3` (overwrite trap if someone launches S6 later).

## Global Constraints

- Each task is executed by a **fresh grok 4.6 subagent** (`cursor-grok-4.6-high-fast` only). Do not use expensive models.
- SSH host aliases only; connect as `idozacharia`. Follow [Guides and Info/CONNECT-VMS.md](Guides and Info/CONNECT-VMS.md). Never hardcode public IPs.
- Do **not** change Locust `user_counts` or `spawn_rate`.
- Do **not** flip collector flags — mesh, resource-usage, and throttle stay `enabled: true`. RetryGuard stays off.
- Keep full deck durations already in the YAMLs: S1 **300 s**, S2 **600 s**. These are checkpoint runs, not 180 s scratch cells.
- If a target `log_folder` already exists on master, **bump** `run_number` / `log_folder` before launch. Never overwrite.
- Before any kill/clean: **list leftovers in chat first** (`NOTIFY: environment is dirty`), then clean.
- Cool-off between runs is **180 s** after the S1 runner returns (teardown already ran), then a second clean-inspect before S2.
- Do not raise Locust users. Do not treat these as campaign-matrix repeats. Do not stop the VMs unless the user asks.
- Edit YAMLs as UTF-8 with LF only (no PowerShell `Set-Content` rewrite).
- Do not commit unless the user asks.
- Do not add mid-hold curl probes. Pass/fail is collected artifacts only.
- Comparison references (do not expect campaign-run4 numbers exactly): S1 run10 both-off ~900 ms getcart / Fail ~1.5%; docker-local mesh run7/8 ~1370 ms / Fail ~27% is the **failure** shape; AGENTS.md cool pair run18 off / run19 mesh-on ~**+37 ms** tax is the new mesh target.

## File map

- Read: [experiments/configs/scenario_1_baseline.yaml](experiments/configs/scenario_1_baseline.yaml) — currently `run_number: 20`, `log_folder: baseline_topfull_no_retryguard_normal_op_run20`, `duration_seconds: 300`, all collectors on, `transport: network_prometheus`
- Read: [experiments/configs/scenario_2_baseline.yaml](experiments/configs/scenario_2_baseline.yaml) — currently `run_number: 17`, `log_folder: baseline_topfull_no_retryguard_sustained_overload_run17`, `duration_seconds: 600`, same collector flags
- Read: [Guides and Info/METRICS-GATHERED.md](Guides and Info/METRICS-GATHERED.md), [Guides and Info/METRICS-COLLECTION-GUIDE.md](Guides and Info/METRICS-COLLECTION-GUIDE.md) §10
- Create (execution start): [docs/superpowers/plans/2026-09-13-s1-s2-baseline-metric-checkpoint.md](docs/superpowers/plans/2026-09-13-s1-s2-baseline-metric-checkpoint.md) — this plan, checkbox-tracked
- Create (after verify): [docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md](docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md) — measured results + pass/fail
- Modify after both runs: the two YAMLs (bump to next free slots) and [AGENTS.md](AGENTS.md) §4
- Pull dest: `experiments/results/campaign_48/S1_normal_op/` and `.../S2_sustained_overload/`

```mermaid
flowchart LR
  slots[Confirm free slots]
  clean1[Inspect and notify if dirty then clean]
  s1[S1 run20 300s all collectors]
  pull1[Pull and inventory S1]
  verify1[Semantic verify S1]
  cool[180s cool-off]
  clean2[Re-inspect and notify if dirty then clean]
  s2[S2 run17 600s all collectors]
  pull2[Pull and inventory S2]
  verify2[Semantic verify S2]
  writeup[Checkpoint write-up and bump YAMLs]
  slots --> clean1 --> s1 --> pull1 --> verify1 --> cool --> clean2 --> s2 --> pull2 --> verify2 --> writeup
```

## What "all metrics" means (must exist in both folders)

Must be **present and non-empty**:

- Locust: `getproduct.csv`, `postcheckout.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv`, `total.csv`
- Mesh: `service_edges.csv`, `service_inbound.csv`, `envoy_retry_collector.log`
- Layer 2: `resource_usage.csv`, `resource_usage_collector.log`
- Throttle: `topfull_throttle.csv`, `topfull_detect.csv`, `topfull_throttle_collector.log`
- Manifest: `run_manifest.json`, `service_capacity.json`

Must be **absent** (baseline, new transport):

- `retryguard.log`
- `envoy_retries_frontend.csv` / `envoy_retries_checkoutservice.csv` (legacy shape; new collector does not write these)

`num_agent.csv` may exist and be empty — not a metric.

## Expected vs not-a-bug

**S1 (normal op):** Fail near zero after spawn; getcart P95 in the run10-like band (~0.7–1.1 s), **not** the docker-local ~1.37 s / ~25% Fail shape. Mesh inbound covers all 11 Boutique services; outbound `2xx` is live (non-zero on hot edges). Layer B `overloaded` mostly 0. Layer A `threshold` may sit at 10000 (uncapped sentinel) — that is OK on S1. `run_manifest.json` records `transport: network_prometheus` and `exec_host: topfull-master`.

**S2 (sustained overload):** Fail **elevated** on getcart / getproduct / postcheckout is expected (SLO-miss Fail, often HTTP 200). Frontend outbound `retry` deltas should be > 0. Layer A may show more `*_fresh=0` under proxy saturation — not a fail unless **all** Layer A values are zero even on `fresh=1` rows. Layer B utilization higher than S1; `overloaded` may still be 0 at paper quotas (known). Direct-path getcart P95 > 1 s is expected and is **not** a collector-tax fail.

Paper CPU after reconcile (no `scale_constraints`): frontend/cart/checkout/ads/currency **1000m**, productcatalog **500m**, recommendation **2000m**, payment **1000m** (default paper limit). Leftover checkout **100m** from an old S3 is dirty — notify, then let the runner heal it.

---

### Task 1: Save the plan and confirm free slots

**Files:**
- Create: `docs/superpowers/plans/2026-09-13-s1-s2-baseline-metric-checkpoint.md`
- Read: `experiments/configs/scenario_1_baseline.yaml`, `experiments/configs/scenario_2_baseline.yaml`

**Interfaces:**
- Consumes: this plan
- Produces: locked slot names (`s1_log_folder`, `s2_log_folder`) used by every later task. Default: S1 `baseline_topfull_no_retryguard_normal_op_run20`, S2 `baseline_topfull_no_retryguard_sustained_overload_run17`.

- [ ] **Step 1: Write the plan file** with this document’s header, constraints, and checkbox tasks (do not edit the CreatePlan UI file as a substitute).

- [ ] **Step 2: Confirm the default slots are free locally and on master**

```powershell
Test-Path experiments\results\campaign_48\S1_normal_op\baseline_topfull_no_retryguard_normal_op_run20
Test-Path experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run17
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls -d /home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run20 /home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run17 2>&1; echo ---; ls -d /home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run1[1-9] /home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run20 2>/dev/null; ls -d /home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1[5-9] 2>/dev/null"
```

Expected: default slots missing locally. On master, explicitly list S1 `run11`–`run20` and S2 `run14`/`run17` (YAML jumped 11→15→20; run18/run19 are the HTTP-transport +37 ms pair and must stay). If a remote folder already exists for the default slot, bump that YAML’s `run_number` and `log_folder` to the next free integer (UTF-8, LF) and announce the new names before Task 2. If SSH times out, start the 3 VMs and refresh `HostName` per CONNECT-VMS.md, then retry — do not invent IPs.

If master still has `..._normal_op_run18` / `run19`, note them as the +37 ms credit pair and leave them alone. Do not pull-overwrite local campaign paper slots (S1 run4–6, S2 run4–6).

---

### Task 2: Inspect leftovers, notify if dirty, then clean (before S1)

**Files:** none (commands only).

**Interfaces:**
- Consumes: live SSH
- Produces: a written dirty/clean report in chat; a cleaned cluster; confirmed paper CPU and VS `attempts: 3`

- [ ] **Step 1: Cluster health**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "whoami; kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: `whoami` is `idozacharia`; nodes Ready; Boutique pods Running (2/2). If kubeconfig is missing (`localhost:8080 refused`), this is a user-config issue, not API-down — stop and report.

- [ ] **Step 2: Inspect leftovers — notify before killing**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "echo '=== tmux ==='; tmux ls 2>/dev/null || echo none; echo '=== procs ==='; pgrep -af 'retryguard|envoy_retry|resource_usage|topfull_throttle|deploy_rl|proxy_online|metric_collector|locust' || true; echo '=== tmp ==='; ls /tmp/rg_*.sh /tmp/envoy_retry_params.json 2>/dev/null || echo none"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "echo '=== tmux ==='; tmux ls 2>/dev/null || echo none; echo '=== locust ==='; pgrep -af locust || echo none"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "echo '=== tmux ==='; tmux ls 2>/dev/null || echo none; echo '=== old mesh ==='; pgrep -af envoy_retry || echo none; ls /tmp/rg_mesh_local.sh /tmp/envoy_retry_params.json 2>/dev/null || echo none"
```

If anything other than idle kube/docker is up, print **`NOTIFY: environment is dirty`** and list every leftover **before** Step 3.

- [ ] **Step 3: Clean only after the notify**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/rg_mesh_local.sh"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "tmux kill-server 2>/dev/null; sudo rm -f /tmp/rg_mesh_local.sh /tmp/envoy_retry_params.json; true"
```

Do not `tmux kill-server` on master here if kube-system tmux is not in use; leftover experiment tmux on master **is** dirty and should be listed in Step 2, then killed with `tmux kill-server` on master only after notify.

- [ ] **Step 4: Confirm VS retries and paper CPU**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,CPU_LIMIT:.spec.template.spec.containers[0].resources.limits.cpu --no-headers; echo ---VS---; kubectl get virtualservice -n default -o json | python3 -c `"import json,sys; d=json.load(sys.stdin);`
`[print(i['metadata']['name'], (i.get('spec',{}).get('http') or [{}])[0].get('retries')) for i in d.get('items',[])]`""
```

Expected: paper limits as in the header (checkout **1000m**, not 100m). VS `attempts` is 3 or retries present. If checkout is 100m, **NOTIFY** leftover S3 limit — continue; `run_scenario.py` reconciles before load, and Task 5 must confirm the healed limit in `service_capacity.json` / post-run `kubectl`.

---

### Task 3: Launch S1 baseline (full 300 s, all collectors)

**Files:**
- Read only: `experiments/configs/scenario_1_baseline.yaml` (do not shorten duration)

**Interfaces:**
- Consumes: clean cluster + locked S1 slot from Task 1
- Produces: completed run on master under `results_base_path/<s1_log_folder>/`

- [ ] **Step 1: Confirm YAML still says 300 s, collectors on, RetryGuard off, `transport: network_prometheus`, and the locked slot**

- [ ] **Step 2: Clear stale `/tmp` runner scripts (AGENTS.md §6), then launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

Expected: runner prints mesh `transport: network_prometheus`, starts tmux `envoyretry` / `resourceusage` / `throttle` on **master** (not worker), Locust on load, then teardown + `scp` hint to `experiments/results/campaign_48/S1_normal_op/`. Wall clock ~7–8 min (preflight + 300 s + stop/collect).

- [ ] **Step 3: Mid-run (optional peek, ~60 s in) confirm collectors are the new transport**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "tmux ls; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/service_edges.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/service_inbound.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/topfull_throttle.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/resource_usage.csv 2>&1 | head"
```

Expected: CSVs already growing on master (no worker two-hop). If mesh files are only under `/home/idozacharia/experiments/mesh_local/`, the old worker-local path is live — **stop and report**; do not continue to S2.

---

### Task 4: Pull S1 and pass the file-inventory gate

**Files:**
- Create via scp: `experiments/results/campaign_48/S1_normal_op/<s1_log_folder>/`

**Interfaces:**
- Consumes: Task 3 remote folder
- Produces: local folder whose file set matches “all metrics” above

- [ ] **Step 1: Pull**

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run20 experiments/results/campaign_48/S1_normal_op/
```

Use the locked folder name from Task 1 if bumped.

- [ ] **Step 2: Inventory**

```powershell
python -c "from pathlib import Path; p=Path('experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run20'); need=['getproduct.csv','postcheckout.csv','getcart.csv','postcart.csv','emptycart.csv','total.csv','service_edges.csv','service_inbound.csv','envoy_retry_collector.log','resource_usage.csv','resource_usage_collector.log','topfull_throttle.csv','topfull_detect.csv','topfull_throttle_collector.log','run_manifest.json','service_capacity.json']; forbid=['retryguard.log','envoy_retries_frontend.csv','envoy_retries_checkoutservice.csv']; print('missing',[f for f in need if not (p/f).exists() or (p/f).stat().st_size==0]); print('unexpected',[f for f in forbid if (p/f).exists()]); print('sorted'); [print(x.name, x.stat().st_size) for x in sorted(p.iterdir())]"
```

Expected: `missing []`, `unexpected []`. Locust CSVs ~301 lines (header + ~300 rows).

If inventory fails, **do not start S2**. Diagnose collector logs first.

---

### Task 5: Semantic verify S1

**Files:**
- Read: the pulled S1 folder
- Compare against: `experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run10/` (both-off) and run7 (old both-on docker-local)

**Interfaces:**
- Consumes: Task 4 local folder
- Produces: a written S1 verdict (PASS / FAIL with numbers)

- [ ] **Step 1: Run this verifier (skip first 30 Locust rows)**

```python
from pathlib import Path
import json, pandas as pd
p = Path("experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run20")
m = json.loads((p/"run_manifest.json").read_text())
print("transport", m.get("envoy_retry_collector"))
print("duration", m.get("duration_seconds"), "retryguard", m.get("retryguard",{}).get("enabled"))
for name in ["getcart","getproduct","postcheckout","postcart","emptycart","total"]:
    df = pd.read_csv(p/f"{name}.csv").iloc[30:]
    print(name, "rows", len(df)+30, "RPS", round(df.RPS.mean(),2), "Fail", round(df.Fail.mean(),2), "P95", round(df.Latency95.mean(),1), "Goodput", round(df.Goodput.mean(),2))
edges = pd.read_csv(p/"service_edges.csv")
inn = pd.read_csv(p/"service_inbound.csv")
print("inbound services", sorted(inn.service.unique()))
print("edges 2xx max", int(edges["2xx"].max()), "retry max", int(edges.retry.max()))
print("hot 2xx", edges.groupby(["caller","target"])["2xx"].max().sort_values(ascending=False).head(8).to_string())
ru = pd.read_csv(p/"resource_usage.csv")
print("resource services", sorted(ru.service.unique()), "frontend mem>0", bool((ru.loc[ru.service=="frontend","memory_working_set_bytes"]>0).any()))
th = pd.read_csv(p/"topfull_throttle.csv")
det = pd.read_csv(p/"topfull_detect.csv")
print("layerA fresh1", int((th.threshold_fresh==1).mean()*100), "% admitted mean fresh", round(th.loc[th.admitted_fresh==1,"admitted_rps"].mean(),2) if (th.admitted_fresh==1).any() else "NO_FRESH")
print("detect cpu>0", bool((det.cadvisor_cpu>0).any()), "overloaded", int(det.overloaded.sum()))
```

S1 PASS only if all of these hold:

- `transport` is `network_prometheus` and RetryGuard is false
- Locust row count ≈ 300
- getcart Fail mean is **single-digit** (run10-like), not ~25 (run7/8 docker-local)
- getcart P95 mean is **< 1200 ms** (run10-like / +37 ms tax), not ~1370+
- inbound unique services include the 11 names in `ALL_SERVICES` (`frontend` … `redis-cart`); `redis-cart` inbound may be zeros
- `service_edges.csv` `2xx` max **> 0** on at least `frontend → cartservice` and `frontend → productcatalogservice`
- `resource_usage.csv` has 11 services and frontend memory > 0
- `topfull_throttle.csv` is not all zeros; at least some `threshold_fresh==1` rows; `topfull_detect.csv` has `cadvisor_cpu > 0`; `overloaded` near 0

S1 FAIL (stop; do not start S2): missing files, docker-local Fail/P95 shape, edges `2xx` still all zero, Layer A all zeros, or mesh still writing on the worker only.

---

### Task 6: Cool-off, then inspect/notify/clean before S2

**Files:** none.

**Interfaces:**
- Consumes: S1 teardown complete
- Produces: second dirty/clean report; quiet cluster

- [ ] **Step 1: Wait 180 s after the S1 runner returns** (do not start S2 immediately — frontend/goproxy queues need to drain).

- [ ] **Step 2: Repeat Task 2 Steps 1–4 verbatim** (inspect → **notify if dirty** → clean → VS/CPU check).

Expected after a successful S1 teardown: idle. If Locust, `envoyretry`, `throttle`, or `deploy_rl` is still up, that is dirty — notify, then clean. Checkout CPU must be 1000m, not 100m.

---

### Task 7: Launch S2 baseline (full 600 s, all collectors)

**Files:**
- Read only: `experiments/configs/scenario_2_baseline.yaml` (do not shorten duration, do not raise users)

**Interfaces:**
- Consumes: Task 6 clean cluster + locked S2 slot
- Produces: completed run on master under `results_base_path/<s2_log_folder>/`

- [ ] **Step 1: Confirm YAML still says 600 s, collectors on, RetryGuard off, `transport: network_prometheus`, locked slot**

- [ ] **Step 2: Clear `/tmp` scripts, then launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
```

Expected: same collector start pattern as S1. Wall clock ~12–14 min.

- [ ] **Step 3: Optional ~60 s peek** — same master `src/logs` CSV check as Task 3 Step 3. Mesh files must be on master.

---

### Task 8: Pull S2 and pass the file-inventory gate

**Files:**
- Create via scp: `experiments/results/campaign_48/S2_sustained_overload/<s2_log_folder>/`

- [ ] **Step 1: Pull**

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run17 experiments/results/campaign_48/S2_sustained_overload/
```

Use the locked name if bumped.

- [ ] **Step 2: Same inventory Python as Task 4**, pointed at the S2 folder. Locust CSVs ~601 lines. `missing []`, `unexpected []`.

If inventory fails, do not write a “ready for analysis” claim.

---

### Task 9: Semantic verify S2 and cross-check vs S1

**Files:**
- Read: pulled S2 folder; S1 folder from Task 5

- [ ] **Step 1: Reuse the Task 5 verifier** with the S2 path. Also print frontend outbound retry deltas:

```python
from pathlib import Path
import pandas as pd
p = Path("experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run17")
e = pd.read_csv(p/"service_edges.csv")
hot = e[e.caller.eq("frontend") & e.target.isin(["cartservice","productcatalogservice","checkoutservice"])]
print(hot.groupby("target")[["total","2xx","5xx","retry"]].agg(["min","max"]))
```

S2 PASS only if:

- File set complete; `transport: network_prometheus`
- Locust rows ≈ 600
- getcart / getproduct / postcheckout **Fail elevated** vs S1 (this is the overload signal, not a collector bug)
- Frontend hot-edge `2xx` max > 0 (Prometheus class counters live)
- Frontend hot-edge `retry` **increases** over the run (`max > min`)
- Resource + detect CSVs have real CPU/memory under load
- Layer A is not all-zero on `*_fresh==1` rows (fresh=0 under saturation is allowed)

S2 FAIL: missing mesh/throttle files, edges `2xx` still all zero, Layer A all zeros, or S2 Fail/P95 indistinguishable from S1 (load never engaged).

- [ ] **Step 2: Cross-scenario sanity** — S1 Fail << S2 Fail on getcart; S1 P95 << S2 P95; S2 retries > S1 retries. If S1 looks like old docker-local tax, say so even if S2 files exist.

---

### Task 10: Write the checkpoint and bump YAMLs

**Files:**
- Create: `docs/superpowers/specs/2026-09-13-s1-s2-baseline-metric-checkpoint.md`
- Modify: `experiments/configs/scenario_1_baseline.yaml` (next free slot, keep 300 s / collectors on)
- Modify: `experiments/configs/scenario_2_baseline.yaml` (next free slot, keep 600 s / collectors on)
- Modify: `AGENTS.md` §4 — these two folders exist; mesh `2xx` live; leftover collector tax vs run10 / run18–19

**Interfaces:**
- Consumes: Task 5 and Task 9 verdicts + numbers
- Produces: a short results note a later analysis session can trust

- [ ] **Step 1: Write the checkpoint spec** with: slot names, dirty/clean notifies, per-file inventory, S1/S2 Locust means, mesh 2xx/retry, Layer A freshness, Layer B overloaded count, pass/fail, and “ready / not ready for scenario analysis.”

- [ ] **Step 2: Bump YAMLs** so the next launch cannot overwrite these folders (S1 default → run21, S2 default → run18, unless Task 1 already used higher numbers). UTF-8, LF.

- [ ] **Step 3: Update AGENTS.md §4** Current status with the two new folders and the verdict. Do not claim `campaign_48/` matrix rows changed; these are post-campaign checkpoint runs stored in the same tree.

---

## Self-review

- Spec coverage: clean-env + notify, cool-off, all collector files, S1 and S2 expected-value gates, no load-calibration, no curl probes, no YAML duration/user edits.
- Placeholders: none — commands, paths, and pass/fail numbers are explicit.
- Type consistency: locked slot names flow Task 1 → 3/4/5 and 7/8/9; bump happens only in Task 10 (or Task 1 if occupied).
