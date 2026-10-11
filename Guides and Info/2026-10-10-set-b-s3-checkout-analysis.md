# Set B Scenario 3, checkout 300 m, (a) / (b) / (c)

## Setup

600 s holds. Mix getproduct / postcheckout / getcart / postcart / emptycart = 175 / 30 / 70 / 90 / 5, `spawn_rate` 50. Paper-C1 except `checkoutservice` at 300 m: frontend 1150 m × 4, checkoutservice 300 m × 1, recommendationservice 1150 m × 1, productcatalogservice 800 m × 1, cartservice 800 m × 1, currencyservice 770 m × 1, shippingservice 770 m × 1, adservice 1150 m × 1, paymentservice 155 m × 1, emailservice 120 m × 1, redis-cart 540 m × 1. Frontend is pinned at 4 replicas. Every other service is 1 replica. The configs roll checkout and recommendations before each hold (`restart_before_hold`, settle 60 s). The study procedure cools off 360 s between holds.

`retry_metric` is `edge_rpr`. `reenable_rejection` is 0.15. Arms, two repeats each: `tf1rg0` is TopFull on and RetryGuard off, `tf0rg1` is TopFull off and RetryGuard on, `tf1rg1` is both on. Folders are under `experiments/results/campaign_48/S3_targeted_bottleneck/`:

- `study2_s3_tf1rg0_rep1`, `study2_s3_tf1rg0_rep2`
- `study2_s3_tf0rg1_rep1`, `study2_s3_tf0rg1_rep2`
- `study2_s3_tf1rg1_rep1`, `study2_s3_tf1rg1_rep2`

Tables are `python experiments/analysis_score.py --sep 2` on those six folders, in the index order. The file streak is seconds. The parenthetical on a RetryGuard hold is the controller's max `high` from `retryguard.log`, which is a sample count.

## Index

A bold bar separates the three arms. Column order follows this index.


| Arm                            | Columns              |
| ------------------------------ | -------------------- |
| TopFull on, RetryGuard off     | tf1rg0-1, tf1rg0-2   |
| TopFull off, RetryGuard on    | tf0rg1-1, tf0rg1-2   |
| Both on                        | tf1rg1-1, tf1rg1-2   |


## Gate

Passed on all six. Locust `total.csv` rows are 570, 567, 576, 570, 570, and 566. Frontend `replica_count` is 4 on every `resource_usage.csv` sample (133/133, 133/133, 138/138, 138/138, 138/138, 139/139). Every other service in that file is 1 on those same samples. No service hit replica 0. `service_capacity.json` is the same on every hold and matches the pin above (checkout 300 m × 1, frontend 1150 m × 4). Mesh span is 691 s, 692 s, 714 s, 715 s, 717 s, and 719 s. Inbound gaps of 1.5 s or longer are 1166 of 6435, 1606 of 6006, 0 of 7854, 0 of 7865, 1298 of 6589, and 1551 of 6358. The two RetryGuard-only holds have no such gap. The four TopFull-on holds do, so those rejection streaks count slower polls. The files are usable, so the columns stay filled.

`retryguard.log` is absent on tf1rg0-1 and tf1rg0-2. It is present on the other four. No `PATCH_FAIL` and no traceback.

## Edge-mode bars

Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.10.

That line is the scorer's first line. It reads the first folder, tf1rg0-1, which has no `retryguard.log`, so the re-enable figure there is the scorer default 0.10. Each RetryGuard `START` line says `metric=edge_rpr`, `rpr_threshold=0.50`, `rejection_threshold=0.20`, `reenable_rejection=0.15`, `interval_samples=30s`, `attempts_on=3`, `edges=14`. The under-bar table uses 0.15 on the four holds that have a `START` line and 0.10 on the two that do not.

Shed and 0→1 take `interval_samples` seconds of row timestamps, 30 s on these holds. 1→2 and 2→3 take 15 s (`CLIMB_INTERVAL_SECONDS`). These holds are after 2026-10-08, so the climb is 15 s rather than 30 s. Both sheds that fired have `elapsed_s=30`.

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The file streak is seconds from the first consecutive `service_edges.csv` row with rpr > 0.5 to the last. A gap between two high rows stays inside the streak. A single row is 0 seconds. **Bold** is a file streak of at least 30 seconds. The parenthetical is the controller's max `high`, a sample count. tf1rg0 has no log, so those cells have no parenthetical.

Only `frontend → checkoutservice`, `frontend → adservice`, and `frontend → recommendationservice` have a tick above the shed bar or a retry delta. The other 11 controlled edges are at retry delta 0 with no tick above 0.5 on every hold.

Longest streak in seconds of rpr > 0.5, then the number of scored ticks above 0.5.


| Edge                             | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1         | tf0rg1-2         | **┃** | tf1rg1-1  | tf1rg1-2  |
| -------------------------------- | -------- | -------- | ----- | ---------------- | ---------------- | ----- | --------- | --------- |
| frontend → checkoutservice       | 14 / 235 | 9 / 208  | **┃** | **32 / 33 (31)** | **32 / 33 (27)** | **┃** | 10 / 232 (10) | 11 / 234 (10) |
| frontend → adservice             | 0 / 0    | 0 / 0    | **┃** | 0 / 0 (0)        | 0 / 0 (0)        | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → recommendationservice | 0 / 0    | 0 / 0    | **┃** | 0 / 0 (0)        | 0 / 0 (0)        | **┃** | 0 / 0 (0) | 0 / 0 (0) |


Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.


| Edge                             | tf1rg0-1             | tf1rg0-2             | **┃** | tf0rg1-1             | tf0rg1-2             | **┃** | tf1rg1-1             | tf1rg1-2             |
| -------------------------------- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | ----- | -------------------- | -------------------- |
| frontend → checkoutservice       | 0.941 / 6.83 / 0.870 | 0.859 / 5.50 / 0.838 | **┃** | 0.108 / 4.40 / 0.067 | 0.109 / 3.25 / 0.067 | **┃** | 0.943 / 5.75 / 0.855 | 0.976 / 4.44 / 0.908 |
| frontend → adservice             | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.01 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 |
| frontend → recommendationservice | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.14 / 0.000 |


Climb streaks while that attempt cap is in force. The first number is samples at 1 attempt with rpr at or under 0.17. The second is samples at 2 attempts with rpr at or under 0.33. An em dash means that cap never applied. No edge on these holds ran at 1 or 2 attempts.


| Edge                             | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| -------------------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend → checkoutservice       | — / —    | — / —    | **┃** | — / —    | — / —    | **┃** | — / —    | — / —    |
| frontend → adservice             | — / —    | — / —    | **┃** | — / —    | — / —    | **┃** | — / —    | — / —    |
| frontend → recommendationservice | — / —    | — / —    | **┃** | — / —    | — / —    | **┃** | — / —    | — / —    |


## Rejection, beside (a)

These are not the shed signal. The streak tables use `(Δ5xx + Δresets) / Δtotal` from `service_inbound.csv`. A non-positive total delta is not high and is not under the re-enable bar, and it breaks the streak. **Bold** in the 0.20 table is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain.

Longest streak above 0.20, then the count of samples above 0.20.


| Service                     | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1    | tf0rg1-2    | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------------- | -------- | -------- | ----- | ----------- | ----------- | ----- | -------- | -------- |
| frontend (not controlled)   | 0 / 0    | 1 / 1    | **┃** | 1 / 1       | 1 / 1       | **┃** | 0 / 0    | 0 / 0    |
| checkoutservice             | 10 / 232 | 7 / 191  | **┃** | **36 / 414** | **37 / 448** | **┃** | 9 / 226  | 9 / 229  |
| recommendationservice       | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |
| paymentservice              | 1 / 3    | 1 / 2    | **┃** | 1 / 2       | 1 / 3       | **┃** | 1 / 3    | 1 / 7    |
| emailservice                | 2 / 19   | 1 / 20   | **┃** | 2 / 46      | 4 / 61      | **┃** | 2 / 24   | 2 / 18   |
| productcatalogservice       | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |
| cartservice                 | 0 / 0    | 1 / 1    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |
| currencyservice             | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |
| shippingservice             | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 1 / 1       | **┃** | 0 / 0    | 0 / 0    |
| adservice                   | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |
| redis-cart (not controlled) | 0 / 0    | 0 / 0    | **┃** | 0 / 0       | 0 / 0       | **┃** | 0 / 0    | 0 / 0    |


Longest streak strictly under the re-enable bar, then the count of samples under that bar. On tf1rg0 the bar is 0.10, because there is no `START` line. On tf0rg1 and tf1rg1 the bar is 0.15, from the `START` line. The controller consults it only while an edge of that callee is at 0 attempts. On tf0rg1 the OFF-window `low` peaks at 3 and at 1, so the 30 s quiet interval does not complete.


| Service                     | tf1rg0-1  | tf1rg0-2  | **┃** | tf0rg1-1  | tf0rg1-2  | **┃** | tf1rg1-1  | tf1rg1-2  |
| --------------------------- | --------- | --------- | ----- | --------- | --------- | ----- | --------- | --------- |
| frontend (not controlled)   | 506 / 506 | 466 / 466 | **┃** | 612 / 612 | 612 / 612 | **┃** | 495 / 495 | 473 / 473 |
| checkoutservice             | 40 / 250  | 45 / 251  | **┃** | 45 / 97   | 43 / 70   | **┃** | 41 / 258  | 37 / 234  |
| recommendationservice       | 507 / 507 | 466 / 466 | **┃** | 613 / 613 | 613 / 613 | **┃** | 495 / 495 | 471 / 471 |
| paymentservice              | 66 / 456  | 61 / 429  | **┃** | 533 / 606 | 537 / 607 | **┃** | 127 / 487 | 86 / 459  |
| emailservice                | 42 / 354  | 45 / 329  | **┃** | 46 / 489  | 44 / 471  | **┃** | 43 / 345  | 39 / 342  |
| productcatalogservice       | 507 / 507 | 466 / 466 | **┃** | 613 / 613 | 613 / 613 | **┃** | 495 / 495 | 472 / 472 |
| cartservice                 | 507 / 507 | 466 / 466 | **┃** | 613 / 613 | 613 / 613 | **┃** | 495 / 495 | 473 / 473 |
| currencyservice             | 507 / 507 | 466 / 466 | **┃** | 613 / 613 | 613 / 613 | **┃** | 495 / 495 | 472 / 472 |
| shippingservice             | 507 / 507 | 466 / 466 | **┃** | 613 / 613 | 612 / 612 | **┃** | 495 / 495 | 472 / 472 |
| adservice                   | 506 / 506 | 465 / 465 | **┃** | 612 / 612 | 611 / 611 | **┃** | 495 / 495 | 472 / 472 |
| redis-cart (not controlled) | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     |


`grpc_4` / `grpc_14` for recommendationservice, productcatalogservice, currencyservice, and adservice. Those two codes are what the retry policy counts on these four read callees. They are not in the 0.20 streak numerator.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| recommendationservice | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| productcatalogservice | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| currencyservice       | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| adservice             | 0 / 0    | 0 / 0    | **┃** | 4 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |


## (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as ticks/rows (share%). **Bold** is a share of at least 0.5.


| Service               | tf1rg0-1            | tf1rg0-2            | **┃** | tf0rg1-1            | tf0rg1-2            | **┃** | tf1rg1-1            | tf1rg1-2            |
| --------------------- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ----- | ------------------- | ------------------- |
| frontend              | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| checkoutservice       | **528/638 (82.8%)** | **518/638 (81.2%)** | **┃** | **584/661 (88.4%)** | **590/661 (89.3%)** | **┃** | **512/663 (77.2%)** | **522/665 (78.5%)** |
| recommendationservice | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| paymentservice        | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| emailservice          | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| productcatalogservice | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| cartservice           | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| currencyservice       | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| shippingservice       | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| adservice             | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |
| redis-cart            | 0/638 (0.0%)        | 0/638 (0.0%)        | **┃** | 0/661 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/665 (0.0%)        |


## (c) Retry volume

Outbound retry delta by target, the sum of positive `retry` increments on `service_edges.csv`. Every other target is 0.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| checkoutservice       | 8,304    | 8,221    | **┃** | 1,151    | 1,146    | **┃** | 8,300    | 8,640    |
| recommendationservice | 0        | 0        | **┃** | 0        | 0        | **┃** | 0        | 1        |
| adservice             | 0        | 0        | **┃** | 1        | 0        | **┃** | 0        | 0        |


Inbound resets (`downstream_rq_rx_reset`) for all 11 services.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend              | 28       | 54       | **┃** | 16       | 23       | **┃** | 7        | 4        |
| checkoutservice       | 4,908    | 4,825    | **┃** | 4,984    | 5,347    | **┃** | 4,880    | 5,040    |
| recommendationservice | 0        | 3        | **┃** | 0        | 0        | **┃** | 1        | 1        |
| paymentservice        | 435      | 477      | **┃** | 125      | 145      | **┃** | 421      | 461      |
| emailservice          | 93       | 106      | **┃** | 496      | 512      | **┃** | 115      | 111      |
| productcatalogservice | 5        | 8        | **┃** | 3        | 0        | **┃** | 2        | 3        |
| cartservice           | 165      | 197      | **┃** | 412      | 446      | **┃** | 206      | 207      |
| currencyservice       | 1        | 0        | **┃** | 0        | 2        | **┃** | 0        | 0        |
| shippingservice       | 290      | 342      | **┃** | 176      | 251      | **┃** | 328      | 345      |
| adservice             | 0        | 0        | **┃** | 1        | 0        | **┃** | 0        | 0        |
| redis-cart            | 0        | 0        | **┃** | 0        | 0        | **┃** | 0        | 0        |


The same `grpc_4 / grpc_14` pair is what the retry policy counts on the four read callees. Checkout, payment, email, cart, and shipping stay on 5xx, resets, and connect-failure.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| recommendationservice | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| productcatalogservice | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| currencyservice       | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |
| adservice             | 0 / 0    | 0 / 0    | **┃** | 4 / 0    | 0 / 0    | **┃** | 0 / 0    | 0 / 0    |


## RetryGuard toggles

`ON→OFF` is the shed to 0 attempts. `0→1` is the restore to 1 attempt. `1→2` and `2→3` are the climb lines.

tf1rg0-1 and tf1rg0-2 have no `retryguard.log`. tf1rg1-1 and tf1rg1-2 have a log and no transition lines, so there is no timestamp log for those four holds.


| Hold     | Edge                       | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------- | -------------------------- | ------ | --- | --- | --- |
| tf1rg0-1 | —                          | 0      | 0   | 0   | 0   |
| tf1rg0-2 | —                          | 0      | 0   | 0   | 0   |
| tf0rg1-1 | frontend → checkoutservice | 1      | 0   | 0   | 0   |
| tf0rg1-2 | frontend → checkoutservice | 1      | 0   | 0   | 0   |
| tf1rg1-1 | —                          | 0      | 0   | 0   | 0   |
| tf1rg1-2 | —                          | 0      | 0   | 0   | 0   |


tf0rg1-1 shed checkout from 3 attempts. `elapsed_s=30`. The OFF window then stays at 0 attempts through the end of the log. `low` peaks at 3.


| Time (UTC)           | Edge                       | Step   | From | Value    |
| -------------------- | -------------------------- | ------ | ---- | -------- |
| 2026-10-09T09:17:20Z | frontend → checkoutservice | ON→OFF | 3    | rpr 1.50 |


tf0rg1-2 shed checkout from 3 attempts. `elapsed_s=30`. No 0→1 after that. `low` peaks at 1.


| Time (UTC)           | Edge                       | Step   | From | Value    |
| -------------------- | -------------------------- | ------ | ---- | -------- |
| 2026-10-09T14:31:38Z | frontend → checkoutservice | ON→OFF | 3    | rpr 2.06 |


## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.


| API          | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| ------------ | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| getproduct   | 168.0    | 167.7    | **┃** | 168.0    | 168.0    | **┃** | 168.0    | 167.9    |
| postcheckout | 8.5      | 9.1      | **┃** | 7.9      | 7.1      | **┃** | 8.6      | 8.1      |
| getcart      | 67.2     | 67.1     | **┃** | 67.2     | 67.1     | **┃** | 67.2     | 67.1     |
| postcart     | 86.4     | 86.3     | **┃** | 86.4     | 86.3     | **┃** | 86.4     | 86.3     |
| emptycart    | 4.8      | 4.8      | **┃** | 4.8      | 4.8      | **┃** | 4.8      | 4.8      |


## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.


| API          | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| ------------ | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| getproduct   | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| postcheckout | 0.644    | 0.627    | **┃** | 0.697    | 0.725    | **┃** | 0.645    | 0.660    |
| getcart      | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| postcart     | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| emptycart    | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |


## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.


| API          | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| ------------ | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| getproduct   | 87       | 91       | **┃** | 89       | 76       | **┃** | 86       | 91       |
| postcheckout | 1230     | 1208     | **┃** | 630      | 623      | **┃** | 1241     | 1267     |
| getcart      | 71       | 73       | **┃** | 74       | 55       | **┃** | 72       | 77       |
| postcart     | 61       | 61       | **┃** | 61       | 60       | **┃** | 61       | 61       |
| emptycart    | 18       | 12       | **┃** | 13       | 13       | **┃** | 16       | 15       |


## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service, req/s.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend              | 302.6    | 302.6    | **┃** | 303.7    | 303.2    | **┃** | 291.9    | 290.9    |
| checkoutservice       | 25.8     | 26.1     | **┃** | 25.7     | 25.7     | **┃** | 25.1     | 25.2     |
| recommendationservice | 221.8    | 221.9    | **┃** | 225.5    | 225.1    | **┃** | 214.0    | 213.2    |
| paymentservice        | 20.5     | 21.1     | **┃** | 24.6     | 24.5     | **┃** | 20.2     | 20.5     |
| emailservice          | 8.6      | 9.2      | **┃** | 10.3     | 9.8      | **┃** | 8.5      | 8.1      |
| productcatalogservice | 1555.6   | 1556.0   | **┃** | 1571.0   | 1568.3   | **┃** | 1501.1   | 1495.7   |
| cartservice           | 325.3    | 325.5    | **┃** | 323.0    | 321.9    | **┃** | 314.0    | 313.3    |
| currencyservice       | 449.5    | 449.8    | **┃** | 435.2    | 433.8    | **┃** | 433.7    | 432.5    |
| shippingservice       | 99.6     | 100.0    | **┃** | 105.3    | 105.0    | **┃** | 96.3     | 96.6     |
| adservice             | 148.5    | 148.3    | **┃** | 143.8    | 143.5    | **┃** | 143.2    | 142.8    |
| redis-cart            | 0.0      | 0.0      | **┃** | 0.0      | 0.0      | **┃** | 0.0      | 0.0      |


## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. redis-cart has no `rq_time` counts, so the cell is an em dash.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend              | 79       | 81       | **┃** | 87       | 81       | **┃** | 81       | 83       |
| checkoutservice       | 382      | 379      | **┃** | 467      | 473      | **┃** | 381      | 385      |
| recommendationservice | 7        | 9        | **┃** | 9        | 7        | **┃** | 8        | 9        |
| paymentservice        | 2        | 2        | **┃** | 2        | 2        | **┃** | 3        | 2        |
| emailservice          | 5        | 5        | **┃** | 4        | 4        | **┃** | 5        | 5        |
| productcatalogservice | 1        | 1        | **┃** | 1        | 1        | **┃** | 1        | 1        |
| cartservice           | 2        | 2        | **┃** | 2        | 2        | **┃** | 2        | 2        |
| currencyservice       | 1        | 1        | **┃** | 2        | 2        | **┃** | 2        | 2        |
| shippingservice       | 1        | 1        | **┃** | 1        | 1        | **┃** | 1        | 1        |
| adservice             | 1        | 1        | **┃** | 1        | 1        | **┃** | 1        | 1        |
| redis-cart            | —        | —        | **┃** | —        | —        | **┃** | —        | —        |


## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. redis-cart has no buckets, so the cell is an em dash.


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend              | 0.023    | 0.023    | **┃** | 0.066    | 0.067    | **┃** | 0.023    | 0.024    |
| checkoutservice       | 0.587    | 0.568    | **┃** | 0.677    | 0.706    | **┃** | 0.588    | 0.606    |
| recommendationservice | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| paymentservice        | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| emailservice          | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| productcatalogservice | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| cartservice           | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| currencyservice       | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| shippingservice       | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| adservice             | 0.000    | 0.000    | **┃** | 0.000    | 0.000    | **┃** | 0.000    | 0.000    |
| redis-cart            | —        | —        | **┃** | —        | —        | **┃** | —        | —        |


## CPU

Per-pod quota, replica mode, mean millicores, max millicores. Quota is the per-pod `quota` in `topfull_detect.csv`. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota. Quota and the replica mode are the same on every hold.


| Service               | Quota | Replicas | tf1rg0-1    | tf1rg0-2    | **┃** | tf0rg1-1    | tf0rg1-2    | **┃** | tf1rg1-1    | tf1rg1-2    |
| --------------------- | ----- | -------- | ----------- | ----------- | ----- | ----------- | ----------- | ----- | ----------- | ----------- |
| frontend              | 1150  | 4        | 1225 / 1499 | 1215 / 1432 | **┃** | 1120 / 1366 | 1259 / 1533 | **┃** | 1118 / 1375 | 1131 / 1404 |
| checkoutservice       | 300   | 1        | 251 / 296   | 250 / 296   | **┃** | 252 / 297   | 251 / 297   | **┃** | 241 / 297   | 240 / 296   |
| recommendationservice | 1150  | 1        | 471 / 609   | 464 / 565   | **┃** | 456 / 568   | 487 / 619   | **┃** | 437 / 548   | 438 / 552   |
| paymentservice        | 155   | 1        | 20 / 29     | 21 / 32     | **┃** | 22 / 30     | 23 / 30     | **┃** | 19 / 29     | 20 / 28     |
| emailservice          | 120   | 1        | 23 / 36     | 23 / 44     | **┃** | 24 / 40     | 24 / 41     | **┃** | 22 / 43     | 21 / 35     |
| productcatalogservice | 800   | 1        | 455 / 540   | 428 / 503   | **┃** | 399 / 486   | 467 / 562   | **┃** | 411 / 497   | 399 / 486   |
| cartservice           | 800   | 1        | 313 / 384   | 305 / 378   | **┃** | 287 / 439   | 315 / 397   | **┃** | 288 / 437   | 303 / 468   |
| currencyservice       | 770   | 1        | 298 / 363   | 290 / 343   | **┃** | 256 / 325   | 287 / 353   | **┃** | 259 / 325   | 267 / 333   |
| shippingservice       | 770   | 1        | 64 / 79     | 62 / 76     | **┃** | 63 / 77     | 66 / 81     | **┃** | 61 / 74     | 60 / 74     |
| adservice             | 1150  | 1        | 123 / 152   | 120 / 142   | **┃** | 107 / 136   | 116 / 139   | **┃** | 107 / 132   | 112 / 137   |
| redis-cart            | 540   | 1        | 40 / 55     | 39 / 53     | **┃** | 36 / 49     | 40 / 55     | **┃** | 36 / 51     | 37 / 51     |


## CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out of the fraction. No sample here has replica count 0.


| Service               | tf1rg0-1  | tf1rg0-2  | **┃** | tf0rg1-1  | tf0rg1-2  | **┃** | tf1rg1-1  | tf1rg1-2  |
| --------------------- | --------- | --------- | ----- | --------- | --------- | ----- | --------- | --------- |
| frontend              | 0.27 / 0.33 | 0.26 / 0.31 | **┃** | 0.24 / 0.30 | 0.27 / 0.33 | **┃** | 0.24 / 0.30 | 0.25 / 0.31 |
| checkoutservice       | 0.84 / 0.99 | 0.83 / 0.99 | **┃** | 0.84 / 0.99 | 0.84 / 0.99 | **┃** | 0.80 / 0.99 | 0.80 / 0.99 |
| recommendationservice | 0.41 / 0.53 | 0.40 / 0.49 | **┃** | 0.40 / 0.49 | 0.42 / 0.54 | **┃** | 0.38 / 0.48 | 0.38 / 0.48 |
| paymentservice        | 0.13 / 0.19 | 0.13 / 0.21 | **┃** | 0.14 / 0.19 | 0.15 / 0.19 | **┃** | 0.13 / 0.19 | 0.13 / 0.18 |
| emailservice          | 0.19 / 0.30 | 0.19 / 0.37 | **┃** | 0.20 / 0.33 | 0.20 / 0.34 | **┃** | 0.18 / 0.36 | 0.18 / 0.29 |
| productcatalogservice | 0.57 / 0.68 | 0.54 / 0.63 | **┃** | 0.50 / 0.61 | 0.58 / 0.70 | **┃** | 0.51 / 0.62 | 0.50 / 0.61 |
| cartservice           | 0.39 / 0.48 | 0.38 / 0.47 | **┃** | 0.36 / 0.55 | 0.39 / 0.50 | **┃** | 0.36 / 0.55 | 0.38 / 0.58 |
| currencyservice       | 0.39 / 0.47 | 0.38 / 0.45 | **┃** | 0.33 / 0.42 | 0.37 / 0.46 | **┃** | 0.34 / 0.42 | 0.35 / 0.43 |
| shippingservice       | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.09 / 0.11 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 |
| adservice             | 0.11 / 0.13 | 0.10 / 0.12 | **┃** | 0.09 / 0.12 | 0.10 / 0.12 | **┃** | 0.09 / 0.11 | 0.10 / 0.12 |
| redis-cart            | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.07 / 0.09 | 0.07 / 0.10 | **┃** | 0.07 / 0.09 | 0.07 / 0.09 |


## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).


| Service               | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --------------------- | -------- | -------- | ----- | -------- | -------- | ----- | -------- | -------- |
| frontend              | 0.349    | 0.333    | **┃** | 0.317    | 0.358    | **┃** | 0.331    | 0.332    |
| checkoutservice       | 1.063    | 1.047    | **┃** | 1.057    | 1.063    | **┃** | 1.067    | 1.067    |
| recommendationservice | 0.570    | 0.554    | **┃** | 0.531    | 0.560    | **┃** | 0.517    | 0.512    |
| paymentservice        | 0.368    | 0.374    | **┃** | 0.465    | 0.355    | **┃** | 0.413    | 0.355    |
| emailservice          | 0.583    | 0.533    | **┃** | 0.517    | 0.608    | **┃** | 0.567    | 0.592    |
| productcatalogservice | 0.713    | 0.679    | **┃** | 0.641    | 0.731    | **┃** | 0.679    | 0.640    |
| cartservice           | 0.535    | 0.504    | **┃** | 0.590    | 0.540    | **┃** | 0.575    | 0.598    |
| currencyservice       | 0.506    | 0.491    | **┃** | 0.484    | 0.521    | **┃** | 0.468    | 0.492    |
| shippingservice       | 0.135    | 0.126    | **┃** | 0.132    | 0.135    | **┃** | 0.130    | 0.132    |
| adservice             | 0.151    | 0.215    | **┃** | 0.182    | 0.142    | **┃** | 0.178    | 0.140    |
| redis-cart            | 0.228    | 0.207    | **┃** | 0.185    | 0.191    | **┃** | 0.206    | 0.220    |


## TopFull live caps

A live read has `threshold_fresh=1` and `threshold` above 0. 10000 is no cap. A live 0 is an empty read and is left out. `postcart` and `emptycart` are no cap on every live read of every hold. `getproduct` and `getcart` are no cap on every live read of every hold. On tf0rg1, `postcheckout` is no cap for the whole live window, which is the 10000 passthrough with TopFull off.

`postcheckout` on the four TopFull-on holds is not short enough to read as an arrow trace. The cells below are the scorer's collapsed spans (132, 132, 140, and 123 spans).

### tf1rg0-1

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 10:33:05–10:43:35 |
| postcheckout | no cap 10:33:05-10:33:45; 13 at 10:33:50; 17.6 at 10:33:55; 18 at 10:33:57; no cap at 10:34:00; 22 at 10:34:05; 10 at 10:34:10; 19 at 10:34:15; 15.6 at 10:34:20; 10 at 10:34:25; 25.7 at 10:34:30; 13.7 at 10:34:35; 10 at 10:34:40; 27.6185 at 10:34:44; 27.6 at 10:34:45; 10 10:34:48-10:34:50; 18.9 at 10:34:55; 29.604 at 10:34:57; 24.8 at 10:35:00; 10 at 10:35:05; 14.2 at 10:35:10; 32.8 at 10:35:15; 10 at 10:35:20; 14.1 at 10:35:25; 27.1846 at 10:35:28; 28.5 at 10:35:30; 10 at 10:35:35; 14.1 at 10:35:40; 23.627 at 10:35:42; 27.4 at 10:35:45; 10 at 10:35:50; 14.1 at 10:35:55; 29.6 at 10:36:00; 10 at 10:36:05; 14.1 at 10:36:10; 23.9 at 10:36:15; 10 at 10:36:20; 26.5 at 10:36:25; 29.6008 at 10:36:27; 12.1 at 10:36:30; 10 10:36:35-10:36:36; 19.6 at 10:36:40; 20.1 at 10:36:45; 10 at 10:36:50; 26.2623 at 10:36:54; 26.3 at 10:36:55; 10 10:37:00-10:37:05; 28.3 at 10:37:10; 10 10:37:15-10:37:17; 19.5 at 10:37:20; 21.0749 at 10:37:21; 25.4 at 10:37:25; 10 at 10:37:30; 14.1 at 10:37:35; 23.8203 at 10:37:39; 23.8 at 10:37:40; 10 at 10:37:45; 14.1 at 10:37:50; 29.4273 at 10:37:53; 29.6 at 10:37:55; 10 10:38:00-10:38:02; 19.6 at 10:38:05; 28.0411 at 10:38:07; 24.1 at 10:38:10; 10 at 10:38:15; 19.8 at 10:38:20; 18.3 at 10:38:25; 10 at 10:38:30; 19.5 at 10:38:35; 16.2365 at 10:38:38; 10.1 at 10:38:40; 10 10:38:43-10:38:45; 22.8057 at 10:38:48; 25.7 at 10:38:50; 10.3 at 10:38:55; 10 at 10:39:00; 21 at 10:39:05; 28.1 at 10:39:10; 11.168 at 10:39:11; 10 10:39:15-10:39:16; 19.5 at 10:39:20; 21.1 at 10:39:25; 10 at 10:39:30; 14.2 at 10:39:35; 28.4 at 10:39:40; 10 at 10:39:45; 14.1335 at 10:39:49; 14.1 at 10:39:50; 26.6473 at 10:39:54; 26.6 at 10:39:55; 10 10:39:58-10:40:00; 25.6 at 10:40:05; 22.6383 at 10:40:07; 10 10:40:10-10:40:15; 14.1 at 10:40:20; 24.5 at 10:40:25; 10 10:40:30-10:40:40; 24.8 at 10:40:45; 10 at 10:40:50; 13.8 at 10:40:55; 25.1 at 10:41:00; 10 10:41:05-10:41:12; 18.7 at 10:41:15; 16.1 at 10:41:20; 10 10:41:25-10:41:26; 19.6 at 10:41:30; 19.4 at 10:41:35; 10 at 10:41:40; 26.1 at 10:41:45; 10 10:41:50-10:41:55; 19.5469 at 10:41:58; 24.9 at 10:42:00; 15.8067 at 10:42:03; 10 10:42:05-10:42:10; 19.6 at 10:42:15; 22.1 at 10:42:20; 10 at 10:42:25; 19.3 at 10:42:30; 18.7 at 10:42:35; 10 at 10:42:40; 25.4572 at 10:42:44; 25.5 at 10:42:45; 11.3 at 10:42:50; 14 at 10:42:55; 26.4 at 10:43:00; 10 10:43:05-10:43:07; 12.6 at 10:43:10; 26.2 at 10:43:15; 10 at 10:43:20; 14.1 at 10:43:25; 29.2 at 10:43:30; 10 10:43:34-10:43:35 |
| getcart      | no cap 10:33:05–10:43:35 |
| postcart     | no cap 10:33:05–10:43:35 |
| emptycart    | no cap 10:33:05–10:43:35 |

### tf1rg0-2

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 12:42:40–12:53:10 |
| postcheckout | no cap 12:42:40-12:43:20; 15.4 at 12:43:25; 17 at 12:43:30; 19.8 at 12:43:31; 20 at 12:43:35; no cap 12:43:39-12:43:40; 25 at 12:43:45; 14.1564 at 12:43:47; 10 12:43:50-12:43:55; 29.5 at 12:44:00; 10 12:44:05-12:44:10; 26.6 at 12:44:15; 10 12:44:20-12:44:25; 28.6 at 12:44:30; 14.7 at 12:44:35; 10 at 12:44:40; 26.9 at 12:44:45; 10 12:44:49-12:44:50; 10.8822 at 12:44:54; 10.9 at 12:44:55; 25.8276 at 12:44:58; 30.1 at 12:45:00; 10 12:45:05-12:45:10; 14.0458 at 12:45:11; 25.8 at 12:45:15; 10 12:45:20-12:45:25; 19.5 at 12:45:30; 14.1 at 12:45:35; 10 at 12:45:40; 24.1 at 12:45:45; 28.992 at 12:45:47; 22.8 at 12:45:50; 10 12:45:51-12:45:55; 19.6 at 12:46:00; 13.8791 at 12:46:04; 13.9 at 12:46:05; 10 at 12:46:10; 22.2 at 12:46:15; 26.9375 at 12:46:17; 16.2 at 12:46:20; 10 at 12:46:25; 22.2 at 12:46:30; 30.6 at 12:46:35; 10 at 12:46:40; 14.1367 at 12:46:43; 19.5 at 12:46:45; 22.6 at 12:46:50; 10 12:46:55-12:46:56; 19.2 at 12:47:00; 20.6 at 12:47:05; 10 at 12:47:10; 25.1 at 12:47:15; 26.2 at 12:47:20; 10 at 12:47:25; 14.0308 at 12:47:27; 22.3 at 12:47:30; 23.5 at 12:47:35; 10 at 12:47:40; 19.7114 at 12:47:44; 19.7 at 12:47:45; 33 at 12:47:50; 23 at 12:47:52; 10 12:47:55-12:48:01; 19.7 at 12:48:05; 24.7 at 12:48:10; 10 at 12:48:15; 19.1109 at 12:48:19; 19.1 at 12:48:20; 25.9583 at 12:48:23; 20.2 at 12:48:25; 10 at 12:48:30; 23.2 at 12:48:35; 25.5 at 12:48:40; 11.7 at 12:48:45; 10 at 12:48:50; 28.5 at 12:48:55; 10 12:48:58-12:49:00; 14.1 at 12:49:05; 33 at 12:49:10; 10 at 12:49:15; 14.1 at 12:49:20; 31.2 at 12:49:25; 10 at 12:49:30; 19 at 12:49:35; 28.5 at 12:49:40; 15.3874 at 12:49:41; 10 12:49:45-12:49:46; 19.5 at 12:49:50; 21.2 at 12:49:55; 10 at 12:50:00; 26.4 at 12:50:05; 10 at 12:50:10; 13.9358 at 12:50:13; 19.5 at 12:50:15; 33 at 12:50:20; 11.9 at 12:50:25; 10 12:50:28-12:50:30; 25.9 at 12:50:35; 30.4691 at 12:50:37; 12 at 12:50:40; 10 at 12:50:45; 25.8 at 12:50:50; 14.9 at 12:50:55; 10 12:51:00-12:51:01; 19.6 at 12:51:05; 12.1 at 12:51:10; 10 at 12:51:15; 27 at 12:51:20; 10 12:51:24-12:51:25; 14.1 at 12:51:30; 28.8004 at 12:51:33; 29 at 12:51:35; 10 12:51:38-12:51:40; 14.1 at 12:51:45; 26.5336 at 12:51:47; 28.5 at 12:51:50; 10 12:51:55-12:52:00; 28.5 at 12:52:05; 10 at 12:52:10; 14.0747 at 12:52:14; 14.1 at 12:52:15; 29.3 at 12:52:20; 10 12:52:23-12:52:30; 28.6 at 12:52:35; 22.8797 at 12:52:36; 10 12:52:40-12:52:45; 24.9 at 12:52:50; 14.9 at 12:52:55; 10 at 12:53:00; 14.124 at 12:53:03; 19.5 at 12:53:05; 18 at 12:53:10 |
| getcart      | no cap 12:42:40–12:53:10 |
| postcart     | no cap 12:42:40–12:53:10 |
| emptycart    | no cap 12:42:40–12:53:10 |

### tf0rg1-1

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 09:15:20–09:26:15 |
| postcheckout | no cap 09:15:20–09:26:15 |
| getcart      | no cap 09:15:20–09:26:15 |
| postcart     | no cap 09:15:20–09:26:15 |
| emptycart    | no cap 09:15:20–09:26:15 |

### tf0rg1-2

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 14:29:40–14:40:35 |
| postcheckout | no cap 14:29:40–14:40:35 |
| getcart      | no cap 14:29:40–14:40:35 |
| postcart     | no cap 14:29:40–14:40:35 |
| emptycart    | no cap 14:29:40–14:40:35 |

### tf1rg1-1

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 10:06:55–10:17:50 |
| postcheckout | no cap 10:06:55-10:08:00; 13 at 10:08:05; no cap at 10:08:10; 20 10:08:14-10:08:15; no cap at 10:08:20; 15 at 10:08:25; 10 at 10:08:30; 19.3 at 10:08:35; no cap at 10:08:40; 15.0328 at 10:08:42; 10 at 10:08:45; 14 at 10:08:50; 19.4659 at 10:08:51; 31.2 at 10:08:55; 26 at 10:08:57; 10.2 at 10:09:00; 10 at 10:09:05; 13.9496 at 10:09:06; 23.5 at 10:09:10; 13.4 at 10:09:15; 10 at 10:09:20; 19 at 10:09:25; 13.688 at 10:09:29; 13.7 at 10:09:30; 10 at 10:09:35; 26.2 at 10:09:40; 12.4 at 10:09:45; 10 10:09:47-10:09:50; 19.4188 at 10:09:52; 30 at 10:09:55; 21.0426 at 10:09:57; 10 10:10:00-10:10:05; 14.1328 at 10:10:06; 26.4 at 10:10:10; 16 at 10:10:15; 10 at 10:10:20; 26.2187 at 10:10:24; 26.2 at 10:10:25; 12.3587 at 10:10:29; 12.4 at 10:10:30; 10 at 10:10:35; 14.1179 at 10:10:38; 19.6 at 10:10:40; 19.101 at 10:10:43; 11.8 at 10:10:45; 10 at 10:10:50; 29.4 at 10:10:55; 19.8758 at 10:10:57; 10 at 10:11:00; 14.2 at 10:11:05; 26.8 at 10:11:10; 10 at 10:11:15; 14.2 at 10:11:20; 28.5 at 10:11:25; 11.1857 at 10:11:28; 10 at 10:11:30; 14.1 at 10:11:35; 29 at 10:11:40; 15.4331 at 10:11:42; 10 10:11:45-10:11:50; 25.7 at 10:11:55; 15.1 at 10:12:00; 10 at 10:12:05; 27.2 at 10:12:10; 10 10:12:15-10:12:20; 24 at 10:12:25; 12.6777 at 10:12:28; 10 at 10:12:30; 14.0951 at 10:12:33; 19.8 at 10:12:35; 28.849 at 10:12:37; 19.4 at 10:12:40; 10 10:12:42-10:12:45; 19.5 at 10:12:50; 12.2 at 10:12:55; 10 at 10:13:00; 32.3 at 10:13:05; 10 10:13:09-10:13:10; 14.1 at 10:13:15; 31.5 at 10:13:20; 13.3872 at 10:13:23; 10 at 10:13:25; 14.1389 at 10:13:28; 19.6 at 10:13:30; 18.1 at 10:13:35; 10 at 10:13:40; 14.1411 at 10:13:41; 25.7 at 10:13:45; 17.2 at 10:13:50; 10 at 10:13:55; 19.6 at 10:14:00; 12.6 at 10:14:05; 10 10:14:09-10:14:10; 23.5018 at 10:14:14; 23.5 at 10:14:15; 10 at 10:14:20; 19 at 10:14:25; 26.0316 at 10:14:28; 22.5 at 10:14:30; 10 10:14:33-10:14:35; 14.1435 at 10:14:38; 19.6 at 10:14:40; 13.2 at 10:14:45; 10 at 10:14:50; 14.1276 at 10:14:52; 24.4 at 10:14:55; 17.4 at 10:15:00; 10 at 10:15:05; 25.6 at 10:15:10; 10 10:15:15-10:15:20; 25.7 at 10:15:25; 10 10:15:28-10:15:35; 25.9 at 10:15:40; 16.1803 at 10:15:42; 10 10:15:45-10:15:50; 28.3 at 10:15:55; 10 10:16:00-10:16:05; 26.1 at 10:16:10; 10 10:16:15-10:16:20; 26.2 at 10:16:25; 10 at 10:16:30; 13.6 at 10:16:35; 23.7328 at 10:16:37; 31 at 10:16:40; 14.5278 at 10:16:42; 10 10:16:45-10:16:50; 19.1152 at 10:16:51; 29.7 at 10:16:55; 10 10:17:00-10:17:05; 25.4379 at 10:17:09; 25.4 at 10:17:10; 10 10:17:15-10:17:20; 26.3 at 10:17:25; 19.4081 at 10:17:27; 10 10:17:30-10:17:32; 14.1 at 10:17:35; 24.1608 at 10:17:37; 30.8 at 10:17:40; 10 10:17:45-10:17:46; 14.2 at 10:17:50 |
| getcart      | no cap 10:06:55–10:17:50 |
| postcart     | no cap 10:06:55–10:17:50 |
| emptycart    | no cap 10:06:55–10:17:50 |

### tf1rg1-2

| API          | Live caps |
| ------------ | --------- |
| getproduct   | no cap 12:16:25–12:27:25 |
| postcheckout | no cap 12:16:25-12:17:45; 18 at 12:17:46; no cap at 12:17:50; 17 at 12:17:55; 10 12:17:57-12:18:00; 18.9 at 12:18:05; 17.2821 at 12:18:09; 17.3 at 12:18:10; 10 at 12:18:15; 28 at 12:18:20; 10.9 at 12:18:25; 10 at 12:18:30; 30.5 at 12:18:35; 10.2 at 12:18:40; 10 12:18:43-12:18:45; 28 at 12:18:50; 12.8 at 12:18:55; 10 at 12:19:00; 19.7 at 12:19:05; 14.3 at 12:19:10; 10 12:19:13-12:19:15; 27.1 at 12:19:20; 23.4482 at 12:19:22; 10 12:19:25-12:19:30; 14.0004 at 12:19:31; 25.8 at 12:19:35; 10 12:19:40-12:19:45; 27.9 at 12:19:50; 10 12:19:55-12:20:00; 27.7 at 12:20:05; 10 12:20:10-12:20:15; 25.3 at 12:20:20; 16 at 12:20:25; 10 at 12:20:30; 14.5 at 12:20:35; 29.3 at 12:20:40; 10 12:20:44-12:20:48; 14.1 at 12:20:50; 26.5093 at 12:20:52; 24.3 at 12:20:55; 10 12:21:00-12:21:05; 24.2 at 12:21:10; 26 at 12:21:15; 10 12:21:20-12:21:25; 21.6898 at 12:21:28; 25.4 at 12:21:30; 10 12:21:35-12:21:40; 25.7 at 12:21:45; 20.2349 at 12:21:46; 10 12:21:50-12:21:55; 24.7 at 12:22:00; 10 at 12:22:05; 19.5 at 12:22:10; 27.8253 at 12:22:12; 14.2 at 12:22:15; 10 at 12:22:20; 14.0052 at 12:22:21; 25.8 at 12:22:25; 10 12:22:30-12:22:35; 27.8 at 12:22:40; 10 at 12:22:45; 14.1 at 12:22:50; 27.9 at 12:22:55; 10 at 12:23:00; 23.3 at 12:23:05; 15.885 at 12:23:09; 15.9 at 12:23:10; 10 at 12:23:15; 19.4048 at 12:23:18; 25.8 at 12:23:20; 10 12:23:25-12:23:30; 14.151 at 12:23:31; 24.3 at 12:23:35; 12.1 at 12:23:40; 10 12:23:44-12:23:45; 24.6 at 12:23:50; 13.9 at 12:23:55; 10 12:23:57-12:24:05; 19.6 at 12:24:10; 10 12:24:15-12:24:20; 27.4375 at 12:24:24; 27.4 at 12:24:25; 10 at 12:24:30; 14.1 at 12:24:35; 25.6949 at 12:24:37; 33 at 12:24:40; no cap at 12:24:41; 21 at 12:24:43; 13.1 at 12:24:45; 10 at 12:24:50; 14.1 at 12:24:55; 25.941 at 12:24:56; 29.1 at 12:25:00; 10 at 12:25:05; 18.8 at 12:25:10; 17.6 at 12:25:15; 10 at 12:25:20; 18.7117 at 12:25:22; 28.3 at 12:25:25; 24.3726 at 12:25:26; 10.2 at 12:25:30; 10 at 12:25:35; 26.4 at 12:25:40; 12.3 at 12:25:45; 10 12:25:47-12:25:50; 19.6 at 12:25:55; 31.4 at 12:26:00; 10 12:26:04-12:26:10; 19.4812 at 12:26:12; 27.1 at 12:26:15; 12.4 at 12:26:20; 10 at 12:26:25; 24.4 at 12:26:30; 15.5 at 12:26:35; 10 12:26:38-12:26:40; 14.0581 at 12:26:42; 24.6 at 12:26:45; 18.4 at 12:26:50; 10 at 12:26:55; 24.5 at 12:27:00; 10 12:27:05-12:27:10; 25.9 at 12:27:15; 10 12:27:20-12:27:25 |
| getcart      | no cap 12:16:25–12:27:25 |
| postcart     | no cap 12:16:25–12:27:25 |
| emptycart    | no cap 12:16:25–12:27:25 |

## Per arm, or per hold

tf1rg0-1 has no `retryguard.log`, so nothing shed and nothing climbed. `frontend → checkoutservice` file streak is 14 s, with 235 ticks above 0.5, volume rpr 0.870, and outbound retries 8,304. `grpc_4` is 0 on the four read callees. Checkout is detector-hot at 82.8%. No other service is.

tf1rg0-2 has no log. The checkout file streak is 9 s, with 208 ticks above 0.5, volume rpr 0.838, and retries 8,221. `grpc_4` is 0. Checkout is detector-hot at 81.2%. No other service is.

tf0rg1-1 shed `frontend → checkoutservice` once, from 3 attempts, at rpr 1.50, with `elapsed_s=30` and `consecutive_high=31`. It did not climb: 0→1, 1→2, and 2→3 are 0, and the OFF-window `low` peaks at 3. The file streak is 32 s. Retries are 1,151 and volume rpr is 0.067. `grpc_4` is 0 except adservice at 4. Checkout is detector-hot at 88.4%. No other service is.

tf0rg1-2 shed `frontend → checkoutservice` once, from 3 attempts, at rpr 2.06, with `elapsed_s=30` and `consecutive_high=27`. It did not climb. The OFF-window `low` peaks at 1. The file streak is 32 s. Retries are 1,146 and volume rpr is 0.067. `grpc_4` is 0. Checkout is detector-hot at 89.3%. No other service is.

tf1rg1-1 has a log and no shed and no climb. The controller `high` on checkout peaks at 10. The file streak is 10 s, with 232 ticks above 0.5, volume rpr 0.855, and retries 8,300. `grpc_4` is 0. Checkout is detector-hot at 77.2%. No other service is.

tf1rg1-2 has a log and no shed and no climb. The controller `high` on checkout peaks at 10. The file streak is 11 s, with 234 ticks above 0.5, volume rpr 0.908, and retries 8,640, plus 1 retry into recommendationservice. `grpc_4` is 0. Checkout is detector-hot at 78.5%. No other service is.

## Related links

How to write this guide: [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). How (a), (b), and (c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Edge mode, including the 15 s climb: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) (Edge mode). The locked mix 175 / 30 / 70 / 90 / 5 is written up for S1 both-off in [2026-10-08-s1-both-off-run8.md](2026-10-08-s1-both-off-run8.md). There is no earlier guide for these checkout 300 m Set B holds.
