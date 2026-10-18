# topfull_cap_avg: average effective TopFull cap per Locust API

Added 2026-10-18. Script: `experiments/topfull_cap_avg.py`. Tests: `experiments/test_topfull_cap_avg.py`.

## What it answers

For one hold, what was the average admitted-rate cap TopFull enforced on each Locust entry API (`getproduct`, `getcart`, `postcart`, `emptycart`, `postcheckout`)? The answer is in req/s, over the whole run starting at the first Locust row.

A raw average of `threshold` does not answer that. When TopFull has no cap on an API, the threshold is 10000, a passthrough value. Averaging it in would drown the real caps. So the tool uses the load actually offered in those seconds instead.

## Command

```powershell
python experiments/topfull_cap_avg.py "<run_dir>" ["<run_dir>" ...] [--csv out.csv]
```

- One directory per run. Example: `experiments/results/final_runs_results/S2_sustained_overload_burst/both/analysis_s2_both_burst_run2`.
- Call it once per run, or pass all runs of a cell in one call. With more than one directory it also prints the **cell mean**, which is the mean of the per-run means. A run is weighted equally, whatever its length.
- `--csv` writes one row per run and API.
- A TopFull-off run (`run_manifest.json` has `topfull_rl.enabled` false, so the `rg_only` and `both_off` variants) has no cap and is skipped with a message. A run with no `topfull_throttle.csv` is skipped the same way.

## Rule for one second

The tool walks every Locust row of an API. The first row is second 0. Each row is classified from the throttle file:

| Cap in force at this row | Meaning | Value used |
|---|---|---|
| Latest **fresh** threshold read (`threshold_fresh` = 1), at most 6 s old, and below 9900 | **capped** | `min(cap, RPS)` |
| That read is 9900 or more | **nocap** (10000 is the passthrough, and the RL can step a little below it) | `RPS` |
| That read is 0 | **empty** (an empty read) | row left out, counted |
| No fresh read within 6 s before the row | **unknown** | row left out, counted |

- `RPS` is the Locust offered rate. Locust `RPS` already includes failed requests (`Goodput = RPS − Fail`), so no `Fail` is added.
- With no cap, nothing is blocked below demand, so the effective cap equals what was offered. With a cap, the effective value is whichever is lower.
- The 9900 threshold and the 6 s carry are the same constants as `run_timeline.py`, `throttle_stale.py`, and `analysis_score.py`. See [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md) for why.
- Only fresh reads count. A carried CSV value is not used past the 6 s window, so a stale stretch becomes `unknown`, not a made-up number.

## Output columns (per API)

| Column | Meaning |
|---|---|
| `rows` | Locust rows for that API |
| `capped_s`, `nocap_s`, `empty_s`, `unknown_s` | Rows in each class above. They add up to `rows` |
| `mean_offered` | Mean `RPS` over capped and no-cap rows |
| `mean_effective` | Mean of the effective value over the same rows. **This is the answer** |
| `mean_cap_when_capped` | Mean raw cap on capped rows only (`-` if none) |
| `effective_pct` | `100 * mean_effective / mean_offered` for that row. `-` when offered is missing or 0 |

`mean_offered` and `mean_effective` use the same rows, so the gap between them is the load TopFull held back. Cell-mean rows average each of those columns across runs and skip runs where it is missing. `effective_pct` is not averaged: on the cell-mean row it is recomputed from that row's averaged offered and effective.

## How to read it

- Always read the four second-counts with the mean. A mean from 5% capped rows is not comparable to one from 95% capped rows.
- `empty_s` can be large. A fresh 0 may be the cap-floor rule (the cap really is 0 and the limiter rejects everything), per [TOPFULL-THROTTLE-METRICS.md](TOPFULL-THROTTLE-METRICS.md) "Cap floor". The tool follows the existing rule and leaves those rows out, so `mean_effective` can read too high on such APIs.
- The tool does **not** filter holds flagged by `throttle_flags.py` or `topfull_health.py` (throttle stale, PROXY FD, RL STALL). Check the flags first, and name a flagged hold per [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) item 17 when you quote it.
- The cap is the proxy's admission limit. Locust `RPS` is what the client sent, so `min(cap, RPS)` is an effective ceiling, not a measured admitted rate. In this project `admitted_rps` in `topfull_throttle.csv` is also the offered rate, so it cannot replace `RPS` here.

## Smoke result (2026-10-18)

`analysis_s2_both_burst_run2`, 550 Locust rows per API:

| API | capped_s | nocap_s | empty_s | unknown_s | mean_offered | mean_effective | effective_pct |
|---|---|---|---|---|---|---|---|---|
| `getproduct` | 227 | 240 | 83 | 0 | 254.9 | 244.3 | 95.8 |
| `getcart` | 220 | 241 | 89 | 0 | 92.6 | 85.7 | 92.5 |
| `postcart` | 0 | 405 | 145 | 0 | 84.9 | 84.9 | 100.0 |
| `emptycart` | 0 | 405 | 145 | 0 | 4.8 | 4.8 | 100.0 |
| `postcheckout` | 458 | 32 | 60 | 0 | 81.1 | 46.1 | 56.8 |

This is one hold, shown to check the tool. It is not a cell result and not a finding. The tool has not been run across cells yet.

## Tests

`python -m pytest experiments/test_topfull_cap_avg.py` covers the row classes (capped, no-cap, empty, unknown), the carry limit, a row before the first read, and the effective-mean arithmetic.
