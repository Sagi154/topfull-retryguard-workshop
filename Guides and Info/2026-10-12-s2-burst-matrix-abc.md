# S2 burst matrix (2026-10-12): normal, bar 1.5, bar 2.0

Twelve locked-S2 holds. RetryGuard is on for every hold. Four holds are normal mode. Eight holds set `burst_rpr` to 1.5 or 2.0, two replicates each, TopFull off and TopFull on. Scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Run log: [2026-10-12-s2-burst-matrix-run-log.md](../docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md).

## 1. Setup

- **Duration** 600 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. Locked S2 mix, Paper-C1.
- **CPU and replica pin** (`service_capacity.json` on all twelve holds):

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

  Frontend replica count is 4 on every `resource_usage.csv` sample, and every other service is 1. That is the Paper-C1 pin: sidecar `proxyCPU=90m` with `proxyCPULimit` unset while frontend is held at 4, and catalog HPA max 1.
- **Controllers.** RetryGuard is on for every hold. TopFull is off on each `rgtf0` folder and on on each `rgtf1` folder.
- **RetryGuard knobs.** `retry_metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.4`, climb `0.16/0.32` with `climb_interval_seconds=10`, `reenable_rejection=0.25`. Normal-mode holds omit `burst_rpr`. Burst holds add `burst_window_seconds=5` and `burst_min_first_attempts=20`, with `burst_rpr` 1.5 or 2.0.
- **Cool-off** 120 s between holds, from `run_scenario.py` exit.
- **Folders:** `experiments/results/campaign_48/S2_sustained_overload/`, the twelve `study6_s2_*` names in §2. Configs: `experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml` through `14_s2_burst20_rgtf1_rep2.yaml`. Each manifest has `run_number` 1; the `log_folder` name is the slot.

## 2. Index

Column order in every table below follows this index. A bold bar (**┃**) follows every pair: normal off, normal on, burst 1.5 off, burst 2.0 off, burst 1.5 on, burst 2.0 on.

| # | Column | Mode | TopFull |
| ---: | --- | --- | --- |
| 1 | `study6_s2_normal_rgtf0_rep1` | normal | off |
| 2 | `study6_s2_normal_rgtf0_rep2` | normal | off |
| | **┃** | | |
| 3 | `study6_s2_normal_rgtf1_rep1` | normal | on |
| 4 | `study6_s2_normal_rgtf1_rep2` | normal | on |
| | **┃** | | |
| 5 | `study6_s2_burst15_rgtf0_rep1` | burst_rpr 1.5 | off |
| 6 | `study6_s2_burst15_rgtf0_rep2` | burst_rpr 1.5 | off |
| | **┃** | | |
| 7 | `study6_s2_burst20_rgtf0_rep1` | burst_rpr 2.0 | off |
| 8 | `study6_s2_burst20_rgtf0_rep2` | burst_rpr 2.0 | off |
| | **┃** | | |
| 9 | `study6_s2_burst15_rgtf1_rep1` | burst_rpr 1.5 | on |
| 10 | `study6_s2_burst15_rgtf1_rep2` | burst_rpr 1.5 | on |
| | **┃** | | |
| 11 | `study6_s2_burst20_rgtf1_rep1` | burst_rpr 2.0 | on |
| 12 | `study6_s2_burst20_rgtf1_rep2` | burst_rpr 2.0 | on |

## 3. Gate

**Pass on all twelve.** The run log records PASS for each hold. No `_r2` folder replaced a hold.

Scorer gate numbers:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| `study6_s2_normal_rgtf0_rep1` | 564 | 664 | 0 of 7304 | present |
| `study6_s2_normal_rgtf0_rep2` | 565 | 665 | 0 of 7315 | present |
| `study6_s2_normal_rgtf1_rep1` | 560 | 665 | 517 of 6798 | present |
| `study6_s2_normal_rgtf1_rep2` | 561 | 665 | 484 of 6831 | present |
| `study6_s2_burst15_rgtf0_rep1` | 566 | 665 | 0 of 7315 | present |
| `study6_s2_burst15_rgtf0_rep2` | 567 | 664 | 0 of 7304 | present |
| `study6_s2_burst20_rgtf0_rep1` | 567 | 665 | 0 of 7315 | present |
| `study6_s2_burst20_rgtf0_rep2` | 568 | 665 | 0 of 7315 | present |
| `study6_s2_burst15_rgtf1_rep1` | 562 | 665 | 1485 of 5830 | present |
| `study6_s2_burst15_rgtf1_rep2` | 562 | 666 | 2200 of 5126 | present |
| `study6_s2_burst20_rgtf1_rep1` | 563 | 665 | 2178 of 5137 | present |
| `study6_s2_burst20_rgtf1_rep2` | 563 | 665 | 2189 of 5126 | present |

`service_capacity.json` matches the pin in §1 on every hold, for every service. `resource_usage.csv` shows frontend at 4 replicas on every sample (150/150, 149/149, 149/149, 150/150, 150/150, 149/149, 149/149, 149/149, 150/150, 149/149, 150/150, 149/149). No service has a zero-replica sample. The scorer printed no replica-change line.

## 4. Edge-mode bars

The scorer's first line:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

The four normal-mode columns omit `burst_rpr`. Burst mode was off on those holds.

The scorer's `Burst bars` line:

> Burst bars: study6_s2_burst15_rgtf0_rep1 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst15_rgtf0_rep2 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst20_rgtf0_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst20_rgtf0_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst15_rgtf1_rep1 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst15_rgtf1_rep2 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst20_rgtf1_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst20_rgtf1_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

A burst shed goes to 0 attempts and recovers on the normal path. Shed and 0→1 take **20 s** of row timestamps (`interval_samples=20`). Climbs 1→2 and 2→3 take **10 s** on these holds (`climb_interval_seconds=10` on the START line).

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

Two edges have a tick above the shed bar or a retry delta: `frontend → recommendationservice` and `frontend → checkoutservice`. Every other controlled edge has no tick above 0.40 and a retry delta of 0, so it is omitted here. The file streak is in seconds. The parenthetical is the controller's max `high` from `retryguard.log`, a sample count. No file streak reaches 30 s, so nothing in these cells is bold.

### (a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)

| Edge | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | 22 / 23 (21) | 22 / 23 (21) | **┃** | 23 / 164 (21) | 22 / 23 (21) | **┃** | 6 / 7 (4) | 6 / 7 (3) | **┃** | 17 / 18 (15) | 6 / 18 (4) | **┃** | 6 / 31 (4) | 8 / 16 (4) | **┃** | 5 / 6 (2) | 8 / 26 (5) |
| frontend → checkoutservice | 13 / 15 (14) | 22 / 23 (21) | **┃** | 6 / 10 (7) | 7 / 8 (8) | **┃** | 6 / 16 (4) | 7 / 30 (4) | **┃** | 6 / 36 (4) | 8 / 26 (5) | **┃** | 7 / 15 (4) | 6 / 9 (3) | **┃** | 6 / 5 (5) | 6 / 6 (3) |

Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.

### (a) Mean / median / max / volume rpr

| Edge | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | 0.119 / 0.000 / 4.94 / 0.056 | 0.081 / 0.000 / 3.25 / 0.048 | **┃** | 0.306 / 0.000 / 3.78 / 0.253 | 0.088 / 0.000 / 3.54 / 0.049 | **┃** | 0.023 / 0.000 / 2.91 / 0.014 | 0.023 / 0.000 / 3.05 / 0.013 | **┃** | 0.053 / 0.000 / 2.53 / 0.034 | 0.065 / 0.000 / 10.14 / 0.032 | **┃** | 0.102 / 0.000 / 3.71 / 0.064 | 0.057 / 0.000 / 2.95 / 0.036 | **┃** | 0.032 / 0.000 / 3.47 / 0.015 | 0.084 / 0.000 / 4.28 / 0.047 |
| frontend → checkoutservice | 0.069 / 0.000 / 10.60 / 0.045 | 0.086 / 0.000 / 3.35 / 0.075 | **┃** | 0.032 / 0.000 / 3.12 / 0.024 | 0.030 / 0.000 / 4.19 / 0.022 | **┃** | 0.051 / 0.000 / 3.50 / 0.043 | 0.102 / 0.000 / 5.39 / 0.075 | **┃** | 0.094 / 0.000 / 5.04 / 0.077 | 0.069 / 0.000 / 3.20 / 0.061 | **┃** | 0.071 / 0.000 / 3.08 / 0.048 | 0.048 / 0.000 / 2.71 / 0.037 | **┃** | 0.023 / 0.000 / 2.54 / 0.024 | 0.033 / 0.000 / 3.18 / 0.023 |

Climb streaks are OBSERVE samples while that attempt cap is in force. An em dash means the edge never ran at that cap.

### (a) Climb streaks, 1-attempt / 2-attempt

| Edge | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend → recommendationservice | — / — | — / — | **┃** | 10 / 9 | — / — | **┃** | — / — | — / — | **┃** | — / — | 2 / — | **┃** | 9 / 8 | 8 / 8 | **┃** | 9 / 8 | 1 / — |
| frontend → checkoutservice | — / — | 11 / 11 | **┃** | — / — | — / — | **┃** | 11 / 11 | 11 / 11 | **┃** | 11 / 11 | 11 / 11 | **┃** | 10 / 10 | 9 / 7 | **┃** | 9 / 9 | 7 / 10 |

### 5a. Burst

The four normal-mode columns omit `burst_rpr`. Burst mode was off on those holds, and their burst-window cells are em dashes.

Burst is a second shed test beside (a). It does not change the three tables above.

Burst bars: study6_s2_burst15_rgtf0_rep1 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst15_rgtf0_rep2 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst20_rgtf0_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst20_rgtf0_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst15_rgtf1_rep1 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst15_rgtf1_rep2 burst_rpr 1.50 (bar at 3 / 2 / 1 attempts 1.50 / 1.00 / 0.50); study6_s2_burst20_rgtf1_rep1 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67); study6_s2_burst20_rgtf1_rep2 burst_rpr 2.00 (bar at 3 / 2 / 1 attempts 2.00 / 1.33 / 0.67). Window and volume floor are on the START line.

Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force (burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count in parentheses. Samples exist only while the edge is above 0 attempts and the window meets the volume floor.


### (a2) Burst window

| Edge | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice → paymentservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (596) | 0.00 / 0.00 / 0 / 0 (597) | **┃** | 0.00 / 0.00 / 0 / 0 (602) | 0.00 / 0.00 / 0 / 0 (593) | **┃** | 0.00 / 0.00 / 0 / 0 (470) | 0.00 / 0.00 / 0 / 0 (408) | **┃** | 0.00 / 0.00 / 0 / 0 (408) | 0.00 / 0.00 / 0 / 0 (408) |
| checkoutservice → currencyservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (596) | 0.00 / 0.00 / 0 / 0 (597) | **┃** | 0.00 / 0.00 / 0 / 0 (602) | 0.00 / 0.00 / 0 / 0 (593) | **┃** | 0.00 / 0.00 / 0 / 0 (470) | 0.00 / 0.00 / 0 / 0 (408) | **┃** | 0.00 / 0.00 / 0 / 0 (408) | 0.00 / 0.00 / 0 / 0 (408) |
| frontend → recommendationservice | — | — | **┃** | — | — | **┃** | 2.00 / 0.00 / 1 / 1 (48) | 2.04 / 0.00 / 1 / 1 (55) | **┃** | 2.18 / 0.00 / 1 / 1 (67) | 2.09 / 0.00 / 3 / 3 (74) | **┃** | 1.97 / 0.00 / 6 / 6 (307) | 2.07 / 0.00 / 3 / 3 (365) | **┃** | 2.09 / 0.00 / 1 / 1 (392) | 2.80 / 0.00 / 4 / 4 (89) |
| frontend → productcatalogservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (601) | **┃** | 0.00 / 0.00 / 0 / 0 (606) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (474) | 0.00 / 0.00 / 0 / 0 (412) | **┃** | 0.00 / 0.00 / 0 / 0 (412) | 0.00 / 0.00 / 0 / 0 (413) |
| checkoutservice → shippingservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (598) | **┃** | 0.00 / 0.00 / 0 / 0 (603) | 0.00 / 0.00 / 0 / 0 (594) | **┃** | 0.00 / 0.00 / 0 / 0 (471) | 0.00 / 0.00 / 0 / 0 (409) | **┃** | 0.00 / 0.00 / 0 / 0 (409) | 0.00 / 0.00 / 0 / 0 (410) |
| checkoutservice → cartservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (598) | **┃** | 0.00 / 0.00 / 0 / 0 (603) | 0.00 / 0.00 / 0 / 0 (594) | **┃** | 0.00 / 0.00 / 0 / 0 (471) | 0.00 / 0.00 / 0 / 0 (409) | **┃** | 0.00 / 0.00 / 0 / 0 (409) | 0.00 / 0.00 / 0 / 0 (410) |
| frontend → checkoutservice | — | — | **┃** | — | — | **┃** | 2.18 / 0.00 / 2 / 2 (545) | 2.15 / 0.00 / 4 / 4 (478) | **┃** | 2.44 / 0.00 / 5 / 5 (455) | 2.44 / 0.00 / 3 / 3 (497) | **┃** | 1.84 / 0.00 / 2 / 2 (433) | 2.15 / 0.00 / 2 / 2 (368) | **┃** | 2.03 / 0.00 / 1 / 1 (396) | 2.21 / 0.00 / 1 / 1 (392) |
| frontend → currencyservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (599) | 0.00 / 0.00 / 0 / 0 (601) | **┃** | 0.00 / 0.00 / 0 / 0 (606) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (474) | 0.00 / 0.00 / 0 / 0 (412) | **┃** | 0.00 / 0.00 / 0 / 0 (412) | 0.00 / 0.00 / 0 / 0 (412) |
| checkoutservice → emailservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (593) | 0.00 / 0.00 / 0 / 0 (590) | **┃** | 0.00 / 0.00 / 0 / 0 (601) | 0.00 / 0.00 / 0 / 0 (586) | **┃** | 0.00 / 0.00 / 0 / 0 (464) | 0.00 / 0.00 / 0 / 0 (406) | **┃** | 0.00 / 0.00 / 0 / 0 (408) | 0.00 / 0.00 / 0 / 0 (408) |
| frontend → shippingservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (599) | **┃** | 0.00 / 0.00 / 0 / 0 (604) | 0.00 / 0.00 / 0 / 0 (594) | **┃** | 0.00 / 0.00 / 0 / 0 (472) | 0.00 / 0.00 / 0 / 0 (410) | **┃** | 0.00 / 0.00 / 0 / 0 (410) | 0.00 / 0.00 / 0 / 0 (410) |
| frontend → cartservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (605) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (473) | 0.00 / 0.00 / 0 / 0 (411) | **┃** | 0.00 / 0.00 / 0 / 0 (411) | 0.00 / 0.00 / 0 / 0 (412) |
| recommendationservice → productcatalogservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (598) | 0.00 / 0.00 / 0 / 0 (600) | **┃** | 0.00 / 0.00 / 0 / 0 (605) | 0.00 / 0.00 / 0 / 0 (599) | **┃** | 0.00 / 0.00 / 0 / 0 (473) | 0.00 / 0.00 / 0 / 0 (411) | **┃** | 0.00 / 0.00 / 0 / 0 (411) | 0.00 / 0.00 / 0 / 0 (411) |
| frontend → adservice | — | — | **┃** | — | — | **┃** | 0.00 / 0.00 / 0 / 0 (597) | 0.00 / 0.00 / 0 / 0 (599) | **┃** | 0.00 / 0.00 / 0 / 0 (604) | 0.00 / 0.00 / 0 / 0 (595) | **┃** | 0.00 / 0.00 / 0 / 0 (472) | 0.00 / 0.00 / 0 / 0 (410) | **┃** | 0.00 / 0.00 / 0 / 0 (410) | 0.00 / 0.00 / 0 / 0 (411) |

`frontend → cartservice` has a full `burst_rpr5` sample count on every burst hold (598, 600, 605, 600, 473, 411, 411, 412) and a peak of 0.00, so the volume floor does not drop it and the shed count is 0. Every other edge in that table, aside from `frontend → checkoutservice` and `frontend → recommendationservice`, has peak 0.00, 0 samples at the bar, and 0 burst sheds.

**Burst vs normal sheds.** In the §9 count table, `ON→OFF burst` is the part of `ON→OFF` fired by the burst test. Normal sheds are the difference. On every burst hold that difference is 0 for both `frontend → checkoutservice` and `frontend → recommendationservice`: every shed is `metric=rpr_burst`. On a burst row of the timestamp table, `Value` is the 5 s aggregate `ΣΔretry / ΣΔfirst`, and the log's `elapsed_s` is the window span. On these holds that span is 2, 3, 4 s.

**Replay check.** The four TopFull-on burst holds:

On `study6_s2_burst15_rgtf1_rep1`, the first `metric=rpr_burst` line is **49 s** after the first OBSERVE line (2026-10-12T03:04:34Z to 2026-10-12T03:05:23Z), on `frontend → checkoutservice`, against the replay's 104–113 s first-fire window at bars 1.0 / 1.5 / 2.0 ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)). Later replay fire counts assume instant recovery. Those later counts are not a live forecast.

On `study6_s2_burst15_rgtf1_rep2`, the first `metric=rpr_burst` line is **47 s** after the first OBSERVE line (2026-10-12T03:22:11Z to 2026-10-12T03:22:58Z), on `frontend → checkoutservice`, against the replay's 104–113 s first-fire window at bars 1.0 / 1.5 / 2.0 ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)). Later replay fire counts assume instant recovery. Those later counts are not a live forecast.

On `study6_s2_burst20_rgtf1_rep1`, the first `metric=rpr_burst` line is **53 s** after the first OBSERVE line (2026-10-12T03:39:49Z to 2026-10-12T03:40:42Z), on `frontend → checkoutservice`, against the replay's 104–113 s first-fire window at bars 1.0 / 1.5 / 2.0 ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)). Later replay fire counts assume instant recovery. Those later counts are not a live forecast.

On `study6_s2_burst20_rgtf1_rep2`, the first `metric=rpr_burst` line is **48 s** after the first OBSERVE line (2026-10-12T03:57:25Z to 2026-10-12T03:58:13Z), on `frontend → checkoutservice`, against the replay's 104–113 s first-fire window at bars 1.0 / 1.5 / 2.0 ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)). Later replay fire counts assume instant recovery. Those later counts are not a live forecast.

The four TopFull-off burst holds have no replay. The four normal-mode holds are the no-burst comparison in this session.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count. **Bold** in the 0.20 table would be a streak of at least 30 on a controlled service. No controlled service reaches 30, so nothing in that table is bold. Frontend and redis-cart stay plain. The re-enable bar on these holds is 0.25.

### (a) context: rejection streak above 0.20 / count. Not the shed signal

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 126 / 545 | 65 / 499 | **┃** | 23 / 179 | 27 / 379 | **┃** | 119 / 525 | 34 / 378 | **┃** | 31 / 373 | 27 / 297 | **┃** | 8 / 53 | 6 / 14 | **┃** | 6 / 7 | 10 / 120 |
| checkoutservice | 14 / 15 | 25 / 25 | **┃** | 6 / 8 | 7 / 7 | **┃** | 10 / 18 | 10 / 40 | **┃** | 10 / 49 | 9 / 32 | **┃** | 8 / 16 | 4 / 10 | **┃** | 5 / 5 | 5 / 6 |
| recommendationservice | 3 / 75 | 2 / 16 | **┃** | 21 / 111 | 2 / 29 | **┃** | 4 / 65 | 2 / 32 | **┃** | 2 / 17 | 6 / 20 | **┃** | 2 / 11 | 1 / 1 | **┃** | 0 / 0 | 6 / 22 |
| paymentservice | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 1 / 2 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| emailservice | 3 / 7 | 2 / 9 | **┃** | 3 / 6 | 2 / 3 | **┃** | 4 / 15 | 6 / 27 | **┃** | 7 / 28 | 3 / 18 | **┃** | 2 / 10 | 3 / 10 | **┃** | 2 / 3 | 2 / 4 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 1 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

### (a) context: rejection streak under the re-enable bar / count

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend (not controlled) | 51 / 106 | 69 / 180 | **┃** | 68 / 405 | 66 / 285 | **┃** | 54 / 137 | 56 / 338 | **┃** | 55 / 343 | 58 / 436 | **┃** | 177 / 438 | 277 / 401 | **┃** | 346 / 409 | 69 / 341 |
| checkoutservice | 520 / 580 | 547 / 587 | **┃** | 340 / 557 | 519 / 560 | **┃** | 334 / 593 | 332 / 575 | **┃** | 265 / 563 | 324 / 581 | **┃** | 264 / 462 | 300 / 403 | **┃** | 367 / 409 | 367 / 407 |
| recommendationservice | 150 / 592 | 564 / 610 | **┃** | 246 / 515 | 216 / 559 | **┃** | 243 / 601 | 248 / 608 | **┃** | 313 / 609 | 277 / 606 | **┃** | 477 / 477 | 413 / 413 | **┃** | 415 / 415 | 168 / 402 |
| paymentservice | 541 / 595 | 562 / 611 | **┃** | 565 / 565 | 567 / 567 | **┃** | 612 / 612 | 612 / 612 | **┃** | 612 / 612 | 553 / 611 | **┃** | 477 / 477 | 412 / 412 | **┃** | 414 / 414 | 412 / 412 |
| emailservice | 520 / 585 | 545 / 597 | **┃** | 340 / 559 | 521 / 563 | **┃** | 283 / 596 | 284 / 585 | **┃** | 269 / 584 | 324 / 595 | **┃** | 265 / 465 | 168 / 403 | **┃** | 368 / 411 | 227 / 408 |
| productcatalogservice | 614 / 614 | 613 / 613 | **┃** | 566 / 566 | 568 / 568 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 478 / 478 | 413 / 413 | **┃** | 415 / 415 | 414 / 414 |
| cartservice | 613 / 613 | 613 / 613 | **┃** | 566 / 566 | 568 / 568 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 478 / 478 | 413 / 413 | **┃** | 415 / 415 | 414 / 414 |
| currencyservice | 613 / 613 | 612 / 612 | **┃** | 566 / 566 | 569 / 569 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 478 / 478 | 413 / 413 | **┃** | 415 / 415 | 414 / 414 |
| shippingservice | 541 / 599 | 612 / 612 | **┃** | 566 / 566 | 569 / 569 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 553 / 612 | **┃** | 478 / 478 | 413 / 413 | **┃** | 415 / 415 | 413 / 413 |
| adservice | 541 / 598 | 612 / 612 | **┃** | 565 / 565 | 568 / 568 | **┃** | 612 / 612 | 612 / 612 | **┃** | 612 / 612 | 552 / 610 | **┃** | 477 / 477 | 412 / 412 | **┃** | 414 / 414 | 413 / 413 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

gRPC counted in the rejection rate and in the retry policy. Cell is grpc_4 / grpc_14.

### grpc_4 / grpc_14

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| recommendationservice | 95,926 / 0 | 75,869 / 0 | **┃** | 75,743 / 0 | 61,998 / 0 | **┃** | 74,662 / 0 | 47,089 / 0 | **┃** | 52,018 / 0 | 48,422 / 0 | **┃** | 23,881 / 0 | 9,316 / 0 | **┃** | 4,019 / 0 | 40,571 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 1 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

### (b) Detector overloaded fraction

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| checkoutservice | 330/715 (46.2%) | **532/715 (74.4%)** | **┃** | **400/716 (55.9%)** | **484/717 (67.5%)** | **┃** | **519/716 (72.5%)** | **576/714 (80.7%)** | **┃** | **542/715 (75.8%)** | **532/714 (74.5%)** | **┃** | **545/717 (76.0%)** | **537/716 (75.0%)** | **┃** | **472/717 (65.8%)** | **517/716 (72.2%)** |
| recommendationservice | **518/715 (72.4%)** | **378/715 (52.9%)** | **┃** | 201/716 (28.1%) | 318/717 (44.4%) | **┃** | **428/716 (59.8%)** | 233/714 (32.6%) | **┃** | 246/715 (34.4%) | 96/714 (13.4%) | **┃** | 63/717 (8.8%) | 24/716 (3.4%) | **┃** | 6/717 (0.8%) | 174/716 (24.3%) |
| paymentservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| emailservice | 159/715 (22.2%) | 272/715 (38.0%) | **┃** | 289/716 (40.4%) | 229/717 (31.9%) | **┃** | 312/716 (43.6%) | **425/714 (59.5%)** | **┃** | **392/715 (54.8%)** | 324/714 (45.4%) | **┃** | **394/717 (55.0%)** | **488/716 (68.2%)** | **┃** | 44/717 (6.1%) | 300/716 (41.9%) |
| productcatalogservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| cartservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| currencyservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| shippingservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| adservice | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |
| redis-cart | 0/715 (0.0%) | 0/715 (0.0%) | **┃** | 0/716 (0.0%) | 0/717 (0.0%) | **┃** | 0/716 (0.0%) | 0/714 (0.0%) | **┃** | 0/715 (0.0%) | 0/714 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) | **┃** | 0/717 (0.0%) | 0/716 (0.0%) |

## 8. (c) Retry volume

### (c) Outbound retry delta by target

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| checkoutservice | 1,163 | 2,352 | **┃** | 696 | 644 | **┃** | 1,365 | 2,747 | **┃** | 2,787 | 2,048 | **┃** | 1,663 | 1,351 | **┃** | 566 | 745 |
| recommendationservice | 14,876 | 12,708 | **┃** | 62,083 | 12,734 | **┃** | 3,702 | 3,550 | **┃** | 9,183 | 8,594 | **┃** | 16,212 | 8,536 | **┃** | 3,557 | 12,135 |

### (c) Inbound resets

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 249 | 244 | **┃** | 194 | 262 | **┃** | 261 | 303 | **┃** | 234 | 213 | **┃** | 274 | 52 | **┃** | 48 | 244 |
| checkoutservice | 818 | 1,743 | **┃** | 405 | 427 | **┃** | 1,073 | 2,330 | **┃** | 2,664 | 1,880 | **┃** | 1,269 | 1,054 | **┃** | 418 | 533 |
| recommendationservice | 40,072 | 31,840 | **┃** | 33,727 | 28,082 | **┃** | 36,607 | 29,612 | **┃** | 26,490 | 26,004 | **┃** | 9,204 | 2,472 | **┃** | 1,002 | 21,241 |
| paymentservice | 61 | 174 | **┃** | 12 | 27 | **┃** | 48 | 116 | **┃** | 65 | 104 | **┃** | 140 | 59 | **┃** | 49 | 17 |
| emailservice | 86 | 185 | **┃** | 241 | 91 | **┃** | 346 | 638 | **┃** | 786 | 529 | **┃** | 335 | 306 | **┃** | 103 | 228 |
| productcatalogservice | 4 | 2 | **┃** | 7 | 9 | **┃** | 3 | 6 | **┃** | 1 | 4 | **┃** | 6 | 4 | **┃** | 7 | 7 |
| cartservice | 63 | 103 | **┃** | 36 | 27 | **┃** | 44 | 168 | **┃** | 195 | 124 | **┃** | 63 | 66 | **┃** | 18 | 30 |
| currencyservice | 1 | 4 | **┃** | 0 | 1 | **┃** | 1 | 0 | **┃** | 1 | 0 | **┃** | 0 | 0 | **┃** | 1 | 14 |
| shippingservice | 69 | 165 | **┃** | 18 | 29 | **┃** | 58 | 164 | **┃** | 138 | 116 | **┃** | 99 | 58 | **┃** | 33 | 33 |
| adservice | 0 | 0 | **┃** | 1 | 1 | **┃** | 0 | 0 | **┃** | 2 | 0 | **┃** | 1 | 0 | **┃** | 3 | 2 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 |

The same `grpc_4 / grpc_14` pair in §6 is what the retry policy counts on the four read callees.

## 9. RetryGuard toggles

Two parts. Part 1 is the scorer's log for each hold. Part 2 summarizes it per callee.

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name. `ON→OFF burst`, when the scorer prints it, counts the sheds whose log line is `metric=rpr_burst`. `From` is the attempt count before the step. `Value` is the rpr on a shed or climb line and the rejection on a re-enable line. On a burst shed, `Value` is the 5 s aggregate.

### Part 1: per hold

Every hold has transition lines.

### study6_s2_normal_rgtf0_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T00:33:47Z | frontend → recommendationservice | ON→OFF | 3 | rpr 4.29 |

### study6_s2_normal_rgtf0_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 1 | 1 |
| checkoutservice | 0 | 1 | 0 | 0 |
| frontend → recommendationservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T00:51:39Z | frontend → checkoutservice | ON→OFF | 3 | rpr 1.86 |
| 2026-10-12T00:52:05Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T00:52:05Z | frontend → recommendationservice | ON→OFF | 3 | rpr 3.17 |
| 2026-10-12T00:52:16Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T00:52:27Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |

### study6_s2_normal_rgtf1_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 7 | 0 | 1 | 0 |
| recommendationservice | 0 | 6 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T01:10:25Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.27 |
| 2026-10-12T01:12:50Z | recommendationservice | OFF→ON | 0 | rejection 0.16 |
| 2026-10-12T01:13:13Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.54 |
| 2026-10-12T01:13:38Z | recommendationservice | OFF→ON | 0 | rejection 0.05 |
| 2026-10-12T01:14:02Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.63 |
| 2026-10-12T01:14:43Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:15:06Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.76 |
| 2026-10-12T01:15:35Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:16:01Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.63 |
| 2026-10-12T01:16:38Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:16:49Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T01:17:19Z | frontend → recommendationservice | ON→OFF | 2 | rpr 1.57 |
| 2026-10-12T01:17:44Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:18:14Z | frontend → recommendationservice | ON→OFF | 1 | rpr 0.94 |

### study6_s2_normal_rgtf1_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → recommendationservice | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T01:27:34Z | frontend → recommendationservice | ON→OFF | 3 | rpr 1.83 |

### study6_s2_burst15_rgtf0_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 2 | 0 | 2 | 2 | 2 |
| frontend → recommendationservice | 1 | 0 | 0 | 0 | 1 |
| checkoutservice | 0 | 2 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T01:47:48Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.18 |
| 2026-10-12T01:47:58Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.00 |
| 2026-10-12T01:48:15Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:48:26Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T01:48:37Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T01:51:37Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.67 |
| 2026-10-12T01:52:02Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T01:52:13Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.03 |
| 2026-10-12T01:52:24Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.02 |

### study6_s2_burst15_rgtf0_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 4 | 0 | 3 | 3 | 4 |
| frontend → recommendationservice | 1 | 0 | 0 | 0 | 1 |
| checkoutservice | 0 | 3 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T02:05:30Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.15 |
| 2026-10-12T02:05:40Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.04 |
| 2026-10-12T02:05:55Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:06:06Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:06:17Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T02:07:27Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.56 |
| 2026-10-12T02:07:52Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:08:03Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:08:14Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.26 |
| 2026-10-12T02:08:27Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.82 |
| 2026-10-12T02:09:09Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:09:21Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:09:32Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.03 |
| 2026-10-12T02:14:25Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.05 |

### study6_s2_burst20_rgtf0_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 5 | 0 | 3 | 2 | 5 |
| frontend → recommendationservice | 1 | 0 | 0 | 0 | 1 |
| checkoutservice | 0 | 5 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T02:23:03Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.09 |
| 2026-10-12T02:23:24Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.18 |
| 2026-10-12T02:23:29Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:23:40Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:23:51Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T02:27:38Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.44 |
| 2026-10-12T02:28:15Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-12T02:28:26Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:28:33Z | frontend → checkoutservice | ON→OFF (burst) | 2 | rpr 1.34 |
| 2026-10-12T02:28:58Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:29:13Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.68 |
| 2026-10-12T02:29:37Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:29:56Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.78 |
| 2026-10-12T02:30:35Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:30:57Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:31:08Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |

### study6_s2_burst20_rgtf0_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 3 | 0 | 2 | 2 | 3 |
| frontend → recommendationservice | 3 | 0 | 0 | 0 | 3 |
| checkoutservice | 0 | 3 | 0 | 0 | 0 |
| recommendationservice | 0 | 2 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T02:40:42Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.44 |
| 2026-10-12T02:40:51Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.09 |
| 2026-10-12T02:41:07Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:41:18Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:41:29Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.08 |
| 2026-10-12T02:42:35Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.11 |
| 2026-10-12T02:42:46Z | recommendationservice | OFF→ON | 0 | rejection 0.15 |
| 2026-10-12T02:42:53Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.73 |
| 2026-10-12T02:43:10Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:43:16Z | frontend → checkoutservice | ON→OFF (burst) | 1 | rpr 0.83 |
| 2026-10-12T02:43:17Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:43:25Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.78 |
| 2026-10-12T02:43:55Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T02:44:06Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T02:44:17Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |

### study6_s2_burst15_rgtf1_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 2 | 0 | 2 | 2 | 2 |
| checkoutservice | 0 | 2 | 0 | 0 | 0 |
| frontend → recommendationservice | 6 | 0 | 2 | 2 | 6 |
| recommendationservice | 0 | 5 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T03:05:23Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.84 |
| 2026-10-12T03:05:48Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:05:51Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 1.97 |
| 2026-10-12T03:05:59Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:06:11Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:06:21Z | recommendationservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-12T03:06:29Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.70 |
| 2026-10-12T03:06:53Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:06:59Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.54 |
| 2026-10-12T03:07:24Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:07:35Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:07:46Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:08:49Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.57 |
| 2026-10-12T03:09:14Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:09:25Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:09:36Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:10:56Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 1.66 |
| 2026-10-12T03:11:22Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:11:35Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.77 |
| 2026-10-12T03:12:00Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:12:13Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:12:25Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:13:19Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 1.84 |

### study6_s2_burst15_rgtf1_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 2 | 0 | 2 | 2 | 2 |
| checkoutservice | 0 | 2 | 0 | 0 | 0 |
| frontend → recommendationservice | 3 | 0 | 2 | 2 | 3 |
| recommendationservice | 0 | 3 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T03:22:58Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 1.76 |
| 2026-10-12T03:23:22Z | checkoutservice | OFF→ON | 0 | rejection 0.08 |
| 2026-10-12T03:23:30Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 1.58 |
| 2026-10-12T03:23:34Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:23:46Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:23:54Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:24:10Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.66 |
| 2026-10-12T03:24:29Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.15 |
| 2026-10-12T03:24:33Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:24:44Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:24:56Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:25:06Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:25:16Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.07 |
| 2026-10-12T03:25:18Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:25:29Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:25:43Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:25:54Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:26:06Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

### study6_s2_burst20_rgtf1_rep1

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 1 | 1 | 1 |
| checkoutservice | 0 | 1 | 0 | 0 | 0 |
| frontend → recommendationservice | 1 | 0 | 1 | 1 | 1 |
| recommendationservice | 0 | 1 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T03:40:42Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.03 |
| 2026-10-12T03:41:03Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-12T03:41:09Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.09 |
| 2026-10-12T03:41:16Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:41:28Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.00 |
| 2026-10-12T03:41:34Z | recommendationservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:41:47Z | frontend → recommendationservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:42:00Z | frontend → recommendationservice | 2→3 | 2 | rpr 0.00 |

### study6_s2_burst20_rgtf1_rep2

| Name | ON→OFF | 0→1 | 1→2 | 2→3 | ON→OFF burst |
| --- | ---: | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 1 | 0 | 1 | 1 | 1 |
| checkoutservice | 0 | 1 | 0 | 0 | 0 |
| frontend → recommendationservice | 4 | 0 | 0 | 0 | 4 |
| recommendationservice | 0 | 3 | 0 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-12T03:58:13Z | frontend → checkoutservice | ON→OFF (burst) | 3 | rpr 2.21 |
| 2026-10-12T03:58:36Z | checkoutservice | OFF→ON | 0 | rejection 0.00 |
| 2026-10-12T03:58:48Z | frontend → checkoutservice | 1→2 | 1 | rpr 0.00 |
| 2026-10-12T03:58:53Z | frontend → recommendationservice | ON→OFF (burst) | 3 | rpr 2.80 |
| 2026-10-12T03:59:00Z | frontend → checkoutservice | 2→3 | 2 | rpr 0.15 |
| 2026-10-12T03:59:20Z | recommendationservice | OFF→ON | 0 | rejection 0.23 |
| 2026-10-12T03:59:28Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.84 |
| 2026-10-12T04:04:50Z | recommendationservice | OFF→ON | 0 | rejection 0.13 |
| 2026-10-12T04:04:57Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.79 |
| 2026-10-12T04:06:42Z | recommendationservice | OFF→ON | 0 | rejection 0.18 |
| 2026-10-12T04:06:50Z | frontend → recommendationservice | ON→OFF (burst) | 1 | rpr 0.73 |

### Part 2: per callee

Checkout and recommendations are the only callees that shed or re-enable. Payment, email, catalog, cart, currency, shipping, and ad have no `ON→OFF` and no `OFF→ON` on any hold.

Counts, shed rpr, and times come from the §9 timestamp log. A burst shed's value is tagged `b`. First shed is seconds after the first `OBSERVE` line in that hold. Attempts after re-enable are the attempt count that edge holds at `EXIT`. Time OFF runs from the shed timestamp to the matching `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is minimum / median, three decimals, over `OBSERVE` `metric=rejection` samples for that callee with timestamps after the shed and at or before the end of the window. The under-bar streak is the longest run of those samples strictly below 0.25. The controller's 0→1 step is `elapsed_s` of 20, except three `OFF→ON` lines at 21 (two on `study6_s2_normal_rgtf1_rep1`, one on `study6_s2_burst15_rgtf1_rep1`). The streak row counts `OBSERVE` samples under the bar, which can be shorter than `elapsed_s` when those lines are not one per second. An em dash means that edge never went to 0 on that hold.

#### checkoutservice

| | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF (burst) / OFF→ON | 0 (0) / 0 | 1 (0) / 1 | **┃** | 0 (0) / 0 | 0 (0) / 0 | **┃** | 2 (2) / 2 | 4 (4) / 3 | **┃** | 5 (5) / 5 | 3 (3) / 3 | **┃** | 2 (2) / 2 | 2 (2) / 2 | **┃** | 1 (1) / 1 | 1 (1) / 1 |
| Shed rpr | — | 1.86 | **┃** | — | — | **┃** | 2.18b; 1.67b | 2.15b; 1.56b; 1.82b; 2.05b | **┃** | 2.09b; 2.44b; 1.34b; 0.68b; 0.78b | 2.44b; 2.11b; 0.83b | **┃** | 1.84b; 1.57b | 1.76b; 2.15b | **┃** | 2.03b | 2.21b |
| First shed (s) | — | 62 | **┃** | — | — | **┃** | 45 | 47 | **┃** | 48 | 51 | **┃** | 49 | 47 | **┃** | 53 | 48 |
| Attempts after re-enable | — | 3 | **┃** | — | — | **┃** | 3 | 0 | **┃** | 3 | 3 | **┃** | 3 | 3 | **┃** | 3 | 3 |
| Time OFF (s) | — | 26 | **┃** | — | — | **┃** | 27; 25 | 25; 25; 42; 31 (to EXIT) | **┃** | 26; 37; 25; 24; 39 | 25; 35; 39 | **┃** | 25; 25 | 24; 37 | **┃** | 21 | 23 |
| OFF rejection min / median | — | 0.000 / 0.000 | **┃** | — | — | **┃** | 0.000 / 0.000; 0.000 / 0.000 | 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.021; 0.000 / 0.000 | **┃** | 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000 | 0.000 / 0.000; 0.000 / 0.042; 0.000 / 0.000 | **┃** | 0.000 / 0.000; 0.000 / 0.000 | 0.000 / 0.013; 0.000 / 0.000 | **┃** | 0.000 / 0.000 | 0.000 / 0.000 |
| Streak under the bar | — | 21 | **┃** | — | — | **┃** | 21; 21 | 20; 21; 18; 14 | **┃** | 21; 21; 21; 18; 21 | 21; 21; 21 | **┃** | 15; 14 | 14; 12 | **┃** | 12 | 14 |

Checkout shed on 9 holds and did not shed on `study6_s2_normal_rgtf0_rep1`, `study6_s2_normal_rgtf1_rep1`, `study6_s2_normal_rgtf1_rep2`. It held 3 attempts at EXIT on `study6_s2_normal_rgtf0_rep2`, `study6_s2_burst15_rgtf0_rep1`, `study6_s2_burst20_rgtf0_rep1`, `study6_s2_burst20_rgtf0_rep2`, `study6_s2_burst15_rgtf1_rep1`, `study6_s2_burst15_rgtf1_rep2`, `study6_s2_burst20_rgtf1_rep1`, `study6_s2_burst20_rgtf1_rep2`. It was at 0 attempts at EXIT on `study6_s2_burst15_rgtf0_rep2`. The longest under-bar streak is 21.

#### recommendationservice

| | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| ON→OFF (burst) / OFF→ON | 1 (0) / 0 | 1 (0) / 0 | **┃** | 7 (0) / 6 | 1 (0) / 0 | **┃** | 1 (1) / 0 | 1 (1) / 0 | **┃** | 1 (1) / 0 | 3 (3) / 2 | **┃** | 6 (6) / 5 | 3 (3) / 3 | **┃** | 1 (1) / 1 | 4 (4) / 3 |
| Shed rpr | 4.29 | 3.17 | **┃** | 1.27; 0.54; 0.63; 0.76; 0.63; 1.57; 0.94 | 1.83 | **┃** | 2.00b | 2.04b | **┃** | 2.18b | 2.09b; 0.73b; 0.78b | **┃** | 1.97b; 0.70b; 0.54b; 1.66b; 0.77b; 1.84b | 1.58b; 0.66b; 2.07b | **┃** | 2.09b | 2.80b; 0.84b; 0.79b; 0.73b |
| First shed (s) | 71 | 88 | **┃** | 125 | 87 | **┃** | 55 | 57 | **┃** | 69 | 60 | **┃** | 77 | 79 | **┃** | 80 | 88 |
| Attempts after re-enable | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 | 3 | **┃** | 3 | 0 |
| Time OFF (s) | 544 (to EXIT) | 527 (to EXIT) | **┃** | 145; 25; 41; 29; 37; 25; 20 (to EXIT) | 527 (to EXIT) | **┃** | 558 (to EXIT) | 556 (to EXIT) | **┃** | 545 (to EXIT) | 115; 24; 399 (to EXIT) | **┃** | 30; 24; 25; 26; 25; 88 (to EXIT) | 24; 23; 27 | **┃** | 25 | 27; 322; 105; 48 (to EXIT) |
| OFF rejection min / median | 0.056 / 0.462 | 0.000 / 0.370 | **┃** | 0.000 / 0.120; 0.000 / 0.000; 0.000 / 0.049; 0.000 / 0.091; 0.000 / 0.010; 0.000 / 0.000; 0.000 / 0.073 | 0.000 / 0.311 | **┃** | 0.000 / 0.410 | 0.000 / 0.279 | **┃** | 0.000 / 0.270 | 0.000 / 0.224; 0.000 / 0.118; 0.028 / 0.251 | **┃** | 0.000 / 0.109; 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.097; 0.000 / 0.000; 0.000 / 0.128 | 0.000 / 0.000; 0.000 / 0.000; 0.000 / 0.000 | **┃** | 0.000 / 0.000 | 0.076 / 0.208; 0.000 / 0.200; 0.000 / 0.172; 0.000 / 0.136 |
| Streak under the bar | 2 | 3 | **┃** | 17; 20; 17; 19; 20; 21; 14 | 13 | **┃** | 6 | 14 | **┃** | 17 | 21; 21; 17 | **┃** | 18; 17; 16; 16; 16; 15 | 13; 13; 13 | **┃** | 16 | 13; 13; 13; 11 |

Recommendations shed on every hold. It held 3 attempts at EXIT on `study6_s2_burst15_rgtf1_rep2`, `study6_s2_burst20_rgtf1_rep1`. The other 10 holds were at 0 attempts at EXIT. The longest under-bar streak is 21.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

### Locust goodput

| API | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 148.5 | 162.0 | **┃** | 188.3 | 171.0 | **┃** | 158.3 | 182.4 | **┃** | 188.4 | 202.9 | **┃** | 239.1 | 236.2 | **┃** | 261.2 | 207.9 |
| postcheckout | 41.2 | 48.3 | **┃** | 43.1 | 46.7 | **┃** | 50.4 | 55.3 | **┃** | 52.9 | 51.1 | **┃** | 54.8 | 57.4 | **┃** | 38.1 | 51.2 |
| getcart | 34.5 | 59.3 | **┃** | 70.0 | 69.4 | **┃** | 48.6 | 75.1 | **┃** | 69.9 | 71.9 | **┃** | 86.9 | 87.4 | **┃** | 95.0 | 75.7 |
| postcart | 86.4 | 86.3 | **┃** | 86.2 | 86.3 | **┃** | 86.4 | 86.4 | **┃** | 86.3 | 86.2 | **┃** | 86.4 | 86.3 | **┃** | 86.3 | 86.3 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.6 | 4.8 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

### Locust fail rate

| API | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 0.409 | 0.366 | **┃** | 0.262 | 0.335 | **┃** | 0.382 | 0.295 | **┃** | 0.271 | 0.221 | **┃** | 0.085 | 0.097 | **┃** | 0.009 | 0.201 |
| postcheckout | 0.498 | 0.420 | **┃** | 0.472 | 0.437 | **┃** | 0.396 | 0.340 | **┃** | 0.364 | 0.388 | **┃** | 0.347 | 0.318 | **┃** | 0.535 | 0.386 |
| getcart | 0.613 | 0.363 | **┃** | 0.248 | 0.263 | **┃** | 0.472 | 0.207 | **┃** | 0.258 | 0.238 | **┃** | 0.086 | 0.082 | **┃** | 0.009 | 0.199 |
| postcart | 0.000 | 0.001 | **┃** | 0.001 | 0.002 | **┃** | 0.000 | 0.001 | **┃** | 0.000 | 0.002 | **┃** | 0.001 | 0.000 | **┃** | 0.000 | 0.001 |
| emptycart | 0.001 | 0.002 | **┃** | 0.004 | 0.003 | **┃** | 0.000 | 0.002 | **┃** | 0.001 | 0.007 | **┃** | 0.002 | 0.001 | **┃** | 0.000 | 0.004 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

### Locust P95

| API | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| getproduct | 642 | 642 | **┃** | 800 | 643 | **┃** | 601 | 613 | **┃** | 638 | 622 | **┃** | 526 | 300 | **┃** | 260 | 632 |
| postcheckout | 853 | 896 | **┃** | 930 | 814 | **┃** | 882 | 966 | **┃** | 974 | 885 | **┃** | 763 | 516 | **┃** | 316 | 849 |
| getcart | 623 | 623 | **┃** | 765 | 624 | **┃** | 585 | 586 | **┃** | 617 | 610 | **┃** | 483 | 277 | **┃** | 238 | 601 |
| postcart | 70 | 72 | **┃** | 73 | 74 | **┃** | 72 | 75 | **┃** | 74 | 75 | **┃** | 75 | 73 | **┃** | 73 | 74 |
| emptycart | 20 | 20 | **┃** | 19 | 21 | **┃** | 22 | 20 | **┃** | 21 | 25 | **┃** | 20 | 22 | **┃** | 19 | 23 |

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

### Inbound arrival rate

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 481.0 | 485.9 | **┃** | 453.0 | 472.2 | **┃** | 491.4 | 491.1 | **┃** | 487.5 | 490.0 | **┃** | 466.2 | 442.5 | **┃** | 449.4 | 473.0 |
| checkoutservice | 40.6 | 50.4 | **┃** | 43.9 | 44.9 | **┃** | 50.3 | 59.3 | **┃** | 58.4 | 53.3 | **┃** | 55.0 | 56.4 | **┃** | 36.5 | 49.4 |
| recommendationservice | 419.3 | 421.1 | **┃** | 462.6 | 407.5 | **┃** | 413.0 | 412.4 | **┃** | 417.3 | 419.1 | **┃** | 406.7 | 371.5 | **┃** | 370.8 | 407.3 |
| paymentservice | 40.4 | 49.8 | **┃** | 43.9 | 44.8 | **┃** | 50.1 | 59.0 | **┃** | 58.1 | 53.0 | **┃** | 54.7 | 56.2 | **┃** | 36.4 | 49.4 |
| emailservice | 38.4 | 45.6 | **┃** | 43.2 | 43.8 | **┃** | 48.0 | 53.7 | **┃** | 52.5 | 49.1 | **┃** | 52.0 | 54.0 | **┃** | 35.4 | 48.3 |
| productcatalogservice | 1733.1 | 1972.7 | **┃** | 2164.2 | 2026.9 | **┃** | 1902.2 | 2171.4 | **┃** | 2181.5 | 2225.4 | **┃** | 2482.9 | 2432.0 | **┃** | 2503.9 | 2253.6 |
| cartservice | 484.0 | 506.0 | **┃** | 487.4 | 498.2 | **┃** | 512.3 | 528.2 | **┃** | 523.8 | 515.8 | **┃** | 517.4 | 498.4 | **┃** | 485.5 | 510.1 |
| currencyservice | 665.0 | 714.6 | **┃** | 702.3 | 716.5 | **┃** | 713.3 | 752.5 | **┃** | 740.3 | 737.4 | **┃** | 752.1 | 715.7 | **┃** | 730.1 | 736.5 |
| shippingservice | 112.0 | 153.4 | **┃** | 155.8 | 153.6 | **┃** | 144.7 | 185.9 | **┃** | 179.6 | 171.5 | **┃** | 189.4 | 192.7 | **┃** | 160.0 | 168.7 |
| adservice | 136.7 | 150.1 | **┃** | 185.3 | 158.1 | **┃** | 145.8 | 167.9 | **┃** | 174.1 | 187.3 | **┃** | 222.4 | 218.4 | **┃** | 240.0 | 192.3 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds.

### Inbound sojourn (ms)

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 479 | 477 | **┃** | 519 | 474 | **┃** | 470 | 477 | **┃** | 489 | 472 | **┃** | 344 | 186 | **┃** | 152 | 467 |
| checkoutservice | 159 | 178 | **┃** | 157 | 152 | **┃** | 200 | 247 | **┃** | 236 | 207 | **┃** | 208 | 184 | **┃** | 87 | 197 |
| recommendationservice | 474 | 459 | **┃** | 408 | 455 | **┃** | 465 | 442 | **┃** | 455 | 436 | **┃** | 263 | 101 | **┃** | 78 | 423 |
| paymentservice | 3 | 3 | **┃** | 3 | 3 | **┃** | 4 | 4 | **┃** | 4 | 4 | **┃** | 4 | 3 | **┃** | 2 | 3 |
| emailservice | 19 | 26 | **┃** | 27 | 20 | **┃** | 33 | 42 | **┃** | 38 | 33 | **┃** | 35 | 32 | **┃** | 11 | 36 |
| productcatalogservice | 2 | 2 | **┃** | 3 | 2 | **┃** | 2 | 2 | **┃** | 2 | 3 | **┃** | 3 | 2 | **┃** | 2 | 3 |
| cartservice | 3 | 3 | **┃** | 4 | 4 | **┃** | 3 | 4 | **┃** | 3 | 4 | **┃** | 4 | 3 | **┃** | 3 | 4 |
| currencyservice | 3 | 3 | **┃** | 4 | 3 | **┃** | 3 | 4 | **┃** | 3 | 4 | **┃** | 4 | 3 | **┃** | 3 | 4 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 | 1 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count.

### Share of inbound requests above 500 ms

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.795 | 0.775 | **┃** | 0.604 | 0.768 | **┃** | 0.795 | 0.755 | **┃** | 0.771 | 0.741 | **┃** | 0.313 | 0.080 | **┃** | 0.021 | 0.709 |
| checkoutservice | 0.032 | 0.058 | **┃** | 0.020 | 0.017 | **┃** | 0.034 | 0.069 | **┃** | 0.077 | 0.059 | **┃** | 0.037 | 0.030 | **┃** | 0.019 | 0.017 |
| recommendationservice | 0.615 | 0.513 | **┃** | 0.319 | 0.417 | **┃** | 0.495 | 0.309 | **┃** | 0.395 | 0.282 | **┃** | 0.120 | 0.044 | **┃** | 0.018 | 0.252 |
| paymentservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| emailservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| productcatalogservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| cartservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| currencyservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| shippingservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| adservice | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 | 0.000 |
| redis-cart | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — | **┃** | — | — |

## 16. CPU

CPU cells are per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum usage across replicas.

Per-pod quota, replica mode, mean millicores, max millicores. Mean and max are `cpu_millicores` summed across replicas, so frontend can sit above its per-pod quota.

### CPU quota / replicas / mean / max

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 1150 / 4 / 1225 / 1603 | 1150 / 4 / 1227 / 1601 | **┃** | 1150 / 4 / 1199 / 1613 | 1150 / 4 / 1234 / 1632 | **┃** | 1150 / 4 / 1234 / 1599 | 1150 / 4 / 1235 / 1589 | **┃** | 1150 / 4 / 1230 / 1604 | 1150 / 4 / 1236 / 1599 | **┃** | 1150 / 4 / 1237 / 1628 | 1150 / 4 / 1244 / 1616 | **┃** | 1150 / 4 / 1272 / 1664 | 1150 / 4 / 1240 / 1636 |
| checkoutservice | 800 / 1 / 496 / 781 | 800 / 1 / 570 / 796 | **┃** | 800 / 1 / 531 / 797 | 800 / 1 / 547 / 791 | **┃** | 800 / 1 / 574 / 794 | 800 / 1 / 603 / 796 | **┃** | 800 / 1 / 594 / 797 | 800 / 1 / 580 / 795 | **┃** | 800 / 1 / 590 / 797 | 800 / 1 / 604 / 799 | **┃** | 800 / 1 / 524 / 786 | 800 / 1 / 570 / 789 |
| recommendationservice | 1150 / 1 / 765 / 1150 | 1150 / 1 / 732 / 1120 | **┃** | 1150 / 1 / 720 / 1119 | 1150 / 1 / 727 / 1118 | **┃** | 1150 / 1 / 736 / 1048 | 1150 / 1 / 718 / 1003 | **┃** | 1150 / 1 / 718 / 1059 | 1150 / 1 / 701 / 1030 | **┃** | 1150 / 1 / 680 / 1031 | 1150 / 1 / 640 / 1043 | **┃** | 1150 / 1 / 655 / 1021 | 1150 / 1 / 711 / 1063 |
| paymentservice | 155 / 1 / 36 / 75 | 155 / 1 / 42 / 85 | **┃** | 155 / 1 / 39 / 72 | 155 / 1 / 39 / 69 | **┃** | 155 / 1 / 43 / 79 | 155 / 1 / 47 / 85 | **┃** | 155 / 1 / 46 / 80 | 155 / 1 / 44 / 81 | **┃** | 155 / 1 / 46 / 79 | 155 / 1 / 46 / 73 | **┃** | 155 / 1 / 36 / 69 | 155 / 1 / 42 / 77 |
| emailservice | 120 / 1 / 67 / 99 | 120 / 1 / 74 / 106 | **┃** | 120 / 1 / 71 / 108 | 120 / 1 / 74 / 106 | **┃** | 120 / 1 / 78 / 109 | 120 / 1 / 81 / 114 | **┃** | 120 / 1 / 79 / 114 | 120 / 1 / 77 / 115 | **┃** | 120 / 1 / 78 / 110 | 120 / 1 / 82 / 112 | **┃** | 120 / 1 / 63 / 106 | 120 / 1 / 76 / 112 |
| productcatalogservice | 800 / 1 / 370 / 515 | 800 / 1 / 375 / 502 | **┃** | 800 / 1 / 377 / 536 | 800 / 1 / 375 / 537 | **┃** | 800 / 1 / 372 / 515 | 800 / 1 / 379 / 511 | **┃** | 800 / 1 / 377 / 505 | 800 / 1 / 381 / 510 | **┃** | 800 / 1 / 388 / 523 | 800 / 1 / 394 / 527 | **┃** | 800 / 1 / 400 / 537 | 800 / 1 / 388 / 540 |
| cartservice | 800 / 1 / 332 / 452 | 800 / 1 / 327 / 467 | **┃** | 800 / 1 / 313 / 508 | 800 / 1 / 322 / 438 | **┃** | 800 / 1 / 322 / 442 | 800 / 1 / 312 / 422 | **┃** | 800 / 1 / 318 / 444 | 800 / 1 / 304 / 429 | **┃** | 800 / 1 / 318 / 524 | 800 / 1 / 323 / 529 | **┃** | 800 / 1 / 311 / 410 | 800 / 1 / 322 / 525 |
| currencyservice | 770 / 1 / 347 / 462 | 770 / 1 / 347 / 465 | **┃** | 770 / 1 / 333 / 455 | 770 / 1 / 349 / 476 | **┃** | 770 / 1 / 348 / 499 | 770 / 1 / 345 / 453 | **┃** | 770 / 1 / 345 / 456 | 770 / 1 / 338 / 450 | **┃** | 770 / 1 / 337 / 462 | 770 / 1 / 334 / 446 | **┃** | 770 / 1 / 340 / 456 | 770 / 1 / 338 / 455 |
| shippingservice | 770 / 1 / 61 / 106 | 770 / 1 / 78 / 108 | **┃** | 770 / 1 / 80 / 123 | 770 / 1 / 80 / 121 | **┃** | 770 / 1 / 74 / 112 | 770 / 1 / 87 / 125 | **┃** | 770 / 1 / 85 / 127 | 770 / 1 / 80 / 115 | **┃** | 770 / 1 / 89 / 124 | 770 / 1 / 93 / 127 | **┃** | 770 / 1 / 85 / 113 | 770 / 1 / 85 / 118 |
| adservice | 1150 / 1 / 110 / 206 | 1150 / 1 / 111 / 179 | **┃** | 1150 / 1 / 125 / 197 | 1150 / 1 / 117 / 192 | **┃** | 1150 / 1 / 111 / 172 | 1150 / 1 / 118 / 174 | **┃** | 1150 / 1 / 120 / 181 | 1150 / 1 / 125 / 177 | **┃** | 1150 / 1 / 138 / 183 | 1150 / 1 / 139 / 184 | **┃** | 1150 / 1 / 151 / 200 | 1150 / 1 / 128 / 187 |
| redis-cart | 540 / 1 / 42 / 64 | 540 / 1 / 40 / 63 | **┃** | 540 / 1 / 39 / 60 | 540 / 1 / 41 / 64 | **┃** | 540 / 1 / 41 / 70 | 540 / 1 / 39 / 62 | **┃** | 540 / 1 / 39 / 61 | 540 / 1 / 38 / 60 | **┃** | 540 / 1 / 38 / 59 | 540 / 1 / 38 / 61 | **┃** | 540 / 1 / 39 / 61 | 540 / 1 / 39 / 61 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. A sample with replica count 0 is left out. None occurred.

### CPU as a fraction of per-pod quota × replicas (mean / max)

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.27 / 0.35 | 0.27 / 0.35 | **┃** | 0.26 / 0.35 | 0.27 / 0.35 | **┃** | 0.27 / 0.35 | 0.27 / 0.35 | **┃** | 0.27 / 0.35 | 0.27 / 0.35 | **┃** | 0.27 / 0.35 | 0.27 / 0.35 | **┃** | 0.28 / 0.36 | 0.27 / 0.36 |
| checkoutservice | 0.62 / 0.98 | 0.71 / 0.99 | **┃** | 0.66 / 1.00 | 0.68 / 0.99 | **┃** | 0.72 / 0.99 | 0.75 / 0.99 | **┃** | 0.74 / 1.00 | 0.72 / 0.99 | **┃** | 0.74 / 1.00 | 0.75 / 1.00 | **┃** | 0.65 / 0.98 | 0.71 / 0.99 |
| recommendationservice | 0.67 / 1.00 | 0.64 / 0.97 | **┃** | 0.63 / 0.97 | 0.63 / 0.97 | **┃** | 0.64 / 0.91 | 0.62 / 0.87 | **┃** | 0.62 / 0.92 | 0.61 / 0.90 | **┃** | 0.59 / 0.90 | 0.56 / 0.91 | **┃** | 0.57 / 0.89 | 0.62 / 0.92 |
| paymentservice | 0.24 / 0.48 | 0.27 / 0.55 | **┃** | 0.25 / 0.46 | 0.25 / 0.45 | **┃** | 0.28 / 0.51 | 0.30 / 0.55 | **┃** | 0.30 / 0.52 | 0.28 / 0.52 | **┃** | 0.30 / 0.51 | 0.30 / 0.47 | **┃** | 0.23 / 0.45 | 0.27 / 0.50 |
| emailservice | 0.56 / 0.82 | 0.62 / 0.88 | **┃** | 0.59 / 0.90 | 0.61 / 0.88 | **┃** | 0.65 / 0.91 | 0.68 / 0.95 | **┃** | 0.66 / 0.95 | 0.64 / 0.96 | **┃** | 0.65 / 0.92 | 0.68 / 0.93 | **┃** | 0.53 / 0.88 | 0.64 / 0.93 |
| productcatalogservice | 0.46 / 0.64 | 0.47 / 0.63 | **┃** | 0.47 / 0.67 | 0.47 / 0.67 | **┃** | 0.46 / 0.64 | 0.47 / 0.64 | **┃** | 0.47 / 0.63 | 0.48 / 0.64 | **┃** | 0.48 / 0.65 | 0.49 / 0.66 | **┃** | 0.50 / 0.67 | 0.48 / 0.68 |
| cartservice | 0.42 / 0.56 | 0.41 / 0.58 | **┃** | 0.39 / 0.64 | 0.40 / 0.55 | **┃** | 0.40 / 0.55 | 0.39 / 0.53 | **┃** | 0.40 / 0.56 | 0.38 / 0.54 | **┃** | 0.40 / 0.66 | 0.40 / 0.66 | **┃** | 0.39 / 0.51 | 0.40 / 0.66 |
| currencyservice | 0.45 / 0.60 | 0.45 / 0.60 | **┃** | 0.43 / 0.59 | 0.45 / 0.62 | **┃** | 0.45 / 0.65 | 0.45 / 0.59 | **┃** | 0.45 / 0.59 | 0.44 / 0.58 | **┃** | 0.44 / 0.60 | 0.43 / 0.58 | **┃** | 0.44 / 0.59 | 0.44 / 0.59 |
| shippingservice | 0.08 / 0.14 | 0.10 / 0.14 | **┃** | 0.10 / 0.16 | 0.10 / 0.16 | **┃** | 0.10 / 0.15 | 0.11 / 0.16 | **┃** | 0.11 / 0.16 | 0.10 / 0.15 | **┃** | 0.12 / 0.16 | 0.12 / 0.16 | **┃** | 0.11 / 0.15 | 0.11 / 0.15 |
| adservice | 0.10 / 0.18 | 0.10 / 0.16 | **┃** | 0.11 / 0.17 | 0.10 / 0.17 | **┃** | 0.10 / 0.15 | 0.10 / 0.15 | **┃** | 0.10 / 0.16 | 0.11 / 0.15 | **┃** | 0.12 / 0.16 | 0.12 / 0.16 | **┃** | 0.13 / 0.17 | 0.11 / 0.16 |
| redis-cart | 0.08 / 0.12 | 0.07 / 0.12 | **┃** | 0.07 / 0.11 | 0.08 / 0.12 | **┃** | 0.08 / 0.13 | 0.07 / 0.11 | **┃** | 0.07 / 0.11 | 0.07 / 0.11 | **┃** | 0.07 / 0.11 | 0.07 / 0.11 | **┃** | 0.07 / 0.11 | 0.07 / 0.11 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

### Detector max utilization

| Service | study6_s2_normal_rgtf0_rep1 | study6_s2_normal_rgtf0_rep2 | **┃** | study6_s2_normal_rgtf1_rep1 | study6_s2_normal_rgtf1_rep2 | **┃** | study6_s2_burst15_rgtf0_rep1 | study6_s2_burst15_rgtf0_rep2 | **┃** | study6_s2_burst20_rgtf0_rep1 | study6_s2_burst20_rgtf0_rep2 | **┃** | study6_s2_burst15_rgtf1_rep1 | study6_s2_burst15_rgtf1_rep2 | **┃** | study6_s2_burst20_rgtf1_rep1 | study6_s2_burst20_rgtf1_rep2 |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: | ---: |
| frontend | 0.362 | 0.360 | **┃** | 0.366 | 0.378 | **┃** | 0.363 | 0.358 | **┃** | 0.358 | 0.363 | **┃** | 0.367 | 0.370 | **┃** | 0.380 | 0.369 |
| checkoutservice | 1.055 | 1.064 | **┃** | 1.024 | 1.016 | **┃** | 1.029 | 1.040 | **┃** | 1.030 | 1.040 | **┃** | 1.039 | 1.028 | **┃** | 1.016 | 1.024 |
| recommendationservice | 1.020 | 1.000 | **┃** | 1.012 | 1.000 | **┃** | 0.991 | 0.990 | **┃** | 0.983 | 1.004 | **┃** | 1.002 | 0.999 | **┃** | 0.996 | 1.011 |
| paymentservice | 0.600 | 0.781 | **┃** | 0.600 | 0.581 | **┃** | 0.690 | 0.735 | **┃** | 0.703 | 0.677 | **┃** | 0.677 | 0.671 | **┃** | 0.729 | 0.613 |
| emailservice | 1.083 | 1.075 | **┃** | 1.033 | 1.033 | **┃** | 1.033 | 1.083 | **┃** | 1.025 | 1.017 | **┃** | 1.050 | 1.042 | **┃** | 0.992 | 1.050 |
| productcatalogservice | 0.660 | 0.686 | **┃** | 0.691 | 0.703 | **┃** | 0.675 | 0.700 | **┃** | 0.667 | 0.665 | **┃** | 0.689 | 0.706 | **┃** | 0.708 | 0.703 |
| cartservice | 0.640 | 0.613 | **┃** | 0.657 | 0.593 | **┃** | 0.637 | 0.593 | **┃** | 0.611 | 0.632 | **┃** | 0.681 | 0.684 | **┃** | 0.576 | 0.704 |
| currencyservice | 0.710 | 0.674 | **┃** | 0.649 | 0.664 | **┃** | 0.743 | 0.673 | **┃** | 0.668 | 0.626 | **┃** | 0.644 | 0.645 | **┃** | 0.651 | 0.661 |
| shippingservice | 0.168 | 0.177 | **┃** | 0.199 | 0.182 | **┃** | 0.181 | 0.223 | **┃** | 0.186 | 0.181 | **┃** | 0.195 | 0.203 | **┃** | 0.184 | 0.187 |
| adservice | 0.417 | 0.174 | **┃** | 0.276 | 0.196 | **┃** | 0.164 | 0.226 | **┃** | 0.195 | 0.169 | **┃** | 0.184 | 0.183 | **┃** | 0.201 | 0.339 |
| redis-cart | 0.306 | 0.311 | **┃** | 0.350 | 0.287 | **┃** | 0.315 | 0.291 | **┃** | 0.296 | 0.343 | **┃** | 0.283 | 0.287 | **┃** | 0.337 | 0.291 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. `postcart` and `emptycart` are no cap on every live read of every hold. On the six TopFull-off holds, every API is no cap for the span the scorer prints. The cells below are the scorer's spans.

### TopFull live caps

A live read has threshold_fresh=1 and threshold above 0. 10000 is no cap. A live 0 is left out.

### study6_s2_normal_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:31:00–00:42:50 |
| postcheckout | no cap 00:31:00–00:42:50 |
| getcart | no cap 00:31:00–00:42:50 |
| postcart | no cap 00:31:00–00:42:50 |
| emptycart | no cap 00:31:00–00:42:50 |

### study6_s2_normal_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:49:00–01:00:50 |
| postcheckout | no cap 00:49:00–01:00:50 |
| getcart | no cap 00:49:00–01:00:50 |
| postcart | no cap 00:49:00–01:00:50 |
| emptycart | no cap 00:49:00–01:00:50 |

### study6_s2_normal_rgtf1_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:06:40–01:09:30; 225.6 at 01:09:35; 216.3 at 01:09:40; 212 at 01:09:45; 298.7 at 01:09:50; no cap 01:09:53–01:10:00 |
| postcheckout | no cap 01:06:40–01:08:35; 31 at 01:08:40; 38 at 01:08:45; 53.9 at 01:08:50; 50.8 at 01:08:55; 45.5 at 01:09:00; 10.9 at 01:09:05; 26.6 at 01:09:10; 60.3 at 01:09:15; 70.4 at 01:09:20; 60.8434 at 01:09:24; 60.8 at 01:09:25; 55.7 at 01:09:30; 23 at 01:09:35; 13.6 at 01:09:40; 10 at 01:09:45; 14.105 at 01:09:49; 14.1 at 01:09:50; 36.21 at 01:09:54; 36.2 at 01:09:55; 79 at 01:10:00 |
| getcart | no cap 01:06:40–01:09:30; 92.6 at 01:09:35; 83.3 at 01:09:40; 79 at 01:09:45; 78.967 at 01:09:48; 79 at 01:09:50; 110 at 01:09:52; no cap 01:09:55–01:10:00 |
| postcart | no cap 01:06:40–01:10:00 |
| emptycart | no cap 01:06:40–01:10:00 |

### study6_s2_normal_rgtf1_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:24:25–01:27:10; 275 at 01:36:20 |
| postcheckout | no cap 01:24:25–01:26:25; 35 at 01:26:28; 40.7 at 01:26:30; 48.4 at 01:26:35; no cap 01:26:39–01:26:45; 66 at 01:26:50; 15.6423 at 01:26:53; 10 at 01:26:55; 19.2 at 01:27:00; 52.6 at 01:27:05; 65.6 at 01:27:10; 46.7526 01:27:15–01:36:18; 46.8 at 01:36:20 |
| getcart | no cap 01:24:25–01:27:10; 100 at 01:36:20 |
| postcart | no cap 01:24:25–01:36:20 |
| emptycart | no cap 01:24:25–01:36:20 |

### study6_s2_burst15_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 01:45:25–01:57:15 |
| postcheckout | no cap 01:45:25–01:57:15 |
| getcart | no cap 01:45:25–01:57:15 |
| postcart | no cap 01:45:25–01:57:15 |
| emptycart | no cap 01:45:25–01:57:15 |

### study6_s2_burst15_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:03:05–02:14:55 |
| postcheckout | no cap 02:03:05–02:14:55 |
| getcart | no cap 02:03:05–02:14:55 |
| postcart | no cap 02:03:05–02:14:55 |
| emptycart | no cap 02:03:05–02:14:55 |

### study6_s2_burst20_rgtf0_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:20:35–02:23:05 |
| postcheckout | no cap 02:20:35–02:23:05 |
| getcart | no cap 02:20:35–02:23:05 |
| postcart | no cap 02:20:35–02:23:05 |
| emptycart | no cap 02:20:35–02:23:05 |

### study6_s2_burst20_rgtf0_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 02:38:10–02:40:45 |
| postcheckout | no cap 02:38:10–02:40:45 |
| getcart | no cap 02:38:10–02:40:45 |
| postcart | no cap 02:38:10–02:40:45 |
| emptycart | no cap 02:38:10–02:40:45 |

### study6_s2_burst15_rgtf1_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:02:55–03:14:45 |
| postcheckout | no cap 03:02:55–03:04:55; 42 at 03:05:00; 50 at 03:05:05; 66 03:05:09–03:05:10; no cap 03:05:15–03:05:20; 24.4622 at 03:05:23; 15.1 at 03:05:25; 19.2 at 03:05:30; 44.1 at 03:05:35; 82.5 at 03:05:40; 71.7 at 03:05:45; 63.9 at 03:14:45 |
| getcart | no cap 03:02:55–03:14:45 |
| postcart | no cap 03:02:55–03:14:45 |
| emptycart | no cap 03:02:55–03:14:45 |

### study6_s2_burst15_rgtf1_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:20:30–03:23:25; 221 at 03:23:30; 213.5 at 03:23:35; 302.5 at 03:23:40; no cap 03:23:45–03:24:05; 258.2 at 03:24:10; 259.85 at 03:24:12; 259.8 at 03:24:15; no cap 03:24:20–03:25:10 |
| postcheckout | no cap 03:20:30–03:22:35; 48 at 03:22:40; 55 at 03:22:45; no cap 03:22:46–03:22:50; 76.1981 at 03:22:51; 70 03:22:54–03:22:55; 16.6616 at 03:22:58; 10.3 at 03:23:00; 14.0252 at 03:23:02; 25 at 03:23:05; 32.7953 at 03:23:06; 54.3 at 03:23:10; 82.8875 at 03:23:14; 82.9 at 03:23:15; 66.4 at 03:23:20; 61.4 at 03:23:25; 25.904 at 03:23:29; 25.9 at 03:23:30; 18.5 at 03:23:35; 36.3667 at 03:23:39; 36.4 at 03:23:40; 78.6 at 03:23:45; 64.6 at 03:23:50; 55 at 03:23:55; 66.8 at 03:24:00; 54.2 at 03:24:05; 27.3 at 03:24:10; 28.9 at 03:24:15; 69.2 at 03:24:20; 54.7 at 03:24:25; 10 at 03:24:30; 19.5 at 03:24:35; 65.1 at 03:24:40; 68.1821 at 03:24:44; 68.2 at 03:24:45; 65.6 at 03:24:50; 62.1885 at 03:24:51; 60.1 at 03:24:55; 52.2004 at 03:24:59; 52.2 at 03:25:00; 57.8289 at 03:25:03; 62.2 at 03:25:05; 63.9 at 03:25:10; 65.1825 at 03:25:11; 43.6614 03:25:13–03:32:24 |
| getcart | no cap 03:20:30–03:23:25; 65.9625 at 03:23:29; 66 at 03:23:30; 58.5 at 03:23:35; 110 at 03:23:40; no cap 03:23:45–03:24:05; 93.2 at 03:24:10; 94.8496 03:24:12–03:24:14; 94.8 at 03:24:15; no cap 03:24:20–03:25:10 |
| postcart | no cap 03:20:30–03:25:10 |
| emptycart | no cap 03:20:30–03:25:10 |

### study6_s2_burst20_rgtf1_rep1

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:38:10–03:50:00 |
| postcheckout | 43.6614 03:38:06–03:38:09; no cap at 03:38:10; 43.6614 03:38:11–03:38:14; no cap at 03:38:15; 43.6614 03:38:16–03:38:19; no cap at 03:38:20; 43.6614 03:38:21–03:38:24; no cap at 03:38:25; 43.6614 03:38:26–03:38:29; no cap at 03:38:30; 43.6614 03:38:31–03:38:34; no cap at 03:38:35; 43.6614 03:38:36–03:38:39; no cap at 03:38:40; 43.6614 03:38:41–03:38:44; no cap at 03:38:45; 43.6614 03:38:46–03:38:49; no cap at 03:38:50; 43.6614 03:38:51–03:38:54; no cap at 03:38:55; 43.6614 03:38:56–03:38:59; no cap at 03:39:00; 43.6614 03:39:01–03:39:04; no cap at 03:39:05; 43.6614 03:39:06–03:39:09; no cap at 03:39:10; 43.6614 03:39:11–03:39:14; no cap at 03:39:15; 43.6614 03:39:16–03:39:19; no cap at 03:39:20; 43.6614 03:39:21–03:39:24; no cap at 03:39:25; 43.6614 03:39:26–03:39:29; no cap at 03:39:30; 43.6614 03:39:31–03:39:34; no cap at 03:39:35; 43.6614 03:39:36–03:39:39; no cap at 03:39:40; 43.6614 03:39:41–03:39:44; no cap at 03:39:45; 43.6614 03:39:46–03:39:49; no cap at 03:39:50; 43.6614 03:39:51–03:39:54; no cap at 03:39:55; 43.6614 03:39:56–03:39:59; no cap at 03:40:00; 43.6614 03:40:01–03:40:04; no cap at 03:40:05; 43.6614 03:40:06–03:40:08; 37.4 at 03:40:10; 45.1 at 03:40:15; no cap 03:40:19–03:40:20; 62.7 at 03:40:22; no cap at 03:40:25; 70 at 03:40:30; 46.6 at 03:40:35; 28.7919 at 03:40:36; 11.2 at 03:40:40; 25.8758 at 03:40:44; 25.9 at 03:40:45; 64.1 at 03:40:50; 68.3 at 03:40:55; 71.3 at 03:41:00; 63.8812 at 03:41:04; 63.9 at 03:41:05; 38.3 at 03:50:00 |
| getcart | no cap 03:38:10–03:50:00 |
| postcart | no cap 03:38:10–03:50:00 |
| emptycart | no cap 03:38:10–03:50:00 |

### study6_s2_burst20_rgtf1_rep2

| API | Live caps |
| --- | --- |
| getproduct | no cap 03:55:45–03:58:45 |
| postcheckout | no cap 03:55:45–03:57:50; 53.9 at 03:57:55; 61.6 at 03:58:00; 66 at 03:58:05; 44.5 at 03:58:10; 10 at 03:58:15; 19.2 at 03:58:20; 51.6 at 03:58:25; 80.8 at 03:58:30; 63.6 at 03:58:35; 72.8 at 03:58:40; 62.3 at 03:58:45; 59.9423 03:58:48–04:07:38 |
| getcart | no cap 03:55:45–03:58:45 |
| postcart | no cap 03:55:45–03:58:45 |
| emptycart | no cap 03:55:45–03:58:45 |

## 20. Per hold

**study6_s2_normal_rgtf0_rep1.** `frontend → checkoutservice` did not shed. `frontend → recommendationservice` shed 1 time (none burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 1,163 into checkoutservice and 14,876 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 95,926 / 0. Detector-hot: recommendationservice 72.4%. Burst mode was off.

**study6_s2_normal_rgtf0_rep2.** `frontend → checkoutservice` shed 1 time (none burst) and re-enabled 1 time. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 1 time (none burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 2,352 into checkoutservice and 12,708 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 75,869 / 0. Detector-hot: checkoutservice 74.4%, recommendationservice 52.9%. Burst mode was off.

**study6_s2_normal_rgtf1_rep1.** `frontend → checkoutservice` did not shed. `frontend → recommendationservice` shed 7 times (none burst) and re-enabled 6 times. At EXIT the edge held 0 attempts. Retry volume is 696 into checkoutservice and 62,083 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 75,743 / 0. Detector-hot: checkoutservice 55.9%. Burst mode was off.

**study6_s2_normal_rgtf1_rep2.** `frontend → checkoutservice` did not shed. `frontend → recommendationservice` shed 1 time (none burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 644 into checkoutservice and 12,734 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 61,998 / 0. Detector-hot: checkoutservice 67.5%. Burst mode was off.

**study6_s2_burst15_rgtf0_rep1.** `frontend → checkoutservice` shed 2 times (all burst) and re-enabled 2 times. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 1 time (all burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 1,365 into checkoutservice and 3,702 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 74,662 / 0. Detector-hot: checkoutservice 72.5%, recommendationservice 59.8%. This hold has no replay.

**study6_s2_burst15_rgtf0_rep2.** `frontend → checkoutservice` shed 4 times (all burst) and re-enabled 3 times. At EXIT the edge held 0 attempts. `frontend → recommendationservice` shed 1 time (all burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 2,747 into checkoutservice and 3,550 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 47,089 / 0. Detector-hot: checkoutservice 80.7%, emailservice 59.5%. This hold has no replay.

**study6_s2_burst20_rgtf0_rep1.** `frontend → checkoutservice` shed 5 times (all burst) and re-enabled 5 times. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 1 time (all burst) and re-enabled 0 times. At EXIT the edge held 0 attempts. Retry volume is 2,787 into checkoutservice and 9,183 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 52,018 / 0. Detector-hot: checkoutservice 75.8%, emailservice 54.8%. This hold has no replay.

**study6_s2_burst20_rgtf0_rep2.** `frontend → checkoutservice` shed 3 times (all burst) and re-enabled 3 times. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 3 times (all burst) and re-enabled 2 times. At EXIT the edge held 0 attempts. Retry volume is 2,048 into checkoutservice and 8,594 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 48,422 / 0. Detector-hot: checkoutservice 74.5%. This hold has no replay.

**study6_s2_burst15_rgtf1_rep1.** `frontend → checkoutservice` shed 2 times (all burst) and re-enabled 2 times. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 6 times (all burst) and re-enabled 5 times. At EXIT the edge held 0 attempts. Retry volume is 1,663 into checkoutservice and 16,212 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 23,881 / 0. Detector-hot: checkoutservice 76.0%, emailservice 55.0%. The first `metric=rpr_burst` shed is 49 s after the first OBSERVE line, on `frontend → checkoutservice`. The replay's first fire is 104–113 s.

**study6_s2_burst15_rgtf1_rep2.** `frontend → checkoutservice` shed 2 times (all burst) and re-enabled 2 times. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 3 times (all burst) and re-enabled 3 times. At EXIT the edge held 3 attempts. Retry volume is 1,351 into checkoutservice and 8,536 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 9,316 / 0. Detector-hot: checkoutservice 75.0%, emailservice 68.2%. The first `metric=rpr_burst` shed is 47 s after the first OBSERVE line, on `frontend → checkoutservice`. The replay's first fire is 104–113 s.

**study6_s2_burst20_rgtf1_rep1.** `frontend → checkoutservice` shed 1 time (all burst) and re-enabled 1 time. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 1 time (all burst) and re-enabled 1 time. At EXIT the edge held 3 attempts. Retry volume is 566 into checkoutservice and 3,557 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 4,019 / 0. Detector-hot: checkoutservice 65.8%. The first `metric=rpr_burst` shed is 53 s after the first OBSERVE line, on `frontend → checkoutservice`. The replay's first fire is 104–113 s.

**study6_s2_burst20_rgtf1_rep2.** `frontend → checkoutservice` shed 1 time (all burst) and re-enabled 1 time. At EXIT the edge held 3 attempts. `frontend → recommendationservice` shed 4 times (all burst) and re-enabled 3 times. At EXIT the edge held 0 attempts. Retry volume is 745 into checkoutservice and 12,135 into recommendationservice. `grpc_4 / grpc_14` on recommendationservice is 40,571 / 0. Detector-hot: checkoutservice 72.2%. The first `metric=rpr_burst` shed is 48 s after the first OBSERVE line, on `frontend → checkoutservice`. The replay's first fire is 104–113 s.

## 21. Related links

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode and burst-mode sections
- [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md)
- Replay this guide is checked against: [2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)
- Earlier burst bar 1.5 pair, not a column in this table: `study5_s2_burst15_rgtf0` and `study5_s2_burst15_rgtf1`, [2026-10-12-s2-burst15-abc.md](2026-10-12-s2-burst15-abc.md)
- Previous same-mix guide, the four tuned both-on holds with burst mode off: [2026-10-11-s2-rgtf1-rep3-rep4-abc.md](2026-10-11-s2-rgtf1-rep3-rep4-abc.md)
- Run log: [2026-10-12-s2-burst-matrix-run-log.md](../docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md)

## Throttle flag addendum (2026-10-15 audit)

- `study6_s2_normal_rgtf1_rep1` is FLAGGED (204 fetch warnings; longest no-fresh threshold read 513 s, longest no-fresh admitted read 513 s). Its cap and admitted-rate numbers are carried, not measured; filter them on `threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
- `study6_s2_normal_rgtf1_rep2` is FLAGGED (218 fetch warnings; longest no-fresh threshold read 5 s, longest no-fresh admitted read 550 s). The cap is measured; admitted req/s is carried, not measured; filter it on `admitted_fresh==1` and do not quote it as measured. Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid.
