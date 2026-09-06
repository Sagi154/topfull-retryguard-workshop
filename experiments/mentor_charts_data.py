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


def downsample_series(df: pd.DataFrame, step_seconds: int) -> pd.DataFrame:
    """Keep the first row in each `step_seconds` elapsed-time bin.
    Works for Locust (index 0, 1, 2, ...) and collector series (index
    ~0, 5, 10, ...). step_seconds <= 1 or an empty frame is unchanged."""
    if df.empty or step_seconds <= 1:
        return df
    keep: list[int] = []
    last_bin: int | None = None
    for i, elapsed in enumerate(df.index):
        bin_id = int(elapsed // step_seconds)
        if last_bin is None or bin_id != last_bin:
            keep.append(i)
            last_bin = bin_id
    return df.iloc[keep]


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


def envoy_retries_per_request(run_dir: Path, csv_name: str) -> pd.DataFrame:
    """Read an envoy_retries_*.csv file and compute retries-per-request
    per target_service by differencing consecutive cumulative rows.
    Returns a DataFrame indexed by elapsed_seconds (relative to the
    file's earliest timestamp) with one column per target_service plus
    a 'total' column (summed retry/total diffs across target services
    at each poll, then divided)."""
    df = pd.read_csv(run_dir / csv_name)
    df["timestamp"] = df["timestamp"].map(_parse_ts)
    t0 = df["timestamp"].min()
    df["elapsed_seconds"] = (df["timestamp"] - t0).dt.total_seconds()

    columns: dict[str, pd.Series] = {}
    for target, group in df.groupby("target_service", sort=True):
        group = group.sort_values("elapsed_seconds").reset_index(drop=True)
        d_retry = group["upstream_rq_retry"].diff().fillna(0.0)
        d_total = group["upstream_rq_total"].diff().fillna(0.0)
        rate = (d_retry / d_total.replace(0, pd.NA)).fillna(0.0)
        columns[target] = pd.Series(
            rate.to_numpy(), index=group["elapsed_seconds"].to_numpy()
        )
    result = pd.DataFrame(columns).sort_index()

    totals = (
        df.groupby("elapsed_seconds")[["upstream_rq_retry", "upstream_rq_total"]]
        .sum()
        .sort_index()
    )
    d_retry_total = totals["upstream_rq_retry"].diff().fillna(0.0)
    d_total_total = totals["upstream_rq_total"].diff().fillna(0.0)
    result["total"] = (
        (d_retry_total / d_total_total.replace(0, pd.NA)).fillna(0.0).to_numpy()
    )
    return result


def resource_usage_series(run_dir: Path, column: str) -> pd.DataFrame:
    """Read resource_usage.csv from run_dir; return a DataFrame indexed by
    elapsed_seconds (relative to the file's earliest timestamp) with one
    column per service, containing the requested numeric column."""
    df = pd.read_csv(run_dir / "resource_usage.csv")
    df["timestamp"] = df["timestamp"].map(_parse_ts)
    t0 = df["timestamp"].min()
    df["elapsed_seconds"] = (df["timestamp"] - t0).dt.total_seconds()

    columns: dict[str, pd.Series] = {}
    for service, group in df.groupby("service", sort=True):
        group = group.sort_values("elapsed_seconds")
        columns[service] = pd.Series(
            group[column].to_numpy(), index=group["elapsed_seconds"].to_numpy()
        )
    return pd.DataFrame(columns).sort_index()


def average_dataframes(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Positionally average a list of DataFrames (as produced by
    envoy_retries_per_request / resource_usage_series for different
    repeats of the same run group): truncate to the shortest row count,
    keep only columns present in every input, and return the pointwise
    mean of values. The returned index is the pointwise mean of the
    truncated input indexes (elapsed seconds), not a 0-based row number.
    """
    if not dfs:
        return pd.DataFrame()
    common_columns = set(dfs[0].columns)
    for df in dfs[1:]:
        common_columns &= set(df.columns)
    common_columns = sorted(common_columns)
    min_len = min(len(df) for df in dfs)
    truncated = [df[common_columns].iloc[:min_len] for df in dfs]
    stacked = pd.concat(
        [t.reset_index(drop=True) for t in truncated],
        axis=0,
        keys=range(len(truncated)),
    )
    result = stacked.groupby(level=1).mean()
    index_mean = pd.concat(
        [pd.Series(t.index.to_numpy()) for t in truncated],
        axis=1,
    ).mean(axis=1)
    result.index = index_mean.to_numpy()
    return result


TOGGLE_PATTERN = re.compile(
    r"^(?P<ts>\S+)\s+(?P<service>\S+)\s+(?P<direction>ON→OFF|OFF→ON)\b"
)


def parse_toggle_events(log_path: Path) -> list[dict]:
    """Parse a retryguard.log file's ON→OFF / OFF→ON lines. Returns a
    list of {'elapsed_seconds', 'service', 'direction'} dicts, with
    elapsed_seconds relative to the log's earliest timestamped line."""
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    timestamps: list[datetime] = []
    raw_events: list[dict] = []
    for line in lines:
        parts = line.split(None, 1)
        if not parts:
            continue
        try:
            ts = _parse_ts(parts[0])
        except ValueError:
            continue
        timestamps.append(ts)
        match = TOGGLE_PATTERN.match(line)
        if match:
            raw_events.append(
                {
                    "timestamp": ts,
                    "service": match.group("service"),
                    "direction": match.group("direction"),
                }
            )
    if not timestamps:
        return []
    t0 = min(timestamps)
    return [
        {
            "elapsed_seconds": (e["timestamp"] - t0).total_seconds(),
            "service": e["service"],
            "direction": e["direction"],
        }
        for e in raw_events
    ]
