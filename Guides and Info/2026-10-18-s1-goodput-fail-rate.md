# S1 goodput and fail rate (2026-10-18)

Same columns as [2026-10-18-s3-goodput-fail-rate.md](2026-10-18-s3-goodput-fail-rate.md). Each API has two tables. The first table is the pooled row. The second table is one row per run.

Holds: the clean folders under `experiments/results/final_runs_results/S1_normal_operation_burst` and `S1_normal_operation_normal`. `analysis_s1_both_burst_run2` is left out: throttle flagged. The other 10 are `health: ok` and not throttle-flagged.

On these 10 holds RetryGuard never shed (`retryguard.log` has no `ON→OFF`) and TopFull never capped (no Locust second with a threshold under 9900). Those runs are one pool here. The pool is `both_burst` `run1` and `run3`, `rg_only_burst` `run1` and `run2`, `both_normal` `run1` and `run2`, `rg_only_normal` `run1` and `run2`, and `tf_only` `run1` and `run2`.

Goodput and the effective-cap percentages come from `variant_summary.py` (`experiments/variant_summary.py`). Fail rate is Locust `Fail / RPS` on seconds with `RPS` > 0, the same seconds as `analysis_score.locust_table`. Goodput is req/s. A blank effective percentage means TopFull is off. The pooled percentage is recomputed from the TopFull-on runs in the pool. Column definitions: [VARIANT-SUMMARY.md](VARIANT-SUMMARY.md).

The pooled row gives each run equal weight. With ten runs, each median is the midpoint of the two central run medians.

## getproduct

### Pooled

| Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | 10 clean holds | 161.1 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | `analysis_s1_both_burst_run1` | 161.2 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_burst_run3` | 161.1 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run1` | 161.1 | 175.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run2` | 161.0 | 175.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run1` | 161.3 | 174.5 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run2` | 161.0 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run1` | 161.2 | 175.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run2` | 161.0 | 175.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run1` | 161.2 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run2` | 160.8 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## getcart

### Pooled

| Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | 10 clean holds | 64.4 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | `analysis_s1_both_burst_run1` | 64.5 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_burst_run3` | 64.4 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run1` | 64.4 | 70.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run2` | 64.4 | 70.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run1` | 64.5 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run2` | 64.4 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run1` | 64.4 | 70.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run2` | 64.4 | 70.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run1` | 64.5 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run2` | 64.4 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## postcheckout

### Pooled

| Group | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | 10 clean holds | 27.6 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Group | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| no shed, no cap | `analysis_s1_both_burst_run1` | 27.7 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_burst_run3` | 27.6 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run1` | 27.6 | 30.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_burst_run2` | 27.6 | 30.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run1` | 27.6 | 29.5 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_both_normal_run2` | 27.7 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run1` | 27.6 | 29.5 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_rg_only_normal_run2` | 27.6 | 30.0 | — | — | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run1` | 27.7 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| no shed, no cap | `analysis_s1_tf_only_run2` | 27.6 | 30.0 | 100.0 | 100.0 | 0.000 | 0.000 |
