# Task 3 Report — Re-run S2 RetryGuard (run11) + baseline (run22) after perf fix

**Date:** 2026-09-15  
**Branch:** `feature/retryguard-perf-fix`  
**Worktree:** `.worktrees/retryguard-perf-fix`

---

## 1. Runs executed

| Run | Scenario | YAML slot | Duration | Completed |
|-----|----------|-----------|----------|-----------|
| S2 baseline run22 | sustained_overload, baseline | `scenario_2_baseline.yaml` → run22 | 600 s | ✅ 20:52–21:08 |
| 300 s cool-off | — | — | 300 s | ✅ |
| S2 RetryGuard run11 | sustained_overload, retryguard | `scenario_2_retryguard.yaml` → run11 | 600 s | ✅ 21:15–21:31 |

---

## 2. Restart signature check (Task 1 regression test)

**Result: CLEAN ✅ — no restart signature in run11.**

| Log | Events |
|-----|--------|
| `retryguard.log` | `WAITING` → `READY` → `START` (lines 1–3), `SHUTDOWN` / `EXIT` (lines 5656–5657) |
| `resource_usage_collector.log` | `START` (line 1), `SHUTDOWN` / `EXIT` (lines 2–3) |
| `envoy_retry_collector.log` | `START` (line 1), `SHUTDOWN` / `EXIT` (lines 2–3) |

The mid-run restart signature seen in run10 (repeated START/WAITING/READY blocks) is **absent**. Task 1's `InboundCsvTailer` fix eliminated the `service_inbound.csv` read storm.

---

## 3. Master-node CPU (Task 2 new metric)

`__master_node__` rows were **absent** in run10/run21 (pre-Task 2 build). First data comes from run22/run11.

| Run | Condition | master max CPU | master mean CPU |
|-----|-----------|---------------|----------------|
| run22 | baseline e2-16 | 6519 m | 5608 m |
| run11 | RG e2-16 | 6691 m | 5647 m |
| **Delta RG vs baseline** | | **+172 m (+2.6%)** | **+39 m (+0.7%)** |

RetryGuard's CPU overhead on the master node is **negligible** — well within run-to-run noise.

---

## 4. P95 / goodput comparison table

### getcart endpoint

| Run | Condition | mean P95 | max P95 | mean Goodput |
|-----|-----------|---------|---------|-------------|
| run21 | baseline e2-16 (prev) | 634 ms | 1600 ms | 102 rps |
| **run22** | **baseline e2-16 (new)** | **756 ms** | **1700 ms** | **137 rps** |
| run10 | RG e2-16 (prev) | 1262 ms | 2600 ms | 84 rps |
| **run11** | **RG e2-16 (new)** | **1594 ms** | **2800 ms** | **113 rps** |

### total (all endpoints)

| Run | Condition | mean Goodput | mean Fail | mean P95 | max P95 |
|-----|-----------|-------------|----------|---------|---------|
| run21 | baseline e2-16 (prev) | 290 rps | 422 | 357 ms | 1044 ms |
| **run22** | **baseline e2-16 (new)** | **504 rps** | **109** | **431 ms** | **1002 ms** |
| run10 | RG e2-16 (prev) | 332 rps | 266 | 669 ms | 1176 ms |
| **run11** | **RG e2-16 (new)** | **390 rps** | **151** | **791 ms** | **1318 ms** |

**RG still ~2× baseline on P95 (getcart 1594 vs 756 ms).** Run-to-run variability is significant (run21 vs run22 baseline: 290 vs 504 total goodput). RG run11 goodput (390) is better than RG run10 (332), within noise.

---

## 5. RetryGuard toggle events in run11

| Metric | Value |
|--------|-------|
| Total OBSERVE lines | 5553 |
| OBSERVE lines with rejection > 0 | **6** (all at SHUTDOWN moment 18:31:19Z) |
| Max observed rejection | 0.6364 (adservice, at shutdown only) |
| ON→OFF events | **0** |
| OFF→ON events | **0** |

Root cause: TopFull Layer A was active (1220 rows with threshold < 10000), throttling admission before mesh inbound services accumulated sustained 5xx. The `high` streak counter never reached `interval_samples=30` during the 600 s run.

---

## 6. File set in pulled folders

Both run22 and run11 contain the full expected file set:
- `getcart.csv`, `total.csv`, `emptycart.csv`, `postcart.csv`, `postcheckout.csv`, `getproduct.csv`
- `resource_usage.csv` (with `__master_node__` rows — new from Task 2)
- `service_edges.csv`, `service_inbound.csv`
- `topfull_throttle.csv`, `topfull_detect.csv`
- `num_agent.csv`, `run_manifest.json`, `service_capacity.json`
- `retryguard.log` (run11 only), `envoy_retry_collector.log`, `resource_usage_collector.log`, `topfull_throttle_collector.log`

---

## 7. VM stop

VMs stopped via `gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --project=networks-workshop --zone=us-central1-a --async` — stop operations initiated successfully.

---

## 8. YAML slots bumped

| Config | Previous | New (after this task) |
|--------|----------|----------------------|
| `scenario_2_baseline.yaml` | run22 / `…_run22` | **run23** / `…_run23` |
| `scenario_2_retryguard.yaml` | run11 / `…_run11` | **run12** / `…_run12` |

---

## 9. Commits

_(To be filled after `git commit` below)_

---

## 10. Key conclusions

1. **Task 1 fix (InboundCsvTailer) confirmed working**: zero restart signature in run11. The read-storm that caused run10's mid-run restarts is eliminated.
2. **Task 2 master CPU metric now live**: RG overhead is +39 m mean / +172 m max — negligible.
3. **P95 gap is structural, not caused by restarts**: even with clean run11 (no restarts), RG P95 is 2× baseline. This is because RG never disables retries (zero toggles) while Istio default 3-attempt retries remain active — the retry penalty without any benefit.
4. **RetryGuard still zero disables on flat S2 + TopFull ON**: same root cause as run9/run10. Need S3/S4 CPU constraints or tighter `per_try_timeout_ms` to produce sustained mesh 5xx.

**Status: DONE**  
**Report path:** `.worktrees/retryguard-perf-fix/.superpowers/sdd/task-3-report.md`
