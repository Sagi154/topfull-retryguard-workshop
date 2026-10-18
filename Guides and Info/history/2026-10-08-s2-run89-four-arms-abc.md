# S2 run 89 mix, four arms, (a) / (b) / (c)

600 s holds, mix getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1, 360 s cool-off between holds. Two holds per arm. Folders are under `experiments/results/campaign_48/S2_sustained_overload/`. Storefront means for the same eight holds are in [2026-10-08-s2-run89-four-arms-replay.md](2026-10-08-s2-run89-four-arms-replay.md).

| Arm | Slots |
|---|---|
| RetryGuard off, TopFull off | 160, 161 |
| RetryGuard on, TopFull off | 20, 21 |
| RetryGuard off, TopFull on | 39, 40 |
| RetryGuard on, TopFull on | 24, 25 |

Columns below follow that order. A bold bar separates the arms.

Edge mode is the RetryGuard these holds run. The shed bar is `rpr > 0.5` for 30 consecutive samples (`retries_threshold` 0.5, `interval_samples` 30). `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A sample with no first attempts is skipped and does not move the counter. From 0 attempts, the 0→1 step needs the callee's inbound rejection, `(Δ5xx + Δresets) / Δtotal`, strictly under **0.10** for 30 samples. A climb from 1 to 2 needs `rpr ≤ 0.17` for 30 samples, and from 2 to 3 needs `rpr ≤ 0.33` for 30. Between the climb bar and 0.5 the attempt count holds. `rejection_threshold` 0.20 is not the edge-mode shed bar.

The file streak below is consecutive `service_edges.csv` rows. On a RetryGuard hold the parenthetical is the controller's own `high` counter from `retryguard.log`, which is the counter that has to reach 30. A slow sample can jump several collector rows and reset earlier than the file streak. **Bold** in (a) is a file streak of at least 30.

Only `frontend → checkoutservice` and `frontend → recommendationservice` have a tick with rpr above 0.5 or a retry delta. The other 12 controlled edges are at retry delta 0 with no tick above 0.5 on every hold.

## (a) Edge rpr, the shed bar

Longest streak of rpr > 0.5, then the number of scored ticks above 0.5. The parenthetical on runs 20, 21, 24, and 25 is the controller's max `high`.

| Edge | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 9 / 9 | 11 / 11 | **┃** | **32 / 118 (30)** | 16 / 16 (16) | **┃** | 4 / 4 | 5 / 101 | **┃** | 5 / 5 (5) | 0 / 0 |
| frontend → recommendationservice | **278 / 396** | **273 / 273** | **┃** | **31 / 93 (30)** | **31 / 31 (30)** | **┃** | **276 / 276** | 0 / 0 | **┃** | **31 / 59 (30)** | **91 / 91 (7)** |

Run 25's recommendations file streak is 91 and its controller `high` peaked at 7. At 01:40:09Z the log shows `rpr=0.0000` and the counter back at 0, so the shed did not fire.

Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.

| Edge | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.043 / 2.84 / 0.052 | 0.078 / 2.73 / 0.097 | **┃** | 0.485 / 2.73 / 0.504 | 0.121 / 2.65 / 0.101 | **┃** | 0.059 / 2.66 / 0.224 | 0.777 / 4.49 / 0.758 | **┃** | 0.034 / 2.98 / 0.036 | 0.000 / 0.16 / 0.011 |
| frontend → recommendationservice | 1.699 / 3.15 / 1.664 | 1.384 / 2.48 / 1.402 | **┃** | 0.349 / 2.53 / 0.288 | 0.181 / 2.56 / 0.121 | **┃** | 2.652 / 3.19 / 2.603 | 0.000 / 0.00 / 0.000 | **┃** | 0.482 / 3.09 / 0.292 | 0.551 / 3.30 / 0.949 |

Climb bars, counted only while that attempt cap is in force. The first number is the longest streak of `rpr ≤ 0.17` on controller samples where the edge is at 1 attempt. The second is the longest streak of `rpr ≤ 0.33` on samples where it is at 2 attempts. A sample above the bar ends the streak. An em dash means the edge never ran at that attempt count, so the bar was not in force. Samples are the `OBSERVE` lines in `retryguard.log`. Holds with RetryGuard off stay at 3 attempts for the whole run.

| Edge | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | 8 / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | — / — | — / — | **┃** | 11 / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

Run 20 is the only hold that reached 1 attempt. Checkout had 100 samples there and the longest `rpr ≤ 0.17` streak was 8. Recommendations had 80 samples at 1 attempt and the longest such streak was 11. No edge on any hold reached 2 attempts, so the `rpr ≤ 0.33` bar was never counted. Run 40's checkout volume rpr is 0.758 with 101 ticks above 0.5, and the shed streak is 5, so the 30-sample shed bar is missed even though the hold-level rate is above 0.5.

## Rejection streaks

These are not the edge-mode shed signal. The streak tables use `(Δ5xx + Δresets) / Δtotal` from `service_inbound.csv`. The controller adds `grpc_4` and `grpc_14` on top of that for the four read callees, and those two deltas are the table after the streaks.

Longest streak above 0.20, then the count of samples above 0.20. **Bold** is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 117 / 387 | 132 / 258 | **┃** | 32 / 97 | 96 / 258 | **┃** | 276 / 276 | 1 / 1 | **┃** | 93 / 237 | 90 / 108 |
| checkoutservice | 8 / 8 | 11 / 11 | **┃** | **45 / 157** | 16 / 17 | **┃** | 4 / 4 | 5 / 99 | **┃** | 5 / 5 | 0 / 0 |
| recommendationservice | 1 / 7 | 1 / 9 | **┃** | 4 / 29 | 1 / 4 | **┃** | 1 / 1 | 0 / 0 | **┃** | 2 / 9 | 2 / 8 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 3 / 4 | 7 / 7 | **┃** | 9 / 78 | 3 / 9 | **┃** | 1 / 2 | 2 / 29 | **┃** | 2 / 4 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak strictly under 0.10, then the count of samples under 0.10. A streak of 30 is the 0→1 bar, and the controller consults it only while an edge of that callee is at 0 attempts.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 30 / 30 | 39 / 39 | **┃** | 60 / 120 | 44 / 44 | **┃** | 31 / 31 | 37 / 264 | **┃** | 33 / 42 | 307 / 312 |
| checkoutservice | 277 / 405 | 271 / 299 | **┃** | 38 / 137 | 266 / 292 | **┃** | 21 / 135 | 15 / 196 | **┃** | 253 / 296 | 306 / 411 |
| recommendationservice | 30 / 30 | 39 / 39 | **┃** | 101 / 215 | 43 / 136 | **┃** | 30 / 32 | 307 / 307 | **┃** | 32 / 136 | 306 / 338 |
| paymentservice | 307 / 414 | 311 / 311 | **┃** | 253 / 304 | 270 / 310 | **┃** | 35 / 138 | 90 / 293 | **┃** | 254 / 302 | 306 / 412 |
| emailservice | 278 / 407 | 272 / 302 | **┃** | 38 / 173 | 245 / 296 | **┃** | 22 / 138 | 22 / 230 | **┃** | 252 / 296 | 306 / 411 |
| productcatalogservice | 308 / 426 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 | **┃** | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 306 / 434 |
| cartservice | 308 / 426 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 | **┃** | 306 / 306 | 307 / 307 | **┃** | 306 / 306 | 306 / 434 |
| currencyservice | 308 / 426 | 312 / 312 | **┃** | 313 / 313 | 312 / 312 | **┃** | 307 / 307 | 307 / 307 | **┃** | 306 / 306 | 306 / 434 |
| shippingservice | 308 / 422 | 312 / 312 | **┃** | 312 / 312 | 312 / 312 | **┃** | 35 / 196 | 307 / 307 | **┃** | 256 / 305 | 306 / 424 |
| adservice | 307 / 421 | 311 / 311 | **┃** | 312 / 312 | 310 / 310 | **┃** | 34 / 224 | 306 / 306 | **┃** | 306 / 306 | 306 / 428 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

On the recommendations storms the reset rate stays under 0.10 for 30–39 samples in total (160 is 30/30, 161 is 39/39, 39 is 30/32). That is one window at the re-enable bar. Run 20's longer quiet streak (101) is the OFF windows, and that hold did re-enable recommendations twice at rejection 0.00.

### gRPC counted in the rejection rate

`adservice`, `currencyservice`, `productcatalogservice`, and `recommendationservice` add `grpc_4` (deadline-exceeded) and `grpc_14` (unavailable) to the rejection numerator. Checkout, payment, email, cart, and shipping stay on 5xx + resets, so their gRPC columns are not in this rate. `grpc_2` and `grpc_13` are not in the numerator for any service.

Cell is `grpc_4 / grpc_14`, the positive increments over the hold.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 465,623 / 0 | 253,735 / 0 | **┃** | 86,231 / 0 | 80,741 / 0 | **┃** | 401,586 / 0 | 0 / 0 | **┃** | 109,142 / 0 | 218,840 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 0 | 0 / 0 |

## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

Ending Layer A caps are in the last section. Runs 160, 161, 20, and 21 stay at the 10000 passthrough.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| checkoutservice | 55/798 (6.9%) | 84/639 (13.1%) | **┃** | **421/665 (63.3%)** | **506/667 (75.9%)** | **┃** | 30/639 (4.7%) | **392/639 (61.3%)** | **┃** | 274/668 (41.0%) | **658/822 (80.0%)** |
| recommendationservice | **726/798 (91.0%)** | **545/639 (85.3%)** | **┃** | 198/665 (29.8%) | 169/667 (25.3%) | **┃** | **551/639 (86.2%)** | 0/639 (0.0%) | **┃** | 219/668 (32.8%) | 126/822 (15.3%) |
| paymentservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 2/639 (0.3%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| emailservice | 20/798 (2.5%) | 29/639 (4.5%) | **┃** | 136/665 (20.5%) | 228/667 (34.2%) | **┃** | 12/639 (1.9%) | 116/639 (18.2%) | **┃** | 46/668 (6.9%) | 21/822 (2.6%) |
| productcatalogservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| cartservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| currencyservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| shippingservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| adservice | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |
| redis-cart | 0/798 (0.0%) | 0/639 (0.0%) | **┃** | 0/665 (0.0%) | 0/667 (0.0%) | **┃** | 0/639 (0.0%) | 0/639 (0.0%) | **┃** | 0/668 (0.0%) | 0/822 (0.0%) |

## (c) Retry volume and gRPC errors

Outbound retry delta, the sum of positive `retry` increments on `service_edges.csv`. Every other target is 0.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 1,480 | 2,090 | **┃** | 18,388 | 3,157 | **┃** | 593 | 17,877 | **┃** | 737 | 286 |
| recommendationservice | 459,907 | 257,454 | **┃** | 72,892 | 31,496 | **┃** | 347,746 | 0 | **┃** | 66,302 | 201,165 |

Inbound resets (`downstream_rq_rx_reset`). This is the failure the rejection rate counts. HTTP 5xx on these backends is 0. Frontend's own HTTP 5xx delta is 121,731 / 64,248 / 61,415 / 85,534 / 114,528 / 6,887 / 81,149 / 69,114 on the eight slots in order; that is the storefront, and it is not a controlled callee.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1,289 | 428 | **┃** | 144 | 267 | **┃** | 452 | 102 | **┃** | 241 | 909 |
| checkoutservice | 991 | 1,471 | **┃** | 20,791 | 2,189 | **┃** | 410 | 11,957 | **┃** | 527 | 175 |
| recommendationservice | 114,375 | 66,730 | **┃** | 27,635 | 32,695 | **┃** | 60,684 | 3 | **┃** | 35,808 | 50,317 |
| paymentservice | 56 | 93 | **┃** | 1,506 | 135 | **┃** | 15 | 1,237 | **┃** | 30 | 10 |
| emailservice | 106 | 59 | **┃** | 1,679 | 124 | **┃** | 40 | 618 | **┃** | 57 | 40 |
| productcatalogservice | 4 | 5 | **┃** | 4 | 9 | **┃** | 1 | 6 | **┃** | 4 | 0 |
| cartservice | 77 | 110 | **┃** | 1,091 | 151 | **┃** | 27 | 506 | **┃** | 29 | 17 |
| currencyservice | 1 | 2 | **┃** | 0 | 3 | **┃** | 0 | 1 | **┃** | 0 | 1 |
| shippingservice | 75 | 131 | **┃** | 1,639 | 171 | **┃** | 27 | 1,022 | **┃** | 36 | 16 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

### gRPC counted in the retry policy

The same four callees retry `deadline-exceeded` and `unavailable` as well as `5xx,reset,connect-failure`. Those tokens are `grpc_4` and `grpc_14`. Checkout, payment, email, cart, and shipping retry `5xx,reset,connect-failure` only, so their gRPC columns are not a retry input. Cell is `grpc_4 / grpc_14`.

| Service | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 465,623 / 0 | 253,735 / 0 | **┃** | 86,231 / 0 | 80,741 / 0 | **┃** | 401,586 / 0 | 0 / 0 | **┃** | 109,142 / 0 | 218,840 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 0 | 0 / 0 |

## RetryGuard toggles

`ON→OFF` is the shed to 0 attempts. `OFF→ON` is the 0→1 step (the log's `attempts=1`, `from_attempts=0`). `1→2` and `2→3` would be the climb lines. Those two lines are absent on all four RetryGuard holds. Runs 160, 161, 39, and 40 have no `retryguard.log`.

| Slot | Edge | ON→OFF | 0→1 | 1→2 | 2→3 |
|---|---|---:|---:|---:|---:|
| 20 | frontend → checkoutservice | 3 | 3 | 0 | 0 |
| 20 | frontend → recommendationservice | 3 | 2 | 0 | 0 |
| 21 | frontend → recommendationservice | 1 | 0 | 0 | 0 |
| 24 | frontend → recommendationservice | 1 | 0 | 0 | 0 |
| 25 | — | 0 | 0 | 0 | 0 |

Run 20, each 0→1 at rejection 0.00. Checkout shed from 3 once, then from 1 twice, and the last 0→1 left it at 1 attempt. Recommendations shed from 3 once and from 1 twice; the last shed stayed at 0.

| Time (UTC) | Edge | Step | From | Value |
|---|---|---|---:|---|
| 2026-10-07T23:33:49Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.22 |
| 2026-10-07T23:36:14Z | checkoutservice | 0→1 | 0 | rejection 0.00 |
| 2026-10-07T23:36:14Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.48 |
| 2026-10-07T23:37:28Z | recommendationservice | 0→1 | 0 | rejection 0.00 |
| 2026-10-07T23:37:30Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.91 |
| 2026-10-07T23:38:46Z | checkoutservice | 0→1 | 0 | rejection 0.00 |
| 2026-10-07T23:38:46Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.72 |
| 2026-10-07T23:40:01Z | recommendationservice | 0→1 | 0 | rejection 0.00 |
| 2026-10-07T23:40:01Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.90 |
| 2026-10-07T23:41:22Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.67 |
| 2026-10-07T23:41:24Z | checkoutservice | 0→1 | 0 | rejection 0.00 |

Run 21: `frontend → recommendationservice` ON→OFF at 2026-10-07T23:57:32Z, rpr 1.25, from 3 attempts. No 0→1 after that. Checkout's controller `high` peaked at 16.

Run 24: `frontend → recommendationservice` ON→OFF at 2026-10-08T01:09:08Z, rpr 2.40, from 3 attempts. No 0→1 after that. Checkout's controller `high` peaked at 5.

Run 25: no shed. Recommendations `high` peaked at 7.

## Per arm

Runs 160 and 161 are the recommendations storm with both controllers off. Recommendations rpr stays above 0.5 for the whole scored series (streaks 278 and 273, volume 1.66 and 1.40), retries are 459,907 and 257,454, and `grpc_4` is 465,623 and 253,735 against reset streaks of 1. The detector is hot on recommendations (91% and 85%). Checkout's shed streak is 9 and 11.

Runs 20 and 21 have RetryGuard on. Run 20 sheds both edges and returns them only as far as 1 attempt; recommendations retries fall to 72,892 and `grpc_4` to 86,231. Run 21 sheds recommendations once, from 3, and leaves it at 0. Checkout on run 21 reaches controller `high` 16.

Runs 39 and 40 have TopFull on and RetryGuard off. Run 39 repeats the recommendations storm (streak 276, retries 347,746, `grpc_4` 401,586) while postcheckout's Layer A threshold ends at 36.5. Run 40 is the other regime: recommendations retries and `grpc_4` are 0, checkout volume rpr is 0.758 with a shed streak of 5, and checkout is detector-hot (61%).

Runs 24 and 25 have both on. Run 24 sheds recommendations once from 3 and leaves it off (retries 66,302). Run 25 does not shed. Its recommendations file streak is 91, the controller `high` stops at 7, retries are 201,165, and `grpc_4` is 218,840. Checkout is detector-hot at 80% with volume rpr 0.011.

## CPU mean / max

App-container millicores, mean / max, from `resource_usage.csv`. Quota is the per-pod CPU limit. The mean / max cells sum usage across replicas, so frontend can sit above its 1150 m pod limit.

| Service | Quota | Replicas | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 | 4 | 1103 / 1531 | 1054 / 1513 | **┃** | 1252 / 1613 | 1273 / 1578 | **┃** | 790 / 1602 | 1330 / 1578 | **┃** | 1223 / 1629 | 1103 / 1586 |
| checkoutservice | 800 | 1 | 424 / 795 | 469 / 798 | **┃** | 588 / 799 | 599 / 794 | **┃** | 71 / 786 | 565 / 797 | **┃** | 472 / 786 | 597 / 783 |
| recommendationservice | 1150 | 1 | 1007 / 1152 | 884 / 1116 | **┃** | 775 / 1124 | 761 / 1118 | **┃** | 977 / 1151 | 637 / 833 | **┃** | 778 / 1151 | 563 / 1151 |
| paymentservice | 155 | 1 | 29 / 83 | 33 / 95 | **┃** | 51 / 85 | 44 / 82 | **┃** | 8 / 68 | 47 / 77 | **┃** | 33 / 69 | 35 / 55 |
| emailservice | 120 | 1 | 55 / 95 | 59 / 112 | **┃** | 50 / 113 | 75 / 110 | **┃** | 15 / 103 | 52 / 99 | **┃** | 60 / 110 | 64 / 100 |
| productcatalogservice | 800 | 1 | 381 / 471 | 357 / 473 | **┃** | 401 / 519 | 381 / 476 | **┃** | 288 / 500 | 457 / 538 | **┃** | 370 / 500 | 411 / 465 |
| cartservice | 800 | 1 | 345 / 386 | 335 / 502 | **┃** | 316 / 478 | 341 / 497 | **┃** | 315 / 484 | 316 / 423 | **┃** | 330 / 422 | 334 / 416 |
| currencyservice | 770 | 1 | 305 / 423 | 291 / 419 | **┃** | 340 / 444 | 352 / 447 | **┃** | 225 / 413 | 338 / 415 | **┃** | 343 / 463 | 271 / 455 |
| shippingservice | 770 | 1 | 57 / 107 | 62 / 110 | **┃** | 85 / 132 | 82 / 111 | **┃** | 14 / 110 | 79 / 106 | **┃** | 73 / 114 | 69 / 120 |
| adservice | 1150 | 1 | 86 / 167 | 91 / 169 | **┃** | 126 / 186 | 116 / 170 | **┃** | 46 / 179 | 149 / 179 | **┃** | 111 / 183 | 102 / 167 |
| redis-cart | 540 | 1 | 43 / 52 | 40 / 51 | **┃** | 37 / 53 | 40 / 54 | **┃** | 39 / 50 | 40 / 53 | **┃** | 41 / 58 | 44 / 56 |

## TopFull cap

Ending Layer A `threshold` from `topfull_throttle.csv`, per Locust API. 10000 is the passthrough. A parenthetical is how many rows on that API sat below 10000. Runs 160, 161, 20, and 21 have no such rows.

| API | 160 | 161 | **┃** | 20 | 21 | **┃** | 39 | 40 | **┃** | 24 | 25 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 10000 (550) | 218.7 (537) | **┃** | 10000 (58) | 97.0 (619) |
| postcheckout | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 36.5 (590) | 50.7 (625) | **┃** | 54.5 (591) | 33.0 (774) |
| getcart | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 76.8 (549) | 73.7 (537) | **┃** | 10000 (66) | 36.0 (619) |
| postcart | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 10000 | 10000 |
| emptycart | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 10000 | 10000 | **┃** | 10000 | 10000 |
