# Set B Scenario 4B, emailservice at 40 m

## Setup

600 s holds on 2026-10-09. Scenario 4B constrains `emailservice` at 40 m. The earlier `campaign_48/` S4B folders constrained `paymentservice`. Mix getproduct 175 / postcheckout 30 / getcart 70 / postcart 90 / emptycart 5, `spawn_rate` 50. Paper-C1, with that email limit in place of the Paper-C1 email quota. `retry_metric` is `edge_rpr`. The YAML sets `reenable_rejection` to 0.15. `paper_cpu_reconcile` is false. Each hold rolls `checkoutservice` and `recommendationservice` and then waits 60 s. The study procedure cools off for 360 s between holds. These seven sit in the Set B sequence with S3 and S4A, so they are not one contiguous block.

`service_capacity.json` is the same pin on every hold:

| Service | Per-pod quota (m) | Replicas |
| --- | ---: | ---: |
| frontend | 1150 | 4 |
| checkoutservice | 800 | 1 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 800 | 1 |
| cartservice | 800 | 1 |
| currencyservice | 770 | 1 |
| shippingservice | 770 | 1 |
| adservice | 1150 | 1 |
| paymentservice | 155 | 1 |
| emailservice | 40 | 1 |
| redis-cart | 540 | 1 |

Arms: `tf1rg0` is TopFull on and RetryGuard off, including the rep3 replay. `tf0rg1` is TopFull off and RetryGuard on. `tf1rg1` is both on. Folders are under `experiments/results/campaign_48/S4B_topology_position_B/`.

## Index

Column order follows this index. A bold bar separates the groups.

| Arm | Columns | Folders |
| --- | --- | --- |
| TopFull on, RetryGuard off | 1, 2 | `study2_s4b_tf1rg0_rep1`, `study2_s4b_tf1rg0_rep2` |
| TopFull on, RetryGuard off (replay) | 3 | `study2_s4b_tf1rg0_rep3` |
| TopFull off, RetryGuard on | 4, 5 | `study2_s4b_tf0rg1_rep1`, `study2_s4b_tf0rg1_rep2` |
| Both on | 6, 7 | `study2_s4b_tf1rg1_rep1`, `study2_s4b_tf1rg1_rep2` |

## Gate

Every hold fails. `emailservice` `replica_count` in `resource_usage.csv` hits 0, and that column is ready replicas. The Locust files, the mesh files, and `service_capacity.json` are usable, so the columns below stay filled. This set cannot support an email-bottleneck comparison: the constrained service is not ready for a stretch of every hold, and on columns 2 and 7 it is ready on none of its resource samples.

`service_capacity.json` matches the pin on all seven (email limit 40 m, spec replicas 1, frontend 1150 m × 4). Frontend ready replicas are 4 on every frontend sample (133, 134, 134, 138, 139, 138, 139). Every other service except email is 1 on every one of those samples. Email is missing from most polls. Its ready counts are 0 on 20 of 38, 0 on 12 of 12, 0 on 15 of 34, 0 on 24 of 44, 0 on 13 of 37, 0 on 24 of 46, and 0 on 12 of 12.

Locust `total.csv` rows are 573, 569, 573, 577, 571, 572, and 567. Mesh spans are 690 s, 692 s, 690 s, 714 s, 715 s, 716 s, and 718 s. Inbound gaps of 1.5 s or longer are 33 of 7557, 11 of 7601, 22 of 7568, 0 of 7854, 0 of 7865, 22 of 7854, and 55 of 7843. `retryguard.log` is absent on columns 1–3 and present on columns 4–7.

## Edge-mode bars

Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.10.

That re-enable figure is the scorer default. Columns 1–3 have no START line, so their under-bar streaks use 0.10. The four RetryGuard logs start with `reenable_rejection=0.15` and `interval_samples=30s`, so columns 4–7 count a sample as under the bar only when rejection is strictly under 0.15. Shed and 0→1 take 30 seconds of row timestamps. 1→2 and 2→3 take 15 s (`CLIMB_INTERVAL_SECONDS`). These holds are after 2026-10-08, when every step used 30 s. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## (a) Edge rpr

The file streak is seconds from the first consecutive scored tick above 0.5 to the last. One tick is 0 seconds. **Bold** is a file streak of at least 30 seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count, and it is present only where that log exists. No streak here reaches 30 seconds.

Only `frontend → checkoutservice` and `frontend → recommendationservice` have a tick above the shed bar or a retry delta. The other 12 controlled edges, including `checkoutservice → emailservice`, are at retry delta 0 with no tick above 0.5.

| Edge | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0 / 1 | 0 / 0 | **┃** | 0 / 2 | **┃** | 0 / 1 (1) | 1 / 5 (2) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.

| Edge | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.005 / 0.64 / 0.002 | 0.000 / 0.00 / 0.000 | **┃** | 0.006 / 1.08 / 0.003 | **┃** | 0.001 / 0.90 / 0.001 | 0.009 / 0.73 / 0.006 | **┃** | 0.001 / 0.27 / 0.001 | 0.000 / 0.00 / 0.000 |
| frontend → recommendationservice | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.17 / 0.000 |

Climb streaks while that attempt cap is in force: samples at 1 attempt with rpr at or under 0.17, then samples at 2 attempts with rpr at or under 0.33. An em dash means that cap never applied. Every cell is an em dash. The edges stayed at 3 attempts, so neither climb bar was in force.

| Edge | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → recommendationservice | — / — | — / — | **┃** | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

## Rejection, beside (a)

This is the 0.20 rejection streak beside (a). It is not the shed signal. Longest streak / count above 0.20. **Bold** would be a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. No controlled streak reaches 30.

A non-positive `Δtotal` is neither above 0.20 nor under the re-enable bar, and it breaks the streak. Email's arrival rate is under 1 req/s, so its under-bar counts stay in the tens.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 |
| checkoutservice | 2 / 2 | 1 / 1 | **┃** | 1 / 2 | **┃** | 0 / 0 | 1 / 2 | **┃** | 0 / 0 | 0 / 0 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 7 / 7 | 0 / 0 | **┃** | 6 / 8 | **┃** | 1 / 1 | 11 / 12 | **┃** | 1 / 2 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak / count strictly under the re-enable bar. Columns 1–3 use 0.10. Columns 4–7 use 0.15.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 610 / 610 | 611 / 611 | **┃** | 610 / 610 | **┃** | 612 / 612 | 612 / 612 | **┃** | 610 / 610 | 608 / 608 |
| checkoutservice | 577 / 607 | 610 / 610 | **┃** | 580 / 604 | **┃** | 593 / 611 | 576 / 607 | **┃** | 610 / 610 | 607 / 607 |
| recommendationservice | 610 / 610 | 611 / 611 | **┃** | 611 / 611 | **┃** | 613 / 613 | 613 / 613 | **┃** | 611 / 611 | 608 / 608 |
| paymentservice | 609 / 609 | 611 / 611 | **┃** | 610 / 610 | **┃** | 612 / 612 | 612 / 612 | **┃** | 610 / 610 | 606 / 606 |
| emailservice | 25 / 38 | 0 / 0 | **┃** | 24 / 31 | **┃** | 18 / 36 | 22 / 27 | **┃** | 16 / 27 | 2 / 2 |
| productcatalogservice | 610 / 610 | 612 / 612 | **┃** | 610 / 610 | **┃** | 613 / 613 | 613 / 613 | **┃** | 611 / 611 | 607 / 607 |
| cartservice | 610 / 610 | 612 / 612 | **┃** | 611 / 611 | **┃** | 613 / 613 | 613 / 613 | **┃** | 611 / 611 | 607 / 607 |
| currencyservice | 610 / 610 | 612 / 612 | **┃** | 611 / 611 | **┃** | 613 / 613 | 613 / 613 | **┃** | 611 / 611 | 608 / 608 |
| shippingservice | 610 / 610 | 612 / 612 | **┃** | 611 / 611 | **┃** | 613 / 613 | 613 / 613 | **┃** | 611 / 611 | 607 / 607 |
| adservice | 609 / 609 | 611 / 611 | **┃** | 610 / 610 | **┃** | 612 / 612 | 612 / 612 | **┃** | 610 / 610 | 607 / 607 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

`grpc_4 / grpc_14` for the four read callees. Checkout, payment, email, cart, and shipping stay on 5xx + resets, so their gRPC columns are not in this rate.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 1 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as `ticks/rows (share%)`. **Bold** is a share of at least 0.5. No share reaches 0.5. Email is the only service with more than two overloaded ticks. On columns 4 and 5 the RL loop is off, so Layer A stays at the 10000 passthrough and this fraction is the engagement signal that still moves.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| checkoutservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 2/662 (0.3%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| recommendationservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| paymentservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| emailservice | 110/636 (17.3%) | 54/637 (8.5%) | **┃** | 77/636 (12.1%) | **┃** | 109/662 (16.5%) | 70/662 (10.6%) | **┃** | 109/662 (16.5%) | 55/662 (8.3%) |
| productcatalogservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| cartservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| currencyservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| shippingservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| adservice | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |
| redis-cart | 0/636 (0.0%) | 0/637 (0.0%) | **┃** | 0/636 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) | **┃** | 0/662 (0.0%) | 0/662 (0.0%) |

## (c) Retry volume

Outbound retry delta by target. Every other target is 0.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 40 | 0 | **┃** | 53 | **┃** | 9 | 101 | **┃** | 10 | 0 |
| recommendationservice | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 |

Inbound resets for all 11 services.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 2 | 34 | **┃** | 16 | **┃** | 30 | 26 | **┃** | 19 | 11 |
| checkoutservice | 14 | 10 | **┃** | 22 | **┃** | 7 | 37 | **┃** | 5 | 0 |
| recommendationservice | 0 | 13 | **┃** | 3 | **┃** | 8 | 1 | **┃** | 0 | 0 |
| paymentservice | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 78 | 0 | **┃** | 92 | **┃** | 10 | 222 | **┃** | 12 | 0 |
| productcatalogservice | 0 | 2 | **┃** | 3 | **┃** | 8 | 14 | **┃** | 4 | 5 |
| cartservice | 0 | 2 | **┃** | 1 | **┃** | 0 | 1 | **┃** | 6 | 0 |
| currencyservice | 0 | 0 | **┃** | 1 | **┃** | 0 | 1 | **┃** | 0 | 0 |
| shippingservice | 0 | 1 | **┃** | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 0 | 3 | **┃** | 0 | **┃** | 1 | 0 | **┃** | 0 | 2 |
| redis-cart | 0 | 0 | **┃** | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

The same `grpc_4 / grpc_14` pair is what the retry policy counts on the four read callees.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 1 / 0 | **┃** | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## RetryGuard toggles

Columns 1–3 have no `retryguard.log`. Columns 4–7 have a log and no transition lines, so there is no timestamp log. Nothing shed and nothing climbed.

| Column | Edge | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | --- | ---: | ---: | ---: | ---: |
| 4 | — | 0 | 0 | 0 | 0 |
| 5 | — | 0 | 0 | 0 | 0 |
| 6 | — | 0 | 0 | 0 | 0 |
| 7 | — | 0 | 0 | 0 | 0 |

## Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 168.0 | 167.8 | **┃** | 167.9 | **┃** | 168.1 | 168.0 | **┃** | 168.0 | 167.8 |
| postcheckout | 28.7 | 28.8 | **┃** | 28.7 | **┃** | 28.8 | 28.7 | **┃** | 28.9 | 28.8 |
| getcart | 67.2 | 67.2 | **┃** | 67.2 | **┃** | 67.2 | 67.2 | **┃** | 67.2 | 67.2 |
| postcart | 86.2 | 86.3 | **┃** | 86.3 | **┃** | 86.3 | 86.2 | **┃** | 86.3 | 86.4 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.007 | 0.000 | **┃** | 0.008 | **┃** | 0.001 | 0.007 | **┃** | 0.000 | 0.000 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

## Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 93 | 90 | **┃** | 96 | **┃** | 87 | 91 | **┃** | 90 | 92 |
| postcheckout | 162 | 171 | **┃** | 162 | **┃** | 147 | 150 | **┃** | 174 | 172 |
| getcart | 80 | 68 | **┃** | 66 | **┃** | 65 | 65 | **┃** | 77 | 63 |
| postcart | 61 | 61 | **┃** | 60 | **┃** | 60 | 61 | **┃** | 60 | 61 |
| emptycart | 13 | 14 | **┃** | 14 | **┃** | 14 | 13 | **┃** | 10 | 14 |

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 314.7 | 313.9 | **┃** | 314.7 | **┃** | 304.4 | 303.8 | **┃** | 303.4 | 302.6 |
| checkoutservice | 25.5 | 25.5 | **┃** | 25.5 | **┃** | 24.7 | 24.8 | **┃** | 24.6 | 24.5 |
| recommendationservice | 233.8 | 233.2 | **┃** | 233.8 | **┃** | 226.2 | 225.7 | **┃** | 225.4 | 224.8 |
| paymentservice | 25.5 | 25.5 | **┃** | 25.5 | **┃** | 24.7 | 24.8 | **┃** | 24.6 | 24.5 |
| emailservice | 0.8 | 0.0 | **┃** | 0.7 | **┃** | 0.6 | 0.8 | **┃** | 0.4 | 0.1 |
| productcatalogservice | 1628.0 | 1624.2 | **┃** | 1627.9 | **┃** | 1575.0 | 1571.9 | **┃** | 1569.5 | 1565.5 |
| cartservice | 340.2 | 339.4 | **┃** | 340.3 | **┃** | 329.1 | 328.7 | **┃** | 328.0 | 327.1 |
| currencyservice | 467.6 | 466.5 | **┃** | 467.6 | **┃** | 452.4 | 451.6 | **┃** | 450.8 | 449.6 |
| shippingservice | 110.5 | 110.3 | **┃** | 110.6 | **┃** | 107.0 | 107.0 | **┃** | 106.6 | 106.3 |
| adservice | 148.8 | 148.3 | **┃** | 148.7 | **┃** | 143.9 | 143.6 | **┃** | 143.4 | 143.0 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. An em dash means the hold has no sojourn samples. Column 2 email and redis-cart on every hold are in that case.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 56 | 53 | **┃** | 50 | **┃** | 48 | 50 | **┃** | 52 | 51 |
| checkoutservice | 53 | 74 | **┃** | 56 | **┃** | 53 | 48 | **┃** | 68 | 73 |
| recommendationservice | 12 | 10 | **┃** | 9 | **┃** | 8 | 8 | **┃** | 11 | 8 |
| paymentservice | 2 | 2 | **┃** | 1 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| emailservice | 109 | — | **┃** | 120 | **┃** | 64 | 138 | **┃** | 91 | 29 |
| productcatalogservice | 1 | 1 | **┃** | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | **┃** | 2 | 2 | **┃** | 2 | 3 |
| currencyservice | 2 | 2 | **┃** | 2 | **┃** | 1 | 2 | **┃** | 2 | 2 |
| shippingservice | 0 | 1 | **┃** | 1 | **┃** | 0 | 1 | **┃** | 0 | 1 |
| adservice | 1 | 1 | **┃** | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | **┃** | — | — | **┃** | — | — |

## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. An em dash means that count is unavailable.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.001 | **┃** | 0.000 | 0.000 |
| checkoutservice | 0.005 | 0.000 | **┃** | 0.005 | **┃** | 0.001 | 0.014 | **┃** | 0.001 | 0.000 |
| recommendationservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | — | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | **┃** | — | — | **┃** | — | — |

## CPU

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its 1150 m pod quota. Email's replica mode is 0 on columns 1, 2, 4, 6, and 7.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1181 / 1377 | 1150 / 4 / 1228 / 1455 | **┃** | 1150 / 4 / 1246 / 1487 | **┃** | 1150 / 4 / 1167 / 1426 | 1150 / 4 / 1192 / 1487 | **┃** | 1150 / 4 / 1137 / 1402 | 1150 / 4 / 1235 / 1528 |
| checkoutservice | 800 / 1 / 422 / 497 | 800 / 1 / 375 / 467 | **┃** | 800 / 1 / 431 / 517 | **┃** | 800 / 1 / 378 / 464 | 800 / 1 / 457 / 568 | **┃** | 800 / 1 / 364 / 458 | 800 / 1 / 353 / 444 |
| recommendationservice | 1150 / 1 / 478 / 566 | 1150 / 1 / 496 / 598 | **┃** | 1150 / 1 / 495 / 617 | **┃** | 1150 / 1 / 457 / 572 | 1150 / 1 / 479 / 628 | **┃** | 1150 / 1 / 452 / 577 | 1150 / 1 / 491 / 631 |
| paymentservice | 155 / 1 / 26 / 34 | 155 / 1 / 26 / 34 | **┃** | 155 / 1 / 27 / 36 | **┃** | 155 / 1 / 25 / 33 | 155 / 1 / 28 / 38 | **┃** | 155 / 1 / 25 / 34 | 155 / 1 / 25 / 34 |
| emailservice | 40 / 0 / 10 / 41 | 40 / 0 / 17 / 41 | **┃** | 40 / 1 / 11 / 40 | **┃** | 40 / 0 / 8 / 40 | 40 / 1 / 12 / 40 | **┃** | 40 / 0 / 11 / 41 | 40 / 0 / 10 / 40 |
| productcatalogservice | 800 / 1 / 403 / 471 | 800 / 1 / 440 / 515 | **┃** | 800 / 1 / 447 / 523 | **┃** | 800 / 1 / 417 / 505 | 800 / 1 / 430 / 530 | **┃** | 800 / 1 / 401 / 487 | 800 / 1 / 454 / 550 |
| cartservice | 800 / 1 / 320 / 461 | 800 / 1 / 314 / 384 | **┃** | 800 / 1 / 336 / 491 | **┃** | 800 / 1 / 311 / 481 | 800 / 1 / 312 / 396 | **┃** | 800 / 1 / 300 / 477 | 800 / 1 / 326 / 500 |
| currencyservice | 770 / 1 / 278 / 332 | 770 / 1 / 289 / 375 | **┃** | 770 / 1 / 296 / 361 | **┃** | 770 / 1 / 281 / 343 | 770 / 1 / 278 / 354 | **┃** | 770 / 1 / 271 / 337 | 770 / 1 / 284 / 359 |
| shippingservice | 770 / 1 / 73 / 85 | 770 / 1 / 72 / 87 | **┃** | 770 / 1 / 74 / 88 | **┃** | 770 / 1 / 69 / 84 | 770 / 1 / 75 / 95 | **┃** | 770 / 1 / 68 / 85 | 770 / 1 / 69 / 86 |
| adservice | 1150 / 1 / 113 / 135 | 1150 / 1 / 115 / 139 | **┃** | 1150 / 1 / 115 / 140 | **┃** | 1150 / 1 / 108 / 132 | 1150 / 1 / 110 / 138 | **┃** | 1150 / 1 / 110 / 135 | 1150 / 1 / 114 / 139 |
| redis-cart | 540 / 1 / 39 / 52 | 540 / 1 / 40 / 55 | **┃** | 540 / 1 / 41 / 54 | **┃** | 540 / 1 / 39 / 53 | 540 / 1 / 40 / 55 | **┃** | 540 / 1 / 38 / 52 | 540 / 1 / 40 / 56 |

## CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out. Columns 2 and 7 leave email out, so those cells are an em dash.

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.26 / 0.30 | 0.27 / 0.32 | **┃** | 0.27 / 0.32 | **┃** | 0.25 / 0.31 | 0.26 / 0.32 | **┃** | 0.25 / 0.30 | 0.27 / 0.33 |
| checkoutservice | 0.53 / 0.62 | 0.47 / 0.58 | **┃** | 0.54 / 0.65 | **┃** | 0.47 / 0.58 | 0.57 / 0.71 | **┃** | 0.46 / 0.57 | 0.44 / 0.56 |
| recommendationservice | 0.42 / 0.49 | 0.43 / 0.52 | **┃** | 0.43 / 0.54 | **┃** | 0.40 / 0.50 | 0.42 / 0.55 | **┃** | 0.39 / 0.50 | 0.43 / 0.55 |
| paymentservice | 0.17 / 0.22 | 0.17 / 0.22 | **┃** | 0.17 / 0.23 | **┃** | 0.16 / 0.21 | 0.18 / 0.25 | **┃** | 0.16 / 0.22 | 0.16 / 0.22 |
| emailservice | 0.29 / 0.75 | — / — | **┃** | 0.33 / 0.85 | **┃** | 0.21 / 0.47 | 0.29 / 0.93 | **┃** | 0.28 / 1.00 | — / — |
| productcatalogservice | 0.50 / 0.59 | 0.55 / 0.64 | **┃** | 0.56 / 0.65 | **┃** | 0.52 / 0.63 | 0.54 / 0.66 | **┃** | 0.50 / 0.61 | 0.57 / 0.69 |
| cartservice | 0.40 / 0.58 | 0.39 / 0.48 | **┃** | 0.42 / 0.61 | **┃** | 0.39 / 0.60 | 0.39 / 0.49 | **┃** | 0.38 / 0.60 | 0.41 / 0.62 |
| currencyservice | 0.36 / 0.43 | 0.37 / 0.49 | **┃** | 0.38 / 0.47 | **┃** | 0.36 / 0.45 | 0.36 / 0.46 | **┃** | 0.35 / 0.44 | 0.37 / 0.47 |
| shippingservice | 0.09 / 0.11 | 0.09 / 0.11 | **┃** | 0.10 / 0.11 | **┃** | 0.09 / 0.11 | 0.10 / 0.12 | **┃** | 0.09 / 0.11 | 0.09 / 0.11 |
| adservice | 0.10 / 0.12 | 0.10 / 0.12 | **┃** | 0.10 / 0.12 | **┃** | 0.09 / 0.11 | 0.10 / 0.12 | **┃** | 0.10 / 0.12 | 0.10 / 0.12 |
| redis-cart | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.08 / 0.10 | **┃** | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.07 / 0.10 | 0.07 / 0.10 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | 1 | 2 | **┃** | 3 | **┃** | 4 | 5 | **┃** | 6 | 7 |
| --- | ---: | ---: | :---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.316 | 0.329 | **┃** | 0.343 | **┃** | 0.334 | 0.343 | **┃** | 0.327 | 0.357 |
| checkoutservice | 0.764 | 0.657 | **┃** | 0.709 | **┃** | 0.649 | 0.809 | **┃** | 0.649 | 0.641 |
| recommendationservice | 0.519 | 0.558 | **┃** | 0.574 | **┃** | 0.520 | 0.592 | **┃** | 0.544 | 0.630 |
| paymentservice | 0.374 | 0.503 | **┃** | 0.387 | **┃** | 0.355 | 0.387 | **┃** | 0.387 | 0.361 |
| emailservice | 1.200 | 1.125 | **┃** | 1.150 | **┃** | 1.150 | 1.125 | **┃** | 1.175 | 1.100 |
| productcatalogservice | 0.625 | 0.684 | **┃** | 0.693 | **┃** | 0.661 | 0.694 | **┃** | 0.647 | 0.725 |
| cartservice | 0.609 | 0.529 | **┃** | 0.624 | **┃** | 0.626 | 0.535 | **┃** | 0.626 | 0.655 |
| currencyservice | 0.479 | 0.570 | **┃** | 0.510 | **┃** | 0.484 | 0.494 | **┃** | 0.505 | 0.509 |
| shippingservice | 0.143 | 0.147 | **┃** | 0.148 | **┃** | 0.144 | 0.152 | **┃** | 0.144 | 0.139 |
| adservice | 0.144 | 0.157 | **┃** | 0.156 | **┃** | 0.137 | 0.139 | **┃** | 0.137 | 0.137 |
| redis-cart | 0.209 | 0.226 | **┃** | 0.202 | **┃** | 0.239 | 0.217 | **┃** | 0.206 | 0.243 |

## TopFull live caps

A live read has `threshold_fresh=1` and `threshold` above 0. 10000 is no cap. A live 0 is an empty read and is left out. Times are UTC on 2026-10-09. The postcheckout series alternates no-cap and a real cap often enough that the spans stay in the scorer's collapsed form.

`getproduct`, `getcart`, `postcart`, and `emptycart` are no cap on every live read of every hold. On columns 4 and 5, `postcheckout` is no cap on every live read as well.

### Column 1

`getproduct`, `getcart`, `postcart`, and `emptycart`: no cap 07:56:50–08:07:20.

`postcheckout`: 47.6226 07:56:46–07:56:49; no cap at 07:56:50; 47.6226 07:56:51–07:56:54; no cap at 07:56:55; 47.6226 07:56:56–07:56:59; no cap at 07:57:00; 47.6226 07:57:01–07:57:04; no cap at 07:57:05; 47.6226 07:57:06–07:57:09; no cap at 07:57:10; 47.6226 07:57:11–07:57:14; no cap at 07:57:15; 47.6226 07:57:16–07:57:19; no cap at 07:57:20; 47.6226 07:57:21–07:57:24; no cap at 07:57:25; 47.6226 07:57:26–07:57:29; no cap 07:57:30–07:57:35; 10.4 at 07:57:40; 17.4 at 07:57:45; 24 at 07:57:50; no cap 07:57:55–07:58:15; 30 07:58:20–07:58:25; no cap 07:58:29–07:58:30; 30 07:58:35–07:58:43; no cap 07:58:45–07:59:25; 30 07:59:30–07:59:35; no cap 07:59:37–08:01:10; 30 at 08:01:15; no cap at 08:01:18; 30 at 08:01:20; no cap 08:01:25–08:04:20; 30 08:04:25–08:04:30; no cap 08:04:35–08:07:20.

### Column 2

`getproduct`, `getcart`, `postcart`, and `emptycart`: no cap 14:00:35–14:11:05.

`postcheckout`: no cap 14:00:35–14:01:45; 30 at 14:01:50; no cap 14:01:52–14:01:55; 30 14:02:00–14:02:05; no cap 14:02:10–14:07:15; 30 at 14:07:20; no cap 14:07:25–14:07:31; 30 at 14:07:35; no cap 14:07:40–14:07:45; 30 at 14:07:50; no cap 14:07:55–14:11:05.

### Column 3

`getproduct`, `getcart`, `postcart`, and `emptycart`: no cap 08:22:00–08:32:30.

`postcheckout`: no cap 08:22:00–08:22:35; 12 at 08:22:40; 10 at 08:22:45; 13.8 at 08:22:50; 23.1 at 08:22:55; 24 at 08:23:00; no cap 08:23:04–08:23:05; 30.8 at 08:23:07; no cap at 08:23:10; 30 08:23:12–08:23:15; no cap 08:23:20–08:26:20; 30 at 08:26:25; no cap 08:26:30–08:31:45; 30 08:31:47–08:31:55; no cap at 08:32:00; 30 08:32:05–08:32:10; no cap 08:32:12–08:32:30.

### Column 4

Every API is no cap 08:47:45–08:58:40.

### Column 5

Every API is no cap 13:08:20–13:19:20.

### Column 6

`getproduct`, `getcart`, `postcart`, and `emptycart`: no cap 10:58:50–11:09:45.

`postcheckout`: no cap 10:58:50–10:59:50; 12.1 at 10:59:55; no cap at 11:00:00; 16 at 11:00:05; no cap at 11:00:06; 22 at 11:00:10; no cap at 11:00:15; 24 at 11:00:16; no cap at 11:00:20; 29 at 11:00:25; no cap at 11:00:27; 30 at 11:00:30; no cap at 11:00:32; 30 at 11:00:33; no cap at 11:00:35; 30 11:00:40–11:00:45; no cap at 11:00:50; 30 at 11:00:55; no cap at 11:00:58; 30 at 11:01:00; no cap 11:01:05–11:02:01; 30 11:02:02–11:02:10; no cap 11:02:15–11:03:40; 30 at 11:03:41; no cap at 11:03:45; 30 at 11:03:50; no cap at 11:03:51; 30 11:03:54–11:03:55; no cap 11:04:00–11:06:50; 30 at 11:06:53; no cap at 11:06:55; 30 at 11:07:00; no cap at 11:07:03; 30 at 11:07:05; no cap 11:07:10–11:09:45.

### Column 7

`getproduct`, `getcart`, `postcart`, and `emptycart`: no cap 14:56:20–15:07:15.

`postcheckout`: no cap 14:56:20–14:57:20; 12.1 at 14:57:25; 14 at 14:57:30; 17.6 at 14:57:32; no cap 14:57:35–15:02:50; 30 15:02:55–15:03:00; no cap 15:03:05–15:03:10; 30 at 15:03:15; no cap at 15:03:18; 30 at 15:03:20; no cap 15:03:25–15:07:15.

## Per hold

Column 1, TopFull on and RetryGuard off. There is no `retryguard.log`, so nothing shed and nothing climbed. Checkout retry delta is 40 and volume rpr is 0.002. Recommendations retry delta is 0 and `grpc_4` is 0. No service is detector-hot. Email's overloaded share is 17.3%.

Column 2, the same arm. Checkout and recommendations retry deltas are 0. `adservice` `grpc_4` is 1. No service is detector-hot. Email's overloaded share is 8.5%. Email's ready count is 0 on all 12 of its resource samples, so its sojourn and its CPU fraction are unavailable.

Column 3, the TopFull-on replay. Nothing shed and nothing climbed. Checkout retry delta is 53 and volume rpr is 0.003. The file streak is 0 seconds (2 ticks). Recommendations retry delta is 0 and `grpc_4` is 0. No service is detector-hot. Email's overloaded share is 12.1%.

Column 4, TopFull off and RetryGuard on. The log has no transition lines. Checkout's controller `high` is 1, the file streak is 0 seconds, and the retry delta is 9. Recommendations retry delta is 0 and `grpc_4` is 0. The climb cells are em dashes. No service is detector-hot. Email's overloaded share is 16.5%. Every live cap is the 10000 passthrough.

Column 5, the same arm. No transition lines. Checkout's file streak is 1 second, `high` is 2, and the retry delta is 101 (volume rpr 0.006). Recommendations retry delta is 0 and `grpc_4` is 0. No service is detector-hot. Email's overloaded share is 10.6%, and checkout has 2 overloaded ticks (0.3%). Every live cap is the 10000 passthrough.

Column 6, both on. No transition lines. Checkout retry delta is 10, the file streak is 0 seconds, and `high` is 0. Recommendations retry delta is 0 and `grpc_4` is 0. No service is detector-hot. Email's overloaded share is 16.5%.

Column 7, both on. No transition lines. Checkout retry delta is 0. Recommendations retry delta is 1, max rpr is 0.17, and `grpc_4` is 1. No service is detector-hot. Email's overloaded share is 8.3%. Email's ready count is 0 on all 12 of its resource samples, so its CPU fraction is unavailable.

## Related links

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), section "Edge mode (`retry_metric: edge_rpr`)"
- [2026-10-08-s1-both-off-run8.md](2026-10-08-s1-both-off-run8.md), the same user counts on a 300 s both-off S1 hold
