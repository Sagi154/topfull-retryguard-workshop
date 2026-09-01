# Metrics Collection Guide

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** This guide explains what data is collected during each experiment run, where it lives, how to pull it to your PC, and how to verify it's usable before moving on to the next run. Read this alongside [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) and [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md).

---

## 1. What gets collected and by what tool

Every run produces output from up to five sources. API performance and the run manifest are always present; RetryGuard decisions only when RetryGuard is on; Envoy retry counters and CPU/memory when their collectors are enabled (default in all 14 scenario configs).

| Source | Written by | Format | Always collected? |
|--------|-----------|--------|------------------|
| **API performance** | `metric_collector.py` | One CSV per Locust endpoint, one row per second | Yes |
| **Run manifest** | `run_scenario.py` at collection time | `run_manifest.json` | Yes |
| **RetryGuard decisions** | `retryguard.py` | `retryguard.log` text file | RetryGuard runs only |
| **Envoy retry counters** | `envoy_retry_collector.py` | `envoy_retries_{caller}.csv` + `envoy_retry_collector.log` | When collector enabled (default) |
| **CPU/memory per service** | `resource_usage_collector.py` | `resource_usage.csv` + `resource_usage_collector.log` | When collector enabled (default) |

> **Layer 2 note:** `resource_usage_collector.py` (kubelet `stats/summary` via `kubectl get --raw`) closes the *instrumentation* half of the CPU/memory gap. TopFull's in-memory `resource_collector.py` still feeds the RL loop only — it is not patched. The existing 38 matrix folders predate this collector; new runs will produce `resource_usage.csv`. Pod replica counts in the CSV will be `1` for every service (fixed-replica experimental design). See [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md).
>
> **Gap 3 note:** The Envoy retry collector closes the *instrumentation* half of the "retries per request" gap. The existing 38 matrix folders were collected *before* this collector existed, so they still have no retry-count series. New runs (including the Gap 1 recovery-phase re-runs) will produce the CSVs. See [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 3.

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
    envoy_retries_frontend.csv          ← when envoy_retry_collector enabled
    envoy_retries_checkoutservice.csv   ← when envoy_retry_collector enabled
    envoy_retry_collector.log           ← when envoy_retry_collector enabled
    resource_usage.csv                  ← when resource_usage_collector enabled
    resource_usage_collector.log        ← when resource_usage_collector enabled
    retryguard.log                      ← RetryGuard runs only
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
| `Latency95` | 95th-percentile response latency in milliseconds — **the latency metric of record** (see [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 2) |
| `Latency99` | Always `0` — hardcoded in TopFull's `metric_collector.py`, never actually computed. **Do not use.** P99 was dropped as a target metric on 2026-08-20: neither RetryGuard's paper (average-latency-based), TopFull's paper (goodput-based), nor the eval deck (generic "API latency") requires it. Column left as-is because it's written by TopFull's unmodified collector. |

### Timing

- **One row = one second.** A 10-minute run produces ~600 rows per file.
- Rows are written from when `metric_collector.py` starts. The first few rows may show `RPS=0` while Locust is still spawning — this is normal.
- There is no absolute timestamp column. The row index is seconds elapsed since the collector started (approximately aligned with run start).

### What healthy data looks like (Scenario 1 — Normal Op)

```
RPS,Fail,Goodput,Latency95,Latency99
13.2,0,13.2,42,0
13.5,0,13.5,40,0
...
```

`Fail=0` throughout, `Goodput≈RPS`. During the smoke run, S1 baseline had 273 rows with `Fail=0` and total goodput ≈390.

### What overloaded data looks like (Scenario 2/3 baseline)

```
RPS,Fail,Goodput,Latency95,Latency99
20.1,19.6,0.5,4200,0
20.3,20.3,0.0,9999,0
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

## 5. The Envoy retry CSVs (retries per request)

**Files** (when `envoy_retry_collector.enabled: true`):

| File | Caller sidecar scraped | Target services in rows |
|------|------------------------|-------------------------|
| `envoy_retries_frontend.csv` | `frontend` | `cartservice`, `productcatalogservice`, `checkoutservice` |
| `envoy_retries_checkoutservice.csv` | `checkoutservice` | `cartservice`, `productcatalogservice`, `paymentservice` |
| `envoy_retry_collector.log` | — | `START` / `WARNING` / `SHUTDOWN` / `EXIT` lines |

**Why scrape callers, not callees.** Envoy records retry counters on the *caller's outbound* cluster stats (`cluster.outbound|…|<svc>.….upstream_rq_retry`), not on the callee's inbound stats. Scraping `frontend` and `checkoutservice` covers the four services we care about (the three RetryGuard toggles plus `paymentservice` for S4B).

> **Prerequisite (handled automatically):** Istio's default stats reduction hides `upstream_rq_retry*` from the plain `/stats` dump unless the pod carries a `sidecar.istio.io/statsInclusionRegexps` annotation. `run_scenario.py`'s `start_envoy_retry_collector()` patches `frontend`/`checkoutservice` with this annotation before every run (idempotent — a no-op after the first time). See [PHASE7-DATA-GAPS.md](PHASE7-DATA-GAPS.md) Gap 3 for the full story; confirmed live on 2026-08-20.

### Columns

```
timestamp, target_service, upstream_rq_total, upstream_rq_retry, upstream_rq_retry_success, upstream_rq_retry_limit_exceeded
```

Counters are **cumulative** for the pod's lifetime (Envoy never resets them mid-run). One row is written per target service per poll (default every 5s).

### Deriving retries-per-request at analysis time

```python
# consecutive rows for the same target_service in one caller CSV
d_retry = row_n["upstream_rq_retry"] - row_n1["upstream_rq_retry"]
d_total = row_n["upstream_rq_total"] - row_n1["upstream_rq_total"]
retries_per_request = (d_retry / d_total) if d_total > 0 else 0.0
```

Join against `retryguard.log` toggle timestamps to show that `ON→OFF` reduces the retry rate on that service.

> The existing 38 matrix folders do **not** contain these files — they predate the collector. Only runs started after this collector was enabled will have them.

---

## 6. The resource usage CSV (CPU/memory per service)

**Files** (when `resource_usage_collector.enabled: true`):

| File | Source | Content |
|------|--------|---------|
| `resource_usage.csv` | kubelet `stats/summary` via `kubectl get --raw` | Per-service CPU and memory, one row per service per poll |
| `resource_usage_collector.log` | — | `START` / `WARNING` / `SHUTDOWN` / `EXIT` lines |

Scrapes the worker node's kubelet summary API. App-container usage only (`istio-proxy` and `POD` pause containers are skipped). Services with no matching pod in a given poll are omitted (not zero-filled).

### Columns

```
timestamp, service, cpu_millicores, memory_working_set_bytes, replica_count
```

| Column | Meaning |
|--------|---------|
| `timestamp` | UTC ISO time of the poll |
| `service` | Deployment name (`checkoutservice`, `paymentservice`, …) |
| `cpu_millicores` | Sum of app-container `usageNanoCores` across replicas, in millicores |
| `memory_working_set_bytes` | Sum of app-container working-set memory across replicas |
| `replica_count` | `readyReplicas` from the Deployment status (always `1` in this workshop's fixed-replica setup) |

Default poll interval: **5s** (same as Envoy collector). A 600s run produces ~120 rows per service.

Join against `retryguard.log` toggle timestamps to show CPU/memory dropping after `ON→OFF` on a service.

> The existing 38 matrix folders do **not** contain this file — they predate the collector.

---

## 7. The run manifest

**File:** `run_manifest.json` — written by `run_scenario.py` at the end of collection.

```json
{
  "scenario_id": 2,
  "scenario_name": "sustained_overload",
  "condition": "baseline",
  "run_number": 1,
  "duration_seconds": 600,
  "retryguard": { "enabled": false, ... },
  "envoy_retry_collector": { "enabled": true, "poll_interval_seconds": 5 },
  "resource_usage_collector": { "enabled": true, "poll_interval_seconds": 5 },
  "scale_constraints": [],
  "log_folder": "baseline_topfull_no_retryguard_sustained_overload_run1",
  "collected_at": "2026-08-11T10:00:00Z"
}
```

This makes each folder self-describing — you don't need to look up the YAML to know what produced it.

---

## 8. How to pull results to your PC

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

## 9. Verifying a run after collection

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
| `resource_usage.csv` has rows (when enabled) | `memory_working_set_bytes > 0` for `frontend` under any load | kubelet `stats/summary` blocked — check collector log on master |

---

## 10. Collecting across runs for analysis (Phase 7 preview)

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

## 11. Quick reference — per-scenario focus metrics

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
