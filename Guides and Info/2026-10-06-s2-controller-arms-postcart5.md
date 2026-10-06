# S2 controller arms, postcart at 5

600 s holds on Paper-C1, `spawn_rate` 50, Istio `attempts: 3`, `perTryTimeout` 500 ms. Frontend HPA pinned at 4, catalog HPA at 1, sidecar request 100 m with no CPU limit. Checkout and recommendations were rolled before each hold. 360 s cool-off between every pair of holds. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).

These slot numbers are the controller-arm folders under `experiments/results/campaign_48/S2_sustained_overload/`. They are not the both-off holds that reuse some of the same numbers.

(a), (b), and (c) are from `experiments/s2_both_off_abc.py` on the full inbound file. The other inbound tables drop the last 5 polls. Locust tables drop the first 30 rows and the last 5. **Bold** in (a) is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain there. **Bold** in (b) is an overloaded share of at least 0.5.

Checkout inbound gap2 is 68% to 100% on all nine holds (355–429 polls). Signal (a) counts those slow polls. Signal (b) is still the 1-second detector clock. A first launch of run9 and a first launch of run21 were stopped while Locust was still up and left no results folder. The folders below are the completed holds.

## Hold index

| Mix | Arm | Column | Folder | Locust rows | Mesh span | Checkout gap2 |
|---|---|---|---|---:|---:|---:|
| 325 / 115 / 150 / 5 / 5 | RetryGuard only | run7 | run_retryguard_no_topfull_sustained_overload_run7 | 563 | 721 s | 68% |
| 325 / 115 / 150 / 5 / 5 | TopFull only | run34 | baseline_topfull_no_retryguard_sustained_overload_run34 | 553 | 699 s | 97% |
| 325 / 115 / 150 / 5 / 5 | Both on | run19 | run_topfull_retryguard_sustained_overload_run19 | 553 | 728 s | 98% |
| 360 / 125 / 150 / 5 / 5 | RetryGuard only | run8 | run_retryguard_no_topfull_sustained_overload_run8 | 563 | 724 s | 72% |
| 360 / 125 / 150 / 5 / 5 | TopFull only | run35 | baseline_topfull_no_retryguard_sustained_overload_run35 | 554 | 699 s | 97% |
| 360 / 125 / 150 / 5 / 5 | Both on | run20 | run_topfull_retryguard_sustained_overload_run20 | 553 | 725 s | 99% |
| 360 / 140 / 180 / 5 / 5 | RetryGuard only | run9 | run_retryguard_no_topfull_sustained_overload_run9 | 559 | 724 s | 79% |
| 360 / 140 / 180 / 5 / 5 | TopFull only | run36 | baseline_topfull_no_retryguard_sustained_overload_run36 | 555 | 697 s | 100% |
| 360 / 140 / 180 / 5 / 5 | Both on | run21 | run_topfull_retryguard_sustained_overload_run21 | 553 | 725 s | 100% |

The tables use that column order. A bold bar separates the three mixes.

Per-pod millicores, request equals limit. Replicas are the Paper-C1 pin. Frontend is 4; every other service is 1. `cpu_millicores` in `resource_usage.csv` is the sum across replicas. Frontend stayed at 4 replicas on every resource sample of all nine holds.

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

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain. Checkout gap2 is 68–100% on every hold, so these streaks are counts of slow polls, not a 1-second series.


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend (not controlled) | 32 / 158 | 260 / 280 | 73 / 228 | **┃** | 52 / 217 | 198 / 281 | 32 / 177 | **┃** | 32 / 161 | 285 / 285 | 56 / 249 |
| checkoutservice | **32 / 149** | 4 / 4 | 5 / 5 | **┃** | 14 / 87 | 4 / 4 | 3 / 3 | **┃** | **32 / 139** | 4 / 5 | 5 / 5 |
| recommendationservice | **31 / 154** | **281 / 281** | **32 / 105** | **┃** | **31 / 137** | **71 / 92** | **32 / 172** | **┃** | **32 / 160** | **286 / 286** | **31 / 127** |
| paymentservice | 1 / 10 | 0 / 0 | 0 / 0 | **┃** | 1 / 3 | 0 / 0 | 0 / 0 | **┃** | 1 / 15 | 0 / 0 | 0 / 0 |
| emailservice | 3 / 32 | 4 / 4 | 1 / 1 | **┃** | 6 / 38 | 1 / 2 | 1 / 1 | **┃** | 3 / 22 | 1 / 2 | 3 / 3 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows (threshold neither 0 nor 10000), any API: run7 0, run34 596, run19 590, run8 0, run35 588, run20 594, run9 647, run36 635, run21 797. postcheckout ended at the 10000 passthrough on run7 (2/664 rows below) and run8 (1/666). It ended at 49.5 (run34), 42.9 (run19), 29.0 (run35), 50.1 (run20), 50.1 (run9), 70.6 (run36), and 21.8 (run21). run9's runner log says the TopFull RL loop was off; the throttle file still ends below the passthrough.


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| checkoutservice | **419/664 (63.1%)** | 40/639 (6.3%) | 96/668 (14.4%) | **┃** | 213/666 (32.0%) | 21/639 (3.3%) | 221/666 (33.2%) | **┃** | **368/666 (55.3%)** | 94/638 (14.7%) | 21/665 (3.2%) |
| recommendationservice | **396/664 (59.6%)** | **565/639 (88.4%)** | **335/668 (50.1%)** | **┃** | 299/666 (44.9%) | **556/639 (87.0%)** | **512/666 (76.9%)** | **┃** | **435/666 (65.3%)** | **574/638 (90.0%)** | **386/665 (58.0%)** |
| paymentservice | 4/664 (0.6%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 3/666 (0.5%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 7/666 (1.1%) | 0/638 (0.0%) | 0/665 (0.0%) |
| emailservice | 56/664 (8.4%) | 8/639 (1.3%) | 10/668 (1.5%) | **┃** | 35/666 (5.3%) | 10/639 (1.6%) | 46/666 (6.9%) | **┃** | 46/666 (6.9%) | 28/638 (4.4%) | 7/665 (1.1%) |
| productcatalogservice | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| cartservice | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| currencyservice | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| shippingservice | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| adservice | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |
| redis-cart | 0/664 (0.0%) | 0/639 (0.0%) | 0/668 (0.0%) | **┃** | 0/666 (0.0%) | 0/639 (0.0%) | 0/666 (0.0%) | **┃** | 0/666 (0.0%) | 0/638 (0.0%) | 0/665 (0.0%) |

## (c) Outbound retry delta

The table is retry by target: the sum of positive Envoy `retry` increments into that service.

- **run7.** frontend → recommendationservice 131,074, frontend → checkoutservice 29,040, checkoutservice → emailservice 46.
- **run34.** frontend → recommendationservice 230,692, frontend → checkoutservice 629.
- **run19.** frontend → recommendationservice 175,927, frontend → checkoutservice 662.
- **run8.** frontend → recommendationservice 165,546, frontend → checkoutservice 12,917.
- **run35.** frontend → recommendationservice 284,925, frontend → checkoutservice 525.
- **run20.** frontend → recommendationservice 142,992, frontend → checkoutservice 488.
- **run9.** frontend → recommendationservice 147,403, frontend → checkoutservice 28,546, checkoutservice → emailservice 114.
- **run36.** frontend → recommendationservice 270,424, frontend → checkoutservice 520.
- **run21.** frontend → recommendationservice 207,708, frontend → checkoutservice 714.


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| checkoutservice | 29,040 | 629 | 662 | **┃** | 12,917 | 525 | 488 | **┃** | 28,546 | 520 | 714 |
| recommendationservice | 131,074 | 230,692 | 175,927 | **┃** | 165,546 | 284,925 | 142,992 | **┃** | 147,403 | 270,424 | 207,708 |
| paymentservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| emailservice | 46 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 114 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 |

## CPU mean / max

App-container millicores, mean / max. Quota is the per-pod CPU limit. The mean / max cells sum that usage across replicas. Frontend is 4 replicas, so its mean can sit above 1150.


| Service | Quota | Replicas | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 1150 | 4 | 1203 / 1627 | 1097 / 1542 | 1069 / 1669 | **┃** | 1097 / 1595 | 955 / 1554 | 1127 / 1641 | **┃** | 1140 / 1605 | 1023 / 1680 | 1067 / 1707 |
| checkoutservice | 800 | 1 | 586 / 799 | 402 / 787 | 246 / 795 | **┃** | 355 / 799 | 98 / 782 | 395 / 788 | **┃** | 534 / 799 | 385 / 730 | 114 / 773 |
| recommendationservice | 1150 | 1 | 837 / 1137 | 970 / 1140 | 716 / 1151 | **┃** | 676 / 1150 | 956 / 1152 | 826 / 1152 | **┃** | 836 / 1144 | 977 / 1149 | 743 / 1152 |
| paymentservice | 155 | 1 | 53 / 106 | 28 / 67 | 19 / 76 | **┃** | 33 / 90 | 10 / 69 | 28 / 75 | **┃** | 49 / 96 | 28 / 67 | 11 / 81 |
| emailservice | 120 | 1 | 40 / 103 | 49 / 82 | 34 / 92 | **┃** | 34 / 97 | 19 / 104 | 50 / 88 | **┃** | 36 / 91 | 50 / 87 | 21 / 100 |
| productcatalogservice | 800 | 1 | 425 / 551 | 422 / 567 | 322 / 534 | **┃** | 322 / 525 | 319 / 543 | 408 / 585 | **┃** | 402 / 556 | 368 / 588 | 299 / 554 |
| cartservice | 800 | 1 | 312 / 459 | 338 / 553 | 337 / 563 | **┃** | 320 / 419 | 335 / 558 | 301 / 420 | **┃** | 303 / 433 | 306 / 378 | 333 / 614 |
| currencyservice | 770 | 1 | 380 / 532 | 337 / 464 | 326 / 500 | **┃** | 338 / 489 | 302 / 446 | 350 / 519 | **┃** | 366 / 525 | 319 / 494 | 337 / 513 |
| shippingservice | 770 | 1 | 94 / 146 | 67 / 116 | 46 / 126 | **┃** | 58 / 145 | 22 / 107 | 70 / 137 | **┃** | 88 / 149 | 57 / 124 | 32 / 137 |
| adservice | 1150 | 1 | 122 / 218 | 97 / 172 | 78 / 184 | **┃** | 82 / 180 | 52 / 171 | 109 / 192 | **┃** | 108 / 181 | 74 / 181 | 69 / 196 |
| redis-cart | 540 | 1 | 29 / 41 | 30 / 40 | 29 / 43 | **┃** | 30 / 41 | 29 / 40 | 29 / 43 | **┃** | 28 / 40 | 30 / 40 | 31 / 44 |


## Locust goodput

Mean `Goodput` (req/s) on rows 30 through the fifth from the end.


| API | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 155.0 | 59.4 | 32.4 | **┃** | 29.0 | 17.7 | 138.8 | **┃** | 136.4 | 35.5 | 21.7 |
| postcheckout | 8.9 | 11.7 | 4.9 | **┃** | 5.7 | 2.1 | 20.8 | **┃** | 7.0 | 12.5 | 1.7 |
| getcart | 73.3 | 30.0 | 16.1 | **┃** | 13.7 | 8.4 | 61.8 | **┃** | 72.2 | 21.0 | 11.4 |
| postcart | 4.2 | 3.8 | 4.0 | **┃** | 4.4 | 3.7 | 3.8 | **┃** | 3.8 | 3.5 | 3.9 |
| emptycart | 3.9 | 3.7 | 3.9 | **┃** | 4.3 | 3.7 | 3.8 | **┃** | 4.1 | 3.6 | 4.1 |


## Locust fail rate

Mean `Fail` on the same trimmed rows. Locust `Fail` is a 1 s SLO miss.


| API | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 0.438 | 0.764 | 0.868 | **┃** | 0.876 | 0.920 | 0.535 | **┃** | 0.470 | 0.837 | 0.904 |
| postcheckout | 0.871 | 0.885 | 0.949 | **┃** | 0.917 | 0.979 | 0.815 | **┃** | 0.901 | 0.865 | 0.984 |
| getcart | 0.437 | 0.748 | 0.862 | **┃** | 0.867 | 0.911 | 0.516 | **┃** | 0.458 | 0.817 | 0.902 |
| postcart | 0.153 | 0.232 | 0.195 | **┃** | 0.124 | 0.261 | 0.246 | **┃** | 0.232 | 0.298 | 0.210 |
| emptycart | 0.213 | 0.261 | 0.218 | **┃** | 0.143 | 0.265 | 0.234 | **┃** | 0.173 | 0.280 | 0.187 |


## Locust P95

Mean `P95` (ms) on the same trimmed rows.


| API | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| getproduct | 1559 | 2126 | 1568 | **┃** | 1526 | 2134 | 1683 | **┃** | 1600 | 2170 | 1685 |
| postcheckout | 2499 | 2011 | 1526 | **┃** | 2032 | 2043 | 1593 | **┃** | 2492 | 2099 | 1575 |
| getcart | 1489 | 2053 | 1511 | **┃** | 1464 | 2063 | 1615 | **┃** | 1540 | 2108 | 1631 |
| postcart | 62 | 56 | 55 | **┃** | 61 | 54 | 63 | **┃** | 71 | 57 | 58 |
| emptycart | 19 | 15 | 15 | **┃** | 16 | 11 | 19 | **┃** | 20 | 16 | 18 |


## Inbound arrival rate

Mean first-attempt arrivals per second from `service_inbound.csv`, last 5 polls dropped.


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 335.7 | 310.6 | 319.6 | **┃** | 335.7 | 284.8 | 316.7 | **┃** | 327.3 | 297.5 | 294.2 |
| checkoutservice | 73.7 | 21.5 | 13.4 | **┃** | 36.8 | 5.5 | 22.5 | **┃** | 70.7 | 21.6 | 5.9 |
| recommendationservice | 503.0 | 634.0 | 497.3 | **┃** | 489.4 | 684.8 | 506.8 | **┃** | 520.6 | 678.4 | 519.8 |
| paymentservice | 59.0 | 21.4 | 13.3 | **┃** | 34.9 | 5.4 | 22.4 | **┃** | 52.2 | 21.5 | 5.6 |
| emailservice | 16.6 | 20.3 | 12.2 | **┃** | 13.0 | 4.5 | 21.7 | **┃** | 14.2 | 20.8 | 4.6 |
| productcatalogservice | 1811.9 | 1421.8 | 1098.1 | **┃** | 1140.3 | 786.3 | 1623.6 | **┃** | 1670.8 | 1094.9 | 796.9 |
| cartservice | 381.1 | 316.1 | 311.8 | **┃** | 334.3 | 270.9 | 328.6 | **┃** | 364.6 | 288.4 | 285.8 |
| currencyservice | 632.6 | 540.3 | 530.6 | **┃** | 545.0 | 456.5 | 575.5 | **┃** | 602.0 | 474.4 | 480.6 |
| shippingservice | 175.2 | 91.1 | 61.9 | **┃** | 99.5 | 23.9 | 102.7 | **┃** | 164.6 | 77.2 | 34.4 |
| adservice | 149.8 | 102.0 | 75.0 | **┃** | 81.2 | 30.4 | 133.7 | **┃** | 129.7 | 62.6 | 46.0 |
| redis-cart | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 |


## Inbound 5xx fraction


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.277 | 0.427 | 0.596 | **┃** | 0.598 | 0.806 | 0.305 | **┃** | 0.333 | 0.582 | 0.726 |
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


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| checkoutservice | 0.488 | 0.036 | 0.060 | **┃** | 0.414 | 0.123 | 0.025 | **┃** | 0.500 | 0.029 | 0.151 |
| recommendationservice | 0.210 | 0.301 | 0.198 | **┃** | 0.229 | 0.203 | 0.201 | **┃** | 0.209 | 0.304 | 0.216 |
| paymentservice | 0.077 | 0.001 | 0.002 | **┃** | 0.030 | 0.005 | 0.003 | **┃** | 0.089 | 0.001 | 0.013 |
| emailservice | 0.022 | 0.003 | 0.004 | **┃** | 0.058 | 0.012 | 0.002 | **┃** | 0.022 | 0.004 | 0.008 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| cartservice | 0.002 | 0.000 | 0.000 | **┃** | 0.003 | 0.000 | 0.000 | **┃** | 0.002 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.012 | 0.000 | 0.001 | **┃** | 0.009 | 0.002 | 0.000 | **┃** | 0.011 | 0.000 | 0.002 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |


## Inbound sojourn

Mean `rq_time` sojourn, milliseconds.


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 967 | 1067 | 891 | **┃** | 916 | 1244 | 935 | **┃** | 1029 | 1194 | 963 |
| checkoutservice | 367 | 85 | 95 | **┃** | 337 | 138 | 106 | **┃** | 384 | 122 | 127 |
| recommendationservice | 494 | 461 | 523 | **┃** | 549 | 479 | 498 | **┃** | 504 | 468 | 495 |
| paymentservice | 9 | 3 | 3 | **┃** | 9 | 4 | 4 | **┃** | 9 | 3 | 3 |
| emailservice | 38 | 13 | 15 | **┃** | 26 | 22 | 18 | **┃** | 49 | 22 | 16 |
| productcatalogservice | 4 | 2 | 3 | **┃** | 3 | 1 | 4 | **┃** | 4 | 3 | 3 |
| cartservice | 4 | 3 | 2 | **┃** | 3 | 2 | 3 | **┃** | 4 | 3 | 3 |
| currencyservice | 6 | 4 | 3 | **┃** | 5 | 3 | 6 | **┃** | 7 | 4 | 4 |
| shippingservice | 2 | 1 | 1 | **┃** | 1 | 1 | 1 | **┃** | 2 | 1 | 1 |
| adservice | 2 | 1 | 1 | **┃** | 2 | 2 | 2 | **┃** | 2 | 2 | 2 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |


## Share of inbound requests above 500 ms


| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.900 | 0.895 | 0.698 | **┃** | 0.695 | 0.905 | 0.876 | **┃** | 0.921 | 0.906 | 0.686 |
| checkoutservice | 0.591 | 0.025 | 0.040 | **┃** | 0.489 | 0.091 | 0.019 | **┃** | 0.640 | 0.020 | 0.096 |
| recommendationservice | 0.738 | 0.653 | 0.824 | **┃** | 0.822 | 0.915 | 0.780 | **┃** | 0.799 | 0.769 | 0.872 |
| paymentservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| emailservice | 0.002 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.008 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a |


## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (per-pod limit × replica_count)`.

| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---|---|---|:---:|---|---|---|:---:|---|---|---|
| frontend | 0.26 / 0.35 | 0.24 / 0.34 | 0.23 / 0.36 | **┃** | 0.24 / 0.35 | 0.21 / 0.34 | 0.24 / 0.36 | **┃** | 0.25 / 0.35 | 0.22 / 0.37 | 0.23 / 0.37 |
| checkoutservice | 0.73 / 1.00 | 0.50 / 0.98 | 0.31 / 0.99 | **┃** | 0.44 / 1.00 | 0.12 / 0.98 | 0.49 / 0.98 | **┃** | 0.67 / 1.00 | 0.48 / 0.91 | 0.14 / 0.97 |
| recommendationservice | 0.73 / 0.99 | 0.84 / 0.99 | 0.62 / 1.00 | **┃** | 0.59 / 1.00 | 0.83 / 1.00 | 0.72 / 1.00 | **┃** | 0.73 / 0.99 | 0.85 / 1.00 | 0.65 / 1.00 |
| paymentservice | 0.34 / 0.68 | 0.18 / 0.43 | 0.12 / 0.49 | **┃** | 0.22 / 0.58 | 0.07 / 0.45 | 0.18 / 0.48 | **┃** | 0.32 / 0.62 | 0.18 / 0.43 | 0.07 / 0.52 |
| emailservice | 0.34 / 0.86 | 0.40 / 0.68 | 0.28 / 0.77 | **┃** | 0.28 / 0.81 | 0.16 / 0.87 | 0.42 / 0.73 | **┃** | 0.30 / 0.76 | 0.42 / 0.72 | 0.18 / 0.83 |
| productcatalogservice | 0.53 / 0.69 | 0.53 / 0.71 | 0.40 / 0.67 | **┃** | 0.40 / 0.66 | 0.40 / 0.68 | 0.51 / 0.73 | **┃** | 0.50 / 0.69 | 0.46 / 0.73 | 0.37 / 0.69 |
| cartservice | 0.39 / 0.57 | 0.42 / 0.69 | 0.42 / 0.70 | **┃** | 0.40 / 0.52 | 0.42 / 0.70 | 0.38 / 0.53 | **┃** | 0.38 / 0.54 | 0.38 / 0.47 | 0.42 / 0.77 |
| currencyservice | 0.49 / 0.69 | 0.44 / 0.60 | 0.42 / 0.65 | **┃** | 0.44 / 0.64 | 0.39 / 0.58 | 0.46 / 0.67 | **┃** | 0.48 / 0.68 | 0.41 / 0.64 | 0.44 / 0.67 |
| shippingservice | 0.12 / 0.19 | 0.09 / 0.15 | 0.06 / 0.16 | **┃** | 0.08 / 0.19 | 0.03 / 0.14 | 0.09 / 0.18 | **┃** | 0.11 / 0.19 | 0.07 / 0.16 | 0.04 / 0.18 |
| adservice | 0.11 / 0.19 | 0.08 / 0.15 | 0.07 / 0.16 | **┃** | 0.07 / 0.16 | 0.05 / 0.15 | 0.10 / 0.17 | **┃** | 0.09 / 0.16 | 0.06 / 0.16 | 0.06 / 0.17 |
| redis-cart | 0.05 / 0.08 | 0.06 / 0.07 | 0.05 / 0.08 | **┃** | 0.06 / 0.08 | 0.05 / 0.07 | 0.05 / 0.08 | **┃** | 0.05 / 0.07 | 0.06 / 0.07 | 0.06 / 0.08 |


## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run7 | run34 | run19 | **┃** | run8 | run35 | run20 | **┃** | run9 | run36 | run21 |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|---:|---:|---:|
| frontend | 0.377 | 0.368 | 0.399 | **┃** | 0.382 | 0.386 | 0.382 | **┃** | 0.360 | 0.382 | 0.419 |
| checkoutservice | 1.038 | 1.026 | 1.010 | **┃** | 1.046 | 1.015 | 1.015 | **┃** | 1.051 | 1.010 | 1.026 |
| recommendationservice | 1.017 | 1.015 | 1.021 | **┃** | 1.020 | 1.025 | 1.022 | **┃** | 1.018 | 1.022 | 1.021 |
| paymentservice | 0.948 | 0.606 | 0.587 | **┃** | 0.994 | 0.677 | 0.723 | **┃** | 0.910 | 0.632 | 0.639 |
| emailservice | 1.025 | 0.942 | 1.017 | **┃** | 1.008 | 0.975 | 0.933 | **┃** | 1.000 | 0.992 | 1.000 |
| productcatalogservice | 0.738 | 0.767 | 0.710 | **┃** | 0.696 | 0.761 | 0.775 | **┃** | 0.746 | 0.785 | 0.759 |
| cartservice | 0.623 | 0.743 | 0.760 | **┃** | 0.619 | 0.759 | 0.586 | **┃** | 0.616 | 0.541 | 0.814 |
| currencyservice | 0.752 | 0.682 | 0.713 | **┃** | 0.688 | 0.691 | 0.778 | **┃** | 0.783 | 0.739 | 0.740 |
| shippingservice | 0.225 | 0.200 | 0.199 | **┃** | 0.231 | 0.194 | 0.218 | **┃** | 0.242 | 0.204 | 0.200 |
| adservice | 0.365 | 0.260 | 0.297 | **┃** | 0.191 | 0.197 | 0.202 | **┃** | 0.183 | 0.181 | 0.205 |
| redis-cart | 0.146 | 0.174 | 0.194 | **┃** | 0.163 | 0.165 | 0.191 | **┃** | 0.133 | 0.176 | 0.137 |

## Per mix

**325 / 115 / 150 / 5 / 5.** run7 (RetryGuard only) clears streak 30 on checkoutservice (32) and recommendationservice (31). Both also clear an overloaded share of 0.5 (checkout 63.1%, recommendations 59.6%). RetryGuard toggles checkout 4× off and 3× on, and recommendations 4× each way. Layer A stays at the passthrough. Retry edges are frontend → recommendationservice 131,074 and frontend → checkoutservice 29,040. Checkout sojourn is 367 ms. getproduct goodput is 155.0 with fail 0.438. postcheckout goodput is 8.9 with fail 0.871. Checkout gap2 is 68%. run34 (TopFull only) clears streak 30 on recommendationservice (281) and an overloaded share of 0.5 there (88.4%). Checkout streak is 4 and its overloaded share is 6.3%. postcheckout ends at 49.5. The largest retry edge is frontend → recommendationservice 230,692. getproduct goodput is 59.4 with fail 0.764. Checkout gap2 is 97%, so the recommendations streak of 281 is not a 1 s series. run19 (both on) clears streak 30 on recommendationservice (32) and an overloaded share of 0.5 there (50.1%). RetryGuard toggles recommendations 3× off and 2× on, and does not toggle checkout (streak 5). postcheckout ends at 42.9. frontend → recommendationservice retries are 175,927. getproduct goodput is 32.4 with fail 0.868. Checkout gap2 is 98%.

**360 / 125 / 150 / 5 / 5.** run8 (RetryGuard only) clears streak 30 on recommendationservice (31). Its overloaded share is 44.9%. Checkout streak is 14 and its overloaded share is 32.0%. RetryGuard toggles recommendations 3× each way and does not toggle checkout. Layer A stays at the passthrough. Retry edges are frontend → recommendationservice 165,546 and frontend → checkoutservice 12,917. Checkout sojourn is 337 ms. getproduct goodput is 29.0 with fail 0.876. Checkout gap2 is 72%. run35 (TopFull only) clears streak 30 on recommendationservice (71) and an overloaded share of 0.5 there (87.0%). Checkout streak is 4. postcheckout ends at 29.0. frontend → recommendationservice retries are 284,925. getproduct goodput is 17.7 with fail 0.920. Checkout gap2 is 97%. run20 (both on) clears streak 30 on recommendationservice (32) and an overloaded share of 0.5 there (76.9%). RetryGuard toggles recommendations 4× off and 3× on. Checkout streak is 3 and its overloaded share is 33.2%. postcheckout ends at 50.1. frontend → recommendationservice retries are 142,992. getproduct goodput is 138.8 with fail 0.535. Checkout gap2 is 99%.

**360 / 140 / 180 / 5 / 5.** run9 (RetryGuard only) clears streak 30 on checkoutservice (32) and recommendationservice (32). Both clear an overloaded share of 0.5 (checkout 55.3%, recommendations 65.3%). RetryGuard toggles checkout 4× off and 3× on, and recommendations 4× each way. The runner log says the TopFull RL loop was off. postcheckout in `topfull_throttle.csv` still ends at 50.1, below 10000 on 647/666 rows. Retry edges are frontend → recommendationservice 147,403 and frontend → checkoutservice 28,546. Checkout sojourn is 384 ms. getproduct goodput is 136.4 with fail 0.470. postcheckout goodput is 7.0 with fail 0.901. Checkout gap2 is 79%. run36 (TopFull only) clears streak 30 on recommendationservice (286) and an overloaded share of 0.5 there (90.0%). Checkout streak is 4 and its overloaded share is 14.7%. postcheckout ends at 70.6. frontend → recommendationservice retries are 270,424. getproduct goodput is 35.5 with fail 0.837. Checkout gap2 is 100%, so the recommendations streak is not a 1 s series. run21 (both on) clears streak 30 on recommendationservice (31) and an overloaded share of 0.5 there (58.0%). RetryGuard toggles recommendations 2× each way and does not toggle checkout (streak 5, overloaded share 3.2%). postcheckout ends at 21.8. frontend → recommendationservice retries are 207,708. getproduct goodput is 21.7 with fail 0.904. postcheckout goodput is 1.7 with fail 0.984. Checkout gap2 is 100%.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Earlier controller-arm mixes: [2026-10-05-s2-controller-arms-nine-holds.md](2026-10-05-s2-controller-arms-nine-holds.md).
- Checkout timeout-retry loop: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md).
- Locust API paths: [LOCUST-API-PATHS.md](LOCUST-API-PATHS.md).
