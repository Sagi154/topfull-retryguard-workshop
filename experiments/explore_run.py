"""Interactive Plotly view of one run on the hold clock.

    python experiments/explore_run.py <run_dir> [--all]

Writes experiments/explore_out/<run folder name>.html (not committed).
Design and decisions: docs/superpowers/specs/2026-10-13-interactive-run-explorer-design.md
"""
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
