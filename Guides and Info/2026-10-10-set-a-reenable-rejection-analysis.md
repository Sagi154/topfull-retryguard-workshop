# S2 Set A re-enable rejection sweep

600 s holds of the locked S2 mix, getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1. RetryGuard is on for every scored hold (`retry_metric: edge_rpr`). The 0→1 bar is the only setting that changes: `reenable_rejection` 0.10, 0.15, or 0.20. Each bar has a RetryGuard-only arm (TopFull off) and a both-on arm. Numbers are from `experiments/analysis_score.py` on the raw CSVs and `retryguard.log`. File streaks are seconds. The parenthetical on a streak cell is the controller's max `high`, a sample count.

## Setup

Duration 600 s. Mix getproduct / postcheckout / getcart / postcart / emptycart = 275 / 90 / 100 / 90 / 5. `spawn_rate` 50. Paper-C1 pin, request equal to limit. Frontend is 4 replicas; every other service is 1. Checkout and recommendations restart before each hold (`restart_before_hold`, 60 s settle). Cool-off is 360 s before the first hold of a session and between holds. Istio `attempts` start at 3 with `perTryTimeout` 500 ms. A shed sets that edge to 0 attempts after `rpr > 0.5` for 30 s of row timestamps. The 0→1 step needs that callee's inbound rejection strictly under the hold's `reenable_rejection` for 30 s, and it restores 1 attempt. Climbs from 1 to 2 and from 2 to 3 stay on rpr and take 15 s.

Folders are under `experiments/results/campaign_48/S2_sustained_overload/`. These names have no `run<N>` suffix, so the columns use the labels in the index.

`service_capacity.json` is this pin on every scored hold:


| Service               | Quota | Replicas |
| --------------------- | ----- | -------- |
| frontend              | 1150  | 4        |
| checkoutservice       | 800   | 1        |
| recommendationservice | 1150  | 1        |
| productcatalogservice | 800   | 1        |
| cartservice           | 800   | 1        |
| currencyservice       | 770   | 1        |
| shippingservice       | 770   | 1        |
| adservice             | 1150  | 1        |
| paymentservice        | 155   | 1        |
| emailservice          | 120   | 1        |
| redis-cart            | 540   | 1        |




## Index

One row per arm. Column order in every table follows this list, left to right. A bold bar separates the six groups.


| Group                 | Columns                   | Folders                                                                                  |
| --------------------- | ------------------------- | ---------------------------------------------------------------------------------------- |
| 0.10, RetryGuard only | 010 off1, 010 off2        | `study2_s2_rr010_rgtf0_rep1`, `study2_s2_rr010_rgtf0_rep2`                               |
| 0.10, both on         | 010 on1, 010 on2          | `study2_s2_rr010_rgtf1_rep1`, `study2_s2_rr010_rgtf1_rep3`                               |
| 0.15, RetryGuard only | 015 off1, 015 off2        | `study2_s2_rr015_rgtf0_rep1`, `study2_s2_rr015_rgtf0_rep3`                               |
| 0.15, both on         | 015 on1, 015 on2, 015 on3 | `study2_s2_rr015_rgtf1_rep1`, `study2_s2_rr015_rgtf1_rep2`, `study2_s2_rr015_rgtf1_rep3` |
| 0.20, RetryGuard only | 020 off1, 020 off2        | `study2_s2_rr020_rgtf0_rep1`, `study2_s2_rr020_rgtf0_rep2`                               |
| 0.20, both on         | 020 on1, 020 on2, 020 on3 | `study2_s2_rr020_rgtf1_rep1`, `study2_s2_rr020_rgtf1_rep3`, `study2_s2_rr020_rgtf1_rep4` |


`010 on2` is rep3. The rep2 folder of that arm is in the gate section. `015 off2` is rep3. `020 on2` is rep3 and `020 on3` is rep4.

## Gate

Nine holds passed. The six RetryGuard-only holds have checkout inbound gap2 of 0.0% (share of checkout `service_inbound.csv` gaps at least 1.5 s). The first both-on hold of each bar is under the 10% checkout gap2 line: 010 on1 is 2.0%, 015 on1 is 0.8%, 020 on1 is 6.1%. On those nine, Locust `total.csv` has 565–574 rows, frontend is 4 on every `resource_usage.csv` sample (138 or 139 samples), no service has a replica count of 0, `service_capacity.json` matches the pin, mesh span is 714–718 s, and `retryguard.log` is present.

Five both-on repeats failed that checkout gap2 check and stay in the tables. Their files are usable. The streak and retry cells on those columns count the slow polls.

- 010 on2: Locust `total.csv` 568 rows, frontend 4 on 139 samples, mesh span 717 s, inbound gaps ≥ 1.5 s 1474 of 6413, checkout gap2 23.0%.
- 015 on2: Locust `total.csv` 568 rows, frontend 4 on 138 samples, mesh span 716 s, inbound gaps ≥ 1.5 s 1914 of 5962, checkout gap2 32.1%.
- 015 on3: Locust `total.csv` 568 rows, frontend 4 on 139 samples, mesh span 716 s, inbound gaps ≥ 1.5 s 1683 of 6193, checkout gap2 27.2%.
- 020 on2: Locust `total.csv` 566 rows, frontend 4 on 139 samples, mesh span 717 s, inbound gaps ≥ 1.5 s 2552 of 5335, checkout gap2 47.8%.
- 020 on3: Locust `total.csv` 567 rows, frontend 4 on 139 samples, mesh span 717 s, inbound gaps ≥ 1.5 s 1782 of 6105, checkout gap2 29.2%.

The other scored holds, same gate fields:

- 010 off1: Locust `total.csv` 573 rows, frontend 4 on 138 samples, mesh span 716 s, inbound gaps ≥ 1.5 s 0 of 7876.
- 010 off2: Locust `total.csv` 574 rows, frontend 4 on 139 samples, mesh span 714 s, inbound gaps ≥ 1.5 s 0 of 7854.
- 010 on1: Locust `total.csv` 565 rows, frontend 4 on 138 samples, mesh span 717 s, inbound gaps ≥ 1.5 s 154 of 7733, checkout gap2 2.0%.
- 015 off1: Locust `total.csv` 573 rows, frontend 4 on 138 samples, mesh span 715 s, inbound gaps ≥ 1.5 s 0 of 7865.
- 015 off2: Locust `total.csv` 573 rows, frontend 4 on 139 samples, mesh span 715 s, inbound gaps ≥ 1.5 s 0 of 7865.
- 015 on1: Locust `total.csv` 566 rows, frontend 4 on 139 samples, mesh span 718 s, inbound gaps ≥ 1.5 s 66 of 7832, checkout gap2 0.8%.
- 020 off1: Locust `total.csv` 573 rows, frontend 4 on 139 samples, mesh span 717 s, inbound gaps ≥ 1.5 s 0 of 7887.
- 020 off2: Locust `total.csv` 573 rows, frontend 4 on 138 samples, mesh span 716 s, inbound gaps ≥ 1.5 s 0 of 7876.
- 020 on1: Locust `total.csv` 565 rows, frontend 4 on 138 samples, mesh span 718 s, inbound gaps ≥ 1.5 s 451 of 7447, checkout gap2 6.1%.

Left out of the scored tables:

- `study2_s2_rr015_rgtf0_rep2`: Locust `total.csv` has 3288 data rows and the checkout inbound span is 3621 s, so Locust ran about 3600 s.
- `study2_s2_rr010_rgtf1_rep2`: Locust `total.csv` is header-only (0 data rows). Mesh span is 715 s.
- `study2_s2_rr020_rgtf1_rep2`: no `retryguard.log`. Locust `total.csv` is header-only, the mesh span is 80 s, and `resource_usage.csv` is absent.



## Edge-mode bars

Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.10.

That line is what the scorer prints when the first folder is a 0.10 hold. The same sentence on a 0.15 folder ends in re-enable bar 0.15, and on a 0.20 folder it ends in re-enable bar 0.20. Each scored `START` line carries that hold's bar, `sample_interval=1s`, and `interval_samples=30s`. Shed and 0→1 take 30 seconds of row timestamps (`elapsed_s=30` on every shed and every 0→1 in this sweep). 1→2 and 2→3 take 15 s (`CLIMB_INTERVAL_SECONDS`); the climbs that fired are `elapsed_s=15`. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

The under-bar rejection table later in this guide uses each hold's own re-enable bar. A 0.10 column counts samples strictly under 0.10. A 0.15 column counts samples strictly under 0.15. A 0.20 column counts samples strictly under 0.20.

## (a) Edge rpr

Longest file streak in seconds of rpr > 0.5, then the number of scored ticks above 0.5. The parenthetical is the controller's max `high`. **Bold** is a file streak of at least 30 seconds. A shed in this sweep fires at `elapsed_s=30`, so `high` can sit in the mid-20s when the timestamp bar is already met (010 off2 recommendations `high` 25, 015 on3 recommendations `high` 27, 020 off2 recommendations `high` 26).

Only `frontend → checkoutservice` and `frontend → recommendationservice` have a tick above the shed bar or a retry delta. The other 12 controlled edges are at retry delta 0 with no tick above 0.5 on every scored hold.

**0.10 and 0.15**


| Edge                             | 010 off1         | 010 off2         | **┃** | 010 on1     | 010 on2          | **┃** | 015 off1         | 015 off2         | **┃** | 015 on1     | 015 on2     | 015 on3          |
| -------------------------------- | ---------------- | ---------------- | ----- | ----------- | ---------------- | ----- | ---------------- | ---------------- | ----- | ----------- | ----------- | ---------------- |
| frontend → checkoutservice       | **32 / 34 (31)** | 8 / 9 (9)        | **┃** | 7 / 149 (7) | 5 / 5 (5)        | **┃** | 0 / 0 (0)        | **32 / 33 (31)** | **┃** | 7 / 180 (8) | 7 / 122 (6) | 6 / 6 (6)        |
| frontend → recommendationservice | **32 / 33 (31)** | **31 / 32 (25)** | **┃** | 0 / 0 (0)   | **32 / 57 (30)** | **┃** | **32 / 33 (31)** | 0 / 0 (0)        | **┃** | 0 / 0 (0)   | 0 / 0 (0)   | **32 / 64 (27)** |


**0.20**


| Edge                             | 020 off1         | 020 off2         | **┃** | 020 on1     | 020 on2     | 020 on3     |
| -------------------------------- | ---------------- | ---------------- | ----- | ----------- | ----------- | ----------- |
| frontend → checkoutservice       | **32 / 36 (31)** | 0 / 0 (0)        | **┃** | 7 / 133 (8) | 7 / 104 (7) | 7 / 127 (7) |
| frontend → recommendationservice | **32 / 33 (31)** | **32 / 33 (26)** | **┃** | 0 / 0 (0)   | 0 / 0 (0)   | 0 / 0 (0)   |


Mean rpr / max rpr / volume rpr. Volume is the hold's `Δretry / first attempts`.

**0.10 and 0.15**


| Edge                             | 010 off1             | 010 off2             | **┃** | 010 on1              | 010 on2              | **┃** | 015 off1             | 015 off2             | **┃** | 015 on1              | 015 on2              | 015 on3              |
| -------------------------------- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | -------------------- |
| frontend → checkoutservice       | 0.128 / 3.58 / 0.092 | 0.038 / 3.40 / 0.026 | **┃** | 0.667 / 7.20 / 0.562 | 0.023 / 3.40 / 0.017 | **┃** | 0.000 / 0.10 / 0.001 | 0.123 / 3.51 / 0.071 | **┃** | 0.757 / 7.00 / 0.693 | 0.701 / 7.05 / 0.640 | 0.030 / 4.00 / 0.016 |
| frontend → recommendationservice | 0.048 / 1.25 / 0.040 | 0.063 / 2.36 / 0.048 | **┃** | 0.000 / 0.00 / 0.000 | 0.166 / 2.67 / 0.114 | **┃** | 0.088 / 2.69 / 0.060 | 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | 0.166 / 2.26 / 0.124 |


**0.20**


| Edge                             | 020 off1             | 020 off2             | **┃** | 020 on1              | 020 on2              | 020 on3              |
| -------------------------------- | -------------------- | -------------------- | ----- | -------------------- | -------------------- | -------------------- |
| frontend → checkoutservice       | 0.130 / 3.41 / 0.099 | 0.001 / 0.19 / 0.001 | **┃** | 0.584 / 6.80 / 0.486 | 0.639 / 4.50 / 0.594 | 0.669 / 5.71 / 0.582 |
| frontend → recommendationservice | 0.067 / 2.03 / 0.050 | 0.063 / 2.11 / 0.048 | **┃** | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | 0.001 / 0.25 / 0.000 |


Climb streaks are `OBSERVE` samples while that attempt cap is in force: samples at 1 attempt with rpr at or under 0.17, then samples at 2 attempts with rpr at or under 0.33. An em dash means that cap never applied.

**0.10 and 0.15**


| Edge                             | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| -------------------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend → checkoutservice       | 16 / 16  | — / —    | **┃** | — / —   | — / —   | **┃** | — / —    | — / —    | **┃** | — / —   | — / —   | — / —   |
| frontend → recommendationservice | — / —    | — / —    | **┃** | — / —   | — / —   | **┃** | — / —    | — / —    | **┃** | — / —   | — / —   | — / —   |


**0.20**


| Edge                             | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| -------------------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend → checkoutservice       | 16 / 16  | — / —    | **┃** | — / —   | — / —   | — / —   |
| frontend → recommendationservice | — / —    | — / —    | **┃** | — / —   | — / —   | — / —   |


The only climbs are checkout on 010 off1 and 020 off1. Both climb streaks are 16 samples, and both steps fired at rpr 0.00 or 0.01 with `elapsed_s=15`. Every other edge never sat at 1 or 2 attempts.

## Rejection, beside (a)

This is `(Δ5xx + Δresets) / Δtotal` from `service_inbound.csv`. It is beside the shed signal. A non-positive total delta breaks the streak. **Bold** in the 0.20 table is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain.

**0.10 and 0.15**


| Service                     | 010 off1    | 010 off2  | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2     | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------------- | ----------- | --------- | ----- | ------- | ------- | ----- | -------- | ------------ | ----- | ------- | ------- | ------- |
| frontend (not controlled)   | 8 / 132     | 143 / 463 | **┃** | 1 / 1   | 16 / 90 | **┃** | 31 / 443 | 1 / 1        | **┃** | 1 / 1   | 0 / 0   | 11 / 92 |
| checkoutservice             | **35 / 37** | 9 / 9     | **┃** | 8 / 152 | 5 / 5   | **┃** | 1 / 1    | **35 / 115** | **┃** | 8 / 183 | 7 / 125 | 6 / 6   |
| recommendationservice       | 1 / 2       | 3 / 21    | **┃** | 0 / 0   | 2 / 11  | **┃** | 2 / 8    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 1 / 3   |
| paymentservice              | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 1 / 1   | 1 / 1   | 0 / 0   |
| emailservice                | 4 / 20      | 2 / 6     | **┃** | 5 / 75  | 2 / 3   | **┃** | 1 / 1    | 2 / 116      | **┃** | 3 / 71  | 4 / 55  | 1 / 2   |
| productcatalogservice       | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| cartservice                 | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| currencyservice             | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| shippingservice             | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| adservice                   | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| redis-cart (not controlled) | 0 / 0       | 0 / 0     | **┃** | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |


**0.20**


| Service                     | 020 off1    | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------------- | ----------- | -------- | ----- | ------- | ------- | ------- |
| frontend (not controlled)   | 33 / 332    | 25 / 370 | **┃** | 1 / 1   | 0 / 0   | 0 / 0   |
| checkoutservice             | **34 / 38** | 0 / 0    | **┃** | 9 / 133 | 6 / 104 | 7 / 126 |
| recommendationservice       | 1 / 6       | 3 / 4    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| paymentservice              | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| emailservice                | 2 / 13      | 0 / 0    | **┃** | 6 / 66  | 4 / 44  | 5 / 53  |
| productcatalogservice       | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| cartservice                 | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| currencyservice             | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| shippingservice             | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| adservice                   | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| redis-cart (not controlled) | 0 / 0       | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |


Longest streak strictly under that column's re-enable bar, then the count of samples under the bar. The streak is a count of inbound rows. The controller's 0→1 step is 30 seconds of its own OFF-window samples (`elapsed_s=30`), listed with the toggles.

**0.10 and 0.15**


| Service                     | 010 off1  | 010 off2  | **┃** | 010 on1   | 010 on2   | **┃** | 015 off1  | 015 off2  | **┃** | 015 on1   | 015 on2   | 015 on3   |
| --------------------------- | --------- | --------- | ----- | --------- | --------- | ----- | --------- | --------- | ----- | --------- | --------- | --------- |
| frontend (not controlled)   | 59 / 116  | 58 / 60   | **┃** | 68 / 570  | 57 / 142  | **┃** | 50 / 70   | 266 / 609 | **┃** | 606 / 606 | 440 / 440 | 81 / 217  |
| checkoutservice             | 415 / 572 | 428 / 602 | **┃** | 47 / 420  | 431 / 470 | **┃** | 610 / 610 | 51 / 431  | **┃** | 48 / 419  | 45 / 308  | 406 / 452 |
| recommendationservice       | 87 / 545  | 57 / 296  | **┃** | 598 / 598 | 55 / 382  | **┃** | 234 / 578 | 612 / 612 | **┃** | 607 / 607 | 440 / 440 | 255 / 439 |
| paymentservice              | 612 / 612 | 612 / 612 | **┃** | 325 / 596 | 477 / 477 | **┃** | 611 / 611 | 555 / 610 | **┃** | 350 / 603 | 190 / 436 | 459 / 459 |
| emailservice                | 416 / 580 | 428 / 604 | **┃** | 48 / 457  | 432 / 470 | **┃** | 610 / 610 | 50 / 425  | **┃** | 47 / 487  | 44 / 356  | 408 / 455 |
| productcatalogservice       | 613 / 613 | 613 / 613 | **┃** | 599 / 599 | 478 / 478 | **┃** | 612 / 612 | 612 / 612 | **┃** | 606 / 606 | 439 / 439 | 460 / 460 |
| cartservice                 | 613 / 613 | 613 / 613 | **┃** | 599 / 599 | 478 / 478 | **┃** | 612 / 612 | 612 / 612 | **┃** | 607 / 607 | 440 / 440 | 460 / 460 |
| currencyservice             | 613 / 613 | 613 / 613 | **┃** | 599 / 599 | 478 / 478 | **┃** | 612 / 612 | 612 / 612 | **┃** | 607 / 607 | 440 / 440 | 460 / 460 |
| shippingservice             | 613 / 613 | 613 / 613 | **┃** | 599 / 599 | 478 / 478 | **┃** | 612 / 612 | 612 / 612 | **┃** | 606 / 606 | 439 / 439 | 460 / 460 |
| adservice                   | 611 / 611 | 612 / 612 | **┃** | 598 / 598 | 478 / 478 | **┃** | 611 / 611 | 611 / 611 | **┃** | 606 / 606 | 439 / 439 | 459 / 459 |
| redis-cart (not controlled) | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | 0 / 0     |


**0.20**


| Service                     | 020 off1  | 020 off2  | **┃** | 020 on1   | 020 on2   | 020 on3   |
| --------------------------- | --------- | --------- | ----- | --------- | --------- | --------- |
| frontend (not controlled)   | 84 / 281  | 55 / 242  | **┃** | 571 / 571 | 381 / 381 | 451 / 451 |
| checkoutservice             | 331 / 574 | 612 / 612 | **┃** | 44 / 438  | 47 / 276  | 48 / 323  |
| recommendationservice       | 498 / 607 | 528 / 609 | **┃** | 572 / 572 | 381 / 381 | 450 / 450 |
| paymentservice              | 612 / 612 | 612 / 612 | **┃** | 571 / 571 | 380 / 380 | 449 / 449 |
| emailservice                | 333 / 590 | 362 / 611 | **┃** | 44 / 481  | 46 / 319  | 48 / 372  |
| productcatalogservice       | 613 / 613 | 613 / 613 | **┃** | 572 / 572 | 381 / 381 | 450 / 450 |
| cartservice                 | 613 / 613 | 613 / 613 | **┃** | 572 / 572 | 381 / 381 | 450 / 450 |
| currencyservice             | 613 / 613 | 613 / 613 | **┃** | 572 / 572 | 380 / 380 | 450 / 450 |
| shippingservice             | 613 / 613 | 613 / 613 | **┃** | 572 / 572 | 380 / 380 | 450 / 450 |
| adservice                   | 612 / 612 | 612 / 612 | **┃** | 571 / 571 | 379 / 379 | 450 / 450 |
| redis-cart (not controlled) | 0 / 0     | 0 / 0     | **┃** | 0 / 0     | 0 / 0     | 0 / 0     |


`grpc_4 / grpc_14` for the four read callees. The controller adds these two deltas on top of 5xx + resets for recommendationservice, productcatalogservice, currencyservice, and adservice. Checkout, payment, email, cart, and shipping stay on 5xx + resets.

**0.10 and 0.15**


| Service               | 010 off1   | 010 off2   | **┃** | 010 on1 | 010 on2    | **┃** | 015 off1   | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3    |
| --------------------- | ---------- | ---------- | ----- | ------- | ---------- | ----- | ---------- | -------- | ----- | ------- | ------- | ---------- |
| recommendationservice | 41,210 / 0 | 62,524 / 0 | **┃** | 0 / 0   | 46,082 / 0 | **┃** | 63,491 / 0 | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 51,113 / 0 |
| productcatalogservice | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |
| currencyservice       | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |
| adservice             | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |


**0.20**


| Service               | 020 off1   | 020 off2   | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | ---------- | ---------- | ----- | ------- | ------- | ------- |
| recommendationservice | 55,667 / 0 | 56,068 / 0 | **┃** | 0 / 0   | 0 / 0   | 2 / 0   |
| productcatalogservice | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| currencyservice       | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| adservice             | 0 / 0      | 0 / 0      | **┃** | 18 / 0  | 0 / 0   | 0 / 0   |




## (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows, as ticks/rows (share%). **Bold** is a share of at least 0.5. With the RL loop off, this is the engagement signal that still moves. Checkout is detector-hot on every scored hold. Email is detector-hot on 010 off1 (62.4%), 015 off1 (64.7%), 015 off2 (80.9%), and 020 off1 (55.4%). Recommendations stays under 7% on every hold.

**0.10 and 0.15**


| Service               | 010 off1            | 010 off2            | **┃** | 010 on1             | 010 on2             | **┃** | 015 off1            | 015 off2            | **┃** | 015 on1             | 015 on2             | 015 on3             |
| --------------------- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ------------------- |
| frontend              | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| checkoutservice       | **586/662 (88.5%)** | **566/661 (85.6%)** | **┃** | **366/662 (55.3%)** | **483/662 (73.0%)** | **┃** | **561/662 (84.7%)** | **588/661 (89.0%)** | **┃** | **364/663 (54.9%)** | **353/662 (53.3%)** | **470/662 (71.0%)** |
| recommendationservice | 9/662 (1.4%)        | 22/661 (3.3%)       | **┃** | 0/662 (0.0%)        | 41/662 (6.2%)       | **┃** | 38/662 (5.7%)       | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 46/662 (6.9%)       |
| paymentservice        | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| emailservice          | **413/662 (62.4%)** | 319/661 (48.3%)     | **┃** | 140/662 (21.1%)     | 148/662 (22.4%)     | **┃** | **428/662 (64.7%)** | **535/661 (80.9%)** | **┃** | 105/663 (15.8%)     | 113/662 (17.1%)     | 271/662 (40.9%)     |
| productcatalogservice | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| cartservice           | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| currencyservice       | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| shippingservice       | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| adservice             | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| redis-cart            | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |


**0.20**


| Service               | 020 off1            | 020 off2            | **┃** | 020 on1             | 020 on2             | 020 on3             |
| --------------------- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ------------------- |
| frontend              | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| checkoutservice       | **573/664 (86.3%)** | **572/661 (86.5%)** | **┃** | **390/662 (58.9%)** | **355/662 (53.6%)** | **381/662 (57.6%)** |
| recommendationservice | 29/664 (4.4%)       | 26/661 (3.9%)       | **┃** | 15/662 (2.3%)       | 0/662 (0.0%)        | 0/662 (0.0%)        |
| paymentservice        | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 1/662 (0.2%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| emailservice          | **368/664 (55.4%)** | 287/661 (43.4%)     | **┃** | 163/662 (24.6%)     | 122/662 (18.4%)     | 135/662 (20.4%)     |
| productcatalogservice | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| cartservice           | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| currencyservice       | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| shippingservice       | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| adservice             | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| redis-cart            | 0/664 (0.0%)        | 0/661 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |




## (c) Retry volume

Outbound retry delta by target, the sum of positive `retry` increments on `service_edges.csv`. Every other target is 0.

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| checkoutservice       | 3,579    | 887      | **┃** | 15,209  | 477     | **┃** | 21       | 3,644    | **┃** | 18,077  | 16,860  | 520     |
| recommendationservice | 10,732   | 12,777   | **┃** | 0       | 27,627  | **┃** | 16,013   | 0        | **┃** | 0       | 0       | 30,600  |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| checkoutservice       | 3,586    | 35       | **┃** | 13,500  | 15,188  | 16,010  |
| recommendationservice | 13,378   | 13,007   | **┃** | 0       | 0       | 2       |


Inbound resets for all 11 services.

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 267      | 233      | **┃** | 173     | 304     | **┃** | 253      | 117      | **┃** | 105     | 16      | 222     |
| checkoutservice       | 2,598    | 615      | **┃** | 10,347  | 304     | **┃** | 23       | 8,012    | **┃** | 12,481  | 11,655  | 352     |
| recommendationservice | 17,397   | 30,243   | **┃** | 8       | 20,741  | **┃** | 24,026   | 2        | **┃** | 13      | 4       | 19,675  |
| paymentservice        | 118      | 15       | **┃** | 517     | 8       | **┃** | 0        | 198      | **┃** | 794     | 655     | 18      |
| emailservice          | 190      | 104      | **┃** | 1,340   | 64      | **┃** | 25       | 6,325    | **┃** | 932     | 1,181   | 45      |
| productcatalogservice | 6        | 1        | **┃** | 38      | 5       | **┃** | 2        | 26       | **┃** | 5       | 3       | 9       |
| cartservice           | 174      | 55       | **┃** | 749     | 18      | **┃** | 0        | 178      | **┃** | 803     | 762     | 23      |
| currencyservice       | 0        | 2        | **┃** | 0       | 0       | **┃** | 0        | 5        | **┃** | 0       | 3       | 0       |
| shippingservice       | 257      | 38       | **┃** | 842     | 17      | **┃** | 0        | 245      | **┃** | 1,174   | 879     | 23      |
| adservice             | 1        | 2        | **┃** | 0       | 1       | **┃** | 0        | 0        | **┃** | 0       | 0       | 2       |
| redis-cart            | 0        | 0        | **┃** | 0       | 0       | **┃** | 0        | 0        | **┃** | 0       | 0       | 0       |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 278      | 257      | **┃** | 21      | 4       | 15      |
| checkoutservice       | 2,524    | 25       | **┃** | 9,455   | 10,432  | 11,011  |
| recommendationservice | 19,799   | 23,026   | **┃** | 0       | 1       | 7       |
| paymentservice        | 153      | 0        | **┃** | 482     | 488     | 505     |
| emailservice          | 144      | 22       | **┃** | 1,426   | 1,434   | 1,146   |
| productcatalogservice | 10       | 4        | **┃** | 5       | 1       | 0       |
| cartservice           | 196      | 1        | **┃** | 606     | 691     | 761     |
| currencyservice       | 1        | 2        | **┃** | 0       | 0       | 0       |
| shippingservice       | 250      | 1        | **┃** | 720     | 815     | 935     |
| adservice             | 0        | 0        | **┃** | 0       | 0       | 0       |
| redis-cart            | 0        | 0        | **┃** | 0       | 0       | 0       |


The same `grpc_4 / grpc_14` pair is what the retry policy counts on the four read callees. `grpc_14` is 0 on every cell. Recommendations `grpc_4` is the large count, and it is 0 on the holds whose recommendations retry delta is 0.

**0.10 and 0.15**


| Service               | 010 off1   | 010 off2   | **┃** | 010 on1 | 010 on2    | **┃** | 015 off1   | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3    |
| --------------------- | ---------- | ---------- | ----- | ------- | ---------- | ----- | ---------- | -------- | ----- | ------- | ------- | ---------- |
| recommendationservice | 41,210 / 0 | 62,524 / 0 | **┃** | 0 / 0   | 46,082 / 0 | **┃** | 63,491 / 0 | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 51,113 / 0 |
| productcatalogservice | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |
| currencyservice       | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |
| adservice             | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0      | **┃** | 0 / 0      | 0 / 0    | **┃** | 0 / 0   | 0 / 0   | 0 / 0      |


**0.20**


| Service               | 020 off1   | 020 off2   | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | ---------- | ---------- | ----- | ------- | ------- | ------- |
| recommendationservice | 55,667 / 0 | 56,068 / 0 | **┃** | 0 / 0   | 0 / 0   | 2 / 0   |
| productcatalogservice | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| currencyservice       | 0 / 0      | 0 / 0      | **┃** | 0 / 0   | 0 / 0   | 0 / 0   |
| adservice             | 0 / 0      | 0 / 0      | **┃** | 18 / 0  | 0 / 0   | 0 / 0   |




## RetryGuard toggles

`ON→OFF` is the shed to 0 attempts. The 0→1 column is the log's `OFF→ON` onto the callee name (`attempts=1`, `from_attempts=0`). `1→2` and `2→3` are the climb lines. Time off below is seconds from the shed timestamp to the re-enable timestamp, or to `SHUTDOWN` when the edge is still at 0.

### 010 off1


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → checkoutservice       | 1      | 0   | 1   | 1   |
| checkoutservice                  | 0      | 1   | 0   | 0   |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value          |
| -------------------- | -------------------------------- | ------ | ---- | -------------- |
| 2026-10-08T23:54:32Z | frontend → checkoutservice       | ON→OFF | 3    | rpr 2.14       |
| 2026-10-08T23:55:07Z | checkoutservice                  | OFF→ON | 0    | rejection 0.00 |
| 2026-10-08T23:55:08Z | frontend → recommendationservice | ON→OFF | 3    | rpr 0.72       |
| 2026-10-08T23:55:23Z | frontend → checkoutservice       | 1→2    | 1    | rpr 0.00       |
| 2026-10-08T23:55:39Z | frontend → checkoutservice       | 2→3    | 2    | rpr 0.01       |




### 010 off2


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-09T06:12:49Z | frontend → recommendationservice | ON→OFF | 3    | rpr 0.90 |


010 on1 has no transition lines.

### 010 on2


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-09T05:49:40Z | frontend → recommendationservice | ON→OFF | 3    | rpr 1.96 |




### 015 off1


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-08T23:03:39Z | frontend → recommendationservice | ON→OFF | 3    | rpr 1.38 |




### 015 off2


| Name                       | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------- | ------ | --- | --- | --- |
| frontend → checkoutservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                       | Step   | From | Value    |
| -------------------- | -------------------------- | ------ | ---- | -------- |
| 2026-10-09T03:21:33Z | frontend → checkoutservice | ON→OFF | 3    | rpr 2.60 |


015 on1 has no transition lines.

015 on2 has no transition lines.

### 015 on3


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-09T06:49:03Z | frontend → recommendationservice | ON→OFF | 3    | rpr 0.95 |




### 020 off1


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → checkoutservice       | 1      | 0   | 1   | 1   |
| checkoutservice                  | 0      | 1   | 0   | 0   |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value          |
| -------------------- | -------------------------------- | ------ | ---- | -------------- |
| 2026-10-08T23:29:51Z | frontend → checkoutservice       | ON→OFF | 3    | rpr 2.61       |
| 2026-10-08T23:30:26Z | checkoutservice                  | OFF→ON | 0    | rejection 0.00 |
| 2026-10-08T23:30:26Z | frontend → recommendationservice | ON→OFF | 3    | rpr 1.20       |
| 2026-10-08T23:30:42Z | frontend → checkoutservice       | 1→2    | 1    | rpr 0.00       |
| 2026-10-08T23:30:58Z | frontend → checkoutservice       | 2→3    | 2    | rpr 0.00       |




### 020 off2


| Name                             | ON→OFF | 0→1 | 1→2 | 2→3 |
| -------------------------------- | ------ | --- | --- | --- |
| frontend → recommendationservice | 1      | 0   | 0   | 0   |



| Time (UTC)           | Name                             | Step   | From | Value    |
| -------------------- | -------------------------------- | ------ | ---- | -------- |
| 2026-10-09T01:35:43Z | frontend → recommendationservice | ON→OFF | 3    | rpr 1.20 |


020 on1 has no transition lines.

020 on2 has no transition lines.

020 on3 has no transition lines.

Time at 0 attempts, from those timestamps to the matching `SHUTDOWN`:

- 010 off1 checkout is off for 35 s (23:54:32Z to 23:55:07Z), then back to 3. Recommendations is off from 23:55:08Z to SHUTDOWN 00:03:23Z, 495 s.
- 010 off2 recommendations is off from 06:12:49Z to SHUTDOWN 06:21:35Z, 526 s.
- 010 on2 recommendations is off from 05:49:40Z to SHUTDOWN 05:56:40Z, 420 s.
- 015 off1 recommendations is off from 23:03:39Z to SHUTDOWN 23:12:32Z, 533 s.
- 015 off2 checkout is off from 03:21:33Z to SHUTDOWN 03:30:25Z, 532 s.
- 015 on3 recommendations is off from 06:49:03Z to SHUTDOWN 06:55:22Z, 379 s.
- 020 off1 checkout is off for 35 s (23:29:51Z to 23:30:26Z), then back to 3. Recommendations is off from 23:30:26Z to SHUTDOWN 23:38:47Z, 501 s.
- 020 off2 recommendations is off from 01:35:43Z to SHUTDOWN 01:44:34Z, 531 s.

On the OFF-window `OBSERVE` lines, the longest run with rejection strictly under the hold's own bar is 31 samples for the two checkout returns (max `elapsed_s` 30, rejection 0.00 at the 0→1 line). It is 14 samples for the 015 off2 checkout that stayed off (max `elapsed_s` 15). On that same 015 off2 window the longest run under 0.10 is 10 samples and under 0.20 is 20, so a 30 s quiet interval is absent at every bar in the sweep. Every recommendations OFF window peaks at 1–3 samples under its own bar. The longest recommendations run under 0.20, on any hold, is 18 samples (010 on2).

## Locust goodput

Mean `Goodput` while `RPS > 0`, per API.

**0.10 and 0.15**


| API          | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 205.8    | 172.5    | **┃** | 263.9   | 197.2   | **┃** | 183.7    | 264.3    | **┃** | 232.2   | 264.1   | 199.0   |
| postcheckout | 59.5     | 55.1     | **┃** | 32.9    | 45.1    | **┃** | 60.2     | 63.8     | **┃** | 29.1    | 30.4    | 49.8    |
| getcart      | 83.5     | 71.5     | **┃** | 96.1    | 76.0    | **┃** | 66.8     | 96.1     | **┃** | 87.7    | 96.0    | 70.5    |
| postcart     | 86.4     | 86.5     | **┃** | 86.3    | 86.4    | **┃** | 86.6     | 86.5     | **┃** | 86.4    | 86.4    | 86.4    |
| emptycart    | 4.8      | 4.8      | **┃** | 4.8     | 4.8     | **┃** | 4.8      | 4.8      | **┃** | 4.8     | 4.8     | 4.8     |


**0.20**


| API          | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 197.1    | 192.0    | **┃** | 264.2   | 264.0   | 263.8   |
| postcheckout | 55.4     | 57.0     | **┃** | 35.0    | 30.1    | 32.9    |
| getcart      | 71.2     | 74.0     | **┃** | 96.0    | 96.2    | 96.0    |
| postcart     | 86.4     | 86.4     | **┃** | 86.4    | 86.4    | 86.4    |
| emptycart    | 4.8      | 4.8      | **┃** | 4.8     | 4.8     | 4.8     |


postcart stays at 86.3–86.6 and emptycart stays at 4.8 on every hold. getproduct and getcart are the cells that move, and the two repeats of one bar often sit in different places. See Per arm.

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`, per API.

**0.10 and 0.15**


| API          | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 0.204    | 0.326    | **┃** | 0.000   | 0.226   | **┃** | 0.285    | 0.000    | **┃** | 0.117   | 0.000   | 0.216   |
| postcheckout | 0.289    | 0.339    | **┃** | 0.566   | 0.447   | **┃** | 0.283    | 0.251    | **┃** | 0.601   | 0.586   | 0.390   |
| getcart      | 0.117    | 0.240    | **┃** | 0.000   | 0.182   | **┃** | 0.285    | 0.000    | **┃** | 0.083   | 0.000   | 0.234   |
| postcart     | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| emptycart    | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |


**0.20**


| API          | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 0.236    | 0.254    | **┃** | 0.000   | 0.000   | 0.000   |
| postcheckout | 0.336    | 0.319    | **┃** | 0.544   | 0.595   | 0.563   |
| getcart      | 0.239    | 0.212    | **┃** | 0.000   | 0.000   | 0.000   |
| postcart     | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| emptycart    | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |




## Locust P95

Mean `Latency95` (ms) while `RPS > 0`, per API.

**0.10 and 0.15**


| API          | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 679      | 707      | **┃** | 344     | 786     | **┃** | 686      | 398      | **┃** | 285     | 317     | 796     |
| postcheckout | 991      | 886      | **┃** | 934     | 845     | **┃** | 858      | 743      | **┃** | 955     | 967     | 910     |
| getcart      | 650      | 670      | **┃** | 348     | 749     | **┃** | 667      | 382      | **┃** | 292     | 311     | 765     |
| postcart     | 75       | 76       | **┃** | 79      | 76      | **┃** | 75       | 80       | **┃** | 74      | 76      | 74      |
| emptycart    | 17       | 19       | **┃** | 12      | 18      | **┃** | 20       | 27       | **┃** | 25      | 19      | 19      |


**0.20**


| API          | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ----- | ------- | ------- | ------- |
| getproduct   | 670      | 683      | **┃** | 355     | 339     | 320     |
| postcheckout | 944      | 862      | **┃** | 916     | 955     | 939     |
| getcart      | 647      | 661      | **┃** | 353     | 350     | 324     |
| postcart     | 75       | 75       | **┃** | 80      | 79      | 78      |
| emptycart    | 17       | 20       | **┃** | 15      | 13      | 30      |


postcheckout P95 stays in 743–991 ms on every hold. getproduct P95 is 285–398 ms on the holds with recommendations retry delta 0, and 670–796 ms on the holds with a recommendations retry delta in the thousands. 015 on1 is the in-between both-on hold: recommendations retries are 0, getproduct P95 is 285 ms, and getproduct fail rate is 0.117.

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s. redis-cart is 0.0 because its `Δtotal` is 0.

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 452.2    | 453.9    | **┃** | 422.6   | 416.7   | **┃** | 452.1    | 457.8    | **┃** | 386.3   | 422.2   | 421.6   |
| checkoutservice       | 59.2     | 49.9     | **┃** | 58.9    | 40.8    | **┃** | 52.3     | 77.0     | **┃** | 61.5    | 60.3    | 45.3    |
| recommendationservice | 389.2    | 393.6    | **┃** | 344.7   | 377.4   | **┃** | 396.4    | 379.7    | **┃** | 308.5   | 344.2   | 386.4   |
| paymentservice        | 58.7     | 49.9     | **┃** | 57.1    | 40.8    | **┃** | 52.3     | 76.1     | **┃** | 59.2    | 58.6    | 45.3    |
| emailservice          | 52.4     | 48.5     | **┃** | 33.6    | 40.1    | **┃** | 52.3     | 68.4     | **┃** | 29.4    | 31.5    | 44.5    |
| productcatalogservice | 2184.5   | 1953.2   | **┃** | 2366.5  | 2040.7  | **┃** | 2012.9   | 2577.4   | **┃** | 2122.1  | 2364.6  | 2063.6  |
| cartservice           | 494.5    | 480.8    | **┃** | 482.2   | 452.2   | **┃** | 484.5    | 533.1    | **┃** | 446.4   | 482.9   | 459.5   |
| currencyservice       | 709.9    | 686.6    | **┃** | 702.7   | 656.3   | **┃** | 685.6    | 746.9    | **┃** | 632.2   | 703.1   | 657.9   |
| shippingservice       | 187.6    | 161.5    | **┃** | 189.2   | 148.4   | **┃** | 162.6    | 232.2    | **┃** | 183.7   | 190.9   | 153.3   |
| adservice             | 178.3    | 150.3    | **┃** | 224.8   | 175.4   | **┃** | 159.7    | 225.5    | **┃** | 197.4   | 225.4   | 177.9   |
| redis-cart            | 0.0      | 0.0      | **┃** | 0.0     | 0.0     | **┃** | 0.0      | 0.0      | **┃** | 0.0     | 0.0     | 0.0     |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 450.6    | 453.2    | **┃** | 422.9   | 420.5   | 423.2   |
| checkoutservice       | 55.6     | 49.6     | **┃** | 57.5    | 56.8    | 60.7    |
| recommendationservice | 391.3    | 393.4    | **┃** | 345.2   | 342.6   | 345.3   |
| paymentservice        | 55.2     | 49.6     | **┃** | 56.2    | 54.9    | 58.9    |
| emailservice          | 48.9     | 49.6     | **┃** | 35.3    | 31.5    | 32.8    |
| productcatalogservice | 2078.9   | 2058.2   | **┃** | 2369.5  | 2354.7  | 2370.7  |
| cartservice           | 486.0    | 480.1    | **┃** | 481.4   | 477.9   | 483.4   |
| currencyservice       | 690.1    | 688.2    | **┃** | 702.1   | 698.5   | 704.2   |
| shippingservice       | 170.0    | 163.4    | **┃** | 187.7   | 184.8   | 191.8   |
| adservice             | 171.0    | 166.8    | **┃** | 224.7   | 225.1   | 225.0   |
| redis-cart            | 0.0      | 0.0      | **┃** | 0.0     | 0.0     | 0.0     |




## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. redis-cart is an em dash because there is no `rq_time_count` to divide.

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 486      | 490      | **┃** | 204     | 477     | **┃** | 496      | 243      | **┃** | 180     | 190     | 479     |
| checkoutservice       | 198      | 153      | **┃** | 310     | 109     | **┃** | 144      | 382      | **┃** | 324     | 318     | 125     |
| recommendationservice | 432      | 449      | **┃** | 49      | 409     | **┃** | 461      | 46       | **┃** | 39      | 40      | 408     |
| paymentservice        | 3        | 3        | **┃** | 5       | 2       | **┃** | 3        | 5        | **┃** | 6       | 5       | 2       |
| emailservice          | 32       | 25       | **┃** | 39      | 20      | **┃** | 26       | 85       | **┃** | 33      | 36      | 21      |
| productcatalogservice | 4        | 4        | **┃** | 5       | 5       | **┃** | 4        | 6        | **┃** | 4       | 4       | 4       |
| cartservice           | 3        | 3        | **┃** | 4       | 3       | **┃** | 3        | 4        | **┃** | 3       | 3       | 3       |
| currencyservice       | 3        | 3        | **┃** | 4       | 3       | **┃** | 2        | 4        | **┃** | 3       | 3       | 3       |
| shippingservice       | 1        | 1        | **┃** | 1       | 1       | **┃** | 1        | 1        | **┃** | 1       | 1       | 1       |
| adservice             | 1        | 1        | **┃** | 1       | 1       | **┃** | 1        | 1        | **┃** | 1       | 1       | 1       |
| redis-cart            | —        | —        | **┃** | —       | —       | **┃** | —        | —        | **┃** | —       | —       | —       |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 482      | 491      | **┃** | 210     | 208     | 196     |
| checkoutservice       | 162      | 144      | **┃** | 303     | 311     | 322     |
| recommendationservice | 436      | 456      | **┃** | 54      | 54      | 43      |
| paymentservice        | 3        | 3        | **┃** | 6       | 5       | 5       |
| emailservice          | 24       | 23       | **┃** | 41      | 38      | 41      |
| productcatalogservice | 4        | 4        | **┃** | 5       | 5       | 5       |
| cartservice           | 3        | 3        | **┃** | 4       | 4       | 4       |
| currencyservice       | 2        | 2        | **┃** | 4       | 4       | 3       |
| shippingservice       | 1        | 1        | **┃** | 1       | 1       | 1       |
| adservice             | 1        | 1        | **┃** | 1       | 1       | 1       |
| redis-cart            | —        | —        | **┃** | —       | —       | —       |




## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. redis-cart is an em dash for the same empty count.

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 0.750    | 0.789    | **┃** | 0.040   | 0.700   | **┃** | 0.796    | 0.114    | **┃** | 0.040   | 0.039   | 0.678   |
| checkoutservice       | 0.067    | 0.017    | **┃** | 0.337   | 0.012   | **┃** | 0.001    | 0.193    | **┃** | 0.410   | 0.375   | 0.012   |
| recommendationservice | 0.264    | 0.325    | **┃** | 0.000   | 0.233   | **┃** | 0.380    | 0.000    | **┃** | 0.000   | 0.000   | 0.286   |
| paymentservice        | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| emailservice          | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| productcatalogservice | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| cartservice           | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| currencyservice       | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| shippingservice       | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| adservice             | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| redis-cart            | —        | —        | **┃** | —       | —       | **┃** | —        | —        | **┃** | —       | —       | —       |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 0.755    | 0.793    | **┃** | 0.046   | 0.039   | 0.042   |
| checkoutservice       | 0.071    | 0.001    | **┃** | 0.296   | 0.354   | 0.354   |
| recommendationservice | 0.314    | 0.312    | **┃** | 0.000   | 0.000   | 0.000   |
| paymentservice        | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| emailservice          | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| productcatalogservice | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| cartservice           | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| currencyservice       | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| shippingservice       | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| adservice             | 0.000    | 0.000    | **┃** | 0.000   | 0.000   | 0.000   |
| redis-cart            | —        | —        | **┃** | —       | —       | —       |




## CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend sits above its 1150 m pod quota. Quota in the cell is the per-pod `quota` mode in `topfull_detect.csv`, and it matches the pin on every service.

**0.10 and 0.15**


| Service               | 010 off1               | 010 off2               | **┃** | 010 on1                | 010 on2                | **┃** | 015 off1               | 015 off2               | **┃** | 015 on1                | 015 on2                | 015 on3                |
| --------------------- | ---------------------- | ---------------------- | ----- | ---------------------- | ---------------------- | ----- | ---------------------- | ---------------------- | ----- | ---------------------- | ---------------------- | ---------------------- |
| frontend              | 1150 / 4 / 1245 / 1501 | 1150 / 4 / 1241 / 1515 | **┃** | 1150 / 4 / 1219 / 1477 | 1150 / 4 / 1241 / 1531 | **┃** | 1150 / 4 / 1261 / 1515 | 1150 / 4 / 1212 / 1458 | **┃** | 1150 / 4 / 1212 / 1494 | 1150 / 4 / 1238 / 1511 | 1150 / 4 / 1218 / 1533 |
| checkoutservice       | 800 / 1 / 661 / 796    | 800 / 1 / 648 / 797    | **┃** | 800 / 1 / 538 / 788    | 800 / 1 / 586 / 777    | **┃** | 800 / 1 / 662 / 797    | 800 / 1 / 676 / 797    | **┃** | 800 / 1 / 537 / 795    | 800 / 1 / 535 / 796    | 800 / 1 / 604 / 789    |
| recommendationservice | 1150 / 1 / 665 / 906   | 1150 / 1 / 689 / 1008  | **┃** | 1150 / 1 / 636 / 836   | 1150 / 1 / 662 / 989   | **┃** | 1150 / 1 / 708 / 1042  | 1150 / 1 / 677 / 837   | **┃** | 1150 / 1 / 594 / 774   | 1150 / 1 / 625 / 805   | 1150 / 1 / 666 / 968   |
| paymentservice        | 155 / 1 / 47 / 80      | 155 / 1 / 45 / 75      | **┃** | 155 / 1 / 43 / 74      | 155 / 1 / 40 / 59      | **┃** | 155 / 1 / 45 / 58      | 155 / 1 / 55 / 82      | **┃** | 155 / 1 / 44 / 83      | 155 / 1 / 42 / 77      | 155 / 1 / 41 / 64      |
| emailservice          | 120 / 1 / 84 / 112     | 120 / 1 / 83 / 109     | **┃** | 120 / 1 / 55 / 108     | 120 / 1 / 74 / 98      | **┃** | 120 / 1 / 88 / 111     | 120 / 1 / 92 / 117     | **┃** | 120 / 1 / 50 / 101     | 120 / 1 / 52 / 112     | 120 / 1 / 77 / 106     |
| productcatalogservice | 800 / 1 / 332 / 415    | 800 / 1 / 324 / 406    | **┃** | 800 / 1 / 408 / 503    | 800 / 1 / 328 / 422    | **┃** | 800 / 1 / 335 / 428    | 800 / 1 / 403 / 481    | **┃** | 800 / 1 / 410 / 501    | 800 / 1 / 413 / 506    | 800 / 1 / 331 / 429    |
| cartservice           | 800 / 1 / 302 / 382    | 800 / 1 / 311 / 398    | **┃** | 800 / 1 / 295 / 447    | 800 / 1 / 314 / 414    | **┃** | 800 / 1 / 336 / 489    | 800 / 1 / 285 / 438    | **┃** | 800 / 1 / 283 / 362    | 800 / 1 / 275 / 345    | 800 / 1 / 311 / 416    |
| currencyservice       | 770 / 1 / 346 / 425    | 770 / 1 / 352 / 453    | **┃** | 770 / 1 / 321 / 402    | 770 / 1 / 344 / 435    | **┃** | 770 / 1 / 356 / 439    | 770 / 1 / 329 / 439    | **┃** | 770 / 1 / 314 / 387    | 770 / 1 / 323 / 400    | 770 / 1 / 335 / 423    |
| shippingservice       | 770 / 1 / 92 / 113     | 770 / 1 / 90 / 112     | **┃** | 770 / 1 / 76 / 105     | 770 / 1 / 88 / 114     | **┃** | 770 / 1 / 90 / 111     | 770 / 1 / 88 / 108     | **┃** | 770 / 1 / 74 / 103     | 770 / 1 / 77 / 109     | 770 / 1 / 86 / 112     |
| adservice             | 1150 / 1 / 115 / 151   | 1150 / 1 / 107 / 141   | **┃** | 1150 / 1 / 126 / 154   | 1150 / 1 / 121 / 165   | **┃** | 1150 / 1 / 114 / 140   | 1150 / 1 / 119 / 145   | **┃** | 1150 / 1 / 124 / 158   | 1150 / 1 / 126 / 153   | 1150 / 1 / 118 / 164   |
| redis-cart            | 540 / 1 / 38 / 52      | 540 / 1 / 39 / 55      | **┃** | 540 / 1 / 34 / 47      | 540 / 1 / 40 / 53      | **┃** | 540 / 1 / 40 / 53      | 540 / 1 / 34 / 46      | **┃** | 540 / 1 / 35 / 50      | 540 / 1 / 35 / 47      | 540 / 1 / 39 / 53      |


**0.20**


| Service               | 020 off1               | 020 off2               | **┃** | 020 on1                | 020 on2                | 020 on3                |
| --------------------- | ---------------------- | ---------------------- | ----- | ---------------------- | ---------------------- | ---------------------- |
| frontend              | 1150 / 4 / 1243 / 1500 | 1150 / 4 / 1244 / 1507 | **┃** | 1150 / 4 / 1237 / 1558 | 1150 / 4 / 1246 / 1527 | 1150 / 4 / 1239 / 1533 |
| checkoutservice       | 800 / 1 / 658 / 797    | 800 / 1 / 639 / 789    | **┃** | 800 / 1 / 548 / 788    | 800 / 1 / 532 / 792    | 800 / 1 / 547 / 791    |
| recommendationservice | 1150 / 1 / 686 / 986   | 1150 / 1 / 677 / 963   | **┃** | 1150 / 1 / 654 / 944   | 1150 / 1 / 654 / 841   | 1150 / 1 / 637 / 802   |
| paymentservice        | 155 / 1 / 46 / 94      | 155 / 1 / 43 / 59      | **┃** | 155 / 1 / 45 / 79      | 155 / 1 / 42 / 73      | 155 / 1 / 43 / 76      |
| emailservice          | 120 / 1 / 81 / 111     | 120 / 1 / 83 / 113     | **┃** | 120 / 1 / 59 / 112     | 120 / 1 / 54 / 104     | 120 / 1 / 54 / 109     |
| productcatalogservice | 800 / 1 / 330 / 418    | 800 / 1 / 323 / 424    | **┃** | 800 / 1 / 410 / 503    | 800 / 1 / 413 / 506    | 800 / 1 / 412 / 506    |
| cartservice           | 800 / 1 / 333 / 476    | 800 / 1 / 312 / 399    | **┃** | 800 / 1 / 288 / 462    | 800 / 1 / 275 / 350    | 800 / 1 / 294 / 458    |
| currencyservice       | 770 / 1 / 352 / 435    | 770 / 1 / 349 / 436    | **┃** | 770 / 1 / 329 / 418    | 770 / 1 / 329 / 408    | 770 / 1 / 323 / 401    |
| shippingservice       | 770 / 1 / 90 / 114     | 770 / 1 / 89 / 112     | **┃** | 770 / 1 / 78 / 107     | 770 / 1 / 77 / 105     | 770 / 1 / 77 / 106     |
| adservice             | 1150 / 1 / 115 / 156   | 1150 / 1 / 113 / 143   | **┃** | 1150 / 1 / 129 / 164   | 1150 / 1 / 130 / 162   | 1150 / 1 / 128 / 155   |
| redis-cart            | 540 / 1 / 39 / 53      | 540 / 1 / 39 / 53      | **┃** | 540 / 1 / 35 / 49      | 540 / 1 / 35 / 49      | 540 / 1 / 34 / 47      |




## CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. Quota is the per-pod `quota` in `topfull_detect.csv`. A sample with replica count 0 is left out. No scored hold has one.

**0.10 and 0.15**


| Service               | 010 off1    | 010 off2    | **┃** | 010 on1     | 010 on2     | **┃** | 015 off1    | 015 off2    | **┃** | 015 on1     | 015 on2     | 015 on3     |
| --------------------- | ----------- | ----------- | ----- | ----------- | ----------- | ----- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- |
| frontend              | 0.27 / 0.33 | 0.27 / 0.33 | **┃** | 0.27 / 0.32 | 0.27 / 0.33 | **┃** | 0.27 / 0.33 | 0.26 / 0.32 | **┃** | 0.26 / 0.32 | 0.27 / 0.33 | 0.26 / 0.33 |
| checkoutservice       | 0.83 / 0.99 | 0.81 / 1.00 | **┃** | 0.67 / 0.98 | 0.73 / 0.97 | **┃** | 0.83 / 1.00 | 0.84 / 1.00 | **┃** | 0.67 / 0.99 | 0.67 / 0.99 | 0.76 / 0.99 |
| recommendationservice | 0.58 / 0.79 | 0.60 / 0.88 | **┃** | 0.55 / 0.73 | 0.58 / 0.86 | **┃** | 0.62 / 0.91 | 0.59 / 0.73 | **┃** | 0.52 / 0.67 | 0.54 / 0.70 | 0.58 / 0.84 |
| paymentservice        | 0.30 / 0.52 | 0.29 / 0.48 | **┃** | 0.27 / 0.48 | 0.26 / 0.38 | **┃** | 0.29 / 0.37 | 0.35 / 0.53 | **┃** | 0.28 / 0.54 | 0.27 / 0.50 | 0.26 / 0.41 |
| emailservice          | 0.70 / 0.93 | 0.70 / 0.91 | **┃** | 0.45 / 0.90 | 0.61 / 0.82 | **┃** | 0.73 / 0.93 | 0.77 / 0.97 | **┃** | 0.42 / 0.84 | 0.44 / 0.93 | 0.64 / 0.88 |
| productcatalogservice | 0.41 / 0.52 | 0.41 / 0.51 | **┃** | 0.51 / 0.63 | 0.41 / 0.53 | **┃** | 0.42 / 0.54 | 0.50 / 0.60 | **┃** | 0.51 / 0.63 | 0.52 / 0.63 | 0.41 / 0.54 |
| cartservice           | 0.38 / 0.48 | 0.39 / 0.50 | **┃** | 0.37 / 0.56 | 0.39 / 0.52 | **┃** | 0.42 / 0.61 | 0.36 / 0.55 | **┃** | 0.35 / 0.45 | 0.34 / 0.43 | 0.39 / 0.52 |
| currencyservice       | 0.45 / 0.55 | 0.46 / 0.59 | **┃** | 0.42 / 0.52 | 0.45 / 0.56 | **┃** | 0.46 / 0.57 | 0.43 / 0.57 | **┃** | 0.41 / 0.50 | 0.42 / 0.52 | 0.43 / 0.55 |
| shippingservice       | 0.12 / 0.15 | 0.12 / 0.15 | **┃** | 0.10 / 0.14 | 0.11 / 0.15 | **┃** | 0.12 / 0.14 | 0.11 / 0.14 | **┃** | 0.10 / 0.13 | 0.10 / 0.14 | 0.11 / 0.15 |
| adservice             | 0.10 / 0.13 | 0.09 / 0.12 | **┃** | 0.11 / 0.13 | 0.11 / 0.14 | **┃** | 0.10 / 0.12 | 0.10 / 0.13 | **┃** | 0.11 / 0.14 | 0.11 / 0.13 | 0.10 / 0.14 |
| redis-cart            | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.06 / 0.09 | 0.07 / 0.10 | **┃** | 0.07 / 0.10 | 0.06 / 0.09 | **┃** | 0.07 / 0.09 | 0.06 / 0.09 | 0.07 / 0.10 |


**0.20**


| Service               | 020 off1    | 020 off2    | **┃** | 020 on1     | 020 on2     | 020 on3     |
| --------------------- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- |
| frontend              | 0.27 / 0.33 | 0.27 / 0.33 | **┃** | 0.27 / 0.34 | 0.27 / 0.33 | 0.27 / 0.33 |
| checkoutservice       | 0.82 / 1.00 | 0.80 / 0.99 | **┃** | 0.69 / 0.98 | 0.66 / 0.99 | 0.68 / 0.99 |
| recommendationservice | 0.60 / 0.86 | 0.59 / 0.84 | **┃** | 0.57 / 0.82 | 0.57 / 0.73 | 0.55 / 0.70 |
| paymentservice        | 0.29 / 0.61 | 0.28 / 0.38 | **┃** | 0.29 / 0.51 | 0.27 / 0.47 | 0.28 / 0.49 |
| emailservice          | 0.68 / 0.93 | 0.69 / 0.94 | **┃** | 0.49 / 0.93 | 0.45 / 0.87 | 0.45 / 0.91 |
| productcatalogservice | 0.41 / 0.52 | 0.40 / 0.53 | **┃** | 0.51 / 0.63 | 0.52 / 0.63 | 0.51 / 0.63 |
| cartservice           | 0.42 / 0.59 | 0.39 / 0.50 | **┃** | 0.36 / 0.58 | 0.34 / 0.44 | 0.37 / 0.57 |
| currencyservice       | 0.46 / 0.56 | 0.45 / 0.57 | **┃** | 0.43 / 0.54 | 0.43 / 0.53 | 0.42 / 0.52 |
| shippingservice       | 0.12 / 0.15 | 0.12 / 0.15 | **┃** | 0.10 / 0.14 | 0.10 / 0.14 | 0.10 / 0.14 |
| adservice             | 0.10 / 0.14 | 0.10 / 0.12 | **┃** | 0.11 / 0.14 | 0.11 / 0.14 | 0.11 / 0.13 |
| redis-cart            | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.06 / 0.09 | 0.06 / 0.09 | 0.06 / 0.09 |




## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

**0.10 and 0.15**


| Service               | 010 off1 | 010 off2 | **┃** | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | **┃** | 015 on1 | 015 on2 | 015 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ----- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 0.337    | 0.342    | **┃** | 0.357   | 0.346   | **┃** | 0.344    | 0.338    | **┃** | 0.359   | 0.378   | 0.348   |
| checkoutservice       | 1.048    | 1.041    | **┃** | 1.036   | 1.029   | **┃** | 1.049    | 1.039    | **┃** | 1.052   | 1.036   | 1.039   |
| recommendationservice | 0.828    | 0.930    | **┃** | 0.790   | 0.929   | **┃** | 0.956    | 0.768    | **┃** | 0.729   | 0.737   | 0.973   |
| paymentservice        | 0.587    | 0.555    | **┃** | 0.665   | 0.510   | **┃** | 0.561    | 0.632    | **┃** | 0.774   | 0.735   | 0.542   |
| emailservice          | 1.033    | 1.042    | **┃** | 1.050   | 1.000   | **┃** | 1.025    | 1.058    | **┃** | 1.008   | 1.025   | 1.017   |
| productcatalogservice | 0.552    | 0.530    | **┃** | 0.667   | 0.583   | **┃** | 0.564    | 0.642    | **┃** | 0.664   | 0.662   | 0.583   |
| cartservice           | 0.515    | 0.574    | **┃** | 0.579   | 0.580   | **┃** | 0.680    | 0.573    | **┃** | 0.542   | 0.465   | 0.579   |
| currencyservice       | 0.613    | 0.666    | **┃** | 0.587   | 0.630   | **┃** | 0.629    | 0.640    | **┃** | 0.566   | 0.562   | 0.603   |
| shippingservice       | 0.184    | 0.179    | **┃** | 0.173   | 0.175   | **┃** | 0.182    | 0.174    | **┃** | 0.178   | 0.179   | 0.183   |
| adservice             | 0.154    | 0.149    | **┃** | 0.164   | 0.161   | **┃** | 0.141    | 0.163    | **┃** | 0.177   | 0.160   | 0.167   |
| redis-cart            | 0.202    | 0.226    | **┃** | 0.206   | 0.220   | **┃** | 0.193    | 0.183    | **┃** | 0.189   | 0.202   | 0.204   |


**0.20**


| Service               | 020 off1 | 020 off2 | **┃** | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ----- | ------- | ------- | ------- |
| frontend              | 0.338    | 0.340    | **┃** | 0.368   | 0.369   | 0.366   |
| checkoutservice       | 1.046    | 1.031    | **┃** | 1.034   | 1.049   | 1.046   |
| recommendationservice | 0.949    | 0.884    | **┃** | 0.870   | 0.773   | 0.757   |
| paymentservice        | 0.716    | 0.529    | **┃** | 0.923   | 0.703   | 0.665   |
| emailservice          | 1.017    | 1.008    | **┃** | 1.033   | 1.067   | 1.050   |
| productcatalogservice | 0.541    | 0.566    | **┃** | 0.667   | 0.682   | 0.674   |
| cartservice           | 0.624    | 0.569    | **┃** | 0.621   | 0.490   | 0.608   |
| currencyservice       | 0.626    | 0.629    | **┃** | 0.601   | 0.587   | 0.569   |
| shippingservice       | 0.183    | 0.171    | **┃** | 0.178   | 0.170   | 0.175   |
| adservice             | 0.156    | 0.177    | **┃** | 0.189   | 0.162   | 0.165   |
| redis-cart            | 0.202    | 0.189    | **┃** | 0.172   | 0.206   | 0.202   |




## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. `postcart` and `emptycart` are no cap on every live read of every scored hold.

RetryGuard-only holds have the RL loop off. 010 off2, 015 off2, and 020 off2 are no cap on every API for the whole window. 010 off1, 015 off1, and 020 off1 alternate a leftover 240 on getproduct and 91 on getcart with no cap, about every 5 s; postcheckout is no cap on those three. The cells below keep the scorer's spans. A two-value alternation is written as one line so the repeated 5 s pair is still the full set of live values.

Both-on holds keep a moving postcheckout cap. getproduct and getcart are no cap across most of those windows, with short bursts of a real cap on 010 on2, 015 on1, 015 on3, and 020 on1.

### 010 off1


| API          | Live caps                                                                                           |
| ------------ | --------------------------------------------------------------------------------------------------- |
| getproduct   | 240 and no cap alternate across 265 spans, from 240 23:52:22–23:52:24 through 240 00:03:21–00:03:23 |
| postcheckout | no cap 23:52:25–00:03:20                                                                            |
| getcart      | 91 and no cap alternate across 265 spans, from 91 23:52:22–23:52:24 through 91 00:03:21–00:03:23    |
| postcart     | no cap 23:52:25–00:03:20                                                                            |
| emptycart    | no cap 23:52:25–00:03:20                                                                            |




### 010 off2


| API          | Live caps                |
| ------------ | ------------------------ |
| getproduct   | no cap 06:10:35–06:21:35 |
| postcheckout | no cap 06:10:35–06:21:35 |
| getcart      | no cap 06:10:35–06:21:35 |
| postcart     | no cap 06:10:35–06:21:35 |
| emptycart    | no cap 06:10:35–06:21:35 |




### 010 on1


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 00:43:15–00:54:10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| postcheckout | no cap 00:43:15–00:44:25; 50.6 at 00:44:30; 59.4 at 00:44:35; no cap at 00:44:40; 75.0009 at 00:44:42; no cap at 00:44:45; 82 00:44:49–00:44:50; 33.7588 at 00:44:53; 20.8 at 00:44:55; 19.3 at 00:45:00; 43 at 00:45:05; 64.4935 at 00:45:06; 82.1 at 00:45:10; 26.6557 at 00:45:14; 26.7 at 00:45:15; 14.2 at 00:45:20; 44.8 at 00:45:25; 65.7108 at 00:45:27; 75.6 at 00:45:30; 63.9637 at 00:45:31; 43.3 at 00:45:35; 89.8 at 00:45:40; 25.5 at 00:45:45; 10 at 00:45:48; 14.1 at 00:45:50; 25.1316 at 00:45:52; 43.1 at 00:45:55; 79.9 at 00:46:00; 20.1 at 00:46:05; 14.2 at 00:46:10; 44 at 00:46:15; 84.6 at 00:46:20; 83.9 at 00:46:25; 15.5 at 00:46:30; 10 at 00:46:31; 14.1 at 00:46:35; 44.4 at 00:46:40; 83.4 at 00:46:45; 35.7613 at 00:46:48; 22.3 at 00:46:50; 19.2 at 00:46:55; 33.6709 at 00:46:57; 56 at 00:47:00; 80.5 at 00:47:05; 23 at 00:47:10; 14.1 at 00:47:15; 45.2 at 00:47:20; 86.5 at 00:47:25; 70.7 at 00:47:30; 62.8827 at 00:47:31; 64.9 at 00:47:35; 77.2 at 00:47:40; 19.3 at 00:47:45; 14 at 00:47:50; 44.5 at 00:47:55; 81.4 at 00:48:00; 57.9 at 00:48:05; 65.2 at 00:48:10; no cap at 00:48:15; 20.1 at 00:48:20; 14 at 00:48:25; 46 at 00:48:30; 82.5 at 00:48:35; 40.654 at 00:48:37; 15.4 at 00:48:40; 14.1 at 00:48:45; 25.3573 at 00:48:46; 44.2 at 00:48:50; 78.3 at 00:48:55; 21.3 at 00:49:00; 14.1342 at 00:49:03; 18.6 at 00:49:05; 30.4853 at 00:49:07; 51.5 at 00:49:10; 70 at 00:49:15; 59.4059 at 00:49:16; 78.3 at 00:49:20; 24.7 at 00:49:25; 14.1299 at 00:49:29; 14.1 at 00:49:30; 32.9155 at 00:49:33; 43.4 at 00:49:35; 61.6182 at 00:49:37; 79.3 at 00:49:40; 60.1423 at 00:49:41; 23.1 at 00:49:45; 19.8 at 00:49:50; 56.4694 at 00:49:54; 56.5 at 00:49:55; 81.2204 at 00:49:58; 84.3 at 00:50:00; 24 at 00:50:05; 10 at 00:50:10; 32.2 at 00:50:15; 72.7 at 00:50:20; 66.1807 at 00:50:23; 73 at 00:50:25; 81.6 at 00:50:30; 63.9 at 00:50:35; 56.7067 at 00:50:36; 88.5 at 00:50:40; 29.6605 at 00:50:44; 29.7 at 00:50:45; 14.1 at 00:50:50; 34.9673 at 00:50:53; 45.2 at 00:50:55; 80.9 at 00:51:00; 73.5 at 00:51:05; 17.2 at 00:51:10; 19 at 00:51:15; 52.5 at 00:51:20; 82.4 at 00:51:25; 16.8 at 00:51:30; 18.2 at 00:51:35; 24.863 at 00:51:36; 42.4 at 00:51:40; 68.5 at 00:51:45; 78 at 00:51:50; 27.9 at 00:51:55; 10 at 00:52:00; 19.3919 at 00:52:01; 32.8 at 00:52:05; 80.1 at 00:52:10; 23.6 at 00:52:15; 14.2 at 00:52:20; 26.3532 at 00:52:22; 42.4 at 00:52:25; 83.1 at 00:52:30; 48.4 at 00:52:35; 11.4672 at 00:52:38; 10 at 00:52:40; 29.7 at 00:52:45; 44.8558 at 00:52:47; 74.5 at 00:52:50; 81.8 at 00:52:55; 20.6 at 00:53:00; 14.1 at 00:53:05; 33.2677 at 00:53:08; 43.9 at 00:53:10; 82.1 at 00:53:15; 85.2 at 00:53:20; 20.6 at 00:53:25; 14.1 at 00:53:30; 45 at 00:53:35; 82.9 at 00:53:40; 79.6366 at 00:53:42; 52.2 at 00:53:45; 10 at 00:53:50; 30.8854 at 00:53:54; 30.9 at 00:53:55; 63.0613 at 00:53:58; 70.7 at 00:54:00; 81.3 at 00:54:05; 79.7 at 00:54:10; 83.8653 at 00:54:11 |
| getcart      | no cap 00:43:15–00:54:10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| postcart     | no cap 00:43:15–00:54:10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| emptycart    | no cap 00:43:15–00:54:10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |




### 010 on2


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 05:45:40–05:47:25; 202 at 05:47:30; 193.6 at 05:47:35; 191.5 at 05:47:40; no cap 05:47:43–05:48:25; 147.3 at 05:48:30; 148.5 at 05:48:35; no cap 05:48:40–05:48:45; 209 at 05:48:49; no cap at 05:48:50; 203.238 05:48:51–05:48:53; 203.2 at 05:48:55; 146.7 at 05:49:00; no cap 05:49:05–05:49:10; 272 05:56:38–05:56:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| postcheckout | no cap 05:45:40–05:46:53; 46 at 05:46:55; 55 at 05:46:56; 56 at 05:47:00; 58 at 05:47:01; no cap at 05:47:05; 23.4237 at 05:47:09; 23.4 at 05:47:10; 14.2 at 05:47:15; 22.7017 at 05:47:17; 39.1 at 05:47:20; 51.6773 at 05:47:22; 63.1 at 05:47:25; 64.0211 at 05:47:26; 25.6 at 05:47:30; 19.6695 at 05:47:32; 17.2 at 05:47:35; 21.3 at 05:47:40; 29.5686 at 05:47:41; 47.0812 at 05:47:44; 47.1 at 05:47:45; 52.845 at 05:47:49; 52.8 at 05:47:50; 12.3 at 05:47:55; 10.6 at 05:48:00; 12.3 at 05:48:05; 11.7 at 05:48:10; 19.3 at 05:48:15; 32.4077 at 05:48:16; 53.2 at 05:48:20; 54.6772 at 05:48:21; 40.1 at 05:48:25; 16.3214 at 05:48:26; 16.3 at 05:48:30; 16.2 at 05:48:35; 42.39 at 05:48:39; 42.4 at 05:48:40; 71.1 at 05:48:45; 24.7101 at 05:48:48; 24.7 at 05:48:50; 18.9483 05:48:51–05:48:53; 18.9 at 05:48:55; 17.6 at 05:49:00; 44.8 at 05:49:05; 61.6324 at 05:49:09; 61.6 at 05:49:10; 38.4841 05:49:11–05:56:38; 38.5 at 05:56:40 |
| getcart      | no cap 05:45:40–05:47:25; 75 at 05:47:30; 66.6 at 05:47:35; 64.5 at 05:47:40; no cap 05:47:45–05:48:25; 83 at 05:48:28; 53.2 at 05:48:30; 52 at 05:48:35; 110 at 05:48:40; no cap at 05:48:45; 72.9 at 05:48:50; 70.2 at 05:48:55; 54.3 at 05:49:00; no cap 05:49:05–05:49:10; 99 05:56:38–05:56:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| postcart     | no cap 05:45:40–05:56:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| emptycart    | no cap 05:45:40–05:56:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |




### 015 off1


| API          | Live caps                                                                                          |
| ------------ | -------------------------------------------------------------------------------------------------- |
| getproduct   | 240 and no cap alternate across 51 spans, from 240 23:01:31–23:01:34 through 240 23:12:31–23:12:32 |
| postcheckout | no cap 23:01:35–23:12:30                                                                           |
| getcart      | 91 and no cap alternate across 51 spans, from 91 23:01:31–23:01:34 through 91 23:12:31–23:12:32    |
| postcart     | no cap 23:01:35–23:12:30                                                                           |
| emptycart    | no cap 23:01:35–23:12:30                                                                           |




### 015 off2


| API          | Live caps                |
| ------------ | ------------------------ |
| getproduct   | no cap 03:19:25–03:30:25 |
| postcheckout | no cap 03:19:25–03:30:25 |
| getcart      | no cap 03:19:25–03:30:25 |
| postcart     | no cap 03:19:25–03:30:25 |
| emptycart    | no cap 03:19:25–03:30:25 |




### 015 on1


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | 240 and no cap alternate across 31 spans, from 240 00:18:03–00:18:04 through 240 00:19:16–00:29:05                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| postcheckout | no cap 00:18:05–00:19:15; 44 at 00:19:20; 60.5 at 00:19:24; 60.5 at 00:19:25; no cap 00:19:30–00:19:35; 75.8 at 00:19:40; 31.3424 at 00:19:43; 19.3 at 00:19:45; 19.7 at 00:19:50; 64.3 at 00:19:55; no cap at 00:20:00; 32.3 at 00:20:05; 10 at 00:20:08; 14.1 at 00:20:10; 48.1 at 00:20:15; 80.8811 at 00:20:17; 86.9 at 00:20:20; 18.2 at 00:20:25; 14.2 at 00:20:30; 47.6 at 00:20:35; 89 at 00:20:40; 27.9 at 00:20:45; 10.7161 at 00:20:47; 14.2 at 00:20:50; 36.2 at 00:20:55; 92.7 at 00:21:00; 22.1 at 00:21:05; 14.1 at 00:21:10; 49.1 at 00:21:15; 82 at 00:21:20; 27 at 00:21:25; 10.2851 at 00:21:27; 14.1 at 00:21:30; 46.2 at 00:21:35; 87 at 00:21:40; 27.6 at 00:21:45; 13.9 at 00:21:50; 48.2858 at 00:21:54; 48.3 at 00:21:55; 80.7 at 00:22:00; 33.4345 at 00:22:03; 20.5 at 00:22:05; 19.8 at 00:22:10; 61.9 at 00:22:15; 74.3 at 00:22:20; 18.1 at 00:22:25; 10 at 00:22:26; 19.2 at 00:22:30; 60.8 at 00:22:35; 96.7 at 00:22:40; 56.0299 at 00:22:42; 21.6 at 00:22:45; 14.1 at 00:22:50; 24.9401 at 00:22:52; 45.9 at 00:22:55; 73.136 at 00:22:57; 73.3 at 00:23:00; 86.1 at 00:23:05; 34.9 at 00:23:10; 13.2893 at 00:23:11; 10 at 00:23:15; 34.2 at 00:23:20; 80.1 at 00:23:25; 88.2339 at 00:23:29; 88.2 at 00:23:30; 22.1 at 00:23:35; 10 at 00:23:38; 14.2 at 00:23:40; 44.2 at 00:23:45; 76 at 00:23:50; 89.4767 at 00:23:51; 45 at 00:23:55; 17.5947 at 00:23:56; 10 at 00:24:00; 25.4 at 00:24:05; 67.2 at 00:24:10; no cap at 00:24:15; 28.4823 at 00:24:18; 17.5 at 00:24:20; 19.8 at 00:24:25; 46.5477 at 00:24:28; 62.3 at 00:24:30; 96.1531 at 00:24:33; 99 at 00:24:35; 21.1 at 00:24:40; 14.2 at 00:24:45; 36.9 at 00:24:50; 65.3225 at 00:24:51; 88.1 at 00:24:55; 49.6 at 00:25:00; 10 at 00:25:05; 26.3 at 00:25:10; 80.3 at 00:25:15; 29.4 at 00:25:20; 14.1 at 00:25:25; 47.4 at 00:25:30; 90 at 00:25:35; 23.4 at 00:25:40; 14.1 at 00:25:45; 25.8174 at 00:25:47; 46.5 at 00:25:50; 85.6 at 00:25:55; 71.0837 at 00:25:56; 27.6 at 00:26:00; 14.2 at 00:26:05; 48.3 at 00:26:10; 83.4 at 00:26:15; 33.0678 at 00:26:18; 20.2 at 00:26:20; 19.6 at 00:26:25; 36.3486 at 00:26:27; 62.5 at 00:26:30; 94 at 00:26:35; 32 at 00:26:40; 14.1 at 00:26:45; 48 at 00:26:50; 78.2 at 00:26:55; 37.9 at 00:27:00; 10 at 00:27:05; 35.8 at 00:27:10; 81.8 at 00:27:15; 90 00:27:19–00:27:20; 13.2 at 00:27:25; 19.7 at 00:27:30; 61.1 at 00:27:35; 76.4488 at 00:27:37; 89.9 at 00:27:40; 28.1 at 00:27:45; 14.2 at 00:27:50; 45.6 at 00:27:55; 83.5 at 00:28:00; 32.1 at 00:28:05; 14.2 at 00:28:10; 47.9 at 00:28:15; 81.8331 at 00:28:18; 89.9 at 00:28:20; 28.2 at 00:28:25; 14.2 at 00:28:30; 45.9 at 00:28:35; 92.6 at 00:28:40; 34.7 at 00:28:45; 10 at 00:28:48; 14.1 at 00:28:50; 48.3 at 00:28:55; 83.7 at 00:29:00; 44.9 at 00:29:05 |
| getcart      | 91 and no cap alternate across 31 spans, from 91 00:18:03–00:18:04 through 91 00:19:16–00:29:05                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| postcart     | no cap 00:18:05–00:29:05                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| emptycart    | no cap 00:18:05–00:29:05                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |




### 015 on2


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 04:51:45–05:02:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| postcheckout | no cap 04:51:45–04:52:55; 50 at 04:53:00; 63.8 at 04:53:05; no cap at 04:53:06; 74.8 at 04:53:10; no cap at 04:53:15; 75 at 04:53:16; 29 at 04:53:20; 14.1 at 04:53:25; 43.2815 at 04:53:29; 43.3 at 04:53:30; 78.5 at 04:53:35; 42.6301 at 04:53:38; 26.4 at 04:53:40; 19 at 04:53:45; 57.6 at 04:53:50; 72.3721 at 04:53:52; 85.5 at 04:53:55; 89 at 04:54:00; 35.8611 at 04:54:01; 13.9 at 04:54:05; 19.4 at 04:54:10; 52.3 at 04:54:15; 70.9078 at 04:54:18; 71 at 04:54:20; 64.4 at 04:54:25; 10.6 at 04:54:30; 10 at 04:54:31; 16.3 at 04:54:35; 47.4 at 04:54:40; 89.7 at 04:54:45; 23.7 at 04:54:50; 14.1 at 04:54:55; 25.8171 at 04:54:57; 44 at 04:55:00; 80.9 at 04:55:05; 77.3621 at 04:55:06; 80.9 at 04:55:10; 59.5 at 04:55:15; 10 04:55:19–04:55:20; 34.3 at 04:55:25; 64.8847 at 04:55:28; 64.1 at 04:55:30; 82.1 at 04:55:35; 43.7431 at 04:55:37; 17 at 04:55:40; 10.4584 at 04:55:41; 14.2 at 04:55:45; 44.5 at 04:55:50; 80.2 at 04:55:55; 28.838 at 04:55:59; 28.8 at 04:56:00; 14.2 at 04:56:05; 36.4007 at 04:56:08; 49.6 at 04:56:10; 88.8 at 04:56:15; 58.3403 at 04:56:17; 22.3 at 04:56:20; 10 at 04:56:25; 36.4 at 04:56:30; 82.3 at 04:56:35; 38.5825 at 04:56:39; 38.6 at 04:56:40; 10 at 04:56:45; 34.7 at 04:56:50; 87.2 at 04:56:55; 22.1 at 04:57:00; 18 at 04:57:05; 24.1146 at 04:57:06; 43.7 at 04:57:10; 90.1 at 04:57:15; 55.6127 at 04:57:17; 21.6 at 04:57:20; 10 at 04:57:25; 36.6 at 04:57:30; 86.8 at 04:57:35; 34.4636 at 04:57:39; 34.5 at 04:57:40; 10 04:57:43–04:57:45; 35.1 at 04:57:50; 59.1778 at 04:57:52; 79.7 at 04:57:55; 94.4 at 04:58:00; 28.4 at 04:58:05; 17.5158 at 04:58:06; 10 at 04:58:10; 14.051 at 04:58:11; 26.1 at 04:58:15; 73.1 at 04:58:20; 86.2 at 04:58:25; 28 at 04:58:30; 14.2 at 04:58:35; 47.5 at 04:58:40; 89.7 at 04:58:45; 26.8 at 04:58:50; 14.2 at 04:58:55; 46.1 at 04:59:00; 70.4659 at 04:59:02; 97.5 at 04:59:05; 30 at 04:59:10; 10 at 04:59:15; 35.7 at 04:59:20; 88.2 at 04:59:25; 29 at 04:59:30; 14.1 at 04:59:35; 26.7131 at 04:59:37; 45.9 at 04:59:40; 78.6 at 04:59:45; 86.8437 at 04:59:46; 56 at 04:59:50; 10 at 04:59:55; 26 at 05:00:00; 74.9 at 05:00:05; 93.5 at 05:00:10; 88 at 05:00:11; 33.7 at 05:00:15; 10 at 05:00:20; 35.9772 at 05:00:24; 36 at 05:00:25; 70.1161 at 05:00:28; 78.6 at 05:00:30; 73.5 at 05:00:35; 78.7737 at 05:00:37; 86.9 at 05:00:40; 71.1036 at 05:00:41; 27.6 at 05:00:45; 10 at 05:00:50; 34.5 at 05:00:55; 77.4 at 05:01:00; 79.4 at 05:01:05; 22.2 at 05:01:10; 10 at 05:01:13; 14.2 at 05:01:15; 48.2 at 05:01:20; 83.5 at 05:01:25; 26.8 at 05:01:30; 14.1 at 05:01:35; 46.1 at 05:01:40; 84.1 at 05:01:45; 25.3 at 05:01:50; 10 at 05:01:53; 14.1 at 05:01:55; 48.7 at 05:02:00; 76.2753 at 05:02:02; 91.7 at 05:02:05; 45.8 at 05:02:10; 28.3707 at 05:02:11; 11 at 05:02:15; 25.6 at 05:02:20; 68.3 at 05:02:25; 82.3 at 05:02:30; 18.1 at 05:02:35; 19.3 at 05:02:40 |
| getcart      | no cap 04:51:45–05:02:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| postcart     | no cap 04:51:45–05:02:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| emptycart    | no cap 04:51:45–05:02:40                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |




### 015 on3


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 06:44:25–06:46:15; 232 at 06:46:18; 228.1 at 06:46:20; 218.9 at 06:46:25; 257.034 at 06:46:29; 257 at 06:46:30; no cap 06:46:35–06:46:40; 220 at 06:46:42; 209.6 at 06:46:45; 201.827 at 06:46:47; 201.8 at 06:46:50; 201.827 at 06:46:51; 302.5 06:46:55–06:46:56; no cap 06:47:00–06:47:05; 201.6 at 06:47:10; 283 at 06:47:15; no cap 06:47:18–06:47:25; 233.564 at 06:47:29; 233.6 at 06:47:30; 153.7 at 06:47:35; 245.719 at 06:47:39; 245.7 at 06:47:40; no cap 06:47:42–06:47:45; 245 at 06:47:50; 149.3 at 06:47:55; 134.746 at 06:47:58; 188.7 at 06:48:00; no cap 06:48:05–06:48:10; 195.1 at 06:48:15; 187.6 at 06:48:20; 264.948 at 06:48:22; 302.5 at 06:48:25; no cap 06:48:30–06:55:20                                                                                                                                                                                          |
| postcheckout | no cap 06:44:25–06:45:35; 53 at 06:45:40; no cap 06:45:45–06:45:50; 77.3 at 06:45:55; 19 at 06:46:00; 14 at 06:46:05; 40.9762 at 06:46:09; 41 at 06:46:10; 54.1744 at 06:46:14; 54.2 at 06:46:15; 28.2 at 06:46:20; 19 at 06:46:25; 20.1 at 06:46:30; 68.3 at 06:46:35; 67.1 at 06:46:40; 33.3 at 06:46:45; 25.4974 at 06:46:47; 25.5 at 06:46:50; 33.7 at 06:46:55; 60 at 06:47:00; 58.1727 at 06:47:02; 23.6 at 06:47:05; 11.2 at 06:47:10; 13.3 at 06:47:15; 35.1 at 06:47:20; 60.9 at 06:47:25; 23.6387 at 06:47:29; 23.6 at 06:47:30; 16.9 at 06:47:35; 31.8 at 06:47:40; 70.9 at 06:47:45; 44.451 at 06:47:49; 44.5 at 06:47:50; 25.0739 at 06:47:54; 25.1 at 06:47:55; 22.6 at 06:48:00; 58 at 06:48:05; 65.9 at 06:48:10; 32.6 at 06:48:15; 25.1 at 06:48:20; 49.3146 at 06:48:23; 67.6 at 06:48:25; 76.9 at 06:48:30; 47.6226 06:48:32–06:55:19; 72.6 at 06:55:20; 47.6226 06:55:21–06:55:22 |
| getcart      | no cap 06:44:25–06:46:15; 94 at 06:46:18; 90.1 at 06:46:20; 80.9 at 06:46:25; 98.1 at 06:46:30; no cap 06:46:35–06:46:40; 84 at 06:46:42; 73.6 at 06:46:45; 65.8269 at 06:46:47; 65.8 at 06:46:50; 77.6492 at 06:46:52; 109.1 at 06:46:55; no cap 06:46:57–06:47:05; 69.6 at 06:47:10; 93.9983 at 06:47:14; 94 at 06:47:15; no cap 06:47:20–06:47:25; 82.5639 at 06:47:29; 82.6 at 06:47:30; 64.8 at 06:47:35; 108.9 at 06:47:40; no cap at 06:47:45; 91 at 06:47:50; 38.3 at 06:47:55; 63.5 at 06:48:00; 110 at 06:48:05; no cap at 06:48:10; 67.1 at 06:48:15; 59.6 at 06:48:20; 110 at 06:48:25; no cap 06:48:30–06:55:20                                                                                                                                                                                                                                                                          |
| postcart     | no cap 06:44:25–06:55:20                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| emptycart    | no cap 06:44:25–06:55:20                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |




### 020 off1


| API          | Live caps                                                                                    |
| ------------ | -------------------------------------------------------------------------------------------- |
| getproduct   | 240 and no cap alternate across 57 spans, from 240 at 23:27:44 through 240 23:38:46–23:38:47 |
| postcheckout | no cap 23:27:45–23:38:45                                                                     |
| getcart      | 91 and no cap alternate across 57 spans, from 91 at 23:27:44 through 91 23:38:46–23:38:47    |
| postcart     | no cap 23:27:45–23:38:45                                                                     |
| emptycart    | no cap 23:27:45–23:38:45                                                                     |




### 020 off2


| API          | Live caps                |
| ------------ | ------------------------ |
| getproduct   | no cap 01:33:35–01:44:30 |
| postcheckout | no cap 01:33:35–01:44:30 |
| getcart      | no cap 01:33:35–01:44:30 |
| postcart     | no cap 01:33:35–01:44:30 |
| emptycart    | no cap 01:33:35–01:44:30 |




### 020 on1


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 01:08:30–01:18:35; 275 01:18:40–01:18:45; 279.7 at 01:18:50; 291 at 01:18:55; 295.8 at 01:19:00; no cap 01:19:05–01:19:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| postcheckout | no cap 01:08:30–01:09:40; 46 at 01:09:45; 61.6 at 01:09:50; no cap at 01:09:55; 81 at 01:10:00; 75 at 01:10:01; 28.9 at 01:10:05; 10 at 01:10:10; 33.2 at 01:10:15; 65.901 at 01:10:18; 67.9 at 01:10:20; 84.9 at 01:10:25; 27.8 at 01:10:30; 14.2 at 01:10:35; 44.3 at 01:10:40; 61.8 at 01:10:45; 14.3 at 01:10:50; 18.8 at 01:10:55; 32.3353 at 01:10:56; 55.8 at 01:11:00; 76 at 01:11:05; 75.9 at 01:11:10; 75.2 at 01:11:15; 78.4 at 01:11:20; 51.5 at 01:11:25; 85.9716 at 01:11:29; 86 at 01:11:30; 24.3 at 01:11:35; 10 at 01:11:38; 14.2 at 01:11:40; 44.6 at 01:11:45; 73.7 at 01:11:50; 84.1 at 01:11:55; 26.1343 at 01:11:59; 26.1 at 01:12:00; 14.2 at 01:12:05; 44.6 at 01:12:10; 55.0873 at 01:12:11; 79.3 at 01:12:15; 21.7 at 01:12:20; 19.7 at 01:12:25; 58.2 at 01:12:30; 81.8 at 01:12:35; 23.9 at 01:12:40; 14.2 at 01:12:45; 46.1 at 01:12:50; 82.2 at 01:12:55; 77.6 at 01:13:00; 12.1 at 01:13:05; 23.8 at 01:13:10; 66.9143 at 01:13:14; 66.9 at 01:13:15; 53.8305 at 01:13:18; 66.4 at 01:13:20; 73.6 at 01:13:25; 25.1 at 01:13:30; 14.2 at 01:13:35; 44.1927 at 01:13:39; 44.2 at 01:13:40; 70.9 at 01:13:45; 94.6 at 01:13:50; 46.4967 at 01:13:52; 17.6 at 01:13:55; 14.1 at 01:14:00; 43.5 at 01:14:05; 84.4 at 01:14:10; 17.8 at 01:14:15; 19.4 at 01:14:20; 34.4865 at 01:14:22; 52.9 at 01:14:25; 73.6 at 01:14:30; 88.1 at 01:14:35; 25.1 at 01:14:40; 14.1 at 01:14:45; 32.1865 at 01:14:48; 42.4 at 01:14:50; 83.1 at 01:14:55; 16.6 at 01:15:00; 14.2 at 01:15:05; 42.9 at 01:15:10; 76.7 at 01:15:15; 23.9 at 01:15:20; 14.1 at 01:15:25; 43.5 at 01:15:30; 56.4113 at 01:15:31; 71 at 01:15:35; 90 01:15:39–01:15:40; 27.4 at 01:15:45; 14.1 at 01:15:50; 42.4 at 01:15:55; 55.3946 at 01:15:57; 77 at 01:16:00; 61.8999 at 01:16:01; 70.5 at 01:16:05; 70.4 at 01:16:10; 65.9947 at 01:16:14; 66 at 01:16:15; 81.2 at 01:16:20; 24.3 at 01:16:25; 10 at 01:16:30; 18.7956 at 01:16:31; 31.9 at 01:16:35; 66.9 at 01:16:40; 71.0182 at 01:16:43; 78.4 at 01:16:45; 16.2 at 01:16:50; 14.1 at 01:16:55; 42.8 at 01:17:00; 70.3 at 01:17:05; 79.3397 at 01:17:08; 81 at 01:17:10; 19.9 at 01:17:15; 10 at 01:17:17; 19 at 01:17:20; 42.6 at 01:17:25; 74.3 at 01:17:30; 89.3081 at 01:17:34; 89.3 at 01:17:35; 44.5 at 01:17:40; 17.0566 at 01:17:42; 10 at 01:17:45; 19.2 at 01:17:50; 52.9 at 01:17:55; 86.6 at 01:18:00; 21.9842 at 01:18:04; 22 at 01:18:05; 14.2086 at 01:18:08; 19.6 at 01:18:10; 51.6 at 01:18:15; 71.2 at 01:18:20; 23 at 01:18:25; 10 at 01:18:26; 19.6 at 01:18:30; 48.1 at 01:18:35; 53.4 at 01:18:40; 59.7987 at 01:18:41; 62.7 at 01:18:45; 63.8 at 01:18:50; 66.6 at 01:18:55; 53.1 at 01:19:00; 80.7 at 01:19:05; 65.2615 at 01:19:09; 65.3 at 01:19:10; 80.8 at 01:19:15; 28.5817 at 01:19:18; 17.6 at 01:19:20; 19.3 at 01:19:25 |
| getcart      | no cap 01:08:30–01:18:35; 98 at 01:18:40; 100 at 01:18:45; 104.7 at 01:18:50; no cap at 01:18:55; 107.8 at 01:19:00; no cap 01:19:05–01:19:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| postcart     | no cap 01:08:30–01:19:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| emptycart    | no cap 01:08:30–01:19:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |




### 020 on2


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 03:59:35–04:10:30                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| postcheckout | no cap 03:59:35–04:00:40; 44 at 04:00:45; 53.9 at 04:00:48; no cap 04:00:50–04:00:55; 68 at 04:01:00; 76 at 04:01:05; no cap at 04:01:06; 51.1 at 04:01:10; 10 04:01:14–04:01:15; 25 at 04:01:20; 61.4 at 04:01:25; 70.4 at 04:01:30; 16.1 at 04:01:35; 19 at 04:01:40; 41.5 at 04:01:45; 66.3784 at 04:01:46; 79.3 at 04:01:50; 18.1 at 04:01:55; 18.7588 at 04:01:59; 18.8 at 04:02:00; 50.4 at 04:02:05; 75.4772 at 04:02:07; 83.4 at 04:02:10; 26.2 at 04:02:15; 10 at 04:02:16; 13.9 at 04:02:20; 36.4 at 04:02:25; 72.8343 at 04:02:29; 72.8 at 04:02:30; 32 at 04:02:35; 14.1 at 04:02:40; 38.7 at 04:02:45; 73.3 at 04:02:50; 84.1 at 04:02:55; 21.6604 at 04:02:59; 21.7 at 04:03:00; 13.8 at 04:03:05; 30.6622 at 04:03:08; 39.8 at 04:03:10; 74.4 at 04:03:15; 61.2875 at 04:03:17; 86.1 at 04:03:20; 36.3 at 04:03:25; 10 at 04:03:30; 33.6 at 04:03:35; 67.6 at 04:03:40; 67.7328 at 04:03:43; 64 at 04:03:45; 82 at 04:03:50; 17.3 at 04:03:55; 14.1 at 04:04:00; 40.7 at 04:04:05; 74.6 at 04:04:10; 68.9 at 04:04:15; 12.5 at 04:04:20; 10 at 04:04:22; 18.5 at 04:04:25; 41.3 at 04:04:30; 79.7 at 04:04:35; 22.9 at 04:04:40; 13.9 at 04:04:45; 45.1 at 04:04:50; 93.4 at 04:04:55; 45.6168 at 04:04:57; 17.1 at 04:05:00; 10.6408 at 04:05:01; 14.1 at 04:05:05; 41.3 at 04:05:10; 67.5 at 04:05:15; 18.6 at 04:05:20; 19 at 04:05:25; 49.2 at 04:05:30; 80 at 04:05:35; 27.5 at 04:05:40; 10.3871 at 04:05:41; 10.1 at 04:05:45; 32.2 at 04:05:50; 79.8694 at 04:05:54; 79.9 at 04:05:55; 93 at 04:06:00; 33.4 at 04:06:05; 10 04:06:08–04:06:10; 34.7 at 04:06:15; 62.7 at 04:06:20; 90.3 at 04:06:25; 55.4962 at 04:06:27; 21.2 at 04:06:30; 10 at 04:06:35; 32 at 04:06:40; 79.4 at 04:06:45; 56.4734 at 04:06:48; 47.7 at 04:06:50; 76.2 at 04:06:55; 41.5517 at 04:06:57; 16 at 04:07:00; 17.8 at 04:07:05; 24.0126 at 04:07:06; 37.8 at 04:07:10; 58.4154 at 04:07:11; 75 at 04:07:15; 81.6 at 04:07:20; 28.3589 at 04:07:24; 28.4 at 04:07:25; 14.1 at 04:07:30; 34.5948 at 04:07:33; 42.6 at 04:07:35; 66.8891 at 04:07:37; 73 at 04:07:40; 72.8137 at 04:07:41; 83.6 at 04:07:45; 18.8 at 04:07:50; 14.1 at 04:07:55; 41.3 at 04:08:00; 75.1 at 04:08:05; 79.7 at 04:08:10; 65.763 at 04:08:11; 24.9 at 04:08:15; 10 at 04:08:20; 30.6 at 04:08:25; 67.9088 at 04:08:29; 67.9 at 04:08:30; 84.9 at 04:08:35; 18 at 04:08:40; 10 at 04:08:42; 19.2 at 04:08:45; 43.1 at 04:08:50; 68 at 04:08:55; 20.1 at 04:09:00; 14.1064 at 04:09:04; 14.1 at 04:09:05; 43.7 at 04:09:10; 71.0826 at 04:09:13; 78.8 at 04:09:15; 79.7992 at 04:09:17; 38.9 at 04:09:20; 10 at 04:09:25; 26.3 at 04:09:30; 73.0409 at 04:09:34; 73 at 04:09:35; 43.4 at 04:09:40; 10.3867 at 04:09:43; 10 at 04:09:45; 31.2 at 04:09:50; 60.7 at 04:09:55; 63.4 at 04:10:00; 10.7 at 04:10:05; 14.1549 at 04:10:07; 24.9 at 04:10:10; 52.7 at 04:10:15; 78.5614 at 04:10:16; 78.2 at 04:10:20; 18.2 at 04:10:25; 13.9 at 04:10:30 |
| getcart      | no cap 03:59:35–04:10:30                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| postcart     | no cap 03:59:35–04:10:30                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| emptycart    | no cap 03:59:35–04:10:30                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |




### 020 on3


| API          | Live caps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| getproduct   | no cap 04:25:25–04:36:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| postcheckout | no cap 04:25:25–04:26:40; 55 at 04:26:45; 71.5 at 04:26:50; 78.1 at 04:26:55; 80.1425 at 04:26:58; 81.5 at 04:27:00; 43.0478 at 04:27:02; 16.2 at 04:27:05; 14.1 at 04:27:10; 26.5923 at 04:27:11; 48.1 at 04:27:15; 87 at 04:27:20; 90 at 04:27:23; no cap at 04:27:25; 19.5814 at 04:27:29; 19.6 at 04:27:30; 14.1 at 04:27:35; 34.6807 at 04:27:38; 45.5 at 04:27:40; 78.723 at 04:27:43; 86.5 at 04:27:45; 46.8 at 04:27:50; 17.6585 at 04:27:52; 10 at 04:27:55; 19.5 at 04:28:00; 58.7 at 04:28:05; 88 at 04:28:10; 25 at 04:28:15; 14.2 at 04:28:20; 45.6 at 04:28:25; 76.5 at 04:28:30; 53.1776 at 04:28:33; 33.7 at 04:28:35; 14.2 at 04:28:40; 26.851 at 04:28:42; 50.1 at 04:28:45; 92.2 at 04:28:50; 71 at 04:28:55; 10.7 at 04:29:00; 26.9902 at 04:29:04; 27 at 04:29:05; 68 at 04:29:10; 64.4 at 04:29:15; 10 at 04:29:20; 14.1431 at 04:29:22; 27.2 at 04:29:25; 59.4 at 04:29:30; 83.2 at 04:29:35; 46 at 04:29:40; 10 at 04:29:45; 34.3 at 04:29:50; 83.1 at 04:29:55; 83.5579 at 04:29:56; 54.1 at 04:30:00; 10 at 04:30:05; 33.845 at 04:30:09; 33.8 at 04:30:10; 77.7 at 04:30:15; 92.1 at 04:30:20; 41.2 at 04:30:25; 10 04:30:29–04:30:30; 35.5073 at 04:30:34; 35.5 at 04:30:35; 76.4 at 04:30:40; 74.4 at 04:30:45; 74.7 at 04:30:50; 10.9 at 04:30:55; 25.7 at 04:31:00; 32.9549 at 04:31:01; 57.3 at 04:31:05; 85.7 at 04:31:10; 16.2 at 04:31:15; 19.4 at 04:31:20; 59.7 at 04:31:25; 81.4077 at 04:31:27; 89.3 at 04:31:30; 23.2 at 04:31:35; 10 at 04:31:40; 36 at 04:31:45; 86.8 at 04:31:50; 43.9 at 04:31:55; 10 04:31:59–04:32:00; 34.8 at 04:32:05; 73.1293 at 04:32:08; 86 at 04:32:10; no cap at 04:32:15; 22.3 at 04:32:20; 14.1326 at 04:32:23; 19.3 at 04:32:25; 61.6 at 04:32:30; 79.7 at 04:32:35; 19.4 at 04:32:40; 11.9502 at 04:32:41; 14.2 at 04:32:45; 48.6 at 04:32:50; 98.8 at 04:32:55; 53.8 at 04:33:00; 10 at 04:33:05; 27.4 at 04:33:10; 77.5 at 04:33:15; 72.5 at 04:33:20; 28.1018 at 04:33:21; 10.7 at 04:33:25; 26.7 at 04:33:30; 62 at 04:33:35; 78.7 at 04:33:40; 23.8 at 04:33:45; 10 at 04:33:47; 14.2 at 04:33:50; 46.5 at 04:33:55; 80.9 at 04:34:00; 87 at 04:34:05; 21.0361 at 04:34:08; 13 at 04:34:10; 14.1479 at 04:34:12; 26.8 at 04:34:15; 34.9673 at 04:34:16; 61.1 at 04:34:20; 76.5 at 04:34:25; 76 at 04:34:30; 73.3 at 04:34:35; 76.2 at 04:34:40; 65.2127 at 04:34:42; 57.2 at 04:34:45; 77.7 at 04:34:50; 89.9133 at 04:34:54; 89.9 at 04:34:55; 66 at 04:35:00; 10 at 04:35:05; 25.9 at 04:35:10; 65.7 at 04:35:15; 90.4 at 04:35:20; 19.8 at 04:35:25; 14.2 at 04:35:30; 26.9344 at 04:35:32; 50.2 at 04:35:35; 78.6 at 04:35:40; 81.8 at 04:35:45; 40.3 at 04:35:50; 10 at 04:35:55; 33.108 at 04:35:59; 33.1 at 04:36:00; 80.7 at 04:36:05; 45.9 at 04:36:10; 17.5689 at 04:36:12; 10 04:36:15–04:36:16; 19.6 at 04:36:20; 48.7 at 04:36:25 |
| getcart      | no cap 04:25:25–04:36:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| postcart     | no cap 04:25:25–04:36:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| emptycart    | no cap 04:25:25–04:36:25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |




## Per arm, or per hold

Across the three bars, a shed edge comes back on two holds, both RetryGuard-only, both `frontend → checkoutservice`, both at rejection 0.00: 010 off1 and 020 off1. Each is off for 35 s and then climbs 1→2→3. Every recommendations shed stays at 0 until SHUTDOWN (379–533 s). The 0.15 checkout shed (015 off2) also stays at 0 for 532 s; its quiet run never reaches 30 s under 0.10, 0.15, or 0.20. Both-on sheds are two recommendations edges (010 on2, 015 on3), both left at 0. The other both-on holds have no transition lines. Checkout file streaks there are 5–7 s, with controller `high` 5–8, while volume rpr on the checkout-retry holds is 0.486–0.693.

Storefront getproduct follows which edge is retrying, and the repeats inside one bar disagree. Recommendations retry delta in the thousands goes with getproduct goodput 172.5–205.8 and P95 670–796. Recommendations retry delta 0 goes with getproduct goodput 232.2–264.3 and P95 285–398. postcart and emptycart do not move. 0.20 RetryGuard-only is the pair that stays in the recommendations-retry regime (goodput 197.1 and 192.0, P95 670 and 683). 0.20 both-on is the trio that stays in the recommendations-cold regime (goodput 264.2, 264.0, 263.8, P95 355, 339, 320). 0.10 and 0.15 each contain both regimes.

010 off1 sheds both edges. Checkout returns at rejection 0.00 and climbs to 3 (retries 3,579). Recommendations stays off (retries 10,732, `grpc_4` 41,210). getproduct goodput 205.8, P95 679. Checkout is detector-hot (88.5%) and email is detector-hot (62.4%).

010 off2 sheds recommendations only and leaves it off (retries 12,777, `grpc_4` 62,524, quiet streak 1 under 0.10). Checkout file streak is 8 s, `high` 9, retries 887. getproduct goodput 172.5, P95 707. Checkout is detector-hot (85.6%). Email is 48.3%.

010 on1 has no shed. Checkout volume rpr is 0.562 and retries are 15,209, with file streak 7 s and `high` 7. Recommendations retries are 0 and `grpc_4` is 0. getproduct goodput 263.9, P95 344, fail rate 0. postcheckout goodput is 32.9. Checkout is detector-hot (55.3%). Checkout gap2 is 2.0%.

010 on2 sheds recommendations and leaves it off (retries 27,627, `grpc_4` 46,082, quiet streak 2 under 0.10, off for 420 s). Checkout retries are 477, streak 5 s. getproduct goodput 197.2, P95 786. Checkout is detector-hot (73.0%). Checkout gap2 is 23.0%, so this column counts slow polls.

015 off1 sheds recommendations and leaves it off (retries 16,013, `grpc_4` 63,491, quiet streak 1 under 0.15). Checkout retries are 21, streak 0 s, `high` 0. getproduct goodput 183.7, P95 686. Checkout is detector-hot (84.7%) and email is detector-hot (64.7%).

015 off2 sheds checkout and leaves it off for 532 s (retries 3,644, quiet streak 14 under 0.15). Recommendations retries are 0 and `grpc_4` is 0. getproduct goodput 264.3, P95 398. postcheckout goodput is 63.8, the highest in the sweep, with fail rate 0.251. Checkout is detector-hot (89.0%) and email is detector-hot (80.9%). This repeat disagrees with 015 off1 on which edge sheds and on getproduct goodput and P95.

015 on1 has no shed. Checkout volume rpr is 0.693 and retries are 18,077, streak 7 s, `high` 8. Recommendations retries are 0. getproduct goodput 232.2, P95 285, fail rate 0.117. postcheckout goodput is 29.1. Checkout is detector-hot (54.9%). Checkout gap2 is 0.8%.

015 on2 has no shed. Checkout volume rpr is 0.640 and retries are 16,860, streak 7 s, `high` 6. Recommendations retries are 0. getproduct goodput 264.1, P95 317, fail rate 0. Checkout is detector-hot (53.3%). Checkout gap2 is 32.1%.

015 on3 sheds recommendations and leaves it off (retries 30,600, `grpc_4` 51,113, quiet streak 2 under 0.15, off for 379 s). Checkout retries are 520, streak 6 s. getproduct goodput 199.0, P95 796. Checkout is detector-hot (71.0%). Checkout gap2 is 27.2%. This repeat disagrees with 015 on1 and 015 on2: those two keep recommendations retries at 0 and getproduct P95 under 320 ms.

020 off1 matches 010 off1's toggle shape at the 0.20 bar. Checkout returns at rejection 0.00 and climbs to 3 (retries 3,586). Recommendations stays off (retries 13,378, `grpc_4` 55,667, quiet streak 3 under 0.20). getproduct goodput 197.1, P95 670. Checkout is detector-hot (86.3%) and email is detector-hot (55.4%).

020 off2 sheds recommendations and leaves it off (retries 13,007, `grpc_4` 56,068, quiet streak 3 under 0.20). Checkout retries are 35, streak 0 s, `high` 0. getproduct goodput 192.0, P95 683. Checkout is detector-hot (86.5%). Email is 43.4%. The two 0.20 RetryGuard-only repeats agree on the recommendations-retry storefront and disagree on checkout: only off1 sheds it, and that shed comes back.

020 on1 has no shed. Checkout volume rpr is 0.486 and retries are 13,500, streak 7 s, `high` 8. Recommendations retries are 0. adservice `grpc_4` is 18. getproduct goodput 264.2, P95 355, fail rate 0. postcheckout goodput is 35.0. Checkout is detector-hot (58.9%). Checkout gap2 is 6.1%.

020 on2 has no shed. Checkout volume rpr is 0.594 and retries are 15,188, streak 7 s, `high` 7. Recommendations retries are 0. getproduct goodput 264.0, P95 339, fail rate 0. Checkout is detector-hot (53.6%). Checkout gap2 is 47.8%, the widest sampling gap in the scored set.

020 on3 has no shed. Checkout volume rpr is 0.582 and retries are 16,010, streak 7 s, `high` 7. Recommendations retries are 2 and `grpc_4` is 2. getproduct goodput 263.8, P95 320, fail rate 0. Checkout is detector-hot (57.6%). Checkout gap2 is 29.2%. The three 0.20 both-on repeats agree: no shed, recommendations retries at 0 or 2, getproduct goodput 263.8–264.2, P95 320–355.

## Related links

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md) for how (a), (b), and (c) are read
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode section, for the shed bar, the climb bars, and `reenable_rejection`
- [2026-10-09-s2-reenable-rejection-set-a.md](2026-10-09-s2-reenable-rejection-set-a.md), the earlier readout of these same folders
- [2026-10-08-s2-run89-four-arms-abc.md](2026-10-08-s2-run89-four-arms-abc.md), the previous scored guide for this mix

