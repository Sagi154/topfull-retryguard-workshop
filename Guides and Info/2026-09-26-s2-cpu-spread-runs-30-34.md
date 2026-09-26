# S2 both-off runs 30–34, all services

600 s holds, both controllers off, `spawn_rate` 50. Frontend pinned at 5, catalog HPA max 1, sidecar request left at 100 m with no CPU limit, agreed CPU table. 360 s cool-off before run30 and between holds. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every number below is from `experiments/s2_both_off_abc.py` on these folders and on the five source folders.

| | run30 | run31 | run32 | run33 | run34 |
|---|---|---|---|---|---|
| Mix | 6 | 7 | 10 | 26 | 12 |
| Counts | 340/100/240/10/10 | 380/100/270/20/20 | 325/80/100/100/5 | 325/100/100/100/5 | 100/150/100/100/5 |
| Source folder | run6 | run7 | run10 | run26 | run12 |

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run30 | run31 | run32 | run33 | run34 |
|---|---|---|---|---|---|
| frontend (not controlled) | 575 / 575 | 578 / 578 | 70 / 516 | 95 / 526 | 122 / 446 |
| checkoutservice | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | **122 / 334** |
| recommendationservice | 7 / 298 | 7 / 292 | 7 / 201 | 8 / 225 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **30 / 215** |
| emailservice | 1 / 2 | 0 / 0 | 0 / 0 | 1 / 1 | 11 / 66 |
| productcatalogservice | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 1 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 1 / 1 | 0 / 0 | 1 / 1 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on run30–run34.

| Service | run30 | run31 | run32 | run33 | run34 |
|---|---|---|---|---|---|
| frontend | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| checkoutservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | **386/637 (60.6%)** |
| recommendationservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| paymentservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 256/637 (40.2%) |
| emailservice | 0/638 (0.0%) | 0/637 (0.0%) | 1/638 (0.2%) | 9/637 (1.4%) | 18/637 (2.8%) |
| productcatalogservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| cartservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| currencyservice | 143/638 (22.4%) | 159/637 (25.0%) | 101/638 (15.8%) | 69/637 (10.8%) | 0/637 (0.0%) |
| shippingservice | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| adservice | 3/638 (0.5%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 2/637 (0.3%) |
| redis-cart | 0/638 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |

## (c) Outbound retry delta by target, whole hold

Sum of positive Envoy retry increments on every caller→target edge into that service.

| Service | run30 | run31 | run32 | run33 | run34 |
|---|---:|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 97 | 26 | 0 | 128 | 60,933 |
| recommendationservice | 234,124 | 225,477 | 171,677 | 177,103 | 0 |
| paymentservice | 0 | 0 | 0 | 0 | 3,865 |
| emailservice | 0 | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 | 0 |

Edges whose delta is at least 1 on any of these five holds. A 0 is an edge the script omitted for that hold.

| Edge | run30 | run31 | run32 | run33 | run34 |
|---|---:|---:|---:|---:|---:|
| frontend → recommendationservice | 234,124 | 225,477 | 171,677 | 177,103 | 0 |
| frontend → checkoutservice | 97 | 26 | 0 | 128 | 60,933 |
| checkoutservice → paymentservice | 0 | 0 | 0 | 0 | 3,865 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`.

| Service | run30 | run31 | run32 | run33 | run34 |
|---|---|---|---|---|---|
| frontend | 1207 / 1544 | 1237 / 1561 | 1260 / 1516 | 1244 / 1474 | 983 / 1299 |
| checkoutservice | 518 / 657 | 511 / 632 | 606 / 851 | 665 / 856 | 1123 / 1506 |
| recommendationservice | 888 / 1066 | 883 / 1024 | 821 / 984 | 827 / 981 | 543 / 745 |
| paymentservice | 36 / 72 | 32 / 42 | 38 / 53 | 42 / 57 | 58 / 150 |
| emailservice | 62 / 92 | 61 / 80 | 71 / 97 | 80 / 117 | 17 / 150 |
| productcatalogservice | 345 / 466 | 350 / 469 | 357 / 438 | 352 / 445 | 352 / 467 |
| cartservice | 278 / 343 | 286 / 400 | 294 / 392 | 300 / 466 | 197 / 316 |
| currencyservice | 347 / 414 | 349 / 401 | 339 / 402 | 336 / 395 | 225 / 307 |
| shippingservice | 81 / 115 | 84 / 118 | 75 / 96 | 78 / 100 | 107 / 151 |
| adservice | 113 / 368 | 92 / 140 | 110 / 148 | 106 / 149 | 75 / 139 |
| redis-cart | 30 / 34 | 31 / 36 | 34 / 39 | 34 / 40 | 21 / 28 |

## Per run

**run30, mix 6 (340/100/240/10/10).** No controlled service clears a streak of 30. No service clears an overloaded share of 0.5. The largest retry edge is frontend → recommendationservice, 234,124. Layer A admitting rows are 0. Source run6, scored by the same script: checkoutservice clears streak 177 and recommendationservice clears streak 44; both clear the overloaded bar (476/637, 74.7%, and 558/637, 87.6%). The largest retry edge is frontend → recommendationservice, 167,763. Layer A admitting rows are 0.

**run31, mix 7 (380/100/270/20/20).** No controlled service clears a streak of 30. No service clears an overloaded share of 0.5. The largest retry edge is frontend → recommendationservice, 225,477. Layer A admitting rows are 0. Source run7: checkoutservice clears streak 230. checkoutservice and recommendationservice both clear the overloaded bar (572/636, 89.9%, and 511/636, 80.3%). recommendationservice streak is 15. The largest retry edge is frontend → recommendationservice, 133,481. Layer A admitting rows are 0.

**run32, mix 10 (325/80/100/100/5).** No controlled service clears a streak of 30. No service clears an overloaded share of 0.5. The largest retry edge is frontend → recommendationservice, 171,677. Layer A admitting rows are 0. Source run10: recommendationservice clears streak 56 and the overloaded bar (561/636, 88.2%). checkoutservice streak is 21 and its overloaded share is 53/636 (8.3%). The largest retry edge is frontend → recommendationservice, 265,285. Layer A admitting rows are 0.

**run33, mix 26 (325/100/100/100/5).** No controlled service clears a streak of 30. No service clears an overloaded share of 0.5. The largest retry edge is frontend → recommendationservice, 177,103. Layer A admitting rows are 0. Source run26: checkoutservice clears streak 592 and the overloaded bar (592/637, 92.9%). recommendationservice clears the overloaded bar (364/637, 57.1%) with streak 2. The largest retry edge is frontend → recommendationservice, 120,541. Layer A admitting rows are 0. [2026-09-26-s2-both-off-replay-runs-26-29.md](2026-09-26-s2-both-off-replay-runs-26-29.md) reports emailservice streak 8 on run26. `experiments/s2_both_off_abc.py` scores that streak 4 / 156.

**run34, mix 12 (100/150/100/100/5).** checkoutservice clears streak 122 and the overloaded bar (386/637, 60.6%). paymentservice clears streak 30. Its overloaded share is 256/637 (40.2%). The largest retry edge is frontend → checkoutservice, 60,933. Layer A admitting rows are 0. Source run12: checkoutservice clears streak 89. No service clears an overloaded share of 0.5 (checkoutservice is 266/637, 41.8%). The largest retry edge is frontend → checkoutservice, 47,538. Layer A admitting rows are 0.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Agreed CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- Source mixes 6 and 7: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
- Source mixes 10 and 12 (run10, run12): [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
- Source mix 26 (run26): [2026-09-26-s2-both-off-replay-runs-26-29.md](2026-09-26-s2-both-off-replay-runs-26-29.md).
- Runs 30–32 beside their sources: [2026-09-26-s2-cpu-spread-runs-30-32.md](2026-09-26-s2-cpu-spread-runs-30-32.md).
- Plan for this series: [2026-09-26-s2-cpu-spread-holds.md](../docs/superpowers/plans/2026-09-26-s2-cpu-spread-holds.md).
