# S2 both-off runs 39–42, all services

600 s holds, both controllers off, `spawn_rate` 50. Checkout-3 CPU table, replicas pinned at the table counts: frontend 4, checkoutservice 3, recommendationservice 3, and productcatalogservice, cartservice, currencyservice, shippingservice, adservice, paymentservice, emailservice, and redis-cart at 1. Sidecar request 100 m with no CPU limit. 360 s cool-off before run39 and between holds. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every number below is from `experiments/s2_both_off_abc.py` on these four folders and on the three earlier mix 7 folders, plus the same Locust, inbound, CPU, and detector reads as [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md).

| Mix | This series | Replica replay | Agreed replay | Earlier both-off |
|---|---|---|---|---|
| new (200/150/200/100/50) | run39 | — | — | — |
| 7 (380/100/270/20/20) | run40 | run35 | run31 | run7 |
| new (325/150/150/100/50) | run41 | — | — | — |
| new (150/250/150/20/20) | run42 | — | — | — |

The tables use that column order, left to right, mix by mix. A bold bar separates the 200/150/200/100/50 hold (run39), mix 7 (run40, run35, run31, run7), the 325/150/150/100/50 hold (run41), and the 150/250/150/20/20 hold (run42).

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | --- | :---: | --- | --- | --- | --- | :---: | --- | :---: | --- |
| frontend (not controlled) | 1 / 1 | **┃** | 2 / 2 | 2 / 2 | 578 / 578 | 21 / 220 | **┃** | 3 / 3 | **┃** | 4 / 90 |
| checkoutservice | 1 / 5 | **┃** | 1 / 2 | 1 / 1 | 0 / 0 | **230 / 264** | **┃** | 1 / 1 | **┃** | **185 / 571** |
| recommendationservice | 0 / 0 | **┃** | 1 / 1 | 1 / 1 | 7 / 292 | 15 / 235 | **┃** | 2 / 2 | **┃** | 1 / 1 |
| paymentservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 4 | **┃** | 0 / 0 | **┃** | 6 / 62 |
| emailservice | 1 / 6 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 | 6 / 87 | **┃** | 0 / 0 | **┃** | 29 / 454 |
| productcatalogservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | **┃** | 2 / 2 | **┃** | 1 / 1 |
| cartservice | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | **┃** | 1 / 1 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 1 / 1 | 0 / 0 | **┃** | 1 / 1 | **┃** | 1 / 1 |
| shippingservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 |
| adservice | 2 / 6 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | **┃** | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on run39, run40, run41, and run42, and 0 on run35, run31, and run7.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | --- | :---: | --- | --- | --- | --- | :---: | --- | :---: | --- |
| frontend | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| checkoutservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **572/636 (89.9%)** | **┃** | 0/644 (0.0%) | **┃** | **579/638 (90.8%)** |
| recommendationservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | **511/636 (80.3%)** | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| paymentservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | **547/638 (85.7%)** |
| emailservice | **415/639 (64.9%)** | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 306/644 (47.5%) | **┃** | **432/638 (67.7%)** |
| productcatalogservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| cartservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| currencyservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 159/637 (25.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| shippingservice | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| adservice | 1/639 (0.2%) | **┃** | 0/638 (0.0%) | 4/637 (0.6%) | 0/637 (0.0%) | 1/636 (0.2%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |
| redis-cart | 0/639 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | **┃** | 0/644 (0.0%) | **┃** | 0/638 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target, the scorer's retry column: the sum of positive Envoy `retry` increments into that service.

- **run39.** frontend → checkoutservice 1,423, frontend → cartservice 7, frontend → recommendationservice 2.
- **run40.** frontend → checkoutservice 31.
- **run35.** frontend → recommendationservice 252, frontend → cartservice 7.
- **run31.** frontend → recommendationservice 225,477, frontend → checkoutservice 26.
- **run7.** frontend → recommendationservice 133,481, frontend → checkoutservice 17,544.
- **run41.** frontend → checkoutservice 13.
- **run42.** frontend → checkoutservice 115,361.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| checkoutservice | 1,423 | **┃** | 31 | 0 | 26 | 17,544 | **┃** | 13 | **┃** | 115,361 |
| recommendationservice | 2 | **┃** | 0 | 252 | 225,477 | 133,481 | **┃** | 0 | **┃** | 0 |
| paymentservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| emailservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| productcatalogservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| cartservice | 7 | **┃** | 0 | 7 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| currencyservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| shippingservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| adservice | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |
| redis-cart | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | **┃** | 0 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`. Quota is the per-pod CPU limit. The mean / max cells sum that usage across the pinned replicas.

| Service | Quota | Replicas | run39 | run40 | run41 | run42 |
|---|---:|---:|---|---|---|---|
| frontend | 1150 | 4 | 1053 / 1253 | 1174 / 1386 | 1078 / 1258 | 859 / 1064 |
| checkoutservice | 800 | 3 | 1276 / 1580 | 746 / 919 | 1224 / 1476 | 2062 / 2394 |
| recommendationservice | 800 | 3 | 714 / 848 | 856 / 1000 | 743 / 885 | 635 / 804 |
| paymentservice | 200 | 1 | 77 / 108 | 44 / 57 | 71 / 100 | 156 / 194 |
| emailservice | 200 | 1 | 148 / 178 | 88 / 108 | 140 / 170 | 153 / 200 |
| productcatalogservice | 600 | 1 | 339 / 400 | 395 / 458 | 344 / 402 | 280 / 343 |
| cartservice | 600 | 1 | 222 / 308 | 242 / 353 | 262 / 391 | 239 / 331 |
| currencyservice | 650 | 1 | 328 / 389 | 367 / 426 | 334 / 395 | 329 / 416 |
| shippingservice | 400 | 1 | 122 / 149 | 96 / 113 | 108 / 130 | 162 / 197 |
| adservice | 600 | 1 | 92 / 263 | 106 / 129 | 94 / 112 | 67 / 84 |
| redis-cart | 300 | 1 | 27 / 33 | 23 / 27 | 29 / 34 | 26 / 33 |

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

| API | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| getproduct | 169.2 | **┃** | 270.5 | 270.2 | 84.7 | 133.5 | **┃** | 245.5 | **┃** | 104.9 |
| postcheckout | 123.8 | **┃** | 70.1 | 73.1 | 26.2 | 16.5 | **┃** | 115.7 | **┃** | 20.5 |
| getcart | 167.8 | **┃** | 194.7 | 203.1 | 72.0 | 104.8 | **┃** | 115.0 | **┃** | 117.6 |
| postcart | 86.8 | **┃** | 15.3 | 13.9 | 13.7 | 10.5 | **┃** | 76.5 | **┃** | 18.0 |
| emptycart | 43.4 | **┃** | 15.0 | 13.3 | 14.0 | 11.3 | **┃** | 39.7 | **┃** | 15.9 |

## Locust fail rate

Mean `Fail / RPS` while `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| getproduct | 0.001 | **┃** | 0.047 | 0.056 | 0.567 | 0.476 | **┃** | 0.017 | **┃** | 0.176 |
| postcheckout | 0.025 | **┃** | 0.043 | 0.028 | 0.524 | 0.731 | **┃** | 0.004 | **┃** | 0.827 |
| getcart | 0.010 | **┃** | 0.056 | 0.045 | 0.524 | 0.448 | **┃** | 0.010 | **┃** | 0.088 |
| postcart | 0.000 | **┃** | 0.016 | 0.098 | 0.058 | 0.352 | **┃** | 0.014 | **┃** | 0.016 |
| emptycart | 0.000 | **┃** | 0.030 | 0.138 | 0.041 | 0.300 | **┃** | 0.000 | **┃** | 0.082 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

| API | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| getproduct | 735 | **┃** | 795 | 897 | 2089 | 1872 | **┃** | 813 | **┃** | 875 |
| postcheckout | 765 | **┃** | 795 | 870 | 2059 | 2542 | **┃** | 808 | **┃** | 2571 |
| getcart | 616 | **┃** | 696 | 782 | 2030 | 1698 | **┃** | 692 | **┃** | 766 |
| postcart | 201 | **┃** | 159 | 156 | 65 | 63 | **┃** | 167 | **┃** | 164 |
| emptycart | 62 | **┃** | 37 | 61 | 15 | 24 | **┃** | 36 | **┃** | 54 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 522.6 | **┃** | 500.5 | 515.4 | 382.7 | 383.0 | **┃** | 518.8 | **┃** | 361.4 |
| checkoutservice | 112.2 | **┃** | 62.1 | 65.6 | 31.4 | 57.0 | **┃** | 101.3 | **┃** | 274.1 |
| recommendationservice | 407.6 | **┃** | 473.6 | 491.4 | 684.0 | 557.0 | **┃** | 417.1 | **┃** | 331.3 |
| paymentservice | 112.2 | **┃** | 62.1 | 65.6 | 31.4 | 52.7 | **┃** | 101.3 | **┃** | 272.4 |
| emailservice | 112.2 | **┃** | 62.1 | 65.6 | 31.4 | 22.0 | **┃** | 101.3 | **┃** | 162.1 |
| productcatalogservice | 2670.9 | **┃** | 3093.6 | 3200.5 | 1678.7 | 2155.3 | **┃** | 2783.5 | **┃** | 2114.8 |
| cartservice | 636.6 | **┃** | 562.4 | 580.8 | 396.5 | 427.6 | **┃** | 619.9 | **┃** | 742.0 |
| currencyservice | 816.8 | **┃** | 947.0 | 981.6 | 631.6 | 704.8 | **┃** | 833.9 | **┃** | 777.7 |
| shippingservice | 372.6 | **┃** | 296.4 | 312.0 | 147.4 | 212.8 | **┃** | 303.2 | **┃** | 630.2 |
| adservice | 149.1 | **┃** | 239.0 | 243.8 | 108.9 | 157.0 | **┃** | 214.8 | **┃** | 111.3 |
| redis-cart | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | **┃** | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal from `service_inbound.csv`.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0.001 | **┃** | 0.000 | 0.001 | 0.347 | 0.181 | **┃** | 0.000 | **┃** | 0.140 |
| checkoutservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| recommendationservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| paymentservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| emailservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| productcatalogservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| currencyservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| adservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | **┃** | n/a | n/a | n/a | n/a | **┃** | n/a | **┃** | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal from `service_inbound.csv`.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0.001 | **┃** | 0.001 | 0.001 | 0.002 | 0.002 | **┃** | 0.001 | **┃** | 0.001 |
| checkoutservice | 0.014 | **┃** | 0.002 | 0.000 | 0.001 | 0.378 | **┃** | 0.000 | **┃** | 0.475 |
| recommendationservice | 0.000 | **┃** | 0.000 | 0.000 | 0.199 | 0.185 | **┃** | 0.000 | **┃** | 0.000 |
| paymentservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.025 | **┃** | 0.000 | **┃** | 0.061 |
| emailservice | 0.019 | **┃** | 0.001 | 0.000 | 0.001 | 0.019 | **┃** | 0.000 | **┃** | 0.395 |
| productcatalogservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.002 | **┃** | 0.000 | **┃** | 0.012 |
| currencyservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.007 | **┃** | 0.000 | **┃** | 0.005 |
| adservice | 0.002 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | **┃** | n/a | n/a | n/a | n/a | **┃** | n/a | **┃** | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 408 | **┃** | 581 | 578 | 936 | 809 | **┃** | 508 | **┃** | 902 |
| checkoutservice | 175 | **┃** | 122 | 112 | 63 | 319 | **┃** | 113 | **┃** | 471 |
| recommendationservice | 15 | **┃** | 11 | 71 | 474 | 449 | **┃** | 13 | **┃** | 20 |
| paymentservice | 8 | **┃** | 4 | 3 | 2 | 6 | **┃** | 4 | **┃** | 37 |
| emailservice | 45 | **┃** | 30 | 6 | 8 | 8 | **┃** | 26 | **┃** | 85 |
| productcatalogservice | 23 | **┃** | 33 | 26 | 3 | 2 | **┃** | 32 | **┃** | 29 |
| cartservice | 7 | **┃** | 5 | 4 | 2 | 3 | **┃** | 6 | **┃** | 11 |
| currencyservice | 11 | **┃** | 8 | 9 | 3 | 4 | **┃** | 9 | **┃** | 13 |
| shippingservice | 2 | **┃** | 2 | 2 | 1 | 1 | **┃** | 2 | **┃** | 4 |
| adservice | 7 | **┃** | 4 | 4 | 1 | 1 | **┃** | 5 | **┃** | 4 |
| redis-cart | n/a | **┃** | n/a | n/a | n/a | n/a | **┃** | n/a | **┃** | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets`.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0.450 | **┃** | 0.830 | 0.723 | 0.861 | 0.832 | **┃** | 0.686 | **┃** | 0.707 |
| checkoutservice | 0.010 | **┃** | 0.000 | 0.000 | 0.000 | 0.421 | **┃** | 0.000 | **┃** | 0.633 |
| recommendationservice | 0.000 | **┃** | 0.000 | 0.001 | 0.632 | 0.380 | **┃** | 0.000 | **┃** | 0.000 |
| paymentservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| emailservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| productcatalogservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| cartservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| currencyservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| shippingservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| adservice | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 |
| redis-cart | n/a | **┃** | n/a | n/a | n/a | n/a | **┃** | n/a | **┃** | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is the per-pod limit in `topfull_detect.csv`. `cpu_millicores` and `replica_count` are from `resource_usage.csv`.

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0.23 / 0.27 | **┃** | 0.26 / 0.30 | 0.28 / 0.33 | 0.22 / 0.27 | 0.29 / 0.37 | **┃** | 0.23 / 0.27 | **┃** | 0.19 / 0.23 |
| checkoutservice | 0.53 / 0.66 | **┃** | 0.31 / 0.38 | 0.56 / 0.69 | 0.34 / 0.42 | 0.85 / 1.00 | **┃** | 0.51 / 0.61 | **┃** | 0.86 / 1.00 |
| recommendationservice | 0.30 / 0.35 | **┃** | 0.36 / 0.42 | 0.38 / 0.44 | 0.44 / 0.51 | 0.75 / 0.93 | **┃** | 0.31 / 0.37 | **┃** | 0.26 / 0.34 |
| paymentservice | 0.39 / 0.54 | **┃** | 0.22 / 0.28 | 0.25 / 0.38 | 0.21 / 0.28 | 0.30 / 0.45 | **┃** | 0.35 / 0.50 | **┃** | 0.78 / 0.97 |
| emailservice | 0.74 / 0.89 | **┃** | 0.44 / 0.54 | 0.41 / 0.48 | 0.40 / 0.53 | 0.29 / 0.55 | **┃** | 0.70 / 0.85 | **┃** | 0.76 / 1.00 |
| productcatalogservice | 0.56 / 0.67 | **┃** | 0.66 / 0.76 | 0.61 / 0.81 | 0.58 / 0.78 | 0.32 / 0.38 | **┃** | 0.57 / 0.67 | **┃** | 0.47 / 0.57 |
| cartservice | 0.37 / 0.51 | **┃** | 0.40 / 0.59 | 0.30 / 0.36 | 0.29 / 0.40 | 0.22 / 0.31 | **┃** | 0.44 / 0.65 | **┃** | 0.40 / 0.55 |
| currencyservice | 0.50 / 0.60 | **┃** | 0.56 / 0.66 | 0.64 / 0.73 | 0.70 / 0.80 | 0.51 / 0.65 | **┃** | 0.51 / 0.61 | **┃** | 0.51 / 0.64 |
| shippingservice | 0.30 / 0.37 | **┃** | 0.24 / 0.28 | 0.30 / 0.34 | 0.21 / 0.29 | 0.14 / 0.19 | **┃** | 0.27 / 0.33 | **┃** | 0.41 / 0.49 |
| adservice | 0.15 / 0.44 | **┃** | 0.18 / 0.21 | 0.25 / 0.65 | 0.15 / 0.23 | 0.11 / 0.23 | **┃** | 0.16 / 0.19 | **┃** | 0.11 / 0.14 |
| redis-cart | 0.09 / 0.11 | **┃** | 0.08 / 0.09 | 0.07 / 0.08 | 0.06 / 0.07 | 0.05 / 0.06 | **┃** | 0.10 / 0.11 | **┃** | 0.09 / 0.11 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run39 | **┃** | run40 | run35 | run31 | run7 | **┃** | run41 | **┃** | run42 |
| --- | ---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | ---: |
| frontend | 0.290 | **┃** | 0.329 | 0.343 | 0.286 | 0.382 | **┃** | 0.294 | **┃** | 0.242 |
| checkoutservice | 0.737 | **┃** | 0.462 | 0.772 | 0.507 | 1.046 | **┃** | 0.674 | **┃** | 1.016 |
| recommendationservice | 0.415 | **┃** | 0.465 | 0.472 | 0.563 | 1.003 | **┃** | 0.399 | **┃** | 0.380 |
| paymentservice | 0.785 | **┃** | 0.455 | 0.503 | 0.427 | 0.742 | **┃** | 0.630 | **┃** | 1.045 |
| emailservice | 1.035 | **┃** | 0.760 | 0.603 | 0.740 | 0.729 | **┃** | 1.015 | **┃** | 1.080 |
| productcatalogservice | 0.750 | **┃** | 0.860 | 0.848 | 0.822 | 0.395 | **┃** | 0.747 | **┃** | 0.642 |
| cartservice | 0.577 | **┃** | 0.642 | 0.406 | 0.425 | 0.340 | **┃** | 0.727 | **┃** | 0.573 |
| currencyservice | 0.674 | **┃** | 0.720 | 0.786 | 0.900 | 0.708 | **┃** | 0.688 | **┃** | 0.717 |
| shippingservice | 0.448 | **┃** | 0.365 | 0.410 | 0.375 | 0.223 | **┃** | 0.403 | **┃** | 0.575 |
| adservice | 0.992 | **┃** | 0.355 | 1.015 | 0.285 | 0.868 | **┃** | 0.312 | **┃** | 0.205 |
| redis-cart | 0.123 | **┃** | 0.103 | 0.084 | 0.078 | 0.074 | **┃** | 0.127 | **┃** | 0.127 |

## Per mix

**200/150/200/100/50.** run39 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 1 (emailservice).

**Mix 7 (380/100/270/20/20).** run40 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 0; run35 clears 0 and 0; run31 clears 0 and 0; run7 clears 1 (checkoutservice) and 2 (checkoutservice, recommendationservice).

**325/150/150/100/50.** run41 clears streak 30 on 0 controlled services and an overloaded share of 0.5 on 0.

**150/250/150/20/20.** run42 clears streak 30 on 1 controlled service (checkoutservice) and an overloaded share of 0.5 on 3 (checkoutservice, paymentservice, emailservice).

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Checkout-3 CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- Replica-table mix 7 replay (run35): [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md).
- Agreed-table mix 7 replay (run31): [2026-09-26-s2-cpu-spread-runs-30-34.md](2026-09-26-s2-cpu-spread-runs-30-34.md).
- Earlier both-off run7: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
