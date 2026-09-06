# Mentor update — charts and pipeline

> **Mentor-facing doc:** [MENTOR-UPDATE.md](MENTOR-UPDATE.md) (infra, Online Boutique, scenarios, dry per-scenario results). This README is for us: how the PNGs were produced and how to read them.

Data source: `experiments/results/campaign_48/` only. Regenerate:

```powershell
python experiments/mentor_charts.py
```

Writes two trees (same filenames today — see leftovers below):

| Tree | Role |
|---|---|
| `charts/` | Curated subset embedded in `MENTOR-UPDATE.md` |
| `charts_gallery/` | Intended extra reference; currently a copy of curated for Locust |

---

## Known leftovers (non-blocking)

These are chart-pipeline caveats, not missing campaign data. They do not belong in `MENTOR-UPDATE.md`.

**1. CPU / retries elapsed time is relative to each collector file’s t0, not Locust or RetryGuard.**

Locust CSVs have no timestamp: row index ≈ elapsed seconds of the run, so Goodput / P95 / Rejection line up with `retryguard.log` toggle times (those are elapsed from the first log line).

Envoy retry CSVs and `resource_usage.csv` use UTC timestamps. `mentor_charts_data.py` sets elapsed time as seconds since **the first poll in that file**. Collectors can start slightly before or after Locust/RetryGuard, so `t = 60s` on a CPU or retries chart is not guaranteed to be the same wall-clock instant as `t = 60s` on a Locust chart. After the `average_dataframes` index fix, those plots span the real poll duration (~650s on a 10 min run), but they still use **their own clock**. Do not treat a CPU dip at 60s as proof it happened at the same moment as a Locust toggle at 60s.

**2. Multi-line charts have no RetryGuard toggle overlays.**

Red/green dashed `ON→OFF` / `OFF→ON` lines are only drawn by `plot_timeseries_comparison` (baseline-vs-RetryGuard Goodput / P95 / Rejection). CPU, memory, and retries-per-request use `plot_multi_line`, which has no `toggle_events` argument. Correlate those overlays with toggles via the Locust charts or the S6 timeline table (`charts/S6_forced_recovery/s5_toggle_timeline.md`), not from the Envoy/CPU PNG alone.

**3. Locust gallery equals curated.**

The design spec asked `charts_gallery/` to include every Locust endpoint (`getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`, plus `total`) × every metric. The implementation never added that loop. For Locust, both trees get system-wide `total_*` always, plus the bottleneck endpoint only for S3/S4 (`postcheckout` or `getproduct`). Opening `charts_gallery/S1_normal_op/` will not show e.g. `getcart_goodput.png`. Envoy (per-target + summed) and CPU/memory overlays are already generated for every scenario in both trees.

See also: [campaign_48/README.md](../../experiments/results/campaign_48/README.md) (CSV columns, how repeats are averaged), [design spec](../../docs/superpowers/specs/2026-09-06-mentor-update-doc-design.md).
