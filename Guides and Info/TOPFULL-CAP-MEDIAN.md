# topfull_cap_median: median effective TopFull cap per Locust API

Added 2026-10-18. Script: `experiments/topfull_cap_median.py`. Tests: `experiments/test_topfull_cap_median.py`.

Same seconds and the same effective value as [TOPFULL-CAP-AVG.md](TOPFULL-CAP-AVG.md). This tool reports the median instead of the mean.

## Command

```powershell
python experiments/topfull_cap_median.py "<run_dir>" ["<run_dir>" ...] [--csv out.csv]
```

A TopFull-off run is skipped. The tool does not filter holds flagged by `throttle_flags.py` or `topfull_health.py`.

## What changes from the average tool

Each scored second still contributes `min(cap, RPS)` when capped and `RPS` when there is no cap. Empty-read and unknown seconds are left out.

| Column | Meaning |
|---|---|
| `median_offered` | Median Locust `RPS` over capped and no-cap seconds |
| `median_effective` | Median of the effective value over those same seconds |
| `median_cap_when_capped` | Median raw cap on capped seconds only (`-` if none) |
| `effective_pct` | `100 * median_effective / median_offered` for that row |

An even number of seconds uses the midpoint of the two central values.

Several directories print a **cell median**: the median of the per-run medians, one weight per run. With two runs that cell row is the midpoint of the two run medians. It is not the median of every second pooled across the runs. `effective_pct` on that row is recomputed from the cell's median offered and median effective.
