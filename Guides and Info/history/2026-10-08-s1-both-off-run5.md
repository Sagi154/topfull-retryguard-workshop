# S1 both-off run5, Paper-C1, mix 175/40/70/90/5

300 s, RetryGuard off, TopFull RL off, `spawn_rate` 50. Counts are getproduct / postcheckout / getcart / postcart / emptycart. Paper-C1: frontend 1150 m × 4, every other service × 1, sidecar request 100 m, no `proxyCPULimit`. Folder: `experiments/results/campaign_48/S1_normal_op/baseline_no_topfull_normal_op_run5`.

The only change from run4 is postcheckout 40 instead of 50.

## Gate

Passed.

- `service_capacity.json` matches Paper-C1 (deployment total 11,655 m).
- `resource_usage.csv`: frontend `replica_count` 4 on 73/73 samples, every other Boutique service 1 on 73/73.
- Locust `total.csv` has 287 rows. Mesh span is 392 s because the collector starts before Locust; 0 of 4312 per-service inbound gaps are 1.5 s or longer.
- No `retryguard.log`. The runner logged TopFull RL off.
- Live Layer A polls are the 10000 passthrough: 67 of 337 rows on each API, every 5th second. The other rows repeat leftover `rate_config` files (getproduct 240, getcart 91, postcheckout / postcart / emptycart 0). Those leftover numbers were not enforced. postcheckout, postcart, and emptycart still show admitted RPS at the end of the hold (40, 90, and 5) on the rows whose file value is 0.

## Storefront

Means over 287 Locust rows. `Fail` in the CSV is failures per second. The fraction below is that column divided by RPS.

| API | RPS | Goodput | Fail fraction | P95 ms |
|---|---:|---:|---:|---:|
| getproduct | 159.9 | 159.9 | 0 | 79 |
| postcheckout | 36.4 | 36.4 | 0 | 189 |
| getcart | 64.2 | 64.2 | 0 | 50 |
| postcart | 82.5 | 82.5 | 0 | 59 |
| emptycart | 4.7 | 4.7 | 0 | 15 |
| total | 347.7 | 347.7 | 0 | 78 |

Run4 at postcheckout 50 had postcheckout P95 657 ms and a fail fraction of 0.023, and total P95 185 ms. This hold has no Locust failures.

| API | Run5 RPS | Run5 P95 ms | Run4 RPS | Run4 P95 ms | Run4 fail fraction |
|---|---:|---:|---:|---:|---:|
| getproduct | 159.9 | 79 | 160.3 | 105 | 0 |
| postcheckout | 36.4 | 189 | 45.7 | 657 | 0.023 |
| getcart | 64.2 | 50 | 64.4 | 93 | 0 |
| postcart | 82.5 | 59 | 82.8 | 60 | 0 |
| emptycart | 4.7 | 15 | 4.7 | 12 | 0 |
| total | 347.7 | 78 | 357.8 | 185 | 0.003 |

## CPU

Mean and max are kubelet app-container millicores from `resource_usage.csv` (73 samples). Frontend in the file is the sum of four pods (1080 / 1470 m); the row below divides that by 4. Detector max is cAdvisor CPU divided by the per-pod quota.

| Service | Limit (m) | Mean (m) | Max (m) | Detector max | Alpha | Overloaded | Run4 detector max |
|---|---:|---:|---:|---:|---:|---:|---:|
| frontend | 1150 | 270 | 368 | 0.333 | 0.80 | 0 / 337 | 0.327 |
| checkoutservice | 800 | 413 | 563 | 0.781 | 0.80 | 0 / 337 | 0.902 |
| emailservice | 120 | 55 | 74 | 0.750 | 0.80 | 0 / 337 | 0.967 |
| productcatalogservice | 800 | 407 | 538 | 0.689 | 0.95 | 0 / 337 | 0.660 |
| recommendationservice | 1150 | 417 | 589 | 0.532 | 0.80 | 0 / 337 | 0.576 |
| cartservice | 800 | 273 | 373 | 0.524 | 0.95 | 0 / 337 | 0.486 |
| currencyservice | 770 | 259 | 351 | 0.509 | 0.80 | 0 / 337 | 0.497 |
| paymentservice | 155 | 28 | 39 | 0.439 | 0.80 | 0 / 337 | 0.587 |
| adservice | 1150 | 105 | 147 | 0.162 | 0.80 | 0 / 337 | 0.593 |
| redis-cart | 540 | 35 | 52 | 0.174 | 0.80 | 0 / 337 | 0.172 |
| shippingservice | 770 | 69 | 92 | 0.142 | 0.80 | 0 / 337 | 0.153 |

Run4 overloaded 33 / 336 ticks on checkout and 46 / 336 on email. This hold has none.

## (a) Edge retries per request

`rpr = Δretry / (Δtotal − Δretry)`. A tick with no first attempts is skipped. The streak is consecutive scored ticks above 0.5. The shed bar is 30.

Every edge has retry delta 0. The cumulative `retry` column still shows 1,540 on frontend → checkoutservice and 3 on frontend → cartservice. Those are the run4 totals, unchanged through this hold, so there is no scored tick above 0.5.

## (a) Rejection streaks

`(Δ5xx + Δresets) / Δtotal`. A tick with no new requests breaks the streak. Longest run above 0.20, then the count of ticks above 0.20. A run of 30 on a controlled service is the disable bar. Frontend and redis-cart are not controlled.

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

`grpc_4` and `grpc_14` deltas are 0 on every service. HTTP 5xx deltas are 0. Inbound reset deltas are frontend 10, checkoutservice 1, productcatalogservice 4, and adservice 1.

## (b) Detector overloaded share

`overloaded=1` ticks over 337 `topfull_detect.csv` rows. The bar used on the S2 tables is a share of 0.5. The streak is consecutive overloaded ticks.

| Service | Overloaded | Share | Longest streak | Util max |
|---|---:|---:|---:|---:|
| frontend | 0 / 337 | 0.0% | 0 | 0.333 |
| checkoutservice | 0 / 337 | 0.0% | 0 | 0.781 |
| recommendationservice | 0 / 337 | 0.0% | 0 | 0.532 |
| paymentservice | 0 / 337 | 0.0% | 0 | 0.439 |
| emailservice | 0 / 337 | 0.0% | 0 | 0.750 |
| productcatalogservice | 0 / 337 | 0.0% | 0 | 0.689 |
| cartservice | 0 / 337 | 0.0% | 0 | 0.524 |
| currencyservice | 0 / 337 | 0.0% | 0 | 0.509 |
| shippingservice | 0 / 337 | 0.0% | 0 | 0.142 |
| adservice | 0 / 337 | 0.0% | 0 | 0.162 |
| redis-cart | 0 / 337 | 0.0% | 0 | 0.174 |

Checkout util max is 0.781 and email util max is 0.750, both under alpha 0.80. On run4 those peaks were 0.902 and 0.967, with overloaded shares 9.8% and 13.7%. Frontend util max is 0.333.

## (c) Retry volume and inbound resets

Outbound retry delta is 0 on every caller. Resets are `downstream_rq_rx_reset`. HTTP 5xx is 0.

| Service | Outbound retries | Inbound resets |
|---|---:|---:|
| frontend | 0 | 10 |
| checkoutservice | 0 | 1 |
| recommendationservice | 0 | 0 |
| paymentservice | 0 | 0 |
| emailservice | 0 | 0 |
| productcatalogservice | 0 | 4 |
| cartservice | 0 | 0 |
| currencyservice | 0 | 0 |
| shippingservice | 0 | 0 |
| adservice | 0 | 1 |
| redis-cart | 0 | 0 |

RetryGuard would not have shed an edge or disabled a callee. TopFull's detector never set `overloaded`.
