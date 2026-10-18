# S2 API summary (2026-10-18)

Same numbers as the variant rows in [2026-10-18-s2-variant-summary.md](2026-10-18-s2-variant-summary.md). That file groups by variant. This file groups by Locust API, so one table shows every included variant.

Source: `python experiments/variant_summary.py` on the unflagged holds in `experiments/results/final_runs_results/S2_sustained_overload_burst` and `S2_sustained_overload_normal`. Column definitions: [VARIANT-SUMMARY.md](../VARIANT-SUMMARY.md). Goodput and fail rate together: [2026-10-18-s2-goodput-fail-rate.md](2026-10-18-s2-goodput-fail-rate.md).

Goodput is req/s. Each row gives its two runs equal weight. With two runs, median goodput is the midpoint of the two run medians. The percentages are recomputed from the aggregated caps. A blank percentage means TopFull is off.

No hold here has a throttle flag. `analysis_s2_both_normal_run1` is left out: health line **RL STALL** (two `RL_RPS_TIMEOUT` lines). The burst folder has no TopFull-only holds. Per-run tables stay in the variant summary.

## getproduct

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 221.7 | 259.0 | 96.6 | 97.8 |
| burst, RetryGuard only | `run1`, `run2` | 205.1 | 222.2 | — | — |
| normal, both | `run2`, `run3` | 200.1 | 230.0 | 93.8 | 88.7 |
| normal, RetryGuard only | `run1`, `run2` | 198.9 | 231.2 | — | — |
| normal, TopFull only | `run1`, `run2` | 172.3 | 220.5 | 93.3 | 84.0 |

## getcart

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 78.8 | 92.0 | 93.9 | 96.7 |
| burst, RetryGuard only | `run1`, `run2` | 74.5 | 80.0 | — | — |
| normal, both | `run2`, `run3` | 70.3 | 78.5 | 89.5 | 85.8 |
| normal, RetryGuard only | `run1`, `run2` | 73.9 | 86.4 | — | — |
| normal, TopFull only | `run1`, `run2` | 59.6 | 73.0 | 88.0 | 77.6 |

## postcheckout

| Variant | Holds | Mean goodput | Median goodput | Mean effective % | Median effective % |
|---|---|---:|---:|---:|---:|
| burst, both | `run1`, `run2` | 39.1 | 42.1 | 61.7 | 57.9 |
| burst, RetryGuard only | `run1`, `run2` | 50.5 | 58.8 | — | — |
| normal, both | `run2`, `run3` | 30.1 | 23.0 | 55.0 | 47.8 |
| normal, RetryGuard only | `run1`, `run2` | 38.5 | 43.8 | — | — |
| normal, TopFull only | `run1`, `run2` | 22.0 | 12.0 | 41.4 | 30.5 |
