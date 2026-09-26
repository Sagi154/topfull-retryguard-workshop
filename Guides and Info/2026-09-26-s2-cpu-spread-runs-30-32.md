# S2 both-off runs 30–32, beside runs 6, 7, and 10

Counts under each pair are getproduct / postcheckout / getcart / postcart / emptycart. Both controllers off, 600 s, `spawn_rate` 50. Runs 6, 7, and 10 use the paper CPU table with frontend at 4 replicas. Runs 30, 31, and 32 replay those counts on the agreed table with frontend at 5 replicas (134/134 resource samples) and catalog at 1. Columns put each source next to its replay: run6 with run30 (mix 6), run7 with run31 (mix 7), run10 with run32 (mix 10). How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The two CPU tables: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).


|        | run6               | run30               | run7               | run31               | run10              | run32               |
| ------ | ------------------ | ------------------- | ------------------ | ------------------- | ------------------ | ------------------- |
| Mix    | 6                  | 6                   | 7                  | 7                   | 10                 | 10                  |
| Counts | 340/100/240/10/10  | same                | 380/100/270/20/20  | same                | 325/80/100/100/5   | same                |
| CPU    | paper, frontend ×4 | agreed, frontend ×5 | paper, frontend ×4 | agreed, frontend ×5 | paper, frontend ×4 | agreed, frontend ×5 |


**On the spread holds, no controlled service would disable, and the retry storm is on recommendationservice while that service’s detector share is 0.** Its longest streak above 0.20 is 7 samples on run30, run31, and run32. Median rejection there is 0.199 / 0.198 / 0.184, so the 298 / 292 / 201 samples above 0.20 never last 30 in a row. The paper-CPU holds do clear the disable bar: checkout on run6 (177) and run7 (230), recommendations on run6 (44) and run10 (56). Frontend, outside the nine controlled services, stays above 0.20 for a long streak on run6 (125), run10 (565), run30 (575), run31 (578), and run32 (70). Layer A admitting rows are 0 on all six holds.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. On runs 30–32 the inbound series is about 690 rows across ~690 s, median gap 1.0 s, so a streak of 30 is about 30 seconds. A streak of 30 is a disable for the nine controlled services. **Bold** marks a controlled service at streak ≥ 30. Frontend is reported and is not controlled, so its streak is left plain.


| Service                     | run6          | run30     | run7          | run31     | run10        | run32    |
| --------------------------- | ------------- | --------- | ------------- | --------- | ------------ | -------- |
| frontend (not controlled)   | 125 / 424     | 575 / 575 | 21 / 220      | 578 / 578 | 565 / 565    | 70 / 516 |
| checkoutservice             | **177 / 324** | 1 / 1     | **230 / 264** | 0         | 21 / 22      | 0        |
| recommendationservice       | **44 / 336**  | 7 / 298   | 15 / 235      | 7 / 292   | **56 / 485** | 7 / 201  |
| paymentservice              | 1 / 8         | 0         | 1 / 4         | 0         | 2 / 2        | 0        |
| emailservice                | 5 / 92        | 1 / 2     | 6 / 87        | 0         | 2 / 3        | 0        |
| productcatalogservice       | 0             | 0         | 1 / 1         | 0         | 1 / 1        | 1 / 1    |
| cartservice                 | 0             | 0         | 0             | 0         | 0            | 0        |
| currencyservice             | 0             | 0         | 0             | 1 / 1     | 0            | 0        |
| shippingservice             | 0             | 0         | 0             | 0         | 0            | 0        |
| adservice                   | 0             | 1 / 1     | 0             | 0         | 0            | 0        |
| redis-cart (not controlled) | 0             | 0         | 0             | 0         | 0            | 0        |


Whole-hold failure fraction, same column order. checkoutservice 46.7% / 0.3% / 37.8% / 0.1% / 6.8% / 0.0%. recommendationservice 21.0% / 19.8% / 18.5% / 19.9% / 25.3% / 18.6%. Frontend 28.0% / 38.5% / 18.3% / 34.8% / 41.7% / 25.0%. On runs 30–32 the recommendationservice failure is all resets (inbound 5xx is 0), and the positive-delta samples split as 298 / 251 / 64 above 0.20, between 0.15 and 0.20, and at or below 0.15 on run30; 292 / 260 / 61 on run31; 201 / 306 / 106 on run32. Frontend failure on those three holds is almost all 5xx (resets are 495 / 492 / 409). Source: `service_inbound.csv`, scored by `experiments/s2_both_off_abc.py`.

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. Tick counts are 637 / 638 / 636 / 637 / 636 / 638. **Bold** is at least half the hold. Layer A admitting rows are 0 on all six holds. On runs 30–32 the threshold is 10000 after 15 / 5 / 5 leading zeros at collector start.


| Service               | run6                | run30           | run7                | run31           | run10               | run32           |
| --------------------- | ------------------- | --------------- | ------------------- | --------------- | ------------------- | --------------- |
| frontend              | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| checkoutservice       | **476/637 (74.7%)** | 0/638 (0%)      | **572/636 (89.9%)** | 0/637 (0%)      | 53/636 (8.3%)       | 0/638 (0%)      |
| recommendationservice | **558/637 (87.6%)** | 0/638 (0%)      | **511/636 (80.3%)** | 0/637 (0%)      | **561/636 (88.2%)** | 0/638 (0%)      |
| paymentservice        | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| emailservice          | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 1/638 (0.2%)    |
| productcatalogservice | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| cartservice           | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| currencyservice       | 0/637 (0%)          | 143/638 (22.4%) | 0/636 (0%)          | 159/637 (25.0%) | 0/636 (0%)          | 101/638 (15.8%) |
| shippingservice       | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| adservice             | 0/637 (0%)          | 3/638 (0.5%)    | 1/636 (0.2%)        | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |
| redis-cart            | 0/637 (0%)          | 0/638 (0%)      | 0/636 (0%)          | 0/637 (0%)      | 0/636 (0%)          | 0/638 (0%)      |


On runs 30–32, currency utilization median is 0.77 / 0.77 / 0.77 against the 500 m quota (alpha 0.8). Catalog median is 0.64 / 0.64 / 0.66 of 600 m. Recommendations median is 0.50 / 0.50 / 0.47 of 2000 m. Checkout median is 0.39 / 0.38 / 0.45 of 1500 m. Source: `topfull_detect.csv`.

## (c) Outbound retry delta by target, whole hold

Sum of positive Envoy retry increments on every caller→target edge into that service. The caller on every non-zero edge is frontend. Hold totals are 189,693 / 234,221 / 151,025 / 225,503 / 266,743 / 171,677.


| Service               | run6    | run30   | run7    | run31   | run10   | run32   |
| --------------------- | ------- | ------- | ------- | ------- | ------- | ------- |
| frontend              | 0       | 0       | 0       | 0       | 0       | 0       |
| checkoutservice       | 21,930  | 97      | 17,544  | 26      | 1,458   | 0       |
| recommendationservice | 167,763 | 234,124 | 133,481 | 225,477 | 265,285 | 171,677 |
| paymentservice        | 0       | 0       | 0       | 0       | 0       | 0       |
| emailservice          | 0       | 0       | 0       | 0       | 0       | 0       |
| productcatalogservice | 0       | 0       | 0       | 0       | 0       | 0       |
| cartservice           | 0       | 0       | 0       | 0       | 0       | 0       |
| currencyservice       | 0       | 0       | 0       | 0       | 0       | 0       |
| shippingservice       | 0       | 0       | 0       | 0       | 0       | 0       |
| adservice             | 0       | 0       | 0       | 0       | 0       | 0       |
| redis-cart            | 0       | 0       | 0       | 0       | 0       | 0       |


Edges with delta at least 1:


| Edge                             | run6    | run30   | run7    | run31   | run10   | run32   |
| -------------------------------- | ------- | ------- | ------- | ------- | ------- | ------- |
| frontend → recommendationservice | 167,763 | 234,124 | 133,481 | 225,477 | 265,285 | 171,677 |
| frontend → checkoutservice       | 21,930  | 97      | 17,544  | 26      | 1,458   | 0       |


On runs 30–32, recommendationservice mean sojourn is 476 / 474 / 465 ms. Of its inbound `rq_time` samples, 66% / 63% / 56% sit above the 500 ms `perTryTimeout`, and essentially all of them are at or under 1000 ms. Frontend mean sojourn on those three holds is 984 / 936 / 731 ms. Locust mean goodput / Fail / P95 on `total.csv` (565 / 564 / 564 rows): run30 186.7 / 232.5 / 1248 ms, run31 210.0 / 231.3 / 1248 ms, run32 289.6 / 189.7 / 1216 ms. Source: `service_edges.csv` retry and `service_inbound.csv` `rq_time_*`.

## CPU mean / max

App-container millicores from `resource_usage.csv`. Frontend is the sum across replicas: 4 on runs 6, 7, and 10 (per-replica mean 315 / 334 / 275 m), and 5 on runs 30, 31, and 32 (per-replica mean 241 / 247 / 252 m). Every other service is one replica. Paper quotas are the run6 / run7 / run10 column. Agreed quotas are the run30 / run31 / run32 column.


| Service               | paper    | agreed   | run6        | run30       | run7        | run31       | run10       | run32       |
| --------------------- | -------- | -------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| frontend              | 1150 × 4 | 1150 × 5 | 1258 / 1660 | 1207 / 1544 | 1334 / 1687 | 1237 / 1561 | 1098 / 1563 | 1260 / 1516 |
| checkoutservice       | 615      | 1500     | 492 / 613   | 518 / 657   | 521 / 613   | 511 / 632   | 344 / 610   | 606 / 851   |
| recommendationservice | 1150     | 2000     | 911 / 1130  | 888 / 1066  | 863 / 1072  | 883 / 1024  | 936 / 1104  | 821 / 984   |
| paymentservice        | 155      | 150      | 46 / 75     | 36 / 72     | 47 / 70     | 32 / 42     | 27 / 79     | 38 / 53     |
| emailservice          | 155      | 150      | 35 / 72     | 62 / 92     | 45 / 85     | 61 / 80     | 46 / 80     | 71 / 97     |
| productcatalogservice | 1535     | 600      | 480 / 613   | 345 / 466   | 490 / 588   | 350 / 469   | 372 / 551   | 357 / 438   |
| cartservice           | 1920     | 1000     | 393 / 498   | 278 / 343   | 423 / 601   | 286 / 400   | 353 / 446   | 294 / 392   |
| currencyservice       | 770      | 500      | 373 / 510   | 347 / 414   | 396 / 503   | 349 / 401   | 323 / 436   | 339 / 402   |
| shippingservice       | 770      | 400      | 98 / 136    | 81 / 115    | 109 / 144   | 84 / 118    | 51 / 92     | 75 / 96     |
| adservice             | 1150     | 600      | 110 / 162   | 113 / 368   | 122 / 265   | 92 / 140    | 102 / 202   | 110 / 148   |
| redis-cart            | 540      | 500      | 27 / 32     | 30 / 34     | 29 / 34     | 31 / 36     | 32 / 38     | 34 / 39     |




## What the pairs show

**Mix 6, run6 beside run30 (340/100/240/10/10).** run6 clears both bars on checkout (streak 177, overloaded 74.7%) and on recommendations (streak 44, overloaded 87.6%), with retry edges of 167,763 and 21,930. run30 clears neither bar. Its recommendations retry edge is 234,124 and its checkout edge is 97.

**Mix 7, run7 beside run31 (380/100/270/20/20).** run7 clears both bars on checkout (streak 230, overloaded 89.9%). recommendationservice is detector-hot (80.3%) with streak 15, under the disable bar, and 133,481 retries. run31 clears neither bar. Its recommendations retry edge is 225,477 and its checkout edge is 26.

**Mix 10, run10 beside run32 (325/80/100/100/5).** run10 clears both bars on recommendationservice (streak 56, overloaded 88.2%) with 265,285 retries. Checkout stays under both bars (streak 21, overloaded 8.3%) with 1,458 retries. run32 clears neither bar. Its recommendations retry edge is 171,677 and its checkout edge is 0.

Across runs 30–32, run30 and run31 carry the larger retry delta and the longer frontend rejection streak. run32 is lower on streak, detector share, retry delta, and Locust Fail. None of those three puts a ≥30 streak, a half-hold detector flag, and a retry storm on the same controlled service. run6 does, on both checkout and recommendations. run10 does, on recommendations.

## Related

- Agreed CPU table and the five-mix order: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Source mixes 6 and 7 in the run3–run7 set: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
- Source mix 10 in the run9–run13 set: [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
- Plan for this series: [2026-09-26-s2-cpu-spread-holds.md](../docs/superpowers/plans/2026-09-26-s2-cpu-spread-holds.md).

