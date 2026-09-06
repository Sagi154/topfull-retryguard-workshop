# Drop Min/Max Chart Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop drawing the blue/orange min/max shaded bands on mentor-update Locust comparison charts so only the two mean lines (plus toggle markers) remain.

**Architecture:** `average_series` already returns `mean`/`min`/`max`; leave that helper unchanged. The bands are drawn only in two matplotlib helpers (`plot_timeseries_comparison` and `_draw_comparison_panel`). Remove the `fill_between` calls, keep plotting `mean`, regenerate the PNGs, and update the mentor-facing legend/observation copy that currently describes the bands.

**Tech Stack:** Python 3, pandas, matplotlib (Agg), unittest, existing `experiments/mentor_charts*.py` pipeline.

## Global Constraints

- Data source remains `experiments/results/campaign_48/` only — do not touch run CSVs.
- Do not change `average_series` / `_load_group_average` contracts (they may still return `min`/`max` columns; just stop plotting them).
- Do not add error bars, std bands, or any replacement shading.
- Do not change CPU/memory/retries `plot_multi_line` charts (they never had bands).
- Existing plot smoke tests must keep passing; they already pass DataFrames with `mean`/`min`/`max`.
- After code change, regenerate PNGs with `python experiments/mentor_charts.py` from repo root so the embedded doc images match.

---

## File Structure

| File | Responsibility |
|---|---|
| `experiments/mentor_charts_plots.py` | Draw PNGs. Remove `ax.fill_between(...)` from `plot_timeseries_comparison` and `_draw_comparison_panel`. |
| `experiments/test_mentor_charts_plots.py` | Existing smoke tests stay; add one test that a mean-only DataFrame still plots (documents that min/max are unused). |
| `Guides and Info/mentor-update/MENTOR-UPDATE.md` | Legend + observation bullets currently mention “shaded min/max band”. |
| `Guides and Info/mentor-update/charts/**/*.png` and `charts_gallery/**/*.png` | Regenerated output; no code. |
| `experiments/mentor_charts_data.py` | **Do not modify.** |

---

### Task 1: Stop drawing min/max bands

**Files:**
- Modify: `experiments/mentor_charts_plots.py`
- Modify: `experiments/test_mentor_charts_plots.py`
- Test: `experiments/test_mentor_charts_plots.py`

**Interfaces:**
- Consumes: `plot_timeseries_comparison(baseline_avg: pd.DataFrame, rg_avg: pd.DataFrame, title: str, ylabel: str, out_path: Path, toggle_events: list[dict] | None = None) -> None` and `_draw_comparison_panel(ax, baseline_avg: pd.DataFrame, rg_avg: pd.DataFrame, subtitle: str, ylabel: str) -> None`. DataFrames currently have columns `mean`, `min`, `max` and a numeric index of elapsed seconds.
- Produces: same signatures. Plotters must read only the `mean` column (ignore `min`/`max` if present). Vertical toggle `axvline`s unchanged.

- [ ] **Step 1: Write the failing test**

Add this method to `TestPlotTimeseriesComparison` in `experiments/test_mentor_charts_plots.py` (keep the existing smoke tests; they still pass DataFrames that include `min`/`max`):

```python
    def test_plots_mean_only_dataframe_without_minmax_columns(self):
        baseline_avg = pd.DataFrame({"mean": [10.0, 12.0, 11.0]})
        rg_avg = pd.DataFrame({"mean": [10.0, 20.0, 25.0]})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_timeseries_comparison(
                baseline_avg, rg_avg, title="Test", ylabel="Goodput", out_path=out_path
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)
```

Add this method to `TestPlotSideBySideComparison` in the same file:

```python
    def test_side_by_side_accepts_mean_only_dataframes(self):
        mean_a = pd.DataFrame({"mean": [10.0, 11.0]})
        mean_b = pd.DataFrame({"mean": [8.0, 9.0]})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "chart.png"
            mcp.plot_side_by_side_comparison(
                pair_a=(mean_a, mean_a),
                pair_b=(mean_b, mean_b),
                title="Test",
                ylabel="Goodput",
                label_a="S4A",
                label_b="S4B",
                out_path=out_path,
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from repo root):

```powershell
python experiments/test_mentor_charts_plots.py TestPlotTimeseriesComparison.test_plots_mean_only_dataframe_without_minmax_columns TestPlotSideBySideComparison.test_side_by_side_accepts_mean_only_dataframes -v
```

Expected: FAIL. `plot_timeseries_comparison` currently does `ax.fill_between(..., baseline_avg["min"], baseline_avg["max"], ...)` which raises `KeyError: 'min'` (or equivalent) when those columns are absent.

- [ ] **Step 3: Write minimal implementation**

In `experiments/mentor_charts_plots.py`, change `plot_timeseries_comparison` to:

```python
def plot_timeseries_comparison(
    baseline_avg: pd.DataFrame,
    rg_avg: pd.DataFrame,
    title: str,
    ylabel: str,
    out_path: Path,
    toggle_events: list[dict] | None = None,
) -> None:
    """Plot baseline vs RetryGuard mean lines against elapsed seconds.
    If toggle_events is given (from mentor_charts_data.parse_toggle_events),
    draw a vertical dashed line per event, colored red for ON→OFF and green
    for OFF→ON."""
    fig, ax = plt.subplots(figsize=(9, 4.5))

    if not baseline_avg.empty:
        ax.plot(baseline_avg.index, baseline_avg["mean"], label="Baseline (TopFull only)", color="tab:blue")
    if not rg_avg.empty:
        ax.plot(rg_avg.index, rg_avg["mean"], label="TopFull + RetryGuard", color="tab:orange")

    for event in toggle_events or []:
        color = _TOGGLE_COLORS.get(event["direction"], "gray")
        ax.axvline(event["elapsed_seconds"], color=color, linestyle="--", linewidth=1, alpha=0.7)

    ax.set_title(title)
    ax.set_xlabel("Elapsed seconds")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
```

Change `_draw_comparison_panel` to:

```python
def _draw_comparison_panel(ax, baseline_avg: pd.DataFrame, rg_avg: pd.DataFrame, subtitle: str, ylabel: str) -> None:
    if not baseline_avg.empty:
        ax.plot(baseline_avg.index, baseline_avg["mean"], label="Baseline", color="tab:blue")
    if not rg_avg.empty:
        ax.plot(rg_avg.index, rg_avg["mean"], label="RetryGuard", color="tab:orange")
    ax.set_title(subtitle)
    ax.set_xlabel("Elapsed seconds")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", fontsize="small")
```

Do not remove the `min`/`max` keys from `average_series`. Do not touch `plot_multi_line`.

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python experiments/test_mentor_charts_plots.py -v
python experiments/test_mentor_charts.py -v
```

Expected: all PASS (including the two new tests and the existing smoke tests that still pass DataFrames with `min`/`max`).

- [ ] **Step 5: Commit**

```powershell
git add experiments/mentor_charts_plots.py experiments/test_mentor_charts_plots.py
git commit -m @"
Drop min/max shaded bands from Locust comparison charts.

The mean lines are enough; the bands made the mentor-update figures hard to read.
"@
```

---

### Task 2: Update the mentor doc and regenerate PNGs

**Files:**
- Modify: `Guides and Info/mentor-update/MENTOR-UPDATE.md`
- Modify: `Guides and Info/mentor-update/charts/**/*.png` (regenerated)
- Modify: `Guides and Info/mentor-update/charts_gallery/**/*.png` (regenerated)
- Test: visual check that a Locust comparison PNG no longer has a translucent fill under the line

**Interfaces:**
- Consumes: Task 1's `plot_timeseries_comparison` / `_draw_comparison_panel` (mean lines only).
- Produces: regenerated PNGs plus copy that no longer claims a shaded min/max band.

- [ ] **Step 1: Update the section-4 legend**

In `Guides and Info/mentor-update/MENTOR-UPDATE.md`, replace the paragraph that currently starts with `All charts below plot **Baseline** (mean of 3 repeats, shaded min/max band)` with:

```markdown
All charts below plot **Baseline** (mean of 3 repeats) against **RetryGuard** (mean of 3 repeats), x-axis in elapsed seconds. Where RetryGuard fired, vertical dashed lines mark disable (`ON→OFF`, red) and re-enable (`OFF→ON`, green) events. Additional per-endpoint/per-service charts not shown here are in `charts_gallery/<scenario>/`.
```

- [ ] **Step 2: Strip band language from observation bullets**

In the same file, edit only the bullets that mention bands (keep the numeric claims; just stop citing the band as evidence):

Section 4.1, first bullet — replace:

```markdown
- Baseline and RetryGuard system-wide goodput overlap around ~400 req/s after a shared ramp in the first ~50s; the min/max bands overlap for the full ~265s, and neither line steps at the 60s marker.
```

with:

```markdown
- Baseline and RetryGuard system-wide goodput overlap around ~400 req/s after a shared ramp in the first ~50s, and neither line steps at the 60s marker.
```

Section 4.1, second bullet — replace:

```markdown
- Rejection is not identically near zero in both conditions. RetryGuard stays in a narrow ~0.01–0.02 band, while baseline is mostly low but shows several spikes (mean ~0.04–0.09, with the last spike’s max band exceeding 0.25).
```

with:

```markdown
- Rejection is not identically near zero in both conditions. RetryGuard stays in a narrow ~0.01–0.02 range, while baseline is mostly low but shows several spikes (mean ~0.04–0.09).
```

Section 4.2, first bullet — replace `with a wider RetryGuard band` with `with a wider RetryGuard spread across repeats` only if that phrase is still accurate as prose about the three repeats; otherwise just delete the parenthetical about the band. Use this exact replacement:

```markdown
- After the first ~30s, RetryGuard mean goodput sits above baseline for most of the hold (often ~250–480 vs ~200–350 req/s) and the means converge again after ~450s. Rejection is lower on RetryGuard early (~0.2–0.45 vs ~0.4–0.6) then both remain high (~0.35–0.6) through the rest of the 10-minute hold.
```

Section 4.3, first bullet — replace `with a wider band` :

```markdown
- The checkout-endpoint (`postcheckout`) goodput collapses to near zero for both conditions after an initial ~5s spike (later bursts still <1 req/s), and postcheckout rejection sits near 1.0 in both. The conditions separate on the system-wide chart, not the checkout-endpoint chart: after the ~60s `ON→OFF`, RetryGuard mean goodput stays above baseline (often ~250–450 vs ~180–300 req/s).
```

Section 4.4, first bullet — replace `wide min/max band`:

```markdown
- On system-wide goodput and rejection, the baseline–RetryGuard gap is larger in B than in A. A both hold ~200 req/s / ~0.65 rejection (RetryGuard smoother; baseline has periodic dips to ~150 req/s). B has RetryGuard holding ~480–530 req/s with rejection ~0.05–0.15, while baseline sags after ~200s and rejection ~0.1–0.25.
```

Do not rewrite other bullets. Do not mention this plan or the pipeline README unless a sentence there currently describes the shaded band as something the PNGs show. `Guides and Info/mentor-update/README.md` does not describe the bands; leave it alone.

- [ ] **Step 3: Regenerate charts**

From repo root:

```powershell
python experiments/mentor_charts.py
```

Expected: prints `Generated ...` lines for S1/S2/S6, S3/S4A/S4B, retries/resources, S4 combined, and S5/S6 merge, then exits 0. PNGs under `Guides and Info/mentor-update/charts/` and `charts_gallery/` are overwritten.

- [ ] **Step 4: Confirm a comparison PNG no longer has a fill**

Open `Guides and Info/mentor-update/charts/S3_targeted_bottleneck/total_goodput.png`. Expected: two solid lines (blue Baseline, orange RetryGuard), red dashed vertical toggle(s), **no** translucent ribbon under either line. Spot-check `charts/S4_topology_position/total_goodput.png` (side-by-side, also previously used `fill_between`).

- [ ] **Step 5: Commit**

```powershell
git add "Guides and Info/mentor-update/MENTOR-UPDATE.md" "Guides and Info/mentor-update/charts" "Guides and Info/mentor-update/charts_gallery"
git commit -m @"
Regenerate mentor-update charts without min/max bands.

Update the section-4 legend and observation bullets so they match the mean-only figures.
"@
```

---

## Self-Review

**1. Spec coverage:** This plan implements the user request to drop the blue/orange min/max bands. Plotters (Task 1), regenerated figures + copy (Task 2). `average_series` left intact so other callers/tests stay valid. Multi-line charts out of scope (no bands today).

**2. Placeholder scan:** No TBD / “similar to Task N” / unimplemented error handling.

**3. Type consistency:** `plot_timeseries_comparison` and `_draw_comparison_panel` still take the same DataFrame shape; they now only index `["mean"]`.
