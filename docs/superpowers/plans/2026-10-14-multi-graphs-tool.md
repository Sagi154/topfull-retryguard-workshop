# multi_graphs_tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `experiments/multi_graphs_tool.py`, which shows N holds as stacked comparison panels controlled by one shared Plotly legend under the last panel.

**Architecture:** Each panel is the existing `graphs_tool.compare_figure(run_dir)` post-processed (no legend, plain CPU names, pinned x-range, shared colours per series). One extra figure holds only the legend: the union of every panel's series, all off except events. A small script on the page reads that legend as the single source of truth and pushes visibility, right-axis layout, event names, and a shared y-range to every panel, and mirrors x/y zoom between panels. `graphs_tool.py` is not modified.

**Tech Stack:** Python 3, plotly 7.1.0 (`plotly.graph_objects`, `plotly.io`), `unittest`, optional `playwright` for browser tests (already used by `test_graphs_tool.py`; tests skip if missing).

## Global Constraints

Copied from [the spec](../specs/2026-10-14-multi-graphs-tool-design.md):

- Runs under `experiments/results/final results/` (S1–S4) only. `campaign_48/`, `august_38/`, S5, S6 are out.
- Any N >= 2 runs. Panels are generated per run.
- Output: `experiments/explore_out/multi_<nameA>__<nameB>[__<nameC>...].html`, git-ignored, self-contained, works offline.
- Page order: N comparison panels (no legend on a panel), then one Plotly legend, then the E/V code key.
- The legend keeps comparison-chart behaviour: section titles, item clicks, titles stay black, every line starts off (`legendonly`); the event lines start on.
- A section title toggles the whole group; an item toggles one line.
- Trace names are identical across runs. CPU uses the plain service name; the limit goes into hover.
- x linked across panels; t = 0 is each run's hold clock; range pinned to the longest run.
- y: one shared range per unit across all panels, max over currently visible traces in all runs, recomputed on every toggle; a manual y-zoom on one panel sets the same range on every panel.
- Each panel draws its own run's events and name annotations; the legend's "RetryGuard events" section toggles them.
- A run lacking a visible series shows "none in this run" for it.
- Out of v1: the nine stacked panels, `--all`, any change to `pull_results.py`, a cursor synced across panels.

**Deviation from the spec:** the spec preferred extracting `graphs_tool`'s legend JS. This plan writes the page script fresh in `multi_graphs_tool.py` and leaves `graphs_tool.py` byte-for-byte unchanged, so single-run pages cannot regress. Task 5 amends the spec to say so.

## File Structure

- Create `experiments/multi_graphs_tool.py`: panel figures, series union, colours, legend figure, page assembly, page script, CLI. One file; `graphs_tool.py` is about 820 lines, this should stay under 450.
- Create `experiments/test_multi_graphs_tool.py`: unit tests (Python structure) plus browser tests (skipped without playwright).
- Modify `Guides and Info/GRAPHS-TOOL.md`: new short section.
- Modify `AGENTS.md`: repo-layout line and "Where to find metrics" row.
- Modify `docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md`: record the deviation.

Run tests from the repo root with `python experiments/test_multi_graphs_tool.py -v` (the existing tests are run the same way). A single class: `python experiments/test_multi_graphs_tool.py TestNormalize -v`.

---

### Task 1: Panel figures, series union, colours, legend figure

**Files:**
- Create: `experiments/multi_graphs_tool.py`
- Create: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: `graphs_tool.compare_figure(run_dir) -> go.Figure`, `graphs_tool.PANEL_KEYS`, `graphs_tool.EVENT_GROUP`, `graphs_tool.COMPARE_EVENT_STEPS`, `graphs_tool.OUT_DIR`.
- Produces (used by later tasks):
  - `run_label(run_dir) -> str`
  - `panel_figure(run_dir) -> go.Figure`
  - `pin_x_range(figs) -> list[float]` (also writes the range onto every fig)
  - `decorate_slider(figs) -> None`
  - `series_union(figs) -> dict[tuple[str, str], go.Scatter]` keyed `(legendgroup, name)`, ordered by group then first seen
  - `assign_colors(figs, union) -> dict[tuple[str, str], str]`
  - `legend_figure(union) -> go.Figure`
  - constants `PANEL_HEIGHT`, `SLIDER_EXTRA`, `LEGEND_HEIGHT`

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_multi_graphs_tool.py`:

```python
"""Unit and browser tests for experiments/multi_graphs_tool.py."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graphs_tool  # noqa: E402
import multi_graphs_tool  # noqa: E402

AXES = {
    "yaxis2": graphs_tool.right_axis("ms", None),
    "yaxis3": graphs_tool.right_axis("fraction", 0.82),
    "yaxis4": graphs_tool.right_axis("retries/req", 0.90),
    "yaxis5": graphs_tool.right_axis("millicores", 0.98),
    "yaxis7": graphs_tool.right_axis("retries", None),
    "yaxis8": graphs_tool.right_axis("ticks", None),
}


def synthetic(series, x_max, events=()):
    """A stand-in for graphs_tool.compare_figure: same axes, same trace conventions.

    series is a list of (legendgroup, name, y values).
    """
    fig = go.Figure()
    for group, name, y in series:
        unit = graphs_tool.UNIT[group]
        fig.add_trace(go.Scatter(
            x=list(range(len(y))), y=y, mode="lines", name=name, visible="legendonly",
            legendgroup=group, meta=unit, yaxis=graphs_tool.trace_yaxis(unit),
            legendgrouptitle={"text": graphs_tool.ylabel(group)}, line={"width": 1.4},
        ))
    for step in events:
        fig.add_trace(go.Scatter(
            x=[1, 1, None], y=[0, 1, None], mode="lines", name=step, visible=True,
            line={"width": 1.2, "color": "red"}, hoverinfo="skip",
            legendgroup=graphs_tool.EVENT_GROUP, meta="event",
            legendgrouptitle={"text": "RetryGuard events"}, yaxis="y6",
        ))
        fig.add_annotation(
            x=1, xref="x", y=1, yref="y domain", text="E3 burst", showarrow=False,
            name=step, hovertext="frontend->checkoutservice ON→OFF",
        )
    fig.update_layout(
        xaxis={"range": [0, x_max]},
        yaxis6={"overlaying": "y", "range": [0, 1], "showticklabels": False},
        **AXES,
    )
    return fig


class TestPanelFigure(unittest.TestCase):
    def test_panel_has_no_legend_and_cpu_name_loses_the_limit(self):
        source = synthetic([("cpu", "frontend (1150)", [1.0, 2.0]),
                            ("locust", "Goodput", [1.0, 2.0])], 10)
        with mock.patch.object(graphs_tool, "compare_figure", return_value=source):
            fig = multi_graphs_tool.panel_figure(Path("final/S2/both/run_a"))
        self.assertFalse(fig.layout.showlegend)
        self.assertTrue(all(trace.showlegend is False for trace in fig.data))
        cpu = next(trace for trace in fig.data if trace.legendgroup == "cpu")
        self.assertEqual(cpu.name, "frontend")
        self.assertIn("of 1150m", cpu.hovertemplate)
        self.assertIn("<extra>frontend</extra>", cpu.hovertemplate)
        goodput = next(trace for trace in fig.data if trace.name == "Goodput")
        self.assertIsNone(goodput.hovertemplate)
        self.assertEqual(fig.layout.height, multi_graphs_tool.PANEL_HEIGHT)

    def test_run_label_names_scenario_variant_and_run(self):
        label = multi_graphs_tool.run_label(Path("x/S2_sustained_overload_burst/both/s2_burst20_rgtf1"))
        self.assertEqual(label, "S2_sustained_overload_burst / both / s2_burst20_rgtf1")


class TestNormalize(unittest.TestCase):
    def figs(self):
        return [
            synthetic([("locust", "Goodput", [1.0]), ("rejection", "checkoutservice", [1.0])], 300),
            synthetic([("locust", "Goodput", [1.0]), ("rpr", "E3 frontend->checkoutservice", [1.0])],
                      600, events=("ON→OFF",)),
        ]

    def test_x_range_is_pinned_to_the_longest_run(self):
        figs = self.figs()
        pinned = multi_graphs_tool.pin_x_range(figs)
        self.assertEqual(pinned, [0, 600])
        for fig in figs:
            self.assertEqual(list(fig.layout.xaxis.range), [0, 600])

    def test_union_is_ordered_by_group_and_keyed_by_group_and_name(self):
        union = multi_graphs_tool.series_union(self.figs())
        self.assertEqual(list(union), [
            ("locust", "Goodput"),
            ("rejection", "checkoutservice"),
            ("rpr", "E3 frontend->checkoutservice"),
            ("events", "ON→OFF"),
        ])

    def test_same_series_gets_the_same_colour_in_every_panel(self):
        figs = self.figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        first = next(t for t in figs[0].data if t.name == "Goodput")
        second = next(t for t in figs[1].data if t.name == "Goodput")
        self.assertEqual(first.line.color, second.line.color)
        self.assertEqual(first.line.color, colors[("locust", "Goodput")])
        reject = next(t for t in figs[0].data if t.name == "checkoutservice")
        self.assertNotEqual(reject.line.color, first.line.color)
        event = next(t for t in figs[1].data if t.name == "ON→OFF")
        self.assertEqual(event.line.color, "red")

    def test_slider_only_on_the_last_panel(self):
        figs = self.figs()
        multi_graphs_tool.decorate_slider(figs)
        self.assertFalse(figs[0].layout.xaxis.rangeslider.visible)
        self.assertTrue(figs[1].layout.xaxis.rangeslider.visible)
        self.assertEqual(figs[1].layout.height, figs[0].layout.height + multi_graphs_tool.SLIDER_EXTRA)
        self.assertEqual(figs[0].layout.xaxis.title.text, "")
        self.assertEqual(figs[1].layout.xaxis.title.text, graphs_tool.HOLD_CLOCK_TITLE)


class TestLegendFigure(unittest.TestCase):
    def test_legend_lists_the_union_off_except_events(self):
        figs = [
            synthetic([("locust", "Goodput", [1.0])], 300),
            synthetic([("rpr", "E3 frontend->checkoutservice", [1.0])], 600, events=("ON→OFF",)),
        ]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        legend = multi_graphs_tool.legend_figure(union, colors)
        self.assertEqual([t.name for t in legend.data],
                         ["Goodput", "E3 frontend->checkoutservice", "ON→OFF"])
        self.assertEqual([t.visible for t in legend.data], ["legendonly", "legendonly", True])
        self.assertEqual([t.meta for t in legend.data], ["req/s", "retries/request", "event"])
        self.assertEqual(legend.data[0].line.color, colors[("locust", "Goodput")])
        self.assertEqual(legend.data[0].legendgrouptitle.font.color, "black")
        self.assertEqual(legend.layout.legend.groupclick, "toggleitem")
        self.assertEqual(legend.layout.height, multi_graphs_tool.LEGEND_HEIGHT)
        self.assertFalse(legend.layout.xaxis.visible)


if __name__ == "__main__":
    unittest.main()
```

The tests use `graphs_tool.HOLD_CLOCK_TITLE`, which does not exist yet. Do not add it to `graphs_tool.py` (that file stays unchanged); instead define it in `multi_graphs_tool.py` and change the test to read `multi_graphs_tool.HOLD_CLOCK_TITLE`. Make that edit to the test file now:

```python
        self.assertEqual(figs[1].layout.xaxis.title.text, multi_graphs_tool.HOLD_CLOCK_TITLE)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python experiments/test_multi_graphs_tool.py -v`
Expected: FAIL at import, `ModuleNotFoundError: No module named 'multi_graphs_tool'`.

- [ ] **Step 3: Write the implementation**

Create `experiments/multi_graphs_tool.py`:

```python
"""multi_graphs_tool: N holds as stacked comparison panels with one shared legend.

    python experiments/multi_graphs_tool.py <run_dir> <run_dir> [<run_dir> ...]

Writes experiments/explore_out/multi_<run names>.html (not committed).
Design: docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import plotly.colors as plotly_colors
import plotly.graph_objects as go
import plotly.io as pio

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graphs_tool  # noqa: E402

OUT_DIR = graphs_tool.OUT_DIR
HOLD_CLOCK_TITLE = "Hold clock (s since the first Locust row)"
PANEL_HEIGHT = 440
SLIDER_EXTRA = 70
# The legend figure starts tall so Plotly never scrolls it. The page script then
# shrinks the figure to the legend's measured height.
LEGEND_HEIGHT = 900
# Room above the plot for the rotated event names.
PANEL_MARGIN = {"t": 80, "r": 36, "b": 48, "l": 64}
GROUP_ORDER = list(graphs_tool.PANEL_KEYS) + [graphs_tool.EVENT_GROUP]
CPU_LIMIT_SUFFIX = re.compile(r" \((\d+)\)$")
PALETTE = plotly_colors.qualitative.Dark24 + plotly_colors.qualitative.Light24


def run_label(run_dir: Path) -> str:
    """Scenario/mode folder, variant folder, and run folder, as one header line."""
    run_dir = Path(run_dir)
    parts = [run_dir.parent.parent.name, run_dir.parent.name, run_dir.name]
    return " / ".join(part for part in parts if part)


def panel_figure(run_dir: Path) -> go.Figure:
    """One run's comparison chart, without its own legend.

    CPU traces lose the limit from the name so the same toggle hits the same line in
    every panel. The limit moves into the hover text.
    """
    fig = graphs_tool.compare_figure(run_dir)
    for trace in fig.data:
        trace.showlegend = False
        if trace.legendgroup != "cpu":
            continue
        match = CPU_LIMIT_SUFFIX.search(trace.name)
        if match is None:
            continue
        base = trace.name[:match.start()]
        trace.hovertemplate = f"%{{y:.0f}} of {match.group(1)}m<extra>{base}</extra>"
        trace.name = base
    fig.update_layout(
        showlegend=False, height=PANEL_HEIGHT, margin=dict(PANEL_MARGIN),
        xaxis_domain=[0, 0.97],
    )
    return fig


def pin_x_range(figs: list[go.Figure]) -> list[float]:
    """Every panel shows the longest run's span, so one second lines up vertically."""
    spans = [fig.layout.xaxis.range for fig in figs if fig.layout.xaxis.range is not None]
    low = min(span[0] for span in spans)
    high = max(span[1] for span in spans)
    for fig in figs:
        fig.update_layout(xaxis_range=[low, high])
    return [low, high]


def decorate_slider(figs: list[go.Figure]) -> None:
    """The range slider and the x title sit on the last panel only."""
    for fig in figs[:-1]:
        fig.update_layout(xaxis_title_text="", margin_b=24)
    last = figs[-1]
    last.update_layout(
        xaxis_title_text=HOLD_CLOCK_TITLE,
        xaxis_rangeslider={"visible": True, "thickness": 0.06},
        height=PANEL_HEIGHT + SLIDER_EXTRA,
    )


def _union_order(item: tuple[tuple[str, str], go.Scatter]) -> tuple[int, int]:
    group, name = item[0]
    step = graphs_tool.COMPARE_EVENT_STEPS.index(name) if group == graphs_tool.EVENT_GROUP else 0
    return GROUP_ORDER.index(group), step


def series_union(figs: list[go.Figure]) -> dict[tuple[str, str], go.Scatter]:
    """Every (legendgroup, name) across the panels, grouped in legend order."""
    found: dict[tuple[str, str], go.Scatter] = {}
    for fig in figs:
        for trace in fig.data:
            found.setdefault((trace.legendgroup, trace.name), trace)
    return dict(sorted(found.items(), key=_union_order))


def assign_colors(figs: list[go.Figure], union: dict) -> dict[tuple[str, str], str]:
    """One colour per series, so a line looks the same in every panel and the legend.

    Plotly colours by trace position, and runs have different trace sets, so the
    default would give the same series different colours in different panels.
    Event lines keep the colour graphs_tool gave them.
    """
    colors = {}
    for index, (key, trace) in enumerate(union.items()):
        if key[0] == graphs_tool.EVENT_GROUP:
            colors[key] = trace.line.color
        else:
            colors[key] = PALETTE[index % len(PALETTE)]
    for fig in figs:
        for trace in fig.data:
            trace.line.color = colors[(trace.legendgroup, trace.name)]
    return colors


def legend_figure(union: dict, colors: dict) -> go.Figure:
    """A figure that draws nothing but the legend of the union of all panels."""
    fig = go.Figure()
    for (group, name), trace in union.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines", name=name,
            visible=True if group == graphs_tool.EVENT_GROUP else "legendonly",
            line={"width": 2, "color": colors[(group, name)]},
            legendgroup=group, meta=trace.meta,
            legendgrouptitle={"text": trace.legendgrouptitle.text, "font": {"color": "black"}},
        ))
    fig.update_layout(
        height=LEGEND_HEIGHT,
        margin={"t": 4, "r": 36, "b": 4, "l": 64},
        xaxis={"visible": False},
        yaxis={"visible": False},
        legend={"groupclick": "toggleitem", "tracegroupgap": 16, "orientation": "h",
                "x": 0, "xanchor": "left", "y": 1, "yanchor": "top",
                "font": {"size": 11}, "grouptitlefont": {"color": "black"}},
    )
    return fig
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python experiments/test_multi_graphs_tool.py -v`
Expected: all tests in `TestPanelFigure`, `TestNormalize`, `TestLegendFigure` PASS.

- [ ] **Step 5: Confirm graphs_tool is untouched**

Run: `git diff --stat -- experiments/graphs_tool.py`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "feat: add multi_graphs_tool panel figures and shared legend figure"
```

---

### Task 2: Page assembly and CLI (no page script yet)

**Files:**
- Modify: `experiments/multi_graphs_tool.py` (append)
- Modify: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: everything produced by Task 1; `graphs_tool.legend_html()`.
- Produces:
  - `out_path(run_dirs) -> Path`
  - `build_page(run_dirs) -> str` (full HTML text; Task 3 adds the script inside this function)
  - `write_page(run_dirs, path) -> None`
  - `main(argv=None) -> int`
  - element ids on the page: `panel-<i>`, `note-<i>`, `legend-graph`

- [ ] **Step 1: Write the failing tests**

Add to `experiments/test_multi_graphs_tool.py`, above the `if __name__` line:

```python
from test_hold_clock import E, iso, make_run  # noqa: E402


class TestPage(unittest.TestCase):
    def test_real_runs_give_panels_then_legend_then_code_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_a = make_run(Path(tmp) / "a")
            run_b = make_run(Path(tmp) / "b")
            (run_b / "retryguard.log").write_text(
                f"{iso(E + 31)}  frontend->checkoutservice  ON→OFF   rpr=2.10  "
                "consecutive_high=2  attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4\n",
                encoding="utf-8",
            )
            out = Path(tmp) / "multi.html"
            multi_graphs_tool.write_page([run_a, run_b], out)
            page = out.read_text(encoding="utf-8")
            single = Path(tmp) / "single.html"
            graphs_tool.write_html(graphs_tool.build_figure(run_a), single, run_a)
            single_size = len(single.read_text(encoding="utf-8"))
        panel0 = page.index('id="panel-0"')
        panel1 = page.index('id="panel-1"')
        legend = page.index('id="legend-graph"')
        key = page.index("Service codes, OFF→ON")
        self.assertLess(panel0, panel1)
        self.assertLess(panel1, legend)
        self.assertLess(legend, key)
        self.assertEqual(page.count("Plotly.newPlot("), 3)
        self.assertNotIn('id="panel-2"', page)
        self.assertIn("E3 burst", page)
        # One Plotly bundle, not one per figure.
        self.assertLess(len(page), 2 * single_size)

    def test_out_path_joins_names_and_disambiguates_repeats(self):
        path = multi_graphs_tool.out_path([Path("x/run_a"), Path("y/run_b"), Path("z/run_a")])
        self.assertEqual(path.parent, graphs_tool.OUT_DIR)
        self.assertEqual(path.name, "multi_run_a__run_b__run_a-3.html")

    def test_cli_needs_two_existing_runs(self):
        with self.assertRaises(SystemExit) as one:
            multi_graphs_tool.main(["only_one"])
        self.assertEqual(one.exception.code, 2)
        with self.assertRaises(SystemExit) as missing:
            multi_graphs_tool.main(["does_not_exist_a", "does_not_exist_b"])
        self.assertEqual(missing.exception.code, 2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python experiments/test_multi_graphs_tool.py TestPage -v`
Expected: FAIL with `AttributeError: module 'multi_graphs_tool' has no attribute 'write_page'`.

- [ ] **Step 3: Write the implementation**

Append to `experiments/multi_graphs_tool.py`:

```python
PAGE_STYLE = """
body { margin: 0; font-family: sans-serif; color: #222; }
h3.run { margin: 14px 16px 0; font-size: 14px; }
div.note { margin: 2px 16px 0; min-height: 15px; font-size: 12px; color: #777; }
"""


def out_path(run_dirs: list[Path]) -> Path:
    """multi_<names>.html. A repeated run folder name gets its position appended."""
    names: list[str] = []
    for index, run_dir in enumerate(run_dirs, start=1):
        name = Path(run_dir).name
        names.append(f"{name}-{index}" if name in names else name)
    return OUT_DIR / f"multi_{'__'.join(names)}.html"


def build_page(run_dirs: list[Path]) -> str:
    run_dirs = [Path(run_dir) for run_dir in run_dirs]
    figs = [panel_figure(run_dir) for run_dir in run_dirs]
    pin_x_range(figs)
    union = series_union(figs)
    colors = assign_colors(figs, union)
    decorate_slider(figs)
    legend = legend_figure(union, colors)

    parts = []
    for index, (run_dir, fig) in enumerate(zip(run_dirs, figs)):
        parts.append(f'<h3 class="run">{html.escape(run_label(run_dir))}</h3>')
        parts.append(f'<div id="note-{index}" class="note"></div>')
        parts.append(pio.to_html(
            fig, full_html=False, include_plotlyjs=True if index == 0 else False,
            div_id=f"panel-{index}",
        ))
    parts.append(pio.to_html(legend, full_html=False, include_plotlyjs=False, div_id="legend-graph"))
    parts.append(graphs_tool.legend_html())
    title = html.escape(" vs ".join(run_dir.name for run_dir in run_dirs))
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{PAGE_STYLE}</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )


def write_page(run_dirs: list[Path], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_page(run_dirs), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive hold-clock comparison of several runs, one panel each.")
    parser.add_argument("runs", nargs="+", help="Run folders (at least two)")
    args = parser.parse_args(argv)
    runs = [Path(run) for run in args.runs]
    if len(runs) < 2:
        parser.error("need at least two run folders")
    missing = [str(run) for run in runs if not run.is_dir()]
    if missing:
        parser.error("not a folder: " + ", ".join(missing))
    out = out_path(runs)
    write_page(runs, out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`json` is imported in the header but not used until Task 3; leave it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python experiments/test_multi_graphs_tool.py -v`
Expected: all tests PASS. If `test_real_runs_give_panels_then_legend_then_code_key` reports `Plotly.newPlot(` count other than 3, print `page.count("newPlot")` and adjust the string to the form Plotly 7.1.0 actually emits; the intent is one call per figure.

- [ ] **Step 5: Commit**

```bash
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "feat: assemble multi_graphs_tool page and CLI"
```

---

### Task 3: Legend drives every panel (visibility, right axes, events, shared y, notes)

**Files:**
- Modify: `experiments/multi_graphs_tool.py`
- Modify: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: `build_page`, element ids `panel-<i>`, `note-<i>`, `legend-graph`, trace `meta` (unit string, or `"event"`), `graphs_tool.COMPARE_AXIS`.
- Produces: `PAGE_JS` (a raw string with tokens `__PANEL_IDS__`, `__AXIS__`, `__X_PIN__`), `page_script(panel_count, x_pin) -> str`. Task 4 adds zoom linking to the same script.

Behaviour the script must have after this task:
- A legend item click toggles one trace in the legend figure, then every panel gets the matching visibility by `(legendgroup, name)`.
- A legend section title click toggles the whole group (all hidden -> show all, otherwise hide all).
- Right-hand axes show, hide, and pack exactly as in `graphs_tool` (same constants), applied to all panels together.
- Event names (annotations) follow the legend's event items.
- Each unit's y-range is `[0, max * 1.05]` over visible traces across all panels (`[0, 1]` if the max is not above 0), identical on every panel.
- `note-<i>` says `none in this run: <Group title> (n), ...` when a visible legend item is absent from that panel (event items excluded).
- The legend figure height fits its legend.

- [ ] **Step 1: Write the failing browser tests**

Add to `experiments/test_multi_graphs_tool.py`, above the `if __name__` line:

```python
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def two_synthetic_panels():
    """A: 300 s, Goodput peaks at 30, a rejection line. B: 600 s, Goodput peaks at 90,
    a retries-per-request line A lacks, and an ON→OFF event with a name on the line."""
    fig_a = synthetic([("locust", "Goodput", [10.0, 20.0, 30.0]),
                       ("rejection", "checkoutservice", [0.0, 0.5, 0.2])], 300)
    fig_b = synthetic([("locust", "Goodput", [30.0, 60.0, 90.0]),
                       ("rpr", "E3 frontend->checkoutservice", [0.0, 1.0, 2.0])],
                      600, events=("ON→OFF",))
    return fig_a, fig_b


class BrowserCase(unittest.TestCase):
    """Loads the page in Chromium and clicks the legend the way a person does."""

    def setUp(self):
        if sync_playwright is None:
            self.skipTest("playwright is not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        out = Path(self.tmp.name) / "multi.html"
        fig_a, fig_b = two_synthetic_panels()
        with mock.patch.object(graphs_tool, "compare_figure", side_effect=[fig_a, fig_b]):
            multi_graphs_tool.write_page(
                [Path("final/S2/both/run_a"), Path("final/S2/rg_only/run_b")], out)
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        browser = self.playwright.chromium.launch()
        self.addCleanup(browser.close)
        self.page = browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.goto(out.as_uri())
        self.page.wait_for_selector("#legend-graph .legend .traces")
        self.page.wait_for_function(
            "() => ['panel-0','panel-1','legend-graph'].every("
            "id => document.getElementById(id) && document.getElementById(id).data)"
        )

    def click_legend(self, label: str, title: bool) -> None:
        point = self.page.evaluate(
            """(args) => {
              const graph = document.getElementById('legend-graph');
              const row = [...graph.querySelectorAll('.legend .traces')].find(item => {
                const text = item.querySelector('text');
                if (!text || text.textContent !== args.label) return false;
                const isTitle = !item.querySelector('.legendtoggle');
                return args.title ? isTitle : !isTitle;
              });
              if (!row) return null;
              const text = row.querySelector('text');
              text.scrollIntoView({block: 'center', inline: 'center'});
              const box = text.getBoundingClientRect();
              return {x: box.x + box.width / 2, y: box.y + box.height / 2};
            }""",
            {"label": label, "title": title},
        )
        self.assertIsNotNone(point, f"missing legend text {label}")
        self.page.mouse.click(point["x"], point["y"])

    def visible(self, panel: int, name: str) -> bool:
        return self.page.evaluate(
            """(args) => document.getElementById('panel-' + args.panel).data
              .filter(t => t.name === args.name)
              .every(t => t.visible !== 'legendonly')""",
            {"panel": panel, "name": name},
        )

    def wait(self, expression: str, arg=None, timeout: int = 4000) -> None:
        self.page.wait_for_function(expression, arg=arg, timeout=timeout)

    def y_range(self, panel: int, axis: str = "yaxis"):
        return self.page.evaluate(
            "(args) => document.getElementById('panel-' + args.panel).layout[args.axis].range",
            {"panel": panel, "axis": axis},
        )


class TestLegendDrivesPanels(BrowserCase):
    def test_item_click_shows_the_line_in_every_panel_with_one_shared_y_range(self):
        self.assertFalse(self.visible(0, "Goodput"))
        self.assertFalse(self.visible(1, "Goodput"))
        self.click_legend("Goodput", title=False)
        self.wait("() => document.getElementById('panel-1').data"
                  ".every(t => t.name !== 'Goodput' || t.visible === true)")
        self.assertTrue(self.visible(0, "Goodput"))
        self.assertTrue(self.visible(1, "Goodput"))
        # Max over both runs is 90; the range is [0, 90 * 1.05] on both panels.
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.assertEqual(self.y_range(0), self.y_range(1))
        self.assertAlmostEqual(self.y_range(1)[1], 94.5, places=2)
        self.assertEqual(self.y_range(1)[0], 0)

    def test_section_title_toggles_the_whole_group_in_every_panel(self):
        self.click_legend("Goodput / RPS (req/s)", title=True)
        self.wait("() => document.getElementById('panel-0').data"
                  ".filter(t => t.legendgroup === 'locust').every(t => t.visible === true)")
        self.assertTrue(self.visible(1, "Goodput"))
        self.click_legend("Goodput / RPS (req/s)", title=True)
        self.wait("() => document.getElementById('panel-0').data"
                  ".filter(t => t.legendgroup === 'locust').every(t => t.visible === 'legendonly')")
        self.assertFalse(self.visible(1, "Goodput"))

    def test_right_axis_shows_on_every_panel_when_a_line_of_that_unit_is_on(self):
        self.assertFalse(self.page.evaluate(
            "() => document.getElementById('panel-0').layout.yaxis3.visible"))
        self.click_legend("checkoutservice", title=False)
        self.wait("() => document.getElementById('panel-1').layout.yaxis3.visible === true")
        self.assertTrue(self.page.evaluate(
            "() => document.getElementById('panel-0').layout.yaxis3.visible"))
        self.assertEqual(self.y_range(0, "yaxis3"), self.y_range(1, "yaxis3"))
        self.assertAlmostEqual(self.y_range(1, "yaxis3")[1], 0.525, places=3)

    def test_note_names_a_visible_series_the_run_lacks(self):
        self.assertEqual(self.page.inner_text("#note-0"), "")
        self.click_legend("E3 frontend->checkoutservice", title=False)
        self.wait("() => document.getElementById('note-0').textContent.length > 0")
        self.assertIn("none in this run", self.page.inner_text("#note-0"))
        self.assertIn("Retries per request (1)", self.page.inner_text("#note-0"))
        self.assertEqual(self.page.inner_text("#note-1"), "")

    def test_event_item_hides_the_names_on_the_lines(self):
        self.assertTrue(self.page.evaluate(
            "() => document.getElementById('panel-1').layout.annotations[0].visible !== false"))
        self.click_legend("ON→OFF", title=False)
        self.wait("() => document.getElementById('panel-1').layout.annotations[0].visible === false")
        self.click_legend("ON→OFF", title=False)
        self.wait("() => document.getElementById('panel-1').layout.annotations[0].visible === true")

    def test_legend_figure_shrinks_to_its_legend(self):
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        height = self.page.evaluate("() => document.getElementById('legend-graph').offsetHeight")
        self.assertGreater(height, 40)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python experiments/test_multi_graphs_tool.py TestLegendDrivesPanels -v`
Expected: FAIL (timeouts), because the page has no script yet. If playwright is missing the tests SKIP; install it first (`pip install playwright`, `python -m playwright install chromium`) so the check is real.

- [ ] **Step 3: Write the page script**

Append to `experiments/multi_graphs_tool.py`:

```python
PAGE_JS = r"""
<script>
(function () {
  var PANEL_IDS = __PANEL_IDS__;
  var AXIS = __AXIS__;
  var X_PIN = __X_PIN__;
  // A unit's axis stays hidden until one of its lines is on. Visible units pack
  // against the plot: the first on the right edge, the rest stepping outward.
  var RIGHT = ['ms', 'fraction', 'retries/request', 'millicores', 'retries', 'ticks'];
  var EVENTS = 'events';

  function start() {
    var legend = document.getElementById('legend-graph');
    var panels = PANEL_IDS.map(function (id) { return document.getElementById(id); });
    var ready = legend && legend.data && panels.every(function (panel) { return panel && panel.data; });
    if (!ready) { setTimeout(start, 50); return; }
    wire(legend, panels);
  }

  function wire(legend, panels) {
    var busy = false;

    function key(trace) { return trace.legendgroup + '||' + trace.name; }

    // The legend figure is the only place visibility is decided.
    function legendState() {
      var state = {};
      legend.data.forEach(function (trace) { state[key(trace)] = trace.visible !== 'legendonly'; });
      return state;
    }

    function axisUpdate() {
      var shown = {};
      legend.data.forEach(function (trace) {
        if (!AXIS[trace.meta] || AXIS[trace.meta] === 'yaxis') return;
        if (trace.visible !== 'legendonly') shown[trace.meta] = true;
      });
      var active = RIGHT.filter(function (unit) { return shown[unit]; });
      var edge = active.length ? 1 - 0.07 * active.length : 0.97;
      var update = {'xaxis.domain[1]': Math.max(0.6, edge)};
      RIGHT.forEach(function (unit) {
        var name = AXIS[unit];
        var place = active.indexOf(unit);
        update[name + '.visible'] = place !== -1;
        if (place !== -1) {
          update[name + '.anchor'] = 'free';
          update[name + '.side'] = 'right';
          update[name + '.position'] = edge + 0.07 * place;
        }
      });
      return update;
    }

    // One range per unit, from the largest visible value in any panel, so a
    // height on one panel means the same thing on every other panel.
    function yRanges(state) {
      var top = {};
      panels.forEach(function (panel) {
        panel.data.forEach(function (trace) {
          if (!state[key(trace)] || !AXIS[trace.meta]) return;
          var max = top[trace.meta];
          Array.prototype.forEach.call(trace.y || [], function (value) {
            if (typeof value === 'number' && isFinite(value) && (max === undefined || value > max)) max = value;
          });
          if (max !== undefined) top[trace.meta] = max;
        });
      });
      var update = {};
      Object.keys(top).forEach(function (unit) {
        update[AXIS[unit] + '.range'] = [0, top[unit] > 0 ? top[unit] * 1.05 : 1];
      });
      return update;
    }

    function showNotes(state) {
      panels.forEach(function (panel, index) {
        var present = {};
        panel.data.forEach(function (trace) { present[key(trace)] = true; });
        var missing = {};
        legend.data.forEach(function (trace) {
          if (trace.legendgroup === EVENTS || !state[key(trace)] || present[key(trace)]) return;
          var title = trace.legendgrouptitle.text;
          missing[title] = (missing[title] || 0) + 1;
        });
        var parts = Object.keys(missing).map(function (title) { return title + ' (' + missing[title] + ')'; });
        document.getElementById('note-' + index).textContent =
          parts.length ? 'none in this run: ' + parts.join(', ') : '';
      });
    }

    function apply() {
      var state = legendState();
      var shared = Object.assign({}, axisUpdate(), yRanges(state));
      busy = true;
      var jobs = panels.map(function (panel) {
        var visible = panel.data.map(function (trace) { return state[key(trace)] ? true : 'legendonly'; });
        var update = Object.assign({}, shared);
        // The names on the event lines are annotations. They follow the legend.
        update.annotations = (panel.layout.annotations || []).map(function (item) {
          var k = EVENTS + '||' + item.name;
          if (!Object.prototype.hasOwnProperty.call(state, k)) return item;
          var copy = Object.assign({}, item);
          copy.visible = state[k];
          return copy;
        });
        return Plotly.restyle(panel, {visible: visible}).then(function () {
          return Plotly.relayout(panel, update);
        });
      });
      return Promise.all(jobs).then(function () { busy = false; showNotes(state); });
    }

    // Item click: toggle that one legend trace, then redraw the panels.
    legend.on('plotly_legendclick', function (event) {
      var trace = event.fullData[event.curveNumber];
      var show = trace.visible === 'legendonly';
      Plotly.restyle(legend, {visible: show ? true : 'legendonly'}, [event.curveNumber]).then(apply);
      return false;
    });

    // Title click: toggle the whole group. A title is the legend row without a
    // toggle rect; an axis title can use the same words, so only legend rows count.
    var titleOf = {};
    legend.data.forEach(function (trace) { titleOf[trace.legendgrouptitle.text] = trace.legendgroup; });
    legend.addEventListener('mousedown', function (event) {
      var text = event.target.closest ? event.target.closest('text') : null;
      if (!text || !text.closest('.legend')) return;
      var row = text.parentNode;
      if (!row || row.querySelector('.legendtoggle')) return;
      var group = titleOf[text.textContent];
      if (!group) return;
      event.stopPropagation();
      var indices = [];
      legend.data.forEach(function (trace, index) { if (trace.legendgroup === group) indices.push(index); });
      var allHidden = indices.every(function (index) { return legend.data[index].visible === 'legendonly'; });
      Plotly.restyle(legend, {visible: allHidden ? true : 'legendonly'}, indices).then(apply);
    }, true);

    // Plotly greys a title once every item in its group is hidden. Repaint black.
    function keepTitles() {
      legend.querySelectorAll('.legend .traces').forEach(function (row) {
        if (row.querySelector('.legendtoggle')) return;
        var node = row.querySelector('text');
        if (!node) return;
        node.style.fill = 'black';
        node.style.fillOpacity = '1';
      });
    }

    // The legend is a row of columns that wrap with the window. Size the figure
    // to the legend so there is no empty band and Plotly never scrolls it.
    var lastHeight = 0;
    function fitLegend() {
      var node = legend.querySelector('.legend');
      if (!node) return;
      var height = Math.ceil(node.getBoundingClientRect().height) + 16;
      if (Math.abs(height - lastHeight) < 3) return;
      lastHeight = height;
      legend.parentElement.style.height = height + 'px';
      legend.style.height = height + 'px';
      Plotly.relayout(legend, {height: height});
    }

    legend.on('plotly_afterplot', function () { keepTitles(); fitLegend(); });
    new MutationObserver(keepTitles).observe(legend, {subtree: true, attributes: true, attributeFilter: ['style']});
    keepTitles();
    fitLegend();
    setTimeout(fitLegend, 0);
    showNotes(legendState());
  }
  start();
})();
</script>
"""


def page_script(panel_count: int, x_pin: list[float]) -> str:
    return (
        PAGE_JS
        .replace("__PANEL_IDS__", json.dumps([f"panel-{i}" for i in range(panel_count)]))
        .replace("__AXIS__", json.dumps(graphs_tool.COMPARE_AXIS))
        .replace("__X_PIN__", json.dumps(x_pin))
    )
```

Then change `build_page` so it keeps the pinned range and adds the script. Replace

```python
    pin_x_range(figs)
```

with

```python
    x_pin = pin_x_range(figs)
```

and replace

```python
        + "".join(parts)
        + "</body></html>"
```

with

```python
        + "".join(parts)
        + page_script(len(figs), x_pin)
        + "</body></html>"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python experiments/test_multi_graphs_tool.py -v`
Expected: every test PASS, including all of `TestLegendDrivesPanels`.

If `test_right_axis_...` fails on the `yaxis3` range, check which unit `rejection` maps to in `graphs_tool.UNIT` (`"fraction"` -> `yaxis3`) and that the synthetic trace used `trace_yaxis`. If a click does not register on the legend, open the saved page by hand (see Task 5, step 3) and confirm the legend renders; the click helper is the same one `test_graphs_tool.py` uses.

- [ ] **Step 5: Commit**

```bash
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "feat: drive every multi_graphs_tool panel from the shared legend"
```

---

### Task 4: Linked zoom (x and y)

**Files:**
- Modify: `experiments/multi_graphs_tool.py` (inside `PAGE_JS`)
- Modify: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: `PAGE_JS` from Task 3 (`wire`, `busy`, `yRanges`, `legendState`, `X_PIN`).
- Produces: nothing new for later tasks.

Behaviour: a manual x zoom, pan, or range-slider move on any panel sets the same x range on every other panel. A manual y range on a panel's unit axis sets the same range on every other panel. A double-click reset (`xaxis.autorange` or `yaxisN.autorange` in the relayout event) sets every panel, including the one clicked, back to the pinned x range and the shared y ranges. The `busy` flag stops panels echoing each other.

- [ ] **Step 1: Write the failing tests**

Add to `experiments/test_multi_graphs_tool.py`, above the `if __name__` line:

```python
class TestLinkedZoom(BrowserCase):
    def x_range(self, panel: int):
        return self.page.evaluate(
            "(i) => document.getElementById('panel-' + i).layout.xaxis.range", panel)

    def test_panels_start_on_the_longest_runs_span(self):
        self.assertEqual(list(self.x_range(0)), [0, 600])
        self.assertEqual(list(self.x_range(1)), [0, 600])

    def test_x_zoom_on_one_panel_moves_the_others(self):
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-0'), {'xaxis.range': [10, 40]})")
        self.wait("() => { const r = document.getElementById('panel-1').layout.xaxis.range;"
                  " return r && r[0] === 10 && r[1] === 40; }")

    def test_y_zoom_on_one_panel_moves_the_others(self):
        self.click_legend("Goodput", title=False)
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-1'), {'yaxis.range': [0, 50]})")
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && r[0] === 0 && r[1] === 50; }")

    def test_autorange_reset_returns_every_panel_to_the_pinned_x_and_shared_y(self):
        self.click_legend("Goodput", title=False)
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-0'), {'xaxis.range': [10, 40]})")
        self.wait("() => document.getElementById('panel-1').layout.xaxis.range[0] === 10")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-1'),"
            " {'xaxis.autorange': true, 'yaxis.autorange': true})")
        self.wait("() => { const a = document.getElementById('panel-0').layout.xaxis.range;"
                  " const b = document.getElementById('panel-1').layout.xaxis.range;"
                  " return a[0] === 0 && a[1] === 600 && b[0] === 0 && b[1] === 600; }")
        self.wait("() => { const r = document.getElementById('panel-1').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python experiments/test_multi_graphs_tool.py TestLinkedZoom -v`
Expected: `test_panels_start_on_the_longest_runs_span` PASSes; the other three FAIL on timeout, because nothing mirrors zoom yet.

- [ ] **Step 3: Write the implementation**

In `PAGE_JS`, immediately after the line `legend.on('plotly_afterplot', function () { keepTitles(); fitLegend(); });` block's `new MutationObserver(...)` line and before `keepTitles();` (inside `wire`), insert:

```js
    // Zoom and pan are mirrored between panels. busy stops a panel echoing a
    // change it just received; apply() sets it too, since it relayouts every panel.
    panels.forEach(function (panel) {
      panel.on('plotly_relayout', function (event) {
        if (busy) return;
        var update = {};
        var reset = false;
        Object.keys(event).forEach(function (name) {
          var axis = /^(yaxis\d*)\.range(\[\d\])?$/.exec(name);
          if (/^xaxis\.range(\[\d\])?$/.test(name)) {
            update['xaxis.range'] = panel.layout.xaxis.range.slice();
          } else if (name === 'xaxis.autorange' && event[name]) {
            update['xaxis.range'] = X_PIN.slice();
            reset = true;
          } else if (axis) {
            update[axis[1] + '.range'] = panel.layout[axis[1]].range.slice();
          } else if (/^yaxis\d*\.autorange$/.test(name) && event[name]) {
            reset = true;
          }
        });
        if (reset) Object.assign(update, yRanges(legendState()));
        if (!Object.keys(update).length) return;
        // A reset also has to fix the panel that was clicked, which autoranged itself.
        var targets = reset ? panels : panels.filter(function (other) { return other !== panel; });
        busy = true;
        Promise.all(targets.map(function (other) { return Plotly.relayout(other, update); }))
          .then(function () { busy = false; });
      });
    });
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python experiments/test_multi_graphs_tool.py -v`
Expected: all tests PASS.

If `test_autorange_reset_...` fails because the clicked panel keeps autorange: with `yRanges` returning ranges only for visible units, a reset with nothing visible leaves that panel on autorange, which is correct. In this test Goodput is on, so `yaxis.range` must be set on both panels; check that the relayout event for the clicked panel contains `yaxis.autorange` (log `Object.keys(event)` in the browser console).

- [ ] **Step 5: Commit**

```bash
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "feat: link x and y zoom across multi_graphs_tool panels"
```

---

### Task 5: Check on real holds, then document

**Files:**
- Modify: `Guides and Info/GRAPHS-TOOL.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md`

**Interfaces:** none. This task ends the work.

- [ ] **Step 1: Run the full suite for both tools**

Run: `python experiments/test_multi_graphs_tool.py -v; python experiments/test_graphs_tool.py -v`
Expected: both PASS. `test_graphs_tool.py` passing confirms the single-run tool is unaffected.

- [ ] **Step 2: Build a page from three real holds**

List the holds, pick three of the same scenario that differ in controller variant:

```powershell
Get-ChildItem "experiments/results/final results/S2_sustained_overload_burst" -Directory | ForEach-Object { Get-ChildItem $_.FullName -Directory | Select-Object -First 2 -ExpandProperty FullName }
```

Run (replace the three paths with ones listed, one each from `both`, `rg_only`, `tf_only` where they exist):

```powershell
python experiments/multi_graphs_tool.py "<both run>" "<rg_only run>" "<tf_only run>"
```

Expected: prints `experiments/explore_out/multi_....html` and exits 0. If a path is longer than Windows allows, shorten by choosing runs with shorter names or report it; do not add truncation without asking.

- [ ] **Step 3: Check the page by eye**

Open the printed file in a browser and confirm each of these. Report any that fail instead of patching around them:

1. Three panels stack, each with its run label above it, then the legend, then the E/V key.
2. Every line is off at first; event lines are on.
3. Clicking `Goodput` shows it on all three panels at the same y-scale.
4. A `tf_only` run shows `none in this run: ...` when an RetryGuard-only series (for example Cumulative retries) is on.
5. Zooming one panel moves the other two; the range slider under the last panel moves all three.
6. CPU lines are named by service only; hovering a CPU line shows `... of <limit>m`.
7. The slider on the last panel draws correctly with the right-hand axes. If it does not, tell the user and propose dropping `decorate_slider`'s slider (keep the x title).

- [ ] **Step 4: Document the tool**

Append to `Guides and Info/GRAPHS-TOOL.md`:

```markdown

## multi_graphs_tool: several holds, one legend

```powershell
python experiments/multi_graphs_tool.py "<run_dir>" "<run_dir>" ["<run_dir>" ...]
```

Two or more holds from `experiments/results/final results/` (S1–S4). The page is `experiments/explore_out/multi_<run names>.html` (git-ignored, offline). Built from [2026-10-14-multi-graphs-tool-design.md](../docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md).

Top to bottom: one comparison panel per run (the run label sits above it), then one legend, then the E/V code key. The legend is the only control. A click on a legend item or a section title changes every panel, so all panels always show the same metrics. Everything starts off except the RetryGuard event lines.

- **x** is linked. Zoom, pan, or the range slider (under the last panel) on one panel moves all of them. t = 0 is each run's own hold clock, and every panel shows the longest run's span, so a shorter run has empty space on the right.
- **y** is shared per unit. The range is 0 to 1.05 times the largest visible value in any panel, so equal heights mean equal values across runs. Turning on a line that peaks high in one run rescales all panels. A manual y range on one panel is copied to the others.
- **Names are the same in every panel.** CPU lines carry the service name only; the limit is in the hover (`… of 1150m`). The same series has the same colour in every panel.
- **"none in this run"** above a panel means a line you turned on does not exist in that run (for example RetryGuard edges on a `tf_only` run). It is not a zero.
- Each panel draws its own run's RetryGuard events and names. Hover over a name for the detail.

Not in this page: the nine stacked panels, `--all`, S5/S6/`campaign_48/`/`august_38/`.
```

In `AGENTS.md`, under the repo-layout block, add after the `graphs_tool.py` line:

```
 multi_graphs_tool.py ← **multi_graphs_tool.** Two or more `final results/` runs as stacked comparison panels under one shared legend. See [GRAPHS-TOOL.md](Guides%20and%20Info/GRAPHS-TOOL.md) "multi_graphs_tool". Command: `python experiments/multi_graphs_tool.py "<run_dir>" "<run_dir>"`
```

and in the "Where to find metrics" table, add after the **graphs_tool** row:

```
| **multi_graphs_tool** — compare 2+ runs | `python experiments/multi_graphs_tool.py "<run_dir>" "<run_dir>" ["<run_dir>" ...]`. One comparison panel per run, one shared legend, linked x, shared y per unit. Writes `experiments/explore_out/multi_<names>.html` (git-ignored). Use graphs_tool for the nine-panel view of one run |
```

- [ ] **Step 5: Amend the spec**

In `docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md`, replace the bullet under "Shape" that begins `- \`graphs_tool.py\` keeps its behavior` with:

```markdown
- `graphs_tool.py` is not modified. Its legend stays above its own comparison chart. `multi_graphs_tool.py` calls `graphs_tool.compare_figure` for each run and post-processes the figure, and carries its own page script. This replaces the earlier idea of extracting `graphs_tool`'s legend JS: extraction risked changing single-run pages for no gain.
```

and replace the second bullet under "Open points for the implementation plan" with:

```markdown
- Resolved in the plan: a click on the legend-only figure rebuilds every panel's `visible` array from the legend's state by `(legendgroup, name)`, then relayouts axes, event names, and y ranges in one call per panel.
```

and its first bullet with:

```markdown
- Resolved in the plan: a `busy` flag is set while the page relayouts panels, so a panel ignores the relayout events its own update causes.
```

Also change the Testing line `Extend the pattern in \`experiments/test_graphs_tool.py\`, in a new` to read `Same pattern as \`experiments/test_graphs_tool.py\`, in a new`, and add under it: `Browser tests use synthetic figures patched in for \`graphs_tool.compare_figure\`, so they do not depend on run data; one test uses real synthetic runs from \`test_hold_clock.make_run\`.`

- [ ] **Step 6: Commit**

```bash
git add "Guides and Info/GRAPHS-TOOL.md" AGENTS.md docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md docs/superpowers/plans/2026-10-14-multi-graphs-tool.md
git commit -m "docs: document multi_graphs_tool and record the design deviation"
```

---

## Self-review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| N >= 2 runs, one panel each, run header (scenario/variant/run) | 1 (`run_label`), 2 (`build_page`, `main`) |
| Page order: panels, legend, code key | 2 (`test_real_runs_give_panels_then_legend_then_code_key`) |
| Output name `multi_<names>.html`, offline, one Plotly bundle | 2 (`out_path`, size assertion) |
| Imports series building from graphs_tool, graphs_tool unchanged | 1 (`panel_figure`, step 5 diff check), 5 (suite) |
| Shared Plotly legend, titles black, items off, events on | 1 (`legend_figure`), 3 (`keepTitles`, title/item click) |
| Section title toggles group, item toggles one | 3 (tests 1 and 2) |
| Identical names, CPU plain name with limit in hover | 1 (`panel_figure`) |
| Right axes together on all panels | 3 (`axisUpdate`, test 3) |
| x linked, pinned to longest run | 1 (`pin_x_range`), 4 |
| y shared per unit, recomputed per toggle, manual y-zoom copied | 3 (`yRanges`), 4 |
| Events per panel, names follow legend | 3 (test 5) |
| "none in this run" | 3 (`showNotes`, test 4) |
| Slider on last panel | 1 (`decorate_slider`), 5 (visual check, fallback named) |
| Tests listed in spec | 1–4 |
| First real check on three holds | 5 |

**Placeholder scan:** no TBD/TODO; every code step carries the code.

**Type and name consistency:** `series_union` keys are `(legendgroup, name)` in Python and `legendgroup + '||' + name` in JS; `assign_colors(figs, union)` returns the dict `legend_figure(union, colors)` takes; `pin_x_range` returns the list `page_script` receives as `x_pin`; element ids `panel-<i>`, `note-<i>`, `legend-graph` are the same in `build_page`, the script, and the tests; `HOLD_CLOCK_TITLE` is defined in `multi_graphs_tool.py` and the Task 1 test reads it there.

**Known judgement calls to confirm with the user before or during execution**
- The spec's "extract and reuse `graphs_tool` JS" became "fresh script, `graphs_tool.py` untouched" (recorded in Task 5).
- Event-line hover uses Plotly's native annotation hover; `graphs_tool`'s proximity tooltip around the line is not copied (not in the spec).
- Run folders with identical names get `-<position>` appended to the output file name only.
