# S2 mode matrix

## Setup

Ten holds, 600 s each, mix 275 / 90 / 100 / 90 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1 is unchanged on every row: checkout 800 m, recommendations 1150 m, catalog 800 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, payment 155 m, email 120 m, redis-cart 540 m. Frontend 1150 m is the HPA pin. Frontend HPA min=max=4, catalog HPA min=max=1, sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off 120 s. Checkout and recommendations stayed up.

Normal and TopFull-only folders are under `experiments/results/final results/S2_sustained_overload_normal/`. Burst folders are under `experiments/results/final results/S2_sustained_overload_burst/`.

- `experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1`
- `experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run2`
- `experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run1`
- `experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run2`
- `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1`
- `experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2`
- `experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1`
- `experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2`
- `experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run1`
- `experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run2`

## Index

Column order is holds 1–10. A bold bar separates each pair. All ten launches passed the collector gate. `final_s2_tf_only_run2`, `final_s2_rg_only_burst_run2`, `final_s2_both_burst_run1`, and `final_s2_both_burst_run2` are throttle FLAG. Cap and admitted-rate numbers on those four folders are carried, not measured.

| Hold | log_folder | RetryGuard | TopFull |
| --- | --- | --- | --- |
| 1 | final_s2_rg_only_normal_run1 | normal | off |
| 2 | final_s2_rg_only_normal_run2 | normal | off |
| 3 | final_s2_both_normal_run1 | normal | on |
| 4 | final_s2_both_normal_run2 | normal | on |
| 5 | final_s2_tf_only_run1 | off | on |
| 6 | final_s2_tf_only_run2 | off | on |
| 7 | final_s2_rg_only_burst_run1 | burst_rpr 2.0 | off |
| 8 | final_s2_rg_only_burst_run2 | burst_rpr 2.0 | off |
| 9 | final_s2_both_burst_run1 | burst_rpr 2.0 | on |
| 10 | final_s2_both_burst_run2 | burst_rpr 2.0 | on |


## Edge-mode bars

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Burst bars: final_s2_rg_only_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s2_rg_only_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s2_both_burst_run1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s2_both_burst_run2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s. Burst mode was off on the six normal and TopFull-only holds.


## (a) Edge rpr

Edges with no tick above the shed bar and volume rpr 0 on every column are omitted: `frontend → cartservice`.


### File streak seconds / ticks above the shed bar (controller high)

Bold when the file streak is at least 30 seconds.

| Edge | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 1 (1) | **┃** | 7 / 20 (8) | 0 / 1 (1) | **┃** | 0 / 0 | 2 / 2 | **┃** | 0 / 0 (0) | 0 / 1 (1) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → recommendationservice | 22 / 190 (21) | 21 / 164 (21) | **┃** | 6 / 55 (7) | 10 / 122 (9) | **┃** | 9 / 111 | **176 / 350** | **┃** | 21 / 263 (21) | 22 / 166 (21) | **┃** | 23 / 206 (19) | 22 / 109 (20) |


### Mean / median / max / volume rpr

| Edge | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.001 / 0.000 / 0.09 / 0.001 | 0.002 / 0.000 / 0.62 / 0.002 | **┃** | 0.076 / 0.000 / 5.00 / 0.046 | 0.006 / 0.000 / 1.36 / 0.007 | **┃** | 0.002 / 0.000 / 0.19 / 0.003 | 0.006 / 0.000 / 1.44 / 0.010 | **┃** | 0.002 / 0.000 / 0.12 / 0.002 | 0.003 / 0.000 / 0.45 / 0.003 | **┃** | 0.003 / 0.000 / 0.20 / 0.003 | 0.000 / 0.000 / 0.09 / 0.000 |
| frontend → recommendationservice | 0.330 / 0.350 / 1.13 / 0.340 | 0.328 / 0.337 / 1.01 / 0.335 | **┃** | 0.072 / 0.000 / 1.09 / 0.066 | 0.186 / 0.000 / 1.75 / 0.171 | **┃** | 0.204 / 0.000 / 1.44 / 0.179 | 0.591 / 0.741 / 2.12 / 0.541 | **┃** | 0.263 / 0.231 / 1.45 / 0.266 | 0.163 / 0.000 / 1.94 / 0.160 | **┃** | 0.295 / 0.295 / 3.78 / 0.280 | 0.203 / 0.000 / 2.56 / 0.171 |


### Climb streaks, 1-attempt / 2-attempt

An em dash means that attempt cap never applied.

| Edge | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | 3 / — | 2 / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | 2 / — | 2 / — | **┃** | 3 / — | 10 / 10 |


## 4a Burst

Burst mode was off on the six normal and TopFull-only holds. Those columns are an em dash.

On the four burst holds the cell is peak `burst_rpr5` / median `burst_rpr5` / samples at the bar in force / burst sheds (`burst_rpr5` samples), pasted from the scorer.

| Edge | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (602) | **┃** | 0.00 / 0.00 / 0 / 0 (537) | 0.00 / 0.00 / 0 / 0 (532) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (536) | 0.00 / 0.00 / 0 / 0 (531) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (536) | 0.00 / 0.00 / 0 / 0 (531) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (602) | **┃** | 0.00 / 0.00 / 0 / 0 (537) | 0.00 / 0.00 / 0 / 0 (532) |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (600) | 0.00 / 0.00 / 0 / 0 (603) | **┃** | 0.00 / 0.00 / 0 / 0 (539) | 0.00 / 0.00 / 0 / 0 (534) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (605) | **┃** | 0.00 / 0.00 / 0 / 0 (540) | 0.00 / 0.00 / 0 / 0 (535) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (605) | **┃** | 0.00 / 0.00 / 0 / 0 (539) | 0.00 / 0.00 / 0 / 0 (535) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.03 / 0.00 / 0 / 0 (597) | 0.16 / 0.00 / 0 / 0 (601) | **┃** | 0.05 / 0.00 / 0 / 0 (536) | 0.02 / 0.00 / 0 / 0 (531) |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (604) | **┃** | 0.00 / 0.00 / 0 / 0 (539) | 0.00 / 0.00 / 0 / 0 (535) |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (536) | 0.00 / 0.00 / 0 / 0 (531) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (602) | **┃** | 0.00 / 0.00 / 0 / 0 (537) | 0.00 / 0.00 / 0 / 0 (533) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 1.03 / 0.46 / 3 / 3 (358) | 1.27 / 0.48 / 0 / 0 (224) | **┃** | 1.72 / 0.42 / 1 / 1 (358) | 1.82 / 0.00 / 0 / 0 (450) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (603) | **┃** | 0.00 / 0.00 / 0 / 0 (538) | 0.00 / 0.00 / 0 / 0 (533) |


## Rejection beside (a)

Longest streak / count above 0.20. Bold when a controlled service's streak is at least 30. Frontend and redis-cart stay plain.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 3 / 81 | 3 / 37 | **┃** | 2 / 2 | 3 / 4 | **┃** | 2 / 2 | 6 / 30 | **┃** | 27 / 265 | 32 / 274 | **┃** | 39 / 206 | 9 / 47 |
| checkoutservice | 1 / 1 | 1 / 1 | **┃** | 7 / 20 | 1 / 1 | **┃** | 0 / 0 | 2 / 3 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 1 / 1 |
| recommendationservice | **112 / 518** | **93 / 499** | **┃** | 7 / 70 | 10 / 147 | **┃** | 8 / 140 | **278 / 371** | **┃** | **104 / 385** | **76 / 390** | **┃** | **184 / 369** | **39 / 153** |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 1 / 1 | **┃** | 4 / 10 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


Longest streak / count under the re-enable bar.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 178 / 604 | 184 / 604 | **┃** | 607 / 607 | 312 / 549 | **┃** | 113 / 484 | 56 / 310 | **┃** | 105 / 467 | 56 / 462 | **┃** | 106 / 435 | 325 / 512 |
| checkoutservice | 611 / 611 | 610 / 610 | **┃** | 324 / 588 | 356 / 549 | **┃** | 368 / 514 | 334 / 553 | **┃** | 611 / 611 | 611 / 611 | **┃** | 548 / 548 | 539 / 539 |
| recommendationservice | 58 / 109 | 78 / 142 | **┃** | 88 / 541 | 59 / 416 | **┃** | 69 / 359 | 53 / 176 | **┃** | 57 / 273 | 53 / 330 | **┃** | 51 / 208 | 201 / 395 |
| paymentservice | 612 / 612 | 611 / 611 | **┃** | 607 / 607 | 550 / 550 | **┃** | 515 / 515 | 557 / 557 | **┃** | 612 / 612 | 612 / 612 | **┃** | 548 / 548 | 540 / 540 |
| emailservice | 611 / 611 | 611 / 611 | **┃** | 327 / 598 | 550 / 550 | **┃** | 368 / 515 | 334 / 554 | **┃** | 611 / 611 | 585 / 610 | **┃** | 467 / 548 | 539 / 539 |
| productcatalogservice | 613 / 613 | 612 / 612 | **┃** | 608 / 608 | 551 / 551 | **┃** | 517 / 517 | 558 / 558 | **┃** | 613 / 613 | 613 / 613 | **┃** | 549 / 549 | 541 / 541 |
| cartservice | 613 / 613 | 612 / 612 | **┃** | 608 / 608 | 551 / 551 | **┃** | 517 / 517 | 558 / 558 | **┃** | 613 / 613 | 613 / 613 | **┃** | 549 / 549 | 541 / 541 |
| currencyservice | 612 / 612 | 612 / 612 | **┃** | 607 / 607 | 551 / 551 | **┃** | 517 / 517 | 557 / 557 | **┃** | 613 / 613 | 613 / 613 | **┃** | 550 / 550 | 540 / 540 |
| shippingservice | 612 / 612 | 612 / 612 | **┃** | 607 / 607 | 551 / 551 | **┃** | 517 / 517 | 557 / 557 | **┃** | 613 / 613 | 612 / 613 | **┃** | 550 / 550 | 540 / 540 |
| adservice | 610 / 610 | 611 / 611 | **┃** | 606 / 606 | 550 / 550 | **┃** | 516 / 516 | 556 / 556 | **┃** | 611 / 611 | 611 / 611 | **┃** | 549 / 549 | 539 / 539 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 1 / 7 | 1 / 2 | **┃** | 1 / 1 | 1 / 2 | **┃** | 1 / 1 | 1 / 11 | **┃** | 8 / 57 | 4 / 35 | **┃** | 10 / 53 | 3 / 12 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 611 / 611 | 611 / 611 | **┃** | 607 / 607 | 551 / 551 | **┃** | 70 / 430 | 55 / 251 | **┃** | 293 / 609 | 315 / 607 | **┃** | 178 / 527 | 540 / 540 |
| productcatalogservice | 613 / 613 | 612 / 612 | **┃** | 608 / 608 | 551 / 551 | **┃** | 517 / 517 | 558 / 558 | **┃** | 613 / 613 | 613 / 613 | **┃** | 549 / 549 | 541 / 541 |
| currencyservice | 612 / 612 | 612 / 612 | **┃** | 607 / 607 | 551 / 551 | **┃** | 517 / 517 | 557 / 557 | **┃** | 613 / 613 | 613 / 613 | **┃** | 550 / 550 | 540 / 540 |
| adservice | 611 / 611 | 611 / 611 | **┃** | 606 / 606 | 550 / 550 | **┃** | 516 / 516 | 556 / 556 | **┃** | 611 / 611 | 611 / 611 | **┃** | 549 / 549 | 539 / 539 |


gRPC counted in the rejection rate on the four read callees and in the retry policy. Cell is grpc_4 / grpc_14.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 94,317 / 0 | 90,575 / 0 | **┃** | 14,012 / 0 | 35,193 / 0 | **┃** | 35,475 / 0 | 105,725 / 0 | **┃** | 91,094 / 0 | 72,472 / 0 | **┃** | 84,492 / 0 | 39,922 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 1 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


## (b) Detector overloaded fraction

Bold when the share is at least 0.5.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| checkoutservice | **581/716 (81.1%)** | **580/716 (81.0%)** | **┃** | **493/715 (69.0%)** | **438/716 (61.2%)** | **┃** | **452/693 (65.2%)** | **406/692 (58.7%)** | **┃** | **558/713 (78.3%)** | **556/714 (77.9%)** | **┃** | **443/716 (61.9%)** | **377/716 (52.7%)** |
| recommendationservice | 4/716 (0.6%) | 1/716 (0.1%) | **┃** | 2/715 (0.3%) | 15/716 (2.1%) | **┃** | 21/693 (3.0%) | 101/692 (14.6%) | **┃** | 41/713 (5.8%) | 36/714 (5.0%) | **┃** | 75/716 (10.5%) | 65/716 (9.1%) |
| paymentservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| emailservice | 266/716 (37.2%) | 263/716 (36.7%) | **┃** | **367/715 (51.3%)** | 263/716 (36.7%) | **┃** | 250/693 (36.1%) | 93/692 (13.4%) | **┃** | 299/713 (41.9%) | 311/714 (43.6%) | **┃** | 119/716 (16.6%) | 20/716 (2.8%) |
| productcatalogservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| cartservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| currencyservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| shippingservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| adservice | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |
| redis-cart | 0/716 (0.0%) | 0/716 (0.0%) | **┃** | 0/715 (0.0%) | 0/716 (0.0%) | **┃** | 0/693 (0.0%) | 0/692 (0.0%) | **┃** | 0/713 (0.0%) | 0/714 (0.0%) | **┃** | 0/716 (0.0%) | 0/716 (0.0%) |


## (c) Retry volume

Outbound retry delta by target.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 38 | 84 | **┃** | 1,993 | 258 | **┃** | 99 | 301 | **┃** | 64 | 107 | **┃** | 103 | 10 |
| recommendationservice | 90,332 | 87,964 | **┃** | 17,142 | 41,840 | **┃** | 43,295 | 120,494 | **┃** | 70,868 | 42,880 | **┃** | 70,319 | 40,496 |
| cartservice | 4 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | — | — | — | — | — |


Inbound resets for all 11 services.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 335 | 323 | **┃** | 134 | 29 | **┃** | 370 | 368 | **┃** | 243 | 319 | **┃** | 334 | 279 |
| checkoutservice | 44 | 66 | **┃** | 1,348 | 146 | **┃** | 59 | 208 | **┃** | 61 | 97 | **┃** | 61 | 10 |
| recommendationservice | 37,542 | 32,804 | **┃** | 4,257 | 10,853 | **┃** | 12,159 | 35,099 | **┃** | 39,691 | 32,949 | **┃** | 39,548 | 14,273 |
| paymentservice | 0 | 0 | **┃** | 48 | 0 | **┃** | 0 | 11 | **┃** | 0 | 1 | **┃** | 1 | 0 |
| emailservice | 50 | 87 | **┃** | 347 | 99 | **┃** | 66 | 24 | **┃** | 65 | 82 | **┃** | 108 | 9 |
| productcatalogservice | 0 | 9 | **┃** | 10 | 8 | **┃** | 4 | 5 | **┃** | 6 | 5 | **┃** | 10 | 4 |
| cartservice | 4 | 0 | **┃** | 103 | 4 | **┃** | 0 | 13 | **┃** | 2 | 1 | **┃** | 0 | 2 |
| currencyservice | 4 | 1 | **┃** | 12 | 3 | **┃** | 1 | 4 | **┃** | 0 | 1 | **┃** | 0 | 0 |
| shippingservice | 0 | 1 | **┃** | 74 | 1 | **┃** | 0 | 13 | **┃** | 1 | 0 | **┃** | 0 | 0 |
| adservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 6 | 1 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |


## RetryGuard toggles

`ON→OFF` is a shed to 0. `0→1` is the re-enable off 0. `1→2` and `2→3` are climbs.

`final_s2_tf_only_run1` and `final_s2_tf_only_run2` have no `retryguard.log`.


### Part 1, per hold


### final_s2_rg_only_normal_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 |
| recommendationservice | 0 | 1 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T10:15:07Z | frontend → recommendationservice | ON→OFF | 3 | rpr 0.70 |
| 2026-10-14T10:15:31Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |


### final_s2_rg_only_normal_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 |
| recommendationservice | 0 | 1 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T10:34:22Z | frontend → recommendationservice | ON→OFF | 3 | rpr 0.68 |
| 2026-10-14T10:34:46Z | recommendationservice | OFF→ON | 0 | rejection 0.10 |

final_s2_both_normal_run1: no transition lines.
final_s2_both_normal_run2: no transition lines.
final_s2_tf_only_run1: no transition lines.
final_s2_tf_only_run2: no transition lines.


### final_s2_rg_only_burst_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 7 | 0 | 0 | 0 | 3 |
| recommendationservice | 0 | 6 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T12:21:48Z | frontend → recommendationservice | ON→OFF | 3 | rpr 0.84 |
| 2026-10-14T12:22:13Z | recommendationservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-14T12:22:49Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.44 |
| 2026-10-14T12:23:13Z | recommendationservice | OFF→ON | 0 | rejection 0.08 |
| 2026-10-14T12:24:04Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.54 |
| 2026-10-14T12:24:36Z | recommendationservice | OFF→ON | 0 | rejection 0.18 |
| 2026-10-14T12:25:13Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.61 |
| 2026-10-14T12:26:04Z | recommendationservice | OFF→ON | 0 | rejection 0.08 |
| 2026-10-14T12:27:44Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.67 |
| 2026-10-14T12:28:34Z | recommendationservice | OFF→ON | 0 | rejection 0.18 |
| 2026-10-14T12:29:28Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.68 |
| 2026-10-14T12:29:56Z | recommendationservice | OFF→ON | 0 | rejection 0.14 |
| 2026-10-14T12:30:05Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.68 |


### final_s2_rg_only_burst_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 4 | 0 | 0 | 0 |
| recommendationservice | 0 | 3 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T12:39:46Z | frontend → recommendationservice | ON→OFF | 3 | rpr 0.67 |
| 2026-10-14T12:43:31Z | recommendationservice | OFF→ON | 0 | rejection 0.18 |
| 2026-10-14T12:44:47Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.43 |
| 2026-10-14T12:45:56Z | recommendationservice | OFF→ON | 0 | rejection 0.21 |
| 2026-10-14T12:46:38Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.53 |
| 2026-10-14T12:47:29Z | recommendationservice | OFF→ON | 0 | rejection 0.15 |
| 2026-10-14T12:48:06Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.80 |


### final_s2_both_burst_run1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 3 | 0 | 0 | 0 | 1 |
| recommendationservice | 0 | 3 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T12:58:58Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.19 |
| 2026-10-14T12:59:53Z | recommendationservice | OFF→ON | 0 | rejection 0.13 |
| 2026-10-14T13:00:05Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.72 |
| 2026-10-14T13:01:24Z | recommendationservice | OFF→ON | 0 | rejection 0.12 |
| 2026-10-14T13:02:11Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.51 |
| 2026-10-14T13:03:19Z | recommendationservice | OFF→ON | 0 | rejection 0.23 |


### final_s2_both_burst_run2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 4 | 0 | 3 | 2 |
| recommendationservice | 0 | 4 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-14T13:15:48Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.57 |
| 2026-10-14T13:16:17Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-14T13:16:28Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-14T13:16:50Z | frontend → recommendationservice | ON→OFF | 2 | rpr 0.57 |
| 2026-10-14T13:17:14Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-14T13:17:25Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-14T13:17:36Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-14T13:21:04Z | frontend → recommendationservice | ON→OFF | 3 | rpr 0.46 |
| 2026-10-14T13:21:28Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-14T13:21:40Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-14T13:21:51Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-14T13:23:14Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.20 |
| 2026-10-14T13:23:38Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |


### Part 2, per edge that sheds

`ON→OFF / OFF→ON` counts the edge's sheds and the callee's re-enables. A parenthetical is the burst-shed count. Shed rpr values are in time order; `b` marks `metric=rpr_burst`. First shed is seconds after the first `OBSERVE` line. Attempts after re-enable is the edge's attempt count on its last log line. Time OFF is seconds from each shed to the next callee `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is the min and median of `metric=rejection` samples for that callee inside each OFF window. The streak counts those samples strictly below 0.25. An em dash on a detail row means that edge did not go to 0 on that hold. TopFull-only columns are an em dash because there is no `retryguard.log`.


#### frontend → recommendationservice

| frontend → recommendationservice | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | — | — | **┃** | 7 (3) / 6 | 4 / 3 | **┃** | 3 (1) / 3 | 4 / 4 |
| Shed rpr | 0.70 | 0.68 | **┃** | — | — | **┃** | — | — | **┃** | 0.84; 0.44; 0.54; 0.61; 0.67b; 0.68b; 0.68b | 0.67; 0.43; 0.53; 0.80 | **┃** | 1.19; 0.72b; 0.51 | 1.57; 0.57; 0.46; 1.20 |
| First shed, seconds after first OBSERVE | 79 | 151 | **┃** | — | — | **┃** | — | — | **┃** | 75 | 73 | **┃** | 142 | 69 |
| Attempts after re-enable | 1 | 1 | **┃** | — | — | **┃** | — | — | **┃** | 0 | 0 | **┃** | 1 | 1 |
| Time OFF (s) | 24 | 24 | **┃** | — | — | **┃** | — | — | **┃** | 25; 24; 32; 51; 50; 28; 41 | 225; 69; 51; 41 | **┃** | 55; 79; 68 | 29; 24; 24; 24 |
| OFF rejection min / median | 0.000 / 0.039 | 0.000 / 0.092 | **┃** | — | — | **┃** | — | — | **┃** | 0.051 / 0.127; 0.000 / 0.127; 0.037 / 0.182; 0.035 / 0.156; 0.098 / 0.175; 0.099 / 0.190; 0.144 / 0.224 | 0.095 / 0.229; 0.095 / 0.171; 0.072 / 0.184; 0.135 / 0.211 | **┃** | 0.067 / 0.164; 0.030 / 0.229; 0.041 / 0.193 | 0.000 / 0.125; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.037 |
| Longest streak under 0.25 | 20 | 20 | **┃** | — | — | **┃** | — | — | **┃** | 20; 20; 19; 20; 16; 20; 7 | 20; 20; 19; 8 | **┃** | 15; 19; 20 | 15; 18; 17; 16 |

Re-enabled and the last edge line is `final_s2_rg_only_normal_run1` ended at 1 attempts; `final_s2_rg_only_normal_run2` ended at 1 attempts; `final_s2_both_burst_run1` ended at 1 attempts; `final_s2_both_burst_run2` ended at 1 attempts. Still at 0 at exit: `final_s2_rg_only_burst_run1` ended at 0; `final_s2_rg_only_burst_run2` ended at 0. No shed on `final_s2_both_normal_run1`, `final_s2_both_normal_run2`.


## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.

| API | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 173.3 | 178.8 | **┃** | 250.3 | 226.4 | **┃** | 221.4 | 171.3 | **┃** | 169.8 | 182.4 | **┃** | 166.8 | 224.4 |
| postcheckout | 54.6 | 55.8 | **┃** | 65.8 | 54.7 | **┃** | 54.5 | 38.2 | **┃** | 56.9 | 59.3 | **┃** | 46.1 | 37.1 |
| getcart | 67.3 | 69.0 | **┃** | 91.0 | 83.1 | **┃** | 81.7 | 63.4 | **┃** | 66.4 | 69.0 | **┃** | 66.8 | 82.6 |
| postcart | 86.4 | 86.4 | **┃** | 86.2 | 86.3 | **┃** | 86.3 | 86.4 | **┃** | 86.3 | 86.4 | **┃** | 86.3 | 86.3 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |


## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.

| API | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.313 | 0.287 | **┃** | 0.037 | 0.107 | **┃** | 0.123 | 0.259 | **┃** | 0.328 | 0.286 | **┃** | 0.333 | 0.123 |
| postcheckout | 0.328 | 0.307 | **┃** | 0.202 | 0.306 | **┃** | 0.311 | 0.444 | **┃** | 0.310 | 0.289 | **┃** | 0.429 | 0.539 |
| getcart | 0.275 | 0.249 | **┃** | 0.037 | 0.098 | **┃** | 0.111 | 0.243 | **┃** | 0.283 | 0.261 | **┃** | 0.273 | 0.114 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |


## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.

| API | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 1040 | 1116 | **┃** | 590 | 851 | **┃** | 823 | 1506 | **┃** | 887 | 782 | **┃** | 923 | 704 |
| postcheckout | 1189 | 1254 | **┃** | 851 | 962 | **┃** | 931 | 1522 | **┃** | 1065 | 966 | **┃** | 1010 | 696 |
| getcart | 1030 | 1091 | **┃** | 534 | 783 | **┃** | 777 | 1435 | **┃** | 856 | 754 | **┃** | 887 | 672 |
| postcart | 72 | 71 | **┃** | 72 | 72 | **┃** | 72 | 71 | **┃** | 73 | 75 | **┃** | 74 | 74 |
| emptycart | 16 | 16 | **┃** | 15 | 13 | **┃** | 16 | 15 | **┃** | 15 | 19 | **┃** | 21 | 14 |


## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 483.3 | 479.2 | **┃** | 474.8 | 451.2 | **┃** | 465.4 | 434.3 | **┃** | 484.8 | 487.4 | **┃** | 460.5 | 440.2 |
| checkoutservice | 61.7 | 62.7 | **┃** | 67.6 | 55.8 | **┃** | 57.5 | 47.7 | **┃** | 59.0 | 58.4 | **┃** | 47.9 | 36.0 |
| recommendationservice | 535.2 | 527.5 | **┃** | 416.7 | 430.2 | **┃** | 445.9 | 535.1 | **┃** | 507.4 | 467.9 | **┃** | 482.3 | 417.2 |
| paymentservice | 61.7 | 62.7 | **┃** | 67.5 | 55.8 | **┃** | 57.5 | 47.7 | **┃** | 59.0 | 58.4 | **┃** | 47.9 | 36.0 |
| emailservice | 61.7 | 62.7 | **┃** | 64.6 | 55.7 | **┃** | 57.5 | 47.2 | **┃** | 59.0 | 58.4 | **┃** | 47.9 | 36.0 |
| productcatalogservice | 2429.9 | 2453.3 | **┃** | 2667.6 | 2507.1 | **┃** | 2581.4 | 2276.7 | **┃** | 2263.0 | 2249.1 | **┃** | 2166.6 | 2363.3 |
| cartservice | 530.6 | 529.5 | **┃** | 542.8 | 505.7 | **┃** | 521.3 | 474.7 | **┃** | 525.6 | 526.5 | **┃** | 496.3 | 473.8 |
| currencyservice | 756.4 | 754.4 | **┃** | 782.4 | 730.5 | **┃** | 751.7 | 672.8 | **┃** | 746.3 | 747.8 | **┃** | 712.4 | 702.9 |
| shippingservice | 196.7 | 199.9 | **┃** | 220.7 | 193.0 | **┃** | 199.0 | 165.9 | **┃** | 185.9 | 183.9 | **┃** | 164.0 | 151.9 |
| adservice | 200.3 | 203.3 | **┃** | 237.7 | 223.7 | **┃** | 229.5 | 196.5 | **┃** | 182.0 | 181.4 | **┃** | 178.1 | 219.3 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |


## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 597 | 590 | **┃** | 328 | 384 | **┃** | 381 | 588 | **┃** | 574 | 533 | **┃** | 553 | 360 |
| checkoutservice | 156 | 156 | **┃** | 230 | 171 | **┃** | 168 | 116 | **┃** | 177 | 172 | **┃** | 146 | 66 |
| recommendationservice | 446 | 440 | **┃** | 232 | 283 | **┃** | 279 | 386 | **┃** | 446 | 446 | **┃** | 427 | 266 |
| paymentservice | 3 | 3 | **┃** | 3 | 3 | **┃** | 2 | 2 | **┃** | 3 | 3 | **┃** | 2 | 2 |
| emailservice | 21 | 22 | **┃** | 36 | 26 | **┃** | 25 | 14 | **┃** | 27 | 25 | **┃** | 18 | 6 |
| productcatalogservice | 4 | 4 | **┃** | 4 | 4 | **┃** | 4 | 4 | **┃** | 4 | 4 | **┃** | 4 | 4 |
| cartservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 3 | 3 | **┃** | 3 | 3 |
| currencyservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 3 | 3 | **┃** | 3 | 2 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |


## Share of inbound requests above 500 ms

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.748 | 0.727 | **┃** | 0.242 | 0.327 | **┃** | 0.330 | 0.529 | **┃** | 0.756 | 0.773 | **┃** | 0.705 | 0.306 |
| checkoutservice | 0.001 | 0.002 | **┃** | 0.032 | 0.005 | **┃** | 0.002 | 0.007 | **┃** | 0.002 | 0.002 | **┃** | 0.002 | 0.000 |
| recommendationservice | 0.362 | 0.351 | **┃** | 0.069 | 0.159 | **┃** | 0.163 | 0.384 | **┃** | 0.372 | 0.349 | **┃** | 0.360 | 0.177 |
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

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1108 / 1473 | 1150 / 4 / 1087 / 1476 | **┃** | 1150 / 4 / 1121 / 1472 | 1150 / 4 / 1115 / 1491 | **┃** | 1150 / 4 / 1151 / 1490 | 1150 / 4 / 1116 / 1526 | **┃** | 1150 / 4 / 1130 / 1501 | 1150 / 4 / 1160 / 1528 | **┃** | 1150 / 4 / 1133 / 1552 | 1150 / 4 / 1158 / 1539 |
| checkoutservice | 800 / 1 / 596 / 799 | 800 / 1 / 596 / 797 | **┃** | 800 / 1 / 579 / 798 | 800 / 1 / 557 / 797 | **┃** | 800 / 1 / 574 / 798 | 800 / 1 / 545 / 782 | **┃** | 800 / 1 / 592 / 797 | 800 / 1 / 601 / 800 | **┃** | 800 / 1 / 540 / 781 | 800 / 1 / 504 / 776 |
| recommendationservice | 1150 / 1 / 637 / 866 | 1150 / 1 / 622 / 864 | **┃** | 1150 / 1 / 544 / 822 | 1150 / 1 / 566 / 842 | **┃** | 1150 / 1 / 588 / 871 | 1150 / 1 / 667 / 952 | **┃** | 1150 / 1 / 642 / 929 | 1150 / 1 / 641 / 938 | **┃** | 1150 / 1 / 645 / 990 | 1150 / 1 / 605 / 1015 |
| paymentservice | 155 / 1 / 42 / 80 | 155 / 1 / 40 / 58 | **┃** | 155 / 1 / 41 / 72 | 155 / 1 / 37 / 60 | **┃** | 155 / 1 / 38 / 60 | 155 / 1 / 35 / 57 | **┃** | 155 / 1 / 40 / 62 | 155 / 1 / 41 / 60 | **┃** | 155 / 1 / 35 / 55 | 155 / 1 / 31 / 61 |
| emailservice | 120 / 1 / 77 / 109 | 120 / 1 / 77 / 112 | **┃** | 120 / 1 / 76 / 113 | 120 / 1 / 71 / 112 | **┃** | 120 / 1 / 73 / 112 | 120 / 1 / 67 / 108 | **┃** | 120 / 1 / 77 / 111 | 120 / 1 / 78 / 108 | **┃** | 120 / 1 / 68 / 106 | 120 / 1 / 58 / 109 |
| productcatalogservice | 800 / 1 / 319 / 424 | 800 / 1 / 315 / 417 | **┃** | 800 / 1 / 317 / 435 | 800 / 1 / 320 / 422 | **┃** | 800 / 1 / 331 / 430 | 800 / 1 / 328 / 441 | **┃** | 800 / 1 / 315 / 429 | 800 / 1 / 316 / 424 | **┃** | 800 / 1 / 316 / 454 | 800 / 1 / 319 / 414 |
| cartservice | 800 / 1 / 282 / 382 | 800 / 1 / 291 / 489 | **┃** | 800 / 1 / 275 / 378 | 800 / 1 / 281 / 378 | **┃** | 800 / 1 / 291 / 384 | 800 / 1 / 293 / 396 | **┃** | 800 / 1 / 285 / 395 | 800 / 1 / 306 / 477 | **┃** | 800 / 1 / 292 / 424 | 800 / 1 / 311 / 535 |
| currencyservice | 770 / 1 / 301 / 406 | 770 / 1 / 296 / 401 | **┃** | 770 / 1 / 303 / 407 | 770 / 1 / 300 / 414 | **┃** | 770 / 1 / 307 / 418 | 770 / 1 / 298 / 407 | **┃** | 770 / 1 / 307 / 420 | 770 / 1 / 314 / 425 | **┃** | 770 / 1 / 306 / 443 | 770 / 1 / 306 / 419 |
| shippingservice | 770 / 1 / 81 / 113 | 770 / 1 / 80 / 115 | **┃** | 770 / 1 / 84 / 118 | 770 / 1 / 82 / 116 | **┃** | 770 / 1 / 84 / 118 | 770 / 1 / 78 / 110 | **┃** | 770 / 1 / 81 / 112 | 770 / 1 / 82 / 113 | **┃** | 770 / 1 / 77 / 113 | 770 / 1 / 78 / 108 |
| adservice | 1150 / 1 / 122 / 353 | 1150 / 1 / 102 / 141 | **┃** | 1150 / 1 / 112 / 150 | 1150 / 1 / 112 / 153 | **┃** | 1150 / 1 / 114 / 157 | 1150 / 1 / 110 / 163 | **┃** | 1150 / 1 / 102 / 142 | 1150 / 1 / 105 / 139 | **┃** | 1150 / 1 / 104 / 165 | 1150 / 1 / 122 / 180 |
| redis-cart | 540 / 1 / 35 / 59 | 540 / 1 / 35 / 59 | **┃** | 540 / 1 / 34 / 57 | 540 / 1 / 35 / 60 | **┃** | 540 / 1 / 36 / 59 | 540 / 1 / 38 / 61 | **┃** | 540 / 1 / 37 / 64 | 540 / 1 / 38 / 63 | **┃** | 540 / 1 / 37 / 63 | 540 / 1 / 37 / 63 |


## Detector max utilization

| Service | final_s2_rg_only_normal_run1 | final_s2_rg_only_normal_run2 | **┃** | final_s2_both_normal_run1 | final_s2_both_normal_run2 | **┃** | final_s2_tf_only_run1 | final_s2_tf_only_run2 | **┃** | final_s2_rg_only_burst_run1 | final_s2_rg_only_burst_run2 | **┃** | final_s2_both_burst_run1 | final_s2_both_burst_run2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.326 | 0.327 | **┃** | 0.338 | 0.351 | **┃** | 0.351 | 0.349 | **┃** | 0.335 | 0.346 | **┃** | 0.350 | 0.350 |
| checkoutservice | 1.058 | 1.046 | **┃** | 1.075 | 1.040 | **┃** | 1.040 | 1.038 | **┃** | 1.052 | 1.036 | **┃** | 1.012 | 1.006 |
| recommendationservice | 0.835 | 0.811 | **┃** | 0.824 | 0.920 | **┃** | 0.885 | 0.910 | **┃** | 0.862 | 0.958 | **┃** | 0.981 | 0.955 |
| paymentservice | 0.639 | 0.510 | **┃** | 0.671 | 0.594 | **┃** | 0.542 | 0.581 | **┃** | 0.548 | 0.581 | **┃** | 0.516 | 0.497 |
| emailservice | 1.017 | 1.042 | **┃** | 1.025 | 1.042 | **┃** | 1.025 | 0.992 | **┃** | 1.000 | 1.000 | **┃** | 1.050 | 0.967 |
| productcatalogservice | 0.549 | 0.549 | **┃** | 0.564 | 0.576 | **┃** | 0.603 | 0.613 | **┃** | 0.557 | 0.557 | **┃** | 0.609 | 0.583 |
| cartservice | 0.545 | 0.631 | **┃** | 0.510 | 0.511 | **┃** | 0.515 | 0.551 | **┃** | 0.549 | 0.640 | **┃** | 0.576 | 0.700 |
| currencyservice | 0.582 | 0.569 | **┃** | 0.566 | 0.582 | **┃** | 0.605 | 0.596 | **┃** | 0.581 | 0.605 | **┃** | 0.666 | 0.612 |
| shippingservice | 0.166 | 0.168 | **┃** | 0.186 | 0.183 | **┃** | 0.175 | 0.170 | **┃** | 0.182 | 0.179 | **┃** | 0.174 | 0.175 |
| adservice | 0.582 | 0.147 | **┃** | 0.145 | 0.216 | **┃** | 0.151 | 0.160 | **┃** | 0.134 | 0.148 | **┃** | 0.149 | 0.211 |
| redis-cart | 0.367 | 0.370 | **┃** | 0.352 | 0.370 | **┃** | 0.313 | 0.396 | **┃** | 0.396 | 0.331 | **┃** | 0.365 | 0.304 |


## Throttle data quality

`final_s2_tf_only_run2` is FLAG: 110 fetch warnings, first 12:08:35, longest no-fresh threshold 280 s and admitted 280 s. TopFull was on, so its cap and admitted-rate numbers are carried, not measured.

`final_s2_rg_only_burst_run2` is FLAG: 16 fetch warnings, first 12:48:05, longest no-fresh threshold 45 s and admitted 45 s. TopFull was off, so there is no live cap to lose.

`final_s2_both_burst_run1` is FLAG: 196 fetch warnings, first 12:58:40, longest no-fresh threshold 494 s and admitted 494 s. TopFull was on, so its cap and admitted-rate numbers are carried, not measured.

`final_s2_both_burst_run2` is FLAG: 224 fetch warnings, first 13:15:30, longest no-fresh threshold 565 s and admitted 565 s. TopFull was on, so its cap and admitted-rate numbers are carried, not measured.

The other six holds are throttle clean. Goodput, P95, rejection, and retry numbers do not use this file.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| final_s2_rg_only_normal_run1 | ok | 0 | — | 5 | 5 |
| final_s2_rg_only_normal_run2 | ok | 0 | — | 5 | 5 |
| final_s2_both_normal_run1 | ok | 0 | — | 5 | 5 |
| final_s2_both_normal_run2 | ok | 0 | — | 5 | 5 |
| final_s2_tf_only_run1 | ok | 0 | — | 5 | 5 |
| final_s2_tf_only_run2 | **FLAGGED** | 110 | 12:08:35 | 280 | 280 |
| final_s2_rg_only_burst_run1 | ok | 0 | — | 5 | 5 |
| final_s2_rg_only_burst_run2 | **FLAGGED** | 16 | 12:48:05 | 45 | 45 |
| final_s2_both_burst_run1 | **FLAGGED** | 196 | 12:58:40 | 494 | 494 |
| final_s2_both_burst_run2 | **FLAGGED** | 224 | 13:15:30 | 565 | 565 |


## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. On the four FLAG holds above, these spans are carried values. `postcart` and `emptycart` are no cap on every live read in all ten holds.


### final_s2_rg_only_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:12:05–10:24:00 |
| postcheckout | no cap 10:12:05–10:24:00 |
| getcart | no cap 10:12:05–10:24:00 |
| postcart | no cap 10:12:05–10:24:00 |
| emptycart | no cap 10:12:05–10:24:00 |


### final_s2_rg_only_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:30:10–10:42:00 |
| postcheckout | no cap 10:30:10–10:42:00 |
| getcart | no cap 10:30:10–10:42:00 |
| postcart | no cap 10:30:10–10:42:00 |
| emptycart | no cap 10:30:10–10:42:00 |


### final_s2_both_normal_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:48:10–10:51:10; 223.4 at 10:51:15; no cap 10:51:20–11:00:00 |
| postcheckout | no cap 10:48:10–10:50:20; 56 at 10:50:25; 66 at 10:50:30; no cap at 10:50:35; 84 at 10:50:40; no cap 10:50:45–10:50:50; 90 10:50:55–10:51:01; no cap at 10:51:05; 51.6 at 10:51:10; 34.8 at 10:51:15; 71.3 at 10:51:20; 78.2 at 10:51:25; 71.3 at 10:51:30; 81.4046 at 10:51:34; 81.4 at 10:51:35; 80.6 at 10:51:40; 72.1 at 10:51:45; 76.493 at 10:51:49; 76.5 at 10:51:50; 21.3782 at 10:51:53; 13.3 at 10:51:55; 14.1409 at 10:51:57; 26.9 at 10:52:00; 67 at 10:52:05; 90 at 10:52:10; no cap at 10:52:13; 90 at 10:52:15; no cap 10:52:20–10:52:25; 36 at 10:52:30; 26.5 at 10:52:35; 77.9 at 10:52:40; 92.8154 at 10:52:42; no cap at 10:52:45; 35.8 at 10:52:50; 10.2 at 10:52:55; 27.4 at 10:53:00; 83.4 at 10:53:05; no cap at 10:53:10; 89 at 10:53:15; 77.9811 at 10:53:18; 86.5 at 10:53:20; 81.8 at 10:53:25; 24.6 at 10:53:30; 46.4 at 10:53:35; 99 at 10:53:40; 90 at 10:53:45; no cap at 10:53:46; 90 10:53:50–10:53:55; no cap at 10:54:00; 61.8 at 10:54:05; 23.8 at 10:54:10; 74.8138 at 10:54:14; 74.8 at 10:54:15; no cap at 10:54:18; 90 at 10:54:20; no cap 10:54:22–10:54:25; 90 at 10:54:30; no cap at 10:54:33; 90 at 10:54:35; no cap 10:54:40–10:54:45; 90 10:54:47–10:54:55; no cap at 10:55:00; 52.3 at 10:55:05; 26.2 at 10:55:10; 46.6135 at 10:55:12; 80.2 at 10:55:15; 96.6 at 10:55:20; 90 at 10:55:23; no cap 10:55:25–10:55:29; 90 at 10:55:30; no cap at 10:55:33; 90 at 10:55:35; no cap at 10:55:40; 33.6 at 10:55:45; 22.5 at 10:55:50; 66.21 at 10:55:54; 66.2 at 10:55:55; 90 10:56:00–10:56:01; no cap 10:56:05–10:56:11; 90 10:56:15–10:56:20; 52.0662 at 10:56:22; 25.6 at 10:56:25; 20.6236 at 10:56:26; 29.5 at 10:56:30; 99 at 10:56:34; 99 at 10:56:35; 90 10:56:40–10:56:45; no cap 10:56:47–10:56:50; 90 at 10:56:55; no cap at 10:56:58; 90 at 10:57:00; no cap 10:57:05–10:57:10; 86 at 10:57:15; 34.2338 at 10:57:17; 25.3 at 10:57:20; 32.0779 at 10:57:21; 59.8 at 10:57:25; no cap 10:57:30–10:57:35; 90 10:57:40–10:57:45; 57.2 at 10:57:50; 26 at 10:57:55; 54.5 at 10:58:00; no cap at 10:58:05; 90 10:58:10–10:58:11; no cap 10:58:15–10:58:20; 81 at 10:58:22; 31.3 at 10:58:25; 19.5814 at 10:58:26; 10 at 10:58:30; 37.6 at 10:58:35; 89.0991 at 10:58:38; 99 at 10:58:40; 90 10:58:45–10:58:55; no cap at 10:59:00; 90 10:59:05–10:59:11; no cap 10:59:15–10:59:20; 86 at 10:59:22; 38.7 at 10:59:25; 25.4847 at 10:59:26; 24.7 at 10:59:30; 76.9 at 10:59:35; no cap 10:59:40–10:59:45; 90 at 10:59:50; 89 at 10:59:55; 28.8 at 11:00:00 |
| getcart | no cap 10:48:10–10:51:10; 82.9 at 10:51:15; no cap 10:51:20–11:00:00 |
| postcart | no cap 10:48:10–11:00:00 |
| emptycart | no cap 10:48:10–11:00:00 |


### final_s2_both_normal_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 11:14:20–11:17:25; 236.358 at 11:17:28; 236.4 at 11:17:30; 178.7 at 11:17:35; 302.5 at 11:17:40; no cap 11:17:45–11:19:30; 250 at 11:19:32; 239.7 at 11:19:35; 152.707 at 11:19:39; 152.7 at 11:19:40; 101.715 at 11:19:41; 131.7 at 11:19:45; 260.437 at 11:19:48; 260.4 at 11:19:50; no cap 11:19:55–11:20:00; 240 at 11:20:05; 157.4 at 11:20:10; 302.5 11:20:14–11:20:15; no cap 11:20:20–11:20:25; 199.269 at 11:20:28; 171.8 at 11:20:30; 228.078 at 11:20:31; 302.5 at 11:20:35; no cap 11:20:40–11:22:25; 236.8 at 11:22:30; 150.8 at 11:22:35; 101.878 at 11:22:37; 144.3 at 11:22:40; 302.5 at 11:22:45; no cap 11:22:50–11:26:10 |
| postcheckout | no cap 11:14:20–11:16:30; 62 at 11:16:35; 68 at 11:16:40; 86.9 at 11:16:45; 91.1 at 11:16:50; 90 at 11:16:55; 87 at 11:16:58; no cap at 11:17:00; 26.5 at 11:17:05; 20.0696 at 11:17:07; 25.6 at 11:17:10; 74.8 at 11:17:15; no cap at 11:17:18; 90 at 11:17:20; no cap at 11:17:25; 53.4965 at 11:17:28; 33.2 at 11:17:30; 33.2387 at 11:17:33; 38.2 at 11:17:35; 66.2843 at 11:17:38; 66.3 at 11:17:40; 90 at 11:17:45; 70.4219 at 11:17:47; 71.3 at 11:17:50; 27.1 at 11:17:55; 60.4 at 11:18:00; 99 at 11:18:05; no cap at 11:18:10; 55.3508 at 11:18:14; 55.4 at 11:18:15; 16.5 at 11:18:20; 38.2 at 11:18:25; 99 at 11:18:30; 90 at 11:18:31; no cap 11:18:35–11:18:40; 24.3 at 11:18:45; 34.4 at 11:18:50; 82.9 at 11:18:55; no cap at 11:19:00; 91.8182 at 11:19:04; 91.8 at 11:19:05; 36.9 at 11:19:10; 25.2 at 11:19:15; 73.6 at 11:19:20; no cap at 11:19:25; 90 at 11:19:30; no cap at 11:19:31; 70.7 at 11:19:35; 45 at 11:19:40; 20.7711 at 11:19:42; 21.3 at 11:19:45; 58.5 at 11:19:50; 99 at 11:19:55; 90 at 11:19:57; 88 at 11:20:00; 34.8 at 11:20:05; 27.1 at 11:20:10; 73.6 at 11:20:15; 87 at 11:20:20; 72.2515 at 11:20:22; 47.8 at 11:20:25; 26.3 at 11:20:30; 56.3 at 11:20:35; 93.9348 at 11:20:37; 98.7 at 11:20:40; 90 at 11:20:45; 32.2 at 11:20:50; 22.3 at 11:20:55; 56.9 at 11:21:00; no cap at 11:21:05; 90 at 11:21:10; 35.1 at 11:21:15; 19.2777 at 11:21:19; 19.3 at 11:21:20; 67.3 at 11:21:25; 99 at 11:21:30; 90 at 11:21:35; 34.8 at 11:21:40; 19.3 at 11:21:45; 51.6679 at 11:21:48; 71 at 11:21:50; no cap 11:21:55–11:22:00; 50.1 at 11:22:05; 22.4077 at 11:22:08; 17 at 11:22:10; 41.7 at 11:22:15; 99 at 11:22:20; no cap at 11:22:25; 71.8 11:22:30–11:22:35; 23.2 at 11:22:40; 31.1 at 11:22:45; 88.7 at 11:22:50; 91.1 at 11:22:55; no cap at 11:23:00; 72.4 at 11:23:05; 27 at 11:23:10; 58.5 at 11:23:15; no cap 11:23:20–11:23:25; 54.2 at 11:23:30; 20.8016 at 11:23:33; 14.5 at 11:23:35; 35.1 at 11:23:40; 99 at 11:23:45; no cap 11:23:50–11:23:55; 90 11:23:57–11:24:00; 89 11:24:05–11:24:06; 49.6 at 11:24:10; 31.4914 at 11:24:11; 25.6 at 11:24:15; 58.9439 at 11:24:18; 80 at 11:24:20; no cap 11:24:25–11:24:26; 90 11:24:30–11:24:35; 35.2 at 11:24:40; 23.6 at 11:24:45; 44.8978 at 11:24:47; 60.1 at 11:24:50; 90 11:24:55–11:25:00; no cap at 11:25:05; 25.4 at 11:25:10; 21.1 at 11:25:15; 73.2 at 11:25:20; 90 11:25:24–11:25:30; 61.7 at 11:25:35; 24.3 at 11:25:40; 73.3412 at 11:25:44; 73.3 at 11:25:45; no cap at 11:25:48; 90 11:25:50–11:25:55; no cap 11:25:57–11:26:00; 28.2 at 11:26:05; 21.2829 at 11:26:07; 27.3 at 11:26:10 |
| getcart | no cap 11:14:20–11:17:25; 82.3584 at 11:17:28; 82.4 at 11:17:30; 58.9649 at 11:17:34; 59 at 11:17:35; 110 at 11:17:40; no cap 11:17:45–11:19:30; 88 at 11:19:32; 77.7 at 11:19:35; 50.8 at 11:19:40; 38.5 at 11:19:45; 107.6 at 11:19:50; no cap 11:19:55–11:20:00; 89 at 11:20:05; 81.816 at 11:20:09; 81.8 at 11:20:10; 110 at 11:20:15; no cap 11:20:20–11:20:25; 75.3 at 11:20:30; 110 at 11:20:35; no cap 11:20:40–11:22:25; 83.8 at 11:22:30; 52.5 at 11:22:35; 43.6309 at 11:22:36; 53.1 at 11:22:40; 74.6611 at 11:22:41; 110 at 11:22:45; no cap 11:22:50–11:26:10 |
| postcart | no cap 11:14:20–11:26:10 |
| emptycart | no cap 11:14:20–11:26:10 |


### final_s2_tf_only_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 11:44:25–11:48:05; 222 at 11:48:10; 141.465 at 11:48:12; 139.3 at 11:48:15; 302.5 at 11:48:20; no cap 11:48:25–11:49:40; 238 at 11:49:45; 173.8 at 11:49:50; 245.493 at 11:49:51; 302.5 at 11:49:55; no cap 11:50:00–11:50:30; 229 at 11:50:35; 141.9 at 11:50:40; 270.4 at 11:50:45; no cap 11:50:50–11:51:00; 143.376 at 11:51:04; 143.4 at 11:51:05; 302.5 11:51:09–11:51:10; no cap 11:51:15–11:51:25; 224 at 11:51:30; 283.3 at 11:51:35; no cap 11:51:40–11:52:20; 226 at 11:52:25; 94.8 at 11:52:30; 148.439 at 11:52:32; 208.2 at 11:52:35; no cap 11:52:40–11:53:10; 220 11:53:15–11:53:20; no cap 11:53:25–11:54:30; 220 at 11:54:35; 221.371 at 11:54:36; 302.5 at 11:54:40; no cap 11:54:45–11:54:55; 232 at 11:55:00; 84.6 at 11:55:05; 236.9 at 11:55:10; 302.5 at 11:55:13; no cap 11:55:15–11:55:25; 212.5 at 11:55:30; 302.5 at 11:55:35; no cap 11:55:40–11:55:55 |
| postcheckout | no cap 11:44:25–11:46:05; 44 at 11:46:10; 60.5 at 11:46:15; 60 at 11:46:17; 68.2 at 11:46:20; no cap 11:46:24–11:46:25; 83 at 11:46:30; 94.6 at 11:46:31; 91 at 11:46:35; 90 at 11:46:40; no cap at 11:46:45; 90 at 11:46:50; 72.4969 at 11:46:53; 46.8 at 11:46:55; 30.5 at 11:47:00; 85.1397 at 11:47:04; 85.1 at 11:47:05; 89.9272 at 11:47:08; 85.5 at 11:47:10; 83.7 at 11:47:15; 20.8 at 11:47:20; 29.1759 at 11:47:23; 40.1 at 11:47:25; 96.4 at 11:47:30; 90 at 11:47:35; 86 at 11:47:40; 19.9 at 11:47:45; 21.0263 at 11:47:47; 29.4 at 11:47:50; 91.3192 at 11:47:54; 91.3 at 11:47:55; 90 11:47:57–11:48:05; 88 at 11:48:06; 48.3 at 11:48:10; 31.612 at 11:48:13; 31.6 at 11:48:15; 61.1 at 11:48:20; 67.5 at 11:48:25; 87.9046 at 11:48:27; 90.9 at 11:48:30; 84.2 at 11:48:35; 73.7 at 11:48:40; 83.5204 at 11:48:42; 81.3 at 11:48:45; 46.8117 at 11:48:49; 46.8 at 11:48:50; 30.2 at 11:48:55; 75.6 at 11:49:00; 90 11:49:05–11:49:11; 57.9 at 11:49:15; 25.8 at 11:49:20; 65.6 at 11:49:25; 90 11:49:30–11:49:35; 84 at 11:49:40; 54.1781 at 11:49:43; 54.2 at 11:49:45; 27.0952 at 11:49:47; 28.2 at 11:49:50; 76.2015 at 11:49:54; 76.2 at 11:49:55; 99 at 11:49:57; 90 at 11:50:00; no cap at 11:50:03; 75 at 11:50:05; 25.8944 at 11:50:08; 18.9 at 11:50:10; 29 at 11:50:15; 92.9 at 11:50:20; 90 at 11:50:25; 88 at 11:50:30; 48.8 at 11:50:35; 32 at 11:50:40; 60 at 11:50:45; 90 11:50:50–11:50:55; no cap at 11:50:57; 49.6 at 11:51:00; 30.8 at 11:51:05; 37.6 at 11:51:10; 87.9 at 11:51:15; 90 at 11:51:18; no cap 11:51:20–11:51:25; 32.5 at 11:51:30; 31.9 at 11:51:35; 80.3 at 11:51:40; no cap at 11:51:45; 90 11:51:47–11:51:50; 88 at 11:51:55; 18.1 at 11:52:00; 33.6 at 11:52:05; 99 at 11:52:10; 90 11:52:12–11:52:20; 49.6 at 11:52:25; 28.1 at 11:52:30; 55.5 at 11:52:35; 99 at 11:52:40; no cap at 11:52:45; 53.8431 at 11:52:49; 53.8 at 11:52:50; 15.2 at 11:52:55; 20.7473 at 11:52:56; 39 at 11:53:00; 94.5 at 11:53:05; no cap at 11:53:10; 25.3 at 11:53:15; 16.2012 at 11:53:16; 16.2 at 11:53:20; 31.7301 at 11:53:23; 44 at 11:53:25; 59.6741 at 11:53:26; 93 at 11:53:30; 90 at 11:53:35; 54.6 at 11:53:40; 18.8 at 11:53:45; 24.5352 at 11:53:46; 46.8 at 11:53:50; no cap at 11:53:55; 90 at 11:54:00; 48.7 at 11:54:05; 12.7 at 11:54:10; 16.106 at 11:54:11; 31.3 at 11:54:15; 94 at 11:54:20; no cap 11:54:22–11:54:25; 54.6386 at 11:54:29; 54.6 at 11:54:30; 21.1 at 11:54:35; 38.6 at 11:54:40; 98.0884 at 11:54:44; 98.1 at 11:54:45; no cap 11:54:49–11:54:50; 89 at 11:54:52; 88 at 11:54:55; 58.1 at 11:55:00; 23.6 at 11:55:05; 45.4865 at 11:55:09; 45.5 at 11:55:10; 85.7 at 11:55:15; 90 at 11:55:20; 45.2 at 11:55:25; 16 at 11:55:30; 19.5008 at 11:55:31; 27.5 at 11:55:35; 70.2823 at 11:55:38; 87.2 at 11:55:40; 83.5174 at 11:55:42; 89.4 at 11:55:45; 82 at 11:55:50; 51.0651 at 11:55:51; 34.2 at 11:55:55 |
| getcart | no cap 11:44:25–11:48:05; 76 at 11:48:10; 76.0293 at 11:48:11; 57.7 at 11:48:15; 76.7115 at 11:48:16; 110 at 11:48:20; no cap 11:48:21–11:49:40; 87 11:49:44–11:49:45; 47.8 at 11:49:50; 110 at 11:49:55; no cap 11:50:00–11:50:30; 82 11:50:35–11:50:36; 65.5 at 11:50:40; no cap 11:50:45–11:51:00; 82 at 11:51:03; 53.3 at 11:51:05; 103.4 at 11:51:10; no cap 11:51:15–11:51:25; 79 at 11:51:30; 86.9 at 11:51:35; no cap 11:51:40–11:52:20; 82 at 11:52:25; 48 at 11:52:30; 98 at 11:52:35; 110 at 11:52:36; no cap 11:52:40–11:53:15; 81 at 11:53:20; 110 at 11:53:25; no cap 11:53:30–11:54:30; 79 at 11:54:35; no cap 11:54:38–11:54:55; 84 at 11:55:00; 53.6938 at 11:55:01; 37.6 at 11:55:05; 90.9323 at 11:55:08; 90.9 at 11:55:10; no cap 11:55:15–11:55:25; 78.5 at 11:55:30; 110 at 11:55:35; no cap 11:55:36–11:55:55 |
| postcart | no cap 11:44:25–11:55:55 |
| emptycart | no cap 11:44:25–11:55:55 |


### final_s2_tf_only_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:01:40–12:04:15; 240 at 12:04:20; no cap 12:04:25–12:04:30; 220.3 at 12:04:35; 202.2 at 12:04:40; 271.006 at 12:04:44; 271 at 12:04:45; no cap 12:04:50–12:05:15; 206 12:05:19–12:05:25; 291.2 at 12:05:30; no cap 12:05:35–12:05:40; 224.4 at 12:05:45; 142 at 12:05:50; 206.2 at 12:05:55; 288.301 at 12:05:56; no cap 12:06:00–12:06:10; 212 at 12:06:15; 300.1 at 12:06:20; no cap 12:06:25–12:06:30; 210.7 at 12:06:35; 164 at 12:06:40; 301.4 at 12:06:45; no cap at 12:06:50; 250.3 12:06:55–12:07:00; 242.809 at 12:07:03; 154 at 12:07:05; 195.2 at 12:07:10; no cap 12:07:15–12:07:50; 203 at 12:07:55; 190.2 at 12:08:00; no cap 12:08:04–12:13:10 |
| postcheckout | no cap 12:01:40–12:03:23; 45 at 12:03:25; 52 at 12:03:30; 69.3 at 12:03:35; 68 at 12:03:37; 77 at 12:03:40; no cap 12:03:44–12:03:51; 44.1 at 12:03:55; 28.969 at 12:03:56; 17.3 at 12:04:00; 32.1 at 12:04:05; 78.4 at 12:04:10; 65.2 at 12:04:15; 20.6 at 12:04:20; 28 at 12:04:25; 77.8 at 12:04:30; 55.3 at 12:04:35; 37.2 at 12:04:40; 37.7 at 12:04:45; 98.3 at 12:04:50; no cap at 12:04:51; 80 at 12:04:55; 21.1 at 12:05:00; 28 at 12:05:05; 82.6 at 12:05:10; 90 at 12:05:15; 33.6 at 12:05:20; 13.1 at 12:05:25; 25 at 12:05:30; 33.7627 at 12:05:31; 59.9397 at 12:05:34; 59.9 at 12:05:35; no cap at 12:05:38; 90 at 12:05:40; 47.1 at 12:05:45; 30.2 at 12:05:50; 28.9 at 12:05:55; 73 at 12:06:00; 90 at 12:06:05; 32.4 at 12:06:10; 13.6193 at 12:06:12; 13.6 at 12:06:15; 18.8235 at 12:06:17; 26.2 at 12:06:20; 36.2111 at 12:06:21; 64.3 at 12:06:25; no cap at 12:06:30; 80 at 12:06:31; 43.2 at 12:06:35; 27.2 at 12:06:40; 48.4707 at 12:06:44; 48.5 at 12:06:45; 66.3235 at 12:06:46; 90.4 at 12:06:50; 75.3 12:06:55–12:07:00; 67.8 at 12:07:05; 20.3 at 12:07:10; 24.3 at 12:07:15; 75.6919 at 12:07:19; 75.7 at 12:07:20; no cap at 12:07:25; 34.2 at 12:07:30; 23.2177 at 12:07:33; 21.8 at 12:07:35; 38.8 at 12:07:40; 92.8 at 12:07:45; 78.4086 at 12:07:47; 73.2 at 12:07:50; 22.8659 at 12:07:54; 22.9 at 12:07:55; 30.1712 at 12:07:59; 30.2 at 12:08:00; 75.6 at 12:08:05; 75.2 at 12:08:10; 19.5 at 12:08:15; 15.3546 at 12:08:17; 16.4 at 12:08:20; 53.9 at 12:08:25; no cap at 12:08:30; 52 at 12:13:10 |
| getcart | no cap 12:01:40–12:04:15; 91 at 12:04:20; no cap 12:04:25–12:04:30; 80.3 at 12:04:35; 62.2 at 12:04:40; 50.3154 at 12:04:42; 69.6 at 12:04:45; no cap 12:04:50–12:05:15; 76 12:05:19–12:05:25; 107.6 at 12:05:30; no cap 12:05:35–12:05:40; 78.4 at 12:05:45; 49.8 at 12:05:50; 74.2 at 12:05:55; no cap 12:06:00–12:06:10; 73 at 12:06:15; 110 at 12:06:20; no cap 12:06:25–12:06:30; 73.7 at 12:06:35; 48 at 12:06:40; 110 at 12:06:45; no cap at 12:06:50; 85.3 12:06:55–12:07:00; 53.2 at 12:07:05; 93 at 12:07:10; no cap 12:07:15–12:07:50; 69 at 12:07:55; 68.9716 at 12:07:57; 66.2 at 12:08:00; no cap 12:08:05–12:13:10 |
| postcart | no cap 12:01:40–12:13:10 |
| emptycart | no cap 12:01:40–12:13:10 |


### final_s2_rg_only_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:18:55–12:30:45 |
| postcheckout | no cap 12:18:55–12:30:45 |
| getcart | no cap 12:18:55–12:30:45 |
| postcart | no cap 12:18:55–12:30:45 |
| emptycart | no cap 12:18:55–12:30:45 |


### final_s2_rg_only_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:36:55–12:48:45 |
| postcheckout | no cap 12:36:55–12:48:45 |
| getcart | no cap 12:36:55–12:48:45 |
| postcart | no cap 12:36:55–12:48:45 |
| emptycart | no cap 12:36:55–12:48:45 |


### final_s2_both_burst_run1

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:54:55–12:57:50; 234 12:57:55–12:57:56; 112.2 at 12:58:00; 109.636 at 12:58:01; 217.6 at 12:58:05; 302.5 at 12:58:10; no cap at 12:58:15; 201 at 12:58:20; 199.4 at 12:58:25; no cap 12:58:30–12:58:35 |
| postcheckout | no cap 12:54:55–12:56:55; 38 at 12:57:00; 47 at 12:57:05; 58.3 at 12:57:07; no cap at 12:57:10; 65 at 12:57:15; no cap 12:57:20–12:57:25; 65.5 at 12:57:30; 16.3 at 12:57:35; 30.1 at 12:57:40; 68.1 at 12:57:45; 77.8 at 12:57:50; 75.8223 at 12:57:52; 47.2 at 12:57:55; 31.6 at 12:58:00; 40 at 12:58:05; 83.6148 at 12:58:09; 83.6 at 12:58:10; 73.2436 at 12:58:12; 46.8 at 12:58:15; 13.2 at 12:58:20; 11.9 at 12:58:25; 31.4 at 12:58:30; 78.5 at 12:58:35 |
| getcart | no cap 12:54:55–12:57:50; 82 at 12:57:55; 34.9 at 12:58:00; 74 at 12:58:05; no cap 12:58:10–12:58:15; 76 at 12:58:20; 74.4303 at 12:58:22; 101.984 at 12:58:24; 102 at 12:58:25; 110 at 12:58:26; no cap 12:58:28–12:58:35 |
| postcart | no cap 12:54:55–12:58:35 |
| emptycart | no cap 12:54:55–12:58:35 |


### final_s2_both_burst_run2

| API | Live caps |
| --- | --- |
| getproduct | no cap 13:13:00–13:15:25; 272 at 13:24:50 |
| postcheckout | no cap 13:13:00–13:15:05; 52.8 at 13:15:07; no cap at 13:15:10; 61 at 13:15:15; no cap at 13:15:20; 71.4 at 13:15:25; 41.6 at 13:24:50 |
| getcart | no cap 13:13:00–13:15:25; 100 at 13:24:50 |
| postcart | no cap 13:13:00–13:24:50 |
| emptycart | no cap 13:13:00–13:24:50 |


## One paragraph per launch

`final_s2_rg_only_normal_run1`: frontend → recommendationservice 1 / 1 shed rpr 0.70 last attempts 1. Outbound retry delta: checkoutservice 38, recommendationservice 90,332, cartservice 4. grpc_4 / grpc_14: recommendationservice 94,317 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 1 / 0. Detector-hot: checkoutservice **581/716 (81.1%)**.

`final_s2_rg_only_normal_run2`: frontend → recommendationservice 1 / 1 shed rpr 0.68 last attempts 1. Outbound retry delta: checkoutservice 84, recommendationservice 87,964, cartservice 0. grpc_4 / grpc_14: recommendationservice 90,575 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **580/716 (81.0%)**.

`final_s2_both_normal_run1`: no shed. Outbound retry delta: checkoutservice 1,993, recommendationservice 17,142, cartservice 0. grpc_4 / grpc_14: recommendationservice 14,012 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **493/715 (69.0%)**, emailservice **367/715 (51.3%)**.

`final_s2_both_normal_run2`: no shed. Outbound retry delta: checkoutservice 258, recommendationservice 41,840, cartservice 0. grpc_4 / grpc_14: recommendationservice 35,193 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **438/716 (61.2%)**.

`final_s2_tf_only_run1`: no retryguard.log. Outbound retry delta: checkoutservice 99, recommendationservice 43,295, cartservice 0. grpc_4 / grpc_14: recommendationservice 35,475 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **452/693 (65.2%)**.

`final_s2_tf_only_run2`: no retryguard.log. Outbound retry delta: checkoutservice 301, recommendationservice 120,494, cartservice 0. grpc_4 / grpc_14: recommendationservice 105,725 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **406/692 (58.7%)**.

`final_s2_rg_only_burst_run1`: frontend → recommendationservice 7 (3) / 6 shed rpr 0.84; 0.44; 0.54; 0.61; 0.67b; 0.68b; 0.68b last attempts 0. Outbound retry delta: checkoutservice 64, recommendationservice 70,868, cartservice —. grpc_4 / grpc_14: recommendationservice 91,094 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **558/713 (78.3%)**.

`final_s2_rg_only_burst_run2`: frontend → recommendationservice 4 / 3 shed rpr 0.67; 0.43; 0.53; 0.80 last attempts 0. Outbound retry delta: checkoutservice 107, recommendationservice 42,880, cartservice —. grpc_4 / grpc_14: recommendationservice 72,472 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **556/714 (77.9%)**.

`final_s2_both_burst_run1`: frontend → recommendationservice 3 (1) / 3 shed rpr 1.19; 0.72b; 0.51 last attempts 1. Outbound retry delta: checkoutservice 103, recommendationservice 70,319, cartservice —. grpc_4 / grpc_14: recommendationservice 84,492 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **443/716 (61.9%)**.

`final_s2_both_burst_run2`: frontend → recommendationservice 4 / 4 shed rpr 1.57; 0.57; 0.46; 1.20 last attempts 1. Outbound retry delta: checkoutservice 10, recommendationservice 40,496, cartservice —. grpc_4 / grpc_14: recommendationservice 39,922 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **377/716 (52.7%)**.


## Related

This campaign's plan is [2026-10-14-s2-mode-matrix.md](../../docs/superpowers/plans/2026-10-14-s2-mode-matrix.md). The run log is [2026-10-14-s2-mode-matrix-run-log.md](../../docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md). Template: [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). The (a)/(b)/(c) reading is [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Controller: [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md). [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../docs/adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../../docs/adr/0009-paper-c1-default-cpu-table.md). Older S2 folders (`study*`, `s2_burst20_*`, `campaign_48/`, bar 1.5) are not columns.
