# S1 both-off run7, Paper-C1, mix 175/35/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run7`.

The only change from run6 is postcheckout 35 instead of 30. A 360 s cool-off and the AGENTS.md §6 clear sequence ran between the two holds.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 74/74 samples, every other Boutique service 1 on 74/74.
- Locust `total.csv` has 287 rows. Mesh span is 392 s because the collector starts before Locust; 0 of 4312 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: 68 of 337 rows on each API. The other rows repeat leftover `rate_config` files (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Storefront goodput shows those leftover zeros were not enforced.

## Storefront

Means over 287 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.9 | 159.9 | 0 | 84 |
| postcheckout | 32.0 | 32.0 | 0 | 134 |
| getcart | 64.2 | 64.2 | 0 | 72 |
| postcart | 82.5 | 82.5 | 0 | 59 |
| emptycart | 4.7 | 4.7 | 0 | 12 |
| total | 343.2 | 343.2 | 0 | 72 |

| API | Run7 RPS | Run7 P95 ms | Run6 P95 ms | Run5 P95 ms | Run4 P95 ms |
|---|---:|---:|---:|---:|---:|
| getproduct | 159.9 | 84 | 88 | 79 | 105 |
| postcheckout | 32.0 | 134 | 155 | 189 | 657 |
| getcart | 64.2 | 72 | 77 | 50 | 93 |
| postcart | 82.5 | 59 | 59 | 59 | 60 |
| emptycart | 4.7 | 12 | 13 | 15 | 12 |
| total | 343.2 | 72 | 79 | 78 | 185 |

Run4 (postcheckout 50) is the only hold in this series with Locust failures. Run5, run6, and run7 have failure fraction 0. postcheckout goodput tracks the user count: 27.5 at 30, 32.0 at 35, 36.4 at 40, 44.6 at 50.

## CPU

Mean and max are kubelet app-container millicores from `resource_usage.csv` (74 samples). Frontend in the file is the sum of four pods (1051 / 1407 m); the row below divides that by 4. Detector max is cAdvisor CPU divided by the per-pod quota.

| Service | Limit (m) | Mean (m) | Max (m) | Detector max | Alpha | Overloaded | Run6 detector max |
|---|---:|---:|---:|---:|---:|---:|---:|
| frontend | 1150 | 263 | 352 | 0.332 | 0.80 | 0 / 337 | 0.303 |
| checkoutservice | 800 | 460 | 621 | 0.834 | 0.80 | 14 / 337 | 0.649 |
| emailservice | 120 | 52 | 69 | 0.750 | 0.80 | 0 / 337 | 0.667 |
| productcatalogservice | 800 | 375 | 495 | 0.652 | 0.95 | 0 / 337 | 0.623 |
| recommendationservice | 1150 | 424 | 575 | 0.538 | 0.80 | 0 / 337 | 0.523 |
| cartservice | 800 | 290 | 481 | 0.636 | 0.95 | 0 / 337 | 0.601 |
| currencyservice | 770 | 253 | 342 | 0.488 | 0.80 | 0 / 337 | 0.453 |
| paymentservice | 155 | 26 | 35 | 0.368 | 0.80 | 0 / 337 | 0.342 |
| adservice | 1150 | 108 | 141 | 0.138 | 0.80 | 0 / 337 | 0.316 |
| redis-cart | 540 | 36 | 51 | 0.209 | 0.80 | 0 / 337 | 0.185 |
| shippingservice | 770 | 69 | 94 | 0.143 | 0.80 | 0 / 337 | 0.131 |

Checkout is the only service over alpha. Its overloaded share is 14 / 337 (4.2%) and the longest streak is 2 ticks. Email peaks at 0.750, under 0.80. On run4 checkout was 33 / 336 (9.8%, streak 4) and email was 46 / 336 (13.7%, streak 3).

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. Every edge has retry delta 0. The cumulative `retry` column still shows 1,540 on frontend → checkoutservice and 3 on frontend → cartservice, unchanged since run4. There is no scored tick above 0.5.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled.

| Service | Streak / ticks > 0.20 |
|---|---:|
| frontend | 0 / 0 |
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

`grpc_4` and `grpc_14` deltas are 0. HTTP 5xx deltas are 0.

## (b) Detector overloaded share

`overloaded=1` ticks over 337 `topfull_detect.csv` rows. The S2 bar is a share of 0.5.

| Service | Overloaded | Share | Longest streak | Util max |
|---|---:|---:|---:|---:|
| frontend | 0 / 337 | 0.0% | 0 | 0.332 |
| checkoutservice | 14 / 337 | 4.2% | 2 | 0.834 |
| recommendationservice | 0 / 337 | 0.0% | 0 | 0.538 |
| paymentservice | 0 / 337 | 0.0% | 0 | 0.368 |
| emailservice | 0 / 337 | 0.0% | 0 | 0.750 |
| productcatalogservice | 0 / 337 | 0.0% | 0 | 0.652 |
| cartservice | 0 / 337 | 0.0% | 0 | 0.636 |
| currencyservice | 0 / 337 | 0.0% | 0 | 0.488 |
| shippingservice | 0 / 337 | 0.0% | 0 | 0.143 |
| adservice | 0 / 337 | 0.0% | 0 | 0.138 |
| redis-cart | 0 / 337 | 0.0% | 0 | 0.209 |

## (c) Retry volume and inbound resets

Outbound retry delta is 0 on every caller. HTTP 5xx is 0.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | 0 | 28 |
| checkoutservice | 0 | 1 |
| recommendationservice | 0 | 5 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 2 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 2 |
| shippingservice | 0 | 0 |
| adservice | 0 | 0 |
| redis-cart | 0 | 0 |

RetryGuard would not have shed an edge or disabled a callee. TopFull's detector flagged checkout for 14 ticks, longest streak 2, which is a brief crossing of alpha and not a sustained overload.
