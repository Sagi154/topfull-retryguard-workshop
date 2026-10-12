# S2 normal mode, RetryGuard on, TopFull on (2026-10-12)

Three 600 s holds. RetryGuard is on and TopFull is on. Normal mode: the START line has no `burst_rpr`. Scored with `experiments/analysis_score.py` and no `--sep`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Run log: [2026-10-12-s2-normal-rgtf1-x3-run-log.md](../docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md).

## 1. Setup

- **Duration** 600 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. Locked S2 mix, Paper-C1.
- **CPU and replica pin** (`service_capacity.json` on all three holds):

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

  Frontend replica count is 4 on every `resource_usage.csv` sample, and every other service is 1. That is the Paper-C1 pin: sidecar `proxyCPU=90m` with `proxyCPULimit` unset while frontend is held at 4, and catalog HPA max 1.
- **Controllers.** RetryGuard is on. TopFull is on.
- **RetryGuard knobs.** `retry_metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.4`, climb `0.16/0.32` with `climb_interval_seconds=10`, `reenable_rejection=0.25`. Normal mode omits `burst_rpr`.
- **Cool-off** 120 s between holds, from `run_scenario.py` exit.
- **Folders:** `experiments/results/campaign_48/S2_sustained_overload/`, the three `study7_s2_normal_rgtf1_rep*` names in §2. Configs: `experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml`, `16_s2_normal_rgtf1_rep2.yaml`, `17_s2_normal_rgtf1_rep3.yaml`. Each manifest has `run_number` 1; the `log_folder` name is the slot.

## 2. Index

One setup. Column order in every table below follows this row. No bold bar.

| | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | --- | --- | --- |
| Arm | normal, RetryGuard on, TopFull on | normal, RetryGuard on, TopFull on | normal, RetryGuard on, TopFull on |

## 3. Gate

**Pass on all three.** The run log records PASS for each hold. No `_r2` folder replaced a hold.

Scorer gate numbers:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| `study7_s2_normal_rgtf1_rep1` | 560 | 665 | 0 of 7315 | present |
| `study7_s2_normal_rgtf1_rep2` | 559 | 664 | 968 of 6336 | present |
| `study7_s2_normal_rgtf1_rep3` | 559 | 665 | 1155 of 6160 | present |

`service_capacity.json` matches the pin in §1 on every hold, for every service. `resource_usage.csv` shows frontend at 4 replicas on every sample (150/150, 149/149, 149/149). No service has a zero-replica sample. The scorer printed no replica-change line.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst mode was off. The START line on every hold is `metric=edge_rpr rpr_threshold=0.40 rejection_threshold=0.20 reenable_rejection=0.25 climb_rpr_1_to_2=0.16 climb_rpr_2_to_3=0.32 climb_interval_seconds=10s sample_interval=1s interval_samples=20s edges=14 attempts_on=3`, with no `burst_rpr=`.

Shed and 0→1 take **20 s** of row timestamps (`interval_samples=20`). Climbs 1→2 and 2→3 take **10 s** on these holds (`climb_interval_seconds=10` on the START line).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

Three edges have a tick above the shed bar or a retry delta: `frontend → checkoutservice`, `frontend → recommendationservice`, and `frontend → cartservice`. Cart's retry delta is 4 on rep1 and 0 on rep2 and rep3, and it has no tick above 0.40. Every other controlled edge has no tick above 0.40 and a retry delta of 0, so it is omitted here. The file streak is in seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. No file streak reaches 30 s, so nothing in these cells is bold.

### (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend → checkoutservice | 22 / 173 (19) | 9 / 163 (8) | 8 / 165 (9) |
| frontend → recommendationservice | 22 / 23 (19) | 0 / 0 (0) | 3 / 3 (3) |
| frontend → cartservice | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

### (a) Mean / median / max / volume rpr

| Edge | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend → checkoutservice | 0.656 / 0.000 / 7.67 / 0.587 | 0.693 / 0.000 / 5.33 / 0.631 | 0.749 / 0.000 / 8.57 / 0.652 |
| frontend → recommendationservice | 0.060 / 0.000 / 3.01 / 0.043 | 0.000 / 0.000 / 0.00 / 0.000 | 0.006 / 0.000 / 1.36 / 0.006 |
| frontend → cartservice | 0.001 / 0.000 / 0.31 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

### (a) Climb streaks, 1-attempt / 2-attempt

| Edge | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend → checkoutservice | 11 / 11 | — / — | — / — |
| frontend → recommendationservice | 11 / 11 | — / — | — / — |
| frontend → cartservice | — / — | — / — | — / — |

### 5a. Burst

Burst mode was off. The START line has no `burst_rpr=`.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count. **Bold** in the 0.20 table would be a streak of at least 30 on a controlled service. No controlled service reaches 30, so nothing in that table is bold. Frontend and redis-cart stay plain. The re-enable bar on these holds is 0.25.

### (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend (not controlled) | 16 / 22 | 1 / 1 | 0 / 0 |
| checkoutservice | 24 / 171 | 8 / 155 | 8 / 159 |
| recommendationservice | 3 / 14 | 0 / 0 | 0 / 0 |
| paymentservice | 1 / 3 | 0 / 0 | 1 / 2 |
| emailservice | 6 / 69 | 4 / 69 | 4 / 70 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 |

### (a) context: rejection streak under the re-enable bar / count

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend (not controlled) | 513 / 594 | 525 / 525 | 508 / 508 |
| checkoutservice | 51 / 447 | 46 / 373 | 49 / 350 |
| recommendationservice | 530 / 611 | 525 / 525 | 508 / 508 |
| paymentservice | 339 / 611 | 524 / 524 | 346 / 505 |
| emailservice | 53 / 517 | 45 / 445 | 50 / 430 |
| productcatalogservice | 613 / 613 | 525 / 525 | 507 / 507 |
| cartservice | 613 / 613 | 525 / 525 | 508 / 508 |
| currencyservice | 612 / 612 | 524 / 524 | 508 / 508 |
| shippingservice | 612 / 612 | 524 / 524 | 508 / 508 |
| adservice | 611 / 611 | 524 / 524 | 507 / 507 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 |

gRPC counted in the rejection rate and in the retry policy. Cell is grpc_4 / grpc_14.

### grpc_4 / grpc_14

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| recommendationservice | 10,045 / 0 | 0 / 0 | 1,158 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as ticks/rows (share%). **Bold** is a share of at least 0.5.

### (b) Detector overloaded fraction

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |
| checkoutservice | **387/717 (54.0%)** | **377/714 (52.8%)** | **384/715 (53.7%)** |
| recommendationservice | 22/717 (3.1%) | 0/714 (0.0%) | 3/715 (0.4%) |
| paymentservice | 4/717 (0.6%) | 0/714 (0.0%) | 0/715 (0.0%) |
| emailservice | 153/717 (21.3%) | 131/714 (18.3%) | 116/715 (16.2%) |
| productcatalogservice | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |
| cartservice | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |
| currencyservice | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |
| shippingservice | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |
| adservice | 1/717 (0.1%) | 0/714 (0.0%) | 0/715 (0.0%) |
| redis-cart | 0/717 (0.0%) | 0/714 (0.0%) | 0/715 (0.0%) |

## 8. (c) Retry volume

Outbound retry delta by target. Inbound resets for all 11 services. The same `grpc_4 / grpc_14` pair in §6 is what the retry policy counts on the four read callees.

### (c) Outbound retry delta by target

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| checkoutservice | 16,617 | 17,378 | 17,441 |
| recommendationservice | 10,680 | 0 | 1,477 |
| cartservice | 4 | 0 | 0 |

### (c) Inbound resets

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 87 | 47 | 56 |
| checkoutservice | 12,871 | 12,930 | 13,169 |
| recommendationservice | 3,607 | 1 | 463 |
| paymentservice | 683 | 478 | 803 |
| emailservice | 1,042 | 1,167 | 1,058 |
| productcatalogservice | 3 | 3 | 2 |
| cartservice | 717 | 812 | 745 |
| currencyservice | 0 | 1 | 0 |
| shippingservice | 938 | 986 | 1,043 |
| adservice | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 |

## 9. RetryGuard toggles

Two parts. Part 1 is the scorer's log for each hold. Part 2 summarizes it per callee.

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name. `From` is the attempt count before the step. `Value` is the rpr on a shed or climb line and the rejection on a re-enable line.

### Part 1: per hold

### study7_s2_normal_rgtf1_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 1 | 1 |
| recommendationservice | 0 | 1 | 0 | 0 |
| frontend → checkoutservice | 1 | 0 | 1 | 1 |
| checkoutservice | 0 | 1 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T08:40:58Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.25 |
| 2026-10-12T08:41:22Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T08:41:24Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.02 |
| 2026-10-12T08:41:34Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T08:41:45Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T08:41:49Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T08:42:00Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T08:42:11Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |

`study7_s2_normal_rgtf1_rep2` and `study7_s2_normal_rgtf1_rep3` have no transition lines.

### Part 2: per callee

Checkout and recommendations are the only callees that shed or re-enable. Payment, email, catalog, cart, currency, shipping, and ad have no `ON→OFF` and no `OFF→ON` on any hold.

Counts, shed rpr, and times come from the §9 timestamp log. Attempts after re-enable are the attempt count that edge holds at EXIT. Time OFF runs from the shed timestamp to the matching `OFF→ON`. OFF rejection is minimum / median, three decimals, over `OBSERVE` `metric=rejection` samples for that callee with timestamps after the shed and at or before the `OFF→ON`. The under-bar streak is the longest run of those samples strictly below 0.25. An em dash means that edge never went to 0 on that hold. Burst mode is off, so this table has no first-shed row.

#### checkoutservice

| | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 1 | 0 / 0 | 0 / 0 |
| Shed rpr | 2.02 | — | — |
| Attempts after re-enable | 3 | — | — |
| Time OFF (s) | 25 | — | — |
| OFF rejection min / median | 0.000 / 0.000 | — | — |
| Streak under the bar | 21 | — | — |

Rep1 re-enabled and climbed 1→2→3, so the edge held 3 attempts at EXIT. Rep2 and rep3 never went to 0. The longest under-bar streak is 21, on rep1.

#### recommendationservice

| | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 1 | 0 / 0 | 0 / 0 |
| Shed rpr | 2.25 | — | — |
| Attempts after re-enable | 3 | — | — |
| Time OFF (s) | 24 | — | — |
| OFF rejection min / median | 0.000 / 0.000 | — | — |
| Streak under the bar | 18 | — | — |

Rep1 re-enabled and climbed 1→2→3, so the edge held 3 attempts at EXIT. Rep2 and rep3 never went to 0. The longest under-bar streak is 18, on rep1.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

### Locust goodput

| API | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| getproduct | 255.9 | 264.1 | 263.0 |
| postcheckout | 32.1 | 31.0 | 30.0 |
| getcart | 93.1 | 96.0 | 95.5 |
| postcart | 86.4 | 86.4 | 86.3 |
| emptycart | 4.8 | 4.8 | 4.8 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

### Locust fail rate

| API | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| getproduct | 0.024 | 0.000 | 0.003 |
| postcheckout | 0.569 | 0.584 | 0.591 |
| getcart | 0.024 | 0.000 | 0.003 |
| postcart | 0.000 | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

### Locust P95

| API | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| getproduct | 329 | 244 | 269 |
| postcheckout | 997 | 939 | 942 |
| getcart | 329 | 268 | 271 |
| postcart | 71 | 68 | 69 |
| emptycart | 16 | 29 | 20 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

### Inbound arrival rate

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 453.7 | 457.1 | 454.8 |
| checkoutservice | 67.6 | 67.7 | 66.5 |
| recommendationservice | 385.8 | 373.0 | 373.0 |
| paymentservice | 65.2 | 66.0 | 64.2 |
| emailservice | 35.2 | 34.6 | 32.7 |
| productcatalogservice | 2518.2 | 2560.8 | 2546.4 |
| cartservice | 518.8 | 524.8 | 519.4 |
| currencyservice | 751.2 | 761.3 | 756.7 |
| shippingservice | 207.4 | 211.3 | 206.1 |
| adservice | 236.5 | 243.0 | 242.2 |
| redis-cart | 0.0 | 0.0 | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

### Inbound sojourn (ms)

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 202 | 167 | 176 |
| checkoutservice | 303 | 317 | 307 |
| recommendationservice | 91 | 57 | 67 |
| paymentservice | 6 | 5 | 5 |
| emailservice | 37 | 37 | 31 |
| productcatalogservice | 2 | 2 | 2 |
| cartservice | 3 | 3 | 3 |
| currencyservice | 3 | 3 | 3 |
| shippingservice | 1 | 1 | 1 |
| adservice | 1 | 1 | 1 |
| redis-cart | — | — | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.

### Share of inbound requests above 500 ms

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 0.068 | 0.039 | 0.044 |
| checkoutservice | 0.347 | 0.374 | 0.376 |
| recommendationservice | 0.043 | 0.000 | 0.006 |
| paymentservice | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 |
| redis-cart | — | — | — |

## 16. CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota.

### CPU quota / replicas / mean / max

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 1150 / 4 / 1199 / 1619 | 1150 / 4 / 1195 / 1587 | 1150 / 4 / 1219 / 1631 |
| checkoutservice | 800 / 1 / 513 / 798 | 800 / 1 / 503 / 797 | 800 / 1 / 507 / 797 |
| recommendationservice | 1150 / 1 / 593 / 1071 | 1150 / 1 / 566 / 788 | 1150 / 1 / 591 / 908 |
| paymentservice | 155 / 1 / 45 / 107 | 155 / 1 / 41 / 77 | 155 / 1 / 41 / 77 |
| emailservice | 120 / 1 / 51 / 112 | 120 / 1 / 48 / 109 | 120 / 1 / 48 / 102 |
| productcatalogservice | 800 / 1 / 407 / 545 | 800 / 1 / 413 / 544 | 800 / 1 / 413 / 544 |
| cartservice | 800 / 1 / 283 / 391 | 800 / 1 / 281 / 463 | 800 / 1 / 303 / 492 |
| currencyservice | 770 / 1 / 313 / 439 | 770 / 1 / 303 / 417 | 770 / 1 / 316 / 439 |
| shippingservice | 770 / 1 / 77 / 127 | 770 / 1 / 75 / 111 | 770 / 1 / 77 / 116 |
| adservice | 1150 / 1 / 150 / 417 | 1150 / 1 / 129 / 171 | 1150 / 1 / 134 / 183 |
| redis-cart | 540 / 1 / 33 / 44 | 540 / 1 / 32 / 42 | 540 / 1 / 33 / 44 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out of the fraction. No sample has replica count 0.

### CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 0.26 / 0.35 | 0.26 / 0.34 | 0.26 / 0.35 |
| checkoutservice | 0.64 / 1.00 | 0.63 / 1.00 | 0.63 / 1.00 |
| recommendationservice | 0.52 / 0.93 | 0.49 / 0.69 | 0.51 / 0.79 |
| paymentservice | 0.29 / 0.69 | 0.27 / 0.50 | 0.27 / 0.50 |
| emailservice | 0.42 / 0.93 | 0.40 / 0.91 | 0.40 / 0.85 |
| productcatalogservice | 0.51 / 0.68 | 0.52 / 0.68 | 0.52 / 0.68 |
| cartservice | 0.35 / 0.49 | 0.35 / 0.58 | 0.38 / 0.61 |
| currencyservice | 0.41 / 0.57 | 0.39 / 0.54 | 0.41 / 0.57 |
| shippingservice | 0.10 / 0.16 | 0.10 / 0.14 | 0.10 / 0.15 |
| adservice | 0.13 / 0.36 | 0.11 / 0.15 | 0.12 / 0.16 |
| redis-cart | 0.06 / 0.08 | 0.06 / 0.08 | 0.06 / 0.08 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

### Detector max utilization

| Service | study7_s2_normal_rgtf1_rep1 | study7_s2_normal_rgtf1_rep2 | study7_s2_normal_rgtf1_rep3 |
| --- | ---: | ---: | ---: |
| frontend | 0.369 | 0.373 | 0.383 |
| checkoutservice | 1.042 | 1.032 | 1.045 |
| recommendationservice | 0.955 | 0.730 | 0.898 |
| paymentservice | 0.948 | 0.710 | 0.742 |
| emailservice | 1.025 | 1.050 | 1.058 |
| productcatalogservice | 0.728 | 0.725 | 0.708 |
| cartservice | 0.547 | 0.610 | 0.646 |
| currencyservice | 0.631 | 0.601 | 0.613 |
| shippingservice | 0.195 | 0.191 | 0.188 |
| adservice | 0.923 | 0.185 | 0.208 |
| redis-cart | 0.085 | 0.087 | 0.089 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. The postcheckout series is the scorer's collapsed spans. `postcart` and `emptycart` are no cap on every live read of every hold.

### study7_s2_normal_rgtf1_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:30:25–08:40:35; 238 at 08:42:20 |
| postcheckout | 59.9423 at 08:30:24; no cap at 08:30:25; 59.9423 08:30:26–08:30:29; no cap at 08:30:30; 59.9423 08:30:31–08:30:34; no cap at 08:30:35; 59.9423 08:30:36–08:30:39; no cap at 08:30:40; 59.9423 08:30:41–08:30:44; no cap at 08:30:45; 59.9423 08:30:46–08:30:49; no cap at 08:30:50; 59.9423 08:30:51–08:30:54; no cap at 08:30:55; 59.9423 08:30:56–08:30:59; no cap at 08:31:00; 59.9423 08:31:01–08:31:04; no cap at 08:31:05; 59.9423 08:31:06–08:31:09; no cap at 08:31:10; 59.9423 08:31:11–08:31:14; no cap at 08:31:15; 59.9423 08:31:16–08:31:19; no cap at 08:31:20; 59.9423 08:31:21–08:31:24; no cap at 08:31:25; 59.9423 08:31:26–08:31:29; no cap at 08:31:30; 59.9423 08:31:31–08:31:34; no cap at 08:31:35; 59.9423 08:31:36–08:31:39; no cap at 08:31:40; 59.9423 08:31:41–08:31:44; no cap at 08:31:45; 59.9423 08:31:46–08:31:49; no cap at 08:31:50; 59.9423 08:31:51–08:31:54; no cap at 08:31:55; 59.9423 08:31:56–08:31:59; no cap at 08:32:00; 59.9423 08:32:01–08:32:04; no cap at 08:32:05; 59.9423 08:32:06–08:32:09; no cap at 08:32:10; 59.9423 08:32:11–08:32:14; no cap at 08:32:15; 59.9423 08:32:16–08:32:19; no cap at 08:32:20; 59.9423 08:32:21–08:32:24; no cap at 08:32:25; 59.9423 08:32:26–08:32:29; 36 at 08:32:30; 48.4 at 08:32:35; 59.4 at 08:32:40; 61 at 08:32:45; 79.2 at 08:32:50; 77 at 08:32:52; no cap 08:32:55–08:33:00; 17.2 at 08:33:05; 19 at 08:33:10; 61.8 at 08:33:15; 60.1 at 08:33:20; 36.935 at 08:33:21; 14.2 at 08:33:25; 26.6 at 08:33:30; 75.2 at 08:33:35; 90 at 08:33:40; 13.1882 at 08:33:44; 13.2 at 08:33:45; 19.9 at 08:33:50; 49.7091 at 08:33:53; 66.3 at 08:33:55; 98.5616 at 08:33:57; 90 08:33:59–08:34:00; 13.4 at 08:34:05; 14.0703 at 08:34:08; 19.5 at 08:34:10; 67.2 at 08:34:15; 86.9184 at 08:34:16; 90.2 at 08:34:20; 26.3 at 08:34:25; 14.1001 at 08:34:29; 14.1 at 08:34:30; 47.1 at 08:34:35; 63.2 at 08:34:40; 76.4994 at 08:34:42; 97.8 at 08:34:45; 52.8636 at 08:34:49; 52.9 at 08:34:50; 10 at 08:34:55; 14.0457 at 08:34:57; 26.1 at 08:35:00; 64.5 at 08:35:05; no cap at 08:35:10; 18.9617 at 08:35:14; 19 at 08:35:15; 14.2244 at 08:35:18; 19.6 at 08:35:20; 62.6 at 08:35:25; 81.824 at 08:35:26; 90.6 at 08:35:30; 21.4 at 08:35:35; 19.7 at 08:35:40; 50.2 at 08:35:45; 99 at 08:35:50; 15.0805 at 08:35:54; 15.1 at 08:35:55; 19.5 at 08:36:00; 36.3556 at 08:36:02; 49.4 at 08:36:05; 92.3 at 08:36:10; 28.5 at 08:36:15; 10 at 08:36:20; 35.6 at 08:36:25; 75.1 at 08:36:30; 98.2507 at 08:36:32; no cap at 08:36:35; 20.7 at 08:36:40; 14 at 08:36:45; 48.4 at 08:36:50; 96.6 at 08:36:55; 89 at 08:37:00; 20.7 at 08:37:05; 19.6 at 08:37:10; 65.8 at 08:37:15; 77.1 at 08:37:20; 18.8 at 08:37:25; 10 at 08:37:26; 19.6 at 08:37:30; 60.4 at 08:37:35; 77.4 at 08:37:40; 11.7 at 08:37:45; 19.6 at 08:37:50; 62.7 at 08:37:55; no cap at 08:38:00; 16.3 at 08:38:05; 19.6 at 08:38:10; 65.6 at 08:38:15; 98.3 at 08:38:20; 20.8 at 08:38:25; 14.1276 at 08:38:28; 18.9 at 08:38:30; 46.3 at 08:38:35; 80 at 08:38:40; 23.2 at 08:38:45; 14.1425 at 08:38:48; 19.6 at 08:38:50; 55.3 at 08:38:55; 65.4 at 08:39:00; 63.5781 at 08:39:04; 63.6 at 08:39:05; 69.8 at 08:39:10; 15.3 at 08:39:15; 14.1 at 08:39:20; 26.6065 at 08:39:21; 47.8 at 08:39:25; 97 at 08:39:30; 90 at 08:39:31; 53.4 at 08:39:35; 12.6 at 08:39:40; 26.1 at 08:39:45; 73.1 at 08:39:50; 81.1775 at 08:39:53; 53.7 at 08:39:55; 10 at 08:40:00; 18.9 at 08:40:05; 51.7 at 08:40:10; 78.8 at 08:40:15; 29 at 08:40:20; 10 at 08:40:25; 33.2 at 08:40:30; 73.3 at 08:40:35; 72.7612 at 08:40:38; 45.3151 08:40:40–08:42:19; 45.3 at 08:42:20 |
| getcart | no cap 08:30:25–08:40:35; 84 at 08:42:20 |
| postcart | no cap 08:30:25–08:42:20 |
| emptycart | no cap 08:30:25–08:42:20 |

### study7_s2_normal_rgtf1_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 09:12:45–09:24:35 |
| postcheckout | no cap 09:12:45–09:14:50; 52 at 09:14:55; no cap at 09:15:00; 72.6 at 09:15:02; no cap at 09:15:05; 79 at 09:15:10; no cap at 09:15:15; 19 at 09:15:20; 10 at 09:15:25; 36.2 at 09:15:30; 79.446 at 09:15:33; 88.4 at 09:15:35; no cap at 09:15:37; 58.6 at 09:15:40; 10 at 09:15:45; 19.3 at 09:15:50; 65.2439 at 09:15:54; 65.2 at 09:15:55; no cap at 09:16:00; 20.9 at 09:16:05; 14.1 at 09:16:10; 49.6126 at 09:16:14; 49.6 at 09:16:15; 86.9085 at 09:16:18; 90.6 at 09:16:20; no cap at 09:16:25; 56.5935 at 09:16:26; 21.9 at 09:16:30; 14 at 09:16:35; 45.7 at 09:16:40; 85.6 at 09:16:45; 85 at 09:16:50; 12.6 at 09:16:55; 19.6 at 09:17:00; 68 at 09:17:05; 99 at 09:17:07; 90 at 09:17:10; 21.9 at 09:17:15; 14.0795 at 09:17:19; 14.1 at 09:17:20; 49.3 at 09:17:25; 73.8 at 09:17:30; 17.3 at 09:17:35; 19.4819 at 09:17:39; 19.5 at 09:17:40; 61.3 at 09:17:45; 99 at 09:17:50; 88 at 09:17:52; 33.7 at 09:17:55; 20.66 at 09:17:56; 10 at 09:18:00; 37.7 at 09:18:05; 67.8375 at 09:18:07; 86.3 at 09:18:10; 48 at 09:18:15; 11.3217 at 09:18:18; 10 at 09:18:20; 19.83 at 09:18:22; 27.3 at 09:18:25; 50.0839 at 09:18:26; 78.3 at 09:18:30; 90 at 09:18:35; 21.6 at 09:18:40; 19.8 at 09:18:45; 66.8 at 09:18:50; 99 at 09:18:52; no cap at 09:18:55; 55.9603 at 09:18:56; 21.6 at 09:19:00; 14.1 at 09:19:05; 27.1235 at 09:19:07; 37 at 09:19:10; 86.1 at 09:19:15; 85 at 09:19:20; 32.8692 at 09:19:22; 20.3 at 09:19:25; 10 at 09:19:26; 19.7 at 09:19:30; 66.2 at 09:19:35; 90 at 09:19:40; 54.9891 at 09:19:41; 21 at 09:19:45; 19.5797 at 09:19:49; 19.6 at 09:19:50; 67.8 at 09:19:55; 99 at 09:19:57; no cap at 09:20:00; 71.9 at 09:20:05; 24.0727 at 09:20:08; 15 at 09:20:10; 19.2 at 09:20:15; 60.9 at 09:20:20; 73.1 at 09:20:25; 14.9 at 09:20:30; 14.2 at 09:20:35; 45.4344 at 09:20:39; 45.4 at 09:20:40; 93.8958 at 09:20:43; 91.8 at 09:20:45; 90 at 09:20:50; 14 at 09:20:55; 19 at 09:21:00; 25.4834 at 09:21:01; 46.3 at 09:21:05; 95.2289 at 09:21:08; 91.2 at 09:21:10; 90 at 09:21:15; 13.4 at 09:21:20; 14.0844 at 09:21:23; 19.5 at 09:21:25; 36.6976 at 09:21:27; 49.9 at 09:21:30; 93.2 at 09:21:35; 15.2 at 09:21:40; 18.9 at 09:21:45; 46 at 09:21:50; no cap at 09:21:55; 69.3 at 09:22:00; 16.7 at 09:22:05; 19.6 at 09:22:10; 49.4059 at 09:22:13; 66.4 at 09:22:15; 99 at 09:22:17; no cap at 09:22:20; 51.576 at 09:22:22; 32 at 09:22:25; 10 at 09:22:30; 26.0465 at 09:22:33; 35.8 at 09:22:35; 58.0294 at 09:22:37; 74.1 at 09:22:40; 86.9308 at 09:22:41; no cap at 09:22:45; 21.4 at 09:22:50; 14 at 09:22:55; 26.6018 at 09:22:57; 47.6 at 09:23:00; 63.5835 at 09:23:01; 85.4 at 09:23:05; 90 at 09:23:10; 13.6 at 09:23:15; 10 at 09:23:16; 19.8 at 09:23:20; 67.3 at 09:23:25; 68.6 at 09:23:30; 43.1329 at 09:23:31; 16.3 at 09:23:35; 19.1632 at 09:23:39; 19.2 at 09:23:40; 48.1 at 09:23:45; 82.4107 at 09:23:46; 92.3 at 09:23:50; 28.1 at 09:23:55; 10 at 09:24:00; 36.7968 at 09:24:04; 36.8 at 09:24:05; 89.025 at 09:24:08; 99 at 09:24:10; 90 09:24:14–09:24:15; 35 at 09:24:20; 14.2 at 09:24:25; 49.5 at 09:24:30; 87.5 at 09:24:35 |
| getcart | no cap 09:12:45–09:24:35 |
| postcart | no cap 09:12:45–09:24:35 |
| emptycart | no cap 09:12:45–09:24:35 |

### study7_s2_normal_rgtf1_rep3

| API | Live caps |
| --- | --- |
| getproduct | no cap 09:30:25–09:40:40; 244.7 at 09:40:45; no cap 09:40:50–09:42:15 |
| postcheckout | no cap 09:30:25–09:32:40; 66 at 09:32:45; 72 at 09:32:50; 84 at 09:32:55; 70 at 09:33:00; 10.6 at 09:33:05; 14.1226 at 09:33:07; 19.6 at 09:33:10; 64 at 09:33:15; no cap at 09:33:20; 24.3161 at 09:33:24; 24.3 at 09:33:25; 14.1 at 09:33:30; 37.3 at 09:33:35; 78.8 at 09:33:40; no cap at 09:33:45; 52.5613 at 09:33:47; 20.2 at 09:33:50; 14.1 at 09:33:55; 46.4492 at 09:33:59; 46.4 at 09:34:00; 78.7 at 09:34:05; 30.2 at 09:34:10; 14.146 at 09:34:14; 14.1 at 09:34:15; 36.7153 at 09:34:18; 50.6 at 09:34:20; 84.8615 at 09:34:22; no cap at 09:34:25; 34.9 at 09:34:30; 14.2 at 09:34:35; 36 at 09:34:40; 82.1 at 09:34:45; 90 at 09:34:50; 45.5904 at 09:34:52; 28.2 at 09:34:55; 14.1 at 09:35:00; 48.5 at 09:35:05; 78.8258 at 09:35:07; 97.1 at 09:35:10; 90 at 09:35:13; no cap at 09:35:15; 18.5 at 09:35:20; 19.5 at 09:35:25; 49.2 at 09:35:30; 78.021 at 09:35:34; 78 at 09:35:35; 19.1706 at 09:35:38; 11.8 at 09:35:40; 19.7 at 09:35:45; 65.8 at 09:35:50; no cap at 09:35:55; 20.1 at 09:36:00; 14.2 at 09:36:05; 48.7331 at 09:36:09; 48.7 at 09:36:10; 95.5548 at 09:36:13; 99 at 09:36:15; 52.7 at 09:36:20; 20.1468 at 09:36:22; 12.6 at 09:36:25; 14.1944 at 09:36:26; 27 at 09:36:30; 85.1 at 09:36:35; no cap 09:36:37–09:36:40; 17.1 at 09:36:45; 19.7 at 09:36:50; 26.902 at 09:36:51; 48.6 at 09:36:55; 77.5 at 09:37:00; 11.8 at 09:37:05; 19.6 at 09:37:10; 65.0367 at 09:37:14; 65 at 09:37:15; 99 at 09:37:18; no cap at 09:37:20; 54.9965 at 09:37:22; 33.8 at 09:37:25; 10 at 09:37:30; 36.9 at 09:37:35; 95 at 09:37:40; no cap at 09:37:45; 19.4 at 09:37:50; 19.6 at 09:37:55; 48.7 at 09:38:00; 65.18 at 09:38:04; 65.2 at 09:38:05; 10 at 09:38:10; 19.2 at 09:38:15; 51.7726 at 09:38:19; 51.8 at 09:38:20; 62.1 at 09:38:25; 10 at 09:38:30; 19.3 at 09:38:35; 60.6 at 09:38:40; 86.4 at 09:38:45; 41.3712 at 09:38:46; 15.9 at 09:38:50; 19.7 at 09:38:55; 64.9 at 09:39:00; 82.4 at 09:39:05; 54.1 at 09:39:10; 20.5105 at 09:39:12; 12.7 at 09:39:15; 26.1 at 09:39:20; 70.4 at 09:39:25; 87.0888 at 09:39:27; 85.3 at 09:39:30; 41.2556 at 09:39:31; 15.5 at 09:39:35; 19.5 at 09:39:40; 55.3 at 09:39:45; 86.7 at 09:39:50; 14.5375 at 09:39:54; 14.5 at 09:39:55; 14.0624 at 09:39:58; 19.4 at 09:40:00; 46.3 at 09:40:05; 84.3351 at 09:40:09; 84.3 at 09:40:10; 63.2 at 09:40:15; 15 at 09:40:20; 19.5 at 09:40:25; 51.3 at 09:40:30; 71.1 at 09:40:35; 67.3107 at 09:40:39; 67.3 at 09:40:40; 37 at 09:40:45; 69.7 at 09:40:50; 65.3 at 09:40:55; 15.3 at 09:41:00; 19.8325 at 09:41:04; 19.8 at 09:41:05; 63.5 at 09:41:10; 99 at 09:41:12; no cap at 09:41:15; 54.8574 at 09:41:16; 21.2 at 09:41:20; 14 at 09:41:25; 51.5 at 09:41:30; 91.3 at 09:41:35; 17.4 at 09:41:40; 19.6 at 09:41:45; 51.6 at 09:41:50; no cap at 09:41:55; 20.7134 at 09:41:59; 20.7 at 09:42:00; 19.7 at 09:42:05; 51.4 at 09:42:10; 97.9 at 09:42:15 |
| getcart | no cap 09:30:25–09:40:40; 86.7 at 09:40:45; no cap 09:40:50–09:42:15 |
| postcart | no cap 09:30:25–09:42:15 |
| emptycart | no cap 09:30:25–09:42:15 |

## 20. Per hold

**study7_s2_normal_rgtf1_rep1.** `frontend → checkoutservice` shed 1 time and re-enabled 1 time, then climbed 1→2→3. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 1 time and re-enabled 1 time, then climbed 1→2→3. At EXIT the edge held 3 attempts. Retry volume is 16,617 into checkoutservice, 10,680 into recommendationservice, and 4 into cartservice. `grpc_4 / grpc_14` on recommendationservice is 10,045 / 0. Detector-hot: checkoutservice 54.0%. Burst mode was off.

**study7_s2_normal_rgtf1_rep2.** `frontend → checkoutservice` stayed at 3 attempts. `frontend → recommendationservice` stayed at 3 attempts. Retry volume is 17,378 into checkoutservice, 0 into recommendationservice, and 0 into cartservice. `grpc_4 / grpc_14` on recommendationservice is 0 / 0. Detector-hot: checkoutservice 52.8%. Burst mode was off.

**study7_s2_normal_rgtf1_rep3.** `frontend → checkoutservice` stayed at 3 attempts. `frontend → recommendationservice` stayed at 3 attempts. Retry volume is 17,441 into checkoutservice, 1,477 into recommendationservice, and 0 into cartservice. `grpc_4 / grpc_14` on recommendationservice is 1,158 / 0. Detector-hot: checkoutservice 53.7%. Burst mode was off.

## 21. Related links

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode and burst-mode sections
- [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md)
- Earlier normal-mode both-on pair, not a column in this table: `study6_s2_normal_rgtf1_rep1` and `study6_s2_normal_rgtf1_rep2`, in [2026-10-12-s2-burst-matrix-abc.md](2026-10-12-s2-burst-matrix-abc.md)
- Run log: [2026-10-12-s2-normal-rgtf1-x3-run-log.md](../docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md)
