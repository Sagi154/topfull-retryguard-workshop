"""Per-second view and stacked chart for one run, on the hold clock.

    python experiments/run_timeline.py <run_dir> [<run_dir> ...] [--all] [--csv] [--columns PATTERN ...]
    python experiments/run_timeline.py --tree "experiments/results/final results"

Writes locust_clock.json and timeline.png into each run folder. --csv also
writes timeline_1s.csv, which is not committed. Rules for one second:
docs/superpowers/specs/2026-10-13-hold-clock-design.md (the Q5 table).
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import hold_clock  # noqa: E402

PNG_NAME = "timeline.png"
CSV_NAME = "timeline_1s.csv"
FLAG = "__carried"
NO_CAP = 10000.0
THROTTLE_CARRY_S = 6
RESOURCE_CARRY_S = 5
LOCUST_COLUMNS = ("RPS", "Fail", "Goodput", "Latency95", "Latency99")
INBOUND_COUNTERS = (
    "total", "2xx", "4xx", "5xx", "resets",
    "grpc_2", "grpc_4", "grpc_13", "grpc_14",
    "rq_time_sum_ms", "rq_time_count",
)
EDGE_COUNTERS = ("total", "2xx", "4xx", "5xx", "retry", "rq_time_sum_ms", "rq_time_count")
DETECT_READINGS = ("cadvisor_cpu", "quota", "alpha", "utilization", "overloaded")
RESOURCE_READINGS = ("cpu_millicores", "memory_working_set_bytes", "replica_count")
RG_NUMERIC_FIELDS = ("rpr", "rejection", "attempts", "high", "low", "burst_rpr5")

# Keep in step with retryguard.CONTROLLED_EDGES (retryguard imports kubernetes,
# so it is not imported here).
CONTROLLED_EDGES = (
    ("frontend", "adservice"),
    ("frontend", "cartservice"),
    ("frontend", "checkoutservice"),
    ("frontend", "currencyservice"),
    ("frontend", "productcatalogservice"),
    ("frontend", "recommendationservice"),
    ("frontend", "shippingservice"),
    ("checkoutservice", "cartservice"),
    ("checkoutservice", "currencyservice"),
    ("checkoutservice", "emailservice"),
    ("checkoutservice", "paymentservice"),
    ("checkoutservice", "productcatalogservice"),
    ("checkoutservice", "shippingservice"),
    ("recommendationservice", "productcatalogservice"),
)


def seconds(hold_s) -> np.ndarray:
    return np.floor(np.asarray(hold_s, dtype=float)).astype(int)


def label(key) -> str:
    return "->".join(key) if isinstance(key, tuple) else str(key)


def measured(secs: np.ndarray, values, name: str) -> pd.DataFrame:
    series = pd.Series(np.asarray(values, dtype=float), index=secs)
    return series.groupby(level=0).mean().rename(name).to_frame()


def ratio(num, den) -> np.ndarray:
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    out = np.full(num.shape, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def carried(secs: np.ndarray, values, name: str, limit: int, ends=None) -> pd.DataFrame:
    """Latest reading per second, carried forward at most `limit` seconds.
    A NaN value is no reading. `ends` marks readings that clear the carry."""
    values = np.asarray(values, dtype=float)
    ends = np.zeros(values.size, dtype=bool) if ends is None else np.asarray(ends, dtype=bool)
    frame = pd.DataFrame({"value": values, "end": ends}, index=secs)
    last = frame["value"].groupby(level=0).last()
    ended = frame["end"].groupby(level=0).any()
    grid = np.arange(int(secs.min()), int(secs.max()) + limit + 1)
    out_value = np.full(grid.size, np.nan)
    out_flag = np.full(grid.size, np.nan)
    current, since = np.nan, None
    for i, sec in enumerate(grid):
        reading = last.get(sec, np.nan)
        if not np.isnan(reading):
            current, since = reading, sec
            out_value[i], out_flag[i] = reading, 0.0
            continue
        if bool(ended.get(sec, False)):
            current, since = np.nan, None
            continue
        if since is not None and sec - since <= limit:
            out_value[i], out_flag[i] = current, 1.0
    return pd.DataFrame({name: out_value, name + FLAG: out_flag}, index=grid)


def poll_deltas(group: pd.DataFrame, columns) -> tuple[np.ndarray, np.ndarray, dict]:
    """Deltas between consecutive polls, at the later poll's second.
    Gaps with a non-positive dt or any counter that went down are dropped."""
    group = group.sort_values("hold_s")
    t = group["hold_s"].to_numpy(dtype=float)
    dt = np.diff(t)
    deltas = {c: np.diff(group[c].to_numpy(dtype=float)) for c in columns}
    keep = dt > 0
    for delta in deltas.values():
        keep &= delta >= 0
    return seconds(t[1:])[keep], dt[keep], {c: d[keep] for c, d in deltas.items()}


def _counters(group: pd.DataFrame, names) -> list[str]:
    return [c for c in names if c in group.columns and group[c].notna().all()]


def locust_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    frames = []
    for name in hold_clock.LOCUST_FILES:
        df = hold_clock.load_source(run_dir, name, clock)
        if df.empty:
            continue
        secs = seconds(df["hold_s"])
        for column in LOCUST_COLUMNS:
            if column in df.columns:
                frames.append(measured(secs, df[column], f"locust.{name}.{column}"))
    return frames


def inbound_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "service_inbound", clock)
    frames = []
    if df.empty:
        return frames
    for service, group in df.groupby("service", sort=True):
        counters = _counters(group, INBOUND_COUNTERS)
        secs, dt, d = poll_deltas(group, counters)
        if secs.size == 0:
            continue
        prefix = f"inbound.{label(service)}"
        for column in counters:
            frames.append(measured(secs, d[column] / dt, f"{prefix}.{column}_per_s"))
        if {"total", "5xx", "resets"} <= set(d):
            failures = d["5xx"] + d["resets"]
            if label(service) in analysis_score.GRPC_CALLEES and {"grpc_4", "grpc_14"} <= set(d):
                failures = failures + d["grpc_4"] + d["grpc_14"]
            frames.append(measured(secs, ratio(failures, d["total"]), f"{prefix}.rejection"))
        if {"rq_time_sum_ms", "rq_time_count"} <= set(d):
            frames.append(measured(
                secs, ratio(d["rq_time_sum_ms"], d["rq_time_count"]), f"{prefix}.sojourn_ms"))
    return frames


def edge_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "service_edges", clock)
    frames = []
    if df.empty:
        return frames
    for key, group in df.groupby(["caller", "target"], sort=True):
        counters = _counters(group, EDGE_COUNTERS)
        secs, dt, d = poll_deltas(group, counters)
        if secs.size == 0:
            continue
        prefix = f"edge.{label(key)}"
        for column in counters:
            frames.append(measured(secs, d[column] / dt, f"{prefix}.{column}_per_s"))
        if {"total", "retry"} <= set(d):
            frames.append(measured(
                secs, ratio(d["retry"], d["total"] - d["retry"]), f"{prefix}.rpr"))
        if {"rq_time_sum_ms", "rq_time_count"} <= set(d):
            frames.append(measured(
                secs, ratio(d["rq_time_sum_ms"], d["rq_time_count"]), f"{prefix}.sojourn_ms"))
    return frames


def throttle_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "topfull_throttle", clock)
    frames = []
    if df.empty:
        return frames
    for api, group in df.groupby("api", sort=True):
        group = group.sort_values("hold_s")
        secs = seconds(group["hold_s"])
        cap = group["threshold"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        live = fresh & (cap > 0) & (cap < NO_CAP)
        frames.append(carried(
            secs, np.where(live, cap, np.nan), f"throttle.{label(api)}.cap",
            THROTTLE_CARRY_S, ends=fresh & (cap >= NO_CAP)))
        admitted_fresh = group["admitted_fresh"].to_numpy(dtype=float) == 1
        frames.append(carried(
            secs, np.where(admitted_fresh, group["admitted_rps"].to_numpy(dtype=float), np.nan),
            f"throttle.{label(api)}.admitted_rps", THROTTLE_CARRY_S))
    return frames


def reading_frames(
    run_dir: Path, clock: dict, source: str, prefix: str, readings, limit: int
) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, source, clock)
    frames = []
    if df.empty:
        return frames
    for service, group in df.groupby("service", sort=True):
        group = group.sort_values("hold_s")
        secs = seconds(group["hold_s"])
        for column in readings:
            if column in group.columns:
                frames.append(carried(
                    secs, pd.to_numeric(group[column], errors="coerce"),
                    f"{prefix}.{label(service)}.{column}", limit))
    return frames


def retryguard_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty:
        return []
    df = df[df["hold_s"].notna()]
    frames = []
    for name, group in df[df["kind"] == "OBSERVE"].groupby("name", sort=True):
        secs = seconds(group["hold_s"])
        for field in RG_NUMERIC_FIELDS:
            if field in group.columns:
                values = pd.to_numeric(group[field], errors="coerce")
                if values.notna().any():
                    frames.append(measured(secs, values, f"rg.{label(name)}.{field}"))
    switches = df[df["kind"] == "switch"]
    if not switches.empty:
        text = switches["name"] + " " + switches["step"]
        joined = text.groupby(seconds(switches["hold_s"])).agg("; ".join)
        frames.append(joined.rename("rg.switches").to_frame())
    return frames


def with_flags(view: pd.DataFrame) -> pd.DataFrame:
    columns = {}
    for column in view.columns:
        if column.endswith(FLAG):
            continue
        flag = view[column + FLAG] if column + FLAG in view.columns else pd.Series(0.0, index=view.index)
        columns[column] = view[column]
        columns[column + FLAG] = flag.where(view[column].notna())
    return pd.DataFrame(columns, index=view.index)


def per_second_view(run_dir: Path, clock: dict | None = None) -> pd.DataFrame:
    run_dir = Path(run_dir)
    clock = clock or hold_clock.read_clock(run_dir)
    frames = (
        locust_frames(run_dir, clock)
        + inbound_frames(run_dir, clock)
        + edge_frames(run_dir, clock)
        + throttle_frames(run_dir, clock)
        + reading_frames(run_dir, clock, "topfull_detect", "detect", DETECT_READINGS, THROTTLE_CARRY_S)
        + reading_frames(run_dir, clock, "resource_usage", "resource", RESOURCE_READINGS, RESOURCE_CARRY_S)
        + retryguard_frames(run_dir, clock)
    )
    if not frames:
        return pd.DataFrame()
    view = pd.concat(frames, axis=1)
    view = view.reindex(range(int(view.index.min()), int(view.index.max()) + 1))
    view.index.name = "hold_s"
    return with_flags(view)


def switch_events(run_dir: Path, clock: dict) -> pd.DataFrame:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty or "step" not in df.columns:
        return pd.DataFrame(columns=["hold_s", "name", "step"])
    switches = df[(df["kind"] == "switch") & df["hold_s"].notna()]
    return switches[["hold_s", "name", "step"]].reset_index(drop=True)


def select_columns(view: pd.DataFrame, patterns: list[str] | None) -> pd.DataFrame:
    if not patterns:
        return view
    keep = [
        column for column in view.columns
        if not column.endswith(FLAG) and any(fnmatch.fnmatchcase(column, p) for p in patterns)
    ]
    return view[[name for column in keep for name in (column, column + FLAG)]]
