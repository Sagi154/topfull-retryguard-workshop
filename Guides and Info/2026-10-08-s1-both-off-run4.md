# S1 both-off run4, Paper-C1, mix 175/50/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run4`.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 73/73 samples, every other Boutique service 1 on 73/73.
- Locust `total.csv` has 287 rows. Mesh span is 390 s because the collector starts before Locust; 0 of 4290 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: every 5th second, on all five APIs. The other rows repeat leftover `rate_config` files from the previous TopFull-on holds (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Those leftover numbers were not enforced. postcheckout, postcart, and emptycart still show admitted RPS at the end of the hold (50, 90, and 5) on the rows whose file value is 0.

## Storefront

Means over 287 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 160.3 | 160.3 | 0 | 105 |
| postcheckout | 45.7 | 44.6 | 0.023 | 657 |
| getcart | 64.4 | 64.4 | 0 | 93 |
| postcart | 82.8 | 82.8 | 0 | 60 |
| emptycart | 4.7 | 4.7 | 0 | 12 |
| total | 357.8 | 356.8 | 0.003 | 185 |

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. A tick with no first attempts is skipped. The streak is consecutive scored ticks above 0.5. The shed bar is 30. Mean / max / volume.

| Edge | Streak / ticks > 0.5 | Mean | Max | Volume |
|---|---:|---:|---:|---:|
| frontend → checkoutservice | 0 / 0 | 0.100 | 0.489 | 0.108 |
| frontend → cartservice | 0 / 0 | 0.001 | 0.429 | 0.000 |

Every other edge has retry delta 0 and no tick above 0.5. Checkout volume is 1,540 retries on 14,317 first attempts.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. A tick with no new requests breaks the streak. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled.

| Service | Streak / ticks > 0.20 |
|---|---:|
| frontend | 1 / 1 |
| checkoutservice | 1 / 2 |
| recommendationservice | 0 / 0 |
| paymentservice | 0 / 0 |
| emailservice | 4 / 54 |
| productcatalogservice | 0 / 0 |
| cartservice | 1 / 1 |
| currencyservice | 0 / 0 |
| shippingservice | 0 / 0 |
| adservice | 0 / 0 |
| redis-cart | 0 / 0 |

Adding `grpc_4` and `grpc_14` does not change the four read callees: those deltas are 0. Checkout recorded `grpc_4` 865 and email 81. Those two services do not count gRPC in the rejection rate.

## (b) Detector overloaded share

`overloaded=1` ticks over 336 `topfull_detect.csv` rows. The bar used on the S2 tables is a share of 0.5. The streak is consecutive overloaded ticks.

| Service | Overloaded | Share | Longest streak |
|---|---:|---:|---:|
| frontend | 0 / 336 | 0.0% | 0 |
| checkoutservice | 33 / 336 | 9.8% | 4 |
| recommendationservice | 0 / 336 | 0.0% | 0 |
| paymentservice | 0 / 336 | 0.0% | 0 |
| emailservice | 46 / 336 | 13.7% | 3 |
| productcatalogservice | 0 / 336 | 0.0% | 0 |
| cartservice | 0 / 336 | 0.0% | 0 |
| currencyservice | 0 / 336 | 0.0% | 0 |
| shippingservice | 0 / 336 | 0.0% | 0 |
| adservice | 0 / 336 | 0.0% | 0 |
| redis-cart | 0 / 336 | 0.0% | 0 |

Checkout util max is 0.902 and email util max is 0.967, both against alpha 0.80. Frontend util max is 0.327.

## (c) Retry volume and inbound resets

Outbound retry delta is the sum of positive `retry` increments. Resets are `downstream_rq_rx_reset`. HTTP 5xx on the backends is 0. Frontend HTTP 5xx delta is 257.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | — | 37 |
| checkoutservice | 1,540 | 904 |
| recommendationservice | 0 | 0 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 1,645 |
| productcatalogservice | 0 | 4 |
| cartservice | 3 | 5 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

The 1,540 checkout retries and the 3 cart retries are both from frontend. `grpc_4 / grpc_14` is 0 / 0 on recommendations, catalog, currency, and ads.
