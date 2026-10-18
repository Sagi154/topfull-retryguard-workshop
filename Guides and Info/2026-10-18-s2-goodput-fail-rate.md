# S2 goodput and fail rate (2026-10-18)

Each API has two tables. The both-runs table is one row per variant. The second table is one row per run. Goodput columns are from [2026-10-18-s2-api-summary.md](2026-10-18-s2-api-summary.md) and the per-run tables in [2026-10-18-s2-variant-summary.md](2026-10-18-s2-variant-summary.md). Fail-rate columns are from [2026-10-18-s2-variant-fail-rate.md](2026-10-18-s2-variant-fail-rate.md). The same tables for S3: [2026-10-18-s3-goodput-fail-rate.md](2026-10-18-s3-goodput-fail-rate.md).

Goodput is req/s. Fail rate is Locust `Fail / RPS` on an entry API. A blank effective percentage means TopFull is off. Column definitions: [VARIANT-SUMMARY.md](VARIANT-SUMMARY.md).

The both-runs row gives each run equal weight. With two runs, each median is the midpoint of the two run medians. The percentages are recomputed from the aggregated caps.

No hold here has a throttle flag. `analysis_s2_both_normal_run1` is left out: health line **RL STALL** (two `RL_RPS_TIMEOUT` lines). The burst folder has no TopFull-only holds.

## getproduct

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 221.7 | 259.0 | 96.6 | 97.8 | 0.144 | 0.008 |
| burst, RetryGuard only | `run1`, `run2` | 205.1 | 222.2 | — | — | 0.210 | 0.164 |
| normal, both | `run2`, `run3` | 200.1 | 230.0 | 93.8 | 88.7 | 0.208 | 0.131 |
| normal, RetryGuard only | `run1`, `run2` | 198.9 | 231.2 | — | — | 0.224 | 0.112 |
| normal, TopFull only | `run1`, `run2` | 172.3 | 220.5 | 93.3 | 84.0 | 0.313 | 0.099 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 235.5 | 270.0 | 97.4 | 99.1 | 0.093 | 0.000 |
| burst, both | `analysis_s2_both_burst_run2` | 207.8 | 248.0 | 95.8 | 96.6 | 0.195 | 0.015 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 203.7 | 213.0 | — | — | 0.214 | 0.195 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 206.5 | 231.5 | — | — | 0.206 | 0.132 |
| normal, both | `analysis_s2_both_normal_run2` | 229.1 | 270.5 | 97.2 | 99.4 | 0.117 | 0.000 |
| normal, both | `analysis_s2_both_normal_run3` | 171.0 | 189.5 | 90.1 | 77.3 | 0.298 | 0.262 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 219.4 | 268.0 | — | — | 0.150 | 0.000 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 178.5 | 194.5 | — | — | 0.297 | 0.224 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 188.3 | 265.0 | 96.4 | 96.1 | 0.258 | 0.000 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 156.4 | 176.0 | 90.1 | 71.3 | 0.368 | 0.197 |

## getcart

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 78.8 | 92.0 | 93.9 | 96.7 | 0.161 | 0.032 |
| burst, RetryGuard only | `run1`, `run2` | 74.5 | 80.0 | — | — | 0.212 | 0.163 |
| normal, both | `run2`, `run3` | 70.3 | 78.5 | 89.5 | 85.8 | 0.231 | 0.177 |
| normal, RetryGuard only | `run1`, `run2` | 73.9 | 86.4 | — | — | 0.208 | 0.095 |
| normal, TopFull only | `run1`, `run2` | 59.6 | 73.0 | 88.0 | 77.6 | 0.342 | 0.160 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 83.9 | 98.0 | 95.4 | 98.5 | 0.110 | 0.000 |
| burst, both | `analysis_s2_both_burst_run2` | 73.7 | 86.0 | 92.5 | 95.0 | 0.211 | 0.063 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 74.9 | 79.5 | — | — | 0.207 | 0.165 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 74.0 | 80.5 | — | — | 0.216 | 0.160 |
| normal, both | `analysis_s2_both_normal_run2` | 82.4 | 99.0 | 95.0 | 99.5 | 0.126 | 0.000 |
| normal, both | `analysis_s2_both_normal_run3` | 58.1 | 58.0 | 83.7 | 71.4 | 0.336 | 0.354 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 81.6 | 98.5 | — | — | 0.133 | 0.000 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 66.2 | 74.2 | — | — | 0.284 | 0.190 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 66.3 | 95.0 | 92.9 | 90.9 | 0.278 | 0.000 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 52.9 | 51.0 | 83.0 | 63.3 | 0.406 | 0.320 |

## postcheckout

### Both runs

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 39.1 | 42.1 | 61.7 | 57.9 | 0.505 | 0.466 |
| burst, RetryGuard only | `run1`, `run2` | 50.5 | 58.8 | — | — | 0.385 | 0.301 |
| normal, both | `run2`, `run3` | 30.1 | 23.0 | 55.0 | 47.8 | 0.593 | 0.702 |
| normal, RetryGuard only | `run1`, `run2` | 38.5 | 43.8 | — | — | 0.513 | 0.443 |
| normal, TopFull only | `run1`, `run2` | 22.0 | 12.0 | 41.4 | 30.5 | 0.692 | 0.841 |

### Each run

| Variant | Run | Mean goodput | Median goodput | Mean effective % | Median effective % | Mean fail rate | Median fail rate |
|---|---|---:|---:|---:|---:|---:|---:|
| burst, both | `analysis_s2_both_burst_run1` | 43.0 | 45.0 | 66.7 | 61.6 | 0.458 | 0.395 |
| burst, both | `analysis_s2_both_burst_run2` | 35.3 | 39.2 | 56.8 | 54.3 | 0.551 | 0.538 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run1` | 50.7 | 59.0 | — | — | 0.382 | 0.304 |
| burst, RetryGuard only | `analysis_s2_rg_only_burst_run2` | 50.2 | 58.5 | — | — | 0.388 | 0.298 |
| normal, both | `analysis_s2_both_normal_run2` | 29.0 | 19.0 | 53.2 | 45.0 | 0.608 | 0.746 |
| normal, both | `analysis_s2_both_normal_run3` | 31.3 | 27.0 | 56.9 | 50.7 | 0.578 | 0.658 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run1` | 42.9 | 52.0 | — | — | 0.467 | 0.350 |
| normal, RetryGuard only | `analysis_s2_rg_only_normal_run2` | 34.2 | 35.5 | — | — | 0.559 | 0.536 |
| normal, TopFull only | `analysis_s2_tf_only_run1` | 21.6 | 13.0 | 36.6 | 26.1 | 0.700 | 0.830 |
| normal, TopFull only | `analysis_s2_tf_only_run2` | 22.4 | 11.0 | 46.5 | 35.2 | 0.685 | 0.852 |
