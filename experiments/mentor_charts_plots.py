"""
mentor_charts_plots.py — matplotlib chart builders consuming the
pandas objects produced by mentor_charts_data.py. Every function writes
a PNG to an explicit out_path and returns None.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_TOGGLE_COLORS = {"ON→OFF": "tab:red", "OFF→ON": "tab:green"}


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


def plot_multi_line(df: pd.DataFrame, title: str, ylabel: str, out_path: Path) -> None:
    """Plot one line per column of df against its index (elapsed seconds
    or row number). Used for CPU/memory-per-service overlays and
    retries-per-target-service overlays. Handles an empty DataFrame by
    still writing an (empty) chart, so orchestration code never has to
    special-case missing data."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for column in df.columns:
        ax.plot(df.index, df[column], label=str(column))
    ax.set_title(title)
    ax.set_xlabel("Elapsed seconds")
    ax.set_ylabel(ylabel)
    if not df.empty:
        ax.legend(loc="best", fontsize="small")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _draw_comparison_panel(ax, baseline_avg: pd.DataFrame, rg_avg: pd.DataFrame, subtitle: str, ylabel: str) -> None:
    if not baseline_avg.empty:
        ax.plot(baseline_avg.index, baseline_avg["mean"], label="Baseline", color="tab:blue")
    if not rg_avg.empty:
        ax.plot(rg_avg.index, rg_avg["mean"], label="RetryGuard", color="tab:orange")
    ax.set_title(subtitle)
    ax.set_xlabel("Elapsed seconds")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", fontsize="small")


def plot_side_by_side_comparison(
    pair_a: tuple[pd.DataFrame, pd.DataFrame],
    pair_b: tuple[pd.DataFrame, pd.DataFrame],
    title: str,
    ylabel: str,
    label_a: str,
    label_b: str,
    out_path: Path,
) -> None:
    """Draw a two-panel figure: left panel is pair_a's baseline-vs-RG
    comparison (S4A), right panel is pair_b's (S4B), sharing the y-axis
    scale so the two positions are visually comparable."""
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
    _draw_comparison_panel(ax_a, pair_a[0], pair_a[1], label_a, ylabel)
    _draw_comparison_panel(ax_b, pair_b[0], pair_b[1], label_b, ylabel)
    fig.suptitle(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
