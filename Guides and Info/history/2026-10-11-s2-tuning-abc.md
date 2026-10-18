# S2 tuning holds (2026-10-11): reenable 0.25, interval 20 s, climb 10 s

Analysis of the four S2 tuning holds plus one replay of hold 1, scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md). Run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md).

## 1. Setup

- **Duration** 600 s. **Mix** getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5**, `spawn_rate` 50. This is the locked S2 mix, Paper-C1.
- **CPU and replica pin** (`service_capacity.json` values from the configs):

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

  Frontend sidecar `proxyCPU=90m`, `proxyCPULimit` unset. Catalog HPA max 1.
- **Controllers.** RetryGuard is on in all five. TopFull is off on `rgtf0` holds (manifest `topfull_rl.enabled: false`) and on on `rgtf1` holds.
- **Cool-off** 120 s between holds, from `run_scenario.py` exit (AGENTS §6).
- **Folders:** `experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf{0,1}_rep{1,2}` and `study4_s2_tune_rgtf0_rep1_r2`. Configs: `experiments/configs/study_2026_10_11/01..04_s2_*.yaml`. The replay is `01_s2_tune_rgtf0_rep1_r2.yaml`.

## 2. Index

Columns in the tables below. Bold bars separate the two replicate pairs from the replay.

| Column | Folder | Arm | Replicate |
| --- | --- | --- | --- |
| rep1 off | `study4_s2_tune_rgtf0_rep1` | TopFull off | 1 |
| rep1 on | `study4_s2_tune_rgtf1_rep1` | TopFull on | 1 |
| rep2 off | `study4_s2_tune_rgtf0_rep2` | TopFull off | 2 |
| rep2 on | `study4_s2_tune_rgtf1_rep2` | TopFull on | 2 |
| rep1 replay | `study4_s2_tune_rgtf0_rep1_r2` | TopFull off | 1, replay |

All five folders have `run_number` 1 in `run_manifest.json`; the `log_folder` name is the slot. The replay repeats the rep1 off configuration as a separate run. Its numbers are shown beside rep1 off, not averaged into it.

## 3. Gate

**Pass on all five.** The run log records PASS for each, with no `PATCH_FAIL` and no traceback.

Scorer gate numbers:

| Column | Locust `total.csv` rows | Mesh span (s) | Inbound gaps ≥ 1.5 s | `retryguard.log` |
| --- | ---: | ---: | ---: | --- |
| rep1 off | 571 | 664 | 0 of 7304 | present |
| rep1 on | 566 | 665 | 0 of 7315 | present |
| rep2 off | 571 | 664 | 0 of 7304 | present |
| rep2 on | 566 | 665 | 0 of 7315 | present |
| rep1 replay | 571 | 664 | 0 of 7304 | present |

`service_capacity.json` matches the pin in §1 on all five holds (checked for every service). `resource_usage.csv` shows frontend at 4 replicas on every sample (148 to 150 samples per hold), and no service has a zero-replica sample. The scorer printed no replica-change line for any S2 hold.

## 4. Edge-mode bars

The scorer's first line for these holds:

> Shed bar rpr > 0.40. Climb bars rpr ≤ 0.16 at 1 attempt and rpr ≤ 0.32 at 2 attempts. Rejection high bar 0.20, re-enable bar 0.25.

START line on every hold: `rpr_threshold=0.40`, `rejection_threshold=0.20`, `reenable_rejection=0.25`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `sample_interval=1s`, `interval_samples=20`, `attempts_on=3`.

Intervals used in this study:

- Shed and 0→1 take **20 s** (`interval_samples=20`).
- Climbs 1→2 and 2→3 take **10 s**. This study overrode the 15 s default with `climb_interval_seconds: 10`.

`rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge. A tick with no first attempts is skipped and does not break the streak.

## 5. (a) Edge rpr

Only `frontend → checkoutservice` has a tick above the shed bar or a retry delta on these holds. The retry delta table in §8 lists checkoutservice alone, so every other controlled edge is at zero.

**File streak, seconds / ticks above the shed bar (controller `high` in parentheses)**

| Edge | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend → checkoutservice | 22 / 249 (21) | 8 / 207 (9) | **┃** | 22 / 69 (21) | 8 / 199 (9) | **┃** | 22 / 214 (21) |

No streak reaches 30 s, so nothing is bold. Every shed streak sits just above the 20 s `interval_samples` threshold, and the controller `high` reads 21 or 9 to match.

**Mean / median / max / volume rpr**

| Edge | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend → checkoutservice | 0.405 / 0.000 / 2.79 / 0.376 | 0.826 / 0.000 / 6.64 / 0.750 | **┃** | 0.153 / 0.000 / 3.00 / 0.115 | 0.811 / 0.000 / 6.00 / 0.698 | **┃** | 0.366 / 0.000 / 4.29 / 0.328 |

The median is zero on every hold. Rpr is high in short bursts and near zero for most ticks.

**Climb streaks, 1-attempt / 2-attempt** (samples while that cap is in force; em dash means that cap never applied)

| Edge | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend → checkoutservice | 5 / — | — / — | **┃** | 2 / — | — / — | **┃** | 3 / — |

No hold climbed to 2 attempts. The 1-attempt streaks are the ticks after a 0→1 re-enable where rpr stayed under 0.16.

## 6. Rejection, beside (a)

Not the shed signal. Cells are longest streak / count above 0.20, then longest streak / count strictly under the re-enable bar of 0.25. No cell reaches 30, so nothing is bold.

**Above 0.20**

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend (not controlled) | 1 / 2 | 1 / 1 | **┃** | 1 / 2 | 0 / 0 | **┃** | 1 / 7 |
| checkoutservice | 26 / 280 | 9 / 204 | **┃** | 25 / 180 | 8 / 189 | **┃** | 25 / 258 |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| paymentservice | 1 / 3 | 1 / 1 | **┃** | 1 / 1 | 1 / 2 | **┃** | 1 / 1 |
| emailservice | 5 / 176 | 4 / 81 | **┃** | 3 / 157 | 4 / 70 | **┃** | 4 / 144 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| cartservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| shippingservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |

**Under the 0.25 re-enable bar**

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend (not controlled) | 612 / 612 | 612 / 612 | **┃** | 612 / 612 | 612 / 612 | **┃** | 612 / 612 |
| checkoutservice | 51 / 348 | 50 / 413 | **┃** | 49 / 480 | 54 / 428 | **┃** | 52 / 376 |
| recommendationservice | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 |
| paymentservice | 612 / 612 | 352 / 611 | **┃** | 472 / 611 | 442 / 610 | **┃** | 611 / 611 |
| emailservice | 55 / 411 | 50 / 487 | **┃** | 49 / 490 | 53 / 516 | **┃** | 53 / 446 |
| productcatalogservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 612 / 612 | **┃** | 613 / 613 |
| cartservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 612 / 612 | **┃** | 613 / 613 |
| currencyservice | 612 / 612 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 |
| shippingservice | 613 / 613 | 613 / 613 | **┃** | 613 / 613 | 613 / 613 | **┃** | 613 / 613 |
| adservice | 611 / 611 | 612 / 612 | **┃** | 612 / 612 | 612 / 612 | **┃** | 612 / 612 |
| redis-cart (not controlled) | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |

The checkoutservice rejection streak under the bar is only 49–54 s, well short of the 612 s of most services. Checkout and email are the two controlled services whose rejection moves above and below the bar. The rest hold one state for the whole hold.

**gRPC counted in the rejection rate, `grpc_4 / grpc_14`.** Every controlled gRPC callee is 0 / 0 on every S2 hold, so no gRPC rejection feeds the controller in this set.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| recommendationservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| productcatalogservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| currencyservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |
| adservice | 0 / 0 | 0 / 0 | **┃** | 0 / 0 | 0 / 0 | **┃** | 0 / 0 |

## 7. (b) Detector overloaded fraction

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| checkoutservice | **586/713 (82.2%)** | **392/717 (54.7%)** | **┃** | **588/713 (82.5%)** | **384/717 (53.6%)** | **┃** | **589/714 (82.5%)** |
| recommendationservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| paymentservice | 0/713 (0.0%) | 3/717 (0.4%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| emailservice | 300/713 (42.1%) | 122/717 (17.0%) | **┃** | **447/713 (62.7%)** | 115/717 (16.0%) | **┃** | 348/714 (48.7%) |
| productcatalogservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| cartservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| currencyservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| shippingservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| adservice | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |
| redis-cart | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/713 (0.0%) | 0/717 (0.0%) | **┃** | 0/714 (0.0%) |

Checkout is detector-hot on every hold. TopFull on lowers its share from about 82% to about 54%. Email crosses the 0.5 bold line only on rep2 off (62.7%). Its other values are 42.1%, 17.0%, 16.0%, and 48.7%.

## 8. (c) Retry volume

Outbound retry delta by target. Every other target is 0 on every hold.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| checkoutservice | 18,925 | 20,066 | **┃** | 5,908 | 19,120 | **┃** | 16,574 |

Inbound resets, all 11 services.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 54 | 58 | **┃** | 53 | 16 | **┃** | 99 |
| checkoutservice | 22,242 | 13,631 | **┃** | 12,443 | 13,753 | **┃** | 20,473 |
| recommendationservice | 0 | 0 | **┃** | 0 | 1 | **┃** | 1 |
| paymentservice | 1,266 | 780 | **┃** | 439 | 721 | **┃** | 1,342 |
| emailservice | 3,550 | 1,009 | **┃** | 6,290 | 830 | **┃** | 3,925 |
| productcatalogservice | 2 | 0 | **┃** | 9 | 3 | **┃** | 9 |
| cartservice | 1,245 | 753 | **┃** | 484 | 863 | **┃** | 1,106 |
| currencyservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| shippingservice | 1,851 | 1,254 | **┃** | 551 | 1,132 | **┃** | 1,630 |
| adservice | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |
| redis-cart | 0 | 0 | **┃** | 0 | 0 | **┃** | 0 |

## 9. RetryGuard toggles

Two parts. Part 1 is the scorer's log for each hold that toggled. Part 2 summarizes it per callee.

### Part 1: per hold

`ON→OFF` is the shed to 0 attempts. The `0→1` column is the log's `OFF→ON` onto the callee name (`attempts=1`, `from_attempts=0`). `1→2` and `2→3` are the climb lines. `From` is the attempt count before the step, and `Value` is the rpr on a shed or climb line and the rejection on a re-enable line. The tables in this part are the scorer's output, unchanged.

#### rep1 off

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 11 | 0 | 0 | 0 |
| checkoutservice | 0 | 10 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-10T23:49:43Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.56 |
| 2026-10-10T23:50:07Z | checkoutservice | OFF→ON | 0 | rejection 0.04 |
| 2026-10-10T23:50:30Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.77 |
| 2026-10-10T23:51:03Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-10T23:51:26Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.91 |
| 2026-10-10T23:52:04Z | checkoutservice | OFF→ON | 0 | rejection 0.08 |
| 2026-10-10T23:52:28Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.94 |
| 2026-10-10T23:52:53Z | checkoutservice | OFF→ON | 0 | rejection 0.09 |
| 2026-10-10T23:53:18Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.89 |
| 2026-10-10T23:53:41Z | checkoutservice | OFF→ON | 0 | rejection 0.11 |
| 2026-10-10T23:54:05Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.90 |
| 2026-10-10T23:54:28Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-10T23:54:52Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.82 |
| 2026-10-10T23:55:16Z | checkoutservice | OFF→ON | 0 | rejection 0.04 |
| 2026-10-10T23:55:42Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.91 |
| 2026-10-10T23:56:06Z | checkoutservice | OFF→ON | 0 | rejection 0.03 |
| 2026-10-10T23:56:33Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.76 |
| 2026-10-10T23:57:28Z | checkoutservice | OFF→ON | 0 | rejection 0.12 |
| 2026-10-10T23:57:52Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.95 |
| 2026-10-10T23:58:15Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-10T23:58:38Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.93 |

#### rep2 off

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 3 | 0 | 0 | 0 |
| checkoutservice | 0 | 3 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-11T00:41:53Z | frontend → checkoutservice | ON→OFF | 3 | rpr 3.00 |
| 2026-10-11T00:42:44Z | checkoutservice | OFF→ON | 0 | rejection 0.12 |
| 2026-10-11T00:43:08Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.90 |
| 2026-10-11T00:49:49Z | checkoutservice | OFF→ON | 0 | rejection 0.04 |
| 2026-10-11T00:50:13Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.81 |
| 2026-10-11T00:50:54Z | checkoutservice | OFF→ON | 0 | rejection 0.06 |

#### rep1 replay

| Name | ON→OFF | 0→1 | 1→2 | 2→3 |
| --- | ---: | ---: | ---: | ---: |
| frontend → checkoutservice | 9 | 0 | 0 | 0 |
| checkoutservice | 0 | 9 | 0 | 0 |

| Time (UTC) | Name | Step | From | Value |
| --- | --- | --- | ---: | --- |
| 2026-10-11T00:06:59Z | frontend → checkoutservice | ON→OFF | 3 | rpr 2.67 |
| 2026-10-11T00:07:23Z | checkoutservice | OFF→ON | 0 | rejection 0.10 |
| 2026-10-11T00:07:47Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.95 |
| 2026-10-11T00:08:11Z | checkoutservice | OFF→ON | 0 | rejection 0.08 |
| 2026-10-11T00:08:34Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.79 |
| 2026-10-11T00:08:58Z | checkoutservice | OFF→ON | 0 | rejection 0.02 |
| 2026-10-11T00:09:21Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.84 |
| 2026-10-11T00:10:24Z | checkoutservice | OFF→ON | 0 | rejection 0.07 |
| 2026-10-11T00:10:47Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.84 |
| 2026-10-11T00:11:11Z | checkoutservice | OFF→ON | 0 | rejection 0.14 |
| 2026-10-11T00:11:36Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.90 |
| 2026-10-11T00:12:00Z | checkoutservice | OFF→ON | 0 | rejection 0.10 |
| 2026-10-11T00:12:23Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.94 |
| 2026-10-11T00:13:49Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-11T00:14:12Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.94 |
| 2026-10-11T00:14:35Z | checkoutservice | OFF→ON | 0 | rejection 0.01 |
| 2026-10-11T00:14:59Z | frontend → checkoutservice | ON→OFF | 1 | rpr 0.76 |
| 2026-10-11T00:15:44Z | checkoutservice | OFF→ON | 0 | rejection 0.10 |

No transition lines on: rep1 on, rep2 on.

### Part 2: per callee

Only `checkoutservice` toggles in S2. Recommendation, email, and the rest show no transitions on any S2 hold, so they get one sentence here.

The table below comes from `retryguard.log` transitions (`from_attempts` → `attempts`). Time OFF runs from the shed timestamp to the matching `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is minimum / median over the `OBSERVE state=OFF` rejection samples for that window. The under-bar streak is the longest run of consecutive OFF samples below 0.25. An em dash means that edge never went to 0 on that hold.

#### checkoutservice

| | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| ON→OFF / OFF→ON | 11 / 10 | — | **┃** | 3 / 3 | — | **┃** | 9 / 9 |
| Shed rpr | 2.56; 0.77; 0.91; 0.94; 0.89; 0.90; 0.82; 0.91; 0.76; 0.95; 0.93 | — | **┃** | 3.00; 0.90; 0.81 | — | **┃** | 2.67; 0.95; 0.79; 0.84; 0.84; 0.90; 0.94; 0.94; 0.76 |
| Attempts after re-enable | 1 (×10) | — | **┃** | 1 (×3) | — | **┃** | 1 (×9) |
| Time OFF (s) | 24; 33; 38; 25; 23; 23; 24; 24; 55; 23; 6 (to EXIT) | — | **┃** | 51; 401; 41 | — | **┃** | 24; 24; 24; 63; 24; 24; 86; 23; 45 |
| OFF rejection min / median | 0.00 / 0.09; 0.00 / 0.11; 0.00 / 0.11; 0.03 / 0.13; 0.00 / 0.05; 0.00 / 0.03; 0.00 / 0.08; 0.00 / 0.03; 0.01 / 0.12; 0.00 / 0.08; 0.04 / 0.51 | — | **┃** | 0.00 / 0.13; 0.01 / 0.16; 0.00 / 0.06 | — | **┃** | 0.02 / 0.09; 0.02 / 0.09; 0.01 / 0.12; 0.00 / 0.10; 0.00 / 0.07; 0.00 / 0.11; 0.00 / 0.13; 0.00 / 0.05; 0.00 / 0.07 |
| Streak under the bar (s) | 20; 20; 20; 20; 16; 20; 20; 20; 20; 20; 2 | — | **┃** | 20; 20; 20 | — | **┃** | 20; 20; 20; 20; 20; 20; 20; 20; 20 |

Each 0→1 re-enable fired after a streak of 20 under-bar samples, which matches `interval_samples=20`. The one exception is rep1 off, window 5. Its streak is 16 by the table's strict definition, but the log's `consecutive_low` counter reads 17 on that re-enable. The controller's counter tolerates a sample at or above the bar in a way this table does not. The window is kept as scored.

Rep1 off and the replay both cycled 9–11 times. rep2 off cycled 3 times, and its middle OFF window ran 401 s, the longest in the S2 set. Every re-enable reached 1 attempt, and none climbed to 2 or 3, so the 10 s climb never fired. The TopFull-on holds never shed at all, because checkout's rpr streak topped out at 8–9 s and never reached the 20 s `interval_samples`.

#### recommendationservice, emailservice

No ON→OFF or OFF→ON transition on any S2 hold. One sentence, no table.

## 10. Locust goodput

Mean `Goodput` while `RPS > 0`.

| API | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| getproduct | 264.3 | 163.0 | **┃** | 264.4 | 264.0 | **┃** | 264.1 |
| postcheckout | 41.0 | 28.4 | **┃** | 53.2 | 30.5 | **┃** | 43.1 |
| getcart | 96.1 | 60.0 | **┃** | 96.1 | 95.9 | **┃** | 96.0 |
| postcart | 86.5 | 86.4 | **┃** | 86.5 | 86.4 | **┃** | 86.4 |
| emptycart | 4.8 | 4.8 | **┃** | 4.8 | 4.8 | **┃** | 4.8 |

## 11. Locust fail rate

Mean `Fail / RPS` while `RPS > 0`.

| API | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| getproduct | 0.000 | 0.368 | **┃** | 0.000 | 0.000 | **┃** | 0.000 |
| postcheckout | 0.500 | 0.607 | **┃** | 0.368 | 0.584 | **┃** | 0.477 |
| getcart | 0.000 | 0.361 | **┃** | 0.000 | 0.000 | **┃** | 0.000 |
| postcart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 |
| emptycart | 0.000 | 0.000 | **┃** | 0.000 | 0.000 | **┃** | 0.000 |

## 12. Locust P95

Mean `Latency95` (ms) while `RPS > 0`.

| API | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| getproduct | 254 | 118 | **┃** | 308 | 247 | **┃** | 275 |
| postcheckout | 874 | 907 | **┃** | 710 | 983 | **┃** | 860 |
| getcart | 269 | 164 | **┃** | 311 | 261 | **┃** | 283 |
| postcart | 68 | 60 | **┃** | 70 | 67 | **┃** | 70 |
| emptycart | 19 | 22 | **┃** | 13 | 16 | **┃** | 18 |

On rep1, TopFull on lowered getproduct and getcart goodput and raised their fail rates. On rep2, the same TopFull-on arm kept getproduct and getcart at TopFull-off levels. The two replicates disagree on TopFull's effect here.

## 13. Inbound arrival rate

Positive `Δtotal` over the elapsed time of `service_inbound.csv`, req/s.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 491.5 | 329.3 | **┃** | 493.1 | 456.1 | **┃** | 491.7 |
| checkoutservice | 104.4 | 70.4 | **┃** | 86.4 | 69.9 | **┃** | 101.0 |
| recommendationservice | 407.4 | 245.3 | **┃** | 409.0 | 372.2 | **┃** | 407.6 |
| paymentservice | 99.3 | 67.5 | **┃** | 84.7 | 67.4 | **┃** | 95.5 |
| emailservice | 46.0 | 31.1 | **┃** | 65.5 | 33.1 | **┃** | 50.1 |
| productcatalogservice | 2766.9 | 1701.2 | **┃** | 2776.6 | 2555.1 | **┃** | 2768.0 |
| cartservice | 575.1 | 396.5 | **┃** | 573.3 | 524.6 | **┃** | 574.0 |
| currencyservice | 804.9 | 508.2 | **┃** | 798.5 | 761.8 | **┃** | 803.8 |
| shippingservice | 269.9 | 177.9 | **┃** | 252.9 | 212.6 | **┃** | 264.5 |
| adservice | 243.0 | 149.9 | **┃** | 243.0 | 242.6 | **┃** | 243.0 |
| redis-cart | 0.0 | 0.0 | **┃** | 0.0 | 0.0 | **┃** | 0.0 |

## 14. Inbound sojourn

`Δrq_time_sum_ms / Δrq_time_count`, milliseconds. Redis-cart has no sojourn.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 205 | 137 | **┃** | 206 | 168 | **┃** | 210 |
| checkoutservice | 410 | 328 | **┃** | 391 | 324 | **┃** | 414 |
| recommendationservice | 58 | 19 | **┃** | 76 | 57 | **┃** | 62 |
| paymentservice | 6 | 5 | **┃** | 5 | 5 | **┃** | 6 |
| emailservice | 49 | 33 | **┃** | 59 | 32 | **┃** | 62 |
| productcatalogservice | 2 | 1 | **┃** | 2 | 2 | **┃** | 2 |
| cartservice | 4 | 3 | **┃** | 4 | 3 | **┃** | 4 |
| currencyservice | 3 | 2 | **┃** | 3 | 3 | **┃** | 4 |
| shippingservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 |
| adservice | 1 | 1 | **┃** | 1 | 1 | **┃** | 1 |

## 15. Share of inbound requests above 500 ms

From the `rq_time_buckets` `le=500` cumulative count. Redis-cart has no share. Every service not listed is 0.000 on every hold.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 0.101 | 0.048 | **┃** | 0.104 | 0.039 | **┃** | 0.107 |
| checkoutservice | 0.477 | 0.450 | **┃** | 0.298 | 0.399 | **┃** | 0.441 |

## 16. CPU

Per-pod quota / replica mode / mean millicores / max millicores. Mean and max sum `cpu_millicores` across replicas, so frontend can sit above its 1150m per-pod quota.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 1150 / 4 / 1215 / 1572 | 1150 / 4 / 966 / 1292 | **┃** | 1150 / 4 / 1231 / 1585 | 1150 / 4 / 1202 / 1571 | **┃** | 1150 / 4 / 1221 / 1602 |
| checkoutservice | 800 / 1 / 629 / 798 | 800 / 1 / 515 / 798 | **┃** | 800 / 1 / 630 / 798 | 800 / 1 / 507 / 795 | **┃** | 800 / 1 / 627 / 798 |
| recommendationservice | 1150 / 1 / 588 / 765 | 1150 / 1 / 387 / 556 | **┃** | 1150 / 1 / 612 / 819 | 1150 / 1 / 560 / 772 | **┃** | 1150 / 1 / 601 / 819 |
| paymentservice | 155 / 1 / 53 / 78 | 155 / 1 / 40 / 75 | **┃** | 155 / 1 / 51 / 80 | 155 / 1 / 41 / 75 | **┃** | 155 / 1 / 53 / 87 |
| emailservice | 120 / 1 / 55 / 112 | 120 / 1 / 46 / 106 | **┃** | 120 / 1 / 77 / 115 | 120 / 1 / 47 / 110 | **┃** | 120 / 1 / 61 / 115 |
| productcatalogservice | 800 / 1 / 410 / 531 | 800 / 1 / 367 / 482 | **┃** | 800 / 1 / 406 / 523 | 800 / 1 / 409 / 535 | **┃** | 800 / 1 / 409 / 532 |
| cartservice | 800 / 1 / 265 / 362 | 800 / 1 / 259 / 433 | **┃** | 800 / 1 / 270 / 410 | 800 / 1 / 271 / 370 | **┃** | 800 / 1 / 274 / 443 |
| currencyservice | 770 / 1 / 309 / 410 | 770 / 1 / 232 / 314 | **┃** | 770 / 1 / 314 / 413 | 770 / 1 / 307 / 406 | **┃** | 770 / 1 / 312 / 422 |
| shippingservice | 770 / 1 / 81 / 107 | 770 / 1 / 64 / 95 | **┃** | 770 / 1 / 82 / 108 | 770 / 1 / 73 / 107 | **┃** | 770 / 1 / 82 / 107 |
| adservice | 1150 / 1 / 118 / 149 | 1150 / 1 / 92 / 118 | **┃** | 1150 / 1 / 121 / 156 | 1150 / 1 / 121 / 156 | **┃** | 1150 / 1 / 120 / 156 |
| redis-cart | 540 / 1 / 32 / 49 | 540 / 1 / 32 / 48 | **┃** | 540 / 1 / 34 / 51 | 540 / 1 / 33 / 51 | **┃** | 540 / 1 / 32 / 51 |

## 17. CPU as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (quota × replica_count)`. No sample had replica count 0.

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 0.26 / 0.34 | 0.21 / 0.28 | **┃** | 0.27 / 0.34 | 0.26 / 0.34 | **┃** | 0.27 / 0.35 |
| checkoutservice | 0.79 / 1.00 | 0.64 / 1.00 | **┃** | 0.79 / 1.00 | 0.63 / 0.99 | **┃** | 0.78 / 1.00 |
| recommendationservice | 0.51 / 0.67 | 0.34 / 0.48 | **┃** | 0.53 / 0.71 | 0.49 / 0.67 | **┃** | 0.52 / 0.71 |
| paymentservice | 0.34 / 0.50 | 0.26 / 0.48 | **┃** | 0.33 / 0.52 | 0.26 / 0.48 | **┃** | 0.34 / 0.56 |
| emailservice | 0.46 / 0.93 | 0.38 / 0.88 | **┃** | 0.64 / 0.96 | 0.39 / 0.92 | **┃** | 0.51 / 0.96 |
| productcatalogservice | 0.51 / 0.66 | 0.46 / 0.60 | **┃** | 0.51 / 0.65 | 0.51 / 0.67 | **┃** | 0.51 / 0.67 |
| cartservice | 0.33 / 0.45 | 0.32 / 0.54 | **┃** | 0.34 / 0.51 | 0.34 / 0.46 | **┃** | 0.34 / 0.55 |
| currencyservice | 0.40 / 0.53 | 0.30 / 0.41 | **┃** | 0.41 / 0.54 | 0.40 / 0.53 | **┃** | 0.41 / 0.55 |
| shippingservice | 0.11 / 0.14 | 0.08 / 0.12 | **┃** | 0.11 / 0.14 | 0.09 / 0.14 | **┃** | 0.11 / 0.14 |
| adservice | 0.10 / 0.13 | 0.08 / 0.10 | **┃** | 0.11 / 0.14 | 0.11 / 0.14 | **┃** | 0.10 / 0.14 |
| redis-cart | 0.06 / 0.09 | 0.06 / 0.09 | **┃** | 0.06 / 0.09 | 0.06 / 0.09 | **┃** | 0.06 / 0.09 |

## 18. Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).

| Service | rep1 off | rep1 on | **┃** | rep2 off | rep2 on | **┃** | rep1 replay |
| --- | ---: | ---: | :---: | ---: | ---: | :---: | ---: |
| frontend | 0.361 | 0.314 | **┃** | 0.364 | 0.388 | **┃** | 0.364 |
| checkoutservice | 1.042 | 1.048 | **┃** | 1.041 | 1.055 | **┃** | 1.049 |
| recommendationservice | 0.710 | 0.541 | **┃** | 0.734 | 0.708 | **┃** | 0.740 |
| paymentservice | 0.690 | 0.826 | **┃** | 0.800 | 0.723 | **┃** | 0.755 |
| emailservice | 1.025 | 1.042 | **┃** | 1.050 | 1.033 | **┃** | 1.058 |
| productcatalogservice | 0.708 | 0.635 | **┃** | 0.699 | 0.718 | **┃** | 0.696 |
| cartservice | 0.479 | 0.559 | **┃** | 0.546 | 0.501 | **┃** | 0.586 |
| currencyservice | 0.590 | 0.462 | **┃** | 0.616 | 0.596 | **┃** | 0.592 |
| shippingservice | 0.182 | 0.166 | **┃** | 0.178 | 0.173 | **┃** | 0.182 |
| adservice | 0.157 | 0.142 | **┃** | 0.163 | 0.157 | **┃** | 0.163 |
| redis-cart | 0.222 | 0.231 | **┃** | 0.204 | 0.224 | **┃** | 0.246 |

## 19. TopFull live caps

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is an empty read and is left out. `postcart` and `emptycart` are no cap on every live read of every S2 hold.

rep2 off is no cap on every API for the whole window. rep1 off and the rep1 replay both carry a live 166.757 on getproduct and a live 61.4746 on getcart that alternate with no cap about every 5 s; postcheckout is no cap on both. The manifest says the RL loop is off on these holds, and I have not established where those reads come from. The cells keep the scorer's spans, except that a pure two-value alternation is written as one line (value and no cap, span count, first and last span) so the full set of live values is still shown.

rep1 on carries the same alternating 166.757 / 61.4746 pair on getproduct and getcart (see its table). rep2 on has no cap on getproduct and getcart. Both TopFull-on holds carry a moving postcheckout cap, between 10 and 99 across the two.

### rep1 off

| API | Live caps |
| --- | --- |
| getproduct | 166.757 and no cap alternate across 285 spans, from 166.757 23:46:52–23:46:54 through 166.757 23:58:41–23:58:44 |
| postcheckout | no cap 23:46:55–23:58:40 |
| getcart | 61.4746 and no cap alternate across 285 spans, from 61.4746 23:46:52–23:46:54 through 61.4746 23:58:41–23:58:44 |
| postcart | no cap 23:46:55–23:58:40 |
| emptycart | no cap 23:46:55–23:58:40 |

### rep1 on

| API | Live caps |
| --- | --- |
| getproduct | 166.757 00:21:23–00:21:24; no cap at 00:21:25; 166.757 00:21:26–00:21:29; no cap at 00:21:30; 166.757 00:21:31–00:21:34; no cap at 00:21:35; 166.757 00:21:36–00:21:39; no cap at 00:21:40; 166.757 00:21:41–00:21:44; no cap at 00:21:45; 166.757 00:21:46–00:21:49; no cap at 00:21:50; 166.757 00:21:51–00:21:54; no cap at 00:21:55; 166.757 00:21:56–00:21:59; no cap at 00:22:00; 166.757 00:22:01–00:22:04; no cap at 00:22:05; 166.757 00:22:06–00:22:09; no cap at 00:22:10; 166.757 00:22:11–00:22:14; no cap at 00:22:15; 166.757 00:22:16–00:22:19; no cap at 00:22:20; 166.757 00:22:21–00:22:24; no cap at 00:22:25; 166.757 00:22:26–00:22:29; no cap at 00:22:30; 166.757 00:22:31–00:22:34; no cap at 00:22:35; 166.757 00:22:36–00:22:39; no cap at 00:22:40; 166.757 00:22:41–00:22:44; no cap at 00:22:45; 166.757 00:22:46–00:22:49; no cap at 00:22:50; 166.757 00:22:51–00:22:54; no cap at 00:22:55; 166.757 00:22:56–00:22:59; no cap at 00:23:00; 166.757 00:23:01–00:23:04; no cap at 00:23:05; 166.757 00:23:06–00:23:09; no cap at 00:23:10; 166.757 00:23:11–00:23:14; no cap at 00:23:15; 166.757 00:23:16–00:23:19; no cap at 00:23:20; 166.757 00:23:21–00:23:24; no cap at 00:23:25; 166.757 00:23:26–00:23:28; 166.8 00:23:30–00:33:15 |
| postcheckout | no cap 00:21:25–00:23:25; 38 at 00:23:30; 52.8 at 00:23:35; no cap 00:23:40–00:23:45; 74 at 00:23:50; 86.9 at 00:23:51; 84 at 00:23:55; 21.8147 at 00:23:59; 21.8 at 00:24:00; 14.1 at 00:24:05; 54.2 at 00:24:10; no cap at 00:24:15; 37.1 at 00:24:20; 14.2 at 00:24:25; 53.8 at 00:24:30; 99 at 00:24:33; no cap at 00:24:35; 34.8 at 00:24:40; 14.2 at 00:24:45; 53.5 at 00:24:50; 89.9298 at 00:24:53; 70.9 at 00:24:55; 10.5 at 00:25:00; 27.7 at 00:25:05; 38.2282 at 00:25:06; 73.4 at 00:25:10; no cap at 00:25:15; 34.1 at 00:25:20; 10 at 00:25:25; 27.4 at 00:25:30; 99 at 00:25:34; 99 at 00:25:35; 51.9 at 00:25:40; 10 at 00:25:45; 27.8424 at 00:25:48; 38.9 at 00:25:50; 99 at 00:25:55; 52 at 00:26:00; 12.2166 at 00:26:03; 10 at 00:26:05; 14.6611 at 00:26:07; 28.7 at 00:26:10; 76.3 at 00:26:15; 39.8 at 00:26:20; 10 at 00:26:25; 38.2 at 00:26:30; 96.7025 at 00:26:33; 99 at 00:26:35; 21.7 at 00:26:40; 10 at 00:26:42; 18.3 at 00:26:45; 67.8 at 00:26:50; 90 at 00:26:55; 32.4469 at 00:26:59; 32.4 at 00:27:00; 14.2 at 00:27:05; 38.7305 at 00:27:08; 53.8 at 00:27:10; no cap at 00:27:15; 49.0215 at 00:27:18; 30.3 at 00:27:20; 10 at 00:27:23; 14.1 at 00:27:25; 53.6 at 00:27:30; 99 at 00:27:35; 33.5 at 00:27:40; 20.8276 at 00:27:41; 10 at 00:27:45; 38.7 at 00:27:50; 99 at 00:27:55; 52.1 at 00:28:00; 10 at 00:28:05; 27.7866 at 00:28:08; 38.9 at 00:28:10; 99 at 00:28:15; 52.9 at 00:28:20; 12.2375 at 00:28:23; 10 at 00:28:25; 27.7 at 00:28:30; 99 at 00:28:35; 26.1 at 00:28:40; 10 at 00:28:45; 38.5 at 00:28:50; 92.9128 at 00:28:54; 92.9 at 00:28:55; 35.1 at 00:29:00; 14.2 at 00:29:05; 54 at 00:29:10; 99 at 00:29:13; no cap at 00:29:15; 35.1637 at 00:29:19; 35.2 at 00:29:20; 14.2 at 00:29:25; 54 at 00:29:30; no cap 00:29:35–00:29:36; 33 at 00:29:40; 10 at 00:29:45; 14.1236 at 00:29:46; 27.5 at 00:29:50; 95.3 at 00:29:55; 31.4859 at 00:29:59; 31.5 at 00:30:00; 14.2 at 00:30:05; 38.5598 at 00:30:08; 53.7 at 00:30:10; 99 at 00:30:15; 49.2 at 00:30:20; 10 at 00:30:25; 38.8739 at 00:30:29; 38.9 at 00:30:30; 99 at 00:30:35; 50.7 at 00:30:40; 10 at 00:30:45; 14.1085 at 00:30:47; 19.7 at 00:30:50; 73.8 at 00:30:55; 43.5 at 00:31:00; 10 at 00:31:05; 27.6993 at 00:31:08; 38.6 at 00:31:10; 96.2 at 00:31:15; 42.7 at 00:31:20; 10 at 00:31:25; 38.8 at 00:31:30; 89.8 at 00:31:35; 35.2 at 00:31:40; 10 at 00:31:43; 14.1 at 00:31:45; 27.546 at 00:31:47; 53.5 at 00:31:50; no cap at 00:31:55; 31.5 at 00:32:00; 12.0653 at 00:32:02; 14.2 at 00:32:05; 38.9 at 00:32:10; 73.4014 at 00:32:11; 99 at 00:32:15; 52.1 at 00:32:20; 19.7751 at 00:32:21; 10 at 00:32:25; 27.4 at 00:32:30; 96.5 at 00:32:35; 54.5 at 00:32:40; 10 at 00:32:45; 38.4 at 00:32:50; 99 at 00:32:53; 99 at 00:32:55; 51.0079 at 00:32:59; 51 at 00:33:00; 10 at 00:33:05; 23.4184 at 00:33:08; 32.7 at 00:33:10; 99 at 00:33:15 |
| getcart | 61.4746 00:21:23–00:21:24; no cap at 00:21:25; 61.4746 00:21:26–00:21:29; no cap at 00:21:30; 61.4746 00:21:31–00:21:34; no cap at 00:21:35; 61.4746 00:21:36–00:21:39; no cap at 00:21:40; 61.4746 00:21:41–00:21:44; no cap at 00:21:45; 61.4746 00:21:46–00:21:49; no cap at 00:21:50; 61.4746 00:21:51–00:21:54; no cap at 00:21:55; 61.4746 00:21:56–00:21:59; no cap at 00:22:00; 61.4746 00:22:01–00:22:04; no cap at 00:22:05; 61.4746 00:22:06–00:22:09; no cap at 00:22:10; 61.4746 00:22:11–00:22:14; no cap at 00:22:15; 61.4746 00:22:16–00:22:19; no cap at 00:22:20; 61.4746 00:22:21–00:22:24; no cap at 00:22:25; 61.4746 00:22:26–00:22:29; no cap at 00:22:30; 61.4746 00:22:31–00:22:34; no cap at 00:22:35; 61.4746 00:22:36–00:22:39; no cap at 00:22:40; 61.4746 00:22:41–00:22:44; no cap at 00:22:45; 61.4746 00:22:46–00:22:49; no cap at 00:22:50; 61.4746 00:22:51–00:22:54; no cap at 00:22:55; 61.4746 00:22:56–00:22:59; no cap at 00:23:00; 61.4746 00:23:01–00:23:04; no cap at 00:23:05; 61.4746 00:23:06–00:23:09; no cap at 00:23:10; 61.4746 00:23:11–00:23:14; no cap at 00:23:15; 61.4746 00:23:16–00:23:19; no cap at 00:23:20; 61.4746 00:23:21–00:23:24; no cap at 00:23:25; 61.4746 00:23:26–00:23:28; 61.5 00:23:30–00:33:15 |
| postcart | no cap 00:21:25–00:33:15 |
| emptycart | no cap 00:21:25–00:33:15 |

### rep2 off

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:39:05–00:50:55 |
| postcheckout | no cap 00:39:05–00:50:55 |
| getcart | no cap 00:39:05–00:50:55 |
| postcart | no cap 00:39:05–00:50:55 |
| emptycart | no cap 00:39:05–00:50:55 |

### rep2 on

| API | Live caps |
| --- | --- |
| getproduct | no cap 00:56:20–01:08:15 |
| postcheckout | no cap 00:56:20–00:58:30; 54 at 00:58:35; 61 at 00:58:40; 79.2 at 00:58:45; no cap at 00:58:50; 91 at 00:58:55; 46.0991 at 00:58:59; 46.1 at 00:59:00; 10 at 00:59:05; 27.3074 at 00:59:08; 37.4 at 00:59:10; 83.2546 at 00:59:13; 87.4 at 00:59:15; no cap at 00:59:17; 70 at 00:59:18; 42.9 at 00:59:20; 10 00:59:23–00:59:25; 37 at 00:59:30; 84 at 00:59:35; no cap at 00:59:36; 51.6 at 00:59:40; 19.8218 at 00:59:42; 10 at 00:59:45; 19.7 at 00:59:50; 67.4 at 00:59:55; 99 at 01:00:00; 54.1281 at 01:00:04; 54.1 at 01:00:05; 10 at 01:00:10; 27.4 at 01:00:15; 84 at 01:00:20; no cap at 01:00:25; 53 at 01:00:30; 10 at 01:00:35; 37.6 at 01:00:40; 93.6 at 01:00:45; 44.3 at 01:00:50; 16.8884 at 01:00:51; 10 at 01:00:55; 35.7 at 01:01:00; 89.8 at 01:01:05; 41.2268 at 01:01:08; 25.8 at 01:01:10; 14.1 at 01:01:15; 26.657 at 01:01:17; 48 at 01:01:20; 56.9923 at 01:01:21; 91.7 at 01:01:25; 48.8 at 01:01:30; 18.7923 at 01:01:32; 10 at 01:01:35; 19.8 at 01:01:40; 36.6646 at 01:01:41; 65.4 at 01:01:45; 71.3 at 01:01:50; 17.0068 at 01:01:53; 10.5 at 01:01:55; 27.1 at 01:02:00; 49.5649 at 01:02:02; 84.3 at 01:02:05; 86 at 01:02:10; 32.5184 at 01:02:11; 12.5 at 01:02:15; 26.4 at 01:02:20; 78.2 at 01:02:25; no cap at 01:02:30; 53.2097 at 01:02:32; 20.2 at 01:02:35; 14.2 at 01:02:40; 49.6 at 01:02:45; 93.3 at 01:02:50; 90 at 01:02:51; 46.8 at 01:02:55; 10 at 01:03:00; 19.3 at 01:03:05; 63.9 at 01:03:10; no cap 01:03:14–01:03:15; 33.9204 at 01:03:18; 20.9 at 01:03:20; 10 at 01:03:22; 19.3 at 01:03:25; 48.7 at 01:03:30; 70.3681 at 01:03:31; 93.3 at 01:03:35; 53.1 at 01:03:40; 10 at 01:03:45; 16.088 at 01:03:47; 30.5 at 01:03:50; 80.5 at 01:03:55; 83.6766 at 01:03:56; 91.7 at 01:04:00; 33.2 at 01:04:05; 10 at 01:04:10; 14.0951 at 01:04:11; 26.7 at 01:04:15; 76.035 at 01:04:19; 76 at 01:04:20; 74.2138 at 01:04:23; 46.4 at 01:04:25; 10 at 01:04:30; 26.4 at 01:04:35; 77.7 at 01:04:40; 86 at 01:04:45; 12.3 at 01:04:50; 14.9 at 01:04:55; 28.2835 at 01:04:56; 50.9 at 01:05:00; 83.5 at 01:05:05; 17 at 01:05:10; 19.8 at 01:05:15; 64.6 at 01:05:20; 96.4 at 01:05:25; 55.7447 at 01:05:28; 34.7 at 01:05:30; 13.173 at 01:05:32; 10 at 01:05:35; 14.1527 at 01:05:36; 27.1 at 01:05:40; 84.562 at 01:05:44; 84.6 at 01:05:45; 90 at 01:05:50; 33.7 at 01:05:55; 14.2 at 01:06:00; 36.4484 at 01:06:03; 49.2 at 01:06:05; 86.4 at 01:06:10; 96.7703 at 01:06:11; 90 at 01:06:15; 21.3 at 01:06:20; 13.173 at 01:06:21; 10 at 01:06:25; 36.2 at 01:06:30; 95.3838 at 01:06:34; 95.4 at 01:06:35; 51.2 at 01:06:40; 19.6894 at 01:06:42; 10 at 01:06:45; 26.9 at 01:06:50; 80.4 at 01:06:55; no cap at 01:07:00; 18.7 at 01:07:05; 19.2 at 01:07:10; 47.9 at 01:07:15; 90.2 at 01:07:20; 43.3 at 01:07:25; 10 01:07:29–01:07:30; 36.1 at 01:07:35; 92.1 at 01:07:40; no cap 01:07:42–01:07:45; 32.9999 at 01:07:48; 20 at 01:07:50; 19.7 at 01:07:55; 49.2 at 01:08:00; 99 at 01:08:05; 47.9 at 01:08:10; 11.3148 at 01:08:13; 11.3 at 01:08:15 |
| getcart | no cap 00:56:20–01:08:15 |
| postcart | no cap 00:56:20–01:08:15 |
| emptycart | no cap 00:56:20–01:08:15 |

### rep1 replay

| API | Live caps |
| --- | --- |
| getproduct | 166.757 and no cap alternate across 285 spans, from 166.757 00:04:06–00:04:09 through 166.757 00:15:56–00:15:59 |
| postcheckout | no cap 00:04:10–00:15:55 |
| getcart | 61.4746 and no cap alternate across 285 spans, from 61.4746 00:04:06–00:04:09 through 61.4746 00:15:56–00:15:59 |
| postcart | no cap 00:04:10–00:15:55 |
| emptycart | no cap 00:04:10–00:15:55 |

## 20. Per arm, per hold

**rep1 off.** Checkout shed 11 times, from rpr 0.76–2.56, and re-enabled 10 times. The 11th shed ran 6 s to exit. Retry delta into checkout is 18,925. Checkout is detector-hot at 82.2%, email at 42.1%. Goodput is getproduct 264.3, postcheckout 41.0, and postcheckout fail is 0.500.

**rep1 on.** No shed, no re-enable. Checkout's streak is 8 s with controller `high` 9, below the 20 s needed. Checkout is detector-hot at 54.7%. Retry delta into checkout is 20,066, slightly above rep1 off. Getproduct goodput falls to 163.0 with fail 0.368, and getcart falls to 60.0 with fail 0.361. Postcheckout fail is 0.607 and P95 is 907 ms.

**rep2 off.** Checkout shed 3 times and re-enabled 3 times. The middle OFF window ran 401 s, the longest in S2. Retry delta into checkout is only 5,908, the lowest of the five. Email is detector-hot at 62.7%, the only bold email value. Getproduct goodput is 264.4 with fail 0.

**rep2 on.** No shed, no re-enable. Checkout is detector-hot at 53.6%. Retry delta into checkout is 19,120. Getproduct goodput is 264.0, and getcart 95.9, both at rep2 off levels. Postcheckout fail is 0.584 and P95 983 ms.

**rep1 replay.** Repeats rep1 off. Checkout shed 9 times and re-enabled 9 times, against 11 and 10 in the original. Retry delta is 16,574, and checkout is detector-hot at 82.5%. Goodput is close to rep1 off on getproduct and getcart. Postcheckout fail is 0.477, against 0.500 in the original.

Across the five holds, RetryGuard acted only on TopFull-off holds, and only on checkout. The TopFull-on holds never shed because checkout's sustained rpr never reached the 20 s interval. That is what keeps rep1 on and rep2 on from producing any toggles. `grpc_4 / grpc_14` is 0 / 0 on every controlled gRPC callee on every hold, so no gRPC rejection fed the controller.

## 21. Related

- [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md), edge-mode section
- Previous same-mix guide, re-enable and climb settings at 0.25 with tighter climb bars: [2026-10-10-s2-rr025-climb-analysis.md](2026-10-10-s2-rr025-climb-analysis.md)
- Plan and run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)
