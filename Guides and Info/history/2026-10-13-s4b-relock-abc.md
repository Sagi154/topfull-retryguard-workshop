# S4B relock — (a) / (b) / (c)

## Setup

Scenario 4B, 600 s. Mix 175 / 30 / 70 / 90 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1 with `emailservice` constrained to 50 m. Path: Frontend → Checkout → Email. Frontend HPA min = max = 4. productcatalogservice HPA min = max = 1. Frontend sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off between holds is 120 s. RetryGuard uses the locked parameters. Burst holds set `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal-mode RetryGuard holds omit those three keys. TopFull-only has no `retryguard.log`. Each cell is two repeats. The bold bar splits the pairs.

Hold 28's first launch exited 1 before Locust and was not pulled. The column is the relaunch of `final_4b_rg_only_burst_run2`, which passed. `experiments/results/campaign_48/S4B_topology_position_B/` constrained paymentservice. It is not a column here.

Scored folders:

- `experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1`
- `experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run2`
- `experiments/results/final results/S4B_topology_position_normal/both/final_4b_both_normal_run1`
- `experiments/results/final results/S4B_topology_position_normal/both/final_4b_both_normal_run2`
- `experiments/results/final results/S4B_topology_position_normal/tf_only/final_4b_tf_only_run1`
- `experiments/results/final results/S4B_topology_position_normal/tf_only/final_4b_tf_only_run2`
- `experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1`
- `experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run2`
- `experiments/results/final results/S4B_topology_position_burst/both/final_4b_both_burst_run1`
- `experiments/results/final results/S4B_topology_position_burst/both/final_4b_both_burst_run2`

## Index

| Hold | log_folder | Mode | TopFull | In this guide |
| --- | --- | --- | --- | --- |
| 21 | final_4b_rg_only_normal_run1 | normal | off | PASS, scored |
| 22 | final_4b_rg_only_normal_run2 | normal | off | PASS, scored |
| 23 | final_4b_both_normal_run1 | normal | on | PASS, scored |
| 24 | final_4b_both_normal_run2 | normal | on | PASS, scored |
| 25 | final_4b_tf_only_run1 | tf | on | PASS, scored |
| 26 | final_4b_tf_only_run2 | tf | on | PASS, scored |
| 27 | final_4b_rg_only_burst_run1 | burst_rpr 2.0 | off | PASS, scored |
| 28 | final_4b_rg_only_burst_run2 | burst_rpr 2.0 | off | first launch exited 1 before Locust, not scored; relaunch PASS, scored |
| 29 | final_4b_both_burst_run1 | burst_rpr 2.0 | on | PASS, scored |
| 30 | final_4b_both_burst_run2 | burst_rpr 2.0 | on | PASS, scored |

Table columns follow the ten scored rows, in that order.

## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars: final_4b_rg_only_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4b_rg_only_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4b_both_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4b_both_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

The START line on those four holds sets `burst_window_seconds=5` and `burst_min_first_attempts=20`. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s. The eight RetryGuard START lines set `interval_samples=20s` and `climb_interval_seconds=10s`. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The scorer's (a) tables are frontend → checkoutservice and frontend → adservice. The other controlled edges have no tick above the shed bar and no retry delta. A bold file-streak cell is at least 30 seconds. The parenthetical is the controller `high` when a `retryguard.log` exists. File-streak unit is seconds. The longest file streak is 4 seconds, on frontend → checkoutservice in `final_4b_both_burst_run2` (3 ticks, controller high 3). `final_4b_both_normal_run1` is 0 / 2 (1) on that edge.

### File streak seconds / ticks above the shed bar (controller high)

| Edge | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 2 (1) | 0 / 0 (0) | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 4 / 3 (3) |
| frontend → adservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

### Mean / median / max / volume rpr

| Edge | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.006 / 0.000 / 0.67 / 0.002 | 0.000 / 0.000 / 0.07 / 0.000 | **┃** | 0.000 / 0.000 / 0.02 / 0.000 | 0.000 / 0.000 / 0.06 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.014 / 0.000 / 2.53 / 0.005 |
| frontend → adservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

On frontend → checkoutservice, `final_4b_both_burst_run2` is mean 0.014 / median 0.000 / max 2.53 / volume 0.005. `final_4b_both_normal_run1` is 0.006 / 0.000 / 0.67 / 0.002. frontend → adservice is 0.000 / 0.000 / 0.00 / 0.000 on every column.

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

### Climb streaks, 1-attempt / 2-attempt

| Edge | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → adservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

Every climb cell is an em dash. The 1-attempt cap and the 2-attempt cap never applied on these two edges.

## 4a Burst

Burst mode was off on the six normal and TopFull-only holds. Those columns are an em dash in the burst window table.

On the four burst holds the (a2) burst window is below. Cell shape is peak `burst_rpr5` / median `burst_rpr5` / samples at the bar in force / burst sheds (`burst_rpr5` samples).

| Edge | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (302) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | 0.00 / 0.00 / 0 / 0 (302) | 0.00 / 0.00 / 0 / 0 (302) |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (305) |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (302) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | 0.00 / 0.00 / 0 / 0 (302) | 0.00 / 0.00 / 0 / 0 (302) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (307) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (303) | **┃** | 0.00 / 0.00 / 0 / 0 (302) | 1.04 / 0.00 / 0 / 0 (302) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (307) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (304) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (305) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (305) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (304) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | 0.00 / 0.00 / 0 / 0 (12) |

Burst sheds are the `ON→OFF burst` column of the scorer toggle table. The four burst holds have no transition lines, so each has 0 burst sheds and 0 normal sheds. Every burst-window cell has 0 samples at the bar and 0 burst sheds. The highest peak `burst_rpr5` is 1.04, on frontend → checkoutservice in `final_4b_both_burst_run2` (302 samples). checkoutservice → emailservice has samples only on that hold, 0.00 / 0.00 / 0 / 0 (12). The other three burst columns are an em dash on that edge.

## Rejection beside (a)

Longest streak / count of inbound rejection above 0.20. Bold when a controlled service's streak is at least 30. frontend and redis-cart stay plain. The longest controlled streak is 3, on checkoutservice and on emailservice in `final_4b_both_burst_run2` (3 / 3). `final_4b_both_normal_run1` is 1 / 1 on checkoutservice and 1 / 2 on emailservice.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 3 / 3 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 1 / 2 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 3 / 3 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak / count under the re-enable bar. The eight RetryGuard columns use 0.25 from the START line. The two TopFull-only columns, `final_4b_tf_only_run1` and `final_4b_tf_only_run2`, have no `retryguard.log`, so the scorer uses its default under-bar 0.10.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 309 / 309 | 308 / 308 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| checkoutservice | 307 / 307 | 307 / 307 | **┃** | 294 / 305 | 306 / 306 | **┃** | 306 / 306 | 305 / 305 | **┃** | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 291 / 304 |
| recommendationservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| paymentservice | 308 / 308 | 308 / 308 | **┃** | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 |
| emailservice | 1 / 1 | 15 / 15 | **┃** | 11 / 15 | 1 / 1 | **┃** | 0 / 0 | 2 / 2 | **┃** | 1 / 1 | 2 / 2 | **┃** | 0 / 0 | 13 / 13 |
| productcatalogservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| cartservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| currencyservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| shippingservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| adservice | 308 / 308 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 307 / 307 | 306 / 306 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

emailservice's under-bar cells are 1 / 1, 15 / 15, 11 / 15, 1 / 1, 0 / 0, 2 / 2, 1 / 1, 2 / 2, 0 / 0, and 13 / 13. checkoutservice is 294 / 305 on `final_4b_both_normal_run1` and 291 / 304 on `final_4b_both_burst_run2`. redis-cart is 0 / 0 on every column.

HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees. Same bars as the table above: 0.25 on the RetryGuard columns, 0.10 on the two TopFull-only columns.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| productcatalogservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| currencyservice | 308 / 308 | 309 / 309 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| adservice | 308 / 308 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 307 / 307 | 306 / 306 | **┃** | 306 / 306 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |

Every HTTP-only cell above 0.20 is 0 / 0. The HTTP-only under-bar cells match the main under-bar table on recommendationservice, productcatalogservice, currencyservice, and adservice.

gRPC counted in the rejection rate on the four read callees and in the retry policy. Cell is grpc_4 / grpc_14.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 1 / 0 | 0 / 0 | **┃** | 3 / 0 | 0 / 0 | **┃** | 2 / 0 | 4 / 0 | **┃** | 0 / 0 | 0 / 0 |

adservice grpc_4 is 1 on `final_4b_both_normal_run1`, 3 on `final_4b_tf_only_run1`, 2 on `final_4b_rg_only_burst_run1`, and 4 on `final_4b_rg_only_burst_run2`. grpc_14 is 0 on every cell. The other three read callees are 0 / 0 on every column.

## (b) Detector overloaded fraction

Share of detector samples at or above 1. Bold when the share is at least 0.5. emailservice is above 0 on every column, from 82/743 (11.0%) on `final_4b_rg_only_normal_run1` to 95/745 (12.8%) on `final_4b_both_burst_run2` and 92/716 (12.8%) on `final_4b_tf_only_run2`. checkoutservice is 40/745 (5.4%) on `final_4b_both_burst_run2`. cartservice is 13/716 (1.8%) on `final_4b_tf_only_run2` and 11/743 (1.5%) on `final_4b_both_burst_run1`.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| checkoutservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 40/745 (5.4%) |
| recommendationservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| paymentservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| emailservice | 82/743 (11.0%) | 88/743 (11.8%) | **┃** | 92/745 (12.3%) | 89/744 (12.0%) | **┃** | 86/717 (12.0%) | 92/716 (12.8%) | **┃** | 89/751 (11.9%) | 89/744 (12.0%) | **┃** | 89/743 (12.0%) | 95/745 (12.8%) |
| productcatalogservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| cartservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 13/716 (1.8%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 11/743 (1.5%) | 0/745 (0.0%) |
| currencyservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| shippingservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| adservice | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |
| redis-cart | 0/743 (0.0%) | 0/743 (0.0%) | **┃** | 0/745 (0.0%) | 0/744 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/751 (0.0%) | 0/744 (0.0%) | **┃** | 0/743 (0.0%) | 0/745 (0.0%) |

## (c) Retry volume

Outbound retry delta by target. The scorer omits a target whose delta is 0 on every column.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 0 | 0 | **┃** | 43 | 6 | **┃** | 1 | 6 | **┃** | 0 | 0 | **┃** | 0 | 93 |
| adservice | 0 | 0 | **┃** | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

checkoutservice is 93 on `final_4b_both_burst_run2`, 43 on `final_4b_both_normal_run1`, 6 on `final_4b_both_normal_run2` and on `final_4b_tf_only_run2`, and 1 on `final_4b_tf_only_run1`. The four RetryGuard-only columns are 0. adservice is 1 on `final_4b_both_normal_run1` and 0 on the other nine columns.

Inbound resets.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 35 | 27 | **┃** | 19 | 19 | **┃** | 22 | 23 | **┃** | 25 | 32 | **┃** | 11 | 20 |
| checkoutservice | 8 | 7 | **┃** | 34 | 14 | **┃** | 1 | 11 | **┃** | 0 | 2 | **┃** | 0 | 69 |
| recommendationservice | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 0 | **┃** | 4 | 4 | **┃** | 0 | 3 |
| paymentservice | 0 | 0 | **┃** | 0 | 6 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 |
| emailservice | 0 | 0 | **┃** | 51 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 131 |
| productcatalogservice | 3 | 3 | **┃** | 1 | 0 | **┃** | 5 | 5 | **┃** | 2 | 3 | **┃** | 2 | 2 |
| cartservice | 0 | 0 | **┃** | 1 | 0 | **┃** | 3 | 2 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| currencyservice | 0 | 1 | **┃** | 0 | 0 | **┃** | 1 | 0 | **┃** | 1 | 2 | **┃** | 3 | 4 |
| shippingservice | 0 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | **┃** | 8 | 1 | **┃** | 1 | 2 | **┃** | 10 | 4 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

emailservice inbound resets are 131 on `final_4b_both_burst_run2` and 51 on `final_4b_both_normal_run1`, and 0 on the other eight columns. checkoutservice is 69 on `final_4b_both_burst_run2`.

## RetryGuard toggles

`ON→OFF` is a shed from the current attempt cap to 0. `0→1` is the re-enable climb off 0.

### Part 1, per hold

`final_4b_tf_only_run1` and `final_4b_tf_only_run2` have no `retryguard.log`. The other eight scored holds have a log and no transition lines, so none of them gets a count table or a timestamp table.

### Part 2, per callee

No callee sheds or re-enables on any scored hold, so there is no per-callee table.

## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.

| API | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 167.8 | 168.0 | **┃** | 167.9 | 167.8 | **┃** | 167.9 | 167.9 | **┃** | 167.8 | 167.8 | **┃** | 168.0 | 167.9 |
| postcheckout | 28.8 | 28.8 | **┃** | 28.7 | 28.8 | **┃** | 28.8 | 28.8 | **┃** | 28.8 | 28.8 | **┃** | 28.8 | 28.6 |
| getcart | 67.1 | 67.2 | **┃** | 67.2 | 67.2 | **┃** | 67.2 | 67.2 | **┃** | 67.2 | 67.1 | **┃** | 67.2 | 67.1 |
| postcart | 86.3 | 86.2 | **┃** | 86.3 | 86.2 | **┃** | 86.4 | 86.4 | **┃** | 86.4 | 86.3 | **┃** | 86.2 | 86.3 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.

| API | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.000 | 0.000 | **┃** | 0.007 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.010 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

postcheckout fail rate is 0.007 on `final_4b_both_normal_run1` and 0.010 on `final_4b_both_burst_run2`. The other fail-rate cells are 0.000.

## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.

| API | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 124 | 109 | **┃** | 116 | 109 | **┃** | 116 | 110 | **┃** | 129 | 115 | **┃** | 110 | 111 |
| postcheckout | 219 | 189 | **┃** | 214 | 201 | **┃** | 203 | 212 | **┃** | 230 | 202 | **┃** | 202 | 189 |
| getcart | 108 | 90 | **┃** | 99 | 75 | **┃** | 91 | 83 | **┃** | 112 | 98 | **┃** | 80 | 94 |
| postcart | 66 | 64 | **┃** | 65 | 64 | **┃** | 65 | 65 | **┃** | 66 | 64 | **┃** | 65 | 65 |
| emptycart | 18 | 16 | **┃** | 15 | 13 | **┃** | 13 | 20 | **┃** | 22 | 14 | **┃** | 17 | 14 |

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 326.2 | 326.2 | **┃** | 326.2 | 325.3 | **┃** | 339.6 | 338.5 | **┃** | 325.8 | 326.7 | **┃** | 326.2 | 325.1 |
| checkoutservice | 26.4 | 26.4 | **┃** | 26.4 | 26.4 | **┃** | 27.5 | 27.5 | **┃** | 26.4 | 26.5 | **┃** | 26.4 | 26.4 |
| recommendationservice | 242.4 | 242.4 | **┃** | 242.3 | 241.7 | **┃** | 252.3 | 251.5 | **┃** | 242.0 | 242.7 | **┃** | 242.4 | 241.5 |
| paymentservice | 26.4 | 26.4 | **┃** | 26.4 | 26.4 | **┃** | 27.5 | 27.5 | **┃** | 26.4 | 26.5 | **┃** | 26.4 | 26.4 |
| emailservice | 0.0 | 0.3 | **┃** | 0.5 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.5 |
| productcatalogservice | 1687.7 | 1687.8 | **┃** | 1687.7 | 1683.2 | **┃** | 1756.7 | 1751.3 | **┃** | 1685.4 | 1690.1 | **┃** | 1687.8 | 1681.6 |
| cartservice | 352.7 | 352.7 | **┃** | 352.7 | 351.7 | **┃** | 367.1 | 365.9 | **┃** | 352.2 | 353.2 | **┃** | 352.7 | 351.6 |
| currencyservice | 484.7 | 484.7 | **┃** | 484.7 | 483.4 | **┃** | 504.6 | 503.0 | **┃** | 484.1 | 485.4 | **┃** | 484.8 | 483.0 |
| shippingservice | 114.7 | 114.7 | **┃** | 114.6 | 114.3 | **┃** | 119.3 | 119.0 | **┃** | 114.5 | 114.8 | **┃** | 114.7 | 114.4 |
| adservice | 154.1 | 154.1 | **┃** | 154.2 | 153.7 | **┃** | 160.4 | 160.0 | **┃** | 153.9 | 154.4 | **┃** | 154.2 | 153.6 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

emailservice arrival is 0.0 on seven columns, 0.3 on `final_4b_rg_only_normal_run2`, and 0.5 on `final_4b_both_normal_run1` and on `final_4b_both_burst_run2`. redis-cart is 0.0 on every column.

## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 73 | 62 | **┃** | 67 | 57 | **┃** | 62 | 60 | **┃** | 69 | 66 | **┃** | 58 | 62 |
| checkoutservice | 89 | 73 | **┃** | 87 | 81 | **┃** | 79 | 88 | **┃** | 96 | 82 | **┃** | 84 | 56 |
| recommendationservice | 14 | 12 | **┃** | 13 | 10 | **┃** | 11 | 10 | **┃** | 16 | 13 | **┃** | 10 | 13 |
| paymentservice | 2 | 2 | **┃** | 3 | 3 | **┃** | 2 | 3 | **┃** | 4 | 2 | **┃** | 2 | 2 |
| emailservice | 1 | 50 | **┃** | 124 | 0 | **┃** | — | 37 | **┃** | 0 | 5 | **┃** | — | 105 |
| productcatalogservice | 2 | 1 | **┃** | 2 | 1 | **┃** | 1 | 1 | **┃** | 1 | 2 | **┃** | 1 | 1 |
| cartservice | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 3 |
| currencyservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.002 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.005 |
| recommendationservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | — | 0.000 | **┃** | 0.000 | 0.000 | **┃** | — | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

checkoutservice is 0.002 on `final_4b_both_normal_run1` and 0.005 on `final_4b_both_burst_run2`. emailservice and redis-cart are an em dash where the scorer has no sojourn count: `final_4b_tf_only_run1` and `final_4b_both_burst_run1` for emailservice, and every column for redis-cart.

## CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max sum usage across replicas. emailservice's per-pod quota is 50 on every column. Its replica mode is 0 or 1.

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1138 / 1535 | 1150 / 4 / 1153 / 1570 | **┃** | 1150 / 4 / 1166 / 1584 | 1150 / 4 / 1228 / 1686 | **┃** | 1150 / 4 / 1228 / 1628 | 1150 / 4 / 1312 / 1735 | **┃** | 1150 / 4 / 1221 / 1679 | 1150 / 4 / 1177 / 1594 | **┃** | 1150 / 4 / 1246 / 1670 | 1150 / 4 / 1153 / 1565 |
| checkoutservice | 800 / 1 / 375 / 515 | 800 / 1 / 358 / 494 | **┃** | 800 / 1 / 381 / 523 | 800 / 1 / 369 / 515 | **┃** | 800 / 1 / 378 / 503 | 800 / 1 / 379 / 518 | **┃** | 800 / 1 / 370 / 512 | 800 / 1 / 365 / 501 | **┃** | 800 / 1 / 372 / 505 | 800 / 1 / 449 / 609 |
| recommendationservice | 1150 / 1 / 443 / 608 | 1150 / 1 / 432 / 590 | **┃** | 1150 / 1 / 435 / 595 | 1150 / 1 / 448 / 652 | **┃** | 1150 / 1 / 456 / 643 | 1150 / 1 / 482 / 674 | **┃** | 1150 / 1 / 473 / 674 | 1150 / 1 / 447 / 614 | **┃** | 1150 / 1 / 463 / 638 | 1150 / 1 / 440 / 607 |
| paymentservice | 155 / 1 / 27 / 39 | 155 / 1 / 26 / 39 | **┃** | 155 / 1 / 26 / 39 | 155 / 1 / 27 / 42 | **┃** | 155 / 1 / 27 / 40 | 155 / 1 / 28 / 41 | **┃** | 155 / 1 / 27 / 40 | 155 / 1 / 26 / 40 | **┃** | 155 / 1 / 27 / 39 | 155 / 1 / 28 / 40 |
| emailservice | 50 / 0 / 0 / 0 | 50 / 1 / 14 / 50 | **┃** | 50 / 1 / 9 / 51 | 50 / 0 / 8 / 51 | **┃** | 50 / 0 / 10 / 50 | 50 / 0 / 12 / 52 | **┃** | 50 / 0 / 17 / 51 | 50 / 0 / 3 / 51 | **┃** | 50 / 0 / 10 / 51 | 50 / 1 / 15 / 50 |
| productcatalogservice | 800 / 1 / 369 / 500 | 800 / 1 / 388 / 524 | **┃** | 800 / 1 / 382 / 514 | 800 / 1 / 427 / 582 | **┃** | 800 / 1 / 415 / 543 | 800 / 1 / 446 / 584 | **┃** | 800 / 1 / 418 / 569 | 800 / 1 / 388 / 529 | **┃** | 800 / 1 / 433 / 581 | 800 / 1 / 394 / 529 |
| cartservice | 800 / 1 / 372 / 571 | 800 / 1 / 349 / 494 | **┃** | 800 / 1 / 383 / 702 | 800 / 1 / 386 / 565 | **┃** | 800 / 1 / 385 / 540 | 800 / 1 / 440 / 754 | **┃** | 800 / 1 / 366 / 521 | 800 / 1 / 364 / 509 | **┃** | 800 / 1 / 422 / 763 | 800 / 1 / 359 / 514 |
| currencyservice | 770 / 1 / 273 / 377 | 770 / 1 / 263 / 364 | **┃** | 770 / 1 / 272 / 377 | 770 / 1 / 279 / 402 | **┃** | 770 / 1 / 280 / 407 | 770 / 1 / 297 / 405 | **┃** | 770 / 1 / 278 / 390 | 770 / 1 / 271 / 378 | **┃** | 770 / 1 / 285 / 388 | 770 / 1 / 270 / 372 |
| shippingservice | 770 / 1 / 73 / 97 | 770 / 1 / 73 / 98 | **┃** | 770 / 1 / 73 / 98 | 770 / 1 / 75 / 101 | **┃** | 770 / 1 / 75 / 101 | 770 / 1 / 78 / 103 | **┃** | 770 / 1 / 73 / 101 | 770 / 1 / 73 / 98 | **┃** | 770 / 1 / 75 / 100 | 770 / 1 / 77 / 103 |
| adservice | 1150 / 1 / 117 / 152 | 1150 / 1 / 113 / 147 | **┃** | 1150 / 1 / 116 / 160 | 1150 / 1 / 116 / 158 | **┃** | 1150 / 1 / 117 / 157 | 1150 / 1 / 126 / 167 | **┃** | 1150 / 1 / 127 / 177 | 1150 / 1 / 114 / 151 | **┃** | 1150 / 1 / 119 / 155 | 1150 / 1 / 114 / 149 |
| redis-cart | 540 / 1 / 40 / 76 | 540 / 1 / 39 / 71 | **┃** | 540 / 1 / 39 / 74 | 540 / 1 / 42 / 76 | **┃** | 540 / 1 / 42 / 78 | 540 / 1 / 44 / 79 | **┃** | 540 / 1 / 41 / 76 | 540 / 1 / 40 / 75 | **┃** | 540 / 1 / 42 / 77 | 540 / 1 / 40 / 74 |

CPU as a fraction of per-pod quota × replicas (mean / max).

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.25 / 0.33 | 0.25 / 0.34 | **┃** | 0.25 / 0.34 | 0.27 / 0.37 | **┃** | 0.27 / 0.35 | 0.29 / 0.38 | **┃** | 0.27 / 0.36 | 0.26 / 0.35 | **┃** | 0.27 / 0.36 | 0.25 / 0.34 |
| checkoutservice | 0.47 / 0.64 | 0.45 / 0.62 | **┃** | 0.48 / 0.65 | 0.46 / 0.64 | **┃** | 0.47 / 0.63 | 0.47 / 0.65 | **┃** | 0.46 / 0.64 | 0.46 / 0.63 | **┃** | 0.46 / 0.63 | 0.56 / 0.76 |
| recommendationservice | 0.38 / 0.53 | 0.38 / 0.51 | **┃** | 0.38 / 0.52 | 0.39 / 0.57 | **┃** | 0.40 / 0.56 | 0.42 / 0.59 | **┃** | 0.41 / 0.59 | 0.39 / 0.53 | **┃** | 0.40 / 0.55 | 0.38 / 0.53 |
| paymentservice | 0.17 / 0.25 | 0.16 / 0.25 | **┃** | 0.17 / 0.25 | 0.17 / 0.27 | **┃** | 0.18 / 0.26 | 0.18 / 0.26 | **┃** | 0.17 / 0.26 | 0.17 / 0.26 | **┃** | 0.17 / 0.25 | 0.18 / 0.26 |
| emailservice | — / — | 0.27 / 0.90 | **┃** | 0.28 / 0.62 | — / — | **┃** | 0.00 / 0.00 | 1.03 / 1.04 | **┃** | 0.90 / 0.90 | — / — | **┃** | — / — | 0.28 / 1.00 |
| productcatalogservice | 0.46 / 0.62 | 0.48 / 0.66 | **┃** | 0.48 / 0.64 | 0.53 / 0.73 | **┃** | 0.52 / 0.68 | 0.56 / 0.73 | **┃** | 0.52 / 0.71 | 0.49 / 0.66 | **┃** | 0.54 / 0.73 | 0.49 / 0.66 |
| cartservice | 0.47 / 0.71 | 0.44 / 0.62 | **┃** | 0.48 / 0.88 | 0.48 / 0.71 | **┃** | 0.48 / 0.68 | 0.55 / 0.94 | **┃** | 0.46 / 0.65 | 0.46 / 0.64 | **┃** | 0.53 / 0.95 | 0.45 / 0.64 |
| currencyservice | 0.35 / 0.49 | 0.34 / 0.47 | **┃** | 0.35 / 0.49 | 0.36 / 0.52 | **┃** | 0.36 / 0.53 | 0.39 / 0.53 | **┃** | 0.36 / 0.51 | 0.35 / 0.49 | **┃** | 0.37 / 0.50 | 0.35 / 0.48 |
| shippingservice | 0.09 / 0.13 | 0.09 / 0.13 | **┃** | 0.09 / 0.13 | 0.10 / 0.13 | **┃** | 0.10 / 0.13 | 0.10 / 0.13 | **┃** | 0.09 / 0.13 | 0.09 / 0.13 | **┃** | 0.10 / 0.13 | 0.10 / 0.13 |
| adservice | 0.10 / 0.13 | 0.10 / 0.13 | **┃** | 0.10 / 0.14 | 0.10 / 0.14 | **┃** | 0.10 / 0.14 | 0.11 / 0.15 | **┃** | 0.11 / 0.15 | 0.10 / 0.13 | **┃** | 0.10 / 0.13 | 0.10 / 0.13 |
| redis-cart | 0.07 / 0.14 | 0.07 / 0.13 | **┃** | 0.07 / 0.14 | 0.08 / 0.14 | **┃** | 0.08 / 0.14 | 0.08 / 0.15 | **┃** | 0.08 / 0.14 | 0.07 / 0.14 | **┃** | 0.08 / 0.14 | 0.07 / 0.14 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | final_4b_rg_only_normal_run1 | final_4b_rg_only_normal_run2 | **┃** | final_4b_both_normal_run1 | final_4b_both_normal_run2 | **┃** | final_4b_tf_only_run1 | final_4b_tf_only_run2 | **┃** | final_4b_rg_only_burst_run1 | final_4b_rg_only_burst_run2 | **┃** | final_4b_both_burst_run1 | final_4b_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.359 | 0.361 | **┃** | 0.371 | 0.397 | **┃** | 0.385 | 0.394 | **┃** | 0.402 | 0.371 | **┃** | 0.389 | 0.358 |
| checkoutservice | 0.782 | 0.743 | **┃** | 0.746 | 0.795 | **┃** | 0.776 | 0.718 | **┃** | 0.774 | 0.706 | **┃** | 0.734 | 0.841 |
| recommendationservice | 0.573 | 0.543 | **┃** | 0.548 | 0.609 | **┃** | 0.592 | 0.629 | **┃** | 0.649 | 0.570 | **┃** | 0.591 | 0.576 |
| paymentservice | 0.561 | 0.484 | **┃** | 0.445 | 0.510 | **┃** | 0.561 | 0.561 | **┃** | 0.516 | 0.445 | **┃** | 0.548 | 0.729 |
| emailservice | 1.100 | 1.120 | **┃** | 1.180 | 1.140 | **┃** | 1.140 | 1.220 | **┃** | 1.100 | 1.120 | **┃** | 1.160 | 1.100 |
| productcatalogservice | 0.681 | 0.704 | **┃** | 0.690 | 0.755 | **┃** | 0.714 | 0.776 | **┃** | 0.760 | 0.688 | **┃** | 0.775 | 0.710 |
| cartservice | 0.750 | 0.691 | **┃** | 0.904 | 0.804 | **┃** | 0.755 | 0.974 | **┃** | 0.749 | 0.711 | **┃** | 0.970 | 0.726 |
| currencyservice | 0.558 | 0.557 | **┃** | 0.568 | 0.568 | **┃** | 0.588 | 0.590 | **┃** | 0.566 | 0.553 | **┃** | 0.592 | 0.549 |
| shippingservice | 0.191 | 0.169 | **┃** | 0.178 | 0.179 | **┃** | 0.183 | 0.188 | **┃** | 0.175 | 0.178 | **┃** | 0.173 | 0.179 |
| adservice | 0.163 | 0.168 | **┃** | 0.176 | 0.170 | **┃** | 0.206 | 0.170 | **┃** | 0.210 | 0.190 | **┃** | 0.167 | 0.162 |
| redis-cart | 0.567 | 0.472 | **┃** | 0.493 | 0.567 | **┃** | 0.543 | 0.470 | **┃** | 0.422 | 0.502 | **┃** | 0.520 | 0.533 |

emailservice's detector max utilization is above 1 on every column, from 1.100 to 1.220. The 1.220 cell is `final_4b_tf_only_run2`.

## Throttle data quality

All ten scored holds are throttle clean: 0 fetch warnings, longest no-fresh threshold 5 s, and longest no-fresh admitted 5 s. No hold is **FLAGGED**. Goodput, P95, rejection, and retry numbers do not come from that file, but a proxy that ran out of file descriptors refuses new connections on every variant, so whether they are clean for this hold is decided by [2026-10-15-proxy-fd-evidence-flagged-holds.md](2026-10-15-proxy-fd-evidence-flagged-holds.md), not by this flag.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | --- | --- | --- | --- | --- |
| final_4b_rg_only_normal_run1 | ok | 0 | — | 5 | 5 |
| final_4b_rg_only_normal_run2 | ok | 0 | — | 5 | 5 |
| final_4b_both_normal_run1 | ok | 0 | — | 5 | 5 |
| final_4b_both_normal_run2 | ok | 0 | — | 5 | 5 |
| final_4b_tf_only_run1 | ok | 0 | — | 5 | 5 |
| final_4b_tf_only_run2 | ok | 0 | — | 5 | 5 |
| final_4b_rg_only_burst_run1 | ok | 0 | — | 5 | 5 |
| final_4b_rg_only_burst_run2 | ok | 0 | — | 5 | 5 |
| final_4b_both_burst_run1 | ok | 0 | — | 5 | 5 |
| final_4b_both_burst_run2 | ok | 0 | — | 5 | 5 |

## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. `postcart` and `emptycart` are no cap on every live read of `final_4b_rg_only_normal_run1`, `final_4b_rg_only_normal_run2`, `final_4b_both_normal_run1`, `final_4b_both_normal_run2`, `final_4b_tf_only_run1`, `final_4b_rg_only_burst_run1`, `final_4b_rg_only_burst_run2`, and `final_4b_both_burst_run2`. `final_4b_tf_only_run2` and `final_4b_both_burst_run1` have live caps on `postcart` and `emptycart` as well as on the other three APIs.

### final_4b_rg_only_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 05:18:30–05:30:50 |
| postcheckout | no cap 05:18:30–05:30:50 |
| getcart | no cap 05:18:30–05:30:50 |
| postcart | no cap 05:18:30–05:30:50 |
| emptycart | no cap 05:18:30–05:30:50 |

### final_4b_rg_only_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 05:39:35–05:51:50 |
| postcheckout | no cap 05:39:35–05:51:50 |
| getcart | no cap 05:39:35–05:51:50 |
| postcart | no cap 05:39:35–05:51:50 |
| emptycart | no cap 05:39:35–05:51:50 |

### final_4b_both_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 05:58:40–06:11:00 |
| postcheckout | no cap 05:58:40–06:01:10; 10 at 06:01:15; 10.7721 at 06:01:19; 10.8 at 06:01:20; 22 06:01:23–06:01:25; 23 at 06:01:30; no cap at 06:01:35; 29 at 06:01:40; no cap 06:01:42–06:04:30; 30 at 06:04:35; no cap at 06:04:38; 30 at 06:04:40; no cap 06:04:45–06:10:00; 30 06:10:05–06:10:15; no cap at 06:10:20; 30 at 06:10:25; no cap at 06:10:28; 30 at 06:10:30; no cap 06:10:35–06:11:00 |
| getcart | no cap 05:58:40–06:11:00 |
| postcart | no cap 05:58:40–06:11:00 |
| emptycart | no cap 05:58:40–06:11:00 |

### final_4b_both_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 06:17:55–06:30:15 |
| postcheckout | no cap 06:17:55–06:22:50; 30 06:22:55–06:22:58; no cap at 06:23:00; 30 06:23:05–06:23:10; no cap 06:23:15–06:28:20; 30 06:28:25–06:28:30; no cap 06:28:35–06:28:41; 30 06:28:45–06:28:53; no cap 06:28:55–06:30:15 |
| getcart | no cap 06:17:55–06:30:15 |
| postcart | no cap 06:17:55–06:30:15 |
| emptycart | no cap 06:17:55–06:30:15 |

### final_4b_tf_only_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 06:37:05–06:49:00 |
| postcheckout | no cap 06:37:05–06:38:55; 10 06:39:00–06:39:03; no cap at 06:39:05; 13 at 06:39:10; no cap at 06:39:13; 15 at 06:39:15; no cap 06:39:20–06:42:15; 30 06:42:17–06:42:25; no cap 06:42:30–06:47:35; 30 06:47:37–06:47:45; no cap at 06:47:50; 30 at 06:47:55; no cap at 06:47:58; 30 06:48:00–06:48:05; no cap 06:48:10–06:49:00 |
| getcart | no cap 06:37:05–06:49:00 |
| postcart | no cap 06:37:05–06:49:00 |
| emptycart | no cap 06:37:05–06:49:00 |

### final_4b_tf_only_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 06:55:40–06:58:15; 175 06:58:16–06:58:20; no cap at 06:58:25; 175 at 06:58:30; no cap at 06:58:35; 175 at 06:58:40; no cap at 06:58:45; 175 at 06:58:50; no cap 06:58:55–06:59:05; 175 at 06:59:10; no cap 06:59:15–07:07:35 |
| postcheckout | no cap 06:55:40–06:57:35; 10 at 06:57:40; no cap at 06:57:45; 16 at 06:57:50; 19.8 at 06:57:53; no cap 06:57:55–06:58:15; 30 06:58:16–06:58:20; no cap at 06:58:25; 30 at 06:58:30; no cap at 06:58:35; 30 at 06:58:40; no cap at 06:58:45; 30 06:58:48–06:58:50; no cap 06:58:55–06:59:05; 30 at 06:59:10; no cap 06:59:15–07:00:45; 30 07:00:49–07:00:55; no cap at 07:00:57; 30 at 07:00:58; no cap at 07:01:00; 30 at 07:01:05; no cap 07:01:06–07:06:10; 30 07:06:15–07:06:18; no cap at 07:06:20; 30 at 07:06:25; no cap at 07:06:26; 30 07:06:30–07:06:35; no cap at 07:06:40; 30 07:06:45–07:06:50; no cap 07:06:55–07:07:35 |
| getcart | no cap 06:55:40–06:58:15; 70 06:58:16–06:58:20; no cap at 06:58:25; 70 at 06:58:30; no cap at 06:58:35; 70 at 06:58:40; no cap at 06:58:45; 70 at 06:58:50; no cap 06:58:55–06:59:05; 70 at 06:59:10; no cap 06:59:15–07:07:35 |
| postcart | no cap 06:55:40–06:58:15; 90 06:58:16–06:58:20; no cap at 06:58:25; 90 at 06:58:30; no cap at 06:58:35; 90 at 06:58:40; no cap at 06:58:45; 90 06:58:50–06:58:52; no cap 06:58:55–06:59:05; 90 at 06:59:10; no cap 06:59:15–07:07:35 |
| emptycart | no cap 06:55:40–06:58:15; 10 06:58:16–06:58:21; no cap 06:58:23–06:58:25; 10 at 06:58:30; no cap at 06:58:35; 10 at 06:58:40; no cap 06:58:43–06:58:45; 10 06:58:50–06:58:55; no cap 06:59:00–06:59:05; 10 at 06:59:10; no cap 06:59:15–07:07:35 |

### final_4b_rg_only_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 07:20:50–07:33:15 |
| postcheckout | no cap 07:20:50–07:33:15 |
| getcart | no cap 07:20:50–07:33:15 |
| postcart | no cap 07:20:50–07:33:15 |
| emptycart | no cap 07:20:50–07:33:15 |

### final_4b_rg_only_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:08:10–08:20:30 |
| postcheckout | no cap 08:08:10–08:20:30 |
| getcart | no cap 08:08:10–08:20:30 |
| postcart | no cap 08:08:10–08:20:30 |
| emptycart | no cap 08:08:10–08:20:30 |

### final_4b_both_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:28:40–08:31:45; 175 08:31:46–08:31:55; no cap at 08:32:00; 175 08:32:05–08:32:10; no cap 08:32:14–08:40:55 |
| postcheckout | no cap 08:28:40–08:31:45; 30 08:31:46–08:31:50; no cap 08:31:55–08:32:05; 30 at 08:32:10; no cap 08:32:15–08:33:30; 30 08:33:35–08:33:36; no cap 08:33:40–08:33:45; 30 at 08:33:50; no cap 08:33:55–08:39:05; 30 at 08:39:10; no cap at 08:39:15; 30 at 08:39:20; no cap 08:39:23–08:39:25; 30 at 08:39:26; no cap 08:39:30–08:39:35; 30 at 08:39:40; no cap 08:39:45–08:40:55 |
| getcart | no cap 08:28:40–08:31:45; 70 08:31:50–08:31:55; no cap at 08:32:00; 70 08:32:05–08:32:15; no cap 08:32:20–08:40:55 |
| postcart | no cap 08:28:40–08:31:45; 90 08:31:46–08:31:50; no cap 08:31:55–08:32:00; 90 08:32:05–08:32:10; no cap 08:32:14–08:40:55 |
| emptycart | no cap 08:28:40–08:31:45; 10 08:31:46–08:31:50; no cap 08:31:55–08:32:00; 10 08:32:05–08:32:10; no cap 08:32:15–08:40:55 |

### final_4b_both_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 08:47:55–09:00:15 |
| postcheckout | no cap 08:47:55–08:50:25; 14.3 at 08:50:28; no cap at 08:50:30; 13 at 08:50:35; 19.6 at 08:50:40; no cap at 08:50:42; 23 at 08:50:45; 25 at 08:50:50; no cap at 08:50:51; 31.9 at 08:50:54; 31.9 at 08:50:55; no cap 08:51:00–08:53:25; 30 at 08:53:30; no cap at 08:53:35; 30 08:53:40–08:53:45; no cap 08:53:47–08:57:10; 30 at 08:57:15; no cap 08:57:20–08:58:25; 30 at 08:58:30; no cap 08:58:35–08:58:55; 30 08:58:59–08:59:05; no cap 08:59:07–08:59:15; 30 08:59:17–08:59:25; no cap 08:59:30–08:59:35; 30 at 08:59:40; no cap 08:59:41–08:59:55; 30 at 09:00:00; no cap 09:00:05–09:00:15 |
| getcart | no cap 08:47:55–09:00:15 |
| postcart | no cap 08:47:55–09:00:15 |
| emptycart | no cap 08:47:55–09:00:15 |

## One paragraph per scored column

**final_4b_rg_only_normal_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 82/743 (11.0%). No share reaches 0.5.

**final_4b_rg_only_normal_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 88/743 (11.8%). No share reaches 0.5.

**final_4b_both_normal_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 43, adservice 1. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 1 / 0. emailservice detector share 92/745 (12.3%). emailservice inbound resets 51. No share reaches 0.5.

**final_4b_both_normal_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 6, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 89/744 (12.0%). No share reaches 0.5.

**final_4b_tf_only_run1.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: checkoutservice 1, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 3 / 0. emailservice detector share 86/717 (12.0%). No share reaches 0.5.

**final_4b_tf_only_run2.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: checkoutservice 6, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 92/716 (12.8%). cartservice detector share 13/716 (1.8%). No share reaches 0.5.

**final_4b_rg_only_burst_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 2 / 0. emailservice detector share 89/751 (11.9%). No share reaches 0.5.

**final_4b_rg_only_burst_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 4 / 0. emailservice detector share 89/744 (12.0%). No share reaches 0.5.

**final_4b_both_burst_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 89/743 (12.0%). cartservice detector share 11/743 (1.5%). No share reaches 0.5.

**final_4b_both_burst_run2.** No transition lines, so nothing shed and nothing climbed. frontend → checkoutservice file streak is 4 seconds, 3 ticks, controller high 3, max rpr 2.53. Outbound retry delta: checkoutservice 93, adservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. emailservice detector share 95/745 (12.8%). checkoutservice detector share 40/745 (5.4%). emailservice inbound resets 131. checkoutservice inbound resets 69. No share reaches 0.5.

## Related

- [S4 relock mode matrix plan](../../docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md)
- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [(a) / (b) / (c) reading](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md) (edge mode and burst mode)
- [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md)
- [campaign_48 S4B](../../experiments/results/campaign_48/S4B_topology_position_B/) (paymentservice constraint; not a column here)
