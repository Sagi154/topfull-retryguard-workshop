# S1 and S2 mode matrix (2026-10-12)

Nine scored holds. S1 is 300 s and S2 is 600 s. Scored with `experiments/analysis_score.py`. A bold bar separates the four S1 columns from the five S2 columns. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Run log: [2026-10-12-s1-s2-mode-matrix-run-log.md](../docs/superpowers/plans/2026-10-12-s1-s2-mode-matrix-run-log.md).

## 1. Setup

- **S1.** Ten holds at 300 s. Mix getproduct / postcheckout / getcart / postcart / emptycart = **175 / 30 / 70 / 90 / 5**, `spawn_rate` 50. Each of the five cells twice.
- **S2.** Five holds at 600 s. Mix **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. Each cell once.
- **CPU and replica pin** (`service_capacity.json` on every scored hold):

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
| emailservice | 120 | 1 |
| redis-cart | 540 | 1 |

  That is the Paper-C1 pin: sidecar `proxyCPU=90m` with `proxyCPULimit` unset while frontend is held at 4, and catalog HPA max 1.
- **Cells.** Normal mode omits `burst_rpr`. Burst mode is `burst_rpr` 2.0, window 5 s, volume floor 20. RetryGuard on uses `retry_metric=edge_rpr`, `rejection_threshold=0.20`, `interval_samples=20`, `retries_threshold=0.4`, climb `0.16/0.32` at 10 s, `reenable_rejection=0.25`. RetryGuard off is `condition: baseline` and has no `retryguard.log`.
- **Cool-off** 120 s between holds, from `run_scenario.py` exit, including between the last S1 hold and the first S2 hold.
- **Folders** are under `experiments/results/final results/`. Configs are `experiments/configs/study_2026_10_12/18`–`32`, plus a `_r2` YAML for each failed cell. Each manifest has `run_number` 1; the `log_folder` name is the slot.

## 2. Index

Comparison columns are the nine holds that passed the matrix gate. Column order follows this row.

| | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | --- | --- | --- | --- | :---: | --- | --- | --- | --- | --- |
| Scenario | S1 | S1 | S1 | S1 | **┃** | S2 | S2 | S2 | S2 | S2 |
| Mode | normal | normal | burst 2.0 | burst 2.0 | **┃** | normal | normal | normal | burst 2.0 | burst 2.0 |
| RetryGuard | on | on | on | on | **┃** | on | on | off | on | on |
| TopFull | off | off | off | off | **┃** | off | on | on | off | on |

## 3. Gate

**Pass on the nine columns.** The six S1 cells with TopFull on failed the matrix gate, and the single replay of each failed the same way. Those twelve folders stay in `experiments/results/final results/` and are not comparison columns.

Failed cells, original and `_r2`, all `live5s_caps=0` with `other=0`. Every fresh threshold stayed at the 10000 passthrough. Locust rows were inside 270–310, frontend was 4 on every resource sample, and VirtualService attempts were 3.

| Hold | Folder | Replay | Locust rows |
| --- | --- | --- | ---: |
| 3 | `s1_normal_rgtf1_rep1` | `s1_normal_rgtf1_rep1_r2` | 287 / 287 |
| 4 | `s1_normal_rgtf1_rep2` | `s1_normal_rgtf1_rep2_r2` | 282 / 284 |
| 5 | `s1_normal_tf1rg0_rep1` | `s1_normal_tf1rg0_rep1_r2` | 277 / 288 |
| 6 | `s1_normal_tf1rg0_rep2` | `s1_normal_tf1rg0_rep2_r2` | 286 / 287 |
| 9 | `s1_burst20_rgtf1_rep1` | `s1_burst20_rgtf1_rep1_r2` | 285 / 287 |
| 10 | `s1_burst20_rgtf1_rep2` | `s1_burst20_rgtf1_rep2_r2` | 288 / 288 |

Scorer gate numbers for the nine columns:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| `s1_normal_rgtf0_rep1` | 288 | 364 | 0 of 4004 | present |
| `s1_normal_rgtf0_rep2` | 289 | 364 | 0 of 4004 | present |
| `s1_burst20_rgtf0_rep1` | 287 | 363 | 0 of 3993 | present |
| `s1_burst20_rgtf0_rep2` | 287 | 363 | 0 of 3993 | present |
| `s2_normal_rgtf0` | 562 | 663 | 0 of 7293 | present |
| `s2_normal_rgtf1` | 558 | 664 | 2145 of 5159 | present |
| `s2_normal_tf1rg0` | 557 | 639 | 2233 of 4796 | absent |
| `s2_burst20_rgtf0` | 563 | 664 | 0 of 7304 | present |
| `s2_burst20_rgtf1` | 558 | 663 | 3168 of 4125 | present |

`service_capacity.json` matches the pin in §1 on every scored hold. No scored hold has a zero-replica sample. The two TopFull-on S2 holds are the ones with inbound gaps of 1.5 s or longer.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

Normal holds have no `burst_rpr=` on the START line. Burst holds START with `burst_rpr=2.00 burst_window_seconds=5 burst_min_first_attempts=20`. The bar at each cap is `burst_rpr × attempts / attempts_on`: **2.00 / 1.33 / 0.67** at 3 / 2 / 1 attempts. A burst shed goes to 0 and recovers on the normal path.

Shed and 0→1 take **20 s** of row timestamps (`interval_samples=20`). Climbs 1→2 and 2→3 take **10 s** (`climb_interval_seconds=10`).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

Two edges have a tick above the shed bar or a retry delta: `frontend → checkoutservice` and `frontend → recommendationservice`. Every other controlled edge has no tick above 0.40 and a retry delta of 0. The file streak is in seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. `s2_normal_tf1rg0` has no log, so that column has no parenthetical. No file streak reaches 30 s, so nothing in these cells is bold.

## (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | **┃** | 22 / 69 (21) | 9 / 140 (8) | 8 / 140 | 7 / 62 (5) | 6 / 37 (2) |
| frontend → recommendationservice | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 (0) | **┃** | 0 / 0 (0) | 0 / 0 (0) | 0 / 0 | 7 / 8 (4) | 0 / 0 (0) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

## (a) Mean / median / max / volume rpr

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.145 / 0.000 / 3.16 / 0.110 | 0.794 / 0.000 / 5.05 / 0.714 | 0.792 / 0.000 / 4.95 / 0.731 | 0.103 / 0.000 / 3.29 / 0.090 | 0.132 / 0.000 / 2.78 / 0.116 |
| frontend → recommendationservice | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | **┃** | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.000 / 0.000 / 0.00 / 0.000 | 0.033 / 0.000 / 2.88 / 0.018 | 0.000 / 0.000 / 0.00 / 0.000 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

## (a) Climb streaks, 1-attempt / 2-attempt

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | — / — | — / — | — / — | — / — | **┃** | 2 / — | — / — | — / — | 5 / — | 2 / — |
| frontend → recommendationservice | — / — | — / — | — / — | — / — | **┃** | — / — | — / — | — / — | 11 / 9 | — / — |

## 5a. Burst

The four S1 columns and the three S2 normal columns are normal mode, so their burst-window cells are an em dash. The two S1 burst holds and the two S2 burst holds are burst mode.

Burst bars: s1_burst20_rgtf0_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); s1_burst20_rgtf0_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); s2_burst20_rgtf0 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); s2_burst20_rgtf1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force (burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count in parentheses. Samples exist only while the edge is above 0 attempts and the window meets the volume floor.

## (a2) Burst window

| Edge | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| checkoutservice → paymentservice | — | — | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (320) |
| frontend → productcatalogservice | — | — | 0.00 / 0.00 / 0 / 0 (308) | 0.00 / 0.00 / 0 / 0 (303) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (602) | 0.00 / 0.00 / 0 / 0 (324) |
| recommendationservice → productcatalogservice | — | — | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (323) |
| checkoutservice → cartservice | — | — | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (299) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (321) |
| checkoutservice → currencyservice | — | — | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (320) |
| frontend → cartservice | — | — | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (323) |
| frontend → currencyservice | — | — | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (302) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (602) | 0.00 / 0.00 / 0 / 0 (324) |
| frontend → adservice | — | — | 0.00 / 0.00 / 0 / 0 (306) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (600) | 0.00 / 0.00 / 0 / 0 (322) |
| frontend → checkoutservice | — | — | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) | **┃** | — | — | — | 2.19 / 0.01 / 10 / 10 (110) | 2.46 / 0.07 / 14 / 14 (101) |
| frontend → recommendationservice | — | — | 0.00 / 0.00 / 0 / 0 (307) | 0.00 / 0.00 / 0 / 0 (301) | **┃** | — | — | — | 2.74 / 0.00 / 1 / 1 (574) | 0.00 / 0.00 / 0 / 0 (323) |
| checkoutservice → emailservice | — | — | 0.00 / 0.00 / 0 / 0 (300) | 0.00 / 0.00 / 0 / 0 (297) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (582) | 0.00 / 0.00 / 0 / 0 (320) |
| checkoutservice → shippingservice | — | — | 0.00 / 0.00 / 0 / 0 (303) | 0.00 / 0.00 / 0 / 0 (299) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (321) |
| frontend → shippingservice | — | — | 0.00 / 0.00 / 0 / 0 (305) | 0.00 / 0.00 / 0 / 0 (300) | **┃** | — | — | — | 0.00 / 0.00 / 0 / 0 (600) | 0.00 / 0.00 / 0 / 0 (322) |

On `s2_burst20_rgtf0`, both sheds are burst sheds (10 on checkout, 1 on recommendations), so normal sheds are 0. On `s2_burst20_rgtf1`, all 14 checkout sheds are burst sheds, so normal sheds are 0. On a burst row of the timestamp table, `Value` is the 5 s aggregate `ΣΔretry / ΣΔfirst`, and `elapsed_s` is the window span.

`s2_burst20_rgtf1` is the both-on burst hold. Its first live burst shed is **63 s** after the first `OBSERVE` (15:07:25Z, `frontend → checkoutservice`, aggregate 2.46). The offline replay's first fire at bar 2.0 is 104–113 s ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)). This live fire is earlier than that band. Later replay fire counts assume instant recovery and are not compared. `s2_burst20_rgtf0` is TopFull off, so it has no replay prediction. Its first burst shed is **52 s** after the first `OBSERVE`.

## 6. Rejection, beside (a)

Not the shed signal. Longest streak / count above 0.20, then longest streak / count strictly under the re-enable bar 0.25. No controlled service reaches a 30 s streak above 0.20, so nothing in that table is bold. Frontend and redis-cart stay plain.

## (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 1 | 2 / 2 | 0 / 0 | 9 / 11 | 1 / 1 |
| checkoutservice | 0 / 0 | 0 / 0 | 1 / 1 | 0 / 0 | **┃** | 26 / 175 | 7 / 134 | 7 / 139 | 11 / 140 | 4 / 62 |
| recommendationservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 6 | 0 / 0 |
| paymentservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 1 / 2 | 1 / 2 | 1 / 2 | 1 / 1 | 0 / 0 |
| emailservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 5 / 131 | 4 / 63 | 3 / 64 | 5 / 108 | 3 / 47 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## (a) context: rejection streak under the re-enable bar / count

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend (not controlled) | 312 / 312 | 313 / 313 | 313 / 313 | 313 / 313 | **┃** | 613 / 613 | 417 / 417 | 47 / 383 | 540 / 603 | 325 / 325 |
| checkoutservice | 311 / 311 | 312 / 312 | 311 / 311 | 312 / 312 | **┃** | 45 / 473 | 42 / 287 | 43 / 256 | 47 / 509 | 44 / 273 |
| recommendationservice | 312 / 312 | 313 / 313 | 313 / 313 | 313 / 313 | **┃** | 612 / 612 | 418 / 418 | 410 / 410 | 613 / 613 | 326 / 326 |
| paymentservice | 311 / 311 | 312 / 312 | 312 / 312 | 312 / 312 | **┃** | 426 / 611 | 189 / 415 | 88 / 402 | 544 / 611 | 325 / 325 |
| emailservice | 311 / 311 | 312 / 312 | 311 / 311 | 312 / 312 | **┃** | 44 / 480 | 41 / 353 | 44 / 297 | 47 / 511 | 44 / 293 |
| productcatalogservice | 313 / 313 | 312 / 312 | 313 / 313 | 313 / 313 | **┃** | 613 / 613 | 418 / 418 | 410 / 410 | 613 / 613 | 326 / 326 |
| cartservice | 313 / 313 | 312 / 312 | 313 / 313 | 313 / 313 | **┃** | 613 / 613 | 418 / 418 | 410 / 410 | 613 / 613 | 326 / 326 |
| currencyservice | 312 / 312 | 313 / 313 | 313 / 313 | 313 / 313 | **┃** | 612 / 612 | 417 / 417 | 411 / 411 | 613 / 613 | 326 / 326 |
| shippingservice | 312 / 312 | 313 / 313 | 313 / 313 | 313 / 313 | **┃** | 612 / 612 | 417 / 417 | 410 / 410 | 613 / 613 | 326 / 326 |
| adservice | 311 / 311 | 312 / 312 | 312 / 312 | 312 / 312 | **┃** | 611 / 611 | 416 / 416 | 410 / 410 | 612 / 612 | 325 / 325 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

gRPC counted in the rejection rate and in the retry policy. Cell is grpc_4 / grpc_14.

## grpc_4 / grpc_14

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 5,330 / 0 | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

## (b) Detector overloaded fraction

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| checkoutservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | **588/712 (82.6%)** | **377/715 (52.7%)** | **368/690 (53.3%)** | **581/714 (81.4%)** | **503/714 (70.4%)** |
| recommendationservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 9/714 (1.3%) | 0/714 (0.0%) |
| paymentservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 2/712 (0.3%) | 0/715 (0.0%) | 2/690 (0.3%) | 0/714 (0.0%) | 0/714 (0.0%) |
| emailservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | **497/712 (69.8%)** | 122/715 (17.1%) | 85/690 (12.3%) | **498/714 (69.7%)** | **375/714 (52.5%)** |
| productcatalogservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| cartservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| currencyservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| shippingservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| adservice | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |
| redis-cart | 0/414 (0.0%) | 0/414 (0.0%) | 0/412 (0.0%) | 0/412 (0.0%) | **┃** | 0/712 (0.0%) | 0/715 (0.0%) | 0/690 (0.0%) | 0/714 (0.0%) | 0/714 (0.0%) |

## 8. (c) Retry volume

## (c) Outbound retry delta by target

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| checkoutservice | 0 | 0 | 0 | 0 | **┃** | 5,694 | 18,888 | 18,763 | 4,607 | 5,042 |
| recommendationservice | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | 4,735 | 0 |

## (c) Inbound resets

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 2 | 29 | 17 | 25 | **┃** | 50 | 102 | 19 | 101 | 70 |
| checkoutservice | 0 | 0 | 7 | 1 | **┃** | 10,789 | 13,378 | 12,918 | 8,679 | 7,596 |
| recommendationservice | 0 | 0 | 1 | 2 | **┃** | 18 | 2 | 3 | 1,686 | 0 |
| paymentservice | 0 | 0 | 0 | 0 | **┃** | 440 | 881 | 910 | 344 | 191 |
| emailservice | 0 | 0 | 0 | 0 | **┃** | 5,879 | 1,077 | 1,255 | 3,976 | 3,880 |
| productcatalogservice | 0 | 4 | 1 | 5 | **┃** | 0 | 8 | 2 | 5 | 15 |
| cartservice | 0 | 0 | 2 | 0 | **┃** | 373 | 879 | 869 | 374 | 387 |
| currencyservice | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | 2 | 0 |
| shippingservice | 0 | 0 | 0 | 0 | **┃** | 530 | 1,132 | 1,090 | 446 | 426 |
| adservice | 0 | 2 | 1 | 1 | **┃** | 0 | 2 | 1 | 1 | 1 |
| redis-cart | 0 | 0 | 0 | 0 | **┃** | 0 | 0 | 0 | 0 | 0 |

The same `grpc_4 / grpc_14` pair is in §6. On the scored holds the only non-zero pair is recommendationservice `grpc_4` **5330** on `s2_burst20_rgtf0`.

## 9. RetryGuard toggles

`ON→OFF` is a shed to 0 attempts. `0→1` is the re-enable. `s2_normal_tf1rg0` has no `retryguard.log`. The four S1 holds and `s2_normal_rgtf1` have a log and no transition lines.

### Part 1, per hold

## RetryGuard toggles

s1_normal_rgtf0_rep1: no transition lines.
s1_normal_rgtf0_rep2: no transition lines.
s1_burst20_rgtf0_rep1: no transition lines.
s1_burst20_rgtf0_rep2: no transition lines.
### s2_normal_rgtf0

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 3 | 0 | 0 | 0 |
| checkoutservice | 0 | 2 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T13:59:19Z | frontend → checkoutservice | ON→OFF | 3 | rpr 3.16 |
| 2026-10-12T14:00:56Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-12T14:01:20Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.94 |
| 2026-10-12T14:04:26Z | checkoutservice | OFF→ON | 0 | rejection 0.03 |
| 2026-10-12T14:04:49Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.83 |

s2_normal_rgtf1: no transition lines.
s2_normal_tf1rg0: no transition lines.
### s2_burst20_rgtf0

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 10 | 0 | 0 | 0 | 10 |
| frontend → recommendationservice | 1 | 0 | 1 | 1 | 1 |
| recommendationservice | 0 | 1 | 0 | 0 | 0 |
| checkoutservice | 0 | 9 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T14:50:00Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.20 |
| 2026-10-12T14:50:14Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.74 |
| 2026-10-12T14:50:41Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T14:50:52Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T14:51:03Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T14:51:05Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T14:51:13Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.84 |
| 2026-10-12T14:52:16Z | checkoutservice | OFF→ON | 0 | rejection 0.13 |
| 2026-10-12T14:52:22Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.72 |
| 2026-10-12T14:52:46Z | checkoutservice | OFF→ON | 0 | rejection 0.05 |
| 2026-10-12T14:52:53Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.69 |
| 2026-10-12T14:53:34Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T14:53:43Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.72 |
| 2026-10-12T14:54:07Z | checkoutservice | OFF→ON | 0 | rejection 0.11 |
| 2026-10-12T14:54:13Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.68 |
| 2026-10-12T14:54:37Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-12T14:54:44Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.83 |
| 2026-10-12T14:56:11Z | checkoutservice | OFF→ON | 0 | rejection 0.10 |
| 2026-10-12T14:56:18Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.82 |
| 2026-10-12T14:58:16Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T14:58:24Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.84 |
| 2026-10-12T14:58:56Z | checkoutservice | OFF→ON | 0 | rejection 0.03 |
| 2026-10-12T14:59:02Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.73 |

### s2_burst20_rgtf1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 14 | 0 | 0 | 0 | 14 |
| checkoutservice | 0 | 14 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T15:07:25Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.46 |
| 2026-10-12T15:07:49Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T15:07:59Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.72 |
| 2026-10-12T15:08:23Z | checkoutservice | OFF→ON | 0 | rejection 0.03 |
| 2026-10-12T15:08:31Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.88 |
| 2026-10-12T15:08:53Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-12T15:09:00Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.85 |
| 2026-10-12T15:09:39Z | checkoutservice | OFF→ON | 0 | rejection 0.07 |
| 2026-10-12T15:09:47Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.79 |
| 2026-10-12T15:10:24Z | checkoutservice | OFF→ON | 0 | rejection 0.09 |
| 2026-10-12T15:10:32Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.77 |
| 2026-10-12T15:10:55Z | checkoutservice | OFF→ON | 0 | rejection 0.05 |
| 2026-10-12T15:11:04Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.95 |
| 2026-10-12T15:11:28Z | checkoutservice | OFF→ON | 0 | rejection 0.09 |
| 2026-10-12T15:11:36Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.80 |
| 2026-10-12T15:11:58Z | checkoutservice | OFF→ON | 0 | rejection 0.07 |
| 2026-10-12T15:12:06Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.86 |
| 2026-10-12T15:12:28Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-12T15:12:36Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.84 |
| 2026-10-12T15:13:48Z | checkoutservice | OFF→ON | 0 | rejection 0.03 |
| 2026-10-12T15:13:56Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.67 |
| 2026-10-12T15:14:54Z | checkoutservice | OFF→ON | 0 | rejection 0.11 |
| 2026-10-12T15:15:05Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.89 |
| 2026-10-12T15:15:29Z | checkoutservice | OFF→ON | 0 | rejection 0.12 |
| 2026-10-12T15:15:37Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.67 |
| 2026-10-12T15:15:59Z | checkoutservice | OFF→ON | 0 | rejection 0.07 |
| 2026-10-12T15:16:09Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.73 |
| 2026-10-12T15:16:31Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |

### Part 2, per callee

Checkout and recommendations are the only callees that shed or re-enable. Payment, email, catalog, cart, currency, shipping, and ad have no `ON→OFF` and no `OFF→ON` on any scored hold.

Counts, shed rpr, and times come from the §9 timestamp log. A burst shed's rpr is the 5 s aggregate and is tagged `b`. Attempts after re-enable are the attempt count that edge holds at controller exit. Time OFF runs from the shed timestamp to the matching `OFF→ON`, or to the last log timestamp when the edge is still at 0. OFF rejection is minimum / median, three decimals, over `OBSERVE` `metric=rejection` samples for that callee with timestamps after the shed and at or before the end of that OFF window. The under-bar streak is the longest run of those samples strictly below 0.25. An em dash means that edge never went to 0 on that hold. The count row is `0 / 0` in that case. The parenthetical on `ON→OFF` is the burst-shed count.

#### checkoutservice

| | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |  **┃**  | 3 / 2 | 0 / 0 | 0 / 0 | 10 (10) / 9 | 14 (14) / 14 |
| Shed rpr | — | — | — | — |  **┃**  | 3.16; 0.94; 0.83 | — | — | 2.20b; 0.84b; 0.72b; 0.69b; 0.72b; 0.68b; 0.83b; 0.82b; 0.84b; 0.73b | 2.46b; 0.72b; 0.88b; 0.85b; 0.79b; 0.77b; 0.95b; 0.80b; 0.86b; 0.84b; 0.67b; 0.89b; 0.67b; 0.73b |
| First shed (s after first OBSERVE) | — | — | — | — |  **┃**  | 65 | — | — | 52 | 63 |
| Attempts after re-enable | — | — | — | — |  **┃**  | 0 | — | — | 0 | 1 |
| Time OFF (s) | — | — | — | — |  **┃**  | 97; 186; 219 | — | — | 65; 63; 24; 41; 24; 24; 87; 118; 32; 19 | 24; 24; 22; 39; 37; 23; 24; 22; 22; 72; 58; 24; 22; 22 |
| OFF rejection min / median | — | — | — | — |  **┃**  | 0.000 / 0.093 | — | — | 0.000 / 0.054 | 0.000 / 0.050 |
| Streak under 0.25 | — | — | — | — |  **┃**  | 21 | — | — | 21 | 12 |

`s2_normal_rgtf0` shed three times and re-enabled twice, both times stopping at 1 attempt, then shed again and was still at 0 at exit. Its longest under-bar streak is 21. `s2_burst20_rgtf0` shed ten times, all burst, re-enabled nine times to 1 attempt, and was still at 0 at exit. Its longest under-bar streak is 21. `s2_burst20_rgtf1` shed fourteen times, all burst, re-enabled fourteen times, and was at 1 attempt at exit. Its longest under-bar streak is 12. No checkout re-enable climbed through 1→2→3. The other six columns never put checkout at 0.

#### recommendationservice

| | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| ON→OFF / OFF→ON | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |  **┃**  | 0 / 0 | 0 / 0 | 0 / 0 | 1 (1) / 1 | 0 / 0 |
| Shed rpr | — | — | — | — |  **┃**  | — | — | — | 2.74b | — |
| First shed (s after first OBSERVE) | — | — | — | — |  **┃**  | — | — | — | 66 | — |
| Attempts after re-enable | — | — | — | — |  **┃**  | — | — | — | 3 | — |
| Time OFF (s) | — | — | — | — |  **┃**  | — | — | — | 27 | — |
| OFF rejection min / median | — | — | — | — |  **┃**  | — | — | — | 0.000 / 0.000 | — |
| Streak under 0.25 | — | — | — | — |  **┃**  | — | — | — | 21 | — |

Only `s2_burst20_rgtf0` moved recommendations. One burst shed, one re-enable, then a climb 1→2→3. It was at 3 attempts at exit. The OFF window was 27 s and the under-bar streak is 21. Every other column left recommendations at 3 attempts for the whole hold.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.


| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 161.0 | 160.8 | 161.0 | 161.2 | **┃** | 264.0 | 264.0 | 263.7 | 259.8 | 263.5 |
| postcheckout | 27.7 | 27.6 | 27.6 | 27.7 | **┃** | 60.0 | 29.8 | 28.1 | 63.8 | 54.4 |
| getcart | 64.4 | 64.5 | 64.4 | 64.5 | **┃** | 96.1 | 95.6 | 96.0 | 94.6 | 96.0 |
| postcart | 82.8 | 82.9 | 82.7 | 82.9 | **┃** | 86.3 | 86.2 | 86.4 | 86.3 | 86.2 |
| emptycart | 4.7 | 4.7 | 4.7 | 4.7 | **┃** | 4.8 | 4.8 | 4.8 | 4.8 | 4.7 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.


| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.014 | 0.000 |
| postcheckout | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.293 | 0.594 | 0.610 | 0.248 | 0.340 |
| getcart | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.013 | 0.000 |
| postcart | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.001 | 0.000 |
| emptycart | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.001 | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.


| API | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| getproduct | 79 | 76 | 69 | 71 | **┃** | 275 | 234 | 243 | 246 | 264 |
| postcheckout | 170 | 183 | 159 | 157 | **┃** | 705 | 957 | 933 | 698 | 614 |
| getcart | 63 | 67 | 46 | 56 | **┃** | 280 | 259 | 255 | 221 | 282 |
| postcart | 59 | 59 | 58 | 59 | **┃** | 70 | 67 | 67 | 70 | 68 |
| emptycart | 10 | 14 | 13 | 12 | **┃** | 14 | 22 | 14 | 16 | 17 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.


| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 291.8 | 291.8 | 292.6 | 292.6 | **┃** | 493.9 | 455.3 | 471.9 | 491.2 | 481.8 |
| checkoutservice | 23.6 | 23.7 | 23.7 | 23.7 | **┃** | 86.3 | 68.3 | 69.5 | 84.1 | 73.3 |
| recommendationservice | 216.8 | 216.7 | 217.3 | 217.3 | **┃** | 409.7 | 371.2 | 384.6 | 414.3 | 397.6 |
| paymentservice | 23.6 | 23.7 | 23.7 | 23.7 | **┃** | 84.7 | 65.6 | 66.9 | 83.0 | 72.5 |
| emailservice | 23.6 | 23.7 | 23.7 | 23.7 | **┃** | 69.4 | 32.7 | 32.9 | 69.4 | 59.9 |
| productcatalogservice | 1509.5 | 1509.1 | 1513.3 | 1513.0 | **┃** | 2781.0 | 2550.0 | 2642.5 | 2748.4 | 2708.8 |
| cartservice | 315.5 | 315.5 | 316.3 | 316.3 | **┃** | 574.9 | 522.9 | 540.9 | 570.1 | 552.8 |
| currencyservice | 433.5 | 433.4 | 434.6 | 434.5 | **┃** | 805.4 | 760.0 | 787.0 | 800.9 | 787.8 |
| shippingservice | 102.6 | 102.6 | 102.9 | 102.9 | **┃** | 253.3 | 209.2 | 215.3 | 249.3 | 230.6 |
| adservice | 137.8 | 137.7 | 138.1 | 138.1 | **┃** | 243.3 | 242.9 | 252.4 | 239.1 | 243.3 |
| redis-cart | 0.0 | 0.0 | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.


| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 47 | 46 | 41 | 42 | **┃** | 199 | 164 | 161 | 197 | 174 |
| checkoutservice | 79 | 82 | 74 | 63 | **┃** | 383 | 325 | 320 | 371 | 334 |
| recommendationservice | 8 | 9 | 6 | 6 | **┃** | 71 | 56 | 52 | 71 | 65 |
| paymentservice | 1 | 2 | 2 | 1 | **┃** | 5 | 6 | 6 | 5 | 4 |
| emailservice | 6 | 7 | 5 | 6 | **┃** | 66 | 36 | 31 | 68 | 60 |
| productcatalogservice | 1 | 1 | 1 | 1 | **┃** | 2 | 2 | 2 | 2 | 2 |
| cartservice | 2 | 2 | 2 | 2 | **┃** | 4 | 3 | 3 | 3 | 3 |
| currencyservice | 1 | 1 | 1 | 1 | **┃** | 4 | 3 | 3 | 3 | 3 |
| shippingservice | 0 | 0 | 0 | 0 | **┃** | 1 | 1 | 1 | 1 | 1 |
| adservice | 1 | 1 | 1 | 1 | **┃** | 1 | 1 | 1 | 1 | 1 |
| redis-cart | — | — | — | — | **┃** | — | — | — | — | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.


| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.096 | 0.039 | 0.036 | 0.096 | 0.066 |
| checkoutservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.227 | 0.402 | 0.424 | 0.181 | 0.192 |
| recommendationservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.021 | 0.000 |
| paymentservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| redis-cart | — | — | — | — | **┃** | — | — | — | — | — |

## 16. CPU

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas.

## CPU quota / replicas / mean / max

| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 1150 / 4 / 827 / 1327 | 1150 / 4 / 828 / 1341 | 1150 / 4 / 908 / 1465 | 1150 / 4 / 844 / 1361 | **┃** | 1150 / 4 / 1247 / 1613 | 1150 / 4 / 1229 / 1634 | 1150 / 4 / 1264 / 1591 | 1150 / 4 / 1251 / 1618 | 1150 / 4 / 1223 / 1608 |
| checkoutservice | 800 / 1 / 257 / 419 | 800 / 1 / 257 / 416 | 800 / 1 / 260 / 421 | 800 / 1 / 262 / 424 | **┃** | 800 / 1 / 628 / 798 | 800 / 1 / 502 / 795 | 800 / 1 / 517 / 796 | 800 / 1 / 625 / 799 | 800 / 1 / 584 / 797 |
| recommendationservice | 1150 / 1 / 318 / 522 | 1150 / 1 / 315 / 523 | 1150 / 1 / 334 / 557 | 1150 / 1 / 324 / 538 | **┃** | 1150 / 1 / 620 / 828 | 1150 / 1 / 574 / 816 | 1150 / 1 / 586 / 772 | 1150 / 1 / 627 / 1039 | 1150 / 1 / 595 / 834 |
| paymentservice | 155 / 1 / 18 / 29 | 155 / 1 / 18 / 30 | 155 / 1 / 18 / 31 | 155 / 1 / 19 / 33 | **┃** | 155 / 1 / 52 / 92 | 155 / 1 / 41 / 77 | 155 / 1 / 43 / 100 | 155 / 1 / 52 / 80 | 155 / 1 / 46 / 74 |
| emailservice | 120 / 1 / 36 / 54 | 120 / 1 / 36 / 55 | 120 / 1 / 36 / 57 | 120 / 1 / 36 / 55 | **┃** | 120 / 1 / 81 / 118 | 120 / 1 / 48 / 105 | 120 / 1 / 47 / 111 | 120 / 1 / 82 / 119 | 120 / 1 / 73 / 115 |
| productcatalogservice | 800 / 1 / 297 / 474 | 800 / 1 / 298 / 477 | 800 / 1 / 340 / 536 | 800 / 1 / 321 / 510 | **┃** | 800 / 1 / 406 / 527 | 800 / 1 / 413 / 549 | 800 / 1 / 430 / 542 | 800 / 1 / 399 / 517 | 800 / 1 / 406 / 536 |
| cartservice | 800 / 1 / 212 / 357 | 800 / 1 / 212 / 346 | 800 / 1 / 229 / 385 | 800 / 1 / 236 / 465 | **┃** | 800 / 1 / 292 / 485 | 800 / 1 / 306 / 505 | 800 / 1 / 286 / 366 | 800 / 1 / 308 / 508 | 800 / 1 / 289 / 490 |
| currencyservice | 770 / 1 / 189 / 309 | 770 / 1 / 194 / 320 | 770 / 1 / 206 / 332 | 770 / 1 / 194 / 320 | **┃** | 770 / 1 / 318 / 420 | 770 / 1 / 311 / 426 | 770 / 1 / 317 / 410 | 770 / 1 / 330 / 473 | 770 / 1 / 314 / 426 |
| shippingservice | 770 / 1 / 50 / 78 | 770 / 1 / 48 / 77 | 770 / 1 / 52 / 82 | 770 / 1 / 51 / 80 | **┃** | 770 / 1 / 84 / 110 | 770 / 1 / 75 / 114 | 770 / 1 / 76 / 108 | 770 / 1 / 92 / 122 | 770 / 1 / 80 / 112 |
| adservice | 1150 / 1 / 82 / 123 | 1150 / 1 / 83 / 128 | 1150 / 1 / 86 / 131 | 1150 / 1 / 82 / 124 | **┃** | 1150 / 1 / 127 / 177 | 1150 / 1 / 129 / 174 | 1150 / 1 / 130 / 166 | 1150 / 1 / 128 / 172 | 1150 / 1 / 125 / 172 |
| redis-cart | 540 / 1 / 27 / 42 | 540 / 1 / 26 / 42 | 540 / 1 / 29 / 45 | 540 / 1 / 28 / 44 | **┃** | 540 / 1 / 33 / 43 | 540 / 1 / 33 / 44 | 540 / 1 / 34 / 43 | 540 / 1 / 34 / 45 | 540 / 1 / 33 / 45 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. A sample with replica count 0 is left out. None of the scored holds had one.


| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.18 / 0.29 | 0.18 / 0.29 | 0.20 / 0.32 | 0.18 / 0.30 | **┃** | 0.27 / 0.35 | 0.27 / 0.36 | 0.27 / 0.35 | 0.27 / 0.35 | 0.27 / 0.35 |
| checkoutservice | 0.32 / 0.52 | 0.32 / 0.52 | 0.32 / 0.53 | 0.33 / 0.53 | **┃** | 0.78 / 1.00 | 0.63 / 0.99 | 0.65 / 0.99 | 0.78 / 1.00 | 0.73 / 1.00 |
| recommendationservice | 0.28 / 0.45 | 0.27 / 0.45 | 0.29 / 0.48 | 0.28 / 0.47 | **┃** | 0.54 / 0.72 | 0.50 / 0.71 | 0.51 / 0.67 | 0.55 / 0.90 | 0.52 / 0.73 |
| paymentservice | 0.12 / 0.19 | 0.12 / 0.19 | 0.12 / 0.20 | 0.12 / 0.21 | **┃** | 0.34 / 0.59 | 0.27 / 0.50 | 0.28 / 0.65 | 0.34 / 0.52 | 0.30 / 0.48 |
| emailservice | 0.30 / 0.45 | 0.30 / 0.46 | 0.30 / 0.47 | 0.30 / 0.46 | **┃** | 0.68 / 0.98 | 0.40 / 0.88 | 0.40 / 0.93 | 0.68 / 0.99 | 0.61 / 0.96 |
| productcatalogservice | 0.37 / 0.59 | 0.37 / 0.60 | 0.42 / 0.67 | 0.40 / 0.64 | **┃** | 0.51 / 0.66 | 0.52 / 0.69 | 0.54 / 0.68 | 0.50 / 0.65 | 0.51 / 0.67 |
| cartservice | 0.26 / 0.45 | 0.26 / 0.43 | 0.29 / 0.48 | 0.29 / 0.58 | **┃** | 0.37 / 0.61 | 0.38 / 0.63 | 0.36 / 0.46 | 0.39 / 0.64 | 0.36 / 0.61 |
| currencyservice | 0.25 / 0.40 | 0.25 / 0.42 | 0.27 / 0.43 | 0.25 / 0.42 | **┃** | 0.41 / 0.55 | 0.40 / 0.55 | 0.41 / 0.53 | 0.43 / 0.61 | 0.41 / 0.55 |
| shippingservice | 0.06 / 0.10 | 0.06 / 0.10 | 0.07 / 0.11 | 0.07 / 0.10 | **┃** | 0.11 / 0.14 | 0.10 / 0.15 | 0.10 / 0.14 | 0.12 / 0.16 | 0.10 / 0.15 |
| adservice | 0.07 / 0.11 | 0.07 / 0.11 | 0.08 / 0.11 | 0.07 / 0.11 | **┃** | 0.11 / 0.15 | 0.11 / 0.15 | 0.11 / 0.14 | 0.11 / 0.15 | 0.11 / 0.15 |
| redis-cart | 0.05 / 0.08 | 0.05 / 0.08 | 0.05 / 0.08 | 0.05 / 0.08 | **┃** | 0.06 / 0.08 | 0.06 / 0.08 | 0.06 / 0.08 | 0.06 / 0.08 | 0.06 / 0.08 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).


| Service | s1_normal_rgtf0_rep1 | s1_normal_rgtf0_rep2 | s1_burst20_rgtf0_rep1 | s1_burst20_rgtf0_rep2 | **┃** | s2_normal_rgtf0 | s2_normal_rgtf1 | s2_normal_tf1rg0 | s2_burst20_rgtf0 | s2_burst20_rgtf1 |
| --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |
| frontend | 0.311 | 0.307 | 0.346 | 0.312 | **┃** | 0.375 | 0.387 | 0.375 | 0.367 | 0.365 |
| checkoutservice | 0.609 | 0.634 | 0.619 | 0.620 | **┃** | 1.051 | 1.039 | 1.052 | 1.054 | 1.058 |
| recommendationservice | 0.495 | 0.477 | 0.505 | 0.502 | **┃** | 0.744 | 0.750 | 0.710 | 1.009 | 0.765 |
| paymentservice | 0.329 | 0.381 | 0.458 | 0.348 | **┃** | 0.903 | 0.755 | 0.955 | 0.697 | 0.626 |
| emailservice | 0.625 | 0.650 | 0.642 | 0.642 | **┃** | 1.058 | 1.033 | 1.050 | 1.075 | 1.058 |
| productcatalogservice | 0.640 | 0.618 | 0.723 | 0.664 | **┃** | 0.694 | 0.724 | 0.709 | 0.682 | 0.700 |
| cartservice | 0.494 | 0.501 | 0.524 | 0.630 | **┃** | 0.644 | 0.657 | 0.516 | 0.686 | 0.632 |
| currencyservice | 0.445 | 0.456 | 0.503 | 0.473 | **┃** | 0.597 | 0.605 | 0.583 | 0.744 | 0.600 |
| shippingservice | 0.130 | 0.129 | 0.142 | 0.135 | **┃** | 0.179 | 0.183 | 0.173 | 0.182 | 0.177 |
| adservice | 0.147 | 0.133 | 0.130 | 0.152 | **┃** | 0.242 | 0.196 | 0.170 | 0.163 | 0.180 |
| redis-cart | 0.081 | 0.083 | 0.094 | 0.093 | **┃** | 0.100 | 0.102 | 0.094 | 0.109 | 0.100 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. `postcart` and `emptycart` are no cap on every scored hold. The two TopFull-on S2 holds move `postcheckout` only. The other five scored holds are no cap on every API.


A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### s1_normal_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:44:20–10:51:05 |
| postcheckout | no cap 10:44:20–10:51:05 |
| getcart | no cap 10:44:20–10:51:05 |
| postcart | no cap 10:44:20–10:51:05 |
| emptycart | no cap 10:44:20–10:51:05 |

### s1_normal_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 10:56:30–11:03:20 |
| postcheckout | no cap 10:56:30–11:03:20 |
| getcart | no cap 10:56:30–11:03:20 |
| postcart | no cap 10:56:30–11:03:20 |
| emptycart | no cap 10:56:30–11:03:20 |

### s1_burst20_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:43:25–12:50:15 |
| postcheckout | no cap 12:43:25–12:50:15 |
| getcart | no cap 12:43:25–12:50:15 |
| postcart | no cap 12:43:25–12:50:15 |
| emptycart | no cap 12:43:25–12:50:15 |

### s1_burst20_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 12:55:35–13:02:25 |
| postcheckout | no cap 12:55:35–13:02:25 |
| getcart | no cap 12:55:35–13:02:25 |
| postcart | no cap 12:55:35–13:02:25 |
| emptycart | no cap 12:55:35–13:02:25 |

### s2_normal_rgtf0

| API | Live caps |
| --- | --- |
| getproduct | no cap 13:56:40–14:08:25 |
| postcheckout | no cap 13:56:40–14:08:25 |
| getcart | no cap 13:56:40–14:08:25 |
| postcart | no cap 13:56:40–14:08:25 |
| emptycart | no cap 13:56:40–14:08:25 |

### s2_normal_rgtf1

| API | Live caps |
| --- | --- |
| getproduct | no cap 14:13:50–14:25:40 |
| postcheckout | no cap 14:13:50–14:15:55; 52 at 14:16:00; 59 at 14:16:05; 75.4 at 14:16:10; 77 at 14:16:12; 79 at 14:16:15; 11.9 at 14:16:20; 10 at 14:16:21; 19.6 at 14:16:25; 63.7 at 14:16:30; 90.7806 at 14:16:32; no cap at 14:16:35; 27.1 at 14:16:40; 10.2314 at 14:16:42; 10 at 14:16:45; 19.5825 at 14:16:46; 36.4 at 14:16:50; 81.5896 at 14:16:54; 81.6 at 14:16:55; 87.3604 at 14:16:58; 82.8 at 14:17:00; 25.6 at 14:17:05; 14.0617 at 14:17:09; 14.1 at 14:17:10; 35.4603 at 14:17:13; 47.3 at 14:17:15; 78.9671 at 14:17:17; 87.5 at 14:17:20; 43.4166 at 14:17:24; 43.4 at 14:17:25; 10.1132 at 14:17:28; 10 at 14:17:30; 19.6586 at 14:17:32; 26.8 at 14:17:35; 71.3 at 14:17:40; no cap at 14:17:45; 21.1 at 14:17:50; 10 at 14:17:55; 35.5 at 14:18:00; 85.1 at 14:18:05; no cap at 14:18:10; 16.2 at 14:18:15; 19.4 at 14:18:20; 26.6764 at 14:18:21; 45.6 at 14:18:25; 91.9 at 14:18:30; 97.4199 at 14:18:31; 86 at 14:18:35; 20.8 at 14:18:40; 14.9316 at 14:18:44; 14.9 at 14:18:45; 50.5 at 14:18:50; 79 at 14:18:55; 64.8 at 14:19:00; 24.8732 at 14:19:02; 15.4 at 14:19:05; 10 at 14:19:06; 18.9 at 14:19:10; 63.6 at 14:19:15; 89.3 at 14:19:20; 15.3182 at 14:19:24; 15.3 at 14:19:25; 19.3 at 14:19:30; 47.8 at 14:19:35; 85.6 at 14:19:40; 39.9426 at 14:19:42; 24.5 at 14:19:45; 10 at 14:19:48; 14 at 14:19:50; 36.1 at 14:19:55; 80.6315 at 14:19:59; 80.6 at 14:20:00; no cap at 14:20:05; 27.3993 at 14:20:08; 17.2 at 14:20:10; 14.1 at 14:20:15; 43.7 at 14:20:20; 86.6307 at 14:20:23; 84.2 at 14:20:25; no cap at 14:20:27; 56.0607 at 14:20:29; 56.1 at 14:20:30; 10 at 14:20:35; 19.5 at 14:20:40; 64.111 at 14:20:44; 64.1 at 14:20:45; 65.6 at 14:20:50; 16.1 at 14:20:55; 19.2 at 14:21:00; 48.9 at 14:21:05; 85.6972 at 14:21:06; 99 at 14:21:10; 46.1 at 14:21:15; 10 at 14:21:20; 37.2 at 14:21:25; 66.74 at 14:21:27; 88 at 14:21:30; no cap at 14:21:31; 90 at 14:21:35; 55.1341 at 14:21:36; 21.2 at 14:21:40; 15.6 at 14:21:45; 53.1 at 14:21:50; 88.1 at 14:21:55; 15.3 at 14:22:00; 19.7 at 14:22:05; 49.8 at 14:22:10; 73.8 at 14:22:15; 99 at 14:22:20; 31.2997 at 14:22:24; 31.3 at 14:22:25; 10 at 14:22:28; 14.2 at 14:22:30; 36.3 at 14:22:35; 82 at 14:22:40; 91.2059 at 14:22:43; 74.6 at 14:22:45; 18.2 at 14:22:50; 19.6449 at 14:22:54; 19.6 at 14:22:55; 49.5628 at 14:22:58; 61.6 at 14:23:00; 82.5 at 14:23:05; 15.7 at 14:23:10; 19.6 at 14:23:15; 49.9 at 14:23:20; no cap at 14:23:25; 52.2441 at 14:23:27; 20.5 at 14:23:30; 12.7904 at 14:23:31; 14.2 at 14:23:35; 35.657 at 14:23:38; 49 at 14:23:40; 99 at 14:23:45; 90 at 14:23:48; no cap at 14:23:50; 18 at 14:23:55; 19.6 at 14:24:00; 27.2384 at 14:24:01; 49.4 at 14:24:05; no cap 14:24:09–14:24:10; 19.4 at 14:24:15; 10 at 14:24:20; 37.2 at 14:24:25; 88.6 at 14:24:30; 71.5 at 14:24:35; 11.1 at 14:24:40; 14.0184 at 14:24:42; 19.5 at 14:24:45; 66.7 at 14:24:50; no cap at 14:24:55; 19.7 at 14:25:00; 10 at 14:25:02; 14.2 at 14:25:05; 50 at 14:25:10; 69 at 14:25:15; 20.6 at 14:25:20; 14.1276 at 14:25:24; 14.1 at 14:25:25; 36.7872 at 14:25:28; 48.6 at 14:25:30; 93.7 at 14:25:35; 18.4701 at 14:25:39; 18.5 at 14:25:40 |
| getcart | no cap 14:13:50–14:25:40 |
| postcart | no cap 14:13:50–14:25:40 |
| emptycart | no cap 14:13:50–14:25:40 |

### s2_normal_tf1rg0

| API | Live caps |
| --- | --- |
| getproduct | no cap 14:31:05–14:42:30 |
| postcheckout | no cap 14:31:05–14:32:40; 44 at 14:32:45; 58.3 at 14:32:50; no cap at 14:32:51; 70.4 at 14:32:55; 75.9 at 14:32:58; no cap 14:33:00–14:33:10; 21 at 14:33:15; 14.1688 at 14:33:18; 19.7 at 14:33:20; 50.6 at 14:33:25; 97.9 at 14:33:30; 18.2 at 14:33:35; 14.1 at 14:33:40; 49.9495 at 14:33:44; 49.9 at 14:33:45; 96.5 at 14:33:50; 90 at 14:33:55; 21.7 at 14:34:00; 19.6 at 14:34:05; 66.4 at 14:34:10; 86.7 at 14:34:15; 14.3883 at 14:34:19; 14.4 at 14:34:20; 14.0723 at 14:34:23; 19.7 at 14:34:25; 50.4 at 14:34:30; 99 at 14:34:35; 14.9 at 14:34:40; 14.1291 at 14:34:42; 19.8 at 14:34:45; 65.3 at 14:34:50; no cap at 14:34:55; 17.6 at 14:35:00; 19.6 at 14:35:05; 49.7 at 14:35:10; 70.2 at 14:35:15; 10.1 at 14:35:20; 19.6 at 14:35:25; 62.8492 at 14:35:29; 62.8 at 14:35:30; no cap at 14:35:35; 18.3 at 14:35:40; 11.26 at 14:35:41; 14.2 at 14:35:45; 49.6 at 14:35:50; 70.1 at 14:35:55; 71.0847 at 14:35:56; 28.9 at 14:36:00; 14.2 at 14:36:05; 27.3692 at 14:36:07; 49 at 14:36:10; 66.7009 at 14:36:11; 77 at 14:36:15; 67.7 at 14:36:20; 10 at 14:36:25; 19.7 at 14:36:30; 64.9 at 14:36:35; no cap at 14:36:40; 26.9076 at 14:36:43; 16.7 at 14:36:45; 10 at 14:36:47; 14.2 at 14:36:50; 49.1333 at 14:36:54; 49.1 at 14:36:55; 84.3 at 14:37:00; 78.2036 at 14:37:01; 31 at 14:37:05; 14.2 at 14:37:10; 37.1 at 14:37:15; 91.4 at 14:37:20; 99 at 14:37:23; no cap at 14:37:25; 21.4 at 14:37:30; 19.6 at 14:37:35; 50.1 at 14:37:40; 78.5 at 14:37:45; 13.4 at 14:37:50; 19.6 at 14:37:55; 50.7 at 14:38:00; 67.2 at 14:38:05; 10.1 at 14:38:10; 10.6701 at 14:38:11; 20.7 at 14:38:15; 68.3 at 14:38:20; 96.3 at 14:38:25; 15.2 at 14:38:30; 10 at 14:38:32; 14.2 at 14:38:35; 49.9 at 14:38:40; 69 at 14:38:45; 10.7 at 14:38:50; 19.8 at 14:38:55; 62.9 at 14:39:00; 67 at 14:39:05; 15.9 at 14:39:10; 14.142 at 14:39:13; 19.6 at 14:39:15; 49.1 at 14:39:20; 69 at 14:39:25; 16.7 at 14:39:30; 19.4 at 14:39:35; 48.6002 at 14:39:38; 63.5 at 14:39:40; 96.1 at 14:39:45; 15.0567 at 14:39:49; 15.1 at 14:39:50; 14.1299 at 14:39:53; 19.6 at 14:39:55; 49.4 at 14:40:00; 79.3 at 14:40:05; 22.6 at 14:40:10; 13.9973 at 14:40:11; 10 at 14:40:15; 37.4 at 14:40:20; 81.7 at 14:40:25; 99 at 14:40:26; 90 at 14:40:30; 18.7 at 14:40:35; 11.6776 at 14:40:36; 14.1 at 14:40:40; 37.8 at 14:40:45; 68.3713 at 14:40:46; 82.3 at 14:40:50; 90 at 14:40:53; no cap at 14:40:55; 19.1 at 14:41:00; 10 at 14:41:02; 19.8 at 14:41:05; 27.2964 at 14:41:06; 49.9 at 14:41:10; 81.9298 at 14:41:14; 81.9 at 14:41:15; 12.8 at 14:41:20; 19.7 at 14:41:25; 64.5 at 14:41:30; no cap at 14:41:35; 28.9 at 14:41:40; 11.1776 at 14:41:41; 14.2 at 14:41:45; 50.7 at 14:41:50; 65.5 at 14:41:55; 40.4659 at 14:41:56; 15.3 at 14:42:00; 19.5057 at 14:42:04; 19.5 at 14:42:05; 48.7695 at 14:42:08; 62.3 at 14:42:10; 91.8749 at 14:42:12; 90.3 at 14:42:15; 24.6 at 14:42:20; 14.1 at 14:42:25; 36.7 at 14:42:30 |
| getcart | no cap 14:31:05–14:42:30 |
| postcart | no cap 14:31:05–14:42:30 |
| emptycart | no cap 14:31:05–14:42:30 |

### s2_burst20_rgtf0

| API | Live caps |
| --- | --- |
| getproduct | no cap 14:47:30–14:59:20 |
| postcheckout | no cap 14:47:30–14:59:20 |
| getcart | no cap 14:47:30–14:59:20 |
| postcart | no cap 14:47:30–14:59:20 |
| emptycart | no cap 14:47:30–14:59:20 |

### s2_burst20_rgtf1

| API | Live caps |
| --- | --- |
| getproduct | no cap 15:04:45–15:16:30 |
| postcheckout | no cap 15:04:45–15:06:45; 49.5 at 15:06:50; 59.4 at 15:06:53; no cap 15:06:55–15:07:00; 74 at 15:07:05; no cap at 15:07:07; 81 at 15:07:10; 98.5 at 15:07:15; 90 15:07:17–15:07:20; 14 at 15:07:25; 19.6 at 15:07:30; 57.7073 at 15:07:34; 57.7 at 15:07:35; no cap at 15:07:38; 90 at 15:07:40; no cap at 15:07:43; 90 15:07:44–15:07:50; no cap at 15:07:55; 22.2 at 15:08:00; 34.8 at 15:08:05; 95.5 at 15:08:10; 88.434 at 15:08:14; 88.4 at 15:08:15; 96.319 at 15:08:18; no cap 15:08:20–15:08:23; 90 at 15:08:25; 16.6 at 15:08:30; 32.2 at 15:08:35; 82.046 at 15:08:39; 82 at 15:08:40; 90 15:08:45–15:08:50; no cap 15:08:54–15:08:55; 64.41 at 15:08:56; 26.6 at 15:09:00; 49.2959 at 15:09:04; 49.3 at 15:09:05; 98.7728 at 15:09:08; no cap at 15:09:10; 90 at 15:09:11; 81.9 at 15:09:15; 77.2 at 15:09:20; 97.9313 at 15:09:22; no cap at 15:09:25; 93.4 at 15:09:30; 90 at 15:09:35; 91 at 15:09:40; 49.9378 at 15:09:44; 49.9 at 15:09:45; 28.6371 at 15:09:48; 39.5 at 15:09:50; 68.6229 at 15:09:52; 78.6 at 15:09:55; 90.3841 at 15:09:56; 77.4 at 15:10:00; 93.0327 at 15:10:03; 93.2 at 15:10:05; 77.8 at 15:10:10; 89.2 at 15:10:15; 90.9 at 15:10:20; no cap at 15:10:25; 38.1 at 15:10:30; 29.7 at 15:10:35; 61.5 at 15:10:40; 90 at 15:10:45; 83.8 at 15:10:50; no cap at 15:10:55; 88 at 15:11:00; 22.9 at 15:11:05; 40.7 at 15:11:10; 84.9 at 15:11:15; 82.6 at 15:11:20; 86.8 at 15:11:25; 87.1671 at 15:11:29; 87.2 at 15:11:30; 17.9 at 15:11:35; 18.8433 at 15:11:36; 36.4 at 15:11:40; 83.2 at 15:11:45; no cap 15:11:49–15:11:50; 97.3 at 15:11:55; 84.5 at 15:12:00; 43.3727 at 15:12:02; 27.7 at 15:12:05; 43.4 at 15:12:10; 88.7 at 15:12:15; 90 at 15:12:20; no cap at 15:12:25; 87.7 at 15:12:30; 16.6 at 15:12:35; 30.1389 at 15:12:37; 54.5 at 15:12:40; 93.6 at 15:12:45; 94.2878 at 15:12:48; 82.6 at 15:12:50; 99 at 15:12:55; 73.8029 at 15:12:59; 73.8 at 15:13:00; no cap at 15:13:05; 95.4847 at 15:13:08; 82.8 at 15:13:10; 88.5 at 15:13:15; 92.8902 at 15:13:19; 92.9 at 15:13:20; 91.2509 at 15:13:23; 85.5 at 15:13:25; 72.3322 at 15:13:27; 71 at 15:13:30; 83.4 at 15:13:35; 81.7386 at 15:13:38; 80.4 at 15:13:40; 79.7 at 15:13:45; 75.6 at 15:13:50; 18.2 at 15:13:55; 35.7 at 15:14:00; 84.0626 at 15:14:03; 91.2 at 15:14:05; 84.0671 at 15:14:07; 93.4 at 15:14:10; 90 at 15:14:15; 75.4 at 15:14:20; 77.2521 at 15:14:21; 99 at 15:14:25; no cap at 15:14:28; 90 at 15:14:30; 78.9 at 15:14:35; 75.1717 at 15:14:37; 76.2 at 15:14:40; 97.6346 at 15:14:44; 97.6 at 15:14:45; 87.7 at 15:14:50; 86.2 at 15:14:55; 88 at 15:15:00; 15.9 at 15:15:05; 38.1 at 15:15:10; 84.8 at 15:15:15; 87.4 at 15:15:20; 90 at 15:15:25; 78.1 at 15:15:30; 48.2 at 15:15:35; 51.9 at 15:15:40; no cap at 15:15:45; 90 at 15:15:50; 77.9 at 15:15:55; 87.4 at 15:16:00; 87.9394 at 15:16:01; 72.6 at 15:16:05; 27.1 at 15:16:10; 46.1435 at 15:16:12; 63.3 at 15:16:15; 71.8928 at 15:16:16; 80.1 at 15:16:20; 85.4 at 15:16:25; 84.2 at 15:16:30 |
| getcart | no cap 15:04:45–15:16:30 |
| postcart | no cap 15:04:45–15:16:30 |
| emptycart | no cap 15:04:45–15:16:30 |

## 20. Per hold

`s1_normal_rgtf0_rep1` and `s1_normal_rgtf0_rep2` are normal mode, RetryGuard on, TopFull off. Nothing shed. Retry delta is 0. `grpc_4` is 0. No service is detector-hot. Locust fail rate is 0. Mean goodput is about 161 / 28 / 64 / 83 / 5.

`s1_burst20_rgtf0_rep1` and `s1_burst20_rgtf0_rep2` are burst 2.0, RetryGuard on, TopFull off. Burst windows were sampled and none crossed the bar. Nothing shed. Retry delta is 0. `grpc_4` is 0. No service is detector-hot. Locust fail rate is 0.

`s2_normal_rgtf0` is normal mode, RetryGuard on, TopFull off. Checkout shed three times (rpr 3.16, 0.94, 0.83), re-enabled twice to 1 attempt, and ended at 0. Recommendations did not shed. Retry delta into checkout is 5,694. `grpc_4` is 0. Checkout is detector-hot (82.6%) and email is detector-hot (69.8%). postcheckout goodput is 60.0 and fail rate is 0.293.

`s2_normal_rgtf1` is normal mode, both on. Nothing shed. Retry delta into checkout is 18,888. `grpc_4` is 0. Checkout is detector-hot (52.7%). Email is 17.1%. postcheckout goodput is 29.8 and fail rate is 0.594. Live caps are on postcheckout only.

`s2_normal_tf1rg0` is normal mode, RetryGuard off, TopFull on. There is no `retryguard.log`. Retry delta into checkout is 18,763. `grpc_4` is 0. Checkout is detector-hot (53.3%). Email is 12.3%. postcheckout goodput is 28.1 and fail rate is 0.610. Live caps are on postcheckout only.

`s2_burst20_rgtf0` is burst 2.0, RetryGuard on, TopFull off. Checkout shed ten times, all burst, and ended at 0. Recommendations shed once (aggregate 2.74) and climbed back to 3. Retry delta is 4,607 into checkout and 4,735 into recommendations. recommendations `grpc_4` is 5,330. Checkout is detector-hot (81.4%) and email is detector-hot (69.7%). postcheckout goodput is 63.8 and fail rate is 0.248.

`s2_burst20_rgtf1` is burst 2.0, both on. Checkout shed fourteen times, all burst, and each re-enable stopped at 1 attempt. The edge was at 1 at exit. Recommendations did not shed. Retry delta into checkout is 5,042. `grpc_4` is 0. Checkout is detector-hot (70.4%) and email is detector-hot (52.5%). postcheckout goodput is 54.4 and fail rate is 0.340. Live caps are on postcheckout only.

## 21. Related links

[ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). (a)/(b)/(c): [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). Edge mode and burst mode: [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md). [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md). Previous S2 burst matrix: [2026-10-12-s2-burst-matrix-abc.md](2026-10-12-s2-burst-matrix-abc.md). Offline first-fire times: [2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md).
