# S3 mode matrix

## Setup

Ten holds, 600 s each, mix 175 / 30 / 70 / 90 / 5 (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50. Paper-C1 on every row except checkout constrained to 200 m: recommendations 1150 m, catalog 800 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, payment 155 m, email 120 m, redis-cart 540 m. Frontend 1150 m is the HPA pin. Frontend HPA min=max=4, catalog HPA min=max=1, sidecar `proxyCPU` 90 m, `proxyCPULimit` unset. Cool-off 120 s. Checkout and recommendations stayed up.

Normal and TopFull-only folders are under `experiments/results/final results/S3_targeted_bottleneck_normal/`. Burst folders are under `experiments/results/final results/S3_targeted_bottleneck_burst/`.

- `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3`
- `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run4`
- `experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run3`
- `experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run4`
- `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run3`
- `experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run4`
- `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3`
- `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run4`
- `experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3`
- `experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4`

All ten launches passed the collector gate. No throttle FLAG. No replay. Column order is holds 11–20. A bold bar separates each pair. `final_s3_*_run1`, `final_s3_*_run2`, `s3_ck200_rgtf1`, and `campaign_48/` S3 are not columns.

## Index

| Hold | log_folder | RetryGuard | TopFull |
| --- | --- | --- | --- |
| 11 | final_s3_rg_only_normal_run3 | normal | off |
| 12 | final_s3_rg_only_normal_run4 | normal | off |
| 13 | final_s3_both_normal_run3 | normal | on |
| 14 | final_s3_both_normal_run4 | normal | on |
| 15 | final_s3_tf_only_run3 | off | on |
| 16 | final_s3_tf_only_run4 | off | on |
| 17 | final_s3_rg_only_burst_run3 | burst_rpr 2.0 | off |
| 18 | final_s3_rg_only_burst_run4 | burst_rpr 2.0 | off |
| 19 | final_s3_both_burst_run3 | burst_rpr 2.0 | on |
| 20 | final_s3_both_burst_run4 | burst_rpr 2.0 | on |

## Edge-mode bars

A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s. Burst mode was off on the six normal and TopFull-only holds.

Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

## Gate numbers

- final_s3_rg_only_normal_run3: Locust total.csv 566 rows, mesh span 665 s, inbound gaps ≥ 1.5 s: 0 of 7315, retryguard.log present.
- final_s3_rg_only_normal_run4: Locust total.csv 564 rows, mesh span 666 s, inbound gaps ≥ 1.5 s: 0 of 7326, retryguard.log present.
- final_s3_both_normal_run3: Locust total.csv 561 rows, mesh span 667 s, inbound gaps ≥ 1.5 s: 11 of 7326, retryguard.log present.
- final_s3_both_normal_run4: Locust total.csv 560 rows, mesh span 667 s, inbound gaps ≥ 1.5 s: 33 of 7304, retryguard.log present.
- final_s3_tf_only_run3: Locust total.csv 563 rows, mesh span 640 s, inbound gaps ≥ 1.5 s: 0 of 7040, retryguard.log absent.
- final_s3_tf_only_run4: Locust total.csv 562 rows, mesh span 641 s, inbound gaps ≥ 1.5 s: 55 of 6996, retryguard.log absent.
- final_s3_rg_only_burst_run3: Locust total.csv 566 rows, mesh span 666 s, inbound gaps ≥ 1.5 s: 0 of 7326, retryguard.log present.
- final_s3_rg_only_burst_run4: Locust total.csv 568 rows, mesh span 665 s, inbound gaps ≥ 1.5 s: 0 of 7315, retryguard.log present.
- final_s3_both_burst_run3: Locust total.csv 558 rows, mesh span 666 s, inbound gaps ≥ 1.5 s: 836 of 6490, retryguard.log present.
- final_s3_both_burst_run4: Locust total.csv 564 rows, mesh span 665 s, inbound gaps ≥ 1.5 s: 0 of 7315, retryguard.log present.

## (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 22 / 23 (21) | 22 / 23 (14) | **┃** | 22 / 23 (21) | 23 / 24 (21) | **┃** | **587 / 588** | **586 / 582** | **┃** | 22 / 23 (19) | 6 / 7 (4) | **┃** | 16 / 19 (14) | 7 / 8 (4) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

## (a) Mean / median / max / volume rpr

| Edge | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.071 / 0.000 / 2.67 / 0.035 | 0.067 / 0.000 / 4.71 / 0.028 | **┃** | 0.080 / 0.000 / 4.60 / 0.050 | 0.080 / 0.000 / 6.25 / 0.052 | **┃** | 2.091 / 2.000 / 5.75 / 2.014 | 2.086 / 2.000 / 7.33 / 1.980 | **┃** | 0.074 / 0.000 / 4.38 / 0.032 | 0.023 / 0.000 / 2.88 / 0.009 | **┃** | 0.069 / 0.000 / 4.50 / 0.041 | 0.033 / 0.000 / 6.00 / 0.018 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

## (a) Climb streaks, 1-attempt / 2-attempt

| Edge | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | 1 / — | — / — |

Burst bars: final_s3_rg_only_burst_run3 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s3_rg_only_burst_run4 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s3_both_burst_run3 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); final_s3_both_burst_run4 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force (burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count in parentheses. Samples exist only while the edge is above 0 attempts and the window meets the volume floor.

## (a2) Burst window

| Edge | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (605) | **┃** | 0.00 / 0.00 / 0 / 0 (519) | 0.00 / 0.00 / 0 / 0 (597) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (600) | 0.00 / 0.00 / 0 / 0 (604) | **┃** | 0.00 / 0.00 / 0 / 0 (519) | 0.00 / 0.00 / 0 / 0 (596) |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (604) | **┃** | 0.00 / 0.00 / 0 / 0 (519) | 0.00 / 0.00 / 0 / 0 (596) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (601) | **┃** | 0.00 / 0.00 / 0 / 0 (516) | 0.00 / 0.00 / 0 / 0 (593) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (602) | 0.00 / 0.00 / 0 / 0 (606) | **┃** | 0.00 / 0.00 / 0 / 0 (521) | 0.00 / 0.00 / 0 / 0 (598) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (602) | **┃** | 0.00 / 0.00 / 0 / 0 (518) | 0.00 / 0.00 / 0 / 0 (594) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (18) | 0.00 / 0.00 / 0 / 0 (20) | **┃** | 0.00 / 0.00 / 0 / 0 (489) | 0.00 / 0.00 / 0 / 0 (577) |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (591) | 0.00 / 0.00 / 0 / 0 (597) | **┃** | 0.00 / 0.00 / 0 / 0 (512) | 0.00 / 0.00 / 0 / 0 (590) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 2.12 / 0.73 / 1 / 1 (37) | 2.09 / 0.00 / 1 / 1 (24) | **┃** | 2.08 / 0.03 / 2 / 2 (38) | 2.47 / 0.00 / 1 / 1 (21) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (594) | 0.00 / 0.00 / 0 / 0 (598) | **┃** | 0.00 / 0.00 / 0 / 0 (512) | 0.00 / 0.00 / 0 / 0 (589) |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (601) | **┃** | 0.00 / 0.00 / 0 / 0 (516) | 0.00 / 0.00 / 0 / 0 (593) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (603) | **┃** | 0.00 / 0.00 / 0 / 0 (518) | 0.00 / 0.00 / 0 / 0 (595) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (605) | **┃** | 0.00 / 0.00 / 0 / 0 (520) | 0.00 / 0.00 / 0 / 0 (597) |

Burst vs normal sheds (`ON→OFF burst` is the part fired by `metric=rpr_burst`): `final_s3_rg_only_burst_run3` 1 burst and 0 normal; `final_s3_rg_only_burst_run4` 1 burst and 0 normal; `final_s3_both_burst_run3` 2 burst and 0 normal; `final_s3_both_burst_run4` 1 burst and 0 normal.

## (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| checkoutservice | **526 / 584** | **194 / 583** | **┃** | 23 / 214 | 24 / 226 | **┃** | **588 / 588** | **581 / 581** | **┃** | **587 / 587** | **524 / 584** | **┃** | 18 / 190 | 9 / 211 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 2 / 38 | 2 / 44 | **┃** | 1 / 3 | 3 / 5 | **┃** | 2 / 36 | 3 / 38 | **┃** | 4 / 42 | 1 / 29 | **┃** | 1 / 3 | 1 / 2 |
| emailservice | 1 / 25 | 2 / 23 | **┃** | 2 / 26 | 2 / 28 | **┃** | 1 / 24 | 1 / 20 | **┃** | 2 / 12 | 2 / 17 | **┃** | 2 / 17 | 2 / 34 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: rejection streak under the re-enable bar / count

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 612 / 612 | 612 / 612 | **┃** | 612 / 612 | 610 / 610 | **┃** | 611 / 611 | 606 / 606 | **┃** | 612 / 612 | 611 / 611 | **┃** | 536 / 536 | 612 / 612 |
| checkoutservice | 27 / 33 | 21 / 37 | **┃** | 24 / 417 | 23 / 402 | **┃** | 23 / 23 | 24 / 24 | **┃** | 25 / 28 | 26 / 31 | **┃** | 26 / 379 | 24 / 418 |
| recommendationservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| paymentservice | 111 / 586 | 90 / 579 | **┃** | 567 / 608 | 565 / 603 | **┃** | 23 / 450 | 26 / 428 | **┃** | 91 / 587 | 214 / 595 | **┃** | 499 / 532 | 579 / 610 |
| emailservice | 28 / 86 | 21 / 66 | **┃** | 56 / 562 | 83 / 561 | **┃** | 22 / 81 | 25 / 74 | **┃** | 25 / 67 | 26 / 102 | **┃** | 96 / 501 | 53 / 566 |
| productcatalogservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| cartservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 537 / 537 | 612 / 612 |
| currencyservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| shippingservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| adservice | 612 / 612 | 612 / 612 | **┃** | 610 / 610 | 609 / 609 | **┃** | 611 / 611 | 606 / 606 | **┃** | 612 / 612 | 611 / 611 | **┃** | 535 / 535 | 611 / 611 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| productcatalogservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| currencyservice | 613 / 613 | 612 / 612 | **┃** | 612 / 612 | 609 / 609 | **┃** | 612 / 612 | 607 / 607 | **┃** | 612 / 612 | 612 / 612 | **┃** | 536 / 536 | 612 / 612 |
| adservice | 612 / 612 | 612 / 612 | **┃** | 610 / 610 | 609 / 609 | **┃** | 611 / 611 | 606 / 606 | **┃** | 612 / 612 | 611 / 611 | **┃** | 535 / 535 | 611 / 611 |

gRPC counted in the rejection rate on the four read callees (main rejection tables above) and in the retry policy. Cell is grpc_4 / grpc_14.

## grpc_4 / grpc_14

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| checkoutservice | **596/712 (83.7%)** | **596/714 (83.5%)** | **┃** | **596/717 (83.1%)** | **597/717 (83.3%)** | **┃** | **597/690 (86.5%)** | **596/690 (86.4%)** | **┃** | **598/715 (83.6%)** | **594/713 (83.3%)** | **┃** | **596/716 (83.2%)** | **595/715 (83.2%)** |
| recommendationservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| paymentservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| emailservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| productcatalogservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| cartservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| currencyservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| shippingservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| adservice | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |
| redis-cart | 0/712 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/717 (0.0%) | **┃** | 0/690 (0.0%) | 0/690 (0.0%) | **┃** | 0/715 (0.0%) | 0/713 (0.0%) | **┃** | 0/716 (0.0%) | 0/715 (0.0%) |

## (c) Outbound retry delta by target

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 614 | 482 | **┃** | 435 | 465 | **┃** | 12,197 | 12,011 | **┃** | 564 | 154 | **┃** | 382 | 165 |

## (c) Inbound resets

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 31 | 24 | **┃** | 11 | 8 | **┃** | 18 | 25 | **┃** | 26 | 40 | **┃** | 10 | 18 |
| checkoutservice | 8,318 | 7,722 | **┃** | 1,710 | 1,813 | **┃** | 8,486 | 8,170 | **┃** | 8,356 | 8,375 | **┃** | 1,807 | 1,684 |
| recommendationservice | 2 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 1 | 4 | **┃** | 0 | 2 |
| paymentservice | 689 | 798 | **┃** | 49 | 46 | **┃** | 656 | 646 | **┃** | 654 | 610 | **┃** | 42 | 21 |
| emailservice | 30 | 26 | **┃** | 137 | 132 | **┃** | 28 | 21 | **┃** | 15 | 18 | **┃** | 144 | 149 |
| productcatalogservice | 1 | 5 | **┃** | 1 | 2 | **┃** | 3 | 3 | **┃** | 0 | 7 | **┃** | 4 | 1 |
| cartservice | 168 | 181 | **┃** | 109 | 96 | **┃** | 123 | 159 | **┃** | 133 | 166 | **┃** | 98 | 100 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 474 | 500 | **┃** | 46 | 57 | **┃** | 488 | 459 | **┃** | 487 | 440 | **┃** | 53 | 46 |
| adservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

## RetryGuard toggles

### final_s3_rg_only_normal_run3

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T00:38:55Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.50 |

### final_s3_rg_only_normal_run4

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T00:56:55Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.61 |

### final_s3_both_normal_run3

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T01:15:09Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.80 |

### final_s3_both_normal_run4

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T01:33:20Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.18 |

final_s3_tf_only_run3: no transition lines.
final_s3_tf_only_run4: no transition lines.
### final_s3_rg_only_burst_run3

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 | 1 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T02:26:13Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.12 |

### final_s3_rg_only_burst_run4

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 | 1 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T02:44:06Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.09 |

### final_s3_both_burst_run3

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 2 | 0 | 0 | 0 | 2 |
| checkoutservice | 0 | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T03:02:23Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.08 |
| 2026-10-15T03:08:45Z | checkoutservice | OFF→ON | 0 | rejection 0.11 |
| 2026-10-15T03:08:51Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.70 |

### final_s3_both_burst_run4

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 | 1 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-15T03:20:20Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.47 |

## RetryGuard toggles, part 2

### Part 2, per edge that sheds

`ON→OFF / OFF→ON` counts the edge's sheds and the callee's re-enables. A parenthetical is the burst-shed count. Shed rpr values are in time order; `b` marks `metric=rpr_burst`. First shed is seconds after the first `OBSERVE` line. Attempts after re-enable is the edge's attempt count on its last transition. Time OFF is seconds from each shed to the next callee `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is the min and median of `metric=rejection` samples for that callee inside each OFF window. The streak counts those samples strictly below 0.25. An em dash on a detail row means that edge did not go to 0 on that hold. TopFull-only columns are an em dash because there is no `retryguard.log`.

#### frontend → checkoutservice

| frontend → checkoutservice | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 0 | 1 / 0 | **┃** | 1 / 0 | 1 / 0 | **┃** | — | — | **┃** | 1 (1) / 0 | 1 (1) / 0 | **┃** | 2 (2) / 1 | 1 (1) / 0 |
| Shed rpr | 1.50 | 1.61 | **┃** | 1.80 | 2.18 | **┃** | — | — | **┃** | 2.12b | 2.09b | **┃** | 2.08b; 0.70b | 2.47b |
| First shed, seconds after first OBSERVE | 49 | 41 | **┃** | 44 | 43 | **┃** | — | — | **┃** | 45 | 32 | **┃** | 41 | 29 |
| Attempts after re-enable | 0 | 0 | **┃** | 0 | 0 | **┃** | — | — | **┃** | 0 | 0 | **┃** | 0 | 0 |
| Time OFF (s) | 565 | 572 | **┃** | 569 | 570 | **┃** | — | — | **┃** | 568 | 581 | **┃** | 382; 184 | 584 |
| OFF rejection min / median | 0.194 / 0.467 | 0.000 / 0.433 | **┃** | 0.000 / 0.062 | 0.000 / 0.071 | **┃** | — | — | **┃** | 0.000 / 0.467 | 0.167 / 0.483 | **┃** | 0.000 / 0.077; 0.000 / 0.074 | 0.000 / 0.057 |
| Longest streak under 0.25 | 1 | 2 | **┃** | 10 | 11 | **┃** | — | — | **┃** | 1 | 1 | **┃** | 17; 7 | 9 |

Re-enabled: `final_s3_both_burst_run3` re-enabled and ended at 0. Still at 0 at exit: `final_s3_rg_only_normal_run3` stayed at 0; `final_s3_rg_only_normal_run4` stayed at 0; `final_s3_both_normal_run3` stayed at 0; `final_s3_both_normal_run4` stayed at 0; `final_s3_rg_only_burst_run3` stayed at 0; `final_s3_rg_only_burst_run4` stayed at 0; `final_s3_both_burst_run4` stayed at 0.

## Locust goodput

| API | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 167.8 | 167.8 | **┃** | 168.0 | 168.0 | **┃** | 168.0 | 167.7 | **┃** | 168.0 | 167.9 | **┃** | 167.8 | 167.9 |
| postcheckout | 0.4 | 0.3 | **┃** | 8.6 | 8.9 | **┃** | 0.3 | 0.3 | **┃** | 0.3 | 0.4 | **┃** | 9.3 | 9.0 |
| getcart | 67.2 | 67.2 | **┃** | 67.2 | 67.2 | **┃** | 67.2 | 67.1 | **┃** | 67.2 | 67.1 | **┃** | 67.1 | 67.2 |
| postcart | 86.2 | 86.4 | **┃** | 86.4 | 86.3 | **┃** | 86.4 | 86.2 | **┃** | 86.3 | 86.3 | **┃** | 86.3 | 86.4 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

| API | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.953 | 0.963 | **┃** | 0.684 | 0.674 | **┃** | 0.960 | 0.957 | **┃** | 0.958 | 0.953 | **┃** | 0.655 | 0.664 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

| API | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 71 | 73 | **┃** | 80 | 79 | **┃** | 68 | 79 | **┃** | 85 | 79 | **┃** | 64 | 76 |
| postcheckout | 601 | 598 | **┃** | 555 | 556 | **┃** | 2119 | 2117 | **┃** | 609 | 566 | **┃** | 538 | 498 |
| getcart | 56 | 43 | **┃** | 68 | 67 | **┃** | 45 | 67 | **┃** | 71 | 64 | **┃** | 40 | 64 |
| postcart | 58 | 58 | **┃** | 60 | 60 | **┃** | 58 | 60 | **┃** | 60 | 58 | **┃** | 58 | 59 |
| emptycart | 10 | 13 | **┃** | 11 | 13 | **┃** | 12 | 14 | **┃** | 15 | 11 | **┃** | 11 | 13 |

## Inbound arrival rate

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 326.3 | 325.9 | **┃** | 312.1 | 312.6 | **┃** | 321.2 | 320.8 | **┃** | 325.7 | 326.5 | **┃** | 313.5 | 313.8 |
| checkoutservice | 27.1 | 26.9 | **┃** | 13.6 | 14.1 | **┃** | 28.5 | 28.2 | **┃** | 27.0 | 26.6 | **┃** | 14.5 | 13.9 |
| recommendationservice | 242.3 | 242.1 | **┃** | 228.4 | 228.9 | **┃** | 234.0 | 233.7 | **┃** | 241.9 | 242.5 | **┃** | 229.7 | 229.8 |
| paymentservice | 16.6 | 17.6 | **┃** | 13.0 | 13.5 | **┃** | 17.3 | 16.0 | **┃** | 16.2 | 16.9 | **┃** | 14.1 | 13.6 |
| emailservice | 0.5 | 0.4 | **┃** | 9.1 | 9.4 | **┃** | 0.5 | 0.5 | **┃** | 0.4 | 0.5 | **┃** | 10.0 | 9.7 |
| productcatalogservice | 1687.8 | 1685.8 | **┃** | 1603.7 | 1606.7 | **┃** | 1646.9 | 1644.8 | **┃** | 1685.1 | 1689.0 | **┃** | 1611.8 | 1612.6 |
| cartservice | 329.0 | 328.3 | **┃** | 324.0 | 324.8 | **┃** | 342.1 | 341.2 | **┃** | 328.0 | 328.6 | **┃** | 326.1 | 325.8 |
| currencyservice | 459.0 | 458.4 | **┃** | 452.4 | 453.2 | **┃** | 477.2 | 476.1 | **┃** | 458.0 | 458.8 | **┃** | 454.7 | 454.5 |
| shippingservice | 95.0 | 95.1 | **┃** | 87.5 | 88.4 | **┃** | 99.2 | 98.1 | **┃** | 94.3 | 95.0 | **┃** | 89.5 | 88.7 |
| adservice | 154.3 | 154.1 | **┃** | 153.9 | 153.9 | **┃** | 160.3 | 160.1 | **┃** | 154.1 | 154.3 | **┃** | 154.1 | 154.3 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn (ms)

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 79 | 77 | **┃** | 61 | 58 | **┃** | 81 | 88 | **┃** | 85 | 81 | **┃** | 51 | 58 |
| checkoutservice | 497 | 498 | **┃** | 370 | 368 | **┃** | 498 | 498 | **┃** | 498 | 496 | **┃** | 369 | 353 |
| recommendationservice | 6 | 6 | **┃** | 10 | 8 | **┃** | 6 | 8 | **┃** | 9 | 7 | **┃** | 6 | 8 |
| paymentservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| emailservice | 4 | 3 | **┃** | 4 | 3 | **┃** | 5 | 4 | **┃** | 3 | 4 | **┃** | 5 | 3 |
| productcatalogservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 0 | 1 | **┃** | 1 | 1 | **┃** | 0 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| currencyservice | 1 | 1 | **┃** | 2 | 1 | **┃** | 1 | 1 | **┃** | 2 | 1 | **┃** | 1 | 1 |
| shippingservice | 1 | 1 | **┃** | 1 | 0 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 0 | 0 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.079 | 0.080 | **┃** | 0.020 | 0.021 | **┃** | 0.029 | 0.029 | **┃** | 0.079 | 0.080 | **┃** | 0.021 | 0.020 |
| checkoutservice | 0.975 | 0.984 | **┃** | 0.326 | 0.318 | **┃** | 0.981 | 0.978 | **┃** | 0.979 | 0.973 | **┃** | 0.296 | 0.297 |
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

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1050 / 1377 | 1150 / 4 / 1121 / 1458 | **┃** | 1150 / 4 / 1033 / 1406 | 1150 / 4 / 995 / 1332 | **┃** | 1150 / 4 / 1098 / 1410 | 1150 / 4 / 1017 / 1308 | **┃** | 1150 / 4 / 1015 / 1361 | 1150 / 4 / 974 / 1281 | **┃** | 1150 / 4 / 1059 / 1398 | 1150 / 4 / 976 / 1368 |
| checkoutservice | 200 / 1 / 155 / 198 | 200 / 1 / 155 / 196 | **┃** | 200 / 1 / 157 / 199 | 200 / 1 / 157 / 199 | **┃** | 200 / 1 / 160 / 196 | 200 / 1 / 159 / 197 | **┃** | 200 / 1 / 154 / 195 | 200 / 1 / 155 / 196 | **┃** | 200 / 1 / 156 / 198 | 200 / 1 / 156 / 198 |
| recommendationservice | 1150 / 1 / 407 / 546 | 1150 / 1 / 425 / 560 | **┃** | 1150 / 1 / 401 / 557 | 1150 / 1 / 377 / 513 | **┃** | 1150 / 1 / 402 / 527 | 1150 / 1 / 390 / 506 | **┃** | 1150 / 1 / 408 / 555 | 1150 / 1 / 383 / 509 | **┃** | 1150 / 1 / 379 / 511 | 1150 / 1 / 370 / 537 |
| paymentservice | 155 / 1 / 15 / 23 | 155 / 1 / 15 / 22 | **┃** | 155 / 1 / 14 / 19 | 155 / 1 / 13 / 19 | **┃** | 155 / 1 / 15 / 21 | 155 / 1 / 14 / 23 | **┃** | 155 / 1 / 14 / 22 | 155 / 1 / 14 / 20 | **┃** | 155 / 1 / 13 / 20 | 155 / 1 / 13 / 21 |
| emailservice | 120 / 1 / 8 / 28 | 120 / 1 / 8 / 20 | **┃** | 120 / 1 / 21 / 28 | 120 / 1 / 20 / 29 | **┃** | 120 / 1 / 8 / 22 | 120 / 1 / 8 / 27 | **┃** | 120 / 1 / 8 / 27 | 120 / 1 / 8 / 25 | **┃** | 120 / 1 / 21 / 32 | 120 / 1 / 21 / 29 |
| productcatalogservice | 800 / 1 / 394 / 513 | 800 / 1 / 435 / 566 | **┃** | 800 / 1 / 366 / 490 | 800 / 1 / 363 / 479 | **┃** | 800 / 1 / 424 / 542 | 800 / 1 / 363 / 464 | **┃** | 800 / 1 / 368 / 488 | 800 / 1 / 352 / 459 | **┃** | 800 / 1 / 408 / 537 | 800 / 1 / 349 / 479 |
| cartservice | 800 / 1 / 255 / 352 | 800 / 1 / 278 / 369 | **┃** | 800 / 1 / 253 / 414 | 800 / 1 / 248 / 383 | **┃** | 800 / 1 / 285 / 456 | 800 / 1 / 266 / 437 | **┃** | 800 / 1 / 241 / 344 | 800 / 1 / 235 / 346 | **┃** | 800 / 1 / 265 / 452 | 800 / 1 / 242 / 361 |
| currencyservice | 770 / 1 / 229 / 303 | 770 / 1 / 248 / 326 | **┃** | 770 / 1 / 236 / 317 | 770 / 1 / 232 / 309 | **┃** | 770 / 1 / 252 / 321 | 770 / 1 / 238 / 310 | **┃** | 770 / 1 / 225 / 300 | 770 / 1 / 216 / 284 | **┃** | 770 / 1 / 238 / 318 | 770 / 1 / 226 / 311 |
| shippingservice | 770 / 1 / 51 / 67 | 770 / 1 / 54 / 69 | **┃** | 770 / 1 / 51 / 68 | 770 / 1 / 49 / 64 | **┃** | 770 / 1 / 55 / 70 | 770 / 1 / 51 / 64 | **┃** | 770 / 1 / 51 / 67 | 770 / 1 / 50 / 65 | **┃** | 770 / 1 / 50 / 66 | 770 / 1 / 50 / 68 |
| adservice | 1150 / 1 / 100 / 145 | 1150 / 1 / 105 / 134 | **┃** | 1150 / 1 / 107 / 142 | 1150 / 1 / 101 / 137 | **┃** | 1150 / 1 / 104 / 129 | 1150 / 1 / 104 / 137 | **┃** | 1150 / 1 / 100 / 128 | 1150 / 1 / 91 / 118 | **┃** | 1150 / 1 / 97 / 127 | 1150 / 1 / 98 / 140 |
| redis-cart | 540 / 1 / 34 / 58 | 540 / 1 / 36 / 62 | **┃** | 540 / 1 / 35 / 62 | 540 / 1 / 33 / 58 | **┃** | 540 / 1 / 36 / 61 | 540 / 1 / 34 / 57 | **┃** | 540 / 1 / 32 / 59 | 540 / 1 / 31 / 54 | **┃** | 540 / 1 / 34 / 60 | 540 / 1 / 32 / 61 |

## CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.23 / 0.30 | 0.24 / 0.32 | **┃** | 0.22 / 0.31 | 0.22 / 0.29 | **┃** | 0.24 / 0.31 | 0.22 / 0.28 | **┃** | 0.22 / 0.30 | 0.21 / 0.28 | **┃** | 0.23 / 0.30 | 0.21 / 0.30 |
| checkoutservice | 0.78 / 0.99 | 0.78 / 0.98 | **┃** | 0.78 / 0.99 | 0.78 / 0.99 | **┃** | 0.80 / 0.98 | 0.80 / 0.98 | **┃** | 0.77 / 0.97 | 0.77 / 0.98 | **┃** | 0.78 / 0.99 | 0.78 / 0.99 |
| recommendationservice | 0.35 / 0.47 | 0.37 / 0.49 | **┃** | 0.35 / 0.48 | 0.33 / 0.45 | **┃** | 0.35 / 0.46 | 0.34 / 0.44 | **┃** | 0.35 / 0.48 | 0.33 / 0.44 | **┃** | 0.33 / 0.44 | 0.32 / 0.47 |
| paymentservice | 0.09 / 0.15 | 0.10 / 0.14 | **┃** | 0.09 / 0.12 | 0.09 / 0.12 | **┃** | 0.09 / 0.14 | 0.09 / 0.15 | **┃** | 0.09 / 0.14 | 0.09 / 0.13 | **┃** | 0.09 / 0.13 | 0.09 / 0.14 |
| emailservice | 0.06 / 0.23 | 0.06 / 0.17 | **┃** | 0.17 / 0.23 | 0.17 / 0.24 | **┃** | 0.06 / 0.18 | 0.06 / 0.23 | **┃** | 0.06 / 0.23 | 0.06 / 0.21 | **┃** | 0.18 / 0.27 | 0.17 / 0.24 |
| productcatalogservice | 0.49 / 0.64 | 0.54 / 0.71 | **┃** | 0.46 / 0.61 | 0.45 / 0.60 | **┃** | 0.53 / 0.68 | 0.45 / 0.58 | **┃** | 0.46 / 0.61 | 0.44 / 0.57 | **┃** | 0.51 / 0.67 | 0.44 / 0.60 |
| cartservice | 0.32 / 0.44 | 0.35 / 0.46 | **┃** | 0.32 / 0.52 | 0.31 / 0.48 | **┃** | 0.36 / 0.57 | 0.33 / 0.55 | **┃** | 0.30 / 0.43 | 0.29 / 0.43 | **┃** | 0.33 / 0.56 | 0.30 / 0.45 |
| currencyservice | 0.30 / 0.39 | 0.32 / 0.42 | **┃** | 0.31 / 0.41 | 0.30 / 0.40 | **┃** | 0.33 / 0.42 | 0.31 / 0.40 | **┃** | 0.29 / 0.39 | 0.28 / 0.37 | **┃** | 0.31 / 0.41 | 0.29 / 0.40 |
| shippingservice | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.09 | 0.06 / 0.08 | **┃** | 0.07 / 0.09 | 0.07 / 0.08 | **┃** | 0.07 / 0.09 | 0.06 / 0.08 | **┃** | 0.07 / 0.09 | 0.06 / 0.09 |
| adservice | 0.09 / 0.13 | 0.09 / 0.12 | **┃** | 0.09 / 0.12 | 0.09 / 0.12 | **┃** | 0.09 / 0.11 | 0.09 / 0.12 | **┃** | 0.09 / 0.11 | 0.08 / 0.10 | **┃** | 0.08 / 0.11 | 0.09 / 0.12 |
| redis-cart | 0.06 / 0.11 | 0.07 / 0.11 | **┃** | 0.06 / 0.11 | 0.06 / 0.11 | **┃** | 0.07 / 0.11 | 0.06 / 0.11 | **┃** | 0.06 / 0.11 | 0.06 / 0.10 | **┃** | 0.06 / 0.11 | 0.06 / 0.11 |

## Detector max utilization

| Service | final_s3_rg_only_normal_run3 | final_s3_rg_only_normal_run4 | **┃** | final_s3_both_normal_run3 | final_s3_both_normal_run4 | **┃** | final_s3_tf_only_run3 | final_s3_tf_only_run4 | **┃** | final_s3_rg_only_burst_run3 | final_s3_rg_only_burst_run4 | **┃** | final_s3_both_burst_run3 | final_s3_both_burst_run4 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.319 | 0.340 | **┃** | 0.329 | 0.317 | **┃** | 0.332 | 0.305 | **┃** | 0.312 | 0.298 | **┃** | 0.325 | 0.304 |
| checkoutservice | 1.045 | 1.075 | **┃** | 1.080 | 1.080 | **┃** | 1.045 | 1.060 | **┃** | 1.055 | 1.050 | **┃** | 1.065 | 1.075 |
| recommendationservice | 0.519 | 0.513 | **┃** | 0.533 | 0.476 | **┃** | 0.491 | 0.469 | **┃** | 0.523 | 0.459 | **┃** | 0.474 | 0.497 |
| paymentservice | 0.329 | 0.316 | **┃** | 0.284 | 0.374 | **┃** | 0.284 | 0.400 | **┃** | 0.355 | 0.290 | **┃** | 0.310 | 0.284 |
| emailservice | 0.325 | 0.317 | **┃** | 0.425 | 0.450 | **┃** | 0.308 | 0.342 | **┃** | 0.425 | 0.317 | **┃** | 0.458 | 0.450 |
| productcatalogservice | 0.679 | 0.751 | **┃** | 0.661 | 0.632 | **┃** | 0.709 | 0.624 | **┃** | 0.642 | 0.611 | **┃** | 0.701 | 0.632 |
| cartservice | 0.497 | 0.519 | **┃** | 0.531 | 0.529 | **┃** | 0.596 | 0.560 | **┃** | 0.525 | 0.494 | **┃** | 0.580 | 0.492 |
| currencyservice | 0.434 | 0.474 | **┃** | 0.479 | 0.444 | **┃** | 0.453 | 0.464 | **┃** | 0.436 | 0.418 | **┃** | 0.470 | 0.436 |
| shippingservice | 0.116 | 0.123 | **┃** | 0.121 | 0.127 | **┃** | 0.127 | 0.117 | **┃** | 0.119 | 0.116 | **┃** | 0.117 | 0.119 |
| adservice | 0.215 | 0.141 | **┃** | 0.156 | 0.191 | **┃** | 0.139 | 0.144 | **┃** | 0.132 | 0.124 | **┃** | 0.143 | 0.133 |
| redis-cart | 0.341 | 0.402 | **┃** | 0.374 | 0.406 | **┃** | 0.346 | 0.317 | **┃** | 0.413 | 0.367 | **┃** | 0.380 | 0.335 |

No hold is FLAGGED. Cap and admitted-rate numbers are measured.

`postcart` and `emptycart` are no cap on every live read of every hold.

## Throttle data quality

Live reads of the TopFull proxy normally land every 5 s. A hold is **FLAGGED** when `topfull_throttle_collector.log` has any `fetch failed` WARNING, or when an API goes longer than 30 s without a fresh threshold or admitted read. Cap and admitted-rate numbers on a flagged hold are carried values; filter on `*_fresh==1` or drop the hold from those numbers. Goodput, P95 and rejection do not use this file.

| Hold | Status | Fetch warnings | First warning | Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |
| --- | --- | --- | --- | --- | --- |
| final_s3_rg_only_normal_run3 | ok | 0 | — | 5 | 5 |
| final_s3_rg_only_normal_run4 | ok | 0 | — | 5 | 5 |
| final_s3_both_normal_run3 | ok | 0 | — | 5 | 5 |
| final_s3_both_normal_run4 | ok | 0 | — | 5 | 5 |
| final_s3_tf_only_run3 | ok | 0 | — | 5 | 5 |
| final_s3_tf_only_run4 | ok | 0 | — | 5 | 5 |
| final_s3_rg_only_burst_run3 | ok | 0 | — | 5 | 5 |
| final_s3_rg_only_burst_run4 | ok | 0 | — | 5 | 5 |
| final_s3_both_burst_run3 | ok | 0 | — | 5 | 5 |
| final_s3_both_burst_run4 | ok | 0 | — | 5 | 5 |

## TopFull live caps

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### final_s3_rg_only_normal_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:36:30–00:48:15 |
| postcheckout | no cap 00:36:30–00:48:15 |
| getcart | no cap 00:36:30–00:48:15 |
| postcart | no cap 00:36:30–00:48:15 |
| emptycart | no cap 00:36:30–00:48:15 |

### final_s3_rg_only_normal_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:54:35–01:06:25 |
| postcheckout | no cap 00:54:35–01:06:25 |
| getcart | no cap 00:54:35–01:06:25 |
| postcart | no cap 00:54:35–01:06:25 |
| emptycart | no cap 00:54:35–01:06:25 |

### final_s3_both_normal_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:12:45–01:24:35 |
| postcheckout | no cap 01:12:45–01:14:40; 11 at 01:14:45; no cap at 01:14:47; 14 at 01:14:50; 10 01:14:55–01:15:10; 16.5 at 01:15:15; 10.3 at 01:15:20; 18.5 at 01:15:25; 13.6 at 01:15:30; 16.744 at 01:15:32; 11.7 at 01:15:35; 11.2362 at 01:15:36; 15.5 at 01:15:40; 15.3 at 01:15:45; 10 at 01:15:50; 15.5 at 01:15:55; 11.1351 at 01:15:59; 11.1 at 01:16:00; 15.9 at 01:16:05; 11 at 01:16:10; 17.3 at 01:16:15; 14.7 at 01:16:20; 11.7 at 01:16:25; 13.7 at 01:16:30; 19.3 at 01:16:35; 13.8375 at 01:16:38; 12 at 01:16:40; 16.9072 at 01:16:42; 18.2 at 01:16:45; 12.1 at 01:16:50; 16.5 at 01:16:55; 12.5 at 01:17:00; 16.2144 at 01:17:02; 14.9 at 01:17:05; 16.4 at 01:17:10; 14.1 at 01:17:15; 10 at 01:17:20; 17.9 at 01:17:25; 11.333 at 01:17:29; 11.3 at 01:17:30; 18.2 at 01:17:35; 10 at 01:17:40; 19.7 at 01:17:45; 13.7 at 01:17:50; 11.3 at 01:17:55; 14.9 at 01:18:00; 18.5 at 01:18:05; 12.5588 at 01:18:07; 10.8 at 01:18:10; 17.1 at 01:18:15; 13.7958 at 01:18:18; 15.5 at 01:18:20; 16.1291 at 01:18:22; 12.2 at 01:18:25; 15.1 at 01:18:30; 17.3 at 01:18:35; 13.6 at 01:18:40; 16.7338 at 01:18:42; 14.3 at 01:18:45; 12.8647 at 01:18:46; 15.7 at 01:18:50; 16.4 at 01:18:55; 10.3 at 01:19:00; 14.2846 at 01:19:02; 16.9 at 01:19:05; 16.9086 at 01:19:06; 10 at 01:19:10; 17.8 at 01:19:15; 14.4 at 01:19:20; 13.1 at 01:19:25; 12.4755 at 01:19:29; 12.5 at 01:19:30; 15.8 at 01:19:35; 10.6 at 01:19:40; 12.075 at 01:19:44; 12.1 at 01:19:45; 15.7077 at 01:19:48; 12.3 at 01:19:50; 16.4 at 01:19:55; 10 at 01:20:00; 18.1756 at 01:20:03; 14.4 at 01:20:05; 10.7 at 01:20:10; 16.2 at 01:20:15; 14.5 at 01:20:20; 10.7 at 01:20:25; 14.5 at 01:20:30; 17.2 at 01:20:35; 13.4 at 01:20:40; 19.3 at 01:20:45; 13.4 at 01:20:50; 15.2 at 01:20:55; 17.2 at 01:21:00; 13.3 at 01:21:05; 16.3 at 01:21:10; 16.2 at 01:21:15; 20.0676 at 01:21:17; 16 at 01:21:20; 12.2461 at 01:21:21; 17.7 at 01:21:25; 11.1 at 01:21:30; 16.5 at 01:21:35; 14.1168 at 01:21:36; 12.5 at 01:21:40; 14.2 at 01:21:45; 11.842 at 01:21:47; 14.6 at 01:21:50; 17.9885 at 01:21:51; 17.2 at 01:21:55; 14.3 at 01:22:00; 13.9256 at 01:22:03; 10.8 at 01:22:05; 16 at 01:22:10; 15.7652 at 01:22:11; 15.2 at 01:22:15; 13.1 at 01:22:20; 15.5154 at 01:22:22; 19.1 at 01:22:25; 10.9 at 01:22:30; 14.3 at 01:22:35; 16.1 at 01:22:40; 19.1735 at 01:22:41; 16 at 01:22:45; 17.9 at 01:22:50; 17.1 at 01:22:55; 19.6831 at 01:22:56; 13.1 at 01:23:00; 19.0817 at 01:23:04; 19.1 at 01:23:05; 11.8 at 01:23:10; 19.5 at 01:23:15; 10 01:23:19–01:23:20; 15.5 at 01:23:25; 14.7 at 01:23:30; 19.2 at 01:23:35; 11.4498 at 01:23:38; 13.6 at 01:23:40; 19.4201 at 01:23:42; 12.9 at 01:23:45; 15.1 at 01:23:50; 11.7 at 01:23:55; 16.1 at 01:24:00; 11.7 at 01:24:05; 16.7 at 01:24:10; 17.3 at 01:24:15; 20.618 at 01:24:17; 11.9 at 01:24:20; 18.8 at 01:24:25; 11.7 at 01:24:30; 18.8 at 01:24:35 |
| getcart | no cap 01:12:45–01:24:35 |
| postcart | no cap 01:12:45–01:24:35 |
| emptycart | no cap 01:12:45–01:24:35 |

### final_s3_both_normal_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:30:55–01:42:50 |
| postcheckout | no cap 01:30:55–01:32:50; 10 at 01:32:55; no cap at 01:33:00; 10 01:33:05–01:33:20; 13.2 at 01:33:25; 15.3 at 01:33:30; 15.6 at 01:33:35; 13.1 at 01:33:40; 13.9 at 01:33:45; 17.5 at 01:33:50; 17.1 at 01:33:55; 10.8 at 01:34:00; 10 at 01:34:01; 17.7 at 01:34:05; 13.3 at 01:34:10; 17.838 at 01:34:12; 18.2 at 01:34:15; 15.3164 at 01:34:16; 10.8 at 01:34:20; 15.8005 at 01:34:24; 15.8 at 01:34:25; 13.9751 at 01:34:28; 17.4 at 01:34:30; 18.8137 at 01:34:31; 13.8 at 01:34:35; 15.9 at 01:34:40; 21.8 at 01:34:45; 22.4088 at 01:34:46; 12.4 at 01:34:50; 19.8 at 01:34:55; 10.3 at 01:35:00; 16.6 at 01:35:05; 14.9604 at 01:35:09; 15 at 01:35:10; 15.0251 at 01:35:13; 18.4 at 01:35:15; 13.5 at 01:35:20; 19.7 at 01:35:25; 12 at 01:35:30; 21.5 at 01:35:35; 10.1 at 01:35:40; 19 at 01:35:45; 12.4 at 01:35:50; 18.3 at 01:35:55; 10 at 01:36:00; 20.2 at 01:36:05; 14.2 at 01:36:10; 18.7 at 01:36:15; 13.4735 at 01:36:19; 13.5 at 01:36:20; 16.6 at 01:36:25; 12.6 at 01:36:30; 19 at 01:36:35; 13.9224 at 01:36:37; 11.4 at 01:36:40; 16.9 at 01:36:45; 17.2 at 01:36:50; 13.3 at 01:36:55; 15.8 at 01:37:00; 15.6696 at 01:37:03; 17.2 at 01:37:05; 13.8969 at 01:37:07; 12.3 at 01:37:10; 16.1 at 01:37:15; 15.5 at 01:37:20; 17.2 at 01:37:25; 18.2 at 01:37:30; 17.4 at 01:37:35; 12.5 at 01:37:40; 18.9 at 01:37:45; 10.8 at 01:37:50; 18.4 at 01:37:55; 11.9 at 01:38:00; 19.1 at 01:38:05; 12.8 at 01:38:10; 19.9202 at 01:38:13; 19.2 at 01:38:15; 12.0014 at 01:38:17; 15.7 at 01:38:20; 17.1 at 01:38:25; 14.2 at 01:38:30; 17.5 at 01:38:35; 11.3 at 01:38:40; 15.4 at 01:38:45; 13.1656 at 01:38:48; 15.2 at 01:38:50; 17.6 at 01:38:55; 16.615 at 01:38:59; 16.6 at 01:39:00; 18.8 at 01:39:05; 11.7 at 01:39:10; 19.9 at 01:39:15; 14.6104 at 01:39:18; 17.1 at 01:39:20; 14.4 at 01:39:25; 16.2 at 01:39:30; 15 at 01:39:35; 13.6913 at 01:39:37; 11.5 at 01:39:40; 15.6 at 01:39:45; 15.1 at 01:39:50; 19.8 at 01:39:55; 10 at 01:40:00; 16.3 at 01:40:05; 14.2 at 01:40:10; 19.2 at 01:40:15; 10.812 at 01:40:19; 10.8 at 01:40:20; 15.1 at 01:40:25; 15.6 at 01:40:30; 10.3332 at 01:40:34; 10.3 at 01:40:35; 16.6654 at 01:40:37; 18.4 at 01:40:40; 13.2504 at 01:40:41; 12.9 at 01:40:45; 13.0458 at 01:40:49; 13 at 01:40:50; 14.3 at 01:40:55; 17.8 at 01:41:00; 10.7 at 01:41:05; 16 at 01:41:10; 17.8 at 01:41:15; 11.1 at 01:41:20; 17.4 at 01:41:25; 11.6751 at 01:41:28; 13.8 at 01:41:30; 16.1385 at 01:41:32; 18.7 at 01:41:35; 10.1 at 01:41:40; 13.6274 at 01:41:44; 13.6 at 01:41:45; 16.8 at 01:41:50; 13.3584 at 01:41:51; 11.4 at 01:41:55; 14.1295 at 01:41:59; 14.1 at 01:42:00; 15.1901 at 01:42:03; 18.2 at 01:42:05; 11.1 at 01:42:10; 17.8 at 01:42:15; 13.7245 at 01:42:18; 13.3 at 01:42:20; 17.1 at 01:42:25; 11.7 at 01:42:30; 19.2 at 01:42:35; 12.1 at 01:42:40; 18.6 at 01:42:45; 11 at 01:42:50 |
| getcart | no cap 01:30:55–01:42:50 |
| postcart | no cap 01:30:55–01:42:50 |
| emptycart | no cap 01:30:55–01:42:50 |

### final_s3_tf_only_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:49:05–02:00:30 |
| postcheckout | no cap 01:49:05–01:50:30; 10 01:50:34–01:50:35; no cap at 01:50:40; 10 01:50:44–02:00:30 |
| getcart | no cap 01:49:05–02:00:30 |
| postcart | no cap 01:49:05–02:00:30 |
| emptycart | no cap 01:49:05–02:00:30 |

### final_s3_tf_only_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:06:25–02:17:50 |
| postcheckout | no cap 02:06:25–02:07:55; 10 at 02:08:00; 13 at 02:08:03; 15.4 at 02:08:05; 10 02:08:10–02:17:50 |
| getcart | no cap 02:06:25–02:17:50 |
| postcart | no cap 02:06:25–02:17:50 |
| emptycart | no cap 02:06:25–02:17:50 |

### final_s3_rg_only_burst_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:23:50–02:35:40 |
| postcheckout | no cap 02:23:50–02:35:40 |
| getcart | no cap 02:23:50–02:35:40 |
| postcart | no cap 02:23:50–02:35:40 |
| emptycart | no cap 02:23:50–02:35:40 |

### final_s3_rg_only_burst_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:41:55–02:53:45 |
| postcheckout | no cap 02:41:55–02:53:45 |
| getcart | no cap 02:41:55–02:53:45 |
| postcart | no cap 02:41:55–02:53:45 |
| emptycart | no cap 02:41:55–02:53:45 |

### final_s3_both_burst_run3

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:00:00–03:11:50 |
| postcheckout | no cap 03:00:00–03:01:55; 10 at 03:02:00; no cap at 03:02:02; 12 at 03:02:05; 10 03:02:10–03:02:25; 14.4 at 03:02:30; 16.9 at 03:02:35; 16.6 at 03:02:40; 15.9 at 03:02:45; 17.9474 at 03:02:49; 17.9 at 03:02:50; 14.8 at 03:02:55; 19.9 at 03:03:00; 13.1 at 03:03:05; 17.2 at 03:03:10; 14.4 at 03:03:15; 18.8 at 03:03:20; 14.9 at 03:03:25; 17.3 at 03:03:30; 17.2 at 03:03:35; 10.1 at 03:03:40; 19 at 03:03:45; 10 at 03:03:50; 18.6097 at 03:03:54; 18.6 at 03:03:55; 11.958 at 03:03:58; 11.8 at 03:04:00; 19.5 at 03:04:05; 15.2692 at 03:04:06; 11.5 at 03:04:10; 20.4 at 03:04:15; 13.6 at 03:04:20; 11.1 at 03:04:25; 16.5 at 03:04:30; 19.0134 at 03:04:31; 13.1 at 03:04:35; 15.8 at 03:04:40; 15.3 at 03:04:45; 18.6 at 03:04:50; 14.2 at 03:04:55; 15.5 at 03:05:00; 20.5 at 03:05:05; 13.8 at 03:05:10; 13.3 at 03:05:15; 18.3 at 03:05:20; 11.2782 at 03:05:24; 11.3 at 03:05:25; 15.5 at 03:05:30; 20.8 at 03:05:35; 10 at 03:05:40; 15 at 03:05:45; 19.7 at 03:05:50; 12.9 at 03:05:55; 15.4788 at 03:05:59; 15.5 at 03:06:00; 17.6542 at 03:06:03; 20.2 at 03:06:05; 13.3443 at 03:06:07; 10 at 03:06:10; 19.3 at 03:06:15; 10 at 03:06:18; 12.5 at 03:06:20; 18.1 at 03:06:25; 15.7 at 03:06:30; 17.1 at 03:06:35; 13.2 at 03:06:40; 19.1 at 03:06:45; 11.4 at 03:06:50; 15.7 at 03:06:55; 12.5859 at 03:06:58; 17.6 at 03:07:00; 10.2 at 03:07:05; 16.3 at 03:07:10; 18.2107 at 03:07:14; 18.2 at 03:07:15; 10 at 03:07:18; 14 at 03:07:20; 18 at 03:07:25; 10 03:07:29–03:07:30; 18.1676 at 03:07:33; 18.1 at 03:07:35; 11.9 at 03:07:40; 17.1 at 03:07:45; 12.8 at 03:07:50; 13.7472 at 03:07:54; 13.7 at 03:07:55; 14.5 at 03:08:00; 18.0809 at 03:08:01; 13.4 at 03:08:05; 17.5 at 03:08:10; 11.9095 at 03:08:12; 10 at 03:08:15; 18.6009 at 03:08:19; 18.6 at 03:08:20; 15.5 at 03:08:25; 11.2 at 03:08:30; 17 at 03:08:35; 14.6584 at 03:08:39; 14.7 at 03:08:40; 19.3 at 03:08:45; 10 at 03:08:50; 17.2 at 03:08:55; 15.9762 at 03:08:57; 15 at 03:09:00; 17.5 at 03:09:05; 10.7141 at 03:09:07; 11.7 at 03:09:10; 14.9 at 03:09:15; 11.992 at 03:09:17; 15.9 at 03:09:20; 14.2152 at 03:09:24; 14.2 at 03:09:25; 17.2 at 03:09:30; 14.7622 at 03:09:31; 19.2 at 03:09:35; 11.1 at 03:09:40; 18.5 at 03:09:45; 11.2 at 03:09:50; 17.4 at 03:09:55; 14.3 at 03:10:00; 16.7 at 03:10:05; 20.3 at 03:10:10; 13.957 at 03:10:13; 11.7 at 03:10:15; 14.3009 at 03:10:17; 18.8 at 03:10:20; 14.8 at 03:10:25; 13.8 at 03:10:30; 20.3 at 03:10:35; 12.4 at 03:10:40; 18.2 at 03:10:45; 12.6 at 03:10:50; 18.0355 at 03:10:54; 18 at 03:10:55; 16 at 03:11:00; 12.1739 at 03:11:01; 18 at 03:11:05; 14.5 at 03:11:10; 19.3431 at 03:11:14; 19.3 at 03:11:15; 15.1 at 03:11:20; 17.4931 at 03:11:21; 18.9 at 03:11:25; 11.1 at 03:11:30; 16.7 at 03:11:35; 14.4 at 03:11:40; 18.8006 at 03:11:42; 22.4 at 03:11:45; 18.2509 at 03:11:46; 10 at 03:11:50 |
| getcart | no cap 03:00:00–03:11:50 |
| postcart | no cap 03:00:00–03:11:50 |
| emptycart | no cap 03:00:00–03:11:50 |

### final_s3_both_burst_run4

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:18:10–03:30:00 |
| postcheckout | no cap 03:18:10–03:20:05; 10 at 03:20:10; no cap at 03:20:11; 13.7 at 03:20:15; 10 03:20:20–03:20:25; 12.9 at 03:20:30; 13.2 at 03:20:35; 14.2 at 03:20:40; 14.6 at 03:20:45; 14.4792 at 03:20:46; 12.2 at 03:20:50; 16.7 at 03:20:55; 15.4 at 03:21:00; 12.6 at 03:21:05; 12.0075 at 03:21:07; 16.2 at 03:21:10; 18.2204 at 03:21:11; 11.6 at 03:21:15; 16.9 at 03:21:20; 14 at 03:21:25; 11.7 at 03:21:30; 15.8675 at 03:21:32; 18.5 at 03:21:35; 14.2434 at 03:21:36; 10.9 at 03:21:40; 22.4 at 03:21:45; 10 at 03:21:50; 13.5165 at 03:21:51; 17.9 at 03:21:55; 10.1 at 03:22:00; 13.1 at 03:22:05; 16.4 at 03:22:10; 14 at 03:22:15; 18.3 at 03:22:20; 10.4 at 03:22:25; 16.4 at 03:22:30; 17.1074 at 03:22:32; 17.5 at 03:22:35; 10.1926 at 03:22:36; 16 at 03:22:40; 14.4725 at 03:22:44; 14.5 at 03:22:45; 12.8 at 03:22:50; 20 at 03:22:55; 11.2 at 03:23:00; 16.3 at 03:23:05; 16.8 at 03:23:10; 14.8 at 03:23:15; 16.969 at 03:23:16; 16.1 at 03:23:20; 20 at 03:23:25; 10.6829 at 03:23:28; 11 at 03:23:30; 18.6 at 03:23:35; 10 at 03:23:40; 15.8 at 03:23:45; 17.9 at 03:23:50; 20.8207 at 03:23:51; 17.5 at 03:23:55; 16.9 at 03:24:00; 11.8 at 03:24:05; 16.8 at 03:24:10; 18.0144 at 03:24:14; 18 at 03:24:15; 10.8 at 03:24:20; 16.3 at 03:24:25; 16 at 03:24:30; 18.2 at 03:24:35; 12.4 at 03:24:40; 16 at 03:24:45; 18.3 at 03:24:50; 12.8 at 03:24:55; 15.2987 at 03:24:59; 15.3 at 03:25:00; 14.0371 at 03:25:03; 17.3 at 03:25:05; 10.6 at 03:25:10; 19.7 at 03:25:15; 10.2274 at 03:25:19; 10.2 at 03:25:20; 21.5 at 03:25:25; 10.1 at 03:25:30; 17.5 at 03:25:35; 10.2 at 03:25:40; 18 at 03:25:45; 14.2 at 03:25:50; 19 at 03:25:55; 11.5654 at 03:25:56; 14.8 at 03:26:00; 12.3364 at 03:26:04; 12.3 at 03:26:05; 18.5 at 03:26:10; 10.9 at 03:26:15; 16.8 at 03:26:20; 11.1 at 03:26:25; 17.5 at 03:26:30; 17.8 at 03:26:35; 19.0993 at 03:26:37; 10.8 at 03:26:40; 14.606 at 03:26:41; 18.8 at 03:26:45; 11.3 at 03:26:50; 14.7 at 03:26:55; 14.5405 at 03:26:58; 18.7 at 03:27:00; 17.52 at 03:27:02; 10 at 03:27:05; 20 at 03:27:10; 10 at 03:27:15; 13.4 at 03:27:20; 16.8 at 03:27:25; 15.1909 at 03:27:27; 10.5 at 03:27:30; 14.6138 at 03:27:31; 19.4 at 03:27:35; 10 at 03:27:40; 18.5 at 03:27:45; 10.9 at 03:27:50; 21.1 at 03:27:55; 10.9 at 03:28:00; 16.7 at 03:28:05; 17.2 at 03:28:10; 12.8 at 03:28:15; 14.0554 at 03:28:16; 17.2 at 03:28:20; 13.6 at 03:28:25; 16.9 at 03:28:30; 12.3 at 03:28:35; 17.7 at 03:28:40; 15.3 at 03:28:45; 13.6 at 03:28:50; 18.6 at 03:28:55; 11.7 at 03:29:00; 21.1 at 03:29:05; 13.8 at 03:29:10; 19.399 at 03:29:13; 14.1 at 03:29:15; 10.9505 at 03:29:17; 19.3 at 03:29:20; 13.1 at 03:29:25; 17.1 at 03:29:30; 14.2 03:29:35–03:29:40; 18.5 at 03:29:45; 11.5071 at 03:29:49; 11.5 at 03:29:50; 15.7 at 03:29:55; 18.3 at 03:30:00 |
| getcart | no cap 03:18:10–03:30:00 |
| postcart | no cap 03:18:10–03:30:00 |
| emptycart | no cap 03:18:10–03:30:00 |

## One paragraph per launch

`final_s3_rg_only_normal_run3`: frontend → checkoutservice 1 / 0 shed rpr 1.50 last attempts 0. Outbound retry delta: checkoutservice 614. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **596/712 (83.7%)**.

`final_s3_rg_only_normal_run4`: frontend → checkoutservice 1 / 0 shed rpr 1.61 last attempts 0. Outbound retry delta: checkoutservice 482. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **596/714 (83.5%)**.

`final_s3_both_normal_run3`: frontend → checkoutservice 1 / 0 shed rpr 1.80 last attempts 0. Outbound retry delta: checkoutservice 435. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **596/717 (83.1%)**.

`final_s3_both_normal_run4`: frontend → checkoutservice 1 / 0 shed rpr 2.18 last attempts 0. Outbound retry delta: checkoutservice 465. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **597/717 (83.3%)**.

`final_s3_tf_only_run3`: no retryguard.log. Outbound retry delta: checkoutservice 12,197. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **597/690 (86.5%)**.

`final_s3_tf_only_run4`: no retryguard.log. Outbound retry delta: checkoutservice 12,011. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **596/690 (86.4%)**.

`final_s3_rg_only_burst_run3`: frontend → checkoutservice 1 (1) / 0 shed rpr 2.12b last attempts 0. Outbound retry delta: checkoutservice 564. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **598/715 (83.6%)**.

`final_s3_rg_only_burst_run4`: frontend → checkoutservice 1 (1) / 0 shed rpr 2.09b last attempts 0. Outbound retry delta: checkoutservice 154. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **594/713 (83.3%)**.

`final_s3_both_burst_run3`: frontend → checkoutservice 2 (2) / 1 shed rpr 2.08b; 0.70b last attempts 0. Outbound retry delta: checkoutservice 382. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **596/716 (83.2%)**.

`final_s3_both_burst_run4`: frontend → checkoutservice 1 (1) / 0 shed rpr 2.47b last attempts 0. Outbound retry delta: checkoutservice 165. grpc_4 / grpc_14: recommendationservice 0 / 0, productcatalogservice 0 / 0, currencyservice 0 / 0, adservice 0 / 0. Detector-hot: checkoutservice **595/715 (83.2%)**.

## Related

This campaign's plan is [2026-10-15-s1-s3-mode-matrix.md](../../docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md). The run log is [2026-10-15-s3-mode-matrix-run-log.md](../../docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md). Template: [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). The (a)/(b)/(c) reading is [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Controller: [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md). [ADR 0006](../../docs/adr/0006-absolute-bottleneck-cap-not-fraction.md), [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../docs/adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../../docs/adr/0009-paper-c1-default-cpu-table.md). `final_s3_*_run1`, `final_s3_*_run2`, `s3_ck200_rgtf1`, and `campaign_48/` S3 are not columns.
