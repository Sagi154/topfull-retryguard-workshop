# Interactive Run Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command turns a `final results/` run folder into a single self-contained interactive HTML page (Plotly) on the hold clock, with RetryGuard markers and a per-edge attempts strip.

**Architecture:** A new `experiments/explore_run.py` imports `run_timeline` (per-second view, panel selection, switch events, escape time) and only adds presentation: edge/service codes, marker rules, an SLO-miss trace, the attempts strip, and the Plotly figure. It never reads the CSVs itself. One small change to `run_timeline.switch_events()` exposes the log fields the markers need.

**Tech Stack:** Python 3.11+ (3.14 locally), pandas, numpy, `plotly` (new), `unittest` run with `python -m pytest`.

Spec: [docs/superpowers/specs/2026-10-13-interactive-run-explorer-design.md](../specs/2026-10-13-interactive-run-explorer-design.md). Builds on the implemented [hold-clock design](../specs/2026-10-13-hold-clock-design.md). Glossary terms in [CONTEXT.md](../../../CONTEXT.md): **Edge code**, **Service code**, **RetryGuard state strip**, **Hold clock**.

**Branch:** run `git branch --show-current` before the first commit and commit on whatever is checked out. (When this plan was written, `main` and `runs-analysis2` pointed at the same commit.) Do not switch branches.

## Global Constraints

- Scope is runs under `experiments/results/final results/` (S1–S4). `campaign_48/`, `august_38/`, S5 and S6 are not targeted. One run per page; no multi-run overlay.
- `explore_run.py` never reads CSVs or logs directly. Everything comes from `run_timeline.per_second_view`, `panel_columns`, `switch_events`, `escape_hold_s`, `_plot_points`, and `hold_clock.read_clock`.
- Panel order, top to bottom: (1) Goodput and RPS, (2) P95, (3) Rejection, (4) Retries per request, (5) TopFull cap, (6) RetryGuard state strip, (7) CPU. Shared hold-clock x-axis, range slider on the bottom panel, `hovermode="x unified"`.
- Rejection panel: solid lines are the controller formula (already in the per-second view); the dashed black line is **Locust SLO-miss** = `locust.total.Fail / locust.total.RPS`, empty where `RPS == 0`. They stay separate traces with separate names.
- Edge codes `E1`–`E14` follow `run_timeline.CONTROLLED_EDGES` order. Service codes `V1`–`V9` follow the order callees first appear in that list (`V`, not `S`, because `S1`–`S6` are scenarios).
- Vertical lines (all panels, exact switch time) only for `VERTICAL_LINE_STEPS = ("ON→OFF", "OFF→ON")`. `ON→OFF` label is `E<n> burst` when `metric=rpr_burst`, otherwise `E<n> normal`. `OFF→ON` label is `V<n>`. Climbs (`1→2`, `2→3`) are not vertical lines: they show on the strip and in hover text. Reason and how to reverse: spec "Decisions".
- Hover on a marker: full edge/service name, step, and any of `metric`, `rpr`, `rejection`, `from_attempts`, `consecutive_low` that are present.
- Escape time: S2 runs only, one dashed black line on panel 1 only, absent when the run never escapes.
- A series is one line. Default visible set is `run_timeline.panel_columns(view)` (rejection and retry lines only if the run has any). Every other line is added as `visible="legendonly"`. `--all` makes them all visible.
- A panel with no lines says "none in this run". A run with no `rg.*.attempts` columns shows "RetryGuard off in this run" on the strip.
- Output: `experiments/explore_out/<run folder name>.html`, git-ignored, `include_plotlyjs=True` (offline-safe), with a legend table of all E and V codes appended.
- Tests: one test per rule that could go wrong silently (codes, marker labels and hover, the climb exclusion, SLO-miss, strip rows and RG-off, trace visibility, the HTML smoke test). No tests for argument parsing, trivial helpers, or plot styling.
- Code comments only state constraints the code can't show.
- On Windows the default console is cp1252. Never print `→` from a script; print paths and numbers only.

---

## File structure

| File | Responsibility |
|---|---|
| Modify `experiments/run_timeline.py` (`switch_events`, ~L275) | Return the log fields markers need; export `SWITCH_EVENT_COLUMNS` |
| Modify `experiments/requirements.txt` | Add `plotly` |
| Modify `.gitignore` | Ignore `experiments/explore_out/` |
| Create `experiments/explore_run.py` | Codes, markers, SLO-miss, strip matrix, line specs, figure, HTML, CLI |
| Create `experiments/test_explore_run.py` | Tests for the rules above |
| Modify `AGENTS.md` (§2 repo layout), `STATUS.md` (Done) | Point at the tool |

---

### Task 1: Dependency, ignore rule, and richer `switch_events`

**Files:**
- Modify: `experiments/requirements.txt`, `.gitignore`
- Modify: `experiments/run_timeline.py` (the `switch_events` function)
- Test: `experiments/test_run_timeline.py` (extend `test_retryguard_observe_and_switches`)

**Interfaces:**
- Produces: `run_timeline.SWITCH_EVENT_COLUMNS: list[str]` = `["hold_s", "name", "step", "metric", "rpr", "rejection", "from_attempts", "consecutive_low"]`; `run_timeline.switch_events(run_dir, clock) -> DataFrame` with exactly those columns (missing fields are NaN; values from the log other than `hold_s` are strings).

- [x] **Step 1: Install plotly and pin it**

Run in the Python environment you run `run_timeline.py` with:

```powershell
python -m pip install plotly
python -m pip show plotly
```

Expected: a `Version:` line. Add that version to `experiments/requirements.txt` (same `name==version` style as the existing PyYAML line):

```text
PyYAML==6.0.3
plotly==<version from pip show>
```

- [x] **Step 2: Ignore the output folder**

Append to `.gitignore` (after the `timeline_1s.csv` line):

```text
experiments/explore_out/
```

- [x] **Step 3: Write the failing test**

In `experiments/test_run_timeline.py`, replace the last four lines of `test_retryguard_observe_and_switches` (from `events = run_timeline.switch_events(...)` to the end of that method) and the two log lines above it, so the log carries real-format fields. The whole method becomes:

```python
    def test_retryguard_observe_and_switches(self):
        (self.run / "retryguard.log").write_text("\n".join([
            f"{iso(1)}  OBSERVE  frontend->checkoutservice  rpr=0.5000  attempts=3  state=ON",
            f"{iso(2)}  frontend->checkoutservice  ON→OFF   rpr=2.10  consecutive_high=2  attempts=0  "
            "from_attempts=3  metric=rpr_burst  elapsed_s=4",
            f"{iso(3)}  checkoutservice  OFF→ON   rejection=0.03  consecutive_low=11  attempts=1  "
            "from_attempts=0  metric=rejection  elapsed_s=20",
        ]), encoding="utf-8")
        view = self.view()
        self.assertEqual(view.loc[1, "rg.frontend->checkoutservice.rpr"], 0.5)
        self.assertEqual(view.loc[2, "rg.switches"], "frontend->checkoutservice ON→OFF")
        events = run_timeline.switch_events(self.run, CLOCK)
        self.assertEqual(list(events.columns), run_timeline.SWITCH_EVENT_COLUMNS)
        self.assertEqual(events["hold_s"].iloc[0], 2.0)
        self.assertEqual(events["metric"].iloc[0], "rpr_burst")
        self.assertEqual(events["from_attempts"].iloc[0], "3")
        self.assertEqual(events["consecutive_low"].iloc[1], "11")
        self.assertTrue(empty(events["rejection"].iloc[0]))
```

- [x] **Step 4: Run it to verify it fails**

Run: `python -m pytest experiments/test_run_timeline.py::TestPerSecondView::test_retryguard_observe_and_switches -v`
Expected: FAIL with `AttributeError: module 'run_timeline' has no attribute 'SWITCH_EVENT_COLUMNS'`.

- [x] **Step 5: Implement**

In `experiments/run_timeline.py`, replace the whole `switch_events` function with:

```python
SWITCH_EVENT_COLUMNS = [
    "hold_s", "name", "step", "metric", "rpr", "rejection", "from_attempts", "consecutive_low",
]


def switch_events(run_dir: Path, clock: dict) -> pd.DataFrame:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty or "step" not in df.columns:
        return pd.DataFrame(columns=SWITCH_EVENT_COLUMNS)
    switches = df[(df["kind"] == "switch") & df["hold_s"].notna()]
    return switches.reindex(columns=SWITCH_EVENT_COLUMNS).reset_index(drop=True)
```

- [x] **Step 6: Run the timeline tests**

Run: `python -m pytest experiments/test_run_timeline.py experiments/test_hold_clock.py -q`
Expected: all pass (the static chart only reads `hold_s` and `step`).

- [x] **Step 7: Commit**

```bash
git add experiments/run_timeline.py experiments/test_run_timeline.py experiments/requirements.txt .gitignore
git commit -m "feat(timeline): switch_events carries metric and hover fields; add plotly"
```

---

### Task 2: Pure helpers in `explore_run.py`

**Files:**
- Create: `experiments/explore_run.py` (helpers only; the figure comes in Task 3)
- Create: `experiments/test_explore_run.py`

**Interfaces:**
- Consumes: `run_timeline.CONTROLLED_EDGES`, `run_timeline.SWITCH_COLORS`, `run_timeline.SWITCH_EVENT_COLUMNS`, `run_timeline.panel_columns(view, show_all)`.
- Produces (all in `explore_run`):
  - `VERTICAL_LINE_STEPS: tuple[str, ...]`
  - `EDGE_NAMES: list[str]`, `EDGE_CODES: dict[str, str]`, `SERVICE_NAMES: list[str]`, `SERVICE_CODES: dict[str, str]`
  - `marker_label(step: str, name: str, metric) -> str | None`
  - `markers(events: DataFrame) -> list[dict]` with keys `x` (float), `label` (str), `hover` (str), `color` (str)
  - `slo_miss(view: DataFrame) -> Series | None`
  - `strip_matrix(view: DataFrame) -> DataFrame | None` (rows `E<n>` in edge order, columns hold seconds)
  - `trace_name(key: str, column: str) -> str`
  - `line_specs(view: DataFrame, show_all: bool = False) -> list[tuple[str, str, str, object]]` of `(panel_key, column, trace_name, visible)` where `visible` is `True` or `"legendonly"`

- [x] **Step 1: Write the failing tests**

Create `experiments/test_explore_run.py`:

```python
"""Unit tests for experiments/explore_run.py."""
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import explore_run  # noqa: E402
import run_timeline  # noqa: E402

NAN = float("nan")


def events(rows):
    return pd.DataFrame(rows, columns=run_timeline.SWITCH_EVENT_COLUMNS)


class TestCodes(unittest.TestCase):
    def test_codes_follow_controlled_edges_order(self):
        codes = explore_run.EDGE_CODES
        self.assertEqual(len(codes), 14)
        self.assertEqual(codes["frontend->adservice"], "E1")
        self.assertEqual(codes["frontend->checkoutservice"], "E3")
        self.assertEqual(codes["frontend->productcatalogservice"], "E5")
        self.assertEqual(codes["recommendationservice->productcatalogservice"], "E14")
        services = explore_run.SERVICE_CODES
        self.assertEqual(len(services), 9)
        self.assertEqual(services["adservice"], "V1")
        self.assertEqual(services["checkoutservice"], "V3")
        self.assertEqual(services["emailservice"], "V8")
        self.assertEqual(services["paymentservice"], "V9")


class TestMarkers(unittest.TestCase):
    def test_labels_hover_and_climb_exclusion(self):
        found = explore_run.markers(events([
            [10.0, "frontend->productcatalogservice", "ON→OFF", "rpr_burst", "2.46", NAN, "3", NAN],
            [20.0, "checkoutservice", "OFF→ON", "rejection", NAN, "0.03", "0", "11"],
            [30.0, "frontend->checkoutservice", "ON→OFF", "rpr", "0.90", NAN, "1", NAN],
            [40.0, "frontend->cartservice", "1→2", "rpr", NAN, NAN, "1", NAN],
            [50.0, "frontend->cartservice", "2→3", "rpr", NAN, NAN, "2", NAN],
        ]))
        self.assertEqual([m["label"] for m in found], ["E5 burst", "V3", "E3 normal"])
        self.assertEqual([m["x"] for m in found], [10.0, 20.0, 30.0])
        self.assertIn("rpr=2.46", found[0]["hover"])
        self.assertIn("from_attempts=3", found[0]["hover"])
        self.assertNotIn("rejection", found[0]["hover"])
        self.assertIn("consecutive_low=11", found[1]["hover"])
        self.assertNotEqual(found[0]["color"], found[1]["color"])


class TestSloMiss(unittest.TestCase):
    def test_fail_over_rps_empty_when_no_load(self):
        view = pd.DataFrame({"locust.total.Fail": [0.0, 5.0, 3.0],
                             "locust.total.RPS": [10.0, 0.0, 6.0]})
        result = explore_run.slo_miss(view)
        self.assertEqual(result.iloc[0], 0.0)
        self.assertTrue(math.isnan(result.iloc[1]))
        self.assertEqual(result.iloc[2], 0.5)
        self.assertIsNone(explore_run.slo_miss(pd.DataFrame({"x": [1]})))


class TestStrip(unittest.TestCase):
    def test_rows_follow_edge_order_and_off_runs_have_none(self):
        view = pd.DataFrame({
            "rg.frontend->checkoutservice.attempts": [3.0, 0.0],
            "rg.frontend->adservice.attempts": [3.0, 3.0],
        })
        matrix = explore_run.strip_matrix(view)
        self.assertEqual(list(matrix.index), ["E1", "E3"])
        self.assertEqual(matrix.loc["E3"].tolist(), [3.0, 0.0])
        self.assertIsNone(explore_run.strip_matrix(pd.DataFrame({"locust.total.RPS": [1.0]})))


class TestLineSpecs(unittest.TestCase):
    def view(self):
        return pd.DataFrame({
            "locust.total.Goodput": [1.0, 2.0],
            "locust.total.RPS": [1.0, 2.0],
            "locust.total.Latency95": [5.0, 6.0],
            "inbound.cartservice.rejection": [0.0, 0.0],
            "inbound.checkoutservice.rejection": [0.0, 0.1],
            "edge.frontend->checkoutservice.rpr": [0.0, 0.4],
            "edge.frontend->checkoutservice.retry_per_s": [0.0, 2.0],
            "resource.frontend.cpu_millicores": [10.0, 20.0],
        })

    def test_quiet_lines_are_legend_only_unless_all(self):
        by_column = {s[1]: s for s in explore_run.line_specs(self.view())}
        self.assertIs(by_column["inbound.checkoutservice.rejection"][3], True)
        self.assertEqual(by_column["inbound.cartservice.rejection"][3], "legendonly")
        self.assertEqual(by_column["edge.frontend->checkoutservice.rpr"][2], "E3 frontend->checkoutservice")
        self.assertEqual(by_column["inbound.cartservice.rejection"][2], "cartservice")
        self.assertEqual(by_column["locust.total.Goodput"][2], "Goodput")
        every = {s[1]: s for s in explore_run.line_specs(self.view(), show_all=True)}
        self.assertIs(every["inbound.cartservice.rejection"][3], True)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run to verify it fails**

Run: `python -m pytest experiments/test_explore_run.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'explore_run'`.

- [x] **Step 3: Implement the helpers**

Create `experiments/explore_run.py`:

```python
"""Interactive Plotly view of one run on the hold clock.

    python experiments/explore_run.py <run_dir> [--all]

Writes experiments/explore_out/<run folder name>.html (not committed).
Design and decisions: docs/superpowers/specs/2026-10-13-interactive-run-explorer-design.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_timeline  # noqa: E402

# Attempts climbs (1→2, 2→3) are deliberately not vertical lines: they show on the
# state strip and in hover text. To draw them, add them here. See the spec, "Decisions".
VERTICAL_LINE_STEPS = ("ON→OFF", "OFF→ON")

EDGE_NAMES = [f"{caller}->{target}" for caller, target in run_timeline.CONTROLLED_EDGES]
EDGE_CODES = {name: f"E{i}" for i, name in enumerate(EDGE_NAMES, start=1)}
SERVICE_NAMES = list(dict.fromkeys(target for _, target in run_timeline.CONTROLLED_EDGES))
SERVICE_CODES = {name: f"V{i}" for i, name in enumerate(SERVICE_NAMES, start=1)}

HOVER_FIELDS = ("metric", "rpr", "rejection", "from_attempts", "consecutive_low")
PANEL_KEYS = ("locust", "p95", "rejection", "rpr", "caps", "cpu")


def marker_label(step: str, name: str, metric) -> str | None:
    if step == "ON→OFF":
        mode = "burst" if metric == "rpr_burst" else "normal"
        return f"{EDGE_CODES.get(name, name)} {mode}"
    if step == "OFF→ON":
        return SERVICE_CODES.get(name, name)
    return None


def markers(events: pd.DataFrame) -> list[dict]:
    found = []
    for _, event in events.iterrows():
        step = event["step"]
        if step not in VERTICAL_LINE_STEPS:
            continue
        lines = [f"{event['name']} {step}"]
        lines += [f"{key}={event[key]}" for key in HOVER_FIELDS if pd.notna(event[key])]
        found.append({
            "x": float(event["hold_s"]),
            "label": marker_label(step, event["name"], event["metric"]),
            "hover": "<br>".join(lines),
            "color": run_timeline.SWITCH_COLORS.get(step, "gray"),
        })
    return found


def slo_miss(view: pd.DataFrame) -> pd.Series | None:
    if not {"locust.total.Fail", "locust.total.RPS"} <= set(view.columns):
        return None
    rps = view["locust.total.RPS"]
    return (view["locust.total.Fail"] / rps).where(rps > 0)


def strip_matrix(view: pd.DataFrame) -> pd.DataFrame | None:
    rows = {
        EDGE_CODES[name]: view[f"rg.{name}.attempts"]
        for name in EDGE_NAMES
        if f"rg.{name}.attempts" in view.columns
    }
    if not rows:
        return None
    return pd.DataFrame(rows).T


def trace_name(key: str, column: str) -> str:
    if key in ("locust", "p95"):
        return column.split(".")[-1]
    if key == "rpr":
        edge = column[len("edge."):-len(".rpr")]
        return f"{EDGE_CODES.get(edge, edge)} {edge}"
    return column.split(".")[1]


def line_specs(view: pd.DataFrame, show_all: bool = False) -> list[tuple[str, str, str, object]]:
    default = run_timeline.panel_columns(view)
    every = run_timeline.panel_columns(view, show_all=True)
    specs = []
    for key in PANEL_KEYS:
        for column in every[key]:
            visible = True if show_all or column in default[key] else "legendonly"
            specs.append((key, column, trace_name(key, column), visible))
    return specs
```

- [x] **Step 4: Run to verify they pass**

Run: `python -m pytest experiments/test_explore_run.py -v`
Expected: 5 passed.

- [x] **Step 5: Commit**

```bash
git add experiments/explore_run.py experiments/test_explore_run.py
git commit -m "feat(explore): edge/service codes, markers, SLO-miss, strip matrix, line specs"
```

---

### Task 3: Figure, HTML and CLI

**Files:**
- Modify: `experiments/explore_run.py`
- Test: `experiments/test_explore_run.py`

**Interfaces:**
- Consumes: Task 2 helpers; `hold_clock.read_clock`, `run_timeline.per_second_view`, `run_timeline.switch_events`, `run_timeline.escape_hold_s`, `run_timeline._plot_points`.
- Produces: `PANELS`, `build_figure(run_dir, show_all=False) -> go.Figure`, `legend_html() -> str`, `write_html(fig, path) -> None`, `main(argv=None) -> int`.

- [x] **Step 1: Write the failing smoke test**

Append to `experiments/test_explore_run.py`, above the `if __name__` line:

```python
import tempfile  # noqa: E402

from test_hold_clock import E, iso, make_run  # noqa: E402


def render(run: Path) -> str:
    out = run / "explore.html"
    explore_run.write_html(explore_run.build_figure(run), out)
    return out.read_text(encoding="utf-8")


class TestBuild(unittest.TestCase):
    def test_html_has_codes_markers_and_retryguard_off_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            off = render(run)
            self.assertIn("RetryGuard off in this run", off)
            self.assertNotIn("E3 burst", off)
            (run / "retryguard.log").write_text("\n".join([
                f"{iso(E + 30)}  OBSERVE  frontend->checkoutservice  rpr=0.5000  attempts=3  "
                "state=ON  metric=rpr",
                f"{iso(E + 31)}  frontend->checkoutservice  ON→OFF   rpr=2.10  consecutive_high=2  "
                "attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4",
                f"{iso(E + 32)}  OBSERVE  frontend->checkoutservice  rpr=0.0000  attempts=0  "
                "state=OFF  metric=rpr",
                f"{iso(E + 60)}  checkoutservice  OFF→ON   rejection=0.03  consecutive_low=11  "
                "attempts=1  from_attempts=0  metric=rejection  elapsed_s=20",
            ]), encoding="utf-8")
            on = render(run)
            self.assertNotIn("RetryGuard off in this run", on)
            self.assertIn("E3 burst", on)
            self.assertIn("V3", on)
            self.assertIn("E14", on)
            self.assertIn("V9", on)
```

- [x] **Step 2: Run to verify it fails**

Run: `python -m pytest experiments/test_explore_run.py::TestBuild -v`
Expected: FAIL with `AttributeError: module 'explore_run' has no attribute 'write_html'`.

- [x] **Step 3: Replace the imports block**

In `experiments/explore_run.py`, replace the import block (from `from __future__ import annotations` through `import run_timeline  # noqa: E402`) with:

```python
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402
import run_timeline  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "explore_out"
```

- [x] **Step 4: Append the figure, HTML and CLI code**

Append to the end of `experiments/explore_run.py`:

```python
PANELS = (
    ("locust", "Goodput / RPS (req/s)"),
    ("p95", "P95 (ms)"),
    ("rejection", "Rejection"),
    ("rpr", "Retries per request"),
    ("caps", "TopFull cap (req/s)"),
    ("strip", "Attempts (0 off, 3 full)"),
    ("cpu", "CPU (millicores)"),
)
ROW = {key: index for index, (key, _) in enumerate(PANELS, start=1)}
ROW_HEIGHTS = [0.17, 0.13, 0.15, 0.15, 0.12, 0.14, 0.14]
ATTEMPT_COLORS = {0: "#d62728", 1: "#ff7f0e", 2: "#f2c744", 3: "#2ca02c"}


def axis(row: int, letter: str) -> str:
    return letter if row == 1 else f"{letter}{row}"


def attempts_colorscale() -> list[list]:
    scale = []
    for level, color in ATTEMPT_COLORS.items():
        scale += [[level / 4, color], [(level + 1) / 4, color]]
    return scale


def add_note(fig: go.Figure, row: int, text: str) -> None:
    fig.add_annotation(
        text=text, xref=f"{axis(row, 'x')} domain", yref=f"{axis(row, 'y')} domain",
        x=0.5, y=0.5, showarrow=False, font={"color": "gray"},
    )


def build_figure(run_dir: Path, show_all: bool = False) -> go.Figure:
    run_dir = Path(run_dir)
    clock = hold_clock.read_clock(run_dir)
    view = run_timeline.per_second_view(run_dir, clock)
    events = run_timeline.switch_events(run_dir, clock)
    fig = make_subplots(
        rows=len(PANELS), cols=1, shared_xaxes=True,
        vertical_spacing=0.025, row_heights=ROW_HEIGHTS,
    )
    used = set()

    for key, column, name, visible in line_specs(view, show_all):
        x, y = run_timeline._plot_points(view[column])
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name=name, visible=visible,
                       line={"width": 1.2}, legendgroup=key),
            row=ROW[key], col=1,
        )
        used.add(key)

    slo = slo_miss(view)
    if slo is not None:
        x, y = run_timeline._plot_points(slo)
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name="Locust SLO-miss",
                       line={"width": 1.5, "dash": "dash", "color": "black"},
                       legendgroup="rejection"),
            row=ROW["rejection"], col=1,
        )
        used.add("rejection")

    matrix = strip_matrix(view)
    if matrix is None:
        add_note(fig, ROW["strip"], "RetryGuard off in this run")
    else:
        fig.add_trace(
            go.Heatmap(
                z=matrix.to_numpy(dtype=float), x=matrix.columns.to_numpy(), y=list(matrix.index),
                colorscale=attempts_colorscale(), zmin=0, zmax=4, showscale=False,
                hovertemplate="%{y}  t=%{x}s  attempts=%{z}<extra></extra>",
            ),
            row=ROW["strip"], col=1,
        )
        fig.update_yaxes(autorange="reversed", row=ROW["strip"], col=1)
        used.add("strip")

    for key, row in ROW.items():
        if key not in used:
            add_note(fig, row, "none in this run")

    shapes = []
    for marker in markers(events):
        for row in range(1, len(PANELS) + 1):
            shapes.append({
                "type": "line", "xref": axis(row, "x"), "yref": f"{axis(row, 'y')} domain",
                "x0": marker["x"], "x1": marker["x"], "y0": 0, "y1": 1,
                "line": {"color": marker["color"], "width": 1}, "opacity": 0.6, "layer": "below",
            })
        fig.add_annotation(
            x=marker["x"], xref="x", y=1, yref="y domain", yanchor="bottom",
            text=marker["label"], textangle=-90, showarrow=False,
            font={"size": 9, "color": marker["color"]}, hovertext=marker["hover"],
        )

    escape_s = run_timeline.escape_hold_s(run_dir, clock)
    if escape_s is not None:
        shapes.append({
            "type": "line", "xref": "x", "yref": "y domain", "x0": escape_s, "x1": escape_s,
            "y0": 0, "y1": 1, "line": {"color": "black", "width": 1.5, "dash": "dash"},
        })
        fig.add_annotation(
            x=escape_s, xref="x", y=0, yref="y domain", yanchor="bottom", xanchor="left",
            text="escape", showarrow=False, font={"size": 9},
        )
    fig.update_layout(shapes=shapes)

    for key, ylabel in PANELS:
        fig.update_yaxes(title_text=ylabel, row=ROW[key], col=1)
    fig.update_xaxes(
        title_text="Hold clock (s since the first Locust row)",
        rangeslider={"visible": True, "thickness": 0.03}, row=len(PANELS), col=1,
    )
    fig.update_layout(
        title=run_dir.name, height=1600, hovermode="x unified", margin={"t": 90},
    )
    return fig


def legend_html() -> str:
    def table(title: str, codes: dict[str, str]) -> str:
        rows = "".join(
            f"<tr><td><b>{code}</b></td><td>{html.escape(name)}</td></tr>"
            for name, code in codes.items()
        )
        return f"<div><h3>{title}</h3><table>{rows}</table></div>"

    return (
        '<div style="display:flex;gap:48px;padding:16px;font-family:sans-serif;font-size:13px">'
        + table("Edge codes (ON→OFF markers)", EDGE_CODES)
        + table("Service codes (OFF→ON markers)", SERVICE_CODES)
        + "</div>"
    )


def write_html(fig: go.Figure, path: Path) -> None:
    page = pio.to_html(fig, full_html=True, include_plotlyjs=True)
    page = page.replace("</body>", legend_html() + "</body>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive hold-clock view of one run.")
    parser.add_argument("run", help="Run folder")
    parser.add_argument("--all", action="store_true", help="Show every service and edge line")
    args = parser.parse_args(argv)
    run = Path(args.run)
    out = OUT_DIR / f"{run.name}.html"
    write_html(build_figure(run, show_all=args.all), out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 5: Run the explore tests**

Run: `python -m pytest experiments/test_explore_run.py -v`
Expected: 6 passed.

- [x] **Step 6: Run the whole timeline family**

Run: `python -m pytest experiments/test_explore_run.py experiments/test_run_timeline.py experiments/test_hold_clock.py -q`
Expected: all pass.

- [x] **Step 7: Commit**

```bash
git add experiments/explore_run.py experiments/test_explore_run.py
git commit -m "feat(explore): interactive Plotly figure, legend table and CLI"
```

---

### Task 4: Check on real runs, then docs

**Files:**
- Modify: `AGENTS.md` (§2 repo layout), `STATUS.md` (Done)

- [x] **Step 1: Burst run**

```powershell
python experiments/explore_run.py "experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1"
python -c "import sys; sys.path.insert(0,'experiments'); import explore_run as e; f=e.build_figure(r'experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1'); print(len(f.data), len(f.layout.shapes), len(f.layout.annotations))"
```

Expected: the first prints the HTML path under `experiments/explore_out/`. In the second, `shapes` is 196 (28 markers × 7 panels), or 197 if the run has an escape line. The log has 14 `E3 burst` sheds and 14 `V3` re-enables, so `annotations` is at least 28.

- [x] **Step 2: Find a normal-mode run with a `metric=rpr` shed**

```powershell
python -c "import sys,pathlib; sys.path.insert(0,'experiments'); import hold_clock; [print(p.parent) for p in sorted(pathlib.Path('experiments/results/final results').rglob('retryguard.log')) if (lambda d: 'step' in d and ((d.kind=='switch')&(d.step=='ON→OFF')&(d.metric=='rpr')).any())(hold_clock.retryguard_rows(p.read_text(encoding='utf-8',errors='replace')))]"
```

Expected: one or more run folders (40 such sheds exist across the 31 logs). Build one with `python experiments/explore_run.py "<folder>"` and confirm the figure has an `E<n> normal` annotation:

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import explore_run as e; f=e.build_figure(r'<folder>'); print(sorted({a.text for a in f.layout.annotations if a.text and 'normal' in a.text}))"
```

If the list is empty, stop and report; the label rule is wrong.

- [x] **Step 3: Check a RetryGuard-off run**

Pick any `tf_only` folder (for example `experiments/results/final results/S2_sustained_overload_normal/tf_only/s2_normal_tf1rg0`), build it, and confirm the page opens with "RetryGuard off in this run" and no marker lines.

- [x] **Step 4: Ask the user to open the pages**

Report the three HTML paths and ask the user to check, by eye, that panels zoom together, the legend toggles hidden lines, marker labels are readable, and the range slider does not hide the bottom panel. Fix layout constants (`height`, `row_heights`, slider `thickness`) from what they report. Do not mark this task done until they have looked.

- [x] **Step 5: Docs**

In `AGENTS.md` §2 repo layout, add one line after the `mentor_charts*.py` line:

```text
 explore_run.py ← interactive Plotly view of one `final results/` run on the hold clock → `experiments/explore_out/<run>.html` (git-ignored); personal exploration tool, not part of the pull
```

In `STATUS.md`, read the Done section's format and append one bullet in the same style: interactive run explorer (`experiments/explore_run.py`) built on the hold clock; spec and plan paths; `plotly` added to `experiments/requirements.txt`; attempts climbs are deliberately not vertical lines (spec "Decisions").

- [x] **Step 6: Final test run and commit**

Run: `python -m pytest experiments/test_explore_run.py experiments/test_run_timeline.py experiments/test_hold_clock.py -q`
Expected: all pass.

```bash
git add AGENTS.md STATUS.md
git commit -m "docs: point AGENTS.md and STATUS.md at the interactive run explorer"
```

---

## Self-review (spec coverage)

| Spec requirement | Task |
|---|---|
| New `experiments/explore_run.py`, `python experiments/explore_run.py <run_dir> [--all]` | 2, 3 |
| Output `experiments/explore_out/<log_folder>.html`, git-ignored, offline-safe | 1 (ignore), 3 |
| Imports `run_timeline`, never reads CSVs | 2, 3 |
| `plotly` in `experiments/requirements.txt` | 1 |
| `switch_events()` returns `metric` (and hover fields) | 1 |
| Seven panels in the agreed order; shared x, range slider, unified hover | 3 |
| Rejection: controller solid + dashed Locust SLO-miss | 2 (`slo_miss`), 3 |
| Default vs `--all` lines; legend toggles the rest | 2 (`line_specs`), 3 |
| Markers `E<n> burst` / `E<n> normal` / `V<n>`, hover fields | 2 (`markers`), 3 |
| Climbs not vertical lines; constant to reverse | 2 (`VERTICAL_LINE_STEPS`) |
| E1–E14 / V1–V9 fixed codes and legend table | 2, 3 (`legend_html`) |
| Strip: rows E1–E14, attempts 0–3 from `OBSERVE` | 2 (`strip_matrix`), 3 |
| Escape time: S2 only, panel 1 only | 3 |
| RetryGuard-off note; "none in this run" notes | 3 |
| First checks on `s2_burst20_rgtf1` and a normal-mode run | 4 |
| Out of scope: overlay, S5/S6, `pull_results.py` hook | not built |

Names checked across tasks: `SWITCH_EVENT_COLUMNS`, `EDGE_CODES`, `SERVICE_CODES`, `markers`, `slo_miss`, `strip_matrix`, `line_specs`, `trace_name`, `build_figure`, `write_html`, `legend_html` are each defined once and used with the same signature.
