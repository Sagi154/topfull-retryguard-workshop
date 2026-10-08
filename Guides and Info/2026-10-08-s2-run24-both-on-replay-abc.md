# S2 run 24 setup, both-on replay, (a) / (b) / (c)

600 s holds, mix getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1, RetryGuard on and TopFull on. Runs 24 and 25 are the existing pair. Runs 26 and 27 are two more holds of that setup, with a 360 s cool-off between them. Runs 28 and 29 are the same setup after `interval_samples` became seconds of row timestamps, again with a 360 s cool-off. Folders are under `experiments/results/campaign_48/S2_sustained_overload/`. Columns for 24 and 25 are copied from [2026-10-08-s2-run89-four-arms-abc.md](2026-10-08-s2-run89-four-arms-abc.md). A bold bar separates that pair from the later holds.


| Arm                                  | Slots  |
| ------------------------------------ | ------ |
| RetryGuard on, TopFull on (existing) | 24, 25 |
| RetryGuard on, TopFull on (replay)   | 26, 27 |
| RetryGuard on, TopFull on (30 s bar) | 28, 29 |


Edge mode is the RetryGuard these holds run. The shed bar is `rpr > 0.5` (`retries_threshold` 0.5). On runs 24–27 the interval is 30 consecutive samples. On runs 28 and 29 the interval is 30 seconds of row timestamps: the streak opens on the first row past the bar and fires when `elapsed_s` reaches 30. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A sample with no first attempts is skipped and does not move the counter. From 0 attempts, the 0→1 step needs the callee's inbound rejection, `(Δ5xx + Δresets) / Δtotal`, strictly under **0.10** for that same interval. A climb from 1 to 2 needs `rpr ≤ 0.17`, and from 2 to 3 needs `rpr ≤ 0.33`. Between the climb bar and 0.5 the attempt count holds. `rejection_threshold` 0.20 is not the edge-mode shed bar.

The file streak below is seconds from the first consecutive `service_edges.csv` row with rpr > 0.5 to the last. Each row already covers the time since the previous row, so a gap between two high rows stays inside the streak. A single row is 0 seconds. The parenthetical is the controller's own `high` counter from `retryguard.log`, still a row count. On runs 24–27 that counter has to reach 30. On runs 28 and 29 the shed fires at `elapsed_s` of 30, about 16 rows. **Bold** in (a) is a file streak of at least 30 seconds.

Only `frontend → checkoutservice` and `frontend → recommendationservice` have a tick with rpr above 0.5 or a retry delta. The other 12 controlled edges are at retry delta 0 with no tick above 0.5 on every hold.

Runs 26 and 27 passed the gate: `total.csv` at least 500 lines (766 and 561), frontend at 4 on every resource sample, every other service at 1, and no zero replica count. Run 26's mesh file spans 1068 s, the same pre-Locust collector lead-in as run 25 (1052 s). Run 27 spans 722 s. Runs 28 and 29 passed the same gate (`total.csv` 559 and 560 lines, frontend 4 on 139 and 140 samples, no zero replica count). Both mesh files span 722 s. Every shed and climb on those two holds has `elapsed_s=30`.

## (a) Edge rpr, the shed bar

Longest streak in seconds of rpr > 0.5, then the number of scored ticks above 0.5. The parenthetical is the controller's max `high`.


| Edge                             | 24              | 25               | **┃** | 26               | 27               | **┃** | 28               | 29               |
| -------------------------------- | --------------- | ---------------- | ----- | ---------------- | ---------------- | ----- | ---------------- | ---------------- |
| frontend → checkoutservice       | 8 / 5 (5)       | 0 / 0            | **┃** | **60 / 67 (30)** | 6 / 4 (4)        | **┃** | 10 / 15 (6)      | 0 / 1 (1)        |
| frontend → recommendationservice | **60 / 59 (30)** | **352 / 91 (7)** | **┃** | **60 / 31 (0)**  | **60 / 31 (30)** | **┃** | **32 / 17 (16)** | **32 / 32 (16)** |


Run 25's recommendations file streak is 352 s (01:34:06Z to 01:39:58Z) and its controller `high` peaked at 7. That span includes one 175 s scrape gap, 01:35:22Z to 01:38:17Z, and the row that closes the gap is still rpr 2.45. Run 26's recommendations file streak is 60 s, from 09:04:47Z to 09:05:47Z. The controller loop starts at 09:10:33Z and every scored sample after that is `rpr=0.0000`, so `high` stays 0.

Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.


| Edge                             | 24                   | 25                   | **┃** | 26                   | 27                   | **┃** | 28                   | 29                   |
| -------------------------------- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | ----- | -------------------- | -------------------- |
| frontend → checkoutservice       | 0.034 / 2.98 / 0.036 | 0.000 / 0.16 / 0.011 | **┃** | 0.200 / 1.96 / 0.272 | 0.030 / 2.48 / 0.025 | **┃** | 0.107 / 3.41 / 0.122 | 0.007 / 1.37 / 0.009 |
| frontend → recommendationservice | 0.482 / 3.09 / 0.292 | 0.551 / 3.30 / 0.949 | **┃** | 0.162 / 3.01 / 0.081 | 0.220 / 2.63 / 0.145 | **┃** | 0.161 / 3.04 / 0.091 | 0.212 / 3.15 / 0.133 |


Climb bars, counted only while that attempt cap is in force. The first number is the longest streak of `rpr ≤ 0.17` on controller samples where the edge is at 1 attempt. The second is the longest streak of `rpr ≤ 0.33` on samples where it is at 2 attempts. A sample above the bar ends the streak. An em dash means the edge never ran at that attempt count, so the bar was not in force. Samples are the `OBSERVE` lines in `retryguard.log`.


| Edge                             | 24    | 25    | **┃** | 26      | 27      | **┃** | 28      | 29    |
| -------------------------------- | ----- | ----- | ----- | ------- | ------- | ----- | ------- | ----- |
| frontend → checkoutservice       | — / — | — / — | **┃** | 30 / 30 | — / —   | **┃** | — / —   | — / — |
| frontend → recommendationservice | — / — | — / — | **┃** | — / —   | 30 / 30 | **┃** | 16 / 16 | — / — |


Run 26 is the only hold here that reached 1 and 2 attempts on checkout. Both climb streaks are 30, and both climbs fired (`rpr` 0.00). Run 27 did the same on recommendations, with streaks of 30. Run 28 did the same on recommendations under the 30-second bar: both climb streaks are 16 rows and both climbs fired at `elapsed_s=30` (`rpr` 0.00). Run 29 never left 0 attempts after the shed. Runs 24 and 25 never left 3 attempts except for the recommendations shed that stayed at 0.

## Rejection streaks

These are not the edge-mode shed signal. The streak tables use `(Δ5xx + Δresets) / Δtotal` from `service_inbound.csv`. A non-positive total delta is not high and is not under 0.10, and it breaks the streak. The controller adds `grpc_4` and `grpc_14` on top of that for the four read callees, and those two deltas are the table after the streaks.

Longest streak above 0.20, then the count of samples above 0.20. **Bold** is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain.


| Service                     | 24       | 25       | **┃** | 26          | 27      | **┃** | 28      | 29       |
| --------------------------- | -------- | -------- | ----- | ----------- | ------- | ----- | ------- | -------- |
| frontend (not controlled)   | 93 / 237 | 90 / 108 | **┃** | 23 / 46     | 31 / 36 | **┃** | 18 / 19 | 81 / 218 |
| checkoutservice             | 5 / 5    | 0 / 0    | **┃** | **32 / 67** | 4 / 4   | **┃** | 6 / 15  | 2 / 2    |
| recommendationservice       | 2 / 9    | 2 / 8    | **┃** | 1 / 7       | 2 / 7   | **┃** | 3 / 9   | 8 / 40   |
| paymentservice              | 0 / 0    | 0 / 0    | **┃** | 1 / 1       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| emailservice                | 2 / 4    | 0 / 0    | **┃** | 7 / 30      | 2 / 2   | **┃** | 3 / 7   | 1 / 1    |
| productcatalogservice       | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| cartservice                 | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| currencyservice             | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| shippingservice             | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| adservice                   | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |
| redis-cart (not controlled) | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0   | **┃** | 0 / 0   | 0 / 0    |


Longest streak strictly under 0.10, then the count of samples under 0.10. On runs 24–27 a streak of 30 is the 0→1 bar. On runs 28 and 29 the bar is 30 seconds of those rows. The controller consults it only while an edge of that callee is at 0 attempts.


| Service                     | 24        | 25        | **┃** | 26        | 27        | **┃** | 28        | 29        |
| --------------------------- | --------- | --------- | ----- | --------- | --------- | ----- | --------- | --------- |
| frontend (not controlled)   | 33 / 42   | 307 / 312 | **┃** | 252 / 321 | 172 / 260 | **┃** | 201 / 290 | 27 / 46   |
| checkoutservice             | 253 / 296 | 306 / 411 | **┃** | 251 / 367 | 279 / 305 | **┃** | 204 / 290 | 238 / 305 |
| recommendationservice       | 32 / 136  | 306 / 338 | **┃** | 307 / 399 | 176 / 273 | **┃** | 203 / 292 | 26 / 148  |
| paymentservice              | 254 / 302 | 306 / 412 | **┃** | 280 / 436 | 309 / 309 | **┃** | 205 / 305 | 238 / 307 |
| emailservice                | 252 / 296 | 306 / 411 | **┃** | 213 / 382 | 271 / 305 | **┃** | 207 / 294 | 238 / 305 |
| productcatalogservice       | 306 / 306 | 306 / 434 | **┃** | 307 / 441 | 309 / 309 | **┃** | 310 / 310 | 310 / 310 |
| cartservice                 | 306 / 306 | 306 / 434 | **┃** | 307 / 441 | 309 / 309 | **┃** | 310 / 310 | 310 / 310 |
| currencyservice             | 306 / 306 | 306 / 434 | **┃** | 307 / 440 | 309 / 309 | **┃** | 310 / 310 | 310 / 310 |
| shippingservice             | 256 / 305 | 306 / 424 | **┃** | 307 / 440 | 309 / 309 | **┃** | 207 / 309 | 242 / 309 |
| adservice                   | 306 / 306 | 306 / 428 | **┃** | 306 / 438 | 309 / 309 | **┃** | 308 / 308 | 309 / 309 |
| redis-cart (not controlled) | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     |


### gRPC counted in the rejection rate

`adservice`, `currencyservice`, `productcatalogservice`, and `recommendationservice` add `grpc_4` (deadline-exceeded) and `grpc_14` (unavailable) to the rejection numerator. Checkout, payment, email, cart, and shipping stay on 5xx + resets, so their gRPC columns are not in this rate. `grpc_2` and `grpc_13` are not in the numerator for any service.

Cell is `grpc_4 / grpc_14`, the positive increments over the hold.


| Service               | 24          | 25          | **┃** | 26         | 27         | **┃** | 28         | 29         |
| --------------------- | ----------- | ----------- | ----- | ---------- | ---------- | ----- | ---------- | ---------- |
| recommendationservice | 109,142 / 0 | 218,840 / 0 | **┃** | 39,627 / 0 | 38,658 / 0 | **┃** | 22,827 / 0 | 85,114 / 0 |
| productcatalogservice | 0 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |
| currencyservice       | 0 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |
| adservice             | 1 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |


## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

Layer A cap traces are in the last section.


| Service               | 24              | 25                  | **┃** | 26                  | 27                  | **┃** | 28              | 29              |
| --------------------- | --------------- | ------------------- | ----- | ------------------- | ------------------- | ----- | --------------- | --------------- |
| frontend              | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| checkoutservice       | 274/668 (41.0%) | **658/822 (80.0%)** | **┃** | **733/829 (88.4%)** | **515/664 (77.6%)** | **┃** | 103/663 (15.5%) | 137/664 (20.6%) |
| recommendationservice | 219/668 (32.8%) | 126/822 (15.3%)     | **┃** | 73/829 (8.8%)       | 72/664 (10.8%)      | **┃** | 145/663 (21.9%) | 196/664 (29.5%) |
| paymentservice        | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 2/663 (0.3%)    | 0/664 (0.0%)    |
| emailservice          | 46/668 (6.9%)   | 21/822 (2.6%)       | **┃** | **510/829 (61.5%)** | 188/664 (28.3%)     | **┃** | 38/663 (5.7%)   | 14/664 (2.1%)   |
| productcatalogservice | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| cartservice           | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| currencyservice       | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| shippingservice       | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| adservice             | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |
| redis-cart            | 0/668 (0.0%)    | 0/822 (0.0%)        | **┃** | 0/829 (0.0%)        | 0/664 (0.0%)        | **┃** | 0/663 (0.0%)    | 0/664 (0.0%)    |


## (c) Retry volume and gRPC errors

Outbound retry delta, the sum of positive `retry` increments on `service_edges.csv`. Every other target is 0.


| Service               | 24     | 25      | **┃** | 26     | 27     | **┃** | 28     | 29     |
| --------------------- | ------ | ------- | ----- | ------ | ------ | ----- | ------ | ------ |
| checkoutservice       | 737    | 286     | **┃** | 16,401 | 734    | **┃** | 2,394  | 149    |
| recommendationservice | 66,302 | 201,165 | **┃** | 34,980 | 35,057 | **┃** | 21,357 | 31,461 |


Inbound resets (`downstream_rq_rx_reset`). This is the failure the rejection rate counts. HTTP 5xx on these backends is 0. Frontend's own HTTP 5xx delta is 81,149 / 69,114 / 30,169 / 14,963 on slots 24–27 and 8,298 / 90,625 on slots 28 and 29.


| Service               | 24     | 25     | **┃** | 26     | 27     | **┃** | 28    | 29     |
| --------------------- | ------ | ------ | ----- | ------ | ------ | ----- | ----- | ------ |
| frontend              | 241    | 909    | **┃** | 583    | 50     | **┃** | 110   | 254    |
| checkoutservice       | 527    | 175    | **┃** | 14,334 | 508    | **┃** | 1,741 | 91     |
| recommendationservice | 35,808 | 50,317 | **┃** | 12,064 | 10,816 | **┃** | 5,866 | 34,238 |
| paymentservice        | 30     | 10     | **┃** | 994    | 29     | **┃** | 104   | 0      |
| emailservice          | 57     | 40     | **┃** | 760    | 80     | **┃** | 183   | 99     |
| productcatalogservice | 4      | 0      | **┃** | 6      | 4      | **┃** | 6     | 2      |
| cartservice           | 29     | 17     | **┃** | 1,002  | 29     | **┃** | 89    | 2      |
| currencyservice       | 0      | 1      | **┃** | 2      | 0      | **┃** | 0     | 0      |
| shippingservice       | 36     | 16     | **┃** | 1,129  | 40     | **┃** | 164   | 0      |
| adservice             | 0      | 0      | **┃** | 0      | 0      | **┃** | 0     | 0      |
| redis-cart            | 0      | 0      | **┃** | 0      | 0      | **┃** | 0     | 0      |


### gRPC counted in the retry policy

The same four callees retry `deadline-exceeded` and `unavailable` as well as `5xx,reset,connect-failure`. Those tokens are `grpc_4` and `grpc_14`. Checkout, payment, email, cart, and shipping retry `5xx,reset,connect-failure` only, so their gRPC columns are not a retry input. Cell is `grpc_4 / grpc_14`.


| Service               | 24          | 25          | **┃** | 26         | 27         | **┃** | 28         | 29         |
| --------------------- | ----------- | ----------- | ----- | ---------- | ---------- | ----- | ---------- | ---------- |
| recommendationservice | 109,142 / 0 | 218,840 / 0 | **┃** | 39,627 / 0 | 38,658 / 0 | **┃** | 22,827 / 0 | 85,114 / 0 |
| productcatalogservice | 0 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |
| currencyservice       | 0 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |
| adservice             | 1 / 0       | 0 / 0       | **┃** | 0 / 0      | 0 / 0      | **┃** | 0 / 0      | 0 / 0      |


## RetryGuard toggles

`ON→OFF` is the shed to 0 attempts. `OFF→ON` is the 0→1 step (the log's `attempts=1`, `from_attempts=0`). `1→2` and `2→3` are the climb lines.


| Slot | Edge                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| ---- | -------------------------------- | ------ | --- | --- | --- |
| 24   | frontend → recommendationservice | 1      | 0   | 0   | 0   |
| 25   | —                                | 0      | 0   | 0   | 0   |
| 26   | frontend → checkoutservice       | 1      | 1   | 1   | 1   |
| 27   | frontend → recommendationservice | 1      | 1   | 1   | 1   |
| 28   | frontend → recommendationservice | 1      | 1   | 1   | 1   |
| 29   | frontend → recommendationservice | 1      | 0   | 0   | 0   |


Run 24: `frontend → recommendationservice` ON→OFF at 2026-10-08T01:09:08Z, rpr 2.40, from 3 attempts. No 0→1 after that. Checkout's controller `high` peaked at 5.

Run 25: no shed. Recommendations `high` peaked at 7.

Run 26 climbed checkout all the way back to 3. Each climb step was at rpr 0.00. Recommendations `high` stayed 0.


| Time (UTC)           | Edge                       | Step   | From | Value          |
| -------------------- | -------------------------- | ------ | ---- | -------------- |
| 2026-10-08T09:12:40Z | frontend → checkoutservice | ON→OFF | 3    | rpr 1.77       |
| 2026-10-08T09:13:47Z | checkoutservice            | 0→1    | 0    | rejection 0.00 |
| 2026-10-08T09:14:47Z | frontend → checkoutservice | 1→2    | 1    | rpr 0.00       |
| 2026-10-08T09:15:46Z | frontend → checkoutservice | 2→3    | 2    | rpr 0.00       |


Run 27 climbed recommendations all the way back to 3. Each climb step was at rpr 0.00. Checkout's controller `high` peaked at 4.


| Time (UTC)           | Edge                             | Step   | From | Value          |
| -------------------- | -------------------------------- | ------ | ---- | -------------- |
| 2026-10-08T09:42:22Z | frontend → recommendationservice | ON→OFF | 3    | rpr 2.22       |
| 2026-10-08T09:45:39Z | recommendationservice            | 0→1    | 0    | rejection 0.00 |
| 2026-10-08T09:46:39Z | frontend → recommendationservice | 1→2    | 1    | rpr 0.00       |
| 2026-10-08T09:47:39Z | frontend → recommendationservice | 2→3    | 2    | rpr 0.00       |


Run 28 climbed recommendations all the way back to 3. Each step is `elapsed_s=30` and 16 counted rows, about half a minute apart. Checkout's controller `high` peaked at 6.


| Time (UTC)           | Edge                             | Step   | From | Value          |
| -------------------- | -------------------------------- | ------ | ---- | -------------- |
| 2026-10-08T11:50:58Z | frontend → recommendationservice | ON→OFF | 3    | rpr 2.96       |
| 2026-10-08T11:51:34Z | recommendationservice            | 0→1    | 0    | rejection 0.00 |
| 2026-10-08T11:52:07Z | frontend → recommendationservice | 1→2    | 1    | rpr 0.00       |
| 2026-10-08T11:52:39Z | frontend → recommendationservice | 2→3    | 2    | rpr 0.00       |


Run 29 shed recommendations and left it off. The OFF window has 239 rejection samples. One of them is under 0.10 (`0.0973` at 12:16:49Z), and the quiet counter then resets, so `low` peaks at 1. Checkout's controller `high` peaked at 1.


| Time (UTC)           | Edge                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-08T12:12:57Z | frontend → recommendationservice | ON→OFF | 3    | rpr 3.15 |


## Per arm

Runs 24 and 25 are the previous both-on pair. Run 24 sheds recommendations once from 3 and leaves it off (retries 66,302). Run 25 does not shed. Its recommendations file streak is 352 s, the controller `high` stops at 7, retries are 201,165, and `grpc_4` is 218,840. Checkout is detector-hot at 80% with volume rpr 0.011.

Run 26 sheds checkout, not recommendations. Checkout file streak is 60 s with controller `high` 30, retries are 16,401, and the edge returns to 3 attempts. Recommendations retries are 34,980, but that file streak ends about five minutes before the controller starts, so it does not shed. Email is detector-hot (61.5%) as well as checkout (88.4%).

Run 27 sheds recommendations from 3 at rpr 2.22 and climbs back to 3. Retries are 35,057 and `grpc_4` is 38,658, against run 24's 66,302 and 109,142 and run 25's 201,165 and 218,840. Checkout streak is 6 s and `high` is 4. Checkout is detector-hot (77.6%). Email is 28.3%.

Run 28 sheds recommendations from 3 at rpr 2.96 and climbs back to 3. Each step fires at `elapsed_s=30` with 16 rows, so the whole return takes about a minute and a half instead of about three. Retries are 21,357 and `grpc_4` is 22,827. Checkout file streak is 10 s and `high` is 6. Recommendations file streak is 32 s. No service is detector-hot. Checkout is 15.5% and recommendations is 21.9%.

Run 29 sheds recommendations from 3 at rpr 3.15 and leaves it off. Retries are 31,461 and `grpc_4` is 85,114. Inbound resets on recommendations are 34,238. Checkout file streak is 0 s (one row). Recommendations file streak is 32 s. No service is detector-hot. Checkout is 20.6% and recommendations is 29.5%.

## CPU mean / max

App-container millicores, mean / max, from `resource_usage.csv`. Quota is the per-pod CPU limit. The mean / max cells sum usage across replicas, so frontend can sit above its 1150 m pod limit.


| Service               | Quota | Replicas | 24          | 25          | **┃** | 26          | 27          | **┃** | 28          | 29          |
| --------------------- | ----- | -------- | ----------- | ----------- | ----- | ----------- | ----------- | ----- | ----------- | ----------- |
| frontend              | 1150  | 4        | 1223 / 1629 | 1103 / 1586 | **┃** | 1505 / 1696 | 1308 / 1639 | **┃** | 1258 / 1572 | 1252 / 1609 |
| checkoutservice       | 800   | 1        | 472 / 786   | 597 / 783   | **┃** | 708 / 798   | 610 / 788   | **┃** | 479 / 796   | 436 / 755   |
| recommendationservice | 1150  | 1        | 778 / 1151  | 563 / 1151  | **┃** | 819 / 1149  | 731 / 1133  | **┃** | 752 / 1150  | 748 / 1150  |
| paymentservice        | 155   | 1        | 33 / 69     | 35 / 55     | **┃** | 57 / 84     | 43 / 61     | **┃** | 33 / 95     | 28 / 51     |
| emailservice          | 120   | 1        | 60 / 110    | 64 / 100    | **┃** | 84 / 108    | 75 / 105    | **┃** | 54 / 103    | 51 / 102    |
| productcatalogservice | 800   | 1        | 370 / 500   | 411 / 465   | **┃** | 482 / 523   | 407 / 520   | **┃** | 396 / 510   | 319 / 417   |
| cartservice           | 800   | 1        | 330 / 422   | 334 / 416   | **┃** | 353 / 425   | 337 / 479   | **┃** | 305 / 394   | 368 / 552   |
| currencyservice       | 770   | 1        | 343 / 463   | 271 / 455   | **┃** | 407 / 466   | 363 / 470   | **┃** | 350 / 446   | 362 / 512   |
| shippingservice       | 770   | 1        | 73 / 114    | 69 / 120    | **┃** | 100 / 127   | 93 / 123    | **┃** | 77 / 106    | 66 / 100    |
| adservice             | 1150  | 1        | 111 / 183   | 102 / 167   | **┃** | 159 / 188   | 143 / 204   | **┃** | 138 / 177   | 109 / 172   |
| redis-cart            | 540   | 1        | 41 / 58     | 44 / 56     | **┃** | 43 / 55     | 40 / 55     | **┃** | 38 / 52     | 42 / 59     |


## TopFull cap

`topfull_throttle.csv` records the cap TopFull has installed on each Locust API, one row per second. A row with `threshold_fresh=1` and `threshold` above 0 is one live `GET /thresholds`. That live value is kept for the following seconds, up to 6 s, so the usual 5 s scrape still fills the 1 s grid. The passthrough sentinel is no cap: it is left off the series, so a graph of this metric is not scaled to a number that is not a TopFull decision. A live 0 is an empty read and is left off the same way. Rows with `threshold_fresh=0` only repeat the last live value. The PPO multiplier and the candidate-API set are printed by `deploy_rl.py` and are not in these folders.

`postcart` and `emptycart` are no cap on every live read of every hold.

Times are UTC. An arrow is the next distinct live cap.

### Run 24

Live reads stop at 01:08:05. Rows through 01:16:04 repeat the last live cap.

| API          | Live caps                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| postcheckout | no cap from 01:05:00. From 01:06:10: 29 → 44 → 48 → 55 → 61.9 → 58 → 13.8 → 17.9 → 29.9 → 35.7 → 29.1 → 22.2 → 19.4 → 13 → 10 (01:07:06–01:07:50) → 14.1 → 27.5 → 54.5 at 01:08:05 |
| getproduct   | no cap until 01:07:00, then 234.3 → 227.9 → 224.9 → 222.3 → 219.8 → 218.5 → 214.7 → 213.4 → 209.6 → 205.8 → 204.5 → 200.6 → 196.8 → 191.8 → 188 → 186.9, then no cap at 01:08:00 |
| getcart      | no cap until 01:06:57, then 81.1 → 78.3 → 71.9 → 68.9 → 66.3 → 63.8 → 62.5 → 58.7 → 57.4 → 53.6 → 49.8 → 48.5 → 44.6 → 40.8 → 35.8 → 32 → 30.9, then 84.8 → 110, then no cap at 01:08:05 |

### Run 25

The first live read is 01:40:00. Rows from 01:32:50 until then repeat 58.8 with `threshold_fresh=0`.

| API          | Live caps                                      |
| ------------ | ---------------------------------------------- |
| postcheckout | no cap at 01:40:00, then 33 from 01:40:05 through 01:50:20 |
| getproduct   | no cap at 01:40:00, then 97 from 01:40:05 through 01:50:20 |
| getcart      | no cap at 01:40:00, then 36 from 01:40:05 through 01:50:20 |

### Run 26

The first live read is already a real cap.

| API          | Live caps                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| postcheckout | 95.8 from 09:03:25 to 09:04:45. Next live read 09:10:10: 60.4 → 61.6 → 59.6 → 59.8 → 60 → 66.9 → 57.5 → 62.1 → 64.3 → 65.4, then 67.6 from 09:10:50 through 09:21:05 |
| getproduct   | 275 from 09:03:25 through 09:10:11, then no cap from 09:10:15 through 09:21:05 |
| getcart      | 100 from 09:03:25 through 09:10:10, then no cap from 09:10:15 through 09:21:05 |

### Run 27

Live reads stop at 09:41:20. Rows through 09:50:24 repeat the last live cap.

| API          | Live caps                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| postcheckout | no cap from 09:39:25 to 09:40:30. Then 39 → 46 → 62.7 → 66 → 72 → 46.5 → 10 → 32.8 → 67.6 → 75.9 at 09:41:19 |
| getproduct   | no cap on every live read, 09:39:25–09:41:20 |
| getcart      | no cap on every live read, 09:39:25–09:41:20 |

### Run 28

Live reads stop at 11:50:25. Rows through 11:57:47 repeat the last live cap.

| API          | Live caps                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| postcheckout | no cap through 11:48:05. From 11:48:10: 59 → 72.6 → 43.3 → 26.7 → 10 → 15.7 → 12.8 → 17.9 → 29.8 → 38.2 → 48.5 → 67.1 → 79.5 → 48.3 → 29.7 → 11.2 → 24.8 → 38 → 41.9 → 50 → 52.3 → 45.6 → 46.9 → 45 → 66.2 → 38.3 → 15.4 → 29 → 36.1 → 37.5 → 59.7 → 55.6 → 46.6 → 46.4 at 11:50:25 |
| getproduct   | no cap through 11:48:20. Then 252 → 301.4 → 286.9, no cap (11:48:45–11:48:55), 275, no cap (11:49:05–11:49:10), 285.5, no cap (11:49:19–11:49:20), 285.5 → 282.4 → 286.1 → 301.4, 275 (11:49:50–11:49:55), 284.2 → 291.4 → 292.8 → 302.5 from 11:50:10 |
| getcart      | no cap through 11:48:20. Then 94 → 110 → 105.6, no cap (11:48:45–11:48:55), 100, no cap (11:49:05–11:49:10), 108.5, 107.4 → 109.3, no cap (11:49:40–11:49:45), 100, 107.8 → 110, 96.8 → 98.5 → 102.3 → 107.8 at 11:50:25 |

### Run 29

| API          | Live caps                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| postcheckout | no cap through 12:11:00. Then 39.6, no cap at 12:11:06, 47.3, no cap (12:11:15–12:11:23), 72 → 23.4 → 10, 14.1 → 19.5 → 25.7 → 43.1 → 42.8 → 26.5 → 17.8 → 15.6 → 10.4 → 10, 19.2 → 46 → 53.1 at 12:12:25. Next live read above 0 is 48 at 12:20:55 |
| getproduct   | no cap through 12:11:30. Then 176.4 → 302.5, no cap at 12:11:50, 239.8 → 231.1 → 228.9 → 223.7 → 220 → 218.8 → 216.3 → 302.5, no cap at 12:12:25, 240 from 12:12:27 through 12:20:54, then no cap at 12:20:55 |
| getcart      | no cap through 12:11:30. Then 69.4, no cap (12:11:44–12:11:50), 80.8 → 72.1 → 69.9 → 64.7 → 61 → 59.8 → 57.3 → 110, no cap at 12:12:25, 91 from 12:12:27 through 12:20:54, then no cap at 12:20:55 |


