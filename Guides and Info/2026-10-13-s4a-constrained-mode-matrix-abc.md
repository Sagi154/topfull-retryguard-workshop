# S4A constrained mode matrix — (a) / (b) / (c)

## Setup

Scenario 4A constrained, 600 s. Mix 10 / 10 / 10 / 600 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1, with productcatalogservice constrained to 50 m. Frontend HPA min = max = 4. productcatalogservice HPA min = max = 1. Frontend sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off between holds is 120 s. RetryGuard uses the locked parameters. Burst holds set `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal-mode RetryGuard holds omit those three keys. The TopFull-only YAML still has them; RetryGuard is off on that cell, so its result directory is `normal`. Each cell is two repeats. The bold bar splits the pairs.

The catalog replica gate failed on 18 of the 20 launches: at least one `resource_usage.csv` sample had `productcatalogservice` `replica_count` other than 1, while the CPU limit during the hold stayed 50 m. Each failed launch was replayed once. Two replays passed: `final_4a_constrained_tf_only_run2_r2` and `final_4a_constrained_rg_only_burst_run2_r2`. Those two replace the INVALID canonical folders as columns. The other eight columns are the canonical folders, which stayed INVALID, because the replay failed the same gate. INVALID folders stay on disk and are not dropped. Earlier S4A holds at 100 m, or on another mix, are not columns.

File streaks in (a) are seconds. The parenthetical on a RetryGuard hold is the controller's max `high` from `retryguard.log`, which is a sample count.

Scored folders:

- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1`
- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run1`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2_r2`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2_r2`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2`

## Index

| Hold | log_folder | Mode | TopFull | In this guide |
| --- | --- | --- | --- | --- |
| 11 | final_4a_constrained_rg_only_normal_run1 | normal | off | INVALID, catalog replicas, scored |
| 11 replay | final_4a_constrained_rg_only_normal_run1_r2 | normal | off | INVALID, kept, not a column |
| 12 | final_4a_constrained_rg_only_normal_run2 | normal | off | INVALID, catalog replicas, scored |
| 12 replay | final_4a_constrained_rg_only_normal_run2_r2 | normal | off | INVALID, kept, not a column |
| 13 | final_4a_constrained_both_normal_run1 | normal | on | INVALID, catalog replicas, scored |
| 13 replay | final_4a_constrained_both_normal_run1_r2 | normal | on | INVALID, kept, not a column |
| 14 | final_4a_constrained_both_normal_run2 | normal | on | INVALID, catalog replicas, scored |
| 14 replay | final_4a_constrained_both_normal_run2_r2 | normal | on | INVALID, kept, not a column |
| 15 | final_4a_constrained_tf_only_run1 | tf | on | INVALID, catalog replicas, scored |
| 15 replay | final_4a_constrained_tf_only_run1_r2 | tf | on | INVALID, kept, not a column |
| 16 | final_4a_constrained_tf_only_run2 | tf | on | INVALID, kept, not a column |
| 16 replay | final_4a_constrained_tf_only_run2_r2 | tf | on | PASS, scored in place of run2 |
| 17 | final_4a_constrained_rg_only_burst_run1 | burst_rpr 2.0 | off | INVALID, catalog replicas, scored |
| 17 replay | final_4a_constrained_rg_only_burst_run1_r2 | burst_rpr 2.0 | off | INVALID, kept, not a column |
| 18 | final_4a_constrained_rg_only_burst_run2 | burst_rpr 2.0 | off | INVALID, kept, not a column |
| 18 replay | final_4a_constrained_rg_only_burst_run2_r2 | burst_rpr 2.0 | off | PASS, scored in place of run2 |
| 19 | final_4a_constrained_both_burst_run1 | burst_rpr 2.0 | on | INVALID, catalog replicas, scored |
| 19 replay | final_4a_constrained_both_burst_run1_r2 | burst_rpr 2.0 | on | INVALID, kept, not a column |
| 20 | final_4a_constrained_both_burst_run2 | burst_rpr 2.0 | on | INVALID, catalog replicas, scored |
| 20 replay | final_4a_constrained_both_burst_run2_r2 | burst_rpr 2.0 | on | INVALID, kept, not a column |

Table columns follow the ten scored rows, in that order.

## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars from the scorer, on the four burst columns: `burst_rpr` 2.00, bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67. The START line sets `burst_window_seconds=5` and `burst_min_first_attempts=20`. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s of row timestamps (`interval_samples`). 1→2 and 2→3 take 10 s on these holds (`climb_interval_seconds=10s` on the START line). `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The scorer keeps an edge when it has a tick above the shed bar or a non-zero retry delta. On these ten columns that is frontend → productcatalogservice, recommendationservice → productcatalogservice, and frontend → recommendationservice. The other controlled edges are not in the tables. A bold file-streak cell is at least 30 seconds.

### File streak seconds / ticks above the shed bar (controller high)

| Edge | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → productcatalogservice | 22 / 91 (21) | 23 / 84 (21) | **┃** | 2 / 3 (2) | 0 / 6 (1) | **┃** | **54 / 90** | 0 / 3 | **┃** | 23 / 31 (15) | 8 / 21 (4) | **┃** | 2 / 2 (2) | 8 / 7 (2) |
| recommendationservice → productcatalogservice | 22 / 89 (20) | 22 / 80 (18) | **┃** | 0 / 1 (1) | 0 / 3 (1) | **┃** | 28 / 77 | 0 / 3 | **┃** | 8 / 14 (3) | 7 / 22 (4) | **┃** | 2 / 3 (2) | 8 / 6 (2) |
| frontend → recommendationservice | 23 / 111 (20) | 22 / 82 (18) | **┃** | 0 / 1 (1) | 0 / 1 (1) | **┃** | 26 / 82 | 0 / 0 | **┃** | 7 / 17 (3) | 9 / 24 (5) | **┃** | 2 / 4 (2) | 6 / 4 (2) |

### Mean / median / max / volume rpr

Mean rpr / median rpr / max rpr / volume rpr. Volume is the hold's Δretry / first attempts.

| Edge | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → productcatalogservice | 0.611 / 0.000 / 5.44 / 0.487 | 0.492 / 0.000 / 3.92 / 0.429 | **┃** | 0.043 / 0.000 / 1.31 / 0.034 | 0.089 / 0.000 / 4.63 / 0.026 | **┃** | 2.229 / 1.776 / 31.58 / 1.736 | 0.057 / 0.000 / 2.22 / 0.025 | **┃** | 0.247 / 0.000 / 1.80 / 0.209 | 0.221 / 0.000 / 4.01 / 0.138 | **┃** | 0.041 / 0.000 / 1.64 / 0.024 | 0.152 / 0.000 / 3.68 / 0.107 |
| recommendationservice → productcatalogservice | 1.131 / 0.122 / 19.00 / 0.432 | 0.999 / 0.127 / 19.00 / 0.451 | **┃** | 0.041 / 0.000 / 4.00 / 0.019 | 0.036 / 0.000 / 1.44 / 0.017 | **┃** | 2.526 / 2.618 / 34.00 / 1.513 | 0.101 / 0.000 / 7.00 / 0.027 | **┃** | 0.121 / 0.000 / 3.22 / 0.070 | 0.228 / 0.000 / 5.33 / 0.097 | **┃** | 0.048 / 0.000 / 1.82 / 0.027 | 0.115 / 0.000 / 3.38 / 0.042 |
| frontend → recommendationservice | 0.711 / 0.000 / 29.00 / 0.323 | 0.613 / 0.000 / 30.00 / 0.243 | **┃** | 0.004 / 0.000 / 0.49 / 0.004 | 0.008 / 0.000 / 1.59 / 0.006 | **┃** | 0.731 / 0.000 / 6.11 / 0.439 | 0.003 / 0.000 / 0.33 / 0.002 | **┃** | 0.101 / 0.000 / 5.43 / 0.058 | 0.258 / 0.000 / 16.00 / 0.078 | **┃** | 0.009 / 0.000 / 0.49 / 0.008 | 0.042 / 0.000 / 3.69 / 0.018 |

### Climb streaks, 1-attempt / 2-attempt

Samples at 1 attempt with rpr at or under 0.16, then samples at 2 attempts with rpr at or under 0.32. An em dash means that cap never applied.

| Edge | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → productcatalogservice | 2 / — | 3 / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | 2 / — | 2 / — | **┃** | — / — | 6 / 6 |
| recommendationservice → productcatalogservice | 1 / — | 5 / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | 8 / 5 | 1 / — | **┃** | — / — | 6 / 6 |
| frontend → recommendationservice | 11 / 10 | 11 / 11 | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | 7 / 7 | 8 / 7 | **┃** | — / — | 6 / 6 |

## 4a Burst

Burst mode was off on the four normal-mode RetryGuard columns and on both TopFull-only columns. RetryGuard is off on the TopFull-only cell, so the burst test does not run there. The normal-mode RetryGuard holds omit the three burst keys.

On the four burst columns the (a2) burst window is below. A cell is peak `burst_rpr5` / median `burst_rpr5` / samples at or above the bar in force / burst sheds, with the `burst_rpr5` sample count in parentheses. The 20-attempt volume floor makes the controller skip a thin window.

| Edge | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.00 / 0.00 / 0 / 0 (6) | 0.00 / 0.00 / 0 / 0 (4) | **┃** | 0.00 / 0.00 / 0 / 0 (97) | 0.00 / 0.00 / 0 / 0 (88) |
| frontend → currencyservice | 0.00 / 0.00 / 0 / 0 (357) | 0.00 / 0.00 / 0 / 0 (349) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) |
| checkoutservice → paymentservice | 0.00 / 0.00 / 0 / 0 (5) | 0.00 / 0.00 / 0 / 0 (4) | **┃** | 0.00 / 0.00 / 0 / 0 (92) | 0.00 / 0.00 / 0 / 0 (87) |
| checkoutservice → shippingservice | 0.00 / 0.00 / 0 / 0 (23) | 0.00 / 0.00 / 0 / 0 (20) | **┃** | 0.00 / 0.00 / 0 / 0 (101) | 0.00 / 0.00 / 0 / 0 (96) |
| frontend → adservice | 0.00 / 0.00 / 0 / 0 (4) | 0.00 / 0.00 / 0 / 0 (3) | **┃** | 0.00 / 0.00 / 0 / 0 (95) | 0.00 / 0.00 / 0 / 0 (88) |
| frontend → recommendationservice | 3.00 / 0.00 / 3 / 3 (224) | 3.54 / 0.00 / 4 / 4 (219) | **┃** | 0.27 / 0.00 / 0 / 0 (303) | 2.64 / 0.00 / 1 / 1 (286) |
| checkoutservice → currencyservice | 0.00 / 0.00 / 0 / 0 (5) | 0.00 / 0.00 / 0 / 0 (4) | **┃** | 0.00 / 0.00 / 0 / 0 (92) | 0.00 / 0.00 / 0 / 0 (87) |
| checkoutservice → emailservice | 0.00 / 0.00 / 0 / 0 (5) | 0.00 / 0.00 / 0 / 0 (4) | **┃** | 0.00 / 0.00 / 0 / 0 (92) | 0.00 / 0.00 / 0 / 0 (87) |
| frontend → productcatalogservice | 1.75 / 0.25 / 3 / 3 (54) | 2.81 / 0.02 / 4 / 4 (46) | **┃** | 0.35 / 0.00 / 0 / 0 (114) | 3.21 / 0.00 / 1 / 1 (98) |
| frontend → cartservice | 0.00 / 0.00 / 0 / 0 (362) | 0.00 / 0.00 / 0 / 0 (352) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| recommendationservice → productcatalogservice | 2.16 / 0.00 / 3 / 3 (42) | 2.77 / 0.09 / 4 / 4 (41) | **┃** | 0.53 / 0.00 / 0 / 0 (107) | 2.12 / 0.00 / 1 / 1 (93) |
| frontend → shippingservice | 0.00 / 0.00 / 0 / 0 (4) | 0.00 / 0.00 / 0 / 0 (5) | **┃** | 0.00 / 0.00 / 0 / 0 (97) | 0.00 / 0.00 / 0 / 0 (90) |
| checkoutservice → cartservice | 0.00 / 0.00 / 0 / 0 (23) | 0.00 / 0.00 / 0 / 0 (20) | **┃** | 0.00 / 0.00 / 0 / 0 (101) | 0.00 / 0.00 / 0 / 0 (96) |

## Rejection beside (a)

Longest streak / count of inbound rejection above 0.20. Bold when a controlled service's streak is at least 30. frontend and redis-cart stay plain. No controlled service on these columns reached a streak of 30.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 384 / 527 | 158 / 518 | **┃** | 85 / 203 | 82 / 204 | **┃** | 99 / 281 | 87 / 206 | **┃** | 116 / 330 | 164 / 320 | **┃** | 85 / 209 | 86 / 216 |
| checkoutservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 22 / 114 | 20 / 87 | **┃** | 0 / 0 | 0 / 0 | **┃** | 14 / 80 | 1 / 1 | **┃** | 17 / 90 | 15 / 73 | **┃** | 1 / 1 | 10 / 11 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 26 / 126 | 23 / 141 | **┃** | 1 / 1 | 0 / 0 | **┃** | 14 / 86 | 1 / 2 | **┃** | 18 / 104 | 16 / 91 | **┃** | 0 / 0 | 10 / 10 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

Share of detector samples at or above 1. Bold when the share is at least 0.5. No service on these columns reached 0.5. productcatalogservice is the highest share, about 21–25%.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| checkoutservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| recommendationservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| paymentservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| emailservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| productcatalogservice | 166/712 (23.3%) | 157/711 (22.1%) | **┃** | 160/713 (22.4%) | 151/713 (21.2%) | **┃** | 173/689 (25.1%) | 149/688 (21.7%) | **┃** | 162/710 (22.8%) | 167/711 (23.5%) | **┃** | 132/713 (18.5%) | 144/714 (20.2%) |
| cartservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| currencyservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| shippingservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| adservice | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
| redis-cart | 0/712 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/713 (0.0%) | **┃** | 0/689 (0.0%) | 0/688 (0.0%) | **┃** | 0/710 (0.0%) | 0/711 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) |
## (c) Retry volume

### Outbound retry delta by target

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 3,062 | 2,397 | **┃** | 51 | 75 | **┃** | 3,814 | 24 | **┃** | 615 | 779 | **┃** | 101 | 204 |
| productcatalogservice | 47,446 | 39,728 | **┃** | 2,031 | 1,545 | **┃** | 110,770 | 1,404 | **┃** | 20,118 | 14,256 | **┃** | 1,468 | 6,688 |

### Inbound resets, all 11 services

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 146 | 113 | **┃** | 0 | 0 | **┃** | 111 | 0 | **┃** | 114 | 129 | **┃** | 0 | 123 |
| checkoutservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| recommendationservice | 1,426 | 1,200 | **┃** | 17 | 35 | **┃** | 1,946 | 11 | **┃** | 1,326 | 1,043 | **┃** | 45 | 171 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 32,940 | 35,923 | **┃** | 309 | 330 | **┃** | 57,619 | 192 | **┃** | 31,640 | 32,967 | **┃** | 568 | 4,934 |
| cartservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

### grpc_4 / grpc_14

The same pair is what the retry policy counts on the four read callees.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 2,697 / 0 | 2,050 / 0 | **┃** | 34 / 0 | 40 / 0 | **┃** | 3,057 / 0 | 13 / 0 | **┃** | 1,969 / 0 | 1,640 / 0 | **┃** | 59 / 0 | 287 / 0 |
| productcatalogservice | 67,934 / 3,307 | 61,694 / 2,985 | **┃** | 208 / 1,803 | 156 / 1,233 | **┃** | 80,828 / 6,680 | 148 / 1,339 | **┃** | 56,834 / 742 | 53,406 / 2,393 | **┃** | 284 / 609 | 5,478 / 351 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## RetryGuard toggles

### Part 1 — counts and timestamps

ON→OFF is a shed from the attempts cap to 0. 0→1 is the re-enable step. 1→2 and 2→3 are climbs. On a burst hold the count table adds `ON→OFF burst`, the sheds whose log line is `metric=rpr_burst`. The timestamp `Value` on those rows is the 5 s aggregate, and the step is marked `(burst)`.

`final_4a_constrained_tf_only_run1` and `final_4a_constrained_tf_only_run2_r2` have no `retryguard.log`. `final_4a_constrained_both_normal_run1`, `final_4a_constrained_both_normal_run2`, and `final_4a_constrained_both_burst_run1` have a log and no transition lines.

#### final_4a_constrained_rg_only_normal_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 4 | 0 | 0 | 0 |
| productcatalogservice | 0 | 4 | 0 | 0 |
| frontend → recommendationservice | 3 | 0 | 3 | 3 |
| recommendationservice → productcatalogservice | 3 | 0 | 0 | 0 |
| recommendationservice | 0 | 3 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T04:05:15Z | frontend → productcatalogservice | ON→OFF | 3 | rpr 2.56 |
| 2026-10-13T04:07:10Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:08:04Z | frontend → recommendationservice | ON→OFF | 3 | rpr 10.00 |
| 2026-10-13T04:08:05Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 1.10 |
| 2026-10-13T04:08:08Z | recommendationservice → productcatalogservice | ON→OFF | 3 | rpr 1.00 |
| 2026-10-13T04:08:30Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:08:30Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:08:42Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:08:53Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T04:09:54Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 1.00 |
| 2026-10-13T04:09:54Z | recommendationservice → productcatalogservice | ON→OFF | 1 | rpr 0.73 |
| 2026-10-13T04:09:54Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.40 |
| 2026-10-13T04:10:20Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:10:20Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:10:31Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:10:43Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T04:13:12Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 0.75 |
| 2026-10-13T04:13:12Z | recommendationservice → productcatalogservice | ON→OFF | 1 | rpr 1.00 |
| 2026-10-13T04:13:12Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.09 |
| 2026-10-13T04:13:41Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:13:42Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:13:52Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:14:03Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

#### final_4a_constrained_rg_only_normal_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 4 | 0 | 0 | 0 |
| frontend → recommendationservice | 3 | 0 | 3 | 3 |
| recommendationservice → productcatalogservice | 3 | 0 | 0 | 0 |
| recommendationservice | 0 | 3 | 0 | 0 |
| productcatalogservice | 0 | 4 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T04:44:23Z | frontend → productcatalogservice | ON→OFF | 3 | rpr 2.10 |
| 2026-10-13T04:45:21Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.65 |
| 2026-10-13T04:45:24Z | recommendationservice → productcatalogservice | ON→OFF | 3 | rpr 1.86 |
| 2026-10-13T04:45:53Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:46:04Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:46:15Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T04:46:16Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:47:12Z | frontend → recommendationservice | ON→OFF | 3 | rpr 3.00 |
| 2026-10-13T04:47:13Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 0.76 |
| 2026-10-13T04:47:13Z | recommendationservice → productcatalogservice | ON→OFF | 1 | rpr 1.00 |
| 2026-10-13T04:47:37Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:47:37Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:47:48Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:47:59Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T04:49:05Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 1.02 |
| 2026-10-13T04:49:28Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:52:14Z | frontend → productcatalogservice | ON→OFF | 1 | rpr 0.68 |
| 2026-10-13T04:52:15Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.85 |
| 2026-10-13T04:52:15Z | recommendationservice → productcatalogservice | ON→OFF | 1 | rpr 1.00 |
| 2026-10-13T04:52:37Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:52:37Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T04:52:48Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T04:52:59Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

#### final_4a_constrained_rg_only_burst_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 3 | 0 | 3 | 3 | 3 |
| recommendationservice → productcatalogservice | 3 | 0 | 1 | 0 | 3 |
| frontend → productcatalogservice | 4 | 0 | 0 | 0 | 3 |
| recommendationservice | 0 | 3 | 0 | 0 | 0 |
| productcatalogservice | 0 | 4 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T07:41:49Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.31 |
| 2026-10-13T07:41:51Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 3 | rpr 2.16 |
| 2026-10-13T07:42:05Z | frontend → productcatalogservice | ON→OFF | 3 | rpr 1.77 |
| 2026-10-13T07:44:03Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:44:03Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:44:16Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T07:44:29Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T07:44:43Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.88 |
| 2026-10-13T07:44:43Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.75 |
| 2026-10-13T07:44:43Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 3.00 |
| 2026-10-13T07:45:23Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:45:25Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:45:35Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T07:45:48Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T07:46:30Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.70 |
| 2026-10-13T07:46:30Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 1 | rpr 1.02 |
| 2026-10-13T07:46:30Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.98 |
| 2026-10-13T07:47:15Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:47:15Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T07:47:26Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T07:47:38Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T07:49:48Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.72 |
| 2026-10-13T07:49:52Z | recommendationservice → productcatalogservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T07:50:25Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |

#### final_4a_constrained_rg_only_burst_run2_r2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 4 | 0 | 0 | 0 | 4 |
| recommendationservice → productcatalogservice | 4 | 0 | 0 | 0 | 4 |
| frontend → recommendationservice | 4 | 0 | 4 | 4 | 4 |
| recommendationservice | 0 | 4 | 0 | 0 | 0 |
| productcatalogservice | 0 | 4 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T08:36:11Z | frontend → productcatalogservice | ON→OFF (burst) | 3 | rpr 2.81 |
| 2026-10-13T08:36:11Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 3 | rpr 2.77 |
| 2026-10-13T08:36:11Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.83 |
| 2026-10-13T08:37:50Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:38:02Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T08:38:13Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T08:38:21Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:38:47Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.82 |
| 2026-10-13T08:38:47Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 1 | rpr 1.02 |
| 2026-10-13T08:38:47Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 3.54 |
| 2026-10-13T08:39:28Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:39:28Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:39:39Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T08:39:51Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T08:40:47Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.86 |
| 2026-10-13T08:40:47Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.88 |
| 2026-10-13T08:40:47Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.47 |
| 2026-10-13T08:41:29Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:41:31Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:41:41Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T08:41:54Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T08:44:05Z | frontend → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.71 |
| 2026-10-13T08:44:07Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 1 | rpr 0.69 |
| 2026-10-13T08:44:09Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 3.36 |
| 2026-10-13T08:44:50Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:44:50Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T08:45:03Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T08:45:15Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

#### final_4a_constrained_both_burst_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 1 | 0 | 1 | 1 | 1 |
| recommendationservice → productcatalogservice | 1 | 0 | 1 | 1 | 1 |
| frontend → recommendationservice | 1 | 0 | 1 | 1 | 1 |
| productcatalogservice | 0 | 1 | 0 | 0 | 0 |
| recommendationservice | 0 | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-13T09:30:42Z | frontend → productcatalogservice | ON→OFF (burst) | 3 | rpr 3.21 |
| 2026-10-13T09:30:42Z | recommendationservice → productcatalogservice | ON→OFF (burst) | 3 | rpr 2.12 |
| 2026-10-13T09:30:42Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.64 |
| 2026-10-13T09:31:19Z | productcatalogservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T09:31:19Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-13T09:31:31Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T09:31:39Z | frontend → productcatalogservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T09:31:39Z | recommendationservice → productcatalogservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-13T09:31:43Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T09:31:51Z | frontend → productcatalogservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-13T09:31:51Z | recommendationservice → productcatalogservice | 2→3 | 2 | rpr 0.00 |

### Part 2 — per callee

Each table is one caller→callee edge that shed on at least one column. ON→OFF counts are that edge. OFF→ON counts are the callee re-enable that closed an OFF window of that edge. A burst shed's rpr is tagged `b`. Time OFF is seconds from the shed to the matching OFF→ON, or to EXIT. OFF rejection is the min / median of `metric=rejection` samples on the callee while that edge is at 0, pooled across the edge's OFF windows. The streak is the longest run of those samples strictly below 0.25. An em dash means that edge never went to 0 on that column, or the column has no `retryguard.log`. The first-shed row is included because this guide has burst columns.

#### frontend → productcatalogservice

| frontend → productcatalogservice | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF (burst) / OFF→ON | 4 / 4 | 4 / 4 | **┃** | — | — | **┃** | — | — | **┃** | 4 (3) / 4 | 4 (4) / 4 | **┃** | — | 1 (1) / 1 |
| Shed rpr | 2.56; 1.10; 1.00; 0.75 | 2.10; 0.76; 1.02; 0.68 | **┃** | — | — | **┃** | — | — | **┃** | 1.77; 0.88b; 0.70b; 0.72b | 2.81b; 0.82b; 0.86b; 0.71b | **┃** | — | 3.21b |
| First shed, seconds after first OBSERVE | 52 | 45 | **┃** | — | — | **┃** | — | — | **┃** | 54 | 41 | **┃** | — | 40 |
| Attempts after re-enable | 1 | 1 | **┃** | — | — | **┃** | — | — | **┃** | 1 | 1 | **┃** | — | 3 |
| Time OFF (s) | 115; 25; 26; 30 | 113; 24; 23; 23 | **┃** | — | — | **┃** | — | — | **┃** | 118; 42; 45; 37 | 130; 41; 44; 45 | **┃** | — | 37 |
| OFF rejection min / median | 0.000 / 0.097 | 0.000 / 0.002 | **┃** | — | — | **┃** | — | — | **┃** | 0.000 / 0.714 | 0.000 / 0.715 | **┃** | — | 0.000 / 0.000 |
| Longest streak under 0.25 | 20 | 19 | **┃** | — | — | **┃** | — | — | **┃** | 14 | 13 | **┃** | — | 10 |

frontend → productcatalogservice shed on 5 of the ten columns. Re-enable fired on final_4a_constrained_rg_only_normal_run1, final_4a_constrained_rg_only_normal_run2, final_4a_constrained_rg_only_burst_run1, final_4a_constrained_rg_only_burst_run2_r2, final_4a_constrained_both_burst_run2. Attempts at EXIT: final_4a_constrained_rg_only_normal_run1 to 1; final_4a_constrained_rg_only_normal_run2 to 1; final_4a_constrained_rg_only_burst_run1 to 1; final_4a_constrained_rg_only_burst_run2_r2 to 1; final_4a_constrained_both_burst_run2 back to 3. The longest under-0.25 streak is 20 samples, on final_4a_constrained_rg_only_normal_run1.

#### recommendationservice → productcatalogservice

| recommendationservice → productcatalogservice | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF (burst) / OFF→ON | 3 / 3 | 3 / 3 | **┃** | — | — | **┃** | — | — | **┃** | 3 (3) / 3 | 4 (4) / 4 | **┃** | — | 1 (1) / 1 |
| Shed rpr | 1.00; 0.73; 1.00 | 1.86; 1.00; 1.00 | **┃** | — | — | **┃** | — | — | **┃** | 2.16b; 0.75b; 1.02b | 2.77b; 1.02b; 0.88b; 0.69b | **┃** | — | 2.12b |
| First shed, seconds after first OBSERVE | 225 | 106 | **┃** | — | — | **┃** | — | — | **┃** | 40 | 41 | **┃** | — | 40 |
| Attempts after re-enable | 1 | 1 | **┃** | — | — | **┃** | — | — | **┃** | 2 | 1 | **┃** | — | 3 |
| Time OFF (s) | 22; 26; 30 | 52; 24; 22 | **┃** | — | — | **┃** | — | — | **┃** | 132; 42; 45 | 130; 41; 44; 43 | **┃** | — | 37 |
| OFF rejection min / median | 0.000 / 0.000 | 0.000 / 0.000 | **┃** | — | — | **┃** | — | — | **┃** | 0.000 / 0.748 | 0.000 / 0.687 | **┃** | — | 0.000 / 0.000 |
| Longest streak under 0.25 | 20 | 19 | **┃** | — | — | **┃** | — | — | **┃** | 14 | 13 | **┃** | — | 10 |

recommendationservice → productcatalogservice shed on 5 of the ten columns. Re-enable fired on final_4a_constrained_rg_only_normal_run1, final_4a_constrained_rg_only_normal_run2, final_4a_constrained_rg_only_burst_run1, final_4a_constrained_rg_only_burst_run2_r2, final_4a_constrained_both_burst_run2. Attempts at EXIT: final_4a_constrained_rg_only_normal_run1 to 1; final_4a_constrained_rg_only_normal_run2 to 1; final_4a_constrained_rg_only_burst_run1 to 2; final_4a_constrained_rg_only_burst_run2_r2 to 1; final_4a_constrained_both_burst_run2 back to 3. The longest under-0.25 streak is 20 samples, on final_4a_constrained_rg_only_normal_run1.

#### frontend → recommendationservice

| frontend → recommendationservice | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF (burst) / OFF→ON | 3 / 3 | 3 / 3 | **┃** | — | — | **┃** | — | — | **┃** | 3 (3) / 3 | 4 (4) / 4 | **┃** | — | 1 (1) / 1 |
| Shed rpr | 10.00; 2.40; 2.09 | 2.65; 3.00; 1.85 | **┃** | — | — | **┃** | — | — | **┃** | 2.31b; 3.00b; 2.98b | 2.83b; 3.54b; 2.47b; 3.36b | **┃** | — | 2.64b |
| First shed, seconds after first OBSERVE | 221 | 103 | **┃** | — | — | **┃** | — | — | **┃** | 38 | 41 | **┃** | — | 40 |
| Attempts after re-enable | 3 | 3 | **┃** | — | — | **┃** | — | — | **┃** | 3 | 3 | **┃** | — | 3 |
| Time OFF (s) | 26; 26; 29 | 32; 25; 22 | **┃** | — | — | **┃** | — | — | **┃** | 134; 40; 45 | 99; 41; 42; 41 | **┃** | — | 37 |
| OFF rejection min / median | 0.000 / 0.000 | 0.000 / 0.000 | **┃** | — | — | **┃** | — | — | **┃** | 0.000 / 0.947 | 0.000 / 0.441 | **┃** | — | 0.000 / 0.000 |
| Longest streak under 0.25 | 20 | 19 | **┃** | — | — | **┃** | — | — | **┃** | 14 | 11 | **┃** | — | 10 |

frontend → recommendationservice shed on 5 of the ten columns. Re-enable fired on final_4a_constrained_rg_only_normal_run1, final_4a_constrained_rg_only_normal_run2, final_4a_constrained_rg_only_burst_run1, final_4a_constrained_rg_only_burst_run2_r2, final_4a_constrained_both_burst_run2. Attempts at EXIT: final_4a_constrained_rg_only_normal_run1 back to 3; final_4a_constrained_rg_only_normal_run2 back to 3; final_4a_constrained_rg_only_burst_run1 back to 3; final_4a_constrained_rg_only_burst_run2_r2 back to 3; final_4a_constrained_both_burst_run2 back to 3. The longest under-0.25 streak is 20 samples, on final_4a_constrained_rg_only_normal_run1.

checkoutservice, paymentservice, emailservice, cartservice, currencyservice, shippingservice, and adservice have no shed and no re-enable on any scored column.

## Locust goodput

Mean Goodput while RPS > 0, per API.

| API | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.1 | 0.1 | **┃** | 2.4 | 2.3 | **┃** | 0.1 | 2.5 | **┃** | 0.1 | 0.1 | **┃** | 2.2 | 1.7 |
| postcheckout | 0.1 | 0.1 | **┃** | 2.6 | 2.6 | **┃** | 0.1 | 2.7 | **┃** | 0.1 | 0.1 | **┃** | 2.4 | 1.9 |
| getcart | 0.2 | 0.1 | **┃** | 2.7 | 2.7 | **┃** | 0.1 | 2.8 | **┃** | 0.1 | 0.1 | **┃** | 2.5 | 2.3 |
| postcart | 55.9 | 40.6 | **┃** | 40.0 | 42.4 | **┃** | 39.1 | 31.4 | **┃** | 41.7 | 36.0 | **┃** | 47.4 | 56.2 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.4 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean Fail / RPS while RPS > 0, per API.

| API | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.958 | 0.968 | **┃** | 0.721 | 0.724 | **┃** | 0.951 | 0.704 | **┃** | 0.963 | 0.962 | **┃** | 0.729 | 0.747 |
| postcheckout | 0.959 | 0.957 | **┃** | 0.700 | 0.700 | **┃** | 0.952 | 0.695 | **┃** | 0.954 | 0.959 | **┃** | 0.711 | 0.729 |
| getcart | 0.952 | 0.956 | **┃** | 0.688 | 0.692 | **┃** | 0.951 | 0.678 | **┃** | 0.958 | 0.959 | **┃** | 0.708 | 0.717 |
| postcart | 0.847 | 0.878 | **┃** | 0.896 | 0.896 | **┃** | 0.856 | 0.914 | **┃** | 0.873 | 0.888 | **┃** | 0.886 | 0.854 |
| emptycart | 0.007 | 0.015 | **┃** | 0.000 | 0.000 | **┃** | 0.088 | 0.000 | **┃** | 0.012 | 0.002 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean Latency95 (ms) while RPS > 0, per API.

| API | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 618 | 509 | **┃** | 381 | 361 | **┃** | 698 | 327 | **┃** | 344 | 393 | **┃** | 372 | 379 |
| postcheckout | 664 | 570 | **┃** | 379 | 366 | **┃** | 733 | 333 | **┃** | 321 | 438 | **┃** | 371 | 385 |
| getcart | 646 | 603 | **┃** | 341 | 330 | **┃** | 658 | 306 | **┃** | 302 | 400 | **┃** | 340 | 352 |
| postcart | 432 | 405 | **┃** | 285 | 208 | **┃** | 707 | 315 | **┃** | 318 | 303 | **┃** | 269 | 215 |
| emptycart | 11 | 10 | **┃** | 13 | 12 | **┃** | 12 | 11 | **┃** | 12 | 10 | **┃** | 14 | 12 |

## Inbound arrival rate

Positive Δtotal over the elapsed time of `service_inbound.csv`, per service, req/s.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 441.9 | 457.0 | **┃** | 80.7 | 110.4 | **┃** | 394.3 | 74.5 | **┃** | 465.1 | 452.0 | **┃** | 101.1 | 193.0 |
| checkoutservice | 0.3 | 0.3 | **┃** | 2.8 | 2.7 | **┃** | 0.2 | 2.9 | **┃** | 0.2 | 0.2 | **┃** | 2.6 | 2.0 |
| recommendationservice | 18.3 | 17.6 | **┃** | 20.5 | 20.4 | **┃** | 19.6 | 21.3 | **┃** | 17.1 | 16.2 | **┃** | 20.3 | 17.3 |
| paymentservice | 0.3 | 0.3 | **┃** | 2.8 | 2.7 | **┃** | 0.2 | 2.9 | **┃** | 0.2 | 0.2 | **┃** | 2.6 | 2.0 |
| emailservice | 0.3 | 0.3 | **┃** | 2.8 | 2.7 | **┃** | 0.2 | 2.9 | **┃** | 0.2 | 0.2 | **┃** | 2.6 | 2.0 |
| productcatalogservice | 217.1 | 198.1 | **┃** | 94.8 | 94.0 | **┃** | 271.7 | 87.6 | **┃** | 179.3 | 175.6 | **┃** | 94.8 | 108.2 |
| cartservice | 63.6 | 50.9 | **┃** | 59.0 | 60.6 | **┃** | 50.4 | 52.3 | **┃** | 52.4 | 47.6 | **┃** | 63.9 | 70.3 |
| currencyservice | 8.9 | 8.9 | **┃** | 22.9 | 22.5 | **┃** | 8.5 | 23.6 | **┃** | 9.5 | 9.5 | **┃** | 21.7 | 18.3 |
| shippingservice | 0.8 | 0.8 | **┃** | 8.4 | 8.2 | **┃** | 0.7 | 8.6 | **┃** | 0.6 | 0.7 | **┃** | 7.8 | 6.3 |
| adservice | 0.2 | 0.2 | **┃** | 2.8 | 2.6 | **┃** | 0.2 | 2.8 | **┃** | 0.2 | 0.2 | **┃** | 2.5 | 2.0 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn

Δrq_time_sum_ms / Δrq_time_count, milliseconds.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 229 | 207 | **┃** | 165 | 117 | **┃** | 333 | 141 | **┃** | 181 | 184 | **┃** | 135 | 113 |
| checkoutservice | 52 | 48 | **┃** | 52 | 49 | **┃** | 48 | 54 | **┃** | 47 | 52 | **┃** | 64 | 49 |
| recommendationservice | 151 | 127 | **┃** | 48 | 46 | **┃** | 162 | 43 | **┃** | 115 | 116 | **┃** | 51 | 58 |
| paymentservice | 4 | 3 | **┃** | 2 | 2 | **┃** | 1 | 2 | **┃** | 2 | 3 | **┃** | 2 | 2 |
| emailservice | 6 | 5 | **┃** | 6 | 7 | **┃** | 6 | 9 | **┃** | 6 | 7 | **┃** | 10 | 6 |
| productcatalogservice | 388 | 394 | **┃** | 112 | 106 | **┃** | 400 | 94 | **┃** | 393 | 401 | **┃** | 110 | 138 |
| cartservice | 8 | 8 | **┃** | 6 | 5 | **┃** | 8 | 4 | **┃** | 8 | 7 | **┃** | 5 | 5 |
| currencyservice | 1 | 1 | **┃** | 2 | 2 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 2 | 1 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.202 | 0.210 | **┃** | 0.099 | 0.066 | **┃** | 0.159 | 0.093 | **┃** | 0.233 | 0.252 | **┃** | 0.077 | 0.068 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.253 | 0.197 | **┃** | 0.003 | 0.003 | **┃** | 0.291 | 0.001 | **┃** | 0.199 | 0.171 | **┃** | 0.005 | 0.026 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.619 | 0.653 | **┃** | 0.006 | 0.005 | **┃** | 0.703 | 0.004 | **┃** | 0.656 | 0.647 | **┃** | 0.008 | 0.085 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max sum `cpu_millicores` across replicas, so frontend can sit above its per-pod quota. productcatalogservice's quota cell is 50. The replica mode is 1. The catalog replica gate still failed on the INVALID columns, because some samples were 0 ready replicas rather than a different mode.

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 495 / 687 | 1150 / 4 / 516 / 721 | **┃** | 1150 / 4 / 124 / 351 | 1150 / 4 / 161 / 431 | **┃** | 1150 / 4 / 481 / 759 | 1150 / 4 / 118 / 303 | **┃** | 1150 / 4 / 519 / 768 | 1150 / 4 / 517 / 729 | **┃** | 1150 / 4 / 137 / 342 | 1150 / 4 / 253 / 381 |
| checkoutservice | 800 / 1 / 10 / 73 | 800 / 1 / 10 / 72 | **┃** | 800 / 1 / 55 / 219 | 800 / 1 / 52 / 213 | **┃** | 800 / 1 / 9 / 93 | 800 / 1 / 55 / 213 | **┃** | 800 / 1 / 8 / 93 | 800 / 1 / 8 / 71 | **┃** | 800 / 1 / 47 / 191 | 800 / 1 / 43 / 178 |
| recommendationservice | 1150 / 1 / 45 / 69 | 1150 / 1 / 44 / 65 | **┃** | 1150 / 1 / 54 / 80 | 1150 / 1 / 54 / 78 | **┃** | 1150 / 1 / 46 / 63 | 1150 / 1 / 55 / 78 | **┃** | 1150 / 1 / 47 / 65 | 1150 / 1 / 45 / 64 | **┃** | 1150 / 1 / 52 / 74 | 1150 / 1 / 47 / 67 |
| paymentservice | 155 / 1 / 5 / 8 | 155 / 1 / 5 / 10 | **┃** | 155 / 1 / 7 / 14 | 155 / 1 / 7 / 16 | **┃** | 155 / 1 / 5 / 9 | 155 / 1 / 7 / 14 | **┃** | 155 / 1 / 5 / 8 | 155 / 1 / 5 / 7 | **┃** | 155 / 1 / 6 / 15 | 155 / 1 / 6 / 16 |
| emailservice | 120 / 1 / 11 / 16 | 120 / 1 / 11 / 16 | **┃** | 120 / 1 / 15 / 30 | 120 / 1 / 14 / 29 | **┃** | 120 / 1 / 11 / 18 | 120 / 1 / 15 / 29 | **┃** | 120 / 1 / 10 / 18 | 120 / 1 / 11 / 17 | **┃** | 120 / 1 / 14 / 29 | 120 / 1 / 14 / 26 |
| productcatalogservice | 50 / 1 / 19 / 57 | 50 / 1 / 22 / 56 | **┃** | 50 / 1 / 19 / 53 | 50 / 1 / 14 / 52 | **┃** | 50 / 1 / 23 / 57 | 50 / 1 / 17 / 54 | **┃** | 50 / 1 / 21 / 55 | 50 / 1 / 19 / 55 | **┃** | 50 / 1 / 19 / 53 | 50 / 1 / 20 / 53 |
| cartservice | 800 / 1 / 53 / 241 | 800 / 1 / 41 / 136 | **┃** | 800 / 1 / 43 / 134 | 800 / 1 / 52 / 221 | **┃** | 800 / 1 / 38 / 131 | 800 / 1 / 52 / 205 | **┃** | 800 / 1 / 40 / 185 | 800 / 1 / 41 / 180 | **┃** | 800 / 1 / 62 / 212 | 800 / 1 / 66 / 223 |
| currencyservice | 770 / 1 / 12 / 25 | 770 / 1 / 12 / 22 | **┃** | 770 / 1 / 19 / 47 | 770 / 1 / 19 / 48 | **┃** | 770 / 1 / 12 / 28 | 770 / 1 / 20 / 48 | **┃** | 770 / 1 / 12 / 26 | 770 / 1 / 12 / 22 | **┃** | 770 / 1 / 18 / 45 | 770 / 1 / 17 / 47 |
| shippingservice | 770 / 1 / 7 / 13 | 770 / 1 / 7 / 13 | **┃** | 770 / 1 / 11 / 28 | 770 / 1 / 11 / 26 | **┃** | 770 / 1 / 7 / 15 | 770 / 1 / 11 / 28 | **┃** | 770 / 1 / 7 / 16 | 770 / 1 / 7 / 13 | **┃** | 770 / 1 / 10 / 24 | 770 / 1 / 10 / 25 |
| adservice | 1150 / 1 / 28 / 33 | 1150 / 1 / 28 / 32 | **┃** | 1150 / 1 / 30 / 38 | 1150 / 1 / 28 / 38 | **┃** | 1150 / 1 / 28 / 32 | 1150 / 1 / 30 / 49 | **┃** | 1150 / 1 / 28 / 36 | 1150 / 1 / 28 / 32 | **┃** | 1150 / 1 / 27 / 37 | 1150 / 1 / 29 / 38 |
| redis-cart | 540 / 1 / 9 / 23 | 540 / 1 / 9 / 23 | **┃** | 540 / 1 / 10 / 22 | 540 / 1 / 10 / 23 | **┃** | 540 / 1 / 9 / 20 | 540 / 1 / 9 / 21 | **┃** | 540 / 1 / 9 / 24 | 540 / 1 / 9 / 24 | **┃** | 540 / 1 / 10 / 23 | 540 / 1 / 10 / 28 |

### Fraction of per-pod quota × replicas (mean / max)

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.11 / 0.15 | 0.11 / 0.16 | **┃** | 0.03 / 0.08 | 0.03 / 0.09 | **┃** | 0.10 / 0.17 | 0.03 / 0.07 | **┃** | 0.11 / 0.17 | 0.11 / 0.16 | **┃** | 0.03 / 0.07 | 0.06 / 0.08 |
| checkoutservice | 0.01 / 0.09 | 0.01 / 0.09 | **┃** | 0.07 / 0.27 | 0.07 / 0.27 | **┃** | 0.01 / 0.12 | 0.07 / 0.27 | **┃** | 0.01 / 0.12 | 0.01 / 0.09 | **┃** | 0.06 / 0.24 | 0.05 / 0.22 |
| recommendationservice | 0.04 / 0.06 | 0.04 / 0.06 | **┃** | 0.05 / 0.07 | 0.05 / 0.07 | **┃** | 0.04 / 0.05 | 0.05 / 0.07 | **┃** | 0.04 / 0.06 | 0.04 / 0.06 | **┃** | 0.05 / 0.06 | 0.04 / 0.06 |
| paymentservice | 0.03 / 0.05 | 0.03 / 0.06 | **┃** | 0.04 / 0.09 | 0.04 / 0.10 | **┃** | 0.03 / 0.06 | 0.04 / 0.09 | **┃** | 0.03 / 0.05 | 0.03 / 0.05 | **┃** | 0.04 / 0.10 | 0.04 / 0.10 |
| emailservice | 0.09 / 0.13 | 0.09 / 0.13 | **┃** | 0.12 / 0.25 | 0.12 / 0.24 | **┃** | 0.09 / 0.15 | 0.12 / 0.24 | **┃** | 0.09 / 0.15 | 0.09 / 0.14 | **┃** | 0.12 / 0.24 | 0.11 / 0.22 |
| productcatalogservice | 0.39 / 1.14 | 0.37 / 1.12 | **┃** | 0.38 / 1.06 | 0.28 / 1.04 | **┃** | 0.48 / 1.14 | 0.35 / 1.08 | **┃** | 0.34 / 1.10 | 0.38 / 1.10 | **┃** | 0.39 / 1.06 | 0.33 / 1.06 |
| cartservice | 0.07 / 0.30 | 0.05 / 0.17 | **┃** | 0.05 / 0.17 | 0.07 / 0.28 | **┃** | 0.05 / 0.16 | 0.06 / 0.26 | **┃** | 0.05 / 0.23 | 0.05 / 0.23 | **┃** | 0.08 / 0.27 | 0.08 / 0.28 |
| currencyservice | 0.02 / 0.03 | 0.02 / 0.03 | **┃** | 0.03 / 0.06 | 0.02 / 0.06 | **┃** | 0.02 / 0.04 | 0.03 / 0.06 | **┃** | 0.02 / 0.03 | 0.02 / 0.03 | **┃** | 0.02 / 0.06 | 0.02 / 0.06 |
| shippingservice | 0.01 / 0.02 | 0.01 / 0.02 | **┃** | 0.01 / 0.04 | 0.01 / 0.03 | **┃** | 0.01 / 0.02 | 0.01 / 0.04 | **┃** | 0.01 / 0.02 | 0.01 / 0.02 | **┃** | 0.01 / 0.03 | 0.01 / 0.03 |
| adservice | 0.02 / 0.03 | 0.02 / 0.03 | **┃** | 0.03 / 0.03 | 0.02 / 0.03 | **┃** | 0.02 / 0.03 | 0.03 / 0.04 | **┃** | 0.02 / 0.03 | 0.02 / 0.03 | **┃** | 0.02 / 0.03 | 0.03 / 0.03 |
| redis-cart | 0.02 / 0.04 | 0.02 / 0.04 | **┃** | 0.02 / 0.04 | 0.02 / 0.04 | **┃** | 0.02 / 0.04 | 0.02 / 0.04 | **┃** | 0.02 / 0.04 | 0.02 / 0.04 | **┃** | 0.02 / 0.04 | 0.02 / 0.05 |

## Detector max utilization

Max utilization in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | final_4a_constrained_rg_only_normal_run1 | final_4a_constrained_rg_only_normal_run2 | **┃** | final_4a_constrained_both_normal_run1 | final_4a_constrained_both_normal_run2 | **┃** | final_4a_constrained_tf_only_run1 | final_4a_constrained_tf_only_run2_r2 | **┃** | final_4a_constrained_rg_only_burst_run1 | final_4a_constrained_rg_only_burst_run2_r2 | **┃** | final_4a_constrained_both_burst_run1 | final_4a_constrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.319 | 0.347 | **┃** | 0.154 | 0.150 | **┃** | 0.258 | 0.144 | **┃** | 0.556 | 0.314 | **┃** | 0.130 | 0.287 |
| checkoutservice | 0.199 | 0.147 | **┃** | 0.381 | 0.396 | **┃** | 0.181 | 0.365 | **┃** | 0.215 | 0.140 | **┃** | 0.359 | 0.321 |
| recommendationservice | 0.146 | 0.090 | **┃** | 0.100 | 0.104 | **┃** | 0.135 | 0.097 | **┃** | 0.087 | 0.089 | **┃** | 0.098 | 0.090 |
| paymentservice | 0.316 | 0.290 | **┃** | 0.361 | 0.297 | **┃** | 0.277 | 0.303 | **┃** | 0.284 | 0.290 | **┃** | 0.316 | 0.355 |
| emailservice | 0.375 | 0.425 | **┃** | 0.533 | 0.517 | **┃** | 0.408 | 0.508 | **┃** | 0.392 | 0.417 | **┃** | 0.508 | 0.508 |
| productcatalogservice | 1.320 | 1.380 | **┃** | 1.200 | 1.200 | **┃** | 1.300 | 1.220 | **┃** | 1.240 | 1.480 | **┃** | 1.180 | 1.280 |
| cartservice | 0.374 | 0.266 | **┃** | 0.260 | 0.339 | **┃** | 0.270 | 0.328 | **┃** | 0.281 | 0.426 | **┃** | 0.324 | 0.339 |
| currencyservice | 0.077 | 0.071 | **┃** | 0.114 | 0.112 | **┃** | 0.071 | 0.103 | **┃** | 0.090 | 0.069 | **┃** | 0.095 | 0.164 |
| shippingservice | 0.061 | 0.064 | **┃** | 0.090 | 0.069 | **┃** | 0.058 | 0.078 | **┃** | 0.066 | 0.051 | **┃** | 0.081 | 0.070 |
| adservice | 0.057 | 0.063 | **┃** | 0.071 | 0.057 | **┃** | 0.063 | 0.095 | **┃** | 0.075 | 0.057 | **┃** | 0.065 | 0.068 |
| redis-cart | 0.070 | 0.100 | **┃** | 0.104 | 0.081 | **┃** | 0.104 | 0.087 | **┃** | 0.144 | 0.178 | **┃** | 0.154 | 0.191 |

## TopFull live caps

A live read has `threshold_fresh=1` and a threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. The series below are the scorer's collapsed spans.

### final_4a_constrained_rg_only_normal_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 04:02:45–04:14:35 |
| postcheckout | no cap 04:02:45–04:14:35 |
| getcart | no cap 04:02:45–04:14:35 |
| postcart | no cap 04:02:45–04:14:35 |
| emptycart | no cap 04:02:45–04:14:35 |

### final_4a_constrained_rg_only_normal_run2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 04:42:05–04:53:50 |
| postcheckout | no cap 04:42:05–04:53:50 |
| getcart | no cap 04:42:05–04:53:50 |
| postcart | no cap 04:42:05–04:53:50 |
| emptycart | no cap 04:42:05–04:53:50 |

### final_4a_constrained_both_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 05:18:10–05:20:00; 10 at 05:20:05; no cap 05:20:08–05:20:10; 10 05:20:13–05:20:50; no cap 05:20:51–05:20:55; 10 05:21:00–05:21:20; no cap 05:21:21–05:21:25; 10 05:21:30–05:21:35; 10.2 at 05:21:40; 10 05:21:45–05:21:55; no cap at 05:22:00; 10 05:22:03–05:22:20; no cap at 05:22:25; 11 05:22:29–05:23:15; 10 05:23:20–05:23:25; 10.2 at 05:23:30; 10.1 at 05:23:35; 10.3 at 05:23:40; no cap 05:23:41–05:25:15; 10 05:25:20–05:25:30; no cap 05:25:35–05:25:40; 10 at 05:25:45; 11 05:25:50–05:28:31; 10.7 at 05:28:35; 10.717 at 05:28:37; no cap at 05:28:40; 10 05:28:45–05:28:55; 11 05:29:00–05:30:00 |
| postcheckout | no cap 05:18:10–05:20:00; 10 at 05:20:05; no cap at 05:20:10; 10 05:20:13–05:21:35; 10.2 at 05:21:40; 10 05:21:45–05:22:22; no cap at 05:22:25; 11 05:22:30–05:23:16; 10 at 05:23:18; no cap at 05:23:20; 10 at 05:23:25; 10.2 at 05:23:30; 10.1 at 05:23:35; 10.3 at 05:23:40; no cap 05:23:45–05:25:15; 10 05:25:20–05:25:30; no cap 05:25:35–05:25:40; 10 at 05:25:45; 11 05:25:46–05:28:30; 10.7 at 05:28:35; no cap at 05:28:40; 10 05:28:45–05:28:55; 11 05:28:56–05:30:00 |
| getcart | no cap 05:18:10–05:20:00; 10 at 05:20:05; no cap at 05:20:10; 10 05:20:13–05:21:35; 10.2 at 05:21:40; 10 at 05:21:45; no cap 05:21:50–05:22:00; 9975.2 at 05:22:05; 9922.6 at 05:22:10; 9904.7 at 05:22:12; 9896.6 at 05:22:15; 9879 at 05:22:20; no cap at 05:22:25; 11 05:22:28–05:23:18; no cap at 05:23:20; 10 05:23:24–05:23:25; 11 05:23:30–05:23:32; 10.9 at 05:23:35; 11 at 05:23:40; no cap 05:23:45–05:25:15; 10 05:25:20–05:25:30; no cap 05:25:35–05:25:40; 10 at 05:25:45; 11 05:25:50–05:28:30; no cap at 05:28:32; 10 05:28:35–05:28:36; no cap at 05:28:40; 10 at 05:28:45; no cap at 05:28:50; 9998 at 05:28:55; 11 05:29:00–05:30:00 |
| postcart | no cap 05:18:10–05:20:00; 174 at 05:20:05; 270.6 at 05:20:10; 306 at 05:20:13; 246.9 at 05:20:15; 244.231 at 05:20:17; 240.8 at 05:20:20; 211 05:20:25–05:20:30; 201.582 at 05:20:31; 176.367 at 05:20:34; 176.4 at 05:20:35; 164.262 at 05:20:38; 164.3 at 05:20:40; 147.9 at 05:20:45; 187.9 05:20:50–05:20:55; 168.3 at 05:21:00; 156.629 at 05:21:01; 121 at 05:21:05; 113.792 at 05:21:08; 113.8 at 05:21:10; 153.9 at 05:21:15; 212 05:21:20–05:21:25; 149.387 at 05:21:28; 146.7 at 05:21:30; 132.2 at 05:21:35; 129.8 at 05:21:40; 138.3 at 05:21:45; 186.1 05:21:50–05:21:55; 161.9 at 05:22:00; 159.9 at 05:22:05; 107.3 at 05:22:10; 89.385 at 05:22:12; 81.3 at 05:22:15; 63.7 at 05:22:20; 87 at 05:22:25; 71.4315 at 05:22:27; 71.4 at 05:22:30; 46.4 at 05:22:35; 40.1938 at 05:22:36; 33.8 at 05:22:40; 32.7 at 05:22:45; 32.3042 at 05:22:47; 33.2 at 05:22:50; 24 at 05:22:55; 20.7782 at 05:22:58; 20.8 at 05:23:00; 18.6 at 05:23:05; 14.2 at 05:23:10; 13.4727 at 05:23:13; 12.4 at 05:23:15; 14.5 at 05:23:20; 19.9 at 05:23:25; 20.1 at 05:23:30; 21 at 05:23:35; 21.1 at 05:23:40; 38.6 at 05:23:45; 33.8217 at 05:23:47; 33.2 at 05:23:50; 18.4 at 05:23:55; 13.3 at 05:24:00; 10 05:24:05–05:25:15; 17.9 at 05:25:20; 24.8 at 05:25:25; 24 at 05:25:30; 31 at 05:25:35; 57.1 at 05:25:40; 60.8 at 05:25:45; 38.1 at 05:25:50; 24.1 at 05:25:55; 12.8 at 05:26:00; 10 05:26:04–05:26:55; 10.0594 at 05:26:59; 10.1 at 05:27:00; 10 05:27:05–05:28:35; 17.3 at 05:28:40; 16.8 at 05:28:45; 22.3 at 05:28:50; 16.2 at 05:28:55; 13.1 at 05:29:00; 10.4 at 05:29:05; 10 05:29:07–05:30:00 |
| emptycart | no cap 05:18:10–05:30:00 |

### final_4a_constrained_both_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 05:54:15–05:56:05; 10 05:56:10–05:57:35; no cap at 05:57:40; 10 05:57:45–05:58:05; 10.2 at 05:58:10; 10.2034 at 05:58:12; 10 05:58:13–05:58:15; 10.2034 at 05:58:18; no cap at 05:58:20; 11 05:58:25–05:59:05; 10 05:59:10–05:59:31; 11 05:59:35–06:00:50; 10 at 06:00:52; no cap at 06:00:55; 10 06:01:00–06:01:05; no cap 06:01:09–06:01:10; 10 06:01:15–06:01:25; 11 06:01:30–06:04:00; 10 06:04:04–06:04:05; no cap 06:04:10–06:04:15; 10 06:04:20–06:04:25; no cap at 06:04:30; 11 06:04:35–06:06:05 |
| postcheckout | no cap 05:54:15–05:56:05; 10 at 05:56:10; no cap at 05:56:15; 10 at 05:56:20; no cap 05:56:23–05:56:25; 9922.78 at 05:56:29; 9922.8 at 05:56:30; 9909.7 at 05:56:35; 9985.04 at 05:56:37; 9969.8 at 05:56:40; 9957.2 at 05:56:45; 9925.3 at 05:56:50; 9909.4 at 05:56:55; 9896.88 at 05:56:56; 9896.9 at 05:57:00; no cap at 05:57:05; 9980 at 05:57:10; 9949.8 at 05:57:15; no cap 05:57:17–05:57:25; 9919.7 at 05:57:30; 9906.7 at 05:57:31; 9896.6 at 05:57:35; no cap at 05:57:40; 9857.3 at 05:57:45; no cap 05:57:50–05:57:55; 10 05:58:00–05:58:05; 10.2 at 05:58:10; no cap 05:58:15–05:58:20; 11 05:58:25–05:59:06; 10 05:59:10–05:59:30; 11 05:59:35–06:00:50; no cap 06:00:55–06:01:00; 9990.9 at 06:01:05; no cap at 06:01:10; 9988.4 at 06:01:15; no cap at 06:01:16; 9992.6 06:01:20–06:01:25; 11 06:01:30–06:04:00; 10 at 06:04:05; 11 06:04:09–06:04:10; no cap at 06:04:15; 10 06:04:20–06:04:25; no cap at 06:04:30; 11 06:04:35–06:06:05 |
| getcart | no cap 05:54:15–05:56:05; 10 at 05:56:10; no cap at 05:56:15; 10 at 05:56:20; no cap at 05:56:25; 10 05:56:29–05:57:15; no cap 05:57:20–05:57:25; 10 05:57:30–05:57:35; no cap 05:57:38–05:57:40; 10 05:57:45–05:57:46; no cap 05:57:50–05:57:55; 10 05:58:00–05:58:05; 10.2 at 05:58:10; 10 05:58:12–05:58:15; no cap at 05:58:20; 11 05:58:24–05:59:05; 10 05:59:10–05:59:30; 11 05:59:35–06:00:50; 10 06:00:54–06:01:06; no cap at 06:01:10; 10 at 06:01:15; 9992.6 06:01:20–06:01:25; 11 06:01:30–06:04:00; no cap at 06:04:05; 10.5 at 06:04:10; no cap at 06:04:15; 10 06:04:20–06:04:25; no cap at 06:04:30; 11 06:04:35–06:06:05 |
| postcart | no cap 05:54:15–05:56:05; 174 05:56:10–05:56:15; 210.3 at 05:56:20; 201.7 at 05:56:25; 124.453 at 05:56:29; 124.5 at 05:56:30; 155.7 at 05:56:35; 140.783 at 05:56:37; 125.6 at 05:56:40; 152.6 at 05:56:45; 120.773 at 05:56:48; 120.8 at 05:56:50; 129.2 at 05:56:55; 116.672 at 05:56:56; 116.7 at 05:57:00; 115.6 at 05:57:05; 140.9 at 05:57:10; 110.7 at 05:57:15; 152.4 at 05:57:20; 205.4 at 05:57:25; 141.017 at 05:57:28; 125.1 at 05:57:30; 112.087 at 05:57:31; 102 at 05:57:35; 141.1 at 05:57:40; 101.8 at 05:57:45; 141.4 at 05:57:50; 182.9 at 05:57:55; 178.7 at 05:58:00; 153.437 at 05:58:01; 140.2 at 05:58:05; 140.4 at 05:58:10; 155.1 at 05:58:15; 213.8 at 05:58:20; 231.2 at 05:58:25; 283.4 at 05:58:30; 255.8 at 05:58:35; 223.607 at 05:58:36; 184.112 at 05:58:38; 184.1 at 05:58:40; 198.5 at 05:58:45; 200.115 at 05:58:47; 175.097 at 05:58:49; 175.1 at 05:58:50; 170.6 at 05:58:55; 188.2 at 05:59:00; 215.3 at 05:59:05; 218 at 05:59:10; 175.9 at 05:59:15; 167.483 at 05:59:18; 157.9 at 05:59:20; 154.09 at 05:59:21; 150.6 at 05:59:25; 143.82 at 05:59:28; 143.8 at 05:59:30; 129.1 at 05:59:35; 110.3 at 05:59:40; 97.1975 at 05:59:41; 101.2 at 05:59:45; 115.773 at 05:59:49; 115.8 at 05:59:50; 104.2 at 05:59:55; 94.8 at 06:00:00; 87.9 at 06:00:05; 54.4 at 06:00:10; 56.7491 at 06:00:13; 56.7 at 06:00:15; 52.5 at 06:00:20; 60.2 at 06:00:25; 59.3769 at 06:00:26; 61 at 06:00:30; 65.4 at 06:00:35; 50.3 at 06:00:40; 44.9 at 06:00:45; 36.5 at 06:00:50; 43.4623 at 06:00:52; 43.5 at 06:00:55; 43.4623 at 06:00:57; 61 at 06:01:00; 51.8601 at 06:01:03; 51.9 at 06:01:05; 72.9 at 06:01:10; 61.4 at 06:01:15; 78.1 at 06:01:20; 82.2 at 06:01:25; 89.2 at 06:01:30; 95.1 at 06:01:35; 93.8 at 06:01:40; 92.3 at 06:01:45; 84.9 at 06:01:50; 73 at 06:01:55; 73.0621 at 06:01:56; 73.7 at 06:02:00; 63.3953 at 06:02:02; 60.6 at 06:02:05; 50.3 at 06:02:10; 52.1 at 06:02:15; 44.2 at 06:02:20; 46.9122 at 06:02:22; 40.5141 at 06:02:24; 40.5 at 06:02:25; 34.1 at 06:02:30; 29.4 at 06:02:35; 21 at 06:02:40; 17.2 at 06:02:45; 17 at 06:02:50; 17.5 at 06:02:55; 19.7 at 06:03:00; 20 at 06:03:05; 17.5 at 06:03:10; 17.9 at 06:03:15; 18.9864 at 06:03:16; 18.7 at 06:03:20; 20.4 at 06:03:25; 16.8 at 06:03:30; 15.5 at 06:03:35; 12.856 at 06:03:36; 12.4963 at 06:03:38; 12.5 at 06:03:40; 10.2 at 06:03:45; 10.393 at 06:03:47; 10 at 06:03:50; 11.5 at 06:03:55; 10.3 at 06:04:00; 13.4 at 06:04:05; 14 at 06:04:10; 34.7 at 06:04:15; 47.9838 at 06:04:16; 45.2 at 06:04:20; 43.3 at 06:04:25; 60.8 at 06:04:30; 44.7 at 06:04:35; 40.4259 at 06:04:36; 37.8 at 06:04:40; 39.2 at 06:04:45; 32.6923 at 06:04:49; 32.7 at 06:04:50; 31.1377 at 06:04:51; 29.6946 at 06:04:53; 29.7 at 06:04:55; 18.278 at 06:04:57; 17.3 at 06:05:00; 14.6 at 06:05:05; 12.8 at 06:05:10; 14.1 at 06:05:15; 14 at 06:05:20; 15.1 06:05:25–06:05:30; 15.961 at 06:05:31; 16.1 at 06:05:35; 15.9 at 06:05:40; 17.557 at 06:05:42; 17.2 at 06:05:45; 18.2 at 06:05:50; 18.4 at 06:05:55; 17.6 at 06:06:00; 16 at 06:06:05 |
| emptycart | no cap 05:54:15–06:06:05 |

### final_4a_constrained_tf_only_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 06:30:30–06:32:00; 10 at 06:32:05; no cap at 06:32:10; 10 06:32:11–06:41:55 |
| postcheckout | no cap 06:30:30–06:32:00; 10 at 06:32:05; no cap at 06:32:10; 10 06:32:15–06:41:55 |
| getcart | no cap 06:30:28–06:32:02; 10 06:32:05–06:32:08; no cap at 06:32:10; 10 at 06:32:15; no cap at 06:32:20; 10 06:32:23–06:41:55 |
| postcart | no cap 06:30:30–06:32:00; 222 at 06:32:05; 306.9 at 06:32:10; 330 at 06:32:15; 398.6 at 06:32:18; 276.5 at 06:32:20; 445.5 at 06:41:55 |
| emptycart | no cap 06:30:30–06:41:55 |

### final_4a_constrained_tf_only_run2_r2

| API | Live caps |
| --- | --- |
| getproduct | 10 07:22:22–07:22:24; no cap at 07:22:25; 10 07:22:26–07:22:29; no cap at 07:22:30; 10 07:22:31–07:22:34; no cap at 07:22:35; 10 07:22:36–07:22:39; no cap at 07:22:40; 10 07:22:41–07:22:44; no cap at 07:22:45; 10 07:22:46–07:22:49; no cap at 07:22:50; 10 07:22:51–07:22:54; no cap at 07:22:55; 10 07:22:56–07:22:59; no cap at 07:23:00; 10 07:23:01–07:23:04; no cap at 07:23:05; 10 07:23:06–07:23:09; no cap at 07:23:10; 10 07:23:11–07:23:14; no cap at 07:23:15; 10 07:23:16–07:23:19; no cap at 07:23:20; 10 07:23:21–07:23:24; no cap at 07:23:25; 10 07:23:26–07:23:29; no cap at 07:23:30; 10 07:23:31–07:23:34; no cap at 07:23:35; 10 07:23:36–07:23:39; no cap at 07:23:40; 10 07:23:41–07:23:44; no cap at 07:23:45; 10 07:23:46–07:23:50; no cap 07:23:55–07:24:00; 10 07:24:05–07:24:10; 9967.4 at 07:24:14; 9967.4 at 07:24:15; 9883 at 07:24:20; no cap at 07:24:25; 9864.7 at 07:24:30; 10 07:24:35–07:25:05; 9981.8 at 07:25:10; 9965.6 at 07:25:15; 9924.9 07:25:20–07:25:30; 11 07:25:31–07:25:33; no cap at 07:25:35; 10 07:25:40–07:25:49; no cap at 07:25:50; 10 07:25:53–07:25:55; no cap at 07:26:00; 11 07:26:05–07:26:40; 10 07:26:44–07:26:50; no cap 07:26:53–07:27:00; 10 07:27:01–07:27:05; no cap 07:27:06–07:27:10; 11 07:27:15–07:28:40; no cap at 07:28:45; 10 07:28:50–07:28:55; no cap at 07:29:00; 9998.3 at 07:29:05; no cap 07:29:06–07:29:10; 11 07:29:12–07:31:55; 10 07:32:00–07:32:02; no cap at 07:32:05; 10 07:32:07–07:32:11; no cap at 07:32:15; 10.6 at 07:32:20; 11 07:32:25–07:33:45 |
| postcheckout | 10 07:22:22–07:22:24; no cap at 07:22:25; 10 07:22:26–07:22:29; no cap at 07:22:30; 10 07:22:31–07:22:34; no cap at 07:22:35; 10 07:22:36–07:22:39; no cap at 07:22:40; 10 07:22:41–07:22:44; no cap at 07:22:45; 10 07:22:46–07:22:49; no cap at 07:22:50; 10 07:22:51–07:22:54; no cap at 07:22:55; 10 07:22:56–07:22:59; no cap at 07:23:00; 10 07:23:01–07:23:04; no cap at 07:23:05; 10 07:23:06–07:23:09; no cap at 07:23:10; 10 07:23:11–07:23:14; no cap at 07:23:15; 10 07:23:16–07:23:19; no cap at 07:23:20; 10 07:23:21–07:23:24; no cap at 07:23:25; 10 07:23:26–07:23:29; no cap at 07:23:30; 10 07:23:31–07:23:34; no cap at 07:23:35; 10 07:23:36–07:23:39; no cap at 07:23:40; 10 07:23:41–07:23:44; no cap at 07:23:45; 10 07:23:46–07:23:55; no cap at 07:24:00; 10 07:24:01–07:25:05; 9981.8 at 07:25:10; 9965.58 at 07:25:13; 9965.6 at 07:25:15; 9932.4 07:25:20–07:25:30; no cap at 07:25:35; 6736.2 at 07:25:40; 6727.89 at 07:25:41; 6714 07:25:45–07:25:50; 6697.3 at 07:25:53; 6697.3 at 07:25:55; no cap at 07:26:00; 11 07:26:05–07:26:40; 10 07:26:44–07:26:50; no cap 07:26:55–07:27:00; 10 07:27:01–07:27:05; no cap at 07:27:10; 11 07:27:13–07:28:40; no cap at 07:28:45; 11 07:28:50–07:28:55; no cap at 07:29:00; 10 at 07:29:05; no cap at 07:29:10; 11 07:29:15–07:32:05; 10 07:32:07–07:32:10; no cap at 07:32:15; 10.6 at 07:32:20; 11 07:32:25–07:33:47 |
| getcart | 10 07:22:22–07:22:24; no cap at 07:22:25; 10 07:22:26–07:22:29; no cap at 07:22:30; 10 07:22:31–07:22:34; no cap at 07:22:35; 10 07:22:36–07:22:39; no cap at 07:22:40; 10 07:22:41–07:22:44; no cap at 07:22:45; 10 07:22:46–07:22:49; no cap at 07:22:50; 10 07:22:51–07:22:54; no cap at 07:22:55; 10 07:22:56–07:22:59; no cap at 07:23:00; 10 07:23:01–07:23:04; no cap at 07:23:05; 10 07:23:06–07:23:09; no cap at 07:23:10; 10 07:23:11–07:23:14; no cap at 07:23:15; 10 07:23:16–07:23:19; no cap at 07:23:20; 10 07:23:21–07:23:24; no cap at 07:23:25; 10 07:23:26–07:23:29; no cap at 07:23:30; 10 07:23:31–07:23:34; no cap at 07:23:35; 10 07:23:36–07:23:39; no cap at 07:23:40; 10 07:23:41–07:23:44; no cap at 07:23:45; 10 07:23:46–07:23:55; no cap 07:23:56–07:24:00; 10 07:24:01–07:25:00; no cap at 07:25:05; 10 07:25:10–07:25:25; no cap 07:25:30–07:25:35; 10 07:25:40–07:26:05; 11 07:26:10–07:26:40; 10 07:26:44–07:26:50; no cap at 07:26:55; 10 07:27:00–07:27:05; no cap 07:27:07–07:27:10; 11 07:27:13–07:28:40; no cap at 07:28:45; 11 07:28:50–07:28:55; no cap at 07:29:00; 10 at 07:29:05; no cap 07:29:07–07:29:10; 11 07:29:15–07:31:59; 10 at 07:32:00; 11 at 07:32:05; 10 07:32:10–07:32:12; no cap at 07:32:15; 10.6 at 07:32:20; 11 at 07:32:25; 10.9787 at 07:32:26; no cap at 07:32:30; 11 07:32:35–07:33:45 |
| postcart | 543.047 07:22:22–07:22:24; no cap at 07:22:25; 543.047 07:22:26–07:22:29; no cap at 07:22:30; 543.047 07:22:31–07:22:34; no cap at 07:22:35; 543.047 07:22:36–07:22:39; no cap at 07:22:40; 543.047 07:22:41–07:22:44; no cap at 07:22:45; 543.047 07:22:46–07:22:49; no cap at 07:22:50; 543.047 07:22:51–07:22:54; no cap at 07:22:55; 543.047 07:22:56–07:22:59; no cap at 07:23:00; 543.047 07:23:01–07:23:04; no cap at 07:23:05; 543.047 07:23:06–07:23:09; no cap at 07:23:10; 543.047 07:23:11–07:23:14; no cap at 07:23:15; 543.047 07:23:16–07:23:19; no cap at 07:23:20; 543.047 07:23:21–07:23:24; no cap at 07:23:25; 543.047 07:23:26–07:23:29; no cap at 07:23:30; 543.047 07:23:31–07:23:34; no cap at 07:23:35; 543.047 07:23:36–07:23:39; no cap at 07:23:40; 543.047 07:23:41–07:23:44; no cap at 07:23:45; 543.047 07:23:46–07:23:48; 159.5 07:23:50–07:23:55; 258.2 at 07:24:00; 182 at 07:24:05; 169.7 at 07:24:10; 204.036 at 07:24:14; 204 at 07:24:15; 119.6 at 07:24:20; 162.3 at 07:24:25; 142.7 at 07:24:30; 196.6 at 07:24:35; 146.2 at 07:24:40; 143.71 at 07:24:42; 139.4 at 07:24:45; 114.7 at 07:24:50; 155.945 at 07:24:54; 155.9 at 07:24:55; 155.945 at 07:24:58; 155.9 at 07:25:00; 135.1 at 07:25:05; 171.498 at 07:25:06; 153.3 at 07:25:10; 137.1 at 07:25:15; 96.4 07:25:20–07:25:25; 116.5 at 07:25:30; 151.5 at 07:25:35; 97.9 at 07:25:40; 89.585 at 07:25:41; 75.7 at 07:25:45; 104.5 at 07:25:50; 87.8115 at 07:25:53; 87.8 at 07:25:55; 119.1 at 07:26:00; 85.6 at 07:26:05; 44.8 at 07:26:10; 27 at 07:26:15; 20.8032 at 07:26:16; 18 at 07:26:20; 12.9582 at 07:26:22; 10 07:26:25–07:26:40; 13.5 at 07:26:45; 13 at 07:26:50; 17.3 at 07:26:55; 24.2 at 07:27:00; 31.3 at 07:27:05; 43.8 at 07:27:10; 34.9 at 07:27:15; 27.3357 at 07:27:16; 24.7922 at 07:27:18; 24.8 at 07:27:20; 20.8118 at 07:27:22; 17.6106 at 07:27:24; 17.6 at 07:27:25; 13.8797 at 07:27:26; 10 07:27:30–07:28:45; 13.7 at 07:28:50; 16.2 at 07:28:55; 22 at 07:29:00; 20.3 at 07:29:05; 27.1 at 07:29:10; 22.3 at 07:29:15; 21.6399 at 07:29:16; 16.7 at 07:29:20; 11.1 at 07:29:25; 10 07:29:30–07:32:00; 13.1 at 07:32:05; 16.311 at 07:32:07; 16.1 at 07:32:10; 21.8 at 07:32:15; 21.9 at 07:32:20; 22.3 at 07:32:25; 30.6 at 07:32:30; 22 at 07:32:35; 17.2728 at 07:32:36; 15.349 at 07:32:38; 15.3 at 07:32:40; 10 07:32:45–07:33:45 |
| emptycart | no cap 07:22:25–07:33:45 |

### final_4a_constrained_rg_only_burst_run1

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 07:39:35–07:41:50 |
| postcheckout | no cap 07:39:35–07:41:50 |
| getcart | no cap 07:39:35–07:41:50 |
| postcart | no cap 07:39:35–07:41:50 |
| emptycart | no cap 07:39:35–07:41:50 |

### final_4a_constrained_rg_only_burst_run2_r2

postcart and emptycart: every live read in the window is no cap.

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:33:55–08:36:05 |
| postcheckout | no cap 08:33:55–08:36:05 |
| getcart | no cap 08:33:55–08:36:05 |
| postcart | no cap 08:33:55–08:36:05 |
| emptycart | no cap 08:33:55–08:36:05 |

### final_4a_constrained_both_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:52:05–08:53:50; 10 08:53:55–08:53:56; no cap 08:53:58–08:54:05; 10 08:54:10–08:54:57; no cap at 08:55:00; 10 08:55:05–08:55:45; no cap at 08:55:50; 10 08:55:54–08:56:15; 11 08:56:20–08:56:56; 10 08:57:00–08:57:05; 10.1834 at 08:57:07; 10.2 at 08:57:10; 10 08:57:15–08:57:25; 11 08:57:30–08:58:50; 10 08:58:54–08:59:05; 10.1 08:59:10–08:59:15; 11 08:59:20–09:02:00; no cap 09:02:05–09:02:10; 10 at 09:02:15; no cap 09:02:19–09:02:20; 10 09:02:21–09:02:25; 11 09:02:28–09:03:55 |
| postcheckout | no cap 08:52:05–08:53:50; 10 at 08:53:55; no cap 08:54:00–08:54:05; 10 08:54:10–08:54:55; no cap at 08:55:00; 10 08:55:05–08:55:45; no cap at 08:55:50; 10 08:55:55–08:56:15; 11 08:56:20–08:56:55; 10 08:56:57–08:57:05; 10.1834 at 08:57:07; 10.2 at 08:57:10; 9989.6 at 08:57:15; 10 08:57:20–08:57:25; 11 08:57:27–08:58:50; 10 08:58:54–08:58:57; no cap at 08:59:00; 10 at 08:59:05; 10.1 08:59:10–08:59:15; 11 08:59:17–09:02:00; no cap 09:02:05–09:02:10; 10 09:02:13–09:02:15; no cap at 09:02:20; 10 09:02:21–09:02:25; 11 09:02:30–09:03:55 |
| getcart | no cap 08:52:05–08:53:50; 10 at 08:53:55; no cap 08:53:57–08:54:05; 10 08:54:10–08:54:48; no cap at 08:54:50; 10 at 08:54:55; no cap at 08:55:00; 10 08:55:05–08:55:09; no cap at 08:55:10; 10 08:55:15–08:55:35; 10.1266 at 08:55:37; 10 08:55:40–08:55:45; no cap at 08:55:50; 10 at 08:55:53; no cap at 08:55:55; 10 at 08:56:00; no cap at 08:56:01; 9947.1 at 08:56:05; no cap 08:56:09–08:56:15; 11 08:56:20–08:56:55; 10 08:57:00–08:57:05; 10.1834 at 08:57:07; 10.2 at 08:57:10; 9989.6 at 08:57:15; 10 08:57:20–08:57:25; 11 08:57:30–08:58:50; 10 08:58:54–08:58:55; no cap at 08:59:00; 10 at 08:59:05; 10.1 at 08:59:10; 10 at 08:59:15; 11 08:59:20–09:02:00; no cap 09:02:05–09:02:10; 10 09:02:13–09:02:15; no cap 09:02:18–09:02:20; 10 09:02:21–09:02:25; 11 09:02:27–09:03:55 |
| postcart | no cap 08:52:05–08:53:50; 102 at 08:53:55; 194.2 at 08:54:00; 264 at 08:54:05; 300.3 at 08:54:07; 290.5 at 08:54:10; 337.5 at 08:54:15; 228.6 at 08:54:20; 173.6 at 08:54:25; 311.1 at 08:54:30; 161 at 08:54:35; 131.9 at 08:54:40; 120.1 at 08:54:45; 119.8 at 08:54:50; 113.3 at 08:54:55; 156.2 at 08:55:00; 184.7 at 08:55:05; 247 at 08:55:10; 230.4 at 08:55:15; 178.9 08:55:20–08:55:25; 224.6 at 08:55:30; 153.7 at 08:55:35; 141.1 at 08:55:40; 136.6 at 08:55:45; 163.5 at 08:55:50; 221.5 at 08:55:55; 182.2 at 08:56:00; 156.3 at 08:56:05; 217.8 08:56:10–08:56:15; 204.485 at 08:56:17; 213.6 at 08:56:20; 219.815 at 08:56:21; 191.5 at 08:56:25; 175.724 at 08:56:27; 155.7 at 08:56:30; 183.3 at 08:56:35; 165.4 at 08:56:40; 103.5 at 08:56:43; 103.5 at 08:56:45; 84.6 at 08:56:50; 99.4 at 08:56:55; 107.9 at 08:57:00; 92.1 at 08:57:05; 86.0279 08:57:07–08:57:09; 86 at 08:57:10; 104 at 08:57:15; 199.8 at 08:57:20; 191.579 at 08:57:24; 191.6 at 08:57:25; 187.5 at 08:57:30; 148.091 at 08:57:33; 148.1 at 08:57:35; 105 at 08:57:40; 87.4 at 08:57:45; 56.6 at 08:57:50; 47.8 at 08:57:55; 41.6171 at 08:57:57; 39.2 at 08:58:00; 37.5639 at 08:58:01; 36.2418 at 08:58:03; 36.2 at 08:58:05; 26.9 at 08:58:10; 21.6 at 08:58:15; 17.6 at 08:58:20; 13.1 at 08:58:25; 10 08:58:29–08:58:40; 10.2 at 08:58:45; 10 at 08:58:50; 12.8 at 08:58:55; 18 at 08:59:00; 34.1 at 08:59:05; 33.9 at 08:59:10; 45.3996 at 08:59:13; 45.4 at 08:59:15; 39.8156 at 08:59:16; 40.5 at 08:59:20; 29.4 at 08:59:25; 21.3 at 08:59:30; 17.4862 at 08:59:31; 15.0235 at 08:59:33; 15 at 08:59:35; 10.4 at 08:59:40; 10 08:59:45–09:00:45; 10.3 at 09:00:50; 10 09:00:55–09:01:00; 10.1 at 09:01:05; 10 09:01:10–09:01:20; 10.1 at 09:01:25; 10 09:01:26–09:01:30; 10.1 at 09:01:35; 10 09:01:40–09:01:55; 10.4 at 09:02:00; 11.8 at 09:02:05; 16 at 09:02:10; 25.7 at 09:02:15; 47.2 at 09:02:20; 45.984 at 09:02:21; 46 at 09:02:25; 39.1 at 09:02:30; 26.3 at 09:02:35; 18.5 at 09:02:40; 12.1 at 09:02:45; 10 09:02:47–09:02:50; 10.2 09:02:55–09:03:00; 10 09:03:05–09:03:55 |
| emptycart | no cap 08:52:05–09:03:55 |

### final_4a_constrained_both_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 09:28:25–09:30:10; 10 09:30:15–09:40:15 |
| postcheckout | no cap 09:28:25–09:30:10; 10 09:30:15–09:40:15 |
| getcart | no cap 09:28:25–09:30:10; 10 09:30:15–09:30:20; no cap at 09:30:22; 10 09:30:25–09:40:15 |
| postcart | no cap 09:28:25–09:30:10; 138 at 09:30:15; 137.415 at 09:30:16; 137.4 at 09:30:20; 242.002 at 09:30:23; 239.4 09:30:25–09:30:30; 329.7 at 09:30:35; 244.888 at 09:30:39; 244.9 at 09:30:40; 180.2 at 09:40:15 |
| emptycart | no cap 09:28:25–09:40:15 |

## One paragraph per launch

**final_4a_constrained_rg_only_normal_run1.** INVALID on the catalog replica gate. frontend → productcatalogservice shed 4 times on the normal rpr path, re-enabled 4, and held 1 attempts at EXIT; recommendationservice → productcatalogservice shed 3 times on the normal rpr path, re-enabled 3, and held 1 attempts at EXIT; frontend → recommendationservice shed 3 times on the normal rpr path, re-enabled 3, and held 3 attempts at EXIT. Outbound retry delta was 47,446 to productcatalogservice and 3,062 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 67,934 / 3,307. productcatalogservice detector overloaded fraction was 166/712 (23.3%). No service reached a 0.5 share.

**final_4a_constrained_rg_only_normal_run2.** INVALID on the catalog replica gate. frontend → productcatalogservice shed 4 times on the normal rpr path, re-enabled 4, and held 1 attempts at EXIT; recommendationservice → productcatalogservice shed 3 times on the normal rpr path, re-enabled 3, and held 1 attempts at EXIT; frontend → recommendationservice shed 3 times on the normal rpr path, re-enabled 3, and held 3 attempts at EXIT. Outbound retry delta was 39,728 to productcatalogservice and 2,397 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 61,694 / 2,985. productcatalogservice detector overloaded fraction was 157/711 (22.1%). No service reached a 0.5 share.

**final_4a_constrained_both_normal_run1.** INVALID on the catalog replica gate. frontend → productcatalogservice did not shed; recommendationservice → productcatalogservice did not shed; frontend → recommendationservice did not shed. Outbound retry delta was 2,031 to productcatalogservice and 51 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 208 / 1,803. productcatalogservice detector overloaded fraction was 160/713 (22.4%). No service reached a 0.5 share.

**final_4a_constrained_both_normal_run2.** INVALID on the catalog replica gate. frontend → productcatalogservice did not shed; recommendationservice → productcatalogservice did not shed; frontend → recommendationservice did not shed. Outbound retry delta was 1,545 to productcatalogservice and 75 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 156 / 1,233. productcatalogservice detector overloaded fraction was 151/713 (21.2%). No service reached a 0.5 share.

**final_4a_constrained_tf_only_run1.** INVALID on the catalog replica gate. RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta was 110,770 to productcatalogservice and 3,814 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 80,828 / 6,680. productcatalogservice detector overloaded fraction was 173/689 (25.1%). No service reached a 0.5 share.

**final_4a_constrained_tf_only_run2_r2.** Passed the catalog replica gate. RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta was 1,404 to productcatalogservice and 24 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 148 / 1,339. productcatalogservice detector overloaded fraction was 149/688 (21.7%). No service reached a 0.5 share.

**final_4a_constrained_rg_only_burst_run1.** INVALID on the catalog replica gate. frontend → productcatalogservice shed 4 times, 3 of them burst, re-enabled 4, and held 1 attempts at EXIT; recommendationservice → productcatalogservice shed 3 times, 3 of them burst, re-enabled 3, and held 2 attempts at EXIT; frontend → recommendationservice shed 3 times, 3 of them burst, re-enabled 3, and held 3 attempts at EXIT. Outbound retry delta was 20,118 to productcatalogservice and 615 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 56,834 / 742. productcatalogservice detector overloaded fraction was 162/710 (22.8%). No service reached a 0.5 share.

**final_4a_constrained_rg_only_burst_run2_r2.** Passed the catalog replica gate. frontend → productcatalogservice shed 4 times, 4 of them burst, re-enabled 4, and held 1 attempts at EXIT; recommendationservice → productcatalogservice shed 4 times, 4 of them burst, re-enabled 4, and held 1 attempts at EXIT; frontend → recommendationservice shed 4 times, 4 of them burst, re-enabled 4, and held 3 attempts at EXIT. Outbound retry delta was 14,256 to productcatalogservice and 779 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 53,406 / 2,393. productcatalogservice detector overloaded fraction was 167/711 (23.5%). No service reached a 0.5 share.

**final_4a_constrained_both_burst_run1.** INVALID on the catalog replica gate. frontend → productcatalogservice did not shed; recommendationservice → productcatalogservice did not shed; frontend → recommendationservice did not shed. Outbound retry delta was 1,468 to productcatalogservice and 101 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 284 / 609. productcatalogservice detector overloaded fraction was 132/713 (18.5%). No service reached a 0.5 share.

**final_4a_constrained_both_burst_run2.** INVALID on the catalog replica gate. frontend → productcatalogservice shed 1 times, 1 of them burst, re-enabled 1, and held 3 attempts at EXIT; recommendationservice → productcatalogservice shed 1 times, 1 of them burst, re-enabled 1, and held 3 attempts at EXIT; frontend → recommendationservice shed 1 times, 1 of them burst, re-enabled 1, and held 3 attempts at EXIT. Outbound retry delta was 6,688 to productcatalogservice and 204 to recommendationservice. grpc_4 / grpc_14 on productcatalogservice was 5,478 / 351. productcatalogservice detector overloaded fraction was 144/714 (20.2%). No service reached a 0.5 share.

## Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [(a) / (b) / (c) reading](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (edge mode and burst mode)
- [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md)
- [2026-10-11 catalog CPU guide](2026-10-11-s4a-catalog-cpu-abc.md) and [2026-10-10 set B catalog guide](2026-10-10-set-b-s4a-catalog-analysis.md), earlier S4A holds at 100 m or another mix, not columns here
- [S3 mode matrix](2026-10-13-s3-mode-matrix-abc.md), the previous matrix in this campaign, a different scenario

## Throttle flag addendum (2026-10-15 audit)

- `final_4a_constrained_both_burst_run1_r2` is FLAGGED (226 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 570 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_both_burst_run2` is FLAGGED (228 fetch warnings; longest no-fresh threshold read 575 s, longest no-fresh admitted read 575 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_both_burst_run2_r2` is FLAGGED (224 fetch warnings; longest no-fresh threshold read 562 s, longest no-fresh admitted read 565 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_both_normal_run2_r2` is FLAGGED (192 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 483 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_tf_only_run1` is FLAGGED (228 fetch warnings; longest no-fresh threshold read 4 s, longest no-fresh admitted read 575 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_tf_only_run1_r2` is FLAGGED (200 fetch warnings; longest no-fresh threshold read 504 s, longest no-fresh admitted read 504 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `final_4a_constrained_tf_only_run2` is FLAGGED (226 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 567 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
