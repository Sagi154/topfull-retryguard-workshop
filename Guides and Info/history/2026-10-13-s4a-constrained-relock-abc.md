# S4A constrained relock — (a) / (b) / (c)

## Setup

Scenario 4A constrained, 600 s. Mix 50 / 20 / 50 / 600 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1, with productcatalogservice constrained to 100 m. Frontend HPA min = max = 4. productcatalogservice HPA min = max = 1. Frontend sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off between holds is 120 s. RetryGuard uses the locked parameters. Burst holds set `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal-mode RetryGuard holds omit those three keys. TopFull-only has no `retryguard.log`. Each cell is two repeats. The bold bar splits the pairs.

Replays followed the gate in force at launch. Re-gated 2026-10-14: a catalog replica gap is recorded, not a gate. A locust row count outside 540–580, or `live5s_caps` above 0 on a TopFull-off hold, stays INVALID. The tabulated column was chosen before the re-gate and was left in place, except the two RetryGuard-only burst columns. Those were replaced on 2026-10-14 with `final_4a_constrained_rg_only_burst_run5_r2` and `final_4a_constrained_rg_only_burst_run6` after `final_4a_constrained_rg_only_burst_run5` failed the row-count gate. `Guides and Info/history/2026-10-13-s4a-constrained-mode-matrix-abc.md` is catalog 50 m and mix 10 / 10 / 10 / 600 / 5. It is not a column here.

Scored folders:

- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3_r2`
- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3_r2`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run5_r2`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run6`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4_r2`

## Index

| Hold | log_folder | Mode | TopFull | In this guide |
| --- | --- | --- | --- | --- |
| 1 | final_4a_constrained_rg_only_normal_run3 | normal | off | PASS, catalog replica gap (catalog_1 85/87), re-gated 2026-10-14: recorded, not a gate, kept, not scored |
| 1 replay | final_4a_constrained_rg_only_normal_run3_r2 | normal | off | PASS, scored |
| 2 | final_4a_constrained_rg_only_normal_run4 | normal | off | PASS, catalog replica gap (catalog_1 77/80), re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 2 replay | final_4a_constrained_rg_only_normal_run4_r2 | normal | off | PASS, catalog replica gap (catalog_1 89/97), re-gated 2026-10-14: recorded, not a gate, not scored |
| 3 | final_4a_constrained_both_normal_run3 | normal | on | first launch exited 1 before Locust, not gated; relaunch PASS, catalog replica gap (catalog_1 103/106), re-gated 2026-10-14: recorded, not a gate, scored |
| 3 replay | final_4a_constrained_both_normal_run3_r2 | normal | on | INVALID, locust_rows 535, not scored |
| 4 | final_4a_constrained_both_normal_run4 | normal | on | PASS, scored |
| 5 | final_4a_constrained_tf_only_run3 | tf | on | PASS, catalog replica gap (catalog_1 95/96), re-gated 2026-10-14: recorded, not a gate, kept, not scored |
| 5 replay | final_4a_constrained_tf_only_run3_r2 | tf | on | PASS, scored |
| 6 | final_4a_constrained_tf_only_run4 | tf | on | PASS, scored |
| 7 | final_4a_constrained_rg_only_burst_run3 | burst_rpr 2.0 | off | INVALID, live5s_caps with TopFull off, not scored |
| 7 replay | final_4a_constrained_rg_only_burst_run3_r2 | burst_rpr 2.0 | off | INVALID, live5s_caps with TopFull off, not scored |
| 8 | final_4a_constrained_rg_only_burst_run4 | burst_rpr 2.0 | off | INVALID, live5s_caps with TopFull off, not scored |
| 8 replay | final_4a_constrained_rg_only_burst_run4_r2 | burst_rpr 2.0 | off | INVALID, live5s_caps with TopFull off, not scored |
| rerun | final_4a_constrained_rg_only_burst_run5 | burst_rpr 2.0 | off | INVALID, locust_rows 535, not scored |
| rerun | final_4a_constrained_rg_only_burst_run5_r2 | burst_rpr 2.0 | off | PASS, catalog_not_ready=0, live5s_caps=0, throttle FLAG, scored |
| rerun | final_4a_constrained_rg_only_burst_run6 | burst_rpr 2.0 | off | PASS, catalog_not_ready=0, live5s_caps=0, throttle FLAG, scored |
| 9 | final_4a_constrained_both_burst_run3 | burst_rpr 2.0 | on | PASS, catalog replica gap (catalog_1 109/112), re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 9 replay | final_4a_constrained_both_burst_run3_r2 | burst_rpr 2.0 | on | PASS, catalog replica gap (catalog_1 99/102), re-gated 2026-10-14: recorded, not a gate, not scored |
| 10 | final_4a_constrained_both_burst_run4 | burst_rpr 2.0 | on | PASS, catalog replica gap (catalog_1 151/152), re-gated 2026-10-14: recorded, not a gate, kept, not scored |
| 10 replay | final_4a_constrained_both_burst_run4_r2 | burst_rpr 2.0 | on | PASS, scored |

Table columns follow the ten scored rows, in that order. A launch that is not scored stays on disk and is not a column.

## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars: final_4a_constrained_rg_only_burst_run5_r2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_constrained_rg_only_burst_run6 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_constrained_both_burst_run3 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_constrained_both_burst_run4_r2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

The START line on those four holds sets `burst_window_seconds=5` and `burst_min_first_attempts=20`. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s.

## (a) Edge rpr

Edges with a tick above the shed bar, or a non-zero retry delta, are below. A bold file-streak cell is at least 30 seconds. The parenthetical is the controller `high` when a `retryguard.log` exists. File-streak unit is seconds.

### File streak seconds / ticks above the shed bar (controller high)

| Edge | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | 2 / 6 (2) | 0 / 5 (1) | **┃** | 2 / 7 (2) | 0 / 5 (1) | **┃** | 0 / 6 | 2 / 8 | **┃** | 0 / 3 (1) | 0 / 0 (0) | **┃** | 2 / 6 (2) | 2 / 7 (2) |
| frontend → productcatalogservice | 2 / 7 (2) | 22 / 14 (11) | **┃** | 2 / 7 (2) | 0 / 7 (1) | **┃** | 2 / 8 | 0 / 5 | **┃** | 0 / 1 (1) | 6 / 21 (7) | **┃** | 2 / 8 (2) | 2 / 9 (2) |
| frontend → recommendationservice | 24 / 37 (11) | 22 / 48 (11) | **┃** | 24 / 76 (11) | 8 / 5 (5) | **┃** | 18 / 10 | 8 / 13 | **┃** | 11 / 17 (7) | 12 / 13 (9) | **┃** | 0 / 0 (0) | 14 / 40 (6) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0 / 0 (0) | 0 / 0 (0) |

### Mean / median / max / volume rpr

| Edge | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | 0.065 / 0.000 / 2.38 / 0.033 | 0.085 / 0.000 / 3.88 / 0.024 | **┃** | 0.071 / 0.000 / 3.18 / 0.035 | 0.037 / 0.000 / 1.34 / 0.021 | **┃** | 0.069 / 0.000 / 3.10 / 0.047 | 0.041 / 0.000 / 0.82 / 0.031 | **┃** | 0.019 / 0.000 / 9.00 / 0.002 | 0.001 / 0.000 / 0.38 / 0.001 | **┃** | 0.046 / 0.000 / 1.70 / 0.033 | 0.097 / 0.000 / 6.33 / 0.043 |
| frontend → productcatalogservice | 0.117 / 0.000 / 7.05 / 0.055 | 0.124 / 0.000 / 1.26 / 0.102 | **┃** | 0.068 / 0.000 / 3.00 / 0.035 | 0.144 / 0.000 / 4.84 / 0.050 | **┃** | 0.096 / 0.000 / 2.84 / 0.060 | 0.045 / 0.000 / 1.52 / 0.035 | **┃** | 0.008 / 0.000 / 0.74 / 0.007 | 0.047 / 0.000 / 2.11 / 0.036 | **┃** | 0.064 / 0.000 / 3.90 / 0.029 | 0.081 / 0.000 / 2.79 / 0.034 |
| frontend → recommendationservice | 0.297 / 0.000 / 3.29 / 0.213 | 0.384 / 0.000 / 3.23 / 0.311 | **┃** | 0.499 / 0.000 / 3.10 / 0.602 | 0.027 / 0.000 / 1.99 / 0.033 | **┃** | 0.061 / 0.000 / 2.24 / 0.071 | 0.060 / 0.000 / 2.40 / 0.069 | **┃** | 0.044 / 0.000 / 4.45 / 0.023 | 0.044 / 0.000 / 3.46 / 0.027 | **┃** | 0.002 / 0.000 / 0.14 / 0.002 | 0.177 / 0.000 / 2.90 / 0.188 |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

### Climb streaks, 1-attempt / 2-attempt

| Edge | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → productcatalogservice | — / — | 6 / 5 | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | 6 / 6 | 6 / 6 | **┃** | 6 / 6 | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | 6 / 6 |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — / — | — / — |

## 4a Burst

Burst mode was off on the six normal and TopFull-only holds.

On the four burst holds the (a2) burst window is below. Cell shape is peak `burst_rpr5` / median `burst_rpr5` / samples at the bar in force / burst sheds (`burst_rpr5` samples).

| Edge | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | 0.06 / 0.00 / 0 / 0 (597) | 0.03 / 0.00 / 0 / 0 (597) | **┃** | 0.74 / 0.00 / 0 / 0 (210) | 0.90 / 0.00 / 0 / 0 (194) |
| frontend → checkoutservice | 0.00 / 0.00 / 0 / 0 (405) | 0.00 / 0.00 / 0 / 0 (530) | **┃** | 0.00 / 0.00 / 0 / 0 (204) | 0.00 / 0.00 / 0 / 0 (185) |
| checkoutservice → paymentservice | 0.00 / 0.00 / 0 / 0 (400) | 0.00 / 0.00 / 0 / 0 (531) | **┃** | 0.00 / 0.00 / 0 / 0 (204) | 0.00 / 0.00 / 0 / 0 (185) |
| frontend → cartservice | 0.00 / 0.00 / 0 / 0 (600) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| checkoutservice → cartservice | 0.00 / 0.00 / 0 / 0 (543) | 0.00 / 0.00 / 0 / 0 (570) | **┃** | 0.00 / 0.00 / 0 / 0 (206) | 0.00 / 0.00 / 0 / 0 (188) |
| frontend → currencyservice | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (599) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (305) |
| checkoutservice → emailservice | 0.00 / 0.00 / 0 / 0 (403) | 0.00 / 0.00 / 0 / 0 (531) | **┃** | 0.00 / 0.00 / 0 / 0 (204) | 0.00 / 0.00 / 0 / 0 (185) |
| checkoutservice → currencyservice | 0.00 / 0.00 / 0 / 0 (402) | 0.00 / 0.00 / 0 / 0 (531) | **┃** | 0.00 / 0.00 / 0 / 0 (204) | 0.00 / 0.00 / 0 / 0 (185) |
| frontend → adservice | 0.00 / 0.00 / 0 / 0 (594) | 0.00 / 0.00 / 0 / 0 (592) | **┃** | 0.00 / 0.00 / 0 / 0 (207) | 0.00 / 0.00 / 0 / 0 (188) |
| frontend → recommendationservice | 2.06 / 0.02 / 1 / 1 (30) | 2.14 / 0.00 / 1 / 1 (44) | **┃** | 0.05 / 0.00 / 0 / 0 (305) | 2.14 / 0.00 / 5 / 5 (226) |
| frontend → shippingservice | 0.00 / 0.00 / 0 / 0 (594) | 0.00 / 0.00 / 0 / 0 (590) | **┃** | 0.00 / 0.00 / 0 / 0 (207) | 0.00 / 0.00 / 0 / 0 (190) |
| frontend → productcatalogservice | 0.09 / 0.00 / 0 / 0 (600) | 1.05 / 0.01 / 0 / 0 (601) | **┃** | 0.75 / 0.00 / 0 / 0 (211) | 0.67 / 0.00 / 0 / 0 (195) |
| checkoutservice → shippingservice | 0.00 / 0.00 / 0 / 0 (541) | 0.00 / 0.00 / 0 / 0 (570) | **┃** | 0.00 / 0.00 / 0 / 0 (207) | 0.00 / 0.00 / 0 / 0 (188) |

Burst sheds are the `ON→OFF burst` column of the scorer toggle table. `final_4a_constrained_rg_only_burst_run5_r2` has 1 burst shed and 0 normal sheds, on frontend → recommendationservice. `final_4a_constrained_rg_only_burst_run6` has 1 burst shed and 0 normal sheds, on frontend → recommendationservice. `final_4a_constrained_both_burst_run3` has no transition lines. `final_4a_constrained_both_burst_run4_r2` has 5 burst sheds and 0 normal sheds, all on frontend → recommendationservice.

## Rejection beside (a)

Longest streak / count of inbound rejection above 0.20. Bold when a controlled service's streak is at least 30. frontend and redis-cart stay plain.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 86 / 155 | 86 / 200 | **┃** | 88 / 133 | 82 / 164 | **┃** | 85 / 148 | 84 / 146 | **┃** | 2 / 2 | 3 / 8 | **┃** | 72 / 109 | 87 / 128 |
| checkoutservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 29 / 145 | 15 / 99 | **┃** | 14 / 97 | 6 / 8 | **┃** | 11 / 11 | 6 / 16 | **┃** | **202 / 568** | **33 / 439** | **┃** | 0 / 0 | 9 / 53 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 2 / 8 | 13 / 22 | **┃** | 1 / 7 | 1 / 7 | **┃** | 1 / 9 | 2 / 11 | **┃** | 1 / 4 | 7 / 31 | **┃** | 2 / 12 | 2 / 8 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak / count under the re-enable bar 0.25.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 22 / 154 | 17 / 108 | **┃** | 37 / 176 | 28 / 144 | **┃** | 22 / 151 | 21 / 161 | **┃** | 612 / 612 | 546 / 608 | **┃** | 64 / 198 | 32 / 181 |
| checkoutservice | 53 / 159 | 59 / 128 | **┃** | 54 / 187 | 95 / 153 | **┃** | 147 / 172 | 156 / 180 | **┃** | 100 / 570 | 73 / 588 | **┃** | 180 / 209 | 122 / 193 |
| recommendationservice | 85 / 165 | 85 / 210 | **┃** | 95 / 215 | 251 / 300 | **┃** | 144 / 292 | 183 / 288 | **┃** | 25 / 67 | 38 / 195 | **┃** | 307 / 307 | 134 / 259 |
| paymentservice | 53 / 159 | 74 / 129 | **┃** | 65 / 187 | 95 / 153 | **┃** | 147 / 172 | 156 / 180 | **┃** | 100 / 570 | 73 / 588 | **┃** | 180 / 209 | 122 / 193 |
| emailservice | 53 / 160 | 93 / 131 | **┃** | 44 / 183 | 95 / 153 | **┃** | 147 / 171 | 156 / 181 | **┃** | 123 / 566 | 88 / 587 | **┃** | 180 / 209 | 122 / 193 |
| productcatalogservice | 51 / 166 | 18 / 117 | **┃** | 45 / 186 | 29 / 147 | **┃** | 29 / 162 | 45 / 168 | **┃** | 370 / 611 | 123 / 590 | **┃** | 93 / 202 | 76 / 187 |
| cartservice | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 613 / 613 | 612 / 612 | **┃** | 307 / 307 | 307 / 307 |
| currencyservice | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 | **┃** | 613 / 613 | 613 / 613 | **┃** | 307 / 307 | 307 / 307 |
| shippingservice | 138 / 171 | 93 / 134 | **┃** | 107 / 191 | 96 / 154 | **┃** | 149 / 175 | 156 / 180 | **┃** | 613 / 613 | 533 / 611 | **┃** | 181 / 211 | 122 / 193 |
| adservice | 99 / 169 | 93 / 134 | **┃** | 107 / 190 | 95 / 151 | **┃** | 148 / 173 | 156 / 181 | **┃** | 459 / 610 | 533 / 608 | **┃** | 180 / 210 | 122 / 193 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 15 / 131 | 14 / 75 | **┃** | 13 / 76 | 4 / 5 | **┃** | 10 / 10 | 3 / 10 | **┃** | 5 / 92 | 2 / 34 | **┃** | 0 / 0 | 7 / 37 |
| productcatalogservice | 2 / 2 | 11 / 13 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 86 / 206 | 86 / 243 | **┃** | 103 / 235 | 275 / 304 | **┃** | 268 / 296 | 183 / 294 | **┃** | 78 / 566 | 127 / 600 | **┃** | 307 / 307 | 140 / 284 |
| productcatalogservice | 85 / 171 | 48 / 135 | **┃** | 107 / 192 | 96 / 154 | **┃** | 113 / 174 | 95 / 180 | **┃** | 612 / 612 | 612 / 612 | **┃** | 182 / 212 | 122 / 195 |
| currencyservice | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 | **┃** | 613 / 613 | 613 / 613 | **┃** | 307 / 307 | 307 / 307 |
| adservice | 99 / 169 | 93 / 134 | **┃** | 107 / 190 | 95 / 151 | **┃** | 148 / 173 | 156 / 181 | **┃** | 459 / 610 | 533 / 608 | **┃** | 180 / 210 | 122 / 193 |

gRPC counted in the rejection rate on the four read callees and in the retry policy. Cell is grpc_4 / grpc_14.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 15,538 / 0 | 12,372 / 0 | **┃** | 14,219 / 0 | 361 / 0 | **┃** | 1,036 / 0 | 695 / 0 | **┃** | 21,506 / 0 | 16,979 / 0 | **┃** | 24 / 0 | 4,335 / 0 |
| productcatalogservice | 2,658 / 7,106 | 10,079 / 3,681 | **┃** | 407 / 8,612 | 845 / 7,734 | **┃** | 806 / 13,241 | 684 / 7,317 | **┃** | 1,038 / 0 | 9,158 / 0 | **┃** | 100 / 8,217 | 685 / 8,192 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

Share of detector samples at or above 1. Bold when the share is at least 0.5. productcatalogservice is the highest share on every column. On `final_4a_constrained_rg_only_burst_run5_r2` and `final_4a_constrained_rg_only_burst_run6` that share is 60.3% and 57.8%. On the other eight columns it stays between 24.5% and 39.3%.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| checkoutservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| recommendationservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| paymentservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| emailservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| productcatalogservice | 216/726 (29.8%) | 177/723 (24.5%) | **┃** | 254/727 (34.9%) | 187/723 (25.9%) | **┃** | 223/706 (31.6%) | 244/697 (35.0%) | **┃** | **434/720 (60.3%)** | **414/716 (57.8%)** | **┃** | 283/721 (39.3%) | 262/727 (36.0%) |
| cartservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| currencyservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| shippingservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| adservice | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |
| redis-cart | 0/726 (0.0%) | 0/723 (0.0%) | **┃** | 0/727 (0.0%) | 0/723 (0.0%) | **┃** | 0/706 (0.0%) | 0/697 (0.0%) | **┃** | 0/720 (0.0%) | 0/716 (0.0%) | **┃** | 0/721 (0.0%) | 0/727 (0.0%) |

## (c) Retry volume

Outbound retry delta by target.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 8,811 | 11,058 | **┃** | 16,624 | 569 | **┃** | 1,449 | 1,078 | **┃** | 1,167 | 1,297 | **┃** | 42 | 4,950 |
| productcatalogservice | 11,643 | 15,630 | **┃** | 7,885 | 9,079 | **┃** | 12,456 | 7,784 | **┃** | 3,105 | 15,926 | **┃** | 6,777 | 8,335 |
| checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0 | 0 |

Inbound resets.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 122 | 157 | **┃** | 146 | 53 | **┃** | 16 | 61 | **┃** | 318 | 349 | **┃** | 12 | 88 |
| checkoutservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| recommendationservice | 9,302 | 6,894 | **┃** | 8,491 | 265 | **┃** | 663 | 491 | **┃** | 5,880 | 3,439 | **┃** | 18 | 2,601 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 3,325 | 6,391 | **┃** | 714 | 1,465 | **┃** | 1,092 | 1,180 | **┃** | 1,617 | 6,037 | **┃** | 162 | 1,111 |
| cartservice | 0 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 1 | 18 | **┃** | 0 | 0 |
| currencyservice | 3 | 3 | **┃** | 3 | 2 | **┃** | 0 | 0 | **┃** | 6 | 6 | **┃** | 0 | 3 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

## RetryGuard toggles

`ON→OFF` is a shed from the current attempt cap to 0. `0→1` is the re-enable (`OFF→ON`). `1→2` and `2→3` are climbs. On a burst row, `Value` is the 5 s aggregate `ΣΔretry / ΣΔfirst`, and the step is tagged `(burst)`. TopFull-only has no `retryguard.log`.

### Part 1

### final_4a_constrained_rg_only_normal_run3_r2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 3 | 0 | 2 | 2 |
| recommendationservice | 0 | 2 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T15:39:40Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.59 |
| 2026-10-13T15:43:41Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T15:43:53Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T15:44:05Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T15:45:05Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.98 |
| 2026-10-13T15:45:42Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T15:45:54Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T15:46:06Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T15:48:31Z | frontend → recommendationservice | ON→OFF | 3 | rpr 3.05 |

### final_4a_constrained_rg_only_normal_run4

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 4 | 0 | 4 | 3 |
| recommendationservice | 0 | 4 | 0 | 0 |
| frontend → productcatalogservice | 1 | 0 | 1 | 1 |
| productcatalogservice | 0 | 1 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T15:59:19Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.62 |
| 2026-10-13T16:01:21Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T16:01:23Z | frontend → productcatalogservice | ON→OFF | 3 | rpr 1.04 |
| 2026-10-13T16:01:39Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T16:01:49Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T16:01:51Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T16:02:23Z | frontend → productcatalogservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T16:02:35Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.06 |
| 2026-10-13T16:02:58Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T16:03:10Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T16:03:22Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T16:04:11Z | frontend → productcatalogservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T16:04:33Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.41 |
| 2026-10-13T16:04:57Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T16:05:09Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T16:05:21Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T16:07:47Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.81 |
| 2026-10-13T16:08:17Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T16:08:29Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |

### final_4a_constrained_both_normal_run3

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 3 | 0 | 3 | 2 |
| recommendationservice | 0 | 3 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T17:15:51Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.58 |
| 2026-10-13T17:16:19Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T17:16:31Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T17:17:12Z | frontend → recommendationservice | ON→OFF | 2 | rpr 1.31 |
| 2026-10-13T17:18:31Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T17:18:43Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T17:18:55Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T17:21:17Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.41 |
| 2026-10-13T17:21:58Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T17:22:10Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T17:22:22Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

final_4a_constrained_both_normal_run4: no transition lines.
final_4a_constrained_tf_only_run3_r2: no transition lines.
final_4a_constrained_tf_only_run4: no transition lines.

### final_4a_constrained_rg_only_burst_run5_r2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 | 1 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T18:09:26Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.06 |

### final_4a_constrained_rg_only_burst_run6

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 | 1 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T18:29:04Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.14 |

final_4a_constrained_both_burst_run3: no transition lines.

### final_4a_constrained_both_burst_run4_r2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 5 | 0 | 4 | 2 | 5 |
| recommendationservice | 0 | 5 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T21:23:17Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.14 |
| 2026-10-13T21:23:42Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T21:23:54Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T21:24:08Z | frontend → recommendationservice | ON→OFF (burst) | 2 | rpr 1.61 |
| 2026-10-13T21:24:56Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T21:25:36Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.05 |
| 2026-10-13T21:25:44Z | frontend → recommendationservice | ON→OFF (burst) | 2 | rpr 1.36 |
| 2026-10-13T21:26:11Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T21:26:21Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.71 |
| 2026-10-13T21:26:45Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T21:26:57Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T21:27:09Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T21:27:35Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.03 |
| 2026-10-13T21:28:08Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T21:28:20Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T21:28:32Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

### Part 2, per edge that sheds

`ON→OFF / OFF→ON` counts the edge's sheds and the callee's re-enables. A parenthetical is the burst-shed count. Shed rpr values are in time order; `b` marks `metric=rpr_burst`. First shed is seconds after the first `OBSERVE` line. Attempts after re-enable is the edge's attempt count on its last log line. Time OFF is seconds from each shed to the next callee `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is the min and median of `metric=rejection` samples for that callee inside each OFF window. The streak counts those samples strictly below 0.25. An em dash means that edge did not go to 0 on that hold. TopFull-only columns are an em dash because there is no `retryguard.log`.

#### frontend → recommendationservice

| frontend → recommendationservice | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 3 / 2 | 4 / 4 | **┃** | 3 / 3 | 0 / 0 | **┃** | — | — | **┃** | 1 (1) / 0 | 1 (1) / 0 | **┃** | 0 / 0 | 5 (5) / 5 |
| Shed rpr | 2.59; 2.98; 3.05 | 2.62; 2.06; 2.41; 2.81 | **┃** | 2.58; 1.31; 2.41 | — | **┃** | — | — | **┃** | 2.06b | 2.14b | **┃** | — | 2.14b; 1.61b; 1.36b; 0.71b; 2.03b |
| First shed, seconds after first OBSERVE | 52 | 58 | **┃** | 69 | — | **┃** | — | — | **┃** | 38 | 47 | **┃** | — | 57 |
| Attempts after re-enable | 0 | 2 | **┃** | 3 | — | **┃** | — | — | **┃** | 0 | 0 | **┃** | — | 3 |
| Time OFF (s) | 241; 37; 29 | 122; 23; 24; 30 | **┃** | 28; 79; 41 | — | **┃** | — | — | **┃** | 574 | 566 | **┃** | — | 25; 48; 27; 24; 33 |
| OFF rejection min / median | 0.000 / 0.682; 0.000 / 0.000; 0.000 / 0.000 | 0.000 / 0.556; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000 | **┃** | 0.000 / 0.000; 0.000 / 0.146; 0.000 / 0.036 | — | **┃** | — | — | **┃** | 0.000 / 0.523 | 0.000 / 0.428 | **┃** | — | 0.000 / 0.000; 0.000 / 0.067; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.092 |
| Longest streak under 0.25 | 10; 10; 10 | 10; 10; 10; 10 | **┃** | 10; 10; 10 | — | **┃** | — | — | **┃** | 3 | 9 | **┃** | — | 10; 10; 10; 10; 10 |

`final_4a_constrained_both_normal_run3` and `final_4a_constrained_both_burst_run4_r2` re-enabled and ended at 3 attempts, and `final_4a_constrained_rg_only_normal_run4` re-enabled and ended at 2. `final_4a_constrained_rg_only_normal_run3_r2` re-enabled an earlier shed and was still at 0 at exit. `final_4a_constrained_rg_only_burst_run5_r2` and `final_4a_constrained_rg_only_burst_run6` each shed once and were still at 0 at exit. `final_4a_constrained_both_normal_run4` and `final_4a_constrained_both_burst_run3` never shed. The longest under-bar streak in the table is 10 samples. The two new windows are 3 and 9 samples.

#### frontend → productcatalogservice

| frontend → productcatalogservice | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | — | — | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| Shed rpr | — | 1.04 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| First shed, seconds after first OBSERVE | — | 182 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Attempts after re-enable | — | 3 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Time OFF (s) | — | 26 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| OFF rejection min / median | — | 0.000 / 0.000 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Longest streak under 0.25 | — | 10 | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

Only `final_4a_constrained_rg_only_normal_run4` shed (rpr 1.04), re-enabled, and climbed to 3 attempts. Its under-bar streak is 10. Every other scored column is `0 / 0` or an em dash.

#### recommendationservice → productcatalogservice

| recommendationservice → productcatalogservice | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | — | — | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| Shed rpr | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| First shed, seconds after first OBSERVE | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Attempts after re-enable | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Time OFF (s) | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| OFF rejection min / median | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Longest streak under 0.25 | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

No scored column shed recommendationservice → productcatalogservice. Every cell in that table is `0 / 0` or an em dash.

## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.

| API | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 1.4 | 1.2 | **┃** | 4.3 | 3.8 | **┃** | 4.7 | 4.0 | **┃** | 8.0 | 2.4 | **┃** | 7.1 | 3.6 |
| postcheckout | 0.6 | 0.6 | **┃** | 2.1 | 3.2 | **┃** | 4.5 | 4.1 | **┃** | 2.8 | 1.5 | **┃** | 6.1 | 3.8 |
| getcart | 2.2 | 2.0 | **┃** | 5.4 | 4.4 | **┃** | 5.6 | 4.6 | **┃** | 10.4 | 5.6 | **┃** | 12.8 | 7.3 |
| postcart | 240.4 | 168.1 | **┃** | 201.5 | 201.6 | **┃** | 207.4 | 255.1 | **┃** | 451.8 | 461.0 | **┃** | 199.2 | 225.4 |
| emptycart | 4.8 | 3.9 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 3.7 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.

| API | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.926 | 0.931 | **┃** | 0.862 | 0.883 | **┃** | 0.869 | 0.887 | **┃** | 0.742 | 0.893 | **┃** | 0.821 | 0.883 |
| postcheckout | 0.927 | 0.925 | **┃** | 0.846 | 0.792 | **┃** | 0.730 | 0.750 | **┃** | 0.780 | 0.864 | **┃** | 0.659 | 0.736 |
| getcart | 0.905 | 0.908 | **┃** | 0.843 | 0.873 | **┃** | 0.854 | 0.875 | **┃** | 0.697 | 0.809 | **┃** | 0.708 | 0.797 |
| postcart | 0.474 | 0.600 | **┃** | 0.609 | 0.598 | **┃** | 0.606 | 0.532 | **┃** | 0.002 | 0.023 | **┃** | 0.624 | 0.538 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.002 | 0.000 | **┃** | 0.000 | 0.009 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.

| API | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 1015 | 855 | **┃** | 1052 | 640 | **┃** | 709 | 697 | **┃** | 1456 | 2004 | **┃** | 566 | 936 |
| postcheckout | 894 | 799 | **┃** | 953 | 594 | **┃** | 665 | 666 | **┃** | 1188 | 1659 | **┃** | 567 | 867 |
| getcart | 852 | 761 | **┃** | 892 | 504 | **┃** | 561 | 540 | **┃** | 1215 | 1644 | **┃** | 486 | 802 |
| postcart | 341 | 377 | **┃** | 293 | 277 | **┃** | 289 | 343 | **┃** | 461 | 596 | **┃** | 310 | 296 |
| emptycart | 16 | 14 | **┃** | 19 | 16 | **┃** | 13 | 12 | **┃** | 20 | 18 | **┃** | 14 | 13 |

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 515.2 | 487.6 | **┃** | 368.7 | 445.6 | **┃** | 426.5 | 479.5 | **┃** | 495.9 | 505.2 | **┃** | 317.3 | 397.6 |
| checkoutservice | 1.7 | 1.5 | **┃** | 3.3 | 4.0 | **┃** | 5.6 | 4.9 | **┃** | 4.9 | 6.4 | **┃** | 5.8 | 6.1 |
| recommendationservice | 74.8 | 69.7 | **┃** | 66.0 | 26.6 | **┃** | 34.1 | 26.0 | **┃** | 78.8 | 72.7 | **┃** | 34.6 | 46.5 |
| paymentservice | 1.7 | 1.5 | **┃** | 3.3 | 4.0 | **┃** | 5.6 | 4.9 | **┃** | 4.9 | 6.4 | **┃** | 5.8 | 6.1 |
| emailservice | 1.7 | 1.5 | **┃** | 3.3 | 4.0 | **┃** | 5.6 | 4.9 | **┃** | 4.9 | 6.4 | **┃** | 5.8 | 6.1 |
| productcatalogservice | 343.7 | 266.3 | **┃** | 344.8 | 296.3 | **┃** | 348.0 | 359.2 | **┃** | 701.5 | 752.7 | **┃** | 350.8 | 371.7 |
| cartservice | 276.8 | 201.5 | **┃** | 228.3 | 215.6 | **┃** | 236.1 | 274.1 | **┃** | 492.5 | 503.8 | **┃** | 222.9 | 250.6 |
| currencyservice | 71.2 | 57.0 | **┃** | 59.0 | 35.6 | **┃** | 45.3 | 35.6 | **┃** | 121.1 | 116.9 | **┃** | 56.2 | 56.5 |
| shippingservice | 8.6 | 7.3 | **┃** | 14.2 | 13.4 | **┃** | 17.9 | 15.1 | **┃** | 25.7 | 31.3 | **┃** | 23.5 | 22.5 |
| adservice | 4.9 | 3.8 | **┃** | 8.2 | 5.2 | **┃** | 6.6 | 5.1 | **┃** | 16.9 | 17.0 | **┃** | 6.9 | 6.1 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 170 | 152 | **┃** | 194 | 127 | **┃** | 135 | 121 | **┃** | 282 | 356 | **┃** | 132 | 165 |
| checkoutservice | 57 | 57 | **┃** | 54 | 55 | **┃** | 69 | 62 | **┃** | 55 | 54 | **┃** | 62 | 70 |
| recommendationservice | 259 | 216 | **┃** | 298 | 85 | **┃** | 103 | 113 | **┃** | 412 | 392 | **┃** | 71 | 195 |
| paymentservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 3 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| emailservice | 5 | 7 | **┃** | 4 | 4 | **┃** | 10 | 10 | **┃** | 4 | 4 | **┃** | 5 | 12 |
| productcatalogservice | 151 | 162 | **┃** | 119 | 141 | **┃** | 120 | 115 | **┃** | 128 | 175 | **┃** | 88 | 122 |
| cartservice | 10 | 8 | **┃** | 8 | 10 | **┃** | 8 | 9 | **┃** | 12 | 12 | **┃** | 7 | 8 |
| currencyservice | 2 | 2 | **┃** | 2 | 1 | **┃** | 2 | 1 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 2 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.089 | 0.066 | **┃** | 0.084 | 0.043 | **┃** | 0.052 | 0.035 | **┃** | 0.171 | 0.185 | **┃** | 0.052 | 0.069 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.387 | 0.322 | **┃** | 0.415 | 0.023 | **┃** | 0.051 | 0.046 | **┃** | 0.476 | 0.386 | **┃** | 0.001 | 0.161 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.014 | 0.061 | **┃** | 0.003 | 0.007 | **┃** | 0.005 | 0.004 | **┃** | 0.004 | 0.023 | **┃** | 0.001 | 0.004 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max sum usage across replicas.

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 574 / 849 | 1150 / 4 / 570 / 845 | **┃** | 1150 / 4 / 453 / 622 | 1150 / 4 / 497 / 732 | **┃** | 1150 / 4 / 495 / 706 | 1150 / 4 / 530 / 769 | **┃** | 1150 / 4 / 533 / 755 | 1150 / 4 / 501 / 722 | **┃** | 1150 / 4 / 406 / 567 | 1150 / 4 / 477 / 677 |
| checkoutservice | 800 / 1 / 36 / 164 | 800 / 1 / 34 / 163 | **┃** | 800 / 1 / 67 / 228 | 800 / 1 / 77 / 223 | **┃** | 800 / 1 / 105 / 270 | 800 / 1 / 95 / 237 | **┃** | 800 / 1 / 94 / 211 | 800 / 1 / 109 / 184 | **┃** | 800 / 1 / 108 / 222 | 800 / 1 / 112 / 305 |
| recommendationservice | 1150 / 1 / 131 / 250 | 1150 / 1 / 127 / 232 | **┃** | 1150 / 1 / 116 / 293 | 1150 / 1 / 66 / 149 | **┃** | 1150 / 1 / 79 / 210 | 1150 / 1 / 64 / 134 | **┃** | 1150 / 1 / 134 / 267 | 1150 / 1 / 120 / 207 | **┃** | 1150 / 1 / 82 / 114 | 1150 / 1 / 98 / 229 |
| paymentservice | 155 / 1 / 6 / 12 | 155 / 1 / 6 / 12 | **┃** | 155 / 1 / 7 / 14 | 155 / 1 / 8 / 16 | **┃** | 155 / 1 / 9 / 23 | 155 / 1 / 9 / 19 | **┃** | 155 / 1 / 7 / 13 | 155 / 1 / 8 / 11 | **┃** | 155 / 1 / 9 / 18 | 155 / 1 / 10 / 18 |
| emailservice | 120 / 1 / 13 / 24 | 120 / 1 / 13 / 26 | **┃** | 120 / 1 / 16 / 29 | 120 / 1 / 17 / 31 | **┃** | 120 / 1 / 20 / 35 | 120 / 1 / 19 / 32 | **┃** | 120 / 1 / 17 / 29 | 120 / 1 / 18 / 26 | **┃** | 120 / 1 / 20 / 31 | 120 / 1 / 21 / 39 |
| productcatalogservice | 100 / 1 / 46 / 101 | 100 / 1 / 36 / 101 | **┃** | 100 / 1 / 46 / 101 | 100 / 1 / 43 / 102 | **┃** | 100 / 1 / 52 / 101 | 100 / 1 / 46 / 101 | **┃** | 100 / 1 / 79 / 101 | 100 / 1 / 80 / 102 | **┃** | 100 / 1 / 54 / 100 | 100 / 1 / 52 / 101 |
| cartservice | 800 / 1 / 154 / 399 | 800 / 1 / 116 / 335 | **┃** | 800 / 1 / 117 / 333 | 800 / 1 / 92 / 304 | **┃** | 800 / 1 / 135 / 355 | 800 / 1 / 170 / 387 | **┃** | 800 / 1 / 147 / 237 | 800 / 1 / 142 / 243 | **┃** | 800 / 1 / 128 / 321 | 800 / 1 / 158 / 374 |
| currencyservice | 770 / 1 / 44 / 85 | 770 / 1 / 44 / 109 | **┃** | 770 / 1 / 44 / 87 | 770 / 1 / 30 / 64 | **┃** | 770 / 1 / 36 / 74 | 770 / 1 / 31 / 60 | **┃** | 770 / 1 / 66 / 97 | 770 / 1 / 60 / 91 | **┃** | 770 / 1 / 42 / 73 | 770 / 1 / 43 / 79 |
| shippingservice | 770 / 1 / 11 / 27 | 770 / 1 / 11 / 28 | **┃** | 770 / 1 / 15 / 36 | 770 / 1 / 14 / 30 | **┃** | 770 / 1 / 17 / 35 | 770 / 1 / 16 / 33 | **┃** | 770 / 1 / 19 / 30 | 770 / 1 / 20 / 29 | **┃** | 770 / 1 / 20 / 34 | 770 / 1 / 19 / 39 |
| adservice | 1150 / 1 / 31 / 48 | 1150 / 1 / 31 / 44 | **┃** | 1150 / 1 / 35 / 51 | 1150 / 1 / 33 / 45 | **┃** | 1150 / 1 / 35 / 47 | 1150 / 1 / 34 / 47 | **┃** | 1150 / 1 / 44 / 60 | 1150 / 1 / 39 / 48 | **┃** | 1150 / 1 / 35 / 47 | 1150 / 1 / 35 / 45 |
| redis-cart | 540 / 1 / 18 / 42 | 540 / 1 / 16 / 43 | **┃** | 540 / 1 / 17 / 37 | 540 / 1 / 17 / 42 | **┃** | 540 / 1 / 17 / 43 | 540 / 1 / 18 / 42 | **┃** | 540 / 1 / 24 / 47 | 540 / 1 / 22 / 44 | **┃** | 540 / 1 / 18 / 44 | 540 / 1 / 19 / 47 |

CPU as a fraction of per-pod quota × replicas (mean / max).

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.12 / 0.18 | 0.12 / 0.18 | **┃** | 0.10 / 0.14 | 0.11 / 0.16 | **┃** | 0.11 / 0.15 | 0.12 / 0.17 | **┃** | 0.12 / 0.16 | 0.11 / 0.16 | **┃** | 0.09 / 0.12 | 0.10 / 0.15 |
| checkoutservice | 0.04 / 0.20 | 0.04 / 0.20 | **┃** | 0.08 / 0.28 | 0.10 / 0.28 | **┃** | 0.13 / 0.34 | 0.12 / 0.30 | **┃** | 0.12 / 0.26 | 0.14 / 0.23 | **┃** | 0.14 / 0.28 | 0.14 / 0.38 |
| recommendationservice | 0.11 / 0.22 | 0.11 / 0.20 | **┃** | 0.10 / 0.25 | 0.06 / 0.13 | **┃** | 0.07 / 0.18 | 0.06 / 0.12 | **┃** | 0.12 / 0.23 | 0.10 / 0.18 | **┃** | 0.07 / 0.10 | 0.09 / 0.20 |
| paymentservice | 0.04 / 0.08 | 0.04 / 0.08 | **┃** | 0.05 / 0.09 | 0.05 / 0.10 | **┃** | 0.06 / 0.15 | 0.06 / 0.12 | **┃** | 0.05 / 0.08 | 0.05 / 0.07 | **┃** | 0.06 / 0.12 | 0.06 / 0.12 |
| emailservice | 0.11 / 0.20 | 0.11 / 0.22 | **┃** | 0.13 / 0.24 | 0.14 / 0.26 | **┃** | 0.16 / 0.29 | 0.15 / 0.27 | **┃** | 0.14 / 0.24 | 0.15 / 0.22 | **┃** | 0.17 / 0.26 | 0.17 / 0.33 |
| productcatalogservice | 0.46 / 1.01 | 0.38 / 1.01 | **┃** | 0.47 / 1.01 | 0.43 / 1.02 | **┃** | 0.52 / 1.01 | 0.46 / 1.01 | **┃** | 0.79 / 1.01 | 0.80 / 1.02 | **┃** | 0.55 / 1.00 | 0.52 / 1.01 |
| cartservice | 0.19 / 0.50 | 0.15 / 0.42 | **┃** | 0.15 / 0.42 | 0.11 / 0.38 | **┃** | 0.17 / 0.44 | 0.21 / 0.48 | **┃** | 0.18 / 0.30 | 0.18 / 0.30 | **┃** | 0.16 / 0.40 | 0.20 / 0.47 |
| currencyservice | 0.06 / 0.11 | 0.06 / 0.14 | **┃** | 0.06 / 0.11 | 0.04 / 0.08 | **┃** | 0.05 / 0.10 | 0.04 / 0.08 | **┃** | 0.09 / 0.13 | 0.08 / 0.12 | **┃** | 0.05 / 0.09 | 0.06 / 0.10 |
| shippingservice | 0.01 / 0.04 | 0.01 / 0.04 | **┃** | 0.02 / 0.05 | 0.02 / 0.04 | **┃** | 0.02 / 0.05 | 0.02 / 0.04 | **┃** | 0.02 / 0.04 | 0.03 / 0.04 | **┃** | 0.03 / 0.04 | 0.02 / 0.05 |
| adservice | 0.03 / 0.04 | 0.03 / 0.04 | **┃** | 0.03 / 0.04 | 0.03 / 0.04 | **┃** | 0.03 / 0.04 | 0.03 / 0.04 | **┃** | 0.04 / 0.05 | 0.03 / 0.04 | **┃** | 0.03 / 0.04 | 0.03 / 0.04 |
| redis-cart | 0.03 / 0.08 | 0.03 / 0.08 | **┃** | 0.03 / 0.07 | 0.03 / 0.08 | **┃** | 0.03 / 0.08 | 0.03 / 0.08 | **┃** | 0.04 / 0.09 | 0.04 / 0.08 | **┃** | 0.03 / 0.08 | 0.03 / 0.09 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | final_4a_constrained_rg_only_normal_run3_r2 | final_4a_constrained_rg_only_normal_run4 | **┃** | final_4a_constrained_both_normal_run3 | final_4a_constrained_both_normal_run4 | **┃** | final_4a_constrained_tf_only_run3_r2 | final_4a_constrained_tf_only_run4 | **┃** | final_4a_constrained_rg_only_burst_run5_r2 | final_4a_constrained_rg_only_burst_run6 | **┃** | final_4a_constrained_both_burst_run3 | final_4a_constrained_both_burst_run4_r2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.237 | 0.208 | **┃** | 0.286 | 0.291 | **┃** | 0.302 | 0.234 | **┃** | 0.190 | 0.190 | **┃** | 0.198 | 0.304 |
| checkoutservice | 0.305 | 0.324 | **┃** | 0.389 | 0.444 | **┃** | 0.515 | 0.446 | **┃** | 0.407 | 0.370 | **┃** | 0.389 | 0.510 |
| recommendationservice | 0.346 | 0.296 | **┃** | 0.297 | 0.144 | **┃** | 0.261 | 0.158 | **┃** | 0.269 | 0.255 | **┃** | 0.137 | 0.330 |
| paymentservice | 0.303 | 0.303 | **┃** | 0.329 | 0.323 | **┃** | 0.381 | 0.381 | **┃** | 0.252 | 0.265 | **┃** | 0.329 | 0.374 |
| emailservice | 0.500 | 0.525 | **┃** | 0.567 | 0.533 | **┃** | 0.633 | 0.550 | **┃** | 0.408 | 0.358 | **┃** | 0.533 | 0.633 |
| productcatalogservice | 1.210 | 1.080 | **┃** | 1.090 | 1.170 | **┃** | 1.110 | 1.110 | **┃** | 1.150 | 1.140 | **┃** | 1.100 | 1.180 |
| cartservice | 0.595 | 0.464 | **┃** | 0.472 | 0.450 | **┃** | 0.549 | 0.566 | **┃** | 0.356 | 0.344 | **┃** | 0.502 | 0.569 |
| currencyservice | 0.178 | 0.195 | **┃** | 0.205 | 0.126 | **┃** | 0.134 | 0.121 | **┃** | 0.168 | 0.190 | **┃** | 0.140 | 0.197 |
| shippingservice | 0.075 | 0.092 | **┃** | 0.094 | 0.087 | **┃** | 0.087 | 0.086 | **┃** | 0.075 | 0.087 | **┃** | 0.086 | 0.105 |
| adservice | 0.085 | 0.061 | **┃** | 0.085 | 0.070 | **┃** | 0.073 | 0.093 | **┃** | 0.064 | 0.062 | **┃** | 0.071 | 0.064 |
| redis-cart | 0.178 | 0.206 | **┃** | 0.196 | 0.239 | **┃** | 0.191 | 0.270 | **┃** | 0.320 | 0.285 | **┃** | 0.252 | 0.331 |

## Throttle data quality

Every scored hold is **FLAGGED**. Cap and admitted-rate numbers are carried, not measured. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag. The four TopFull-off columns (`rg_only` normal and burst) have no admission cap to lose; their live-cap tables are still pasted. The rg_only burst columns are `final_4a_constrained_rg_only_burst_run5_r2` and `final_4a_constrained_rg_only_burst_run6`. Both had `live5s_caps=0`. `final_4a_constrained_rg_only_burst_run5` had 535 Locust rows and is not a column.

- `final_4a_constrained_both_burst_run3_r2` is FLAGGED (222 fetch warnings; longest no-fresh threshold read 558 s, longest no-fresh admitted read 560 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag.
- `final_4a_constrained_both_burst_run4` is FLAGGED (226 fetch warnings; longest no-fresh threshold read 570 s, longest no-fresh admitted read 570 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag.
- `final_4a_constrained_both_normal_run3_r2` is FLAGGED (224 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 564 s). The cap is measured; admitted req/s is carried, not measured; filter it on `admitted_fresh==1` and do not quote it as measured. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag.
- `final_4a_constrained_tf_only_run3` is FLAGGED (228 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 575 s). The cap is measured; admitted req/s is carried, not measured; filter it on `admitted_fresh==1` and do not quote it as measured. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | --- | --- | --- | --- | --- |
| final_4a_constrained_rg_only_normal_run3_r2 | **FLAGGED** | 228 | 15:39:30 | 575 | 575 |
| final_4a_constrained_rg_only_normal_run4 | **FLAGGED** | 230 | 15:59:00 | 578 | 578 |
| final_4a_constrained_both_normal_run3 | **FLAGGED** | 226 | 17:15:30 | 5 | 570 |
| final_4a_constrained_both_normal_run4 | **FLAGGED** | 226 | 17:58:00 | 5 | 568 |
| final_4a_constrained_tf_only_run3_r2 | **FLAGGED** | 224 | 18:34:35 | 5 | 565 |
| final_4a_constrained_tf_only_run4 | **FLAGGED** | 224 | 18:52:40 | 5 | 565 |
| final_4a_constrained_rg_only_burst_run5_r2 | **FLAGGED** | 228 | 18:09:30 | 575 | 575 |
| final_4a_constrained_rg_only_burst_run6 | **FLAGGED** | 228 | 18:29:00 | 575 | 575 |
| final_4a_constrained_both_burst_run3 | **FLAGGED** | 226 | 20:26:25 | 5 | 568 |
| final_4a_constrained_both_burst_run4_r2 | **FLAGGED** | 228 | 21:23:05 | 572 | 574 |

## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. `postcart` and `emptycart` are called out when every live read is no cap.

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### final_4a_constrained_rg_only_normal_run3_r2

| API | Live caps |
| --- | --- |
| getproduct | no cap 15:36:55–15:49:00 |
| postcheckout | no cap 15:36:55–15:49:00 |
| getcart | no cap 15:36:55–15:49:00 |
| postcart | no cap 15:36:55–15:49:00 |
| emptycart | no cap 15:36:55–15:49:00 |

### final_4a_constrained_rg_only_normal_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 15:56:35–15:58:55 |
| postcheckout | no cap 15:56:35–15:58:55 |
| getcart | no cap 15:56:35–15:58:55 |
| postcart | no cap 15:56:35–15:58:55 |
| emptycart | no cap 15:56:35–15:58:55 |

### final_4a_constrained_both_normal_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 17:12:50–17:15:05; 22.2 at 17:15:10; 21.69 at 17:15:13; 21.7 at 17:15:15; 21.4 at 17:15:20; 25.8422 at 17:15:22; 25.2248 at 17:15:24; 25.2 at 17:15:25; 23.754 at 17:15:28; 23.8 at 17:24:55 |
| postcheckout | no cap 17:12:50–17:15:05; 10.0988 at 17:15:07; 10.2 at 17:15:10; 10 17:15:15–17:24:55 |
| getcart | no cap 17:12:50–17:15:05; 22.2 at 17:15:10; 21.69 at 17:15:13; 21.7 at 17:15:15; 21.69 at 17:15:16; 19.8 at 17:15:20; 23.598 at 17:15:24; 23.6 at 17:15:25; 15.5314 17:15:30–17:24:53; 15.5 at 17:24:55 |
| postcart | no cap 17:12:50–17:15:05; 270.099 at 17:15:07; 270.2 at 17:15:10; 269.69 at 17:15:13; 269.7 17:15:15–17:15:20; 356.666 at 17:15:22; 356.048 at 17:15:24; 356 at 17:15:25; 354.578 17:15:29–17:24:53; 354.6 at 17:24:55 |
| emptycart | no cap 17:12:50–17:24:55 |

### final_4a_constrained_both_normal_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 17:55:25–17:57:25; 16 at 17:57:30; 18.9 at 17:57:35; 19.2693 at 17:57:37; 19.3 at 17:57:40; 13.2 at 17:57:45; 12.3412 at 17:57:48; 12.3 17:57:50–17:57:55; 11.9171 17:57:56–18:07:21 |
| postcheckout | no cap 17:55:25–17:57:25; 10 17:57:30–18:07:21 |
| getcart | no cap 17:55:25–17:57:25; 18 at 17:57:30; 17.5969 at 17:57:33; 17.6 at 17:57:35; 18.989 at 17:57:36; 19 at 17:57:40; 13.3 at 17:57:45; 12.4279 at 17:57:48; 12.4 17:57:50–17:57:55 |
| postcart | no cap 17:55:25–17:57:25; 210 at 17:57:30; 268.5 at 17:57:35; 268.488 at 17:57:36; 268.5 at 17:57:40; 363.2 at 17:57:45; 362.363 at 17:57:48; 362.4 at 17:57:50; 466.5 at 17:57:55; 466.507 17:57:56–18:07:21 |
| emptycart | no cap 17:55:25–17:57:55 |

### final_4a_constrained_tf_only_run3_r2

| API | Live caps |
| --- | --- |
| getproduct | no cap 18:32:15–18:33:55; 13.4 18:34:00–18:34:05; 12.6 at 18:34:10; 12.9022 at 18:34:14; 12.9 at 18:34:15; 14.3 18:34:20–18:34:25; 14.2 at 18:34:30; 14.2415 18:34:31–18:43:54; 14.2 at 18:43:55 |
| postcheckout | 10 18:32:12–18:32:14; no cap at 18:32:15; 10 18:32:16–18:32:19; no cap at 18:32:20; 10 18:32:21–18:32:24; no cap at 18:32:25; 10 18:32:26–18:32:29; no cap at 18:32:30; 10 18:32:31–18:32:34; no cap at 18:32:35; 10 18:32:36–18:32:39; no cap at 18:32:40; 10 18:32:41–18:32:44; no cap at 18:32:45; 10 18:32:46–18:32:49; no cap at 18:32:50; 10 18:32:51–18:32:54; no cap at 18:32:55; 10 18:32:56–18:32:59; no cap at 18:33:00; 10 18:33:01–18:33:04; no cap at 18:33:05; 10 18:33:06–18:33:09; no cap at 18:33:10; 10 18:33:11–18:33:14; no cap at 18:33:15; 10 18:33:16–18:33:19; no cap at 18:33:20; 10 18:33:21–18:33:24; no cap at 18:33:25; 10 18:33:26–18:33:29; no cap at 18:33:30; 10 18:33:31–18:33:34; no cap at 18:33:35; 10 18:33:36–18:33:39; no cap at 18:33:40; 10 18:33:41–18:33:44; no cap at 18:33:45; 10 18:33:46–18:33:49; no cap at 18:33:50; 10 18:33:51–18:33:54; no cap at 18:33:55; 10 18:33:56–18:34:05; no cap at 18:34:10; 10 at 18:34:15; 11 at 18:34:20; 13.7 at 18:34:25; 12.5173 at 18:34:28; 12.5 18:34:30–18:43:55 |
| getcart | 10 18:32:12–18:32:14; no cap at 18:32:15; 10 18:32:16–18:32:19; no cap at 18:32:20; 10 18:32:21–18:32:24; no cap at 18:32:25; 10 18:32:26–18:32:29; no cap at 18:32:30; 10 18:32:31–18:32:34; no cap at 18:32:35; 10 18:32:36–18:32:39; no cap at 18:32:40; 10 18:32:41–18:32:44; no cap at 18:32:45; 10 18:32:46–18:32:49; no cap at 18:32:50; 10 18:32:51–18:32:54; no cap at 18:32:55; 10 18:32:56–18:32:59; no cap at 18:33:00; 10 18:33:01–18:33:04; no cap at 18:33:05; 10 18:33:06–18:33:09; no cap at 18:33:10; 10 18:33:11–18:33:14; no cap at 18:33:15; 10 18:33:16–18:33:19; no cap at 18:33:20; 10 18:33:21–18:33:24; no cap at 18:33:25; 10 18:33:26–18:33:29; no cap at 18:33:30; 10 18:33:31–18:33:34; no cap at 18:33:35; 10 18:33:36–18:33:39; no cap at 18:33:40; 10 18:33:41–18:33:44; no cap at 18:33:45; 10 18:33:46–18:33:49; no cap at 18:33:50; 10 18:33:51–18:33:54; no cap at 18:33:55; 10 18:33:56–18:33:57; 15.4 18:34:00–18:34:05; 12.2858 at 18:34:08; 12.3 18:34:10–18:34:15; 14.3 18:34:20–18:34:25; 14.2569 at 18:34:27; 14.1 18:34:30–18:43:55 |
| postcart | no cap 18:32:15–18:33:55; 163.4 at 18:34:00; 163.393 at 18:34:02; 163.4 at 18:34:05; 246.7 at 18:34:10; 246.67 at 18:34:13; 246.7 at 18:34:15; 324.662 at 18:34:18; 324.7 18:34:20–18:34:25; 420.1 at 18:34:30; 430.6 at 18:43:55 |
| emptycart | no cap 18:32:15–18:43:55 |

### final_4a_constrained_tf_only_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 18:50:25–18:52:05; 18 at 18:52:07; 10 18:52:10–18:52:15; 10.2 at 18:52:20; 11.2 at 18:52:25; 10.2 at 18:52:30; 10 18:52:35–19:02:01 |
| postcheckout | no cap 18:50:25–18:52:05; 10 18:52:07–18:52:15; 10.2 at 18:52:20; 13.4 at 18:52:25; 10.2 at 18:52:30; 10.1945 at 18:52:34; 10 18:52:35–19:02:01 |
| getcart | no cap 18:50:25–18:52:05; 20 at 18:52:07; 10 18:52:10–18:52:14; 13.5 at 18:52:15; 10.2 at 18:52:20; 13.3873 at 18:52:23; 13.4 at 18:52:25; 10.2 at 18:52:30; 10 18:52:33–19:02:01 |
| postcart | no cap 18:50:25–18:52:05; 234 at 18:52:07; 216.9 at 18:52:10; 297 at 18:52:15; 296.4 at 18:52:20; 400.6 at 18:52:25; 427.745 at 18:52:29; 427.7 at 18:52:30; 489.9 at 18:52:35; 417.753 18:52:37–19:01:59; 489.9 at 19:02:00; 417.753 at 19:02:01 |
| emptycart | no cap 18:50:25–19:02:00 |

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### final_4a_constrained_rg_only_burst_run5_r2

| API | Live caps |
| --- | --- |
| getproduct | no cap 18:07:05–18:19:00 |
| postcheckout | no cap 18:07:05–18:19:00 |
| getcart | no cap 18:07:05–18:19:00 |
| postcart | no cap 18:07:05–18:19:00 |
| emptycart | no cap 18:07:05–18:19:00 |

### final_4a_constrained_rg_only_burst_run6

| API | Live caps |
| --- | --- |
| getproduct | no cap 18:26:35–18:38:30 |
| postcheckout | no cap 18:26:35–18:38:30 |
| getcart | no cap 18:26:35–18:38:30 |
| postcart | no cap 18:26:35–18:38:30 |
| emptycart | no cap 18:26:35–18:38:30 |

### final_4a_constrained_both_burst_run3

| API | Live caps |
| --- | --- |
| getproduct | 10 20:23:48–20:23:49; no cap at 20:23:50; 10 20:23:51–20:23:54; no cap at 20:23:55; 10 20:23:56–20:23:59; no cap at 20:24:00; 10 20:24:01–20:24:04; no cap at 20:24:05; 10 20:24:06–20:24:09; no cap at 20:24:10; 10 20:24:11–20:24:14; no cap at 20:24:15; 10 20:24:16–20:24:19; no cap at 20:24:20; 10 20:24:21–20:24:24; no cap at 20:24:25; 10 20:24:26–20:24:29; no cap at 20:24:30; 10 20:24:31–20:24:34; no cap at 20:24:35; 10 20:24:36–20:24:39; no cap at 20:24:40; 10 20:24:41–20:24:44; no cap at 20:24:45; 10 20:24:46–20:24:49; no cap at 20:24:50; 10 20:24:51–20:24:54; no cap at 20:24:55; 10 20:24:56–20:24:59; no cap at 20:25:00; 10 20:25:01–20:25:04; no cap at 20:25:05; 10 20:25:06–20:25:09; no cap at 20:25:10; 10 20:25:11–20:25:14; no cap at 20:25:15; 10 20:25:16–20:25:19; no cap at 20:25:20; 10 20:25:21–20:25:24; no cap at 20:25:25; 10 20:25:26–20:25:29; no cap at 20:25:30; 10 20:25:31–20:25:34; no cap at 20:25:35; 10 20:25:36–20:25:39; no cap at 20:25:40; 10 20:25:41–20:25:44; no cap at 20:25:45; 10 20:25:46–20:25:49; no cap at 20:25:50; 10 20:25:51–20:25:54; no cap at 20:25:55; 18.5 at 20:26:00; 18.3 at 20:26:05; 14.6 at 20:26:10; 12.3 at 20:26:15; 10 at 20:26:20 |
| postcheckout | 10 20:23:48–20:23:49; no cap at 20:23:50; 10 20:23:51–20:23:54; no cap at 20:23:55; 10 20:23:56–20:23:59; no cap at 20:24:00; 10 20:24:01–20:24:04; no cap at 20:24:05; 10 20:24:06–20:24:09; no cap at 20:24:10; 10 20:24:11–20:24:14; no cap at 20:24:15; 10 20:24:16–20:24:19; no cap at 20:24:20; 10 20:24:21–20:24:24; no cap at 20:24:25; 10 20:24:26–20:24:29; no cap at 20:24:30; 10 20:24:31–20:24:34; no cap at 20:24:35; 10 20:24:36–20:24:39; no cap at 20:24:40; 10 20:24:41–20:24:44; no cap at 20:24:45; 10 20:24:46–20:24:49; no cap at 20:24:50; 10 20:24:51–20:24:54; no cap at 20:24:55; 10 20:24:56–20:24:59; no cap at 20:25:00; 10 20:25:01–20:25:04; no cap at 20:25:05; 10 20:25:06–20:25:09; no cap at 20:25:10; 10 20:25:11–20:25:14; no cap at 20:25:15; 10 20:25:16–20:25:19; no cap at 20:25:20; 10 20:25:21–20:25:24; no cap at 20:25:25; 10 20:25:26–20:25:29; no cap at 20:25:30; 10 20:25:31–20:25:34; no cap at 20:25:35; 10 20:25:36–20:25:39; no cap at 20:25:40; 10 20:25:41–20:25:44; no cap at 20:25:45; 10 20:25:46–20:25:49; no cap at 20:25:50; 10 20:25:51–20:25:54; no cap at 20:25:55; 10 20:26:00–20:26:05; 11.8 20:26:10–20:26:15; 10 20:26:16–20:26:22 |
| getcart | 10 20:23:48–20:23:49; no cap at 20:23:50; 10 20:23:51–20:23:54; no cap at 20:23:55; 10 20:23:56–20:23:59; no cap at 20:24:00; 10 20:24:01–20:24:04; no cap at 20:24:05; 10 20:24:06–20:24:09; no cap at 20:24:10; 10 20:24:11–20:24:14; no cap at 20:24:15; 10 20:24:16–20:24:19; no cap at 20:24:20; 10 20:24:21–20:24:24; no cap at 20:24:25; 10 20:24:26–20:24:29; no cap at 20:24:30; 10 20:24:31–20:24:34; no cap at 20:24:35; 10 20:24:36–20:24:39; no cap at 20:24:40; 10 20:24:41–20:24:44; no cap at 20:24:45; 10 20:24:46–20:24:49; no cap at 20:24:50; 10 20:24:51–20:24:54; no cap at 20:24:55; 10 20:24:56–20:24:59; no cap at 20:25:00; 10 20:25:01–20:25:04; no cap at 20:25:05; 10 20:25:06–20:25:09; no cap at 20:25:10; 10 20:25:11–20:25:14; no cap at 20:25:15; 10 20:25:16–20:25:19; no cap at 20:25:20; 10 20:25:21–20:25:24; no cap at 20:25:25; 10 20:25:26–20:25:29; no cap at 20:25:30; 10 20:25:31–20:25:34; no cap at 20:25:35; 10 20:25:36–20:25:39; no cap at 20:25:40; 10 20:25:41–20:25:44; no cap at 20:25:45; 10 20:25:46–20:25:49; no cap at 20:25:50; 10 20:25:51–20:25:54; no cap at 20:25:55; 20.5 at 20:26:00; 20.3 at 20:26:05; 20.5 at 20:26:10; 20.6 at 20:26:15; 19 at 20:26:20; 21.0324 20:35:46–20:35:47 |
| postcart | 417.753 20:23:48–20:23:49; no cap at 20:23:50; 417.753 20:23:51–20:23:54; no cap at 20:23:55; 417.753 20:23:56–20:23:59; no cap at 20:24:00; 417.753 20:24:01–20:24:04; no cap at 20:24:05; 417.753 20:24:06–20:24:09; no cap at 20:24:10; 417.753 20:24:11–20:24:14; no cap at 20:24:15; 417.753 20:24:16–20:24:19; no cap at 20:24:20; 417.753 20:24:21–20:24:24; no cap at 20:24:25; 417.753 20:24:26–20:24:29; no cap at 20:24:30; 417.753 20:24:31–20:24:34; no cap at 20:24:35; 417.753 20:24:36–20:24:39; no cap at 20:24:40; 417.753 20:24:41–20:24:44; no cap at 20:24:45; 417.753 20:24:46–20:24:49; no cap at 20:24:50; 417.753 20:24:51–20:24:54; no cap at 20:24:55; 417.753 20:24:56–20:24:59; no cap at 20:25:00; 417.753 20:25:01–20:25:04; no cap at 20:25:05; 417.753 20:25:06–20:25:09; no cap at 20:25:10; 417.753 20:25:11–20:25:14; no cap at 20:25:15; 417.753 20:25:16–20:25:19; no cap at 20:25:20; 417.753 20:25:21–20:25:24; no cap at 20:25:25; 417.753 20:25:26–20:25:29; no cap at 20:25:30; 417.753 20:25:31–20:25:34; no cap at 20:25:35; 417.753 20:25:36–20:25:39; no cap at 20:25:40; 417.753 20:25:41–20:25:44; no cap at 20:25:45; 417.753 20:25:46–20:25:49; no cap at 20:25:50; 417.753 20:25:51–20:25:54; no cap at 20:25:55; 234.5 at 20:26:00; 234.3 at 20:26:05; 307.3 at 20:26:10; 307.4 at 20:26:15; 307.356 at 20:26:17; 401.4 at 20:26:20; 422.821 20:26:24–20:35:46 |
| emptycart | no cap 20:23:50–20:26:20 |

### final_4a_constrained_both_burst_run4_r2

| API | Live caps |
| --- | --- |
| getproduct | no cap 21:20:30–21:22:35; 16 at 21:22:40; 16.2 at 21:22:45; 16.2934 at 21:22:49; 16.3 at 21:22:50; 16.1929 21:22:52–21:22:53; 11.3 at 21:22:55; 15.5 at 21:23:00 |
| postcheckout | no cap 21:20:30–21:22:35; 10 21:22:40–21:22:45; 12.1 at 21:22:49; 12.1 at 21:22:50; no cap at 21:22:52; 13 21:22:55–21:23:00 |
| getcart | no cap 21:20:30–21:22:35; 18 at 21:22:40; 18.2 at 21:22:45; 18.3 at 21:22:50; 20.3 at 21:22:55; 22.6345 at 21:22:58; 22.6 at 21:23:00 |
| postcart | no cap 21:20:30–21:22:35; 210 at 21:22:40; 210.2 at 21:22:45; 210.3 at 21:22:50; 291.792 at 21:22:51; 305.7 at 21:22:55; 396.9 at 21:23:00; 492.167 at 21:23:02 |
| emptycart | no cap 21:20:30–21:23:00 |

## One paragraph per scored column

Launches that are not a column are in the index. They are not repeated here.

**final_4a_constrained_rg_only_normal_run3_r2.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-13T15:39:40Z, rpr 2.59; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T15:45:05Z, rpr 2.98; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T15:48:31Z, rpr 3.05. Outbound retry delta: recommendationservice 8,811, productcatalogservice 11,643, checkoutservice —. grpc_4 / grpc_14: recommendationservice 15,538 / 0, productcatalogservice 2,658 / 7,106, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 216/726 (29.8%).

**final_4a_constrained_rg_only_normal_run4.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-13T15:59:19Z, rpr 2.62; frontend → productcatalogservice ON→OFF from 3 at 2026-10-13T16:01:23Z, rpr 1.04; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T16:02:35Z, rpr 2.06; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T16:04:33Z, rpr 2.41; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T16:07:47Z, rpr 2.81. Outbound retry delta: recommendationservice 11,058, productcatalogservice 15,630, checkoutservice —. grpc_4 / grpc_14: recommendationservice 12,372 / 0, productcatalogservice 10,079 / 3,681, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 177/723 (24.5%).

**final_4a_constrained_both_normal_run3.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-13T17:15:51Z, rpr 2.58; frontend → recommendationservice ON→OFF from 2 at 2026-10-13T17:17:12Z, rpr 1.31; frontend → recommendationservice ON→OFF from 3 at 2026-10-13T17:21:17Z, rpr 2.41. Outbound retry delta: recommendationservice 16,624, productcatalogservice 7,885, checkoutservice —. grpc_4 / grpc_14: recommendationservice 14,219 / 0, productcatalogservice 407 / 8,612, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 254/727 (34.9%).

**final_4a_constrained_both_normal_run4.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: recommendationservice 569, productcatalogservice 9,079, checkoutservice —. grpc_4 / grpc_14: recommendationservice 361 / 0, productcatalogservice 845 / 7,734, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 187/723 (25.9%).

**final_4a_constrained_tf_only_run3_r2.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: recommendationservice 1,449, productcatalogservice 12,456, checkoutservice —. grpc_4 / grpc_14: recommendationservice 1,036 / 0, productcatalogservice 806 / 13,241, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 223/706 (31.6%).

**final_4a_constrained_tf_only_run4.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: recommendationservice 1,078, productcatalogservice 7,784, checkoutservice —. grpc_4 / grpc_14: recommendationservice 695 / 0, productcatalogservice 684 / 7,317, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 244/697 (35.0%).

**final_4a_constrained_rg_only_burst_run5_r2.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-14T18:09:26Z, rpr 2.06 (burst). Outbound retry delta: recommendationservice 1,167, productcatalogservice 3,105, checkoutservice —. grpc_4 / grpc_14: recommendationservice 21,506 / 0, productcatalogservice 1,038 / 0, currencyservice 0 / 0, adservice 0 / 0. productcatalogservice reached a detector share of 0.5: 434/720 (60.3%).

**final_4a_constrained_rg_only_burst_run6.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-14T18:29:04Z, rpr 2.14 (burst). Outbound retry delta: recommendationservice 1,297, productcatalogservice 15,926, checkoutservice —. grpc_4 / grpc_14: recommendationservice 16,979 / 0, productcatalogservice 9,158 / 0, currencyservice 0 / 0, adservice 0 / 0. productcatalogservice reached a detector share of 0.5: 414/716 (57.8%).

**final_4a_constrained_both_burst_run3.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: recommendationservice 42, productcatalogservice 6,777, checkoutservice 0. grpc_4 / grpc_14: recommendationservice 24 / 0, productcatalogservice 100 / 8,217, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 283/721 (39.3%).

**final_4a_constrained_both_burst_run4_r2.** Sheds: frontend → recommendationservice ON→OFF from 3 at 2026-10-13T21:23:17Z, rpr 2.14 (burst); frontend → recommendationservice ON→OFF from 2 at 2026-10-13T21:24:08Z, rpr 1.61 (burst); frontend → recommendationservice ON→OFF from 2 at 2026-10-13T21:25:44Z, rpr 1.36 (burst); frontend → recommendationservice ON→OFF from 1 at 2026-10-13T21:26:21Z, rpr 0.71 (burst); frontend → recommendationservice ON→OFF from 3 at 2026-10-13T21:27:35Z, rpr 2.03 (burst). Outbound retry delta: recommendationservice 4,950, productcatalogservice 8,335, checkoutservice 0. grpc_4 / grpc_14: recommendationservice 4,335 / 0, productcatalogservice 685 / 8,192, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. productcatalogservice was 262/727 (36.0%).

## Related

- [S4 relock mode matrix plan](../../docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md)
- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [(a) / (b) / (c) reading](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md)
- [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md)
- [ADR 0008](../../docs/adr/0008-locked-retryguard-parameters.md)
- [ADR 0009](../../docs/adr/0009-paper-c1-default-cpu-table.md)
- [2026-10-13-s4a-constrained-mode-matrix-abc.md](2026-10-13-s4a-constrained-mode-matrix-abc.md) (catalog 50 m, mix 10 / 10 / 10 / 600 / 5; not a column here)
