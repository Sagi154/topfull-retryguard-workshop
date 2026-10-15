"""graphs_tool: interactive Plotly view of one run on the hold clock.

    python experiments/graphs_tool.py <run_dir> [--all]

Writes experiments/explore_out/<run folder name>.html (not committed).
Design and decisions: docs/superpowers/specs/2026-10-13-interactive-run-explorer-design.md
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import hold_clock  # noqa: E402
import run_timeline  # noqa: E402
import topfull_cpu_quotas  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "explore_out"

# Attempts climbs (1→2, 2→3) are deliberately not vertical lines on the stacked
# panels: they show on the state strip and in hover text. To draw them there, add
# them here. See the spec, "Decisions". The comparison chart lists every step the
# run logged, climbs included, so each kind can be toggled on its own.
VERTICAL_LINE_STEPS = ("ON→OFF", "OFF→ON")
COMPARE_EVENT_STEPS = VERTICAL_LINE_STEPS + ("1→2", "2→3")
EVENT_GROUP = "events"

EDGE_NAMES = [f"{caller}->{target}" for caller, target in run_timeline.CONTROLLED_EDGES]
EDGE_CODES = {name: f"E{i}" for i, name in enumerate(EDGE_NAMES, start=1)}
SERVICE_NAMES = list(dict.fromkeys(target for _, target in run_timeline.CONTROLLED_EDGES))
SERVICE_CODES = {name: f"V{i}" for i, name in enumerate(SERVICE_NAMES, start=1)}

HOVER_FIELDS = ("metric", "rpr", "rejection", "from_attempts", "consecutive_low")
PANEL_KEYS = ("locust", "p95", "rejection", "rpr", "retry_cum", "caps", "overload_ticks", "cpu")


def marker_label(step: str, name: str, metric) -> str | None:
    if step == "ON→OFF":
        mode = "burst" if metric == "rpr_burst" else "normal"
        return f"{EDGE_CODES.get(name, name)} {mode}"
    if step == "OFF→ON":
        return SERVICE_CODES.get(name, name)
    return None


def markers(events: pd.DataFrame, steps: tuple[str, ...] = VERTICAL_LINE_STEPS) -> list[dict]:
    found = []
    for _, event in events.iterrows():
        step = event["step"]
        if step not in steps:
            continue
        lines = [f"{event['name']} {step}"]
        lines += [f"{key}={event[key]}" for key in HOVER_FIELDS if pd.notna(event[key])]
        found.append({
            "x": float(event["hold_s"]),
            "step": step,
            "name": event["name"],
            "label": marker_label(step, event["name"], event["metric"]),
            "hover": "<br>".join(lines),
            "color": run_timeline.SWITCH_COLORS.get(step, "gray"),
        })
    return found


def event_caption(marker: dict) -> str:
    """Short name drawn on a comparison-chart line, so the line can be hovered."""
    if marker["label"]:
        return marker["label"]
    code = EDGE_CODES.get(marker["name"], marker["name"])
    return f"{code} {marker['step']}"


def event_series(events: pd.DataFrame) -> list[tuple[str, list, list, list, str]]:
    """One vertical-line series per RetryGuard step that this run logged."""
    grouped: dict[str, list[dict]] = {}
    for marker in markers(events, steps=COMPARE_EVENT_STEPS):
        grouped.setdefault(marker["step"], []).append(marker)
    series = []
    for step in COMPARE_EVENT_STEPS:
        rows = grouped.get(step) or []
        if not rows:
            continue
        x: list = []
        y: list = []
        hover: list = []
        for marker in rows:
            x += [marker["x"], marker["x"], None]
            y += [0, 1, None]
            hover += [marker["hover"], marker["hover"], None]
        series.append((step, x, y, hover, rows[0]["color"]))
    return series


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


def cpu_limits(run_dir: Path) -> dict[str, int]:
    """Millicore limit per service: the run's CPU table, else the paper table."""
    limits = dict(topfull_cpu_quotas.PAPER_CPU_LIMIT_MILLICORES)
    manifest_path = Path(run_dir) / "run_manifest.json"
    if not manifest_path.exists():
        return limits
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest.get("scale_constraints") or []:
        if row.get("method") != "cpu_limit" or "deployment" not in row:
            continue
        limits[row["deployment"]] = topfull_cpu_quotas.cpu_limit_millicores_for(row)
    return limits


def trace_name(key: str, column: str, limits: dict[str, int] | None = None) -> str:
    if key in ("locust", "p95"):
        return column.split(".")[-1]
    if key in ("rpr", "retry_cum"):
        suffix = ".rpr" if key == "rpr" else ".retry_cum"
        edge = column[len("edge."):-len(suffix)]
        return f"{EDGE_CODES.get(edge, edge)} {edge}"
    service = column.split(".")[1]
    if key == "cpu" and limits and service in limits:
        return f"{service} ({limits[service]})"
    return service


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


def line_specs(
    view: pd.DataFrame,
    show_all: bool = False,
    limits: dict[str, int] | None = None,
) -> list[tuple[str, str, str, object]]:
    default = run_timeline.panel_columns(view)
    every = run_timeline.panel_columns(view, show_all=True)
    specs = []
    for key in PANEL_KEYS:
        for column in every[key]:
            visible = True if show_all or column in default[key] else "legendonly"
            specs.append((key, column, trace_name(key, column, limits), visible))
    specs.extend(per_api_specs(view))
    return specs


PANELS = (
    ("locust", "Goodput / RPS (req/s)"),
    ("p95", "P95 (ms)"),
    ("rejection", "Rejection"),
    ("rpr", "Retries per request"),
    ("retry_cum", "Cumulative retries"),
    ("caps", "TopFull cap (req/s)"),
    ("overload_ticks", "Overload ticks"),
    ("strip", "Attempts (0 off, 3 full)"),
    ("cpu", "CPU (millicores)"),
)
ROW = {key: index for index, (key, _) in enumerate(PANELS, start=1)}
PANEL_TITLES = dict(PANELS)


def ylabel(key: str) -> str:
    return PANEL_TITLES[key]


# The comparison chart overlays any of the line panels. req/s stays on the left axis, so a
# cap and goodput read on the same scale. Each other unit has its own right-hand axis,
# hidden until one of its lines is shown, so a rejection fraction is not flattened by
# milliseconds or millicores.
UNIT = {"locust": "req/s", "caps": "req/s", "p95": "ms", "rejection": "fraction",
        "rpr": "retries/request", "cpu": "millicores",
        "retry_cum": "retries", "overload_ticks": "ticks"}
COMPARE_AXIS = {
    "req/s": "yaxis",
    "ms": "yaxis2",
    "fraction": "yaxis3",
    "retries/request": "yaxis4",
    "millicores": "yaxis5",
    "retries": "yaxis7",
    "ticks": "yaxis8",
}
STEP_KEYS = frozenset({"retry_cum", "overload_ticks"})


def series_of(view: pd.DataFrame, column: str) -> pd.Series:
    if column == "locust.total.slo_miss":
        return slo_miss(view)
    return view[column]


def plot_points(series: pd.Series, step: bool = False) -> tuple:
    """Step series stay joined across a poll gap. A rate series still breaks."""
    if not step:
        return run_timeline._plot_points(series)
    points = series.dropna()
    return points.index.to_numpy(dtype=float), points.to_numpy(dtype=float)


ROW_HEIGHTS = [0.12, 0.09, 0.10, 0.10, 0.10, 0.08, 0.10, 0.10, 0.10]
ATTEMPT_COLORS = {0: "#d62728", 1: "#ff7f0e", 2: "#f2c744", 3: "#2ca02c"}


def axis(row: int, letter: str) -> str:
    """Axis name for a stacked panel. Row 1 is the first panel."""
    return letter if row == 1 else f"{letter}{row}"


def trace_yaxis(unit: str) -> str:
    key = COMPARE_AXIS[unit]
    return "y" if key == "yaxis" else "y" + key[len("yaxis"):]


def right_axis(title: str, position: float | None) -> dict:
    axis_layout = {
        "title": {"text": title},
        "overlaying": "y",
        "side": "right",
        "visible": False,
        "showgrid": False,
        "zeroline": False,
    }
    if position is not None:
        axis_layout["anchor"] = "free"
        axis_layout["position"] = position
    return axis_layout


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
    limits = cpu_limits(run_dir)
    fig = make_subplots(
        rows=len(PANELS), cols=1, shared_xaxes=True,
        vertical_spacing=0.025, row_heights=ROW_HEIGHTS,
    )
    used = set()

    for key, column, name, visible in line_specs(view, show_all, limits):
        step = key in STEP_KEYS
        x, y = plot_points(view[column], step=step)
        line = style_line(name, step, 1.2)
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name=name, visible=visible,
                       line=line, legendgroup=key,
                       legendgrouptitle={"text": ylabel(key), "font": {"color": "black"}}),
            row=ROW[key], col=1,
        )
        used.add(key)

    slo = slo_miss(view)
    if slo is not None:
        x, y = run_timeline._plot_points(slo)
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", name="Locust SLO-miss",
                       line={"width": 1.5, "dash": "dash", "color": "black"},
                       legendgroup="rejection",
                       legendgrouptitle={"text": ylabel("rejection"), "font": {"color": "black"}}),
            row=ROW["rejection"], col=1,
        )
        used.add("rejection")

    matrix = strip_matrix(view)
    if matrix is None:
        add_note(fig, ROW["strip"], "RetryGuard off in this run")
        used.add("strip")
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
    for marker in markers(events, steps=COMPARE_EVENT_STEPS):
        for row in range(1, len(PANELS) + 1):
            shapes.append({
                "type": "line", "xref": axis(row, "x"), "yref": f"{axis(row, 'y')} domain",
                "x0": marker["x"], "x1": marker["x"], "y0": 0, "y1": 1,
                "line": {"color": marker["color"], "width": 1}, "opacity": 0.6,
                "layer": "above" if row == ROW["strip"] else "below",
                "name": marker["step"],
            })
        if not marker["label"]:
            continue
        fig.add_annotation(
            x=marker["x"], xref="x", y=1, yref="y domain", yanchor="bottom",
            text=marker["label"], textangle=-90, showarrow=False,
            font={"size": 9, "color": marker["color"]}, hovertext=marker["hover"],
            name=marker["step"],
        )
    for step, _x, _y, _hover, color in event_series(events):
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None], mode="lines", name=step,
                line={"color": color, "width": 2},
                legendgroup=EVENT_GROUP,
                legendgrouptitle={"text": "RetryGuard events", "font": {"color": "black"}},
                hoverinfo="skip", showlegend=True,
            ),
            row=1, col=1,
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

    for key, title in PANELS:
        fig.update_yaxes(title_text=title, row=ROW[key], col=1)
    fig.update_xaxes(
        title_text="Hold clock (s since the first Locust row)",
        rangeslider={"visible": True, "thickness": 0.03}, row=len(PANELS), col=1,
    )
    fig.update_layout(
        title=run_dir.name, height=2100, hovermode="x unified", margin={"t": 90},
        legend={"groupclick": "toggleitem", "tracegroupgap": 14,
                "grouptitlefont": {"color": "black"}},
    )
    return fig


def compare_figure(run_dir: Path) -> go.Figure:
    """One chart where any lines can be overlaid, each unit on its own y-axis."""
    run_dir = Path(run_dir)
    clock = hold_clock.read_clock(run_dir)
    view = run_timeline.per_second_view(run_dir, clock)
    limits = cpu_limits(run_dir)
    events = run_timeline.switch_events(run_dir, clock)
    specs = line_specs(view, show_all=True, limits=limits)
    if slo_miss(view) is not None:
        specs.append(("rejection", "locust.total.slo_miss", "Locust SLO-miss", True))
    fig = go.Figure()
    for key, column, name, _visible in specs:
        step = key in STEP_KEYS
        x, y = plot_points(series_of(view, column), step=step)
        unit = UNIT[key]
        line = style_line(name, step, 1.4)
        fig.add_trace(go.Scatter(
            x=list(x), y=list(y), mode="lines", name=name, visible="legendonly",
            line=line, legendgroup=key, meta=unit, yaxis=trace_yaxis(unit),
            legendgrouptitle={"text": ylabel(key)},
        ))
    # Event lines use a fixed 0–1 axis over the plot, so a shed stays full height
    # when a req/s line and a rejection line are on different scales.
    for step, x, y, _hover, color in event_series(events):
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", name=step, visible=True,
            line={"width": 1.2, "color": color},
            hoverinfo="skip",
            legendgroup=EVENT_GROUP, meta="event",
            legendgrouptitle={"text": "RetryGuard events"},
            yaxis="y6",
        ))
    # Names sit above the plot, same as the stacked panels.
    for marker in markers(events, steps=COMPARE_EVENT_STEPS):
        fig.add_annotation(
            x=marker["x"], xref="x", y=1, yref="y domain", yanchor="bottom",
            text=event_caption(marker), textangle=-90, showarrow=False,
            font={"size": 9, "color": marker["color"]}, hovertext=marker["hover"],
            name=marker["step"],
        )
    # Every line starts hidden, and Plotly then sizes the x-axis to an empty span
    # instead of the hold. Pin the span so a line shows across the whole run.
    hold = view.index.to_numpy(dtype=float)
    x_range = [float(hold.min()), float(hold.max())] if hold.size else [0, 1]
    fig.update_layout(
        height=760, hovermode="x unified",
        margin={"t": 340, "r": 36, "b": 48, "l": 64},
        legend={"groupclick": "toggleitem", "tracegroupgap": 16, "orientation": "h",
                "x": 0, "xanchor": "left", "y": 1, "yanchor": "bottom",
                "font": {"size": 11}, "grouptitlefont": {"color": "black"}},
        xaxis={"title": "Hold clock (s since the first Locust row)",
               "domain": [0, 0.74], "range": x_range},
        yaxis={"title": {"text": "req/s"}},
        yaxis2=right_axis("ms", None),
        yaxis3=right_axis("fraction", 0.82),
        yaxis4=right_axis("retries/req", 0.90),
        yaxis5=right_axis("millicores", 0.98),
        yaxis7=right_axis("retries", None),
        yaxis8=right_axis("ticks", None),
        yaxis6={
            "overlaying": "y",
            "side": "left",
            "showticklabels": False,
            "showgrid": False,
            "zeroline": False,
            "showline": False,
            "ticks": "",
            "range": [0, 1],
            "fixedrange": True,
        },
    )
    return fig


# Plotly's legend has no mode where a title click toggles the group while an item
# click toggles only itself, and it greys a title whenever its group is fully hidden.
# groupclick stays "toggleitem"; this script adds the title behaviour on top.
LEGEND_CLICK_JS = """
<script>
(function () {
  var graph = document.getElementById("graph");

  function entries(group) {
    return graph.data
      .map(function (trace, index) { return { trace: trace, index: index }; })
      .filter(function (entry) { return entry.trace.legendgroup === group; });
  }

  // Plotly greys a group title once every trace in it is hidden, and no legend
  // option stops that. Repaint the titles after each redraw.
  function keepTitles() {
    // A section title is a legend row with no toggle rect. Plotly 7 gives it the
    // same legendtext class as an item, and greys it once the group is hidden.
    graph.querySelectorAll(".legend .traces").forEach(function (row) {
      if (row.querySelector(".legendtoggle")) return;
      var node = row.querySelector("text");
      if (!node) return;
      node.style.fill = "black";
      node.style.fillOpacity = "1";
    });
  }

  // An item click toggles only that trace. A title click toggles the whole group.
  // Both are done here: with legend groups, Plotly's own click hides every trace
  // in the group, so the built-in handler is cancelled and the click redone.
  graph.on("plotly_legendclick", function (event) {
    var trace = event.fullData[event.curveNumber];
    var show = trace.visible === "legendonly";
    Plotly.restyle(graph, { visible: show ? true : "legendonly" }, [event.curveNumber]).then(function () {
      keepTitles();
      return syncEvents();
    });
    return false;
  });

  var titleOf = {};
  graph.data.forEach(function (trace) {
    if (trace.legendgroup && trace.legendgrouptitle) titleOf[trace.legendgrouptitle.text] = trace.legendgroup;
  });

  graph.addEventListener("mousedown", function (event) {
    var node = event.target;
    var text = node.closest ? node.closest("text") : null;
    // A section title is the legend row that has no toggle rect. An item row has
    // one. An axis title sits outside the legend and can use the same words.
    if (!text || !text.closest(".legend")) return;
    var row = text.parentNode;
    if (!row || row.querySelector(".legendtoggle")) return;
    var group = titleOf[text.textContent];
    if (!group) return;
    event.stopPropagation();
    var groupEntries = entries(group);
    var allHidden = groupEntries.every(function (entry) { return entry.trace.visible === "legendonly"; });
    Plotly.restyle(graph, { visible: allHidden ? true : "legendonly" },
      groupEntries.map(function (entry) { return entry.index; })).then(function () {
        keepTitles();
        return syncEvents();
      });
  }, true);

  // The event lines are shapes, not traces. The legend items only exist so a
  // section click can show or hide one step on every panel.
  function syncEvents() {
    var shown = {};
    graph.data.forEach(function (trace) {
      if (trace.legendgroup !== "events") return;
      shown[trace.name] = trace.visible !== "legendonly";
    });
    if (!Object.keys(shown).length) return;
    function apply(item) {
      if (!Object.prototype.hasOwnProperty.call(shown, item.name)) return item;
      var copy = Object.assign({}, item);
      copy.visible = shown[item.name];
      return copy;
    }
    return Plotly.relayout(graph, {
      shapes: (graph.layout.shapes || []).map(apply),
      annotations: (graph.layout.annotations || []).map(apply),
    });
  }

  graph.on("plotly_afterplot", keepTitles);
  new MutationObserver(keepTitles).observe(graph, { subtree: true, attributes: true, attributeFilter: ["style"] });
})();
</script>
"""


COMPARE_LEGEND_JS = """
<script>
(function () {
  function start() {
    var graph = document.getElementById('compare-graph');
    if (!graph || !graph.data) { setTimeout(start, 50); return; }
    wire(graph);
  }
  function wire(graph) {
  var AXIS = AXIS_MAP;
  // A unit's axis stays hidden until one of its lines is on, so an unused scale
  // does not sit on the chart and a fraction is not drawn against milliseconds.
  var RIGHT = ['ms', 'fraction', 'retries/request', 'millicores', 'retries', 'ticks'];
  // A unit's axis stays hidden until one of its lines is on. Visible units pack
  // against the plot: the first on the right edge, the rest stepping outward.
  // A millicores axis left at the far margin reads as a section that did nothing.
  function syncAxes() {
    var shown = {};
    graph.data.forEach(function (trace) {
      if (!trace.meta || !AXIS[trace.meta] || AXIS[trace.meta] === 'yaxis') return;
      if (trace.visible !== 'legendonly') shown[trace.meta] = true;
    });
    var active = RIGHT.filter(function (unit) { return shown[unit]; });
    var edge = active.length ? 1 - 0.07 * active.length : 0.97;
    var update = {'xaxis.domain[1]': Math.max(0.6, edge)};
    RIGHT.forEach(function (unit) {
      var key = AXIS[unit];
      var place = active.indexOf(unit);
      update[key + '.visible'] = place !== -1;
      if (place !== -1) {
        update[key + '.anchor'] = 'free';
        update[key + '.side'] = 'right';
        update[key + '.position'] = edge + 0.07 * place;
      }
    });
    return Plotly.relayout(graph, update);
  }
  // The names on the event lines are annotations. Hiding a step hides its names
  // with the line, the same way the stacked panels hide their event marks.
  function syncEvents() {
    var shown = {};
    graph.data.forEach(function (trace) {
      if (trace.legendgroup !== 'events') return;
      shown[trace.name] = trace.visible !== 'legendonly';
    });
    if (!Object.keys(shown).length) return;
    function apply(item) {
      if (!Object.prototype.hasOwnProperty.call(shown, item.name)) return item;
      var copy = Object.assign({}, item);
      copy.visible = shown[item.name];
      return copy;
    }
    return Plotly.relayout(graph, {
      annotations: (graph.layout.annotations || []).map(apply),
    });
  }
  function sync() { return syncAxes().then(syncEvents); }
  graph.on('plotly_legendclick', function (event) {
    var trace = event.fullData[event.curveNumber];
    var show = trace.visible === 'legendonly';
    Plotly.restyle(graph, {visible: show ? true : 'legendonly'}, [event.curveNumber]).then(sync);
    return false;
  });
  var titleOf = {};
  graph.data.forEach(function (trace) {
    if (trace.legendgrouptitle) titleOf[trace.legendgrouptitle.text] = trace.legendgroup;
  });
  graph.addEventListener('mousedown', function (event) {
    var text = event.target.closest ? event.target.closest('text') : null;
    // A section title is the legend row that has no toggle rect. An item row has
    // one. An axis title sits outside the legend and can use the same words.
    if (!text || !text.closest('.legend')) return;
    var row = text.parentNode;
    if (!row || row.querySelector('.legendtoggle')) return;
    var group = titleOf[text.textContent];
    if (!group) return;
    event.stopPropagation();
    var indices = [];
    graph.data.forEach(function (trace, index) { if (trace.legendgroup === group) indices.push(index); });
    var allHidden = indices.every(function (index) { return graph.data[index].visible === 'legendonly'; });
    Plotly.restyle(graph, {visible: allHidden ? true : 'legendonly'}, indices).then(sync);
  }, true);
  function keepTitles() {
    // A section title is a legend row with no toggle rect. Plotly 7 gives it the
    // same legendtext class as an item, and greys it once the group is hidden.
    graph.querySelectorAll('.legend .traces').forEach(function (row) {
      if (row.querySelector('.legendtoggle')) return;
      var node = row.querySelector('text');
      if (!node) return;
      node.style.fill = 'black';
      node.style.fillOpacity = '1';
    });
  }
  // The legend is a row of columns above the chart. The event names also sit
  // above the plot, so the legend stays clear of that band. When the window is
  // too narrow the columns wrap; grow the chart so they still fit.
  var fits = 0;
  var NAME_ROOM = 68;
  function liftLegend() {
    var plotH = graph._fullLayout && graph._fullLayout._size && graph._fullLayout._size.h;
    if (!plotH) return;
    var y = 1 + NAME_ROOM / plotH;
    var current = graph.layout.legend && graph.layout.legend.y;
    if (current != null && Math.abs(current - y) < 0.004) return;
    return Plotly.relayout(graph, {'legend.y': y});
  }
  function fitLegend() {
    if (fits > 6) return;
    var legend = graph.querySelector('.legend');
    var grid = graph.querySelector('.gridlayer');
    if (!legend || !grid) return;
    var legendBox = legend.getBoundingClientRect();
    var gridBox = grid.getBoundingClientRect();
    var host = graph.getBoundingClientRect();
    var gap = gridBox.top - legendBox.bottom;
    var need = 0;
    if (gap < NAME_ROOM - 2) need = NAME_ROOM - gap;
    if (legendBox.top < host.top + 2) need = Math.max(need, host.top + 2 - legendBox.top);
    if (need > 2) {
      fits += 1;
      var extra = need + 8;
      Plotly.relayout(graph, {'margin.t': graph.layout.margin.t + extra, height: graph.layout.height + extra});
    }
  }
  // Plotly draws the svg at layout.height and leaves the div at its first
  // pixel height. The extra hangs over the code key and cuts off the first rows.
  function fitBox() {
    var svg = graph.querySelector('.main-svg');
    var box = graph.parentElement;
    if (!svg || !box) return;
    var drawn = Math.ceil(svg.getBoundingClientRect().height);
    if (drawn > graph.offsetHeight + 1) {
      box.style.height = drawn + 'px';
      graph.style.height = drawn + 'px';
    }
  }
  graph.on('plotly_afterplot', function () { keepTitles(); liftLegend(); fitLegend(); fitBox(); });
  new MutationObserver(keepTitles).observe(graph, {subtree: true, attributes: true, attributeFilter: ['style']});
  fitLegend();
  fitBox();
  setTimeout(function () { fitLegend(); fitBox(); }, 0);

  // Hovering the line, or the name on it, shows that action. The stroke is a few
  // pixels wide, so proximity — not only the text glyph — opens the same text.
  var tip = document.createElement('div');
  tip.id = 'event-tip';
  tip.style.cssText = 'position:fixed;z-index:30;display:none;max-width:340px;padding:6px 8px;'
    + 'background:#fff;border:1px solid #bbb;border-radius:4px;font:12px/1.35 sans-serif;'
    + 'color:#222;pointer-events:none;box-shadow:0 1px 4px rgba(0,0,0,.18)';
  graph.appendChild(tip);
  function escapeHtml(value) {
    return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function actionTip(ev) {
    var axis = graph._fullLayout && graph._fullLayout.xaxis;
    var plot = graph.querySelector('.nsewdrag');
    if (!axis || !plot || typeof axis.d2p !== 'function') { tip.style.display = 'none'; return; }
    var box = plot.getBoundingClientRect();
    if (ev.clientX < box.left || ev.clientX > box.right || ev.clientY < box.top || ev.clientY > box.bottom) {
      tip.style.display = 'none';
      return;
    }
    var shown = {};
    graph.data.forEach(function (trace) {
      if (trace.legendgroup !== 'events') return;
      shown[trace.name] = trace.visible !== 'legendonly';
    });
    var px = ev.clientX - graph.getBoundingClientRect().left;
    var near = (graph.layout.annotations || []).filter(function (item) {
      return item.hovertext && shown[item.name] && Math.abs(axis.d2p(item.x) - px) <= 8;
    });
    if (!near.length) { tip.style.display = 'none'; return; }
    tip.innerHTML = near.map(function (item) {
      return item.hovertext.split('<br>').map(escapeHtml).join('<br>');
    }).join('<hr style="border:none;border-top:1px solid #ddd;margin:4px 0">');
    tip.style.display = 'block';
    var left = ev.clientX + 14;
    if (left + 340 > window.innerWidth) left = ev.clientX - 354;
    tip.style.left = left + 'px';
    tip.style.top = Math.min(ev.clientY + 14, window.innerHeight - 80) + 'px';
  }
  graph.addEventListener('mousemove', actionTip);
  graph.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
  }
  start();
})();
</script>
"""


def compare_legend_js() -> str:
    return COMPARE_LEGEND_JS.replace("AXIS_MAP", json.dumps(COMPARE_AXIS))


def legend_html() -> str:
    """The E and V key. It sits above the stacked panels, next to the marker labels."""
    edges = list(EDGE_CODES.items())
    edge_rows = "".join(
        "<tr>"
        f"<td><b>{left_code}</b></td><td>{html.escape(left_name)}</td>"
        f"<td style='padding-left:20px'><b>{right_code}</b></td><td>{html.escape(right_name)}</td>"
        "</tr>"
        for (left_name, left_code), (right_name, right_code) in zip(edges[:7], edges[7:])
    )
    service_rows = "".join(
        f"<tr><td><b>{code}</b></td><td>{html.escape(name)}</td></tr>"
        for name, code in SERVICE_CODES.items()
    )
    cell = "padding:1px 8px 1px 0;white-space:nowrap"
    return (
        '<div style="display:flex;gap:40px;margin:8px 16px 4px;padding:8px 12px;'
        'font-family:sans-serif;font-size:12px;line-height:1.35;color:#222;'
        'background:#f6f7f9;border:1px solid #ddd">'
        '<table style="border-collapse:collapse">'
        f'<caption style="text-align:left;font-weight:600;padding-bottom:4px">Edge codes, ON→OFF</caption>'
        f"{edge_rows}</table>"
        '<table style="border-collapse:collapse">'
        f'<caption style="text-align:left;font-weight:600;padding-bottom:4px">Service codes, OFF→ON</caption>'
        f"{service_rows}</table></div>"
    ).replace("<td>", f'<td style="{cell}">')


def detach_compare_height(block: str) -> str:
    """Move the comparison chart's pixel height onto the plot itself.

    Plotly wraps the plot in a fixed-height box. The page then lengthens the
    plot so its legend clears the event names, and those extra pixels paint
    over the code key that follows the box.
    """
    pattern = re.compile(
        r'<div style="height:(\d+)px; width:100%;">'
        r'(\s*)<div id="compare-graph" class="plotly-graph-div" style="height:100%; width:100%;">'
    )
    match = pattern.search(block)
    if match is None:
        raise RuntimeError("comparison chart wrapper was not the expected fixed-height box")
    height, space = match.group(1), match.group(2)
    return pattern.sub(
        f'<div style="width:100%;">{space}'
        f'<div id="compare-graph" class="plotly-graph-div" style="height:{height}px; width:100%;">',
        block,
        count=1,
    )


def write_html(fig: go.Figure, path: Path, run_dir: Path | None = None) -> None:
    page = pio.to_html(fig, full_html=True, include_plotlyjs=True, div_id="graph")
    key = legend_html()
    if run_dir is not None:
        compare = compare_figure(run_dir)
        block = detach_compare_height(
            pio.to_html(compare, full_html=False, include_plotlyjs=False, div_id="compare-graph")
        )
        div, _, script = block.partition("<script>")
        # Plotly closes the chart wrapper after the script. The key has to follow
        # that close, or it sits inside the chart.
        script, wrapper, _ = script.rpartition("</div>")
        page = page.replace("<body>", "<body>" + div + wrapper + key)
        page = page.replace(
            "</body>", "<script>" + script + compare_legend_js() + "</body>"
        )
    else:
        page = page.replace("<body>", "<body>" + key)
    page = page.replace("</body>", LEGEND_CLICK_JS + "</body>")
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
    write_html(build_figure(run, show_all=args.all), out, run)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
