# S1 both-off run6, Paper-C1, mix 175/30/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run6`.

The only change from run5 is postcheckout 30 instead of 40. The AGENTS.md §6 clear sequence ran before the launch.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 74/74 samples, every other Boutique service 1 on 74/74.
- Locust `total.csv` has 288 rows. Mesh span is 393 s because the collector starts before Locust; 0 of 4323 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: 68 of 337 rows on each API. The other rows repeat leftover `rate_config` files (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Storefront goodput shows those leftover zeros were not enforced.

## Storefront

Means over 288 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.9 | 159.9 | 0 | 88 |
| postcheckout | 27.5 | 27.5 | 0 | 155 |
| getcart | 64.2 | 64.2 | 0 | 77 |
| postcart | 82.5 | 82.5 | 0 | 59 |
| emptycart | 4.7 | 4.7 | 0 | 13 |
| total | 338.7 | 338.7 | 0 | 79 |

| API | Run6 RPS | Run6 P95 ms | Run5 RPS | Run5 P95 ms | Run4 P95 ms |
|---|---:|---:|---:|---:|---:|
| getproduct | 159.9 | 88 | 159.9 | 79 | 105 |
| postcheckout | 27.5 | 155 | 36.4 | 189 | 657 |
| getcart | 64.2 | 77 | 64.2 | 50 | 93 |
| postcart | 82.5 | 59 | 82.5 | 59 | 60 |
| emptycart | 4.7 | 13 | 4.7 | 15 | 12 |
| total | 338.7 | 79 | 347.7 | 78 | 185 |

Run4 (postcheckout 50) is the only one of the three with Locust failures. Run5 and run6 have failure fraction 0.

## CPU

Mean and max are kubelet app-container millicores from `resource_usage.csv` (74 samples). Frontend in the file is the sum of four pods (997 / 1338 m); the row below divides that by 4. Detector max is cAdvisor CPU divided by the per-pod quota.

| Service | Limit (m) | Mean (m) | Max (m) | Detector max | Alpha | Overloaded | Run5 detector max |
|---|---:|---:|---:|---:|---:|---:|---:|
| frontend | 1150 | 249 | 335 | 0.303 | 0.80 | 0 / 337 | 0.333 |
| checkoutservice | 800 | 328 | 444 | 0.649 | 0.80 | 0 / 337 | 0.781 |
| emailservice | 120 | 44 | 58 | 0.667 | 0.80 | 0 / 337 | 0.750 |
| productcatalogservice | 800 | 356 | 473 | 0.623 | 0.95 | 0 / 337 | 0.689 |
| recommendationservice | 1150 | 407 | 557 | 0.523 | 0.80 | 0 / 337 | 0.532 |
| cartservice | 800 | 270 | 458 | 0.601 | 0.95 | 0 / 337 | 0.524 |
| currencyservice | 770 | 234 | 323 | 0.453 | 0.80 | 0 / 337 | 0.509 |
| paymentservice | 155 | 22 | 31 | 0.342 | 0.80 | 0 / 337 | 0.439 |
| adservice | 1150 | 104 | 146 | 0.316 | 0.80 | 0 / 337 | 0.162 |
| redis-cart | 540 | 34 | 50 | 0.185 | 0.80 | 0 / 337 | 0.174 |
| shippingservice | 770 | 62 | 83 | 0.131 | 0.80 | 0 / 337 | 0.142 |

Checkout and email both stay under alpha 0.80. On run4 those peaks were 0.902 and 0.967.

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. Every edge has retry delta 0. The cumulative `retry` column still shows 1,540 on frontend → checkoutservice and 3 on frontend → cartservice, the same totals left by run4. There is no scored tick above 0.5.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled.

| Service | Streak / ticks > 0.20 |
|---|---:|
| frontend | 1 / 1 |
| checkoutservice | 0 / 0 |
| recommendationservice | 0 / 0 |
| paymentservice | 0 / 0 |
| emailservice | 0 / 0 |
| productcatalogservice | 0 / 0 |
| cartservice | 0 / 0 |
| currencyservice | 0 / 0 |
| shippingservice | 0 / 0 |
| adservice | 0 / 0 |
| redis-cart | 0 / 0 |

`grpc_4` and `grpc_14` deltas are 0. HTTP 5xx deltas are 0. The only inbound reset delta is frontend 10.

## (b) Detector overloaded share

`overloaded=1` ticks over 337 `topfull_detect.csv` rows. Every service is 0 / 337, share 0.0%, longest streak 0. Checkout util max is 0.649 and email util max is 0.667, both under alpha 0.80. Frontend util max is 0.303.

## (c) Retry volume and inbound resets

Outbound retry delta is 0 on every caller. HTTP 5xx is 0.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | 0 | 10 |
| checkoutservice | 0 | 0 |
| recommendationservice | 0 | 0 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 0 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

RetryGuard would not have shed an edge or disabled a callee. TopFull's detector never set `overloaded`.
