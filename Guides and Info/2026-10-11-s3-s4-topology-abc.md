# S3 / S4A / S4B topology holds (2026-10-11): checkout 300m, productcatalog 400m, email 50m / 60m

Analysis of ten holds, one TopFull-off and one TopFull-on per variant, scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md).

**Gate status: flagged, not clean.** The run log records PASS on all ten, but the scorer shows two things the template counts as gate items. See §3.

## 1. Setup

- **Duration** 600 s. `spawn_rate` 50.
- **Mix.** S3 and S4B use the S1 locked mix **175 / 30 / 70 / 90 / 5** (getproduct / postcheckout / getcart / postcart / emptycart). S4A keeps that mix but sets postcart to **140** (`A140`) or **190** (`A190`).
- **Bottleneck per variant:**

| Variant | Constraint | Per-pod quota (m) | Replicas |
| --- | --- | ---: | ---: |
| S3 | checkoutservice | 300 | 1 |
| S4A | productcatalogservice | 400 | 1 |
| S4B | emailservice (Checkout-mediated) | 50 (`B50`) or 60 (`B60`) | 1 |

- **Rest of the cluster, Paper-C1 pin:** frontend 1150m × 4 replicas, sidecar `proxyCPU=90m`, `proxyCPULimit` unset. Recommendation 1150m, payment 155m, cart 800m, currency 770m, shipping 770m, ad 1150m, redis 540m, all at 1 replica. Catalog 800m outside S4A. Email 120m outside S4B.
- **Controllers.** RetryGuard on in all ten, with the tuned set from the S2 tuning study (`reenable_rejection 0.25`, `interval_samples 20`, climb `0.16 / 0.32` at `climb_interval_seconds 10`). TopFull off on `rgtf0` holds and on on `rgtf1` holds.
- **Cool-off** 120 s between holds (AGENTS §6).
- **Folders:** `experiments/results/campaign_48/S3_targeted_bottleneck/` (`study4_s3_ck300_rgtf{0,1}`), `S4A_topology_position_A/` (`study4_s4a_pc400_u{140,190}_rgtf{0,1}`), and `S4B_topology_position_B/` (`study4_s4b_em{50,60}_rgtf{0,1}`).

## 2. Index

Short column labels used in every table. Bold bars separate the five variant pairs.

| Column | Folder | Variant | Arm |
| --- | --- | --- | --- |
| S3 off | `study4_s3_ck300_rgtf0` | S3, checkout 300m | TopFull off |
| S3 on | `study4_s3_ck300_rgtf1` | S3, checkout 300m | TopFull on |
| A140 off | `study4_s4a_pc400_u140_rgtf0` | S4A, catalog 400m, postcart 140 | TopFull off |
| A140 on | `study4_s4a_pc400_u140_rgtf1` | S4A, catalog 400m, postcart 140 | TopFull on |
| A190 off | `study4_s4a_pc400_u190_rgtf0` | S4A, catalog 400m, postcart 190 | TopFull off |
| A190 on | `study4_s4a_pc400_u190_rgtf1` | S4A, catalog 400m, postcart 190 | TopFull on |
| B50 off | `study4_s4b_em50_rgtf0` | S4B, email 50m | TopFull off |
| B50 on | `study4_s4b_em50_rgtf1` | S4B, email 50m | TopFull on |
| B60 off | `study4_s4b_em60_rgtf0` | S4B, email 60m | TopFull off |
| B60 on | `study4_s4b_em60_rgtf1` | S4B, email 60m | TopFull on |

## 3. Gate

Scorer gate numbers. The template counts a zero replica count and inbound gaps of 1.5 s or longer as gate items, so these are the numbers that matter. The run log's PASS does not cover them.

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | Email replicas | `retryguard.log` |
| --- | ---: | ---: | ---: | --- | --- |
| S3 off | 573 | 665 | 0 of 7315 | — | present |
| S3 on | 568 | 665 | 0 of 7315 | — | present |
| A140 off | 573 | 664 | 0 of 7304 | — | present |
| A140 on | 567 | 665 | **77 of 7238** | — | present |
| A190 off | 574 | 664 | 0 of 7304 | — | present |
| A190 on | 568 | 665 | **297 of 7018** | — | present |
| B50 off | 573 | 664 | 0 of 7304 | **replicas 0–1 on 77 samples** | present |
| B50 on | 568 | 666 | 0 of 7326 | **replicas 0–1 on 138 samples** | present |
| B60 off | 573 | 664 | 0 of 7304 | **replicas 0–1 on 149 samples** | present |
| B60 on | 568 | 666 | 0 of 7326 | **replicas 0–1 on 149 samples** | present |

Bold marks a flagged item. Two problems:

1. **Email replicas.** All four S4B holds show emailservice at replica count 0 on 77–149 samples. The S4B email quota is pinned at one replica, so that is a pod-level gap in the resource data. The S4B numbers below need a decision before they are cited. The emailservice CPU mean at 50m (17 mean, 31 mean TopFull on) is lower than at 60m (38 and 41), and the detector's email share at 50m off (26.5%) is lower than at 60m off (63.6%). Both would fit a run of zero-CPU samples dragging the mean down. I have not confirmed that.
2. **Inbound gaps.** A140 on has 77 gaps and A190 on has 297. Those two holds have mesh sample gaps and should be read with that caveat.

## 4. Edge-mode bars

Scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Shed and 0→1 re-enable run on a **20 s** streak (`interval_samples` 20). Climbs 1→2 and 2→3 run on **10 s** (`climb_interval_seconds` override, not the 15 s default). Same tuned set as S2.

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge.

## 5. (a) Edge rpr

Two edges carry rpr in this set: `frontend → checkoutservice` and `checkoutservice → emailservice`. The second is nonzero only on B50 on, at 0 streak. The retry tables in §8 show retry volume into checkout on six holds and into email on one. Every other controlled edge is at zero.

**File streak, seconds / ticks above the shed bar (controller `high` in parentheses)**

| Edge | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 22 / 23 (21) | 10 / 297 (11) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 10 / 58 (11) | 7 / 181 (8) | **┃** | 6 / 33 (7) | 5 / 46 (6) |
| checkoutservice → emailservice | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 1 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) |

Read the second number carefully. "297" on S3 on is **total ticks above 0.40 across the hold, not a contiguous streak**. The longest contiguous run is 10 s, and controller `high` peaks at 11, under the 20 s `interval_samples`. That is why S3 on never shed.

No cell reaches 30 s, so nothing is bold.

**Mean / median / max / volume rpr**

| Edge | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | 0.086 / 0.000 / 3.50 / 0.049 | 1.036 / 0.273 / 6.25 / 0.903 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.078 / 0.000 / 1.17 / 0.071 | 0.241 / 0.000 / 1.82 / 0.249 | **┃** | 0.054 / 0.000 / 1.08 / 0.053 | 0.073 / 0.000 / 2.18 / 0.066 |
| checkoutservice → emailservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.005 / 0.000 / 0.71 / 0.006 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 |

S3 on is the only hold with a positive median rpr (0.273). On most of its ticks the frontend → checkout edge carried retries, which is not true of any other hold.

**Climb streaks, 1-attempt / 2-attempt.** Em dash on all ten: no hold reached a climb cap. The 1→2 and 2→3 steps never ran here.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count above 0.20, then longest streak / count strictly under 0.25. No cell in the above-0.20 tables reaches 30, so nothing is bold.

**Above 0.20**

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 1 / 1 | **┃** | 1 / 1 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 0 / 0 |
| checkoutservice | 26 / 372 | 12 / 287 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 1 / 1 | **┃** | 4 / 32 | 4 / 92 | **┃** | 6 / 19 | 5 / 31 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| paymentservice | 0 / 0 | 1 / 10 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 2 / 41 | 2 / 26 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 15 / 66 | 9 / 225 | **┃** | 17 / 59 | 8 / 73 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

**Under the 0.25 re-enable bar**

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 613 / 613 | 613 / 613 | **┃** | 612 / 612 | 606 / 606 | **┃** | 613 / 613 | 587 / 587 | **┃** | 612 / 612 | 614 / 614 | **┃** | 613 / 613 | 614 / 614 |
| checkoutservice | 47 / 320 | 40 / 338 | **┃** | 612 / 612 | 604 / 604 | **┃** | 611 / 611 | 584 / 584 | **┃** | 247 / 593 | 63 / 568 | **┃** | 198 / 601 | 383 / 594 |
| recommendationservice | 613 / 613 | 612 / 612 | **┃** | 613 / 613 | 605 / 605 | **┃** | 612 / 612 | 586 / 586 | **┃** | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 |
| paymentservice | 612 / 612 | 269 / 608 | **┃** | 612 / 612 | 604 / 604 | **┃** | 611 / 611 | 584 / 584 | **┃** | 611 / 611 | 612 / 612 | **┃** | 613 / 613 | 612 / 612 |
| emailservice | 66 / 565 | 41 / 432 | **┃** | 612 / 612 | 604 / 604 | **┃** | 611 / 611 | 583 / 584 | **┃** | 36 / 87 | 46 / 310 | **┃** | 168 / 512 | 117 / 520 |
| productcatalogservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 606 / 606 | **┃** | 613 / 613 | 586 / 586 | **┃** | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 |
| cartservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 606 / 606 | **┃** | 613 / 613 | 586 / 586 | **┃** | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 |
| currencyservice | 613 / 613 | 612 / 612 | **┃** | 613 / 613 | 605 / 605 | **┃** | 612 / 612 | 586 / 586 | **┃** | 613 / 613 | 612 / 612 | **┃** | 614 / 614 | 613 / 613 |
| shippingservice | 613 / 613 | 612 / 612 | **┃** | 613 / 613 | 605 / 605 | **┃** | 612 / 612 | 586 / 586 | **┃** | 612 / 612 | 612 / 612 | **┃** | 613 / 613 | 613 / 613 |
| adservice | 612 / 612 | 612 / 612 | **┃** | 612 / 612 | 604 / 604 | **┃** | 611 / 611 | 584 / 584 | **┃** | 612 / 612 | 611 / 611 | **┃** | 613 / 613 | 613 / 613 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

Checkout and email are the two controlled services whose rejection moves across the bar. Checkout's streak under the bar drops to 40–47 s on S3 and to 63 s on B50 on. The rest sit near one state for the whole hold.

**gRPC counted in the rejection rate, `grpc_4 / grpc_14`.** All controlled gRPC callees are 0 / 0 on every hold.

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| checkoutservice | **586/713 (82.2%)** | **493/718 (68.7%)** | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 45/713 (6.3%) | 74/717 (10.3%) | **┃** | 20/714 (2.8%) | 24/716 (3.4%) |
| recommendationservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| paymentservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| emailservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 189/713 (26.5%) | 332/717 (46.3%) | **┃** | **454/714 (63.6%)** | **467/716 (65.2%)** |
| productcatalogservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | **569/713 (79.8%)** | **538/717 (75.0%)** | **┃** | 28/713 (3.9%) | 84/717 (11.7%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| cartservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| currencyservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| shippingservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| adservice | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |
| redis-cart | 0/713 (0.0%) | 0/718 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) | 0/716 (0.0%) |

Each variant's bottleneck is the detector's hot service. Checkout is hot on S3, catalog on A140 but not A190, and email on B60 but only lightly on B50.

## 8. (c) Retry volume

Outbound retry delta by target. Every target not listed is 0 on every hold.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 854 | 8,981 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 1,235 | 3,307 | **┃** | 923 | 1,086 |
| emailservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 90 | **┃** | 0 | 0 |

Inbound resets, all 11 services.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 24 | 43 | **┃** | 26 | 22 | **┃** | 29 | 16 | **┃** | 16 | 16 | **┃** | 29 | 11 |
| checkoutservice | 4,670 | 5,996 | **┃** | 2 | 0 | **┃** | 4 | 1 | **┃** | 643 | 1,653 | **┃** | 500 | 573 |
| recommendationservice | 0 | 7 | **┃** | 0 | 1 | **┃** | 0 | 2 | **┃** | 2 | 2 | **┃** | 3 | 0 |
| paymentservice | 54 | 449 | **┃** | 2 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| emailservice | 660 | 105 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 2,348 | 6,719 | **┃** | 1,599 | 1,881 |
| productcatalogservice | 5 | 1 | **┃** | 2 | 8 | **┃** | 6 | 2 | **┃** | 3 | 6 | **┃** | 8 | 1 |
| cartservice | 223 | 200 | **┃** | 2 | 0 | **┃** | 0 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| shippingservice | 81 | 369 | **┃** | 0 | 0 | **┃** | 2 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 2 | 0 | **┃** | 1 | 0 | **┃** | 0 | 3 | **┃** | 1 | 0 | **┃** | 0 | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

Email's inbound resets are high on the S4B holds (2,348 and 6,719 on B50, 1,599 and 1,881 on B60) and checkout's are high on S3 (4,670 and 5,996). Those are the two bottleneck services. The resets sit alongside the retry volume in the same holds; this pass does not show which one causes the other.

## 9. RetryGuard toggles

Only `checkoutservice` toggles, and only on S3 off. Email never shed on any S4B hold, and catalog never shed on S4A, so those callees get one sentence each below.

The table comes from `retryguard.log` transitions (`from_attempts` → `attempts`). Time OFF runs from the shed timestamp to `EXIT` because the edge never re-enabled. OFF rejection is minimum / median over the `OBSERVE state=OFF` rejection samples in that window. The under-bar streak is the longest run of consecutive OFF samples below 0.25. An em dash means that edge never went to 0 on that hold.

### checkoutservice

| | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF / OFF→ON | 1 / 0 | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Shed rpr | 2.22 | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Attempts after re-enable | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Time OFF (s) | 546 (to EXIT) | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| OFF rejection min / median | 0.00 / 0.24 | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |
| Streak under the bar (s) | 11 | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

S3 off shed checkout once, at 01:16:31 with rpr 2.22 and controller `high` 21, and never re-enabled. The edge stayed at 0 for 546 s to exit. Its longest under-bar streak was 11 s, well short of the 20 s needed for a 0→1 step, so the controller had no reason to re-enable. Median rejection was 0.24, just under the 0.25 bar, but not for long enough.

No other hold shed.

### emailservice, productcatalogservice, recommendationservice

No ON→OFF or OFF→ON transition on any of their edges on any S3/S4 hold. One sentence, no table. Email is detector-hot on B60 (63.6% and 65.2%), but its `checkoutservice → emailservice` edge never shed. Catalog is detector-hot on A140 (79.8%) with no shed for the same reason.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 168.1 | 167.8 | **┃** | 167.8 | 167.9 | **┃** | 167.9 | 167.9 | **┃** | 168.0 | 167.7 | **┃** | 167.9 | 167.9 |
| postcheckout | 13.1 | 9.0 | **┃** | 28.7 | 28.8 | **┃** | 28.8 | 28.8 | **┃** | 26.8 | 17.0 | **┃** | 27.5 | 25.9 |
| getcart | 67.2 | 67.1 | **┃** | 67.1 | 67.2 | **┃** | 67.2 | 67.2 | **┃** | 67.2 | 67.1 | **┃** | 67.2 | 67.1 |
| postcart | 86.4 | 86.3 | **┃** | 134.2 | 134.3 | **┃** | 182.3 | 182.3 | **┃** | 86.4 | 86.2 | **┃** | 86.4 | 86.4 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 |

Postcart goodput tracks the S4A postcart rate (134 at 140, 182 at 190), so the S4A postcart setting took effect. Postcheckout goodput is low on the S3 holds (13.1 off, 9.0 on) and the two B50 / B60 on holds, and it is the only API that moved with TopFull on S3 and B50.

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcheckout | 0.524 | 0.622 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.064 | 0.362 | **┃** | 0.036 | 0.091 |
| getcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |

Postcheckout fail is the only API with failures in this set. It is 0.52–0.62 on S3 and 0.36 on B50 on.

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 71 | 77 | **┃** | 107 | 113 | **┃** | 116 | 111 | **┃** | 77 | 77 | **┃** | 82 | 80 |
| postcheckout | 589 | 1219 | **┃** | 182 | 188 | **┃** | 182 | 184 | **┃** | 305 | 769 | **┃** | 437 | 478 |
| getcart | 42 | 65 | **┃** | 72 | 91 | **┃** | 101 | 97 | **┃** | 65 | 64 | **┃** | 68 | 64 |
| postcart | 58 | 58 | **┃** | 68 | 65 | **┃** | 66 | 65 | **┃** | 58 | 58 | **┃** | 60 | 59 |
| emptycart | 10 | 14 | **┃** | 12 | 14 | **┃** | 12 | 11 | **┃** | 12 | 14 | **┃** | 13 | 14 |

S3 on's postcheckout P95 is 1219 ms, twice S3 off's 589. B50 on's is 769 ms, against 305 off.

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 326.3 | 315.2 | **┃** | 371.5 | 370.9 | **┃** | 415.7 | 415.1 | **┃** | 326.9 | 319.7 | **┃** | 327.3 | 324.9 |
| checkoutservice | 27.3 | 28.5 | **┃** | 26.5 | 26.5 | **┃** | 26.5 | 26.5 | **┃** | 28.1 | 24.9 | **┃** | 27.8 | 26.5 |
| recommendationservice | 242.3 | 231.3 | **┃** | 243.1 | 242.7 | **┃** | 243.1 | 242.8 | **┃** | 242.8 | 235.8 | **┃** | 243.1 | 241.0 |
| paymentservice | 26.6 | 23.3 | **┃** | 26.5 | 26.5 | **┃** | 26.5 | 26.5 | **┃** | 28.1 | 24.9 | **┃** | 27.8 | 26.5 |
| emailservice | 17.5 | 9.5 | **┃** | 26.5 | 26.5 | **┃** | 26.5 | 26.5 | **┃** | 6.9 | 21.4 | **┃** | 25.2 | 25.2 |
| productcatalogservice | 1687.6 | 1621.4 | **┃** | 1737.2 | 1734.5 | **┃** | 1781.4 | 1778.8 | **┃** | 1691.1 | 1648.5 | **┃** | 1693.1 | 1679.7 |
| cartservice | 350.7 | 340.4 | **┃** | 398.0 | 397.4 | **┃** | 442.3 | 441.6 | **┃** | 356.9 | 349.5 | **┃** | 356.5 | 353.1 |
| currencyservice | 471.9 | 469.6 | **┃** | 486.3 | 485.5 | **┃** | 486.2 | 485.5 | **┃** | 487.1 | 475.4 | **┃** | 487.4 | 483.3 |
| shippingservice | 114.5 | 106.3 | **┃** | 115.0 | 114.8 | **┃** | 115.0 | 114.8 | **┃** | 118.1 | 111.5 | **┃** | 117.6 | 114.9 |
| adservice | 154.4 | 154.4 | **┃** | 154.6 | 154.4 | **┃** | 154.6 | 154.4 | **┃** | 154.6 | 154.2 | **┃** | 154.7 | 154.3 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

Email's inbound arrival is lowest on B50 off (6.9 req/s) and S3 on (9.5 req/s), then S3 off (17.5). B50 off is one of the holds with email replica dips (see §3). S3 on has no replica data in this pass, so its low email arrival is not explained here.

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. Redis-cart has no sojourn.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 73 | 79 | **┃** | 53 | 52 | **┃** | 55 | 52 | **┃** | 50 | 63 | **┃** | 55 | 55 |
| checkoutservice | 444 | 374 | **┃** | 65 | 62 | **┃** | 70 | 57 | **┃** | 98 | 269 | **┃** | 155 | 170 |
| recommendationservice | 6 | 9 | **┃** | 9 | 10 | **┃** | 12 | 12 | **┃** | 9 | 9 | **┃** | 7 | 8 |
| paymentservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| emailservice | 5 | 4 | **┃** | 6 | 11 | **┃** | 7 | 12 | **┃** | 157 | 155 | **┃** | 106 | 112 |
| productcatalogservice | 0 | 1 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| cartservice | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 | **┃** | 2 | 2 |
| currencyservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| shippingservice | 1 | 1 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |

Checkout sojourn on S3 is 444 ms off and 374 on, the highest in the set. Email sojourn is 155–157 ms at 50m and 106–112 ms at 60m, against 4–12 ms on S3 and S4A.

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. Every service not listed is 0.000 on every hold, and redis-cart has no share.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.051 | 0.023 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.008 | 0.024 | **┃** | 0.008 | 0.009 |
| checkoutservice | 0.436 | 0.561 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.115 | 0.402 | **┃** | 0.078 | 0.099 |

## 16. CPU

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum `cpu_millicores` across replicas, so frontend can sit above its 1150m per-pod quota.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1067 / 1412 | 1150 / 4 / 954 / 1269 | **┃** | 1150 / 4 / 1021 / 1332 | 1150 / 4 / 1001 / 1327 | **┃** | 1150 / 4 / 1012 / 1319 | 1150 / 4 / 1009 / 1321 | **┃** | 1150 / 4 / 951 / 1241 | 1150 / 4 / 942 / 1245 | **┃** | 1150 / 4 / 960 / 1268 | 1150 / 4 / 1023 / 1356 |
| checkoutservice | 300 / 1 / 232 / 297 | 300 / 1 / 220 / 296 | **┃** | 800 / 1 / 314 / 418 | 800 / 1 / 311 / 418 | **┃** | 800 / 1 / 304 / 401 | 800 / 1 / 310 / 414 | **┃** | 800 / 1 / 395 / 682 | 800 / 1 / 346 / 568 | **┃** | 800 / 1 / 399 / 621 | 800 / 1 / 397 / 611 |
| recommendationservice | 1150 / 1 / 397 / 539 | 1150 / 1 / 365 / 496 | **┃** | 1150 / 1 / 392 / 518 | 1150 / 1 / 383 / 513 | **┃** | 1150 / 1 / 372 / 487 | 1150 / 1 / 367 / 489 | **┃** | 1150 / 1 / 366 / 485 | 1150 / 1 / 358 / 481 | **┃** | 1150 / 1 / 380 / 496 | 1150 / 1 / 397 / 537 |
| paymentservice | 155 / 1 / 20 / 28 | 155 / 1 / 18 / 27 | **┃** | 155 / 1 / 22 / 31 | 155 / 1 / 21 / 30 | **┃** | 155 / 1 / 21 / 30 | 155 / 1 / 21 / 30 | **┃** | 155 / 1 / 24 / 43 | 155 / 1 / 22 / 38 | **┃** | 155 / 1 / 24 / 41 | 155 / 1 / 24 / 42 |
| emailservice | 120 / 1 / 30 / 43 | 120 / 1 / 20 / 37 | **┃** | 120 / 1 / 42 / 54 | 120 / 1 / 41 / 54 | **┃** | 120 / 1 / 41 / 53 | 120 / 1 / 41 / 54 | **┃** | 50 / 1 / 17 / 50 | 50 / 1 / 31 / 48 | **┃** | 60 / 1 / 38 / 59 | 60 / 1 / 41 / 58 |
| productcatalogservice | 800 / 1 / 408 / 533 | 800 / 1 / 340 / 450 | **┃** | 400 / 1 / 315 / 398 | 400 / 1 / 308 / 395 | **┃** | 400 / 1 / 290 / 373 | 400 / 1 / 291 / 379 | **┃** | 800 / 1 / 340 / 443 | 800 / 1 / 339 / 448 | **┃** | 800 / 1 / 358 / 465 | 800 / 1 / 373 / 487 |
| cartservice | 800 / 1 / 269 / 365 | 800 / 1 / 259 / 433 | **┃** | 800 / 1 / 276 / 430 | 800 / 1 / 269 / 395 | **┃** | 800 / 1 / 306 / 491 | 800 / 1 / 273 / 374 | **┃** | 800 / 1 / 250 / 414 | 800 / 1 / 247 / 345 | **┃** | 800 / 1 / 264 / 438 | 800 / 1 / 287 / 473 |
| currencyservice | 770 / 1 / 244 / 322 | 770 / 1 / 226 / 300 | **┃** | 770 / 1 / 237 / 311 | 770 / 1 / 234 / 312 | **┃** | 770 / 1 / 229 / 298 | 770 / 1 / 227 / 300 | **┃** | 770 / 1 / 227 / 308 | 770 / 1 / 226 / 303 | **┃** | 770 / 1 / 233 / 310 | 770 / 1 / 249 / 332 |
| shippingservice | 770 / 1 / 57 / 75 | 770 / 1 / 52 / 69 | **┃** | 770 / 1 / 60 / 77 | 770 / 1 / 56 / 74 | **┃** | 770 / 1 / 57 / 75 | 770 / 1 / 57 / 78 | **┃** | 770 / 1 / 62 / 95 | 770 / 1 / 58 / 85 | **┃** | 770 / 1 / 64 / 93 | 770 / 1 / 64 / 90 |
| adservice | 1150 / 1 / 95 / 124 | 1150 / 1 / 94 / 127 | **┃** | 1150 / 1 / 88 / 114 | 1150 / 1 / 89 / 115 | **┃** | 1150 / 1 / 88 / 112 | 1150 / 1 / 87 / 112 | **┃** | 1150 / 1 / 89 / 155 | 1150 / 1 / 89 / 115 | **┃** | 1150 / 1 / 89 / 114 | 1150 / 1 / 98 / 126 |
| redis-cart | 540 / 1 / 34 / 51 | 540 / 1 / 31 / 47 | **┃** | 540 / 1 / 34 / 50 | 540 / 1 / 34 / 53 | **┃** | 540 / 1 / 35 / 53 | 540 / 1 / 36 / 53 | **┃** | 540 / 1 / 32 / 49 | 540 / 1 / 32 / 48 | **┃** | 540 / 1 / 33 / 50 | 540 / 1 / 34 / 53 |

Replica mode is 1 for every service except frontend, and the email rows show the dips the gate section raised. Email's mean CPU at B50 off (17) is less than half the value at B60 off (38), which fits zero-replica samples pulling the mean down. That is not confirmed.

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`, as the scorer reports them. Treat the B50 email numbers with the replica caveat from §3.

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.23 / 0.31 | 0.21 / 0.28 | **┃** | 0.22 / 0.29 | 0.22 / 0.29 | **┃** | 0.22 / 0.29 | 0.22 / 0.29 | **┃** | 0.21 / 0.27 | 0.20 / 0.27 | **┃** | 0.21 / 0.28 | 0.22 / 0.29 |
| checkoutservice | 0.77 / 0.99 | 0.73 / 0.99 | **┃** | 0.39 / 0.52 | 0.39 / 0.52 | **┃** | 0.38 / 0.50 | 0.39 / 0.52 | **┃** | 0.49 / 0.85 | 0.43 / 0.71 | **┃** | 0.50 / 0.78 | 0.50 / 0.76 |
| recommendationservice | 0.35 / 0.47 | 0.32 / 0.43 | **┃** | 0.34 / 0.45 | 0.33 / 0.45 | **┃** | 0.32 / 0.42 | 0.32 / 0.43 | **┃** | 0.32 / 0.42 | 0.31 / 0.42 | **┃** | 0.33 / 0.43 | 0.35 / 0.47 |
| paymentservice | 0.13 / 0.18 | 0.12 / 0.17 | **┃** | 0.14 / 0.20 | 0.14 / 0.19 | **┃** | 0.13 / 0.19 | 0.13 / 0.19 | **┃** | 0.16 / 0.28 | 0.14 / 0.25 | **┃** | 0.15 / 0.26 | 0.16 / 0.27 |
| emailservice | 0.25 / 0.36 | 0.16 / 0.31 | **┃** | 0.35 / 0.45 | 0.35 / 0.45 | **┃** | 0.34 / 0.44 | 0.34 / 0.45 | **┃** | 0.43 / 1.00 | 0.66 / 0.96 | **┃** | 0.69 / 0.98 | 0.70 / 0.97 |
| productcatalogservice | 0.51 / 0.67 | 0.42 / 0.56 | **┃** | 0.79 / 0.99 | 0.77 / 0.99 | **┃** | 0.73 / 0.93 | 0.73 / 0.95 | **┃** | 0.42 / 0.55 | 0.42 / 0.56 | **┃** | 0.45 / 0.58 | 0.47 / 0.61 |
| cartservice | 0.34 / 0.46 | 0.32 / 0.54 | **┃** | 0.34 / 0.54 | 0.34 / 0.49 | **┃** | 0.38 / 0.61 | 0.34 / 0.47 | **┃** | 0.31 / 0.52 | 0.31 / 0.43 | **┃** | 0.33 / 0.55 | 0.36 / 0.59 |
| currencyservice | 0.32 / 0.42 | 0.29 / 0.39 | **┃** | 0.31 / 0.40 | 0.30 / 0.41 | **┃** | 0.30 / 0.39 | 0.29 / 0.39 | **┃** | 0.29 / 0.40 | 0.29 / 0.39 | **┃** | 0.30 / 0.40 | 0.32 / 0.43 |
| shippingservice | 0.07 / 0.10 | 0.07 / 0.09 | **┃** | 0.08 / 0.10 | 0.07 / 0.10 | **┃** | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.08 / 0.12 | 0.08 / 0.11 | **┃** | 0.08 / 0.12 | 0.08 / 0.12 |
| adservice | 0.08 / 0.11 | 0.08 / 0.11 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.10 | **┃** | 0.08 / 0.13 | 0.08 / 0.10 | **┃** | 0.08 / 0.10 | 0.08 / 0.11 |
| redis-cart | 0.06 / 0.09 | 0.06 / 0.09 | **┃** | 0.06 / 0.09 | 0.06 / 0.10 | **┃** | 0.07 / 0.10 | 0.07 / 0.10 | **┃** | 0.06 / 0.09 | 0.06 / 0.09 | **┃** | 0.06 / 0.09 | 0.06 / 0.10 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.332 | 0.302 | **┃** | 0.313 | 0.354 | **┃** | 0.306 | 0.304 | **┃** | 0.288 | 0.293 | **┃** | 0.357 | 0.314 |
| checkoutservice | 1.047 | 1.097 | **┃** | 0.614 | 0.600 | **┃** | 0.576 | 0.603 | **┃** | 0.897 | 0.902 | **┃** | 0.920 | 0.901 |
| recommendationservice | 0.490 | 0.467 | **┃** | 0.488 | 0.478 | **┃** | 0.456 | 0.446 | **┃** | 0.451 | 0.448 | **┃** | 0.470 | 0.492 |
| paymentservice | 0.477 | 0.368 | **┃** | 0.381 | 0.477 | **┃** | 0.477 | 0.335 | **┃** | 0.413 | 0.400 | **┃** | 0.561 | 0.394 |
| emailservice | 0.583 | 0.550 | **┃** | 0.725 | 0.675 | **┃** | 0.658 | 0.658 | **┃** | 1.120 | 1.120 | **┃** | 1.083 | 1.100 |
| productcatalogservice | 0.710 | 0.596 | **┃** | 1.030 | 1.032 | **┃** | 0.973 | 0.990 | **┃** | 0.588 | 0.594 | **┃** | 0.616 | 0.635 |
| cartservice | 0.504 | 0.568 | **┃** | 0.564 | 0.547 | **┃** | 0.646 | 0.541 | **┃** | 0.556 | 0.496 | **┃** | 0.576 | 0.620 |
| currencyservice | 0.478 | 0.451 | **┃** | 0.455 | 0.444 | **┃** | 0.455 | 0.438 | **┃** | 0.439 | 0.432 | **┃** | 0.451 | 0.499 |
| shippingservice | 0.135 | 0.119 | **┃** | 0.131 | 0.130 | **┃** | 0.130 | 0.126 | **┃** | 0.139 | 0.147 | **┃** | 0.144 | 0.151 |
| adservice | 0.154 | 0.203 | **┃** | 0.155 | 0.125 | **┃** | 0.117 | 0.119 | **┃** | 0.355 | 0.129 | **┃** | 0.133 | 0.130 |
| redis-cart | 0.209 | 0.228 | **┃** | 0.209 | 0.226 | **┃** | 0.213 | 0.231 | **┃** | 0.219 | 0.219 | **┃** | 0.241 | 0.265 |

Productcatalog max utilization is 1.030 on A140 off and 0.973 on A190 off, both at or near the cap, yet A190's detector share is only 3.9% against A140's 79.8%. This does not match the rest of the table, and I have not explained it.

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. The scorer collapsed the long series, so I list spans only.

- **TopFull-off holds (S3 off, A140 off, A190 off, B50 off, B60 off):** no live cap on any API for the whole window.
- **S3 on:** getproduct, getcart, postcart, and emptycart are no cap. postcheckout has live caps between 10 and 33 from 01:31:00 to 01:42:55, too long to list.
- **A140 on:** getproduct has live caps 170–193.6, getcart 70–77, postcart 140 and 154, and postcheckout 29–33. emptycart is no cap.
- **A190 on:** getproduct 175, getcart 70, postcart 190 and 191, postcheckout 29–33. emptycart is no cap.
- **B50 on:** postcheckout has live caps between 10 and 33 from 03:17:28 to 03:26:20. getproduct, getcart, postcart, and emptycart are no cap.
- **B60 on:** postcheckout has live caps between 10 and 33 from 03:52:30 to 04:01:55. The rest are no cap.

Postcart's live caps on A140 and A190 sit at or just above the postcart rate (140, 154 and 190, 191). Those caps bind little. This pass does not establish that TopFull throttled postcart.

## 20. Per variant, per hold

**S3 off.** Checkout shed once, at rpr 2.22, and stayed at 0 for 546 s. Checkout is detector-hot at 82.2%. Retry delta into checkout is 854. Postcheckout goodput is 13.1 with fail 0.524, and P95 589 ms.

**S3 on.** No shed. Checkout's contiguous rpr streak is 10 s, controller `high` 11, and the 297 is the total tick count above 0.40. Checkout's median rpr is 0.273, the only positive median in the set. Retry delta into checkout is 8,981, about ten times S3 off. Checkout is detector-hot at 68.7%. Postcheckout goodput falls to 9.0 with fail 0.622 and P95 1219 ms. TopFull caps postcheckout between 10 and 33.

**A140 off.** No retries, no rpr, no shed. Productcatalog is detector-hot at 79.8% with max utilization 1.030, but nothing downstream fails or retries. Postcart goodput is 134.2, matching the 140 rate. Postcheckout is 28.7 with fail 0.

**A140 on.** No shed. Productcatalog is detector-hot at 75.0%. TopFull caps postcart at 140 and getproduct at 170–193.6. Goodput is 167.9 for getproduct and 134.3 for postcart, and postcheckout is 28.8 with fail 0.

**A190 off.** No shed. Productcatalog is detector-hot at only 3.9%, despite a higher postcart rate than A140 and higher inbound arrival (1781 req/s against 1737). Max utilization is 0.973. Postcart goodput is 182.3.

**A190 on.** No shed. Productcatalog is detector-hot at 11.7%. TopFull caps postcart at 190 and getproduct at 175. Postcart goodput is 182.3 and postcheckout 28.8 with fail 0.

**B50 off.** No shed. Checkout's frontend edge reaches the 0.40 shed bar for 10 s, with 58 ticks above it, but never for 20 s. Email is detector-hot at 26.5%. Email replica dips appear on 77 samples. Retry delta into checkout is 1,235. Email inbound resets are 2,348. Postcheckout goodput 26.8 with fail 0.064.

**B50 on.** No shed. Frontend → checkout streak is 7 s and checkout → email has one tick above zero. Checkout retry delta is 3,307, and email retry delta is 90, the only email retry in the set. Email is detector-hot at 46.3%. Email replica dips appear on 138 samples. Postcheckout goodput falls to 17.0 with fail 0.362 and P95 769 ms.

**B60 off.** No shed. Email is detector-hot at 63.6% (bold). Email replica dips appear on 149 samples. Retry delta into checkout is 923. Postcheckout fail 0.036, P95 437 ms.

**B60 on.** No shed. Email is detector-hot at 65.2% (bold). Email replica dips appear on 149 samples. Retry delta into checkout is 1,086. Postcheckout fail 0.091, P95 478 ms.

Across the set, RetryGuard acted once. S3 off shed checkout and never re-enabled. Every other hold had a frontend → checkout streak of at most 11 s, short of the 20 s `interval_samples` needed to shed.

## 21. Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md)
- Earlier set-B reads of the same variants, under the previous controller: [2026-10-10-set-b-s3-checkout-analysis.md](2026-10-10-set-b-s3-checkout-analysis.md), [2026-10-10-set-b-s4a-catalog-analysis.md](2026-10-10-set-b-s4a-catalog-analysis.md), [2026-10-10-set-b-s4b-email-analysis.md](2026-10-10-set-b-s4b-email-analysis.md)
- Plan and run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)
