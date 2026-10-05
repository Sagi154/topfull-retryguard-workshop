# S2 controller arms, nine holds

600 s holds on Paper-C1, `spawn_rate` 50, Istio `attempts: 3`, `perTryTimeout` 500 ms. Frontend HPA pinned at 4, catalog HPA at 1, sidecar request 100 m with no CPU limit. Checkout and recommendations were rolled before each hold. 360 s cool-off between holds inside a mix. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).

These slot numbers are the controller-arm folders under `experiments/results/campaign_48/S2_sustained_overload/`. They are not the both-off holds that reuse some of the same numbers.

(a), (b), and (c) are from `experiments/s2_both_off_abc.py` on the full inbound file. The other inbound tables drop the last 5 polls. Locust tables drop the first 30 rows and the last 5. **Bold** in (a) is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain there. **Bold** in (b) is an overloaded share of at least 0.5.

run4's collectors ran long (Locust `total.csv` 1043 rows, mesh span 1247 s, 1185 detector ticks). run33 and run18 have checkout inbound gap2 of 78% and 77% (393 and 411 polls), so their (a) streaks are not a 1 s series. (b) on those two holds is still the 1 s detector clock.

## Hold index

| Mix | Arm | Column | Folder | Locust rows | Mesh span | Checkout gap2 |
|---|---|---|---|---:|---:|---:|
| 275 / 90 / 100 / 90 / 5 | RetryGuard only | run4 | `run_retryguard_no_topfull_sustained_overload_run4` | 1043 | 1247 s | 0% |
| 275 / 90 / 100 / 90 / 5 | TopFull only | run31 | `baseline_topfull_no_retryguard_sustained_overload_run31` | 562 | 691 s | 0% |
| 275 / 90 / 100 / 90 / 5 | Both on | run16 | `run_topfull_retryguard_sustained_overload_run16` | 561 | 718 s | 0% |
| 325 / 90 / 150 / 90 / 5 | RetryGuard only | run5 | `run_retryguard_no_topfull_sustained_overload_run5` | 561 | 726 s | 0% |
| 325 / 90 / 150 / 90 / 5 | TopFull only | run32 | `baseline_topfull_no_retryguard_sustained_overload_run32` | 552 | 694 s | 10% |
| 325 / 90 / 150 / 90 / 5 | Both on | run17 | `run_topfull_retryguard_sustained_overload_run17` | 552 | 720 s | 5% |
| 325 / 115 / 150 / 90 / 5 | RetryGuard only | run6 | `run_retryguard_no_topfull_sustained_overload_run6` | 561 | 721 s | 7% |
| 325 / 115 / 150 / 90 / 5 | TopFull only | run33 | `baseline_topfull_no_retryguard_sustained_overload_run33` | 550 | 698 s | 78% |
| 325 / 115 / 150 / 90 / 5 | Both on | run18 | `run_topfull_retryguard_sustained_overload_run18` | 557 | 727 s | 77% |

The tables use that column order. A bold bar separates the three mixes.

Per-pod millicores, request equals limit. Replicas are the Paper-C1 pin. Frontend is 4; every other service is 1. `cpu_millicores` in `resource_usage.csv` is the sum across replicas.

| Service | Quota | Replicas |
|---|---:|---:|
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

Frontend stayed at 4 replicas on every resource sample of all nine holds.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend (not controlled) | 1 / 1 | 2 / 2 | 0 / 0 | **┃** | 7 / 126 | 25 / 228 | 132 / 473 | **┃** | 76 / 323 | 249 / 281 | 16 / 137 |
| checkoutservice | **37 / 543** | 8 / 194 | 8 / 189 | **┃** | 1 / 1 | 1 / 1 | 0 / 0 | **┃** | **33 / 209** | 3 / 3 | 4 / 4 |
| recommendationservice | 1 / 1 | 1 / 1 | 1 / 1 | **┃** | 8 / 170 | 20 / 168 | **31 / 238** | **┃** | **32 / 293** | **187 / 284** | 20 / 235 |
| paymentservice | 1 / 1 | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 17 / 22 | 0 / 0 | 0 / 0 |
| emailservice | 13 / 236 | 6 / 101 | 6 / 97 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 5 / 86 | 0 / 0 | 1 / 2 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows (threshold neither 0 nor 10000), any API: run4 0, run31 563, run16 577, run5 0, run32 579, run17 584, run6 0, run33 595, run18 1,724. On run4, run5, and run6 the postcheckout threshold ended at the 10000 passthrough. On the TopFull arms it ended at 34.5 (run31), 10.0 (run16), 62.5 (run32), 76.0 (run17), 38.9 (run33), and 50.5 (run18). run18 also capped getproduct (ended 299.9, 570/667 rows) and getcart (ended 148.9, 572/667 rows). The other TopFull holds capped postcheckout only.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| checkoutservice | **1088/1185 (91.8%)** | **367/636 (57.7%)** | **364/662 (55.0%)** | **┃** | **424/666 (63.7%)** | 189/638 (29.6%) | 139/663 (21.0%) | **┃** | 304/664 (45.8%) | 18/638 (2.8%) | 129/667 (19.3%) |
| recommendationservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | **500/666 (75.1%)** | **558/638 (87.5%)** | **530/663 (79.9%)** | **┃** | 324/664 (48.8%) | **567/638 (88.9%)** | **569/667 (85.3%)** |
| paymentservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 23/664 (3.5%) | 0/638 (0.0%) | 0/667 (0.0%) |
| emailservice | 550/1185 (46.4%) | 104/636 (16.4%) | 108/662 (16.3%) | **┃** | 95/666 (14.3%) | 39/638 (6.1%) | 64/663 (9.7%) | **┃** | 46/664 (6.9%) | 9/638 (1.4%) | 25/667 (3.7%) |
| productcatalogservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| cartservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| currencyservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| shippingservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| adservice | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |
| redis-cart | 0/1185 (0.0%) | 0/636 (0.0%) | 0/662 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/663 (0.0%) | **┃** | 0/664 (0.0%) | 0/638 (0.0%) | 0/667 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target: the sum of positive Envoy `retry` increments into that service.

- **run4.** frontend → checkoutservice 58,472, checkoutservice → emailservice 2,679.
- **run31.** frontend → checkoutservice 18,919.
- **run16.** frontend → checkoutservice 18,731, frontend → recommendationservice 2.
- **run5.** frontend → recommendationservice 136,554, frontend → checkoutservice 35.
- **run32.** frontend → recommendationservice 148,394, frontend → checkoutservice 65.
- **run17.** frontend → recommendationservice 173,635, frontend → checkoutservice 24.
- **run6.** frontend → recommendationservice 155,116, frontend → checkoutservice 18,973, checkoutservice → emailservice 60, checkoutservice → paymentservice 42, frontend → cartservice 3.
- **run33.** frontend → recommendationservice 221,036, frontend → checkoutservice 471.
- **run18.** frontend → recommendationservice 161,507, frontend → checkoutservice 650.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| checkoutservice | 58,472 | 18,919 | 18,731 | **┃** | 35 | 65 | 24 | **┃** | 18,973 | 471 | 650 |
| recommendationservice | 0 | 0 | 2 | **┃** | 136,554 | 148,394 | 173,635 | **┃** | 155,116 | 221,036 | 161,507 |
| paymentservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 42 | 0 | 0 |
| emailservice | 2,679 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 60 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 3 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |

## CPU mean / max

App-container millicores, mean / max. Quota is the per-pod CPU limit. The mean / max cells sum that usage across replicas. Frontend is 4 replicas, so its mean can sit above 1150.

| Service | Quota | Replicas | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 1150 | 4 | 1358 / 1554 | 1315 / 1538 | 1284 / 1562 | **┃** | 1210 / 1548 | 1260 / 1550 | 1182 / 1613 | **┃** | 1191 / 1627 | 1249 / 1645 | 1265 / 1639 |
| checkoutservice | 800 | 1 | 719 / 800 | 562 / 794 | 542 / 795 | **┃** | 572 / 759 | 540 / 755 | 504 / 782 | **┃** | 484 / 799 | 407 / 797 | 474 / 771 |
| recommendationservice | 1150 | 1 | 672 / 792 | 622 / 755 | 618 / 795 | **┃** | 798 / 995 | 844 / 1002 | 826 / 1053 | **┃** | 750 / 1151 | 915 / 1133 | 877 / 1132 |
| paymentservice | 155 | 1 | 65 / 90 | 46 / 74 | 44 / 76 | **┃** | 39 / 57 | 37 / 60 | 35 / 58 | **┃** | 50 / 154 | 28 / 70 | 34 / 65 |
| emailservice | 120 | 1 | 60 / 120 | 51 / 106 | 50 / 115 | **┃** | 74 / 104 | 68 / 105 | 65 / 107 | **┃** | 39 / 97 | 49 / 81 | 59 / 86 |
| productcatalogservice | 800 | 1 | 462 / 518 | 452 / 524 | 441 / 532 | **┃** | 398 / 513 | 414 / 503 | 382 / 504 | **┃** | 387 / 510 | 422 / 559 | 441 / 568 |
| cartservice | 800 | 1 | 306 / 444 | 314 / 450 | 302 / 439 | **┃** | 308 / 392 | 338 / 501 | 330 / 514 | **┃** | 406 / 578 | 421 / 517 | 398 / 548 |
| currencyservice | 770 | 1 | 359 / 417 | 343 / 408 | 333 / 446 | **┃** | 336 / 417 | 351 / 425 | 334 / 452 | **┃** | 352 / 492 | 351 / 438 | 354 / 500 |
| shippingservice | 770 | 1 | 94 / 110 | 80 / 106 | 79 / 110 | **┃** | 88 / 114 | 86 / 109 | 78 / 135 | **┃** | 80 / 149 | 71 / 112 | 83 / 116 |
| adservice | 1150 | 1 | 142 / 176 | 139 / 166 | 138 / 172 | **┃** | 115 / 156 | 116 / 163 | 103 / 172 | **┃** | 133 / 461 | 106 / 176 | 120 / 176 |
| redis-cart | 540 | 1 | 36 / 44 | 36 / 45 | 36 / 45 | **┃** | 37 / 49 | 39 / 49 | 38 / 48 | **┃** | 40 / 54 | 42 / 54 | 40 / 53 |

## Locust goodput

Mean `Goodput` (req/s) on rows 30 through the fifth from the end.

| API | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 274.1 | 273.4 | 273.3 | **┃** | 145.3 | 141.4 | 126.3 | **┃** | 101.0 | 71.7 | 104.7 |
| postcheckout | 44.4 | 29.8 | 29.8 | **┃** | 37.6 | 33.5 | 30.9 | **┃** | 7.8 | 15.5 | 23.1 |
| getcart | 99.6 | 99.4 | 99.5 | **┃** | 72.7 | 71.8 | 62.1 | **┃** | 51.7 | 40.9 | 56.1 |
| postcart | 89.7 | 89.5 | 89.5 | **┃** | 76.6 | 78.9 | 80.0 | **┃** | 69.2 | 77.1 | 72.0 |
| emptycart | 5.0 | 5.0 | 5.0 | **┃** | 3.8 | 3.8 | 4.7 | **┃** | 4.2 | 4.5 | 3.7 |

## Locust fail rate

`Fail / RPS` summed over those same rows. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 0.000 | 0.000 | 0.000 | **┃** | 0.493 | 0.476 | 0.487 | **┃** | 0.557 | 0.663 | 0.604 |
| postcheckout | 0.360 | 0.620 | 0.620 | **┃** | 0.513 | 0.560 | 0.540 | **┃** | 0.870 | 0.830 | 0.775 |
| getcart | 0.000 | 0.000 | 0.000 | **┃** | 0.460 | 0.444 | 0.468 | **┃** | 0.521 | 0.607 | 0.557 |
| postcart | 0.000 | 0.000 | 0.000 | **┃** | 0.144 | 0.089 | 0.034 | **┃** | 0.111 | 0.046 | 0.187 |
| emptycart | 0.000 | 0.000 | 0.000 | **┃** | 0.236 | 0.238 | 0.065 | **┃** | 0.151 | 0.100 | 0.257 |

## Locust P95

Mean `Latency95` (ms) on those same rows.

| API | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 274 | 260 | 259 | **┃** | 2038 | 2068 | 2040 | **┃** | 1703 | 2162 | 2102 |
| postcheckout | 1533 | 992 | 987 | **┃** | 2033 | 1995 | 2041 | **┃** | 2442 | 2061 | 1897 |
| getcart | 293 | 273 | 275 | **┃** | 1879 | 1946 | 1986 | **┃** | 1639 | 2091 | 2016 |
| postcart | 68 | 66 | 67 | **┃** | 67 | 67 | 66 | **┃** | 69 | 68 | 69 |
| emptycart | 17 | 10 | 19 | **┃** | 16 | 18 | 13 | **┃** | 15 | 17 | 20 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, last 5 polls dropped. redis-cart has no HTTP inbound counters.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 479.4 | 439.2 | 422.6 | **┃** | 399.7 | 430.5 | 413.1 | **┃** | 356.3 | 362.7 | 348.1 |
| checkoutservice | 108.7 | 65.9 | 63.4 | **┃** | 41.1 | 38.0 | 36.4 | **┃** | 51.2 | 21.3 | 27.0 |
| recommendationservice | 394.9 | 358.0 | 344.4 | **┃** | 521.9 | 573.8 | 584.5 | **┃** | 509.4 | 609.6 | 508.5 |
| paymentservice | 102.1 | 64.1 | 61.2 | **┃** | 41.1 | 38.0 | 36.4 | **┃** | 49.3 | 21.3 | 26.9 |
| emailservice | 44.8 | 32.1 | 30.3 | **┃** | 41.2 | 38.0 | 36.4 | **┃** | 17.0 | 20.5 | 26.0 |
| productcatalogservice | 2693.4 | 2458.3 | 2365.1 | **┃** | 1992.6 | 2076.3 | 1837.3 | **┃** | 1518.2 | 1533.4 | 1679.9 |
| cartservice | 576.7 | 505.4 | 484.5 | **┃** | 429.8 | 456.8 | 432.1 | **┃** | 385.3 | 372.2 | 366.6 |
| currencyservice | 815.7 | 732.3 | 704.5 | **┃** | 630.4 | 674.4 | 624.3 | **┃** | 540.4 | 532.8 | 538.1 |
| shippingservice | 272.5 | 204.6 | 195.0 | **┃** | 156.6 | 154.5 | 137.7 | **┃** | 140.3 | 96.8 | 115.9 |
| adservice | 244.2 | 234.1 | 225.2 | **┃** | 156.5 | 162.6 | 137.2 | **┃** | 112.8 | 109.5 | 129.9 |
| redis-cart | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal, last 5 polls dropped.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.043 | 0.025 | 0.025 | **┃** | 0.154 | 0.186 | 0.253 | **┃** | 0.321 | 0.299 | 0.194 |
| checkoutservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal, last 5 polls dropped.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| checkoutservice | 0.334 | 0.301 | 0.313 | **┃** | 0.001 | 0.002 | 0.000 | **┃** | 0.433 | 0.026 | 0.028 |
| recommendationservice | 0.000 | 0.000 | 0.000 | **┃** | 0.173 | 0.180 | 0.188 | **┃** | 0.204 | 0.302 | 0.233 |
| paymentservice | 0.022 | 0.011 | 0.012 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.081 | 0.000 | 0.001 |
| emailservice | 0.052 | 0.058 | 0.057 | **┃** | 0.001 | 0.001 | 0.001 | **┃** | 0.055 | 0.003 | 0.003 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| cartservice | 0.003 | 0.003 | 0.002 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.003 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.013 | 0.007 | 0.008 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.010 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count, last 5 polls dropped.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 231 | 165 | 169 | **┃** | 680 | 694 | 756 | **┃** | 937 | 885 | 765 |
| checkoutservice | 461 | 313 | 313 | **┃** | 115 | 99 | 106 | **┃** | 333 | 80 | 100 |
| recommendationservice | 65 | 56 | 58 | **┃** | 450 | 455 | 479 | **┃** | 569 | 465 | 450 |
| paymentservice | 5 | 5 | 5 | **┃** | 2 | 2 | 2 | **┃** | 14 | 3 | 3 |
| emailservice | 117 | 32 | 33 | **┃** | 19 | 16 | 16 | **┃** | 32 | 13 | 14 |
| productcatalogservice | 2 | 2 | 2 | **┃** | 2 | 2 | 2 | **┃** | 3 | 3 | 2 |
| cartservice | 4 | 3 | 3 | **┃** | 3 | 3 | 3 | **┃** | 3 | 3 | 3 |
| currencyservice | 4 | 3 | 3 | **┃** | 3 | 3 | 2 | **┃** | 3 | 3 | 4 |
| shippingservice | 2 | 1 | 1 | **┃** | 1 | 1 | 1 | **┃** | 1 | 1 | 1 |
| adservice | 1 | 1 | 1 | **┃** | 1 | 1 | 1 | **┃** | 2 | 1 | 1 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets`, last 5 polls dropped.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.089 | 0.036 | 0.037 | **┃** | 0.711 | 0.725 | 0.759 | **┃** | 0.774 | 0.741 | 0.707 |
| checkoutservice | 0.579 | 0.395 | 0.387 | **┃** | 0.001 | 0.001 | 0.001 | **┃** | 0.489 | 0.017 | 0.018 |
| recommendationservice | 0.000 | 0.000 | 0.000 | **┃** | 0.421 | 0.461 | 0.593 | **┃** | 0.834 | 0.607 | 0.471 |
| paymentservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| emailservice | 0.040 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.004 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (per-pod limit × replica_count)`. The limit and replica count are the Paper-C1 snapshot in `service_capacity.json`.

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 0.30 / 0.34 | 0.29 / 0.33 | 0.28 / 0.34 | **┃** | 0.26 / 0.34 | 0.27 / 0.34 | 0.26 / 0.35 | **┃** | 0.26 / 0.35 | 0.27 / 0.36 | 0.28 / 0.36 |
| checkoutservice | 0.90 / 1.00 | 0.70 / 0.99 | 0.68 / 0.99 | **┃** | 0.72 / 0.95 | 0.67 / 0.94 | 0.63 / 0.98 | **┃** | 0.61 / 1.00 | 0.51 / 1.00 | 0.59 / 0.96 |
| recommendationservice | 0.58 / 0.69 | 0.54 / 0.66 | 0.54 / 0.69 | **┃** | 0.69 / 0.87 | 0.73 / 0.87 | 0.72 / 0.92 | **┃** | 0.65 / 1.00 | 0.80 / 0.99 | 0.76 / 0.98 |
| paymentservice | 0.42 / 0.58 | 0.29 / 0.48 | 0.28 / 0.49 | **┃** | 0.25 / 0.37 | 0.24 / 0.39 | 0.22 / 0.37 | **┃** | 0.32 / 0.99 | 0.18 / 0.45 | 0.22 / 0.42 |
| emailservice | 0.50 / 1.00 | 0.43 / 0.88 | 0.42 / 0.96 | **┃** | 0.62 / 0.87 | 0.57 / 0.88 | 0.54 / 0.89 | **┃** | 0.33 / 0.81 | 0.41 / 0.68 | 0.49 / 0.72 |
| productcatalogservice | 0.58 / 0.65 | 0.57 / 0.66 | 0.55 / 0.67 | **┃** | 0.50 / 0.64 | 0.52 / 0.63 | 0.48 / 0.63 | **┃** | 0.48 / 0.64 | 0.53 / 0.70 | 0.55 / 0.71 |
| cartservice | 0.38 / 0.56 | 0.39 / 0.56 | 0.38 / 0.55 | **┃** | 0.39 / 0.49 | 0.42 / 0.63 | 0.41 / 0.64 | **┃** | 0.51 / 0.72 | 0.53 / 0.65 | 0.50 / 0.69 |
| currencyservice | 0.47 / 0.54 | 0.45 / 0.53 | 0.43 / 0.58 | **┃** | 0.44 / 0.54 | 0.46 / 0.55 | 0.43 / 0.59 | **┃** | 0.46 / 0.64 | 0.46 / 0.57 | 0.46 / 0.65 |
| shippingservice | 0.12 / 0.14 | 0.10 / 0.14 | 0.10 / 0.14 | **┃** | 0.11 / 0.15 | 0.11 / 0.14 | 0.10 / 0.18 | **┃** | 0.10 / 0.19 | 0.09 / 0.15 | 0.11 / 0.15 |
| adservice | 0.12 / 0.15 | 0.12 / 0.14 | 0.12 / 0.15 | **┃** | 0.10 / 0.14 | 0.10 / 0.14 | 0.09 / 0.15 | **┃** | 0.12 / 0.40 | 0.09 / 0.15 | 0.10 / 0.15 |
| redis-cart | 0.07 / 0.08 | 0.07 / 0.08 | 0.07 / 0.08 | **┃** | 0.07 / 0.09 | 0.07 / 0.09 | 0.07 / 0.09 | **┃** | 0.07 / 0.10 | 0.08 / 0.10 | 0.07 / 0.10 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run4 | run31 | run16 | **┃** | run5 | run32 | run17 | **┃** | run6 | run33 | run18 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.353 | 0.370 | 0.373 | **┃** | 0.357 | 0.349 | 0.361 | **┃** | 0.373 | 0.391 | 0.374 |
| checkoutservice | 1.052 | 1.034 | 1.054 | **┃** | 1.012 | 0.989 | 1.024 | **┃** | 1.074 | 1.019 | 1.004 |
| recommendationservice | 0.721 | 0.707 | 0.737 | **┃** | 0.902 | 0.921 | 0.964 | **┃** | 1.019 | 1.004 | 1.006 |
| paymentservice | 0.748 | 0.690 | 0.697 | **┃** | 0.503 | 0.471 | 0.497 | **┃** | 1.052 | 0.568 | 0.665 |
| emailservice | 1.058 | 1.033 | 1.058 | **┃** | 0.975 | 1.033 | 1.017 | **┃** | 1.042 | 0.925 | 0.933 |
| productcatalogservice | 0.677 | 0.701 | 0.716 | **┃** | 0.661 | 0.661 | 0.677 | **┃** | 0.677 | 0.731 | 0.777 |
| cartservice | 0.580 | 0.584 | 0.575 | **┃** | 0.540 | 0.666 | 0.659 | **┃** | 0.806 | 0.718 | 0.733 |
| currencyservice | 0.592 | 0.600 | 0.657 | **┃** | 0.590 | 0.590 | 0.612 | **┃** | 0.736 | 0.655 | 0.713 |
| shippingservice | 0.179 | 0.171 | 0.174 | **┃** | 0.173 | 0.166 | 0.195 | **┃** | 0.227 | 0.173 | 0.199 |
| adservice | 0.238 | 0.169 | 0.168 | **┃** | 0.165 | 0.182 | 0.160 | **┃** | 0.710 | 0.183 | 0.187 |
| redis-cart | 0.128 | 0.131 | 0.131 | **┃** | 0.133 | 0.161 | 0.141 | **┃** | 0.189 | 0.202 | 0.206 |

## Per mix

**275 / 90 / 100 / 90 / 5.** run4 (RetryGuard only) clears streak 30 on checkoutservice (37) and an overloaded share of 0.5 on checkoutservice (91.8%). Recommendations stays at streak 1 and 0 overloaded ticks. RetryGuard toggles checkout 16× off and 16× on, and does not toggle recommendations. Layer A stays at the passthrough. The largest retry edge is frontend → checkoutservice. run4's files cover about 20 minutes, not 10. run31 (TopFull only) clears streak 30 on 0 controlled services and an overloaded share of 0.5 on checkoutservice (57.7%). Recommendations is cold (streak 1, 0 overloaded ticks). postcheckout ends at 34.5. run16 (both on) matches that shape: checkout streak 8, overloaded 55.0%, recommendations streak 1 and 0 overloaded ticks, RetryGuard toggles 0, postcheckout ends at 10.0. Storefront goodput on this mix stays at the configured browse rates (getproduct about 274, getcart about 99, fail 0). postcheckout goodput is 44.4 with RetryGuard only and 29.8 on both TopFull arms.

**325 / 90 / 150 / 90 / 5.** run5 (RetryGuard only) clears streak 30 on 0 controlled services and an overloaded share of 0.5 on checkoutservice (63.7%) and recommendationservice (75.1%). Recommendations streak is 8, so RetryGuard does not toggle. The largest retry edge is frontend → recommendationservice (136,554). Checkout sojourn is 115 ms and its streak is 1. run32 (TopFull only) clears streak 30 on 0 and an overloaded share of 0.5 on recommendationservice (87.5%). Checkout streak is 1 and its overloaded share is 29.6%. postcheckout ends at 62.5. Checkout gap2 is 10%. run17 (both on) clears streak 30 on recommendationservice (31) and an overloaded share of 0.5 on recommendationservice (79.9%). RetryGuard toggles recommendations once off and once on. Checkout streak is 0. postcheckout ends at 76.0. getproduct goodput on this mix is 145.3 / 141.4 / 126.3, with fail about 0.48–0.49.

**325 / 115 / 150 / 90 / 5.** run6 (RetryGuard only) clears streak 30 on checkoutservice (33) and recommendationservice (32). Neither overloaded share reaches 0.5 (checkout 45.8%, recommendations 48.8%). RetryGuard toggles checkout 4× each way and recommendations 6× each way. Layer A stays at the passthrough. Retry edges are frontend → recommendationservice 155,116 and frontend → checkoutservice 18,973. postcheckout goodput is 7.8 with fail 0.870. run33 (TopFull only) clears an overloaded share of 0.5 on recommendationservice (88.9%). Its recommendations streak of 187 sits on a scrape with checkout gap2 78%, so that streak is not a 1 s series. Checkout streak is 3 and its overloaded share is 2.8%. postcheckout ends at 38.9. run18 (both on) clears an overloaded share of 0.5 on recommendationservice (85.3%). Recommendations streak is 20, also on a gappy inbound scrape (gap2 77%). RetryGuard toggles 0. TopFull caps getproduct, getcart, and postcheckout. postcheckout ends at 50.5.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Layout this file follows: [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md).
- Checkout timeout-retry loop: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md).
- Locust API paths: [LOCUST-API-PATHS.md](LOCUST-API-PATHS.md).
