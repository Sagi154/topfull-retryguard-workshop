# S2 tuning holds (2026-10-11): reenable 0.25, interval 20 s, climb 10 s

Analysis of the four S2 tuning holds plus one replay of hold 1, scored with `experiments/analysis_score.py --sep 2`. Follows [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md). Run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md).

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

The replay repeats the rep1 off configuration as a separate run. Its numbers are shown beside rep1 off, not averaged into it.

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

The scorer printed no replica-change or zero-replica line for any S2 hold. The CPU table's replica mode is 4 for frontend and 1 for every other service, which matches the pin. I did not re-read `service_capacity.json` in this pass.

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

Only `checkoutservice` toggles in S2. Recommendation, email, and the rest show no transitions on any S2 hold, so they get one sentence here.

The table below comes from `retryguard.log` transitions (`from_attempts` → `attempts`). Time OFF runs from the shed timestamp to the matching `OFF→ON`, or to `EXIT` when the edge is still at 0. OFF rejection is minimum / median over the `OBSERVE state=OFF` rejection samples for that window. The under-bar streak is the longest run of consecutive OFF samples below 0.25. An em dash means that edge never went to 0 on that hold.

### checkoutservice

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

### recommendationservice, emailservice

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

A live read has `threshold_fresh=1` and threshold above 0. 10000 is no cap. A live 0 is left out. The scorer collapsed the long series, so I list spans only.

- **rep2 off:** no live cap on any API for the whole window (00:39:05–00:50:55).
- **rep1 off and rep1 replay:** the scorer reports live reads on getproduct (166.757) and getcart (61.4746). They alternate with "no cap" every 5 s, from 23:46:52 to 23:58:44 on rep1, and 00:04:06 to 00:15:59 on the replay. postcheckout, postcart, and emptycart are no cap throughout. **These reads are unexplained.** The manifest says TopFull is off on these holds. I have not checked the source of those reads.
- **rep1 on:** postcart and emptycart are no cap. getproduct is 166.757 until 00:23:28, then 166.8 to 00:33:15. getcart is 61.5 from 00:23:30. postcheckout has live caps from 00:23:30 onward, between 10 and 99, too long to list here.
- **rep2 on:** getproduct, getcart, postcart, and emptycart are no cap. postcheckout has live caps from 00:58:35 onward, between 10 and 99, too long to list here.

## 20. Per arm, per hold

**rep1 off.** Checkout shed 11 times, from rpr 0.76–2.56, and re-enabled 10 times. The 11th shed ran 6 s to exit. Retry delta into checkout is 18,925. Checkout is detector-hot at 82.2%, email at 42.1%. Goodput is getproduct 264.3, postcheckout 41.0, and postcheckout fail is 0.500.

**rep1 on.** No shed, no re-enable. Checkout's streak is 8 s with controller `high` 9, below the 20 s needed. Checkout is detector-hot at 54.7%. Retry delta into checkout is 20,066, slightly above rep1 off. Getproduct goodput falls to 163.0 with fail 0.368, and getcart falls to 60.0 with fail 0.361. Postcheckout fail is 0.607 and P95 is 907 ms.

**rep2 off.** Checkout shed 3 times and re-enabled 3 times. The middle OFF window ran 401 s, the longest in S2. Retry delta into checkout is only 5,908, the lowest of the five. Email is detector-hot at 62.7%, the only bold email value. Getproduct goodput is 264.4 with fail 0.

**rep2 on.** No shed, no re-enable. Checkout is detector-hot at 53.6%. Retry delta into checkout is 19,120. Getproduct goodput is 264.0, and getcart 95.9, both at rep2 off levels. Postcheckout fail is 0.584 and P95 983 ms.

**rep1 replay.** Repeats rep1 off. Checkout shed 9 times and re-enabled 9 times, against 11 and 10 in the original. Retry delta is 16,574, and checkout is detector-hot at 82.5%. Goodput is close to rep1 off on getproduct and getcart. Postcheckout fail is 0.477, against 0.500 in the original.

Across the five holds, RetryGuard acted only on TopFull-off holds, and only on checkout. The TopFull-on holds never shed because checkout's sustained rpr never reached the 20 s interval. That is what keeps rep1 on and rep2 on from producing any toggles.

## 21. Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md)
- [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md)
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md), edge-mode section
- Previous same-mix guide, re-enable and climb settings at 0.25 with tighter climb bars: [2026-10-10-s2-rr025-climb-analysis.md](2026-10-10-s2-rr025-climb-analysis.md)
- Plan and run log: [2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md](../docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md)
