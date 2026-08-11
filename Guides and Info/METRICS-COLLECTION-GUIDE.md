# Metrics Collection Guide

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** This guide explains what data is collected during each experiment run, where it lives, how to pull it to your PC, and how to verify it's usable before moving on to the next run. Read this alongside [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) and [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md).

---

## 1. What gets collected and by what tool

Every run produces output from three sources. The first two are always present; the third only when RetryGuard is on.

| Source | Written by | Format | Always collected? |
|--------|-----------|--------|------------------|
| **API performance** | `metric_collector.py` | One CSV per Locust endpoint, one row per second | Yes |
| **Run manifest** | `run_scenario.py` at collection time | `run_manifest.json` | Yes |
| **RetryGuard decisions** | `retryguard.py` | `retryguard.log` text file | RetryGuard runs only |

> **Known gap:** `resource_collector.py` (CPU/memory per pod via cAdvisor) is used in-memory by the RL loop but does **not** write per-run CSV files to the results folder. CPU/memory charts are not available from the current pipeline. If those metrics are needed for Phase 7, the collector needs to be wired up first — see EXPERIMENT-READINESS-WORKPLAN.md Step 8.

---

## 2. Folder structure per run

The runner (`run_scenario.py`) creates one folder per run on the master VM under `results_base_path`:

```
/home/idozacharia/experiments/results/
  <log_folder>/
    getproduct.csv
    postcheckout.csv
    getcart.csv
    postcart.csv
    emptycart.csv
    retryguard.log          ← RetryGuard runs only
    run_manifest.json
```

`log_folder` comes directly from the YAML config (e.g. `baseline_topfull_no_retryguard_sustained_overload_run1`). Each run has a unique folder name because the run number is embedded in it — runs never overwrite each other.

### All results for a scenario (multiple runs + both conditions) look like:

```
/home/idozacharia/experiments/results/
  baseline_topfull_no_retryguard_sustained_overload_run1/
  baseline_topfull_no_retryguard_sustained_overload_run2/
  baseline_topfull_no_retryguard_sustained_overload_run3/
  run_topfull_retryguard_sustained_overload_run1/
  run_topfull_retryguard_sustained_overload_run2/
  run_topfull_retryguard_sustained_overload_run3/
```

---

## 3. The API performance CSVs

### Files

One file per Locust endpoint — five files per run:

| File | Locust endpoint | What it measures |
|------|----------------|-----------------|
| `getproduct.csv` | Browse product page | `productcatalogservice` load path |
| `postcheckout.csv` | Submit checkout | `checkoutservice` load path (critical for S3) |
| `getcart.csv` | View cart | `cartservice` read path |
| `postcart.csv` | Add to cart | `cartservice` write path |
| `emptycart.csv` | Empty cart | `cartservice` session teardown |

### Columns

```
RPS, Fail, Goodput, Latency95, Latency99
```

| Column | Meaning |
|--------|---------|
| `RPS` | Requests per second sent to this endpoint (offered load) |
| `Fail` | Failed requests per second (5xx / timeout) |
| `Goodput` | `RPS - Fail` — successful requests per second (the primary health metric) |
| `Latency95` | 95th-percentile response latency in milliseconds |
| `Latency99` | 99th-percentile response latency in milliseconds |

### Timing

- **One row = one second.** A 10-minute run produces ~600 rows per file.
- Rows are written from when `metric_collector.py` starts. The first few rows may show `RPS=0` while Locust is still spawning — this is normal.
- There is no absolute timestamp column. The row index is seconds elapsed since the collector started (approximately aligned with run start).

### What healthy data looks like (Scenario 1 — Normal Op)

```
RPS,Fail,Goodput,Latency95,Latency99
13.2,0,13.2,42,58
13.5,0,13.5,40,55
...
```

`Fail=0` throughout, `Goodput≈RPS`. During the smoke run, S1 baseline had 273 rows with `Fail=0` and total goodput ≈390.

### What overloaded data looks like (Scenario 2/3 baseline)

```
RPS,Fail,Goodput,Latency95,Latency99
20.1,19.6,0.5,4200,8100
20.3,20.3,0.0,9999,9999
...
```

`Fail` approaches `RPS`, `Goodput` near zero, latency spikes.

---

## 4. The RetryGuard log

**File:** `retryguard.log` (present only in RetryGuard-condition runs)

**Also visible live** during a run:
```bash
ssh topfull-master "tmux attach -t retryguard"   # Ctrl+B, D to detach
```

### Log line types

| Keyword | Meaning |
|---------|---------|
| `START` | Controller initialized — shows all params |
| `OBSERVE` | End of each 30s window — reports rejection rate + counters for every service |
| `ON→OFF` | RetryGuard disabled retries on a service (VirtualService patched) |
| `OFF→ON` | RetryGuard re-enabled retries on a service |
| `SKIP` | No CSV data available for a service this window |
| `PATCH_FAIL` | Kubernetes API patch failed (logged, state not updated) |
| `SHUTDOWN` / `EXIT` | Controller received stop signal |

### Example log

```
2026-08-04T13:20:00Z  START  threshold=0.20 window=30s disable_windows=2 re_enable_windows=3 services=['cartservice', 'checkoutservice', 'productcatalogservice']
2026-08-04T13:20:30Z  OBSERVE  cartservice         rejection=0.0100  low=1 high=0  state=ON
2026-08-04T13:20:30Z  OBSERVE  checkoutservice     rejection=0.3800  low=0 high=1  state=ON
2026-08-04T13:20:30Z  OBSERVE  productcatalogservice  rejection=0.0200  low=1 high=0  state=ON
2026-08-04T13:21:00Z  OBSERVE  checkoutservice     rejection=0.4100  low=0 high=2  state=ON
2026-08-04T13:21:00Z  checkoutservice  ON→OFF   rejection=0.41  consecutive_high=2  attempts=0
2026-08-04T13:24:00Z  OBSERVE  checkoutservice     rejection=0.0500  low=3 high=0  state=OFF
2026-08-04T13:24:00Z  checkoutservice  OFF→ON   rejection=0.05  consecutive_low=3  attempts=3
```

### Reading an ON→OFF event

`checkoutservice  ON→OFF   rejection=0.41  consecutive_high=2  attempts=0`

- `checkoutservice` rejection rate stayed above 20% for 2 consecutive windows (≥60s)
- RetryGuard patched the VirtualService to remove the `retries` block
- From this timestamp, Istio no longer retries failed `checkoutservice` calls

Cross-reference this timestamp with `postcheckout.csv` — you should see `Fail` drop and/or `Goodput` recover shortly after.

---

## 5. The run manifest

**File:** `run_manifest.json` — written by `run_scenario.py` at the end of collection.

```json
{
  "scenario_id": 2,
  "scenario_name": "sustained_overload",
  "condition": "baseline",
  "run_number": 1,
  "duration_seconds": 600,
  "retryguard": { "enabled": false, ... },
  "scale_constraints": [],
  "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run1",
  "collected_at": "2026-08-11T10:00:00Z"
}
```

This makes each folder self-describing — you don't need to look up the YAML to know what produced it.

---

## 6. How to pull results to your PC

After each run completes (the runner prints the `scp` command for you):

```powershell
# Pull one run folder
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/

# Pull all results at once (after multiple runs)
scp -r topfull-master:/home/idozacharia/experiments/results/ experiments/results/
```

Local layout after pulling:

```
experiments/results/
  baseline_topfull_no_retryguard_sustained_overload_run1/
    getproduct.csv
    postcheckout.csv
    ...
    run_manifest.json
  baseline_topfull_no_retryguard_sustained_overload_run2/
    ...
```

---

## 7. Verifying a run after collection

Before moving on to the next run or repeating, do a quick sanity check:

```powershell
# On your PC — check row counts (should be ~duration_seconds rows)
(Get-Content experiments\results\<log_folder>\postcheckout.csv | Measure-Object -Line).Lines

# Or on master before pulling
ssh topfull-master "wc -l /home/idozacharia/experiments/results/<log_folder>/*.csv"
```

| Check | Expected | If wrong |
|-------|----------|----------|
| Row count ≈ `duration_seconds` | ~300 for S1, ~600 for S2–5 | Locust didn't start, or metric_collector died early |
| `RPS > 0` in most rows | Consistently positive after first ~10 rows | Locust spawn took too long, or connectivity issue |
| `Fail` near zero for S1 | `0` every row | Something wrong with the cluster — investigate before running S2+ |
| `Fail` elevated for S2/3 baseline | High throughout overload period | Expected and correct |
| `retryguard.log` exists (RetryGuard runs) | File present, `START` line at top | RetryGuard didn't start — check `tmux` session |
| `run_manifest.json` exists | Always | Runner aborted before collection step |

---

## 8. Collecting across runs for analysis (Phase 7 preview)

Each run folder is independent. For Phase 7, you'll load all runs for a given scenario+condition together.

**Pattern (Python):**

```python
import pandas as pd
from pathlib import Path

results = Path("experiments/results")

# Load all baseline runs for Scenario 2, postcheckout endpoint
runs = sorted(results.glob("baseline_topfull_no_retryguard_sustained_overload_run*/postcheckout.csv"))
dfs = [pd.read_csv(r) for r in runs]

# Per-run aggregate: mean goodput over the run
mean_goodputs = [df["Goodput"].mean() for df in dfs]

# Time-series average across runs (truncate to shortest run first)
min_len = min(len(df) for df in dfs)
avg_series = pd.concat([df["Goodput"].iloc[:min_len] for df in dfs], axis=1).mean(axis=1)
```

**Cross-referencing RetryGuard decisions with metrics:**

1. Find an `ON→OFF` timestamp in `retryguard.log` (e.g. `13:21:00Z`)
2. Estimate the row index: seconds since run start (check `run_manifest.json` `collected_at` and subtract)
3. Look at `postcheckout.csv` rows around that index — expect `Fail` to decrease and `Goodput` to rise within 1–2 rows (the controller acts at 30s granularity; the CSV records at 1s granularity)

---

## 9. Quick reference — per-scenario focus metrics

| Scenario | Primary files | What to look for |
|----------|--------------|-----------------|
| 1 — Normal Op | all 5 CSVs | `Fail=0` everywhere; `retryguard.log` shows zero `ON→OFF` lines |
| 2 — Sustained Overload | `postcheckout.csv`, `getproduct.csv` | Baseline: `Fail` high throughout. RetryGuard: `Fail` dips after toggle events |
| 3 — Targeted Bottleneck | `postcheckout.csv` (primary), all others (propagation) | Baseline: `postcheckout` rejection spikes. RetryGuard: toggle events in log align with goodput recovery |
| 4A — Topology: ProductCatalog | `getproduct.csv` | Same structure as S3 but at `getproduct` |
| 4B — Topology: Payment | `postcheckout.csv` | Payment is reached via checkout path — rejection appears in `postcheckout` |
| 5 — Interval Tuning | `postcheckout.csv` + `retryguard.log` | Count toggle events per run; compare time-to-recovery across interval configs |

---

*Related guides: [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) (how to run), [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (log format detail), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) §4 (data collection mechanics).*
