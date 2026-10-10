# S2 re-enable 0.25 and tighter climb bars

Six 600 s holds of the locked S2 mix, scored with `experiments/analysis_score.py --sep 2`. Columns follow the index. A bold bar separates the three settings. Short labels:

| Label | Folder |
| --- | --- |
| 025 off | `study3_s2_rr025_rgtf0` |
| 025 on | `study3_s2_rr025_rgtf1` |
| 025c off | `study3_s2_rr025_c1025_rgtf0` |
| 025c on | `study3_s2_rr025_c1025_rgtf1` |
| 020c off | `study3_s2_rr020_c1025_rgtf0` |
| 020c on | `study3_s2_rr020_c1025_rgtf1` |

## Setup

Duration 600 s. Mix getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. Paper-C1, `paper_cpu_reconcile: false`. Frontend pinned at 4 (sidecar request 90m, `proxyCPULimit` unset), catalog HPA max 1, every other service at 1 replica. Checkout and recommendations rolled before each hold (`restart_before_hold`, 60 s). Cool-off 360 s before hold 1 and between each pair. Folders are under `experiments/results/campaign_48/S2_sustained_overload/`. Configs are `experiments/configs/study_2026_10_10/`. No `_r2` replay.

| Setting | Arm | Label |
| --- | --- | --- |
| re-enable 0.25, climb 0.17 / 0.33 | RetryGuard on, TopFull off | 025 off |
| re-enable 0.25, climb 0.17 / 0.33 | both on | 025 on |
| re-enable 0.25, climb 0.10 / 0.25 | RetryGuard on, TopFull off | 025c off |
| re-enable 0.25, climb 0.10 / 0.25 | both on | 025c on |
| re-enable 0.20, climb 0.10 / 0.25 | RetryGuard on, TopFull off | 020c off |
| re-enable 0.20, climb 0.10 / 0.25 | both on | 020c on |

## Gate

The run log marks all six PASS: Locust rows 562 / 564 / 565 / 561 / 566 / 562, frontend replica 4 on every `resource_usage.csv` sample (139 or 140 samples), VirtualServices back at attempts 3 with no route timeout, no `PATCH_FAIL` and no traceback. `service_capacity.json` is the same Paper-C1 pin on every hold: frontend 1150m × 4, checkout 800m × 1, recommendations 1150m × 1, productcatalog 800m × 1, email 120m × 1, payment 155m × 1. The scorer prints a replica line only when a service’s count changes or hits 0. It printed none, and the CPU table’s replica mode is 4 for frontend and 1 for every other service.

Scorer gate numbers. Mesh span is about 12 minutes on every hold. Inbound gaps of 1.5 s or longer are 0 on 025 off, 025 on, 025c off, and 020c off. **025c on** has 1067 gaps of 6875 pairs. **020c on** has 528 of 7392. Those two files are still scored; the columns stay filled.

## Edge-mode bars

The scorer’s opening line is the first folder only:

> Shed bar rpr > 0.50. Climb bars rpr ≤ 0.17 at 1 attempt and rpr ≤ 0.33 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Each hold’s START line:

| Label | re-enable | climb 1→2 | climb 2→3 |
| --- | ---: | ---: | ---: |
| 025 off, 025 on | 0.25 | 0.17 | 0.33 |
| 025c off, 025c on | 0.25 | 0.10 | 0.25 |
| 020c off, 020c on | 0.20 | 0.10 | 0.25 |

Every START line is `metric=edge_rpr`, `rpr_threshold=0.50`, `rejection_threshold=0.20`, `sample_interval=1s`, `interval_samples=30s`, `attempts_on=3`. Shed and 0→1 take 30 s of row timestamps. Climbs 1→2 and 2→3 take 15 s (`CLIMB_INTERVAL_SECONDS`). `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

The file streak below is seconds. The parenthetical is the controller’s max `high`, a sample count. **Bold** in (a) is a file streak of at least 30 seconds. Climb streaks are `OBSERVE` sample counts while that attempt cap is in force, scored against that hold’s own climb bars.

## (a) Edge rpr

Only `frontend → recommendationservice`, `frontend → checkoutservice`, and `frontend → cartservice` have a tick above 0.5 or a retry delta. The other 11 controlled edges are at retry delta 0 with no tick above 0.5 on every hold. Cart’s only activity is one tick on 025 off (streak 0 s, retry delta 4).

Longest streak in seconds of rpr > 0.5, then ticks above 0.5, then controller `high`.

| Edge | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | **32 / 33 (31)** | 0 / 0 (0) | **┃** | **32 / 33 (31)** | **32 / 33 (31)** | **┃** | **32 / 33 (31)** | **33 / 66 (30)** |
| frontend → cartservice | 0 / 1 (1) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |
| frontend → checkoutservice | **32 / 98 (31)** | 8 / 177 (9) | **┃** | 25 / 26 (26) | 5 / 6 (6) | **┃** | 13 / 14 (14) | **33 / 160 (30)** |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold’s `Δretry / first attempts`.

| Edge | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | 0.180 / 0.000 / 8.33 / 0.079 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.122 / 0.000 / 3.82 / 0.072 | 0.142 / 0.000 / 3.54 / 0.068 | **┃** | 0.144 / 0.000 / 4.04 / 0.074 | 0.242 / 0.000 / 5.29 / 0.150 |
| frontend → cartservice | 0.001 / 0.000 / 0.80 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |
| frontend → checkoutservice | 0.223 / 0.000 / 4.10 / 0.171 | 0.718 / 0.000 / 6.83 / 0.626 | **┃** | 0.099 / 0.000 / 3.78 / 0.066 | 0.031 / 0.000 / 3.76 / 0.029 | **┃** | 0.052 / 0.000 / 3.36 / 0.042 | 0.386 / 0.000 / 4.35 / 0.333 |

Climb streaks, samples at 1 attempt with rpr at or under that hold’s 1→2 bar, then samples at 2 attempts with rpr at or under that hold’s 2→3 bar. An em dash means that cap never applied.

| Edge | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | 16 / 16 | — / — | **┃** | — / — | — / — | **┃** | — / — | 16 / 12 |
| frontend → cartservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| frontend → checkoutservice | 5 / — | — / — | **┃** | — / — | — / — | **┃** | — / — | 9 / — |

025 off is the only default-climb hold that reached 1 and 2 attempts on recommendations (streaks 16 / 16, both climbs at rpr 0.00). Checkout there reached 1 attempt (streak 5) and did not climb. 020c on did the same pair: recommendations 16 / 12, and the 2→3 step still fired at rpr 0.00; checkout’s 1-attempt streak is 9 and it did not climb. The four middle columns never left the attempt count they had after the shed, or never shed.

## Rejection, beside (a)

The 0.20 streak sits beside the shed bar. Cells are longest streak / count from `(Δ5xx + Δresets) / Δtotal`. A non-positive total delta breaks the streak. **Bold** is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. The controller adds `grpc_4` and `grpc_14` on recommendations, productcatalog, currency, and ads. Those two deltas are the later table. They are absent from both streak tables.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 35 / 40 | 1 / 1 | **┃** | 34 / 370 | 24 / 164 | **┃** | 369 / 552 | 41 / 82 |
| checkoutservice | **37 / 199** | 8 / 171 | **┃** | 26 / 26 | 7 / 7 | **┃** | 14 / 15 | **36 / 194** |
| recommendationservice | 16 / 35 | 0 / 0 | **┃** | 3 / 18 | 3 / 21 | **┃** | 7 / 114 | **40 / 73** |
| paymentservice | 1 / 3 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 2 |
| emailservice | 3 / 161 | 4 / 57 | **┃** | 3 / 11 | 1 / 3 | **┃** | 2 / 7 | 4 / 89 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Longest streak strictly under that hold’s re-enable bar, then the count. The bar is **0.25** on 025 off, 025 on, 025c off, and 025c on. It is **0.20** on 020c off and 020c on. The controller consults it only while an edge into that callee is at 0 attempts.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 460 / 574 | 612 / 612 | **┃** | 66 / 397 | 66 / 415 | **┃** | 54 / 61 | 351 / 483 |
| checkoutservice | 44 / 424 | 45 / 447 | **┃** | 547 / 586 | 423 / 504 | **┃** | 528 / 582 | 34 / 336 |
| recommendationservice | 469 / 601 | 613 / 613 | **┃** | 352 / 609 | 241 / 510 | **┃** | 51 / 496 | 399 / 492 |
| paymentservice | 448 / 590 | 612 / 612 | **┃** | 612 / 612 | 423 / 513 | **┃** | 529 / 597 | 275 / 531 |
| emailservice | 44 / 433 | 45 / 535 | **┃** | 550 / 600 | 285 / 508 | **┃** | 529 / 588 | 62 / 376 |
| productcatalogservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 516 / 516 | **┃** | 613 / 613 | 565 / 565 |
| cartservice | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 516 / 516 | **┃** | 612 / 612 | 565 / 565 |
| currencyservice | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 515 / 515 | **┃** | 612 / 612 | 565 / 565 |
| shippingservice | 472 / 597 | 613 / 613 | **┃** | 613 / 613 | 427 / 514 | **┃** | 529 / 603 | 409 / 545 |
| adservice | 471 / 594 | 612 / 612 | **┃** | 612 / 612 | 514 / 514 | **┃** | 531 / 606 | 408 / 547 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

### gRPC counted in the rejection rate

Cell is `grpc_4 / grpc_14`. Catalog, currency, and ads are 0 / 0 on every hold.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 22,151 / 0 | 0 / 0 | **┃** | 60,559 / 0 | 41,029 / 0 | **┃** | 92,448 / 0 | 43,891 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| checkoutservice | **555/663 (83.7%)** | **385/664 (58.0%)** | **┃** | **559/664 (84.2%)** | 97/663 (14.6%) | **┃** | **468/663 (70.6%)** | **500/664 (75.3%)** |
| recommendationservice | 45/663 (6.8%) | 1/664 (0.2%) | **┃** | 40/664 (6.0%) | 84/663 (12.7%) | **┃** | 321/663 (48.4%) | 87/664 (13.1%) |
| paymentservice | 6/663 (0.9%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| emailservice | **434/663 (65.5%)** | 136/664 (20.5%) | **┃** | **438/664 (66.0%)** | 24/663 (3.6%) | **┃** | 142/663 (21.4%) | 307/664 (46.2%) |
| productcatalogservice | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| cartservice | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| currencyservice | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| shippingservice | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| adservice | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |
| redis-cart | 0/663 (0.0%) | 0/664 (0.0%) | **┃** | 0/664 (0.0%) | 0/663 (0.0%) | **┃** | 0/663 (0.0%) | 0/664 (0.0%) |

## (c) Retry volume

Outbound retry delta by target. Cart is 4 on 025 off and 0 on the other five. Every other target is 0.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 8,131 | 16,512 | **┃** | 2,502 | 540 | **┃** | 1,164 | 14,033 |
| recommendationservice | 20,723 | 0 | **┃** | 18,952 | 15,920 | **┃** | 19,719 | 35,357 |
| cartservice | 4 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

Inbound resets.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 70 | 107 | **┃** | 254 | 241 | **┃** | 227 | 73 |
| checkoutservice | 13,081 | 12,275 | **┃** | 1,868 | 412 | **┃** | 881 | 16,179 |
| recommendationservice | 7,328 | 7 | **┃** | 27,311 | 18,947 | **┃** | 43,950 | 16,993 |
| paymentservice | 779 | 699 | **┃** | 86 | 15 | **┃** | 31 | 1,254 |
| emailservice | 5,399 | 1,017 | **┃** | 130 | 44 | **┃** | 70 | 2,228 |
| productcatalogservice | 3 | 6 | **┃** | 2 | 4 | **┃** | 0 | 5 |
| cartservice | 528 | 676 | **┃** | 138 | 20 | **┃** | 45 | 703 |
| currencyservice | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 1 |
| shippingservice | 695 | 1,049 | **┃** | 152 | 33 | **┃** | 65 | 1,282 |
| adservice | 5 | 0 | **┃** | 1 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

The same `grpc_4 / grpc_14` pair above is what the retry policy counts on recommendations, catalog, currency, and ads.

## RetryGuard toggles

Every hold has a `retryguard.log`. Checkout and recommendations are the callees whose attempt count changed. An em dash means that edge never went to 0, so the re-enable bar was not in force. A cell with more than one cycle lists the cycles in time order, separated by semicolons. Time OFF is seconds from the shed timestamp to the re-enable timestamp, or to the `EXIT` line when the edge stays at 0. OFF rejection is the `state=OFF` `OBSERVE` samples for that callee, minimum / median, shown to two decimals. The under-bar streak is seconds. On a cycle that re-enabled it is the `elapsed_s` on the `OFF→ON` line. On a cycle that stayed at 0 it is the longest run of those samples with rejection strictly under that hold’s bar, from the first sample of the run to the last. A streak of 30 s is the `0→1` step.

### checkoutservice

| | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 3 / 2 | — | **┃** | — | — | **┃** | — | 5 / 4 |
| Shed rpr | 2.92; 0.91; 0.79 | — | **┃** | — | — | **┃** | — | 1.86; 0.85; 0.94; 0.90; 0.83 |
| Attempts after re-enable | 1; 1; — | — | **┃** | — | — | **┃** | — | 1; 1; 1; 1; — |
| Time OFF (s) | 67; 281; 114 | — | **┃** | — | — | **┃** | — | 38; 91; 150; 44; 19 |
| OFF rejection min / median | 0.00 / 0.14; 0.00 / 0.08; 0.02 / 0.14 | — | **┃** | — | — | **┃** | — | 0.00 / 0.00; 0.00 / 0.10; 0.00 / 0.01; 0.00 / 0.01; 0.00 / 0.09 |
| Streak under the bar (s) | 30; 30; 25 | — | **┃** | — | — | **┃** | — | 30; 30; 30; 30; 10 |

025 off re-enabled twice, and the third shed stayed at 0. 020c on re-enabled four times, and the fifth shed stayed at 0. The other four holds never sent checkout to 0.

### recommendationservice

| | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 1 | — | **┃** | 1 / 0 | 1 / 0 | **┃** | 1 / 0 | 2 / 2 |
| Shed rpr | 2.24 | — | **┃** | 2.16 | 3.14 | **┃** | 2.46 | 3.59; 0.99 |
| Attempts after re-enable | 3 | — | **┃** | — | — | **┃** | — | 1; 3 |
| Time OFF (s) | 44 | — | **┃** | 519 | 520 | **┃** | 532 | 42; 43 |
| OFF rejection min / median | 0.00 / 0.00 | — | **┃** | 0.01 / 0.26 | 0.00 / 0.19 | **┃** | 0.00 / 0.45 | 0.00 / 0.00; 0.00 / 0.00 |
| Streak under the bar (s) | 30 | — | **┃** | 5 | 22 | **┃** | 0 | 30; 30 |

025 off re-enabled, and the climb that followed stopped at 3 attempts. 020c on re-enabled twice: the first climb stopped at 1 attempt and the second stopped at 3. 025c off, 025c on, and 020c off each shed once and stayed at 0. 025 on never sent recommendations to 0.

The scorer's timestamp log for each hold follows.

### 025 off

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T16:15:47Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.92 |
| 2026-10-10T16:16:52Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.24 |
| 2026-10-10T16:16:54Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T16:17:36Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T16:17:38Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.91 |
| 2026-10-10T16:17:52Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-10T16:18:08Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-10T16:22:19Z | checkoutservice | OFF→ON | 0 | rejection 0.09 |
| 2026-10-10T16:22:52Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.79 |

### 025 on

No transition lines.

### 025c off

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T17:07:17Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.16 |

### 025c on

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T17:32:55Z | frontend → recommendationservice | ON→OFF | 3 | rpr 3.14 |

### 020c off

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T17:57:29Z | frontend → recommendationservice | ON→OFF | 3 | rpr 2.46 |

### 020c on

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T18:22:51Z | frontend → recommendationservice | ON→OFF | 3 | rpr 3.59 |
| 2026-10-10T18:23:32Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.86 |
| 2026-10-10T18:23:33Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T18:24:10Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T18:24:10Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.99 |
| 2026-10-10T18:24:53Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T18:24:54Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.85 |
| 2026-10-10T18:25:09Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-10T18:25:25Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-10T18:26:25Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-10T18:26:59Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.94 |
| 2026-10-10T18:29:29Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-10T18:30:05Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.90 |
| 2026-10-10T18:30:49Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-10T18:31:23Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.83 |

## Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 247.1 | 264.1 | **┃** | 181.7 | 202.6 | **┃** | 136.0 | 190.8 |
| postcheckout | 50.0 | 30.6 | **┃** | 58.9 | 29.3 | **┃** | 44.2 | 40.1 |
| getcart | 90.0 | 96.0 | **┃** | 70.3 | 75.7 | **┃** | 54.0 | 82.7 |
| postcart | 85.9 | 86.4 | **┃** | 86.2 | 86.3 | **┃** | 86.1 | 85.8 |
| emptycart | 4.7 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.7 | 4.7 |

## Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.060 | 0.000 | **┃** | 0.295 | 0.218 | **┃** | 0.463 | 0.264 |
| postcheckout | 0.400 | 0.587 | **┃** | 0.302 | 0.631 | **┃** | 0.469 | 0.516 |
| getcart | 0.058 | 0.000 | **┃** | 0.252 | 0.196 | **┃** | 0.417 | 0.132 |
| postcart | 0.007 | 0.000 | **┃** | 0.002 | 0.000 | **┃** | 0.004 | 0.005 |
| emptycart | 0.024 | 0.000 | **┃** | 0.008 | 0.000 | **┃** | 0.028 | 0.024 |

## Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 423 | 319 | **┃** | 682 | 674 | **┃** | 683 | 384 |
| postcheckout | 923 | 960 | **┃** | 972 | 723 | **┃** | 860 | 938 |
| getcart | 400 | 327 | **┃** | 662 | 645 | **┃** | 661 | 356 |
| postcart | 76 | 75 | **┃** | 72 | 77 | **┃** | 72 | 71 |
| emptycart | 25 | 14 | **┃** | 17 | 24 | **┃** | 22 | 19 |

## Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s. Redis-cart is 0.0 on every hold.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 442.4 | 419.3 | **┃** | 444.9 | 403.4 | **┃** | 446.4 | 403.6 |
| checkoutservice | 77.3 | 59.5 | **┃** | 55.7 | 26.1 | **┃** | 40.1 | 78.1 |
| recommendationservice | 394.2 | 341.8 | **┃** | 393.9 | 348.1 | **┃** | 396.5 | 375.7 |
| paymentservice | 75.2 | 56.9 | **┃** | 55.4 | 26.0 | **┃** | 40.0 | 72.4 |
| emailservice | 55.6 | 30.8 | **┃** | 51.2 | 25.2 | **┃** | 38.1 | 40.3 |
| productcatalogservice | 2424.6 | 2348.0 | **┃** | 1995.1 | 1928.6 | **┃** | 1645.9 | 2031.4 |
| cartservice | 510.7 | 477.9 | **┃** | 482.7 | 424.1 | **┃** | 454.1 | 460.3 |
| currencyservice | 711.7 | 697.5 | **┃** | 682.5 | 627.4 | **┃** | 640.8 | 625.6 |
| shippingservice | 220.7 | 187.3 | **┃** | 169.6 | 116.5 | **┃** | 125.6 | 204.7 |
| adservice | 210.5 | 223.8 | **┃** | 155.5 | 172.9 | **┃** | 116.3 | 162.0 |

## Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. Redis-cart has no sojourn.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 283 | 195 | **┃** | 501 | 453 | **┃** | 489 | 284 |
| checkoutservice | 403 | 314 | **┃** | 210 | 91 | **┃** | 137 | 403 |
| recommendationservice | 125 | 67 | **┃** | 456 | 422 | **┃** | 469 | 121 |
| paymentservice | 6 | 5 | **┃** | 4 | 2 | **┃** | 3 | 6 |
| emailservice | 78 | 37 | **┃** | 36 | 12 | **┃** | 18 | 61 |
| productcatalogservice | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 2 |
| cartservice | 4 | 4 | **┃** | 3 | 4 | **┃** | 3 | 4 |
| currencyservice | 3 | 4 | **┃** | 3 | 3 | **┃** | 3 | 3 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |

## Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. Payment, email, catalog, cart, currency, shipping, and ads are 0.000 on every hold. Redis-cart has no share.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.163 | 0.039 | **┃** | 0.774 | 0.672 | **┃** | 0.791 | 0.188 |
| checkoutservice | 0.287 | 0.358 | **┃** | 0.043 | 0.017 | **┃** | 0.028 | 0.389 |
| recommendationservice | 0.083 | 0.000 | **┃** | 0.381 | 0.247 | **┃** | 0.570 | 0.178 |

## CPU

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum `cpu_millicores` across replicas, so frontend sits above its 1150m per-pod quota.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1302 / 1601 | 1150 / 4 / 1296 / 1599 | **┃** | 1150 / 4 / 1281 / 1561 | 1150 / 4 / 1319 / 1639 | **┃** | 1150 / 4 / 1283 / 1560 | 1150 / 4 / 1249 / 1580 |
| checkoutservice | 800 / 1 / 643 / 798 | 800 / 1 / 545 / 797 | **┃** | 800 / 1 / 649 / 797 | 800 / 1 / 459 / 797 | **┃** | 800 / 1 / 581 / 795 | 800 / 1 / 591 / 799 |
| recommendationservice | 1150 / 1 / 735 / 1148 | 1150 / 1 / 675 / 867 | **┃** | 1150 / 1 / 736 / 1120 | 1150 / 1 / 739 / 1143 | **┃** | 1150 / 1 / 788 / 1151 | 1150 / 1 / 700 / 1146 |
| paymentservice | 155 / 1 / 58 / 115 | 155 / 1 / 44 / 78 | **┃** | 155 / 1 / 47 / 84 | 155 / 1 / 31 / 66 | **┃** | 155 / 1 / 41 / 79 | 155 / 1 / 52 / 82 |
| emailservice | 120 / 1 / 79 / 120 | 120 / 1 / 54 / 110 | **┃** | 120 / 1 / 85 / 112 | 120 / 1 / 55 / 100 | **┃** | 120 / 1 / 73 / 103 | 120 / 1 / 61 / 119 |
| productcatalogservice | 800 / 1 / 421 / 516 | 800 / 1 / 445 / 540 | **┃** | 800 / 1 / 389 / 484 | 800 / 1 / 397 / 500 | **┃** | 800 / 1 / 379 / 478 | 800 / 1 / 416 / 522 |
| cartservice | 800 / 1 / 318 / 462 | 800 / 1 / 298 / 371 | **┃** | 800 / 1 / 334 / 432 | 800 / 1 / 344 / 438 | **┃** | 800 / 1 / 366 / 500 | 800 / 1 / 319 / 466 |
| currencyservice | 770 / 1 / 356 / 450 | 770 / 1 / 341 / 422 | **┃** | 770 / 1 / 361 / 456 | 770 / 1 / 369 / 470 | **┃** | 770 / 1 / 369 / 463 | 770 / 1 / 338 / 465 |
| shippingservice | 770 / 1 / 96 / 126 | 770 / 1 / 80 / 109 | **┃** | 770 / 1 / 90 / 114 | 770 / 1 / 79 / 112 | **┃** | 770 / 1 / 77 / 105 | 770 / 1 / 88 / 130 |
| adservice | 1150 / 1 / 165 / 501 | 1150 / 1 / 146 / 183 | **┃** | 1150 / 1 / 119 / 166 | 1150 / 1 / 140 / 185 | **┃** | 1150 / 1 / 105 / 165 | 1150 / 1 / 119 / 183 |
| redis-cart | 540 / 1 / 37 / 54 | 540 / 1 / 37 / 51 | **┃** | 540 / 1 / 40 / 56 | 540 / 1 / 41 / 59 | **┃** | 540 / 1 / 43 / 60 | 540 / 1 / 39 / 57 |

CPU as a fraction of per-pod quota × replicas. Mean / max. A sample with replica count 0 is left out. None occurred.

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.28 / 0.35 | 0.28 / 0.35 | **┃** | 0.28 / 0.34 | 0.29 / 0.36 | **┃** | 0.28 / 0.34 | 0.27 / 0.34 |
| checkoutservice | 0.80 / 1.00 | 0.68 / 1.00 | **┃** | 0.81 / 1.00 | 0.57 / 1.00 | **┃** | 0.73 / 0.99 | 0.74 / 1.00 |
| recommendationservice | 0.64 / 1.00 | 0.59 / 0.75 | **┃** | 0.64 / 0.97 | 0.64 / 0.99 | **┃** | 0.68 / 1.00 | 0.61 / 1.00 |
| paymentservice | 0.38 / 0.74 | 0.28 / 0.50 | **┃** | 0.31 / 0.54 | 0.20 / 0.43 | **┃** | 0.26 / 0.51 | 0.33 / 0.53 |
| emailservice | 0.66 / 1.00 | 0.45 / 0.92 | **┃** | 0.71 / 0.93 | 0.46 / 0.83 | **┃** | 0.61 / 0.86 | 0.51 / 0.99 |
| productcatalogservice | 0.53 / 0.65 | 0.56 / 0.68 | **┃** | 0.49 / 0.60 | 0.50 / 0.62 | **┃** | 0.47 / 0.60 | 0.52 / 0.65 |
| cartservice | 0.40 / 0.58 | 0.37 / 0.46 | **┃** | 0.42 / 0.54 | 0.43 / 0.55 | **┃** | 0.46 / 0.62 | 0.40 / 0.58 |
| currencyservice | 0.46 / 0.58 | 0.44 / 0.55 | **┃** | 0.47 / 0.59 | 0.48 / 0.61 | **┃** | 0.48 / 0.60 | 0.44 / 0.60 |
| shippingservice | 0.12 / 0.16 | 0.10 / 0.14 | **┃** | 0.12 / 0.15 | 0.10 / 0.15 | **┃** | 0.10 / 0.14 | 0.11 / 0.17 |
| adservice | 0.14 / 0.44 | 0.13 / 0.16 | **┃** | 0.10 / 0.14 | 0.12 / 0.16 | **┃** | 0.09 / 0.14 | 0.10 / 0.16 |
| redis-cart | 0.07 / 0.10 | 0.07 / 0.09 | **┃** | 0.07 / 0.10 | 0.08 / 0.11 | **┃** | 0.08 / 0.11 | 0.07 / 0.11 |

## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | 025 off | 025 on | **┃** | 025c off | 025c on | **┃** | 020c off | 020c on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.361 | 0.376 | **┃** | 0.355 | 0.366 | **┃** | 0.352 | 0.363 |
| checkoutservice | 1.040 | 1.042 | **┃** | 1.042 | 1.019 | **┃** | 1.040 | 1.042 |
| recommendationservice | 1.008 | 0.805 | **┃** | 0.998 | 1.007 | **┃** | 1.010 | 1.011 |
| paymentservice | 0.852 | 0.774 | **┃** | 0.710 | 0.600 | **┃** | 0.652 | 0.723 |
| emailservice | 1.067 | 1.042 | **┃** | 1.025 | 0.975 | **┃** | 1.033 | 1.050 |
| productcatalogservice | 0.681 | 0.740 | **┃** | 0.665 | 0.709 | **┃** | 0.618 | 0.708 |
| cartservice | 0.598 | 0.519 | **┃** | 0.586 | 0.596 | **┃** | 0.686 | 0.619 |
| currencyservice | 0.642 | 0.638 | **┃** | 0.671 | 0.677 | **┃** | 0.660 | 0.675 |
| shippingservice | 0.199 | 0.175 | **┃** | 0.184 | 0.175 | **┃** | 0.175 | 0.195 |
| adservice | 0.722 | 0.178 | **┃** | 0.155 | 0.305 | **┃** | 0.159 | 0.185 |
| redis-cart | 0.244 | 0.239 | **┃** | 0.261 | 0.230 | **┃** | 0.267 | 0.220 |

## TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out.

On the three TopFull-off holds (025 off, 025c off, 020c off) every live read on all five APIs is no cap for the whole window.

**025 on.** getproduct, getcart, postcart, and emptycart are no cap for the whole window (16:39:45–16:50:45). postcheckout is no cap until 16:40:50, then a live 38 at 16:40:55, and the scorer’s remaining spans keep moving through 16:50:45. That series is too long to reprint as an arrow.

**025c on.** postcart and emptycart are no cap for the whole window (17:30:35–17:41:30). getproduct, getcart, and postcheckout leave no cap. postcheckout’s first real cap is 37 at 17:31:43. Those three series are too long to reprint.

**020c on.** postcart and emptycart are no cap for the whole window (18:20:40–18:31:40). The other three:

| API | Live caps |
| --- | --- |
| getproduct | no cap 18:20:40–18:22:15; 262 at 18:22:17; 264.4 at 18:22:20; 264.435 at 18:22:21; 166.757 18:22:22–18:31:39; 226.6 at 18:31:40; 166.757 at 18:31:41 |
| postcheckout | no cap 18:20:40–18:21:45; 39.6 at 18:21:50; 47.3 at 18:21:55; 54.9 at 18:22:00; 33.2 at 18:22:05; 10 at 18:22:10; 18.2486 at 18:22:12; 23.3 at 18:22:15; 29.3 at 18:22:20; 88 at 18:31:40 |
| getcart | no cap 18:20:40–18:22:15; 97 at 18:22:17; 99.4 at 18:22:20; 61.4746 18:22:23–18:31:39; 99.4 at 18:31:40; 61.4746 at 18:31:41 |

## Per hold

**025 off.** Checkout shed three times (from 3 at rpr 2.92, then twice from 1 at rpr 0.91 and 0.79). The first two OFF windows were 67 s and 281 s and both re-enabled to 1 attempt (streak 30 s, rejection 0.00 then 0.09). The third window ran 114 s to exit with an under-bar streak of 25 s, so it stayed at 0. Recommendations shed once from 3 at rpr 2.24, was off for 44 s, returned at rejection 0.00, and climbed 1→2→3 at rpr 0.00 (streaks 16 / 16). Retry delta is 20,723 into recommendations and 8,131 into checkout. recommendations `grpc_4` is 22,151. Checkout (83.7%) and email (65.5%) are detector-hot.

**025 on.** No shed and no climb. Checkout’s file streak is 8 s and `high` is 9, with volume rpr 0.626 and retry delta 16,512. Recommendations retry delta is 0, `grpc_4` is 0, and sojourn is 67 ms. Checkout is detector-hot at 58.0%. Email is 20.5%. postcheckout is the only API with a live cap.

**025c off.** Recommendations shed once from 3 at rpr 2.16 and stayed at 0 for 519 s. The longest OFF-window streak under 0.25 was 5 s (OFF rejection median 0.26). Checkout’s file streak is 25 s (`high` 26), under the 30 s shed. Retry delta is 18,952 into recommendations and 2,502 into checkout. recommendations `grpc_4` is 60,559. Checkout (84.2%) and email (66.0%) are detector-hot. Recommendations sojourn is 456 ms.

**025c on.** Recommendations shed once from 3 at rpr 3.14 and stayed at 0 for 520 s. The longest OFF-window streak under 0.25 was 22 s (OFF rejection median 0.19). Checkout’s file streak is 5 s (`high` 6). Retry delta is 15,920 into recommendations and 540 into checkout. recommendations `grpc_4` is 41,029. No service has an overloaded share of 0.5 (checkout 14.6%, recommendations 12.7%, email 3.6%). Inbound gaps of 1.5 s or longer are 1067 of 6875 pairs. getproduct, getcart, and postcheckout have live caps.

**020c off.** Recommendations shed once from 3 at rpr 2.46 and stayed at 0 for 532 s. The longest OFF-window streak under 0.20 was 0 s, one sample (OFF rejection median 0.45). Checkout’s file streak is 13 s (`high` 14). Retry delta is 19,719 into recommendations and 1,164 into checkout. recommendations `grpc_4` is 92,448, the largest of the six. Checkout is detector-hot at 70.6%. Recommendations is 48.4%, and its sojourn is 469 ms, with 0.570 of inbound requests above 500 ms. getproduct goodput is 136.0 and its fail rate is 0.463.

**020c on.** Recommendations shed from 3 at rpr 3.59 and from 1 at rpr 0.99. Both OFF windows re-enabled at 30 s (42 s and 43 s off, rejection 0.00). The first climb stopped at 1 attempt; the second climbed 1→2→3 at rpr 0.00 (streaks 16 / 12). Checkout shed five times (once from 3 at rpr 1.86, then four times from 1 at rpr 0.85, 0.94, 0.90, and 0.83). The first four OFF windows re-enabled to 1 attempt (streak 30 s) and the fifth ran 19 s to exit with an under-bar streak of 10 s. Retry delta is 35,357 into recommendations and 14,033 into checkout. recommendations `grpc_4` is 43,891. Checkout is detector-hot at 75.3%. Email is 46.2%. Inbound gaps of 1.5 s or longer are 528 of 7392 pairs.

## Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md) edge-mode section
- Same mix, re-enable 0.10 / 0.15 / 0.20 at the default climb: [2026-10-10-set-a-reenable-rejection-analysis.md](2026-10-10-set-a-reenable-rejection-analysis.md)
- Plan and run log: [2026-10-10-s2-rr025-climb-holds.md](../docs/superpowers/plans/2026-10-10-s2-rr025-climb-holds.md), [2026-10-10-s2-rr025-climb-run-log.md](../docs/superpowers/plans/2026-10-10-s2-rr025-climb-run-log.md)
