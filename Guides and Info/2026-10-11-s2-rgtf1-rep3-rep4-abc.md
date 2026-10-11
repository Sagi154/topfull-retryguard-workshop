# S2 both-on replicates 3 and 4 (2026-10-11)

Analysis of the four tuned both-on S2 holds, scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Same cell as [2026-10-11-s2-tuning-abc.md](2026-10-11-s2-tuning-abc.md). Run log: [2026-10-11-s2-rgtf1-rep3-rep4-run-log.md](../docs/superpowers/plans/2026-10-11-s2-rgtf1-rep3-rep4-run-log.md).

## 1. Setup

- **Duration** 600 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. Locked S2 mix, Paper-C1.
- **CPU and replica pin** (`service_capacity.json`):

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

  Frontend sidecar `proxyCPU=90m`, `proxyCPULimit` unset. Catalog HPA max 1 during the holds.
- **Controllers.** RetryGuard on and TopFull on on all four. Tuned parameters: `retry_metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`.
- **Cool-off** 120 s between rep3 and rep4, from `run_scenario.py` exit.
- **Folders:** `experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep{1,2,3,4}`. New configs: `experiments/configs/study_2026_10_11/21_s2_tune_rgtf1_rep3.yaml` and `22_s2_tune_rgtf1_rep4.yaml`.

## 2. Index

Columns below. The bold bar separates the two earlier both-on holds from the two new ones.

| Column | Folder | Arm | Replicate |
| --- | --- | --- | --- |
| rep1 on | `study4_s2_tune_rgtf1_rep1` | RetryGuard on, TopFull on | 1 |
| rep2 on | `study4_s2_tune_rgtf1_rep2` | RetryGuard on, TopFull on | 2 |
| rep3 on | `study4_s2_tune_rgtf1_rep3` | RetryGuard on, TopFull on | 3 |
| rep4 on | `study4_s2_tune_rgtf1_rep4` | RetryGuard on, TopFull on | 4 |

All four folders have `run_number` 1. The `log_folder` name is the slot.

## 3. Gate

**Pass on all four** under the run-log gates: Locust rows in range, START line with the tuned parameters, no `PATCH_FAIL` and no traceback, frontend replica 4 and catalog replica 1 on every sample, Paper-C1 `service_capacity.json`, at least one live TopFull cap below 10000, VirtualServices restored to `attempts: 3` with no route timeout.

Scorer gate numbers:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| rep1 on | 566 | 665 | 0 of 7315 | present |
| rep2 on | 566 | 665 | 0 of 7315 | present |
| rep3 on | 550 | 673 | 3124 of 4279 | present |
| rep4 on | 550 | 673 | 3663 of 3740 | present |

`service_capacity.json` matches the pin in §1 on all four holds. `resource_usage.csv` shows frontend at 4 replicas on every sample (149 / 150 / 155 / 155) and catalog at 1 on every sample (149 / 150 / 155 / 155). No service has a zero-replica sample.

On rep3 and rep4 the frontend inbound timestamps are spaced at a median of 2.0 s (maximum 2.0 s), so the scorer's 1.5 s gap rule marks most consecutive pairs. On rep1 and rep2 that median is 1.0 s and the scorer reports 0 gaps. The mesh span stays about 665–673 s on all four.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

START line on every hold: `metric=edge_rpr`, `rpr_threshold=0.40`, `rejection_threshold=0.20`, `reenable_rejection=0.25`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `sample_interval=1s`, `interval_samples=20`, `attempts_on=3`.

Intervals on these holds:

- Shed and 0→1 take **20 s** (`interval_samples=20`).
- Climbs 1→2 and 2→3 take **10 s** (`climb_interval_seconds=10`).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

`frontend → checkoutservice` is the edge with a sustained retry delta. `frontend → cartservice` has one tick above the shed bar on rep3 and a retry delta of 4. Every other controlled edge has a zero retry delta and no tick above the shed bar.

**File streak, seconds / ticks above the shed bar (controller `high` in parentheses)**

| Edge | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 8 / 207 (9) | 8 / 199 (9) | **┃** | 12 / 90 (7) | 10 / 89 (6) |
| frontend → cartservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 1 (1) | 0 / 0 (0) |

No streak reaches 30 s, so nothing is bold. The longest checkout file streak is 12 s, under the 20 s shed interval. Controller `high` is 9, 9, 7, and 6.

**Mean / median / max / volume rpr**

| Edge | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.826 / 0.000 / 6.64 / 0.750 | 0.811 / 0.000 / 6.00 / 0.698 | **┃** | 0.612 / 0.000 / 3.91 / 0.589 | 0.646 / 0.000 / 3.68 / 0.591 |
| frontend → cartservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.002 / 0.000 / 0.50 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

The median is zero on every cell. Checkout volume rpr is 0.750, 0.698, 0.589, and 0.591.

**Climb streaks, 1-attempt / 2-attempt** (samples while that cap is in force; an em dash means that cap never applied)

| Edge | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — |
| frontend → cartservice | — / — | — / — | **┃** | — / — | — / — |

Attempts stayed at 3. The 1-attempt and 2-attempt caps never applied.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count above 0.20, then longest streak / count strictly under the re-enable bar of 0.25. No controlled service reaches a 0.20 streak of 30, so nothing in that table is bold. Frontend and redis-cart stay plain.

**Above 0.20**

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 1 / 1 | 0 / 0 | **┃** | 1 / 1 | 1 / 1 |
| checkoutservice | 9 / 204 | 8 / 189 | **┃** | 6 / 86 | 6 / 89 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 1 / 1 | 1 / 2 | **┃** | 1 / 2 | 0 / 0 |
| emailservice | 4 / 81 | 4 / 70 | **┃** | 3 / 41 | 3 / 36 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

**Strictly under 0.25**

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 612 / 612 | 612 / 612 | **┃** | 329 / 329 | 306 / 306 |
| checkoutservice | 50 / 413 | 54 / 428 | **┃** | 44 / 245 | 24 / 220 |
| recommendationservice | 613 / 613 | 613 / 613 | **┃** | 329 / 329 | 307 / 307 |
| paymentservice | 352 / 611 | 442 / 610 | **┃** | 199 / 328 | 306 / 306 |
| emailservice | 50 / 487 | 53 / 516 | **┃** | 44 / 293 | 40 / 270 |
| productcatalogservice | 613 / 613 | 612 / 612 | **┃** | 330 / 330 | 307 / 307 |
| cartservice | 613 / 613 | 612 / 612 | **┃** | 330 / 330 | 307 / 307 |
| currencyservice | 613 / 613 | 613 / 613 | **┃** | 330 / 330 | 307 / 307 |
| shippingservice | 613 / 613 | 613 / 613 | **┃** | 329 / 329 | 307 / 307 |
| adservice | 612 / 612 | 612 / 612 | **┃** | 329 / 329 | 307 / 307 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

**grpc_4 / grpc_14**

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| checkoutservice | **392/717 (54.7%)** | **384/717 (53.6%)** | **┃** | **377/736 (51.2%)** | **376/739 (50.9%)** |
| recommendationservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 1/736 (0.1%) | 13/739 (1.8%) |
| paymentservice | 3/717 (0.4%) | 0/717 (0.0%) | **┃** | 10/736 (1.4%) | 3/739 (0.4%) |
| emailservice | 122/717 (17.0%) | 115/717 (16.0%) | **┃** | 142/736 (19.3%) | 156/739 (21.1%) |
| productcatalogservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| cartservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| currencyservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| shippingservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| adservice | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |
| redis-cart | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/736 (0.0%) | 0/739 (0.0%) |

Checkout is the only service at or above 0.5, on all four holds, between 50.9% and 54.7%. Email stays at 16.0%–21.1%.

## 8. (c) Retry volume

Outbound retry delta by target. Every other target is 0 on every hold.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 20,066 | 19,120 | **┃** | 15,511 | 15,629 |
| cartservice | 0 | 0 | **┃** | 4 | 0 |

Inbound resets, all 11 services.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 58 | 16 | **┃** | 145 | 192 |
| checkoutservice | 13,631 | 13,753 | **┃** | 11,494 | 11,776 |
| recommendationservice | 0 | 1 | **┃** | 41 | 94 |
| paymentservice | 780 | 721 | **┃** | 910 | 756 |
| emailservice | 1,009 | 830 | **┃** | 1,135 | 954 |
| productcatalogservice | 0 | 3 | **┃** | 6 | 9 |
| cartservice | 753 | 863 | **┃** | 668 | 613 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 1,254 | 1,132 | **┃** | 889 | 940 |
| adservice | 0 | 0 | **┃** | 1 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 |

`grpc_4 / grpc_14` is 0 / 0 on the four read callees, the same pair as in §6.

## 9. RetryGuard toggles

`ON→OFF` is a shed. `0→1` is the first step back on.

rep1 on, rep2 on, rep3 on, and rep4 on have no transition lines.

No callee shed or re-enabled on any of these four holds, so there is no per-callee table. Attempts stayed at 3, and the re-enable bar was never in force.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 163.0 | 264.0 | **┃** | 263.7 | 263.8 |
| postcheckout | 28.4 | 30.5 | **┃** | 31.6 | 31.8 |
| getcart | 60.0 | 95.9 | **┃** | 96.0 | 95.7 |
| postcart | 86.4 | 86.4 | **┃** | 86.3 | 86.4 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.368 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.607 | 0.584 | **┃** | 0.577 | 0.579 |
| getcart | 0.361 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| getproduct | 118 | 247 | **┃** | 342 | 347 |
| postcheckout | 907 | 983 | **┃** | 950 | 959 |
| getcart | 164 | 261 | **┃** | 352 | 358 |
| postcart | 60 | 67 | **┃** | 79 | 79 |
| emptycart | 22 | 16 | **┃** | 14 | 25 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 329.3 | 456.1 | **┃** | 449.6 | 449.8 |
| checkoutservice | 70.4 | 69.9 | **┃** | 62.2 | 62.5 |
| recommendationservice | 245.3 | 372.2 | **┃** | 366.6 | 366.8 |
| paymentservice | 67.5 | 67.4 | **┃** | 60.2 | 59.8 |
| emailservice | 31.1 | 33.1 | **┃** | 33.7 | 33.4 |
| productcatalogservice | 1701.2 | 2555.1 | **┃** | 2517.2 | 2518.1 |
| cartservice | 396.5 | 524.6 | **┃** | 511.3 | 510.8 |
| currencyservice | 508.2 | 761.8 | **┃** | 747.2 | 747.7 |
| shippingservice | 177.9 | 212.6 | **┃** | 199.1 | 198.1 |
| adservice | 149.9 | 242.6 | **┃** | 239.8 | 239.9 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 137 | 168 | **┃** | 210 | 219 |
| checkoutservice | 328 | 324 | **┃** | 309 | 307 |
| recommendationservice | 19 | 57 | **┃** | 54 | 56 |
| paymentservice | 5 | 5 | **┃** | 8 | 5 |
| emailservice | 33 | 32 | **┃** | 40 | 39 |
| productcatalogservice | 1 | 2 | **┃** | 5 | 5 |
| cartservice | 3 | 3 | **┃** | 4 | 4 |
| currencyservice | 2 | 3 | **┃** | 5 | 4 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 2 |
| redis-cart | — | — | **┃** | — | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. Cells are the scorer's share.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.048 | 0.039 | **┃** | 0.040 | 0.041 |
| checkoutservice | 0.450 | 0.399 | **┃** | 0.335 | 0.330 |
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

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum `cpu_millicores` across replicas.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 966 / 1292 | 1150 / 4 / 1202 / 1571 | **┃** | 1150 / 4 / 1143 / 1556 | 1150 / 4 / 1143 / 1564 |
| checkoutservice | 800 / 1 / 515 / 798 | 800 / 1 / 507 / 795 | **┃** | 800 / 1 / 484 / 797 | 800 / 1 / 495 / 796 |
| recommendationservice | 1150 / 1 / 387 / 556 | 1150 / 1 / 560 / 772 | **┃** | 1150 / 1 / 613 / 864 | 1150 / 1 / 625 / 905 |
| paymentservice | 155 / 1 / 40 / 75 | 155 / 1 / 41 / 75 | **┃** | 155 / 1 / 44 / 105 | 155 / 1 / 41 / 80 |
| emailservice | 120 / 1 / 46 / 106 | 120 / 1 / 47 / 110 | **┃** | 120 / 1 / 50 / 111 | 120 / 1 / 50 / 108 |
| productcatalogservice | 800 / 1 / 367 / 482 | 800 / 1 / 409 / 535 | **┃** | 800 / 1 / 383 / 522 | 800 / 1 / 382 / 525 |
| cartservice | 800 / 1 / 259 / 433 | 800 / 1 / 271 / 370 | **┃** | 800 / 1 / 262 / 415 | 800 / 1 / 259 / 356 |
| currencyservice | 770 / 1 / 232 / 314 | 770 / 1 / 307 / 406 | **┃** | 770 / 1 / 294 / 400 | 770 / 1 / 298 / 408 |
| shippingservice | 770 / 1 / 64 / 95 | 770 / 1 / 73 / 107 | **┃** | 770 / 1 / 70 / 106 | 770 / 1 / 71 / 106 |
| adservice | 1150 / 1 / 92 / 118 | 1150 / 1 / 121 / 156 | **┃** | 1150 / 1 / 151 / 384 | 1150 / 1 / 131 / 185 |
| redis-cart | 540 / 1 / 32 / 48 | 540 / 1 / 33 / 51 | **┃** | 540 / 1 / 33 / 54 | 540 / 1 / 33 / 53 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`.

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.21 / 0.28 | 0.26 / 0.34 | **┃** | 0.25 / 0.34 | 0.25 / 0.34 |
| checkoutservice | 0.64 / 1.00 | 0.63 / 0.99 | **┃** | 0.61 / 1.00 | 0.62 / 0.99 |
| recommendationservice | 0.34 / 0.48 | 0.49 / 0.67 | **┃** | 0.53 / 0.75 | 0.54 / 0.79 |
| paymentservice | 0.26 / 0.48 | 0.26 / 0.48 | **┃** | 0.28 / 0.68 | 0.26 / 0.52 |
| emailservice | 0.38 / 0.88 | 0.39 / 0.92 | **┃** | 0.41 / 0.93 | 0.42 / 0.90 |
| productcatalogservice | 0.46 / 0.60 | 0.51 / 0.67 | **┃** | 0.48 / 0.65 | 0.48 / 0.66 |
| cartservice | 0.32 / 0.54 | 0.34 / 0.46 | **┃** | 0.33 / 0.52 | 0.32 / 0.45 |
| currencyservice | 0.30 / 0.41 | 0.40 / 0.53 | **┃** | 0.38 / 0.52 | 0.39 / 0.53 |
| shippingservice | 0.08 / 0.12 | 0.09 / 0.14 | **┃** | 0.09 / 0.14 | 0.09 / 0.14 |
| adservice | 0.08 / 0.10 | 0.11 / 0.14 | **┃** | 0.13 / 0.33 | 0.11 / 0.16 |
| redis-cart | 0.06 / 0.09 | 0.06 / 0.09 | **┃** | 0.06 / 0.10 | 0.06 / 0.10 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | rep1 on | rep2 on | **┃** | rep3 on | rep4 on |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.314 | 0.388 | **┃** | 0.367 | 0.374 |
| checkoutservice | 1.048 | 1.055 | **┃** | 1.036 | 1.060 |
| recommendationservice | 0.541 | 0.708 | **┃** | 0.812 | 0.826 |
| paymentservice | 0.826 | 0.723 | **┃** | 0.981 | 0.974 |
| emailservice | 1.042 | 1.033 | **┃** | 1.033 | 1.050 |
| productcatalogservice | 0.635 | 0.718 | **┃** | 0.698 | 0.699 |
| cartservice | 0.559 | 0.501 | **┃** | 0.590 | 0.506 |
| currencyservice | 0.462 | 0.596 | **┃** | 0.577 | 0.578 |
| shippingservice | 0.166 | 0.173 | **┃** | 0.174 | 0.181 |
| adservice | 0.142 | 0.157 | **┃** | 0.531 | 0.210 |
| redis-cart | 0.231 | 0.224 | **┃** | 0.230 | 0.270 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and a threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. The postcheckout series changes on almost every 5 s tick, so each hold below gives the scorer's span counts, the min and max live cap, and the window, instead of a tick list. `postcart` and `emptycart` are no cap on every live read of every hold.

**rep1 on** (00:21:23–00:33:15). getproduct alternates a live cap of 166.757–166.8 (27 spans) with no cap (25 spans). getcart alternates 61.475–61.5 (27 spans) with no cap (25 spans). postcheckout has 144 live-cap spans from 10 to 99 and 9 no-cap spans.

**rep2 on** (00:56:20–01:08:15). getproduct, getcart, postcart, and emptycart are no cap for the whole window. postcheckout has 148 live-cap spans from 10 to 99 and 9 no-cap spans.

**rep3 on** (15:56:30–16:08:40). getproduct is no cap except one span at 275 (16:01:55). getcart is no cap except one span at 100 at the same time. postcheckout has 161 live-cap spans from 10 to 89.3 and 2 no-cap spans. postcart and emptycart are no cap for the whole window.

**rep4 on** (16:15:40–16:27:50). getproduct is no cap except five spans at 275. getcart is no cap except five spans at 100, on the same windows. postcheckout has 156 live-cap spans from 10 to 87.1 and 2 no-cap spans. postcart and emptycart are no cap for the whole window.

## 20. Per hold

**rep1 on.** Zero transitions. Checkout's file streak is 8 s with controller `high` 9, under the 20 s shed interval. Checkout is detector-hot at 54.7%. Retry delta into checkout is 20,066. `grpc_4` is 0. Getproduct goodput is 163.0 with fail 0.368, and getcart is 60.0 with fail 0.361. Postcheckout fail is 0.607 and P95 is 907 ms.

**rep2 on.** Zero transitions. Checkout's file streak is 8 s with controller `high` 9. Checkout is detector-hot at 53.6%. Retry delta into checkout is 19,120. `grpc_4` is 0. Getproduct goodput is 264.0 and getcart is 95.9, both with fail 0. Postcheckout fail is 0.584 and P95 is 983 ms.

**rep3 on.** Zero transitions. Checkout's file streak is 12 s with controller `high` 7. Cart has one tick above the shed bar and a retry delta of 4. Checkout is detector-hot at 51.2%. Retry delta into checkout is 15,511. `grpc_4` is 0. Getproduct goodput is 263.7 and getcart is 96.0, both with fail 0. Postcheckout fail is 0.577 and P95 is 950 ms.

**rep4 on.** Zero transitions. Checkout's file streak is 10 s with controller `high` 6. Checkout is detector-hot at 50.9%. Retry delta into checkout is 15,629. `grpc_4` is 0. Getproduct goodput is 263.8 and getcart is 95.7, both with fail 0. Postcheckout fail is 0.579 and P95 is 959 ms.

Across the four holds, RetryGuard logged zero sheds and zero climbs. Checkout stayed the detector-hot service, and the checkout retry delta on the two new holds is 15,511 and 15,629.

## 21. Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode section
- Earlier both-on columns in the same cell: [2026-10-11-s2-tuning-abc.md](2026-10-11-s2-tuning-abc.md)
- Run log: [2026-10-11-s2-rgtf1-rep3-rep4-run-log.md](../docs/superpowers/plans/2026-10-11-s2-rgtf1-rep3-rep4-run-log.md)
