# S4A unconstrained relock — (a) / (b) / (c)

## Setup

Scenario 4A unconstrained, 600 s. Mix 50 / 20 / 50 / 600 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Plain Paper-C1. productcatalogservice stays at 800 m. No constrained row. Frontend HPA min = max = 4. productcatalogservice HPA min = max = 1. Frontend sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off between holds is 120 s. RetryGuard uses the locked parameters. Burst holds set `burst_rpr` 2.0, `burst_window_seconds` 5, and `burst_min_first_attempts` 20. Normal-mode RetryGuard holds omit those three keys. TopFull-only has no `retryguard.log`. Each cell is two repeats. The bold bar splits the pairs.

Replays followed the gate in force at launch. Re-gated 2026-10-14: `live5s_caps` 0 on a TopFull-on hold is recorded, not a gate. The tabulated column was chosen before the re-gate and was left in place. Holds 11, 12, 17, and 18 passed on the first launch, so their columns are the canonical folders. `Guides and Info/2026-10-13-s4a-constrained-relock-abc.md` is catalog 100 m. `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md` is catalog 50 m. Neither is a column here.

Scored folders:

- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1`
- `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1`
- `experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1`
- `experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1`
- `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run2`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1`
- `experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2`

## Index

| Hold | log_folder | Mode | TopFull | In this guide |
| --- | --- | --- | --- | --- |
| 11 | final_4a_unconstrained_rg_only_normal_run1 | normal | off | PASS, scored |
| 12 | final_4a_unconstrained_rg_only_normal_run2 | normal | off | PASS, scored; throttle FLAG |
| 13 | final_4a_unconstrained_both_normal_run1 | normal | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 13 replay | final_4a_unconstrained_both_normal_run1_r2 | normal | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, not scored |
| 14 | final_4a_unconstrained_both_normal_run2 | normal | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 14 replay | final_4a_unconstrained_both_normal_run2_r2 | normal | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, not scored |
| 15 | final_4a_unconstrained_tf_only_run1 | tf | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 15 replay | final_4a_unconstrained_tf_only_run1_r2 | tf | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, not scored |
| 16 | final_4a_unconstrained_tf_only_run2 | tf | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 16 replay | final_4a_unconstrained_tf_only_run2_r2 | tf | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, not scored |
| 17 | final_4a_unconstrained_rg_only_burst_run1 | burst_rpr 2.0 | off | PASS, scored |
| 18 | final_4a_unconstrained_rg_only_burst_run2 | burst_rpr 2.0 | off | PASS, scored |
| 19 | final_4a_unconstrained_both_burst_run1 | burst_rpr 2.0 | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored; replay also PASS |
| 19 replay | final_4a_unconstrained_both_burst_run1_r2 | burst_rpr 2.0 | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, not scored |
| 20 | final_4a_unconstrained_both_burst_run2 | burst_rpr 2.0 | on | first launch exited 1 before collect (disk full), not gated, not scored; relaunch PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, scored |
| 20 replay | final_4a_unconstrained_both_burst_run2_r2 | burst_rpr 2.0 | on | PASS, live5s_caps 0, re-gated 2026-10-14: recorded, not a gate, throttle FLAG, not scored |

Table columns follow the ten scored rows, in that order. A launch that is not scored stays on disk and is not a column.

## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars: final_4a_unconstrained_rg_only_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_unconstrained_rg_only_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_unconstrained_both_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_4a_unconstrained_both_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

The START line on those four holds sets `burst_window_seconds=5` and `burst_min_first_attempts=20`. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The only edge with a retry delta is frontend → checkoutservice. The other controlled edges have no tick above the shed bar and no retry delta. A bold file-streak cell is at least 30 seconds. The parenthetical is the controller `high` when a `retryguard.log` exists. File-streak unit is seconds. No file streak here reaches 30 seconds.

### File streak seconds / ticks above the shed bar (controller high)

| Edge | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

### Mean / median / max / volume rpr

| Edge | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.06 / 0.001 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.05 / 0.000 | 0.000 / 0.000 / 0.05 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.05 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

### Climb streaks, 1-attempt / 2-attempt

| Edge | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

## 4a Burst

Burst mode was off on the six normal and TopFull-only holds. Those columns are an em dash in the burst window table.

On the four burst holds the (a2) burst window is below. Cell shape is peak `burst_rpr5` / median `burst_rpr5` / samples at the bar in force / burst sheds (`burst_rpr5` samples).

| Edge | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (307) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (301) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (301) |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (303) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (305) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (301) | 0.02 / 0.00 / 0 / 0 (302) | **┃** | 0.00 / 0.00 / 0 / 0 (301) | 0.00 / 0.00 / 0 / 0 (301) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (301) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (301) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (303) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (307) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (303) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (305) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (301) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (301) |

Burst sheds are the `ON→OFF burst` column of the scorer toggle table. The four burst holds have no transition lines, so each has 0 burst sheds and 0 normal sheds. Every burst-window cell has 0 samples at the bar and 0 burst sheds. The highest peak `burst_rpr5` is 0.02, on frontend → checkoutservice in `final_4a_unconstrained_rg_only_burst_run2` (302 samples).

## Rejection beside (a)

Longest streak / count of inbound rejection above 0.20. Bold when a controlled service's streak is at least 30. frontend and redis-cart stay plain. No controlled streak here reaches 30.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak / count under the re-enable bar. The eight RetryGuard columns use 0.25 from the START line. The two TopFull-only columns, final_4a_unconstrained_tf_only_run1 and final_4a_unconstrained_tf_only_run2, have no retryguard.log, so the scorer uses its default 0.10. That is why adservice on tf_only_run1 is 261 / 306 under the bar and 0 / 0 above 0.20.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 307 / 307 | 308 / 308 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 308 / 308 | **┃** | 307 / 307 | 307 / 307 |
| checkoutservice | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 306 / 306 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| recommendationservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| paymentservice | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 306 / 306 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 306 / 306 |
| emailservice | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 306 / 306 | 305 / 305 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| productcatalogservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| cartservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| currencyservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| shippingservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| adservice | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 261 / 306 | 306 / 306 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees. Same bars as the table above: 0.25 on the RetryGuard columns, 0.10 on the two TopFull-only columns.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| productcatalogservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| currencyservice | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 | **┃** | 308 / 308 | 307 / 307 | **┃** | 307 / 307 | 307 / 307 |
| adservice | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 306 / 306 | **┃** | 307 / 307 | 306 / 306 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 307 / 307 |

gRPC counted in the rejection rate on the four read callees and in the retry policy. Cell is grpc_4 / grpc_14.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 19 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

Share of detector samples at or above 1. Bold when the share is at least 0.5. No service in these ten columns reaches 0.5. The only non-zero cell is emailservice on `final_4a_unconstrained_tf_only_run1`, 1/692 (0.1%).

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| checkoutservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| recommendationservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| paymentservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| emailservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 1/692 (0.1%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| productcatalogservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| cartservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| currencyservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| shippingservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| adservice | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |
| redis-cart | 0/725 (0.0%) | 0/743 (0.0%) | **┃** | 0/718 (0.0%) | 0/718 (0.0%) | **┃** | 0/692 (0.0%) | 0/691 (0.0%) | **┃** | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/717 (0.0%) | 0/718 (0.0%) |

## (c) Retry volume

Outbound retry delta by target. The scorer omits a target whose delta is 0 on every column.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 0 | 0 | **┃** | 6 | 0 | **┃** | 2 | 2 | **┃** | 0 | 5 | **┃** | 0 | 0 |

Inbound resets.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 39 | 15 | **┃** | 7 | 58 | **┃** | 14 | 31 | **┃** | 63 | 16 | **┃** | 23 | 9 |
| checkoutservice | 0 | 9 | **┃** | 1 | 8 | **┃** | 2 | 4 | **┃** | 0 | 2 | **┃** | 0 | 1 |
| recommendationservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 1 | 1 | **┃** | 3 | 2 | **┃** | 0 | 5 | **┃** | 0 | 1 |
| productcatalogservice | 27 | 0 | **┃** | 0 | 9 | **┃** | 0 | 7 | **┃** | 21 | 11 | **┃** | 12 | 2 |
| cartservice | 2 | 3 | **┃** | 6 | 20 | **┃** | 13 | 9 | **┃** | 15 | 0 | **┃** | 2 | 5 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 1 | 0 | **┃** | 0 | 0 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | **┃** | 10 | 0 | **┃** | 1 | 0 | **┃** | 0 | 4 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

## RetryGuard toggles

`ON→OFF` is a shed from the current attempt cap to 0. `0→1` is the re-enable climb off 0.

### Part 1, per hold

`final_4a_unconstrained_tf_only_run1` and `final_4a_unconstrained_tf_only_run2` have no `retryguard.log`. The other eight scored holds have a log and no transition lines, so none of them gets a count table or a timestamp table.

### Part 2, per callee

No callee sheds or re-enables on any scored hold, so there is no per-callee table.

## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.

| API | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 47.9 | 46.8 | **┃** | 48.0 | 48.0 | **┃** | 47.9 | 47.8 | **┃** | 48.0 | 47.9 | **┃** | 47.9 | 48.0 |
| postcheckout | 19.2 | 19.2 | **┃** | 19.2 | 19.2 | **┃** | 19.2 | 19.2 | **┃** | 19.2 | 19.0 | **┃** | 19.2 | 19.2 |
| getcart | 47.9 | 47.4 | **┃** | 47.9 | 47.9 | **┃** | 47.9 | 48.0 | **┃** | 48.0 | 47.7 | **┃** | 47.9 | 48.0 |
| postcart | 575.4 | 576.2 | **┃** | 575.6 | 575.4 | **┃** | 575.3 | 576.2 | **┃** | 574.7 | 576.0 | **┃** | 575.0 | 575.8 |
| emptycart | 4.8 | 4.8 | **┃** | 4.7 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.

| API | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.

| API | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 140 | 295 | **┃** | 284 | 143 | **┃** | 212 | 366 | **┃** | 298 | 323 | **┃** | 279 | 338 |
| postcheckout | 234 | 324 | **┃** | 282 | 248 | **┃** | 341 | 340 | **┃** | 313 | 275 | **┃** | 320 | 360 |
| getcart | 176 | 254 | **┃** | 268 | 228 | **┃** | 245 | 342 | **┃** | 227 | 285 | **┃** | 299 | 299 |
| postcart | 284 | 248 | **┃** | 183 | 197 | **┃** | 225 | 186 | **┃** | 239 | 229 | **┃** | 214 | 200 |
| emptycart | 13 | 13 | **┃** | 57 | 14 | **┃** | 19 | 12 | **┃** | 20 | 24 | **┃** | 28 | 12 |

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 635.1 | 637.1 | **┃** | 637.6 | 638.5 | **┃** | 665.5 | 665.4 | **┃** | 640.4 | 640.4 | **┃** | 639.4 | 639.5 |
| checkoutservice | 17.5 | 17.6 | **┃** | 17.6 | 17.6 | **┃** | 18.4 | 18.4 | **┃** | 17.7 | 17.7 | **┃** | 17.6 | 17.6 |
| recommendationservice | 105.2 | 105.5 | **┃** | 105.5 | 105.6 | **┃** | 110.1 | 110.1 | **┃** | 105.9 | 105.9 | **┃** | 105.8 | 105.8 |
| paymentservice | 17.5 | 17.6 | **┃** | 17.6 | 17.6 | **┃** | 18.4 | 18.4 | **┃** | 17.7 | 17.7 | **┃** | 17.6 | 17.6 |
| emailservice | 17.5 | 17.6 | **┃** | 17.6 | 17.6 | **┃** | 18.4 | 18.4 | **┃** | 17.7 | 17.7 | **┃** | 17.6 | 17.6 |
| productcatalogservice | 1200.2 | 1203.8 | **┃** | 1204.4 | 1206.2 | **┃** | 1257.1 | 1257.0 | **┃** | 1209.8 | 1209.8 | **┃** | 1207.9 | 1208.0 |
| cartservice | 652.6 | 654.6 | **┃** | 655.2 | 656.1 | **┃** | 683.9 | 683.7 | **┃** | 658.1 | 658.1 | **┃** | 657.0 | 657.1 |
| currencyservice | 210.3 | 210.9 | **┃** | 210.9 | 211.2 | **┃** | 220.2 | 220.2 | **┃** | 211.9 | 211.9 | **┃** | 211.6 | 211.6 |
| shippingservice | 78.9 | 79.1 | **┃** | 79.2 | 79.3 | **┃** | 82.6 | 82.6 | **┃** | 79.5 | 79.5 | **┃** | 79.4 | 79.4 |
| adservice | 43.8 | 43.9 | **┃** | 43.9 | 44.0 | **┃** | 45.8 | 45.8 | **┃** | 44.1 | 44.1 | **┃** | 44.0 | 44.0 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 49 | 66 | **┃** | 72 | 57 | **┃** | 57 | 76 | **┃** | 65 | 69 | **┃** | 62 | 77 |
| checkoutservice | 99 | 97 | **┃** | 120 | 111 | **┃** | 104 | 106 | **┃** | 83 | 99 | **┃** | 100 | 109 |
| recommendationservice | 19 | 33 | **┃** | 52 | 33 | **┃** | 53 | 87 | **┃** | 67 | 79 | **┃** | 65 | 84 |
| paymentservice | 3 | 4 | **┃** | 3 | 4 | **┃** | 2 | 2 | **┃** | 3 | 4 | **┃** | 3 | 2 |
| emailservice | 30 | 8 | **┃** | 29 | 15 | **┃** | 20 | 19 | **┃** | 8 | 12 | **┃** | 17 | 23 |
| productcatalogservice | 3 | 6 | **┃** | 4 | 3 | **┃** | 3 | 4 | **┃** | 4 | 4 | **┃** | 3 | 5 |
| cartservice | 5 | 5 | **┃** | 13 | 9 | **┃** | 7 | 10 | **┃** | 8 | 8 | **┃** | 7 | 10 |
| currencyservice | 4 | 4 | **┃** | 5 | 4 | **┃** | 4 | 5 | **┃** | 4 | 6 | **┃** | 5 | 4 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 2 | **┃** | 2 | 1 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.001 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.001 | **┃** | 0.000 | 0.000 |
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

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max sum usage across replicas.

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 919 / 1236 | 1150 / 4 / 883 / 1234 | **┃** | 1150 / 4 / 883 / 1193 | 1150 / 4 / 916 / 1235 | **┃** | 1150 / 4 / 967 / 1284 | 1150 / 4 / 880 / 1141 | **┃** | 1150 / 4 / 877 / 1159 | 1150 / 4 / 906 / 1208 | **┃** | 1150 / 4 / 930 / 1277 | 1150 / 4 / 866 / 1151 |
| checkoutservice | 800 / 1 / 250 / 340 | 800 / 1 / 273 / 389 | **┃** | 800 / 1 / 252 / 352 | 800 / 1 / 262 / 354 | **┃** | 800 / 1 / 264 / 360 | 800 / 1 / 284 / 374 | **┃** | 800 / 1 / 262 / 349 | 800 / 1 / 277 / 373 | **┃** | 800 / 1 / 277 / 394 | 800 / 1 / 274 / 366 |
| recommendationservice | 1150 / 1 / 205 / 273 | 1150 / 1 / 208 / 294 | **┃** | 1150 / 1 / 203 / 275 | 1150 / 1 / 206 / 275 | **┃** | 1150 / 1 / 207 / 283 | 1150 / 1 / 196 / 259 | **┃** | 1150 / 1 / 192 / 256 | 1150 / 1 / 200 / 266 | **┃** | 1150 / 1 / 198 / 277 | 1150 / 1 / 197 / 262 |
| paymentservice | 155 / 1 / 18 / 26 | 155 / 1 / 20 / 30 | **┃** | 155 / 1 / 20 / 32 | 155 / 1 / 20 / 30 | **┃** | 155 / 1 / 20 / 31 | 155 / 1 / 21 / 31 | **┃** | 155 / 1 / 22 / 39 | 155 / 1 / 22 / 32 | **┃** | 155 / 1 / 20 / 31 | 155 / 1 / 21 / 32 |
| emailservice | 120 / 1 / 38 / 50 | 120 / 1 / 39 / 52 | **┃** | 120 / 1 / 39 / 51 | 120 / 1 / 39 / 51 | **┃** | 120 / 1 / 40 / 54 | 120 / 1 / 41 / 51 | **┃** | 120 / 1 / 38 / 48 | 120 / 1 / 41 / 54 | **┃** | 120 / 1 / 40 / 53 | 120 / 1 / 40 / 52 |
| productcatalogservice | 800 / 1 / 254 / 339 | 800 / 1 / 233 / 332 | **┃** | 800 / 1 / 236 / 320 | 800 / 1 / 257 / 344 | **┃** | 800 / 1 / 268 / 357 | 800 / 1 / 235 / 306 | **┃** | 800 / 1 / 232 / 310 | 800 / 1 / 244 / 322 | **┃** | 800 / 1 / 253 / 351 | 800 / 1 / 227 / 303 |
| cartservice | 800 / 1 / 356 / 578 | 800 / 1 / 391 / 692 | **┃** | 800 / 1 / 352 / 586 | 800 / 1 / 369 / 586 | **┃** | 800 / 1 / 386 / 631 | 800 / 1 / 364 / 582 | **┃** | 800 / 1 / 353 / 572 | 800 / 1 / 346 / 569 | **┃** | 800 / 1 / 369 / 626 | 800 / 1 / 344 / 538 |
| currencyservice | 770 / 1 / 107 / 146 | 770 / 1 / 115 / 161 | **┃** | 770 / 1 / 115 / 158 | 770 / 1 / 113 / 151 | **┃** | 770 / 1 / 118 / 162 | 770 / 1 / 121 / 185 | **┃** | 770 / 1 / 112 / 153 | 770 / 1 / 117 / 161 | **┃** | 770 / 1 / 114 / 157 | 770 / 1 / 118 / 157 |
| shippingservice | 770 / 1 / 40 / 54 | 770 / 1 / 44 / 61 | **┃** | 770 / 1 / 44 / 59 | 770 / 1 / 43 / 57 | **┃** | 770 / 1 / 44 / 58 | 770 / 1 / 47 / 62 | **┃** | 770 / 1 / 45 / 58 | 770 / 1 / 46 / 62 | **┃** | 770 / 1 / 45 / 60 | 770 / 1 / 45 / 59 |
| adservice | 1150 / 1 / 51 / 63 | 1150 / 1 / 51 / 66 | **┃** | 1150 / 1 / 53 / 70 | 1150 / 1 / 54 / 67 | **┃** | 1150 / 1 / 56 / 75 | 1150 / 1 / 54 / 64 | **┃** | 1150 / 1 / 50 / 60 | 1150 / 1 / 53 / 69 | **┃** | 1150 / 1 / 55 / 72 | 1150 / 1 / 52 / 63 |
| redis-cart | 540 / 1 / 46 / 74 | 540 / 1 / 46 / 82 | **┃** | 540 / 1 / 41 / 69 | 540 / 1 / 41 / 71 | **┃** | 540 / 1 / 46 / 75 | 540 / 1 / 43 / 73 | **┃** | 540 / 1 / 42 / 73 | 540 / 1 / 44 / 76 | **┃** | 540 / 1 / 46 / 81 | 540 / 1 / 41 / 70 |

CPU as a fraction of per-pod quota × replicas (mean / max).

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.20 / 0.27 | 0.19 / 0.27 | **┃** | 0.19 / 0.26 | 0.20 / 0.27 | **┃** | 0.21 / 0.28 | 0.19 / 0.25 | **┃** | 0.19 / 0.25 | 0.20 / 0.26 | **┃** | 0.20 / 0.28 | 0.19 / 0.25 |
| checkoutservice | 0.31 / 0.42 | 0.34 / 0.49 | **┃** | 0.32 / 0.44 | 0.33 / 0.44 | **┃** | 0.33 / 0.45 | 0.36 / 0.47 | **┃** | 0.33 / 0.44 | 0.35 / 0.47 | **┃** | 0.35 / 0.49 | 0.34 / 0.46 |
| recommendationservice | 0.18 / 0.24 | 0.18 / 0.26 | **┃** | 0.18 / 0.24 | 0.18 / 0.24 | **┃** | 0.18 / 0.25 | 0.17 / 0.23 | **┃** | 0.17 / 0.22 | 0.17 / 0.23 | **┃** | 0.17 / 0.24 | 0.17 / 0.23 |
| paymentservice | 0.12 / 0.17 | 0.13 / 0.19 | **┃** | 0.13 / 0.21 | 0.13 / 0.19 | **┃** | 0.13 / 0.20 | 0.14 / 0.20 | **┃** | 0.14 / 0.25 | 0.14 / 0.21 | **┃** | 0.13 / 0.20 | 0.13 / 0.21 |
| emailservice | 0.31 / 0.42 | 0.32 / 0.43 | **┃** | 0.33 / 0.42 | 0.33 / 0.42 | **┃** | 0.33 / 0.45 | 0.34 / 0.42 | **┃** | 0.32 / 0.40 | 0.34 / 0.45 | **┃** | 0.33 / 0.44 | 0.33 / 0.43 |
| productcatalogservice | 0.32 / 0.42 | 0.29 / 0.41 | **┃** | 0.30 / 0.40 | 0.32 / 0.43 | **┃** | 0.33 / 0.45 | 0.29 / 0.38 | **┃** | 0.29 / 0.39 | 0.30 / 0.40 | **┃** | 0.32 / 0.44 | 0.28 / 0.38 |
| cartservice | 0.44 / 0.72 | 0.49 / 0.86 | **┃** | 0.44 / 0.73 | 0.46 / 0.73 | **┃** | 0.48 / 0.79 | 0.46 / 0.73 | **┃** | 0.44 / 0.71 | 0.43 / 0.71 | **┃** | 0.46 / 0.78 | 0.43 / 0.67 |
| currencyservice | 0.14 / 0.19 | 0.15 / 0.21 | **┃** | 0.15 / 0.21 | 0.15 / 0.20 | **┃** | 0.15 / 0.21 | 0.16 / 0.24 | **┃** | 0.15 / 0.20 | 0.15 / 0.21 | **┃** | 0.15 / 0.20 | 0.15 / 0.20 |
| shippingservice | 0.05 / 0.07 | 0.06 / 0.08 | **┃** | 0.06 / 0.08 | 0.06 / 0.07 | **┃** | 0.06 / 0.08 | 0.06 / 0.08 | **┃** | 0.06 / 0.08 | 0.06 / 0.08 | **┃** | 0.06 / 0.08 | 0.06 / 0.08 |
| adservice | 0.04 / 0.05 | 0.04 / 0.06 | **┃** | 0.05 / 0.06 | 0.05 / 0.06 | **┃** | 0.05 / 0.07 | 0.05 / 0.06 | **┃** | 0.04 / 0.05 | 0.05 / 0.06 | **┃** | 0.05 / 0.06 | 0.05 / 0.05 |
| redis-cart | 0.09 / 0.14 | 0.09 / 0.15 | **┃** | 0.08 / 0.13 | 0.08 / 0.13 | **┃** | 0.09 / 0.14 | 0.08 / 0.14 | **┃** | 0.08 / 0.14 | 0.08 / 0.14 | **┃** | 0.08 / 0.15 | 0.08 / 0.13 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | final_4a_unconstrained_rg_only_normal_run1 | final_4a_unconstrained_rg_only_normal_run2 | **┃** | final_4a_unconstrained_both_normal_run1 | final_4a_unconstrained_both_normal_run2 | **┃** | final_4a_unconstrained_tf_only_run1 | final_4a_unconstrained_tf_only_run2 | **┃** | final_4a_unconstrained_rg_only_burst_run1 | final_4a_unconstrained_rg_only_burst_run2 | **┃** | final_4a_unconstrained_both_burst_run1 | final_4a_unconstrained_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.303 | 0.297 | **┃** | 0.295 | 0.303 | **┃** | 0.317 | 0.274 | **┃** | 0.282 | 0.295 | **┃** | 0.304 | 0.281 |
| checkoutservice | 0.601 | 0.616 | **┃** | 0.555 | 0.580 | **┃** | 0.609 | 0.579 | **┃** | 0.559 | 0.623 | **┃** | 0.584 | 0.581 |
| recommendationservice | 0.318 | 0.369 | **┃** | 0.323 | 0.330 | **┃** | 0.326 | 0.321 | **┃** | 0.326 | 0.340 | **┃** | 0.319 | 0.320 |
| paymentservice | 0.432 | 0.484 | **┃** | 0.471 | 0.432 | **┃** | 0.432 | 0.523 | **┃** | 0.516 | 0.503 | **┃** | 0.710 | 0.445 |
| emailservice | 0.675 | 0.775 | **┃** | 0.767 | 0.742 | **┃** | 0.817 | 0.742 | **┃** | 0.733 | 0.800 | **┃** | 0.742 | 0.758 |
| productcatalogservice | 0.504 | 0.516 | **┃** | 0.502 | 0.479 | **┃** | 0.521 | 0.463 | **┃** | 0.455 | 0.487 | **┃** | 0.521 | 0.482 |
| cartservice | 0.858 | 0.895 | **┃** | 0.819 | 0.856 | **┃** | 0.860 | 0.868 | **┃** | 0.814 | 0.805 | **┃** | 0.905 | 0.855 |
| currencyservice | 0.301 | 0.284 | **┃** | 0.309 | 0.278 | **┃** | 0.287 | 0.352 | **┃** | 0.300 | 0.343 | **┃** | 0.284 | 0.312 |
| shippingservice | 0.121 | 0.126 | **┃** | 0.132 | 0.126 | **┃** | 0.129 | 0.130 | **┃** | 0.125 | 0.131 | **┃** | 0.126 | 0.135 |
| adservice | 0.113 | 0.092 | **┃** | 0.113 | 0.094 | **┃** | 0.149 | 0.096 | **┃** | 0.091 | 0.109 | **┃** | 0.094 | 0.092 |
| redis-cart | 0.391 | 0.448 | **┃** | 0.422 | 0.426 | **┃** | 0.406 | 0.404 | **┃** | 0.406 | 0.511 | **┃** | 0.517 | 0.356 |

## Throttle data quality

`final_4a_unconstrained_rg_only_normal_run2` is **FLAGGED**: 144 fetch warnings, first warning 22:26:35, longest no-fresh threshold 365 s and longest no-fresh admitted 365 s. That hold is TopFull off, so it has no admission cap to lose. Its live-cap table is still pasted. Cap and admitted-rate numbers on that hold are carried, not measured. The other nine scored holds are throttle clean (0 fetch warnings, longest no-fresh gap 5 s). Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | --- | --- | --- | --- | --- |
| final_4a_unconstrained_rg_only_normal_run1 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_rg_only_normal_run2 | **FLAGGED** | 144 | 22:26:35 | 365 | 365 |
| final_4a_unconstrained_both_normal_run1 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_both_normal_run2 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_tf_only_run1 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_tf_only_run2 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_rg_only_burst_run1 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_rg_only_burst_run2 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_both_burst_run1 | ok | 0 | — | 5 | 5 |
| final_4a_unconstrained_both_burst_run2 | ok | 0 | — | 5 | 5 |

## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. `postcart` and `emptycart` are no cap on every live read of every scored column. The same is true of getproduct, postcheckout, and getcart.

### final_4a_unconstrained_rg_only_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 22:01:30–22:13:30 |
| postcheckout | no cap 22:01:30–22:13:30 |
| getcart | no cap 22:01:30–22:13:30 |
| postcart | no cap 22:01:30–22:13:30 |
| emptycart | no cap 22:01:30–22:13:30 |

### final_4a_unconstrained_rg_only_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 22:20:15–22:32:35 |
| postcheckout | no cap 22:20:15–22:32:35 |
| getcart | no cap 22:20:15–22:32:35 |
| postcart | no cap 22:20:15–22:32:35 |
| emptycart | no cap 22:20:15–22:32:35 |

### final_4a_unconstrained_both_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:20:15–00:32:05 |
| postcheckout | no cap 00:20:15–00:32:05 |
| getcart | no cap 00:20:15–00:32:05 |
| postcart | no cap 00:20:15–00:32:05 |
| emptycart | no cap 00:20:15–00:32:05 |

### final_4a_unconstrained_both_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:56:45–01:08:35 |
| postcheckout | no cap 00:56:45–01:08:35 |
| getcart | no cap 00:56:45–01:08:35 |
| postcart | no cap 00:56:45–01:08:35 |
| emptycart | no cap 00:56:45–01:08:35 |

### final_4a_unconstrained_tf_only_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:33:20–01:44:45 |
| postcheckout | no cap 01:33:20–01:44:45 |
| getcart | no cap 01:33:20–01:44:45 |
| postcart | no cap 01:33:20–01:44:45 |
| emptycart | no cap 01:33:20–01:44:45 |

### final_4a_unconstrained_tf_only_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:08:20–02:19:45 |
| postcheckout | no cap 02:08:20–02:19:45 |
| getcart | no cap 02:08:20–02:19:45 |
| postcart | no cap 02:08:20–02:19:45 |
| emptycart | no cap 02:08:20–02:19:45 |

### final_4a_unconstrained_rg_only_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:43:15–02:55:05 |
| postcheckout | no cap 02:43:15–02:55:05 |
| getcart | no cap 02:43:15–02:55:05 |
| postcart | no cap 02:43:15–02:55:05 |
| emptycart | no cap 02:43:15–02:55:05 |

### final_4a_unconstrained_rg_only_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:01:30–03:13:20 |
| postcheckout | no cap 03:01:30–03:13:20 |
| getcart | no cap 03:01:30–03:13:20 |
| postcart | no cap 03:01:30–03:13:20 |
| emptycart | no cap 03:01:30–03:13:20 |

### final_4a_unconstrained_both_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:20:15–03:32:05 |
| postcheckout | no cap 03:20:15–03:32:05 |
| getcart | no cap 03:20:15–03:32:05 |
| postcart | no cap 03:20:15–03:32:05 |
| emptycart | no cap 03:20:15–03:32:05 |

### final_4a_unconstrained_both_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 04:17:30–04:29:25 |
| postcheckout | no cap 04:17:30–04:29:25 |
| getcart | no cap 04:17:30–04:29:25 |
| postcart | no cap 04:17:30–04:29:25 |
| emptycart | no cap 04:17:30–04:29:25 |

## One paragraph per scored column

Launches that are not a column are in the index. They are not repeated here.

**final_4a_unconstrained_rg_only_normal_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_rg_only_normal_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5. Throttle FLAG, TopFull off, no admission cap to lose.

**final_4a_unconstrained_both_normal_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 6. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_both_normal_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_tf_only_run1.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: checkoutservice 2. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 19 / 0. No service reached a detector share of 0.5. emailservice was 1/692 (0.1%).

**final_4a_unconstrained_tf_only_run2.** RetryGuard was off, so this hold did not shed and did not climb. Outbound retry delta: checkoutservice 2. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_rg_only_burst_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_rg_only_burst_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 5. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_both_burst_run1.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

**final_4a_unconstrained_both_burst_run2.** No transition lines, so nothing shed and nothing climbed. Outbound retry delta: checkoutservice 0. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. No service reached a detector share of 0.5.

## Related

- [S4 relock mode matrix plan](../docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md)
- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [(a) / (b) / (c) reading](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md)
- [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md)
- [ADR 0008](../docs/adr/0008-locked-retryguard-parameters.md)
- [ADR 0009](../docs/adr/0009-paper-c1-default-cpu-table.md)
- [2026-10-13-s4a-constrained-relock-abc.md](2026-10-13-s4a-constrained-relock-abc.md)
- [2026-10-13-s4a-constrained-mode-matrix-abc.md](2026-10-13-s4a-constrained-mode-matrix-abc.md) (catalog 50 m; not a column here)
