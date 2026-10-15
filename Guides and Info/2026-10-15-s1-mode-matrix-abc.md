# S1 mode matrix

## Setup

Ten holds, 300 s each, mix 175 / 30 / 70 / 90 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1 is unchanged on every row: checkout 800 m, recommendations 1150 m, catalog 800 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, payment 155 m, email 120 m, redis-cart 540 m. Frontend 1150 m is the HPA pin. Frontend HPA min=max=4, catalog HPA min=max=1, sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off 120 s. Checkout and recommendations stayed up.

Normal and TopFull-only folders are under `experiments/results/final results/S1_normal_operation_normal/`. Burst folders are under `experiments/results/final results/S1_normal_operation_burst/`.

- `experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1`
- `experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run2`
- `experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run1`
- `experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run2`
- `experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run1`
- `experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run2`
- `experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1`
- `experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run2`
- `experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run1`
- `experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run2`

All ten launches passed the collector gate. No throttle FLAG. No replay. Column order is holds 1–10. A bold bar separates each pair. `s1_normal_*`, `s1_burst20_*`, and `campaign_48/` S1 are not columns.

## Index

| Hold | log_folder | RetryGuard | TopFull |
| --- | --- | --- | --- |
| 1 | final_s1_rg_only_normal_run1 | normal | off |
| 2 | final_s1_rg_only_normal_run2 | normal | off |
| 3 | final_s1_both_normal_run1 | normal | on |
| 4 | final_s1_both_normal_run2 | normal | on |
| 5 | final_s1_tf_only_run1 | off | on |
| 6 | final_s1_tf_only_run2 | off | on |
| 7 | final_s1_rg_only_burst_run1 | burst_rpr 2.0 | off |
| 8 | final_s1_rg_only_burst_run2 | burst_rpr 2.0 | off |
| 9 | final_s1_both_burst_run1 | burst_rpr 2.0 | on |
| 10 | final_s1_both_burst_run2 | burst_rpr 2.0 | on |

## Edge-mode bars

A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s. Burst mode was off on the six normal and TopFull-only holds.

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

## Gate numbers

- final_s1_rg_only_normal_run1: Locust total.csv 287 rows, mesh span 364 s, inbound gaps ≥ 1.5 s: 0 of 4004, retryguard.log present.
- final_s1_rg_only_normal_run2: Locust total.csv 287 rows, mesh span 365 s, inbound gaps ≥ 1.5 s: 0 of 4015, retryguard.log present.
- final_s1_both_normal_run1: Locust total.csv 286 rows, mesh span 365 s, inbound gaps ≥ 1.5 s: 0 of 4015, retryguard.log present.
- final_s1_both_normal_run2: Locust total.csv 287 rows, mesh span 366 s, inbound gaps ≥ 1.5 s: 0 of 4026, retryguard.log present.
- final_s1_tf_only_run1: Locust total.csv 288 rows, mesh span 340 s, inbound gaps ≥ 1.5 s: 0 of 3740, retryguard.log absent.
- final_s1_tf_only_run2: Locust total.csv 288 rows, mesh span 343 s, inbound gaps ≥ 1.5 s: 0 of 3773, retryguard.log absent.
- final_s1_rg_only_burst_run1: Locust total.csv 288 rows, mesh span 365 s, inbound gaps ≥ 1.5 s: 0 of 4015, retryguard.log present.
- final_s1_rg_only_burst_run2: Locust total.csv 289 rows, mesh span 364 s, inbound gaps ≥ 1.5 s: 0 of 4004, retryguard.log present.
- final_s1_both_burst_run1: Locust total.csv 287 rows, mesh span 365 s, inbound gaps ≥ 1.5 s: 0 of 4015, retryguard.log present.
- final_s1_both_burst_run2: Locust total.csv 287 rows, mesh span 366 s, inbound gaps ≥ 1.5 s: 0 of 4026, retryguard.log present.

## (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

## (a) Mean / median / max / volume rpr

| Edge | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | 0.001 / 0.000 / 0.33 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.07 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

## (a) Climb streaks, 1-attempt / 2-attempt

| Edge | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

Burst bars: final_s1_rg_only_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s1_rg_only_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s1_both_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s1_both_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force (burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count in parentheses. Samples exist only while the edge is above 0 attempts and the window meets the volume floor.

## (a2) Burst window

| Edge | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (307) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (306) |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (306) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (303) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (308) | 0.00 / 0.00 / 0 / 0 (306) | **┃** | 0.00 / 0.00 / 0 / 0 (308) | 0.00 / 0.00 / 0 / 0 (308) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (303) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (304) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (298) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (300) |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (299) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (300) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (299) | **┃** | 0.01 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (300) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (299) | **┃** | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (300) |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | 0.00 / 0.00 / 0 / 0 (304) | 0.00 / 0.00 / 0 / 0 (303) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (304) | **┃** | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (305) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (305) | **┃** | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (307) |

Burst vs normal sheds (`ON→OFF burst` is the part fired by `metric=rpr_burst`): `final_s1_rg_only_burst_run1` 0 burst and 0 normal; `final_s1_rg_only_burst_run2` 0 burst and 0 normal; `final_s1_both_burst_run1` 0 burst and 0 normal; `final_s1_both_burst_run2` 0 burst and 0 normal.

## (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: rejection streak under the re-enable bar / count

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 313 / 313 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| checkoutservice | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 |
| recommendationservice | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 |
| paymentservice | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 | **┃** | 311 / 311 | 311 / 311 | **┃** | 312 / 312 | 312 / 312 |
| emailservice | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 | **┃** | 311 / 311 | 310 / 310 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 |
| productcatalogservice | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| cartservice | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| currencyservice | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 |
| shippingservice | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 |
| adservice | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 |
| productcatalogservice | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 313 / 313 | 313 / 313 |
| currencyservice | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 313 / 313 | **┃** | 312 / 312 | 312 / 312 | **┃** | 312 / 312 | 313 / 313 |
| adservice | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 | **┃** | 312 / 312 | 311 / 311 | **┃** | 311 / 311 | 311 / 311 | **┃** | 311 / 311 | 312 / 312 |

gRPC counted in the rejection rate on the four read callees (main rejection tables above) and in the retry policy. Cell is grpc_4 / grpc_14.

## grpc_4 / grpc_14

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| checkoutservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| recommendationservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| paymentservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| emailservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| productcatalogservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| cartservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| currencyservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| shippingservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| adservice | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |
| redis-cart | 0/413 (0.0%) | 0/414 (0.0%) | **┃** | 0/415 (0.0%) | 0/415 (0.0%) | **┃** | 0/390 (0.0%) | 0/393 (0.0%) | **┃** | 0/413 (0.0%) | 0/412 (0.0%) | **┃** | 0/415 (0.0%) | 0/417 (0.0%) |

## (c) Outbound retry delta by target

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 2 | 0 |
| cartservice | 3 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

## (c) Inbound resets

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 4 | 5 | **┃** | 10 | 2 | **┃** | 2 | 7 | **┃** | 7 | 8 | **┃** | 8 | 2 |
| checkoutservice | 0 | 0 | **┃** | 3 | 0 | **┃** | 0 | 5 | **┃** | 4 | 0 | **┃** | 0 | 0 |
| recommendationservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 5 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 0 | 2 | **┃** | 3 | 1 | **┃** | 2 | 0 | **┃** | 0 | 2 | **┃** | 4 | 1 |
| cartservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

## RetryGuard toggles

final_s1_rg_only_normal_run1: no transition lines.
final_s1_rg_only_normal_run2: no transition lines.
final_s1_both_normal_run1: no transition lines.
final_s1_both_normal_run2: no transition lines.
final_s1_tf_only_run1: no transition lines.
final_s1_tf_only_run2: no transition lines.
final_s1_rg_only_burst_run1: no transition lines.
final_s1_rg_only_burst_run2: no transition lines.
final_s1_both_burst_run1: no transition lines.
final_s1_both_burst_run2: no transition lines.

## RetryGuard toggles, part 2

No callee shed or re-enabled on any hold. One sentence, no table.

## Locust goodput

| API | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 161.3 | 161.3 | **┃** | 160.7 | 161.1 | **┃** | 161.0 | 161.0 | **┃** | 161.0 | 161.1 | **┃** | 161.2 | 161.5 |
| postcheckout | 27.7 | 27.7 | **┃** | 27.7 | 27.7 | **┃** | 27.6 | 27.6 | **┃** | 27.6 | 27.6 | **┃** | 27.7 | 27.7 |
| getcart | 64.5 | 64.5 | **┃** | 64.3 | 64.4 | **┃** | 64.3 | 64.4 | **┃** | 64.4 | 64.4 | **┃** | 64.5 | 64.6 |
| postcart | 82.9 | 82.9 | **┃** | 82.6 | 82.8 | **┃** | 82.8 | 82.8 | **┃** | 82.8 | 82.8 | **┃** | 82.9 | 83.0 |
| emptycart | 4.7 | 4.7 | **┃** | 4.7 | 4.7 | **┃** | 4.7 | 4.7 | **┃** | 4.7 | 4.7 | **┃** | 4.7 | 4.7 |

## Locust fail rate

| API | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

| API | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 72 | 82 | **┃** | 80 | 88 | **┃** | 88 | 84 | **┃** | 92 | 93 | **┃** | 80 | 84 |
| postcheckout | 152 | 150 | **┃** | 194 | 188 | **┃** | 170 | 208 | **┃** | 156 | 213 | **┃** | 197 | 151 |
| getcart | 49 | 70 | **┃** | 69 | 75 | **┃** | 75 | 58 | **┃** | 78 | 78 | **┃** | 55 | 68 |
| postcart | 59 | 59 | **┃** | 59 | 60 | **┃** | 60 | 60 | **┃** | 61 | 61 | **┃** | 59 | 60 |
| emptycart | 11 | 12 | **┃** | 13 | 13 | **┃** | 17 | 12 | **┃** | 12 | 17 | **┃** | 12 | 13 |

## Inbound arrival rate

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 291.4 | 290.8 | **┃** | 290.8 | 289.8 | **┃** | 312.2 | 309.7 | **┃** | 290.6 | 291.6 | **┃** | 290.8 | 290.1 |
| checkoutservice | 23.6 | 23.6 | **┃** | 23.6 | 23.5 | **┃** | 25.3 | 25.1 | **┃** | 23.6 | 23.6 | **┃** | 23.6 | 23.5 |
| recommendationservice | 216.4 | 216.0 | **┃** | 216.0 | 215.2 | **┃** | 231.9 | 230.0 | **┃** | 215.8 | 216.6 | **┃** | 216.0 | 215.4 |
| paymentservice | 23.6 | 23.6 | **┃** | 23.6 | 23.5 | **┃** | 25.3 | 25.1 | **┃** | 23.6 | 23.6 | **┃** | 23.6 | 23.5 |
| emailservice | 23.6 | 23.6 | **┃** | 23.6 | 23.5 | **┃** | 25.3 | 25.1 | **┃** | 23.5 | 23.6 | **┃** | 23.6 | 23.5 |
| productcatalogservice | 1507.0 | 1504.2 | **┃** | 1503.8 | 1498.8 | **┃** | 1614.8 | 1601.6 | **┃** | 1503.0 | 1508.3 | **┃** | 1504.1 | 1500.1 |
| cartservice | 315.0 | 314.4 | **┃** | 314.3 | 313.3 | **┃** | 337.6 | 334.8 | **┃** | 314.2 | 315.3 | **┃** | 314.4 | 313.6 |
| currencyservice | 432.8 | 432.0 | **┃** | 431.9 | 430.5 | **┃** | 463.8 | 460.0 | **┃** | 431.7 | 433.2 | **┃** | 432.0 | 430.8 |
| shippingservice | 102.4 | 102.3 | **┃** | 102.3 | 101.9 | **┃** | 109.8 | 108.9 | **┃** | 102.2 | 102.5 | **┃** | 102.2 | 102.0 |
| adservice | 137.6 | 137.3 | **┃** | 137.3 | 136.8 | **┃** | 147.4 | 146.2 | **┃** | 137.2 | 137.7 | **┃** | 137.3 | 137.0 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn (ms)

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 40 | 48 | **┃** | 48 | 52 | **┃** | 51 | 49 | **┃** | 52 | 55 | **┃** | 46 | 50 |
| checkoutservice | 62 | 64 | **┃** | 84 | 85 | **┃** | 79 | 82 | **┃** | 65 | 88 | **┃** | 80 | 61 |
| recommendationservice | 6 | 8 | **┃** | 9 | 10 | **┃** | 9 | 8 | **┃** | 10 | 9 | **┃** | 7 | 8 |
| paymentservice | 2 | 1 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| emailservice | 8 | 8 | **┃** | 7 | 7 | **┃** | 5 | 15 | **┃** | 7 | 12 | **┃** | 12 | 6 |
| productcatalogservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| currencyservice | 1 | 1 | **┃** | 1 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 1 | 2 |
| shippingservice | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 1 | **┃** | 1 | 1 | **┃** | 0 | 0 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

CPU cells are per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum usage across replicas.

## CPU quota / replicas / mean / max

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 862 / 1370 | 1150 / 4 / 805 / 1283 | **┃** | 1150 / 4 / 821 / 1361 | 1150 / 4 / 864 / 1422 | **┃** | 1150 / 4 / 895 / 1397 | 1150 / 4 / 970 / 1500 | **┃** | 1150 / 4 / 873 / 1487 | 1150 / 4 / 847 / 1388 | **┃** | 1150 / 4 / 903 / 1440 | 1150 / 4 / 824 / 1343 |
| checkoutservice | 800 / 1 / 250 / 409 | 800 / 1 / 254 / 410 | **┃** | 800 / 1 / 253 / 418 | 800 / 1 / 260 / 432 | **┃** | 800 / 1 / 277 / 432 | 800 / 1 / 281 / 442 | **┃** | 800 / 1 / 271 / 485 | 800 / 1 / 277 / 461 | **┃** | 800 / 1 / 261 / 430 | 800 / 1 / 260 / 426 |
| recommendationservice | 1150 / 1 / 320 / 517 | 1150 / 1 / 321 / 515 | **┃** | 1150 / 1 / 320 / 548 | 1150 / 1 / 345 / 569 | **┃** | 1150 / 1 / 353 / 557 | 1150 / 1 / 381 / 602 | **┃** | 1150 / 1 / 352 / 654 | 1150 / 1 / 348 / 589 | **┃** | 1150 / 1 / 346 / 558 | 1150 / 1 / 330 / 543 |
| paymentservice | 155 / 1 / 22 / 44 | 155 / 1 / 18 / 31 | **┃** | 155 / 1 / 18 / 31 | 155 / 1 / 19 / 33 | **┃** | 155 / 1 / 19 / 31 | 155 / 1 / 20 / 34 | **┃** | 155 / 1 / 19 / 34 | 155 / 1 / 19 / 32 | **┃** | 155 / 1 / 19 / 31 | 155 / 1 / 18 / 31 |
| emailservice | 120 / 1 / 35 / 54 | 120 / 1 / 36 / 53 | **┃** | 120 / 1 / 36 / 56 | 120 / 1 / 37 / 59 | **┃** | 120 / 1 / 38 / 56 | 120 / 1 / 40 / 60 | **┃** | 120 / 1 / 38 / 64 | 120 / 1 / 38 / 60 | **┃** | 120 / 1 / 37 / 56 | 120 / 1 / 36 / 55 |
| productcatalogservice | 800 / 1 / 328 / 517 | 800 / 1 / 292 / 457 | **┃** | 800 / 1 / 295 / 480 | 800 / 1 / 305 / 488 | **┃** | 800 / 1 / 316 / 481 | 800 / 1 / 357 / 538 | **┃** | 800 / 1 / 313 / 515 | 800 / 1 / 305 / 487 | **┃** | 800 / 1 / 335 / 529 | 800 / 1 / 294 / 468 |
| cartservice | 800 / 1 / 224 / 370 | 800 / 1 / 204 / 343 | **┃** | 800 / 1 / 221 / 437 | 800 / 1 / 218 / 364 | **┃** | 800 / 1 / 259 / 482 | 800 / 1 / 282 / 501 | **┃** | 800 / 1 / 220 / 419 | 800 / 1 / 236 / 455 | **┃** | 800 / 1 / 225 / 375 | 800 / 1 / 220 / 426 |
| currencyservice | 770 / 1 / 206 / 327 | 770 / 1 / 188 / 299 | **┃** | 770 / 1 / 196 / 323 | 770 / 1 / 204 / 335 | **┃** | 770 / 1 / 214 / 330 | 770 / 1 / 224 / 350 | **┃** | 770 / 1 / 205 / 362 | 770 / 1 / 203 / 338 | **┃** | 770 / 1 / 211 / 338 | 770 / 1 / 190 / 312 |
| shippingservice | 770 / 1 / 50 / 78 | 770 / 1 / 51 / 79 | **┃** | 770 / 1 / 49 / 80 | 770 / 1 / 51 / 81 | **┃** | 770 / 1 / 53 / 80 | 770 / 1 / 57 / 87 | **┃** | 770 / 1 / 53 / 91 | 770 / 1 / 54 / 88 | **┃** | 770 / 1 / 53 / 83 | 770 / 1 / 52 / 83 |
| adservice | 1150 / 1 / 112 / 284 | 1150 / 1 / 85 / 132 | **┃** | 1150 / 1 / 87 / 138 | 1150 / 1 / 92 / 140 | **┃** | 1150 / 1 / 93 / 136 | 1150 / 1 / 97 / 144 | **┃** | 1150 / 1 / 92 / 152 | 1150 / 1 / 90 / 144 | **┃** | 1150 / 1 / 91 / 134 | 1150 / 1 / 84 / 124 |
| redis-cart | 540 / 1 / 30 / 60 | 540 / 1 / 29 / 58 | **┃** | 540 / 1 / 29 / 60 | 540 / 1 / 30 / 65 | **┃** | 540 / 1 / 31 / 61 | 540 / 1 / 33 / 65 | **┃** | 540 / 1 / 30 / 62 | 540 / 1 / 30 / 62 | **┃** | 540 / 1 / 31 / 62 | 540 / 1 / 30 / 59 |

## CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.19 / 0.30 | 0.17 / 0.28 | **┃** | 0.18 / 0.30 | 0.19 / 0.31 | **┃** | 0.19 / 0.30 | 0.21 / 0.33 | **┃** | 0.19 / 0.32 | 0.18 / 0.30 | **┃** | 0.20 / 0.31 | 0.18 / 0.29 |
| checkoutservice | 0.31 / 0.51 | 0.32 / 0.51 | **┃** | 0.32 / 0.52 | 0.33 / 0.54 | **┃** | 0.35 / 0.54 | 0.35 / 0.55 | **┃** | 0.34 / 0.61 | 0.35 / 0.58 | **┃** | 0.33 / 0.54 | 0.33 / 0.53 |
| recommendationservice | 0.28 / 0.45 | 0.28 / 0.45 | **┃** | 0.28 / 0.48 | 0.30 / 0.49 | **┃** | 0.31 / 0.48 | 0.33 / 0.52 | **┃** | 0.31 / 0.57 | 0.30 / 0.51 | **┃** | 0.30 / 0.49 | 0.29 / 0.47 |
| paymentservice | 0.14 / 0.28 | 0.12 / 0.20 | **┃** | 0.12 / 0.20 | 0.12 / 0.21 | **┃** | 0.13 / 0.20 | 0.13 / 0.22 | **┃** | 0.12 / 0.22 | 0.13 / 0.21 | **┃** | 0.12 / 0.20 | 0.12 / 0.20 |
| emailservice | 0.30 / 0.45 | 0.30 / 0.44 | **┃** | 0.30 / 0.47 | 0.31 / 0.49 | **┃** | 0.32 / 0.47 | 0.33 / 0.50 | **┃** | 0.31 / 0.53 | 0.32 / 0.50 | **┃** | 0.31 / 0.47 | 0.30 / 0.46 |
| productcatalogservice | 0.41 / 0.65 | 0.36 / 0.57 | **┃** | 0.37 / 0.60 | 0.38 / 0.61 | **┃** | 0.40 / 0.60 | 0.45 / 0.67 | **┃** | 0.39 / 0.64 | 0.38 / 0.61 | **┃** | 0.42 / 0.66 | 0.37 / 0.58 |
| cartservice | 0.28 / 0.46 | 0.25 / 0.43 | **┃** | 0.28 / 0.55 | 0.27 / 0.46 | **┃** | 0.32 / 0.60 | 0.35 / 0.63 | **┃** | 0.28 / 0.52 | 0.29 / 0.57 | **┃** | 0.28 / 0.47 | 0.28 / 0.53 |
| currencyservice | 0.27 / 0.42 | 0.24 / 0.39 | **┃** | 0.25 / 0.42 | 0.27 / 0.44 | **┃** | 0.28 / 0.43 | 0.29 / 0.45 | **┃** | 0.27 / 0.47 | 0.26 / 0.44 | **┃** | 0.27 / 0.44 | 0.25 / 0.41 |
| shippingservice | 0.06 / 0.10 | 0.07 / 0.10 | **┃** | 0.06 / 0.10 | 0.07 / 0.11 | **┃** | 0.07 / 0.10 | 0.07 / 0.11 | **┃** | 0.07 / 0.12 | 0.07 / 0.11 | **┃** | 0.07 / 0.11 | 0.07 / 0.11 |
| adservice | 0.10 / 0.25 | 0.07 / 0.11 | **┃** | 0.08 / 0.12 | 0.08 / 0.12 | **┃** | 0.08 / 0.12 | 0.08 / 0.13 | **┃** | 0.08 / 0.13 | 0.08 / 0.13 | **┃** | 0.08 / 0.12 | 0.07 / 0.11 |
| redis-cart | 0.05 / 0.11 | 0.05 / 0.11 | **┃** | 0.05 / 0.11 | 0.06 / 0.12 | **┃** | 0.06 / 0.11 | 0.06 / 0.12 | **┃** | 0.06 / 0.11 | 0.06 / 0.11 | **┃** | 0.06 / 0.11 | 0.05 / 0.11 |

## Detector max utilization

| Service | final_s1_rg_only_normal_run1 | final_s1_rg_only_normal_run2 | **┃** | final_s1_both_normal_run1 | final_s1_both_normal_run2 | **┃** | final_s1_tf_only_run1 | final_s1_tf_only_run2 | **┃** | final_s1_rg_only_burst_run1 | final_s1_rg_only_burst_run2 | **┃** | final_s1_both_burst_run1 | final_s1_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.321 | 0.301 | **┃** | 0.318 | 0.325 | **┃** | 0.328 | 0.353 | **┃** | 0.344 | 0.317 | **┃** | 0.345 | 0.300 |
| checkoutservice | 0.596 | 0.613 | **┃** | 0.589 | 0.616 | **┃** | 0.600 | 0.659 | **┃** | 0.686 | 0.623 | **┃** | 0.599 | 0.621 |
| recommendationservice | 0.473 | 0.480 | **┃** | 0.508 | 0.523 | **┃** | 0.506 | 0.570 | **┃** | 0.654 | 0.535 | **┃** | 0.510 | 0.505 |
| paymentservice | 0.419 | 0.342 | **┃** | 0.381 | 0.355 | **┃** | 0.400 | 0.394 | **┃** | 0.342 | 0.419 | **┃** | 0.348 | 0.348 |
| emailservice | 0.633 | 0.633 | **┃** | 0.683 | 0.692 | **┃** | 0.667 | 0.683 | **┃** | 0.708 | 0.733 | **┃** | 0.700 | 0.700 |
| productcatalogservice | 0.679 | 0.613 | **┃** | 0.639 | 0.645 | **┃** | 0.619 | 0.710 | **┃** | 0.681 | 0.636 | **┃** | 0.703 | 0.625 |
| cartservice | 0.497 | 0.525 | **┃** | 0.571 | 0.489 | **┃** | 0.629 | 0.650 | **┃** | 0.555 | 0.588 | **┃** | 0.505 | 0.546 |
| currencyservice | 0.474 | 0.451 | **┃** | 0.471 | 0.522 | **┃** | 0.477 | 0.486 | **┃** | 0.514 | 0.487 | **┃** | 0.481 | 0.453 |
| shippingservice | 0.132 | 0.136 | **┃** | 0.130 | 0.134 | **┃** | 0.127 | 0.153 | **┃** | 0.147 | 0.148 | **┃** | 0.140 | 0.138 |
| adservice | 0.670 | 0.158 | **┃** | 0.134 | 0.154 | **┃** | 0.149 | 0.162 | **┃** | 0.160 | 0.144 | **┃** | 0.364 | 0.146 |
| redis-cart | 0.263 | 0.313 | **┃** | 0.387 | 0.372 | **┃** | 0.300 | 0.324 | **┃** | 0.378 | 0.365 | **┃** | 0.317 | 0.341 |

No hold is FLAGGED. Cap and admitted-rate numbers are measured.

`postcart` and `emptycart` are no cap on every live read of every hold.

## Throttle data quality

Live reads of the TopFull proxy normally land every 5 s. A hold is **FLAGGED** when `topfull_throttle_collector.log` has any `fetch failed` WARNING, or when an API goes longer than 30 s without a fresh threshold or admitted read. Cap and admitted-rate numbers on a flagged hold are carried values; filter on `*_fresh==1` or drop the hold from those numbers. Goodput, P95 and rejection do not use this file.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | --- | --- | --- | --- | --- |
| final_s1_rg_only_normal_run1 | ok | 0 | — | 5 | 5 |
| final_s1_rg_only_normal_run2 | ok | 0 | — | 5 | 5 |
| final_s1_both_normal_run1 | ok | 0 | — | 5 | 5 |
| final_s1_both_normal_run2 | ok | 0 | — | 5 | 5 |
| final_s1_tf_only_run1 | ok | 0 | — | 5 | 5 |
| final_s1_tf_only_run2 | ok | 0 | — | 5 | 5 |
| final_s1_rg_only_burst_run1 | ok | 0 | — | 5 | 5 |
| final_s1_rg_only_burst_run2 | ok | 0 | — | 5 | 5 |
| final_s1_both_burst_run1 | ok | 0 | — | 5 | 5 |
| final_s1_both_burst_run2 | ok | 0 | — | 5 | 5 |

## TopFull live caps

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### final_s1_rg_only_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 22:23:35–22:30:25 |
| postcheckout | no cap 22:23:35–22:30:25 |
| getcart | no cap 22:23:35–22:30:25 |
| postcart | no cap 22:23:35–22:30:25 |
| emptycart | no cap 22:23:35–22:30:25 |

### final_s1_rg_only_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 22:38:40–22:45:30 |
| postcheckout | no cap 22:38:40–22:45:30 |
| getcart | no cap 22:38:40–22:45:30 |
| postcart | no cap 22:38:40–22:45:30 |
| emptycart | no cap 22:38:40–22:45:30 |

### final_s1_both_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 22:51:40–22:58:30 |
| postcheckout | no cap 22:51:40–22:58:30 |
| getcart | no cap 22:51:40–22:58:30 |
| postcart | no cap 22:51:40–22:58:30 |
| emptycart | no cap 22:51:40–22:58:30 |

### final_s1_both_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 23:04:50–23:11:40 |
| postcheckout | no cap 23:04:50–23:11:40 |
| getcart | no cap 23:04:50–23:11:40 |
| postcart | no cap 23:04:50–23:11:40 |
| emptycart | no cap 23:04:50–23:11:40 |

### final_s1_tf_only_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 23:17:50–23:24:15 |
| postcheckout | no cap 23:17:50–23:24:15 |
| getcart | no cap 23:17:50–23:24:15 |
| postcart | no cap 23:17:50–23:24:15 |
| emptycart | no cap 23:17:50–23:24:15 |

### final_s1_tf_only_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 23:30:05–23:36:30 |
| postcheckout | no cap 23:30:05–23:36:30 |
| getcart | no cap 23:30:05–23:36:30 |
| postcart | no cap 23:30:05–23:36:30 |
| emptycart | no cap 23:30:05–23:36:30 |

### final_s1_rg_only_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 23:43:15–23:50:00 |
| postcheckout | no cap 23:43:15–23:50:00 |
| getcart | no cap 23:43:15–23:50:00 |
| postcart | no cap 23:43:15–23:50:00 |
| emptycart | no cap 23:43:15–23:50:00 |

### final_s1_rg_only_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 23:56:10–00:03:00 |
| postcheckout | no cap 23:56:10–00:03:00 |
| getcart | no cap 23:56:10–00:03:00 |
| postcart | no cap 23:56:10–00:03:00 |
| emptycart | no cap 23:56:10–00:03:00 |

### final_s1_both_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:09:10–00:16:00 |
| postcheckout | no cap 00:09:10–00:16:00 |
| getcart | no cap 00:09:10–00:16:00 |
| postcart | no cap 00:09:10–00:16:00 |
| emptycart | no cap 00:09:10–00:16:00 |

### final_s1_both_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:22:15–00:29:05 |
| postcheckout | no cap 00:22:15–00:29:05 |
| getcart | no cap 00:22:15–00:29:05 |
| postcart | no cap 00:22:15–00:29:05 |
| emptycart | no cap 00:22:15–00:29:05 |

## One paragraph per launch

`final_s1_rg_only_normal_run1`: no shed. Outbound retry delta: cartservice 3. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_rg_only_normal_run2`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_both_normal_run1`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_both_normal_run2`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_tf_only_run1`: no retryguard.log. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_tf_only_run2`: no retryguard.log. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_rg_only_burst_run1`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_rg_only_burst_run2`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_both_burst_run1`: no shed. Outbound retry delta: checkoutservice 2. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

`final_s1_both_burst_run2`: no shed. Outbound retry delta: 0 on every target. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: none at or above 0.5.

## Related

This campaign's plan is [2026-10-15-s1-s3-mode-matrix.md](../docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md). The run log is [2026-10-15-s1-mode-matrix-run-log.md](../docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md). Template: [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). The (a)/(b)/(c) reading is [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Controller: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md). [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../docs/adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../docs/adr/0009-paper-c1-default-cpu-table.md). Older S1 folders (`s1_normal_*`, `s1_burst20_*`, `campaign_48/`) are not columns.
