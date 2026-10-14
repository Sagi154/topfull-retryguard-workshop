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
    """The range slider and the x title sit on the last panel only.

    Panels that have no height yet take PANEL_HEIGHT. The last panel is that
    height plus the slider, so the extra space is the slider and nothing else.
    """
    for fig in figs[:-1]:
        height = PANEL_HEIGHT if fig.layout.height is None else fig.layout.height
        fig.update_layout(xaxis_title_text="", margin_b=24, height=height)
    last = figs[-1]
    panel_height = PANEL_HEIGHT if figs[0].layout.height is None else figs[0].layout.height
    last.update_layout(
        xaxis_title_text=HOLD_CLOCK_TITLE,
        xaxis_rangeslider={"visible": True, "thickness": 0.06},
        height=panel_height + SLIDER_EXTRA,
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
