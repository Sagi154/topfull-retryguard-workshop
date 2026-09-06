# `campaign_48/` — Phase 7 Paper-Grade Campaign

> **What this is:** the primary Phase 7 dataset — 48 experiment runs collected 2026-09-05 → 2026-09-06, covering all 6 scenarios × both conditions (baseline / RetryGuard) × 3 repeats, with every collector (Locust, Envoy retries, CPU/memory, RetryGuard log) enabled. Read [PHASE7-DATA-GAPS.md](../../../Guides%20and%20Info/PHASE7-DATA-GAPS.md) and [PHASE7-RESOLVE-GAPS-1-3.md](../../../Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md) for how/why this campaign came to be. This doc is a **map of the folder**, not the analysis itself.
>
> For full file-format detail (columns, log line types, verification checks), see [METRICS-COLLECTION-GUIDE.md](../../../Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) — this doc summarizes it in the context of this specific campaign.

---

## 1. Top-level layout — one folder per scenario

`campaign_48/` is organized as **7 scenario folders**, each holding that scenario's baseline + RetryGuard run folders (S5 is RetryGuard-only). This nesting was added on 2026-09-06 (originally all 48 run folders sat flat under `campaign_48/`); if you see references to a flat layout in older guides, mentally add the scenario subfolder.

```
campaign_48/
  S1_normal_op/
  S2_sustained_overload/
  S3_targeted_bottleneck/
  S4A_topology_position_A/
  S4B_topology_position_B/
  S5_interval_tuning/
  S6_forced_recovery/
```

| Scenario folder | Scenario # | Meaning | Run folders inside |
|---|---|---|---|
| `S1_normal_op/` | S1 | Flat load, well within capacity | `baseline_topfull_no_retryguard_normal_op_run{4,5,6}`, `run_topfull_retryguard_normal_op_run{4,5,6}` |
| `S2_sustained_overload/` | S2 | Peak load from t=0, held flat | `baseline_topfull_no_retryguard_sustained_overload_run{4,5,6}`, `run_topfull_retryguard_sustained_overload_run{4,5,6}` |
| `S3_targeted_bottleneck/` | S3 | `checkoutservice` CPU-limited to `100m` | `baseline_topfull_no_retryguard_targeted_bottleneck_run{4,5,6}`, `run_topfull_retryguard_targeted_bottleneck_run{4,5,6}` |
| `S4A_topology_position_A/` | S4A | `productcatalogservice` CPU-limited | `baseline_topfull_no_retryguard_topology_position_A_run{4,5,6}`, `run_topfull_retryguard_topology_position_A_run{4,5,6}` |
| `S4B_topology_position_B/` | S4B | `paymentservice` CPU-limited | `baseline_topfull_no_retryguard_topology_position_B_run{4,5,6}`, `run_topfull_retryguard_topology_position_B_run{4,5,6}` |
| `S5_interval_tuning/` | S5 | RetryGuard-only; runs on **S6's load shape** (peak → drop), sweeping the re-enable check window (`re_enable_windows` × 30s). Compared against **S6 baseline**, not S2. | `run_topfull_retryguard_interval_{10,20,30,60}s_run{3,4,5}` — 12 folders, no baseline counterpart |
| `S6_forced_recovery/` | S6 | Peak 5 min, then ~25% load for 10 min (this is what "recovery" means — the load *drops*, giving RetryGuard a chance to re-enable retries) | `baseline_topfull_no_retryguard_forced_recovery_run{1,2,3}`, `run_topfull_retryguard_forced_recovery_run{1,2,3}` |

Within each scenario folder, the individual run-folder names still encode **condition_scenario_runNumber**:

- Prefix `baseline_topfull_no_retryguard_...` → **baseline condition** (TopFull only, Istio default retries `attempts:3`, RetryGuard off).
- Prefix `run_topfull_retryguard_...` → **RetryGuard condition** (TopFull + RetryGuard dynamically toggling retries).
- The trailing `run<N>` is the repeat number — these are the campaign's own slot numbers (not always starting at 1; S1–S4 use `run4–6` because `run1–3` were already used by the historical August 38 matrix, and S5 uses `run3–5` for the same reason). S6 is new to this campaign, so it starts at `run1`.

Counting: 5 scenarios (S1–S4B) × 2 conditions × 3 runs = 30, plus S6 × 2 conditions × 3 runs = 6, plus S5 × 4 intervals × 3 runs = 12. **30 + 6 + 12 = 48.**

> **S5 has no `baseline_...` folder.** It's a RetryGuard-only sensitivity sweep (does the paper's default 30s interval hold up?). To evaluate it you cross-reference each `S5_interval_tuning/interval_*` folder against `S6_forced_recovery/run_topfull_retryguard_forced_recovery_run*` (RG) and `S6_forced_recovery/baseline_topfull_no_retryguard_forced_recovery_run*` (baseline) — i.e. S6's runs are the reference points S5 is compared against.

---

## 2. Why three repeats, and how to plot them

Locust's simulated users pick paths at random, so two otherwise identical runs are not the same traffic. A single folder is too noisy to treat as "the" baseline or "the" RetryGuard result — that is why every arm has **three repeats** (eval deck: repeated trials to remove load-generation noise).

The quantity we care about is still the metric **as a function of time during the run** (when Fail climbs, when RetryGuard toggles, whether goodput recovers after the load drop). Do **not** collapse a run into one mean for the whole folder — that erases the scenario.

**How we combine the three repeats (decision):** align by second (Locust row index ≈ elapsed seconds; truncate to the shortest of the three) and average the three curves **pointwise**. That gives **one baseline line and one RetryGuard line**. Optionally draw a band around each line (min/max or std across the three repeats) so Locust spread is visible. Overlay `ON→OFF` / `OFF→ON` timestamps from `retryguard.log` on the same x-axis — those are events, not a third curve to average.

Same treatment for Envoy and resource series after you put them on a time axis (they poll every 5s; Envoy counters must be differenced first). S5: one averaged curve per interval (`10/20/30/60s`), each from that interval's three repeats, compared against S6's averaged baseline (and S6 RetryGuard) lines.

---

## 3. What each CSV actually measures

There are three kinds of file in every run folder. This section explains what the numbers mean, in plain terms, using real rows pulled from `S1_normal_op/run_topfull_retryguard_normal_op_run4/`.

### 3a. Locust CSVs — `getproduct.csv`, `postcheckout.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv`, `total.csv`

Each file tracks **one Locust endpoint** (one simulated user action); `total.csv` is the sum of all five. **One row = one second** of the run. Columns:

```
RPS,Fail,Goodput,Latency95,Latency99
50.0,0.0,50.0,270.0,0
```

| Column | What it is | How to read the number |
|---|---|---|
| `RPS` | Requests **sent** to this endpoint in that second (offered load) | `RPS = 50.0` → Locust fired ~50 requests/sec at this endpoint. This is *demand*, not success — it goes up because we told Locust to, not because the system is doing well. |
| `Fail` | Of those, how many **failed** (5xx / timeout) that second | `Fail = 0.0` → none failed. `Fail = 19.6` (out of `RPS = 20.1`, an overloaded example) → almost every request that second failed. |
| `Goodput` | `RPS − Fail` — requests that **succeeded** that second | This is the headline health number. `Goodput = 50.0` with `RPS = 50.0` means 100% of offered load succeeded (healthy). If `Goodput` drops far below `RPS` while `RPS` stays flat, the system is rejecting requests, not just responding slowly. |
| `Latency95` | 95th-percentile response time (ms) for requests **in that second** | `Latency95 = 270` means 95% of that second's requests came back in ≤270ms (and up to 5% took longer). Bigger = slower for the tail of users. Compare it to a "feels fine" number like 300–500ms for this stack, and note when it spikes into the thousands (queueing/overload) vs stays flat (healthy). |
| `Latency99` | Always `0` in every row — **do not use** (hardcoded/unused upstream; see [METRICS-COLLECTION-GUIDE.md](../../../Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) Gap 2) | — |

**Derived (not a column, but the metric you'll actually report):** rejection rate = `Fail / RPS` for rows where `RPS > 0`. A rejection rate near `0` is healthy; the RetryGuard/scenario threshold for "overloaded" is **~20%**.

Worked read of the row above: at that second, Locust sent 50 requests/sec to this endpoint, all 50 succeeded (`Goodput = RPS`), and the slowest 5% of those requests took over 270ms.

### 3b. Envoy retry CSVs — `envoy_retries_frontend.csv`, `envoy_retries_checkoutservice.csv`

Each row is a **snapshot poll** (every ~5s) of the calling service's sidecar, reporting outbound-retry counters **per target service it calls**. These counters are **cumulative since the pod started** — they only ever go up within a run, so a single row's raw value is not itself a rate.

```
timestamp,target_service,upstream_rq_total,upstream_rq_retry,upstream_rq_retry_success,upstream_rq_retry_limit_exceeded
2026-09-05T16:51:25Z,checkoutservice,110002,370,12,158
```

| Column | What it is | How to read the number |
|---|---|---|
| `timestamp` | UTC time of this poll | Use to align with the Locust CSVs' second-by-second rows and with `retryguard.log` toggle times. |
| `target_service` | Which downstream service these counters are about (e.g. `frontend`'s sidecar reports on `cartservice`, `productcatalogservice`, `checkoutservice`) | Tells you *whose* retries you're looking at, not the caller's. |
| `upstream_rq_total` | Total requests `frontend` has sent to `target_service` since pod start | `110002` at this poll — this keeps climbing as the run goes on; not itself interesting, it's the denominator for the rate below. |
| `upstream_rq_retry` | Total retry attempts issued to `target_service` since pod start | `370` retries issued so far. Also cumulative — a flat value across consecutive polls means **no new retries happened** in that interval (as in this example: `checkoutservice` stays at 370 across three straight 5s polls → zero retries during that window). |
| `upstream_rq_retry_success` | Of those retries, how many eventually succeeded | `12` — informational; rarely needed for the headline analysis. |
| `upstream_rq_retry_limit_exceeded` | Retries that hit Istio's `attempts:3` cap and still failed | `158` — informational. |

**Derived (this is the number you actually want — "retries per request"):** diff consecutive rows for the same `target_service`:
```
Δretry  = row_n.upstream_rq_retry  - row_{n-1}.upstream_rq_retry
Δtotal  = row_n.upstream_rq_total  - row_{n-1}.upstream_rq_total
retries_per_request = Δretry / Δtotal    (0 if Δtotal == 0)
```
A `retries_per_request` of `0` means the retry storm isn't happening on that service at that moment; a value that drops toward `0` right after an `ON→OFF` line in `retryguard.log` is the "RetryGuard actually suppressed retries" evidence.

### 3c. Resource usage CSV — `resource_usage.csv`

One row per **service per poll** (every ~5s), reporting that service's actual CPU and memory consumption on the worker node (app container only, sidecar excluded).

```
timestamp,service,cpu_millicores,memory_working_set_bytes,replica_count
2026-09-05T16:51:52Z,cartservice,4,81047552,1
```

| Column | What it is | How to read the number |
|---|---|---|
| `timestamp` | UTC time of this poll | Align with Locust/Envoy timestamps and `retryguard.log`. |
| `service` | Which Online Boutique deployment this row is about | One row per service per poll — filter to the service you care about (e.g. the bottlenecked one in S3/S4). |
| `cpu_millicores` | CPU actually used, in millicores (1000m = 1 full core) | `4` = using 0.4% of one core — essentially idle (S1 is light load). Under S3's bottleneck, expect this to climb toward the CPU limit (`100m` there) as the service saturates. |
| `memory_working_set_bytes` | Working-set memory in bytes | `81047552` ≈ 81 MB. Compare across time for the same service — a drop after RetryGuard disables retries on a downstream bottleneck is the "resource savings" evidence for Layer 2. |
| `replica_count` | Ready replica count from the Deployment | Always `1` in this workshop (fixed single replica) — not informative here. |

Divide `memory_working_set_bytes` by `1024*1024` to read it as MB, or by `1e6` for MB (decimal) — either is fine as long as you're consistent across the comparison.

---

## 4. What's inside every run folder

All 48 run folders (two levels down, e.g. `campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run4/`) have the same 13 files (baseline folders are missing only `retryguard.log`, since RetryGuard isn't running):

```
<scenario_dir>/<log_folder>/
  getproduct.csv                       ← Locust endpoint: browse product page
  postcheckout.csv                     ← Locust endpoint: submit checkout   (★ primary metric for S3/S4B)
  getcart.csv                          ← Locust endpoint: view cart
  postcart.csv                         ← Locust endpoint: add to cart
  emptycart.csv                        ← Locust endpoint: empty cart
  total.csv                            ← sum across all 5 endpoints (system-level view)
  num_agent.csv                        ← TopFull RL agent count over time (in this campaign: always 0 — not wired up; ignore)
  envoy_retries_frontend.csv           ← retries frontend issued when calling cart/productcatalog/checkout
  envoy_retries_checkoutservice.csv    ← retries checkoutservice issued when calling cart/productcatalog/payment
  envoy_retry_collector.log            ← collector health log (START/WARNING/SHUTDOWN) — only check if the CSV looks empty/wrong
  resource_usage.csv                   ← per-service CPU (millicores) and memory (bytes), polled every 5s
  resource_usage_collector.log         ← collector health log — only check if resource_usage.csv looks wrong
  retryguard.log                       ← RetryGuard's own decisions (ON→OFF / OFF→ON toggle events)   [RetryGuard runs only]
  run_manifest.json                    ← self-describing metadata: scenario, condition, run#, durations, config used
```

### What to actually look at, file by file

| File | Look at this | Ignore / rarely needed |
|---|---|---|
| `postcheckout.csv`, `getproduct.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv` | Columns `RPS, Fail, Goodput, Latency95` — one row per second. `Goodput` is the headline health metric; `Latency95` is the latency metric of record. | `Latency99` — always `0`, hardcoded/unused in TopFull's collector. Don't use it. |
| `total.csv` | Same columns, but summed across all 5 endpoints — use for **system-level** goodput/latency claims (as opposed to per-service). | Same `Latency99` caveat. |
| `envoy_retries_frontend.csv` / `envoy_retries_checkoutservice.csv` | `upstream_rq_total` and `upstream_rq_retry` **per target service**, sampled every 5s. Counters are **cumulative** — you must diff consecutive rows to get retries-per-second/retries-per-request. This is how you prove "RetryGuard actually reduced retry volume on this service." | `upstream_rq_retry_success` / `upstream_rq_retry_limit_exceeded` — nice-to-have detail, not needed for the headline analysis. |
| `resource_usage.csv` | `cpu_millicores` and `memory_working_set_bytes` per service, every 5s. Use to show a bottlenecked service's CPU/memory dropping after RetryGuard disables its retries. | `replica_count` — always `1` in this workshop (fixed-replica design), not informative. |
| `retryguard.log` (RG runs only) | The `ON→OFF` and `OFF→ON` lines — these are the controller's toggle events, with timestamps you cross-reference against the CSVs above. `OBSERVE` lines show the rejection rate that drove each decision. | `SKIP` / `PATCH_FAIL` — only relevant if debugging a run that looks broken. |
| `run_manifest.json` | Sanity-check `scenario_name`, `condition`, `run_number`, `duration_seconds` match what the folder name claims, before trusting the data. | Nothing — it's small, just glance at it once per folder. |
| `num_agent.csv` | Nothing in this campaign — always `0`, TopFull's RL agent-count instrumentation was never wired to populate it. | Everything — effectively dead data here. |
| `envoy_retry_collector.log`, `resource_usage_collector.log` | Only open these if the corresponding CSV looks empty, truncated, or all-zero — they'll show a `WARNING`/crash reason. | Otherwise skip entirely. |

### Row-count sanity check

- `duration_seconds` (from `run_manifest.json`) by scenario: S1 `normal_op` = 300s, S2–S4B = 600s, S6 `forced_recovery` and S5 `interval_*` = 900s (5 min peak + 10 min reduced load). Expect roughly that many rows in the per-second CSVs (`total.csv`, `postcheckout.csv`, etc.).
- Envoy/resource CSVs poll every 5s, so expect roughly `duration_seconds / 5` rows per service.
- If a CSV has far fewer rows than expected, treat that run with suspicion before including it in analysis (see verification checklist in [METRICS-COLLECTION-GUIDE.md](../../../Guides%20and%20Info/METRICS-COLLECTION-GUIDE.md) §9).

---

## 5. Quick recipes

**"Did RetryGuard actually toggle in this run?"**
```powershell
Select-String -Path "S1_normal_op\run_topfull_retryguard_normal_op_run4\retryguard.log" -Pattern "ON->OFF|OFF->ON|ON→OFF|OFF→ON"
```

**"Compare baseline vs RetryGuard goodput for a scenario"** — load `total.csv` (or the relevant endpoint CSV) from the three baseline folders and the three RetryGuard folders under that scenario. Align by row (second), average the three `Goodput` series pointwise, plot two lines (optional band). See §2.

**"Does S5's interval choice change recovery speed?"** — for each interval, average the three `postcheckout.csv` curves as in §2, find `OFF→ON` times in each `retryguard.log`, and compare recovery after the load drop across the four interval lines vs S6 baseline.

**"Load all runs for a scenario in Python"**
```python
from pathlib import Path
import pandas as pd

scenario = Path("experiments/results/campaign_48/S2_sustained_overload")
dfs = [pd.read_csv(p) for p in sorted(scenario.glob("baseline_*/total.csv"))]
min_len = min(len(df) for df in dfs)
baseline_mean = pd.concat([df["Goodput"].iloc[:min_len] for df in dfs], axis=1).mean(axis=1)
```

---

*See also: [experiments/results/README.md](../README.md) (campaign_48 vs august_38 split), [SCENARIOS-GUIDE.md](../../../Guides%20and%20Info/SCENARIOS-GUIDE.md) (scenario detail), [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md) (log format detail).*
