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
