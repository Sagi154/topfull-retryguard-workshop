# S2 final-candidate holds, (a)/(b)/(c)

600 s both-off holds (`topfull_rl` off, RetryGuard off, `spawn_rate` 50, Istio attempts 3, `perTryTimeout` 500 ms). Runs 60–70 are the 2026-09-29 series. Runs 6, 42, 43, and 54 are the reference holds those rounds were built to match. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). CPU tables: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md). Every number below is from `experiments/s2_both_off_abc.py` on that run folder, except Locust row counts and replica dips, which are counted from `total.csv` and `resource_usage.csv`.

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Sidecar CPU limit was unset on every hold. Paper holds used sidecar request 90 m. The others used 100 m. Frontend was pinned at 4. Comparison columns are grouped by that mix. A bold bar separates mix groups.

## Hold index

| Slot | Label | Table | Sidecar | Mix | Locust rows | Gate |
| --- | --- | --- | --- | ---: | --- | --- |
| run6 | reference | Paper | 90 m | 340/100/240/10/10 | 569 | pass |
| run42 | reference | Checkout-3 | 100 m | 150/250/150/20/20 | 565 | pass |
| run43 | reference | Checkout-4 | 100 m | 200/250/200/50/50 | 560 | emailservice replica dip 2/134 |
| run54 | reference | Recs-3 | 90 m | 100/300/100/200/200 | 565 | pass |
| run60 | A2 | Checkout-3 | 100 m | 150/250/150/20/20 | 571 | pass |
| run61 | B1 | Checkout-3 | 100 m | 200/250/200/50/50 | 572 | pass |
| run62 | D3 | Checkout-3 | 100 m | 300/200/200/10/10 | 573 | pass |
| run63 | A3 | Checkout-3, email 180 m, redis-cart 320 m | 100 m | 150/250/150/20/20 | 571 | paymentservice replica dip 1/134 |
| run64 | B2 | Checkout-4 | 100 m | 150/250/150/20/20 | 572 | emailservice replica dip 2/132 |
| run65 | A1 | Paper | 90 m | 340/100/240/10/10 | 567 | pass |
| run66 | D2 | Paper | 90 m | 300/200/200/10/10 | 572 | checkoutservice replica dip 3/66 |
| run67 | D1 | Hybrid | 100 m | 300/200/200/10/10 | 571 | pass |
| run68 | C1 | Hybrid | 100 m | 270/200/280/10/10 | 571 | pass |
| run69 | C2 | Hybrid | 100 m | 200/250/250/10/10 | 570 | pass |
| run70 | C3 | Hybrid | 100 m | 270/200/280/10/10 | 569 | pass |

Mesh span on every folder above is between 689 s and 705 s. Layer A admitting rows are 0 on all fifteen holds.

Replica dips are `replica_count` in `resource_usage.csv` disagreeing with `service_capacity.json`. The Locust series is still a full hold on each of those four folders. run66's checkoutservice dip is 3 samples out of only 66 checkout rows in that file.

## (a) Inbound rejection streak

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. **Bold** is streak ≥ 30 on a controlled service. Frontend and redis-cart stay plain.

Columns, left to right, by mix: 340/100/240/10/10 (run6, run65); 150/250/150/20/20 (run42, run60, run63, run64); 200/250/200/50/50 (run43, run61); 100/300/100/200/200 (run54); 300/200/200/10/10 (run62, run66, run67); 270/200/280/10/10 (run68, run70); 200/250/250/10/10 (run69).

| Service | run6 | run65 | **┃** | run42 | run60 | run63 | run64 | **┃** | run43 | run61 | **┃** | run54 | **┃** | run62 | run66 | run67 | **┃** | run68 | run70 | **┃** | run69 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend (not controlled) | 125 / 424 | 4 / 22 | **┃** | 4 / 90 | 14 / 308 | 26 / 391 | 7 / 71 | **┃** | 2 / 2 | 3 / 31 | **┃** | 2 / 3 | **┃** | 2 / 2 | 162 / 402 | 575 / 575 | **┃** | 578 / 578 | 576 / 576 | **┃** | 563 / 572 |
| checkoutservice | **177 / 324** | **357 / 578** | **┃** | **185 / 571** | **577 / 578** | **549 / 563** | **169 / 255** | **┃** | **147 / 424** | **271 / 566** | **┃** | **66 / 342** | **┃** | 1 / 1 | **78 / 220** | 2 / 3 | **┃** | 1 / 1 | 1 / 1 | **┃** | 23 / 23 |
| recommendationservice | **44 / 336** | 2 / 10 | **┃** | 1 / 1 | 2 / 2 | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | **┃** | 1 / 1 | 8 / 32 | **35 / 437** | **┃** | 17 / 453 | 16 / 426 | **┃** | 19 / 443 |
| paymentservice | 1 / 8 | 2 / 26 | **┃** | 6 / 62 | 6 / 116 | 11 / 155 | 1 / 2 | **┃** | 2 / 2 | 1 / 3 | **┃** | 0 / 0 | **┃** | 0 / 0 | 5 / 93 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 2 |
| emailservice | 5 / 92 | 6 / 83 | **┃** | 29 / 454 | 8 / 319 | 17 / 328 | **170 / 259** | **┃** | **147 / 427** | **272 / 572** | **┃** | **179 / 359** | **┃** | 1 / 1 | 1 / 3 | 1 / 2 | **┃** | 1 / 2 | 1 / 2 | **┃** | 4 / 14 |
| productcatalogservice | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | **┃** | 0 / 0 | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 1 / 1 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 1 / 1 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 1 / 1 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 |
| adservice | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 1 / 3 | 0 / 0 | 0 / 0 | **┃** | 1 / 2 | 1 / 1 | **┃** | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |

## (b) Detector overloaded share

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Same column order as (a).

| Service | run6 | run65 | **┃** | run42 | run60 | run63 | run64 | **┃** | run43 | run61 | **┃** | run54 | **┃** | run62 | run66 | run67 | **┃** | run68 | run70 | **┃** | run69 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| checkoutservice | **476/637 (74.7%)** | **587/637 (92.2%)** | **┃** | **579/638 (90.8%)** | **580/642 (90.3%)** | **582/642 (90.7%)** | **499/637 (78.3%)** | **┃** | **481/638 (75.4%)** | **578/643 (89.9%)** | **┃** | **397/636 (62.4%)** | **┃** | 8/641 (1.2%) | 207/636 (32.5%) | 10/637 (1.6%) | **┃** | 5/638 (0.8%) | 6/637 (0.9%) | **┃** | 37/639 (5.8%) |
| recommendationservice | **558/637 (87.6%)** | **558/637 (87.6%)** | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | **391/636 (61.5%)** | **566/637 (88.9%)** | **┃** | **576/638 (90.3%)** | **569/637 (89.3%)** | **┃** | **549/639 (85.9%)** |
| paymentservice | 0/637 (0.0%) | 2/637 (0.3%) | **┃** | **547/638 (85.7%)** | **573/642 (89.3%)** | **563/642 (87.7%)** | **507/637 (79.6%)** | **┃** | **509/638 (79.8%)** | **486/643 (75.6%)** | **┃** | 208/636 (32.7%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 2/637 (0.3%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 3/639 (0.5%) |
| emailservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | **432/638 (67.7%)** | 176/642 (27.4%) | 119/642 (18.5%) | **567/637 (89.0%)** | **┃** | **566/638 (88.7%)** | **588/643 (91.4%)** | **┃** | **583/636 (91.7%)** | **┃** | **577/641 (90.0%)** | 0/636 (0.0%) | 6/637 (0.9%) | **┃** | 9/638 (1.4%) | 6/637 (0.9%) | **┃** | 14/639 (2.2%) |
| productcatalogservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| cartservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| currencyservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 3/641 (0.5%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| shippingservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| adservice | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 6/638 (0.9%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 1/637 (0.2%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |
| redis-cart | 0/637 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/642 (0.0%) | 0/642 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/643 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/641 (0.0%) | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/639 (0.0%) |

## (c) Retry delta

Sum of positive Envoy `retry` increments into that target. Same column order. The large edges sit on the service that is hot on (a) or (b): frontend → recommendationservice when recommendations is the hot service (run6, and Hybrid run67–run70), and frontend → checkoutservice when checkout is the hot service (the Checkout-3/4 holds and the Paper replay run65). Checkout → emailservice appears only on the holds where email itself clears streak 30 (run43 2,652, run64 3,679) or just beside them (run61 99).

| Service | run6 | run65 | **┃** | run42 | run60 | run63 | run64 | **┃** | run43 | run61 | **┃** | run54 | **┃** | run62 | run66 | run67 | **┃** | run68 | run70 | **┃** | run69 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| checkoutservice | 21,930 | 51,589 | **┃** | 115,361 | 133,659 | 138,755 | 104,622 | **┃** | 82,368 | 98,121 | **┃** | 61,870 | **┃** | 248 | 35,594 | 348 | **┃** | 227 | 214 | **┃** | 3,964 |
| recommendationservice | 167,763 | 10,009 | **┃** | 0 | 0 | 95 | 5,097 | **┃** | 141 | 0 | **┃** | 0 | **┃** | 2,369 | 19,980 | 241,612 | **┃** | 248,174 | 239,565 | **┃** | 226,502 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | 175 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | 8 | 3,679 | **┃** | 2,652 | 99 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| productcatalogservice | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| cartservice | 0 | 0 | **┃** | 0 | 5 | 0 | 0 | **┃** | 6 | 0 | **┃** | 0 | **┃** | 0 | 0 | 6 | **┃** | 0 | 0 | **┃** | 0 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| adservice | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |

Top edges, largest first:

- **run6.** frontend → recommendationservice 167,763, frontend → checkoutservice 21,930.
- **run65.** frontend → checkoutservice 51,589, frontend → recommendationservice 10,009.
- **run42.** frontend → checkoutservice 115,361.
- **run60.** frontend → checkoutservice 133,659.
- **run63.** frontend → checkoutservice 138,755.
- **run64.** frontend → checkoutservice 104,622, frontend → recommendationservice 5,097, checkoutservice → emailservice 3,679.
- **run43.** frontend → checkoutservice 82,368, checkoutservice → emailservice 2,652.
- **run61.** frontend → checkoutservice 98,121, checkoutservice → emailservice 99.
- **run54.** frontend → checkoutservice 61,870.
- **run62.** frontend → recommendationservice 2,369, frontend → checkoutservice 248.
- **run66.** frontend → checkoutservice 35,594, frontend → recommendationservice 19,980.
- **run67.** frontend → recommendationservice 241,612, frontend → checkoutservice 348.
- **run68.** frontend → recommendationservice 248,174, frontend → checkoutservice 227.
- **run70.** frontend → recommendationservice 239,565, frontend → checkoutservice 214.
- **run69.** frontend → recommendationservice 226,502, frontend → checkoutservice 3,964.

## Scorecard

The pick rule wants (a) on at least two controlled services, (b) on at least two services, and (c) in the tens of thousands, on at least two replays. An independent pair is checkout plus recommendations. A chain is checkout plus payment plus email.

| Hold | (a) controlled ≥ 30 | (b) ≥ 0.5 | (c) on those edges | Pair |
| --- | --- | --- | --- | --- |
| run6 | checkout 177, recommendations 44 | checkout 74.7%, recommendations 87.6% | 168k recs, 22k checkout | independent |
| run65 | checkout 357 | checkout 92.2%, recommendations 87.6% | 52k checkout, 10k recs | recommendations (b) only |
| run42 | checkout 185 | checkout 90.8%, payment 85.7%, email 67.7% | 115k checkout | chain on (b); email streak 29 |
| run60 | checkout 577 | checkout 90.3%, payment 89.3% | 134k checkout | checkout + payment |
| run63 | checkout 549 | checkout 90.7%, payment 87.7% | 139k checkout | checkout + payment; email streak 17 |
| run64 | checkout 169, email 170 | checkout 78.3%, payment 79.6%, email 89.0% | 105k checkout, 3.7k email | chain |
| run43 | checkout 147, email 147 | checkout 75.4%, payment 79.8%, email 88.7% | 82k checkout, 2.7k email | chain |
| run61 | checkout 271, email 272 | checkout 89.9%, payment 75.6%, email 91.4% | 98k checkout | chain |
| run54 | checkout 66, email 179 | checkout 62.4%, email 91.7% | 62k checkout | checkout + email; payment 32.7% |
| run62 | none | email 90.0% | 2.4k recs | email (b) only |
| run66 | checkout 78 | recommendations 61.5% | 36k checkout, 20k recs | one service each |
| run67 | recommendations 35 | recommendations 88.9% | 242k recs | one service |
| run68 | none | recommendations 90.3% | 248k recs | recommendations (b) and (c); streak 17 |
| run70 | none | recommendations 89.3% | 240k recs | same as run68; streak 16 |
| run69 | none | recommendations 85.9% | 227k recs | recommendations (b) and (c); checkout streak 23 |

No mix in this series clears the full rule on two clean replays. The independent pair exists on run6 only. The chain (checkout and email on (a), payment on (b), checkout retries in the tens of thousands) repeats on run43, run61, and run64. run43 and run64 have an emailservice replica dip. run61 is clean.

## Design questions

**A1 (run65) against run6.** Same Paper table, same mix, sidecar 90 m. Checkout streak stays above 30 (177, then 357) and both services stay above 0.5 overloaded (checkout 74.7% then 92.2%, recommendations 87.6% on both). Recommendations streak does not: 44, then 2. The retry mass moves from recommendations (167,763) to checkout (51,589), with recommendations left at 10,009.

**A2 (run60) against run42.** Same Checkout-3 table, same mix, sidecar 100 m. Checkout streak stays above 30 (185, then 577), checkout stays overloaded (90.8%, then 90.3%), payment stays overloaded (85.7%, then 89.3%), and frontend → checkout retries stay above 100,000 (115,361, then 133,659). Email does not: streak 29 then 8, overloaded share 67.7% then 27.4%.

**A3 (run63).** Email limit 180 m and redis-cart 320 m, same mix as run42/run60. Email streak is 17. That is under 30. Checkout streak is 549 and payment overloaded share is 87.7%. Paymentservice `replica_count` disagreed on 1 of 134 resource samples.

**B1 (run61) and B2 (run64).** B1 is the run43 mix (200/250/200/50/50) on Checkout-3. It matches run43: checkout and email both clear streak 30 (271 and 272), and checkout, payment, and email are all overloaded (89.9%, 75.6%, 91.4%). B1 follows the mix. B2 is the run42 mix (150/250/150/20/20) on Checkout-4. It matches run43's chain (checkout streak 169, email streak 170, payment overloaded 79.6%) and does not match run42, where email streak was 29. B2 follows the Checkout-4 table. Emailservice `replica_count` disagreed on 2 of 132 samples on run64, and on 2 of 134 on run43.

**Round C.** C1 (run68) and C2 (run69) both have zero controlled services at streak ≥ 30, and each has one service at overloaded share ≥ 0.5 (recommendations, 90.3% and 85.9%). C1's recommendations retry delta is larger (248,174 versus 226,502), so C3 replays C1. The replay (run70) matches C1: recommendations streak 16 versus 17, overloaded share 89.3% versus 90.3%, retries 239,565 versus 248,174, checkout streak 1. C2's checkout streak of 23 does not come back.

**Round D.** Same mix 300/200/200/10/10 on three tables. Checkout-3 (run62) clears nothing on (a); email is overloaded at 90.0% with streak 1, and retries stay at 2,369. Paper (run66) clears checkout on (a) at streak 78 and recommendations on (b) at 61.5%, with retries 35,594 and 19,980. Hybrid (run67) is the one that clears recommendations on (a) at streak 35, with overloaded share 88.9% and retries 241,612. Checkout stays cold on that Hybrid hold (streak 2, overloaded 1.6%).

## Recommendation

Measured: do not lock Hybrid 270/200/280/10/10. Recommendations is detector-hot and the retry delta is about 240,000 on both run68 and the replay run70, and the rejection streak stays at 16–17. The one Hybrid hold that did cross streak 30 is run67 (300/200/200/10/10, streak 35, retries 241,612). It was not replayed, and checkout was cold, so it is one service.

The pattern that repeats is the checkout–email chain, with payment overloaded and frontend → checkout retries in the tens of thousands. It is on Checkout-4 at 200/250/200/50/50 (run43) and at 150/250/150/20/20 (run64), and on Checkout-3 at 200/250/200/50/50 (run61, the clean one). Sidecar request on those holds is 100 m, with no CPU limit.

The only independent pair is still Paper run6, sidecar 90 m, mix 340/100/240/10/10: checkout streak 177 and recommendations streak 44, both overloaded, retries 167,763 into recommendations. The Paper replay run65 kept both services overloaded and lost the recommendations streak.

Not measured, so not a claim about the next hold: a second Paper replay of that mix might or might not bring the recommendations streak back, and a second Hybrid run67 might or might not repeat streak 35.

Remaining risks that were measured. The storefront cap on run60 was the closed loop on postcheckout (P95 about 2.4 s), with the load VM idle and the frontend app container near a quarter of 1150 m. Raising user counts does not raise offered rate once that wait is in place. Emailservice and paymentservice replica dips show up under Checkout-4 and on the A3 hold. run66's checkout resource series is short (66 rows).

## Round 0

The snapshot during run60 names the limiter. Fast tags sat near one request per second per user. postcheckout achieved 131.5 req/s from 250 users because P95 was 2.4–2.5 s. Load-VM idle fraction was 0.898. Frontend `istio-proxy` was about 460–545 m with no CPU limit, and emptycart stayed at 19 req/s and 23 ms. E1 and E2 were not run. Detail: [2026-09-29-s2-round0-ceiling-snapshot.md](2026-09-29-s2-round0-ceiling-snapshot.md).

## Related

- [2026-09-29-s2-final-candidate-holds.md](2026-09-29-s2-final-candidate-holds.md)
- [2026-09-29-s2-abc-runs-6-42-43-54.md](2026-09-29-s2-abc-runs-6-42-43-54.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md)
