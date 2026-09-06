"""
mentor_charts_data.py — Pure data loading and aggregation helpers over
experiments/results/campaign_48/ run folders. No plotting, no network
access; every function takes explicit paths/DataFrames and returns
pandas objects.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CAMPAIGN_ROOT = Path(__file__).resolve().parent / "results" / "campaign_48"


def find_run_dirs(scenario_dir: Path, prefix: str) -> list[Path]:
    """Return the run folders directly under scenario_dir whose name
    matches '<prefix>_run<N>' (N numeric), sorted by run number ascending."""
    pattern = re.compile(rf"^{re.escape(prefix)}_run(\d+)$")
    matches: list[tuple[int, Path]] = []
    for child in scenario_dir.iterdir():
        if not child.is_dir():
            continue
        m = pattern.match(child.name)
        if m:
            matches.append((int(m.group(1)), child))
    matches.sort(key=lambda pair: pair[0])
    return [path for _, path in matches]


def load_metric_column(
    run_dirs: list[Path], csv_name: str, column: str
) -> list[pd.Series]:
    """Read `column` from `csv_name` in each run dir. Each returned Series
    has a plain 0-based RangeIndex; for the per-second Locust CSVs this
    index IS elapsed seconds."""
    series_list = []
    for run_dir in run_dirs:
        df = pd.read_csv(run_dir / csv_name)
        series_list.append(df[column].reset_index(drop=True))
    return series_list


def average_series(series_list: list[pd.Series]) -> pd.DataFrame:
    """Truncate every series to the length of the shortest one, then
    return a DataFrame with columns 'mean', 'min', 'max' computed
    pointwise (row-by-row) across the input series."""
    if not series_list:
        return pd.DataFrame(columns=["mean", "min", "max"])
    min_len = min(len(s) for s in series_list)
    truncated = [s.iloc[:min_len].reset_index(drop=True) for s in series_list]
    stacked = pd.concat(truncated, axis=1)
    return pd.DataFrame(
        {
            "mean": stacked.mean(axis=1),
            "min": stacked.min(axis=1),
            "max": stacked.max(axis=1),
        }
    )


def _parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def rejection_rate_series(run_dirs: list[Path], csv_name: str) -> list[pd.Series]:
    """Compute Fail/RPS per row for each run dir's csv_name (0.0 where
    RPS == 0, since there was no offered load to reject)."""
    series_list = []
    for run_dir in run_dirs:
        df = pd.read_csv(run_dir / csv_name)
        rate = (df["Fail"] / df["RPS"].replace(0, pd.NA)).fillna(0.0)
        series_list.append(rate.reset_index(drop=True))
    return series_list
