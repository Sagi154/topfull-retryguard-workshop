# S2 copy-verification hold, run85

Both controllers off, 600 s, on the disk copy in project `project-76deda76-55f1-42d2-abb`. Mix is the run84 replay of run80: getproduct / postcheckout / getcart / postcart / emptycart = **325 / 80 / 100 / 90 / 5**, `spawn_rate` 50. Istio `attempts: 3`, `perTryTimeout` 500 ms. Paper CPU reconcile ran at the start (`experiments/topfull_cpu_quotas.py`). Frontend HPA stayed min 1 / max 4. Sidecar request was the restored 100 m annotation, with no CPU limit. The three VMs are **TERMINATED** after the pull.

Folder: `experiments/results/copy verification/baseline_no_topfull_sustained_overload_run85`.

(a)/(b)/(c) below are from `experiments/s2_both_off_abc.py`. The lens-blend table used the canon scorer, which drops the last five inbound rows; those streaks differ by only a few samples (recommendations 426 here, 422 in the canon scorer).

## Hold index

| Slot | Where | Mix | Controllers | Locust rows | Mesh span | gap2 | Layer A admitting rows |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| run84 | `networks-workshop` | 325/80/100/90/5 | both off | 571 | 694 s | 0% | 0 |
| run85 | copied project | 325/80/100/90/5 | both off | 569 | 686 s | 0% | 0 |

Layer A `threshold` is only 0 or 10000 on both holds, and the last sample of every API is 10000. That is the passthrough sentinel: TopFull admission stayed off.

## Verdict

The copy ran a real both-off hold. Sampling, file set, and the off-switch match run84. The scorecard does not.

On the lens-blend bar (recommendations and checkout each need streak ≥ 10 and overloaded ticks ≥ 10, plus email or payment overloaded ticks ≥ 10):

| Slot | Recommendations | Checkout | Email / payment | Verdict |
| --- | --- | --- | --- | --- |
| run84 | streak 2, ov 540 | streak 0, ov 157 | email ov 29, payment ov 0 | miss |
| run85 | streak 426, ov 472 | streak 22, ov 133 | email ov 0, payment ov 5 | near-miss |

run85 clears recommendations and checkout. Payment's 5 overloaded ticks meet the near-miss leftover bar and miss the full bar of 10.

Frontend replicas are the concrete difference. run84 was at 4 for all 134 resource samples. run85 started at 1 and reached 3: 19 samples at 1, 43 at 2, 71 at 3. The HPA maximum is still 4. The recorded CPU limits also differ: run84's `service_capacity.json` has checkout / catalog / cart / email at 800 / 800 / 800 / 120, while run85 is the current paper table (615 / 1535 / 1920 / 155).

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart are outside that set.

| Service | run84 | run85 |
| --- | ---: | ---: |
| frontend (not controlled) | 64 / 495 | 425 / 472 |
| checkoutservice | 0 / 0 | 22 / 99 |
| recommendationservice | 2 / 43 | **426 / 479** |
| paymentservice | 0 / 0 | 2 / 10 |
| emailservice | 0 / 0 | 3 / 24 |
| productcatalogservice | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 |

## (b) Detector overloaded ticks

`overloaded=1` over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | run84 | run85 |
| --- | ---: | ---: |
| frontend | 0/640 (0.0%) | 6/635 (0.9%) |
| checkoutservice | 157/640 (24.5%) | 133/635 (20.9%) |
| recommendationservice | **540/640 (84.4%)** | **472/635 (74.3%)** |
| paymentservice | 0/640 (0.0%) | 5/635 (0.8%) |
| emailservice | 29/640 (4.5%) | 0/635 (0.0%) |
| productcatalogservice | 0/640 (0.0%) | 0/635 (0.0%) |
| cartservice | 0/640 (0.0%) | 0/635 (0.0%) |
| currencyservice | 0/640 (0.0%) | 0/635 (0.0%) |
| shippingservice | 0/640 (0.0%) | 0/635 (0.0%) |
| adservice | 0/640 (0.0%) | 0/635 (0.0%) |
| redis-cart | 0/640 (0.0%) | 0/635 (0.0%) |

## (c) Outbound retry delta

- **run84.** frontend → recommendationservice 149,129, frontend → checkoutservice 8.
- **run85.** frontend → recommendationservice 288,235, frontend → checkoutservice 5,993.

No caller other than frontend retried on either hold.

| Service | run84 | run85 |
| --- | ---: | ---: |
| frontend | 0 | 0 |
| checkoutservice | 8 | 5,993 |
| recommendationservice | 149,129 | 288,235 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 0 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

## Inbound failure fraction

Δ(5xx+resets) / Δtotal over the mesh span.

| Service | run84 | run85 |
| --- | ---: | ---: |
| frontend | 0.266 | 0.558 |
| checkoutservice | 0.000 | 0.357 |
| recommendationservice | 0.148 | 0.395 |
| paymentservice | 0.000 | 0.065 |
| emailservice | 0.000 | 0.045 |
| productcatalogservice | 0.000 | 0.000 |
| cartservice | 0.000 | 0.001 |
| currencyservice | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.009 |
| adservice | 0.000 | 0.000 |

## CPU limits recorded in `service_capacity.json`

Millicores, request equal to limit. Replica count in that file is the snapshot at write time, not the mode across the hold.

| Service | run84 limit | run84 replicas in file | run85 limit | run85 replicas in file |
| --- | ---: | ---: | ---: | ---: |
| frontend | 1150 | 4 | 1150 | 1 |
| checkoutservice | 800 | 1 | 615 | 1 |
| recommendationservice | 1150 | 1 | 1150 | 1 |
| productcatalogservice | 800 | 1 | 1535 | 1 |
| cartservice | 800 | 1 | 1920 | 1 |
| currencyservice | 770 | 1 | 770 | 1 |
| shippingservice | 770 | 1 | 770 | 1 |
| adservice | 1150 | 1 | 1150 | 1 |
| paymentservice | 155 | 1 | 155 | 1 |
| emailservice | 120 | 1 | 155 | 1 |
| redis-cart | 540 | 1 | 540 | 1 |

## CPU mean / max and replica mode

App-container millicores from `resource_usage.csv`, mean / max. Replica mode is the most common `replica_count` in that file.

| Service | run84 replicas | run84 CPU | run85 replicas | run85 CPU |
| --- | ---: | ---: | ---: | ---: |
| frontend | 4 | 1270 / 1591 | 3 | 716 / 957 |
| checkoutservice | 1 | 529 / 776 | 1 | 140 / 612 |
| recommendationservice | 1 | 848 / 1025 | 1 | 940 / 1153 |
| paymentservice | 1 | 36 / 56 | 1 | 19 / 124 |
| emailservice | 1 | 67 / 106 | 1 | 17 / 73 |
| productcatalogservice | 1 | 411 / 506 | 1 | 328 / 445 |
| cartservice | 1 | 369 / 539 | 1 | 404 / 549 |
| currencyservice | 1 | 362 / 435 | 1 | 252 / 359 |
| shippingservice | 1 | 74 / 106 | 1 | 23 / 89 |
| adservice | 1 | 114 / 170 | 1 | 77 / 419 |
| redis-cart | 1 | 40 / 46 | 1 | 36 / 44 |

Master node CPU mean / max: run84 3942 / 6115 m, run85 3731 / 5899 m, both on the 8-vCPU master.

## Locust

Mean while `RPS` > 0. `Fail / RPS` counts SLO misses, not only HTTP 5xx.

| API | run84 goodput | run85 goodput | run84 fail | run85 fail | run84 P95 ms | run85 P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 142.1 | 24.6 | 0.482 | 0.857 | 1932 | 2013 |
| postcheckout | 33.2 | 1.9 | 0.503 | 0.950 | 1909 | 2252 |
| getcart | 46.3 | 10.3 | 0.458 | 0.816 | 1777 | 1934 |
| postcart | 85.9 | 79.9 | 0.007 | 0.000 | 67 | 79 |
| emptycart | 4.8 | 4.8 | 0.018 | 0.000 | 18 | 21 |

postcart and emptycart stay on the fast path in both holds. Browse and checkout goodput fall on run85, with P95 still around 2 s.

## Inbound arrival and sojourn

Mean inbound requests/s (Δtotal / mesh span) and mean sojourn (Δ`rq_time_sum_ms` / Δ`rq_time_count`). redis-cart has no HTTP inbound counters.

| Service | run84 req/s | run85 req/s | run84 W ms | run85 W ms |
| --- | ---: | ---: | ---: | ---: |
| frontend | 453.6 | 312.3 | 677 | 1193 |
| checkoutservice | 38.4 | 15.5 | 95 | 415 |
| recommendationservice | 588.6 | 656.0 | 466 | 463 |
| paymentservice | 38.4 | 14.3 | 2 | 13 |
| emailservice | 38.4 | 3.9 | 12 | 6 |
| productcatalogservice | 1991.3 | 910.2 | 2 | 7 |
| cartservice | 471.7 | 300.7 | 3 | 3 |
| currencyservice | 682.8 | 389.9 | 2 | 5 |
| shippingservice | 127.6 | 40.4 | 1 | 2 |
| adservice | 163.7 | 44.6 | 1 | 5 |

Recommendations sojourn is the same (~460 ms) while its failure fraction rises from 0.15 to 0.40 and its retry edge roughly doubles. Checkout sojourn rises from 95 ms to 415 ms, still under the 500 ms `perTryTimeout`, with a failure fraction of 0.36 and a streak of 22. Frontend sojourn rises from 677 ms to 1193 ms.
