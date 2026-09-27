# S2 both-off runs 35–38, all services

600 s holds, both controllers off, `spawn_rate` 50. Replica CPU table, replicas pinned at the table counts: frontend 4, checkoutservice 2, recommendationservice 3, cartservice 2, paymentservice 2, emailservice 2, and productcatalogservice, currencyservice, shippingservice, adservice, and redis-cart at 1. Sidecar request 70 m with no CPU limit. 360 s cool-off before run35 and between holds. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every number below is from `experiments/s2_both_off_abc.py` on these four folders and on the six earlier ones.

| Mix | This series | Agreed-table replay | Earlier both-off |
|---|---|---|---|
| 7 (380/100/270/20/20) | run35 | run31 | run7 |
| 12 (100/150/100/100/5) | run36 | run34 | run12 |
| 26 (325/100/100/100/5) | run37 | run33 | run26 |
| new (250/150/250/50/50) | run38 | — | — |

The three tables use that column order, left to right: this series, the agreed-table replay, the earlier both-off hold, mix by mix, then run38.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run35 | run31 | run7 | run36 | run34 | run12 | run37 | run33 | run26 | run38 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend (not controlled) | 2 / 2 | 578 / 578 | 21 / 220 | 10 / 357 | 122 / 446 | 122 / 518 | 1 / 1 | 95 / 526 | 72 / 517 | 2 / 2 |
| checkoutservice | 1 / 1 | 0 / 0 | **230 / 264** | **557 / 557** | **122 / 334** | **89 / 287** | 1 / 1 | 0 / 0 | **592 / 592** | 1 / 1 |
| recommendationservice | 1 / 1 | 7 / 292 | 15 / 235 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 8 / 225 | 2 / 43 | 1 / 1 |
| paymentservice | 0 / 0 | 0 / 0 | 1 / 4 | 0 / 0 | **30 / 215** | 3 / 44 | 0 / 0 | 0 / 0 | 2 / 13 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | 6 / 87 | 8 / 295 | 11 / 66 | 1 / 2 | 0 / 0 | 1 / 1 | 4 / 156 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 1 / 1 |
| cartservice | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 |
| currencyservice | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | 1 / 1 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 3 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on run35, run36, run37, and run38, and 0 on run31, run7, run34, run12, run33, and run26.

| Service | run35 | run31 | run7 | run36 | run34 | run12 | run37 | run33 | run26 | run38 |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| checkoutservice | 0/637 (0.0%) | 0/637 (0.0%) | **572/636 (89.9%)** | **572/637 (89.8%)** | **386/637 (60.6%)** | 266/637 (41.8%) | 41/638 (6.4%) | 0/637 (0.0%) | **592/637 (92.9%)** | **457/637 (71.7%)** |
| recommendationservice | 0/637 (0.0%) | 0/637 (0.0%) | **511/636 (80.3%)** | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | **364/637 (57.1%)** | 0/637 (0.0%) |
| paymentservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 1/637 (0.2%) | 256/637 (40.2%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| emailservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 1/637 (0.2%) | 18/637 (2.8%) | 0/637 (0.0%) | 0/638 (0.0%) | 9/637 (1.4%) | 0/637 (0.0%) | 0/637 (0.0%) |
| productcatalogservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| cartservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| currencyservice | 0/637 (0.0%) | 159/637 (25.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 69/637 (10.8%) | 0/637 (0.0%) | 0/637 (0.0%) |
| shippingservice | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| adservice | 4/637 (0.6%) | 0/637 (0.0%) | 1/636 (0.2%) | 0/637 (0.0%) | 2/637 (0.3%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |
| redis-cart | 0/637 (0.0%) | 0/637 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/638 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) | 0/637 (0.0%) |

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

| Service | run35 | run31 | run7 | run36 | run34 | run12 | run37 | run33 | run26 | run38 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| checkoutservice | 0 | 26 | 17,544 | 100,515 | 60,933 | 47,538 | 18 | 128 | 45,182 | 68 |
| recommendationservice | 252 | 225,477 | 133,481 | 0 | 0 | 0 | 192 | 177,103 | 120,541 | 101 |
| paymentservice | 0 | 0 | 0 | 0 | 3,865 | 0 | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cartservice | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

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
