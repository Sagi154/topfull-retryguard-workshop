# S3 goodput and fail rate (2026-10-18)

Same layout as [2026-10-18-s2-goodput-fail-rate.md](2026-10-18-s2-goodput-fail-rate.md). Each API has two tables. The both-runs table is one row per variant. The second table is one row per run. S1, with no-shed and no-cap runs pooled: [2026-10-18-s1-goodput-fail-rate.md](2026-10-18-s1-goodput-fail-rate.md). S4A, constrained rows plus the unconstrained pool: [2026-10-18-s4a-goodput-fail-rate.md](2026-10-18-s4a-goodput-fail-rate.md).

Holds: every folder under `experiments/results/final_runs_results/S3_targeted_bottleneck_burst` and `S3_targeted_bottleneck_normal`. All 15 are clean (`health: ok`, throttle not flagged). The burst folder has no TopFull-only holds.

A run with both controllers on is counted here as TopFull only when `retryguard.log` has no `ON→OFF`. That is `analysis_s3_both_normal_run1`, `run2`, and `run3`. The three `both_burst` runs each shed (`frontend → checkoutservice`), so they stay on the both row. RetryGuard-only runs stay on their own rows.

Goodput and the effective-cap percentages come from `variant_summary.py` (`experiments/variant_summary.py`). Fail rate is Locust `Fail / RPS` on seconds with `RPS` > 0, the same seconds as `analysis_score.locust_table`. Goodput is req/s. A blank effective percentage means TopFull is off. Column definitions: [VARIANT-SUMMARY.md](VARIANT-SUMMARY.md).

The variant row gives each of its runs equal weight. With three runs, each median is the middle of the three run medians. The TopFull-only row has six runs, so each median is the midpoint of the two central run medians. The percentages are recomputed from the aggregated caps.

## getproduct

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2`, `run3` | 168.0 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, RetryGuard only | `run1`, `run2`, `run3` | 167.9 | 175.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `run1`, `run2`, `run3` | 167.9 | 175.0 | — | — | 0.000 | 0.000 |
| normal, TopFull only | `tf_only run1`–`run3`, `both_normal run1`–`run3` | 167.8 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s3_both_burst_run1` | 168.1 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, both | `analysis_s3_both_burst_run2` | 168.0 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, both | `analysis_s3_both_burst_run3` | 167.8 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run1` | 167.9 | 175.0 | — | — | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run2` | 168.0 | 175.0 | — | — | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run3` | 167.8 | 175.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run1` | 167.8 | 174.5 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run2` | 168.0 | 175.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run3` | 167.9 | 175.0 | — | — | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run1` | 168.0 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run2` | 167.8 | 174.5 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run3` | 167.7 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run1` | 167.8 | 174.5 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run2` | 168.0 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run3` | 167.8 | 175.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## getcart

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2`, `run3` | 67.2 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, RetryGuard only | `run1`, `run2`, `run3` | 67.1 | 70.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `run1`, `run2`, `run3` | 67.2 | 70.0 | — | — | 0.000 | 0.000 |
| normal, TopFull only | `tf_only run1`–`run3`, `both_normal run1`–`run3` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s3_both_burst_run1` | 67.2 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, both | `analysis_s3_both_burst_run2` | 67.2 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, both | `analysis_s3_both_burst_run3` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run1` | 67.1 | 70.0 | — | — | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run2` | 67.2 | 70.0 | — | — | 0.000 | 0.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run3` | 67.1 | 70.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run1` | 67.1 | 70.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run2` | 67.2 | 70.0 | — | — | 0.000 | 0.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run3` | 67.1 | 70.0 | — | — | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run1` | 67.2 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run2` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_tf_only_run3` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run1` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run2` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |
| normal, TopFull only | `analysis_s3_both_normal_run3` | 67.1 | 70.0 | 100.0 | 100.0 | 0.000 | 0.000 |

## postcheckout

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2`, `run3` | 8.6 | 9.0 | 46.7 | 43.7 | 0.685 | 0.694 |
| burst, RetryGuard only | `run1`, `run2`, `run3` | 0.3 | 0.0 | — | — | 0.961 | 1.000 |
| normal, RetryGuard only | `run1`, `run2`, `run3` | 0.5 | 0.0 | — | — | 0.953 | 1.000 |
| normal, TopFull only | `tf_only run1`–`run3`, `both_normal run1`–`run3` | 4.2 | 3.0 | 27.9 | 20.0 | 0.821 | 0.896 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s3_both_burst_run1` | 7.8 | 8.5 | 42.6 | 43.7 | 0.718 | 0.701 |
| burst, both | `analysis_s3_both_burst_run2` | 8.2 | 9.0 | 43.6 | 43.7 | 0.697 | 0.694 |
| burst, both | `analysis_s3_both_burst_run3` | 9.7 | 11.0 | 54.1 | 55.0 | 0.639 | 0.625 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run1` | 0.2 | 0.0 | — | — | 0.964 | 1.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run2` | 0.2 | 0.0 | — | — | 0.966 | 1.000 |
| burst, RetryGuard only | `analysis_s3_rg_only_burst_run3` | 0.5 | 0.0 | — | — | 0.951 | 1.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run1` | 0.3 | 0.0 | — | — | 0.959 | 1.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run2` | 0.4 | 0.0 | — | — | 0.959 | 1.000 |
| normal, RetryGuard only | `analysis_s3_rg_only_normal_run3` | 0.8 | 0.5 | — | — | 0.941 | 0.984 |
| normal, TopFull only | `analysis_s3_tf_only_run1` | 3.9 | 3.0 | 26.6 | 19.7 | 0.836 | 0.898 |
| normal, TopFull only | `analysis_s3_tf_only_run2` | 3.6 | 3.0 | 24.4 | 19.5 | 0.841 | 0.900 |
| normal, TopFull only | `analysis_s3_tf_only_run3` | 5.0 | 4.0 | 33.5 | 24.7 | 0.790 | 0.867 |
| normal, TopFull only | `analysis_s3_both_normal_run1` | 4.1 | 3.0 | 27.8 | 20.3 | 0.826 | 0.894 |
| normal, TopFull only | `analysis_s3_both_normal_run2` | 3.7 | 3.0 | 23.6 | 17.7 | 0.842 | 0.902 |
| normal, TopFull only | `analysis_s3_both_normal_run3` | 4.8 | 3.5 | 31.7 | 25.4 | 0.793 | 0.867 |
