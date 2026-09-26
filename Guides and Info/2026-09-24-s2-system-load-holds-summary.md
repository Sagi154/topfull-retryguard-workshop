# S2 system-load holds — 2026-09-22 → 2026-09-23

Task 9 S2 tries under the Ron-config / `online_boutique_create_v2.sh` regime. These are **not** new 48-run matrix rows. Folders live under `experiments/results/campaign_48/S2_sustained_overload/`.

This note uses the three measurement layers in [METRICS-GATHERED.md](METRICS-GATHERED.md). Locust `Fail` is a 1 s SLO miss (or a non-OK status), **not** Boutique 5xx. `Latency99` is unused. Mesh rejection is inbound `Δ(5xx + resets) / Δtotal`. Outbound retries are `service_edges.csv` `Δretry` within the run (Envoy counters are cumulative across the campaign).

Locust means below drop the first 30 s and the last 10 s. Inbound λ / failure / sojourn use the whole `service_inbound.csv` span unless a number is tagged as coming from that run's `rho_estimate_report.md` (tick-filtered `w_mean_ms` / `w_p50_ms`).

---

## Shared setup

| Item | Value |
|---|---|
| Scenario | S2 sustained overload, **flat 600 s** hold |
| Loadgen | `online_boutique_create_v2.sh` — five independent single-tag swarms |
| `spawn_rate` | **50** on every hold (Ron's divisor: Locust `-r = count / 50`, not users/sec) |
| Worker | `e2-standard-16`; master / load `e2-standard-8` |
| CPU quotas | Ron-config paper table (frontend 1150 m, checkout 615 m, recommendations 1150 m, catalog 1535 m, …) |
| Collectors | Locust CSVs + full-mesh Envoy + `resource_usage.csv` + Layer A/B throttle |
| Next free YAML slots after this window | S2 baseline **run31**, S2 RetryGuard **run16**, S2 RetryGuard-without-TopFull **run3**, both-off control **run14** |

`spawn_rate: 50` is a **slow ramp**. A 300-user tag reaches its plateau in about 6 s (`300 / 50 = 6` users/sec). It is not a 50 users/sec spawn.

---

## Roster and user counts

Counts are always **getproduct / postcheckout / getcart / postcart / emptycart**.

| Hold | When (UTC) | Arm | Counts | Frontend replicas | Other services | Folder |
|---|---|---|---|---|---|---|
| Baseline **24** | 2026-09-22 20:50 | TopFull on, RG off | **100 / 60 / 100 / 50 / 50** | HPA 1→3 (mode 3; never 4) | 1 | `baseline_topfull_no_retryguard_sustained_overload_run24` |
| Baseline **25** | 2026-09-22 21:30 | TopFull on, RG off | **200 / 60 / 140 / 50 / 50** | HPA 1→3 (mode 3) | 1 | `…_run25` |
| Baseline **26** | 2026-09-23 17:19 | TopFull on, RG off | **250 / 60 / 180 / 50 / 50** | HPA 1→2 (mode 2) | 1 | `…_run26` |
| Baseline **27** | 2026-09-23 18:24 | TopFull on, RG off | **250 / 60 / 180 / 50 / 50** | **Pinned 4 / 4** (134/134 samples) | 1; catalog HPA max 1 | `…_run27` |
| RetryGuard **13** | 2026-09-23 19:23 | TopFull on, RG on | **250 / 60 / 180 / 50 / 50** | Pinned 4 / 4 (138/138) | 1; catalog HPA max 1 | `run_topfull_retryguard_sustained_overload_run13` |
| Baseline **28** | 2026-09-23 19:45 | TopFull on, RG off | **300 / 60 / 210 / 50 / 50** | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `…_run28` |
| RetryGuard **14** | 2026-09-23 20:24 | TopFull on, RG on | **300 / 80 / 180 / 50 / 50** | Pinned 4 / 4 (140/140) | 1; catalog HPA max 1 | `run_topfull_retryguard_sustained_overload_run14` |
| Baseline **29** | 2026-09-23 20:47 | TopFull on, RG off | **300 / 80 / 180 / 50 / 50** | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `…_run29` |
| RG, **no TopFull RL** run1 | 2026-09-23 21:26 | TopFull **off**, RG on | **300 / 60 / 210 / 50 / 50** (same as 28) | Pinned 4 / 4 (139/139) | 1; catalog HPA max 1 | `run_retryguard_no_topfull_sustained_overload_run1` |
| Both-off **run3** | 2026-09-24 10:00 | TopFull **off**, RG **off** | **300 / 100 / 210 / 20 / 20** | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run3` |
| Both-off **run4** | 2026-09-24 10:40 | TopFull **off**, RG **off** | **380 / 100 / 270 / 20 / 20** | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run4` |
| Both-off **run5** | 2026-09-24 11:16 | TopFull **off**, RG **off** | **300 / 100 / 210 / 20 / 20** (replay of 3) | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run5` |
| Both-off **run6** | 2026-09-24 11:38 | TopFull **off**, RG **off** | **340 / 100 / 240 / 10 / 10** (halfway) | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run6` |
| Both-off **run7** | 2026-09-24 12:00 | TopFull **off**, RG **off** | **380 / 100 / 270 / 20 / 20** (replay of 4) | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run7` |
| RG-only **run2** | 2026-09-24 14:55 | TopFull **off**, RG **on** | **340 / 100 / 240 / 5 / 5** | Pinned 4 / 4 (142/142) | 1; catalog HPA max 1 | `run_retryguard_no_topfull_sustained_overload_run2` |
| Baseline **30** | 2026-09-24 15:20 | TopFull on, RG off | **340 / 100 / 240 / 5 / 5** | Pinned 4 / 4 (135/135) | 1; catalog HPA max 1 | `baseline_topfull_no_retryguard_sustained_overload_run30` |
| RetryGuard **15** | 2026-09-24 15:46 | TopFull on, RG on | **340 / 100 / 240 / 5 / 5** | Pinned 4 / 4 (142/142) | 1; catalog HPA max 1 | `run_topfull_retryguard_sustained_overload_run15` |
| Both-off **run8** | 2026-09-24 16:47 | TopFull **off**, RG **off** | **300 / 60 / 300 / 30 / 5** | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run8` |
| Both-off **run9** | 2026-09-24 17:42 | TopFull **off**, RG **off** | **250 / 80 / 250 / 100 / 5** | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run9` |
| Both-off **run10** | 2026-09-24 18:03 | TopFull **off**, RG **off** | **325 / 80 / 100 / 100 / 5** | Pinned 4 / 4 (133/133) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run10` |
| Both-off **run11** | 2026-09-24 18:24 | TopFull **off**, RG **off** | **250 / 100 / 100 / 100 / 5** | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run11` |
| Both-off **run12** | 2026-09-24 18:46 | TopFull **off**, RG **off** | **100 / 150 / 100 / 100 / 5** | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run12` |
| Both-off **run13** | 2026-09-24 19:07 | TopFull **off**, RG **off** | **50 / 150 / 50 / 100 / 5** | Pinned 4 / 4 (134/134) | 1; catalog HPA max 1 | `baseline_no_topfull_sustained_overload_run13` |

Pinned holds used the frontend sidecar request **90 m** workaround so four frontend pods would schedule (node requests were ~10 m over allocatable at a 100 m sidecar request). App-container limit stayed 1150 m. HPAs were restored after each pair (frontend min 1 / max 4, catalog max 2, sidecar annotation removed).

A first launch of try 3 died before Locust (CRLF in the deployed v2 script) and was **not** kept. `deploy_repo_script` now strips CR.

---

## Layer 1 — Locust storefront (`total.csv` + five API CSVs)

`RPS` is offered load (also the best proxy for TopFull's admitted load). `Goodput = RPS − Fail`. Storefront rejection is derived `Fail / RPS`. `total.csv` P95 is the **mean of the five endpoint P95s**, not a system-wide percentile.

| Hold | Locust rows | System goodput | System SLO rej. | System P95 (ms) | getproduct gp / P95 / Fail÷RPS | getcart gp / P95 / Fail÷RPS | postcheckout gp / P95 / Fail÷RPS |
|---|---:|---:|---:|---:|---|---|---|
| Base 24 | 557 | 327 | 0.08 | 491 | 99 / 693 / ~0 | 99 / 602 / ~0 | 28 / 886 / **0.51** |
| Base 25 | 562 | 387 | 0.21 | 606 | 150 / 992 / 0.23 | 123 / 907 / 0.11 | 16 / 820 / **0.74** |
| Base 26 | 565 | **156** | **0.67** | 829 | **13 / 1355 / 0.93** | **39 / 1226 / 0.73** | 16 / 1051 / 0.69 |
| Base 27 | 563 | 335 | 0.36 | 1107 | 130 / **1737** / 0.40 | 97 / 1579 / 0.39 | 16 / **2094** / 0.65 |
| RG 13 | 566 | 503 | 0.14 | 310 | 226 / 587 / 0.08 | 167 / 420 / 0.07 | 10 / 387 / **0.82** |
| Base 28 | 563 | 532 | 0.12 | 625 | 242 / 728 / 0.11 | 177 / 461 / 0.09 | 20 / 1784 / 0.50 |
| RG 14 | 563 | 567 | 0.08 | 360 | 280 / 730 / ~0 | 170 / 484 / ~0 | 22 / 453 / 0.71 |
| Base 29 | 566 | 567 | 0.10 | 369 | 281 / 705 / ~0 | 173 / 518 / ~0 | 16 / 484 / 0.79 |
| RG no-TF | 569 | 320 | 0.41 | 1170 | 122 / 1988 / 0.48 | 93 / 1838 / 0.45 | 24 / 1922 / 0.49 |
| Both-off 3 | 571 | 497 | 0.10 | 773 | 268 / 767 / ~0 | 191 / 527 / ~0 | 0 / 2453 / **1.00** |
| Both-off 4 | 571 | 267 | 0.52 | 1280 | 121 / **2070** / 0.54 | 97 / **1951** / 0.51 | 23 / 2300 / 0.63 |
| Both-off 5 | 572 | 120 | 0.71 | 1235 | 49 / 1993 / 0.74 | 35 / 1898 / 0.74 | 5 / 2191 / **0.92** |
| Both-off 6 | 569 | 218 | 0.57 | 1367 | 110 / 2047 / 0.56 | 86 / 1911 / 0.53 | 10 / **2798** / 0.83 |
| Both-off 7 | 569 | 279 | 0.50 | 1294 | 135 / 1959 / 0.50 | 106 / 1784 / 0.47 | 16 / 2637 / 0.71 |

`postcart` / `emptycart` stayed near their 50-user offer (~45–50 req/s, P95 usually < 300 ms) on every TopFull-on hold. They only degraded when the frontend itself was 5xx-ing (run 27 and the no-TopFull control).

---

## Layer 1 — mesh inbound + outbound retries

Inbound sojourn (`W`) is this hop's own `downstream_rq_time`, not Locust end-to-end latency. Failure is `Δ(5xx + resets) / Δtotal`. Checkout 5xx stayed **0** on these holds — checkout "failure" is almost all inbound **resets**. Frontend failure, when it exists, is mostly **5xx**.

| Hold | FE λ / fail / W mean (P50) | Checkout λ / fail / W | Rec λ / fail / W | Outbound Δretry (hot edge) |
|---|---|---|---|---|
| Base 24 | 276 / 0.009 / 255 (174) | 32 / **0.117** / 246 | 196 / ~0 / 91 | **3,191** FE→checkout |
| Base 25 | 376 / 0.001 / 356 (222) | 15 / 0.017 / 69 | 292 / ~0 / 90 | 240 (231 FE→checkout) |
| Base 26 | 380 / 0.002 / **853 (1257)** | 18 / ~0 / 92 | 303 / ~0 / 101 | **5** (no storm) |
| Base 27 | 435 / **0.233** / 641 (799) | 38 / **0.208** / 185 | 545 / **0.135** / 377 | **138,558** (130,531 FE→rec + 8,027 FE→checkout) |
| RG 13 | 417 / 0.001 / 259 (271) | 10 / 0.030 / 64 | 336 / 0.0006 / 144 | 572 (378 FE→checkout) |
| Base 28 | 470 / 0.029 / 350 (328) | 63 / **0.296** / 381 | 392 / ~0 / 141 | **20,254** FE→checkout |
| RG 14 | 465 / 0.001 / 304 (315) | 19 / 0.022 / 72 | 387 / ~0 / 165 | 476 (475 FE→checkout) |
| Base 29 | 484 / 0.001 / 321 (336) | 16 / 0.024 / 68 | 402 / 0.001 / 204 | 573 (439 FE→checkout) |
| RG no-TF | 436 / **0.255** / 653 (807) | 26 / 0.003 / 94 | 569 / **0.135** / 437 | **143,350** (143,252 FE→rec) |
| Both-off 3 | 528 / 0.094 / 490 (414) | 145 / **0.554** / 489 (749) | 491 / ~0 / 133 (119) | **57,168** (checkout-dominated) |
| Both-off 4 | 432 / **0.213** / 803 (846) | 49 / **0.207** / 220 (149) | 657 / **0.202** / 439 (479) | **160,447** (153,093 FE→rec) |
| Both-off 5 | 391 / **0.609** / 1045 (1304) | 36 / **0.371** / 179 (89) | 774 / **0.276** / 429 (716) | **257,157** |
| Both-off 6 | 406 / **0.280** / 903 (903) | 67 / **0.467** / 327 (644) | 668 / **0.210** / 439 (483) | **187,572** |
| Both-off 7 | 430 / **0.183** / 806 (835) | 64 / **0.378** / 314 (252) | 627 / **0.185** / 434 (461) | **148,852** |

`W` mean / P50 in this table are from each folder's `rho_estimate_report.md`. Whole-file first-to-last `Δrq_time_sum / Δrq_time_count` is in the same ballpark.

---

## Layer 2 — CPU, memory, replicas (`resource_usage.csv`)

App containers only (istio-proxy skipped). `replica_count` is Deployment `readyReplicas`. [METRICS-GATHERED.md](METRICS-GATHERED.md) still says this is always 1; that is stale for frontend under HPA.

| Hold | FE replicas | FE CPU mean / max (m) | Checkout CPU mean / max | Rec CPU mean / max | Rec / checkout mem max |
|---|---|---|---|---|---|
| Base 24 | 1–3 (mode 3) | 661 / 1705 | 471 / 615 | 411 / 519 | 104 / 77 MB |
| Base 25 | 1–3 (mode 3) | 827 / 1077 | 302 / 608 | 587 / 706 | 105 / 67 MB |
| Base 26 | 1–2 (mode 2) | 650 / 751 | 285 / 491 | 567 / 681 | 106 / 47 MB |
| Base 27 | **4 / 4** | 1187 / 1469 | 413 / 612 | **862 / 1115** | 121 / 82 MB |
| RG 13 | 4 / 4 | 1215 / 1524 | 204 / 600 | 717 / 977 | 121 / 65 MB |
| Base 28 | 4 / 4 | 1203 / 1412 | **520 / 612** | 726 / 865 | 115 / 77 MB |
| RG 14 | 4 / 4 | 1091 / 1337 | 297 / 583 | 619 / 762 | 117 / 71 MB |
| Base 29 | 4 / 4 | 1226 / 1441 | 262 / 603 | 694 / 822 | 117 / 75 MB |
| RG no-TF | 4 / 4 | 1210 / 1498 | 385 / 600 | **836 / 1072** | 127 / 61 MB |
| Both-off 3 | **4 / 4** (133/133) | 1308 / 1528 | **540 / 614** | 751 / 884 | 57 / 95 MB |
| Both-off 4 | **4 / 4** (133/133) | 1348 / 1675 | 508 / 611 | **886 / 1063** | 75 / 75 MB |
| Both-off 5 | **4 / 4** (134/134) | 990 / 1552 | 239 / 612 | **963 / 1150** | 89 / 77 MB |
| Both-off 6 | **4 / 4** (133/133) | 1258 / 1660 | 492 / 613 | **911 / 1130** | 91 / 72 MB |
| Both-off 7 | **4 / 4** (133/133) | 1335 / 1687 | 521 / 613 | **863 / 1072** | 91 / 72 MB |

Catalog, cart, currency, payment stayed at **1 replica** on every hold. Catalog CPU never approached its 1535 m quota.

---

## Layer 3 — TopFull (Layer A throttle + Layer B detector)

Layer A: `topfull_throttle.csv`. `threshold = 10000` is the passthrough sentinel (uncapped). Real caps below use `threshold_fresh == 1` and `0 < threshold < 9999`. Fresh-scrape counts vary a lot (14 on run 26 / 29 vs 600+ on run 13 / 28) — skipped ticks still write a row with `*_fresh = 0`.

Layer B: `topfull_detect.csv`. `overloaded` reconstructs `Detector.detect()` (cAdvisor CPU vs quota × α). Quota is the live paper map (checkout 615 m, α = 0.8; frontend 1150 m, α = 0.8; recommendations 1150 m, α = 0.8).

| Hold | Layer A last real cap | Layer B hottest | Overloaded ticks |
|---|---|---|---|
| Base 24 | **postcheckout 27.9** (min 10; 154 fresh caps). Browse open. | Checkout util max 1.06 | Checkout **463 / 638** |
| Base 25 | postcheckout **11.6** (min 10). Brief getproduct cap ~199. | Checkout 1.04; FE 0.85 | Checkout 80 / 638; FE 16 / 638 |
| Base 26 | postcheckout **20.2** on **1** fresh sample. Browse open. Only 14 fresh Layer A rows. | Checkout 0.91; FE 0.71 | Checkout **5 / 637** |
| Base 27 | postcheckout **58.5** (min 10). getproduct last 250, getcart last 180 (near the offer — not a hard starve). | Rec **0.99**; checkout 1.05 | Rec **444 / 638**; checkout 253 / 638 |
| RG 13 | postcheckout **10** (min 10, 569 fresh caps). Browse briefly ~228 / 168 then open. | Rec 0.91; checkout 1.03 | Rec 113 / 663; checkout **26 / 663** |
| Base 28 | postcheckout last **49** (min 10, 50 fresh). getcart held at **177** for 567 fresh samples. | Checkout **1.06**; rec 0.85 | Checkout **575 / 638**; rec 15 / 638 |
| RG 14 | postcheckout **21** (min 21, only 7 fresh caps). Browse **open** (10000). | Checkout 1.01; rec **0.72** (below 0.80 gate) | Checkout 30 / 666; rec **0** |
| Base 29 | postcheckout **11.9** (min 11.9, 5 fresh). Browse open. | Checkout 1.00; rec 0.77 | Checkout 24 / 637; rec **0** |
| RG no-TF | **all APIs 10000** the whole hold (`deploy_rl.py` not started) | Rec **1.00**; checkout 1.01 | Rec **529 / 662**; checkout 175 / 662 |
| Both-off 3 | **all APIs 10000** (`deploy_rl.py` not started; 65 fresh, share-capped 0) | Checkout **1.06**; rec 0.85 | Checkout **591 / 636**; rec 38 / 636; currency **0** |
| Both-off 4 | **all APIs 10000** (`deploy_rl.py` not started; 65 fresh, share-capped 0) | Rec **0.97**; checkout 1.04 | Rec **565 / 636**; checkout **552 / 636**; currency **0** |
| Both-off 5 | **all APIs 10000** (`deploy_rl.py` not started; 70 fresh, share-capped 0) | Rec **1.01**; checkout 1.05 | Rec **515 / 638**; checkout 106 / 638; payment **0** |
| Both-off 6 | **all APIs 10000** (`deploy_rl.py` not started; 65 fresh, share-capped 0) | Rec **1.00**; checkout 1.05 | Rec **558 / 637**; checkout **476 / 637**; payment **0** |
| Both-off 7 | **all APIs 10000** (`deploy_rl.py` not started; 65 fresh, share-capped 0) | Checkout **1.05**; rec 1.00 | Checkout **572 / 636**; rec **511 / 636**; payment **0** |

`num_agent.csv` is empty on these folders (same as the rest of the campaign). Use Locust `RPS` / Layer A `admitted_rps` as the admission proxy.

---

## Layer 3 — RetryGuard (`retryguard.log`)

Controller: 1 s samples, disable after **30** consecutive samples with inbound rejection ≥ **0.20**, re-enable after 30 consecutive below 0.20. It reads `service_inbound.csv`, not Locust.

| Hold | START / SHUTDOWN | ON→OFF | OFF→ON | Hottest streak (need 30) |
|---|---|---:|---:|---|
| Base 24–29 | n/a (baseline) | — | — | — |
| RG 13 | yes / yes | **0** | **0** | checkout **7 / 30** (max rej 0.44; 7 samples ≥ 0.20) |
| RG 14 | yes / yes | **0** | **0** | checkout **6 / 30** (max rej 0.51; 6 samples ≥ 0.20) |
| RG no-TF | yes / yes | **0** | **0** | recommendations **2 / 30** (29 samples ≥ 0.20, never consecutive) |
| Both-off 3 | n/a (RG off) | — | — | checkout **592 / 30** (fail 0.554; scored from `service_inbound.csv`) |
| Both-off 4 | n/a (RG off) | — | — | checkout **49 / 30** (fail 0.207); rec **13 / 30** (fail 0.202) |
| Both-off 5 | n/a (RG off) | — | — | rec **288 / 30** (fail 0.276); checkout **90 / 30** (fail 0.371) |
| Both-off 6 | n/a (RG off) | — | — | checkout **177 / 30** (fail 0.467); rec **44 / 30** (fail 0.210) |
| Both-off 7 | n/a (RG off) | — | — | checkout **230 / 30** (fail 0.378); rec **15 / 30** (fail 0.185) |

RetryGuard **ran and never patched** on the RG-on holds in this window. Zero `ON→OFF` is not "retries were off." Istio stayed at `attempts: 3`. The difference between a 138 k-retry baseline and a 500-retry RG hold is **TopFull admission**, not RetryGuard. Both-off run3 did not start the controller; the 592-tick checkout streak is what RetryGuard would have seen. Both-off run4 likewise: checkout streak **49** (still a disable) and rec streak **13**.

---

## What we noticed

### 1. Raising Locust users first queued the frontend, not the backends

Tries 1–3 (runs 24–26) left frontend on HPA. Browse SLO got worse as counts rose, but **mesh inbound 5xx/resets on recommendations stayed ~0**. Run 26 is the clearest case: getproduct `Fail / RPS = 0.93` while every backend inbound failure is ~0 and outbound retry Δ is **5**. The storefront was missing the 1 s SLO because frontend sojourn was ~850 ms mean / **1257 ms P50**, with only **2** frontend replicas and CPU max **751 m** — well under the 1150 m quota. The bottleneck was frontend queueing, not a saturated checkout/rec.

Run 24 already had a live checkout (inbound fail 0.12, 3.2 k FE→checkout retries, Layer B overloaded 463 ticks) at the *lowest* user counts. Adding browse users (25, then 26) **starved checkout** (λ 32 → 15 → 18) and moved pain onto the frontend.

### 2. Pinning frontend at 4 (run 27) is what produced a backend storm

Same counts as run 26 (**250 / 60 / 180 / 50 / 50**), but frontend readyReplicas = 4 for the whole hold. Offered λ reached the backends:

- recommendations inbound fail **0.13**, sojourn 377 ms, Layer B overloaded **444 / 638**, **130 k** FE→rec retries
- checkout inbound fail **0.21**, sojourn 185 ms, **8 k** FE→checkout retries
- frontend itself started 5xx-ing (inbound fail **0.23**)
- getproduct goodput recovered (13 → 130) but P95 got worse (1355 → 1737)

This is the only TopFull-on hold in the window where **recommendations** both rejected and turned Layer B overloaded for most of the run.

### 3. Same counts + same pin do not replay — TopFull RL is the random variable

Runs **27** and **RG 13** used the same Locust mix and the same replica pin. Outcomes are not close:

| | Base 27 | RG 13 |
|---|---|---|
| System goodput | 335 | 503 |
| FE→rec retries | 130,531 | 194 |
| Checkout inbound fail | 0.21 | 0.030 |
| Rec inbound fail | 0.13 | ~0 |
| Layer A postcheckout last cap | **58.5** | **10** |
| Layer B rec overloaded | 444 | 113 |

RetryGuard never disabled on run 13, so it did not cause the gap. Layer A admitted far less postcheckout on the RG hold (cap 10 vs 58.5). That starved checkout, which also cut the rec fan-out that run 27 amplified with retries. This is the same non-repeatable admission we saw later: run 28's getcart cap of 177 vs run 14/29 leaving browse at the 10000 sentinel.

### 4. Retries in "the baselines" were not a RetryGuard-off effect

It looked odd that runs 27 and 28 had huge retry Δ and RG 13/14 did not. RetryGuard never issued `ON→OFF` on 13 or 14, so Istio retries stayed **on** in every arm. Envoy only retries when the callee fails. When TopFull holds postcheckout at ~10–21 req/s, checkout inbound failure stays ~0.02–0.03 and there is nothing to retry. When TopFull lets more through (run 27 cap 58.5, run 28 last cap 49 with checkout λ 63), checkout/rec fail and the 3-attempt policy lights up.

### 5. Raising getproduct/getcart (run 28) moved the storm onto checkout, not recommendations

Counts **300 / 60 / 210 / 50 / 50**, still pinned. Goal was "keep checkout + rec results, add another TopFull-hot service." What happened:

- checkout inbound fail **0.30**, FE→checkout retries **+20,254**, Layer B checkout overloaded **575 / 638**
- recommendations fail **~0**, util max 0.85, only 15 overloaded ticks
- currency util max stayed ~0.57 (never overloaded)
- Layer A held **getcart at 177** for most fresh samples — that is why rec did not replay run 27

Browse goodput looked "better" than run 27 (getproduct 242 vs 130, P95 728 vs 1737) because the bottleneck had moved off the frontend/rec path and onto checkout.

### 6. Raising postcheckout instead of getcart (RG 14 + base 29) starved checkout again

Counts **300 / 80 / 180 / 50 / 50**. Both arms look like each other, not like 27 or 28:

- checkout inbound fail **0.022 / 0.024**
- rec fail ~0, util max **0.72 / 0.77** (below the 0.80 Layer B gate)
- Layer A capped **only postcheckout** (last 21 then 12); browse stayed at 10000
- RG 14 high streak **6 / 30** — still nowhere near a disable
- outbound retries 476 / 573, almost all FE→checkout

More postcheckout users did **not** raise admitted checkout λ. TopFull absorbed the extra offer at the proxy.

### 7. TopFull-off control (same mix as run 28) put the storm back on recommendations

`run_retryguard_no_topfull_sustained_overload_run1`: proxy up, `deploy_rl.py` not started, Layer A threshold **10000** on every API.

- checkout inbound fail fell from **0.30 → 0.003**; FE→checkout retries **20,254 → 98**
- recommendations inbound fail **0.135**, **143,252** FE→rec retries, Layer B overloaded 529 / 662
- frontend inbound fail **0.25**, sojourn 653 ms
- RetryGuard still **zero ON→OFF** — recommendations had 29 samples ≥ 0.20 but max consecutive high streak **2 / 30**

So: **without TopFull**, rec fails the way run 27 did. **With TopFull**, the RL often starves the path that would have produced a 30-sample hold. RetryGuard's 30 s window is slower than the flicker of inbound rejection, even when the whole-run failure fraction is 0.13.

### 8. Frontend replica pin was applied **before** every hold from 27 onward

Runs 27, RG 13, 28, RG 14, 29, and the no-TopFull control all started with frontend already at 4. The huge spread among 27–29 is **not** "HPA turned on at different times." It is load-mix changes plus TopFull's non-deterministic Layer A decisions.

Runs 24–26 were the opposite: HPA was free, and it never reached 4 (max 3, then 2). That is why run 26's frontend stayed slow at low CPU.

### 9. Both-off run3 (300 / 100 / 210 / 20 / 20) put a 30 s RetryGuard hold on checkout

Same frontend pin as the later window. Browse stayed at the no-TF run1 point (`300 / 210`); postcheckout rose 60 → 100; postcart / emptycart fell 50 → 20. Neither controller ran.

- checkout inbound fail **0.554**, sojourn 489 ms (P50 749), consecutive rejection > 0.20 for **592** ticks. RetryGuard would have disabled.
- Layer B checkout overloaded **591 / 636** (util max 1.06). Checkout is the TopFull service and the RetryGuard service on this mix.
- recommendations inbound fail **~0**, λ **491** vs **665** on no-TF run1, overloaded only **38 / 636**. Currency util mean 0.59 / p95 0.72 — never overloaded. The second and third TopFull services did not stay hot.
- Browse storefront recovered vs no-TF run1: getproduct goodput **268** / P95 **767** vs 122 / 1988. postcheckout goodput **0** / P95 **2453** — every checkout SLO missed.
- Outbound retry Δ **57,168** (checkout-dominated), vs 143 k FE→rec on no-TF run1.
- Machines (`compare_runs.py`): master **5.21 / 5.78** of 8; worker **11.62 / 11.97** of 16; load **1.05 / 1.89** of 8 (hottest Locust 29%). All stay in the replica-probe band. **Do not upgrade VMs from this hold.**

Raising postcheckout with both controllers off moved the storm onto checkout and cooled recommendations. A later both-on run of this mix can test whether TopFull admission or RetryGuard disable is what keeps checkout out of the 0.20 band.

### 10. Both-off run4 (380 / 100 / 270 / 20 / 20) put recommendations on Layer B without a 30-tick rec streak

Same frontend pin. Browse rose +80 getproduct / +60 getcart vs run3; postcheckout stayed 100; cart-only tags stayed 20. Neither controller ran.

- recommendations inbound fail **0.202**, λ **657** vs **491** on run3 (and **665** on no-TF run1), sojourn 439 ms (P50 479). Layer B overloaded **565 / 636** (util max 0.97). Consecutive rejection > 0.20 lasted only **13 / 30** — same flicker as no-TF run1's streak of 2, now at a higher whole-run fail.
- checkout inbound fail **0.207**, λ **49** vs **145** on run3, consecutive rejection > 0.20 for **49** ticks. RetryGuard would still have disabled. Layer B checkout overloaded **552 / 636**. Extra browse starved some checkout work but did not cool it off the 0.20 / 0.80 gates.
- Two services overloaded at once (max **2**, mean **1.91**): checkout + recommendations. Currency util max 0.77 — never overloaded.
- Frontend inbound fail **0.213**, sojourn **803 ms** (P50 846) vs run3 **0.094 / 490**. Browse storefront dropped: getproduct goodput **121** / P95 **2070** vs run3 268 / 767. Extra users added concurrency and frontend 5xx more than they added rec RPS.
- Outbound retry Δ **160,447** (153,093 FE→rec + 7,354 FE→checkout), vs 57 k checkout-dominated on run3 and 143 k FE→rec on no-TF run1.
- Machines (`compare_runs.py`): master **4.82 / 5.49** of 8; worker **11.92 / 12.43** of 16; load **1.20 / 1.90** of 8 (hottest Locust 28.5%). All stay in the replica-probe band. **Do not upgrade VMs from this hold.**

The browse raise reached recommendations (second TopFull service) and kept a checkout RetryGuard-length streak. Rec itself still cannot hold 30 consecutive ticks above 0.20. Do not raise browse again: frontend already shed toward the no-TF run1 sojourn band, and checkout λ already fell.

### 11. Afternoon trio (run5 replay 3, run6 halfway, run7 replay 4)

Same pin, 300 s cool-off between holds, both controllers off. Run5 and run7 reuse this morning's counts. Run6 is the new mix (`340 / 100 / 240 / 10 / 10`).

| | run3 morning | run5 replay | run6 halfway | run4 morning | run7 replay |
|---|---|---|---|---|---|
| Counts | 300/100/210/20/20 | same | 340/100/240/10/10 | 380/100/270/20/20 | same |
| Checkout streak / fail / ov | 592 / 0.554 / 591 | **90 / 0.371 / 106** | **177 / 0.467 / 476** | 49 / 0.207 / 552 | **230 / 0.378 / 572** |
| Rec streak / fail / ov | 0 / ~0 / 38 | **288 / 0.276 / 515** | **44 / 0.210 / 558** | 13 / 0.202 / 565 | **15 / 0.185 / 511** |
| FE fail / W ms | 0.094 / 490 | **0.609 / 1045** | 0.280 / 903 | 0.213 / 803 | 0.183 / 806 |
| Machines p95 (m/w/l) | 5.21 / 11.62 / 1.05 | 5.09 / 11.50 / 1.07 | 5.28 / 11.94 / 1.15 | 4.82 / 11.92 / 1.20 | 5.23 / 12.16 / 1.42 |

- **run3 vs run5 did not replay.** Same counts, same pin: this morning rec was cool (38 ov ticks); the afternoon replay made rec the RetryGuard service (streak **288**) and left checkout Layer B-hot only 106 / 638. Frontend sojourn jumped to **1045 ms** / fail **0.609**. Today's cluster is harsher on browse than 10:00 UTC.
- **run4 vs run7 is a successful Layer B replay.** Two services overloaded (checkout 572, rec 511). Checkout streak **230** (stronger than this morning's 49). Rec streak still **15 / 30** — same flicker as run4's 13.
- **run6 is the only hold where both services would trip RetryGuard** (checkout 177, rec 44) and both stay Layer B-hot (476 / 558). Cart tags at 10 took some frontend work off; checkout λ 67 sits between run5's 36 and run7's 64. Payment still 0 overloaded ticks.
- Machines: master p95 5.1–5.3 of 8, worker 11.5–12.2 of 16, load 1.1–1.4 of 8. **Do not upgrade VMs.** VMs stopped after this trio.

If the next both-on run needs one mix, use **run6** (`340 / 100 / 240 / 10 / 10`): two TopFull services and two RetryGuard-length streaks on an uncontrolled hold.

### 12. Controller trio (RG-only, TF-only, both) on 340 / 100 / 240 / 5 / 5

Same pin, 300 s cool-offs, cart tags 5 (run6 sibling was 10). Folders: `run_retryguard_no_topfull_sustained_overload_run2`, `baseline_topfull_no_retryguard_sustained_overload_run30`, `run_topfull_retryguard_sustained_overload_run15`.

| | both-off run6 | RG-only run2 | TF-only run30 | both-on run15 |
|---|---|---|---|---|
| Counts | 340/100/240/10/10 | 340/100/240/5/5 | same | same |
| Checkout fail / streak / Layer B ov | 0.467 / 177 / 476 | **0.423 / 36 / 499** | **0.018 / 5 / 266** | **0.015 / 2 / 53** |
| Rec fail / streak / Layer B ov | 0.210 / 44 / 558 | **0.180 / 41 / 306** | **0.257 / 286 / 570** | **0.183 / 31 / 383** |
| FE fail / W ms | 0.280 / 903 | 0.240 / 956 | 0.330 / 940 | 0.170 / 835 |
| Layer A | 10000 | **10000** (0 real caps) | postcheckout last **43.7** (min 11.6); browse share-capped | postcheckout share-capped **0.975** (thresh ~280); browse ~9884 |
| `retryguard.log` | n/a | **15 ON→OFF / 14 OFF→ON** (checkout + rec) | n/a | **3 ON→OFF / 3 OFF→ON** (rec only) |
| Machines p95 (m/w/l) | 5.28 / 11.94 / 1.15 | 5.05 / 12.21 / 1.30 | 6.43 / 11.02 / 1.82 | 6.66 / 12.02 / 1.48 |

- **RG-only:** Layer A stayed at 10000. RetryGuard actually patched: checkout **7×** ON→OFF and recommendations **8×**. Checkout last disable was still OFF at SHUTDOWN. This mix is not "RG-inert" once TopFull is off.
- **TF-only:** TopFull absorbed checkout (fail 0.018, streak 5) while recommendations stayed in the disable band (streak **286**) and Layer B-hot (570/640). A later both-on quiet checkout is TopFull, not a light mix.
- **Both-on:** both controllers engaged. TopFull still starved checkout (fail 0.015, no toggle, Layer B only 53 ticks). RetryGuard still disabled recommendations **3×**. Not the run13/14 "zero ON→OFF under live TopFull" story — rec held 31 consecutive ticks above 0.20.
- Machines: master p95 5.1–6.7 of 8, worker 11.0–12.2 of 16, load 1.3–1.8 of 8. **Do not upgrade VMs.** VMs stopped after this trio.

### 13. Both-off run8 (300 / 60 / 300 / 30 / 5)

Same pin. Proxy up, `deploy_rl.py` skipped, RetryGuard off. Layer A stayed at **10000** (0 real caps). Locust 568 rows. Frontend replicas 4/4 on 133/133 samples.

- Frontend inbound fail **0.785**, sojourn **1413 ms**, streak **572**. Browse storefront Fail/RPS **0.92** (getproduct goodput **10**, getcart **11**, P95 ~2180 ms). Total goodput **48** req/s.
- Recommendations λ **761**, fail **0.171**, streak only **6 / 30**, Layer B overloaded **574 / 636** (util max 1.02). Outbound retries **343,548**, all frontend→recommendations (0.66 per first attempt).
- Checkout λ **3.7**, fail **0**, streak **0**, Layer B **6 / 636**. postcheckout goodput **2.2**. The checkout path never got a sustained arrival rate.
- Machines p95: master **3.82 / 5.62** of 8, worker **9.09 / 10.02** of 16, load **1.10 / 1.93** of 8 (locust 35.5%). **Do not upgrade VMs.**

### 14. Both-off sweep run9–run13

Same pin, 300 s cool-offs, both controllers off. Layer A stayed at **10000**. Frontend replicas 4 on every resource sample.

| | run9 | run10 | run11 | run12 | run13 |
|---|---|---|---|---|---|
| Counts | 250/80/250/100/5 | 325/80/100/100/5 | 250/100/100/100/5 | 100/150/100/100/5 | 50/150/50/100/5 |
| Checkout streak / fail / ov | 5 / 0.195 / 22 | 21 / 0.068 / 53 | **38** / 0.239 / 57 | **89** / 0.413 / 266 | **65** / 0.402 / 244 |
| Rec streak / fail / ov | 25 / 0.204 / 576 | **56** / 0.253 / 561 | 22 / 0.201 / 560 | 0 / 0 / 0 | 0 / 0 / 0 |
| FE streak / fail | 577 / 0.720 | 565 / 0.417 | 561 / 0.605 | 122 / 0.280 | 181 / 0.372 |
| FE→rec retries | 343,801 | 265,285 | 286,223 | 0 | 0 |
| FE→checkout retries | 384 | 1,458 | 2,854 | 47,538 | 45,209 |

Runs 9–11 keep recommendations detector-hot. Run10 is the only one of those with a recommendations streak of 30. Runs 12 and 13, with postcheckout at 150 and getproduct cut to 100 then 50, move the retries onto checkout and leave recommendations cold. HPAs restored. VMs stopped after the sweep.

---

## Short read of the window

1. **S2 is not locked.** We do not yet have a repeatable "sustained overload" mix where recommendations stay in RetryGuard's disable band **and** another service keeps TopFull Layer B hot, under live TopFull, with frontend pinned.
2. The only TopFull-on hold that really overloaded recommendations was **baseline 27**. Repeating its counts with RetryGuard on (**RG 13**) did not replay it.
3. Raising browse users (**28**) overloads checkout and is absorbed on getcart; raising checkout users (**14 / 29**) is absorbed on postcheckout. Both leave rec cool.
4. Turning TopFull off (**no-TF run1**) brings the rec storm back but still does not give RetryGuard a 30-sample hold.
5. Both-off **run3** (`300 / 100 / 210 / 20 / 20`) is the first hold in this window with a 30-tick RetryGuard signal: checkout streak **592**. Checkout is also Layer B overloaded for almost the whole hold. Recommendations and currency stayed cool. Master / worker / load CPU does not justify a VM upgrade.
6. Both-off **run4** (`380 / 100 / 270 / 20 / 20`) is the first both-off hold with **two** Layer B-hot services (rec 565 / 636, checkout 552 / 636) and still a checkout RetryGuard streak (**49**). Rec fail is 0.202 but the high streak is only **13 / 30**. Frontend sojourn jumped to 803 ms.
7. Afternoon trio: **run5 did not replay run3** (rec streak 288, frontend fail 0.61). **run7 did replay run4's two Layer B services** (checkout streak 230, rec streak 15). **run6** (`340 / 100 / 240 / 10 / 10`) is the only hold with two RetryGuard-length streaks (checkout 177, rec 44) plus two Layer B-hot services. Prefer that mix for a later both-on run. Machines still do not justify a VM upgrade; VMs stopped after the trio.
8. Controller trio on `340 / 100 / 240 / 5 / 5`: **RG-only** patched checkout and rec (15 ON→OFF). **TF-only** collapsed checkout fail to 0.018 and left rec streak 286. **Both-on** still capped checkout and still disabled rec 3×. Quiet checkout under TopFull is admission, not a missing RetryGuard.
9. Do not treat Locust `Fail / RPS` as mesh rejection. Run 26 is the teaching example (SLO 0.93, mesh fail ~0).
10. Do not treat "low retries on an RG folder" as RetryGuard working. Check `retryguard.log` for `ON→OFF` first.
11. Both-off **run8** (`300 / 60 / 300 / 30 / 5`) pinned the failure on the frontend (fail 0.785, streak 572, sojourn 1413 ms) and left checkout idle (λ 3.7). Recommendations was Layer B-hot (574/636) but the rejection streak was only 6/30. Retry Δ 343,548, all frontend→recommendations.
12. Both-off **run9–run13**: recommendations stays detector-hot through run11 and goes cold on run12–run13 once postcheckout is 150 and getproduct falls to 100 then 50. Checkout's streak clears 30 on run11, run12, and run13. Layer A stays at 10000.

Task 9 S2 remains open. S6 has not been started.
