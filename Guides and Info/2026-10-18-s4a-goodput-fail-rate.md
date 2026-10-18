# S4A goodput and fail rate (2026-10-18)

Same columns as [2026-10-18-s3-goodput-fail-rate.md](2026-10-18-s3-goodput-fail-rate.md). Each API has two tables. The first table is the pooled row. The second table is one row per run. Constrained and unconstrained are separate.

Holds: the folders under `experiments/results/final_runs_results/S4A_topology_position_burst` and `S4A_topology_position_normal`. `analysis_4a_constrained_both_normal_run1` is left out: health line **RL STALL** (two `RL_RPS_TIMEOUT` lines). The other 25 are `health: ok` and not throttle-flagged.

Constrained is two clean holds per group. The pinned matrix was two holds per variant. The 2026-10-17 replay added the third hold on the unconstrained variants only. `both_normal` also has `run1` on disk; that folder is the RL STALL hold left out above, so its clean pair is `run2` and `run3`.

A shed is an `ON→OFF` line in `retryguard.log`. A cap is a Locust second whose threshold in force is under 9900. On the 15 unconstrained holds RetryGuard never shed and TopFull never capped, so they are one pool. The pool is `both_burst` `run1`–`run3`, `rg_only_burst` `run1`–`run3`, `both_normal` `run1`–`run3`, `rg_only_normal` `run1`–`run3`, and `tf_only` `run1`–`run3`. Every clean constrained hold with RetryGuard on did shed, and every clean constrained hold with TopFull on did cap, so those stay on their own rows.

Goodput and the effective-cap percentages use the same definitions as `variant_summary.py` (`experiments/variant_summary.py`). This file also includes `postcart`, the 600-user entry in the locked S4A mix. That tool's tables are `getproduct`, `getcart`, and `postcheckout`. Fail rate is Locust `Fail / RPS` on seconds with `RPS` > 0, the same seconds as `analysis_score.locust_table`. Goodput is req/s. A blank effective percentage means TopFull is off. The unconstrained percentage is recomputed from the TopFull-on runs in that pool. Column definitions: [VARIANT-SUMMARY.md](VARIANT-SUMMARY.md).

The pooled row gives each run equal weight. With two runs, each median is the midpoint of the two run medians. With 15 runs, each median is the middle of the 15 run medians.

## getproduct

### Pooled

| Topology | Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `run1`, `run2` | 3.0 | 0.0 | 28.6 | 19.8 | 0.906 | 1.000 |
| constrained | burst, RetryGuard only | `run1`, `run2` | 1.8 | 0.2 | — | — | 0.926 | 0.995 |
| constrained | normal, both | `run2`, `run3` | 6.1 | 5.8 | 27.0 | 19.7 | 0.839 | 0.879 |
| constrained | normal, RetryGuard only | `run1`, `run2` | 1.7 | 0.2 | — | — | 0.932 | 0.992 |
| constrained | TopFull only | `run1`, `run2` | 5.6 | 3.2 | 25.9 | 21.9 | 0.849 | 0.924 |
| unconstrained | no shed, no cap | 15 clean holds | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Topology | Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `analysis_4a_constrained_both_burst_run1` | 3.9 | 0.0 | 28.6 | 20.0 | 0.888 | 1.000 |
| constrained | burst, both | `analysis_4a_constrained_both_burst_run2` | 2.0 | 0.0 | 28.6 | 19.6 | 0.925 | 1.000 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run1` | 2.2 | 0.5 | — | — | 0.919 | 0.990 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run2` | 1.5 | 0.0 | — | — | 0.933 | 1.000 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run2` | 6.4 | 6.5 | 29.4 | 22.2 | 0.830 | 0.864 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run3` | 5.8 | 5.0 | 24.6 | 17.1 | 0.847 | 0.893 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run1` | 2.2 | 0.5 | — | — | 0.918 | 0.984 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run2` | 1.1 | 0.0 | — | — | 0.945 | 1.000 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run1` | 7.2 | 5.5 | 28.2 | 26.8 | 0.817 | 0.868 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run2` | 4.1 | 1.0 | 23.4 | 16.9 | 0.880 | 0.979 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run1` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run2` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run3` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run1` | 47.9 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run2` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run3` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run1` | 47.7 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run2` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run3` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run1` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run2` | 47.9 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run3` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run1` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run2` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run3` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## getcart

### Pooled

| Topology | Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `run1`, `run2` | 4.0 | 1.2 | 29.3 | 19.9 | 0.884 | 0.969 |
| constrained | burst, RetryGuard only | `run1`, `run2` | 2.9 | 1.2 | — | — | 0.904 | 0.971 |
| constrained | normal, both | `run2`, `run3` | 8.6 | 8.5 | 31.1 | 26.4 | 0.788 | 0.823 |
| constrained | normal, RetryGuard only | `run1`, `run2` | 2.2 | 1.0 | — | — | 0.919 | 0.980 |
| constrained | TopFull only | `run1`, `run2` | 9.3 | 6.8 | 34.0 | 28.1 | 0.770 | 0.850 |
| unconstrained | no shed, no cap | 15 clean holds | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Topology | Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `analysis_4a_constrained_both_burst_run1` | 4.9 | 2.0 | 33.1 | 22.4 | 0.863 | 0.947 |
| constrained | burst, both | `analysis_4a_constrained_both_burst_run2` | 3.0 | 0.5 | 25.6 | 17.4 | 0.905 | 0.990 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run1` | 3.8 | 2.0 | — | — | 0.885 | 0.954 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run2` | 1.9 | 0.5 | — | — | 0.923 | 0.988 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run2` | 6.4 | 6.0 | 23.4 | 18.2 | 0.832 | 0.874 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run3` | 10.7 | 11.0 | 39.1 | 34.8 | 0.744 | 0.772 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run1` | 2.4 | 1.0 | — | — | 0.913 | 0.980 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run2` | 1.9 | 1.0 | — | — | 0.926 | 0.980 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run1` | 12.2 | 12.0 | 39.9 | 37.5 | 0.714 | 0.740 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run2` | 6.5 | 1.5 | 27.8 | 18.5 | 0.826 | 0.960 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run1` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run2` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run3` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run1` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run2` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run3` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run1` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run2` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run3` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run1` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run2` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run3` | 48.0 | 50.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run1` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run2` | 47.9 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run3` | 48.0 | 50.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## postcart

### Pooled

| Topology | Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `run1`, `run2` | 385.0 | 442.0 | 81.5 | 83.4 | 0.309 | 0.221 |
| constrained | burst, RetryGuard only | `run1`, `run2` | 393.1 | 392.4 | — | — | 0.295 | 0.248 |
| constrained | normal, both | `run2`, `run3` | 553.7 | 593.2 | 96.4 | 99.3 | 0.035 | 0.000 |
| constrained | normal, RetryGuard only | `run1`, `run2` | 335.3 | 335.0 | — | — | 0.385 | 0.388 |
| constrained | TopFull only | `run1`, `run2` | 269.2 | 247.2 | 69.5 | 67.4 | 0.469 | 0.480 |
| unconstrained | no shed, no cap | 15 clean holds | 574.2 | 599.5 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Topology | Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `analysis_4a_constrained_both_burst_run1` | 275.7 | 305.0 | 75.4 | 69.9 | 0.491 | 0.442 |
| constrained | burst, both | `analysis_4a_constrained_both_burst_run2` | 494.4 | 579.0 | 87.4 | 96.8 | 0.128 | 0.000 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run1` | 491.3 | 579.0 | — | — | 0.134 | 0.000 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run2` | 294.9 | 205.8 | — | — | 0.457 | 0.497 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run2` | 557.2 | 593.5 | 97.1 | 99.4 | 0.025 | 0.000 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run3` | 550.2 | 593.0 | 95.7 | 99.2 | 0.044 | 0.000 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run1` | 438.0 | 543.5 | — | — | 0.204 | 0.000 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run2` | 232.5 | 126.5 | — | — | 0.565 | 0.777 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run1` | 325.2 | 331.5 | 65.4 | 58.5 | 0.399 | 0.399 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run2` | 213.2 | 163.0 | 74.4 | 81.1 | 0.539 | 0.562 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run1` | 574.7 | 600.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run2` | 575.0 | 600.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run3` | 575.1 | 600.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run1` | 574.3 | 600.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run2` | 575.4 | 600.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run3` | 575.6 | 600.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run1` | 575.4 | 599.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run2` | 568.1 | 594.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run3` | 576.3 | 597.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run1` | 575.3 | 598.5 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run2` | 570.0 | 592.5 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run3` | 575.7 | 596.5 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run1` | 571.5 | 597.5 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run2` | 575.2 | 600.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run3` | 576.0 | 599.5 | 100.0 | 100.0 | 0.000 | 0.000 |

## postcheckout

### Pooled

| Topology | Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `run1`, `run2` | 1.6 | 0.8 | 36.6 | 27.3 | 0.886 | 0.951 |
| constrained | burst, RetryGuard only | `run1`, `run2` | 0.9 | 0.2 | — | — | 0.918 | 0.989 |
| constrained | normal, both | `run2`, `run3` | 2.0 | 1.2 | 27.8 | 20.3 | 0.857 | 0.938 |
| constrained | normal, RetryGuard only | `run1`, `run2` | 0.6 | 0.0 | — | — | 0.935 | 1.000 |
| constrained | TopFull only | `run1`, `run2` | 4.2 | 2.5 | 44.2 | 38.7 | 0.742 | 0.833 |
| unconstrained | no shed, no cap | 15 clean holds | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Topology | Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| constrained | burst, both | `analysis_4a_constrained_both_burst_run1` | 2.2 | 1.5 | 35.3 | 25.1 | 0.854 | 0.902 |
| constrained | burst, both | `analysis_4a_constrained_both_burst_run2` | 1.0 | 0.0 | 38.0 | 29.5 | 0.917 | 1.000 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run1` | 1.2 | 0.5 | — | — | 0.904 | 0.977 |
| constrained | burst, RetryGuard only | `analysis_4a_constrained_rg_only_burst_run2` | 0.6 | 0.0 | — | — | 0.932 | 1.000 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run2` | 1.2 | 0.0 | 24.2 | 14.9 | 0.901 | 1.000 |
| constrained | normal, both | `analysis_4a_constrained_both_normal_run3` | 2.9 | 2.5 | 31.2 | 25.6 | 0.813 | 0.875 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run1` | 0.6 | 0.0 | — | — | 0.935 | 1.000 |
| constrained | normal, RetryGuard only | `analysis_4a_constrained_rg_only_normal_run2` | 0.5 | 0.0 | — | — | 0.935 | 1.000 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run1` | 6.5 | 5.0 | 52.8 | 44.9 | 0.626 | 0.667 |
| constrained | TopFull only | `analysis_4a_constrained_tf_only_run2` | 1.9 | 0.0 | 35.0 | 32.0 | 0.858 | 1.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run1` | 19.1 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run2` | 19.0 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_burst_run3` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run1` | 19.2 | 20.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run2` | 19.2 | 20.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_burst_run3` | 19.2 | 20.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run1` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run2` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_both_normal_run3` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run1` | 19.1 | 19.5 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run2` | 19.2 | 20.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_rg_only_normal_run3` | 19.2 | 20.0 | — | — | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run1` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run2` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| unconstrained | no shed, no cap | `analysis_4a_unconstrained_tf_only_run3` | 19.2 | 20.0 | 100.0 | 100.0 | 0.000 | 0.000 |
