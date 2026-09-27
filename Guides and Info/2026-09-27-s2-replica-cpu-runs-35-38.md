# S2 both-off runs 35–38, all services

600 s holds, both controllers off, `spawn_rate` 50. Replica CPU table, replicas pinned at the table counts: frontend 4, checkoutservice 2, recommendationservice 3, cartservice 2, paymentservice 2, emailservice 2, and productcatalogservice, currencyservice, shippingservice, adservice, and redis-cart at 1. Sidecar request 70 m with no CPU limit. 360 s cool-off before run35 and between holds. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every number below is from `experiments/s2_both_off_abc.py` on these four folders and on the six earlier ones.

| Mix | This series | Agreed-table replay | Earlier both-off |
|---|---|---|---|
| 7 (380/100/270/20/20) | run35 | run31 | run7 |
| 12 (100/150/100/100/5) | run36 | run34 | run12 |
| 26 (325/100/100/100/5) | run37 | run33 | run26 |
| new (250/150/250/50/50) | run38 | — | — |

The tables use that column order, left to right: this series, the agreed-table replay, the earlier both-off hold, mix by mix, then run38. A bold bar separates mix 7 (run35, run31, run7), mix 12 (run36, run34, run12), mix 26 (run37, run33, run26), and the new mix (run38).

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | --- | --- | --- | :---: | --- | --- | --- | :---: | --- | --- | --- | :---: | --- |
| frontend (not controlled) | 2 / 2 | 578 / 578 | 21 / 220 | **┃** | 10 / 357 | 122 / 446 | 122 / 518 | **┃** | 1 / 1 | 95 / 526 | 72 / 517 | **┃** | 2 / 2 |
| checkoutservice | 1 / 1 | 0 / 0 | **230 / 264** | **┃** | **557 / 557** | **122 / 334** | **89 / 287** | **┃** | 1 / 1 | 0 / 0 | **592 / 592** | **┃** | 1 / 1 |
| recommendationservice | 1 / 1 | 7 / 292 | 15 / 235 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 8 / 225 | 2 / 43 | **┃** | 1 / 1 |
| paymentservice | 0 / 0 | 0 / 0 | 1 / 4 | **┃** | 0 / 0 | **30 / 215** | 3 / 44 | **┃** | 0 / 0 | 0 / 0 | 2 / 13 | **┃** | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | 6 / 87 | **┃** | 8 / 295 | 11 / 66 | 1 / 2 | **┃** | 0 / 0 | 1 / 1 | 4 / 156 | **┃** | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 | **┃** | 1 / 1 |
| cartservice | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 |
| currencyservice | 1 / 1 | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 | **┃** | 1 / 1 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 1 / 3 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| adservice | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on run35, run36, run37, and run38, and 0 on run31, run7, run34, run12, run33, and run26.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | --- | --- | --- | :---: | --- | --- | --- | :---: | --- | --- | --- | :---: | --- |
| frontend | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| checkoutservice | 0/637 (0.0%) | 0/637 (0.0%) | **572/636 (89.9%)** | **┃** | **572/637 (89.8%)** | **386/637 (60.6%)** | 266/637 (41.8%) | **┃** | 41/638 (6.4%) | 0/637 (0.0%) | **592/637 (92.9%)** | **┃** | **457/637 (71.7%)** |
| recommendationservice | 0/637 (0.0%) | 0/637 (0.0%) | **511/636 (80.3%)** | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **364/637 (57.1%)** | **┃** | 0/637 (0.0%) |
| paymentservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 1/637 (0.2%) | 256/637 (40.2%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| emailservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 1/637 (0.2%) | 18/637 (2.8%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 9/637 (1.4%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| productcatalogservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| cartservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| currencyservice | 0/637 (0.0%) | 159/637 (25.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 69/637 (10.8%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| shippingservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| adservice | 4/637 (0.6%) | 0/637 (0.0%) | 1/636 (0.2%) | **┃** | 0/637 (0.0%) | 2/637 (0.3%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |
| redis-cart | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target, the scorer's retry column: the sum of positive Envoy `retry` increments into that service.

- **run35.** frontend → recommendationservice 252, frontend → cartservice 7.
- **run31.** frontend → recommendationservice 225,477, frontend → checkoutservice 26.
- **run7.** frontend → recommendationservice 133,481, frontend → checkoutservice 17,544.
- **run36.** frontend → checkoutservice 100,515.
- **run34.** frontend → checkoutservice 60,933, checkoutservice → paymentservice 3,865.
- **run12.** frontend → checkoutservice 47,538.
- **run37.** frontend → recommendationservice 192, frontend → checkoutservice 18.
- **run33.** frontend → recommendationservice 177,103, frontend → checkoutservice 128.
- **run26.** frontend → recommendationservice 120,541, frontend → checkoutservice 45,182.
- **run38.** frontend → recommendationservice 101, frontend → checkoutservice 68.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| checkoutservice | 0 | 26 | 17,544 | **┃** | 100,515 | 60,933 | 47,538 | **┃** | 18 | 128 | 45,182 | **┃** | 68 |
| recommendationservice | 252 | 225,477 | 133,481 | **┃** | 0 | 0 | 0 | **┃** | 192 | 177,103 | 120,541 | **┃** | 101 |
| paymentservice | 0 | 0 | 0 | **┃** | 0 | 3,865 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| emailservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| productcatalogservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| cartservice | 7 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| currencyservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| shippingservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| adservice | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |
| redis-cart | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`. Quota is the per-pod CPU limit. The mean / max cells sum that usage across the pinned replicas.

| Service | Quota | Replicas | run35 | run36 | run37 | run38 |
|---|---:|---:|---|---|---|---|
| frontend | 1150 | 4 | 1285 / 1495 | 792 / 939 | 1219 / 1417 | 1021 / 1189 |
| checkoutservice | 800 | 2 | 893 / 1102 | 1378 / 1596 | 995 / 1244 | 1171 / 1379 |
| recommendationservice | 800 | 3 | 920 / 1058 | 485 / 586 | 834 / 983 | 727 / 851 |
| paymentservice | 150 | 2 | 74 / 115 | 152 / 201 | 82 / 103 | 89 / 106 |
| emailservice | 150 | 2 | 122 / 145 | 41 / 205 | 144 / 175 | 162 / 191 |
| productcatalogservice | 600 | 1 | 366 / 487 | 298 / 362 | 350 / 427 | 324 / 384 |
| cartservice | 600 | 2 | 366 / 432 | 283 / 394 | 363 / 477 | 285 / 427 |
| currencyservice | 650 | 1 | 414 / 474 | 241 / 290 | 379 / 457 | 328 / 393 |
| shippingservice | 400 | 1 | 118 / 138 | 129 / 152 | 97 / 121 | 128 / 152 |
| adservice | 600 | 1 | 148 / 388 | 64 / 97 | 132 / 158 | 81 / 98 |
| redis-cart | 500 | 1 | 34 / 39 | 26 / 31 | 35 / 41 | 28 / 34 |

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

| API | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| getproduct | 270.2 | 84.7 | 133.5 | **┃** | 96.0 | 96.0 | 95.8 | **┃** | 306.2 | 110.7 | 147.6 | **┃** | 169.7 |
| postcheckout | 73.1 | 26.2 | 16.5 | **┃** | 6.0 | 3.1 | 0.4 | **┃** | 91.5 | 37.5 | 0.7 | **┃** | 103.7 |
| getcart | 203.1 | 72.0 | 104.8 | **┃** | 95.9 | 96.0 | 95.5 | **┃** | 94.7 | 39.6 | 50.0 | **┃** | 174.4 |
| postcart | 13.9 | 13.7 | 10.5 | **┃** | 96.0 | 96.0 | 96.0 | **┃** | 92.0 | 88.1 | 54.9 | **┃** | 34.9 |
| emptycart | 13.3 | 14.0 | 11.3 | **┃** | 4.8 | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | 4.1 | **┃** | 35.0 |

## Locust fail rate

Mean `Fail / RPS` while `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| getproduct | 0.056 | 0.567 | 0.476 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.016 | 0.505 | 0.449 | **┃** | 0.000 |
| postcheckout | 0.028 | 0.524 | 0.731 | **┃** | 0.914 | 0.938 | 0.979 | **┃** | 0.042 | 0.471 | 0.966 | **┃** | 0.009 |
| getcart | 0.045 | 0.524 | 0.448 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.010 | 0.453 | 0.413 | **┃** | 0.001 |
| postcart | 0.098 | 0.058 | 0.352 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.039 | 0.006 | 0.411 | **┃** | 0.000 |
| emptycart | 0.138 | 0.041 | 0.300 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.001 | 0.000 | 0.151 | **┃** | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

| API | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| getproduct | 897 | 2089 | 1872 | **┃** | 525 | 515 | 505 | **┃** | 741 | 2064 | 1921 | **┃** | 788 |
| postcheckout | 870 | 2059 | 2542 | **┃** | 2253 | 1595 | 1278 | **┃** | 864 | 2028 | 3338 | **┃** | 844 |
| getcart | 782 | 2030 | 1698 | **┃** | 476 | 518 | 358 | **┃** | 749 | 1978 | 1689 | **┃** | 681 |
| postcart | 156 | 65 | 63 | **┃** | 130 | 98 | 109 | **┃** | 161 | 82 | 76 | **┃** | 170 |
| emptycart | 61 | 15 | 24 | **┃** | 16 | 12 | 17 | **┃** | 60 | 16 | 19 | **┃** | 84 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 515.4 | 382.7 | 383.0 | **┃** | 332.5 | 353.3 | 360.2 | **┃** | 522.1 | 416.1 | 378.6 | **┃** | 459.5 |
| checkoutservice | 65.6 | 31.4 | 57.0 | **┃** | 218.9 | 176.9 | 104.0 | **┃** | 81.3 | 43.8 | 93.9 | **┃** | 92.6 |
| recommendationservice | 491.4 | 684.0 | 557.0 | **┃** | 243.3 | 264.1 | 271.1 | **┃** | 436.7 | 589.8 | 500.6 | **┃** | 397.6 |
| paymentservice | 65.6 | 31.4 | 52.7 | **┃** | 205.2 | 109.7 | 2.4 | **┃** | 81.3 | 43.8 | 74.3 | **┃** | 92.6 |
| emailservice | 65.6 | 31.4 | 22.0 | **┃** | 16.4 | 7.2 | 0.5 | **┃** | 81.2 | 43.8 | 2.3 | **┃** | 92.6 |
| productcatalogservice | 3200.5 | 1678.7 | 2155.3 | **┃** | 1629.7 | 1754.4 | 1796.1 | **┃** | 2970.2 | 1761.2 | 1920.5 | **┃** | 2565.1 |
| cartservice | 580.8 | 396.5 | 427.6 | **┃** | 536.9 | 440.9 | 348.9 | **┃** | 603.3 | 439.1 | 445.7 | **┃** | 551.8 |
| currencyservice | 981.6 | 631.6 | 704.8 | **┃** | 565.7 | 499.0 | 368.3 | **┃** | 872.8 | 604.9 | 658.3 | **┃** | 794.7 |
| shippingservice | 312.0 | 147.4 | 212.8 | **┃** | 447.7 | 266.7 | 141.7 | **┃** | 246.5 | 132.2 | 183.8 | **┃** | 339.8 |
| adservice | 243.8 | 108.9 | 157.0 | **┃** | 84.8 | 84.8 | 84.8 | **┃** | 270.8 | 137.1 | 173.7 | **┃** | 150.1 |
| redis-cart | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | **┃** | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal from `service_inbound.csv`.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0.001 | 0.347 | 0.181 | **┃** | 0.198 | 0.257 | 0.280 | **┃** | 0.000 | 0.260 | 0.255 | **┃** | 0.000 |
| checkoutservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal from `service_inbound.csv`.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0.001 | 0.002 | 0.002 | **┃** | 0.001 | 0.000 | 0.000 | **┃** | 0.001 | 0.001 | 0.001 | **┃** | 0.001 |
| checkoutservice | 0.000 | 0.001 | 0.378 | **┃** | 0.491 | 0.289 | 0.413 | **┃** | 0.001 | 0.003 | 0.433 | **┃** | 0.001 |
| recommendationservice | 0.000 | 0.199 | 0.185 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.188 | 0.148 | **┃** | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.025 | **┃** | 0.025 | 0.574 | 0.094 | **┃** | 0.000 | 0.000 | 0.059 | **┃** | 0.000 |
| emailservice | 0.000 | 0.001 | 0.019 | **┃** | 0.165 | 0.326 | 0.033 | **┃** | 0.000 | 0.004 | 0.224 | **┃** | 0.001 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | 0.000 | 0.002 | **┃** | 0.016 | 0.004 | 0.003 | **┃** | 0.000 | 0.000 | 0.004 | **┃** | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.007 | **┃** | 0.022 | 0.008 | 0.055 | **┃** | 0.000 | 0.000 | 0.020 | **┃** | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 578 | 936 | 809 | **┃** | 578 | 430 | 340 | **┃** | 450 | 753 | 815 | **┃** | 504 |
| checkoutservice | 112 | 63 | 319 | **┃** | 493 | 350 | 487 | **┃** | 168 | 76 | 502 | **┃** | 181 |
| recommendationservice | 71 | 474 | 449 | **┃** | 45 | 154 | 127 | **┃** | 63 | 469 | 454 | **┃** | 91 |
| paymentservice | 3 | 2 | 6 | **┃** | 6 | 154 | 4 | **┃** | 3 | 3 | 5 | **┃** | 4 |
| emailservice | 6 | 8 | 8 | **┃** | 11 | 80 | 14 | **┃** | 9 | 14 | 9 | **┃** | 12 |
| productcatalogservice | 26 | 3 | 2 | **┃** | 9 | 4 | 2 | **┃** | 21 | 3 | 3 | **┃** | 17 |
| cartservice | 4 | 2 | 3 | **┃** | 9 | 8 | 10 | **┃** | 5 | 3 | 3 | **┃** | 8 |
| currencyservice | 9 | 3 | 4 | **┃** | 21 | 20 | 10 | **┃** | 8 | 3 | 3 | **┃** | 27 |
| shippingservice | 2 | 1 | 1 | **┃** | 3 | 2 | 2 | **┃** | 2 | 1 | 1 | **┃** | 2 |
| adservice | 4 | 1 | 1 | **┃** | 3 | 2 | 2 | **┃** | 3 | 1 | 1 | **┃** | 4 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets`.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0.723 | 0.861 | 0.832 | **┃** | 0.280 | 0.215 | 0.117 | **┃** | 0.462 | 0.738 | 0.765 | **┃** | 0.596 |
| checkoutservice | 0.000 | 0.000 | 0.421 | **┃** | 0.930 | 0.603 | 0.951 | **┃** | 0.000 | 0.002 | 0.982 | **┃** | 0.001 |
| recommendationservice | 0.001 | 0.632 | 0.380 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.001 | 0.579 | 0.454 | **┃** | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a | n/a | n/a | **┃** | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is the per-pod limit in `topfull_detect.csv`. `cpu_millicores` and `replica_count` are from `resource_usage.csv`.

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0.28 / 0.33 | 0.22 / 0.27 | 0.29 / 0.37 | **┃** | 0.17 / 0.20 | 0.17 / 0.23 | 0.23 / 0.30 | **┃** | 0.26 / 0.31 | 0.22 / 0.26 | 0.27 / 0.33 | **┃** | 0.22 / 0.26 |
| checkoutservice | 0.56 / 0.69 | 0.34 / 0.42 | 0.85 / 1.00 | **┃** | 0.86 / 1.00 | 0.75 / 1.00 | 0.61 / 1.00 | **┃** | 0.62 / 0.78 | 0.44 / 0.57 | 0.88 / 1.00 | **┃** | 0.73 / 0.86 |
| recommendationservice | 0.38 / 0.44 | 0.44 / 0.51 | 0.75 / 0.93 | **┃** | 0.20 / 0.24 | 0.27 / 0.37 | 0.54 / 0.74 | **┃** | 0.35 / 0.41 | 0.41 / 0.49 | 0.71 / 0.84 | **┃** | 0.30 / 0.35 |
| paymentservice | 0.25 / 0.38 | 0.21 / 0.28 | 0.30 / 0.45 | **┃** | 0.51 / 0.67 | 0.36 / 1.00 | 0.03 / 0.34 | **┃** | 0.27 / 0.34 | 0.28 / 0.38 | 0.35 / 0.50 | **┃** | 0.30 / 0.35 |
| emailservice | 0.41 / 0.48 | 0.40 / 0.53 | 0.29 / 0.55 | **┃** | 0.14 / 0.68 | 0.11 / 1.00 | 0.06 / 0.34 | **┃** | 0.48 / 0.58 | 0.53 / 0.78 | 0.07 / 0.40 | **┃** | 0.54 / 0.64 |
| productcatalogservice | 0.61 / 0.81 | 0.58 / 0.78 | 0.32 / 0.38 | **┃** | 0.50 / 0.60 | 0.59 / 0.78 | 0.29 / 0.38 | **┃** | 0.58 / 0.71 | 0.59 / 0.74 | 0.27 / 0.33 | **┃** | 0.54 / 0.64 |
| cartservice | 0.30 / 0.36 | 0.29 / 0.40 | 0.22 / 0.31 | **┃** | 0.24 / 0.33 | 0.20 / 0.32 | 0.08 / 0.13 | **┃** | 0.30 / 0.40 | 0.30 / 0.47 | 0.19 / 0.28 | **┃** | 0.24 / 0.36 |
| currencyservice | 0.64 / 0.73 | 0.70 / 0.80 | 0.51 / 0.65 | **┃** | 0.37 / 0.45 | 0.45 / 0.61 | 0.22 / 0.29 | **┃** | 0.58 / 0.70 | 0.67 / 0.79 | 0.46 / 0.55 | **┃** | 0.50 / 0.60 |
| shippingservice | 0.30 / 0.34 | 0.21 / 0.29 | 0.14 / 0.19 | **┃** | 0.32 / 0.38 | 0.27 / 0.38 | 0.08 / 0.13 | **┃** | 0.24 / 0.30 | 0.19 / 0.25 | 0.11 / 0.13 | **┃** | 0.32 / 0.38 |
| adservice | 0.25 / 0.65 | 0.15 / 0.23 | 0.11 / 0.23 | **┃** | 0.11 / 0.16 | 0.13 / 0.23 | 0.07 / 0.09 | **┃** | 0.22 / 0.26 | 0.18 / 0.25 | 0.11 / 0.15 | **┃** | 0.13 / 0.16 |
| redis-cart | 0.07 / 0.08 | 0.06 / 0.07 | 0.05 / 0.06 | **┃** | 0.05 / 0.06 | 0.04 / 0.06 | 0.03 / 0.04 | **┃** | 0.07 / 0.08 | 0.07 / 0.08 | 0.06 / 0.07 | **┃** | 0.06 / 0.07 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run35 | run31 | run7 | **┃** | run36 | run34 | run12 | **┃** | run37 | run33 | run26 | **┃** | run38 |
| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | :---: | ---: |
| frontend | 0.343 | 0.286 | 0.382 | **┃** | 0.229 | 0.240 | 0.326 | **┃** | 0.336 | 0.268 | 0.349 | **┃** | 0.276 |
| checkoutservice | 0.772 | 0.507 | 1.046 | **┃** | 1.051 | 1.052 | 1.059 | **┃** | 0.856 | 0.700 | 1.059 | **┃** | 0.925 |
| recommendationservice | 0.472 | 0.563 | 1.003 | **┃** | 0.289 | 0.419 | 0.797 | **┃** | 0.455 | 0.553 | 0.893 | **┃** | 0.434 |
| paymentservice | 0.503 | 0.427 | 0.742 | **┃** | 0.813 | 1.067 | 0.626 | **┃** | 0.447 | 0.553 | 0.658 | **┃** | 0.480 |
| emailservice | 0.603 | 0.740 | 0.729 | **┃** | 0.813 | 1.020 | 0.516 | **┃** | 0.690 | 0.933 | 0.555 | **┃** | 0.760 |
| productcatalogservice | 0.848 | 0.822 | 0.395 | **┃** | 0.670 | 0.870 | 0.411 | **┃** | 0.758 | 0.782 | 0.356 | **┃** | 0.747 |
| cartservice | 0.406 | 0.425 | 0.340 | **┃** | 0.372 | 0.367 | 0.181 | **┃** | 0.434 | 0.495 | 0.316 | **┃** | 0.389 |
| currencyservice | 0.786 | 0.900 | 0.708 | **┃** | 0.531 | 0.732 | 0.421 | **┃** | 0.762 | 0.902 | 0.597 | **┃** | 0.689 |
| shippingservice | 0.410 | 0.375 | 0.223 | **┃** | 0.487 | 0.450 | 0.171 | **┃** | 0.360 | 0.315 | 0.173 | **┃** | 0.468 |
| adservice | 1.015 | 0.285 | 0.868 | **┃** | 0.273 | 0.873 | 0.137 | **┃** | 0.345 | 0.368 | 0.180 | **┃** | 0.315 |
| redis-cart | 0.084 | 0.078 | 0.074 | **┃** | 0.070 | 0.064 | 0.046 | **┃** | 0.092 | 0.090 | 0.091 | **┃** | 0.076 |

## Per mix

**Mix 7 (380/100/270/20/20).** run35 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 0; run31 clears 0 and 0; run7 clears 1 (checkoutservice) and 2 (checkoutservice, recommendationservice).

**Mix 12 (100/150/100/100/5).** run36 clears streak 30 on 1 controlled service (checkoutservice) and an overloaded share of 0.5 on 1 (checkoutservice); run34 clears 2 (checkoutservice, paymentservice) and 1 (checkoutservice); run12 clears 1 (checkoutservice) and 0.

**Mix 26 (325/100/100/100/5).** run37 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 0; run33 clears 0 and 0; run26 clears 1 (checkoutservice) and 2 (checkoutservice, recommendationservice).

**New mix (250/150/250/50/50).** run38 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 1 (checkoutservice).

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Replica CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- Agreed-table replays run31, run33, and run34: [2026-09-26-s2-cpu-spread-runs-30-34.md](2026-09-26-s2-cpu-spread-runs-30-34.md).
- Earlier both-off run7: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
- Earlier both-off run12: [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
- Earlier both-off run26: [2026-09-26-s2-both-off-replay-runs-26-29.md](2026-09-26-s2-both-off-replay-runs-26-29.md).
- Plan for this series: [2026-09-27-s2-replica-cpu-holds.md](../docs/superpowers/plans/2026-09-27-s2-replica-cpu-holds.md).
