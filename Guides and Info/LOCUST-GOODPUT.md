# locust_goodput: mean and median goodput per Locust API

Added 2026-10-18. Script: `experiments/locust_goodput.py`. Tests: `experiments/test_locust_goodput.py`.

## Command

```powershell
python experiments/locust_goodput.py "<run_dir>" ["<run_dir>" ...] [--csv out.csv]
```

Pass the run directories of one variant together. Each run is printed, then one pooled row.

## What is counted

Goodput is the `Goodput` column in that API's Locust file (`getproduct.csv`, `getcart.csv`, `postcart.csv`, `emptycart.csv`, `postcheckout.csv`). Locust defines it as `RPS − Fail`.

Seconds with `RPS` of 0 are left out. That is the same set of seconds `analysis_score.locust_table` averages, so `mean_goodput` for one run matches that scorer's goodput for the API.

An even number of seconds uses the midpoint of the two central values.

## Across a variant

The pooled row is the mean and the median of every scored second from the runs you passed. A longer run counts for more seconds. It is not the mean of the per-run means, and it is not the median of the per-run medians.

The tool does not filter holds flagged by `throttle_flags.py` or `topfull_health.py`. Goodput does not use the TopFull cap, so a TopFull-off run is included when you pass it.
