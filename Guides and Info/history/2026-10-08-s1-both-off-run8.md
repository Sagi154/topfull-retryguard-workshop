# S1 both-off run8, Paper-C1, mix 175/30/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run8`.

This is a replay of run6. The AGENTS.md §6 clear sequence ran before the launch.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 74/74 samples, every other Boutique service 1 on 74/74.
- Locust `total.csv` has 290 rows. Mesh span is 392 s because the collector starts before Locust; 0 of 4312 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: 68 of 337 rows on each API. The other rows repeat leftover `rate_config` files (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Storefront goodput shows those leftover zeros were not enforced.

## Storefront

Means over 290 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.7 | 159.7 | 0 | 69 |
| postcheckout | 27.4 | 27.4 | 0 | 169 |
| getcart | 64.1 | 64.1 | 0 | 49 |
| postcart | 82.4 | 82.4 | 0 | 58 |
| emptycart | 4.7 | 4.7 | 0 | 11 |
| total | 338.3 | 338.3 | 0 | 71 |

| API | Run8 RPS | Run8 P95 ms | Run6 RPS | Run6 P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.7 | 69 | 159.9 | 88 |
| postcheckout | 27.4 | 169 | 27.5 | 155 |
| getcart | 64.1 | 49 | 64.2 | 77 |
| postcart | 82.4 | 58 | 82.5 | 59 |
| emptycart | 4.7 | 11 | 4.7 | 13 |
| total | 338.3 | 71 | 338.7 | 79 |

Run6 and run8 both have failure fraction 0. postcheckout goodput is 27.4 against 27.5.

## CPU

Mean and max are kubelet app-container millicores from `resource_usage.csv` (74 samples). Frontend in the file is the sum of four pods (1076 / 1436 m); the row below divides that by 4. Detector max is cAdvisor CPU divided by the per-pod quota.

| Service | Limit (m) | Mean (m) | Max (m) | Detector max | Alpha | Overloaded | Run6 detector max |
|---|---:|---:|---:|---:|---:|---:|---:|
| frontend | 1150 | 269 | 359 | 0.335 | 0.80 | 0 / 337 | 0.303 |
| checkoutservice | 800 | 319 | 424 | 0.644 | 0.80 | 0 / 337 | 0.649 |
| emailservice | 120 | 43 | 56 | 0.667 | 0.80 | 0 / 337 | 0.667 |
| recommendationservice | 1150 | 408 | 557 | 0.520 | 0.80 | 0 / 337 | 0.523 |
| productcatalogservice | 800 | 405 | 533 | 0.688 | 0.95 | 0 / 337 | 0.623 |
| cartservice | 800 | 272 | 369 | 0.520 | 0.95 | 0 / 337 | 0.601 |
| currencyservice | 770 | 254 | 342 | 0.481 | 0.80 | 0 / 337 | 0.453 |
| paymentservice | 155 | 22 | 31 | 0.381 | 0.80 | 0 / 337 | 0.342 |
| redis-cart | 540 | 35 | 52 | 0.189 | 0.80 | 0 / 337 | 0.185 |
| adservice | 1150 | 103 | 135 | 0.163 | 0.80 | 0 / 337 | 0.316 |
| shippingservice | 770 | 61 | 81 | 0.136 | 0.80 | 0 / 337 | 0.131 |

Checkout and email both stay under alpha 0.80, matching run6 (0.649 and 0.667).

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. Every edge has retry delta 0. The cumulative `retry` column still shows 1,540 on frontend → checkoutservice and 3 on frontend → cartservice, unchanged since run4. There is no scored tick above 0.5.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled. Every service is 0 / 0. `grpc_4` and `grpc_14` deltas are 0. HTTP 5xx deltas are 0. Inbound reset deltas are frontend 8 and recommendationservice 1.

## (b) Detector overloaded share

`overloaded=1` ticks over 337 `topfull_detect.csv` rows. Every service is 0 / 337, share 0.0%, longest streak 0. Checkout util max is 0.644 and email util max is 0.667. Frontend util max is 0.335.

## (c) Retry volume and inbound resets

Outbound retry delta is 0 on every caller. HTTP 5xx is 0.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | 0 | 8 |
| checkoutservice | 0 | 0 |
| recommendationservice | 0 | 1 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 0 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

RetryGuard would not have shed an edge or disabled a callee. TopFull's detector never set `overloaded`.
