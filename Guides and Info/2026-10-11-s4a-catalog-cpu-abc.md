# S4A catalog CPU holds (2026-10-11): 50 m, then 400 / 300 / 200 / 100 m

Analysis of six holds, scored with `experiments/analysis_score.py`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). The 50 m hold uses a lighter browse mix. The other five share one mix and step the catalog CPU limit.

**Gate status: flagged, not clean.** Every hold has inbound gaps of 1.5 s or longer, and the 50 m hold has catalog at replica count 0 on some samples. See §3.

## 1. Setup

- **Duration** 600 s. `spawn_rate` 50.
- **Mix.** 50 m is **10 / 10 / 10 / 600 / 5** (getproduct / postcheckout / getcart / postcart / emptycart). The other five are **50 / 20 / 50 / 600 / 5**.
- **Bottleneck:** `productcatalogservice` at the per-pod quota in the index. One replica. Frontend pinned at 4, sidecar `proxyCPU=90m`, `proxyCPULimit` unset.
- **Rest of the cluster, Paper-C1:** checkout 800 m, recommendation 1150 m, payment 155 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, email 120 m, redis 540 m, all at 1 replica. Frontend app container 1150 m.
- **Controllers.** RetryGuard on in all six (`reenable_rejection 0.25`, `interval_samples 20`, climb `0.16 / 0.32` at `climb_interval_seconds 10`). TopFull off on every hold except 400 on.
- **Cool-off** 120 s between holds (AGENTS §6).
- **Folders:** `experiments/results/campaign_48/S4A_topology_position_A/`. Configs `experiments/configs/study_2026_10_11/15` through `20`.

## 2. Index

Short column labels used in every table. The first bar separates the lighter mix. The second bar separates the 400 m pair from the staircase.

| Column | Folder | Catalog quota | Arm |
| --- | --- | ---: | --- |
| 50 m | `study4_s4a_pc50_u600_rgtf0` | 50 m | TopFull off |
| 400 off | `study4_s4a_pc400_u600_rgtf0` | 400 m | TopFull off |
| 400 on | `study4_s4a_pc400_u600_rgtf1` | 400 m | TopFull on |
| 300 m | `study4_s4a_pc300_u600_rgtf0` | 300 m | TopFull off |
| 200 m | `study4_s4a_pc200_u600_rgtf0` | 200 m | TopFull off |
| 100 m | `study4_s4a_pc100_u600_rgtf0` | 100 m | TopFull off |

## 3. Gate

Scorer gate numbers. The template counts a zero replica count and inbound gaps of 1.5 s or longer as gate items.

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | Catalog replicas | `retryguard.log` |
| --- | ---: | ---: | ---: | --- | --- |
| 50 m | 557 | 669 | **33 of 7326** | **replicas 0–1 on 82 samples** | present |
| 400 off | 545 | 664 | **33 of 7271** | — | present |
| 400 on | 546 | 664 | **11 of 7293** | — | present |
| 300 m | 547 | 664 | **154 of 7150** | — | present |
| 200 m | 546 | 666 | **88 of 7238** | — | present |
| 100 m | 557 | 663 | **154 of 7139** | — | present |

Bold marks a flagged item. Two problems:

1. **Inbound gaps.** Every hold has them. 300 m and 100 m have 154 each. Those two should be read with that caveat.
2. **Catalog replicas on 50 m.** The scorer reports replica count 0–1 on 82 samples. The two zeros are 08:57:05Z and 08:57:10Z. Frontend is 4 on every sample of every hold, and catalog is 1 on every resource row the collector wrote for 400 off, 400 on, 300 m, and 200 m.

On 100 m the collector wrote catalog on 76 timestamps, all at replica 1, and omitted it on 73 of 149 frontend timestamps (11:04:45Z–11:05:35Z, 11:06:35Z–11:09:15Z, 11:09:45Z–11:12:05Z). The scorer did not flag a zero replica there, because a missing kubelet row is not a `replica_count` of 0.

## 4. Edge-mode bars

Scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Shed and 0→1 re-enable run on a **20 s** streak (`interval_samples` 20). Climbs 1→2 and 2→3 run on **10 s** (`climb_interval_seconds` override, not the 15 s default).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge.

## 5. (a) Edge rpr

Five edges carry a tick above the shed bar or a retry delta. Every other controlled edge is at zero.

**File streak, seconds / ticks above the shed bar (controller `high` in parentheses)**

| Edge | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 22 / 92 (21) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | 22 / 34 (21) |
| recommendationservice → productcatalogservice | 22 / 97 (21) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | 0 / 5 (1) |
| frontend → recommendationservice | 23 / 137 (21) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 10 / 52 (11) | 22 / 65 (21) |
| frontend → cartservice | 0 / 1 (1) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |
| frontend → checkoutservice | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) |

No cell reaches 30 s, so nothing is bold. The sheds are the 22 s and 23 s streaks, which clear the 20 s interval, with controller `high` 21. On 200 m the recommendations edge reaches the shed bar for 10 s and `high` 11, short of 20 s, so it does not shed.

**Mean / median / max / volume rpr**

| Edge | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 0.419 / 0.000 / 7.22 / 0.333 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.206 / 0.000 / 3.00 / 0.132 |
| recommendationservice → productcatalogservice | 1.160 / 0.189 / 19.00 / 0.415 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.052 / 0.000 / 4.21 / 0.046 |
| frontend → recommendationservice | 1.046 / 0.000 / 40.00 / 0.358 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.131 / 0.000 / 3.85 / 0.087 | 0.263 / 0.000 / 4.64 / 0.174 |
| frontend → cartservice | 0.001 / 0.000 / 0.86 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.05 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.001 / 0.000 / 0.33 / 0.001 | 0.000 / 0.000 / 0.00 / 0.000 |

The only positive median is recommendations → catalog on 50 m (0.189).

**Climb streaks, 1-attempt / 2-attempt.** An em dash means that cap never applied.

| Edge | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend → productcatalogservice | 2 / — | **┃** | — / — | — / — | **┃** | — / — | — / — | 10 / 11 |
| recommendationservice → productcatalogservice | 1 / — | **┃** | — / — | — / — | **┃** | — / — | — / — | — / — |
| frontend → recommendationservice | 11 / 11 | **┃** | — / — | — / — | **┃** | — / — | — / — | 11 / 11 |
| frontend → cartservice | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | — / — |
| frontend → checkoutservice | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | — / — |

Recommendations climbed 1→2→3 on 50 m and on 100 m. Catalog climbed 1→2→3 only on 100 m. On 50 m the catalog edges came back to 1 attempt and shed again before a 10 s climb.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count above 0.20, then longest streak / count strictly under 0.25. No controlled service reaches a streak of 30 above 0.20, so nothing in that table is bold. Frontend and redis-cart stay plain.

**Above 0.20**

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend (not controlled) | 188 / 543 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 164 / 393 |
| checkoutservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | 0 / 0 |
| recommendationservice | 1 / 19 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 5 / 28 | 7 / 66 |
| paymentservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| emailservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| productcatalogservice | 21 / 130 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 4 / 22 |
| cartservice | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |

**Under the 0.25 re-enable bar**

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend (not controlled) | 33 / 71 | **┃** | 610 / 610 | 612 / 612 | **┃** | 599 / 599 | 605 / 605 | 42 / 210 |
| checkoutservice | 18 / 98 | **┃** | 609 / 609 | 610 / 610 | **┃** | 598 / 598 | 373 / 603 | 40 / 211 |
| recommendationservice | 352 / 602 | **┃** | 610 / 610 | 612 / 612 | **┃** | 599 / 599 | 265 / 594 | 319 / 553 |
| paymentservice | 18 / 99 | **┃** | 609 / 609 | 610 / 610 | **┃** | 598 / 598 | 374 / 604 | 40 / 211 |
| emailservice | 19 / 97 | **┃** | 609 / 609 | 610 / 610 | **┃** | 598 / 598 | 374 / 604 | 40 / 213 |
| productcatalogservice | 34 / 187 | **┃** | 610 / 610 | 611 / 611 | **┃** | 599 / 599 | 606 / 606 | 58 / 241 |
| cartservice | 362 / 607 | **┃** | 610 / 610 | 611 / 611 | **┃** | 599 / 599 | 606 / 606 | 599 / 599 |
| currencyservice | 360 / 604 | **┃** | 610 / 610 | 612 / 612 | **┃** | 599 / 599 | 606 / 606 | 599 / 599 |
| shippingservice | 24 / 118 | **┃** | 610 / 610 | 612 / 612 | **┃** | 599 / 599 | 606 / 606 | 52 / 237 |
| adservice | 23 / 101 | **┃** | 608 / 608 | 582 / 610 | **┃** | 598 / 598 | 459 / 604 | 40 / 227 |
| redis-cart (not controlled) | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |

On 400 off, 400 on, and 300 m, rejection stays under 0.25 for the whole hold. On 50 m and 100 m, frontend, checkout, payment, email, catalog, shipping, and ad spend long stretches above the bar. Catalog's longest streak above 0.20 is 21 s on 50 m.

**gRPC counted in the rejection rate, `grpc_4 / grpc_14`.**

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| recommendationservice | 3,911 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 4,176 / 0 | 9,186 / 0 |
| productcatalogservice | 72,163 / 1,803 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 13,519 / 4,715 |
| currencyservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 3 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| checkoutservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| recommendationservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| paymentservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| emailservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 1/716 (0.1%) | 0/714 (0.0%) |
| productcatalogservice | 204/724 (28.2%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | **513/716 (71.6%)** | 163/714 (22.8%) |
| cartservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| currencyservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| shippingservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| adservice | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |
| redis-cart | 0/724 (0.0%) | **┃** | 0/713 (0.0%) | 0/715 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) | 0/714 (0.0%) |

Catalog is the only service the detector marks overloaded. It crosses 0.5 only at 200 m. At 400 m and 300 m the share is 0. At 50 m and 100 m it is 28.2% and 22.8%.

## 8. (c) Retry volume

Outbound retry delta by target. Every target not listed is 0 on every hold.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| checkoutservice | 0 | **┃** | 0 | 1 | **┃** | 0 | 10 | 0 |
| recommendationservice | 3,488 | **┃** | 0 | 0 | **┃** | 0 | 5,650 | 5,667 |
| productcatalogservice | 40,701 | **┃** | 0 | 0 | **┃** | 0 | 0 | 19,131 |
| cartservice | 12 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |

The catalog total is both callers. On 50 m that is 39,065 from frontend and 1,636 from recommendations. On 100 m it is 18,445 from frontend and 686 from recommendations.

Inbound resets, all 11 services.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 89 | **┃** | 44 | 0 | **┃** | 1 | 66 | 200 |
| checkoutservice | 0 | **┃** | 0 | 0 | **┃** | 0 | 9 | 0 |
| recommendationservice | 523 | **┃** | 0 | 0 | **┃** | 0 | 2,149 | 2,879 |
| paymentservice | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |
| emailservice | 0 | **┃** | 0 | 0 | **┃** | 0 | 5 | 0 |
| productcatalogservice | 31,688 | **┃** | 14 | 0 | **┃** | 0 | 29 | 7,574 |
| cartservice | 7 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |
| currencyservice | 1 | **┃** | 0 | 0 | **┃** | 0 | 1 | 6 |
| shippingservice | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |
| adservice | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |
| redis-cart | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | 0 |

Catalog resets are 31,688 on 50 m and 7,574 on 100 m. Recommendations resets show up on those two holds and on 200 m (2,149), which is the hold with 5,650 retries into recommendations and 0 retries into catalog.

## 9. RetryGuard toggles

`productcatalogservice` and `recommendationservice` shed. Checkout, cart, and the other callees have no `ON→OFF` or `OFF→ON` on any hold.

The tables come from `retryguard.log`. Time OFF runs from each shed timestamp to the matching `OFF→ON` on that callee. OFF rejection is minimum / median over the `OBSERVE state=OFF` rejection samples in that window. The under-bar streak is the longest run of those samples strictly below 0.25. An em dash means that callee never went to 0 on that hold. More than one shed: values in time order, separated by `;`.

### productcatalogservice

| | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 6 / 4 | **┃** | — | — | **┃** | — | — | 1 / 1 |
| Shed rpr | 4.34; 1.50; 0.59; 4.67; 1.00; 1.51 | **┃** | — | — | **┃** | — | — | 0.98 |
| Attempts after re-enable | 1 (×4) | **┃** | — | — | **┃** | — | — | 3 |
| Time OFF (s) | 151; 22; 24; 24; 23; 22 | **┃** | — | — | **┃** | — | — | 57 |
| OFF rejection min / median | 0.000 / 0.551; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000 | **┃** | — | — | **┃** | — | — | 0.000 / 0.000 |
| Streak under the bar (s) | 20; 20; 16; 16; 20; 20 | **┃** | — | — | **┃** | — | — | 20 |

On 50 m the six sheds are four on `frontend → productcatalogservice` (rpr 4.34, 1.50, 0.59, 1.51) and two on `recommendationservice → productcatalogservice` (rpr 4.67, 1.00). The callee re-enabled four times, each time to 1 attempt, and never climbed to 2. The third and fourth sheds share one 24 s window, which is why their rejection row repeats. That window's strict under-bar streak is 16 s. The log's `consecutive_low` on the 09:03:04Z re-enable is 17. The first window ran 151 s. Its median rejection was 0.551, and a streak of 20 under 0.25 at the end of the window is what re-enabled it.

On 100 m, `frontend → productcatalogservice` shed once at rpr 0.98, stayed off 57 s, re-enabled, and climbed 1→2→3. The recommendations → catalog edge had five ticks above 0.40 and did not shed.

### recommendationservice

| | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 2 / 2 | **┃** | — | — | **┃** | — | — | 2 / 2 |
| Shed rpr | 11.67; 1.82 | **┃** | — | — | **┃** | — | — | 2.48; 1.75 |
| Attempts after re-enable | 3; 3 | **┃** | — | — | **┃** | — | — | 3; 3 |
| Time OFF (s) | 24; 23 | **┃** | — | — | **┃** | — | — | 111; 52 |
| OFF rejection min / median | 0.000 / 0.000; 0.000 / 0.000 | **┃** | — | — | **┃** | — | — | 0.000 / 0.471; 0.000 / 0.447 |
| Streak under the bar (s) | 16; 20 | **┃** | — | — | **┃** | — | — | 18; 20 |

Both holds that shed recommendations climbed back to 3 attempts. On 50 m the first window's strict streak is 16 s and the log's `consecutive_low` at re-enable is 17. On 100 m the first window's strict streak is 18 s and the log's `consecutive_low` is 19. The second window on each hold is a clean 20 s under the bar. On 200 m the edge's file streak is 10 s, so the callee never went to 0.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| getproduct | 0.1 | **┃** | 47.9 | 47.9 | **┃** | 47.9 | 40.9 | 1.4 |
| postcheckout | 0.2 | **┃** | 19.2 | 19.1 | **┃** | 19.2 | 16.6 | 0.6 |
| getcart | 0.2 | **┃** | 47.9 | 47.9 | **┃** | 47.9 | 42.3 | 2.1 |
| postcart | 74.4 | **┃** | 575.0 | 573.7 | **┃** | 574.7 | 535.3 | 144.1 |
| emptycart | 4.6 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | 3.9 |

Postcart goodput is about 575 at 400 m and 300 m, 535 at 200 m, and 144 at 100 m. The 50 m mix only offered 10 browse users, so its getproduct and getcart goodput near 0 is the mix, and its postcart goodput is 74.4.

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| getproduct | 0.962 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.080 | 0.920 |
| postcheckout | 0.951 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.073 | 0.912 |
| getcart | 0.955 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.069 | 0.901 |
| postcart | 0.818 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.013 | 0.627 |
| emptycart | 0.042 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 |

400 off, 400 on, and 300 m have no failures. 200 m is the first of the shared mix with a fail rate, still under 0.08 except postcart at 0.013. 50 m and 100 m fail on every API except emptycart.

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| getproduct | 728 | **┃** | 306 | 261 | **┃** | 427 | 844 | 813 |
| postcheckout | 816 | **┃** | 231 | 264 | **┃** | 241 | 780 | 759 |
| getcart | 801 | **┃** | 264 | 175 | **┃** | 420 | 716 | 752 |
| postcart | 411 | **┃** | 211 | 207 | **┃** | 236 | 345 | 318 |
| emptycart | 14 | **┃** | 29 | 21 | **┃** | 16 | 14 | 17 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 474.9 | **┃** | 641.4 | 641.4 | **┃** | 641.3 | 593.8 | 453.9 |
| checkoutservice | 0.4 | **┃** | 17.7 | 17.7 | **┃** | 17.7 | 16.0 | 1.5 |
| recommendationservice | 19.4 | **┃** | 106.1 | 106.1 | **┃** | 106.1 | 105.7 | 57.5 |
| paymentservice | 0.4 | **┃** | 17.7 | 17.7 | **┃** | 17.7 | 16.0 | 1.5 |
| emailservice | 0.4 | **┃** | 17.7 | 17.7 | **┃** | 17.7 | 16.0 | 1.5 |
| productcatalogservice | 239.6 | **┃** | 1211.6 | 1211.6 | **┃** | 1211.5 | 1114.6 | 254.2 |
| cartservice | 81.6 | **┃** | 659.1 | 659.1 | **┃** | 659.0 | 609.5 | 176.8 |
| currencyservice | 9.5 | **┃** | 212.2 | 212.2 | **┃** | 212.2 | 193.5 | 53.4 |
| shippingservice | 1.3 | **┃** | 79.6 | 79.6 | **┃** | 79.6 | 72.6 | 7.6 |
| adservice | 0.4 | **┃** | 44.2 | 44.2 | **┃** | 44.2 | 39.5 | 4.3 |
| redis-cart | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 |

Catalog arrival stays near 1,212 req/s at 400 m and 300 m, 1,115 at 200 m, and falls to 254.2 at 100 m. The 50 m hold arrives at 239.6 req/s on the lighter mix.

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. Redis-cart has no sojourn.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 228 | **┃** | 61 | 54 | **┃** | 87 | 163 | 154 |
| checkoutservice | 46 | **┃** | 118 | 65 | **┃** | 71 | 86 | 63 |
| recommendationservice | 198 | **┃** | 54 | 43 | **┃** | 72 | 155 | 202 |
| paymentservice | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | 2 |
| emailservice | 3 | **┃** | 11 | 9 | **┃** | 6 | 15 | 6 |
| productcatalogservice | 379 | **┃** | 4 | 5 | **┃** | 15 | 42 | 169 |
| cartservice | 8 | **┃** | 5 | 5 | **┃** | 7 | 14 | 10 |
| currencyservice | 1 | **┃** | 5 | 4 | **┃** | 4 | 3 | 3 |
| shippingservice | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | 1 |
| adservice | 4 | **┃** | 2 | 1 | **┃** | 2 | 2 | 2 |

Catalog sojourn on the shared mix is 4 ms, 5 ms, 15 ms, 42 ms, and 169 ms as the quota steps from 400 m to 100 m. Recommendations sojourn rises with it: 54 ms, 43 ms, 72 ms, 155 ms, 202 ms.

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. Every service not listed is 0.000 on every hold, and redis-cart has no share.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 0.221 | **┃** | 0.000 | 0.000 | **┃** | 0.003 | 0.054 | 0.076 |
| checkoutservice | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.001 | 0.000 |
| recommendationservice | 0.317 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.067 | 0.269 |
| productcatalogservice | 0.570 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.087 |

Catalog's share over 500 ms is 0.570 at 50 m and 0.087 at 100 m. At 200 m that share is 0.000, which matches the 0 retry delta into catalog. Recommendations is already at 0.067 over 500 ms on that hold.

## 16. CPU

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum `cpu_millicores` across replicas, so frontend can sit above its 1150 m per-pod quota.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 1150 / 4 / 490 / 758 | **┃** | 1150 / 4 / 768 / 1007 | 1150 / 4 / 806 / 1056 | **┃** | 1150 / 4 / 731 / 970 | 1150 / 4 / 786 / 1170 | 1150 / 4 / 664 / 1041 |
| checkoutservice | 800 / 1 / 11 / 92 | **┃** | 800 / 1 / 222 / 298 | 800 / 1 / 241 / 324 | **┃** | 800 / 1 / 253 / 346 | 800 / 1 / 302 / 458 | 800 / 1 / 38 / 178 |
| recommendationservice | 1150 / 1 / 43 / 74 | **┃** | 1150 / 1 / 184 / 244 | 1150 / 1 / 189 / 252 | **┃** | 1150 / 1 / 191 / 257 | 1150 / 1 / 239 / 526 | 1150 / 1 / 161 / 330 |
| paymentservice | 155 / 1 / 4 / 10 | **┃** | 155 / 1 / 17 / 30 | 155 / 1 / 17 / 25 | **┃** | 155 / 1 / 17 / 25 | 155 / 1 / 19 / 30 | 155 / 1 / 6 / 11 |
| emailservice | 120 / 1 / 8 / 15 | **┃** | 120 / 1 / 33 / 43 | 120 / 1 / 34 / 45 | **┃** | 120 / 1 / 35 / 46 | 120 / 1 / 40 / 62 | 120 / 1 / 13 / 28 |
| productcatalogservice | 50 / 1 / 21 / 55 | **┃** | 400 / 1 / 205 / 269 | 400 / 1 / 212 / 276 | **┃** | 300 / 1 / 179 / 240 | 200 / 1 / 156 / 201 | 100 / 1 / 37 / 102 |
| cartservice | 800 / 1 / 37 / 137 | **┃** | 800 / 1 / 288 / 456 | 800 / 1 / 314 / 507 | **┃** | 800 / 1 / 237 / 391 | 800 / 1 / 232 / 388 | 800 / 1 / 96 / 323 |
| currencyservice | 770 / 1 / 12 / 33 | **┃** | 770 / 1 / 92 / 124 | 770 / 1 / 97 / 129 | **┃** | 770 / 1 / 93 / 126 | 770 / 1 / 129 / 207 | 770 / 1 / 43 / 114 |
| shippingservice | 770 / 1 / 6 / 13 | **┃** | 770 / 1 / 39 / 53 | 770 / 1 / 41 / 54 | **┃** | 770 / 1 / 39 / 52 | 770 / 1 / 48 / 71 | 770 / 1 / 11 / 28 |
| adservice | 1150 / 1 / 34 / 105 | **┃** | 1150 / 1 / 63 / 169 | 1150 / 1 / 50 / 76 | **┃** | 1150 / 1 / 50 / 62 | 1150 / 1 / 65 / 98 | 1150 / 1 / 47 / 66 |
| redis-cart | 540 / 1 / 8 / 26 | **┃** | 540 / 1 / 39 / 60 | 540 / 1 / 39 / 59 | **┃** | 540 / 1 / 34 / 53 | 540 / 1 / 31 / 75 | 540 / 1 / 15 / 41 |

Replica mode is 4 for frontend and 1 for every other service. Catalog's mean at 100 m is 37 m, well under the 100 m quota, which fits the missing resource rows in §3 pulling the mean down.

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`.

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 0.11 / 0.16 | **┃** | 0.17 / 0.22 | 0.18 / 0.23 | **┃** | 0.16 / 0.21 | 0.17 / 0.25 | 0.14 / 0.23 |
| checkoutservice | 0.01 / 0.12 | **┃** | 0.28 / 0.37 | 0.30 / 0.41 | **┃** | 0.32 / 0.43 | 0.38 / 0.57 | 0.05 / 0.22 |
| recommendationservice | 0.04 / 0.06 | **┃** | 0.16 / 0.21 | 0.16 / 0.22 | **┃** | 0.17 / 0.22 | 0.21 / 0.46 | 0.14 / 0.29 |
| paymentservice | 0.02 / 0.06 | **┃** | 0.11 / 0.19 | 0.11 / 0.16 | **┃** | 0.11 / 0.16 | 0.12 / 0.19 | 0.04 / 0.07 |
| emailservice | 0.07 / 0.12 | **┃** | 0.27 / 0.36 | 0.28 / 0.38 | **┃** | 0.29 / 0.38 | 0.33 / 0.52 | 0.11 / 0.23 |
| productcatalogservice | 0.40 / 1.10 | **┃** | 0.51 / 0.67 | 0.53 / 0.69 | **┃** | 0.60 / 0.80 | 0.78 / 1.00 | 0.37 / 1.02 |
| cartservice | 0.05 / 0.17 | **┃** | 0.36 / 0.57 | 0.39 / 0.63 | **┃** | 0.30 / 0.49 | 0.29 / 0.48 | 0.12 / 0.40 |
| currencyservice | 0.02 / 0.04 | **┃** | 0.12 / 0.16 | 0.13 / 0.17 | **┃** | 0.12 / 0.16 | 0.17 / 0.27 | 0.06 / 0.15 |
| shippingservice | 0.01 / 0.02 | **┃** | 0.05 / 0.07 | 0.05 / 0.07 | **┃** | 0.05 / 0.07 | 0.06 / 0.09 | 0.01 / 0.04 |
| adservice | 0.03 / 0.09 | **┃** | 0.06 / 0.15 | 0.04 / 0.07 | **┃** | 0.04 / 0.05 | 0.06 / 0.09 | 0.04 / 0.06 |
| redis-cart | 0.01 / 0.05 | **┃** | 0.07 / 0.11 | 0.07 / 0.11 | **┃** | 0.06 / 0.10 | 0.06 / 0.14 | 0.03 / 0.08 |

Catalog's max fraction is at or above 1.0 on 50 m (1.10), 200 m (1.00), and 100 m (1.02). At 400 m the max is 0.67 and 0.69. At 300 m it is 0.80.

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | 50 m | **┃** | 400 off | 400 on | **┃** | 300 m | 200 m | 100 m |
| --- | ---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |
| frontend | 0.618 | **┃** | 0.249 | 0.269 | **┃** | 0.256 | 0.297 | 0.356 |
| checkoutservice | 0.186 | **┃** | 0.472 | 0.530 | **┃** | 0.516 | 0.777 | 0.386 |
| recommendationservice | 0.093 | **┃** | 0.310 | 0.315 | **┃** | 0.315 | 0.580 | 0.679 |
| paymentservice | 0.277 | **┃** | 0.400 | 0.335 | **┃** | 0.329 | 0.529 | 0.335 |
| emailservice | 0.325 | **┃** | 0.608 | 0.633 | **┃** | 0.683 | 0.850 | 0.583 |
| productcatalogservice | 1.360 | **┃** | 0.800 | 0.843 | **┃** | 0.940 | 1.065 | 1.230 |
| cartservice | 0.398 | **┃** | 0.641 | 0.736 | **┃** | 0.552 | 0.564 | 0.484 |
| currencyservice | 0.090 | **┃** | 0.247 | 0.238 | **┃** | 0.222 | 0.386 | 0.248 |
| shippingservice | 0.040 | **┃** | 0.105 | 0.108 | **┃** | 0.106 | 0.187 | 0.101 |
| adservice | 0.496 | **┃** | 0.293 | 0.123 | **┃** | 0.086 | 0.143 | 0.083 |
| redis-cart | 0.159 | **┃** | 0.246 | 0.194 | **┃** | 0.263 | 0.476 | 0.243 |

Catalog's max utilization is above 1 on 50 m, 200 m, and 100 m, and 0.800–0.940 on the two 400 m holds and on 300 m. The 400 m holds still have a detector overloaded share of 0 (§7).

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. Every live read the scorer kept is no cap.

- **400 off:** no cap on every API, 09:27:05–09:38:50.
- **400 on:** no cap on every API, 09:44:30–09:56:20. TopFull is on for this hold, and the scorer still records no live cap.
- **300 m:** no cap on every API, 10:24:40–10:36:30.
- **100 m:** no cap on every API, 11:00:15–11:12:05.
- **50 m:** no cap on every API, and the series only covers 08:54:40–08:57:10.
- **200 m:** no cap on every API, and the series only covers 10:42:25–10:44:50.

## 20. Per hold

**50 m.** Catalog sojourn is 379 ms and 0.570 of completions are over 500 ms. Retry delta into catalog is 40,701, with 31,688 inbound resets and `grpc_4` 72,163. Six sheds into catalog, four re-enables, each stopping at 1 attempt. Recommendations sheds twice and climbs back to 3 both times. Retry delta into recommendations is 3,488. Catalog is detector-overloaded on 28.2% of ticks. Postcart goodput is 74.4 with fail 0.818. Catalog replica count hits 0 on two samples.

**400 off.** No retries, no rpr, no shed. Catalog sojourn is 4 ms, arrival 1,211.6 req/s, share over 500 ms is 0. Detector overloaded share is 0. Postcart goodput is 575.0 with fail 0.

**400 on.** Same picture as 400 off. Catalog sojourn is 5 ms. One retry into checkout. TopFull records no live cap. Postcart goodput is 573.7 with fail 0.

**300 m.** No shed. Catalog sojourn is 15 ms, arrival 1,211.5 req/s, share over 500 ms is 0. Detector overloaded share is 0. Postcart goodput is 574.7 with fail 0. This hold has 154 inbound gaps (§3).

**200 m.** No shed. `frontend → recommendationservice` reaches the shed bar for 10 s, controller `high` 11, short of 20 s. Retry delta into recommendations is 5,650 and into catalog is 0. Catalog sojourn is 42 ms and its share over 500 ms is 0. Recommendations' share over 500 ms is 0.067. Catalog is detector-hot at 71.6%. Postcart goodput is 535.3 with fail 0.013. Getproduct fail is 0.080 and P95 is 844 ms.

**100 m.** `frontend → productcatalogservice` sheds once at rpr 0.98, stays off 57 s, re-enables, and climbs to 3. Recommendations sheds twice (rpr 2.48, 1.75) and climbs to 3 both times. Retry delta into catalog is 19,131 and into recommendations is 5,667. Catalog sojourn is 169 ms, share over 500 ms is 0.087, arrival falls to 254.2 req/s. `grpc_4` on catalog is 13,519 and `grpc_14` is 4,715. Catalog is detector-overloaded on 22.8% of ticks. Postcart goodput is 144.1 with fail 0.627. This hold has 154 inbound gaps, and 73 frontend timestamps have no catalog resource row.

On the shared mix, catalog retries and a catalog shed appear at 100 m. At 200 m the retries are on recommendations, and the recommendations streak stays under the 20 s shed interval. At 400 m and 300 m both edges stay at rpr 0.

## 21. Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md)
- The morning S4A holds at catalog 400 m with postcart 140 and 190: [2026-10-11-s3-s4-topology-abc.md](2026-10-11-s3-s4-topology-abc.md)
