# S2 latch-probe v2 runs 132–153, all services

600 s holds, both controllers off, `spawn_rate` 50 except the `spawn10` and `*_spawn10` holds. Paper-C1, frontend pinned at 4, sidecar request 100 m with no CPU limit. Seed 20261004, started at run132 because runs 128–131 were already taken. Checkout and recommendations were rolled before every hold. The base mix is 275 / 90 / 100 / 90 / 5. Arms whose name contains `pc120` use postcheckout 120. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Classes and the arm verdicts: [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md).

Run136 and run138 failed the sampling gate and are omitted. Run152 and run153 are the replacements (block R). Twenty holds are in the tables.

Every number below is from `experiments/s2_probe_tables.py` on the folders in `experiments/results/new vms/`. (a), (b), and (c) keep the inbound tail. The other inbound tables drop the last 5 polls. Locust tables drop the first 30 rows and the last 5. The results guide drops the last 5 inbound polls for streaks, so a streak there can be a few samples shorter. Run139 checkout streak is 566 in the (a) table here and 562 in the results guide.

Block R in the tables is the two replacement holds.

## Hold index

### Block A

| Slot | Treatment | Change from the base | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
| --- | --- | --- | --- |
| run132 | control | none | 275 / 90 / 100 / 90 / 5 |
| run133 | spawn10 | `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run134 | control | none | 275 / 90 / 100 / 90 / 5 |
| run135 | ck_cpu1000_pc120 | checkout 1000 m × 1, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run136 | recs_cpu1000_spawn10 | recommendations 1000 m × 1, `spawn_rate` 10. Failed the sampling gate. Omitted below. | 275 / 90 / 100 / 90 / 5 |
| run137 | ck_rep2_pc120 | checkout 800 m × 2, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run138 | recs_cpu1000 | recommendations 1000 m × 1. Failed the sampling gate. Omitted below. | 275 / 90 / 100 / 90 / 5 |
| run139 | control | none | 275 / 90 / 100 / 90 / 5 |
| run140 | ck_rep2_pc120_spawn10 | checkout 800 m × 2, postcheckout 120, `spawn_rate` 10 | 275 / 120 / 100 / 90 / 5 |
| run141 | ck_cpu1000_pc120_spawn10 | checkout 1000 m × 1, postcheckout 120, `spawn_rate` 10 | 275 / 120 / 100 / 90 / 5 |

### Block B

| Slot | Treatment | Change from the base | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
| --- | --- | --- | --- |
| run142 | spawn10 | `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run143 | control | none | 275 / 90 / 100 / 90 / 5 |
| run144 | recs_cpu1000_spawn10 | recommendations 1000 m × 1, `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run145 | ck_rep2_pc120_spawn10 | checkout 800 m × 2, postcheckout 120, `spawn_rate` 10 | 275 / 120 / 100 / 90 / 5 |
| run146 | ck_cpu1000_pc120 | checkout 1000 m × 1, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run147 | control | none | 275 / 90 / 100 / 90 / 5 |
| run148 | recs_cpu1000 | recommendations 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |
| run149 | ck_cpu1000_pc120_spawn10 | checkout 1000 m × 1, postcheckout 120, `spawn_rate` 10 | 275 / 120 / 100 / 90 / 5 |
| run150 | ck_rep2_pc120 | checkout 800 m × 2, postcheckout 120 | 275 / 120 / 100 / 90 / 5 |
| run151 | control | none | 275 / 90 / 100 / 90 / 5 |

### Replacements

| Slot | Treatment | Change from the base | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
| --- | --- | --- | --- |
| run152 | recs_cpu1000_spawn10 | replacement for run136. Recommendations 1000 m × 1, `spawn_rate` 10 | 275 / 90 / 100 / 90 / 5 |
| run153 | recs_cpu1000 | replacement for run138. Recommendations 1000 m × 1 | 275 / 90 / 100 / 90 / 5 |

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 115 / 481 | 189 / 555 | 146 / 376 | 109 / 397 | 70 / 492 | 1 / 1 | 27 / 388 | 3 / 6 |
| checkoutservice | 10 / 10 | 8 / 8 | **158 / 159** | **116 / 166** | 14 / 16 | **566 / 566** | 16 / 20 | **303 / 601** |
| recommendationservice | **50 / 211** | **38 / 251** | 23 / 223 | 6 / 199 | 15 / 350 | 0 / 0 | 3 / 74 | 1 / 1 |
| paymentservice | 0 / 0 | 0 / 0 | 1 / 1 | 6 / 18 | 0 / 0 | 1 / 5 | 0 / 0 | 4 / 38 |
| emailservice | 1 / 4 | 4 / 8 | 4 / 44 | 5 / 46 | 15 / 17 | 4 / 165 | 16 / 21 | 7 / 205 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 1 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 1 / 1 | 1 / 2 | 2 / 2 | 100 / 559 | 261 / 378 | 2 / 2 | 2 / 2 | 2 / 2 | 299 / 549 | 108 / 493 |
| checkoutservice | **603 / 604** | **371 / 445** | **604 / 604** | 9 / 11 | **113 / 188** | **562 / 562** | **565 / 565** | **604 / 605** | 15 / 15 | **53 / 54** |
| recommendationservice | 1 / 1 | 0 / 0 | 1 / 1 | 9 / 303 | 19 / 239 | 0 / 0 | 0 / 0 | 1 / 1 | 24 / 462 | 4 / 154 |
| paymentservice | 1 / 6 | 1 / 1 | 1 / 4 | 0 / 0 | 3 / 24 | 1 / 4 | 1 / 6 | 2 / 31 | 0 / 0 | 0 / 0 |
| emailservice | 5 / 206 | 5 / 124 | 7 / 225 | 15 / 15 | 5 / 55 | 5 / 148 | 6 / 177 | 8 / 177 | 16 / 16 | 5 / 17 |
| productcatalogservice | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 2 / 2 | 425 / 425 |
| checkoutservice | **302 / 604** | **121 / 121** |
| recommendationservice | 1 / 1 | 17 / 276 |
| paymentservice | 1 / 6 | 1 / 1 |
| emailservice | 10 / 302 | 4 / 43 |
| productcatalogservice | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 |

## (b) Detector overloaded ticks / ticks (share)

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| checkoutservice | **329/640 (51%)** | 164/639 (26%) | 271/639 (42%) | 262/639 (41%) | 19/639 (3%) | **589/638 (92%)** | 24/642 (4%) | **599/639 (94%)** |
| recommendationservice | **508/640 (79%)** | **584/639 (91%)** | **379/639 (59%)** | **388/639 (61%)** | **541/639 (85%)** | 0/638 (0%) | 301/642 (47%) | 0/639 (0%) |
| paymentservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 9/639 (1%) | 1/638 (0%) | 2/642 (0%) | 0/639 (0%) |
| emailservice | 109/640 (17%) | 37/639 (6%) | 51/639 (8%) | 156/639 (24%) | **350/639 (55%)** | 12/638 (2%) | **411/642 (64%)** | 4/639 (1%) |
| productcatalogservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| cartservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| currencyservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| shippingservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| adservice | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |
| redis-cart (not controlled) | 0/640 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/639 (0%) | 0/638 (0%) | 0/642 (0%) | 0/639 (0%) |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| checkoutservice | **606/640 (95%)** | **410/451 (91%)** | **606/639 (95%)** | 10/642 (2%) | 254/638 (40%) | **591/638 (93%)** | **590/638 (92%)** | **604/638 (95%)** | 17/639 (3%) | 154/639 (24%) |
| recommendationservice | 0/640 (0%) | 0/451 (0%) | 19/639 (3%) | **398/642 (62%)** | **364/638 (57%)** | 0/638 (0%) | 156/638 (24%) | 2/638 (0%) | **551/639 (86%)** | **515/639 (81%)** |
| paymentservice | 1/640 (0%) | 0/451 (0%) | 0/639 (0%) | 1/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 13/639 (2%) | 0/639 (0%) |
| emailservice | 1/640 (0%) | 11/451 (2%) | 1/639 (0%) | **345/642 (54%)** | 142/638 (22%) | 19/638 (3%) | 16/638 (3%) | 4/638 (1%) | 223/639 (35%) | 34/639 (5%) |
| productcatalogservice | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| cartservice | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| currencyservice | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| shippingservice | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| adservice | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |
| redis-cart (not controlled) | 0/640 (0%) | 0/451 (0%) | 0/639 (0%) | 0/642 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/638 (0%) | 0/639 (0%) | 0/639 (0%) |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0/638 (0%) | 0/638 (0%) |
| checkoutservice | **600/638 (94%)** | 148/638 (23%) |
| recommendationservice | 266/638 (42%) | **449/638 (70%)** |
| paymentservice | 0/638 (0%) | 0/638 (0%) |
| emailservice | 0/638 (0%) | 15/638 (2%) |
| productcatalogservice | 0/638 (0%) | 0/638 (0%) |
| cartservice | 0/638 (0%) | 0/638 (0%) |
| currencyservice | 0/638 (0%) | 0/638 (0%) |
| shippingservice | 0/638 (0%) | 0/638 (0%) |
| adservice | 0/638 (0%) | 0/638 (0%) |
| redis-cart (not controlled) | 0/638 (0%) | 0/638 (0%) |

## (c) Outbound retry delta by target

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 923 | 727 | 16945 | 23255 | 1758 | 61199 | 1997 | 76718 |
| recommendationservice | 168467 | 202058 | 146773 | 144697 | 188153 | 2 | 139838 | 2920 |
| paymentservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 | 0 | 0 | 55 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| redis-cart (not controlled) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 61448 | 56683 | 61071 | 1122 | 26227 | 61690 | 62515 | 76898 | 1962 | 5285 |
| recommendationservice | 1082 | 0 | 6 | 215043 | 132183 | 0 | 0 | 188 | 213469 | 190893 |
| paymentservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| redis-cart (not controlled) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0 | 0 |
| checkoutservice | 56426 | 12373 |
| recommendationservice | 1353 | 200126 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 0 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart (not controlled) | 0 | 0 |

## CPU mean / max (m, summed over replicas)

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 1197 / 1492 | 1173 / 1425 | 1210 / 1538 | 1210 / 1568 | 1147 / 1400 | 1332 / 1547 | 1167 / 1356 | 1056 / 1245 |
| checkoutservice | 554 / 796 | 495 / 714 | 548 / 801 | 677 / 1001 | 810 / 1590 | 697 / 801 | 880 / 1549 | 871 / 1003 |
| recommendationservice | 850 / 1068 | 915 / 1111 | 815 / 1098 | 797 / 1025 | 840 / 1017 | 672 / 803 | 823 / 1002 | 647 / 796 |
| paymentservice | 39 / 83 | 34 / 50 | 44 / 82 | 52 / 100 | 53 / 128 | 67 / 86 | 55 / 112 | 65 / 94 |
| emailservice | 71 / 111 | 64 / 91 | 49 / 111 | 62 / 115 | 85 / 120 | 13 / 109 | 90 / 120 | 12 / 79 |
| productcatalogservice | 379 / 472 | 374 / 449 | 388 / 499 | 381 / 492 | 375 / 453 | 426 / 493 | 373 / 439 | 412 / 481 |
| cartservice | 332 / 400 | 305 / 463 | 322 / 402 | 334 / 470 | 321 / 390 | 308 / 372 | 287 / 363 | 163 / 257 |
| currencyservice | 335 / 417 | 335 / 402 | 335 / 427 | 338 / 432 | 329 / 416 | 362 / 431 | 342 / 400 | 279 / 340 |
| shippingservice | 77 / 113 | 66 / 96 | 74 / 112 | 85 / 124 | 90 / 170 | 94 / 113 | 100 / 169 | 89 / 117 |
| adservice | 102 / 154 | 94 / 129 | 106 / 167 | 107 / 164 | 97 / 145 | 143 / 169 | 101 / 127 | 123 / 141 |
| redis-cart (not controlled) | 40 / 51 | 34 / 41 | 40 / 50 | 39 / 49 | 40 / 48 | 36 / 43 | 34 / 41 | 18 / 23 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 1201 / 1381 | 1334 / 1542 | 1074 / 1240 | 1136 / 1319 | 1213 / 1744 | 1350 / 1548 | 1346 / 1578 | 1084 / 1244 | 1127 / 1391 | 1176 / 1547 |
| checkoutservice | 709 / 797 | 701 / 798 | 710 / 800 | 808 / 1235 | 663 / 1003 | 707 / 799 | 701 / 800 | 896 / 1003 | 744 / 1588 | 507 / 797 |
| recommendationservice | 678 / 818 | 664 / 776 | 647 / 749 | 834 / 976 | 785 / 1029 | 697 / 814 | 685 / 840 | 693 / 823 | 863 / 1031 | 869 / 1120 |
| paymentservice | 69 / 82 | 67 / 82 | 66 / 79 | 51 / 91 | 48 / 100 | 68 / 84 | 68 / 85 | 70 / 98 | 48 / 130 | 37 / 82 |
| emailservice | 11 / 68 | 13 / 95 | 12 / 49 | 87 / 113 | 57 / 105 | 13 / 105 | 13 / 101 | 11 / 54 | 79 / 120 | 59 / 95 |
| productcatalogservice | 430 / 494 | 449 / 516 | 428 / 490 | 357 / 411 | 384 / 570 | 455 / 520 | 454 / 522 | 436 / 505 | 367 / 467 | 378 / 494 |
| cartservice | 209 / 341 | 308 / 375 | 156 / 223 | 286 / 347 | 314 / 394 | 298 / 364 | 299 / 359 | 164 / 264 | 324 / 391 | 324 / 394 |
| currencyservice | 317 / 379 | 362 / 426 | 282 / 332 | 333 / 393 | 337 / 431 | 365 / 427 | 364 / 437 | 299 / 355 | 322 / 419 | 326 / 430 |
| shippingservice | 97 / 114 | 97 / 114 | 90 / 106 | 90 / 130 | 80 / 119 | 96 / 114 | 94 / 111 | 97 / 124 | 82 / 170 | 70 / 114 |
| adservice | 135 / 157 | 141 / 167 | 117 / 136 | 96 / 113 | 109 / 169 | 144 / 201 | 143 / 170 | 121 / 145 | 91 / 147 | 99 / 170 |
| redis-cart (not controlled) | 24 / 30 | 36 / 44 | 18 / 23 | 35 / 42 | 38 / 50 | 36 / 43 | 35 / 43 | 18 / 24 | 41 / 50 | 41 / 51 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 1146 / 1315 | 1053 / 1516 |
| checkoutservice | 714 / 799 | 342 / 797 |
| recommendationservice | 717 / 859 | 811 / 1003 |
| paymentservice | 68 / 80 | 28 / 84 |
| emailservice | 14 / 49 | 30 / 106 |
| productcatalogservice | 450 / 524 | 334 / 479 |
| cartservice | 176 / 245 | 316 / 427 |
| currencyservice | 303 / 352 | 301 / 420 |
| shippingservice | 97 / 114 | 46 / 112 |
| adservice | 133 / 155 | 76 / 172 |
| redis-cart (not controlled) | 19 / 24 | 38 / 49 |

## Inbound arrival rate (req/s)

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 408.7 | 406.8 | 404.2 | 422.5 | 416.3 | 439.9 | 419.8 | 409.6 |
| checkoutservice | 39.9 | 34.2 | 59.7 | 82.2 | 55.2 | 129.8 | 58.8 | 161.3 |
| recommendationservice | 571.4 | 617.6 | 534.7 | 551.0 | 607.2 | 359.1 | 545.7 | 356.2 |
| paymentservice | 39.8 | 34.1 | 54.7 | 66.3 | 55.2 | 110.5 | 58.8 | 117.4 |
| emailservice | 38.2 | 33.0 | 24.6 | 34.3 | 54.1 | 3.9 | 57.7 | 3.2 |
| productcatalogservice | 1704.5 | 1555.4 | 1756.7 | 1906.1 | 1773.8 | 2462.9 | 1892.4 | 2398.4 |
| cartservice | 425.0 | 412.4 | 437.3 | 470.4 | 446.4 | 542.4 | 456.8 | 536.7 |
| currencyservice | 585.1 | 563.9 | 601.4 | 635.0 | 598.5 | 767.8 | 620.7 | 748.9 |
| shippingservice | 126.6 | 108.8 | 150.7 | 181.8 | 158.0 | 268.1 | 174.2 | 276.6 |
| adservice | 128.9 | 110.9 | 140.8 | 150.5 | 128.5 | 232.7 | 136.3 | 233.1 |
| redis-cart (not controlled) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 451.5 | 413.0 | 429.4 | 400.5 | 424.2 | 442.1 | 440.9 | 424.2 | 398.0 | 390.7 |
| checkoutservice | 129.1 | 122.3 | 130.7 | 53.4 | 84.1 | 132.1 | 132.4 | 160.6 | 48.3 | 40.6 |
| recommendationservice | 370.0 | 337.5 | 359.5 | 640.8 | 534.9 | 361.2 | 360.0 | 349.4 | 627.6 | 585.6 |
| paymentservice | 115.3 | 104.7 | 112.7 | 53.4 | 64.2 | 110.9 | 111.2 | 115.1 | 48.3 | 39.4 |
| emailservice | 2.5 | 6.2 | 3.1 | 52.7 | 30.5 | 4.1 | 3.9 | 2.3 | 47.7 | 29.9 |
| productcatalogservice | 2527.6 | 2313.0 | 2451.6 | 1745.0 | 1944.7 | 2476.2 | 2469.0 | 2378.0 | 1569.7 | 1592.8 |
| cartservice | 557.1 | 509.8 | 534.4 | 428.4 | 470.0 | 544.1 | 544.5 | 548.1 | 417.9 | 406.6 |
| currencyservice | 784.8 | 720.5 | 764.4 | 589.3 | 634.8 | 771.6 | 770.8 | 749.1 | 554.1 | 553.8 |
| shippingservice | 278.1 | 253.1 | 278.1 | 153.8 | 179.4 | 268.3 | 269.9 | 293.7 | 137.0 | 119.5 |
| adservice | 240.0 | 217.3 | 229.3 | 126.8 | 155.3 | 233.3 | 233.0 | 213.0 | 108.8 | 119.4 |
| redis-cart (not controlled) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 440.6 | 383.4 |
| checkoutservice | 120.3 | 38.9 |
| recommendationservice | 359.7 | 591.4 |
| paymentservice | 109.5 | 35.7 |
| emailservice | 4.1 | 13.4 |
| productcatalogservice | 2460.8 | 1285.8 |
| cartservice | 545.4 | 385.3 |
| currencyservice | 758.1 | 515.9 |
| shippingservice | 269.0 | 95.4 |
| adservice | 235.8 | 86.3 |
| redis-cart (not controlled) | 0.0 | 0.0 |

## Inbound 5xx fraction

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.277 | 0.346 | 0.262 | 0.244 | 0.261 | 0.088 | 0.229 | 0.122 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.089 | 0.086 | 0.098 | 0.265 | 0.242 | 0.089 | 0.089 | 0.115 | 0.316 | 0.299 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |  |  |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0.086 | 0.447 |
| checkoutservice | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |

## Inbound reset fraction

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| checkoutservice | 0.024 | 0.020 | 0.297 | 0.314 | 0.029 | 0.484 | 0.027 | 0.461 |
| recommendationservice | 0.188 | 0.195 | 0.162 | 0.158 | 0.207 | 0.000 | 0.156 | 0.009 |
| paymentservice | 0.001 | 0.001 | 0.029 | 0.033 | 0.000 | 0.061 | 0.000 | 0.065 |
| emailservice | 0.003 | 0.004 | 0.006 | 0.009 | 0.050 | 0.097 | 0.059 | 0.270 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.002 | 0.002 | 0.000 | 0.005 | 0.000 | 0.007 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.001 | 0.000 | 0.011 | 0.012 | 0.000 | 0.023 | 0.000 | 0.025 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| checkoutservice | 0.464 | 0.482 | 0.455 | 0.016 | 0.348 | 0.496 | 0.479 | 0.476 | 0.038 | 0.137 |
| recommendationservice | 0.003 | 0.000 | 0.000 | 0.204 | 0.157 | 0.000 | 0.000 | 0.001 | 0.226 | 0.173 |
| paymentservice | 0.044 | 0.052 | 0.047 | 0.000 | 0.038 | 0.057 | 0.062 | 0.068 | 0.000 | 0.011 |
| emailservice | 0.238 | 0.070 | 0.239 | 0.036 | 0.024 | 0.072 | 0.109 | 0.317 | 0.063 | 0.004 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.006 | 0.005 | 0.006 | 0.000 | 0.002 | 0.005 | 0.006 | 0.006 | 0.000 | 0.001 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.021 | 0.023 | 0.020 | 0.000 | 0.014 | 0.023 | 0.025 | 0.026 | 0.000 | 0.005 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |  |  |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0.000 | 0.000 |
| checkoutservice | 0.455 | 0.333 |
| recommendationservice | 0.004 | 0.177 |
| paymentservice | 0.038 | 0.029 |
| emailservice | 0.279 | 0.012 |
| productcatalogservice | 0.000 | 0.000 |
| cartservice | 0.007 | 0.002 |
| currencyservice | 0.000 | 0.000 |
| shippingservice | 0.019 | 0.013 |
| adservice | 0.000 | 0.000 |
| redis-cart (not controlled) |  |  |

## Inbound sojourn (ms)

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 744 | 817 | 657 | 675 | 775 | 305 | 706 | 575 |
| checkoutservice | 130 | 122 | 285 | 274 | 117 | 489 | 123 | 501 |
| recommendationservice | 468 | 485 | 386 | 395 | 462 | 91 | 469 | 224 |
| paymentservice | 3 | 3 | 5 | 6 | 3 | 7 | 3 | 11 |
| emailservice | 21 | 16 | 20 | 31 | 48 | 23 | 52 | 29 |
| productcatalogservice | 3 | 2 | 2 | 3 | 2 | 3 | 3 | 3 |
| cartservice | 3 | 3 | 3 | 3 | 3 | 4 | 4 | 10 |
| currencyservice | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 26 |
| shippingservice | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 |
| adservice | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 463 | 251 | 496 | 859 | 643 | 275 | 278 | 531 | 836 | 788 |
| checkoutservice | 503 | 475 | 503 | 106 | 298 | 487 | 490 | 503 | 113 | 173 |
| recommendationservice | 232 | 39 | 211 | 475 | 372 | 57 | 61 | 187 | 467 | 458 |
| paymentservice | 7 | 7 | 7 | 2 | 6 | 7 | 7 | 9 | 3 | 3 |
| emailservice | 17 | 26 | 12 | 43 | 35 | 29 | 25 | 35 | 39 | 16 |
| productcatalogservice | 3 | 2 | 4 | 3 | 3 | 2 | 2 | 4 | 2 | 2 |
| cartservice | 7 | 4 | 9 | 3 | 4 | 5 | 4 | 11 | 3 | 3 |
| currencyservice | 13 | 4 | 19 | 3 | 3 | 4 | 4 | 22 | 3 | 3 |
| shippingservice | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 1 | 1 |
| adservice | 2 | 1 | 2 | 1 | 1 | 1 | 1 | 2 | 1 | 1 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |  |  |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 485 | 787 |
| checkoutservice | 503 | 303 |
| recommendationservice | 213 | 434 |
| paymentservice | 8 | 6 |
| emailservice | 11 | 15 |
| productcatalogservice | 4 | 2 |
| cartservice | 12 | 3 |
| currencyservice | 18 | 3 |
| shippingservice | 2 | 1 |
| adservice | 2 | 1 |
| redis-cart (not controlled) |  |  |

## Share of inbound requests above 500 ms

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.74 | 0.77 | 0.54 | 0.55 | 0.74 | 0.09 | 0.77 | 0.44 |
| checkoutservice | 0.02 | 0.02 | 0.42 | 0.40 | 0.04 | 0.95 | 0.05 | 0.98 |
| recommendationservice | 0.59 | 0.69 | 0.53 | 0.49 | 0.58 | 0.00 | 0.52 | 0.01 |
| paymentservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| emailservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| productcatalogservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| cartservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| currencyservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| shippingservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| adservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.32 | 0.09 | 0.34 | 0.77 | 0.50 | 0.09 | 0.09 | 0.37 | 0.74 | 0.68 |
| checkoutservice | 0.99 | 0.92 | 0.99 | 0.03 | 0.45 | 0.95 | 0.96 | 0.99 | 0.05 | 0.15 |
| recommendationservice | 0.01 | 0.00 | 0.00 | 0.60 | 0.45 | 0.00 | 0.00 | 0.00 | 0.64 | 0.64 |
| paymentservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| emailservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| productcatalogservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| cartservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| currencyservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| shippingservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| adservice | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| redis-cart (not controlled) |  |  |  |  |  |  |  |  |  |  |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0.33 | 0.58 |
| checkoutservice | 0.98 | 0.50 |
| recommendationservice | 0.00 | 0.74 |
| paymentservice | 0.00 | 0.00 |
| emailservice | 0.00 | 0.00 |
| productcatalogservice | 0.00 | 0.00 |
| cartservice | 0.00 | 0.00 |
| currencyservice | 0.00 | 0.00 |
| shippingservice | 0.00 | 0.00 |
| adservice | 0.00 | 0.00 |
| redis-cart (not controlled) |  |  |

## CPU use as a fraction of per-pod quota x replicas (mean / max)

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.26 / 0.32 | 0.26 / 0.31 | 0.26 / 0.33 | 0.26 / 0.34 | 0.25 / 0.30 | 0.29 / 0.34 | 0.25 / 0.29 | 0.23 / 0.27 |
| checkoutservice | 0.69 / 0.99 | 0.62 / 0.89 | 0.68 / 1.00 | 0.68 / 1.00 | 0.51 / 0.99 | 0.87 / 1.00 | 0.55 / 0.97 | 0.87 / 1.00 |
| recommendationservice | 0.74 / 0.93 | 0.80 / 0.97 | 0.71 / 0.95 | 0.69 / 0.89 | 0.73 / 0.88 | 0.58 / 0.70 | 0.72 / 0.87 | 0.56 / 0.69 |
| paymentservice | 0.25 / 0.54 | 0.22 / 0.32 | 0.28 / 0.53 | 0.33 / 0.65 | 0.34 / 0.83 | 0.43 / 0.55 | 0.36 / 0.72 | 0.42 / 0.61 |
| emailservice | 0.59 / 0.93 | 0.53 / 0.76 | 0.41 / 0.93 | 0.52 / 0.96 | 0.71 / 1.00 | 0.11 / 0.91 | 0.75 / 1.00 | 0.10 / 0.66 |
| productcatalogservice | 0.47 / 0.59 | 0.47 / 0.56 | 0.48 / 0.62 | 0.48 / 0.61 | 0.47 / 0.57 | 0.53 / 0.62 | 0.47 / 0.55 | 0.51 / 0.60 |
| cartservice | 0.42 / 0.50 | 0.38 / 0.58 | 0.40 / 0.50 | 0.42 / 0.59 | 0.40 / 0.49 | 0.38 / 0.47 | 0.36 / 0.45 | 0.20 / 0.32 |
| currencyservice | 0.43 / 0.54 | 0.44 / 0.52 | 0.44 / 0.55 | 0.44 / 0.56 | 0.43 / 0.54 | 0.47 / 0.56 | 0.44 / 0.52 | 0.36 / 0.44 |
| shippingservice | 0.10 / 0.15 | 0.09 / 0.12 | 0.10 / 0.15 | 0.11 / 0.16 | 0.12 / 0.22 | 0.12 / 0.15 | 0.13 / 0.22 | 0.12 / 0.15 |
| adservice | 0.09 / 0.13 | 0.08 / 0.11 | 0.09 / 0.15 | 0.09 / 0.14 | 0.08 / 0.13 | 0.12 / 0.15 | 0.09 / 0.11 | 0.11 / 0.12 |
| redis-cart (not controlled) | 0.07 / 0.09 | 0.06 / 0.08 | 0.07 / 0.09 | 0.07 / 0.09 | 0.07 / 0.09 | 0.07 / 0.08 | 0.06 / 0.08 | 0.03 / 0.04 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.26 / 0.30 | 0.29 / 0.34 | 0.23 / 0.27 | 0.25 / 0.29 | 0.26 / 0.38 | 0.29 / 0.34 | 0.29 / 0.34 | 0.24 / 0.27 | 0.24 / 0.30 | 0.26 / 0.34 |
| checkoutservice | 0.89 / 1.00 | 0.88 / 1.00 | 0.89 / 1.00 | 0.50 / 0.77 | 0.66 / 1.00 | 0.88 / 1.00 | 0.88 / 1.00 | 0.90 / 1.00 | 0.46 / 0.99 | 0.63 / 1.00 |
| recommendationservice | 0.59 / 0.71 | 0.58 / 0.67 | 0.65 / 0.75 | 0.73 / 0.85 | 0.68 / 0.89 | 0.61 / 0.71 | 0.68 / 0.84 | 0.60 / 0.72 | 0.75 / 0.90 | 0.76 / 0.97 |
| paymentservice | 0.45 / 0.53 | 0.44 / 0.53 | 0.42 / 0.51 | 0.33 / 0.59 | 0.31 / 0.65 | 0.44 / 0.54 | 0.44 / 0.55 | 0.45 / 0.63 | 0.31 / 0.84 | 0.24 / 0.53 |
| emailservice | 0.09 / 0.57 | 0.11 / 0.79 | 0.10 / 0.41 | 0.72 / 0.94 | 0.47 / 0.88 | 0.11 / 0.88 | 0.11 / 0.84 | 0.09 / 0.45 | 0.66 / 1.00 | 0.49 / 0.79 |
| productcatalogservice | 0.54 / 0.62 | 0.56 / 0.65 | 0.53 / 0.61 | 0.45 / 0.51 | 0.48 / 0.71 | 0.57 / 0.65 | 0.57 / 0.65 | 0.55 / 0.63 | 0.46 / 0.58 | 0.47 / 0.62 |
| cartservice | 0.26 / 0.43 | 0.38 / 0.47 | 0.19 / 0.28 | 0.36 / 0.43 | 0.39 / 0.49 | 0.37 / 0.46 | 0.37 / 0.45 | 0.21 / 0.33 | 0.41 / 0.49 | 0.40 / 0.49 |
| currencyservice | 0.41 / 0.49 | 0.47 / 0.55 | 0.37 / 0.43 | 0.43 / 0.51 | 0.44 / 0.56 | 0.47 / 0.55 | 0.47 / 0.57 | 0.39 / 0.46 | 0.42 / 0.54 | 0.42 / 0.56 |
| shippingservice | 0.13 / 0.15 | 0.13 / 0.15 | 0.12 / 0.14 | 0.12 / 0.17 | 0.10 / 0.15 | 0.12 / 0.15 | 0.12 / 0.14 | 0.13 / 0.16 | 0.11 / 0.22 | 0.09 / 0.15 |
| adservice | 0.12 / 0.14 | 0.12 / 0.15 | 0.10 / 0.12 | 0.08 / 0.10 | 0.09 / 0.15 | 0.12 / 0.17 | 0.12 / 0.15 | 0.11 / 0.13 | 0.08 / 0.13 | 0.09 / 0.15 |
| redis-cart (not controlled) | 0.04 / 0.06 | 0.07 / 0.08 | 0.03 / 0.04 | 0.06 / 0.08 | 0.07 / 0.09 | 0.07 / 0.08 | 0.07 / 0.08 | 0.03 / 0.04 | 0.08 / 0.09 | 0.08 / 0.09 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0.25 / 0.29 | 0.23 / 0.33 |
| checkoutservice | 0.89 / 1.00 | 0.43 / 1.00 |
| recommendationservice | 0.72 / 0.86 | 0.81 / 1.00 |
| paymentservice | 0.44 / 0.52 | 0.18 / 0.54 |
| emailservice | 0.12 / 0.41 | 0.25 / 0.88 |
| productcatalogservice | 0.56 / 0.66 | 0.42 / 0.60 |
| cartservice | 0.22 / 0.31 | 0.40 / 0.53 |
| currencyservice | 0.39 / 0.46 | 0.39 / 0.55 |
| shippingservice | 0.13 / 0.15 | 0.06 / 0.15 |
| adservice | 0.12 / 0.13 | 0.07 / 0.15 |
| redis-cart (not controlled) | 0.03 / 0.04 | 0.07 / 0.09 |

## Detector max utilization

### Block A

| Service | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.33 | 0.32 | 0.35 | 0.36 | 0.33 | 0.35 | 0.31 | 0.30 |
| checkoutservice | 1.02 | 1.02 | 1.06 | 1.04 | 1.01 | 1.06 | 1.01 | 1.07 |
| recommendationservice | 0.95 | 1.00 | 0.98 | 0.94 | 0.94 | 0.73 | 0.92 | 0.80 |
| paymentservice | 0.66 | 0.56 | 0.75 | 0.75 | 0.88 | 0.83 | 0.84 | 0.74 |
| emailservice | 1.02 | 0.97 | 1.00 | 1.06 | 1.07 | 1.02 | 1.08 | 0.94 |
| productcatalogservice | 0.63 | 0.63 | 0.66 | 0.69 | 0.61 | 0.67 | 0.61 | 0.68 |
| cartservice | 0.55 | 0.63 | 0.57 | 0.61 | 0.55 | 0.51 | 0.52 | 0.41 |
| currencyservice | 0.58 | 0.56 | 0.60 | 0.62 | 0.60 | 0.62 | 0.56 | 0.57 |
| shippingservice | 0.16 | 0.17 | 0.18 | 0.20 | 0.24 | 0.19 | 0.24 | 0.18 |
| adservice | 0.21 | 0.13 | 0.17 | 0.17 | 0.15 | 0.17 | 0.15 | 0.16 |
| redis-cart (not controlled) | 0.13 | 0.11 | 0.12 | 0.13 | 0.13 | 0.12 | 0.12 | 0.09 |

### Block B

| Service | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 0.32 | 0.37 | 0.29 | 0.30 | 0.39 | 0.36 | 0.35 | 0.29 | 0.32 | 0.35 |
| checkoutservice | 1.06 | 1.05 | 1.06 | 0.97 | 1.06 | 1.05 | 1.05 | 1.06 | 1.00 | 1.06 |
| recommendationservice | 0.76 | 0.72 | 0.83 | 0.91 | 0.93 | 0.78 | 0.90 | 0.86 | 0.96 | 0.99 |
| paymentservice | 0.81 | 0.73 | 0.76 | 0.85 | 0.78 | 0.78 | 0.78 | 0.79 | 0.92 | 0.65 |
| emailservice | 0.87 | 0.90 | 0.97 | 1.04 | 1.04 | 1.02 | 1.02 | 1.01 | 1.06 | 0.96 |
| productcatalogservice | 0.67 | 0.67 | 0.68 | 0.56 | 0.74 | 0.69 | 0.69 | 0.70 | 0.63 | 0.65 |
| cartservice | 0.47 | 0.51 | 0.36 | 0.49 | 0.54 | 0.54 | 0.51 | 0.39 | 0.56 | 0.54 |
| currencyservice | 0.59 | 0.61 | 0.54 | 0.59 | 0.61 | 0.62 | 0.63 | 0.55 | 0.58 | 0.59 |
| shippingservice | 0.20 | 0.18 | 0.18 | 0.22 | 0.19 | 0.19 | 0.18 | 0.19 | 0.25 | 0.18 |
| adservice | 0.19 | 0.20 | 0.16 | 0.12 | 0.19 | 0.27 | 0.17 | 0.17 | 0.14 | 0.16 |
| redis-cart (not controlled) | 0.11 | 0.13 | 0.08 | 0.12 | 0.14 | 0.13 | 0.14 | 0.10 | 0.14 | 0.15 |

### Block R

| Service | run152 | run153 |
|---|---|---|
| frontend (not controlled) | 0.31 | 0.35 |
| checkoutservice | 1.04 | 1.04 |
| recommendationservice | 0.93 | 1.03 |
| paymentservice | 0.78 | 0.71 |
| emailservice | 0.75 | 0.97 |
| productcatalogservice | 0.72 | 0.64 |
| cartservice | 0.38 | 0.58 |
| currencyservice | 0.55 | 0.61 |
| shippingservice | 0.18 | 0.18 |
| adservice | 0.17 | 0.19 |
| redis-cart (not controlled) | 0.10 | 0.14 |

## Locust goodput (req/s)

### Block A

| API | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| getproduct | 103.0 | 82.0 | 134.7 | 144.5 | 98.7 | 273.5 | 110.8 | 266.4 |
| postcheckout | 30.7 | 24.9 | 18.2 | 25.5 | 40.5 | 1.7 | 46.6 | 0.2 |
| getcart | 41.1 | 33.1 | 51.1 | 54.5 | 40.0 | 99.4 | 48.7 | 77.1 |
| postcart | 89.5 | 87.6 | 89.5 | 88.5 | 88.6 | 89.5 | 81.0 | 60.6 |
| emptycart | 5.0 | 5.0 | 5.0 | 4.8 | 4.8 | 5.0 | 5.0 | 5.0 |

### Block B

| API | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| getproduct | 275.1 | 260.9 | 262.5 | 97.0 | 152.7 | 273.2 | 273.3 | 242.8 | 79.1 | 98.3 |
| postcheckout | 0.1 | 4.2 | 0.2 | 40.4 | 22.2 | 2.4 | 1.8 | 0.1 | 33.5 | 21.5 |
| getcart | 99.9 | 95.1 | 100.0 | 39.1 | 58.1 | 99.4 | 99.5 | 98.3 | 32.7 | 38.5 |
| postcart | 90.0 | 85.6 | 74.6 | 73.7 | 88.2 | 89.5 | 89.5 | 80.2 | 86.4 | 89.5 |
| emptycart | 5.0 | 4.8 | 5.0 | 4.9 | 4.9 | 5.0 | 5.0 | 5.0 | 4.8 | 5.0 |

### Block R

| API | run152 | run153 |
|---|---|---|
| getproduct | 269.3 | 82.6 |
| postcheckout | 0.3 | 8.6 |
| getcart | 94.7 | 31.0 |
| postcart | 89.9 | 89.5 |
| emptycart | 4.4 | 5.0 |

## Locust fail rate (Fail / RPS)

### Block A

| API | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| getproduct | 0.544 | 0.624 | 0.413 | 0.382 | 0.553 | 0.000 | 0.476 | 0.014 |
| postcheckout | 0.576 | 0.646 | 0.711 | 0.695 | 0.573 | 0.964 | 0.497 | 0.996 |
| getcart | 0.510 | 0.591 | 0.398 | 0.366 | 0.513 | 0.000 | 0.446 | 0.229 |
| postcart | 0.000 | 0.027 | 0.000 | 0.012 | 0.010 | 0.000 | 0.000 | 0.327 |
| emptycart | 0.000 | 0.000 | 0.000 | 0.028 | 0.037 | 0.000 | 0.000 | 0.000 |

### Block B

| API | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| getproduct | 0.000 | 0.000 | 0.023 | 0.548 | 0.353 | 0.000 | 0.000 | 0.000 | 0.626 | 0.546 |
| postcheckout | 0.998 | 0.912 | 0.997 | 0.562 | 0.734 | 0.951 | 0.963 | 0.999 | 0.633 | 0.668 |
| getcart | 0.001 | 0.000 | 0.000 | 0.509 | 0.333 | 0.000 | 0.000 | 0.003 | 0.586 | 0.518 |
| postcart | 0.000 | 0.000 | 0.172 | 0.181 | 0.015 | 0.000 | 0.000 | 0.010 | 0.034 | 0.000 |
| emptycart | 0.000 | 0.000 | 0.000 | 0.017 | 0.016 | 0.000 | 0.000 | 0.000 | 0.041 | 0.000 |

### Block R

| API | run152 | run153 |
|---|---|---|
| getproduct | 0.004 | 0.612 |
| postcheckout | 0.994 | 0.859 |
| getcart | 0.051 | 0.605 |
| postcart | 0.001 | 0.000 |
| emptycart | 0.117 | 0.000 |

## Locust P95 (ms)

### Block A

| API | run132 | run133 | run134 | run135 | run137 | run139 | run140 | run141 |
|---|---|---|---|---|---|---|---|---|
| getproduct | 2103 | 2164 | 1607 | 1628 | 2105 | 325 | 2107 | 760 |
| postcheckout | 2117 | 2153 | 2159 | 2201 | 2134 | 2329 | 2077 | 2582 |
| getcart | 1999 | 2080 | 1532 | 1574 | 2041 | 311 | 1963 | 673 |
| postcart | 70 | 130 | 71 | 71 | 73 | 75 | 138 | 129 |
| emptycart | 16 | 15 | 15 | 18 | 20 | 14 | 26 | 45 |

### Block B

| API | run142 | run143 | run144 | run145 | run146 | run147 | run148 | run149 | run150 | run151 |
|---|---|---|---|---|---|---|---|---|---|---|
| getproduct | 656 | 223 | 659 | 2197 | 1505 | 288 | 274 | 714 | 2116 | 1997 |
| postcheckout | 2590 | 2109 | 2506 | 2176 | 2164 | 2262 | 2273 | 2537 | 2142 | 2176 |
| getcart | 603 | 220 | 428 | 2142 | 1457 | 289 | 287 | 651 | 2060 | 1950 |
| postcart | 117 | 72 | 128 | 125 | 71 | 74 | 72 | 131 | 70 | 69 |
| emptycart | 27 | 23 | 35 | 14 | 23 | 20 | 31 | 55 | 18 | 17 |

### Block R

| API | run152 | run153 |
|---|---|---|
| getproduct | 714 | 1774 |
| postcheckout | 2564 | 2175 |
| getcart | 630 | 1735 |
| postcart | 152 | 64 |
| emptycart | 48 | 15 |

## CPU steal % over the hold (hold % / worst 5 s interval)

### Block A

| Run | master | worker | load |
|---|---|---|---|
| run132 | 0.08 / 0.15 | 0.13 / 0.53 | 0.27 / 1.18 |
| run133 | 0.10 / 0.28 | 0.18 / 0.88 | 0.62 / 2.77 |
| run134 | 0.16 / 1.94 | 0.11 / 0.36 | 0.27 / 1.92 |
| run135 | 0.13 / 0.43 | 0.09 / 0.25 | 0.43 / 1.78 |
| run137 | 0.15 / 0.36 | 0.08 / 0.17 | 1.95 / 8.02 |
| run139 | 0.24 / 2.72 | 0.07 / 0.15 | 0.21 / 1.07 |
| run140 | 0.13 / 0.25 | 0.06 / 0.13 | 0.89 / 3.67 |
| run141 | 0.09 / 0.18 | 0.07 / 0.12 | 0.56 / 3.59 |

### Block B

| Run | master | worker | load |
|---|---|---|---|
| run142 | 0.09 / 0.15 | 0.08 / 0.16 | 0.90 / 9.76 |
| run143 | 0.09 / 0.15 | 0.05 / 0.13 | 0.90 / 4.50 |
| run144 | 0.12 / 0.20 | 0.06 / 0.09 | 0.50 / 5.27 |
| run145 | 0.17 / 0.35 | 0.07 / 0.14 | 1.45 / 17.60 |
| run146 | 0.12 / 0.18 | 0.07 / 0.13 | 0.01 / 0.03 |
| run147 | 0.11 / 0.17 | 0.05 / 0.12 | 0.02 / 0.05 |
| run148 | 0.11 / 0.17 | 0.06 / 0.14 | 0.01 / 0.03 |
| run149 | 0.16 / 0.43 | 0.10 / 0.38 | 0.02 / 0.05 |
| run150 | 0.19 / 0.53 | 0.12 / 0.25 | 0.02 / 0.05 |
| run151 | 0.28 / 1.03 | 0.12 / 0.28 | 0.02 / 0.05 |

### Block R

| Run | master | worker | load |
|---|---|---|---|
| run152 | 0.30 / 1.79 | 0.11 / 0.42 | 0.01 / 0.03 |
| run153 | 1.03 / 13.67 | 0.11 / 0.23 | 0.01 / 0.03 |

## Per arm

Streak / overloaded ticks below are the (a) streak and the (b) overloaded-tick count from the tables above. A blend is recommendations and checkout both at streak ≥ 10 and overloaded ticks ≥ 10, plus email or payment overloaded ticks ≥ 10. A near-miss is two of those three, with the missing row at a streak or overloaded-tick count of at least 5. Otherwise the hold is a miss. Hold-mean checkout sojourn is the inbound sojourn table, not the 90–150 s window in the results guide.

**control.** run132 is a blend: recommendations 50 / 508, checkout 10 / 329, email 109. Retries to recommendationservice 168,467 and to checkoutservice 923. Hold-mean checkout sojourn is 130 ms. run134 is a blend: recommendations 23 / 379, checkout 158 / 271, email 51. Retries to recommendationservice 146,773 and to checkoutservice 16,945. Hold-mean checkout sojourn is 285 ms. run139 is a miss: recommendations 0 / 0, checkout 566 / 589, email 12. Retries to recommendationservice 2 and to checkoutservice 61,199. Hold-mean checkout sojourn is 489 ms. run143 is a miss: recommendations 0 / 0, checkout 371 / 410, email 11. Retries to recommendationservice 0 and to checkoutservice 56,683. Hold-mean checkout sojourn is 475 ms. run147 is a miss: recommendations 0 / 0, checkout 562 / 591, email 19. Retries to recommendationservice 0 and to checkoutservice 61,690. Hold-mean checkout sojourn is 487 ms. run151 is a near-miss: recommendations 4 / 515, checkout 53 / 154, email 34. Retries to recommendationservice 190,893 and to checkoutservice 5,285. Hold-mean checkout sojourn is 173 ms.

**spawn10.** Verdict in the results guide: mixed. run133 is a near-miss: recommendations 38 / 584, checkout 8 / 164, email 37. Retries to recommendationservice 202,058 and to checkoutservice 727. Hold-mean checkout sojourn is 122 ms. run142 is a miss: recommendations 1 / 0, checkout 603 / 606, email 1, payment 1. Retries to recommendationservice 1,082 and to checkoutservice 61,448. Hold-mean checkout sojourn is 503 ms.

**ck_cpu1000_pc120.** Verdict in the results guide: moved. run135 is a near-miss: recommendations 6 / 388, checkout 116 / 262, email 156. Retries to recommendationservice 144,697 and to checkoutservice 23,255. Hold-mean checkout sojourn is 274 ms. run146 is a blend: recommendations 19 / 364, checkout 113 / 254, email 142. Retries to recommendationservice 132,183 and to checkoutservice 26,227. Hold-mean checkout sojourn is 298 ms.

**ck_rep2_pc120.** Verdict in the results guide: moved, latch avoided. run137 is a blend: recommendations 15 / 541, checkout 14 / 19, email 350. Retries to recommendationservice 188,153 and to checkoutservice 1,758. Hold-mean checkout sojourn is 117 ms. run150 is a blend: recommendations 24 / 551, checkout 15 / 17, email 223, payment 13. Retries to recommendationservice 213,469 and to checkoutservice 1,962. Hold-mean checkout sojourn is 113 ms.

**recs_cpu1000.** Verdict in the results guide: mixed. run148 is a near-miss: recommendations 0 / 156, checkout 565 / 590, email 16. Retries to recommendationservice 0 and to checkoutservice 62,515. Hold-mean checkout sojourn is 490 ms. run153 is a blend: recommendations 17 / 449, checkout 121 / 148, email 15. Retries to recommendationservice 200,126 and to checkoutservice 12,373. Hold-mean checkout sojourn is 303 ms.

**recs_cpu1000_spawn10.** Verdict in the results guide: mixed. run144 is a miss: recommendations 1 / 19, checkout 604 / 606, email 1, payment 0. Retries to recommendationservice 6 and to checkoutservice 61,071. Hold-mean checkout sojourn is 503 ms. run152 is a miss: recommendations 1 / 266, checkout 302 / 600, email 0, payment 0. Retries to recommendationservice 1,353 and to checkoutservice 56,426. Hold-mean checkout sojourn is 503 ms.

**ck_rep2_pc120_spawn10.** Verdict in the results guide: moved, latch avoided. run140 is a near-miss: recommendations 3 / 301, checkout 16 / 24, email 411. Retries to recommendationservice 139,838 and to checkoutservice 1,997. Hold-mean checkout sojourn is 123 ms. run145 is a miss: recommendations 9 / 398, checkout 9 / 10, email 345. Retries to recommendationservice 215,043 and to checkoutservice 1,122. Hold-mean checkout sojourn is 106 ms.

**ck_cpu1000_pc120_spawn10.** Verdict in the results guide: mixed. run141 is a miss: recommendations 1 / 0, checkout 303 / 599, email 4, payment 0. Retries to recommendationservice 2,920 and to checkoutservice 76,718. Hold-mean checkout sojourn is 501 ms. run149 is a miss: recommendations 1 / 2, checkout 604 / 604, email 4, payment 0. Retries to recommendationservice 188 and to checkoutservice 76,898. Hold-mean checkout sojourn is 503 ms.

Across these tables, the only controlled services with a streak ≥ 30 are checkout and recommendations.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Classes and arm verdicts: [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md).
- First probe: [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md) and [2026-10-04-s2-latch-probe-abc.md](2026-10-04-s2-latch-probe-abc.md).
- Why the two modes exclude each other: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md).
