# S2 Paper-C1, the run 89 mix and the run 86 mix

600 s holds, both controllers off, `spawn_rate` 50. Paper-C1: frontend pinned at 4, every other service at 1, sidecar request 100 m with no CPU limit. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The pin: [2026-10-02-s2-paper-c1-run89-handoff.md](2026-10-02-s2-paper-c1-run89-handoff.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. run97 repeats the run 89 mix. run98 repeats the run 86 mix. run94, run95, and run96 are the earlier replays of the run 89 mix on the disk copy. run86 and run89 stay in `experiments/results/campaign_48/S2_sustained_overload/`. The other five are in `experiments/results/new vms/`. A bold bar separates the two mixes. Every number below is from `experiments/s2_both_off_abc.py` on these seven folders, plus the Locust CSVs, `service_inbound.csv`, `resource_usage.csv`, and `topfull_detect.csv`.

| Mix | This series | Earlier holds of the same mix |
| --- | --- | --- |
| 275 / 90 / 100 / 90 / 5 | run97 | run89, run94, run95, run96 |
| 275 / 80 / 100 / 90 / 5 | run98 | run86 |

The tables use that column order: run97, then run89, run94, run95, and run96, then run98 and run86.

## Gates

| Slot | Locust rows | Mesh span | Gaps ≥ 1.5 s | Frontend replicas | Other replicas | Layer A admitting rows |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| run97 | 570 | 692 s | 0% | 4 on 134/134 | 1 on every sample | 0 |
| run89 | 567 | 694 s | 0% | 4 on 134/134 | 1 on every sample | 0 |
| run94 | 558 | 688 s | 0% | 4 on 133/133 | 1 on every sample | 0 |
| run95 | 563 | 687 s | 0% | 4 on 133/133 | 1 on every sample | 0 |
| run96 | 560 | 689 s | 0% | 4 on 134/134 | 1 on every sample | 0 |
| run98 | 570 | 692 s | 0% | 4 on 133/133 | 1 on every sample | 0 |
| run86 | 567 | 693 s | 0% | 4 on 134/134 | 1 on every sample | 0 |

Sampling is 1 s on all seven. `service_capacity.json` on run97 and run98 matches the Paper-C1 table below.

## CPU table

Millicores per pod. Request equals limit. Frontend is × 4. Every other replica count is 1. Deployment total is 11,655 m.

| Service | Quota | Replicas |
| --- | ---: | ---: |
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

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 185 / 536 | 77 / 474 | 1 / 1 | 1 / 1 | 1 / 1 | **┃** | 568 / 568 | 196 / 453 |
| checkoutservice | 23 / 24 | **58 / 97** | **564 / 564** | **568 / 568** | **569 / 569** | **┃** | 0 / 0 | **108 / 115** |
| recommendationservice | **64 / 332** | **238 / 470** | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | **250 / 553** | **229 / 324** |
| paymentservice | 6 / 7 | 1 / 12 | 3 / 15 | 1 / 7 | 1 / 3 | **┃** | 0 / 0 | 2 / 16 |
| emailservice | 4 / 10 | 5 / 19 | 5 / 148 | 5 / 142 | 3 / 116 | **┃** | 0 / 0 | 3 / 28 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on all seven holds.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/637 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| checkoutservice | 123/637 (19.3%) | 164/638 (25.7%) | **590/636 (92.8%)** | **591/635 (93.1%)** | **592/637 (92.9%)** | **┃** | 24/637 (3.8%) | 163/638 (25.5%) |
| recommendationservice | **545/637 (85.6%)** | **485/638 (76.0%)** | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | **567/637 (89.0%)** | **456/638 (71.5%)** |
| paymentservice | 7/637 (1.1%) | 0/638 (0.0%) | 10/636 (1.6%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 16/638 (2.5%) |
| emailservice | 36/637 (5.7%) | 23/638 (3.6%) | 16/636 (2.5%) | 11/635 (1.7%) | 10/637 (1.6%) | **┃** | 14/637 (2.2%) | 22/638 (3.4%) |
| productcatalogservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| cartservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| currencyservice | 0/637 (0.0%) | 2/638 (0.3%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| shippingservice | 0/637 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| adservice | 0/637 (0.0%) | 0/638 (0.0%) | 2/636 (0.3%) | 0/635 (0.0%) | 2/637 (0.3%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |
| redis-cart | 0/637 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) | 0/637 (0.0%) | **┃** | 0/637 (0.0%) | 0/638 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target, the scorer's retry column: the sum of positive Envoy `retry` increments into that service.

- **run97.** frontend → recommendationservice 215,908, frontend → checkoutservice 2,191, frontend → cartservice 4.
- **run89.** frontend → recommendationservice 224,314, frontend → checkoutservice 9,302.
- **run94.** frontend → checkoutservice 61,002, frontend → cartservice 4.
- **run95.** frontend → checkoutservice 61,643.
- **run96.** frontend → checkoutservice 61,775.
- **run98.** frontend → recommendationservice 310,947, frontend → checkoutservice 28.
- **run86.** frontend → recommendationservice 217,256, frontend → checkoutservice 10,434.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| checkoutservice | 2,191 | 9,302 | 61,002 | 61,643 | 61,775 | **┃** | 28 | 10,434 |
| recommendationservice | 215,908 | 224,314 | 0 | 0 | 0 | **┃** | 310,947 | 217,256 |
| paymentservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| cartservice | 4 | 0 | 4 | 0 | 0 | **┃** | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 | 0 | **┃** | 0 | 0 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`. Quota is the per-pod CPU limit. The mean / max cells sum that usage across the pinned replicas.

| Service | Quota | Replicas | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 | 4 | 1115 / 1485 | 1167 / 1628 | 1378 / 1580 | 1364 / 1578 | 1364 / 1581 | **┃** | 979 / 1496 | 1154 / 1607 |
| checkoutservice | 800 | 1 | 385 / 797 | 418 / 796 | 705 / 802 | 702 / 801 | 702 / 801 | **┃** | 58 / 778 | 334 / 798 |
| recommendationservice | 1150 | 1 | 911 / 1152 | 876 / 1149 | 719 / 848 | 721 / 879 | 710 / 845 | **┃** | 995 / 1151 | 892 / 1153 |
| paymentservice | 155 | 1 | 31 / 128 | 35 / 89 | 74 / 130 | 68 / 85 | 68 / 83 | **┃** | 7 / 58 | 33 / 117 |
| emailservice | 120 | 1 | 49 / 104 | 44 / 81 | 13 / 106 | 12 / 106 | 12 / 101 | **┃** | 15 / 110 | 33 / 105 |
| productcatalogservice | 800 | 1 | 357 / 489 | 395 / 526 | 460 / 530 | 460 / 530 | 456 / 530 | **┃** | 290 / 482 | 387 / 552 |
| cartservice | 800 | 1 | 353 / 528 | 441 / 691 | 308 / 370 | 320 / 470 | 309 / 413 | **┃** | 372 / 534 | 422 / 523 |
| currencyservice | 770 | 1 | 320 / 427 | 349 / 527 | 363 / 422 | 356 / 423 | 355 / 422 | **┃** | 294 / 425 | 343 / 524 |
| shippingservice | 770 | 1 | 51 / 107 | 59 / 127 | 95 / 112 | 93 / 110 | 93 / 111 | **┃** | 12 / 101 | 48 / 113 |
| adservice | 1150 | 1 | 106 / 365 | 92 / 207 | 182 / 436 | 157 / 189 | 159 / 237 | **┃** | 50 / 169 | 90 / 221 |
| redis-cart | 540 | 1 | 41 / 49 | 44 / 60 | 35 / 41 | 35 / 40 | 35 / 40 | **┃** | 45 / 55 | 44 / 57 |

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

| API | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 67.3 | 68.3 | 264.0 | 263.9 | 264.0 | **┃** | 9.5 | 75.2 |
| postcheckout | 18.4 | 10.5 | 3.2 | 2.8 | 2.6 | **┃** | 2.8 | 7.3 |
| getcart | 26.8 | 25.9 | 96.3 | 96.0 | 95.9 | **┃** | 3.7 | 27.8 |
| postcart | 86.5 | 86.3 | 86.4 | 86.4 | 86.3 | **┃** | 86.4 | 86.4 |
| emptycart | 4.8 | 4.8 | 4.8 | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.668 | 0.651 | 0.000 | 0.000 | 0.000 | **┃** | 0.941 | 0.617 |
| postcheckout | 0.716 | 0.820 | 0.933 | 0.942 | 0.944 | **┃** | 0.941 | 0.853 |
| getcart | 0.642 | 0.644 | 0.000 | 0.000 | 0.000 | **┃** | 0.938 | 0.614 |
| postcart | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

| API | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 1988 | 1826 | 320 | 302 | 310 | **┃** | 2062 | 1741 |
| postcheckout | 2035 | 2105 | 2229 | 2206 | 2204 | **┃** | 2054 | 2083 |
| getcart | 1941 | 1769 | 336 | 326 | 325 | **┃** | 2050 | 1693 |
| postcart | 65 | 69 | 74 | 72 | 73 | **┃** | 62 | 68 |
| emptycart | 14 | 20 | 19 | 16 | 26 | **┃** | 13 | 17 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 382.7 | 368.5 | 442.7 | 443.7 | 442.3 | **┃** | 319.5 | 362.1 |
| checkoutservice | 28.3 | 36.3 | 130.6 | 131.9 | 131.6 | **┃** | 3.0 | 32.5 |
| recommendationservice | 614.1 | 608.4 | 361.6 | 362.5 | 361.3 | **┃** | 688.1 | 592.8 |
| paymentservice | 28.1 | 31.5 | 109.5 | 108.2 | 108.1 | **┃** | 3.0 | 29.2 |
| emailservice | 24.1 | 18.1 | 3.8 | 3.4 | 3.2 | **┃** | 3.0 | 11.9 |
| productcatalogservice | 1295.8 | 1294.1 | 2480.1 | 2486.4 | 2478.1 | **┃** | 540.5 | 1229.4 |
| cartservice | 378.6 | 372.9 | 544.2 | 545.1 | 543.4 | **┃** | 283.1 | 364.3 |
| currencyservice | 507.3 | 496.0 | 772.7 | 774.8 | 772.5 | **┃** | 349.7 | 485.1 |
| shippingservice | 85.8 | 92.0 | 266.1 | 265.2 | 264.4 | **┃** | 9.9 | 82.4 |
| adservice | 84.8 | 85.9 | 234.2 | 234.7 | 234.0 | **┃** | 10.1 | 82.0 |
| redis-cart | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal from `service_inbound.csv`.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.422 | 0.411 | 0.088 | 0.089 | 0.089 | **┃** | 0.693 | 0.434 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | **┃** | n/a | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal from `service_inbound.csv`.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.001 | 0.002 | 0.001 | 0.000 | 0.000 | **┃** | 0.002 | 0.002 |
| checkoutservice | 0.083 | 0.325 | 0.477 | 0.479 | 0.478 | **┃** | 0.008 | 0.396 |
| recommendationservice | 0.206 | 0.291 | 0.000 | 0.000 | 0.000 | **┃** | 0.245 | 0.231 |
| paymentservice | 0.029 | 0.047 | 0.064 | 0.064 | 0.064 | **┃** | 0.000 | 0.069 |
| emailservice | 0.005 | 0.012 | 0.084 | 0.112 | 0.101 | **┃** | 0.014 | 0.019 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.001 | 0.005 | 0.005 | 0.005 | **┃** | 0.000 | 0.001 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.002 | 0.007 | 0.023 | 0.023 | 0.023 | **┃** | 0.000 | 0.011 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | **┃** | n/a | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 842 | 869 | 310 | 302 | 303 | **┃** | 1129 | 853 |
| checkoutservice | 144 | 231 | 491 | 491 | 492 | **┃** | 159 | 284 |
| recommendationservice | 473 | 437 | 96 | 82 | 84 | **┃** | 494 | 429 |
| paymentservice | 8 | 7 | 9 | 7 | 7 | **┃** | 4 | 12 |
| emailservice | 17 | 24 | 29 | 27 | 22 | **┃** | 33 | 22 |
| productcatalogservice | 2 | 3 | 2 | 2 | 2 | **┃** | 1 | 3 |
| cartservice | 3 | 3 | 5 | 5 | 5 | **┃** | 3 | 4 |
| currencyservice | 2 | 4 | 5 | 6 | 6 | **┃** | 2 | 5 |
| shippingservice | 1 | 1 | 2 | 2 | 2 | **┃** | 1 | 2 |
| adservice | 1 | 2 | 1 | 1 | 1 | **┃** | 1 | 2 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | **┃** | n/a | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets`.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.720 | 0.636 | 0.089 | 0.090 | 0.089 | **┃** | 0.712 | 0.594 |
| checkoutservice | 0.083 | 0.274 | 0.955 | 0.961 | 0.962 | **┃** | 0.011 | 0.413 |
| recommendationservice | 0.754 | 0.698 | 0.000 | 0.000 | 0.000 | **┃** | 0.972 | 0.726 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a | n/a | **┃** | n/a | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is the per-pod limit in `topfull_detect.csv`. `cpu_millicores` and `replica_count` are from `resource_usage.csv`.

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.24 / 0.32 | 0.25 / 0.35 | 0.30 / 0.34 | 0.30 / 0.34 | 0.30 / 0.34 | **┃** | 0.21 / 0.33 | 0.25 / 0.35 |
| checkoutservice | 0.48 / 1.00 | 0.52 / 0.99 | 0.88 / 1.00 | 0.88 / 1.00 | 0.88 / 1.00 | **┃** | 0.07 / 0.97 | 0.42 / 1.00 |
| recommendationservice | 0.79 / 1.00 | 0.76 / 1.00 | 0.63 / 0.74 | 0.63 / 0.76 | 0.62 / 0.73 | **┃** | 0.87 / 1.00 | 0.78 / 1.00 |
| paymentservice | 0.20 / 0.83 | 0.23 / 0.57 | 0.48 / 0.84 | 0.44 / 0.55 | 0.44 / 0.54 | **┃** | 0.04 / 0.37 | 0.21 / 0.75 |
| emailservice | 0.41 / 0.87 | 0.37 / 0.68 | 0.11 / 0.88 | 0.10 / 0.88 | 0.10 / 0.84 | **┃** | 0.13 / 0.92 | 0.27 / 0.88 |
| productcatalogservice | 0.45 / 0.61 | 0.49 / 0.66 | 0.57 / 0.66 | 0.57 / 0.66 | 0.57 / 0.66 | **┃** | 0.36 / 0.60 | 0.48 / 0.69 |
| cartservice | 0.44 / 0.66 | 0.55 / 0.86 | 0.39 / 0.46 | 0.40 / 0.59 | 0.39 / 0.52 | **┃** | 0.47 / 0.67 | 0.53 / 0.65 |
| currencyservice | 0.42 / 0.55 | 0.45 / 0.68 | 0.47 / 0.55 | 0.46 / 0.55 | 0.46 / 0.55 | **┃** | 0.38 / 0.55 | 0.45 / 0.68 |
| shippingservice | 0.07 / 0.14 | 0.08 / 0.16 | 0.12 / 0.15 | 0.12 / 0.14 | 0.12 / 0.14 | **┃** | 0.02 / 0.13 | 0.06 / 0.15 |
| adservice | 0.09 / 0.32 | 0.08 / 0.18 | 0.16 / 0.38 | 0.14 / 0.16 | 0.14 / 0.21 | **┃** | 0.04 / 0.15 | 0.08 / 0.19 |
| redis-cart | 0.08 / 0.09 | 0.08 / 0.11 | 0.07 / 0.08 | 0.06 / 0.07 | 0.06 / 0.07 | **┃** | 0.08 / 0.10 | 0.08 / 0.11 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run97 | run89 | run94 | run95 | run96 | **┃** | run98 | run86 |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.335 | 0.378 | 0.367 | 0.367 | 0.366 | **┃** | 0.339 | 0.389 |
| checkoutservice | 1.031 | 1.039 | 1.051 | 1.048 | 1.080 | **┃** | 0.999 | 1.036 |
| recommendationservice | 1.010 | 1.015 | 0.763 | 0.800 | 0.761 | **┃** | 1.018 | 1.019 |
| paymentservice | 1.000 | 0.800 | 0.948 | 0.794 | 0.787 | **┃** | 0.703 | 0.942 |
| emailservice | 1.017 | 1.017 | 1.025 | 0.975 | 0.992 | **┃** | 0.983 | 1.017 |
| productcatalogservice | 0.640 | 0.708 | 0.696 | 0.708 | 0.693 | **┃** | 0.634 | 0.743 |
| cartservice | 0.699 | 0.921 | 0.522 | 0.615 | 0.564 | **┃** | 0.682 | 0.729 |
| currencyservice | 0.606 | 0.805 | 0.613 | 0.597 | 0.588 | **┃** | 0.617 | 0.716 |
| shippingservice | 0.160 | 0.203 | 0.188 | 0.195 | 0.186 | **┃** | 0.147 | 0.197 |
| adservice | 0.595 | 0.323 | 0.921 | 0.189 | 0.803 | **┃** | 0.163 | 0.354 |
| redis-cart | 0.094 | 0.126 | 0.080 | 0.080 | 0.080 | **┃** | 0.109 | 0.117 |

## Per mix

**275 / 90 / 100 / 90 / 5.**
run97 clears streak 30 on 1 controlled service (recommendationservice) and an overloaded share of 0.5 on 1 (recommendationservice). Recommendations 64 / 545, checkout 23 / 123, email ov 36, payment ov 7: blend.
run89 clears streak 30 on 2 controlled services (checkoutservice, recommendationservice) and an overloaded share of 0.5 on 1 (recommendationservice). Recommendations 238 / 485, checkout 58 / 164, email ov 23, payment ov 0: blend.
run94 clears streak 30 on 1 controlled service (checkoutservice) and an overloaded share of 0.5 on 1 (checkoutservice). Recommendations 0 / 0, checkout 564 / 590, email ov 16, payment ov 10: not a blend.
run95 clears streak 30 on 1 controlled service (checkoutservice) and an overloaded share of 0.5 on 1 (checkoutservice). Recommendations 0 / 0, checkout 568 / 591, email ov 11, payment ov 0: not a blend.
run96 clears streak 30 on 1 controlled service (checkoutservice) and an overloaded share of 0.5 on 1 (checkoutservice). Recommendations 0 / 0, checkout 569 / 592, email ov 10, payment ov 0: not a blend.

**275 / 80 / 100 / 90 / 5.**
run98 clears streak 30 on 1 controlled service (recommendationservice) and an overloaded share of 0.5 on 1 (recommendationservice). Recommendations 250 / 567, checkout 0 / 24, email ov 14, payment ov 0: not a blend.
run86 clears streak 30 on 2 controlled services (checkoutservice, recommendationservice) and an overloaded share of 0.5 on 1 (recommendationservice). Recommendations 229 / 456, checkout 108 / 163, email ov 22, payment ov 16: blend.

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- The layout this file copies: [2026-09-27-s2-replica-cpu-runs-35-38.md](2026-09-27-s2-replica-cpu-runs-35-38.md).
- Paper-C1 pin and the run 89 mix: [2026-10-02-s2-paper-c1-run89-handoff.md](2026-10-02-s2-paper-c1-run89-handoff.md).
- Earlier tables for run89, run92, run94, and run95: [2026-10-02-s2-paper-c1-run89-replay.md](2026-10-02-s2-paper-c1-run89-replay.md).
- Earlier Paper-C1 holds including run86: [2026-10-01-s2-paper-c1-runs-80-84-88.md](2026-10-01-s2-paper-c1-runs-80-84-88.md).

