# S2 variant summary (2026-10-18)

`python experiments/variant_summary.py` on the unflagged holds in `experiments/results/final_runs_results/S2_sustained_overload_burst` and `S2_sustained_overload_normal`. Column definitions: [VARIANT-SUMMARY.md](VARIANT-SUMMARY.md).

The tables are `getproduct`, `getcart`, and `postcheckout`. Goodput is req/s. The variant row gives each run equal weight. With two runs, median goodput is the midpoint of the two run medians. The percentages are recomputed from the aggregated caps. A blank percentage means TopFull is off.

No hold here has a throttle flag. `analysis_s2_both_normal_run1` is left out: health line **RL STALL** (two `RL_RPS_TIMEOUT` lines). The burst folder has no TopFull-only holds.

## S2 burst, both controllers — `run1`, `run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 221.7 | 259.0 | 96.6 | 97.8 |
| getcart | 78.8 | 92.0 | 93.9 | 96.7 |
| postcheckout | 39.1 | 42.1 | 61.7 | 57.9 |

### `analysis_s2_both_burst_run1`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 235.5 | 270.0 | 97.4 | 99.1 |
| getcart | 83.9 | 98.0 | 95.4 | 98.5 |
| postcheckout | 43.0 | 45.0 | 66.7 | 61.6 |

### `analysis_s2_both_burst_run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 207.8 | 248.0 | 95.8 | 96.6 |
| getcart | 73.7 | 86.0 | 92.5 | 95.0 |
| postcheckout | 35.3 | 39.2 | 56.8 | 54.3 |

## S2 burst, RetryGuard only — `run1`, `run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 205.1 | 222.2 | — | — |
| getcart | 74.5 | 80.0 | — | — |
| postcheckout | 50.5 | 58.8 | — | — |

### `analysis_s2_rg_only_burst_run1`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 203.7 | 213.0 | — | — |
| getcart | 74.9 | 79.5 | — | — |
| postcheckout | 50.7 | 59.0 | — | — |

### `analysis_s2_rg_only_burst_run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 206.5 | 231.5 | — | — |
| getcart | 74.0 | 80.5 | — | — |
| postcheckout | 50.2 | 58.5 | — | — |

## S2 normal, both controllers — `run2`, `run3`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 200.1 | 230.0 | 93.8 | 88.7 |
| getcart | 70.3 | 78.5 | 89.5 | 85.8 |
| postcheckout | 30.1 | 23.0 | 55.0 | 47.8 |

### `analysis_s2_both_normal_run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 229.1 | 270.5 | 97.2 | 99.4 |
| getcart | 82.4 | 99.0 | 95.0 | 99.5 |
| postcheckout | 29.0 | 19.0 | 53.2 | 45.0 |

### `analysis_s2_both_normal_run3`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 171.0 | 189.5 | 90.1 | 77.3 |
| getcart | 58.1 | 58.0 | 83.7 | 71.4 |
| postcheckout | 31.3 | 27.0 | 56.9 | 50.7 |

## S2 normal, RetryGuard only — `run1`, `run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 198.9 | 231.2 | — | — |
| getcart | 73.9 | 86.4 | — | — |
| postcheckout | 38.5 | 43.8 | — | — |

### `analysis_s2_rg_only_normal_run1`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 219.4 | 268.0 | — | — |
| getcart | 81.6 | 98.5 | — | — |
| postcheckout | 42.9 | 52.0 | — | — |

### `analysis_s2_rg_only_normal_run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 178.5 | 194.5 | — | — |
| getcart | 66.2 | 74.2 | — | — |
| postcheckout | 34.2 | 35.5 | — | — |

## S2 normal, TopFull only — `run1`, `run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 172.3 | 220.5 | 93.3 | 84.0 |
| getcart | 59.6 | 73.0 | 88.0 | 77.6 |
| postcheckout | 22.0 | 12.0 | 41.4 | 30.5 |

### `analysis_s2_tf_only_run1`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 188.3 | 265.0 | 96.4 | 96.1 |
| getcart | 66.3 | 95.0 | 92.9 | 90.9 |
| postcheckout | 21.6 | 13.0 | 36.6 | 26.1 |

### `analysis_s2_tf_only_run2`

| API | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---:|---:|---:|---:|
| getproduct | 156.4 | 176.0 | 90.1 | 71.3 |
| getcart | 52.9 | 51.0 | 83.0 | 63.3 |
| postcheckout | 22.4 | 11.0 | 46.5 | 35.2 |
