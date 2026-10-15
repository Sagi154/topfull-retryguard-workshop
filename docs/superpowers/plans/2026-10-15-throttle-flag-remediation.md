# Throttle Flag Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four remedies of AGENTS.md §6 "After every hold: check throttle data quality" for the TopFull-on flagged holds under `experiments/results/final results/`, without dropping any row and without re-running anything. TopFull-off holds are `N/A: TopFull off`, not flags.

**Architecture:** One small pure module (`experiments/throttle_stale.py`) finds the stale stretches of `topfull_throttle.csv` (no fresh threshold read for more than `STALE_GAP_S`, which is 10 s and must equal `analysis_score.THROTTLE_STALE_S`). `graphs_tool.py` and `multi_graphs_tool.py` use it to draw stale caps dashed, in the same colour as the fresh cap, with a grey band and a legend entry (remedy 2). `analysis_score.throttle_quality` flags only a TopFull-on hold, and only when a fetch failed or a gap exceeds 10 s (Task 9). A second script, `experiments/throttle_flags.py`, scans `final results/` through that function and generates the STATUS.md lines (remedy 1), the per-guide worklist and notes (remedy 3), and the TopFull-on re-run decision table (remedy 4). Everything it writes is reviewed as a diff before it is committed.

**Tech Stack:** Python 3.14, pandas, numpy, plotly (all in `experiments/requirements.txt`), pytest 9 running `unittest.TestCase` classes. Windows PowerShell.

## Global Constraints

- Work on a new branch `throttle-flag-remediation` from `main`. Commit steps below are written out; the executing agent runs them, this plan does not.
- **Do not drop rows.** `topfull_throttle.csv` and every run folder stay byte-identical. Stale values are marked, not removed (user decision, remedy 2).
- **Do not re-run any hold, bump any `run_number`, or touch the VMs.** Remedy 4 produces a decision list only. A re-run is the user's call and bumps `run_number` per [STATUS.md](../../../STATUS.md) "Next free slots".
- **TopFull-off holds are not flags.** Decided by the user (2026-10-15): `rg_only` and `both_off` are ignored for this issue. `analysis_score.throttle_quality` returns `flagged` false for them and the printed table says `N/A: TopFull off`. `throttle_flags.py` sets `HoldFlag.flagged` false for them, so they get no STATUS.md line, no guide edit, and no re-run row. `TF_OFF_LABEL = "N/A: TopFull off"`. Warnings and gap numbers are still computed and still printed, so the collector problem stays visible.
- **`THROTTLE_STALE_S` changes from 30 to 10.** A hold is flagged when any API goes longer than 10 s with no fresh threshold or admitted read (the normal poll is 5 s; a live cap is carried at most 6 s). A gap of exactly 10 s is not stale. `throttle_stale.STALE_GAP_S` is `10.0` and must stay equal to `float(analysis_score.THROTTLE_STALE_S)`. Measured on the live tree the same day: every clean TopFull-on hold has a longest gap of 5 s, and no TopFull-off hold sits in the 11–30 s band, so this change adds **zero** holds to the flag set. It still changes the rule, the graphs, and the docs, so a later 11 s hole is marked and flagged.
- Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid; every note this plan writes says so.
- Existing files use LF line endings. Never write STATUS.md, a guide, or a script through a path that converts to CRLF. After every edit run `git diff --stat` and confirm only the intended lines changed.
- Scope is only `experiments/results/final results/`. `campaign_48/`, `august_38/`, and the run logs under `docs/superpowers/plans/` are not edited.
- Run all Python from the repo root `C:\Users\sagi1\Projects\Workshop`. Tests: `python -m pytest <file> -v`.

## Decided (2026-10-15, do not reopen inside a task)

1. **TopFull-off holds are `N/A: TopFull off`, not flagged.** The audit's 25 `rg_only` flags, including `S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1` (0 `fetch failed` warnings, a 55 s gap, 6.3% of the span), are out of remedies 1, 3, and 4. The 55 s stretch is still a stale stretch if that run's graph is drawn (Task 1 marks any no-fresh stretch longer than 10 s, warnings or not), but the hold is not a flag and its guide is not edited.
2. **The stale gap is 10 s, not 30 s.** Same comparison the scorer already uses (`worst > THROTTLE_STALE_S`), with the constant lowered. Head, middle, and tail gaps all count. A `fetch failed` WARNING still flags a TopFull-on hold even when every gap is under 10 s.

**Live tree vs the audit file.** [2026-10-15-throttle-flag-audit.md](../../../Guides%20and%20Info/2026-10-15-throttle-flag-audit.md) says 144 holds, 50 flagged, 25 TopFull-on. A rescan the same evening found **146** leaf folders. The two added after the audit are both TopFull-on and flagged: `final_s2_both_burst_run3` and `final_s2_tf_only_run3`. After the two decisions the flag count the tools must reproduce is **27, all TopFull-on** (S2 has 8, S4A has 19). Do not force the scan back to 50 to match the audit file. 24 of the 27 are `final_` folders; the other 3 are the older `study6` / `study7` folders.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `experiments/throttle_stale.py` | Create | Pure functions: stale stretches, stale cap points, merged stale bands. No plotly. |
| `experiments/test_throttle_stale.py` | Create | Unit tests for the above. |
| `experiments/graphs_tool.py` | Modify | Stale cap traces, stale band shapes, explicit cap colours, on the stacked panel and the comparison chart. |
| `experiments/multi_graphs_tool.py` | Modify | Stale series share their fresh line's colour; the shared legend draws them dashed. |
| `experiments/test_graphs_tool.py` | Modify | Tests for stacked and comparison figures on flagged and clean runs. |
| `experiments/test_multi_graphs_tool.py` | Modify | Tests for colour sharing and the dashed legend entry. |
| `experiments/throttle_flags.py` | Create | Scan `final results/`; `audit`, `status`, `guides`, `rerun` subcommands. |
| `experiments/test_throttle_flags.py` | Create | Unit tests on a synthetic tree. |
| `Guides and Info/GRAPHS-TOOL.md` | Modify | Document stale marking. |
| `experiments/analysis_score.py` | Modify | `THROTTLE_STALE_S = 10`. `throttle_quality(..., topfull_on=True)` returns `flagged` false when TopFull is off, and still returns warnings and gaps. `topfull_enabled(run_dir)` reads `run_manifest.json`. The printed table says `N/A: TopFull off`. |
| `experiments/test_analysis_score.py` | Modify | Tests for the off-hold, the 10 s boundary, and `topfull_enabled`. |
| `AGENTS.md`, `Guides and Info/ANALYSIS-TEMPLATE.md` | Modify | Remedy 2 wording, plus the flag applies to TopFull-on holds only and the gap is 10 s. |
| `STATUS.md` | Modify (generated) | One throttle line per flagged hold, in that hold's Done bullet; one backfill bullet for holds that have none. |
| `Guides and Info/2026-10-14-s2-mode-matrix-abc.md` and the other guides in Task 7 | Modify | Name flagged holds per ANALYSIS-TEMPLATE.md item 17. |
| `Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md` | Create (generated) | Remedy 4 decision table for the user. |

## Background the executor needs

- `topfull_throttle.csv` columns: `timestamp, api, threshold, admitted_rps, threshold_fresh, admitted_fresh`, one row per API per second. A `*_fresh` of 1 is a live read. 0 is the last value carried. Normal live reads land every 5 s, so most rows of a clean hold are `fresh=0`. That is expected and is **not** stale.
- `analysis_score._longest_gap(stamps, fresh)` measures: first row to first fresh read, between fresh reads, last fresh read to last row. After Task 9, a TopFull-on hold is flagged when that is over 10 s on any API, or the collector log has any `fetch failed` WARNING. A TopFull-off hold is never flagged.
- `run_timeline.throttle_frames` already blanks non-fresh cap rows, then carries a fresh cap forward at most `THROTTLE_CARRY_S = 6` s. So today a stale stretch is an empty hole in the cap panel. The new dashed line fills exactly that hole, starting after the 6 s carry.
- 10000 is "no cap" and a live 0 is an empty read. Neither is drawn, for fresh or stale rows.
- Hold clock: `hold_clock.load_source(run_dir, "topfull_throttle", clock)` returns the CSV plus a `hold_s` column (seconds since the first Locust row).
- STATUS.md Done bullets are written per matrix or per hold group, one line each, not per hold. "Each flagged hold's Done bullet" therefore means the first bullet that names that hold's folder.

---

### Task 1: Stale-stretch module (remedy 2 core)

**Files:**
- Create: `experiments/throttle_stale.py`
- Test: `experiments/test_throttle_stale.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces (later tasks rely on these exact names):
  - `STALE_GAP_S = 10.0`, `CARRY_S = 6`, `NO_CAP = 10000.0`
  - `stale_stretches(hold_s, fresh, gap_s=STALE_GAP_S) -> list[tuple[float, float]]`
  - `stale_cap_series(df, gap_s=STALE_GAP_S, carry_s=CARRY_S, no_cap=NO_CAP) -> dict[str, tuple[np.ndarray, np.ndarray]]` (api to `(hold_s, cap)`)
  - `stale_bands(df, gap_s=STALE_GAP_S) -> list[tuple[float, float]]` (merged across APIs)
  - `df` is the frame from `hold_clock.load_source(..., "topfull_throttle", ...)`: columns `api, hold_s, threshold, threshold_fresh`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_throttle_stale.py`:

```python
"""Unit tests for experiments/throttle_stale.py."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import throttle_stale  # noqa: E402


def frame(fresh_until, total=100, api="getproduct", cap=150.0):
    rows = [{
        "api": api, "hold_s": float(s), "threshold": cap,
        "threshold_fresh": int(s % 5 == 0 and s <= fresh_until),
    } for s in range(total)]
    return pd.DataFrame(rows)


class TestStretches(unittest.TestCase):
    def test_a_gap_over_30_s_to_the_end_is_a_stretch(self):
        t = list(range(0, 100, 5))
        fresh = [x <= 20 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(20.0, 95.0)])

    def test_normal_five_second_polls_have_no_stretch(self):
        t = list(range(100))
        fresh = [x % 5 == 0 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [])

    def test_a_gap_before_the_first_fresh_read_counts(self):
        t = list(range(100))
        fresh = [x >= 40 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(0.0, 40.0)])

    def test_exactly_10_s_is_not_stale(self):
        t = list(range(11))
        fresh = [x in (0, 10) for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [])

    def test_eleven_seconds_is_a_stretch(self):
        t = list(range(12))
        fresh = [x in (0, 11) for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(0.0, 11.0)])

    def test_empty_input_gives_nothing(self):
        self.assertEqual(throttle_stale.stale_stretches([], []), [])


class TestCapSeries(unittest.TestCase):
    def test_stale_points_start_after_the_carry_window(self):
        series = throttle_stale.stale_cap_series(frame(fresh_until=20))
        x, y = series["getproduct"]
        self.assertEqual(float(x[0]), 27.0)
        self.assertEqual(float(x[-1]), 99.0)
        self.assertTrue(np.all(y == 150.0))

    def test_clean_hold_has_no_stale_series_and_no_band(self):
        df = frame(fresh_until=99)
        self.assertEqual(throttle_stale.stale_cap_series(df), {})
        self.assertEqual(throttle_stale.stale_bands(df), [])

    def test_no_cap_and_empty_reads_are_not_drawn(self):
        self.assertEqual(throttle_stale.stale_cap_series(frame(20, cap=10000.0)), {})
        self.assertEqual(throttle_stale.stale_cap_series(frame(20, cap=0.0)), {})

    def test_missing_or_old_csv_does_not_crash(self):
        self.assertEqual(throttle_stale.stale_cap_series(pd.DataFrame()), {})
        old = pd.DataFrame({"api": ["a"], "hold_s": [1.0], "threshold": [5.0]})
        self.assertEqual(throttle_stale.stale_cap_series(old), {})
        self.assertEqual(throttle_stale.stale_bands(old), [])


class TestBands(unittest.TestCase):
    def test_bands_merge_across_apis(self):
        df = pd.concat([frame(20, api="getproduct"), frame(40, api="getcart")])
        self.assertEqual(throttle_stale.stale_bands(df), [(20.0, 99.0)])

    def test_separate_stretches_stay_separate(self):
        rows = []
        for s in range(200):
            fresh = s % 5 == 0 and not (20 < s < 80) and not (100 < s < 160)
            rows.append({"api": "getproduct", "hold_s": float(s), "threshold": 150.0,
                         "threshold_fresh": int(fresh)})
        self.assertEqual(throttle_stale.stale_bands(pd.DataFrame(rows)),
                         [(20.0, 80.0), (100.0, 160.0)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_throttle_stale.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'throttle_stale'`.

- [ ] **Step 3: Write the module**

Create `experiments/throttle_stale.py`:

```python
"""Stale stretches of topfull_throttle.csv, for the graphs and the flag reports.

A stretch is a span with no fresh threshold read for longer than STALE_GAP_S (10 s).
This is the same comparison analysis_score.throttle_quality uses after Task 9
(head, middle, and tail gaps all count; a gap of exactly 10 s is not a stretch).
Task 9 sets THROTTLE_STALE_S = 10 so the two constants match. Rows are never dropped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STALE_GAP_S = 10.0
# Keep in step with run_timeline.THROTTLE_CARRY_S: the solid cap line already carries a
# fresh cap forward this long, so the dashed stale line starts after it.
CARRY_S = 6
NO_CAP = 10000.0
REQUIRED = {"api", "hold_s", "threshold", "threshold_fresh"}


def stale_stretches(hold_s, fresh, gap_s: float = STALE_GAP_S) -> list[tuple[float, float]]:
    """(start, end) of every gap between fresh reads longer than gap_s.

    The first row and the last row are anchors, so a hold whose reads never start,
    or stop early, has a head or tail stretch.
    """
    t = np.asarray(hold_s, dtype=float)
    ok = np.asarray(fresh, dtype=bool)
    if t.size == 0:
        return []
    anchors = [float(t[0])] + [float(x) for x in t[ok]] + [float(t[-1])]
    return [(a, b) for a, b in zip(anchors, anchors[1:]) if b - a > gap_s]


def _by_api(df: pd.DataFrame):
    if df is None or df.empty or not REQUIRED <= set(df.columns):
        return
    for api, group in df.groupby("api", sort=True):
        group = group.dropna(subset=["hold_s"]).sort_values("hold_s")
        if not group.empty:
            yield str(api), group


def stale_cap_series(
    df: pd.DataFrame,
    gap_s: float = STALE_GAP_S,
    carry_s: float = CARRY_S,
    no_cap: float = NO_CAP,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Carried (non-fresh) cap values inside a stale stretch, per API.

    Points start carry_s after the last fresh read, where the solid line stops.
    10000 (no cap) and 0 (empty read) are left out, as they are for fresh reads.
    """
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for api, group in _by_api(df):
        t = group["hold_s"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        cap = group["threshold"].to_numpy(dtype=float)
        keep = np.zeros(t.size, dtype=bool)
        for start, end in stale_stretches(t, fresh, gap_s):
            keep |= (t > start + carry_s) & (t <= end) & ~fresh
        keep &= (cap > 0) & (cap < no_cap)
        if keep.any():
            out[api] = (t[keep], cap[keep])
    return out


def stale_bands(df: pd.DataFrame, gap_s: float = STALE_GAP_S) -> list[tuple[float, float]]:
    """Stale stretches of every API, merged where they overlap."""
    spans: list[tuple[float, float]] = []
    for _api, group in _by_api(df):
        t = group["hold_s"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        spans.extend(stale_stretches(t, fresh, gap_s))
    spans.sort()
    merged: list[tuple[float, float]] = []
    for lo, hi in spans:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_throttle_stale.py -v`
Expected: `12 passed`.

- [ ] **Step 5: Commit**

```powershell
git checkout -b throttle-flag-remediation
git add experiments/throttle_stale.py experiments/test_throttle_stale.py
git commit -m "feat: find stale stretches of the TopFull throttle series"
```

---

### Task 2: graphs_tool marks stale caps (remedy 2, stacked panel and comparison chart)

**Files:**
- Modify: `experiments/graphs_tool.py` (imports near lines 17–26, `build_figure` near lines 259–369, `compare_figure` near lines 371–444)
- Test: `experiments/test_graphs_tool.py`

**Interfaces:**
- Consumes: `throttle_stale.stale_cap_series`, `throttle_stale.stale_bands` (Task 1).
- Produces (Task 3 and Task 4 rely on these exact names):
  - `graphs_tool.STALE_SUFFIX = " (stale)"`
  - `graphs_tool.STALE_BAND_FILL`, `STALE_BAND_NAME = "throttle-stale"`, `STALE_BAND_TEXT`
  - `graphs_tool.cap_color(api: str) -> str`
  - `graphs_tool.stale_cap_traces(throttle_df) -> list[go.Scatter]` (name `"<api> (stale)"`, `legendgroup="caps"`, dashed)
  - `graphs_tool.stale_band_layout(bands, xref, yref) -> tuple[list[dict], list[dict]]` (shape dicts, annotation dicts)

Behaviour: fresh cap lines stay solid and get an explicit per-API colour from `cap_color`. A flagged run gets, per API with a carried cap inside a stale stretch, a dashed line `"<api> (stale)"` in the same colour, plus a grey rectangle over each stale stretch labelled "no fresh cap read". A clean run (or one without the CSV) gets no extra traces or shapes.

- [ ] **Step 1: Write the failing tests**

In `experiments/test_graphs_tool.py`, change the existing import line `from test_hold_clock import E, iso, make_run  # noqa: E402` to:

```python
from test_hold_clock import E, iso, make_run, write_csv  # noqa: E402
```

Append at the end of the file, above any `if __name__ == "__main__":` line (keep that line last):

```python
THROTTLE_HEADER = ["timestamp", "api", "threshold", "admitted_rps",
                   "threshold_fresh", "admitted_fresh"]


def add_throttle(run: Path, fresh_until: int, total: int = 80, cap: float = 150.0) -> None:
    """One API, one row a second from hold second ~0; fresh every 5 s up to fresh_until."""
    rows = []
    for s in range(total):
        ok = int(s % 5 == 0 and s <= fresh_until)
        rows.append([iso(E + 20 + s), "getproduct", cap, 10.0, ok, ok])
    write_csv(run / "topfull_throttle.csv", THROTTLE_HEADER, rows)


def named(fig, name):
    return next((t for t in fig.data if t.name == name), None)


def stale_bands(fig):
    return [s for s in fig.layout.shapes if s.name == graphs_tool.STALE_BAND_NAME]


class TestStaleCaps(unittest.TestCase):
    def test_flagged_run_draws_the_stale_cap_dashed_in_the_same_colour(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            add_throttle(run, fresh_until=20)
            fig = graphs_tool.build_figure(run)
        fresh = named(fig, "getproduct")
        stale = named(fig, "getproduct (stale)")
        self.assertIsNotNone(fresh)
        self.assertIsNotNone(stale)
        self.assertIsNone(fresh.line.dash)
        self.assertEqual(stale.line.dash, "dash")
        self.assertEqual(stale.line.color, fresh.line.color)
        self.assertEqual(stale.line.color, graphs_tool.cap_color("getproduct"))
        self.assertEqual(stale.legendgroup, "caps")
        self.assertEqual(stale.yaxis, graphs_tool.axis(graphs_tool.ROW["caps"], "y"))
        self.assertTrue(all(v == 150.0 for v in stale.y))
        # The dashed line starts where the solid carry stops, so the two never overlap.
        self.assertGreater(min(stale.x), max(fresh.x))

    def test_flagged_run_shades_the_stale_stretch_on_the_cap_panel_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            add_throttle(run, fresh_until=20)
            fig = graphs_tool.build_figure(run)
        bands = stale_bands(fig)
        self.assertEqual(len(bands), 1)
        self.assertEqual(bands[0].xref, graphs_tool.axis(graphs_tool.ROW["caps"], "x"))
        self.assertEqual(bands[0].fillcolor, graphs_tool.STALE_BAND_FILL)
        self.assertAlmostEqual(bands[0].x0, 20, delta=3)
        self.assertAlmostEqual(bands[0].x1, 79, delta=3)
        texts = [a.text for a in fig.layout.annotations]
        self.assertIn(graphs_tool.STALE_BAND_TEXT, texts)

    def test_clean_run_has_no_stale_trace_and_no_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            add_throttle(run, fresh_until=79)
            fig = graphs_tool.build_figure(run)
            compare = graphs_tool.compare_figure(run)
        for figure in (fig, compare):
            self.assertIsNotNone(named(figure, "getproduct"))
            self.assertIsNone(named(figure, "getproduct (stale)"))
            self.assertEqual(stale_bands(figure), [])

    def test_run_without_a_throttle_file_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            fig = graphs_tool.build_figure(run)
            compare = graphs_tool.compare_figure(run)
        for figure in (fig, compare):
            self.assertEqual([t.name for t in figure.data if t.name.endswith(graphs_tool.STALE_SUFFIX)], [])
            self.assertEqual(stale_bands(figure), [])

    def test_comparison_chart_has_a_legend_entry_that_starts_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            add_throttle(run, fresh_until=20)
            fig = graphs_tool.compare_figure(run)
            html_text = render(run)
        stale = named(fig, "getproduct (stale)")
        self.assertIsNotNone(stale)
        self.assertEqual(stale.visible, "legendonly")
        self.assertEqual(stale.meta, "req/s")
        self.assertEqual(stale.yaxis, "y")
        self.assertEqual(stale.line.dash, "dash")
        self.assertEqual(stale.line.color, named(fig, "getproduct").line.color)
        self.assertEqual(len(stale_bands(fig)), 1)
        self.assertEqual(stale_bands(fig)[0].xref, "x")
        self.assertIn("getproduct (stale)", html_text)
        self.assertIn(graphs_tool.STALE_BAND_NAME, html_text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_graphs_tool.py::TestStaleCaps -v`
Expected: 5 FAILED with `AttributeError: module 'graphs_tool' has no attribute 'cap_color'` (or `STALE_BAND_NAME`).

- [ ] **Step 3: Add the imports, constants, and helpers**

In `experiments/graphs_tool.py`, after `import plotly.io as pio` add:

```python
import plotly.colors as plotly_colors
```

After `import run_timeline  # noqa: E402` add:

```python
import analysis_score  # noqa: E402
import throttle_stale  # noqa: E402
```

Immediately above `def build_figure(` insert:

```python
# A flagged hold's carried caps are drawn, not dropped: dashed, in the fresh line's
# colour, with a grey band over the stretch that had no fresh read.
STALE_SUFFIX = " (stale)"
STALE_BAND_FILL = "rgba(128,128,128,0.18)"
STALE_BAND_NAME = "throttle-stale"
STALE_BAND_TEXT = "no fresh cap read"
CAP_PALETTE = plotly_colors.qualitative.Dark24


def cap_color(api: str) -> str:
    """One fixed colour per entry API, so a fresh cap and its stale line match."""
    order = list(analysis_score.APIS)
    index = order.index(api) if api in order else len(order)
    return CAP_PALETTE[index % len(CAP_PALETTE)]


def stale_cap_traces(throttle_df: pd.DataFrame) -> list[go.Scatter]:
    """One dashed trace per API that has a carried cap inside a stale stretch."""
    traces = []
    for api, (x, y) in throttle_stale.stale_cap_series(throttle_df).items():
        traces.append(go.Scatter(
            x=[float(v) for v in x], y=[float(v) for v in y], mode="lines",
            name=api + STALE_SUFFIX, legendgroup="caps",
            legendgrouptitle={"text": ylabel("caps"), "font": {"color": "black"}},
            line={"width": 1.4, "dash": "dash", "color": cap_color(api)},
            hovertemplate="%{y:.1f} (carried, not a fresh read)<extra>%{fullData.name}</extra>",
        ))
    return traces


def stale_band_layout(bands, xref: str, yref: str) -> tuple[list[dict], list[dict]]:
    """Grey rectangles and their labels, for one axis pair."""
    shapes = [{
        "type": "rect", "xref": xref, "yref": yref, "x0": lo, "x1": hi, "y0": 0, "y1": 1,
        "fillcolor": STALE_BAND_FILL, "line": {"width": 0}, "layer": "below",
        "name": STALE_BAND_NAME,
    } for lo, hi in bands]
    notes = [{
        "x": lo, "xref": xref, "y": 1, "yref": yref, "xanchor": "left", "yanchor": "top",
        "text": STALE_BAND_TEXT, "showarrow": False, "font": {"size": 9, "color": "gray"},
    } for lo, _hi in bands]
    return shapes, notes
```

- [ ] **Step 4: Wire the stacked figure**

In `build_figure`, replace

```python
        line = {"width": 1.2, "shape": "hv"} if step else {"width": 1.2}
```

with

```python
        line = {"width": 1.2, "shape": "hv"} if step else {"width": 1.2}
        if key == "caps":
            line["color"] = cap_color(name)
```

Immediately above `    slo = slo_miss(view)` (the one in `build_figure`) insert:

```python
    throttle_df = hold_clock.load_source(run_dir, "topfull_throttle", clock)
    for trace in stale_cap_traces(throttle_df):
        fig.add_trace(trace, row=ROW["caps"], col=1)
        used.add("caps")
```

Immediately above `    fig.update_layout(shapes=shapes)` insert:

```python
    band_shapes, band_notes = stale_band_layout(
        throttle_stale.stale_bands(throttle_df),
        axis(ROW["caps"], "x"), f"{axis(ROW['caps'], 'y')} domain",
    )
    shapes.extend(band_shapes)
    for note in band_notes:
        fig.add_annotation(**note)
```

- [ ] **Step 5: Wire the comparison chart**

In `compare_figure`, replace

```python
        line = {"width": 1.4, "shape": "hv"} if step else {"width": 1.4}
```

with

```python
        line = {"width": 1.4, "shape": "hv"} if step else {"width": 1.4}
        if key == "caps":
            line["color"] = cap_color(name)
```

Immediately above the comment line `    # Event lines use a fixed 0–1 axis over the plot, so a shed stays full height` insert:

```python
    throttle_df = hold_clock.load_source(run_dir, "topfull_throttle", clock)
    for trace in stale_cap_traces(throttle_df):
        trace.update(visible="legendonly", meta=UNIT["caps"], yaxis=trace_yaxis(UNIT["caps"]))
        fig.add_trace(trace)
    band_shapes, band_notes = stale_band_layout(
        throttle_stale.stale_bands(throttle_df), "x", "y domain")
    for shape in band_shapes:
        fig.add_shape(**shape)
    for note in band_notes:
        fig.add_annotation(**note)
```

- [ ] **Step 6: Run the new tests, then the whole file**

Run: `python -m pytest experiments/test_graphs_tool.py::TestStaleCaps -v`
Expected: `5 passed`.

Run: `python -m pytest experiments/test_graphs_tool.py -q`
Expected: all pass (the pre-existing tests have no throttle file or a clean one, so nothing else changes).

If `test_flagged_run_shades_the_stale_stretch_on_the_cap_panel_only` is off by more than the 3 s delta, print `hold_clock.read_clock(run)["start_utc"]` and widen the delta to the observed Locust-clock fit error. Do not loosen the assertion for any other reason.

- [ ] **Step 7: Commit**

```powershell
git add experiments/graphs_tool.py experiments/test_graphs_tool.py
git commit -m "feat: graphs_tool draws stale TopFull caps dashed inside a grey band"
```

---

### Task 3: multi_graphs_tool keeps stale lines matched and dashed in the legend (remedy 2, comparison panels)

**Files:**
- Modify: `experiments/multi_graphs_tool.py` (`assign_colors` near lines 118–134, `legend_figure` near lines 137–167)
- Test: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: `graphs_tool.STALE_SUFFIX` (Task 2), `graphs_tool.compare_figure` already emitting `"<api> (stale)"` traces and `throttle-stale` shapes (Task 2).
- Produces: `assign_colors` gives `(group, "<api> (stale)")` the colour of `(group, "<api>")`; `legend_figure` draws names ending in `STALE_SUFFIX` with `line.dash == "dash"` and every other item `"solid"`.

The panels need no other change: `panel_figure` copies `compare_figure`, so the band shapes and the stale trace come along. `series_union` keys on `(legendgroup, name)`, so `getproduct (stale)` becomes one extra shared legend entry, and a run without it shows the existing "run lacks this series" note when that entry is turned on.

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_multi_graphs_tool.py`, above any `if __name__ == "__main__":` line:

```python
class TestStaleSeries(unittest.TestCase):
    def stale_figs(self):
        both = synthetic([("caps", "getproduct", [1.0]), ("caps", "getproduct (stale)", [2.0])], 100)
        both.data[1].line.dash = "dash"
        fresh_only = synthetic([("caps", "getproduct", [1.0])], 100)
        return [fresh_only, both]

    def test_stale_series_takes_the_colour_of_its_fresh_line(self):
        figs = self.stale_figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("caps", "getproduct (stale)")], colors[("caps", "getproduct")])
        stale = next(t for t in figs[1].data if t.name == "getproduct (stale)")
        self.assertEqual(stale.line.color, colors[("caps", "getproduct")])
        self.assertEqual(stale.line.dash, "dash")

    def test_colour_is_shared_even_when_the_stale_line_is_seen_first(self):
        stale_first = synthetic([("caps", "getproduct (stale)", [2.0])], 100)
        fresh_second = synthetic([("caps", "getproduct", [1.0])], 100)
        figs = [stale_first, fresh_second]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("caps", "getproduct (stale)")], colors[("caps", "getproduct")])

    def test_legend_draws_the_stale_entry_dashed_and_the_rest_solid(self):
        figs = self.stale_figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        legend = multi_graphs_tool.legend_figure(union, colors)
        by_name = {t.name: t for t in legend.data}
        self.assertEqual(by_name["getproduct (stale)"].line.dash, "dash")
        self.assertEqual(by_name["getproduct"].line.dash, "solid")
        self.assertEqual(by_name["getproduct (stale)"].visible, "legendonly")
        self.assertEqual(by_name["getproduct (stale)"].legendgroup, "caps")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_multi_graphs_tool.py::TestStaleSeries -v`
Expected: 3 FAILED (colours differ; `dash` is `None`, not `"dash"`/`"solid"`).

- [ ] **Step 3: Implement**

In `multi_graphs_tool.assign_colors`, replace the body from `colors = {}` to just before the `for fig in figs:` loop:

```python
    colors = {}
    for index, (key, trace) in enumerate(union.items()):
        if key[0] == graphs_tool.EVENT_GROUP:
            colors[key] = trace.line.color
        else:
            colors[key] = PALETTE[index % len(PALETTE)]
```

with

```python
    colors = {}
    stale_keys = []
    for index, (key, trace) in enumerate(union.items()):
        if key[0] == graphs_tool.EVENT_GROUP:
            colors[key] = trace.line.color
        elif key[1].endswith(graphs_tool.STALE_SUFFIX):
            stale_keys.append((index, key))
        else:
            colors[key] = PALETTE[index % len(PALETTE)]
    # A stale line is its fresh line's carried values, so it keeps that colour.
    for index, key in stale_keys:
        fresh = (key[0], key[1][: -len(graphs_tool.STALE_SUFFIX)])
        colors[key] = colors.get(fresh, PALETTE[index % len(PALETTE)])
```

In `legend_figure`, replace

```python
            line={"width": 2, "color": colors[(group, name)]},
```

with

```python
            line={"width": 2, "color": colors[(group, name)],
                  "dash": "dash" if name.endswith(graphs_tool.STALE_SUFFIX) else "solid"},
```

- [ ] **Step 4: Run the new tests, then both graph test files including the browser tests**

Run: `python -m pytest experiments/test_multi_graphs_tool.py::TestStaleSeries -v`
Expected: `3 passed`.

Run: `python -m pytest experiments/test_multi_graphs_tool.py experiments/test_graphs_tool.py -q`
Expected: all pass. The pre-change baseline for `test_graphs_tool.py`, `test_multi_graphs_tool.py`, and `test_analysis_score.py` together was 58 passed in about 50 s; these two files now add 8 new tests (5 in Task 2, 3 here). Browser tests that cannot start a browser are skipped by the file's existing `BrowserCase`; a skip count that was already there is fine, a new failure is not.

- [ ] **Step 5: Render one real flagged pair and look at it**

```powershell
python experiments/multi_graphs_tool.py "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run1" "experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1"
```

Expected: prints the `experiments/explore_out/multi_final_s2_both_burst_run1__s2_burst20_rgtf1.html` path. Open it, switch on the `caps` group in the legend: the first panel shows solid caps up to about 3 min, then dashed lines inside a grey "no fresh cap read" band; the second panel (clean) shows no band. `explore_out/` is git-ignored, so this file is not committed.

- [ ] **Step 6: Commit**

```powershell
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "feat: multi_graphs_tool shares stale-cap colour and dashes it in the legend"
```

---

### Task 4: Documentation for the stale marking (remedy 2 wording)

**Files:**
- Modify: `Guides and Info/GRAPHS-TOOL.md` (the `**TopFull cap.**` paragraph near line 58, the comparison table row near line 76, end of file)
- Modify: `AGENTS.md` (§6, "After every hold: check throttle data quality", item (2))
- Modify: `Guides and Info/ANALYSIS-TEMPLATE.md` (item 17, line 58)

**Interfaces:**
- Consumes: the behaviour from Tasks 2–3.
- Produces: docs only.

- [ ] **Step 1: GRAPHS-TOOL.md, TopFull cap paragraph**

Replace this exact paragraph:

```markdown
**TopFull cap.** A reading of 10000 means no cap and is not drawn. A fresh 0 is an empty read, not a cap of zero. The last usable cap is held for at most 6 s. If `analysis_score.py` flags the hold (`Throttle data quality`), do not read the cap line as measured. Goodput, P95, rejection, retries, and overload ticks do not use that file.
```

with:

```markdown
**TopFull cap.** A reading of 10000 means no cap and is not drawn. A fresh 0 is an empty read, not a cap of zero. The last usable cap is held for at most 6 s as a solid line. If the collector then goes more than 10 s without a fresh threshold read (the same rule `analysis_score.py` uses to flag a TopFull-on hold in `Throttle data quality`; a TopFull-off hold is `N/A: TopFull off` and is not flagged), the cap panel shows the stretch as a **grey band labelled "no fresh cap read"**, and the cap the collector kept repeating is drawn as a **dashed line** named `<api> (stale)` in the same colour as that API's solid line. The dashed value is a carried number, not a measurement. Rows are not dropped; the band and the dashes are the only difference. A hold that is flagged only because admitted-rate reads went stale (threshold reads stayed fresh) shows no band, because the cap line itself is measured. A clean hold shows neither. Goodput, P95, rejection, retries, and overload ticks do not use that file.
```

- [ ] **Step 2: GRAPHS-TOOL.md, comparison table row**

Replace `| req/s | left, always there | Goodput, RPS, TopFull cap |` with `| req/s | left, always there | Goodput, RPS, TopFull cap, TopFull cap (stale) |`.

- [ ] **Step 3: GRAPHS-TOOL.md, multi section**

The `multi_graphs_tool` section is the last section of the file. Append at the end of the file:

```markdown

**Stale caps in the comparison panels.** A flagged run's panel carries the same grey band and the same dashed `<api> (stale)` line. The shared legend lists `<api> (stale)` as its own entry under the cap group, drawn dashed, in the colour of `<api>`. It starts hidden like every other line. A run with no stale stretch has no such series, so turning the entry on shows the usual "this run lacks the series" note for that run. Use it to see at a glance which of the compared holds have measured caps and which have carried ones.
```

- [ ] **Step 4: AGENTS.md item (2)**

Replace this exact fragment in §6:

```
(2) never use its cap or admitted-rate numbers as measured (drop them or filter on `*_fresh==1`);
```

with:

```
(2) never use its cap or admitted-rate numbers as measured: the rows stay in the CSV, filter any number on `*_fresh==1`, and `graphs_tool` / `multi_graphs_tool` draw a stale stretch as a grey band with dashed `(stale)` lines;
```

- [ ] **Step 5: ANALYSIS-TEMPLATE.md item 17**

Replace this exact fragment:

```
Name every flagged hold in one sentence, and either drop it from cap and admitted-rate numbers or filter those numbers on `threshold_fresh==1` / `admitted_fresh==1`.
```

with:

```
Name every flagged hold in one sentence, and filter its cap and admitted-rate numbers on `threshold_fresh==1` / `admitted_fresh==1`. The rows stay in the file; the graphs draw a stale stretch as a grey band with dashed `(stale)` lines.
```

- [ ] **Step 6: Verify only intended lines changed**

Run: `git diff --stat`
Expected: `AGENTS.md`, `ANALYSIS-TEMPLATE.md`, `GRAPHS-TOOL.md` each changed by a few lines. A diff of hundreds of lines means line endings were converted: `git checkout -- <file>` and redo the edit.

- [ ] **Step 7: Commit**

```powershell
git add AGENTS.md "Guides and Info/ANALYSIS-TEMPLATE.md" "Guides and Info/GRAPHS-TOOL.md"
git commit -m "docs: stale throttle stretches are marked, not dropped"
```

---

### Task 5: Flag scan core (shared by remedies 1, 3, 4)

**Files:**
- Create: `experiments/throttle_flags.py`
- Test: `experiments/test_throttle_flags.py`

**Interfaces:**
- Consumes: `analysis_score.throttle_quality`, `analysis_score._rows`, `analysis_score.parse_ts`, `throttle_stale.stale_stretches` (Task 1).
- Produces (Tasks 6–9 rely on these exact names):
  - `HoldFlag` frozen dataclass: `path: str` (relative to root, forward slashes), `scenario: str` (`S1`…`S4B`), `mode: str` (`normal`/`burst`), `variant: str`, `name: str`, `topfull_on: bool`, `flagged: bool`, `warnings: int`, `first_warning: str | None`, `threshold_gap_s: float`, `admitted_gap_s: float`, `threshold_stale_pct: float`, `admitted_stale_pct: float`.
  - `scan(root: Path) -> list[HoldFlag]` (sorted by path)
  - `TF_OFF_LABEL = "N/A: TopFull off"`, `TF_ON_LABEL = "FLAGGED"`, `label(h: HoldFlag) -> str`
  - `name_pattern(name: str) -> re.Pattern`
  - `DEFAULT_ROOT`, `STATUS_PATH`, `GUIDES_DIR`

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_throttle_flags.py`:

```python
"""Unit tests for experiments/throttle_flags.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import throttle_flags  # noqa: E402
from test_hold_clock import E, iso, write_csv  # noqa: E402

HEADER = ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"]


def make_hold(root, scenario_dir, variant, name, fresh_until=99, warnings=0,
              total=100, csv=True):
    run = Path(root) / scenario_dir / variant / name
    run.mkdir(parents=True)
    if csv:
        rows = []
        for s in range(total):
            ok = int(s % 5 == 0 and s <= fresh_until)
            rows.append([iso(E + s), "getproduct", 150.0, 10.0, ok, ok])
        write_csv(run / "topfull_throttle.csv", HEADER, rows)
    lines = ["2026-10-13T00:00:00Z  START  x"]
    lines += [f"2026-10-13T00:00:{i % 60:02d}Z  WARNING  thresholds fetch failed: timed out"
              for i in range(warnings)]
    (run / "topfull_throttle_collector.log").write_text("\n".join(lines), encoding="utf-8")
    return run


def hold(name, on=True, flagged=True, warnings=5, tgap=60.0, agap=60.0, tpct=50.0, apct=50.0,
         scenario="S2", mode="burst", variant=None):
    variant = variant or ("both" if on else "rg_only")
    return throttle_flags.HoldFlag(
        path=f"S2_sustained_overload_{mode}/{variant}/{name}", scenario=scenario, mode=mode,
        variant=variant, name=name, topfull_on=on, flagged=flagged, warnings=warnings,
        first_warning="2026-10-13T00:00:00Z" if warnings else None,
        threshold_gap_s=tgap, admitted_gap_s=agap,
        threshold_stale_pct=tpct, admitted_stale_pct=apct,
    )


class TestScan(unittest.TestCase):
    def scan(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            return throttle_flags.scan(Path(tmp))

    def test_clean_hold_is_not_flagged(self):
        flags = self.scan(lambda r: make_hold(r, "S2_sustained_overload_burst", "both", "run_a"))
        self.assertEqual(len(flags), 1)
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertTrue(h.topfull_on)
        self.assertEqual((h.scenario, h.mode, h.variant, h.name),
                         ("S2", "burst", "both", "run_a"))

    def test_tail_stale_hold_reports_gap_and_percent_of_span(self):
        flags = self.scan(lambda r: make_hold(
            r, "S4A_topology_position_normal", "tf_only", "run_b", fresh_until=20))
        h = flags[0]
        self.assertTrue(h.flagged)
        self.assertEqual(h.scenario, "S4A")
        self.assertEqual(h.mode, "normal")
        self.assertEqual(h.threshold_gap_s, 79.0)
        self.assertAlmostEqual(h.threshold_stale_pct, 79 / 99 * 100, places=1)
        self.assertAlmostEqual(h.admitted_stale_pct, 79 / 99 * 100, places=1)
        self.assertEqual(h.warnings, 0)

    def test_fetch_warnings_on_a_topfull_off_hold_do_not_flag_it(self):
        flags = self.scan(lambda r: make_hold(
            r, "S2_sustained_overload_burst", "rg_only", "run_c", warnings=3))
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertFalse(h.topfull_on)
        self.assertEqual(h.warnings, 3)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertEqual(h.first_warning, "2026-10-13T00:00:00Z")

    def test_missing_csv_is_not_a_flag_even_with_log_warnings(self):
        flags = self.scan(lambda r: make_hold(
            r, "S1_normal_operation_normal", "tf_only", "run_d", csv=False, warnings=2))
        self.assertFalse(flags[0].flagged)

    def test_scan_is_sorted_and_uses_forward_slashes(self):
        def build(root):
            make_hold(root, "S2_sustained_overload_burst", "both", "b")
            make_hold(root, "S1_normal_operation_normal", "both", "a")
        flags = self.scan(build)
        self.assertEqual([h.path for h in flags], [
            "S1_normal_operation_normal/both/a", "S2_sustained_overload_burst/both/b"])


class TestLabels(unittest.TestCase):
    def test_label_separates_topfull_on_and_off(self):
        self.assertEqual(throttle_flags.label(hold("a", on=True)), throttle_flags.TF_ON_LABEL)
        self.assertEqual(throttle_flags.label(hold("a", on=False)), throttle_flags.TF_OFF_LABEL)

    def test_name_pattern_does_not_match_a_longer_name(self):
        pattern = throttle_flags.name_pattern("final_4a_x_run1")
        self.assertTrue(pattern.search("folders `final_4a_x_run1` and more"))
        self.assertFalse(pattern.search("folder final_4a_x_run1_r2"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_throttle_flags.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'throttle_flags'`.

- [ ] **Step 3: Write the scan core**

Create `experiments/throttle_flags.py`:

```python
"""Throttle-flag reports over experiments/results/final results.

    python experiments/throttle_flags.py audit  [--root DIR]
    python experiments/throttle_flags.py status [--root DIR] [--write]
    python experiments/throttle_flags.py guides [--root DIR] [--notes]
    python experiments/throttle_flags.py rerun  [--root DIR] [--out PATH]

The flag rule is analysis_score.throttle_quality, with one extra gate: a TopFull-off
variant (`rg_only`, `both_off`) is never flagged. A TopFull-on hold is flagged when the
collector log has any `fetch failed` WARNING, or any API goes longer than
analysis_score.THROTTLE_STALE_S (10 s after Task 9; 30 s until that task lands) with no
fresh threshold or admitted read. A missing or empty topfull_throttle.csv is not a flag.
Nothing here edits a run folder.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import throttle_stale  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO / "experiments" / "results" / "final results"
STATUS_PATH = REPO / "STATUS.md"
GUIDES_DIR = REPO / "Guides and Info"
RERUN_PATH = GUIDES_DIR / "2026-10-15-throttle-flag-rerun-decisions.md"
AUDIT_PATH = GUIDES_DIR / "2026-10-15-throttle-flag-audit.md"
AUDIT_TAG = "Throttle flags (2026-10-15 audit):"
BACKFILL_HEAD = "- **Throttle flag backfill (2026-10-15)** — holds with no Done bullet of their own."
TOPFULL_ON_VARIANTS = ("both", "tf_only")
# Decided 2026-10-15: TopFull-off holds are not flags. This label is what `label()`
# returns for them; status, guides, and rerun only iterate holds with flagged=True.
TF_ON_LABEL = "FLAGGED"
TF_OFF_LABEL = "N/A: TopFull off"
CELL_SUFFIX = re.compile(r"_run\d+(?:_r\d+)?$")
SCENARIO_ORDER = ("S1", "S2", "S3", "S4A", "S4B")


@dataclass(frozen=True)
class HoldFlag:
    path: str
    scenario: str
    mode: str
    variant: str
    name: str
    topfull_on: bool
    flagged: bool
    warnings: int
    first_warning: str | None
    threshold_gap_s: float
    admitted_gap_s: float
    threshold_stale_pct: float
    admitted_stale_pct: float


def label(h: HoldFlag) -> str:
    return TF_ON_LABEL if h.topfull_on else TF_OFF_LABEL


def name_pattern(name: str) -> re.Pattern:
    """The folder name as a whole token: `_r2` and `_run10` do not match `run1`."""
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")


def _stale_pct(rows: list[dict], key: str) -> float:
    """Worst API's share of its first-to-last span inside a stretch over STALE_GAP_S."""
    by_api: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("timestamp"):
            by_api[row.get("api", "")].append(row)
    worst = 0.0
    for series in by_api.values():
        series.sort(key=lambda r: r["timestamp"])
        stamps = [analysis_score.parse_ts(r["timestamp"]) for r in series]
        t = np.array([(s - stamps[0]).total_seconds() for s in stamps])
        span = float(t[-1] - t[0])
        if span <= 0:
            continue
        fresh = np.array([int(float(r.get(key) or 0)) == 1 for r in series])
        inside = sum(hi - lo for lo, hi in throttle_stale.stale_stretches(t, fresh))
        worst = max(worst, 100.0 * inside / span)
    return worst


def scan_hold(root: Path, run_dir: Path) -> HoldFlag:
    scenario_dir, variant, name = run_dir.relative_to(root).parts
    rows = analysis_score._rows(run_dir / "topfull_throttle.csv")
    topfull_on = variant in TOPFULL_ON_VARIANTS
    # Do not pass topfull_on into throttle_quality here. That parameter arrives in
    # Task 9. Until then the scorer still flags a TopFull-off hold, and this AND
    # is what keeps those holds out of flagged.
    quality = analysis_score.throttle_quality(rows, run_dir / "topfull_throttle_collector.log")
    return HoldFlag(
        path="/".join((scenario_dir, variant, name)),
        scenario=scenario_dir.split("_", 1)[0],
        mode=scenario_dir.rsplit("_", 1)[1],
        variant=variant,
        name=name,
        topfull_on=topfull_on,
        flagged=bool(quality["flagged"] and quality["has_csv"] and topfull_on),
        warnings=int(quality["warnings"]),
        first_warning=quality["first_warning"],
        threshold_gap_s=float(quality["threshold_gap_s"] or 0.0),
        admitted_gap_s=float(quality["admitted_gap_s"] or 0.0),
        threshold_stale_pct=_stale_pct(rows, "threshold_fresh"),
        admitted_stale_pct=_stale_pct(rows, "admitted_fresh"),
    )


def scan(root: Path) -> list[HoldFlag]:
    root = Path(root)
    run_dirs = sorted(p for p in root.glob("*/*/*") if p.is_dir())
    return sorted((scan_hold(root, p) for p in run_dirs), key=lambda h: h.path)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_throttle_flags.py -v`
Expected: `7 passed`.

- [ ] **Step 5: Add the `audit` subcommand and check parity with the audit document**

Append to `experiments/throttle_flags.py`:

```python
def audit_text(flags: list[HoldFlag]) -> str:
    flagged = [h for h in flags if h.flagged]
    on = [h for h in flagged if h.topfull_on]
    lines = [
        f"runs={len(flags)} flagged={len(flagged)} "
        f"topfull_on_flagged={len(on)} topfull_off_flagged={len(flagged) - len(on)}",
    ]
    for h in flagged:
        lines.append(
            f"{h.path}  {'on' if h.topfull_on else 'off'}  warnings={h.warnings}  "
            f"gap_s={h.threshold_gap_s:.0f}/{h.admitted_gap_s:.0f}  "
            f"stale_pct={h.threshold_stale_pct:.1f}/{h.admitted_stale_pct:.1f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "status", "guides", "rerun"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    flags = scan(args.root)
    if args.cmd == "audit":
        print(audit_text(flags))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `python experiments/throttle_flags.py audit`
Expected first line. This is the live tree after the TopFull-off decision, not the audit file's 144 / 50:

```
runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0
```

Then spot-check two lines against [the audit](../../../Guides%20and%20Info/2026-10-15-throttle-flag-audit.md) section 2, and confirm the TopFull-off hold is absent:

```
S2_sustained_overload_burst/both/final_s2_both_burst_run1  on  warnings=196  gap_s=494/494  stale_pct=69.1/69.1
S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1  on  warnings=228  gap_s=4/575  stale_pct=0.0/83.6
```

```powershell
python experiments/throttle_flags.py audit | Select-String "final_s3_rg_only_normal_run1|rg_only"
```

Expected: no output. `final_s2_both_burst_run3` and `final_s2_tf_only_run3` must each appear once (they are not in the audit file; they were pulled after it).

If the first line or either spot-check differs, stop: the scan disagrees with `analysis_score` and nothing downstream can be trusted. A first line of `flagged=50` means the TopFull-off AND in `scan_hold` was skipped.

- [ ] **Step 6: Commit**

```powershell
git add experiments/throttle_flags.py experiments/test_throttle_flags.py
git commit -m "feat: scan final results for throttle flags with the scorer's rule"
```

---

### Task 6: Remedy 1, generated STATUS.md lines

**Files:**
- Modify: `experiments/throttle_flags.py` (add `status_sentence`, `apply_status`, wire `status`)
- Test: `experiments/test_throttle_flags.py`
- Modify (generated): `STATUS.md`

**Interfaces:**
- Consumes: `HoldFlag`, `label`, `name_pattern`, `AUDIT_TAG`, `BACKFILL_HEAD`, `STATUS_PATH` (Task 5).
- Produces: `status_sentence(h: HoldFlag) -> str`, `apply_status(text: str, flags: list[HoldFlag]) -> str` (idempotent; returns `text` unchanged when `AUDIT_TAG` is already present).

Each flagged hold's sentence is appended to the end of the first Done bullet that names the hold's folder, under one shared `Throttle flags (2026-10-15 audit):` marker per bullet. Flagged holds that no Done bullet names go into one backfill bullet inserted at the end of Done, before `## Next free slots`.

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_throttle_flags.py`, above the `if __name__` line:

```python
STATUS_TEXT = """# STATUS

## Done

- **Matrix A (2026-10-12)** — folders `hold_a` and `hold_b`, 600 s.
- **Matrix B (2026-10-13)** — folder `hold_c`.

## Next free slots

- hold_a is also listed here and must not be touched.
"""


class TestStatusLines(unittest.TestCase):
    def flags(self):
        return [
            hold("hold_a", on=True, warnings=196, tgap=494, agap=494, tpct=69.1, apct=69.1),
            hold("hold_b", on=True, flagged=False),
            hold("hold_c", on=False, flagged=False, warnings=0, tgap=55, agap=55, tpct=6.3, apct=6.3),
            hold("hold_z", on=True, warnings=12, tgap=5, agap=300, tpct=0.0, apct=60.0),
        ]

    def test_sentence_names_flag_stale_time_and_topfull_state(self):
        text = throttle_flags.status_sentence(self.flags()[0])
        self.assertIn("`hold_a` FLAGGED", text)
        self.assertIn("196 fetch warnings", text)
        self.assertIn("threshold stale 494 s (69.1% of span)", text)
        self.assertIn("admitted stale 494 s (69.1% of span)", text)

    def test_gap_only_sentence_uses_the_10_s_rule(self):
        text = throttle_flags.status_sentence(
            hold("hold_gap", on=True, warnings=0, tgap=55, agap=55, tpct=6.3, apct=6.3))
        self.assertIn("no fetch warnings, 10 s stale-gap rule only", text)

    def test_a_topfull_off_hold_is_not_a_status_line(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        self.assertNotIn("`hold_c`", out)
        self.assertNotIn(throttle_flags.TF_OFF_LABEL, out)

    def test_line_goes_on_the_bullet_that_names_the_hold(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        bullets = [l for l in out.split("\n") if l.startswith("- **Matrix")]
        self.assertIn(throttle_flags.AUDIT_TAG, bullets[0])
        self.assertIn("`hold_a` FLAGGED", bullets[0])
        self.assertNotIn("hold_b` FLAGGED", bullets[0])
        self.assertNotIn(throttle_flags.AUDIT_TAG, bullets[1])

    def test_unmatched_hold_goes_to_one_backfill_bullet_before_next_free_slots(self):
        out = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        lines = out.split("\n")
        backfill = [i for i, l in enumerate(lines) if l.startswith("- **Throttle flag backfill")]
        self.assertEqual(len(backfill), 1)
        self.assertIn("`hold_z` FLAGGED", lines[backfill[0]])
        self.assertLess(backfill[0], lines.index("## Next free slots"))
        self.assertEqual(lines[lines.index("## Next free slots") - 1], "")

    def test_sections_after_done_are_untouched_and_apply_is_idempotent(self):
        once = throttle_flags.apply_status(STATUS_TEXT, self.flags())
        self.assertIn("- hold_a is also listed here and must not be touched.", once)
        self.assertNotIn("hold_a` FLAGGED", once.split("## Next free slots")[1])
        self.assertEqual(throttle_flags.apply_status(once, self.flags()), once)

    def test_no_flagged_holds_leaves_the_text_alone(self):
        clean = [hold("hold_a", flagged=False)]
        self.assertEqual(throttle_flags.apply_status(STATUS_TEXT, clean), STATUS_TEXT)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_throttle_flags.py::TestStatusLines -v`
Expected: 7 FAILED with `AttributeError: module 'throttle_flags' has no attribute 'status_sentence'`.

- [ ] **Step 3: Implement**

In `experiments/throttle_flags.py`, insert above `def main(`:

```python
def _warnings_text(h: HoldFlag) -> str:
    if h.warnings:
        return f"{h.warnings} fetch warnings"
    return f"no fetch warnings, {throttle_stale.STALE_GAP_S:g} s stale-gap rule only"


def status_sentence(h: HoldFlag) -> str:
    return (
        f"`{h.name}` {label(h)}: {_warnings_text(h)}; "
        f"threshold stale {h.threshold_gap_s:.0f} s ({h.threshold_stale_pct:.1f}% of span), "
        f"admitted stale {h.admitted_gap_s:.0f} s ({h.admitted_stale_pct:.1f}% of span)."
    )


def apply_status(text: str, flags: list[HoldFlag]) -> str:
    """Append a throttle line to the Done bullet that names each flagged hold.

    Works on LF text. Idempotent: returns the text unchanged once the audit tag is in it.
    """
    flagged = [h for h in flags if h.flagged]
    if not flagged or AUDIT_TAG in text:
        return text
    lines = text.split("\n")
    done = lines.index("## Done")
    end = next(i for i in range(done + 1, len(lines)) if lines[i].startswith("## "))
    per_bullet: dict[int, list[str]] = defaultdict(list)
    unmatched: list[str] = []
    for h in flagged:
        pattern = name_pattern(h.name)
        hit = next((i for i in range(done + 1, end)
                    if lines[i].startswith("- ") and pattern.search(lines[i])), None)
        if hit is None:
            unmatched.append(status_sentence(h))
        else:
            per_bullet[hit].append(status_sentence(h))
    for index, sentences in per_bullet.items():
        lines[index] = f"{lines[index]} {AUDIT_TAG} {' '.join(sentences)}"
    if unmatched:
        at = end
        while at > done + 1 and lines[at - 1] == "":
            at -= 1
        lines.insert(at, f"{BACKFILL_HEAD} {AUDIT_TAG} {' '.join(unmatched)}")
    return "\n".join(lines)


def write_status(path: Path, flags: list[HoldFlag]) -> bool:
    """Rewrite STATUS.md keeping its line endings. Returns False when nothing changed."""
    raw = Path(path).read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    new = apply_status(raw.replace("\r\n", "\n"), flags)
    if new == raw.replace("\r\n", "\n"):
        return False
    Path(path).write_bytes(new.replace("\n", eol).encode("utf-8"))
    return True
```

In `main`, replace the line `args = parser.parse_args(argv)` through the end of the function with:

```python
    sub.choices["status"].add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    flags = scan(args.root)
    if args.cmd == "audit":
        print(audit_text(flags))
        return 0
    if args.cmd == "status":
        if args.write:
            changed = write_status(STATUS_PATH, flags)
            print("STATUS.md updated" if changed else "STATUS.md unchanged (already applied or no flags)")
        else:
            raw = STATUS_PATH.read_bytes().decode("utf-8").replace("\r\n", "\n")
            new = apply_status(raw, flags)
            before = set(raw.split("\n"))
            for line in new.split("\n"):
                if line not in before:
                    print(line + "\n")
        return 0
    return 0
```

(`sub.choices["status"].add_argument` must run before `parse_args`; keep that order exactly.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_throttle_flags.py -v`
Expected: `14 passed`.

- [ ] **Step 5: Dry-run on the real STATUS.md and review**

Run: `python experiments/throttle_flags.py status`
Expected: the changed or new bullets printed, nothing written. TopFull-off folder names (`rg_only`, including `final_s3_rg_only_normal_run1` and `s2_burst20_rgtf0`) must not appear. Confirm by eye that: (a) every one of the 27 TopFull-on flagged names appears exactly once, (b) each sentence sits on a bullet that actually concerns that hold, (c) the backfill bullet comes last. Holds no Done bullet names, including `final_s2_both_burst_run3` and `final_s2_tf_only_run3` if STATUS.md does not already name them, go in the backfill bullet.

Check (a) mechanically:

```powershell
python experiments/throttle_flags.py status | Select-String -Pattern '`[^`]+` FLAGGED' -AllMatches | ForEach-Object { $_.Matches.Count } | Measure-Object -Sum
```

Expected: `Sum : 27`.

- [ ] **Step 6: Write it and check the diff is only appended text**

Run: `python experiments/throttle_flags.py status --write`
Expected: `STATUS.md updated`.

Run: `git diff --stat STATUS.md`
Expected: a small number of changed lines (the touched bullets plus 1 inserted line). No deletions other than the replaced bullet lines, and no whole-file churn.

Run it again: `python experiments/throttle_flags.py status --write`
Expected: `STATUS.md unchanged (already applied or no flags)`.

- [ ] **Step 7: Commit**

```powershell
git add experiments/throttle_flags.py experiments/test_throttle_flags.py STATUS.md
git commit -m "docs: record each flagged hold's throttle staleness in STATUS.md"
```

---

### Task 7: Remedy 3, name flagged holds in the write-ups

**Files:**
- Modify: `experiments/throttle_flags.py` (add `scan_guides`, `guides_markdown`, `guide_note`, wire `guides`)
- Test: `experiments/test_throttle_flags.py`
- Modify (by hand, from generated notes): the guides listed in Step 6

**Interfaces:**
- Consumes: `HoldFlag`, `label`, `name_pattern`, `GUIDES_DIR` (Task 5), `_warnings_text` (Task 6).
- Produces:
  - `GuideRow` frozen dataclass: `guide: str`, `mentioned: tuple[HoldFlag, ...]`, `named: tuple[HoldFlag, ...]`, `has_section: bool`; property `missing`.
  - `scan_guides(flags, guides_dir) -> list[GuideRow]`
  - `guides_markdown(rows) -> str`
  - `guide_note(h: HoldFlag) -> str` (the paste-ready sentence per ANALYSIS-TEMPLATE.md item 17)

"Named" means: a line of the guide contains the hold's folder name as a whole token **and** the word `FLAGGED`. "Mentioned" means the folder name appears at all. A guide needs a note when a flagged hold is mentioned and not named. Scope is the flat `Guides and Info/*.md` write-ups; run logs and plans under `docs/` are not write-ups and are not edited (their facts are carried by the STATUS.md lines from Task 6).

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_throttle_flags.py`, above the `if __name__` line:

```python
class TestGuideScan(unittest.TestCase):
    def scan(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8")
            flags = [hold("hold_a", on=True), hold("hold_b", on=False), hold("hold_c", flagged=False)]
            return throttle_flags.scan_guides(flags, Path(tmp))

    def test_a_guide_that_names_the_flag_has_nothing_missing(self):
        rows = self.scan({"g1.md": "## Throttle data quality\n\n| hold_a | **FLAGGED** | 5 |\n"})
        self.assertEqual(len(rows), 1)
        self.assertEqual([h.name for h in rows[0].named], ["hold_a"])
        self.assertEqual(rows[0].missing, ())
        self.assertTrue(rows[0].has_section)

    def test_a_guide_that_only_mentions_the_hold_is_missing_it(self):
        rows = self.scan({"g2.md": "Columns: hold_a, hold_b.\n"})
        self.assertEqual([h.name for h in rows[0].missing], ["hold_a", "hold_b"])
        self.assertFalse(rows[0].has_section)

    def test_clean_holds_and_unrelated_guides_are_ignored(self):
        rows = self.scan({"g3.md": "hold_c only.\n", "g4.md": "nothing here\n"})
        self.assertEqual(rows, [])

    def test_note_has_the_item_17_facts_and_the_off_variant_wording(self):
        on = throttle_flags.guide_note(hold("hold_a", on=True, warnings=196, tgap=494, agap=494))
        self.assertIn("`hold_a` is FLAGGED", on)
        self.assertIn("carried, not measured", on)
        self.assertIn("Goodput, P95, rejection, and retry numbers", on)
        off = throttle_flags.guide_note(hold("hold_b", on=False))
        self.assertIn("no admission cap to lose", off)

    def test_markdown_lists_every_guide_with_counts(self):
        rows = self.scan({"g2.md": "Columns: hold_a, hold_b.\n"})
        text = throttle_flags.guides_markdown(rows)
        self.assertIn("| g2.md | 2 | 1 | 0 | `hold_a`, `hold_b` |", text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_throttle_flags.py::TestGuideScan -v`
Expected: 5 FAILED with `AttributeError: ... no attribute 'scan_guides'`.

- [ ] **Step 3: Implement**

In `experiments/throttle_flags.py`, insert above `def main(`:

```python
@dataclass(frozen=True)
class GuideRow:
    guide: str
    mentioned: tuple
    named: tuple
    has_section: bool

    @property
    def missing(self) -> tuple:
        named = {h.name for h in self.named}
        return tuple(h for h in self.mentioned if h.name not in named)


def scan_guides(flags: list[HoldFlag], guides_dir: Path) -> list[GuideRow]:
    skip = {AUDIT_PATH.name, RERUN_PATH.name}
    flagged = [h for h in flags if h.flagged]
    rows = []
    for path in sorted(Path(guides_dir).glob("*.md")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        mentioned, named = [], []
        for h in flagged:
            pattern = name_pattern(h.name)
            hits = [line for line in lines if pattern.search(line)]
            if not hits:
                continue
            mentioned.append(h)
            if any("FLAGGED" in line for line in hits):
                named.append(h)
        if mentioned:
            rows.append(GuideRow(path.name, tuple(mentioned), tuple(named),
                                 "Throttle data quality" in text))
    return rows


def guides_markdown(rows: list[GuideRow]) -> str:
    out = [
        "| Guide | Flagged holds mentioned | TopFull on | Named FLAGGED | Missing |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        missing = ", ".join(f"`{h.name}`" for h in row.missing) or "none"
        on = sum(1 for h in row.mentioned if h.topfull_on)
        out.append(f"| {row.guide} | {len(row.mentioned)} | {on} | {len(row.named)} | {missing} |")
    return "\n".join(out)


def guide_note(h: HoldFlag) -> str:
    """One paste-ready sentence per ANALYSIS-TEMPLATE.md item 17."""
    facts = (
        f"{_warnings_text(h)}; longest no-fresh threshold read {h.threshold_gap_s:.0f} s, "
        f"longest no-fresh admitted read {h.admitted_gap_s:.0f} s"
    )
    if h.topfull_on:
        handling = (
            "Its cap and admitted-rate numbers are carried, not measured; filter them on "
            "`threshold_fresh==1` / `admitted_fresh==1` and do not quote them as measured."
        )
    else:
        handling = (
            "That hold has TopFull off, so it is N/A: TopFull off and is not a flag. "
            "It has no admission cap to lose."
        )
    return (
        f"`{h.name}` is {label(h)} ({facts}). {handling} "
        f"Goodput, P95, rejection, and retry numbers do not use `topfull_throttle.csv` and stay valid."
    )
```

In `main`, add, before the final `return 0`:

```python
    if args.cmd == "guides":
        rows = scan_guides(flags, GUIDES_DIR)
        print(guides_markdown(rows))
        if args.notes:
            for row in rows:
                if not row.missing:
                    continue
                print(f"\n### {row.guide}\n")
                for h in row.missing:
                    print(f"- {guide_note(h)}")
        return 0
```

and, next to the `status` extra argument (before `parse_args`):

```python
    sub.choices["guides"].add_argument("--notes", action="store_true")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_throttle_flags.py -v`
Expected: `19 passed`.

- [ ] **Step 5: Produce the worklist**

Run: `python experiments/throttle_flags.py guides`
Expected: a table that, before any guide edit, contains these guides (flagged-hold counts from the audit scan; "Missing" shows the holds still unnamed):

Counts below are TopFull-on flagged holds only. A guide whose only flagged mention was a TopFull-off hold is not in this table and must not be edited.

| Guide | Flagged holds mentioned | State expected before edits |
|---|---|---|
| `2026-10-14-s2-mode-matrix-abc.md` | 3: `final_s2_both_burst_run1`, `final_s2_both_burst_run2`, `final_s2_tf_only_run2` | Has a `Throttle data quality` table. `final_s2_rg_only_burst_run2` is TopFull off and must not be added as a flag. Check the prose handling sentence (item 17) for the three TopFull-on holds |
| `2026-10-15-s2-topfull-proxy-reruns.md` | 2: `final_s2_both_burst_run3`, `final_s2_tf_only_run3` | Written after the audit. Both are TopFull-on and flagged. Add the item 17 sentence for each if the guide does not already say FLAGGED |
| `2026-10-13-s4a-constrained-relock-abc.md` | 10 | Says "Every scored hold is FLAGGED"; the TopFull-off rows in that table are not flags. Check that each of the 10 TopFull-on holds is named FLAGGED |
| `2026-10-13-s4a-unconstrained-relock-abc.md` | 2: `final_4a_unconstrained_both_burst_run2_r2`, `final_4a_unconstrained_both_normal_run1_r2` | Do not add a flag line for `final_4a_unconstrained_rg_only_normal_run2`. The two TopFull-on `_r2` holds are the ones to name |
| `2026-10-13-s4a-constrained-mode-matrix-abc.md` | 7 | Superseded earlier lock; one addendum for the TopFull-on holds only |
| `2026-10-12-s2-burst-matrix-abc.md` and `-rescored.md` | 2 each: `study6_s2_normal_rgtf1_rep1`, `study6_s2_normal_rgtf1_rep2` | Do not add lines for `study6_s2_normal_rgtf0_rep1/2`. Older S2 study folders; one addendum each for the two TopFull-on holds |
| `2026-10-12-s2-normal-rgtf1-x3-abc.md` and `-rescored.md` | 3 each: `study6_s2_normal_rgtf1_rep1/2`, `study7_s2_normal_rgtf1_rep1` | Older S2 study folders; TopFull on, so an addendum matters here |

Guides that must **not** appear, and must not be edited: `2026-10-15-s1-mode-matrix-abc.md`, `2026-10-15-s3-mode-matrix-abc.md`, `2026-10-13-s4b-relock-abc.md`, `2026-10-13-s3-mode-matrix-abc.md` (its only flag was `final_s3_rg_only_normal_run1`), and `2026-10-12-s1-s2-mode-matrix-abc.md`, `-rescored.md`, `2026-10-12-s2-mode-matrix-abc.md`, `-rescored.md` (their only flag was `s2_burst20_rgtf0`). If any of them appears, stop: a TopFull-off hold is still being counted as flagged.

- [ ] **Step 6: Generate the notes and edit each guide with a `Missing` entry**

Run: `python experiments/throttle_flags.py guides --notes`

For each guide whose `Missing` column is not `none`:

1. Open the guide, go to its `Throttle data quality` section (the heading text matches `Throttle data quality`). For a guide with no such section, add `## Throttle flag addendum (2026-10-15 audit)` at the very end.
2. Paste the guide's note bullets from the generated output, one per missing hold, directly under the existing prose for that section (or the new heading). Do not edit the guide's existing numbers or tables.
3. For a TopFull-on hold, also check every place the guide **quotes a cap or admitted rate** for that hold (search the guide for the hold name next to `cap`, `admitted`, `live cap`, `threshold`). If one is quoted as measured, add `(carried)` after it, or filter it per item 17, or delete the number and say why in the addendum. Edit only the sentences that quote the flagged hold.
4. Where the guide already says "the other N scored holds are throttle clean" or "No hold is FLAGGED" and the generated output shows a mentioned-but-unnamed flagged hold, correct the sentence to the true count.

After each guide:

Run: `python experiments/throttle_flags.py guides`
Expected: that guide's `Missing` is now `none`.

Run: `git diff --stat "Guides and Info"`
Expected: a handful of changed lines per guide.

When every row shows `none`, the final table is the proof for remedy 3.

- [ ] **Step 7: Commit (one commit for all guide edits plus the script change)**

```powershell
git add experiments/throttle_flags.py experiments/test_throttle_flags.py "Guides and Info"
git commit -m "docs: name every flagged hold in the write-ups that quote its caps"
```

---

### Task 8: Remedy 4, TopFull-on re-run decision list

**Files:**
- Modify: `experiments/throttle_flags.py` (add `numbers_affected`, `cell_key`, `rerun_markdown`, wire `rerun`)
- Test: `experiments/test_throttle_flags.py`
- Create (generated): `Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md`

**Interfaces:**
- Consumes: `HoldFlag`, `SCENARIO_ORDER`, `CELL_SUFFIX`, `RERUN_PATH` (Task 5), `TF_OFF_LABEL`.
- Produces: `numbers_affected(h) -> str`, `cell_key(h) -> str | None`, `rerun_markdown(flags) -> str`.

The document is for the user. It never re-runs anything and never picks a decision. It has one table per scenario for the 27 TopFull-on flagged holds, sorted by path, with these columns: Hold, In locked set (`final_` prefix), Fetch warnings, Threshold stale s (% of span), Admitted stale s (% of span), Numbers affected, Cell (clean / flagged `final_` holds in the same scenario, mode, variant, and constraint), Decision (blank).

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_throttle_flags.py`, above the `if __name__` line:

```python
class TestRerunList(unittest.TestCase):
    def flags(self):
        return [
            hold("final_s2_both_burst_run1", on=True, tgap=494, agap=494, tpct=69.1, apct=69.1),
            hold("final_s2_both_burst_run2", on=True, flagged=False),
            hold("study6_s2_normal_rgtf1_rep1", on=True, tgap=5, agap=300, tpct=0.0, apct=60.0,
                 mode="normal"),
            hold("final_s2_rg_only_burst_run2", on=False),
        ]

    def test_numbers_affected_follows_which_reads_went_stale(self):
        both = throttle_flags.numbers_affected(self.flags()[0])
        self.assertIn("TopFull cap lines", both)
        self.assertIn("admitted req/s", both)
        admitted_only = throttle_flags.numbers_affected(self.flags()[2])
        self.assertNotIn("TopFull cap lines", admitted_only)
        self.assertIn("admitted req/s", admitted_only)
        none = throttle_flags.numbers_affected(hold("x", tgap=5, agap=5))
        self.assertIn("fetch warnings only", none)

    def test_cell_key_strips_the_run_suffix_and_skips_study_folders(self):
        self.assertEqual(throttle_flags.cell_key(hold("final_4a_constrained_both_burst_run3_r2")),
                         "final_4a_constrained_both_burst")
        self.assertIsNone(throttle_flags.cell_key(hold("study6_s2_normal_rgtf1_rep1")))

    def test_only_topfull_on_flags_get_a_row(self):
        text = throttle_flags.rerun_markdown(self.flags())
        self.assertIn("`final_s2_both_burst_run1`", text)
        self.assertIn("`study6_s2_normal_rgtf1_rep1`", text)
        self.assertNotIn("final_s2_rg_only_burst_run2", text)
        self.assertNotIn("final_s2_both_burst_run2", text)
        self.assertNotIn("Pending", text)
        self.assertNotIn(throttle_flags.TF_OFF_LABEL, text)

    def test_locked_set_and_cell_counts_and_blank_decision(self):
        text = throttle_flags.rerun_markdown(self.flags())
        row = next(l for l in text.splitlines() if l.startswith("| `final_s2_both_burst_run1`"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[1], "yes")
        self.assertEqual(cells[6], "1 clean / 1 flagged")
        self.assertEqual(cells[7], "")
        study = next(l for l in text.splitlines() if l.startswith("| `study6_s2_normal_rgtf1_rep1`"))
        study_cells = [c.strip() for c in study.strip("|").split("|")]
        self.assertEqual(study_cells[1], "no")
        self.assertEqual(study_cells[6], "n/a")

    def test_scenarios_are_grouped_in_order(self):
        text = throttle_flags.rerun_markdown(self.flags())
        self.assertIn("### S2", text)
        self.assertNotIn("## Pending", text)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_throttle_flags.py::TestRerunList -v`
Expected: 5 FAILED with `AttributeError: ... no attribute 'numbers_affected'`.

- [ ] **Step 3: Implement**

In `experiments/throttle_flags.py`, insert above `def main(`:

```python
def numbers_affected(h: HoldFlag) -> str:
    stale = analysis_score.THROTTLE_STALE_S
    parts = []
    if h.threshold_gap_s > stale:
        parts.append("TopFull cap lines and the live-cap table")
    if h.admitted_gap_s > stale:
        parts.append("admitted req/s")
    if not parts:
        return f"fetch warnings only; no stretch over {stale:g} s, so no number is lost"
    return "; ".join(parts)


def cell_key(h: HoldFlag) -> str | None:
    """Same scenario, mode, variant, and constraint, without the run number. final_ only."""
    if not h.name.startswith("final_"):
        return None
    return CELL_SUFFIX.sub("", h.name)


def _cell_text(h: HoldFlag, flags: list[HoldFlag]) -> str:
    key = cell_key(h)
    if key is None:
        return "n/a"
    siblings = [o for o in flags if cell_key(o) == key]
    flagged = sum(1 for o in siblings if o.flagged)
    return f"{len(siblings) - flagged} clean / {flagged} flagged"


def rerun_markdown(flags: list[HoldFlag]) -> str:
    flagged_on = [h for h in flags if h.flagged and h.topfull_on]
    out = [
        "# TopFull-on throttle flags: re-run decision list",
        "",
        "Generated by `python experiments/throttle_flags.py rerun`. Source: "
        "[2026-10-15-throttle-flag-audit.md](2026-10-15-throttle-flag-audit.md). "
        "Nothing was re-run. A re-run is the user's decision and bumps `run_number` in the "
        "scenario YAML per [STATUS.md](../STATUS.md) \"Next free slots\"; it never reuses a folder name.",
        "",
        f"{len(flagged_on)} TopFull-on holds are flagged. Goodput, P95, rejection, and retry numbers "
        "do not use `topfull_throttle.csv` and stay valid for every hold below. Only the cap and "
        "admitted-rate numbers named in the \"Numbers affected\" column are carried, not measured.",
        "",
        "How to read the columns: **In locked set** is `yes` for a `final_` folder (the current "
        "locked mode matrices) and `no` for an older study or earlier-lock folder, which AGENTS.md "
        "already calls not comparable. **Cell** counts the `final_` holds with the same scenario, "
        "mode, variant, and constraint: how many are clean and how many are flagged. **Decision** "
        "is left blank for the user (`re-run` / `keep`).",
        "",
    ]
    for scenario in SCENARIO_ORDER:
        group = [h for h in flagged_on if h.scenario == scenario]
        if not group:
            continue
        out += [
            f"### {scenario}",
            "",
            "| Hold | In locked set | Fetch warnings | Threshold stale s (% of span) | "
            "Admitted stale s (% of span) | Numbers affected | Cell | Decision |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        ]
        for h in sorted(group, key=lambda x: x.path):
            out.append(
                f"| `{h.name}` | {'yes' if h.name.startswith('final_') else 'no'} | {h.warnings} | "
                f"{h.threshold_gap_s:.0f} ({h.threshold_stale_pct:.1f}%) | "
                f"{h.admitted_gap_s:.0f} ({h.admitted_stale_pct:.1f}%) | "
                f"{numbers_affected(h)} | {_cell_text(h, flags)} |  |"
            )
        out.append("")
    return "\n".join(out)
```

In `main`, add before the final `return 0`:

```python
    if args.cmd == "rerun":
        text = rerun_markdown(flags)
        if args.out:
            args.out.write_bytes(text.encode("utf-8"))
            print(f"wrote {args.out}")
        else:
            print(text)
        return 0
```

and, next to the other extra arguments (before `parse_args`):

```python
    sub.choices["rerun"].add_argument("--out", type=Path, default=None)
```

(`write_bytes` keeps LF on Windows.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_throttle_flags.py -v`
Expected: `24 passed`.

- [ ] **Step 5: Generate the document and check it against the audit**

Run: `python experiments/throttle_flags.py rerun --out "Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md"`
Expected: `wrote Guides and Info\2026-10-15-throttle-flag-rerun-decisions.md`.

Checks (all must hold):

```powershell
(Select-String -Path "Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md" -Pattern '^\| `').Count
```

Expected: `27` (rows in the scenario tables).

```powershell
(Select-String -Path "Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md" -Pattern '^### S').Line
```

Expected: `### S2` and `### S4A` (S1, S3, S4B have no TopFull-on flags).

Expected row counts: S2 has 8 TopFull-on flags (`final_s2_both_burst_run1`, `final_s2_both_burst_run2`, `final_s2_both_burst_run3`, `final_s2_tf_only_run2`, `final_s2_tf_only_run3`, and the three older `study6_s2_normal_rgtf1_rep1`, `study6_s2_normal_rgtf1_rep2`, `study7_s2_normal_rgtf1_rep1`); S4A has 19. Of the 27, 24 are `final_` folders (locked set `yes`) and 3 are study folders (`no`). No `rg_only` name appears. There is no "Pending" section.

- [ ] **Step 6: Commit**

```powershell
git add experiments/throttle_flags.py experiments/test_throttle_flags.py "Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md"
git commit -m "docs: TopFull-on throttle flags, grouped by scenario, for the re-run decision"
```

---

### Task 9: Scorer and AGENTS.md stop flagging TopFull-off holds, and the gap is 10 s

**Files:**
- Modify: `experiments/analysis_score.py` (`THROTTLE_STALE_S`, `throttle_quality`, `topfull_enabled`, `score_run`, the `Throttle data quality` prose)
- Modify: `experiments/test_analysis_score.py` (append to `TestThrottleQuality`)
- Modify: `experiments/throttle_flags.py` (`scan_hold` passes `topfull_on`)
- Modify: `AGENTS.md` (§6 flag sentence)

**Interfaces:**
- Consumes: `throttle_stale.STALE_GAP_S` (Task 1, value `10.0`). `scan_hold` (Task 5).
- Produces: `analysis_score.THROTTLE_STALE_S = 10`, `throttle_quality(rows, log_path, topfull_on: bool = True) -> dict` with keys `topfull_on` and `flagged`, `topfull_enabled(run_dir: Path) -> bool`.

`flagged` is true only when TopFull is on and (the log has a `fetch failed` WARNING or some API's longest no-fresh gap is greater than 10 s). A gap of exactly 10 s is not a flag. Warnings and gaps are still returned when TopFull is off. `score_run` passes `topfull_enabled(run_dir)`. A missing, unreadable, or non-JSON `run_manifest.json` means TopFull on. `topfull_rl.enabled: false` means off.

- [ ] **Step 1: Write the failing tests**

Append to `class TestThrottleQuality` in `experiments/test_analysis_score.py`. If `test_topfull_off_hold_is_not_flagged_but_still_reports_the_problem` is already in the file, do not duplicate it; add only the tests that are absent.

```python
    def test_topfull_off_hold_is_not_flagged_but_still_reports_the_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "topfull_throttle_collector.log"
            log.write_text(
                "2026-10-13T00:00:05Z  WARNING  stats fetch failed: timed out\n",
                encoding="utf-8",
            )
            q = score.throttle_quality(self._rows(fresh_until=20), log, topfull_on=False)
        self.assertFalse(q["flagged"])
        self.assertFalse(q["topfull_on"])
        self.assertEqual(q["warnings"], 1)
        self.assertGreater(q["threshold_gap_s"], score.THROTTLE_STALE_S)

    def test_topfull_on_is_the_default(self):
        q = score.throttle_quality(self._rows(fresh_until=20), Path("missing.log"))
        self.assertTrue(q["topfull_on"])

    def test_topfull_enabled_reads_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertTrue(score.topfull_enabled(folder))  # no manifest
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": false}}', encoding="utf-8")
            self.assertFalse(score.topfull_enabled(folder))
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": true}}', encoding="utf-8")
            self.assertTrue(score.topfull_enabled(folder))
            (folder / "run_manifest.json").write_text("not json", encoding="utf-8")
            self.assertTrue(score.topfull_enabled(folder))

    def test_ten_seconds_is_not_a_flag_and_eleven_is(self):
        def rows(gap):
            return [
                {"timestamp": "2026-10-13T00:00:00Z", "api": "getproduct",
                 "threshold_fresh": 1, "admitted_fresh": 1},
                {"timestamp": f"2026-10-13T00:00:{gap:02d}Z", "api": "getproduct",
                 "threshold_fresh": 1, "admitted_fresh": 1},
            ]
        ten = score.throttle_quality(rows(10), Path("missing.log"))
        self.assertFalse(ten["flagged"])
        self.assertEqual(ten["threshold_gap_s"], 10)
        eleven = score.throttle_quality(rows(11), Path("missing.log"))
        self.assertTrue(eleven["flagged"])
        self.assertEqual(eleven["threshold_gap_s"], 11)

    def test_stale_gap_matches_the_marker(self):
        import throttle_stale
        self.assertEqual(score.THROTTLE_STALE_S, 10)
        self.assertEqual(throttle_stale.STALE_GAP_S, float(score.THROTTLE_STALE_S))

    def test_rendered_table_says_na_for_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "final_s2_rg_only_burst_run9"
            folder.mkdir()
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": false}}', encoding="utf-8")
            (folder / "topfull_throttle_collector.log").write_text(
                "2026-10-13T00:00:05Z  WARNING  stats fetch failed: timed out\n",
                encoding="utf-8")
            _write(
                folder / "topfull_throttle.csv",
                ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
                [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
                 ["2026-10-13T00:01:00Z", "getproduct", 10000, 0, 0, 0]],
            )
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | N/A: TopFull off |", text)
        self.assertNotIn("| 9 | **FLAGGED** |", text)
```

`_write` is already defined in this test file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest experiments/test_analysis_score.py::TestThrottleQuality -v`
Expected: the new tests FAIL (`TypeError: throttle_quality() got an unexpected keyword argument 'topfull_on'`, or `AttributeError: module 'analysis_score' has no attribute 'topfull_enabled'`, or `THROTTLE_STALE_S` is 30). The three tests that already existed (`test_healthy_hold_is_not_flagged`, `test_reads_that_stop_flag_the_hold`, `test_fetch_warning_in_log_flags_the_hold`) still PASS. `test_reads_that_stop_flag_the_hold` uses a ~99 s gap, so it stays a flag at 10 s.

- [ ] **Step 3: Implement the scorer**

In `experiments/analysis_score.py`, change `THROTTLE_STALE_S = 30` to:

```python
THROTTLE_STALE_S = 10
```

Replace `def throttle_quality(rows: list[dict], log_path: Path) -> dict:` and its `flagged = ...` / `return` with:

```python
def topfull_enabled(run_dir: Path) -> bool:
    """True unless run_manifest.json says topfull_rl.enabled is false.

    A missing file, a read error, or a body that is not JSON means on.
    """
    path = Path(run_dir) / "run_manifest.json"
    if not path.is_file():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(data, dict):
        return True
    block = data.get("topfull_rl")
    if not isinstance(block, dict):
        return True
    return bool(block.get("enabled", True))


def throttle_quality(rows: list[dict], log_path: Path, topfull_on: bool = True) -> dict:
    """How trustworthy topfull_throttle.csv is for this hold.

    Live reads of the TopFull proxy (/thresholds, /stats) normally land every 5 s.
    A TopFull-on hold is flagged when topfull_throttle_collector.log has any fetch
    WARNING, or when any API goes longer than THROTTLE_STALE_S without a fresh
    threshold or admitted read. A TopFull-off hold is never flagged. Warnings and
    gaps are still reported.
    """
    warnings = 0
    first_warning = None
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "WARNING" in line and "fetch failed" in line:
                warnings += 1
                if first_warning is None:
                    first_warning = line.split()[0]
    by_api: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("timestamp"):
            by_api[row.get("api", "")].append(row)
    gaps: dict[str, float | None] = {"threshold_fresh": None, "admitted_fresh": None}
    for series in by_api.values():
        series.sort(key=lambda r: r["timestamp"])
        stamps = [parse_ts(r["timestamp"]) for r in series]
        for key in gaps:
            gap = _longest_gap(stamps, [int(float(r.get(key) or 0)) == 1 for r in series])
            if gap is not None and (gaps[key] is None or gap > gaps[key]):
                gaps[key] = gap
    worst = max([g for g in gaps.values() if g is not None], default=None)
    would_flag = warnings > 0 or (worst is not None and worst > THROTTLE_STALE_S)
    return {
        "has_csv": bool(rows),
        "warnings": warnings,
        "first_warning": first_warning,
        "threshold_gap_s": gaps["threshold_fresh"],
        "admitted_gap_s": gaps["admitted_fresh"],
        "topfull_on": bool(topfull_on),
        "flagged": bool(would_flag and topfull_on),
    }
```

In `score_run`, change the `throttle_quality` call to:

```python
        "throttle_quality": throttle_quality(
            throttle_rows, run_dir / "topfull_throttle_collector.log",
            topfull_on=topfull_enabled(run_dir),
        ),
```

In the `## Throttle data quality` prose, replace the whole `lines.append` f-string that starts `Live reads of the TopFull proxy normally land every 5 s.` (it currently ends at `do not use this file.`) with:

```python
        f"Live reads of the TopFull proxy normally land every 5 s. A hold is **FLAGGED** only "
        f"when TopFull is on and `topfull_throttle_collector.log` has any `fetch failed` WARNING, "
        f"or an API goes longer than {THROTTLE_STALE_S} s without a fresh threshold or admitted "
        f"read. A TopFull-off hold (`rg_only`, `both_off`) is `N/A: TopFull off`, not a flag. "
        f"Cap and admitted-rate numbers on a flagged hold are carried values; filter on "
        f"`*_fresh==1`. The rows stay in the file. Goodput, P95 and rejection do not use this file."
```

Replace the status line inside the table loop:

```python
        status = "**FLAGGED**" if q["flagged"] else "ok"
```

with:

```python
        if not q.get("topfull_on", True):
            status = "N/A: TopFull off"
        elif q["flagged"]:
            status = "**FLAGGED**"
        else:
            status = "ok"
```

- [ ] **Step 4: Pass `topfull_on` from the scanner**

In `experiments/throttle_flags.py`, in `scan_hold`, replace the `throttle_quality` call with:

```python
    quality = analysis_score.throttle_quality(
        rows, run_dir / "topfull_throttle_collector.log", topfull_on=topfull_on)
```

Leave `flagged=bool(quality["flagged"] and quality["has_csv"] and topfull_on)`. Delete the comment that says not to pass `topfull_on`.

- [ ] **Step 5: AGENTS.md §6**

Task 4 has already replaced item (2). Replace this fragment (the flag definition, which Task 4 does not touch):

```
A hold is **FLAGGED** if that log has any `fetch failed` WARNING or any API goes over 30 s with no fresh threshold or admitted read (normal is 5 s). Then: (1) put one line in the [STATUS.md](STATUS.md) Done bullet for that hold saying it is flagged and how long it was stale;
```

with:

```
The flag applies only when TopFull is on (`topfull_rl.enabled` in `run_manifest.json`, which is the `both` and `tf_only` variant folders). A TopFull-off hold (`rg_only`, `both_off`) is `N/A: TopFull off`, not flagged, even when the collector log has `fetch failed` or a long gap. A TopFull-on hold is **FLAGGED** if that log has any `fetch failed` WARNING or any API goes over 10 s with no fresh threshold or admitted read (normal is 5 s; a gap of exactly 10 s is not a flag). Then: (1) put one line in the [STATUS.md](STATUS.md) Done bullet for that hold saying it is flagged and how long it was stale;
```

Also replace `(4) if the flag is on a TopFull-on hold, tell the user` with `(4) tell the user`, because a flag is already TopFull-on.

- [ ] **Step 6: Run the tests**

Run: `python -m pytest experiments/test_analysis_score.py::TestThrottleQuality experiments/test_throttle_flags.py experiments/test_throttle_stale.py -v`
Expected: all pass. `TestThrottleQuality` includes the new tests. `test_throttle_flags.py` is `24 passed`.

Run: `python experiments/throttle_flags.py audit`
Expected first line, unchanged from Task 5, because 10 s adds no hold:

```
runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0
```

- [ ] **Step 7: Commit**

```powershell
git add experiments/analysis_score.py experiments/test_analysis_score.py experiments/throttle_flags.py AGENTS.md
git commit -m "fix: flag throttle gaps over 10s only when TopFull is on"
```

---

### Task 10: Close-out checks and the STATUS bullet

**Files:**
- Modify: `STATUS.md` (one new Done bullet, appended at the end of Done by hand)
- Test: the full affected test set

**Interfaces:**
- Consumes: everything above.
- Produces: the remediation recorded as done, with the open question named.

- [ ] **Step 1: Full test run**

Run: `python -m pytest experiments/test_throttle_stale.py experiments/test_throttle_flags.py experiments/test_graphs_tool.py experiments/test_multi_graphs_tool.py experiments/test_analysis_score.py experiments/test_hold_clock.py -q`
Expected: all pass, no failures. `TestThrottleQuality` includes the TopFull-off cases and the 10 s boundary.

- [ ] **Step 2: Counts and untouched data**

Run: `python experiments/throttle_flags.py audit`
Expected first line: `runs=146 flagged=27 topfull_on_flagged=27 topfull_off_flagged=0`.

Run: `git status --short "experiments/results"`
Expected: no output (no run folder was touched).

- [ ] **Step 3: Remedy checklist, one check per remedy**

- Remedy 1: `python experiments/throttle_flags.py status --write` prints `STATUS.md unchanged (already applied or no flags)`, and `rg -c "FLAGGED" STATUS.md` shows the new lines.
- Remedy 2: Task 3 Step 5's rendered page showed the band and dashed lines; Task 2 and 3 tests pass.
- Remedy 3: `python experiments/throttle_flags.py guides` shows `none` in every `Missing` cell.
- Remedy 4: `Guides and Info/2026-10-15-throttle-flag-rerun-decisions.md` exists with 27 rows, no `rg_only` name, and no Pending section.

- [ ] **Step 4: Append the STATUS.md bullet**

Add as the last Done bullet (above `## Next free slots`), by hand:

```markdown
- **Throttle flag remediation (2026-10-15)** — no hold run, nothing re-run, no row dropped. Live tree: 146 holds, 27 flagged, all TopFull-on. TopFull-off holds are `N/A: TopFull off`. The stale gap is 10 s. Remedy 1: each flagged hold has a throttle line in its Done bullet, plus a backfill bullet. Remedy 2: `graphs_tool` and `multi_graphs_tool` draw stale caps dashed in a grey band, with a `(stale)` legend entry ([GRAPHS-TOOL.md](Guides%20and%20Info/GRAPHS-TOOL.md)). Remedy 3: every write-up that quotes a flagged hold names it per ANALYSIS-TEMPLATE.md item 17. Remedy 4: [2026-10-15-throttle-flag-rerun-decisions.md](Guides%20and%20Info/2026-10-15-throttle-flag-rerun-decisions.md) lists the 27 TopFull-on flags for the user's re-run decision. Tools: `experiments/throttle_stale.py`, `experiments/throttle_flags.py`. Locked YAML slots were not bumped.
```

Do not touch AGENTS.md "Latest" (no hold ran).

- [ ] **Step 5: Final diff review, then commit**

Run: `git diff --stat main`
Expected: the files in the File Structure table and nothing else.

```powershell
git add STATUS.md
git commit -m "docs: record the throttle flag remediation in STATUS.md"
```

---

## Self-Review (run against the request)

1. **Spec coverage.**
   - Remedy 1, scripted and reviewable, TopFull-off holds excluded: Task 6.
   - Remedy 2, mark not drop, graphs at `STALE_GAP_S` 10 s: Tasks 1–4. A gap-only stretch (no `fetch failed` warning) is still marked, including on a TopFull-off run if that graph is drawn. The admitted-rate column is not drawn, so only `threshold_fresh` drives marking.
   - Remedy 3, TopFull-on holds only; the S3 guide and the `s2_burst20_rgtf0` guides are listed as not edited: Task 7.
   - Remedy 4, 27 TopFull-on rows, no pending section: Task 8.
   - TopFull-off is `N/A` in the scorer, the scanner, and AGENTS.md §6, and `THROTTLE_STALE_S` is 10: Global Constraints, Task 5 (`scan_hold` AND), Task 9.
2. **Placeholder scan.** No "TBD", "similar to Task N", or code-less steps. Task 7 Step 6 is a manual editing procedure on prose, with the exact sentence generated by the tested `guide_note`; it names the exact command and the exact pass condition (`Missing` is `none`).
3. **Type and name consistency.** Names defined once and reused identically: `STALE_SUFFIX`, `STALE_BAND_NAME`, `STALE_BAND_FILL`, `STALE_BAND_TEXT`, `cap_color`, `stale_cap_traces`, `stale_band_layout` (Task 2) are used by Task 3 and the tests; `stale_stretches`, `stale_cap_series`, `stale_bands` (Task 1) are used by Task 2 and by `throttle_flags._stale_pct`; `HoldFlag` fields (Task 5) match the `hold()` test helper in every later test; `label`, `TF_OFF_LABEL`, `_warnings_text`, `status_sentence`, `guide_note`, `numbers_affected`, `cell_key` are each defined before they are used.
4. **Known risk, stated.** Task 2's band-position assertion depends on the Locust clock fit of the synthetic run (about 1 s). The `delta=3` margin covers it; Step 6 says what to do if it does not.
