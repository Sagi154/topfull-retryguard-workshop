# variant_summary: goodput and effective cap percentage per variant

Added 2026-10-18. Script: `experiments/variant_summary.py`. Tests: `experiments/test_variant_summary.py`.

One view of the three tools [LOCUST-GOODPUT.md](LOCUST-GOODPUT.md), [TOPFULL-CAP-AVG.md](TOPFULL-CAP-AVG.md), and [TOPFULL-CAP-MEDIAN.md](TOPFULL-CAP-MEDIAN.md).

## Command

```powershell
python experiments/variant_summary.py "<run_dir-or-variant_dir>" ["<run_dir-or-variant_dir>" ...]
```

A folder with `run_manifest.json` or `getproduct.csv` is a run. A folder whose children are runs is a variant directory. Runs are grouped by `<scenario>/<variant>`, the two parent folder names.

`postcart` and `emptycart` are left out. The tables are `getproduct`, `getcart`, and `postcheckout`.

## Columns, per Locust API

| Column | One run | Variant row |
|---|---|---|
| `mean_goodput` | Mean Locust `Goodput` on seconds with `RPS` > 0 | Mean of the runs' mean goodputs |
| `median_goodput` | Median of those same seconds | Median of the runs' median goodputs |
| `mean_effective_pct` | `100 * mean effective cap / mean offered` | Recomputed from the mean of the run means |
| `median_effective_pct` | `100 * median effective cap / median offered` | Recomputed from the median of the run medians |

Each run has equal weight in the variant row. The percentages are not an average of the runs' percentages. With two runs, `median_goodput` is the midpoint of the two run medians.

The variant block is printed first, then one table per run. A TopFull-off run keeps its goodput and leaves both percentage cells blank. The tool does not drop holds flagged by `throttle_flags.py` or `topfull_health.py`.
