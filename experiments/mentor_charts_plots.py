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
    """Plot baseline vs RetryGuard mean lines (with min/max shaded band)
    against elapsed seconds. If toggle_events is given (from
    mentor_charts_data.parse_toggle_events), draw a vertical dashed line
    per event, colored red for ON→OFF and green for OFF→ON, labeled with
    the service name."""
    fig, ax = plt.subplots(figsize=(9, 4.5))

    if not baseline_avg.empty:
        ax.plot(baseline_avg.index, baseline_avg["mean"], label="Baseline (TopFull only)", color="tab:blue")
        ax.fill_between(baseline_avg.index, baseline_avg["min"], baseline_avg["max"], color="tab:blue", alpha=0.15)
    if not rg_avg.empty:
        ax.plot(rg_avg.index, rg_avg["mean"], label="TopFull + RetryGuard", color="tab:orange")
        ax.fill_between(rg_avg.index, rg_avg["min"], rg_avg["max"], color="tab:orange", alpha=0.15)

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
