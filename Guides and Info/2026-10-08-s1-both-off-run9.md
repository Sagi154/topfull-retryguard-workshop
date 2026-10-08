# S1 both-off run9, Paper-C1, mix 175/25/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run9`.

The only change from run8 is postcheckout 25 instead of 30. A 360 s cool-off and the AGENTS.md §6 clear sequence ran between the two holds.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 74/74 samples, every other Boutique service 1 on 74/74.
- Locust `total.csv` has 287 rows. Mesh span is 393 s because the collector starts before Locust; 0 of 4323 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: 68 of 338 rows on each API. The other rows repeat leftover `rate_config` files (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Storefront goodput shows those leftover zeros were not enforced.

## Storefront

Means over 287 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.7 | 159.7 | 0 | 92 |
| postcheckout | 22.8 | 22.7 | 0.001 | 446 |
| getcart | 64.1 | 64.1 | 0 | 76 |
| postcart | 82.4 | 82.4 | 0 | 59 |
| emptycart | 4.6 | 4.6 | 0 | 14 |
| total | 333.7 | 333.6 | 0.000 | 137 |

| postcheckout users | Hold | Goodput | Fail fraction | P95 ms | Total P95 ms |
|---:|---|---:|---:|---:|---:|
| 50 | run4 | 44.6 | 0.023 | 657 | 185 |
| 40 | run5 | 36.4 | 0 | 189 | 78 |
| 35 | run7 | 32.0 | 0 | 134 | 72 |
| 30 | run6 | 27.5 | 0 | 155 | 79 |
| 30 | run8 | 27.4 | 0 | 169 | 71 |
| 25 | run9 | 22.7 | 0.001 | 446 | 137 |

postcheckout goodput still tracks the user count. The P95 at 25 users is higher than at 30, 35, and 40. The fail column averages 0.03 failures per second, about 9 failures over the hold.

## CPU

Mean and max are kubelet app-container millicores from `resource_usage.csv` (74 samples). Frontend in the file is the sum of four pods (1005 / 1353 m); the row below divides that by 4. Detector max is cAdvisor CPU divided by the per-pod quota.

| Service | Limit (m) | Mean (m) | Max (m) | Detector max | Alpha | Overloaded | Run8 detector max |
|---|---:|---:|---:|---:|---:|---:|---:|
| frontend | 1150 | 251 | 338 | 0.318 | 0.80 | 0 / 338 | 0.335 |
| checkoutservice | 800 | 210 | 309 | 0.571 | 0.80 | 0 / 338 | 0.644 |
| emailservice | 120 | 37 | 52 | 0.650 | 0.80 | 0 / 338 | 0.667 |
| recommendationservice | 1150 | 405 | 556 | 0.517 | 0.80 | 0 / 338 | 0.520 |
| productcatalogservice | 800 | 363 | 477 | 0.647 | 0.95 | 0 / 338 | 0.688 |
| currencyservice | 770 | 236 | 323 | 0.466 | 0.80 | 0 / 338 | 0.481 |
| cartservice | 800 | 249 | 336 | 0.456 | 0.95 | 0 / 338 | 0.520 |
| paymentservice | 155 | 17 | 24 | 0.290 | 0.80 | 0 / 338 | 0.381 |
| redis-cart | 540 | 32 | 48 | 0.183 | 0.80 | 0 / 338 | 0.189 |
| adservice | 1150 | 104 | 136 | 0.140 | 0.80 | 0 / 338 | 0.163 |
| shippingservice | 770 | 53 | 71 | 0.123 | 0.80 | 0 / 338 | 0.136 |

Checkout mean CPU fell from 319 m on run8 to 210 m. Its detector peak is 0.571, under alpha 0.80. Email peaks at 0.650.

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. A tick with no first attempts is skipped. The streak is consecutive scored ticks above 0.5. The shed bar is 30.

| Edge | Streak / ticks > 0.5 | Mean | Max | Volume |
|---|---:|---:|---:|---:|
| frontend → checkoutservice | 0 / 0 | 0.005 | 0.357 | 0.006 |

Every other edge has retry delta 0. The 45 new retries are on 7,175 first attempts. The cumulative checkout `retry` column moves from the run4 leftover of 1,540 to 1,585.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled.

| Service | Streak / ticks > 0.20 |
|---|---:|
| frontend | 0 / 0 |
| checkoutservice | 0 / 0 |
| recommendationservice | 0 / 0 |
| paymentservice | 0 / 0 |
| emailservice | 1 / 2 |
| productcatalogservice | 0 / 0 |
| cartservice | 0 / 0 |
| currencyservice | 0 / 0 |
| shippingservice | 0 / 0 |
| adservice | 0 / 0 |
| redis-cart | 0 / 0 |

HTTP 5xx delta is 10, all on frontend. `grpc_4` is 26 on checkoutservice and 3 on emailservice. `grpc_14` is 0.

## (b) Detector overloaded share

`overloaded=1` ticks over 338 `topfull_detect.csv` rows. Every service is 0 / 338, share 0.0%, longest streak 0. Checkout util max is 0.571 and email util max is 0.650. Frontend util max is 0.318.

## (c) Retry volume and inbound resets

Outbound retry delta is the sum of positive `retry` increments. Resets are `downstream_rq_rx_reset`.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | 45 | 10 |
| checkoutservice | 0 | 32 |
| recommendationservice | 0 | 2 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 59 |
| productcatalogservice | 0 | 0 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

The 45 retries are frontend → checkoutservice. RetryGuard would not have shed an edge or disabled a callee. TopFull's detector never set `overloaded`.
