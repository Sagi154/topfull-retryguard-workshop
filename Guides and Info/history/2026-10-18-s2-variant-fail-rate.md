# S2 variant fail rate (2026-10-18)

Each API has two tables. The both-runs table is one row per variant. The second table is one row per run.

Holds: the unflagged folders in `experiments/results/final_runs_results/S2_sustained_overload_burst` and `S2_sustained_overload_normal`. Goodput on these holds: [2026-10-18-s2-variant-summary.md](2026-10-18-s2-variant-summary.md) and [2026-10-18-s2-api-summary.md](2026-10-18-s2-api-summary.md). Goodput and fail rate together: [2026-10-18-s2-goodput-fail-rate.md](2026-10-18-s2-goodput-fail-rate.md). P95 on these holds: [2026-10-18-s2-variant-p95.md](2026-10-18-s2-variant-p95.md).

Fail rate is Locust `Fail / RPS`, on seconds with `RPS` > 0. Mean fail rate is the mean of those seconds, the same seconds `analysis_score.locust_table` averages, so one run's mean matches that scorer's Locust fail rate for the API. Median fail rate is the median of those same seconds. An even number of seconds uses the midpoint of the two central values. This is the storefront SLO-miss fraction on an entry API. Inbound mesh rejection stays a per-service number.

The both-runs row gives each run equal weight. With two runs, median fail rate is the midpoint of the two run medians.

No hold here has a throttle flag. `analysis_s2_both_normal_run1` is left out: health line **RL STALL** (two `RL_RPS_TIMEOUT` lines). The burst folder has no TopFull-only holds.

## getproduct

### Both runs

| Variant | Holds | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `run1`, `run2` | 0.144 | 0.008 |
| burst, RetryGuard only | `run1`, `run2` | 0.210 | 0.164 |
| normal, both | `run2`, `run3` | 0.208 | 0.131 |
| normal, RetryGuard only | `run1`, `run2` | 0.224 | 0.112 |
| normal, TopFull only | `run1`, `run2` | 0.313 | 0.099 |

### Each run

| Variant | Run | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 0.093 | 0.000 |
| burst, both | `analysis_s2_both_burst_run2` | 0.195 | 0.015 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 0.214 | 0.195 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 0.206 | 0.132 |
| normal, both | `analysis_s2_both_normal_run2` | 0.117 | 0.000 |
| normal, both | `analysis_s2_both_normal_run3` | 0.298 | 0.262 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 0.150 | 0.000 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 0.297 | 0.224 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 0.258 | 0.000 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 0.368 | 0.197 |

## getcart

### Both runs

| Variant | Holds | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `run1`, `run2` | 0.161 | 0.032 |
| burst, RetryGuard only | `run1`, `run2` | 0.212 | 0.163 |
| normal, both | `run2`, `run3` | 0.231 | 0.177 |
| normal, RetryGuard only | `run1`, `run2` | 0.208 | 0.095 |
| normal, TopFull only | `run1`, `run2` | 0.342 | 0.160 |

### Each run

| Variant | Run | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 0.110 | 0.000 |
| burst, both | `analysis_s2_both_burst_run2` | 0.211 | 0.063 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 0.207 | 0.165 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 0.216 | 0.160 |
| normal, both | `analysis_s2_both_normal_run2` | 0.126 | 0.000 |
| normal, both | `analysis_s2_both_normal_run3` | 0.336 | 0.354 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 0.133 | 0.000 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 0.284 | 0.190 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 0.278 | 0.000 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 0.406 | 0.320 |

## postcheckout

### Both runs

| Variant | Holds | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `run1`, `run2` | 0.505 | 0.466 |
| burst, RetryGuard only | `run1`, `run2` | 0.385 | 0.301 |
| normal, both | `run2`, `run3` | 0.593 | 0.702 |
| normal, RetryGuard only | `run1`, `run2` | 0.513 | 0.443 |
| normal, TopFull only | `run1`, `run2` | 0.692 | 0.841 |

### Each run

| Variant | Run | Mean fail rate | Median fail rate |
|---|---|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 0.458 | 0.395 |
| burst, both | `analysis_s2_both_burst_run2` | 0.551 | 0.538 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 0.382 | 0.304 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 0.388 | 0.298 |
| normal, both | `analysis_s2_both_normal_run2` | 0.608 | 0.746 |
| normal, both | `analysis_s2_both_normal_run3` | 0.578 | 0.658 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 0.467 | 0.350 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 0.559 | 0.536 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 0.700 | 0.830 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 0.685 | 0.852 |
