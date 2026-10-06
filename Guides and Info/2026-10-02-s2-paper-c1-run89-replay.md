# S2 Paper-C1, the run 89 mix, runs 89, 92, 94, and 95

Same mix four times: **275 / 90 / 100 / 90 / 5** (getproduct / postcheckout / getcart / postcart / emptycart). 600 s, both controllers off, `spawn_rate` 50. Paper-C1 from [2026-09-30-s2-lens-blend-handoff.md](2026-09-30-s2-lens-blend-handoff.md): frontend pinned at 4, every other service at 1, sidecar request 100 m with no CPU limit. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Earlier Paper-C1 holds: [2026-10-01-s2-paper-c1-runs-80-84-88.md](2026-10-01-s2-paper-c1-runs-80-84-88.md).

run89 is the first hold of this mix. run92 is its replay. run94 is the third hold and run95 is the fourth, both launched 2026-10-02 on the disk copy (`project-76deda76-55f1-42d2-abb`) from branch `s2-paper-c1-run89-replay`. run89 and run92 stay in `experiments/results/campaign_48/S2_sustained_overload/`. run94 and run95 are in `experiments/results/new vms/`.

## Pass bar

The bar is the handoff's, not a retry target. Streak = `(Δ5xx + Δresets) / Δtotal > 0.20` on consecutive 1 s inbound polls. Overloaded tick = `topfull_detect.csv` `overloaded=1`.

| Element | Requirement |
| --- | --- |
| Recommendations | streak ≥ 10 and ≥ 10 overloaded ticks |
| Checkout | streak ≥ 10 and ≥ 10 overloaded ticks |
| Chain leaf | email or payment with ≥ 10 overloaded ticks |
| Not counted | retry volume, goodput, max utilization |

A hold that clears all three rows is a blend. The handoff does not accept a blend until a replay also clears it. A streak of 30 is the separate RetryGuard disable length used in the (a) table; **bold** there means streak ≥ 30 on a controlled service. Frontend and redis-cart are outside that set.

| Slot | Rec streak | Rec ov | Checkout streak | Checkout ov | Email ov | Payment ov | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| run89 | 238 | 485 | 58 | 164 | 23 | 0 | blend |
| run92 | 454 | 480 | 59 | 128 | 6 | 5 | independent pair; leaf missed |
| run94 | 0 | 0 | 564 | 590 | 16 | 10 | checkout + thin leaf; recommendations missed |
| run95 | 0 | 0 | 568 | 591 | 11 | 0 | checkout + thin leaf; recommendations missed |

run89 clears all three rows. The leaf is thin: email is 23 of 638 detector ticks (3.6%), streak 5. run92 keeps checkout and recommendations and drops the leaf under 10 ticks. run94 keeps checkout and puts both leaves at or above 10 ticks (email 16, payment 10) while recommendations is cold. run95 keeps the same checkout latch and clears the leaf on email alone (11 ticks); payment is 0. The blend did not survive a replay.

## Gates

| Slot | Locust rows | Mesh span | Gaps ≥ 1.5 s | Frontend replicas | Other replicas | Layer A admitting rows |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| run89 | 567 | 694 s | 0% | 4 on 134/134 | 1 on every sample | 0 |
| run92 | 565 | 694 s | 0% | 4 on 134/134 | 1 on every sample | 0 |
| run94 | 558 | 688 s | 0% | 4 on 133/133 | 1 on every sample | 0 |
| run95 | 563 | 687 s | 0% | 4 on 133/133 | 1 on every sample | 0 |

`service_capacity.json` on run94 and run95 matches the Paper-C1 table below. Sampling is 1 s. All four holds are scorable.

## CPU table

Millicores per pod. Request equals limit. Frontend is × 4. Every other replica count is 1. Deployment total is 11,655 m, the handoff's C1 total.

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

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend (not controlled) | 77 / 474 | 453 / 484 | 1 / 1 | 1 / 1 |
| checkoutservice | **58 / 97** | **59 / 102** | **564 / 564** | **568 / 568** |
| recommendationservice | **238 / 470** | **454 / 481** | 0 / 0 | 0 / 0 |
| paymentservice | 1 / 12 | 1 / 9 | 3 / 15 | 1 / 7 |
| emailservice | 5 / 19 | 3 / 16 | 5 / 148 | 5 / 142 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0 on all four holds.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0/638 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |
| checkoutservice | 164/638 (25.7%) | 128/638 (20.1%) | **590/636 (92.8%)** | **591/635 (93.1%)** |
| recommendationservice | **485/638 (76.0%)** | **480/638 (75.2%)** | 0/636 (0.0%) | 0/635 (0.0%) |
| paymentservice | 0/638 (0.0%) | 5/638 (0.8%) | 10/636 (1.6%) | 0/635 (0.0%) |
| emailservice | 23/638 (3.6%) | 6/638 (0.9%) | 16/636 (2.5%) | 11/635 (1.7%) |
| productcatalogservice | 0/638 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |
| cartservice | 0/638 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |
| currencyservice | 2/638 (0.3%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |
| shippingservice | 0/638 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |
| adservice | 0/638 (0.0%) | 0/638 (0.0%) | 2/636 (0.3%) | 0/635 (0.0%) |
| redis-cart | 0/638 (0.0%) | 0/638 (0.0%) | 0/636 (0.0%) | 0/635 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first.

- **run89.** frontend → recommendationservice 224,314, frontend → checkoutservice 9,302.
- **run92.** frontend → recommendationservice 235,145, frontend → checkoutservice 10,323.
- **run94.** frontend → checkoutservice 61,002, frontend → cartservice 4.
- **run95.** frontend → checkoutservice 61,643.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0 | 0 | 0 | 0 |
| checkoutservice | 9,302 | 10,323 | 61,002 | 61,643 |
| recommendationservice | 224,314 | 235,145 | 0 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 4 | 0 |
| currencyservice | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 |

## CPU mean / max

App-container millicores, mean / max, from `resource_usage.csv`. The cell is the sum across replicas. Frontend is 4 replicas, so its mean sits above the per-pod quota.

| Service | Quota | run89 | run92 | run94 | run95 |
| --- | ---: | --- | --- | --- | --- |
| frontend | 1150 | 1167 / 1628 | 1107 / 1628 | 1378 / 1580 | 1364 / 1578 |
| checkoutservice | 800 | 418 / 796 | 327 / 799 | 705 / 802 | 702 / 801 |
| recommendationservice | 1150 | 876 / 1149 | 923 / 1146 | 719 / 848 | 721 / 879 |
| paymentservice | 155 | 35 / 89 | 29 / 95 | 74 / 130 | 68 / 85 |
| emailservice | 120 | 44 / 81 | 32 / 81 | 13 / 106 | 12 / 106 |
| productcatalogservice | 800 | 395 / 526 | 375 / 540 | 460 / 530 | 460 / 530 |
| cartservice | 800 | 441 / 691 | 481 / 717 | 308 / 370 | 320 / 470 |
| currencyservice | 770 | 349 / 527 | 330 / 522 | 363 / 422 | 356 / 423 |
| shippingservice | 770 | 59 / 127 | 46 / 129 | 95 / 112 | 93 / 110 |
| adservice | 1150 | 92 / 207 | 78 / 193 | 182 / 436 | 157 / 189 |
| redis-cart | 540 | 44 / 60 | 43 / 53 | 35 / 41 | 35 / 40 |

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

| API | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| getproduct | 68.3 | 62.9 | 264.0 | 263.9 |
| postcheckout | 10.5 | 7.1 | 3.2 | 2.8 |
| getcart | 25.9 | 23.4 | 96.3 | 96.0 |
| postcart | 86.3 | 86.4 | 86.4 | 86.4 |
| emptycart | 4.8 | 4.8 | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| getproduct | 0.674 | 0.700 | 0.000 | 0.000 |
| postcheckout | 0.806 | 0.855 | 0.923 | 0.928 |
| getcart | 0.663 | 0.694 | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

| API | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| getproduct | 1826 | 1813 | 320 | 302 |
| postcheckout | 2105 | 2101 | 2229 | 2206 |
| getcart | 1769 | 1756 | 336 | 326 |
| postcart | 69 | 67 | 74 | 72 |
| emptycart | 20 | 18 | 19 | 16 |

## Inbound arrival rate

Hold arrival, sum of positive Δtotal divided by that service's timestamp span, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 368.5 | 362.2 | 442.7 | 443.7 |
| checkoutservice | 36.3 | 32.0 | 130.6 | 131.9 |
| recommendationservice | 608.4 | 618.7 | 361.6 | 362.5 |
| paymentservice | 31.5 | 26.3 | 109.5 | 108.2 |
| emailservice | 18.1 | 11.6 | 3.8 | 3.4 |
| productcatalogservice | 1294.1 | 1157.6 | 2480.1 | 2486.4 |
| cartservice | 372.9 | 357.2 | 544.2 | 545.1 |
| currencyservice | 496.0 | 470.7 | 772.7 | 774.8 |
| shippingservice | 92.0 | 75.1 | 266.1 | 265.2 |
| adservice | 85.9 | 70.9 | 234.2 | 234.7 |
| redis-cart | 0.0 | 0.0 | 0.0 | 0.0 |

## Inbound 5xx fraction

Hold positive Δ5xx / Δtotal.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0.411 | 0.477 | 0.088 | 0.089 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a |

## Inbound reset fraction

Hold positive Δresets / Δtotal.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0.002 | 0.002 | 0.001 | 0.000 |
| checkoutservice | 0.325 | 0.408 | 0.477 | 0.479 |
| recommendationservice | 0.291 | 0.280 | 0.000 | 0.000 |
| paymentservice | 0.047 | 0.059 | 0.064 | 0.064 |
| emailservice | 0.012 | 0.010 | 0.084 | 0.112 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.001 | 0.001 | 0.005 | 0.005 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.007 | 0.010 | 0.023 | 0.023 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), positive Δrq_time_sum_ms / Δrq_time_count.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 869 | 892 | 310 | 302 |
| checkoutservice | 231 | 262 | 491 | 491 |
| recommendationservice | 437 | 434 | 96 | 82 |
| paymentservice | 7 | 7 | 9 | 7 |
| emailservice | 24 | 15 | 29 | 27 |
| productcatalogservice | 3 | 3 | 2 | 2 |
| cartservice | 3 | 3 | 5 | 5 |
| currencyservice | 4 | 4 | 5 | 6 |
| shippingservice | 1 | 2 | 2 | 2 |
| adservice | 2 | 2 | 1 | 1 |
| redis-cart | n/a | n/a | n/a | n/a |

## Share of inbound requests above 500 ms

From the cumulative `rq_time_buckets`, positive Δ(`+Inf` − `500`) / Δ`+Inf`.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0.636 | 0.614 | 0.089 | 0.090 |
| checkoutservice | 0.274 | 0.401 | 0.955 | 0.961 |
| recommendationservice | 0.698 | 0.752 | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | n/a | n/a | n/a | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is the per-pod limit in `topfull_detect.csv`.

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0.25 / 0.35 | 0.24 / 0.35 | 0.30 / 0.34 | 0.30 / 0.34 |
| checkoutservice | 0.52 / 1.00 | 0.41 / 1.00 | 0.88 / 1.00 | 0.88 / 1.00 |
| recommendationservice | 0.76 / 1.00 | 0.80 / 1.00 | 0.63 / 0.74 | 0.63 / 0.76 |
| paymentservice | 0.23 / 0.57 | 0.19 / 0.61 | 0.48 / 0.84 | 0.44 / 0.55 |
| emailservice | 0.37 / 0.68 | 0.27 / 0.68 | 0.11 / 0.88 | 0.10 / 0.88 |
| productcatalogservice | 0.49 / 0.66 | 0.47 / 0.68 | 0.57 / 0.66 | 0.57 / 0.66 |
| cartservice | 0.55 / 0.86 | 0.60 / 0.90 | 0.39 / 0.46 | 0.40 / 0.59 |
| currencyservice | 0.45 / 0.68 | 0.43 / 0.68 | 0.47 / 0.55 | 0.46 / 0.55 |
| shippingservice | 0.08 / 0.16 | 0.06 / 0.17 | 0.12 / 0.15 | 0.12 / 0.14 |
| adservice | 0.08 / 0.18 | 0.07 / 0.17 | 0.16 / 0.38 | 0.14 / 0.16 |
| redis-cart | 0.08 / 0.11 | 0.08 / 0.10 | 0.07 / 0.08 | 0.06 / 0.07 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run89 | run92 | run94 | run95 |
| --- | ---: | ---: | ---: | ---: |
| frontend | 0.378 | 0.368 | 0.367 | 0.367 |
| checkoutservice | 1.039 | 1.051 | 1.051 | 1.048 |
| recommendationservice | 1.015 | 1.016 | 0.763 | 0.800 |
| paymentservice | 0.800 | 0.865 | 0.948 | 0.794 |
| emailservice | 1.017 | 0.925 | 1.025 | 0.975 |
| productcatalogservice | 0.708 | 0.711 | 0.696 | 0.708 |
| cartservice | 0.921 | 0.932 | 0.522 | 0.615 |
| currencyservice | 0.805 | 0.757 | 0.613 | 0.597 |
| shippingservice | 0.203 | 0.209 | 0.188 | 0.195 |
| adservice | 0.323 | 0.214 | 0.921 | 0.189 |
| redis-cart | 0.126 | 0.117 | 0.080 | 0.080 |

## Per hold

**run89.** Checkout streak 58 and recommendations streak 238, both past a RetryGuard disable. Recommendations is detector-hot for 76.0% of the hold; checkout for 25.7%. Email has 23 overloaded ticks, which clears the leaf row, at 3.6% of the hold and a streak of 5. The retry storm is frontend → recommendationservice, 224,314, with 9,302 into checkout. Browse goodput is low (getproduct 68 req/s, fail 0.674, P95 1826 ms). Checkout sojourn is 231 ms, and 27.4% of its inbound requests sit above 500 ms. Recommendations sojourn is 437 ms, and 69.8% sit above 500 ms.

**run92.** The independent pair comes back: checkout streak 59, recommendations streak 454, recommendations overloaded 75.2%, frontend → recommendations retries 235,145. Email falls to 6 overloaded ticks and payment to 5, so the leaf row misses. Checkout sojourn is 262 ms, with 40.1% of requests above 500 ms. Browse goodput stays in the same band as run89 (getproduct 63 req/s, fail 0.700).

**run94.** The pair flips. Checkout streak is 564, the whole scored series, overloaded 92.8%, sojourn 491 ms, 95.5% of requests above 500 ms, reset fraction 0.477, frontend → checkout retries 61,002. Recommendations streak is 0, overloaded ticks are 0, retries are 0, sojourn is 96 ms. Email has 16 overloaded ticks and payment 10, both on the leaf side of the bar, at 2.5% and 1.6% of the hold. Browse traffic gets through: getproduct goodput 264 req/s, fail 0, P95 320 ms; getcart 96 req/s, fail 0, P95 336 ms. postcheckout goodput is 3.2 req/s with fail 0.923 and P95 2229 ms. Checkout arrival rises from about 36 req/s and 32 req/s on the first two holds to 131 req/s here, and recommendations arrival falls from about 610 req/s to 362 req/s.

**run95.** Fourth hold of the same mix, same Paper-C1 pin, frontend at 4 for all 133 resource samples. It repeats run94. Checkout streak is 568, the whole scored series, overloaded 93.1%, sojourn 491 ms, 96.1% of requests above 500 ms, reset fraction 0.479, frontend → checkout retries 61,643. Recommendations streak is 0, overloaded ticks are 0, retries are 0, sojourn is 82 ms. Email has 11 overloaded ticks (1.7% of the hold), which still clears the leaf row; payment has 0. Browse traffic gets through: getproduct goodput 263.9 req/s, fail 0, P95 302 ms; getcart 96.0 req/s, fail 0, P95 326 ms. postcheckout goodput is 2.8 req/s with fail 0.928 and P95 2206 ms. Checkout arrival is 132 req/s and recommendations arrival is 363 req/s.

## Where this leaves the mix

275 / 90 / 100 / 90 / 5 produced one blend (run89). run92 repeats the checkout + recommendations pair and loses the leaf. run94 and run95 both latch checkout for the whole hold and leave recommendations cold. Two holds in a row on this boot took that latch. The both-off YAML points at **run96** with these same counts. The cluster was left on the Paper-C1 pin. The three VMs were left running. Do not overwrite run89, run92, run94, or run95.
