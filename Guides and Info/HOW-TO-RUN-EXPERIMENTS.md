# How to Run an Experiment and Read the Results

TAU Deepness Lab Workshop — TopFull + RetryGuard

> **Who this is for:** Anyone on the team running a scenario manually, without an AI agent.
> Read this once before your first run. The whole flow takes about 15 minutes for a 5-minute scenario, 25 minutes for a 10-minute one.
>
> **Phase 7 close-out (2026-09-04):** do not replay the August 38 and do not mix old goodput with a one-off collector run. The plan of record is a **paper-grade 48-run campaign** (new `log_folder` slots, all collectors on, ×3 including S5). Slots, order, and the `OFF→ON` gate: [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md). Never `run_all_scenarios.py` for that campaign.

---

## 0. Before you start: prerequisites (one-time)

### 0a. Python package
```powershell
# From the repo root (uses the local venv created by the agent)
experiments\.venv\Scripts\pip install pyyaml
# Or if you prefer a global install:
pip install pyyaml
```

### 0b. SSH aliases
Confirm all three VMs are reachable:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
```
Both should return immediately without a password prompt.
If not, follow [CONNECT-VMS.md](CONNECT-VMS.md) to fix `~/.ssh/config` (IPs are ephemeral — refresh after every VM restart).

### 0c. Check that the VMs are actually running
```powershell
gcloud compute instances list --project=networks-workshop `
  --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```
All three should show `RUNNING`. If `TERMINATED`, start them:
```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load `
  --zone=us-central1-a
```
Then refresh SSH hostnames in `~/.ssh/config` because IPs will have changed.

---

## 1. Pick the config file

All 16 config files live in `experiments/configs/`. Each one is a single scenario × condition combination:

| File | What it does | Duration |
|---|---|---|
| `scenario_1_baseline.yaml` | Normal load, no RetryGuard | 5 min |
| `scenario_1_retryguard.yaml` | Normal load + RetryGuard | 5 min |
| `scenario_2_baseline.yaml` | Flat sustained overload, no RetryGuard | 10 min |
| `scenario_2_retryguard.yaml` | Flat sustained overload + RetryGuard | 10 min |
| `scenario_3_baseline.yaml` | Checkout CPU-capped, no RetryGuard | 10 min |
| `scenario_3_retryguard.yaml` | Checkout CPU-capped + RetryGuard | 10 min |
| `scenario_4a_baseline.yaml` | ProductCatalog CPU-capped, no RetryGuard | 10 min |
| `scenario_4a_retryguard.yaml` | ProductCatalog CPU-capped + RetryGuard | 10 min |
| `scenario_4b_baseline.yaml` | Payment CPU-capped, no RetryGuard | 10 min |
| `scenario_4b_retryguard.yaml` | Payment CPU-capped + RetryGuard | 10 min |
| `scenario_5_interval_10s.yaml` | S6 load + RetryGuard, re-enable=30s | 15 min |
| `scenario_5_interval_20s.yaml` | S6 load + RetryGuard, re-enable=60s | 15 min |
| `scenario_5_interval_30s.yaml` | S6 load + RetryGuard, re-enable=90s | 15 min |
| `scenario_5_interval_60s.yaml` | S6 load + RetryGuard, re-enable=180s | 15 min |
| `scenario_6_recovery_baseline.yaml` | Peak then load-drop, no RetryGuard | 15 min |
| `scenario_6_recovery_retryguard.yaml` | Peak then load-drop + RetryGuard (paper default interval) | 15 min |

**Start with Scenario 1 baseline** if you're not sure — it's only 5 minutes and the safest first run.

---

## 2. Bump the run number (every repeat)

The config stores a `run_number` and a `log_folder`. These must be unique for every run or you'll **overwrite previous results**.

Open the config file, find these two lines, and increment:
```yaml
run_number: 2          # was 1 → change to next free number
log_folder: baseline_topfull_no_retryguard_normal_op_run2   # match the number
```

The naming convention is:
- Baseline: `baseline_topfull_no_retryguard_<scenario>_run<N>`
- RetryGuard: `run_topfull_retryguard_<scenario>_run<N>`

> **Where are we now?** Smoke runs used run1 for S1-baseline/retryguard and S3-baseline/retryguard. Those configs are already bumped to the next number. All other configs are still at run1.

---

## 3. Run the scenario

From the **repo root** on your Windows machine:

```powershell
# Use the local venv (recommended — pyyaml is already installed):
$env:PYTHONUTF8 = '1'
experiments\.venv\Scripts\python experiments\run_scenario.py `
    experiments\configs\scenario_1_baseline.yaml
```

Or if you have pyyaml globally:
```powershell
$env:PYTHONUTF8 = '1'
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
```

`$env:PYTHONUTF8 = '1'` tells Python to use UTF-8 for console output (needed for the progress bar on Windows).

### What you'll see

The runner prints each stage as it goes:

```
════════════════════════════════════════════════════════════
  Scenario : 1 — normal_operation
  Condition: baseline
  Run #    : 3
  Duration : 300s  (5m 0s)
  RetryGuard: OFF
════════════════════════════════════════════════════════════

  Pre-flight checks
  ...
  [16:10:57] Nodes: 2 Ready ✓
  [16:11:04] All pods Running ✓
  [16:11:07] Loadgen reachable ✓

  Starting master stack
  ...
  [16:12:02] deploy_rl.py running ✓

  Starting Locust load
  ...
  [16:12:31] Locust running: 46 processes ✓

  Experiment running — 300s
  [██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   ...

  Collecting results
  [16:17:43] Results saved to: /home/idozacharia/experiments/results/...
```

The run is done when you see the final `Done` block with start/end times.

**If something fails early** (e.g. deploy_rl didn't start), it will print a clear `[ERROR]` message and then still run the stop + collect steps so you get partial data. The error message tells you which tmux session to check for details.

### Abort at any time with Ctrl+C
The runner catches the interrupt, stops Locust and all master processes cleanly, and still copies whatever partial logs exist to the results folder.

---

## 4. Watch the run live (optional)

While the runner is going, you can SSH into master in a separate terminal and tail the live logs.

**Check the RetryGuard controller (RetryGuard runs only):**
```bash
ssh topfull-master "tmux attach -t retryguard"
# Press Ctrl+B, D to detach without killing it
```

You'll see lines like:
```
2026-08-07T13:49:30Z  OBSERVE  checkoutservice  rejection=0.9970  low=0 high=1  state=ON
2026-08-07T13:50:00Z  checkoutservice  ON→OFF   rejection=0.99  consecutive_high=2  attempts=0
```

**Check the metric collector CSV in real time:**
```bash
ssh topfull-master "tail -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/postcheckout.csv"
```

**Check the RL controller:**
```bash
ssh topfull-master "tmux attach -t toprl"
# Ctrl+B, D to detach
```

**Verify the VirtualService was actually patched (during a RetryGuard run):**
```bash
ssh topfull-master "kubectl get virtualservice checkoutservice -o jsonpath='{.spec.http[0].retries}'"
# Retries ON:  {"attempts":3,"retryOn":"5xx,reset,connect-failure"}
# Retries OFF: {}  (or missing — field is omitted when disabled)
```

---

## 5. Pull results to your PC

After the run completes, copy the results folder from master:

```powershell
# Replace the folder name with the actual log_folder from your config:
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run3 `
    experiments\results\
```

This creates `experiments/results/<log_folder>/` on your PC.

---

## 6. What's in the results folder

```
<log_folder>/
  getproduct.csv        ← GET /product/* endpoint
  postcheckout.csv      ← POST /checkout endpoint  (watch this for S3)
  getcart.csv           ← GET /cart endpoint
  postcart.csv          ← POST /cart (add to cart)
  emptycart.csv         ← DELETE /cart (empty cart)
  total.csv             ← sum across all endpoints
  num_agent.csv         ← TopFull RL agent output (throttling counts per service)
  retryguard.log        ← (RetryGuard runs only) controller event log
  run_manifest.json     ← snapshot of the config + timestamps
```

### CSV columns

Every `*.csv` file has the same five columns, one row per second:

| Column | What it means |
|---|---|
| `RPS` | Requests per second arriving at the endpoint |
| `Fail` | Failed requests per second (5xx or timeout) |
| `Goodput` | Successful requests per second (`RPS - Fail`) |
| `Latency95` | 95th-percentile latency in milliseconds — the latency metric of record (P99 dropped, see [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 2) |
| `Latency99` | Always `0` — hardcoded in TopFull's `metric_collector.py`. Do not use. |

**The key comparison metric is `Goodput`** — how much useful work the system was able to complete. Under overload, `Fail` rises and `Goodput` drops.

**Rejection rate** (not a column, but what the paper measures) is `Fail / RPS`. You can compute it per row.

### retryguard.log columns

Each line has a fixed-width timestamp, an event type, and fields:

| Event | What happened |
|---|---|
| `START` | Controller started; params listed |
| `OBSERVE` | End of one 30s window; current rejection and counter state |
| `<svc>  ON→OFF` | Retries disabled on that service's VirtualService |
| `<svc>  OFF→ON` | Retries re-enabled on that service's VirtualService |
| `PATCH_FAIL` | VS patch rejected (see reason); internal state NOT updated |
| `EXIT` | Controller shut down cleanly |

Example:
```
2026-08-07T13:49:30Z  OBSERVE  checkoutservice  rejection=0.9970  low=0 high=1  state=ON
2026-08-07T13:50:00Z  checkoutservice  ON→OFF   rejection=0.99  consecutive_high=2  attempts=0
```
→ After 2 windows above 20% rejection, retries were disabled on `checkoutservice`.

---

## 7. Read the numbers

### Quick sanity checks (do these first)

```powershell
# Open PowerShell, go to repo root, use the venv python:
experiments\.venv\Scripts\python -c @"
import csv, pathlib, json
base = pathlib.Path('experiments/results/baseline_topfull_no_retryguard_normal_op_run3')
print(json.loads((base/'run_manifest.json').read_text())['log_folder'])
for name in ['total.csv','postcheckout.csv','getproduct.csv']:
    rows = list(csv.DictReader((base/name).open()))
    rps  = [float(r['RPS']) for r in rows]
    fail = [float(r['Fail']) for r in rows]
    good = [float(r['Goodput']) for r in rows]
    rej  = [f/r if r>0 else 0 for r,f in zip(rps,fail)]
    print(f'{name}: rows={len(rows)} goodput_mean={sum(good)/len(good):.1f} '
          f'fail_mean={sum(fail)/len(fail):.2f} rejection_mean={sum(rej)/len(rej)*100:.1f}%')
"@
```

Replace the folder name to match your run.

What you expect to see:
- **Scenario 1 (normal op):** `Fail` near 0, rejection near 0%
- **Scenario 2/3/4 baseline (overload):** elevated `Fail`, rejection 20–100% at the bottleneck
- **Scenario 1 RetryGuard:** numbers nearly identical to baseline (RetryGuard must be a no-op)

### Check for RetryGuard toggles
```powershell
# Print only the interesting lines from retryguard.log:
Get-Content experiments\results\run_topfull_retryguard_targeted_bottleneck_run2\retryguard.log |
  Where-Object { $_ -match 'ON→OFF|OFF→ON|PATCH_FAIL|START|EXIT' }
```

You want to see at least one `ON→OFF` for a genuinely overloaded service.

### Cross-reference a toggle with CSV data

Suppose `retryguard.log` shows `checkoutservice ON→OFF` at `13:50:00Z`. The metric_collector starts recording when the run begins (after `deploy_rl` and Locust are up, typically ~50–60 seconds into the runner's clock). The CSV rows are 1-second samples from that point forward with no embedded timestamps, but you can estimate the index:

```
toggle_time_unix - metric_collector_start_unix = approximate CSV row index
```

A quick way to find the right region: scan `postcheckout.csv` for where `Goodput` drops to 0 (that's the overload onset) and where `Fail` drops (that's the toggle effect).

```powershell
experiments\.venv\Scripts\python -c @"
import csv, pathlib
rows = list(csv.DictReader(
    pathlib.Path('experiments/results/run_topfull_retryguard_targeted_bottleneck_run2/postcheckout.csv').open()
))
for i, r in enumerate(rows):
    rps = float(r['RPS']); fail = float(r['Fail']); good = float(r['Goodput'])
    rej = fail/rps*100 if rps>0 else 0
    if i % 30 == 0 or rej > 80 or rej < 20:  # sample key rows
        print(f'{i:4d}  rps={rps:5.1f} fail={fail:5.1f} goodput={good:5.1f} rej={rej:5.1f}%')
"@
```

---

## 8. Comparing baseline vs RetryGuard

After you have at least one run of each condition for a scenario, compare mean `Goodput` and mean rejection rate:

```powershell
experiments\.venv\Scripts\python -c @"
import csv, pathlib

def stats(path, endpoint='postcheckout.csv'):
    rows = list(csv.DictReader((path/endpoint).open()))
    # Skip first 10 rows (ramp-up)
    rows = rows[10:]
    rps  = [float(r['RPS']) for r in rows]
    fail = [float(r['Fail']) for r in rows]
    good = [float(r['Goodput']) for r in rows]
    rej  = [f/r if r>0 else 0 for r,f in zip(rps, fail)]
    return dict(goodput=sum(good)/len(good), rej=sum(rej)/len(rej)*100, n=len(rows))

b = stats(pathlib.Path('experiments/results/baseline_topfull_no_retryguard_targeted_bottleneck_run2'))
r = stats(pathlib.Path('experiments/results/run_topfull_retryguard_targeted_bottleneck_run2'))
print(f'Baseline : goodput={b[\"goodput\"]:.2f}  rejection={b[\"rej\"]:.1f}%')
print(f'RetryGuard: goodput={r[\"goodput\"]:.2f}  rejection={r[\"rej\"]:.1f}%')
print(f'Delta    : goodput {(r[\"goodput\"]-b[\"goodput\"])/b[\"goodput\"]*100:+.1f}%  rejection {r[\"rej\"]-b[\"rej\"]:+.1f}pp')
"@
```

---

## 9. After you're done with a scenario

1. **Before the next repeat:** open the config, bump `run_number` and `log_folder` suffix. Don't forget.
2. **Before a different scenario:** no extra cleanup needed — the runner restores CPU limits and VirtualService retries automatically.
3. **To verify the cluster is clean** after any RetryGuard run:
   ```bash
   ssh topfull-master "kubectl get virtualservice checkoutservice -o jsonpath='{.spec.http[0].retries}'; echo"
   # Expected: {"attempts":3,"retryOn":"5xx,reset,connect-failure"}
   ssh topfull-master "kubectl get deployment checkoutservice -o jsonpath='{.spec.template.spec.containers[0].resources}'; echo"
   # Expected: original limits (cpu:1, memory:128Mi) and requests (cpu:500m, memory:64Mi)
   ```
4. **Stop the VMs when done for the day** (saves GCP credit):
   ```powershell
   gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
   ```

---

## 10. Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `SSH connection refused / timed out` | VM is TERMINATED or IP changed | Check `gcloud compute instances list`; start VM; update `HostName` in `~/.ssh/config` |
| `deploy_rl.py did not start` | Ray startup failed or port collision | `ssh topfull-master "tmux attach -t toprl"` — read the Python traceback; usually gone after a clean kill + retry |
| `UnicodeEncodeError: charmap` | Windows console encoding | Add `$env:PYTHONUTF8='1'` before running |
| `cpu_limit patch failed` | Already logged; runner now handles this correctly | If it still fails, check `kubectl describe deployment <svc>` for resource constraints |
| `PATCH_FAIL http=400 reason=Bad Request` | RetryGuard bug or VS in unexpected state | The runner deploys `experiments/retryguard.py` from this repo at the start of every RetryGuard run. If a run was started outside the runner, copy it once: `scp experiments/retryguard.py topfull-master:/tmp/rg.py && ssh topfull-master "sudo cp /tmp/rg.py /home/idozacharia/experiments/retryguard.py"` |
| RetryGuard never fires `ON→OFF` | Load too light, or threshold too high | Run Scenario 3 (deterministic CPU cap) — overload is guaranteed. Scenario 2 requires the right load level. |
| CSV files are empty | Locust didn't start, or metric_collector died | Check `ssh topfull-master "tmux attach -t metrics"` for errors; check `pgrep -c locust` on loadgen |
| Run took much longer than expected | Normal — `actual` includes startup overhead | Startup adds ~80–90s on top of `duration_seconds`; plan accordingly |

---

## 11. What next run numbers to use

§11 used to list **smoke** next-slots (stale). For anything that will go in the report, use the **paper-grade campaign** slots in [PHASE7-RESOLVE-GAPS-1-3.md](PHASE7-RESOLVE-GAPS-1-3.md) §3a:

| Config group | Do **not** use (August matrix) | Campaign slots |
|---|---|---|
| S1 baseline / RetryGuard | run1–3 | **run4–6** (bump YAML from run3 first) |
| S2 / S3 / S4A / S4B | run1–3 | **run4–6** |
| S5 intervals | run1–2 (flat hold, no re-enable) | **run3–5** |
| S6 recovery | — (never run) | **run1–3** |

Bump `run_number` and `log_folder` after **every** run. A 48-run checklist and the S6 `OFF→ON` gate are in that same runbook.
