# S2 run 89 mix, four arms, edge rpr

600 s holds, mix getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1. Two holds per arm. Folders are under `experiments/results/campaign_48/S2_sustained_overload/`.

rpr is `Δretry / (Δtotal − Δretry)` on each consecutive pair of `service_edges.csv` rows for one `(caller, target)`. The 14 edges are `CONTROLLED_EDGES` in `experiments/retryguard.py`. A pair is scored when first attempts `(Δtotal − Δretry)` are above 0. The mean, the ticks above 0.5, the streak, and the retry delta use scored pairs only. A streak is consecutive scored ticks with rpr > 0.5. A scored tick at or below 0.5 ends it. **Bold** is a streak of at least 30, the controller's `interval_samples`.

An edge is listed when any scored tick has rpr > 0.5, or when its retry delta is neither 0 nor 2. Every other edge on that hold has retry delta 0 and no tick above 0.5, and those edges share one line. `checkoutservice → productcatalogservice` has no scored tick on any of these eight holds.

Locust counts are lines in `total.csv`, and the header line is included. A tick is one row-pair for that edge, on the collector's clock. `frontend → checkoutservice` is 1 s apart on slots 155 and 156 (697 and 657 rows) and 2 s apart on slots 11, 12, 37, 38, 22, and 23 (442, 428, 354, 351, 367, and 366 rows).

## Slot 155

RetryGuard off, TopFull off, slot 155 (`baseline_no_topfull_sustained_overload_run155`). Locust `total.csv` 563 lines (header included).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → cartservice | 0.0007 | 0.4000 | 0 | 0 | 4 |
| frontend → checkoutservice | 0.2419 | 4.4000 | 64 | **64** | 6,753 |
| frontend → recommendationservice | 0.6045 | 2.1801 | 395 | **60** | 139,534 |
| The other 11 edges | — | — | 0 | 0 | 0 |

## Slot 156

RetryGuard off, TopFull off, slot 156 (`baseline_no_topfull_sustained_overload_run156`). Locust `total.csv` 564 lines (header included).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 1.3966 | 3.9375 | 337 | **202** | 40,053 |
| frontend → recommendationservice | 0.3632 | 3.1502 | 165 | **61** | 70,136 |
| The other 12 edges | — | — | 0 | 0 | 0 |

## Slot 11

RetryGuard on, TopFull off, slot 11 (`run_retryguard_no_topfull_sustained_overload_run11`). Locust `total.csv` 566 lines (header included). ON→OFF 3 / OFF→ON 3 (`frontend→checkoutservice` 1, `frontend→recommendationservice` 2; each OFF→ON is that callee's rejection fallback).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.2762 | 2.7671 | 43 | **31** | 7,997 |
| frontend → recommendationservice | 0.4762 | 2.1115 | 171 | **32** | 112,016 |
| The other 12 edges | — | — | 0 | 0 | 0 |

On this hold the checkout edge's retry counter moved 7,999 from the first row to the last. The table's 7,997 is the sum on scored pairs. The other 2 landed on a skipped pair.

## Slot 12

RetryGuard on, TopFull off, slot 12 (`run_retryguard_no_topfull_sustained_overload_run12`). Locust `total.csv` 565 lines (header included). ON→OFF 1 / OFF→ON 1 (`frontend→checkoutservice`; the OFF→ON is the `checkoutservice` rejection fallback).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.2248 | 2.7654 | 31 | **31** | 6,644 |
| frontend → recommendationservice | 0.4591 | 1.4609 | 150 | 23 | 116,243 |
| The other 12 edges | — | — | 0 | 0 | 0 |

## Slot 37

RetryGuard off, TopFull on, slot 37 (`baseline_topfull_no_retryguard_sustained_overload_run37`). Locust `total.csv` 555 lines (header included).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.4535 | 3.9000 | 60 | 5 | 10,789 |
| frontend → recommendationservice | 0.0508 | 1.0029 | 17 | 4 | 12,016 |
| The other 12 edges | — | — | 0 | 0 | 0 |

## Slot 38

RetryGuard off, TopFull on, slot 38 (`baseline_topfull_no_retryguard_sustained_overload_run38`). Locust `total.csv` 555 lines (header included).

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.6278 | 3.8710 | 86 | 5 | 15,006 |
| frontend → recommendationservice | 0.0209 | 1.2027 | 3 | 3 | 4,785 |
| The other 12 edges | — | — | 0 | 0 | 0 |

## Slot 22

RetryGuard on, TopFull on, slot 22 (`run_topfull_retryguard_sustained_overload_run22`). Locust `total.csv` 556 lines (header included). ON→OFF 0 / OFF→ON 0.

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.5315 | 3.6889 | 72 | 5 | 13,031 |
| frontend → recommendationservice | 0.0628 | 1.2271 | 19 | 6 | 13,813 |
| The other 12 edges | — | — | 0 | 0 | 0 |

## Slot 23

RetryGuard on, TopFull on, slot 23 (`run_topfull_retryguard_sustained_overload_run23`). Locust `total.csv` 556 lines (header included). ON→OFF 0 / OFF→ON 0.

| Edge | Mean rpr | Max rpr | Ticks above 0.5 | Longest streak | Retry delta |
|---|---:|---:|---:|---:|---:|
| frontend → checkoutservice | 0.7677 | 3.9143 | 106 | 5 | 18,728 |
| The other 13 edges | — | — | 0 | 0 | 0 |
