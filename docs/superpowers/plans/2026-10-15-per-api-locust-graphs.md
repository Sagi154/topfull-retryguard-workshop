# Per-API Locust lines on the graph pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw each Locust entry API's goodput, offered RPS, and P95 on the single-run graphs page and the multi-run graphs page, inside the existing Goodput / RPS and P95 sections.

**Architecture:** `run_timeline.locust_frames` already puts `locust.<api>.Goodput`, `locust.<api>.RPS`, and `locust.<api>.Latency95` on the per-second view for `getproduct`, `postcheckout`, `getcart`, `postcart`, and `emptycart`. `graphs_tool.line_specs` is the only series list both pages use. Append those columns there, after the series that exist today, with their own names and colours. `multi_graphs_tool` keeps building panels from `graphs_tool.compare_figure`; its colour assignment skips the new names so every series that exists today keeps the palette slot it has now. `run_timeline.panel_columns` stays the totals-only list, so `timeline.png` does not gain these lines.

**Tech Stack:** Python, pandas, Plotly, unittest. Tests run with `python -m pytest`.

## Global Constraints

- Touch only `experiments/graphs_tool.py`, `experiments/multi_graphs_tool.py`, `experiments/test_graphs_tool.py`, `experiments/test_multi_graphs_tool.py`, and `Guides and Info/GRAPHS-TOOL.md`.
- Do not modify `experiments/run_timeline.py`. `panel_columns` stays totals-only. `timeline.png` does not gain per-API lines.
- Do not rename the existing traces. Totals stay `Goodput`, `RPS`, and `Latency95`.
- Do not change the default visibility of any existing trace. On the nine stacked panels the new lines are on, because that section is already on. On the comparison chart and on the multi page every non-event line still starts off, including the new ones. Clicking the section title turns the new lines on and off with the totals, because they share the group.
- Append the new traces after the existing `line_specs` traces. Give each new trace an explicit colour. Do not insert them between existing traces. Plotly paints an uncoloured line from its index in `fig.data`, and an insertion in the middle would recolour the lines that are already on the page.
- API order is `analysis_score.APIS`: `getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`. A missing `{api}.csv` omits that API's three lines. Do not draw `Latency99`. Do not draw `Fail`.
- One colour per API, shared by that API's Goodput, RPS, and P95. API RPS is dashed. API Goodput and API P95 are solid. Totals stay solid and uncoloured.
- Do not change legend JavaScript, figure height, axis layout, hover mode, or the `--all` quiet-line rule. The new lines are not part of that rule: a column that exists is listed even when every value is 0.
- The user checks the pages by eye. Do not open a browser to approve the picture. The existing Playwright legend-click tests stay the click regression gate. Skip them only when Playwright is not installed; that skip already exists.

---

## File structure

- `experiments/graphs_tool.py` — names, colours, dash, and the extra `line_specs` entries. Both pages read this list.
- `experiments/multi_graphs_tool.py` — `assign_colors` only. A per-API name takes `API_LINE_COLOR` and does not consume a `PALETTE` slot.
- `experiments/test_graphs_tool.py` — the series list, the colours, and a guard that `panel_columns` is unchanged.
- `experiments/test_multi_graphs_tool.py` — palette indices with a per-API name sitting between two existing series.
- `Guides and Info/GRAPHS-TOOL.md` — what the two sections now contain.

`experiments/multi_graphs_tool.py` does not read CSVs. A run that lacks one API file simply has no trace of that name. The shared legend still lists the name when another run has it, and that panel already shows "none in this run" for a turned-on line it does not have.

## Task 1: Add the per-API series to graphs_tool

**Files:**
- Modify: `experiments/graphs_tool.py` (import, new helpers after `trace_name`, `line_specs`, the two `line =` assignments in `build_figure` and `compare_figure`)
- Modify: `experiments/test_graphs_tool.py` (new test class after `TestLineSpecs`)
- Test: `experiments/test_graphs_tool.py`

**Interfaces:**
- Consumes: `analysis_score.APIS` (`tuple[str, ...]`), `run_timeline.panel_columns(view, show_all=False) -> dict[str, list[str]]`, existing `line_specs(view, show_all=False, limits=None) -> list[tuple[str, str, str, object]]` of `(legendgroup, column, name, visible)`.
- Produces:
  - `API_LINE_COLOR: dict[str, str]` keyed by API name.
  - `api_of(name: str) -> str | None`
  - `per_api_specs(view: pd.DataFrame) -> list[tuple[str, str, str, bool]]`
  - `style_line(name: str, step: bool, width: float) -> dict`
  - `line_specs` returns the same tuples as today, then the per-API tuples.

- [ ] **Step 1: Write the failing test**

Add this class to `experiments/test_graphs_tool.py` immediately after `TestLineSpecs`. `run_timeline` and `pandas` are already imported in that file.

```python
class TestPerApiLines(unittest.TestCase):
    def view(self):
        base = {
            "locust.total.Goodput": [10.0, 12.0],
            "locust.total.RPS": [11.0, 13.0],
            "locust.total.Latency95": [40.0, 50.0],
            "locust.getproduct.Goodput": [8.0, 9.0],
            "locust.getproduct.RPS": [8.0, 9.0],
            "locust.getproduct.Latency95": [30.0, 35.0],
            "locust.emptycart.Goodput": [0.0, 0.0],
            "locust.emptycart.RPS": [0.0, 0.0],
            "locust.emptycart.Latency95": [0.0, 0.0],
            "locust.getcart.Latency99": [0.0, 0.0],
        }
        return pd.DataFrame(base)

    def test_specs_keep_totals_then_append_each_api(self):
        specs = graphs_tool.line_specs(self.view())
        locust = [(column, name, visible) for key, column, name, visible in specs if key == "locust"]
        p95 = [(column, name, visible) for key, column, name, visible in specs if key == "p95"]
        self.assertEqual(locust[:2], [
            ("locust.total.Goodput", "Goodput", True),
            ("locust.total.RPS", "RPS", True),
        ])
        self.assertEqual(locust[2:], [
            ("locust.getproduct.Goodput", "getproduct Goodput", True),
            ("locust.emptycart.Goodput", "emptycart Goodput", True),
            ("locust.getproduct.RPS", "getproduct RPS", True),
            ("locust.emptycart.RPS", "emptycart RPS", True),
        ])
        self.assertEqual(p95, [
            ("locust.total.Latency95", "Latency95", True),
            ("locust.getproduct.Latency95", "getproduct P95", True),
            ("locust.emptycart.Latency95", "emptycart P95", True),
        ])
        self.assertNotIn("locust.getcart.Latency99", [spec[1] for spec in specs])

    def test_totals_stay_ahead_of_the_new_traces(self):
        specs = graphs_tool.line_specs(self.view())
        names = [spec[2] for spec in specs]
        self.assertLess(names.index("Latency95"), names.index("getproduct Goodput"))
        self.assertLess(names.index("RPS"), names.index("getproduct Goodput"))

    def test_a_zero_api_is_still_listed_and_quiet_rules_stay(self):
        view = self.view()
        view["inbound.cartservice.rejection"] = [0.0, 0.0]
        quiet = {spec[1]: spec for spec in graphs_tool.line_specs(view)}
        self.assertEqual(quiet["locust.emptycart.Goodput"][3], True)
        self.assertEqual(quiet["inbound.cartservice.rejection"][3], "legendonly")

    def test_timeline_panels_stay_totals_only(self):
        panels = run_timeline.panel_columns(self.view())
        self.assertEqual(panels["locust"], ["locust.total.Goodput", "locust.total.RPS"])
        self.assertEqual(panels["p95"], ["locust.total.Latency95"])

    def test_style_line_colours_an_api_and_dashes_only_its_rps(self):
        self.assertIsNone(graphs_tool.api_of("Goodput"))
        self.assertIsNone(graphs_tool.api_of("Latency95"))
        self.assertIsNone(graphs_tool.api_of("RPS"))
        self.assertEqual(graphs_tool.api_of("getproduct Goodput"), "getproduct")
        goodput = graphs_tool.style_line("getproduct Goodput", step=False, width=1.2)
        rps = graphs_tool.style_line("getproduct RPS", step=False, width=1.4)
        p95 = graphs_tool.style_line("getproduct P95", step=False, width=1.2)
        total = graphs_tool.style_line("Goodput", step=False, width=1.2)
        self.assertEqual(goodput["color"], graphs_tool.API_LINE_COLOR["getproduct"])
        self.assertEqual(rps["color"], goodput["color"])
        self.assertEqual(p95["color"], goodput["color"])
        self.assertNotIn("dash", goodput)
        self.assertNotIn("dash", p95)
        self.assertEqual(rps["dash"], "dash")
        self.assertEqual(rps["width"], 1.4)
        self.assertNotIn("color", total)
        self.assertNotIn("dash", total)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_graphs_tool.py::TestPerApiLines -v`

Expected: FAIL. `graphs_tool.api_of` is missing, and `line_specs` does not yet return `getproduct Goodput`.

- [ ] **Step 3: Write the implementation**

In `experiments/graphs_tool.py`, add `import analysis_score` next to the other local imports (after `import run_timeline`).

Add this block immediately after `trace_name`:

```python
API_LINE_COLOR = {
    "getproduct": "#1f77b4",
    "postcheckout": "#ff7f0e",
    "getcart": "#2ca02c",
    "postcart": "#d62728",
    "emptycart": "#9467bd",
}


def api_of(name: str) -> str | None:
    api, _, label = name.rpartition(" ")
    if api in analysis_score.APIS and label in ("Goodput", "RPS", "P95"):
        return api
    return None


def per_api_specs(view: pd.DataFrame) -> list[tuple[str, str, str, bool]]:
    """Goodput, then RPS, then P95, one line per API file that is on the view."""
    specs = []
    for key, column_name, label in (
        ("locust", "Goodput", "Goodput"),
        ("locust", "RPS", "RPS"),
        ("p95", "Latency95", "P95"),
    ):
        for api in analysis_score.APIS:
            column = f"locust.{api}.{column_name}"
            if column in view.columns:
                specs.append((key, column, f"{api} {label}", True))
    return specs


def style_line(name: str, step: bool, width: float) -> dict:
    line = {"width": width, "shape": "hv"} if step else {"width": width}
    api = api_of(name)
    if api is None:
        return line
    line["color"] = API_LINE_COLOR[api]
    if name.endswith(" RPS"):
        line["dash"] = "dash"
    return line
```

At the end of `line_specs`, after the `PANEL_KEYS` loop and before `return specs`, add:

```python
    specs.extend(per_api_specs(view))
```

In `build_figure`, replace

```python
        line = {"width": 1.2, "shape": "hv"} if step else {"width": 1.2}
```

with

```python
        line = style_line(name, step, 1.2)
```

In `compare_figure`, replace

```python
        line = {"width": 1.4, "shape": "hv"} if step else {"width": 1.4}
```

with

```python
        line = style_line(name, step, 1.4)
```

Leave the SLO-miss trace, the event traces, and the heatmap on their current line dicts. `compare_figure` already forces `visible="legendonly"` on every `line_specs` entry, so the new comparison-chart lines start off.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest experiments/test_graphs_tool.py::TestPerApiLines experiments/test_graphs_tool.py::TestLineSpecs -v`

Expected: PASS. `TestLineSpecs` still sees `Goodput` as the name of `locust.total.Goodput`, and a quiet rejection line stays `legendonly`.

- [ ] **Step 5: Commit**

```powershell
git add experiments/graphs_tool.py experiments/test_graphs_tool.py
git commit -m "Add per-API Locust goodput, RPS, and P95 to the graphs series list."
```

## Task 2: Keep multi-page colours on their current palette slots

**Files:**
- Modify: `experiments/multi_graphs_tool.py` (`assign_colors` only)
- Modify: `experiments/test_multi_graphs_tool.py` (new test on `TestNormalize`)
- Test: `experiments/test_multi_graphs_tool.py`

**Interfaces:**
- Consumes: `graphs_tool.api_of(name: str) -> str | None` and `graphs_tool.API_LINE_COLOR` from Task 1. `series_union(figs) -> dict[tuple[str, str], go.Scatter]`. `PALETTE` in `multi_graphs_tool`.
- Produces: `assign_colors(figs, union) -> dict[tuple[str, str], str]` with the same signature. For a non-event, non-API series, the colour is `PALETTE[i]` where `i` counts only those series, in union order. A per-API series uses `API_LINE_COLOR[api_of(name)]` and does not increment `i`.

- [ ] **Step 1: Write the failing test**

Add this method to `TestNormalize` in `experiments/test_multi_graphs_tool.py`:

```python
    def test_per_api_names_do_not_take_a_palette_slot(self):
        figs = [synthetic([
            ("locust", "Goodput", [1.0]),
            ("locust", "RPS", [1.0]),
            ("locust", "getproduct Goodput", [1.0]),
            ("locust", "getproduct RPS", [1.0]),
            ("p95", "Latency95", [5.0]),
            ("p95", "getproduct P95", [5.0]),
            ("rejection", "checkoutservice", [0.1]),
        ], 10)]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("locust", "Goodput")], multi_graphs_tool.PALETTE[0])
        self.assertEqual(colors[("locust", "RPS")], multi_graphs_tool.PALETTE[1])
        self.assertEqual(colors[("p95", "Latency95")], multi_graphs_tool.PALETTE[2])
        self.assertEqual(colors[("rejection", "checkoutservice")], multi_graphs_tool.PALETTE[3])
        api = graphs_tool.API_LINE_COLOR["getproduct"]
        self.assertEqual(colors[("locust", "getproduct Goodput")], api)
        self.assertEqual(colors[("locust", "getproduct RPS")], api)
        self.assertEqual(colors[("p95", "getproduct P95")], api)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_multi_graphs_tool.py::TestNormalize::test_per_api_names_do_not_take_a_palette_slot -v`

Expected: FAIL. Today `Latency95` is `PALETTE[4]` because `getproduct Goodput` and `getproduct RPS` each take a slot, and `getproduct Goodput` is a palette colour rather than `API_LINE_COLOR["getproduct"]`.

- [ ] **Step 3: Write the implementation**

Replace `assign_colors` in `experiments/multi_graphs_tool.py` with:

```python
def assign_colors(figs: list[go.Figure], union: dict) -> dict[tuple[str, str], str]:
    """One colour per series, so a line looks the same in every panel and the legend.

    Plotly colours by trace position, and runs have different trace sets, so the
    default would give the same series different colours in different panels.
    Event lines keep the colour graphs_tool gave them. A per-API Locust line
    uses that API's colour and does not consume a palette slot, so Goodput, RPS,
    Latency95, and every later series keep the slot they had before those lines
    existed.
    """
    colors = {}
    index = 0
    for key, trace in union.items():
        group, name = key
        if group == graphs_tool.EVENT_GROUP:
            colors[key] = trace.line.color
            continue
        api = graphs_tool.api_of(name)
        if api is not None:
            colors[key] = graphs_tool.API_LINE_COLOR[api]
            continue
        colors[key] = PALETTE[index % len(PALETTE)]
        index += 1
    for fig in figs:
        for trace in fig.data:
            trace.line.color = colors[(trace.legendgroup, trace.name)]
    return colors
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest experiments/test_multi_graphs_tool.py::TestNormalize -v`

Expected: PASS, including `test_same_series_gets_the_same_colour_in_every_panel` and `test_union_is_ordered_by_group_and_keyed_by_group_and_name`.

- [ ] **Step 5: Commit**

```powershell
git add experiments/multi_graphs_tool.py experiments/test_multi_graphs_tool.py
git commit -m "Keep existing multi-graph colours when per-API Locust lines are added."
```

## Task 3: Document the two sections

**Files:**
- Modify: `Guides and Info/GRAPHS-TOOL.md` (the panels table, the comparison-chart unit table, and one short paragraph under the panels table)
- Test: a text check, no new Python test

**Interfaces:**
- Consumes: the names and dash rule from Task 1.
- Produces: the guide a reader uses before opening a page.

- [ ] **Step 1: Update the panels table**

In the panels table, replace the Goodput / RPS and P95 rows with:

```markdown
| 1 | Goodput / RPS | Locust goodput and offered RPS. Totals, then each entry API. | `total.csv` and `{api}.csv` columns `Goodput`, `RPS` | req/s | totals and each API whose file is present |
| 2 | P95 | Shopper-visible latency. The total, then each entry API. | `total.csv` and `{api}.csv` column `Latency95` | ms | the total line and each API whose file is present |
```

`{api}` is `getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`.

- [ ] **Step 2: Add the reading paragraph**

Immediately after the panels table, before "A line going up means more of that quantity at that second.", add:

```markdown
**Per-API Locust lines.** The five entry APIs are `getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`. Legend names are `getproduct Goodput`, `getproduct RPS`, and `getproduct P95`, and the same shape for the other four. The total lines stay `Goodput`, `RPS`, and `Latency95`. `Latency95` is the unweighted mean of the five API P95s. `getproduct P95` is that API's own percentile. One colour belongs to one API, and that API's RPS line is dashed. An API whose CSV is missing has no line. `Latency99` is not drawn.
```

- [ ] **Step 3: Update the comparison-chart unit table**

Replace the req/s and ms rows with:

```markdown
| req/s | left, always there | Goodput, RPS, each API Goodput, each API RPS, TopFull cap |
| ms | right, while a P95 line is on | Latency95, each API P95 |
```

- [ ] **Step 4: Check the sentences are in the file**

Run: `python -c "from pathlib import Path; text = Path(r'Guides and Info/GRAPHS-TOOL.md').read_text(encoding='utf-8'); need = ['getproduct Goodput', 'getproduct RPS', 'getproduct P95', 'Latency99 is not drawn']; missing = [s for s in need if s not in text]; raise SystemExit(missing or 0)"`

Expected: exit code 0.

- [ ] **Step 5: Commit**

```powershell
git add "Guides and Info/GRAPHS-TOOL.md"
git commit -m "Document per-API goodput, RPS, and P95 on the graphs pages."
```

## Task 4: Regression gate, then stop for a visual check

**Files:**
- No further edits unless a test below fails because this change broke it. Fix that failure in the file the test points at. Do not restyle the page to make a picture look better.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: a green test run. HTML under `experiments/explore_out/` is generated only so the user can look. It is git-ignored. Do not commit it.

- [ ] **Step 1: Run the graph-tool tests**

Run:

```powershell
python -m pytest experiments/test_graphs_tool.py experiments/test_multi_graphs_tool.py experiments/test_run_timeline.py -v
```

Expected: PASS. Playwright tests skip with "playwright is not installed" when that package is absent. Any other failure is a regression. `test_run_timeline.py` must stay green without edits to `run_timeline.py`.

- [ ] **Step 2: Write two pages for the user to look at**

Use folders that are already on disk. Do not launch a hold.

```powershell
python experiments/graphs_tool.py "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4"
python experiments/multi_graphs_tool.py "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3" "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4"
```

Expected: the commands print the HTML paths and exit 0. Do not open the files to judge colours, crowding, or legend order.

- [ ] **Step 3: Stop**

Tell the user the two HTML paths and what to look for:

- Stacked page, Goodput / RPS panel: `Goodput` and `RPS` still drawn, plus ten API lines (five solid goodput, five dashed RPS). Same colour per API.
- Stacked page, P95 panel: `Latency95` still drawn, plus five solid `{api} P95` lines in those same colours.
- Comparison chart and multi page: those new names are in the two sections and start off. The section title turns them on with the totals.
- Other panels, event lines, and the code key look as they did before this change.

The user does the visual check. Do not change legend layout, height, or colours in response to a guess about how the page will look.

---

## Self-review

Spec coverage:

- Goodput per API and RPS per API in the Goodput / RPS section: Task 1 `per_api_specs` groups `locust`, and both figure builders place that group on the existing panel and the comparison chart. Multi reads `compare_figure`.
- P95 per API in the P95 section: same helper, group `p95`.
- Single and multi: one series list. Task 2 only stops the multi palette from shifting.
- Existing totals, timeline chart, quiet-line rule, and comparison-chart start-off rule: guarded by `test_timeline_panels_stay_totals_only`, `test_a_zero_api_is_still_listed_and_quiet_rules_stay`, and the unchanged `compare_figure` visibility override.
- Visual sign-off stays with the user: Task 4 step 3.

Placeholder scan: no TBD, no "write tests for the above", no "similar to Task N".

Type consistency: `api_of`, `API_LINE_COLOR`, `per_api_specs`, `style_line`, and `assign_colors(figs, union)` use the same names in Tasks 1 and 2. Series names are `{api} Goodput`, `{api} RPS`, and `{api} P95`.
