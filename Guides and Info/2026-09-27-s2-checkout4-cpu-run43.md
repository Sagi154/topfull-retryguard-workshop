# S2 both-off run43, all services

600 s hold, both controllers off, `spawn_rate` 50. Checkout-4 CPU table, replicas pinned at the table counts: frontend 4, checkoutservice 4, recommendationservice 2, and productcatalogservice, cartservice, currencyservice, shippingservice, adservice, paymentservice, emailservice, and redis-cart at 1. Sidecar request 100 m with no CPU limit. 360 s cool-off before the hold. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). The CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every number below is from `experiments/s2_both_off_abc.py` on this folder, plus the same Locust, inbound, CPU, and detector reads as [2026-09-27-s2-checkout3-cpu-runs-39-42.md](2026-09-27-s2-checkout3-cpu-runs-39-42.md).

The hold failed the replica-count gate. `resource_usage.csv` has 134 samples per service. emailservice was 1 on 132 of them and 0 on two polls (`2026-09-27T20:00:20Z` and `2026-09-27T20:07:30Z`), each with `cpu_millicores` 0 and the neighboring samples at 1 replica. Every other service stayed at its pin on every sample. Locust `total.csv` has 560 rows. Runs 44 and 45 were not launched. This mix has no earlier both-off hold.

| Mix | This series |
|---|---|
| new (200/250/200/50/50) | run43 |

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain.

| Service | run43 |
| --- | --- |
| frontend (not controlled) | 2 / 2 |
| checkoutservice | **147 / 424** |
| recommendationservice | 1 / 1 |
| paymentservice | 2 / 2 |
| emailservice | **147 / 427** |
| productcatalogservice | 0 / 0 |
| cartservice | 1 / 1 |
| currencyservice | 1 / 1 |
| shippingservice | 0 / 0 |
| adservice | 1 / 2 |
| redis-cart (not controlled) | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5. Layer A admitting rows are 0.

| Service | run43 |
| --- | --- |
| frontend | 0/638 (0.0%) |
| checkoutservice | **481/638 (75.4%)** |
| recommendationservice | 0/638 (0.0%) |
| paymentservice | **509/638 (79.8%)** |
| emailservice | **566/638 (88.7%)** |
| productcatalogservice | 0/638 (0.0%) |
| cartservice | 0/638 (0.0%) |
| currencyservice | 0/638 (0.0%) |
| shippingservice | 0/638 (0.0%) |
| adservice | 6/638 (0.9%) |
| redis-cart | 0/638 (0.0%) |

## (c) Outbound retry delta

Edges with a positive retry delta, largest first. The table is retry by target, the scorer's retry column: the sum of positive Envoy `retry` increments into that service.

- **run43.** frontend → checkoutservice 82,368, checkoutservice → emailservice 2,652, frontend → recommendationservice 141, frontend → cartservice 6.

| Service | run43 |
| --- | ---: |
| frontend | 0 |
| checkoutservice | 82,368 |
| recommendationservice | 141 |
| paymentservice | 0 |
| emailservice | 2,652 |
| productcatalogservice | 0 |
| cartservice | 6 |
| currencyservice | 0 |
| shippingservice | 0 |
| adservice | 0 |
| redis-cart | 0 |

## CPU mean / max

App-container millicores, mean / max, from `cpu_mean_max`. Quota is the per-pod CPU limit. The mean / max cells sum that usage across the pinned replicas.

| Service | Quota | Replicas | run43 |
|---|---:|---:|---|
| frontend | 1150 | 4 | 926 / 1226 |
| checkoutservice | 800 | 4 | 2343 / 2809 |
| recommendationservice | 800 | 2 | 606 / 806 |
| paymentservice | 200 | 1 | 158 / 192 |
| emailservice | 200 | 1 | 156 / 201 |
| productcatalogservice | 600 | 1 | 269 / 362 |
| cartservice | 600 | 1 | 253 / 304 |
| currencyservice | 650 | 1 | 345 / 407 |
| shippingservice | 400 | 1 | 180 / 215 |
| adservice | 600 | 1 | 102 / 288 |
| redis-cart | 300 | 1 | 29 / 34 |

## Locust goodput

Mean `Goodput` (req/s) while `RPS` > 0.

| API | run43 |
| --- | ---: |
| getproduct | 142.8 |
| postcheckout | 40.9 |
| getcart | 143.8 |
| postcart | 36.9 |
| emptycart | 36.9 |

## Locust fail rate

Mean `Fail / RPS` while `RPS` > 0. `Fail` is a 1 s SLO miss or a non-OK status.

| API | run43 |
| --- | ---: |
| getproduct | 0.005 |
| postcheckout | 0.696 |
| getcart | 0.000 |
| postcart | 0.000 |
| emptycart | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS` > 0.

| API | run43 |
| --- | ---: |
| getproduct | 764 |
| postcheckout | 2281 |
| getcart | 632 |
| postcart | 167 |
| emptycart | 103 |

## Inbound arrival rate

Mean inbound requests/s, Δtotal over elapsed time, from `service_inbound.csv`. redis-cart has no HTTP inbound counters.

| Service | run43 |
| --- | ---: |
| frontend | 424.2 |
| checkoutservice | 224.9 |
| recommendationservice | 359.2 |
| paymentservice | 224.9 |
| emailservice | 219.3 |
| productcatalogservice | 2311.4 |
| cartservice | 766.6 |
| currencyservice | 798.0 |
| shippingservice | 575.6 |
| adservice | 126.0 |
| redis-cart | 0.0 |

## Inbound 5xx fraction

Hold Δ5xx / Δtotal from `service_inbound.csv`.

| Service | run43 |
| --- | ---: |
| frontend | 0.090 |
| checkoutservice | 0.000 |
| recommendationservice | 0.000 |
| paymentservice | 0.000 |
| emailservice | 0.000 |
| productcatalogservice | 0.000 |
| cartservice | 0.000 |
| currencyservice | 0.000 |
| shippingservice | 0.000 |
| adservice | 0.000 |
| redis-cart | n/a |

## Inbound reset fraction

Hold Δresets / Δtotal from `service_inbound.csv`.

| Service | run43 |
| --- | ---: |
| frontend | 0.002 |
| checkoutservice | 0.372 |
| recommendationservice | 0.001 |
| paymentservice | 0.002 |
| emailservice | 0.628 |
| productcatalogservice | 0.000 |
| cartservice | 0.000 |
| currencyservice | 0.000 |
| shippingservice | 0.000 |
| adservice | 0.001 |
| redis-cart | n/a |

## Inbound sojourn

Hold mean inbound sojourn (ms), Δrq_time_sum_ms / Δrq_time_count.

| Service | run43 |
| --- | ---: |
| frontend | 655 |
| checkoutservice | 440 |
| recommendationservice | 145 |
| paymentservice | 15 |
| emailservice | 286 |
| productcatalogservice | 13 |
| cartservice | 16 |
| currencyservice | 13 |
| shippingservice | 3 |
| adservice | 4 |
| redis-cart | n/a |

## Share of inbound requests above 500 ms

Share of inbound requests with sojourn above 500 ms, from `rq_time_buckets`.

| Service | run43 |
| --- | ---: |
| frontend | 0.585 |
| checkoutservice | 0.641 |
| recommendationservice | 0.000 |
| paymentservice | 0.000 |
| emailservice | 0.000 |
| productcatalogservice | 0.000 |
| cartservice | 0.000 |
| currencyservice | 0.000 |
| shippingservice | 0.000 |
| adservice | 0.000 |
| redis-cart | n/a |

## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. `quota` is the per-pod limit in `topfull_detect.csv`. `cpu_millicores` and `replica_count` are from `resource_usage.csv`. Samples with `replica_count` 0 are left out of this ratio.

| Service | run43 |
| --- | ---: |
| frontend | 0.20 / 0.27 |
| checkoutservice | 0.73 / 0.88 |
| recommendationservice | 0.38 / 0.50 |
| paymentservice | 0.79 / 0.96 |
| emailservice | 0.79 / 1.00 |
| productcatalogservice | 0.45 / 0.60 |
| cartservice | 0.42 / 0.51 |
| currencyservice | 0.53 / 0.63 |
| shippingservice | 0.45 / 0.54 |
| adservice | 0.17 / 0.48 |
| redis-cart | 0.10 / 0.11 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | run43 |
| --- | ---: |
| frontend | 0.277 |
| checkoutservice | 0.916 |
| recommendationservice | 0.586 |
| paymentservice | 1.030 |
| emailservice | 1.055 |
| productcatalogservice | 0.678 |
| cartservice | 0.560 |
| currencyservice | 0.698 |
| shippingservice | 0.615 |
| adservice | 1.000 |
| redis-cart | 0.123 |

## Per mix

**200/250/200/50/50.** run43 clears streak 30 on 2 controlled services (checkoutservice, emailservice) and an overloaded share of 0.5 on 3 (checkoutservice, paymentservice, emailservice).

## Related

- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Checkout-4 CPU table: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- Checkout-3 series this table follows: [2026-09-27-s2-checkout3-cpu-runs-39-42.md](2026-09-27-s2-checkout3-cpu-runs-39-42.md).
