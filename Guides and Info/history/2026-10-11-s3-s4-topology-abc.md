# S3 / S4A / S4B topology holds (2026-10-11): checkout 300m, productcatalog 400m, email 50m / 60m

Analysis of ten holds, one TopFull-off and one TopFull-on per variant, scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). Run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md).

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

Short column labels used in every table. Bold bars separate the five variant pairs. All ten folders have `run_number` 1 in `run_manifest.json`; the `log_folder` name is the slot.

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

**Flagged, not passed.** The run log records PASS on all ten, but the template counts a zero-replica service and inbound gaps of 1.5 s or longer as gate items, and S4B and two S4A holds have them.

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | Frontend replicas (samples) | Email rows with replica 0 / email rows | `retryguard.log` |
| --- | ---: | ---: | ---: | --- | --- | --- |
| S3 off | 573 | 665 | 0 of 7315 | 4 on every sample (149) | 0 | present |
| S3 on | 568 | 665 | 0 of 7315 | 4 on every sample (150) | 0 | present |
| A140 off | 573 | 664 | 0 of 7304 | 4 on every sample (148) | 0 | present |
| A140 on | 567 | 665 | **77 of 7238** | 4 on every sample (150) | 0 | present |
| A190 off | 574 | 664 | 0 of 7304 | 4 on every sample (149) | 0 | present |
| A190 on | 568 | 665 | **297 of 7018** | 4 on every sample (149) | 0 | present |
| B50 off | 573 | 664 | 0 of 7304 | 4 on every sample (149) | **25 of 77** | present |
| B50 on | 568 | 666 | 0 of 7326 | 4 on every sample (149) | **6 of 138** | present |
| B60 off | 573 | 664 | 0 of 7304 | 4 on every sample (149) | **12 of 149** | present |
| B60 on | 568 | 666 | 0 of 7326 | 4 on every sample (149) | **6 of 149** | present |

`service_capacity.json` matches the pin in §1 on all ten holds: checkout 300m on S3, catalog 400m on S4A, email 50m or 60m on S4B, and the §1 values elsewhere, with frontend at 4 replicas. Bold marks a flagged item.

1. **Email zero-replica rows (S4B only).** `resource_usage.csv` has 149 polls per hold. Email has a row with `replica_count` 0 on 25, 6, 12, and 6 of them (B50 off, B50 on, B60 off, B60 on). B50 off has an email row on only 77 of 149 polls, and B50 on on 138. No other service has a zero-replica row on any hold. Some of B50 off's zero-replica rows carry 48 to 50 m of CPU, which does not fit a pod that is down. The email CPU mean at 50m off (17) is below 60m off (38), and the detector's email share at 50m off (26.5%) is below 60m off (63.6%). Zero-replica rows with CPU 0 would pull both down. I have not confirmed that. The S4B numbers need a decision before they are cited.
2. **Inbound gaps.** A140 on has 77 gaps and A190 on has 297. Read those two holds with that caveat.

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

**Climb streaks, 1-attempt / 2-attempt** (samples while that cap is in force; em dash means that cap never applied)

| Edge | S3 off | S3 on | **┃** | A140 off | A140 on | **┃** | A190 off | A190 on | **┃** | B50 off | B50 on | **┃** | B60 off | B60 on |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |
| checkoutservice → emailservice | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — | **┃** | — / — | — / — |

No hold reached a climb cap, so the 1→2 and 2→3 steps never ran in this set.

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

Two parts. Part 1 is the scorer's log for each hold that toggled. Part 2 summarizes it per callee.

### Part 1: per hold

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name (`attempts=1`, `from_attempts=0`). `1→2` and `2→3` are the climb lines. `From` is the attempt count before the step, and `Value` is the rpr on a shed or climb line and the rejection on a re-enable line. The tables in this part are the scorer's output, unchanged.

#### S3 off

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-11T01:16:31Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.22 |

No transition lines on: S3 on, A140 off, A140 on, A190 off, A190 on, B50 off, B50 on, B60 off, B60 on.

### Part 2: per callee

Only `checkoutservice` toggles, and only on S3 off. Email never shed on any S4B hold, and catalog never shed on S4A, so those callees get one sentence each below.

The table comes from `retryguard.log` transitions (`from_attempts` → `attempts`). Time OFF runs from the shed timestamp to `EXIT` because the edge never re-enabled. OFF rejection is minimum / median over the `OBSERVE state=OFF` rejection samples in that window. The under-bar streak is the longest run of consecutive OFF samples below 0.25. An em dash means that edge never went to 0 on that hold.

#### checkoutservice

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

#### emailservice, productcatalogservice, recommendationservice

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

Replica mode is 1 for every service except frontend, and the email rows show the dips the gate section raised. Email's mean CPU at B50 off (17) is less than half the value at B60 off (38), B50 off has 25 zero-replica rows among its 77 email rows, which would pull its mean CPU (17) below B60 off's (38). That is not confirmed.

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

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. `emptycart` is no cap on every live read of every hold. `postcart` is no cap on every hold except A140 on and A190 on.

The five TopFull-off holds (S3 off, A140 off, A190 off, B50 off, B60 off) are no cap on every API for the whole window. S3 on, B50 on, and B60 on keep a moving postcheckout cap (10 to 33) with getproduct, getcart, and postcart no cap. A140 on and A190 on carry live caps on getproduct, postcheckout, getcart, and postcart that alternate with no cap; postcheckout is 29 to 33 on A140 on and 30 on A190 on. The cells keep the scorer's spans, one table per hold.

### S3 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:13:45–01:25:35 |
| postcheckout | no cap 01:13:45–01:25:35 |
| getcart | no cap 01:13:45–01:25:35 |
| postcart | no cap 01:13:45–01:25:35 |
| emptycart | no cap 01:13:45–01:25:35 |

### S3 on

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:31:00–01:42:55 |
| postcheckout | no cap 01:31:00–01:33:10; 19 at 01:33:15; 21 at 01:33:20; 14.4 at 01:33:25; 10 at 01:33:30; 19.5 at 01:33:35; 28.9231 at 01:33:36; 18.5 at 01:33:40; 10 at 01:33:45; 14.1 at 01:33:50; 27.9147 at 01:33:53; 29.8 at 01:33:55; 10 01:34:00–01:34:05; 25.8 at 01:34:10; 10 01:34:14–01:34:20; 27.9 at 01:34:25; 16.6 at 01:34:30; 10 at 01:34:35; 19.7 at 01:34:40; 32.3 at 01:34:45; 10 01:34:50–01:34:52; 14.1 at 01:34:55; 28.1 at 01:35:00; 10 01:35:05–01:35:10; 24.8907 at 01:35:14; 24.9 at 01:35:15; 10 01:35:18–01:35:20; 14.2 at 01:35:25; 32.8 at 01:35:30; 10 01:35:35–01:35:40; 33 at 01:35:45; 15 at 01:35:50; 10 01:35:52–01:35:55; 19.5 at 01:36:00; 22.8 at 01:36:05; 10 01:36:09–01:36:10; 19.6 at 01:36:15; 12.3 at 01:36:20; 10 01:36:22–01:36:25; 25.1 at 01:36:30; 29.9 at 01:36:35; 18.5551 at 01:36:38; 11.4 at 01:36:40; 10 at 01:36:45; 32.8 at 01:36:50; 12.5 at 01:36:55; 10 at 01:37:00; 26.3 at 01:37:05; 23 at 01:37:10; 10 at 01:37:15; 14.1 at 01:37:20; 26.1891 at 01:37:22; 28.7 at 01:37:25; 12.1 at 01:37:30; 10 at 01:37:35; 30.3657 at 01:37:39; 30.4 at 01:37:40; 10 at 01:37:45; 18.7 at 01:37:50; 32.7697 at 01:37:53; 26.9 at 01:37:55; 10 01:38:00–01:38:02; 19.8 at 01:38:05; 20 at 01:38:10; 12.2951 at 01:38:11; 10 01:38:15–01:38:16; 14.1 at 01:38:20; 31.2 at 01:38:25; 10 01:38:29–01:38:30; 14.1159 at 01:38:34; 14.1 at 01:38:35; 30 at 01:38:40; 18.856 at 01:38:41; 10 at 01:38:45; 19.6 at 01:38:50; no cap at 01:38:55; 10.5 at 01:39:00; 10 at 01:39:05; 29.3 at 01:39:10; 10 01:39:15–01:39:20; 19.7388 at 01:39:22; 29.4 at 01:39:25; 15 at 01:39:30; 10 at 01:39:35; 26 at 01:39:40; 10 01:39:45–01:39:50; 32.9 at 01:39:55; 25 at 01:40:00; 10 01:40:04–01:40:05; 19.6 at 01:40:10; 25.3 at 01:40:15; 10.744 at 01:40:17; 10 01:40:20–01:40:25; 28.3 at 01:40:30; 10 01:40:34–01:40:35; 14.2 at 01:40:40; 33 at 01:40:45; 10 01:40:50–01:40:51; 14.1 at 01:40:55; 33 at 01:41:00; 10 at 01:41:05; 14.081 at 01:41:09; 14.1 at 01:41:10; 30.4 at 01:41:15; 10 01:41:20–01:41:22; 19.7 at 01:41:25; 26.3235 at 01:41:26; 32.5 at 01:41:30; 10 01:41:34–01:41:40; 29.4 at 01:41:45; 18.8 at 01:41:50; 10 at 01:41:55; 26.3342 at 01:41:58; 29.7 at 01:42:00; 19.7867 at 01:42:02; 10 01:42:05–01:42:10; 31.8 at 01:42:15; 10 01:42:19–01:42:20; 14.1 at 01:42:25; 31.8 at 01:42:30; 13.1161 at 01:42:32; 10 01:42:35–01:42:40; 19.4447 at 01:42:41; 25.6 at 01:42:45; 18.7 at 01:42:50; 10 at 01:42:55 |
| getcart | no cap 01:31:00–01:42:55 |
| postcart | no cap 01:31:00–01:42:55 |
| emptycart | no cap 01:31:00–01:42:55 |

### A140 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:48:45–02:00:30 |
| postcheckout | no cap 01:48:45–02:00:30 |
| getcart | no cap 01:48:45–02:00:30 |
| postcart | no cap 01:48:45–02:00:30 |
| emptycart | no cap 01:48:45–02:00:30 |

### A140 on

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:06:00–02:08:30; 170 at 02:08:35; no cap at 02:08:40; 175 at 02:08:45; no cap 02:08:47–02:08:55; 175 02:08:57–02:09:06; no cap 02:09:10–02:09:15; 175 02:09:20–02:09:33; no cap 02:09:35–02:09:40; 175 02:09:42–02:09:51; no cap 02:09:55–02:10:00; 175 at 02:10:05; 192.5 02:10:10–02:10:15; no cap 02:10:19–02:10:20; 175 at 02:10:25; no cap at 02:10:28; 174 at 02:10:30; no cap 02:10:35–02:10:40; 175 at 02:10:45; no cap at 02:10:46; 175 02:10:50–02:10:56; no cap at 02:11:00; 175 at 02:11:05; no cap 02:11:10–02:11:20; 193.6 at 02:11:25; 175 02:11:30–02:11:38; no cap 02:11:40–02:11:45; 175 at 02:11:50; no cap at 02:11:55; 175 02:12:00–02:12:10; no cap 02:12:15–02:12:20; 175 at 02:12:25; no cap at 02:12:26; 175 at 02:12:30; no cap 02:12:35–02:12:40; 175 02:12:45–02:12:56; no cap 02:13:00–02:13:05; 175 02:13:10–02:13:15; no cap 02:13:20–02:13:25; 175 at 02:13:30; no cap at 02:13:31; 175 02:13:35–02:13:40; no cap 02:13:45–02:13:50; 175 at 02:13:55; no cap at 02:13:58; 175 02:14:00–02:14:05; no cap 02:14:10–02:14:16; 175 02:14:17–02:14:20; no cap at 02:14:25; 175 at 02:14:28; no cap 02:14:30–02:14:35; 175 02:14:37–02:14:50; no cap at 02:14:55; 175 02:15:00–02:15:01; no cap 02:15:03–02:15:05; 176 at 02:15:10; no cap 02:15:15–02:15:20; 175 at 02:15:25; no cap at 02:15:26; 175 02:15:27–02:15:30; no cap at 02:15:35; 175 at 02:15:38; no cap 02:15:40–02:15:45; 175 at 02:15:50; no cap at 02:15:53; 175 02:15:55–02:16:00; no cap 02:16:02–02:16:10; 175 02:16:12–02:16:15; no cap at 02:16:18; 175 at 02:16:20; no cap 02:16:25–02:16:30; 175 02:16:35–02:16:46; no cap at 02:16:50; 175 at 02:16:53; no cap 02:16:55–02:17:00; 175 02:17:02–02:17:11; no cap 02:17:15–02:17:20; 175 at 02:17:25; no cap at 02:17:26; 175 02:17:30–02:17:39; no cap 02:17:40–02:17:43; 175 02:17:45–02:17:50 |
| postcheckout | no cap 02:06:00–02:08:30; 29 at 02:08:35; no cap at 02:08:40; 30 at 02:08:45; no cap 02:08:47–02:08:55; 30 02:08:57–02:09:06; no cap 02:09:10–02:09:15; 30 02:09:20–02:09:33; no cap 02:09:35–02:09:41; 30 02:09:42–02:09:51; no cap 02:09:55–02:10:00; 30 at 02:10:05; 33 02:10:10–02:10:15; no cap 02:10:19–02:10:20; 30 at 02:10:25; no cap at 02:10:28; 29 at 02:10:30; no cap 02:10:35–02:10:40; 30 at 02:10:45; no cap at 02:10:46; 30 02:10:50–02:10:56; no cap at 02:11:00; 30 at 02:11:05; no cap 02:11:10–02:11:20; 33 at 02:11:25; 30 02:11:30–02:11:35; no cap at 02:11:37; 30 at 02:11:38; no cap 02:11:40–02:11:45; 30 at 02:11:50; no cap at 02:11:55; 30 02:12:00–02:12:10; no cap 02:12:15–02:12:20; 30 at 02:12:25; no cap at 02:12:26; 30 at 02:12:30; no cap 02:12:35–02:12:40; 30 at 02:12:45; no cap at 02:12:46; 30 02:12:50–02:12:56; no cap 02:13:00–02:13:05; 30 02:13:10–02:13:15; no cap 02:13:20–02:13:25; 30 at 02:13:30; no cap at 02:13:31; 30 02:13:35–02:13:43; no cap 02:13:45–02:13:50; 30 02:13:52–02:13:55; no cap at 02:13:58; 30 02:14:00–02:14:05; no cap 02:14:07–02:14:16; 30 02:14:17–02:14:20; no cap 02:14:25–02:14:27; 30 at 02:14:28; no cap 02:14:30–02:14:35; 30 02:14:37–02:14:50; no cap at 02:14:55; 30 at 02:15:00; no cap at 02:15:05; 30 at 02:15:10; no cap 02:15:15–02:15:20; 30 at 02:15:25; no cap at 02:15:26; 30 02:15:27–02:15:30; no cap at 02:15:35; 30 at 02:15:38; no cap 02:15:40–02:15:45; 30 at 02:15:50; no cap at 02:15:53; 30 02:15:55–02:16:00; no cap 02:16:02–02:16:10; 30 02:16:12–02:16:15; no cap at 02:16:18; 30 at 02:16:20; no cap 02:16:25–02:16:30; 30 02:16:35–02:16:46; no cap 02:16:50–02:16:52; 30 at 02:16:53; no cap 02:16:55–02:17:00; 30 02:17:02–02:17:11; no cap 02:17:15–02:17:20; 30 at 02:17:25; no cap at 02:17:26; 30 02:17:30–02:17:35; no cap 02:17:40–02:17:43; 30 02:17:45–02:17:50 |
| getcart | no cap 02:06:00–02:08:30; 77 at 02:08:35; no cap 02:08:37–02:08:40; 70 at 02:08:45; no cap 02:08:47–02:08:55; 70 02:08:57–02:09:06; no cap 02:09:10–02:09:15; 70 02:09:20–02:09:33; no cap 02:09:35–02:09:41; 70 02:09:42–02:09:51; no cap 02:09:55–02:10:00; 70 at 02:10:05; 77 02:10:10–02:10:15; no cap 02:10:19–02:10:20; 70 at 02:10:25; no cap at 02:10:28; 70 at 02:10:30; no cap 02:10:35–02:10:40; 70 at 02:10:45; no cap at 02:10:46; 70 02:10:50–02:10:56; no cap at 02:11:00; 70 at 02:11:05; no cap 02:11:10–02:11:20; 77 at 02:11:25; 70 02:11:30–02:11:35; no cap at 02:11:37; 70 at 02:11:38; no cap 02:11:40–02:11:45; 70 at 02:11:50; no cap at 02:11:55; 70 at 02:12:00; no cap at 02:12:01; 70 02:12:05–02:12:10; no cap 02:12:15–02:12:20; 70 at 02:12:25; no cap at 02:12:26; 70 at 02:12:30; no cap 02:12:35–02:12:40; 70 at 02:12:45; no cap at 02:12:46; 70 02:12:50–02:12:56; no cap 02:13:00–02:13:05; 70 02:13:10–02:13:15; no cap 02:13:20–02:13:25; 70 at 02:13:30; no cap at 02:13:31; 70 02:13:35–02:13:43; no cap 02:13:45–02:13:50; 70 02:13:52–02:13:55; no cap at 02:13:58; 70 02:14:00–02:14:05; no cap 02:14:07–02:14:16; 70 02:14:17–02:14:20; no cap 02:14:25–02:14:27; 70 at 02:14:28; no cap 02:14:30–02:14:36; 70 02:14:37–02:14:50; no cap at 02:14:55; 70 02:15:00–02:15:02; no cap at 02:15:05; 70 at 02:15:10; no cap 02:15:15–02:15:20; 70 at 02:15:25; no cap at 02:15:26; 70 02:15:27–02:15:30; no cap at 02:15:35; 70 at 02:15:38; no cap 02:15:40–02:15:45; 70 at 02:15:50; no cap at 02:15:53; 70 02:15:55–02:16:00; no cap 02:16:02–02:16:10; 70 02:16:12–02:16:15; no cap at 02:16:18; 70 02:16:20–02:16:21; no cap 02:16:25–02:16:30; 70 02:16:35–02:16:46; no cap 02:16:50–02:16:52; 70 at 02:16:53; no cap 02:16:55–02:17:00; 70 02:17:02–02:17:11; no cap 02:17:15–02:17:20; 70 at 02:17:25; no cap at 02:17:26; 70 02:17:29–02:17:35; no cap 02:17:40–02:17:43; 70 02:17:45–02:17:50 |
| postcart | no cap 02:06:00–02:08:30; 154 at 02:08:35; no cap 02:08:37–02:08:40; 140 at 02:08:45; no cap 02:08:47–02:08:55; 140 02:08:57–02:09:06; no cap 02:09:10–02:09:15; 140 02:09:20–02:09:33; no cap 02:09:35–02:09:41; 140 02:09:42–02:09:51; no cap 02:09:55–02:10:05; 154 at 02:10:10; no cap 02:10:14–02:10:20; 140 at 02:10:25; no cap at 02:10:28; 140 at 02:10:30; no cap 02:10:35–02:10:40; 140 at 02:10:45; no cap at 02:10:46; 140 02:10:50–02:10:56; no cap at 02:11:00; 140 at 02:11:05; no cap 02:11:10–02:11:20; 154 at 02:11:25; 140 02:11:30–02:11:35; no cap at 02:11:37; 140 at 02:11:38; no cap 02:11:40–02:11:55; 140 at 02:12:00; no cap at 02:12:01; 140 02:12:05–02:12:10; no cap 02:12:15–02:12:20; 140 at 02:12:25; no cap at 02:12:26; 140 at 02:12:30; no cap 02:12:35–02:12:40; 140 at 02:12:45; no cap at 02:12:46; 140 02:12:50–02:12:56; no cap 02:13:00–02:13:05; 140 02:13:10–02:13:15; no cap 02:13:20–02:13:25; 140 at 02:13:30; no cap at 02:13:31; 140 02:13:35–02:13:43; no cap 02:13:45–02:13:50; 140 02:13:52–02:13:55; no cap at 02:13:58; 140 02:14:00–02:14:05; no cap 02:14:07–02:14:16; 140 02:14:17–02:14:20; no cap 02:14:25–02:14:27; 140 at 02:14:28; no cap 02:14:30–02:14:36; 140 02:14:37–02:14:50; no cap at 02:14:55; 140 at 02:15:00; no cap at 02:15:05; 140 at 02:15:10; no cap 02:15:15–02:15:20; 140 at 02:15:25; no cap at 02:15:26; 140 02:15:27–02:15:30; no cap at 02:15:35; 140 at 02:15:38; no cap 02:15:40–02:15:45; 140 at 02:15:50; no cap at 02:15:53; 140 02:15:55–02:16:00; no cap 02:16:02–02:16:10; 140 02:16:12–02:16:15; no cap at 02:16:18; 140 02:16:20–02:16:21; no cap 02:16:25–02:16:30; 140 02:16:35–02:16:46; no cap 02:16:50–02:16:52; 140 at 02:16:53; no cap 02:16:55–02:17:00; 140 02:17:02–02:17:11; no cap 02:17:15–02:17:20; 140 at 02:17:25; no cap at 02:17:26; 140 02:17:29–02:17:35; no cap 02:17:40–02:17:43; 140 02:17:45–02:17:50 |
| emptycart | no cap 02:06:00–02:17:50 |

### A190 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:23:15–02:35:05 |
| postcheckout | no cap 02:23:15–02:35:05 |
| getcart | no cap 02:23:15–02:35:05 |
| postcart | no cap 02:23:15–02:35:05 |
| emptycart | no cap 02:23:15–02:35:05 |

### A190 on

| API | Live caps |
| --- | --- |
| getproduct | 175 and no cap alternate across 53 spans, from 175 at 02:43:20 through 175 at 02:52:10 |
| postcheckout | 30 and no cap alternate across 51 spans, from 30 at 02:43:20 through 30 at 02:52:10 |
| getcart | 70 and no cap alternate across 55 spans, from 70 02:43:20–02:43:30 through 70 02:52:10–02:52:12 |
| postcart | no cap 02:40:30–02:43:15; 190 02:43:20–02:43:30; no cap at 02:43:35; 190 at 02:43:40; no cap at 02:43:45; 190 at 02:43:50; no cap at 02:43:55; 190 02:43:58–02:44:00; no cap 02:44:05–02:44:15; 190 at 02:44:20; no cap 02:44:24–02:44:25; 190 02:44:30–02:44:31; no cap 02:44:33–02:44:35; 190 at 02:44:40; no cap 02:44:45–02:44:50; 190 02:44:55–02:45:00; no cap at 02:45:05; 190 02:45:10–02:45:15; no cap 02:45:20–02:45:30; 190 at 02:45:35; no cap 02:45:40–02:45:55; 190 at 02:46:00; no cap at 02:46:05; 190 02:46:10–02:46:12; no cap 02:46:14–02:46:15; 190 at 02:46:20; no cap at 02:46:25; 190 at 02:46:30; no cap at 02:46:35; 191 at 02:46:40; no cap at 02:46:45; 190 at 02:46:50; no cap 02:46:55–02:47:10; 190 at 02:47:15; no cap at 02:47:16; 190 at 02:47:20; no cap 02:47:25–02:48:15; 190 02:48:16–02:48:20; no cap at 02:48:25; 190 at 02:48:30; no cap 02:48:35–02:48:40; 190 02:48:45–02:48:50; no cap at 02:48:55; 190 at 02:49:00; no cap 02:49:05–02:49:40; 190 at 02:49:45; no cap 02:49:46–02:49:55; 190 at 02:50:00; no cap 02:50:01–02:50:15; 190 at 02:50:20; no cap 02:50:25–02:51:10; 190 at 02:51:15; no cap 02:51:20–02:51:35; 190 at 02:51:40; no cap at 02:51:45; 190 at 02:51:50; no cap 02:51:55–02:52:05; 190 at 02:52:10; no cap 02:52:15–02:52:20 |
| emptycart | no cap 02:40:30–02:52:20 |

### B50 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:58:10–03:10:00 |
| postcheckout | no cap 02:58:10–03:10:00 |
| getcart | no cap 02:58:10–03:10:00 |
| postcart | no cap 02:58:10–03:10:00 |
| emptycart | no cap 02:58:10–03:10:00 |

### B50 on

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:15:25–03:27:15 |
| postcheckout | no cap 03:15:25–03:17:25; 13 at 03:17:28; 15.4 at 03:17:30; 17 at 03:17:35; 19 at 03:17:40; no cap at 03:17:45; 25 at 03:17:50; 18.5208 at 03:17:54; 18.5 at 03:17:55; 14.1 at 03:18:00; no cap at 03:18:05; 30 03:18:10–03:18:15; 20.8 at 03:18:20; 10 03:18:23–03:18:25; 33 at 03:18:30; 29 at 03:18:35; 10 at 03:18:40; 21.5 at 03:18:45; 33 at 03:18:46; 19.4 at 03:18:50; 10 at 03:18:55; 27.6 at 03:19:00; 28 at 03:19:05; 10 at 03:19:10; 26.1 at 03:19:15; 30 at 03:19:20; 10 03:19:24–03:19:25; 24.015 at 03:19:28; 33 at 03:19:30; 30 at 03:19:33; 18.9 at 03:19:35; 10 at 03:19:37; 15.1 at 03:19:40; 33 at 03:19:45; 19.4 at 03:19:50; 10 at 03:19:55; 31.9758 at 03:19:59; 32 at 03:20:00; no cap at 03:20:05; 10 at 03:20:10; 19.4 at 03:20:15; 33 at 03:20:16; 19.3 at 03:20:20; 10 at 03:20:25; 31.3 at 03:20:30; 30 at 03:20:35; 10 03:20:39–03:20:40; 25.7566 at 03:20:43; 33 at 03:20:45; 30 at 03:20:48; 19.6 at 03:20:50; 10 03:20:52–03:20:55; 14.1298 at 03:20:56; 26.8 at 03:21:00; 28 at 03:21:05; 10 at 03:21:10; 13.8149 at 03:21:12; 26.8 at 03:21:15; 16.1 at 03:21:20; 15.5 at 03:21:25; 33 at 03:21:30; no cap at 03:21:35; 10 at 03:21:40; 26.5 at 03:21:45; 30 03:21:49–03:21:50; 10 at 03:21:55; 27.6 at 03:22:00; 18.2 at 03:22:05; 10 at 03:22:10; 14.0674 at 03:22:11; 19.8 at 03:22:15; 22.4 at 03:22:20; 13.9 at 03:22:25; 33 at 03:22:30; 29 at 03:22:35; 10 03:22:39–03:22:40; 29.9 at 03:22:45; 15 at 03:22:50; 10.2656 at 03:22:52; 17.9 at 03:22:55; 33 at 03:23:00; 18.4 at 03:23:05; 10.6 at 03:23:10; 33 03:23:14–03:23:15; 30 at 03:23:20; 10 at 03:23:25; 32.9489 at 03:23:29; 32.9 at 03:23:30; 18.8321 at 03:23:34; 18.8 at 03:23:35; 14.1 at 03:23:40; 21.9291 at 03:23:43; 31 at 03:23:45; 27 at 03:23:50; 10.3 at 03:23:55; 21.6879 at 03:23:58; 30.4 at 03:24:00; 14.1 at 03:24:05; 10 at 03:24:10; 32.2 at 03:24:15; 30 at 03:24:20; 14.6467 at 03:24:22; 10 at 03:24:25; 30 at 03:24:30; 33 at 03:24:31; 30 at 03:24:35; 10 at 03:24:40; 33 03:24:44–03:24:45; 18.8 at 03:24:50; 13.2 at 03:24:55; 19.7004 at 03:24:57; 23.8 at 03:25:00; 33 at 03:25:01; 28 at 03:25:05; 10 at 03:25:10; 31.2 at 03:25:15; 30 at 03:25:20; no cap at 03:25:22; 18.1 at 03:25:25; 12.6 at 03:25:30; 33 at 03:25:35; 30 03:25:40–03:25:45; no cap at 03:25:50; 19.5 at 03:25:55; 13.6 at 03:26:00; 33 at 03:26:05; no cap at 03:26:07; 30 at 03:26:10; 10 at 03:26:15; 21.3343 at 03:26:18; 29.9 at 03:26:20; no cap 03:26:25–03:27:15 |
| getcart | no cap 03:15:25–03:27:15 |
| postcart | no cap 03:15:25–03:27:15 |
| emptycart | no cap 03:15:25–03:27:15 |

### B60 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:32:55–03:44:45 |
| postcheckout | no cap 03:32:55–03:44:45 |
| getcart | no cap 03:32:55–03:44:45 |
| postcart | no cap 03:32:55–03:44:45 |
| emptycart | no cap 03:32:55–03:44:45 |

### B60 on

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:50:10–04:02:00 |
| postcheckout | no cap 03:50:10–03:52:25; 25.3 at 03:52:30; no cap at 03:52:35; 27 at 03:52:40; 27.9487 at 03:52:41; 22.1 at 03:52:45; no cap 03:52:50–03:52:55; 30 03:53:00–03:53:05; no cap 03:53:06–03:53:10; 30 03:53:14–03:53:15; no cap 03:53:20–03:53:25; 30 at 03:53:30; 17.2 at 03:53:35; 10.9 at 03:53:40; 15.3515 at 03:53:41; 29.2 at 03:53:45; 19.7 at 03:53:50; 14.1383 at 03:53:54; 14.1 at 03:53:55; 27.0242 at 03:53:58; 33 at 03:54:00; 30 at 03:54:05; 18.7 at 03:54:10; 10 at 03:54:15; 15.1835 at 03:54:16; 25.6 at 03:54:20; 30 03:54:25–03:54:30; no cap at 03:54:35; 20.0064 at 03:54:36; 10 at 03:54:40; 27.3 at 03:54:45; 30 at 03:54:50; 10 at 03:54:55; 31.1 at 03:55:00; no cap 03:55:05–03:55:10; 30 03:55:12–03:55:20; no cap at 03:55:25; 30 03:55:30–03:55:38; no cap at 03:55:40; 30 03:55:45–03:55:50; no cap at 03:55:55; 30 03:56:00–03:56:10; no cap 03:56:14–03:56:15; 30 03:56:20–03:56:25; no cap at 03:56:30; 30 at 03:56:35; no cap at 03:56:38; 30 at 03:56:40; no cap 03:56:45–03:56:50; 30 03:56:55–03:57:03; no cap at 03:57:05; 30 03:57:10–03:57:15; no cap at 03:57:20; 30 03:57:25–03:57:30; no cap at 03:57:35; 30 at 03:57:40; no cap at 03:57:41; 30 03:57:45–03:57:50; no cap 03:57:55–03:57:56; 30 at 03:57:57; no cap 03:58:00–03:58:05; 30.8284 at 03:58:09; 30.8 at 03:58:10; 30 03:58:15–03:58:20; no cap 03:58:24–03:58:25; 30 03:58:30–03:58:35; no cap at 03:58:40; 30 at 03:58:45; no cap at 03:58:48; 30 at 03:58:50; no cap 03:58:55–03:59:00; 30 03:59:02–03:59:10; no cap 03:59:12–03:59:15; 30 03:59:20–03:59:26; no cap at 03:59:30; 30 at 03:59:35; no cap 03:59:40–04:00:00; 30 at 04:00:05; no cap at 04:00:08; 30 at 04:00:10; 19.2 at 04:00:15; 10 at 04:00:20; 19.735 at 04:00:21; 28.3 at 04:00:25; no cap 04:00:30–04:00:33; 30 at 04:00:35; no cap 04:00:40–04:00:45; 30 04:00:50–04:00:55; no cap 04:01:00–04:01:06; 30 04:01:10–04:01:15; 10 at 04:01:20; 33 at 04:01:25; 25.2 at 04:01:30; 13.9421 at 04:01:33; 10 at 04:01:35; 14.2398 at 04:01:37; 27.6 at 04:01:40; 29 at 04:01:45; no cap at 04:01:50; 30 04:01:55–04:02:00 |
| getcart | no cap 03:50:10–04:02:00 |
| postcart | no cap 03:50:10–04:02:00 |
| emptycart | no cap 03:50:10–04:02:00 |

## 20. Per variant, per hold

**S3 off.** Checkout shed once, at rpr 2.22, and stayed at 0 for 546 s. Checkout is detector-hot at 82.2%. Retry delta into checkout is 854. Postcheckout goodput is 13.1 with fail 0.524, and P95 589 ms.

**S3 on.** No shed. Checkout's contiguous rpr streak is 10 s, controller `high` 11, and the 297 is the total tick count above 0.40. Checkout's median rpr is 0.273, the only positive median in the set. Retry delta into checkout is 8,981, about ten times S3 off. Checkout is detector-hot at 68.7%. Postcheckout goodput falls to 9.0 with fail 0.622 and P95 1219 ms. TopFull caps postcheckout between 10 and 33.

**A140 off.** No retries, no rpr, no shed. Productcatalog is detector-hot at 79.8% with max utilization 1.030, but nothing downstream fails or retries. Postcart goodput is 134.2, matching the 140 rate. Postcheckout is 28.7 with fail 0.

**A140 on.** No shed. Productcatalog is detector-hot at 75.0%. TopFull caps postcart at 140 and getproduct at 170–193.6. Goodput is 167.9 for getproduct and 134.3 for postcart, and postcheckout is 28.8 with fail 0.

**A190 off.** No shed. Productcatalog is detector-hot at only 3.9%, despite a higher postcart rate than A140 and higher inbound arrival (1781 req/s against 1737). Max utilization is 0.973. Postcart goodput is 182.3.

**A190 on.** No shed. Productcatalog is detector-hot at 11.7%. TopFull caps postcart at 190 and getproduct at 175. Postcart goodput is 182.3 and postcheckout 28.8 with fail 0.

**B50 off.** No shed. Checkout's frontend edge reaches the 0.40 shed bar for 10 s, with 58 ticks above it, but never for 20 s. Email is detector-hot at 26.5%. Email has 25 zero-replica rows among its 77 email rows. Retry delta into checkout is 1,235. Email inbound resets are 2,348. Postcheckout goodput 26.8 with fail 0.064.

**B50 on.** No shed. Frontend → checkout streak is 7 s and checkout → email has one tick above zero. Checkout retry delta is 3,307, and email retry delta is 90, the only email retry in the set. Email is detector-hot at 46.3%. Email has 6 zero-replica rows among its 138 email rows. Postcheckout goodput falls to 17.0 with fail 0.362 and P95 769 ms.

**B60 off.** No shed. Email is detector-hot at 63.6% (bold). Email has 12 zero-replica rows among its 149 email rows. Retry delta into checkout is 923. Postcheckout fail 0.036, P95 437 ms.

**B60 on.** No shed. Email is detector-hot at 65.2% (bold). Email has 6 zero-replica rows among its 149 email rows. Retry delta into checkout is 1,086. Postcheckout fail 0.091, P95 478 ms.

Across the set, RetryGuard acted once. S3 off shed checkout and never re-enabled. Every other hold had a frontend → checkout streak of at most 11 s, short of the 20 s `interval_samples` needed to shed. `grpc_4 / grpc_14` is 0 / 0 on every controlled gRPC callee on every hold, so no gRPC rejection fed the controller.

## 21. Related

- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md), edge-mode section
- Earlier set-B reads of the same variants, under the previous controller: [2026-10-10-set-b-s3-checkout-analysis.md](2026-10-10-set-b-s3-checkout-analysis.md), [2026-10-10-set-b-s4a-catalog-analysis.md](2026-10-10-set-b-s4a-catalog-analysis.md), [2026-10-10-set-b-s4b-email-analysis.md](2026-10-10-set-b-s4b-email-analysis.md)
- Plan and run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)
