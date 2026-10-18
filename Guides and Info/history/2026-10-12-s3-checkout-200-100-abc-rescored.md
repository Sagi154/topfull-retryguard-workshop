> Re-scored 2026-10-13 with the scorer that matches the controller's rejection (`grpc_4 + grpc_14` counted on adservice, currencyservice, productcatalogservice, recommendationservice). Only item 5 changed. Original: [2026-10-12-s3-checkout-200-100-abc.md](2026-10-12-s3-checkout-200-100-abc.md).

# S3 checkout 200 m then 100 m, both on (2026-10-12)

Two 600 s holds. RetryGuard is on and TopFull is on. Column order is 200 m, then 100 m. Scored with `python experiments/analysis_score.py --sep 1` on the two folders below. Follows [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). Run log: [2026-10-12-s3-checkout-200-100-rgtf1-run-log.md](../../docs/superpowers/plans/2026-10-12-s3-checkout-200-100-rgtf1-run-log.md).

## 1. Setup

- **Duration** 600 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **175 / 30 / 70 / 90 / 5**, `spawn_rate` 50.
- **CPU table.** Set B, with checkout at 200 m on the first hold and 100 m on the second. Frontend is pinned at 4 replicas. Every other service is 1 replica. `service_capacity.json` on each hold matches this table.

| Service | Per-pod quota (m) | Replicas |
| --- | ---: | ---: |
| frontend | 1150 | 4 |
| checkoutservice | 200, then 100 | 1 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 800 | 1 |
| cartservice | 800 | 1 |
| currencyservice | 770 | 1 |
| shippingservice | 770 | 1 |
| adservice | 1150 | 1 |
| paymentservice | 155 | 1 |
| emailservice | 120 | 1 |
| redis-cart | 540 | 1 |

- **Controllers.** RetryGuard is on. TopFull is on. Normal mode (no `burst_rpr`).
- **RetryGuard knobs.** Both START lines record `metric=edge_rpr rpr_threshold=0.50 rejection_threshold=0.20 reenable_rejection=0.15 climb_rpr_1_to_2=0.17 climb_rpr_2_to_3=0.33 climb_interval_seconds=15s sample_interval=1s interval_samples=30s edges=14 attempts_on=3`. The run manifest omits `climb_interval_seconds`. The START line records that 15 s default.
- **Cool-off** 120 s between the holds, from `run_scenario.py` exit.
- **Folders:** `experiments/results/results-trial/s3_ck200_rgtf1/` and `experiments/results/results-trial/s3_ck100_rgtf1/`.
- The Set B both-on holds at 300 m are the parent comparison and are not columns in this guide. That write-up is [2026-10-10-set-b-s3-checkout-analysis.md](2026-10-10-set-b-s3-checkout-analysis.md).

## 2. Index

Two rows, one column each. Column order in every table below follows this index. A bold bar separates the columns.

| Checkout | Column |
| --- | --- |
| 200 m, both on | s3_ck200_rgtf1 |
| 100 m, both on | s3_ck100_rgtf1 |

## 3. Gate

Both columns are the original holds. The run log marks both **PASS**.

Scorer gate numbers:

- s3_ck200_rgtf1: Locust total.csv 562 rows, mesh span 665 s, inbound gaps ≥ 1.5 s: 0 of 7315, retryguard.log present.
- s3_ck100_rgtf1: Locust total.csv 563 rows, mesh span 665 s, inbound gaps ≥ 1.5 s: 0 of 7315, retryguard.log present.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.15.

Burst mode was off.

Shed and 0→1 take **30 s** of row timestamps (`interval_samples=30`). Climb steps are 15 s because `climb_interval_seconds` is unset. Holds after 2026-10-08 use that 15 s climb. Both sheds record `elapsed_s=30`.

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

The file streak is seconds. **Bold** is a file streak of at least 30 seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. Checkout is bold on both holds. Cart is in the table because the 200 m hold has a retry delta; its ticks above the shed bar are 0. The other controlled edges have no tick above the shed bar and no retry delta.

### (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend → checkoutservice | **32 / 33 (31)** | **┃** | **30 / 39 (31)** |
| frontend → cartservice | 0 / 0 (0) | **┃** | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

### (a) Mean / median / max / volume rpr

| Edge | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend → checkoutservice | 0.107 / 0.000 / 4.60 / 0.080 | **┃** | 0.114 / 0.000 / 3.29 / 0.097 |
| frontend → cartservice | 0.001 / 0.000 / 0.33 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

### (a) Climb streaks, 1-attempt / 2-attempt

| Edge | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend → checkoutservice | — / — | **┃** | — / — |
| frontend → cartservice | — / — | **┃** | — / — |

Both climb cells are em dashes. Each shed went from 3 attempts to 0, so the 1-attempt cap and the 2-attempt cap were never in force.

## 6. Rejection, beside (a)

Longest streak / count of rejection above 0.20. This is not the shed signal. **Bold** is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. Checkout is the bold row.

### (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend (not controlled) | 0 / 0 | **┃** | 0 / 0 |
| checkoutservice | **35 / 282** | **┃** | **192 / 592** |
| recommendationservice | 0 / 0 | **┃** | 0 / 0 |
| paymentservice | 2 / 6 | **┃** | 3 / 75 |
| emailservice | 3 / 37 | **┃** | 1 / 5 |
| productcatalogservice | 0 / 0 | **┃** | 0 / 0 |
| cartservice | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 |
| shippingservice | 0 / 0 | **┃** | 0 / 0 |
| adservice | 1 / 1 | **┃** | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | **┃** | 0 / 0 |

The next table is the whole hold: longest streak / count of rejection samples under the re-enable bar 0.15. The OFF-window streak in §9 is only the samples while `frontend → checkoutservice` is at 0 attempts.

### (a) context: rejection streak under the re-enable bar / count

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend (not controlled) | 612 / 612 | **┃** | 613 / 613 |
| checkoutservice | 15 / 308 | **┃** | 7 / 11 |
| recommendationservice | 612 / 612 | **┃** | 613 / 613 |
| paymentservice | 564 / 601 | **┃** | 21 / 414 |
| emailservice | 34 / 506 | **┃** | 6 / 29 |
| productcatalogservice | 613 / 613 | **┃** | 613 / 613 |
| cartservice | 611 / 612 | **┃** | 613 / 613 |
| currencyservice | 613 / 613 | **┃** | 613 / 613 |
| shippingservice | 612 / 612 | **┃** | 613 / 613 |
| adservice | 610 / 610 | **┃** | 612 / 612 |
| redis-cart (not controlled) | 0 / 0 | **┃** | 0 / 0 |

### (a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| recommendationservice | 0 / 0 | **┃** | 0 / 0 |
| productcatalogservice | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 |
| adservice | 1 / 1 | **┃** | 0 / 0 |

### (a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| recommendationservice | 612 / 612 | **┃** | 613 / 613 |
| productcatalogservice | 613 / 613 | **┃** | 613 / 613 |
| currencyservice | 613 / 613 | **┃** | 613 / 613 |
| adservice | 610 / 610 | **┃** | 612 / 612 |


## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as `ticks/rows (share%)`. **Bold** is a share of at least 0.5. Checkout is the bold row on both holds.

### (b) Detector overloaded fraction

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| checkoutservice | **598/715 (83.6%)** | **┃** | **594/716 (83.0%)** |
| recommendationservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| paymentservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| emailservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| productcatalogservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| cartservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| currencyservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| shippingservice | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |
| adservice | 1/715 (0.1%) | **┃** | 0/716 (0.0%) |
| redis-cart | 0/715 (0.0%) | **┃** | 0/716 (0.0%) |

## 8. (c) Retry volume

Outbound retry delta by target, then inbound resets for all 11 services.

### (c) Outbound retry delta by target

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| checkoutservice | 594 | **┃** | 576 |
| cartservice | 3 | **┃** | 0 |

### (c) Inbound resets

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 21 | **┃** | 9 |
| checkoutservice | 2,495 | **┃** | 4,093 |
| recommendationservice | 0 | **┃** | 0 |
| paymentservice | 49 | **┃** | 176 |
| emailservice | 155 | **┃** | 5 |
| productcatalogservice | 3 | **┃** | 0 |
| cartservice | 97 | **┃** | 58 |
| currencyservice | 0 | **┃** | 0 |
| shippingservice | 45 | **┃** | 128 |
| adservice | 1 | **┃** | 0 |
| redis-cart | 0 | **┃** | 0 |

gRPC counted in the rejection rate and in the retry policy. Cell is grpc_4 / grpc_14.

### grpc_4 / grpc_14

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| recommendationservice | 0 / 0 | **┃** | 0 / 0 |
| productcatalogservice | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 |
| adservice | 2 / 0 | **┃** | 0 / 0 |

## 9. RetryGuard toggles

Two parts. Part 1 is the scorer's log for each hold. Part 2 summarizes it per callee.

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name. `From` is the attempt count before the step. `Value` is the rpr on a shed line and the rejection on a re-enable line.

### Part 1: per hold

### s3_ck200_rgtf1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T20:08:17Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.00 |

### s3_ck100_rgtf1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T20:26:13Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.56 |

### Part 2: per callee

Checkout is the only callee that sheds or re-enables. Payment, email, catalog, cart, currency, shipping, ad, and recommendations have no `ON→OFF` and no `OFF→ON` on either hold.

Counts, shed rpr, and times come from the Part 1 timestamp log. Attempts after re-enable are the attempt count that edge holds at EXIT. Time OFF runs from the shed timestamp to the EXIT line, because the edge is still at 0. OFF rejection is minimum / median, three decimals, over `OBSERVE` `metric=rejection` samples for checkoutservice with `state=OFF` and timestamps after the shed and at or before EXIT. The under-bar streak is the longest run of those samples strictly below 0.15. The first-shed row is omitted.

#### checkoutservice

| | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| ON→OFF / OFF→ON | 1 / 0 | **┃** | 1 / 0 |
| Shed rpr | 2.00 | **┃** | 1.56 |
| Attempts after re-enable | 0 | **┃** | 0 |
| Time OFF (s) | 567 (to EXIT) | **┃** | 566 (to EXIT) |
| OFF rejection min / median | 0.000 / 0.133 | **┃** | 0.000 / 0.636 |
| Streak under the bar | 7 | **┃** | 2 |

Both holds shed `frontend → checkoutservice` once, from 3 attempts, and stayed at 0 through EXIT. Time OFF is 567 s on the 200 m hold (20:08:17Z to 20:17:44Z) and 566 s on the 100 m hold (20:26:13Z to 20:35:39Z). Attempts at EXIT are 0. The OFF window has 556 samples on the 200 m hold and 551 on the 100 m hold. The longest under-bar streak is 7 samples and 2 samples. A streak of 30 samples is the 0→1 step (`interval_samples` 30).

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

### Locust goodput

| API | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| getproduct | 168.1 | **┃** | 167.8 |
| postcheckout | 6.8 | **┃** | 0.1 |
| getcart | 67.2 | **┃** | 67.2 |
| postcart | 86.4 | **┃** | 86.4 |
| emptycart | 4.8 | **┃** | 4.8 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

### Locust fail rate

| API | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| getproduct | 0.000 | **┃** | 0.000 |
| postcheckout | 0.753 | **┃** | 0.987 |
| getcart | 0.000 | **┃** | 0.000 |
| postcart | 0.000 | **┃** | 0.000 |
| emptycart | 0.000 | **┃** | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

### Locust P95

| API | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| getproduct | 75 | **┃** | 89 |
| postcheckout | 594 | **┃** | 651 |
| getcart | 53 | **┃** | 75 |
| postcart | 59 | **┃** | 60 |
| emptycart | 13 | **┃** | 12 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.

### Inbound arrival rate

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 311.2 | **┃** | 309.2 |
| checkoutservice | 12.1 | **┃** | 9.8 |
| recommendationservice | 227.3 | **┃** | 225.2 |
| paymentservice | 11.1 | **┃** | 3.6 |
| emailservice | 7.4 | **┃** | 0.1 |
| productcatalogservice | 1597.5 | **┃** | 1585.2 |
| cartservice | 321.4 | **┃** | 309.9 |
| currencyservice | 450.4 | **┃** | 440.3 |
| shippingservice | 84.2 | **┃** | 71.2 |
| adservice | 154.3 | **┃** | 154.4 |
| redis-cart | 0.0 | **┃** | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

### Inbound sojourn (ms)

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 53 | **┃** | 60 |
| checkoutservice | 371 | **┃** | 482 |
| recommendationservice | 6 | **┃** | 9 |
| paymentservice | 3 | **┃** | 2 |
| emailservice | 6 | **┃** | 4 |
| productcatalogservice | 1 | **┃** | 1 |
| cartservice | 2 | **┃** | 2 |
| currencyservice | 1 | **┃** | 2 |
| shippingservice | 0 | **┃** | 1 |
| adservice | 1 | **┃** | 1 |
| redis-cart | — | **┃** | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.

### Share of inbound requests above 500 ms

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 0.019 | **┃** | 0.028 |
| checkoutservice | 0.276 | **┃** | 0.955 |
| recommendationservice | 0.000 | **┃** | 0.000 |
| paymentservice | 0.000 | **┃** | 0.000 |
| emailservice | 0.000 | **┃** | 0.000 |
| productcatalogservice | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | **┃** | 0.000 |
| currencyservice | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | **┃** | 0.000 |
| adservice | 0.000 | **┃** | 0.000 |
| redis-cart | — | **┃** | — |

## 16. CPU

CPU cells are per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum usage across replicas.

### CPU quota / replicas / mean / max

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 1150 / 4 / 1215 / 1591 | **┃** | 1150 / 4 / 1152 / 1524 |
| checkoutservice | 200 / 1 / 158 / 199 | **┃** | 100 / 1 / 67 / 98 |
| recommendationservice | 1150 / 1 / 399 / 525 | **┃** | 1150 / 1 / 409 / 549 |
| paymentservice | 155 / 1 / 18 / 30 | **┃** | 155 / 1 / 8 / 14 |
| emailservice | 120 / 1 / 23 / 31 | **┃** | 120 / 1 / 10 / 13 |
| productcatalogservice | 800 / 1 / 460 / 595 | **┃** | 800 / 1 / 416 / 548 |
| cartservice | 800 / 1 / 388 / 529 | **┃** | 800 / 1 / 371 / 653 |
| currencyservice | 770 / 1 / 259 / 348 | **┃** | 770 / 1 / 246 / 332 |
| shippingservice | 770 / 1 / 57 / 73 | **┃** | 770 / 1 / 50 / 66 |
| adservice | 1150 / 1 / 139 / 413 | **┃** | 1150 / 1 / 117 / 151 |
| redis-cart | 540 / 1 / 36 / 48 | **┃** | 540 / 1 / 34 / 46 |

Frontend mean and max sit above the 1150 m per-pod quota on both holds. Those cells sum `cpu_millicores` across the 4 replicas.

### CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 0.26 / 0.35 | **┃** | 0.25 / 0.33 |
| checkoutservice | 0.79 / 0.99 | **┃** | 0.67 / 0.98 |
| recommendationservice | 0.35 / 0.46 | **┃** | 0.36 / 0.48 |
| paymentservice | 0.11 / 0.19 | **┃** | 0.05 / 0.09 |
| emailservice | 0.19 / 0.26 | **┃** | 0.08 / 0.11 |
| productcatalogservice | 0.57 / 0.74 | **┃** | 0.52 / 0.69 |
| cartservice | 0.48 / 0.66 | **┃** | 0.46 / 0.82 |
| currencyservice | 0.34 / 0.45 | **┃** | 0.32 / 0.43 |
| shippingservice | 0.07 / 0.09 | **┃** | 0.07 / 0.09 |
| adservice | 0.12 / 0.36 | **┃** | 0.10 / 0.13 |
| redis-cart | 0.07 / 0.09 | **┃** | 0.06 / 0.09 |

## 17. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

### Detector max utilization

| Service | s3_ck200_rgtf1 | **┃** | s3_ck100_rgtf1 |
| --- | ---: | :---: | ---: |
| frontend | 0.431 | **┃** | 0.348 |
| checkoutservice | 1.075 | **┃** | 1.100 |
| recommendationservice | 0.488 | **┃** | 0.505 |
| paymentservice | 0.439 | **┃** | 0.400 |
| emailservice | 0.542 | **┃** | 0.392 |
| productcatalogservice | 0.784 | **┃** | 0.723 |
| cartservice | 0.731 | **┃** | 0.836 |
| currencyservice | 0.534 | **┃** | 0.475 |
| shippingservice | 0.134 | **┃** | 0.142 |
| adservice | 0.857 | **┃** | 0.209 |
| redis-cart | 0.115 | **┃** | 0.117 |

## 18. TopFull live caps

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

The 200 m `postcheckout` series is the scorer's collapsed spans. On both holds, every live read for getproduct, getcart, postcart, and emptycart is no cap.

### s3_ck200_rgtf1

| API | Live caps |
| --- | --- |
| getproduct | no cap 20:05:50–20:17:40 |
| postcheckout | no cap 20:05:50–20:07:46; 10 20:07:47–20:08:20; 16.5 at 20:08:25; 10.0336 at 20:08:27; 12.4 at 20:08:30; 14.0784 at 20:08:32; 10 at 20:08:35; 16 at 20:08:40; 10.1 at 20:08:45; 12.9 at 20:08:50; 12.1 at 20:08:55; 12.9 at 20:09:00; 12.2078 at 20:09:04; 12.2 at 20:09:05; 13.8721 at 20:09:09; 13.9 at 20:09:10; 10.2 at 20:09:15; 14.8 at 20:09:20; 10.7244 at 20:09:23; 10 at 20:09:25; 14.1 at 20:09:30; 11.1741 at 20:09:32; 10 at 20:09:35; 15.7 at 20:09:40; 10.1 at 20:09:45; 10 at 20:09:50; 13.1 at 20:09:55; 13.2 at 20:10:00; 11.9 at 20:10:05; 14.7 at 20:10:10; 10.5257 at 20:10:14; 10.5 at 20:10:15; 13.6 at 20:10:20; 10 at 20:10:25; 11.8417 at 20:10:27; 14.9 at 20:10:30; 10 at 20:10:35; 11.0454 at 20:10:36; 14.9 at 20:10:40; 10 at 20:10:45; 13.4 at 20:10:50; 12.3 at 20:10:55; 14.4 at 20:11:00; 12.8 at 20:11:05; 12.3 at 20:11:10; 10 at 20:11:15; 14.7 at 20:11:20; 10.5 at 20:11:25; 11.1 20:11:30–20:11:35; 12.5175 at 20:11:38; 15.2 at 20:11:40; 10 at 20:11:45; 11.5636 at 20:11:47; 15.7 at 20:11:50; 10 at 20:11:55; 14.1 at 20:12:00; 11.4 at 20:12:05; 14.4947 at 20:12:09; 14.5 at 20:12:10; 10 at 20:12:15; 14.5 at 20:12:20; 10 at 20:12:25; 10.5437 at 20:12:29; 10.5 at 20:12:30; 13.2 at 20:12:35; 15.1 at 20:12:40; 10 at 20:12:45; 13.9 at 20:12:50; 10 at 20:12:55; 14 at 20:13:00; 10 at 20:13:05; 10.9903 at 20:13:06; 10 at 20:13:10; 15.153 at 20:13:14; 15.2 at 20:13:15; 13.6796 at 20:13:18; 14.8 at 20:13:20; 12.6 at 20:13:25; 14.2 at 20:13:30; 10 20:13:34–20:13:35; 15.5 at 20:13:40; 10.6 at 20:13:45; 14.1 at 20:13:50; 13.1 at 20:13:55; 12.2 at 20:14:00; 15.2 at 20:14:05; 14.2 at 20:14:10; 12.4 at 20:14:15; 13.4552 at 20:14:19; 13.5 at 20:14:20; 10 20:14:23–20:14:25; 13.6 at 20:14:30; 14.2 at 20:14:35; 10.5966 at 20:14:36; 13.7 at 20:14:40; 10 at 20:14:45; 14.5 at 20:14:50; 10 at 20:14:55; 12.8923 at 20:14:57; 17 at 20:15:00; 10 at 20:15:05; 15.9 at 20:15:10; 10.8 at 20:15:15; 13.1593 at 20:15:18; 13.7 at 20:15:20; 12.5 at 20:15:25; 12.4 at 20:15:30; 10.1 at 20:15:35; 14 at 20:15:40; 14.8 at 20:15:45; 15.2 at 20:15:50; 10 at 20:15:55; 14.6984 at 20:15:58; 14.9 at 20:16:00; 10.8497 at 20:16:02; 14.9 at 20:16:05; 10 at 20:16:10; 16.6 at 20:16:15; 10.4 at 20:16:20; 10.1 at 20:16:25; 13.9 at 20:16:30; 13.1 at 20:16:35; 13.9 at 20:16:40; 10 at 20:16:45; 16.4 at 20:16:50; 10.3 at 20:16:55; 10 at 20:16:56; 14.1 at 20:17:00; 10 at 20:17:05; 13.6 at 20:17:10; 12.9 at 20:17:15; 10 at 20:17:20; 13.8333 at 20:17:21; 14.9 at 20:17:25; 13 at 20:17:30; 11.5 at 20:17:35; 14.2 at 20:17:40 |
| getcart | no cap 20:05:50–20:17:40 |
| postcart | no cap 20:05:50–20:17:40 |
| emptycart | no cap 20:05:50–20:17:40 |

### s3_ck100_rgtf1

| API | Live caps |
| --- | --- |
| getproduct | no cap 20:23:45–20:35:35 |
| postcheckout | no cap 20:23:45–20:25:30; 10 20:25:35–20:35:35 |
| getcart | no cap 20:23:45–20:35:35 |
| postcart | no cap 20:23:45–20:35:35 |
| emptycart | no cap 20:23:45–20:35:35 |

## 19. Per hold

**s3_ck200_rgtf1.** `frontend → checkoutservice` shed once at rpr 2.00, from 3 attempts, and stayed at 0. The climb cells are em dashes. Retry volume is 594 into checkoutservice and 3 into cartservice. `grpc_4 / grpc_14` on adservice is 2 / 0. The other three read callees are 0 / 0. Detector-hot: checkoutservice 598/715 (83.6%).

**s3_ck100_rgtf1.** `frontend → checkoutservice` shed once at rpr 1.56, from 3 attempts, and stayed at 0. The climb cells are em dashes. Retry volume is 576 into checkoutservice and 0 into cartservice. `grpc_4 / grpc_14` is 0 / 0 on all four read callees. Detector-hot: checkoutservice 594/716 (83.0%).

## 20. Related links

- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md), Edge mode and Burst mode sections
- [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md)
- Parent comparison, 300 m, not a column here: [2026-10-10-set-b-s3-checkout-analysis.md](2026-10-10-set-b-s3-checkout-analysis.md)
- Run log: [2026-10-12-s3-checkout-200-100-rgtf1-run-log.md](../../docs/superpowers/plans/2026-10-12-s3-checkout-200-100-rgtf1-run-log.md)
