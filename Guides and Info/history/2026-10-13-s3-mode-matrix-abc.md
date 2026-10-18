# S3 mode matrix — (a) / (b) / (c)

## Setup

Scenario 3, 600 s. Mix 175 / 30 / 70 / 90 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1, with checkoutservice constrained to 200 m. Frontend HPA min = max = 4. productcatalogservice HPA min = max = 1. Frontend sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off between holds is 120 s. RetryGuard uses the locked parameters. Burst holds set `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal-mode RetryGuard holds omit those three keys. TopFull-only still has them in `s3_tf_only.yaml`; RetryGuard is off on that cell, so its result directory is `normal`. Each cell is two repeats. The bold bar splits the pairs.

The first launch of `final_s3_rg_only_normal_run1` is INVALID (locust_rows 682) and stays on disk. It is not a column. Its one replay, `final_s3_rg_only_normal_run1_r2`, is the scored hold for that cell. Earlier S3 holds, including the Set B checkout 200/100 pair, used a different CPU table and are not columns.

Scored folders:

- `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1_r2`
- `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run2`
- `experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run1`
- `experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run2`
- `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run1`
- `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run2`
- `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run1`
- `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run2`
- `experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run1`
- `experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run2`

## Index

| Hold | log_folder | Mode | TopFull | In this guide |
| --- | --- | --- | --- | --- |
| 1 | final_s3_rg_only_normal_run1 | normal | off | INVALID, 682 rows, kept, not scored |
| 1 replay | final_s3_rg_only_normal_run1_r2 | normal | off | PASS, scored in place of run1 |
| 2 | final_s3_rg_only_normal_run2 | normal | off | PASS |
| 3 | final_s3_both_normal_run1 | normal | on | PASS |
| 4 | final_s3_both_normal_run2 | normal | on | PASS |
| 5 | final_s3_tf_only_run1 | tf | on | PASS |
| 6 | final_s3_tf_only_run2 | tf | on | PASS |
| 7 | final_s3_rg_only_burst_run1 | burst_rpr 2.0 | off | PASS |
| 8 | final_s3_rg_only_burst_run2 | burst_rpr 2.0 | off | PASS |
| 9 | final_s3_both_burst_run1 | burst_rpr 2.0 | on | PASS |
| 10 | final_s3_both_burst_run2 | burst_rpr 2.0 | on | PASS |

Table columns follow the ten PASS rows, in that order. The INVALID launch is not a column.

## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars: rg_only/1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); rg_only/2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); both/1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); both/2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

In that Burst bars line, `rg_only/1` is `final_s3_rg_only_burst_run1`, `rg_only/2` is `final_s3_rg_only_burst_run2`, `both/1` is `final_s3_both_burst_run1`, and `both/2` is `final_s3_both_burst_run2`. The START line on those holds sets `burst_window_seconds=5` and `burst_min_first_attempts=20`. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s.

## (a) Edge rpr

The only edge with a tick above the shed bar, or a non-zero retry delta, is frontend → checkoutservice. A bold file-streak cell is at least 30 seconds.

### File streak seconds / ticks above the shed bar (controller high)

| Edge | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 22 / 23 (21) | 22 / 23 (21) | **┃** | 22 / 23 (20) | 22 / 23 (20) | **┃** | **596 / 590** | **595 / 571** | **┃** | 22 / 23 (21) | 23 / 24 (20) | **┃** | 22 / 23 (21) | 22 / 23 (21) |

### Mean / median / max / volume rpr

| Edge | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.067 / 0.000 / 3.00 / 0.029 | 0.065 / 0.000 / 7.33 / 0.026 | **┃** | 0.056 / 0.000 / 2.71 / 0.046 | 0.063 / 0.000 / 4.33 / 0.047 | **┃** | 1.842 / 1.750 / 7.00 / 1.771 | 1.790 / 1.727 / 5.20 / 1.714 | **┃** | 0.054 / 0.000 / 3.17 / 0.020 | 0.067 / 0.000 / 2.60 / 0.031 | **┃** | 0.064 / 0.000 / 3.14 / 0.048 | 0.060 / 0.000 / 3.00 / 0.045 |

### Climb streaks, 1-attempt / 2-attempt

| Edge | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

## 4a Burst

Burst mode was off on the six normal and TopFull-only holds.

On the four burst holds the (a2) burst window is below. Burst sheds in that table are 0 on every edge, including frontend → checkoutservice. The one ON→OFF on that edge is the normal rpr shed, so the burst-vs-normal split is 0 burst sheds and 1 normal shed on each of those four holds.

| Edge | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | 0.00 / 0.00 / 0 / 0 (603) | 0.00 / 0.00 / 0 / 0 (595) | **┃** | 0.00 / 0.00 / 0 / 0 (557) | 0.00 / 0.00 / 0 / 0 (566) |
| frontend → cartservice | 0.00 / 0.00 / 0 / 0 (604) | 0.00 / 0.00 / 0 / 0 (595) | **┃** | 0.00 / 0.00 / 0 / 0 (557) | 0.00 / 0.00 / 0 / 0 (567) |
| frontend → recommendationservice | 0.00 / 0.00 / 0 / 0 (604) | 0.00 / 0.00 / 0 / 0 (595) | **┃** | 0.00 / 0.00 / 0 / 0 (556) | 0.00 / 0.00 / 0 / 0 (566) |
| checkoutservice → emailservice | 0.00 / 0.00 / 0 / 0 (8) | 0.00 / 0.00 / 0 / 0 (9) | **┃** | 0.00 / 0.00 / 0 / 0 (514) | 0.00 / 0.00 / 0 / 0 (519) |
| frontend → adservice | 0.00 / 0.00 / 0 / 0 (603) | 0.00 / 0.00 / 0 / 0 (594) | **┃** | 0.00 / 0.00 / 0 / 0 (556) | 0.00 / 0.00 / 0 / 0 (565) |
| frontend → currencyservice | 0.00 / 0.00 / 0 / 0 (605) | 0.00 / 0.00 / 0 / 0 (595) | **┃** | 0.00 / 0.00 / 0 / 0 (557) | 0.00 / 0.00 / 0 / 0 (567) |
| checkoutservice → cartservice | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (592) | **┃** | 0.00 / 0.00 / 0 / 0 (553) | 0.00 / 0.00 / 0 / 0 (563) |
| frontend → checkoutservice | 1.65 / 1.29 / 0 / 0 (27) | 1.82 / 1.52 / 0 / 0 (30) | **┃** | 1.88 / 1.09 / 0 / 0 (32) | 1.79 / 1.30 / 0 / 0 (30) |
| checkoutservice → currencyservice | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (588) | **┃** | 0.00 / 0.00 / 0 / 0 (550) | 0.00 / 0.00 / 0 / 0 (560) |
| frontend → shippingservice | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (593) | **┃** | 0.00 / 0.00 / 0 / 0 (555) | 0.00 / 0.00 / 0 / 0 (565) |
| frontend → productcatalogservice | 0.00 / 0.00 / 0 / 0 (606) | 0.00 / 0.00 / 0 / 0 (596) | **┃** | 0.00 / 0.00 / 0 / 0 (558) | 0.00 / 0.00 / 0 / 0 (568) |
| checkoutservice → paymentservice | 0.00 / 0.00 / 0 / 0 (582) | 0.00 / 0.00 / 0 / 0 (576) | **┃** | 0.00 / 0.00 / 0 / 0 (550) | 0.00 / 0.00 / 0 / 0 (559) |
| checkoutservice → shippingservice | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (592) | **┃** | 0.00 / 0.00 / 0 / 0 (553) | 0.00 / 0.00 / 0 / 0 (563) |

## Rejection beside (a)

Longest streak / count of inbound rejection above 0.20. Bold when a controlled service's streak is at least 30. frontend and redis-cart stay plain.

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | **591 / 591** | **592 / 592** | **┃** | 23 / 232 | 24 / 261 | **┃** | **590 / 590** | **571 / 571** | **┃** | **599 / 599** | **590 / 590** | **┃** | 20 / 245 | 24 / 251 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 4 / 138 | 3 / 108 | **┃** | 1 / 2 | 2 / 4 | **┃** | 4 / 88 | 3 / 90 | **┃** | 3 / 117 | 5 / 148 | **┃** | 1 / 3 | 3 / 4 |
| emailservice | 1 / 2 | 1 / 1 | **┃** | 3 / 27 | 2 / 30 | **┃** | 1 / 1 | 1 / 6 | **┃** | 2 / 3 | 1 / 2 | **┃** | 2 / 32 | 1 / 19 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

Share of detector samples at or above 1. Bold when the share is at least 0.5.

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| checkoutservice | **601/711 (84.5%)** | **597/711 (84.0%)** | **┃** | **599/713 (84.0%)** | **600/713 (84.2%)** | **┃** | **599/688 (87.1%)** | **599/688 (87.1%)** | **┃** | **598/710 (84.2%)** | **599/711 (84.2%)** | **┃** | **599/714 (83.9%)** | **598/714 (83.8%)** |
| recommendationservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| paymentservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| emailservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| productcatalogservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| cartservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 13/688 (1.9%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| currencyservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| shippingservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| adservice | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |
| redis-cart | 0/711 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/688 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/714 (0.0%) | 0/714 (0.0%) |

## (c) Retry volume

### Outbound retry delta by target

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 499 | 459 | **┃** | 338 | 341 | **┃** | 10,670 | 10,327 | **┃** | 345 | 532 | **┃** | 354 | 334 |

### Inbound resets, all 11 services

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 33 | 28 | **┃** | 19 | 21 | **┃** | 29 | 26 | **┃** | 19 | 16 | **┃** | 6 | 7 |
| checkoutservice | 10,272 | 10,365 | **┃** | 1,695 | 1,820 | **┃** | 9,784 | 9,495 | **┃** | 10,202 | 9,833 | **┃** | 2,035 | 1,997 |
| recommendationservice | 3 | 1 | **┃** | 6 | 5 | **┃** | 0 | 1 | **┃** | 1 | 0 | **┃** | 0 | 0 |
| paymentservice | 667 | 531 | **┃** | 16 | 36 | **┃** | 671 | 695 | **┃** | 662 | 766 | **┃** | 35 | 32 |
| emailservice | 2 | 1 | **┃** | 116 | 137 | **┃** | 1 | 6 | **┃** | 3 | 2 | **┃** | 123 | 118 |
| productcatalogservice | 4 | 3 | **┃** | 1 | 5 | **┃** | 0 | 3 | **┃** | 1 | 2 | **┃** | 1 | 1 |
| cartservice | 38 | 36 | **┃** | 101 | 50 | **┃** | 52 | 55 | **┃** | 27 | 40 | **┃** | 91 | 84 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 340 | 345 | **┃** | 49 | 38 | **┃** | 307 | 382 | **┃** | 252 | 409 | **┃** | 39 | 30 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 3 | **┃** | 0 | 0 | **┃** | 2 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

### grpc_4 / grpc_14

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 3 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 6 / 0 | 0 / 0 |

## RetryGuard toggles

### Part 1 — counts and timestamps

ON→OFF is a shed from attempts on to 0. 0→1 is the re-enable step. The two TopFull-only holds, `final_s3_tf_only_run1` and `final_s3_tf_only_run2`, have no retryguard.log, so they have no toggle table.

#### final_s3_rg_only_normal_run1_r2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T00:25:42Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.42 |

#### final_s3_rg_only_normal_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T00:50:54Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.32 |

#### final_s3_both_normal_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T01:14:34Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.25 |

#### final_s3_both_normal_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T01:32:56Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.83 |

#### final_s3_rg_only_burst_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T02:26:22Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.38 |

#### final_s3_rg_only_burst_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T02:46:40Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.61 |

#### final_s3_both_burst_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T03:05:13Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.57 |

#### final_s3_both_burst_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T03:27:33Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.29 |

### Part 2 — per callee

One edge shed: frontend → checkoutservice. Counts and the shed rpr are the ON→OFF line in retryguard.log, which matches the Part 1 timestamp table. OFF rejection uses metric=rejection samples on checkoutservice while the edge is at 0 attempts, from the shed timestamp through EXIT. The re-enable bar is 0.25. An em dash on the TopFull-only columns means there is no retryguard.log. Attempts after re-enable are 0 because the edge went to 0 and no 0→1 line exists, so it was still at 0 at EXIT.

| frontend → checkoutservice | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 0 | 1 / 0 | **┃** | 1 / 0 | 1 / 0 | **┃** | — | — | **┃** | 1 / 0 | 1 / 0 | **┃** | 1 / 0 | 1 / 0 |
| Shed rpr | 2.42 | 1.32 | **┃** | 1.25 | 1.83 | **┃** | — | — | **┃** | 1.38 | 1.61 | **┃** | 2.57 | 2.29 |
| First shed, seconds after first OBSERVE | 41 | 42 | **┃** | 41 | 40 | **┃** | — | — | **┃** | 34 | 43 | **┃** | 40 | 38 |
| Attempts after re-enable | 0 | 0 | **┃** | 0 | 0 | **┃** | — | — | **┃** | 0 | 0 | **┃** | 0 | 0 |
| Time OFF (s) | 571 | 572 | **┃** | 573 | 574 | **┃** | — | — | **┃** | 580 | 571 | **┃** | 574 | 575 |
| OFF rejection min / median | 0.300 / 0.581 | 0.300 / 0.588 | **┃** | 0.000 / 0.087 | 0.000 / 0.154 | **┃** | — | — | **┃** | 0.267 / 0.567 | 0.000 / 0.567 | **┃** | 0.000 / 0.136 | 0.000 / 0.160 |
| Longest streak under 0.25 | 0 | 0 | **┃** | 12 | 8 | **┃** | — | — | **┃** | 0 | 1 | **┃** | 9 | 8 |

frontend → checkoutservice shed once on each RetryGuard hold, from 3 attempts, on the normal rpr path. The first shed is 34–43 s after the first OBSERVE. Time OFF is 571–580 s, the rest of the hold. No hold re-enabled, so the longest streak under 0.25 stays below the 30-sample 0→1 step: 0 or 1 sample when TopFull is off, and 8–12 samples when both controllers are on. OFF-window rejection median is 0.567–0.588 with TopFull off and 0.087–0.160 with both on.

## Locust goodput

Mean Goodput while RPS > 0, per API.

| API | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 168.1 | 167.8 | **┃** | 167.8 | 167.9 | **┃** | 167.7 | 167.8 | **┃** | 167.8 | 168.0 | **┃** | 167.9 | 167.8 |
| postcheckout | 0.2 | 0.2 | **┃** | 7.2 | 7.3 | **┃** | 0.1 | 0.1 | **┃** | 0.1 | 0.2 | **┃** | 6.8 | 6.9 |
| getcart | 67.2 | 67.1 | **┃** | 67.1 | 67.2 | **┃** | 67.2 | 67.1 | **┃** | 67.1 | 67.2 | **┃** | 67.2 | 67.1 |
| postcart | 86.4 | 86.3 | **┃** | 86.3 | 86.3 | **┃** | 86.4 | 86.3 | **┃** | 86.3 | 86.2 | **┃** | 86.3 | 86.3 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean Fail / RPS while RPS > 0, per API.

| API | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.965 | 0.967 | **┃** | 0.731 | 0.731 | **┃** | 0.979 | 0.977 | **┃** | 0.977 | 0.966 | **┃** | 0.745 | 0.745 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean Latency95 (ms) while RPS > 0, per API.

| API | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 88 | 84 | **┃** | 89 | 88 | **┃** | 85 | 84 | **┃** | 95 | 92 | **┃** | 83 | 87 |
| postcheckout | 617 | 610 | **┃** | 569 | 577 | **┃** | 2133 | 2130 | **┃** | 614 | 616 | **┃** | 564 | 576 |
| getcart | 71 | 62 | **┃** | 72 | 67 | **┃** | 57 | 56 | **┃** | 76 | 72 | **┃** | 54 | 70 |
| postcart | 61 | 60 | **┃** | 61 | 60 | **┃** | 61 | 60 | **┃** | 62 | 61 | **┃** | 60 | 62 |
| emptycart | 12 | 13 | **┃** | 14 | 15 | **┃** | 15 | 11 | **┃** | 18 | 12 | **┃** | 13 | 15 |

## Inbound arrival rate

Positive Δtotal over the elapsed time of service_inbound.csv, per service.

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 327.4 | 327.4 | **┃** | 312.3 | 311.6 | **┃** | 321.8 | 322.3 | **┃** | 327.5 | 327.3 | **┃** | 311.9 | 311.7 |
| checkoutservice | 27.1 | 27.0 | **┃** | 11.7 | 11.6 | **┃** | 26.1 | 25.6 | **┃** | 26.9 | 27.1 | **┃** | 11.8 | 11.6 |
| recommendationservice | 243.2 | 243.2 | **┃** | 228.1 | 227.6 | **┃** | 234.4 | 234.8 | **┃** | 243.3 | 243.1 | **┃** | 227.8 | 227.6 |
| paymentservice | 8.4 | 8.2 | **┃** | 11.2 | 11.0 | **┃** | 11.4 | 12.2 | **┃** | 8.8 | 9.2 | **┃** | 11.2 | 11.0 |
| emailservice | 0.2 | 0.2 | **┃** | 7.7 | 7.8 | **┃** | 0.1 | 0.2 | **┃** | 0.1 | 0.2 | **┃** | 7.4 | 7.5 |
| productcatalogservice | 1693.8 | 1693.9 | **┃** | 1602.8 | 1599.5 | **┃** | 1649.9 | 1652.6 | **┃** | 1694.2 | 1693.1 | **┃** | 1601.1 | 1599.7 |
| cartservice | 328.4 | 328.5 | **┃** | 322.2 | 321.5 | **┃** | 338.9 | 339.1 | **┃** | 328.2 | 328.4 | **┃** | 321.7 | 321.5 |
| currencyservice | 458.5 | 458.2 | **┃** | 452.0 | 451.2 | **┃** | 474.8 | 475.3 | **┃** | 458.8 | 458.5 | **┃** | 451.1 | 450.9 |
| shippingservice | 89.6 | 90.0 | **┃** | 84.3 | 83.8 | **┃** | 92.6 | 93.0 | **┃** | 89.8 | 90.2 | **┃** | 84.2 | 83.8 |
| adservice | 154.8 | 154.8 | **┃** | 154.8 | 154.6 | **┃** | 160.6 | 160.9 | **┃** | 154.8 | 154.8 | **┃** | 154.6 | 154.6 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn

Δrq_time_sum_ms / Δrq_time_count, milliseconds.

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 86 | 83 | **┃** | 61 | 59 | **┃** | 84 | 82 | **┃** | 89 | 87 | **┃** | 56 | 60 |
| checkoutservice | 492 | 492 | **┃** | 375 | 392 | **┃** | 496 | 495 | **┃** | 495 | 493 | **┃** | 377 | 378 |
| recommendationservice | 7 | 7 | **┃** | 7 | 8 | **┃** | 7 | 6 | **┃** | 9 | 8 | **┃** | 7 | 8 |
| paymentservice | 3 | 3 | **┃** | 3 | 2 | **┃** | 3 | 3 | **┃** | 3 | 3 | **┃** | 2 | 2 |
| emailservice | 12 | 8 | **┃** | 7 | 7 | **┃** | 4 | 4 | **┃** | 8 | 5 | **┃** | 7 | 8 |
| productcatalogservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| currencyservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 0 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.079 | 0.079 | **┃** | 0.017 | 0.019 | **┃** | 0.029 | 0.029 | **┃** | 0.080 | 0.079 | **┃** | 0.019 | 0.019 |
| checkoutservice | 0.982 | 0.982 | **┃** | 0.296 | 0.259 | **┃** | 0.989 | 0.989 | **┃** | 0.992 | 0.983 | **┃** | 0.298 | 0.273 |
| recommendationservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## CPU

Per-pod quota, replica mode, mean millicores, max millicores. checkoutservice is the constrained row at 200m.

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1249 / 1707 | 1150 / 4 / 1268 / 1663 | **┃** | 1150 / 4 / 1154 / 1526 | 1150 / 4 / 1227 / 1587 | **┃** | 1150 / 4 / 1260 / 1634 | 1150 / 4 / 1286 / 1635 | **┃** | 1150 / 4 / 1200 / 1569 | 1150 / 4 / 1193 / 1570 | **┃** | 1150 / 4 / 1247 / 1634 | 1150 / 4 / 1029 / 1539 |
| checkoutservice | 200 / 1 / 157 / 196 | 200 / 1 / 156 / 196 | **┃** | 200 / 1 / 159 / 199 | 200 / 1 / 159 / 199 | **┃** | 200 / 1 / 161 / 197 | 200 / 1 / 161 / 196 | **┃** | 200 / 1 / 157 / 199 | 200 / 1 / 156 / 197 | **┃** | 200 / 1 / 159 / 199 | 200 / 1 / 138 / 199 |
| recommendationservice | 1150 / 1 / 450 / 676 | 1150 / 1 / 448 / 612 | **┃** | 1150 / 1 / 411 / 555 | 1150 / 1 / 428 / 563 | **┃** | 1150 / 1 / 431 / 570 | 1150 / 1 / 435 / 581 | **┃** | 1150 / 1 / 451 / 597 | 1150 / 1 / 439 / 596 | **┃** | 1150 / 1 / 425 / 574 | 1150 / 1 / 365 / 558 |
| paymentservice | 155 / 1 / 12 / 18 | 155 / 1 / 12 / 19 | **┃** | 155 / 1 / 15 / 22 | 155 / 1 / 15 / 23 | **┃** | 155 / 1 / 14 / 22 | 155 / 1 / 15 / 23 | **┃** | 155 / 1 / 12 / 20 | 155 / 1 / 12 / 20 | **┃** | 155 / 1 / 15 / 24 | 155 / 1 / 14 / 22 |
| emailservice | 120 / 1 / 10 / 27 | 120 / 1 / 10 / 27 | **┃** | 120 / 1 / 23 / 32 | 120 / 1 / 24 / 32 | **┃** | 120 / 1 / 11 / 19 | 120 / 1 / 10 / 18 | **┃** | 120 / 1 / 10 / 19 | 120 / 1 / 10 / 22 | **┃** | 120 / 1 / 23 / 30 | 120 / 1 / 21 / 31 |
| productcatalogservice | 800 / 1 / 450 / 604 | 800 / 1 / 464 / 605 | **┃** | 800 / 1 / 428 / 556 | 800 / 1 / 443 / 572 | **┃** | 800 / 1 / 466 / 593 | 800 / 1 / 476 / 597 | **┃** | 800 / 1 / 437 / 567 | 800 / 1 / 437 / 572 | **┃** | 800 / 1 / 471 / 610 | 800 / 1 / 374 / 556 |
| cartservice | 800 / 1 / 396 / 695 | 800 / 1 / 400 / 702 | **┃** | 800 / 1 / 365 / 509 | 800 / 1 / 383 / 522 | **┃** | 800 / 1 / 401 / 674 | 800 / 1 / 497 / 751 | **┃** | 800 / 1 / 370 / 513 | 800 / 1 / 376 / 664 | **┃** | 800 / 1 / 402 / 587 | 800 / 1 / 324 / 512 |
| currencyservice | 770 / 1 / 268 / 385 | 770 / 1 / 266 / 357 | **┃** | 770 / 1 / 252 / 335 | 770 / 1 / 268 / 363 | **┃** | 770 / 1 / 271 / 358 | 770 / 1 / 282 / 380 | **┃** | 770 / 1 / 259 / 343 | 770 / 1 / 254 / 342 | **┃** | 770 / 1 / 269 / 359 | 770 / 1 / 223 / 342 |
| shippingservice | 770 / 1 / 60 / 80 | 770 / 1 / 61 / 79 | **┃** | 770 / 1 / 59 / 75 | 770 / 1 / 57 / 75 | **┃** | 770 / 1 / 62 / 78 | 770 / 1 / 60 / 77 | **┃** | 770 / 1 / 60 / 78 | 770 / 1 / 59 / 77 | **┃** | 770 / 1 / 59 / 76 | 770 / 1 / 53 / 78 |
| adservice | 1150 / 1 / 115 / 159 | 1150 / 1 / 116 / 190 | **┃** | 1150 / 1 / 109 / 143 | 1150 / 1 / 120 / 154 | **┃** | 1150 / 1 / 116 / 157 | 1150 / 1 / 123 / 167 | **┃** | 1150 / 1 / 113 / 143 | 1150 / 1 / 110 / 144 | **┃** | 1150 / 1 / 119 / 173 | 1150 / 1 / 100 / 144 |
| redis-cart | 540 / 1 / 37 / 51 | 540 / 1 / 37 / 49 | **┃** | 540 / 1 / 36 / 48 | 540 / 1 / 38 / 50 | **┃** | 540 / 1 / 38 / 50 | 540 / 1 / 38 / 50 | **┃** | 540 / 1 / 36 / 48 | 540 / 1 / 35 / 47 | **┃** | 540 / 1 / 38 / 51 | 540 / 1 / 33 / 49 |

### Fraction of per-pod quota × replicas (mean / max)

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.27 / 0.37 | 0.28 / 0.36 | **┃** | 0.25 / 0.33 | 0.27 / 0.34 | **┃** | 0.27 / 0.36 | 0.28 / 0.36 | **┃** | 0.26 / 0.34 | 0.26 / 0.34 | **┃** | 0.27 / 0.36 | 0.22 / 0.33 |
| checkoutservice | 0.78 / 0.98 | 0.78 / 0.98 | **┃** | 0.79 / 0.99 | 0.80 / 0.99 | **┃** | 0.81 / 0.98 | 0.81 / 0.98 | **┃** | 0.78 / 0.99 | 0.78 / 0.98 | **┃** | 0.79 / 0.99 | 0.69 / 0.99 |
| recommendationservice | 0.39 / 0.59 | 0.39 / 0.53 | **┃** | 0.36 / 0.48 | 0.37 / 0.49 | **┃** | 0.37 / 0.50 | 0.38 / 0.51 | **┃** | 0.39 / 0.52 | 0.38 / 0.52 | **┃** | 0.37 / 0.50 | 0.32 / 0.49 |
| paymentservice | 0.08 / 0.12 | 0.07 / 0.12 | **┃** | 0.10 / 0.14 | 0.10 / 0.15 | **┃** | 0.09 / 0.14 | 0.09 / 0.15 | **┃** | 0.08 / 0.13 | 0.08 / 0.13 | **┃** | 0.10 / 0.15 | 0.09 / 0.14 |
| emailservice | 0.09 / 0.23 | 0.09 / 0.23 | **┃** | 0.19 / 0.27 | 0.20 / 0.27 | **┃** | 0.09 / 0.16 | 0.09 / 0.15 | **┃** | 0.08 / 0.16 | 0.08 / 0.18 | **┃** | 0.19 / 0.25 | 0.18 / 0.26 |
| productcatalogservice | 0.56 / 0.76 | 0.58 / 0.76 | **┃** | 0.53 / 0.69 | 0.55 / 0.71 | **┃** | 0.58 / 0.74 | 0.59 / 0.75 | **┃** | 0.55 / 0.71 | 0.55 / 0.71 | **┃** | 0.59 / 0.76 | 0.47 / 0.69 |
| cartservice | 0.50 / 0.87 | 0.50 / 0.88 | **┃** | 0.46 / 0.64 | 0.48 / 0.65 | **┃** | 0.50 / 0.84 | 0.62 / 0.94 | **┃** | 0.46 / 0.64 | 0.47 / 0.83 | **┃** | 0.50 / 0.73 | 0.40 / 0.64 |
| currencyservice | 0.35 / 0.50 | 0.35 / 0.46 | **┃** | 0.33 / 0.44 | 0.35 / 0.47 | **┃** | 0.35 / 0.46 | 0.37 / 0.49 | **┃** | 0.34 / 0.45 | 0.33 / 0.44 | **┃** | 0.35 / 0.47 | 0.29 / 0.44 |
| shippingservice | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.07 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.07 / 0.10 |
| adservice | 0.10 / 0.14 | 0.10 / 0.17 | **┃** | 0.09 / 0.12 | 0.10 / 0.13 | **┃** | 0.10 / 0.14 | 0.11 / 0.15 | **┃** | 0.10 / 0.12 | 0.10 / 0.13 | **┃** | 0.10 / 0.15 | 0.09 / 0.13 |
| redis-cart | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.09 | 0.06 / 0.09 |

## Detector max utilization

| Service | final_s3_rg_only_normal_run1_r2 | final_s3_rg_only_normal_run2 | **┃** | final_s3_both_normal_run1 | final_s3_both_normal_run2 | **┃** | final_s3_tf_only_run1 | final_s3_tf_only_run2 | **┃** | final_s3_rg_only_burst_run1 | final_s3_rg_only_burst_run2 | **┃** | final_s3_both_burst_run1 | final_s3_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.387 | 0.383 | **┃** | 0.347 | 0.367 | **┃** | 0.383 | 0.388 | **┃** | 0.365 | 0.365 | **┃** | 0.383 | 0.352 |
| checkoutservice | 1.115 | 1.045 | **┃** | 1.080 | 1.095 | **┃** | 1.065 | 1.035 | **┃** | 1.085 | 1.080 | **┃** | 1.070 | 1.075 |
| recommendationservice | 0.651 | 0.566 | **┃** | 0.520 | 0.527 | **┃** | 0.523 | 0.533 | **┃** | 0.561 | 0.553 | **┃** | 0.530 | 0.517 |
| paymentservice | 0.355 | 0.413 | **┃** | 0.374 | 0.361 | **┃** | 0.529 | 0.368 | **┃** | 0.368 | 0.465 | **┃** | 0.413 | 0.361 |
| emailservice | 0.450 | 0.542 | **┃** | 0.558 | 0.592 | **┃** | 0.375 | 0.408 | **┃** | 0.375 | 0.458 | **┃** | 0.550 | 0.558 |
| productcatalogservice | 0.790 | 0.795 | **┃** | 0.749 | 0.754 | **┃** | 0.772 | 0.800 | **┃** | 0.749 | 0.764 | **┃** | 0.810 | 0.740 |
| cartservice | 0.887 | 0.900 | **┃** | 0.701 | 0.709 | **┃** | 0.880 | 0.969 | **┃** | 0.739 | 0.856 | **┃** | 0.779 | 0.695 |
| currencyservice | 0.568 | 0.518 | **┃** | 0.503 | 0.506 | **┃** | 0.565 | 0.540 | **┃** | 0.510 | 0.491 | **┃** | 0.544 | 0.516 |
| shippingservice | 0.136 | 0.149 | **┃** | 0.151 | 0.138 | **┃** | 0.148 | 0.144 | **┃** | 0.152 | 0.136 | **┃** | 0.152 | 0.145 |
| adservice | 0.211 | 0.378 | **┃** | 0.159 | 0.171 | **┃** | 0.250 | 0.217 | **┃** | 0.152 | 0.163 | **┃** | 0.232 | 0.157 |
| redis-cart | 0.120 | 0.139 | **┃** | 0.126 | 0.124 | **┃** | 0.128 | 0.133 | **┃** | 0.130 | 0.139 | **┃** | 0.146 | 0.126 |

## TopFull live caps

A live read of 10000 is no cap. A live read of 0 is an empty read and is left out. The collapsed spans are the scorer's.

### final_s3_rg_only_normal_run1_r2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:23:25–00:35:10 |
| postcheckout | no cap 00:23:25–00:35:10 |
| getcart | no cap 00:23:25–00:35:10 |
| postcart | no cap 00:23:25–00:35:10 |
| emptycart | no cap 00:23:25–00:35:10 |

### final_s3_rg_only_normal_run2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:48:35–01:00:25 |
| postcheckout | no cap 00:48:35–01:00:25 |
| getcart | no cap 00:48:35–01:00:25 |
| postcart | no cap 00:48:35–01:00:25 |
| emptycart | no cap 00:48:35–01:00:25 |

### final_s3_both_normal_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:12:15–01:24:05 |
| postcheckout | no cap 01:12:15–01:14:10; 12 at 01:14:15; 10 01:14:20–01:14:35; 13.0053 at 01:14:39; 13 at 01:14:40; 10.6 at 01:14:45; 14.6963 at 01:14:48; 13.4 at 01:14:50; 11.4 at 01:14:55; 11 at 01:15:00; 10.8055 at 01:15:02; 13.6 at 01:15:05; 10.3 at 01:15:10; 11.7 at 01:15:15; 15.0665 at 01:15:16; 12.2 at 01:15:20; 15.6 at 01:15:25; 10 01:15:29–01:15:30; 12.8711 at 01:15:33; 10 at 01:15:35; 16.2 at 01:15:40; 10.4 at 01:15:45; 11.5 at 01:15:50; 11.4 at 01:15:55; 14.8 at 01:16:00; 12.5 at 01:16:05; 10.5 at 01:16:10; 14.1 at 01:16:15; 10 at 01:16:20; 12.7 at 01:16:25; 14.6 at 01:16:30; 10.3 at 01:16:35; 10.351 at 01:16:39; 10.4 at 01:16:40; 13.5 at 01:16:45; 10 at 01:16:50; 11.2 at 01:16:55; 12.7127 at 01:16:57; 10.6 at 01:17:00; 11.6 at 01:17:05; 14.6 at 01:17:10; 10 at 01:17:15; 11.7 at 01:17:20; 12.8 at 01:17:25; 15.234 at 01:17:27; 10 at 01:17:30; 10.5 at 01:17:35; 13.2 at 01:17:40; 11.1 at 01:17:45; 10.9 at 01:17:50; 11.3 at 01:17:55; 14.7 at 01:18:00; 10 at 01:18:03; 11.2 at 01:18:05; 10.3 at 01:18:10; 11.5622 at 01:18:12; 12.8 at 01:18:15; 12.7 at 01:18:20; 10.8 at 01:18:25; 15.9 at 01:18:30; 10.4 at 01:18:35; 11.9 at 01:18:40; 10 at 01:18:43; 11.6 at 01:18:45; 14.3318 at 01:18:47; 10 at 01:18:50; 12.2 at 01:18:55; 13.4 at 01:19:00; 10.8171 at 01:19:01; 10 at 01:19:05; 16 at 01:19:10; 10.6 at 01:19:15; 11.1 at 01:19:20; 14 at 01:19:25; 11.4 at 01:19:30; 13.8999 at 01:19:31; 11.4 at 01:19:35; 15.8 at 01:19:40; 13 at 01:19:45; 11 at 01:19:50; 11.2501 at 01:19:53; 12.9 01:19:55–01:20:00; 10.3 at 01:20:05; 12.6 at 01:20:10; 11.5 at 01:20:15; 12.2331 at 01:20:19; 12.2 at 01:20:20; 10.7 at 01:20:25; 11.1 at 01:20:30; 10.6029 at 01:20:33; 13.1 at 01:20:35; 10.3 at 01:20:40; 11.481 at 01:20:42; 14.2 at 01:20:45; 10 at 01:20:50; 13.1 at 01:20:55; 14.4785 at 01:20:59; 14.5 at 01:21:00; 10 at 01:21:05; 11.9 at 01:21:10; 13.6 at 01:21:15; 10 at 01:21:20; 11.1 at 01:21:25; 14.5 at 01:21:30; 10.9631 at 01:21:31; 10 at 01:21:35; 12.3 at 01:21:40; 12 at 01:21:45; 10 at 01:21:50; 10.6927 at 01:21:54; 10.7 at 01:21:55; 15.5 at 01:22:00; 10 at 01:22:05; 13 at 01:22:10; 10.2094 at 01:22:12; 15.7 at 01:22:15; 10 at 01:22:20; 10.2 at 01:22:25; 14.3 at 01:22:30; 10 01:22:34–01:22:35; 12.6 at 01:22:40; 10 at 01:22:43; 11.6 at 01:22:45; 10.1 at 01:22:50; 13.8 at 01:22:55; 15.2248 at 01:22:57; 10 at 01:23:00; 11.9085 at 01:23:01; 10.6 at 01:23:05; 16.3 at 01:23:10; 10 at 01:23:15; 11.9254 at 01:23:19; 11.9 at 01:23:20; 13.1 at 01:23:25; 12.2915 at 01:23:28; 10 at 01:23:30; 14.6 at 01:23:35; 11.7 at 01:23:40; 11.4129 at 01:23:41; 11.5 at 01:23:45; 16.4 at 01:23:50; 10 at 01:23:55; 12.9 at 01:24:00; 12.6643 at 01:24:04; 12.7 at 01:24:05 |
| getcart | no cap 01:12:15–01:24:05 |
| postcart | no cap 01:12:15–01:24:05 |
| emptycart | no cap 01:12:15–01:24:05 |

### final_s3_both_normal_run2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:30:40–01:42:30 |
| postcheckout | no cap 01:30:40–01:32:30; 10 01:32:35–01:33:00; 15.3 at 01:33:05; 10.4816 at 01:33:09; 10.5 at 01:33:10; 11.2 at 01:33:15; 11 at 01:33:20; 14.755 at 01:33:22; 12.3 at 01:33:25; 12.3933 at 01:33:26; 10.2 at 01:33:30; 13.3 at 01:33:35; 11.4 at 01:33:40; 11.9 at 01:33:45; 11.6 at 01:33:50; 15.1 at 01:33:55; 10.1 at 01:34:00; 13.965 at 01:34:02; 14.5 at 01:34:05; 10 at 01:34:10; 12.5744 at 01:34:11; 16.1 at 01:34:15; 10 at 01:34:20; 13.3 at 01:34:25; 12.3 at 01:34:30; 11.9689 at 01:34:33; 10 01:34:35–01:34:40; 14.7539 at 01:34:42; 16.6 at 01:34:45; 10 at 01:34:50; 16.7 at 01:34:55; 10 01:34:59–01:35:00; 14.2779 at 01:35:03; 11.1 at 01:35:05; 10 at 01:35:10; 13.0964 at 01:35:12; 13.9 at 01:35:15; 12.4 at 01:35:20; 15.2 at 01:35:25; 10 01:35:29–01:35:30; 11.9 at 01:35:35; 11.8 at 01:35:40; 15.3 at 01:35:45; 10 at 01:35:50; 12.5104 at 01:35:54; 12.5 at 01:35:55; 10 at 01:36:00; 11.8 at 01:36:05; 10.7663 at 01:36:07; 10 at 01:36:10; 15.6 at 01:36:15; 10 at 01:36:20; 13.2719 at 01:36:24; 13.3 at 01:36:25; 10 at 01:36:30; 12.4 at 01:36:35; 11.8 01:36:40–01:36:45; 12.5 at 01:36:50; 12.4 at 01:36:55; 12.3 at 01:37:00; 14.7 at 01:37:05; 10 at 01:37:10; 13.8 at 01:37:15; 11.6026 at 01:37:19; 11.6 at 01:37:20; 11 at 01:37:25; 12.2 at 01:37:30; 11.2 at 01:37:35; 10.7781 at 01:37:37; 10.8 at 01:37:40; 13.8972 at 01:37:41; 12.7 at 01:37:45; 11.3 at 01:37:50; 10.8 01:37:55–01:38:00; 14.4399 at 01:38:02; 12.3 at 01:38:05; 10.4509 at 01:38:06; 11.2 at 01:38:10; 11.1 at 01:38:15; 12.5 at 01:38:20; 13.7 at 01:38:25; 10 at 01:38:30; 11.8 at 01:38:35; 11.5 at 01:38:40; 12.3 at 01:38:45; 12.7 at 01:38:50; 12.4 at 01:38:55; 11.1 at 01:39:00; 12.1526 at 01:39:04; 12.2 at 01:39:05; 12.5 at 01:39:10; 14.154 at 01:39:12; 11.5 at 01:39:15; 11.1 at 01:39:20; 15.2 at 01:39:25; 10.7447 at 01:39:26; 10 at 01:39:30; 14.2 at 01:39:35; 11.7 at 01:39:40; 14.4707 at 01:39:44; 14.5 at 01:39:45; 10 at 01:39:50; 13.7 at 01:39:55; 12.7 at 01:40:00; 14.3 at 01:40:05; 10 at 01:40:10; 12 at 01:40:15; 11.6 at 01:40:20; 15.6 at 01:40:25; 10 at 01:40:30; 13.6888 at 01:40:31; 12.8 at 01:40:35; 12.3 at 01:40:40; 14.2 at 01:40:45; 10 at 01:40:50; 12.6956 at 01:40:51; 13.5 at 01:40:55; 10.4 at 01:41:00; 10 at 01:41:05; 12.033 at 01:41:08; 13.3 at 01:41:10; 15.0563 at 01:41:12; 10 01:41:15–01:41:16; 12.3 at 01:41:20; 13.9814 at 01:41:24; 14 at 01:41:25; 10.2 at 01:41:30; 15.6 at 01:41:35; 11.2714 at 01:41:36; 10 at 01:41:40; 11.7 at 01:41:45; 10 at 01:41:50; 14.0001 at 01:41:53; 12.5 at 01:41:55; 11.8 at 01:42:00; 13.4059 at 01:42:02; 12.6 at 01:42:05; 11.3 at 01:42:10; 15.3 at 01:42:15; 10.2 at 01:42:20; 11.9 at 01:42:25; 10.9499 at 01:42:26; 10.4 at 01:42:30 |
| getcart | no cap 01:30:40–01:42:30 |
| postcart | no cap 01:30:40–01:42:30 |
| emptycart | no cap 01:30:40–01:42:30 |

### final_s3_tf_only_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:49:10–02:00:30 |
| postcheckout | no cap 01:49:10–01:50:30; 10 01:50:35–02:00:30 |
| getcart | no cap 01:49:10–02:00:30 |
| postcart | no cap 01:49:10–02:00:30 |
| emptycart | no cap 01:49:10–02:00:30 |

### final_s3_tf_only_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:06:40–02:09:05; 175 02:09:09–02:09:10; no cap 02:09:15–02:09:30; 175 02:09:35–02:09:40; no cap 02:09:45–02:10:05; 175 at 02:10:10; no cap 02:10:15–02:11:00; 175 02:11:05–02:11:10; no cap 02:11:15–02:11:25; 175 02:11:30–02:11:35; no cap 02:11:40–02:18:05 |
| postcheckout | no cap 02:06:40–02:08:00; 10 02:08:05–02:18:05 |
| getcart | no cap 02:06:40–02:09:30; 70 02:09:35–02:09:40; no cap 02:09:45–02:11:00; 70 at 02:11:05; no cap 02:11:10–02:11:25; 70 02:11:27–02:11:35; no cap 02:11:40–02:18:05 |
| postcart | no cap 02:06:40–02:09:05; 90 at 02:09:10; no cap 02:09:15–02:09:30; 90 02:09:35–02:09:40; no cap 02:09:45–02:10:05; 90 at 02:10:10; no cap 02:10:15–02:11:00; 90 02:11:05–02:11:10; no cap 02:11:15–02:11:25; 90 02:11:30–02:11:35; no cap 02:11:39–02:18:05 |
| emptycart | no cap 02:06:40–02:09:05; 10 02:09:08–02:09:10; no cap 02:09:15–02:09:30; 10 02:09:35–02:09:40; no cap 02:09:41–02:10:05; 10 at 02:10:10; no cap 02:10:15–02:11:00; 10 at 02:11:05; no cap 02:11:09–02:11:25; 10 02:11:30–02:11:35; no cap 02:11:40–02:18:05 |

### final_s3_rg_only_burst_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:24:15–02:36:00 |
| postcheckout | no cap 02:24:15–02:36:00 |
| getcart | no cap 02:24:15–02:36:00 |
| postcart | no cap 02:24:15–02:36:00 |
| emptycart | no cap 02:24:15–02:36:00 |

### final_s3_rg_only_burst_run2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:44:20–02:56:10 |
| postcheckout | no cap 02:44:20–02:56:10 |
| getcart | no cap 02:44:20–02:56:10 |
| postcart | no cap 02:44:20–02:56:10 |
| emptycart | no cap 02:44:20–02:56:10 |

### final_s3_both_burst_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:02:55–03:14:45 |
| postcheckout | no cap 03:02:55–03:04:45; 10 03:04:50–03:05:15; 15 at 03:05:20; 12 at 03:05:25; 11.2 at 03:05:30; 14.7 at 03:05:35; 10 at 03:05:40; 13.8207 at 03:05:41; 11 at 03:05:45; 11.7082 at 03:05:46; 14.6 at 03:05:50; 10 at 03:05:55; 13.649 at 03:05:59; 13.6 at 03:06:00; 10 at 03:06:03; 12 at 03:06:05; 10 at 03:06:10; 13 at 03:06:15; 10 at 03:06:20; 10.3 at 03:06:25; 15.4803 at 03:06:29; 15.5 at 03:06:30; 10 at 03:06:35; 12 at 03:06:40; 10 at 03:06:42; 13.1 at 03:06:45; 11.1 at 03:06:50; 11.3 at 03:06:55; 15 at 03:07:00; 12.248 at 03:07:04; 12.2 at 03:07:05; 10.7 at 03:07:10; 15.9 at 03:07:15; 10 at 03:07:20; 10.6 at 03:07:25; 15.4 at 03:07:30; 10.1 at 03:07:35; 10.6202 at 03:07:39; 10.6 at 03:07:40; 13.3 at 03:07:45; 10 at 03:07:50; 11.0043 at 03:07:52; 15.8 at 03:07:55; 10 at 03:08:00; 11.5 at 03:08:05; 14.7 at 03:08:10; 10 at 03:08:15; 17.7 at 03:08:20; 10 at 03:08:22; 12 at 03:08:25; 13.2 at 03:08:30; 10 03:08:31–03:08:35; 17 at 03:08:40; 13.5 at 03:08:45; 10.4808 at 03:08:48; 10 at 03:08:50; 15 at 03:08:55; 10 at 03:09:00; 13.5945 at 03:09:01; 10.2 at 03:09:05; 15.6 at 03:09:10; 12.9 at 03:09:15; 11.3 at 03:09:20; 14.6 at 03:09:25; 10 at 03:09:30; 15.6 at 03:09:35; 10 at 03:09:40; 10.3 at 03:09:45; 15.6 at 03:09:50; 12.2741 at 03:09:54; 12.3 at 03:09:55; 10 at 03:10:00; 12.8 at 03:10:05; 14.8 at 03:10:10; 10.6 at 03:10:15; 11.2 at 03:10:20; 14.2 at 03:10:25; 10.6 at 03:10:30; 13.3507 at 03:10:31; 10.4 at 03:10:35; 15.8 at 03:10:40; 12.8466 at 03:10:44; 12.8 at 03:10:45; 14.8 at 03:10:50; 10 at 03:10:55; 16.3 at 03:11:00; 10.8 at 03:11:05; 11.2 at 03:11:10; 11.9 at 03:11:15; 15.8339 at 03:11:17; 11.1 at 03:11:20; 10.8 at 03:11:25; 14.8249 at 03:11:26; 10 at 03:11:30; 10.4 at 03:11:35; 15.1487 at 03:11:39; 15.1 at 03:11:40; 10.8 at 03:11:45; 12.2 at 03:11:50; 10 at 03:11:55; 14.9241 at 03:11:56; 15.2 at 03:12:00; 10.3 at 03:12:05; 12.366 at 03:12:09; 12.4 at 03:12:10; 14.5 at 03:12:15; 10 at 03:12:20; 11.0269 at 03:12:22; 14.1 at 03:12:25; 11.3 at 03:12:30; 12.395 at 03:12:31; 12.1 03:12:35–03:12:40; 15.9 at 03:12:45; 13.0593 at 03:12:47; 10 at 03:12:50; 12.8 at 03:12:55; 10 at 03:13:00; 16.5 at 03:13:05; 10 at 03:13:10; 14.9 at 03:13:15; 10 at 03:13:20; 13.303 at 03:13:21; 10.2 at 03:13:25; 15.8 at 03:13:30; 10.5257 at 03:13:34; 10.5 at 03:13:35; 12.8 at 03:13:40; 15.1 at 03:13:45; 14.2496 at 03:13:47; 12 at 03:13:50; 10.7 at 03:13:55; 13.9861 at 03:13:59; 14 at 03:14:00; 12 at 03:14:05; 10 at 03:14:10; 16.4 at 03:14:15; 14.6731 at 03:14:16; 10 at 03:14:20; 12.3 at 03:14:25; 10.8382 at 03:14:29; 10.8 at 03:14:30; 11 at 03:14:35; 14.4 at 03:14:40; 10.1929 at 03:14:42; 10 at 03:14:45 |
| getcart | no cap 03:02:55–03:14:45 |
| postcart | no cap 03:02:55–03:14:45 |
| emptycart | no cap 03:02:55–03:14:45 |

### final_s3_both_burst_run2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:25:15–03:37:05 |
| postcheckout | no cap 03:25:15–03:27:05; 10 at 03:27:10; no cap at 03:27:13; 10 03:27:15–03:27:35; 13.8 at 03:27:40; 10.5297 at 03:27:44; 10.5 at 03:27:45; 14.6 at 03:27:50; 10.2 at 03:27:55; 14.8 at 03:28:00; 10.4836 at 03:28:01; 10 03:28:05–03:28:10; 14.6 at 03:28:15; 10 at 03:28:20; 11.2 at 03:28:25; 13.7 at 03:28:30; 14.9 at 03:28:35; 10 at 03:28:40; 14.2 at 03:28:45; 11.2 at 03:28:50; 14.6238 at 03:28:51; 10 at 03:28:55; 13.4257 at 03:28:59; 13.4 at 03:29:00; 12 at 03:29:05; 10 at 03:29:10; 13.3 at 03:29:15; 14.0322 at 03:29:16; 10 at 03:29:20; 12.2 at 03:29:25; 13.2 at 03:29:30; 12.5076 at 03:29:34; 12.5 at 03:29:35; 11 at 03:29:40; 11.5182 at 03:29:43; 12.1 at 03:29:45; 10 at 03:29:50; 10.5 at 03:29:55; 14.2 at 03:30:00; 13.8 at 03:30:05; 10 at 03:30:10; 12 at 03:30:15; 11.7 at 03:30:20; 11.4 at 03:30:25; 10.3 at 03:30:30; 10.0257 at 03:30:32; 12.8 at 03:30:35; 10 at 03:30:40; 10.6 at 03:30:45; 11.5 at 03:30:50; 15.3 at 03:30:55; 15.1807 at 03:30:57; 10 at 03:31:00; 13.2 at 03:31:05; 14.4 at 03:31:10; 10 at 03:31:15; 11.2 at 03:31:20; 12.3 at 03:31:25; 10 03:31:30–03:31:35; 14.9 at 03:31:40; 10 at 03:31:42; 11.8 at 03:31:45; 12.2 at 03:31:50; 13.7 at 03:31:55; 10.0726 at 03:31:59; 10.1 at 03:32:00; 13.4 at 03:32:05; 10 at 03:32:10; 12.5 at 03:32:15; 10.6 at 03:32:20; 13.1 at 03:32:25; 10.6 at 03:32:30; 10 at 03:32:35; 13.1 at 03:32:40; 10 at 03:32:41; 10.4 at 03:32:45; 11.6 at 03:32:50; 12.7 at 03:32:55; 15.1 at 03:33:00; 10 03:33:02–03:33:05; 14.4673 at 03:33:06; 14.9 at 03:33:10; 10.8 at 03:33:15; 10.6803 at 03:33:19; 10.7 at 03:33:20; 14 at 03:33:25; 10 at 03:33:30; 10.4 at 03:33:35; 12.4717 at 03:33:36; 13 at 03:33:40; 10 at 03:33:45; 15.153 at 03:33:49; 15.2 at 03:33:50; 10.2 at 03:33:55; 13.8 at 03:34:00; 13.1 at 03:34:05; 10 at 03:34:10; 10.2 at 03:34:15; 13.9898 at 03:34:19; 14 at 03:34:20; 12.8 at 03:34:25; 10 at 03:34:30; 10.6831 at 03:34:32; 14.4 at 03:34:35; 10 at 03:34:40; 13.0965 at 03:34:41; 11.8 at 03:34:45; 13.12 at 03:34:49; 13.1 at 03:34:50; 14.3 at 03:34:55; 10 03:35:00–03:35:05; 14.9 at 03:35:10; 13.8917 at 03:35:14; 13.9 at 03:35:15; 12 at 03:35:20; 10 at 03:35:25; 13.8 at 03:35:30; 10 at 03:35:35; 14.5 at 03:35:40; 13.6 at 03:35:45; 15.043 at 03:35:48; 10.7 at 03:35:50; 12.8 at 03:35:55; 14.7102 at 03:35:57; 10 at 03:36:00; 11.2 at 03:36:05; 11.4652 at 03:36:09; 11.5 at 03:36:10; 11.0479 at 03:36:13; 13.5 at 03:36:15; 10 at 03:36:20; 11.8 at 03:36:25; 11.5 at 03:36:30; 13.1 at 03:36:35; 10.8 at 03:36:40; 10 at 03:36:45; 13.0573 at 03:36:47; 15.3 at 03:36:50; 10.7317 at 03:36:51; 10 at 03:36:55; 11.4 at 03:37:00; 13.6 at 03:37:05 |
| getcart | no cap 03:25:15–03:37:05 |
| postcart | no cap 03:25:15–03:37:05 |
| emptycart | no cap 03:25:15–03:37:05 |

## One paragraph per launch

**final_s3_rg_only_normal_run1_r2.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T00:25:42Z, rpr 2.42, and did not climb. Outbound retry delta to checkoutservice was 499. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **601/711 (84.5%)**.

**final_s3_rg_only_normal_run2.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T00:50:54Z, rpr 1.32, and did not climb. Outbound retry delta to checkoutservice was 459. grpc_4 / grpc_14 is adservice 3 / 0; recommendationservice, productcatalogservice, currencyservice are 0 / 0. checkoutservice was the only detector-hot service: overloaded fraction **597/711 (84.0%)**.

**final_s3_both_normal_run1.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T01:14:34Z, rpr 1.25, and did not climb. Outbound retry delta to checkoutservice was 338. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **599/713 (84.0%)**.

**final_s3_both_normal_run2.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T01:32:56Z, rpr 1.83, and did not climb. Outbound retry delta to checkoutservice was 341. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **600/713 (84.2%)**.

**final_s3_tf_only_run1.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta to checkoutservice was 10,670. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **599/688 (87.1%)**.

**final_s3_tf_only_run2.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta to checkoutservice was 10,327. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **599/688 (87.1%)**.

**final_s3_rg_only_burst_run1.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T02:26:22Z, rpr 1.38, and did not climb. The shed line is metric=rpr. Burst sheds on this edge were 0. Outbound retry delta to checkoutservice was 345. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **598/710 (84.2%)**.

**final_s3_rg_only_burst_run2.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T02:46:40Z, rpr 1.61, and did not climb. The shed line is metric=rpr. Burst sheds on this edge were 0. Outbound retry delta to checkoutservice was 532. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **599/711 (84.2%)**.

**final_s3_both_burst_run1.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T03:05:13Z, rpr 2.57, and did not climb. The shed line is metric=rpr. Burst sheds on this edge were 0. Outbound retry delta to checkoutservice was 354. grpc_4 / grpc_14 is adservice 6 / 0; recommendationservice, productcatalogservice, currencyservice are 0 / 0. checkoutservice was the only detector-hot service: overloaded fraction **599/714 (83.9%)**.

**final_s3_both_burst_run2.** frontend → checkoutservice shed once, ON→OFF from 3 at 2026-10-13T03:27:33Z, rpr 2.29, and did not climb. The shed line is metric=rpr. Burst sheds on this edge were 0. Outbound retry delta to checkoutservice was 334. grpc_4 / grpc_14 is 0 / 0 on recommendationservice, productcatalogservice, currencyservice, and adservice. checkoutservice was the only detector-hot service: overloaded fraction **598/714 (83.8%)**.

## Related

- [S3 and S4 mode matrix plan](../../docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix.md)
- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [(a) / (b) / (c) reading](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md)
- [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md)
- [ADR 0008](../../docs/adr/0008-locked-retryguard-parameters.md)
- [ADR 0009](../../docs/adr/0009-paper-c1-default-cpu-table.md)
