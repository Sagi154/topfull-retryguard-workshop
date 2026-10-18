# S1 mode matrix (2026-10-12): normal and burst 2.0

Four scored holds. Each is 300 s, RetryGuard on, TopFull off. Two are normal mode. Two set `burst_rpr` to 2.0. The six S1 cells with TopFull on failed the matrix gate, and the single replay of each failed the same way. Those twelve folders stay in `experiments/results/final results/` and are not comparison columns. Scored with `experiments/analysis_score.py`. Follows [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). Run log: [2026-10-12-s1-s2-mode-matrix-run-log.md](../../docs/superpowers/plans/2026-10-12-s1-s2-mode-matrix-run-log.md).

## 1. Setup

- **Duration** 300 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **175 / 30 / 70 / 90 / 5**, `spawn_rate` 50. Locked S1 mix, Paper-C1. Two repeats of each scored cell.
- **CPU and replica pin** (`service_capacity.json` on all four scored holds):

| Service | Per-pod quota (m) | Replicas |
| --- | ---: | ---: |
| frontend | 1150 | 4 |
| checkoutservice | 800 | 1 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 800 | 1 |
| cartservice | 800 | 1 |
| currencyservice | 770 | 1 |
| shippingservice | 770 | 1 |
| adservice | 1150 | 1 |
| paymentservice | 155 | 1 |
| emailservice | 120 | 1 |
| redis-cart | 540 | 1 |

  Frontend replica count is 4 on every `resource_usage.csv` sample of the scored holds, and every other service is 1. That is the Paper-C1 pin: sidecar `proxyCPU=90m` with `proxyCPULimit` unset while frontend is held at 4, and catalog HPA max 1.
- **Controllers.** RetryGuard is on for every scored hold. TopFull is off on every scored hold. The TopFull-on cells are the failed gate in §3.
- **RetryGuard knobs.** `retry_metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.4`, climb `0.16/0.32` with `climb_interval_seconds=10`, `reenable_rejection=0.25`. Normal-mode holds omit `burst_rpr`. Burst holds add `burst_window_seconds=5` and `burst_min_first_attempts=20`, with `burst_rpr` 2.0.
- **Cool-off** 120 s between holds, from `run_scenario.py` exit.
- **Folders:** `experiments/results/final results/S1_normal_operation_<normal|burst>/<rg_only|both>/`, the four names in §2. Configs: `experiments/configs/study_2026_10_12/18_s1_normal_rgtf0_rep1.yaml`, `19_s1_normal_rgtf0_rep2.yaml`, `24_s1_burst20_rgtf0_rep1.yaml`, `25_s1_burst20_rgtf0_rep2.yaml`. Each manifest has `run_number` 1; the `log_folder` name is the slot.

## 2. Index

Column order in every table below follows this index. A bold bar (**┃**) follows the normal pair.

| # | Column | Mode | RetryGuard | TopFull |
| ---: | --- | --- | --- | --- |
| 1 | `s1_normal_rgtf0_rep1` | normal | on | off |
| 2 | `s1_normal_rgtf0_rep2` | normal | on | off |
| | **┃** | | | |
| 3 | `s1_burst20_rgtf0_rep1` | burst_rpr 2.0 | on | off |
| 4 | `s1_burst20_rgtf0_rep2` | burst_rpr 2.0 | on | off |

## 3. Gate

**Pass on the four columns.** The run log records PASS for each scored hold.

The six TopFull-on cells failed `live5s_caps=0` with `other=0`. Every fresh threshold stayed at the 10000 passthrough. Locust rows were inside 270–310, frontend was 4 on every resource sample, and VirtualService attempts were 3. Each cell was replayed once (`_r2`) and failed the same way. Both copies are kept.

| Hold | Folder | Replay | Locust rows |
| --- | --- | --- | ---: |
| 3 | `s1_normal_rgtf1_rep1` | `s1_normal_rgtf1_rep1_r2` | 287 / 287 |
| 4 | `s1_normal_rgtf1_rep2` | `s1_normal_rgtf1_rep2_r2` | 282 / 284 |
| 5 | `s1_normal_tf1rg0_rep1` | `s1_normal_tf1rg0_rep1_r2` | 277 / 288 |
| 6 | `s1_normal_tf1rg0_rep2` | `s1_normal_tf1rg0_rep2_r2` | 286 / 287 |
| 9 | `s1_burst20_rgtf1_rep1` | `s1_burst20_rgtf1_rep1_r2` | 285 / 287 |
| 10 | `s1_burst20_rgtf1_rep2` | `s1_burst20_rgtf1_rep2_r2` | 288 / 288 |

Scorer gate numbers for the four columns:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| `s1_normal_rgtf0_rep1` | 288 | 364 | 0 of 4004 | present |
| `s1_normal_rgtf0_rep2` | 289 | 364 | 0 of 4004 | present |
| `s1_burst20_rgtf0_rep1` | 287 | 363 | 0 of 3993 | present |
| `s1_burst20_rgtf0_rep2` | 287 | 363 | 0 of 3993 | present |

`service_capacity.json` matches the pin in §1 on every scored hold, for every service. `resource_usage.csv` shows frontend at 4 replicas on every sample (88/88, 89/89, 89/89, 89/89). No service has a zero-replica sample.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

The two normal-mode columns omit `burst_rpr`. Burst mode was off on those holds.

The scorer's `Burst bars` line:

> Burst bars: s1_burst20_rgtf0_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); s1_burst20_rgtf0_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

A burst shed goes to 0 attempts and recovers on the normal path. Shed and 0→1 take **20 s** of row timestamps (`interval_samples=20`). Climbs 1→2 and 2→3 take **10 s** on these holds (`climb_interval_seconds=10` on the START line).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

Two edges have a tick above the shed bar or a retry delta on the wider matrix: `frontend → checkoutservice` and `frontend → recommendationservice`. On these four holds both edges have no tick above 0.40 and a retry delta of 0. Every other controlled edge is the same, so it is omitted here. The file streak is in seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. No file streak reaches 30 s, so nothing in these cells is bold.

### (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → recommendationservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

### (a) Mean / median / max / volume rpr

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |
| frontend → recommendationservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

### (a) Climb streaks, 1-attempt / 2-attempt

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | — / — | — / — | **┃** | — / — | — / — |

### 5a. Burst

The two normal-mode columns omit `burst_rpr`. Burst mode was off on those holds, and their burst-window cells are em dashes.

Burst is a second shed test beside (a). It does not change the three tables above.

Burst bars: s1_burst20_rgtf0_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); s1_burst20_rgtf0_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force (burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count in parentheses. Samples exist only while the edge is above 0 attempts and the window meets the volume floor.

### (a2) Burst window

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| checkoutservice → paymentservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) |
| frontend → productcatalogservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (308) | 0.00 / 0.00 / 0 / 0 (303) |
| recommendationservice → productcatalogservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (301) |
| checkoutservice → cartservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (299) |
| checkoutservice → currencyservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) |
| frontend → cartservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (302) |
| frontend → currencyservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (302) |
| frontend → adservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (301) |
| frontend → checkoutservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) |
| frontend → recommendationservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (301) |
| checkoutservice → emailservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) |
| checkoutservice → shippingservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (299) |
| frontend → shippingservice | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (300) |

`frontend → checkoutservice` and `frontend → recommendationservice` have a full `burst_rpr5` sample count on both burst holds and a peak of 0.00, so the volume floor does not drop them and the shed count is 0. Every other edge in that table has peak 0.00, 0 samples at the bar, and 0 burst sheds.

**Burst vs normal sheds.** Neither burst hold has an `ON→OFF` line, so the burst-shed count is 0 and the normal-shed count is 0.

**Replay check.** Both scored burst holds are TopFull off, so neither has a replay. The TopFull-on burst cells failed the gate in §3 and are not columns here.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count. **Bold** in the 0.20 table would be a streak of at least 30 on a controlled service. No controlled service reaches 30, so nothing in that table is bold. Frontend and redis-cart stay plain. The re-enable bar on these holds is 0.25.

### (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

### (a) context: rejection streak under the re-enable bar / count

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 312 / 312 | 313 / 313 | **┃** | 313 / 313 | 313 / 313 |
| checkoutservice | 311 / 311 | 312 / 312 | **┃** | 311 / 311 | 312 / 312 |
| recommendationservice | 312 / 312 | 313 / 313 | **┃** | 313 / 313 | 313 / 313 |
| paymentservice | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 |
| emailservice | 311 / 311 | 312 / 312 | **┃** | 311 / 311 | 312 / 312 |
| productcatalogservice | 313 / 313 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| cartservice | 313 / 313 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| currencyservice | 312 / 312 | 313 / 313 | **┃** | 313 / 313 | 313 / 313 |
| shippingservice | 312 / 312 | 313 / 313 | **┃** | 313 / 313 | 313 / 313 |
| adservice | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

gRPC counted in the rejection rate and in the retry policy. Cell is grpc_4 / grpc_14.

### grpc_4 / grpc_14

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. No service reaches 0.5, so nothing in this table is bold.

### (b) Detector overloaded fraction

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| checkoutservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| recommendationservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| paymentservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| emailservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| productcatalogservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| cartservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| currencyservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| shippingservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| adservice | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |
| redis-cart | 0/414 (0.0%) | 0/414 (0.0%) | **┃** | 0/412 (0.0%) | 0/412 (0.0%) |

## 8. (c) Retry volume

### (c) Outbound retry delta by target

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 0 | 0 | **┃** | 0 | 0 |
| recommendationservice | 0 | 0 | **┃** | 0 | 0 |

### (c) Inbound resets

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 2 | 29 | **┃** | 17 | 25 |
| checkoutservice | 0 | 0 | **┃** | 7 | 1 |
| recommendationservice | 0 | 0 | **┃** | 1 | 2 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 0 | 4 | **┃** | 1 | 5 |
| cartservice | 0 | 0 | **┃** | 2 | 0 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 2 | **┃** | 1 | 1 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 |

The same `grpc_4 / grpc_14` pair in §6 is what the retry policy counts on the four read callees. Every pair on these holds is 0 / 0.

## 9. RetryGuard toggles

Two parts. Part 1 is the scorer's log for each hold. Part 2 summarizes it per callee.

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name.

### Part 1: per hold

The four holds have a `retryguard.log` and no transition lines: `s1_normal_rgtf0_rep1`, `s1_normal_rgtf0_rep2`, `s1_burst20_rgtf0_rep1`, `s1_burst20_rgtf0_rep2`.

### Part 2: per callee

No callee shed or re-enabled on any of these four holds. Payment, email, catalog, cart, currency, shipping, ad, checkout, and recommendations have no `ON→OFF` and no `OFF→ON`.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

### Locust goodput

| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 161.0 | 160.8 | **┃** | 161.0 | 161.2 |
| postcheckout | 27.7 | 27.6 | **┃** | 27.6 | 27.7 |
| getcart | 64.4 | 64.5 | **┃** | 64.4 | 64.5 |
| postcart | 82.8 | 82.9 | **┃** | 82.7 | 82.9 |
| emptycart | 4.7 | 4.7 | **┃** | 4.7 | 4.7 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

### Locust fail rate

| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

### Locust P95

| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 79 | 76 | **┃** | 69 | 71 |
| postcheckout | 170 | 183 | **┃** | 159 | 157 |
| getcart | 63 | 67 | **┃** | 46 | 56 |
| postcart | 59 | 59 | **┃** | 58 | 59 |
| emptycart | 10 | 14 | **┃** | 13 | 12 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

### Inbound arrival rate

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 291.8 | 291.8 | **┃** | 292.6 | 292.6 |
| checkoutservice | 23.6 | 23.7 | **┃** | 23.7 | 23.7 |
| recommendationservice | 216.8 | 216.7 | **┃** | 217.3 | 217.3 |
| paymentservice | 23.6 | 23.7 | **┃** | 23.7 | 23.7 |
| emailservice | 23.6 | 23.7 | **┃** | 23.7 | 23.7 |
| productcatalogservice | 1509.5 | 1509.1 | **┃** | 1513.3 | 1513.0 |
| cartservice | 315.5 | 315.5 | **┃** | 316.3 | 316.3 |
| currencyservice | 433.5 | 433.4 | **┃** | 434.6 | 434.5 |
| shippingservice | 102.6 | 102.6 | **┃** | 102.9 | 102.9 |
| adservice | 137.8 | 137.7 | **┃** | 138.1 | 138.1 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

### Inbound sojourn (ms)

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 47 | 46 | **┃** | 41 | 42 |
| checkoutservice | 79 | 82 | **┃** | 74 | 63 |
| recommendationservice | 8 | 9 | **┃** | 6 | 6 |
| paymentservice | 1 | 2 | **┃** | 2 | 1 |
| emailservice | 6 | 7 | **┃** | 5 | 6 |
| productcatalogservice | 1 | 1 | **┃** | 1 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | 2 |
| currencyservice | 1 | 1 | **┃** | 1 | 1 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 |
| adservice | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.

### Share of inbound requests above 500 ms

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — |

## 16. CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota.

### CPU quota / replicas / mean / max

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 827 / 1327 | 1150 / 4 / 828 / 1341 | **┃** | 1150 / 4 / 908 / 1465 | 1150 / 4 / 844 / 1361 |
| checkoutservice | 800 / 1 / 257 / 419 | 800 / 1 / 257 / 416 | **┃** | 800 / 1 / 260 / 421 | 800 / 1 / 262 / 424 |
| recommendationservice | 1150 / 1 / 318 / 522 | 1150 / 1 / 315 / 523 | **┃** | 1150 / 1 / 334 / 557 | 1150 / 1 / 324 / 538 |
| paymentservice | 155 / 1 / 18 / 29 | 155 / 1 / 18 / 30 | **┃** | 155 / 1 / 18 / 31 | 155 / 1 / 19 / 33 |
| emailservice | 120 / 1 / 36 / 54 | 120 / 1 / 36 / 55 | **┃** | 120 / 1 / 36 / 57 | 120 / 1 / 36 / 55 |
| productcatalogservice | 800 / 1 / 297 / 474 | 800 / 1 / 298 / 477 | **┃** | 800 / 1 / 340 / 536 | 800 / 1 / 321 / 510 |
| cartservice | 800 / 1 / 212 / 357 | 800 / 1 / 212 / 346 | **┃** | 800 / 1 / 229 / 385 | 800 / 1 / 236 / 465 |
| currencyservice | 770 / 1 / 189 / 309 | 770 / 1 / 194 / 320 | **┃** | 770 / 1 / 206 / 332 | 770 / 1 / 194 / 320 |
| shippingservice | 770 / 1 / 50 / 78 | 770 / 1 / 48 / 77 | **┃** | 770 / 1 / 52 / 82 | 770 / 1 / 51 / 80 |
| adservice | 1150 / 1 / 82 / 123 | 1150 / 1 / 83 / 128 | **┃** | 1150 / 1 / 86 / 131 | 1150 / 1 / 82 / 124 |
| redis-cart | 540 / 1 / 27 / 42 | 540 / 1 / 26 / 42 | **┃** | 540 / 1 / 29 / 45 | 540 / 1 / 28 / 44 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. A sample with replica count 0 is left out. None of these holds had one.

### CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.18 / 0.29 | 0.18 / 0.29 | **┃** | 0.20 / 0.32 | 0.18 / 0.30 |
| checkoutservice | 0.32 / 0.52 | 0.32 / 0.52 | **┃** | 0.32 / 0.53 | 0.33 / 0.53 |
| recommendationservice | 0.28 / 0.45 | 0.27 / 0.45 | **┃** | 0.29 / 0.48 | 0.28 / 0.47 |
| paymentservice | 0.12 / 0.19 | 0.12 / 0.19 | **┃** | 0.12 / 0.20 | 0.12 / 0.21 |
| emailservice | 0.30 / 0.45 | 0.30 / 0.46 | **┃** | 0.30 / 0.47 | 0.30 / 0.46 |
| productcatalogservice | 0.37 / 0.59 | 0.37 / 0.60 | **┃** | 0.42 / 0.67 | 0.40 / 0.64 |
| cartservice | 0.26 / 0.45 | 0.26 / 0.43 | **┃** | 0.29 / 0.48 | 0.29 / 0.58 |
| currencyservice | 0.25 / 0.40 | 0.25 / 0.42 | **┃** | 0.27 / 0.43 | 0.25 / 0.42 |
| shippingservice | 0.06 / 0.10 | 0.06 / 0.10 | **┃** | 0.07 / 0.11 | 0.07 / 0.10 |
| adservice | 0.07 / 0.11 | 0.07 / 0.11 | **┃** | 0.08 / 0.11 | 0.07 / 0.11 |
| redis-cart | 0.05 / 0.08 | 0.05 / 0.08 | **┃** | 0.05 / 0.08 | 0.05 / 0.08 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

### Detector max utilization

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | **┃** | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.311 | 0.307 | **┃** | 0.346 | 0.312 |
| checkoutservice | 0.609 | 0.634 | **┃** | 0.619 | 0.620 |
| recommendationservice | 0.495 | 0.477 | **┃** | 0.505 | 0.502 |
| paymentservice | 0.329 | 0.381 | **┃** | 0.458 | 0.348 |
| emailservice | 0.625 | 0.650 | **┃** | 0.642 | 0.642 |
| productcatalogservice | 0.640 | 0.618 | **┃** | 0.723 | 0.664 |
| cartservice | 0.494 | 0.501 | **┃** | 0.524 | 0.630 |
| currencyservice | 0.445 | 0.456 | **┃** | 0.503 | 0.473 |
| shippingservice | 0.130 | 0.129 | **┃** | 0.142 | 0.135 |
| adservice | 0.147 | 0.133 | **┃** | 0.130 | 0.152 |
| redis-cart | 0.081 | 0.083 | **┃** | 0.094 | 0.093 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. `postcart` and `emptycart` are no cap on every live read of every hold. On these four TopFull-off holds, every API is no cap for the span the scorer prints.

### TopFull live caps

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### s1_normal_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:44:20–10:51:05 |
| postcheckout | no cap 10:44:20–10:51:05 |
| getcart | no cap 10:44:20–10:51:05 |
| postcart | no cap 10:44:20–10:51:05 |
| emptycart | no cap 10:44:20–10:51:05 |

### s1_normal_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:56:30–11:03:20 |
| postcheckout | no cap 10:56:30–11:03:20 |
| getcart | no cap 10:56:30–11:03:20 |
| postcart | no cap 10:56:30–11:03:20 |
| emptycart | no cap 10:56:30–11:03:20 |

### s1_burst20_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:43:25–12:50:15 |
| postcheckout | no cap 12:43:25–12:50:15 |
| getcart | no cap 12:43:25–12:50:15 |
| postcart | no cap 12:43:25–12:50:15 |
| emptycart | no cap 12:43:25–12:50:15 |

### s1_burst20_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:55:35–13:02:25 |
| postcheckout | no cap 12:55:35–13:02:25 |
| getcart | no cap 12:55:35–13:02:25 |
| postcart | no cap 12:55:35–13:02:25 |
| emptycart | no cap 12:55:35–13:02:25 |

## 20. Per hold

**s1_normal_rgtf0_rep1.** Nothing shed. Retry volume is 0 into checkoutservice and 0 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 0 / 0. No service is detector-hot. Locust fail rate is 0 on every API. Mean goodput is 161.0 / 27.7 / 64.4 / 82.8 / 4.7. Burst mode was off.

**s1_normal_rgtf0_rep2.** Nothing shed. Retry volume is 0 into checkoutservice and 0 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 0 / 0. No service is detector-hot. Locust fail rate is 0 on every API. Mean goodput is 160.8 / 27.6 / 64.5 / 82.9 / 4.7. Burst mode was off.

**s1_burst20_rgtf0_rep1.** Burst windows were sampled and none crossed the bar. Nothing shed. Retry volume is 0 into checkoutservice and 0 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 0 / 0. No service is detector-hot. Locust fail rate is 0 on every API. Mean goodput is 161.0 / 27.6 / 64.4 / 82.7 / 4.7. This hold has no replay.

**s1_burst20_rgtf0_rep2.** Burst windows were sampled and none crossed the bar. Nothing shed. Retry volume is 0 into checkoutservice and 0 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 0 / 0. No service is detector-hot. Locust fail rate is 0 on every API. Mean goodput is 161.2 / 27.7 / 64.5 / 82.9 / 4.7. This hold has no replay.

## 21. Related links

- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md), edge-mode and burst-mode sections
- [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md)
- The S2 half of this matrix: [2026-10-12-s2-mode-matrix-abc.md](2026-10-12-s2-mode-matrix-abc.md)
- Earlier S2 burst matrix, same bar 2.0 and a different load: [2026-10-12-s2-burst-matrix-abc.md](2026-10-12-s2-burst-matrix-abc.md)
- Run log: [2026-10-12-s1-s2-mode-matrix-run-log.md](../../docs/superpowers/plans/2026-10-12-s1-s2-mode-matrix-run-log.md)
