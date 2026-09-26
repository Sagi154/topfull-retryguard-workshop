# S2 both-off holds — no RetryGuard, no TopFull (2026-09-24)

Five flat 600 s holds with the Go proxy up, `deploy_rl.py` not started, and RetryGuard not started. Istio stayed at `attempts: 3`. These are **not** 48-run matrix rows. Folders:

`experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run{3,4,5,6,7}`

The mixed roster that also includes the TopFull-on holds from 2026-09-22–23 is [2026-09-24-s2-system-load-holds-summary.md](2026-09-24-s2-system-load-holds-summary.md). This note is only the both-off series.

Earlier folders on the same YAML counter are out of this window: **run1** (2026-09-15 TopFull-off control, different pin) and **run2** (frontend μ calibration). YAML next free after this series: **run8**.

Locust `Fail` is a 1 s SLO miss, not Boutique 5xx. Mesh failure is inbound `Δ(5xx + resets) / Δtotal`. Checkout 5xx stayed 0; checkout failure is inbound resets. Frontend failure is mostly 5xx.

Two windows, labeled where they are used:

- **Steady** (`compare_runs.py`): drop the first 60 s and the last 10 s. Locust means, inbound λ / fail / sojourn, simultaneous-overload, machine cores.
- **Whole hold**: first-to-last counter delta. RetryGuard-length streaks (consecutive 1 s samples with rejection > 0.20; a disable needs 30) and Layer B overloaded tick counts.

---

## Shared setup

| Item | Value |
|---|---|
| Loadgen | `online_boutique_create_v2.sh`, five independent swarms, `spawn_rate` **50** (Ron's divisor: `-r = count / 50`) |
| Machines | worker `e2-standard-16`; master and load `e2-standard-8` |
| Frontend | pinned **4 / 4** for every resource sample (sidecar request 90 m so four pods would schedule; app limit 1150 m) |
| Other replicas | 1; catalog HPA max 1 |
| Layer A | threshold **10000** on every API (passthrough; 0 fresh caps below 9999) |
| Cool-off | 300 s between the afternoon holds (run5 → run6 → run7) |

Counts are **getproduct / postcheckout / getcart / postcart / emptycart**.

| Run | Start (UTC) | Counts | Role | Master cores p95 / max | Worker cores p95 / max | Load cores p95 / max |
|---|---|---|---|---|---|---|
| **3** | 2026-09-24 10:00 | **300 / 100 / 210 / 20 / 20** | morning | 5.21 / 5.78 of 8 | 11.62 / 11.97 of 16 | 1.05 / 1.89 of 8 |
| **4** | 10:40 | **380 / 100 / 270 / 20 / 20** | morning, more browse | 4.82 / 5.49 of 8 | 11.92 / 12.43 of 16 | 1.20 / 1.90 of 8 |
| **5** | 11:16 | **300 / 100 / 210 / 20 / 20** | replay of 3 | 5.09 / 5.79 of 8 | 11.50 / 12.77 of 16 | 1.07 / 1.75 of 8 |
| **6** | 11:38 | **340 / 100 / 240 / 10 / 10** | halfway browse; cart tags cut to 10 | 5.28 / 6.15 of 8 | 11.94 / 12.54 of 16 | 1.15 / 2.02 of 8 |
| **7** | 12:00 | **380 / 100 / 270 / 20 / 20** | replay of 4 | 5.23 / 5.96 of 8 | 12.16 / 12.58 of 16 | 1.42 / 2.46 of 8 |

VM cores are the steady window. Master comes from `__master_node__` in `resource_usage.csv`. Worker and load come from `worker_cpu.txt` and `load_cpu.txt` (`top` idle, converted to cores). Frontend replicas were 133/133 at 4 except run5 (134/134). Hottest Locust process was 26–32% of one core on runs 3–6 and 45% on run7. None of the three machines is pegged.

---

## Verdict

A useful uncontrolled S2 mix needs two things at once: a **30-tick** inbound streak on more than one service (what RetryGuard would disable on), and those same services **Layer B overloaded** for most of the hold (what TopFull's detector would call hot).

| Run | Checkout streak / Layer B | Rec streak / Layer B | Both? |
|---|---|---|---|
| 3 | **592** / 591 of 636 | 1 / 38 of 636 | Checkout only |
| 4 | **49** / 552 of 636 | 13 / **565** of 636 | Two Layer B services; rec streak short |
| 5 | **90** / 106 of 638 | **288** / 515 of 638 | Two streaks; checkout not Layer B-hot |
| **6** | **177** / **476** of 637 | **44** / **558** of 637 | **Yes — both streaks and both Layer B** |
| 7 | **230** / 572 of 636 | 15 / 511 of 636 | Two Layer B services; rec streak still 15 |

**run6** (`340 / 100 / 240 / 10 / 10`) is the only hold that clears both gates. Currency never went `overloaded`. Payment's longest streak was 7 (run3) and its overloaded count stayed at 0 after run3's 5 ticks.

Same counts did not replay in the afternoon:

- **run3 vs run5.** Morning checkout was the hot service (streak 592, rec cool). The replay made recommendations the long streak (288) and left checkout Layer B-hot on only 106 ticks. Frontend inbound fail rose from 0.09 to **0.61**.
- **run4 vs run7.** Both kept checkout and recommendations Layer B-hot together (simultaneous-overload mean 1.91 and 1.86). Checkout's streak got longer (49 → 230). Rec's streak stayed short (13 → 15).

---

## Locust storefront (steady window)

`Goodput = RPS − Fail`. System P95 is `total.csv` `Latency95` (the mean of the five endpoint P95s for that second), then averaged over the window.

| Run | Rows | System goodput | System SLO rej. | System P95 (ms) | getproduct gp / P95 / Fail÷RPS | getcart gp / P95 / Fail÷RPS | postcheckout gp / P95 / Fail÷RPS |
|---|---:|---:|---:|---:|---|---|---|
| 3 | 570 | 497 | 0.10 | 773 | 268 / 767 / ~0 | 191 / 527 / ~0 | 0 / 2453 / **1.00** |
| 4 | 571 | 261 | 0.53 | 1289 | 117 / 2108 / 0.56 | 94 / 1998 / 0.52 | 25 / 2262 / 0.62 |
| 5 | 572 | 102 | 0.75 | 1259 | 38 / 2060 / 0.79 | 28 / 1976 / 0.79 | 5 / 2171 / 0.92 |
| 6 | 569 | 212 | 0.58 | 1380 | 107 / 2085 / 0.57 | 84 / 1948 / 0.55 | 10 / 2787 / 0.82 |
| 7 | 569 | 273 | 0.51 | 1306 | 131 / 1997 / 0.51 | 103 / 1826 / 0.48 | 17 / 2619 / 0.70 |

Run3 is the only hold where browse stayed inside the SLO. Raising browse (run4, and the afternoon replays) moved getproduct and getcart P95 to about 2 s. postcheckout missed the SLO on every hold; on run3 it missed every second.

`postcart` / `emptycart` tracked their offer (about 19 and 17 req/s on the 20-user holds, about 9 on run6) with P95 under 90 ms.

---

## Mesh inbound and outbound retries (steady window)

Sojourn `W` is this hop's `downstream_rq_time`, not Locust end-to-end latency. Outbound `Δretry` is the sum of Envoy `retry` deltas on every edge inside the steady window.

| Run | FE λ / fail / W ms | Checkout λ / fail / W ms | Rec λ / fail / W ms | Outbound Δretry |
|---|---|---|---|---:|
| 3 | 515 / 0.09 / 496 | 141 / **0.55** / 496 | 479 / ~0 / 135 | 57,168 |
| 4 | 420 / 0.21 / 810 | 48 / **0.21** / 223 | 638 / **0.20** / 455 | 157,810 |
| 5 | 381 / **0.61** / 1044 | 29 / **0.37** / 297 | 751 / **0.27** / 449 | 257,157 |
| 6 | 395 / 0.28 / 918 | 64 / **0.46** / 351 | 651 / **0.21** / 457 | 187,572 |
| 7 | 420 / 0.18 / 809 | 63 / **0.38** / 320 | 610 / 0.18 / 449 | 148,852 |

Extra browse users did not raise checkout arrival. Checkout λ fell from 141 on run3 to the 30–60 band on every later hold, while recommendations λ rose from 479 into the 600–750 band. The retry volume follows that shift: run3 is the small, checkout-dominated delta; run4 onward is a recommendations storm (run4's whole-hold split was about 153 k frontend→recommendations and 7 k frontend→checkout).

Catalog, cart, currency, shipping, and ad inbound failure stayed ~0. Currency sojourn on run3 was 48 ms and fell to 3–11 ms after that.

---

## CPU and replicas (whole `resource_usage.csv`)

App containers. Quotas: frontend 1150 m × 4 replicas, checkout 615 m, recommendations 1150 m.

| Run | FE CPU mean / max (m) | Checkout CPU mean / max | Rec CPU mean / max | Rec / checkout mem max |
|---|---|---|---|---|
| 3 | 1308 / 1528 | **540 / 614** | 751 / 884 | 56 / 95 MB |
| 4 | 1348 / 1675 | 508 / 611 | **886 / 1063** | 75 / 75 MB |
| 5 | 990 / 1552 | 239 / 612 | **963 / 1150** | 89 / 77 MB |
| 6 | 1258 / 1660 | 492 / 613 | **911 / 1130** | 91 / 72 MB |
| 7 | 1334 / 1687 | 521 / 613 | **863 / 1072** | 91 / 72 MB |

Checkout sat on its 615 m limit whenever it was the Layer B service (runs 3, 4, 6, 7) and dropped to a 239 m mean on run5, matching the Layer B miss. Recommendations pegged its 1150 m quota only on run5. Frontend CPU per pod stays well under 1150 m because the 1300–1700 m figure is the deployment total across 4 replicas.

Steady-window utilization p95 (CPU / limit, replica-adjusted) agrees: checkout ≥ 0.99 on every hold; recommendations crosses 0.85 from run4 on (0.76 on run3). Frontend utilization p95 stays about 0.33.

---

## Layer B

Layer B `overloaded` is cAdvisor CPU vs the paper quota × α = 0.8. Tick counts are the whole file. "At once" is the steady window.

| Run | Checkout ov / util max | Rec ov / util max | At once (max / mean) |
|---|---|---|---|
| 3 | 591/636 / 1.06 | 38/636 / 0.85 | 2 / 1.08 |
| 4 | 552/636 / 1.04 | 565/636 / 0.97 | 2 / 1.91 |
| 5 | 106/638 / 1.05 | 515/638 / 1.01 | 2 / 1.05 |
| 6 | 476/637 / 1.05 | 558/637 / 1.00 | 2 / 1.76 |
| 7 | 572/636 / 1.05 | 511/636 / 1.00 | 2 / 1.86 |

Per-VM cores for each run are in the roster above. **Do not upgrade the VMs from these holds.** VMs were stopped after run7.

---

## What to take forward

1. Use **run6's mix** (`340 / 100 / 240 / 10 / 10`) if the next step is a both-on hold. It is the only both-off folder where checkout and recommendations would each have disabled retries **and** each stayed Layer B-hot.
2. Do not treat run3's checkout streak (592) as a stable property of `300 / 100 / 210 / 20 / 20`. Run5, same counts and same pin, put the long streak on recommendations and cooled checkout.
3. Do not raise browse past run4/run7. That pair does keep two Layer B services, but recommendations never holds 30 consecutive ticks above 0.20 (streak 13, then 15), and frontend sojourn sits near 800 ms with browse P95 near 2 s.
4. Layer A at 10000 is expected: TopFull's RL process was not running. A later both-on run of the run6 mix is what shows whether admission control removes these streaks.
