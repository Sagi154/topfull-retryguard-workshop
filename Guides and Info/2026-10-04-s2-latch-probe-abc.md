# S2 latch-probe runs 108–126, all services

600 s holds, both controllers off, `spawn_rate` 50 except the `spawn10` holds. Paper-C1, frontend pinned at 4, sidecar request 100 m with no CPU limit. One change from the run 89 mix (275 / 90 / 100 / 90 / 5) per hold, in two shuffled blocks (seed 20261003). How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The probe and its class labels: [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md).

Eighteen holds passed the sampling gate. Run116 failed it (`total.csv` has 4 rows) and is omitted. Run127 was not run. A truncated first launch of run123 is under `experiments/results/new vms/_discarded/` and is not in these tables. Every number below is from `experiments/s2_both_off_abc.py` on the eighteen folders in `experiments/results/new vms/`, plus the five Locust CSVs, `service_inbound.csv`, `resource_usage.csv`, and `topfull_detect.csv`. This scorer does not drop the last 5 inbound polls. The probe results guide does, so a streak there can be a few samples shorter.

Each comparison table is split into block A and block B so the eighteen columns are not one row.

### Block A

| Slot | Treatment | Change from the base | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
| --- | --- | --- | --- |
| run108 | restart | roll checkout and recommendations before Locust | 275 / 90 / 100 / 90 / 5 |
| run109 | spawn10 | `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run110 | recs_cpu1000 | recommendations 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |
| run111 | control | none | 275 / 90 / 100 / 90 / 5 |
| run112 | ck_rep2 | checkout 800 m × 2 | 275 / 90 / 100 / 90 / 5 |
| run113 | ck_cpu1000 | checkout 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |
| run114 | recs_users310 | getproduct 310 | 310 / 90 / 100 / 90 / 5 |
| run115 | ck_rep2_pc120 | checkout 800 m × 2, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run117 | pc120 | postcheckout 120 | 275 / 120 / 100 / 90 / 5 |

### Block B

| Slot | Treatment | Change from the base | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
| --- | --- | --- | --- |
| run118 | recs_users310 | getproduct 310 | 310 / 90 / 100 / 90 / 5 |
| run119 | ck_rep2 | checkout 800 m × 2 | 275 / 90 / 100 / 90 / 5 |
| run120 | spawn10 | `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run121 | control | none | 275 / 90 / 100 / 90 / 5 |
| run122 | ck_cpu1000 | checkout 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |
| run123 | ck_rep2_pc120 | checkout 800 m × 2, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run124 | restart | roll checkout and recommendations before Locust | 275 / 90 / 100 / 90 / 5 |
| run125 | pc120 | postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run126 | recs_cpu1000 | recommendations 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend (not controlled) | 558 / 558 | 78 / 306 | 45 / 45 | 212 / 385 | 554 / 554 | 384 / 560 | 561 / 561 | 561 / 561 | 562 / 562 |
| checkoutservice | 12 / 12 | **283 / 283** | **496 / 496** | **181 / 181** | 0 / 0 | 0 / 0 | 9 / 12 | 11 / 12 | 19 / 19 |
| recommendationservice | **558 / 558** | 11 / 202 | **45 / 45** | **69 / 316** | **145 / 538** | **143 / 542** | **185 / 548** | **116 / 536** | **136 / 544** |
| paymentservice | 1 / 3 | 1 / 4 | 1 / 7 | 1 / 3 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 |
| emailservice | 5 / 6 | 6 / 119 | 3 / 94 | 4 / 56 | 0 / 0 | 0 / 0 | 5 / 7 | 11 / 11 | 3 / 5 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend (not controlled) | 565 / 565 | 49 / 520 | 410 / 584 | 561 / 561 | 563 / 563 | 218 / 543 | 2 / 2 | 2 / 4 | 2 / 2 |
| checkoutservice | 0 / 0 | 0 / 0 | 14 / 14 | 11 / 11 | 0 / 0 | 20 / 20 | **571 / 571** | **553 / 576** | **568 / 568** |
| recommendationservice | **124 / 552** | 21 / 391 | **45 / 492** | **156 / 529** | **563 / 563** | 20 / 399 | 1 / 1 | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 14 | 9 / 248 | 2 / 9 |
| emailservice | 0 / 0 | 0 / 0 | 2 / 4 | 4 / 6 | 0 / 0 | 21 / 21 | 6 / 105 | 1 / 4 | 5 / 125 |
| productcatalogservice | 1 / 1 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on every hold in both blocks.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| checkoutservice | 36/638 (5.6%) | **379/637 (59.5%)** | **548/638 (85.9%)** | 252/637 (39.6%) | 0/637 (0.0%) | 25/638 (3.9%) | 40/639 (6.3%) | 12/639 (1.9%) | 92/637 (14.4%) |
| recommendationservice | **558/638 (87.5%)** | **321/637 (50.4%)** | **506/638 (79.3%)** | **387/637 (60.8%)** | **558/637 (87.6%)** | **557/638 (87.3%)** | **561/639 (87.8%)** | **547/639 (85.6%)** | **561/637 (88.1%)** |
| paymentservice | 4/638 (0.6%) | 1/637 (0.2%) | 1/638 (0.2%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 4/639 (0.6%) | 0/637 (0.0%) |
| emailservice | 11/638 (1.7%) | 24/637 (3.8%) | 13/638 (2.0%) | 21/637 (3.3%) | 34/637 (5.3%) | 28/638 (4.4%) | 12/639 (1.9%) | 142/639 (22.2%) | 36/637 (5.7%) |
| productcatalogservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| cartservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| currencyservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| shippingservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| adservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |
| redis-cart | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/639 (0.0%) | 0/639 (0.0%) | 0/637 (0.0%) |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| checkoutservice | 31/637 (4.9%) | 0/638 (0.0%) | 69/637 (10.8%) | 48/637 (7.5%) | 23/638 (3.6%) | 19/637 (3.0%) | **590/637 (92.6%)** | **589/637 (92.5%)** | **591/637 (92.8%)** |
| recommendationservice | **564/637 (88.5%)** | **449/638 (70.4%)** | **593/637 (93.1%)** | **560/637 (87.9%)** | **563/638 (88.2%)** | **530/637 (83.2%)** | 0/637 (0.0%) | 0/637 (0.0%) | 98/637 (15.4%) |
| paymentservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 12/637 (1.9%) | 2/637 (0.3%) | 0/637 (0.0%) | 4/637 (0.6%) |
| emailservice | 16/637 (2.5%) | 125/638 (19.6%) | 15/637 (2.4%) | 12/637 (1.9%) | 21/638 (3.3%) | 204/637 (32.0%) | 10/637 (1.6%) | 13/637 (2.0%) | 14/637 (2.2%) |
| productcatalogservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| cartservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| currencyservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| shippingservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| adservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| redis-cart | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target, the scorer's retry column: the sum of positive Envoy `retry` increments into that service.

### Block A

- **run108.** frontend → recommendationservice 292,131, frontend → checkoutservice 1,094, frontend → cartservice 4.
- **run109.** frontend → recommendationservice 105,651, frontend → checkoutservice 27,798.
- **run110.** frontend → checkoutservice 56,837, frontend → recommendationservice 22,814.
- **run111.** frontend → recommendationservice 141,345, frontend → checkoutservice 19,091.
- **run112.** frontend → recommendationservice 224,832, frontend → checkoutservice 7.
- **run113.** frontend → recommendationservice 239,467, frontend → checkoutservice 21.
- **run114.** frontend → recommendationservice 226,938, frontend → checkoutservice 830.
- **run115.** frontend → recommendationservice 217,861, frontend → checkoutservice 1,194.
- **run117.** frontend → recommendationservice 230,747, frontend → checkoutservice 2,213.

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 1,094 | 27,798 | 56,837 | 19,091 | 7 | 21 | 830 | 1,194 | 2,213 |
| recommendationservice | 292,131 | 105,651 | 22,814 | 141,345 | 224,832 | 239,467 | 226,938 | 217,861 | 230,747 |
| paymentservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cartservice | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Block B

- **run118.** frontend → recommendationservice 241,497, frontend → checkoutservice 13.
- **run119.** frontend → recommendationservice 170,432, frontend → checkoutservice 2.
- **run120.** frontend → recommendationservice 213,137, frontend → checkoutservice 1,303.
- **run121.** frontend → recommendationservice 226,799, frontend → checkoutservice 1,039.
- **run122.** frontend → recommendationservice 279,481, frontend → checkoutservice 39.
- **run123.** frontend → recommendationservice 194,503, frontend → checkoutservice 2,335.
- **run124.** frontend → checkoutservice 64,036.
- **run125.** frontend → checkoutservice 87,211.
- **run126.** frontend → checkoutservice 64,124.

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 13 | 2 | 1,303 | 1,039 | 39 | 2,335 | 64,036 | 87,211 | 64,124 |
| recommendationservice | 241,497 | 170,432 | 213,137 | 226,799 | 279,481 | 194,503 | 0 | 0 | 0 |
| paymentservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`. Quota is the Paper-C1 per-pod limit. Replicas is the Paper-C1 pin. The mean / max cells sum usage across replicas, so a two-replica checkout can sit above the per-pod quota. Holds that leave that pin are listed under the tables.

### Block A

| Service | Quota | Replicas | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 1150 | 4 | 989 / 1468 | 1158 / 1380 | 1325 / 1567 | 1194 / 1541 | 1091 / 1453 | 1059 / 1447 | 1165 / 1499 | 1111 / 1361 | 1135 / 1495 |
| checkoutservice | 800 | 1 | 67 / 793 | 606 / 798 | 660 / 800 | 519 / 798 | 500 / 1144 | 346 / 883 | 471 / 789 | 706 / 1325 | 501 / 794 |
| recommendationservice | 1150 | 1 | 987 / 1152 | 818 / 1057 | 738 / 1000 | 834 / 1148 | 897 / 1125 | 923 / 1150 | 889 / 1057 | 848 / 1041 | 903 / 1072 |
| paymentservice | 155 | 1 | 10 / 117 | 53 / 96 | 66 / 86 | 42 / 84 | 31 / 72 | 24 / 60 | 32 / 75 | 45 / 98 | 35 / 76 |
| emailservice | 120 | 1 | 14 / 107 | 41 / 90 | 13 / 104 | 43 / 103 | 57 / 115 | 45 / 111 | 60 / 103 | 79 / 119 | 65 / 103 |
| productcatalogservice | 800 | 1 | 295 / 486 | 407 / 508 | 440 / 523 | 382 / 487 | 352 / 461 | 340 / 463 | 368 / 472 | 352 / 450 | 361 / 498 |
| cartservice | 800 | 1 | 350 / 441 | 225 / 376 | 308 / 384 | 340 / 484 | 327 / 396 | 335 / 469 | 333 / 469 | 321 / 397 | 333 / 404 |
| currencyservice | 770 | 1 | 288 / 413 | 316 / 400 | 364 / 438 | 330 / 431 | 307 / 408 | 300 / 404 | 322 / 409 | 312 / 375 | 315 / 406 |
| shippingservice | 770 | 1 | 13 / 109 | 82 / 112 | 90 / 111 | 70 / 113 | 58 / 126 | 45 / 108 | 63 / 107 | 78 / 141 | 63 / 102 |
| adservice | 1150 | 1 | 67 / 411 | 118 / 166 | 145 / 178 | 104 / 170 | 80 / 143 | 71 / 146 | 95 / 168 | 87 / 142 | 86 / 160 |
| redis-cart | 540 | 1 | 43 / 58 | 26 / 37 | 36 / 45 | 39 / 49 | 41 / 49 | 41 / 50 | 40 / 47 | 40 / 48 | 40 / 48 |

### Block B

| Service | Quota | Replicas | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 1150 | 4 | 1120 / 1522 | 1165 / 1442 | 1110 / 1355 | 1106 / 1485 | 983 / 1512 | 1150 / 1391 | 1384 / 1604 | 1368 / 1589 | 1371 / 1593 |
| checkoutservice | 800 | 1 | 384 / 790 | 684 / 1107 | 429 / 791 | 398 / 799 | 139 / 930 | 739 / 1588 | 706 / 802 | 683 / 801 | 704 / 799 |
| recommendationservice | 1150 | 1 | 924 / 1124 | 833 / 1030 | 943 / 1148 | 919 / 1123 | 975 / 1151 | 854 / 1032 | 711 / 860 | 704 / 834 | 677 / 813 |
| paymentservice | 155 | 1 | 26 / 61 | 42 / 68 | 30 / 81 | 28 / 75 | 11 / 66 | 48 / 128 | 70 / 89 | 43 / 69 | 72 / 123 |
| emailservice | 120 | 1 | 50 / 109 | 76 / 115 | 55 / 86 | 51 / 96 | 23 / 116 | 82 / 120 | 12 / 100 | 10 / 94 | 12 / 106 |
| productcatalogservice | 800 | 1 | 359 / 478 | 370 / 445 | 365 / 472 | 358 / 476 | 311 / 480 | 375 / 487 | 463 / 528 | 463 / 531 | 460 / 529 |
| cartservice | 800 | 1 | 334 / 410 | 329 / 398 | 292 / 421 | 338 / 440 | 332 / 411 | 334 / 402 | 313 / 376 | 298 / 357 | 313 / 452 |
| currencyservice | 770 | 1 | 317 / 399 | 327 / 391 | 318 / 385 | 308 / 385 | 280 / 401 | 325 / 398 | 367 / 441 | 363 / 426 | 361 / 425 |
| shippingservice | 770 | 1 | 50 / 104 | 80 / 122 | 57 / 109 | 52 / 106 | 20 / 121 | 81 / 167 | 93 / 111 | 88 / 104 | 92 / 108 |
| adservice | 1150 | 1 | 82 / 161 | 98 / 140 | 83 / 143 | 80 / 157 | 50 / 160 | 94 / 153 | 158 / 188 | 153 / 184 | 151 / 179 |
| redis-cart | 540 | 1 | 41 / 48 | 40 / 47 | 32 / 38 | 41 / 51 | 42 / 51 | 40 / 48 | 36 / 43 | 35 / 42 | 36 / 44 |

Holds that leave the Paper-C1 pin, from `topfull_detect.csv` quota and `resource_usage.csv` replica mode: run110 and run126 recommendations quota 1000 m; run113 and run122 checkout quota 1000 m; run112, run115, run119, and run123 checkout replicas 2 (quota still 800 m). Every other service stays on the pin above.

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

### Block A

| API | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 13.4 | 175.3 | 244.4 | 131.7 | 59.4 | 46.5 | 78.4 | 74.7 | 65.7 |
| postcheckout | 2.9 | 14.8 | 3.4 | 16.1 | 21.6 | 16.4 | 22.1 | 32.7 | 22.9 |
| getcart | 5.0 | 63.2 | 88.2 | 49.7 | 24.7 | 19.5 | 29.0 | 30.9 | 26.4 |
| postcart | 86.2 | 88.7 | 86.3 | 86.3 | 86.3 | 86.3 | 80.8 | 83.9 | 81.6 |
| emptycart | 4.8 | 4.9 | 4.8 | 4.8 | 4.8 | 4.8 | 4.3 | 4.6 | 4.4 |

### Block B

| API | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 58.6 | 101.7 | 67.0 | 56.9 | 18.0 | 94.0 | 263.8 | 263.8 | 264.2 |
| postcheckout | 17.7 | 34.9 | 19.3 | 17.5 | 6.3 | 36.7 | 2.5 | 2.4 | 2.9 |
| getcart | 21.4 | 41.0 | 27.4 | 23.4 | 7.2 | 36.3 | 95.8 | 95.7 | 96.0 |
| postcart | 82.9 | 86.4 | 87.1 | 86.3 | 86.4 | 85.3 | 86.4 | 86.3 | 86.4 |
| emptycart | 4.6 | 4.8 | 5.0 | 4.8 | 4.8 | 4.7 | 4.8 | 4.8 | 4.8 |

## Locust fail rate

Mean of `Fail / RPS` on rows with `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

### Block A

| API | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 0.909 | 0.318 | 0.069 | 0.441 | 0.686 | 0.750 | 0.637 | 0.617 | 0.656 |
| postcheckout | 0.926 | 0.791 | 0.918 | 0.739 | 0.658 | 0.734 | 0.642 | 0.615 | 0.709 |
| getcart | 0.907 | 0.323 | 0.068 | 0.424 | 0.653 | 0.722 | 0.598 | 0.579 | 0.628 |
| postcart | 0.003 | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 | 0.061 | 0.027 | 0.052 |
| emptycart | 0.015 | 0.012 | 0.000 | 0.000 | 0.000 | 0.001 | 0.107 | 0.054 | 0.084 |

### Block B

| API | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 0.710 | 0.518 | 0.688 | 0.700 | 0.880 | 0.548 | 0.000 | 0.000 | 0.000 |
| postcheckout | 0.699 | 0.499 | 0.721 | 0.711 | 0.876 | 0.583 | 0.931 | 0.942 | 0.927 |
| getcart | 0.683 | 0.480 | 0.660 | 0.670 | 0.874 | 0.526 | 0.000 | 0.000 | 0.000 |
| postcart | 0.018 | 0.000 | 0.024 | 0.000 | 0.000 | 0.011 | 0.000 | 0.000 | 0.000 |
| emptycart | 0.043 | 0.000 | 0.000 | 0.000 | 0.005 | 0.021 | 0.000 | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

### Block A

| API | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 2035 | 1484 | 475 | 1509 | 2032 | 2034 | 2036 | 2032 | 2034 |
| postcheckout | 2032 | 2334 | 2213 | 2096 | 1990 | 1998 | 2043 | 2025 | 2074 |
| getcart | 1994 | 1429 | 484 | 1464 | 1968 | 1977 | 1972 | 1967 | 1968 |
| postcart | 62 | 116 | 74 | 68 | 66 | 65 | 68 | 68 | 65 |
| emptycart | 17 | 32 | 16 | 14 | 16 | 18 | 15 | 17 | 14 |

### Block B

| API | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 2044 | 2006 | 2130 | 2030 | 2043 | 1975 | 308 | 292 | 271 |
| postcheckout | 2017 | 1970 | 2141 | 2030 | 2000 | 2005 | 2207 | 2205 | 2164 |
| getcart | 1976 | 1937 | 2062 | 1961 | 1994 | 1919 | 317 | 308 | 285 |
| postcart | 64 | 69 | 93 | 64 | 61 | 66 | 71 | 71 | 70 |
| emptycart | 14 | 14 | 14 | 14 | 12 | 16 | 15 | 21 | 21 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 341.4 | 432.7 | 430.6 | 406.5 | 381.2 | 373.2 | 381.3 | 396.7 | 383.4 |
| checkoutservice | 5.2 | 78.2 | 119.6 | 59.8 | 28.3 | 21.3 | 30.9 | 44.6 | 37.2 |
| recommendationservice | 682.2 | 502.3 | 383.0 | 529.9 | 625.4 | 637.7 | 632.0 | 631.4 | 640.6 |
| paymentservice | 5.1 | 72.1 | 97.3 | 54.5 | 28.3 | 21.3 | 30.9 | 44.6 | 35.8 |
| emailservice | 3.3 | 20.5 | 3.8 | 21.2 | 28.3 | 21.3 | 29.6 | 44.6 | 33.0 |
| productcatalogservice | 605.2 | 2047.8 | 2304.3 | 1730.9 | 1310.9 | 1131.9 | 1441.3 | 1494.8 | 1350.4 |
| cartservice | 300.0 | 485.7 | 519.6 | 437.7 | 379.1 | 358.9 | 387.6 | 409.0 | 381.9 |
| currencyservice | 378.1 | 674.0 | 735.4 | 602.3 | 505.9 | 474.2 | 536.8 | 542.6 | 510.1 |
| shippingservice | 14.6 | 188.4 | 240.4 | 147.0 | 88.0 | 66.8 | 96.7 | 126.6 | 103.8 |
| adservice | 13.2 | 173.8 | 214.4 | 137.1 | 83.7 | 64.2 | 106.0 | 99.9 | 88.4 |
| redis-cart | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 383.1 | 408.6 | 400.2 | 380.5 | 352.8 | 418.1 | 440.4 | 455.1 | 440.3 |
| checkoutservice | 23.9 | 41.3 | 29.8 | 26.2 | 8.0 | 51.1 | 134.2 | 181.7 | 134.7 |
| recommendationservice | 653.8 | 574.0 | 626.7 | 627.5 | 675.6 | 619.4 | 359.8 | 374.3 | 359.7 |
| paymentservice | 23.9 | 41.3 | 29.6 | 26.1 | 8.0 | 51.1 | 105.3 | 61.3 | 109.5 |
| emailservice | 23.9 | 41.3 | 27.3 | 24.3 | 8.0 | 51.1 | 3.0 | 2.2 | 3.5 |
| productcatalogservice | 1280.6 | 1715.0 | 1406.5 | 1271.4 | 742.7 | 1674.9 | 2467.8 | 2555.5 | 2467.4 |
| cartservice | 376.3 | 427.5 | 396.7 | 374.3 | 315.7 | 440.1 | 542.9 | 581.9 | 544.2 |
| currencyservice | 515.3 | 586.6 | 535.9 | 499.6 | 403.7 | 586.5 | 770.3 | 811.0 | 770.4 |
| shippingservice | 75.3 | 129.3 | 92.4 | 81.4 | 24.6 | 144.4 | 261.7 | 272.1 | 267.2 |
| adservice | 83.8 | 126.9 | 90.6 | 80.0 | 23.0 | 115.0 | 233.1 | 233.4 | 232.8 |
| redis-cart | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal from `service_inbound.csv`.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.702 | 0.219 | 0.125 | 0.290 | 0.410 | 0.489 | 0.355 | 0.350 | 0.399 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.444 | 0.276 | 0.416 | 0.435 | 0.658 | 0.321 | 0.089 | 0.118 | 0.089 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal from `service_inbound.csv`.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.002 | 0.001 | 0.001 | 0.001 | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 |
| checkoutservice | 0.242 | 0.378 | 0.549 | 0.368 | 0.000 | 0.001 | 0.031 | 0.025 | 0.067 |
| recommendationservice | 0.290 | 0.148 | 0.043 | 0.184 | 0.259 | 0.261 | 0.256 | 0.251 | 0.250 |
| paymentservice | 0.054 | 0.031 | 0.067 | 0.030 | 0.000 | 0.000 | 0.001 | 0.000 | 0.008 |
| emailservice | 0.036 | 0.023 | 0.062 | 0.014 | 0.000 | 0.001 | 0.007 | 0.045 | 0.004 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.003 | 0.004 | 0.002 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.006 | 0.013 | 0.022 | 0.012 | 0.000 | 0.000 | 0.000 | 0.000 | 0.001 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.002 | 0.001 | 0.001 | 0.002 | 0.002 | 0.001 | 0.000 | 0.000 | 0.000 |
| checkoutservice | 0.000 | 0.000 | 0.046 | 0.043 | 0.005 | 0.042 | 0.559 | 0.580 | 0.546 |
| recommendationservice | 0.253 | 0.214 | 0.233 | 0.250 | 0.273 | 0.212 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.004 | 0.002 | 0.000 | 0.000 | 0.073 | 0.175 | 0.065 |
| emailservice | 0.001 | 0.000 | 0.003 | 0.003 | 0.006 | 0.076 | 0.086 | 0.025 | 0.091 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.004 | 0.001 | 0.005 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.001 | 0.001 | 0.000 | 0.000 | 0.023 | 0.009 | 0.024 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 1041 | 655 | 368 | 658 | 859 | 894 | 873 | 840 | 887 |
| checkoutservice | 237 | 350 | 483 | 286 | 66 | 85 | 117 | 99 | 162 |
| recommendationservice | 487 | 390 | 141 | 389 | 475 | 479 | 470 | 470 | 475 |
| paymentservice | 18 | 7 | 7 | 5 | 2 | 2 | 3 | 3 | 3 |
| emailservice | 37 | 15 | 35 | 14 | 16 | 20 | 16 | 34 | 23 |
| productcatalogservice | 1 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 2 |
| cartservice | 3 | 7 | 5 | 4 | 3 | 3 | 3 | 3 | 3 |
| currencyservice | 2 | 10 | 5 | 3 | 2 | 2 | 3 | 2 | 2 |
| shippingservice | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| adservice | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 894 | 738 | 839 | 866 | 995 | 778 | 298 | 333 | 279 |
| checkoutservice | 97 | 69 | 124 | 112 | 97 | 110 | 487 | 490 | 486 |
| recommendationservice | 479 | 464 | 486 | 478 | 487 | 466 | 85 | 72 | 69 |
| paymentservice | 2 | 2 | 3 | 3 | 2 | 3 | 7 | 5 | 8 |
| emailservice | 13 | 20 | 13 | 13 | 29 | 39 | 23 | 32 | 20 |
| productcatalogservice | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 |
| cartservice | 3 | 3 | 4 | 3 | 3 | 3 | 4 | 5 | 4 |
| currencyservice | 2 | 2 | 3 | 2 | 2 | 2 | 5 | 5 | 4 |
| shippingservice | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| adservice | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets` (`+Inf` minus the 500 ms bucket, over `+Inf`).

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.718 | 0.608 | 0.130 | 0.530 | 0.738 | 0.737 | 0.740 | 0.747 | 0.751 |
| checkoutservice | 0.234 | 0.603 | 0.937 | 0.456 | 0.000 | 0.001 | 0.024 | 0.033 | 0.058 |
| recommendationservice | 0.961 | 0.396 | 0.097 | 0.524 | 0.733 | 0.803 | 0.670 | 0.657 | 0.712 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.754 | 0.740 | 0.777 | 0.741 | 0.729 | 0.740 | 0.090 | 0.117 | 0.090 |
| checkoutservice | 0.001 | 0.000 | 0.047 | 0.039 | 0.004 | 0.058 | 0.956 | 0.960 | 0.953 |
| recommendationservice | 0.761 | 0.570 | 0.737 | 0.758 | 0.935 | 0.629 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is that run's per-pod limit in `topfull_detect.csv`. `cpu_millicores` and `replica_count` are from `resource_usage.csv`. Samples with `replica_count` 0 are left out.

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.22 / 0.32 | 0.25 / 0.30 | 0.29 / 0.34 | 0.26 / 0.34 | 0.24 / 0.32 | 0.23 / 0.31 | 0.25 / 0.33 | 0.24 / 0.30 | 0.25 / 0.33 |
| checkoutservice | 0.08 / 0.99 | 0.76 / 1.00 | 0.83 / 1.00 | 0.65 / 1.00 | 0.31 / 0.71 | 0.35 / 0.88 | 0.59 / 0.99 | 0.44 / 0.83 | 0.63 / 0.99 |
| recommendationservice | 0.86 / 1.00 | 0.71 / 0.92 | 0.74 / 1.00 | 0.72 / 1.00 | 0.78 / 0.98 | 0.80 / 1.00 | 0.77 / 0.92 | 0.74 / 0.91 | 0.79 / 0.93 |
| paymentservice | 0.06 / 0.75 | 0.34 / 0.62 | 0.43 / 0.55 | 0.27 / 0.54 | 0.20 / 0.46 | 0.16 / 0.39 | 0.21 / 0.48 | 0.29 / 0.63 | 0.23 / 0.49 |
| emailservice | 0.12 / 0.89 | 0.34 / 0.75 | 0.11 / 0.87 | 0.36 / 0.86 | 0.47 / 0.96 | 0.38 / 0.93 | 0.50 / 0.86 | 0.66 / 0.99 | 0.54 / 0.86 |
| productcatalogservice | 0.37 / 0.61 | 0.51 / 0.64 | 0.55 / 0.65 | 0.48 / 0.61 | 0.44 / 0.58 | 0.42 / 0.58 | 0.46 / 0.59 | 0.44 / 0.56 | 0.45 / 0.62 |
| cartservice | 0.44 / 0.55 | 0.28 / 0.47 | 0.38 / 0.48 | 0.43 / 0.60 | 0.41 / 0.49 | 0.42 / 0.59 | 0.42 / 0.59 | 0.40 / 0.50 | 0.42 / 0.51 |
| currencyservice | 0.37 / 0.54 | 0.41 / 0.52 | 0.47 / 0.57 | 0.43 / 0.56 | 0.40 / 0.53 | 0.39 / 0.52 | 0.42 / 0.53 | 0.40 / 0.49 | 0.41 / 0.53 |
| shippingservice | 0.02 / 0.14 | 0.11 / 0.15 | 0.12 / 0.14 | 0.09 / 0.15 | 0.08 / 0.16 | 0.06 / 0.14 | 0.08 / 0.14 | 0.10 / 0.18 | 0.08 / 0.13 |
| adservice | 0.06 / 0.36 | 0.10 / 0.14 | 0.13 / 0.15 | 0.09 / 0.15 | 0.07 / 0.12 | 0.06 / 0.13 | 0.08 / 0.15 | 0.08 / 0.12 | 0.07 / 0.14 |
| redis-cart | 0.08 / 0.11 | 0.05 / 0.07 | 0.07 / 0.08 | 0.07 / 0.09 | 0.08 / 0.09 | 0.08 / 0.09 | 0.07 / 0.09 | 0.07 / 0.09 | 0.07 / 0.09 |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.24 / 0.33 | 0.25 / 0.31 | 0.24 / 0.29 | 0.24 / 0.32 | 0.21 / 0.33 | 0.25 / 0.30 | 0.30 / 0.35 | 0.30 / 0.35 | 0.30 / 0.35 |
| checkoutservice | 0.48 / 0.99 | 0.43 / 0.69 | 0.54 / 0.99 | 0.50 / 1.00 | 0.14 / 0.93 | 0.46 / 0.99 | 0.88 / 1.00 | 0.86 / 1.00 | 0.88 / 1.00 |
| recommendationservice | 0.80 / 0.98 | 0.72 / 0.90 | 0.82 / 1.00 | 0.80 / 0.98 | 0.85 / 1.00 | 0.74 / 0.90 | 0.62 / 0.75 | 0.61 / 0.73 | 0.68 / 0.81 |
| paymentservice | 0.17 / 0.39 | 0.27 / 0.44 | 0.19 / 0.52 | 0.18 / 0.48 | 0.07 / 0.43 | 0.31 / 0.83 | 0.45 / 0.57 | 0.28 / 0.45 | 0.46 / 0.79 |
| emailservice | 0.42 / 0.91 | 0.63 / 0.96 | 0.45 / 0.72 | 0.42 / 0.80 | 0.19 / 0.97 | 0.68 / 1.00 | 0.10 / 0.83 | 0.09 / 0.78 | 0.10 / 0.88 |
| productcatalogservice | 0.45 / 0.60 | 0.46 / 0.56 | 0.46 / 0.59 | 0.45 / 0.59 | 0.39 / 0.60 | 0.47 / 0.61 | 0.58 / 0.66 | 0.58 / 0.66 | 0.58 / 0.66 |
| cartservice | 0.42 / 0.51 | 0.41 / 0.50 | 0.36 / 0.53 | 0.42 / 0.55 | 0.42 / 0.51 | 0.42 / 0.50 | 0.39 / 0.47 | 0.37 / 0.45 | 0.39 / 0.56 |
| currencyservice | 0.41 / 0.52 | 0.43 / 0.51 | 0.41 / 0.50 | 0.40 / 0.50 | 0.36 / 0.52 | 0.42 / 0.52 | 0.48 / 0.57 | 0.47 / 0.55 | 0.47 / 0.55 |
| shippingservice | 0.07 / 0.14 | 0.10 / 0.16 | 0.07 / 0.14 | 0.07 / 0.14 | 0.03 / 0.16 | 0.11 / 0.22 | 0.12 / 0.14 | 0.11 / 0.14 | 0.12 / 0.14 |
| adservice | 0.07 / 0.14 | 0.09 / 0.12 | 0.07 / 0.12 | 0.07 / 0.14 | 0.04 / 0.14 | 0.08 / 0.13 | 0.14 / 0.16 | 0.13 / 0.16 | 0.13 / 0.16 |
| redis-cart | 0.08 / 0.09 | 0.07 / 0.09 | 0.06 / 0.07 | 0.08 / 0.09 | 0.08 / 0.09 | 0.07 / 0.09 | 0.07 / 0.08 | 0.06 / 0.08 | 0.07 / 0.08 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

### Block A

| Service | run108 | run109 | run110 | run111 | run112 | run113 | run114 | run115 | run117 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.345 | 0.318 | 0.358 | 0.351 | 0.341 | 0.338 | 0.337 | 0.314 | 0.341 |
| checkoutservice | 1.030 | 1.048 | 1.045 | 1.035 | 0.760 | 0.935 | 1.024 | 1.009 | 1.038 |
| recommendationservice | 1.016 | 0.970 | 1.025 | 1.007 | 1.003 | 1.010 | 0.987 | 0.928 | 0.979 |
| paymentservice | 0.890 | 0.865 | 0.806 | 0.677 | 0.548 | 0.497 | 0.613 | 0.852 | 0.703 |
| emailservice | 1.008 | 0.975 | 1.067 | 0.983 | 1.025 | 1.008 | 1.033 | 1.050 | 1.000 |
| productcatalogservice | 0.655 | 0.685 | 0.700 | 0.675 | 0.604 | 0.605 | 0.618 | 0.609 | 0.665 |
| cartservice | 0.635 | 0.519 | 0.565 | 0.637 | 0.547 | 0.635 | 0.606 | 0.542 | 0.544 |
| currencyservice | 0.579 | 0.591 | 0.632 | 0.604 | 0.548 | 0.575 | 0.582 | 0.542 | 0.573 |
| shippingservice | 0.191 | 0.179 | 0.187 | 0.192 | 0.181 | 0.162 | 0.165 | 0.240 | 0.155 |
| adservice | 0.525 | 0.179 | 0.190 | 0.167 | 0.135 | 0.140 | 0.187 | 0.219 | 0.180 |
| redis-cart | 0.137 | 0.083 | 0.094 | 0.107 | 0.106 | 0.104 | 0.104 | 0.104 | 0.111 |

### Block B

| Service | run118 | run119 | run120 | run121 | run122 | run123 | run124 | run125 | run126 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.343 | 0.322 | 0.310 | 0.335 | 0.342 | 0.328 | 0.373 | 0.367 | 0.365 |
| checkoutservice | 1.006 | 0.769 | 1.024 | 1.022 | 0.975 | 1.005 | 1.067 | 1.052 | 1.055 |
| recommendationservice | 0.996 | 0.944 | 1.010 | 1.004 | 1.016 | 0.935 | 0.774 | 0.796 | 0.861 |
| paymentservice | 0.490 | 0.568 | 0.723 | 0.716 | 0.484 | 0.910 | 0.813 | 0.671 | 0.852 |
| emailservice | 0.975 | 1.025 | 0.908 | 0.992 | 1.042 | 1.042 | 0.983 | 0.967 | 1.008 |
| productcatalogservice | 0.640 | 0.588 | 0.634 | 0.631 | 0.631 | 0.634 | 0.716 | 0.726 | 0.698 |
| cartservice | 0.570 | 0.549 | 0.589 | 0.594 | 0.599 | 0.556 | 0.516 | 0.496 | 0.605 |
| currencyservice | 0.562 | 0.595 | 0.560 | 0.566 | 0.612 | 0.551 | 0.619 | 0.604 | 0.623 |
| shippingservice | 0.160 | 0.178 | 0.161 | 0.173 | 0.186 | 0.232 | 0.194 | 0.174 | 0.182 |
| adservice | 0.148 | 0.137 | 0.160 | 0.153 | 0.169 | 0.173 | 0.183 | 0.771 | 0.176 |
| redis-cart | 0.115 | 0.109 | 0.100 | 0.115 | 0.119 | 0.113 | 0.109 | 0.115 | 0.102 |

## Per lever

The pairs below are inbound streak / overloaded ticks. A blend is recommendations and checkout both at streak ≥ 10 and overloaded ticks ≥ 10, plus email or payment overloaded ticks ≥ 10. A near-miss is two of those three, with the missing row at a streak or overloaded-tick count of at least 5. Otherwise the hold is a miss. Across all eighteen holds, the only controlled services with a streak ≥ 30 are checkout and recommendations. Payment, email, catalog, cart, currency, shipping, and ad stay under that bar.

**control.** run111 is a blend: recommendations 69 / 387, checkout 181 / 252, email 21. Frontend → recommendations retries 141,345. run121 is a blend: recommendations 156 / 560, checkout 11 / 48, email 12. Frontend → recommendations retries 226,799. Both clear a recommendations streak of 30. Checkout clears 30 only on run111.

**restart.** run108 is a blend: recommendations 558 / 558, checkout 12 / 36, email 11. Frontend → recommendations retries 292,131. run124 is a miss: recommendations 1 / 0, checkout 571 / 590, email 10. Frontend → checkout retries 64,036 and recommendations retries 0. The two holds land on opposite retry targets.

**spawn10.** run109 is a blend: recommendations 11 / 321, checkout 283 / 379, email 24. Frontend → recommendations retries 105,651 and frontend → checkout retries 27,798. run120 is a blend: recommendations 45 / 593, checkout 14 / 69, email 15. Frontend → recommendations retries 213,137. Checkout clears a streak of 30 on run109 and does not on run120.

**recs_users310.** run114 is a near-miss: recommendations 185 / 561, checkout 9 / 40, email 12. run118 is a near-miss: recommendations 124 / 564, checkout 0 / 31, email 16. Checkout streak stays under 10 on both, and frontend → recommendations retries are 226,938 and 241,497.

**recs_cpu1000.** run110 is a blend: recommendations 45 / 506, checkout 496 / 548, email 13. Frontend → recommendations retries 22,814 and frontend → checkout retries 56,837. run126 is a near-miss: recommendations 0 / 98, checkout 568 / 591, email 14. Frontend → checkout retries 64,124 and recommendations retries 0.

**ck_rep2.** run112 is a miss: recommendations 145 / 558, checkout 0 / 0, email 34. run119 is a miss: recommendations 21 / 449, checkout 0 / 0, email 125. Checkout overloaded ticks are 0 on both, and frontend → checkout retries are 7 and 2. Frontend → recommendations retries are 224,832 and 170,432. Hold-mean checkout sojourn is 66 ms and 69 ms.

**ck_cpu1000.** run113 is a near-miss: recommendations 143 / 557, checkout 0 / 25, email 28. run122 is a near-miss: recommendations 563 / 563, checkout 0 / 23, email 21. Checkout streak is 0 on both. Frontend → recommendations retries are 239,467 and 279,481. Hold-mean checkout sojourn is 85 ms and 97 ms.

**ck_rep2_pc120.** run115 is a blend: recommendations 116 / 547, checkout 11 / 12, email 142. run123 is a blend: recommendations 20 / 530, checkout 20 / 19, email 204, payment 12. Checkout streak stays under 30 on both (11 and 20). Frontend → recommendations retries are 217,861 and 194,503.

**pc120.** run117 is a blend: recommendations 136 / 561, checkout 19 / 92, email 36. run125 is a miss: recommendations 0 / 0, checkout 553 / 589, email 13. Frontend → recommendations retries are 230,747 on run117 and 0 on run125. Frontend → checkout retries on run125 are 87,211.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Probe classes and the lever verdicts: [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md).
- The layout this file copies: [2026-10-03-s2-paper-c1-runs-99-107.md](2026-10-03-s2-paper-c1-runs-99-107.md).
- Blend bar: [2026-09-30-s2-candidate-ranking-runs-1-79.md](2026-09-30-s2-candidate-ranking-runs-1-79.md).
