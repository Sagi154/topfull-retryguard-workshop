# Set B Scenario 4A, catalog at 300 m

## Setup

600 s holds. Mix getproduct 175 / postcheckout 30 / getcart 70 / postcart 90 / emptycart 5, `spawn_rate` 50. Paper-C1, with `productcatalogservice` at 300 m. Frontend is pinned at 4 replicas. Every other service is 1 replica. Per-pod limits: frontend 1150, checkoutservice 800, recommendationservice 1150, productcatalogservice 300, cartservice 800, currencyservice 770, shippingservice 770, adservice 1150, paymentservice 155, emailservice 120, redis-cart 540. `retry_metric` is `edge_rpr` and `reenable_rejection` is 0.15. Arms: TopFull on and RetryGuard off (`tf1rg0`), TopFull off and RetryGuard on (`tf0rg1`), both on (`tf1rg1`). Two repeats each. The result folders do not record the cool-off. Folders:

- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf1rg0_rep1`
- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf1rg0_rep2`
- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf0rg1_rep1`
- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf0rg1_rep2`
- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf1rg1_rep1`
- `experiments/results/campaign_48/S4A_topology_position_A/study2_s4a_tf1rg1_rep2`

## Index

Column order follows this index. A bold bar separates the arms.


| Arm                            | Slots                  |
| ------------------------------ | ---------------------- |
| TopFull on, RetryGuard off     | tf1rg0-1, tf1rg0-2     |
| TopFull off, RetryGuard on    | tf0rg1-1, tf0rg1-2     |
| TopFull on, RetryGuard on      | tf1rg1-1, tf1rg1-2     |


`tf1rg0-1` is `study2_s4a_tf1rg0_rep1`. The other five labels match the same way.

## Gate

Five holds passed. `tf1rg1-2` failed the inbound-gap check and stays in the tables: the files still cover the hold.

`service_capacity.json` matches the pin on every hold (frontend 1150 m × 4, productcatalogservice 300 m × 1, the other limits above at 1 replica). Frontend `replica_count` is 4 on every `resource_usage.csv` sample (134, 134, 138, 139, 139, 140). No service has a replica count of 0. `retryguard.log` is absent on `tf1rg0-1` and `tf1rg0-2`. The four RetryGuard logs start with `metric=edge_rpr` and `reenable_rejection=0.15`, and none contains `PATCH_FAIL`.


| Check | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| Locust `total.csv` rows | 570 | 566 | **┃** | 575 | 568 | **┃** | 569 | 559 |
| Mesh span (s) | 692 | 692 | **┃** | 715 | 717 | **┃** | 715 | 720 |
| Inbound gaps ≥ 1.5 s | 121 of 7491 | 220 of 7392 | **┃** | 0 of 7865 | 0 of 7887 | **┃** | 33 of 7832 | 1584 of 6336 |


`tf1rg1-2` has 1584 of 6336 pairs at 1.5 s or longer. On `productcatalogservice` that is 144 of 576 pairs, each 2.0 s (25%), above the 10% line for the controlled service. Mesh span is 720 s and the longest gap is 2.0 s, so the columns stay filled. The other five holds are at or under 3% of pairs at 2.0 s on `productcatalogservice` (11/681, 20/672, 0/715, 0/717, 3/712).

## Edge-mode bars

Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.10.

That opening line is the score with `tf1rg0-1` first. That folder has no `retryguard.log`, so the printed re-enable bar is the 0.10 default. The four RetryGuard START lines set `reenable_rejection=0.15`. The under-bar table uses 0.15 on those four columns and 0.10 on `tf1rg0-1` and `tf1rg0-2`.

Shed and 0→1 take `interval_samples` seconds of row timestamps. The START line records `interval_samples=30s`. Climbs 1→2 and 2→3 take 15 s (`CLIMB_INTERVAL_SECONDS`). These holds are 2026-10-09, so the climb is 15 s. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The file streak is seconds from the first consecutive scored tick above 0.5 to the last. One tick is 0 seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. A TopFull-only cell has no parenthetical because there is no log. **Bold** is a file streak of at least 30 seconds. No cell here reaches 30 seconds.

Only `frontend → checkoutservice` and `frontend → recommendationservice` have a tick above the shed bar or a retry delta. The other 12 controlled edges are at retry delta 0 with no tick above 0.5 on every hold.

Longest streak in seconds of rpr > 0.5, then the number of scored ticks above 0.5.


| Edge | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → recommendationservice | 6 / 18 | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 2 / 4 (2) |


Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.


| Edge | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.000 / 0.03 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 |
| frontend → recommendationservice | 0.035 / 2.46 / 0.029 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.011 / 1.27 / 0.013 |


Climb streaks while that attempt cap is in force: samples at 1 attempt with rpr at or under 0.17, then samples at 2 attempts with rpr at or under 0.33. An em dash means that cap never applied. Every cell is an em dash: no edge sat at 1 attempt or at 2 attempts.


| Edge | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |


## Rejection, beside (a)

The 0.20 streak sits beside (a). It is the `(Δ5xx + Δresets) / Δtotal` series from `service_inbound.csv`. A non-positive total delta breaks the streak and counts for neither side. **Bold** in the 0.20 table is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. No controlled service reaches a streak of 30.

Longest streak above 0.20, then the count of samples above 0.20.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 2 / 4 | 2 / 2 | **┃** | 1 / 1 | 1 / 1 | **┃** | 0 / 0 | 1 / 2 |
| checkoutservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


Longest streak strictly under the re-enable bar, then the count of samples under that bar. The bar is 0.10 on `tf1rg0-1` and `tf1rg0-2`, and 0.15 on the four RetryGuard holds.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 534 / 596 | 591 / 591 | **┃** | 613 / 613 | 612 / 612 | **┃** | 609 / 609 | 314 / 468 |
| checkoutservice | 601 / 601 | 591 / 591 | **┃** | 612 / 612 | 612 / 612 | **┃** | 609 / 609 | 469 / 469 |
| recommendationservice | 533 / 592 | 592 / 592 | **┃** | 612 / 612 | 612 / 612 | **┃** | 609 / 609 | 470 / 470 |
| paymentservice | 601 / 601 | 592 / 592 | **┃** | 612 / 612 | 612 / 612 | **┃** | 609 / 609 | 469 / 469 |
| emailservice | 601 / 601 | 592 / 592 | **┃** | 611 / 611 | 612 / 612 | **┃** | 609 / 609 | 469 / 469 |
| productcatalogservice | 602 / 602 | 593 / 593 | **┃** | 613 / 613 | 613 / 613 | **┃** | 609 / 609 | 470 / 470 |
| cartservice | 602 / 602 | 593 / 593 | **┃** | 613 / 613 | 613 / 613 | **┃** | 609 / 609 | 470 / 470 |
| currencyservice | 602 / 602 | 593 / 593 | **┃** | 613 / 613 | 613 / 613 | **┃** | 610 / 610 | 470 / 470 |
| shippingservice | 602 / 602 | 593 / 593 | **┃** | 613 / 613 | 613 / 613 | **┃** | 609 / 609 | 469 / 469 |
| adservice | 601 / 601 | 591 / 591 | **┃** | 611 / 611 | 612 / 612 | **┃** | 609 / 609 | 469 / 469 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


`grpc_4 / grpc_14` for the four read callees. These two deltas are not in the 0.20 numerator above.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 4,019 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1,962 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


## (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as ticks/rows (share%). **Bold** is a share of at least 0.5.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| checkoutservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| recommendationservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| paymentservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| emailservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| productcatalogservice | **579/638 (90.8%)** | **582/637 (91.4%)** | **┃** | **586/662 (88.5%)** | **576/662 (87.0%)** | **┃** | **587/661 (88.8%)** | **583/664 (87.8%)** |
| cartservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| currencyservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| shippingservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| adservice | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |
| redis-cart | 0/638 (0.0%) | 0/637 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/661 (0.0%) | 0/664 (0.0%) |


## (c) Retry volume

Outbound retry delta by target, the sum of positive `retry` increments on `service_edges.csv`. Every other target is 0.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| recommendationservice | 4,677 | 0 | **┃** | 0 | 0 | **┃** | 0 | 2,151 |


Inbound resets for all 11 services.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 137 | 90 | **┃** | 40 | 39 | **┃** | 24 | 94 |
| checkoutservice | 1 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| recommendationservice | 1,141 | 42 | **┃** | 10 | 15 | **┃** | 5 | 463 |
| paymentservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| productcatalogservice | 18 | 25 | **┃** | 9 | 22 | **┃** | 12 | 47 |
| cartservice | 1 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 1 | 0 |
| shippingservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 4 | 2 | **┃** | 3 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |


The same `grpc_4 / grpc_14` pair is what the retry policy counts on the four read callees.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 4,019 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1,962 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |


## RetryGuard toggles

`tf1rg0-1` and `tf1rg0-2` have no `retryguard.log`. The four RetryGuard holds have a log and no transition lines, so there is no timestamp log.

`ON→OFF` is the shed to 0 attempts. `0→1`, `1→2`, and `2→3` are the climb steps.


| Hold | Edge | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | --- | ---: | ---: | ---: | ---: |
| tf0rg1-1 | — | 0 | 0 | 0 | 0 |
| tf0rg1-2 | — | 0 | 0 | 0 | 0 |
| tf1rg1-1 | — | 0 | 0 | 0 | 0 |
| tf1rg1-2 | — | 0 | 0 | 0 | 0 |


## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.


| API | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 163.7 | 167.4 | **┃** | 168.0 | 167.7 | **┃** | 166.3 | 165.7 |
| postcheckout | 27.6 | 28.7 | **┃** | 28.8 | 28.7 | **┃** | 28.8 | 28.2 |
| getcart | 65.3 | 67.0 | **┃** | 67.2 | 67.1 | **┃** | 67.0 | 66.1 |
| postcart | 85.9 | 86.2 | **┃** | 86.3 | 86.3 | **┃** | 86.1 | 86.0 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |


## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.


| API | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.019 | 0.004 | **┃** | 0.000 | 0.000 | **┃** | 0.011 | 0.010 |
| postcheckout | 0.034 | 0.001 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.017 |
| getcart | 0.021 | 0.002 | **┃** | 0.000 | 0.000 | **┃** | 0.002 | 0.013 |
| postcart | 0.005 | 0.002 | **┃** | 0.000 | 0.000 | **┃** | 0.004 | 0.003 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |


## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.


| API | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 433 | 363 | **┃** | 272 | 348 | **┃** | 228 | 396 |
| postcheckout | 451 | 370 | **┃** | 311 | 363 | **┃** | 258 | 403 |
| getcart | 375 | 277 | **┃** | 217 | 277 | **┃** | 185 | 341 |
| postcart | 100 | 101 | **┃** | 94 | 96 | **┃** | 87 | 97 |
| emptycart | 13 | 21 | **┃** | 14 | 14 | **┃** | 14 | 15 |


## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s. redis-cart arrival is 0.0 because its `total` column does not rise.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 310.6 | 313.2 | **┃** | 303.9 | 303.1 | **┃** | 302.2 | 299.7 |
| checkoutservice | 24.7 | 25.4 | **┃** | 24.6 | 24.6 | **┃** | 24.6 | 24.1 |
| recommendationservice | 237.1 | 232.6 | **┃** | 225.8 | 225.2 | **┃** | 224.3 | 225.4 |
| paymentservice | 24.7 | 25.4 | **┃** | 24.6 | 24.6 | **┃** | 24.6 | 24.1 |
| emailservice | 24.7 | 25.4 | **┃** | 24.6 | 24.6 | **┃** | 24.6 | 24.1 |
| productcatalogservice | 1604.8 | 1619.5 | **┃** | 1572.0 | 1567.9 | **┃** | 1561.6 | 1548.3 |
| cartservice | 335.2 | 338.6 | **┃** | 328.5 | 327.7 | **┃** | 326.8 | 323.7 |
| currencyservice | 460.4 | 465.2 | **┃** | 451.5 | 450.4 | **┃** | 448.6 | 444.5 |
| shippingservice | 107.7 | 110.1 | **┃** | 106.8 | 106.5 | **┃** | 106.7 | 104.6 |
| adservice | 146.5 | 147.8 | **┃** | 143.6 | 143.2 | **┃** | 142.2 | 141.4 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |


## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. redis-cart has no rising `rq_time_count`, so the cell is an em dash.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 206 | 189 | **┃** | 142 | 180 | **┃** | 115 | 202 |
| checkoutservice | 68 | 73 | **┃** | 70 | 66 | **┃** | 74 | 59 |
| recommendationservice | 118 | 71 | **┃** | 50 | 83 | **┃** | 30 | 110 |
| paymentservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| emailservice | 8 | 10 | **┃** | 7 | 7 | **┃** | 10 | 6 |
| productcatalogservice | 13 | 15 | **┃** | 11 | 13 | **┃** | 8 | 13 |
| cartservice | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 3 |
| currencyservice | 3 | 3 | **┃** | 2 | 3 | **┃** | 2 | 3 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — |


## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. redis-cart has no bucket pair, so the cell is an em dash.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.049 | 0.002 | **┃** | 0.000 | 0.002 | **┃** | 0.000 | 0.028 |
| checkoutservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| recommendationservice | 0.030 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.014 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — |


## CPU

Per-pod quota, replica mode, then mean / max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota. Quota and replica mode are the same on every hold.


| Service | Quota | Replicas | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 | 4 | 940 / 1106 | 950 / 1114 | **┃** | 920 / 1115 | 901 / 1114 | **┃** | 963 / 1190 | 904 / 1120 |
| checkoutservice | 800 | 1 | 374 / 499 | 408 / 500 | **┃** | 359 / 449 | 368 / 464 | **┃** | 347 / 444 | 391 / 520 |
| recommendationservice | 1150 | 1 | 439 / 658 | 460 / 547 | **┃** | 421 / 517 | 419 / 524 | **┃** | 430 / 556 | 422 / 597 |
| paymentservice | 155 | 1 | 25 / 33 | 25 / 32 | **┃** | 24 / 31 | 22 / 31 | **┃** | 23 / 31 | 24 / 33 |
| emailservice | 120 | 1 | 49 / 61 | 52 / 62 | **┃** | 47 / 57 | 48 / 59 | **┃** | 47 / 59 | 48 / 60 |
| productcatalogservice | 300 | 1 | 266 / 300 | 264 / 300 | **┃** | 256 / 300 | 255 / 300 | **┃** | 255 / 300 | 256 / 300 |
| cartservice | 800 | 1 | 238 / 339 | 247 / 380 | **┃** | 232 / 302 | 232 / 361 | **┃** | 241 / 331 | 229 / 294 |
| currencyservice | 770 | 1 | 242 / 291 | 244 / 292 | **┃** | 239 / 318 | 232 / 300 | **┃** | 237 / 299 | 237 / 300 |
| shippingservice | 770 | 1 | 64 / 80 | 66 / 79 | **┃** | 60 / 75 | 61 / 76 | **┃** | 60 / 75 | 62 / 81 |
| adservice | 1150 | 1 | 99 / 119 | 102 / 117 | **┃** | 96 / 113 | 96 / 118 | **┃** | 95 / 118 | 97 / 119 |
| redis-cart | 540 | 1 | 30 / 42 | 31 / 42 | **┃** | 30 / 42 | 29 / 42 | **┃** | 32 / 45 | 30 / 44 |


## CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out. No sample here has replica count 0.


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.20 / 0.24 | 0.21 / 0.24 | **┃** | 0.20 / 0.24 | 0.20 / 0.24 | **┃** | 0.21 / 0.26 | 0.20 / 0.24 |
| checkoutservice | 0.47 / 0.62 | 0.51 / 0.62 | **┃** | 0.45 / 0.56 | 0.46 / 0.58 | **┃** | 0.43 / 0.56 | 0.49 / 0.65 |
| recommendationservice | 0.38 / 0.57 | 0.40 / 0.48 | **┃** | 0.37 / 0.45 | 0.36 / 0.46 | **┃** | 0.37 / 0.48 | 0.37 / 0.52 |
| paymentservice | 0.16 / 0.21 | 0.16 / 0.21 | **┃** | 0.15 / 0.20 | 0.15 / 0.20 | **┃** | 0.15 / 0.20 | 0.16 / 0.21 |
| emailservice | 0.41 / 0.51 | 0.43 / 0.52 | **┃** | 0.39 / 0.47 | 0.40 / 0.49 | **┃** | 0.39 / 0.49 | 0.40 / 0.50 |
| productcatalogservice | 0.89 / 1.00 | 0.88 / 1.00 | **┃** | 0.85 / 1.00 | 0.85 / 1.00 | **┃** | 0.85 / 1.00 | 0.85 / 1.00 |
| cartservice | 0.30 / 0.42 | 0.31 / 0.47 | **┃** | 0.29 / 0.38 | 0.29 / 0.45 | **┃** | 0.30 / 0.41 | 0.29 / 0.37 |
| currencyservice | 0.31 / 0.38 | 0.32 / 0.38 | **┃** | 0.31 / 0.41 | 0.30 / 0.39 | **┃** | 0.31 / 0.39 | 0.31 / 0.39 |
| shippingservice | 0.08 / 0.10 | 0.09 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.11 |
| adservice | 0.09 / 0.10 | 0.09 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 |
| redis-cart | 0.06 / 0.08 | 0.06 / 0.08 | **┃** | 0.06 / 0.08 | 0.05 / 0.08 | **┃** | 0.06 / 0.08 | 0.06 / 0.08 |


## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).


| Service | tf1rg0-1 | tf1rg0-2 | **┃** | tf0rg1-1 | tf0rg1-2 | **┃** | tf1rg1-1 | tf1rg1-2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.254 | 0.256 | **┃** | 0.254 | 0.252 | **┃** | 0.271 | 0.254 |
| checkoutservice | 0.736 | 0.740 | **┃** | 0.662 | 0.695 | **┃** | 0.675 | 0.735 |
| recommendationservice | 0.693 | 0.517 | **┃** | 0.482 | 0.493 | **┃** | 0.512 | 0.669 |
| paymentservice | 0.381 | 0.387 | **┃** | 0.368 | 0.503 | **┃** | 0.368 | 0.484 |
| emailservice | 0.800 | 0.733 | **┃** | 0.758 | 0.717 | **┃** | 0.700 | 0.742 |
| productcatalogservice | 1.067 | 1.043 | **┃** | 1.040 | 1.040 | **┃** | 1.037 | 1.040 |
| cartservice | 0.458 | 0.496 | **┃** | 0.440 | 0.485 | **┃** | 0.470 | 0.448 |
| currencyservice | 0.412 | 0.453 | **┃** | 0.466 | 0.465 | **┃** | 0.436 | 0.457 |
| shippingservice | 0.135 | 0.139 | **┃** | 0.131 | 0.131 | **┃** | 0.136 | 0.135 |
| adservice | 0.177 | 0.127 | **┃** | 0.123 | 0.150 | **┃** | 0.123 | 0.134 |
| redis-cart | 0.204 | 0.200 | **┃** | 0.204 | 0.207 | **┃** | 0.187 | 0.189 |


## TopFull live caps

A live read has `threshold_fresh=1` and a threshold above 0. A live 10000 is no cap. A live 0 is an empty read and is left out. The TopFull-on series are long, so the cells keep the scorer's collapsed spans. Times are UTC. `emptycart` is no cap on every live read of every hold. On `tf0rg1-1` and `tf0rg1-2`, `postcart` is no cap on every live read as well.

### tf1rg0-1

| API | Live caps |
| --- | --- |
| getproduct | no cap 11:25:00–11:25:45; 83.8 at 11:25:50; no cap at 11:25:53; 101 at 11:25:55; no cap 11:25:59–11:26:00; 152.2 at 11:26:05; 160.6 at 11:26:10; 165.716 at 11:26:12; no cap at 11:26:15; 175 11:26:20–11:26:25; no cap 11:26:30–11:26:35; 175 at 11:26:40; no cap at 11:26:43; 175 11:26:45–11:26:50; no cap at 11:26:55; 175 at 11:27:00; no cap at 11:27:01; 175 11:27:05–11:27:10; no cap 11:27:15–11:27:20; 175 at 11:27:25; no cap at 11:27:28; 175 11:27:29–11:27:35; no cap at 11:27:36; 175 11:27:40–11:27:45; no cap at 11:27:50; 175 at 11:27:55; no cap at 11:27:56; 175 11:28:00–11:28:05; no cap 11:28:10–11:28:15; 175 11:28:20–11:28:33; no cap 11:28:35–11:28:40; 175 at 11:28:45; no cap at 11:28:48; 175 11:28:50–11:28:51; no cap 11:28:55–11:29:00; 175 at 11:29:05; no cap at 11:29:06; 175 11:29:10–11:29:16; no cap 11:29:20–11:29:25; 175 at 11:29:30; no cap at 11:29:31; 175 at 11:29:35; no cap at 11:29:40; 175 at 11:29:45; no cap at 11:29:50; 175 at 11:29:55; no cap at 11:29:56; 175 11:30:00–11:30:05; no cap at 11:30:10; 175 at 11:30:15; no cap 11:30:20–11:30:25; 175 11:30:30–11:30:40; no cap at 11:30:45; 175 at 11:30:50; no cap at 11:30:51; 175 11:30:55–11:31:00; no cap 11:31:05–11:31:10; 175 11:31:15–11:31:25; no cap 11:31:30–11:31:35; 175 at 11:31:40; no cap at 11:31:43; 175 11:31:45–11:31:50; no cap 11:31:52–11:32:01; 175 11:32:05–11:32:10; no cap at 11:32:15; 180.472 at 11:32:19; 180.5 at 11:32:20; 175 at 11:32:25; no cap at 11:32:30; 175 11:32:32–11:32:41; no cap 11:32:45–11:32:50; 175 11:32:55–11:33:05; no cap 11:33:10–11:33:15; 175 at 11:33:20; no cap at 11:33:23; 175 11:33:25–11:33:33; no cap 11:33:35–11:33:40; 175 at 11:33:42; 182.1 at 11:33:45; 175 at 11:33:50; no cap at 11:33:55; 175 11:33:58–11:34:05; no cap at 11:34:07; 175 at 11:34:08; no cap 11:34:10–11:34:15; 175 at 11:34:20; 172 at 11:34:25; 162.7 at 11:34:30; 157.9 at 11:34:35; 153.361 at 11:34:39; 153.4 at 11:34:40; 161.4 at 11:34:45; 171.4 at 11:34:50; 175 at 11:34:55; no cap at 11:34:58; 175 11:35:00–11:35:05; no cap 11:35:07–11:35:10; 175 at 11:35:15; no cap at 11:35:16; 170.3 at 11:35:20; 168.02 at 11:35:21; 164.5 at 11:35:25; 158.723 at 11:35:29; 158.7 at 11:35:30; 155.935 at 11:35:33; 155.9 at 11:35:35 |
| postcheckout | no cap 11:25:00–11:25:45; 16.5 at 11:25:50; no cap at 11:25:53; 18 at 11:25:55; no cap 11:25:59–11:26:00; 26.4 at 11:26:05; 29.7 at 11:26:10; 33.7164 at 11:26:12; no cap at 11:26:15; 30 11:26:20–11:26:25; no cap 11:26:30–11:26:35; 30 at 11:26:40; no cap at 11:26:43; 30 11:26:45–11:26:50; no cap at 11:26:55; 30 at 11:27:00; no cap at 11:27:01; 30 11:27:05–11:27:10; no cap 11:27:15–11:27:20; 30 at 11:27:25; no cap at 11:27:28; 30 11:27:29–11:27:45; no cap at 11:27:50; 30 at 11:27:55; no cap at 11:27:56; 30 11:28:00–11:28:05; no cap 11:28:10–11:28:15; 30 11:28:20–11:28:33; no cap 11:28:35–11:28:40; 30 11:28:42–11:28:45; no cap at 11:28:48; 30 11:28:50–11:28:51; no cap 11:28:55–11:29:00; 30 at 11:29:05; no cap at 11:29:06; 30 11:29:10–11:29:16; no cap 11:29:20–11:29:25; 30 at 11:29:30; no cap at 11:29:31; 30 at 11:29:35; no cap at 11:29:40; 30 at 11:29:45; no cap at 11:29:50; 30 at 11:29:55; no cap at 11:29:56; 30 11:30:00–11:30:05; no cap at 11:30:10; 30 at 11:30:15; no cap 11:30:20–11:30:25; 30 11:30:30–11:30:40; no cap at 11:30:45; 30 at 11:30:50; no cap at 11:30:51; 30 11:30:55–11:31:00; no cap 11:31:05–11:31:10; 30 at 11:31:15; no cap at 11:31:18; 30 11:31:19–11:31:28; no cap 11:31:30–11:31:35; 30 at 11:31:40; no cap at 11:31:43; 30 11:31:45–11:31:50; no cap 11:31:52–11:32:01; 30 11:32:05–11:32:10; no cap at 11:32:15; 33 11:32:19–11:32:20; 30 at 11:32:25; no cap at 11:32:30; 30 11:32:32–11:32:41; no cap 11:32:45–11:32:50; 30 at 11:32:55; no cap at 11:32:58; 30 11:32:59–11:33:05; no cap 11:33:10–11:33:15; 30 at 11:33:20; no cap at 11:33:23; 30 11:33:25–11:33:33; no cap 11:33:35–11:33:40; 30 at 11:33:42; 33 at 11:33:45; 30 11:33:50–11:33:53; no cap 11:33:55–11:34:00; 30 at 11:34:05; no cap at 11:34:07; 30 at 11:34:08; no cap 11:34:10–11:34:15; 30 11:34:17–11:34:20; 29 at 11:34:25; 19.7 at 11:34:30; 14.9 at 11:34:35; 10.3613 at 11:34:39; 10.4 at 11:34:40; 18.6 at 11:34:45; 28.6 at 11:34:50; 30 at 11:34:55; no cap at 11:34:58; 30 11:35:00–11:35:05; no cap 11:35:07–11:35:10; 30 at 11:35:15; no cap at 11:35:16; 25.3 at 11:35:20; 23.02 at 11:35:21; 19.5 at 11:35:25; 13.723 at 11:35:29; 13.7 at 11:35:30; 10.935 at 11:35:33; 10.9 at 11:35:35 |
| getcart | no cap 11:25:00–11:25:45; 37.8 at 11:25:50; 42 at 11:25:55; no cap at 11:26:00; 62.7 at 11:26:05; 70.4 at 11:26:10; 71.7164 at 11:26:12; no cap at 11:26:15; 70 11:26:20–11:26:25; no cap 11:26:30–11:26:35; 70 at 11:26:40; no cap at 11:26:43; 70 11:26:45–11:26:50; no cap at 11:26:55; 70 at 11:27:00; no cap at 11:27:01; 70 11:27:05–11:27:10; no cap 11:27:15–11:27:20; 70 11:27:25–11:27:45; no cap at 11:27:50; 70 at 11:27:55; no cap at 11:27:56; 70 11:28:00–11:28:05; no cap 11:28:10–11:28:15; 70 11:28:20–11:28:30; no cap 11:28:35–11:28:40; 70 at 11:28:45; no cap at 11:28:48; 70 at 11:28:50; no cap 11:28:55–11:29:00; 70 at 11:29:05; no cap at 11:29:06; 70 11:29:10–11:29:16; no cap 11:29:20–11:29:25; 70 at 11:29:30; no cap at 11:29:31; 70 11:29:35–11:29:38; no cap at 11:29:40; 70 at 11:29:45; no cap at 11:29:50; 70 at 11:29:55; no cap at 11:29:56; 70 11:30:00–11:30:05; no cap at 11:30:10; 70 at 11:30:15; no cap 11:30:20–11:30:25; 70 11:30:30–11:30:40; no cap at 11:30:45; 70 11:30:50–11:31:00; no cap 11:31:05–11:31:10; 70 11:31:15–11:31:25; no cap 11:31:30–11:31:35; 70 at 11:31:40; no cap at 11:31:43; 70 11:31:45–11:31:50; no cap 11:31:52–11:32:00; 70 11:32:05–11:32:10; no cap at 11:32:15; 74.4716 at 11:32:19; 74.5 at 11:32:20; 70 11:32:25–11:32:41; no cap 11:32:45–11:32:50; 70 11:32:55–11:33:05; no cap 11:33:10–11:33:15; 70 at 11:33:20; no cap at 11:33:23; 70 11:33:25–11:33:30; no cap 11:33:35–11:33:40; 76.1 at 11:33:45; 70 at 11:33:50; no cap at 11:33:55; 70 11:33:59–11:34:05; no cap at 11:34:07; 70 at 11:34:08; no cap 11:34:10–11:34:15; 70 at 11:34:20; 67 at 11:34:25; 57.7 at 11:34:30; 52.9 at 11:34:35; 48.4 at 11:34:40; 53.1059 at 11:34:43; 56.4 at 11:34:45; 66.4 at 11:34:50; 70 at 11:34:55; no cap at 11:34:58; 70 11:35:00–11:35:05; no cap 11:35:07–11:35:10; 70 at 11:35:15; no cap at 11:35:16; 65.3 at 11:35:20; 63.02 at 11:35:21; 59.5 at 11:35:25; 53.723 at 11:35:29; 53.7 at 11:35:30; 50.9 at 11:35:35 |
| postcart | no cap 11:25:00–11:25:45; 45.8 at 11:25:50; no cap at 11:25:53; 53 at 11:25:55; no cap at 11:26:00; 80.3 at 11:26:05; 90.2 at 11:26:10; 89.7164 at 11:26:12; no cap at 11:26:15; 90 11:26:20–11:26:25; no cap 11:26:30–11:26:35; 90 at 11:26:40; no cap at 11:26:43; 90 11:26:45–11:26:50; no cap at 11:26:55; 90 at 11:27:00; no cap at 11:27:01; 90 11:27:05–11:27:10; no cap 11:27:15–11:27:20; 90 at 11:27:25; no cap at 11:27:28; 90 11:27:29–11:27:45; no cap at 11:27:50; 90 at 11:27:55; no cap at 11:27:56; 90 11:28:00–11:28:05; no cap 11:28:10–11:28:15; 90 11:28:20–11:28:30; no cap 11:28:35–11:28:40; 90 at 11:28:45; no cap at 11:28:48; 90 11:28:50–11:28:51; no cap 11:28:55–11:29:00; 90 at 11:29:05; no cap at 11:29:06; 90 11:29:10–11:29:16; no cap 11:29:20–11:29:25; 90 at 11:29:30; no cap at 11:29:31; 90 at 11:29:35; no cap at 11:29:40; 90 at 11:29:45; no cap at 11:29:50; 90 at 11:29:55; no cap at 11:29:56; 90 11:30:00–11:30:05; no cap at 11:30:10; 90 at 11:30:15; no cap 11:30:20–11:30:25; 90 11:30:30–11:30:40; no cap at 11:30:45; 90 at 11:30:50; no cap at 11:30:51; 90 11:30:55–11:31:00; no cap 11:31:05–11:31:10; 90 11:31:15–11:31:25; no cap 11:31:30–11:31:35; 90 at 11:31:40; no cap at 11:31:43; 90 11:31:45–11:31:50; no cap 11:31:52–11:32:01; 90 11:32:05–11:32:10; no cap at 11:32:15; 95.4716 at 11:32:19; 95.5 at 11:32:20; 90 at 11:32:25; no cap 11:32:29–11:32:30; 90 11:32:32–11:32:41; no cap 11:32:45–11:32:50; 90 11:32:55–11:33:05; no cap 11:33:10–11:33:15; 90 at 11:33:20; no cap at 11:33:23; 90 11:33:25–11:33:33; no cap 11:33:35–11:33:40; 97.1 at 11:33:45; 90 at 11:33:50; no cap at 11:33:55; 90 11:34:00–11:34:05; no cap at 11:34:07; 90 at 11:34:08; no cap 11:34:10–11:34:15; 90 11:34:20–11:34:25; 80.7 at 11:34:30; 75.9 at 11:34:35; 71.4 at 11:34:40; 76.1059 at 11:34:43; 79.4 at 11:34:45; 89.4 at 11:34:50; 90 at 11:34:55; no cap at 11:34:58; 90 11:35:00–11:35:05; no cap 11:35:07–11:35:10; 90 at 11:35:15; no cap at 11:35:16; 85.3 at 11:35:20; 83.02 at 11:35:21; 79.5 at 11:35:25; 73.723 at 11:35:29; 73.7 at 11:35:30; 70.935 at 11:35:33; 70.9 at 11:35:35 |
| emptycart | no cap 11:25:00–11:35:35 |

### tf1rg0-2

| API | Live caps |
| --- | --- |
| getproduct | no cap 13:34:40–13:35:20; 76 13:35:25–13:35:29; 106.2 at 13:35:30; 91.8 at 13:35:35; 129.652 at 13:35:38; 147.4 at 13:35:40; 143 at 13:35:42; 150.3 at 13:35:45; 166.3 at 13:35:50; 169.923 at 13:35:51; no cap at 13:35:54; 175 at 13:35:55; no cap at 13:35:56; 175 13:36:00–13:36:10; no cap 13:36:14–13:36:15; 175 at 13:36:20; no cap at 13:36:21; 175 13:36:25–13:36:31; no cap 13:36:35–13:36:40; 175 at 13:36:45; no cap at 13:36:48; 175 13:36:50–13:36:55; no cap 13:36:57–13:37:05; 175 at 13:37:10; no cap at 13:37:13; 175 13:37:14–13:37:23; no cap 13:37:25–13:37:30; 175 at 13:37:35; no cap at 13:37:38; 175 13:37:40–13:37:45; no cap at 13:37:47; 175 at 13:37:48; no cap 13:37:50–13:37:55; 175 at 13:38:00; no cap at 13:38:03; 175 13:38:05–13:38:10; no cap 13:38:12–13:38:20; 175 13:38:22–13:38:31; no cap 13:38:35–13:38:40; 175 at 13:38:45; no cap at 13:38:46; 175 13:38:50–13:38:56; no cap 13:39:00–13:39:05; 175 at 13:39:10; no cap at 13:39:11; 175 13:39:15–13:39:21; no cap 13:39:25–13:39:30; 175 13:39:35–13:39:45; no cap 13:39:50–13:39:55; 175 at 13:40:00; no cap 13:40:05–13:40:10; 175 13:40:15–13:40:25; no cap 13:40:30–13:40:35; 175 at 13:40:40; no cap at 13:40:41; 175 13:40:42–13:40:45; no cap at 13:40:48; 175 13:40:50–13:40:55; no cap 13:40:57–13:41:05; 175 at 13:41:10; no cap at 13:41:13; 175 13:41:15–13:41:20; no cap 13:41:25–13:41:30; 175 13:41:35–13:41:45; no cap 13:41:47–13:41:55; 175 13:41:57–13:42:10; no cap 13:42:12–13:42:20; 175 13:42:22–13:42:31; no cap 13:42:35–13:42:40; 175 at 13:42:45; no cap at 13:42:46; 175 13:42:50–13:43:00; no cap at 13:43:05; 175 at 13:43:10; no cap at 13:43:11; 175 13:43:15–13:43:21; no cap 13:43:25–13:43:30; 175 at 13:43:35; no cap at 13:43:36; 175 13:43:40–13:43:45; no cap 13:43:50–13:43:55; 175 at 13:44:00; no cap at 13:44:01; 175 13:44:05–13:44:10; no cap 13:44:15–13:44:20; 175 at 13:44:25; no cap at 13:44:26; 175 13:44:27–13:44:36; no cap 13:44:40–13:44:45; 175 at 13:44:50; no cap at 13:44:51; 175 13:44:52–13:45:01; no cap 13:45:05–13:45:10 |
| postcheckout | no cap 13:34:40–13:35:20; 14 at 13:35:25; 17.6 at 13:35:30; 22 at 13:35:35; 25.3 at 13:35:40; 25 at 13:35:42; 28.6 at 13:35:45; 30.3 at 13:35:50; no cap at 13:35:54; 30 at 13:35:55; no cap at 13:35:56; 30 13:36:00–13:36:10; no cap 13:36:14–13:36:15; 30 at 13:36:20; no cap at 13:36:21; 30 13:36:25–13:36:31; no cap 13:36:35–13:36:40; 30 at 13:36:45; no cap at 13:36:48; 30 13:36:50–13:36:55; no cap 13:36:57–13:37:05; 30 at 13:37:10; no cap at 13:37:13; 30 13:37:14–13:37:20; no cap at 13:37:22; 30 at 13:37:23; no cap 13:37:25–13:37:30; 30 at 13:37:35; no cap at 13:37:38; 30 13:37:40–13:37:45; no cap at 13:37:47; 30 at 13:37:48; no cap 13:37:50–13:37:55; 30 13:37:57–13:38:00; no cap at 13:38:03; 30 13:38:05–13:38:10; no cap 13:38:12–13:38:20; 30 13:38:22–13:38:31; no cap 13:38:35–13:38:40; 30 at 13:38:45; no cap at 13:38:46; 30 13:38:50–13:38:56; no cap 13:39:00–13:39:05; 30 at 13:39:10; no cap at 13:39:11; 30 13:39:15–13:39:21; no cap 13:39:25–13:39:30; 30 13:39:35–13:39:45; no cap 13:39:50–13:39:55; 30 at 13:40:00; no cap 13:40:05–13:40:10; 30 13:40:12–13:40:20; no cap 13:40:25–13:40:35; 30 at 13:40:40; no cap at 13:40:41; 30 13:40:42–13:40:45; no cap at 13:40:48; 30 13:40:50–13:40:55; no cap 13:40:57–13:41:05; 30 at 13:41:10; no cap at 13:41:13; 30 13:41:15–13:41:20; no cap 13:41:25–13:41:30; 30 13:41:35–13:41:45; no cap 13:41:47–13:41:56; 30 13:41:57–13:42:10; no cap 13:42:12–13:42:21; 30 13:42:22–13:42:31; no cap 13:42:35–13:42:40; 30 at 13:42:45; no cap at 13:42:46; 30 13:42:50–13:43:00; no cap at 13:43:05; 30 at 13:43:10; no cap at 13:43:11; 30 13:43:15–13:43:21; no cap 13:43:25–13:43:30; 30 at 13:43:35; no cap at 13:43:36; 30 13:43:40–13:43:45; no cap 13:43:50–13:43:55; 30 at 13:44:00; no cap at 13:44:01; 30 13:44:05–13:44:10; no cap 13:44:15–13:44:20; 30 at 13:44:25; no cap at 13:44:26; 30 13:44:27–13:44:36; no cap 13:44:40–13:44:45; 30 at 13:44:50; no cap at 13:44:51; 30 13:44:52–13:45:01; no cap 13:45:05–13:45:10 |
| getcart | no cap 13:34:40–13:35:20; 32 at 13:35:25; 44 at 13:35:30; 47.8 at 13:35:35; 59.4 at 13:35:40; 59 at 13:35:42; 66 at 13:35:45; 69.3 at 13:35:50; no cap at 13:35:54; 70 at 13:35:55; no cap at 13:35:56; 70 13:36:00–13:36:10; no cap 13:36:14–13:36:15; 70 at 13:36:20; no cap at 13:36:21; 70 13:36:25–13:36:31; no cap 13:36:35–13:36:40; 70 at 13:36:45; no cap at 13:36:48; 70 13:36:50–13:36:55; no cap 13:36:57–13:37:05; 70 at 13:37:10; no cap at 13:37:13; 70 13:37:14–13:37:23; no cap 13:37:25–13:37:30; 70 at 13:37:35; no cap at 13:37:38; 70 13:37:40–13:37:45; no cap at 13:37:47; 70 at 13:37:48; no cap 13:37:50–13:37:55; 70 13:37:57–13:38:00; no cap at 13:38:03; 70 13:38:05–13:38:10; no cap 13:38:12–13:38:20; 70 13:38:22–13:38:31; no cap 13:38:35–13:38:40; 70 at 13:38:45; no cap at 13:38:46; 70 13:38:50–13:38:56; no cap 13:39:00–13:39:05; 70 at 13:39:10; no cap at 13:39:11; 70 13:39:15–13:39:21; no cap 13:39:25–13:39:30; 70 13:39:35–13:39:45; no cap 13:39:50–13:39:55; 70 at 13:40:00; no cap 13:40:02–13:40:10; 70 13:40:15–13:40:20; no cap 13:40:24–13:40:35; 70 at 13:40:40; no cap at 13:40:41; 70 13:40:42–13:40:45; no cap at 13:40:48; 70 13:40:50–13:40:55; no cap 13:40:57–13:41:05; 70 at 13:41:10; no cap at 13:41:13; 70 13:41:15–13:41:20; no cap 13:41:25–13:41:30; 70 13:41:35–13:41:45; no cap 13:41:47–13:41:55; 70 13:41:57–13:42:10; no cap 13:42:12–13:42:20; 70 13:42:22–13:42:31; no cap 13:42:35–13:42:40; 70 at 13:42:45; no cap at 13:42:46; 70 13:42:50–13:43:00; no cap at 13:43:05; 70 at 13:43:10; no cap at 13:43:11; 70 13:43:15–13:43:21; no cap 13:43:25–13:43:30; 70 at 13:43:35; no cap at 13:43:36; 70 13:43:40–13:43:45; no cap 13:43:50–13:43:55; 70 at 13:44:00; no cap at 13:44:01; 70 13:44:05–13:44:10; no cap 13:44:15–13:44:20; 70 at 13:44:25; no cap at 13:44:26; 70 13:44:27–13:44:36; no cap 13:44:40–13:44:45; 70 at 13:44:50; no cap at 13:44:51; 70 13:44:52–13:45:01; no cap 13:45:05–13:45:10 |
| postcart | no cap 13:34:40–13:35:20; 41 13:35:25–13:35:30; 56.8 at 13:35:35; 74.8 at 13:35:38; 77 at 13:35:40; 75 at 13:35:42; 82.3 at 13:35:45; 88.3 at 13:35:50; 91.9229 at 13:35:51; no cap at 13:35:54; 90 at 13:35:55; no cap at 13:35:56; 90 13:36:00–13:36:10; no cap 13:36:14–13:36:15; 90 13:36:20–13:36:31; no cap 13:36:35–13:36:40; 90 at 13:36:45; no cap at 13:36:48; 90 13:36:50–13:36:55; no cap 13:37:00–13:37:05; 90 13:37:10–13:37:23; no cap 13:37:25–13:37:30; 90 13:37:35–13:37:48; no cap 13:37:50–13:37:55; 90 at 13:38:00; no cap at 13:38:03; 90 13:38:05–13:38:10; no cap 13:38:12–13:38:20; 90 13:38:25–13:38:31; no cap 13:38:35–13:38:40; 90 at 13:38:45; no cap at 13:38:46; 90 13:38:50–13:38:56; no cap 13:39:00–13:39:05; 90 at 13:39:10; no cap at 13:39:11; 90 13:39:15–13:39:21; no cap 13:39:25–13:39:30; 90 13:39:35–13:39:45; no cap 13:39:50–13:39:55; 90 13:40:00–13:40:01; no cap 13:40:05–13:40:10; 90 13:40:15–13:40:25; no cap 13:40:30–13:40:35; 90 13:40:40–13:40:45; no cap at 13:40:48; 90 13:40:50–13:40:55; no cap 13:40:57–13:41:05; 90 13:41:10–13:41:20; no cap 13:41:25–13:41:30; 90 13:41:35–13:41:45; no cap 13:41:47–13:41:55; 90 13:41:57–13:42:10; no cap 13:42:12–13:42:20; 90 13:42:22–13:42:31; no cap 13:42:35–13:42:40; 90 13:42:45–13:43:00; no cap at 13:43:05; 90 13:43:10–13:43:21; no cap 13:43:25–13:43:30; 90 at 13:43:35; no cap at 13:43:36; 90 13:43:40–13:43:45; no cap 13:43:50–13:43:55; 90 at 13:44:00; no cap at 13:44:01; 90 13:44:05–13:44:10; no cap 13:44:15–13:44:20; 90 13:44:25–13:44:36; no cap 13:44:40–13:44:45; 90 13:44:50–13:45:00; no cap 13:45:05–13:45:10 |
| emptycart | no cap 13:34:40–13:45:10 |

### tf0rg1-1

| API | Live caps |
| --- | --- |
| getproduct | no cap 09:40:50–09:51:45 |
| postcheckout | no cap 09:40:50–09:51:45 |
| getcart | no cap 09:40:50–09:51:45 |
| postcart | no cap 09:40:50–09:51:45 |
| emptycart | no cap 09:40:50–09:51:45 |

### tf0rg1-2

| API | Live caps |
| --- | --- |
| getproduct | no cap 15:22:00–15:33:00 |
| postcheckout | no cap 15:22:00–15:33:00 |
| getcart | no cap 15:22:00–15:33:00 |
| postcart | no cap 15:22:00–15:33:00 |
| emptycart | no cap 15:22:00–15:33:00 |

### tf1rg1-1

| API | Live caps |
| --- | --- |
| getproduct | no cap 11:50:20–11:51:25; 82 at 11:51:30; 86.8 at 11:51:35; 96.2451 at 11:51:39; 96.2 at 11:51:40; 107.4 at 11:51:45; 109.43 at 11:51:46; 115.5 at 11:51:50; 131 at 11:51:55; 171.7 at 11:52:00; 183.891 at 11:52:01; 175 11:52:05–11:52:06; no cap 11:52:10–11:52:15; 175 at 11:52:20; no cap at 11:52:21; 175 11:52:25–11:52:30; no cap 11:52:35–11:52:40; 175 11:52:45–11:52:58; no cap 11:53:00–11:53:05; 175 at 11:53:10; no cap at 11:53:13; 175 11:53:15–11:53:20; no cap at 11:53:22; 175 at 11:53:23; no cap 11:53:25–11:53:30; 175 11:53:32–11:53:35; no cap at 11:53:38; 175 at 11:53:40; no cap 11:53:45–11:53:50; 175 11:53:55–11:54:05; no cap 11:54:10–11:54:15; 175 at 11:54:20; no cap at 11:54:21; 175 11:54:25–11:54:30; no cap 11:54:35–11:54:40; 175 11:54:45–11:54:58; no cap 11:55:00–11:55:05; 175 at 11:55:10; no cap at 11:55:13; 175 11:55:15–11:55:20; no cap 11:55:22–11:55:30; 175 11:55:32–11:55:35; no cap at 11:55:38; 175 at 11:55:40; no cap 11:55:45–11:55:50; 175 11:55:52–11:55:55; no cap at 11:55:58; 175 11:56:00–11:56:05; no cap 11:56:07–11:56:10; 175 at 11:56:15; no cap at 11:56:16; 175 11:56:20–11:56:26; no cap 11:56:30–11:56:35; 175 at 11:56:40; no cap at 11:56:41; 175 11:56:45–11:56:50; no cap 11:56:55–11:57:00; 175 at 11:57:05; no cap at 11:57:06; 175 11:57:10–11:57:16; no cap 11:57:20–11:57:25; 175 at 11:57:30; no cap at 11:57:31; 175 11:57:35–11:57:40; no cap 11:57:45–11:57:50; 175 at 11:57:55; no cap at 11:57:56; 175 11:58:00–11:58:05; no cap 11:58:10–11:58:15; 175 11:58:20–11:58:33; no cap 11:58:35–11:58:40; 175 at 11:58:45; no cap at 11:58:48; 175 11:58:50–11:58:58; no cap 11:59:00–11:59:05; 175 11:59:07–11:59:10; no cap at 11:59:13; 175 11:59:15–11:59:20; no cap 11:59:22–11:59:30; 175 11:59:35–11:59:45; no cap 11:59:47–11:59:55; 175 12:00:00–12:00:13; no cap 12:00:15–12:00:20; 175 12:00:22–12:00:35; no cap 12:00:37–12:00:40; 175 at 12:00:45; no cap at 12:00:46; 175 12:00:47–12:01:00; no cap 12:01:05–12:01:09; 175 at 12:01:10; no cap at 12:01:11; 175 12:01:12–12:01:15 |
| postcheckout | no cap 11:50:20–11:51:25; 14 at 11:51:30; 17.0121 at 11:51:32; 18.7 at 11:51:35; 22 11:51:39–11:51:40; 25.3 11:51:43–11:51:45; 27.333 at 11:51:46; 28.6 at 11:51:50; 33 11:51:55–11:52:01; 30 11:52:05–11:52:06; no cap 11:52:10–11:52:15; 30 at 11:52:20; no cap at 11:52:21; 30 11:52:25–11:52:30; no cap 11:52:35–11:52:40; 30 11:52:45–11:52:55; no cap 11:53:00–11:53:05; 30 at 11:53:10; no cap at 11:53:13; 30 11:53:15–11:53:23; no cap 11:53:25–11:53:30; 30 at 11:53:35; no cap at 11:53:38; 30 at 11:53:40; no cap 11:53:45–11:53:50; 30 11:53:55–11:54:05; no cap 11:54:10–11:54:15; 30 at 11:54:20; no cap at 11:54:21; 30 11:54:25–11:54:30; no cap 11:54:35–11:54:40; 30 11:54:45–11:54:55; no cap 11:55:00–11:55:05; 30 at 11:55:10; no cap at 11:55:13; 30 11:55:15–11:55:20; no cap 11:55:22–11:55:30; 30 at 11:55:35; no cap at 11:55:38; 30 at 11:55:40; no cap 11:55:45–11:55:50; 30 at 11:55:55; no cap at 11:55:58; 30 11:56:00–11:56:05; no cap at 11:56:10; 30 at 11:56:15; no cap at 11:56:16; 30 11:56:20–11:56:26; no cap 11:56:30–11:56:35; 30 at 11:56:40; no cap at 11:56:41; 30 11:56:45–11:56:50; no cap 11:56:55–11:57:00; 30 at 11:57:05; no cap at 11:57:06; 30 11:57:10–11:57:16; no cap 11:57:20–11:57:25; 30 at 11:57:30; no cap at 11:57:31; 30 11:57:35–11:57:40; no cap 11:57:45–11:57:50; 30 at 11:57:55; no cap at 11:57:56; 30 11:58:00–11:58:05; no cap 11:58:10–11:58:15; 30 11:58:20–11:58:30; no cap 11:58:35–11:58:40; 30 at 11:58:45; no cap at 11:58:48; 30 11:58:50–11:58:55; no cap 11:59:00–11:59:05; 30 at 11:59:10; no cap at 11:59:13; 30 11:59:15–11:59:20; no cap 11:59:25–11:59:30; 30 11:59:35–11:59:45; no cap 11:59:47–11:59:55; 30 12:00:00–12:00:13; no cap 12:00:15–12:00:20; 30 12:00:25–12:00:35; no cap 12:00:37–12:00:40; 30 12:00:45–12:01:00; no cap 12:01:05–12:01:09; 30 at 12:01:10; no cap at 12:01:11; 30 12:01:12–12:01:15 |
| getcart | no cap 11:50:20–11:51:25; 34 at 11:51:30; 38.8 at 11:51:35; 48.2451 at 11:51:39; 48.2 at 11:51:40; 59.4 at 11:51:45; 61.4303 at 11:51:46; 67.1 at 11:51:50; 75.9 at 11:51:55; 77 11:52:00–11:52:01; 70 11:52:05–11:52:06; no cap 11:52:10–11:52:15; 70 at 11:52:20; no cap at 11:52:21; 70 11:52:25–11:52:30; no cap 11:52:35–11:52:40; 70 at 11:52:45; no cap at 11:52:48; 70 11:52:49–11:52:58; no cap 11:53:00–11:53:05; 70 at 11:53:10; no cap at 11:53:13; 70 11:53:15–11:53:20; no cap at 11:53:22; 70 at 11:53:23; no cap 11:53:25–11:53:30; 70 11:53:32–11:53:35; no cap at 11:53:38; 70 11:53:40–11:53:41; no cap 11:53:45–11:53:50; 70 11:53:55–11:54:05; no cap 11:54:10–11:54:15; 70 at 11:54:20; no cap at 11:54:21; 70 11:54:25–11:54:30; no cap 11:54:35–11:54:40; 70 at 11:54:45; no cap at 11:54:48; 70 11:54:49–11:54:58; no cap 11:55:00–11:55:05; 70 at 11:55:10; no cap at 11:55:13; 70 11:55:15–11:55:20; no cap 11:55:22–11:55:30; 70 11:55:32–11:55:35; no cap at 11:55:38; 70 at 11:55:40; no cap 11:55:45–11:55:50; 70 11:55:52–11:55:55; no cap at 11:55:58; 70 11:56:00–11:56:05; no cap 11:56:07–11:56:10; 70 at 11:56:15; no cap at 11:56:16; 70 11:56:20–11:56:26; no cap 11:56:30–11:56:35; 70 at 11:56:40; no cap at 11:56:41; 70 11:56:45–11:56:50; no cap 11:56:55–11:57:00; 70 at 11:57:05; no cap at 11:57:06; 70 11:57:10–11:57:16; no cap 11:57:20–11:57:25; 70 at 11:57:30; no cap at 11:57:31; 70 11:57:35–11:57:40; no cap 11:57:45–11:57:50; 70 at 11:57:55; no cap at 11:57:56; 70 11:58:00–11:58:05; no cap 11:58:10–11:58:15; 70 11:58:20–11:58:33; no cap 11:58:35–11:58:40; 70 at 11:58:45; no cap at 11:58:48; 70 11:58:50–11:58:55; no cap at 11:58:57; 70 at 11:58:58; no cap 11:59:00–11:59:05; 70 11:59:07–11:59:10; no cap at 11:59:13; 70 11:59:15–11:59:20; no cap 11:59:22–11:59:30; 70 11:59:35–11:59:45; no cap 11:59:47–11:59:55; 70 12:00:00–12:00:13; no cap 12:00:15–12:00:20; 70 12:00:22–12:00:35; no cap 12:00:37–12:00:40; 70 at 12:00:45; no cap at 12:00:46; 70 12:00:47–12:01:00; no cap 12:01:05–12:01:09; 70 at 12:01:10; no cap at 12:01:11; 70 12:01:12–12:01:15 |
| postcart | no cap 11:50:20–11:51:25; 44 at 11:51:30; 47.0121 at 11:51:32; 48.8 at 11:51:35; 58.2451 at 11:51:39; 58.2 at 11:51:40; 69.4 at 11:51:45; 71.4303 at 11:51:46; 77.5 at 11:51:50; 93 at 11:51:55; 99 at 11:52:00; 99 at 11:52:01; 90 11:52:05–11:52:06; no cap 11:52:10–11:52:15; 90 at 11:52:20; no cap at 11:52:21; 90 11:52:25–11:52:30; no cap 11:52:35–11:52:40; 90 11:52:45–11:52:55; no cap 11:53:00–11:53:05; 90 at 11:53:10; no cap at 11:53:13; 90 11:53:15–11:53:23; no cap 11:53:25–11:53:30; 90 at 11:53:35; no cap at 11:53:38; 90 at 11:53:40; no cap 11:53:45–11:53:50; 90 11:53:55–11:54:05; no cap 11:54:10–11:54:15; 90 at 11:54:20; no cap at 11:54:21; 90 11:54:25–11:54:30; no cap 11:54:35–11:54:40; 90 11:54:45–11:54:55; no cap 11:55:00–11:55:05; 90 at 11:55:10; no cap at 11:55:13; 90 11:55:15–11:55:20; no cap 11:55:22–11:55:30; 90 11:55:32–11:55:35; no cap at 11:55:38; 90 at 11:55:40; no cap 11:55:45–11:55:50; 90 at 11:55:55; no cap at 11:55:58; 90 11:56:00–11:56:05; no cap 11:56:07–11:56:10; 90 at 11:56:15; no cap at 11:56:16; 90 11:56:20–11:56:26; no cap 11:56:30–11:56:35; 90 at 11:56:40; no cap at 11:56:41; 90 11:56:45–11:56:50; no cap 11:56:55–11:57:00; 90 at 11:57:05; no cap at 11:57:06; 90 11:57:10–11:57:16; no cap 11:57:20–11:57:25; 90 at 11:57:30; no cap at 11:57:31; 90 11:57:35–11:57:40; no cap 11:57:45–11:57:50; 90 at 11:57:55; no cap at 11:57:56; 90 11:58:00–11:58:05; no cap 11:58:10–11:58:15; 90 11:58:20–11:58:30; no cap 11:58:35–11:58:40; 90 at 11:58:45; no cap at 11:58:48; 90 11:58:50–11:58:58; no cap 11:59:00–11:59:05; 90 11:59:07–11:59:10; no cap at 11:59:13; 90 11:59:15–11:59:20; no cap 11:59:22–11:59:30; 90 11:59:35–11:59:45; no cap 11:59:47–11:59:55; 90 12:00:00–12:00:13; no cap 12:00:15–12:00:20; 90 12:00:22–12:00:35; no cap 12:00:37–12:00:40; 90 12:00:45–12:01:00; no cap 12:01:05–12:01:09; 90 at 12:01:10; no cap at 12:01:11; 90 12:01:12–12:01:15 |
| emptycart | no cap 11:50:20–12:01:15 |

### tf1rg1-2

| API | Live caps |
| --- | --- |
| getproduct | no cap 15:48:25–15:49:30; 70 at 15:49:35; 93.2664 at 15:49:38; no cap 15:49:40–15:49:50; 136.863 at 15:49:52; 154 at 15:49:55; 169.4 at 15:50:00; no cap at 15:50:01; 181.7 at 15:50:05; 175 15:50:10–15:50:15; no cap at 15:50:18; 175 15:50:20–15:50:25; no cap at 15:50:27; 175 at 15:50:28; no cap 15:50:30–15:50:35; 175 at 15:50:40; no cap at 15:50:41; 175 15:50:45–15:50:50; no cap 15:50:55–15:51:00; 175 15:51:05–15:51:20; no cap 15:51:22–15:51:35; 175 15:51:37–15:51:40; no cap at 15:51:43; 175 15:51:45–15:51:55; no cap 15:51:57–15:52:05; 175 15:52:10–15:52:25; no cap at 15:52:27; 175 at 15:52:28; no cap 15:52:30–15:52:35; 175 at 15:52:40; no cap at 15:52:41; 175 15:52:45–15:52:51; no cap 15:52:55–15:53:05; 175 15:53:07–15:53:28; no cap 15:53:30–15:53:55; 175 15:53:57–15:54:00; no cap at 15:54:01; 175 15:54:05–15:54:28; no cap 15:54:30–15:54:35; 175 15:54:40–15:54:55; no cap 15:54:57–15:55:03; 175 15:55:05–15:55:15; no cap at 15:55:20; 182.5 at 15:55:25; no cap at 15:55:28; 175 15:55:30–15:55:35; no cap 15:55:40–15:55:45; 175 at 15:55:50; no cap at 15:55:51; 175 at 15:55:55; no cap at 15:55:58; 175 15:56:00–15:56:10; 151.889 at 15:56:14; 151.9 at 15:56:15; 138.918 at 15:56:19; 138.9 at 15:56:20; 144.858 at 15:56:24; 144.9 at 15:56:25; 165.331 at 15:56:29; 165.3 at 15:56:30; 181.179 at 15:56:31; 175 15:56:35–15:56:40; no cap 15:56:45–15:56:50; 175 15:56:55–15:57:05; no cap 15:57:10–15:57:21; 175 15:57:22–15:57:35; no cap 15:57:40–15:57:45; 175 at 15:57:50; no cap at 15:57:53; 175 15:57:55–15:58:05; no cap at 15:58:10; 175 15:58:15–15:58:30; no cap 15:58:32–15:58:40; 175 15:58:45–15:58:50; no cap 15:58:55–15:59:00; 175 at 15:59:05; no cap at 15:59:06; 175 15:59:07–15:59:20; 164 15:59:23–15:59:25 |
| postcheckout | no cap 15:48:25–15:49:30; 12 at 15:49:35; 16.5 at 15:49:38; no cap 15:49:40–15:49:50; 26.4 at 15:49:52; 26.4 at 15:49:55; 30.8 at 15:50:00; no cap at 15:50:01; 30 at 15:50:03; 33 at 15:50:05; 30 15:50:10–15:50:15; no cap at 15:50:18; 30 15:50:20–15:50:25; no cap at 15:50:27; 30 at 15:50:28; no cap 15:50:30–15:50:35; 30 at 15:50:40; no cap at 15:50:41; 30 15:50:45–15:50:50; no cap 15:50:55–15:51:00; 30 15:51:05–15:51:20; no cap 15:51:22–15:51:35; 30 15:51:37–15:51:40; no cap at 15:51:43; 30 15:51:45–15:51:55; no cap 15:51:57–15:52:05; 30 15:52:10–15:52:25; no cap at 15:52:27; 30 at 15:52:28; no cap 15:52:30–15:52:35; 30 at 15:52:40; no cap at 15:52:41; 30 15:52:45–15:52:51; no cap 15:52:55–15:53:05; 30 15:53:07–15:53:28; no cap 15:53:30–15:53:55; 30 15:53:57–15:54:00; no cap at 15:54:01; 30 15:54:05–15:54:28; no cap 15:54:30–15:54:35; 30 at 15:54:40; no cap at 15:54:41; 30 15:54:45–15:54:55; no cap 15:54:57–15:55:03; 30 15:55:05–15:55:15; no cap at 15:55:20; 33 at 15:55:25; no cap at 15:55:28; 30 15:55:30–15:55:35; no cap 15:55:40–15:55:45; 30 at 15:55:50; no cap at 15:55:51; 30 at 15:55:55; no cap at 15:55:58; 30 15:56:00–15:56:10; 15.8887 at 15:56:14; 15.9 at 15:56:15; 10 15:56:19–15:56:20; 19.4221 at 15:56:24; 19.4 at 15:56:25; 33 15:56:29–15:56:31; 30 15:56:35–15:56:40; no cap 15:56:42–15:56:50; 30 15:56:55–15:57:05; no cap 15:57:10–15:57:21; 30 15:57:22–15:57:35; no cap 15:57:40–15:57:45; 30 at 15:57:50; no cap at 15:57:53; 30 15:57:55–15:58:05; no cap at 15:58:10; 30 15:58:15–15:58:30; no cap 15:58:32–15:58:40; 30 15:58:45–15:58:50; no cap 15:58:55–15:59:00; 30 at 15:59:05; no cap at 15:59:06; 30 15:59:07–15:59:20; no cap at 15:59:22; 27 15:59:23–15:59:25 |
| getcart | no cap 15:48:25–15:49:30; 29 at 15:49:35; 39.6 at 15:49:38; no cap 15:49:40–15:49:50; 59.8629 at 15:49:52; 62.7 at 15:49:55; 72.6 at 15:50:00; no cap at 15:50:01; 70 at 15:50:03; 77 at 15:50:05; 70 15:50:10–15:50:15; no cap at 15:50:18; 70 15:50:20–15:50:25; no cap at 15:50:27; 70 at 15:50:28; no cap 15:50:30–15:50:35; 70 at 15:50:40; no cap at 15:50:41; 70 15:50:45–15:50:50; no cap 15:50:55–15:51:00; 70 at 15:51:05; no cap at 15:51:08; 70 15:51:09–15:51:20; no cap 15:51:22–15:51:36; 70 15:51:37–15:51:40; no cap at 15:51:43; 70 15:51:45–15:51:55; no cap 15:51:57–15:52:05; 70 at 15:52:10; no cap at 15:52:13; 70 15:52:14–15:52:25; no cap at 15:52:27; 70 at 15:52:28; no cap 15:52:30–15:52:35; 70 at 15:52:40; no cap at 15:52:41; 70 15:52:45–15:52:51; no cap 15:52:55–15:53:05; 70 15:53:07–15:53:10; no cap at 15:53:13; 70 15:53:14–15:53:28; no cap 15:53:30–15:53:50; 70 at 15:53:52; no cap at 15:53:55; 70 15:53:57–15:54:00; no cap at 15:54:01; 70 15:54:05–15:54:28; no cap 15:54:30–15:54:35; 70 at 15:54:40; no cap at 15:54:41; 70 15:54:45–15:54:55; no cap 15:54:57–15:55:03; 70 15:55:05–15:55:15; no cap at 15:55:20; 77 at 15:55:25; no cap at 15:55:28; 70 15:55:30–15:55:38; no cap 15:55:40–15:55:45; 70 at 15:55:50; no cap at 15:55:51; 70 at 15:55:55; no cap at 15:55:58; 70 15:56:00–15:56:10; 52.8887 at 15:56:14; 52.9 at 15:56:15; 39.9178 at 15:56:19; 39.9 at 15:56:20; 45.9 at 15:56:25; 66.3306 at 15:56:29; 66.3 at 15:56:30; 77 at 15:56:31; 70 15:56:35–15:56:40; no cap 15:56:42–15:56:50; 70 15:56:55–15:57:05; no cap 15:57:10–15:57:21; 70 15:57:22–15:57:35; no cap 15:57:37–15:57:45; 70 15:57:47–15:57:50; no cap at 15:57:53; 70 15:57:55–15:58:05; no cap at 15:58:10; 70 15:58:15–15:58:30; no cap 15:58:32–15:58:40; 70 15:58:44–15:58:50; no cap 15:58:55–15:59:00; 70 at 15:59:05; no cap at 15:59:06; 70 15:59:07–15:59:20; no cap at 15:59:22; 66 15:59:23–15:59:25 |
| postcart | no cap 15:48:25–15:49:30; 38 at 15:49:35; 50.6 at 15:49:38; no cap 15:49:40–15:49:50; 74.8629 at 15:49:52; 80.3 at 15:49:55; 92.4 at 15:50:00; no cap at 15:50:01; 98.7 at 15:50:05; 90 15:50:10–15:50:15; no cap at 15:50:18; 90 15:50:20–15:50:25; no cap 15:50:30–15:50:35; 90 at 15:50:40; no cap at 15:50:41; 90 15:50:45–15:50:50; no cap 15:50:55–15:51:00; 90 15:51:05–15:51:20; no cap 15:51:25–15:51:35; 90 15:51:37–15:51:40; no cap at 15:51:43; 90 15:51:45–15:51:55; no cap 15:51:57–15:52:05; 90 15:52:10–15:52:25; no cap at 15:52:27; 90 at 15:52:28; no cap 15:52:30–15:52:35; 90 at 15:52:40; no cap at 15:52:41; 90 15:52:45–15:52:51; no cap 15:52:55–15:53:05; 90 15:53:07–15:53:28; no cap 15:53:30–15:53:55; 90 15:53:57–15:54:00; no cap at 15:54:01; 90 15:54:05–15:54:25; no cap 15:54:30–15:54:35; 90 15:54:40–15:54:55; no cap at 15:55:00; 91 at 15:55:05; 90 15:55:09–15:55:15; no cap at 15:55:20; 96.5 at 15:55:25; no cap at 15:55:28; 90 15:55:30–15:55:35; no cap 15:55:40–15:55:45; 90 at 15:55:50; no cap at 15:55:51; 90 at 15:55:55; no cap at 15:55:58; 90 15:56:00–15:56:10; 78.8887 at 15:56:14; 78.9 at 15:56:15; 65.9178 at 15:56:19; 65.9 at 15:56:20; 71.8576 at 15:56:24; 71.9 at 15:56:25; 92.3306 at 15:56:29; 92.3 at 15:56:30; 99 at 15:56:31; 90 15:56:35–15:56:40; no cap 15:56:45–15:56:50; 90 15:56:55–15:57:05; no cap 15:57:10–15:57:20; 90 15:57:22–15:57:35; no cap 15:57:40–15:57:45; 90 at 15:57:50; no cap at 15:57:53; 90 15:57:55–15:58:05; no cap at 15:58:10; 90 15:58:15–15:58:30; no cap 15:58:32–15:58:40; 90 15:58:45–15:58:50; no cap 15:58:55–15:59:00; 90 15:59:05–15:59:20; 83 15:59:23–15:59:25 |
| emptycart | no cap 15:48:25–15:59:25 |

## Per arm, or per hold

`tf1rg0-1` has RetryGuard off, so nothing shed and nothing climbed. Recommendations retry volume is 4,677 and `grpc_4` is 4,019. Checkout retry volume is 1. The recommendations file streak is 6 s. `productcatalogservice` is detector-hot at 90.8%. Every other service is 0%.

`tf1rg0-2` has RetryGuard off. Outbound retry volume is 0 and `grpc_4` is 0. `productcatalogservice` is detector-hot at 91.4%.

`tf0rg1-1` has a RetryGuard log and no transition, so nothing shed and nothing climbed. Retry volume is 0 and `grpc_4` is 0. Controller `high` is 0. `productcatalogservice` is detector-hot at 88.5%.

`tf0rg1-2` has no transition. Retry volume is 0 and `grpc_4` is 0. `productcatalogservice` is detector-hot at 87.0%.

`tf1rg1-1` has no transition. Retry volume is 0 and `grpc_4` is 0. `productcatalogservice` is detector-hot at 88.8%.

`tf1rg1-2` has no transition, so nothing shed and nothing climbed. Recommendations retry volume is 2,151 and `grpc_4` is 1,962. The file streak is 2 s and the controller `high` is 2. `productcatalogservice` is detector-hot at 87.8%.

## Related links

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode section
- The same user counts are the S1 lock in [2026-10-08-s1-both-off-run8.md](2026-10-08-s1-both-off-run8.md), a 300 s hold at the Paper-C1 catalog limit of 800 m.
