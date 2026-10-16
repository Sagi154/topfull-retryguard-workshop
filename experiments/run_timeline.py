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
# A threshold at or above this is no cap: 10000 is the passthrough, and the RL can step a little
# below it (9999.55, 9997.5). Keep in step with throttle_stale.NO_CAP and analysis_score.NO_CAP_FROM.
NO_CAP = 9900.0
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


def cumulative_sum(secs: np.ndarray, deltas, name: str) -> pd.DataFrame:
    """Running sum of per-poll increases, stored on the later poll's second.

    Two polls in one second add. Seconds with no poll stay empty, so a carried
    reading is not an extra tick.
    """
    added = pd.Series(np.asarray(deltas, dtype=float), index=secs).groupby(level=0).sum()
    return added.cumsum().rename(name).to_frame()


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
        if "retry" in d:
            frames.append(cumulative_sum(secs, d["retry"], f"{prefix}.retry_cum"))
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


def overload_tick_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    """Count of detector rows with overloaded=1, not seconds the flag was carried."""
    df = hold_clock.load_source(run_dir, "topfull_detect", clock)
    if df.empty or "overloaded" not in df.columns:
        return []
    frames = []
    for service, group in df.groupby("service", sort=True):
        group = group.sort_values("hold_s")
        flag = pd.to_numeric(group["overloaded"], errors="coerce").fillna(0)
        ticks = (flag.to_numpy(dtype=float) == 1).astype(float)
        frames.append(cumulative_sum(
            seconds(group["hold_s"]), ticks, f"detect.{label(service)}.overload_ticks_cum"))
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
        + overload_tick_frames(run_dir, clock)
        + reading_frames(run_dir, clock, "resource_usage", "resource", RESOURCE_READINGS, RESOURCE_CARRY_S)
        + retryguard_frames(run_dir, clock)
    )
    if not frames:
        return pd.DataFrame()
    view = pd.concat(frames, axis=1)
    view = view.reindex(range(int(view.index.min()), int(view.index.max()) + 1))
    view.index.name = "hold_s"
    return with_flags(view)


SWITCH_EVENT_COLUMNS = [
    "hold_s", "name", "step", "metric", "rpr", "rejection", "from_attempts", "consecutive_low",
]


def switch_events(run_dir: Path, clock: dict) -> pd.DataFrame:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty or "step" not in df.columns:
        return pd.DataFrame(columns=SWITCH_EVENT_COLUMNS)
    switches = df[(df["kind"] == "switch") & df["hold_s"].notna()]
    return switches.reindex(columns=SWITCH_EVENT_COLUMNS).reset_index(drop=True)


def select_columns(view: pd.DataFrame, patterns: list[str] | None) -> pd.DataFrame:
    if not patterns:
        return view
    keep = [
        column for column in view.columns
        if not column.endswith(FLAG) and any(fnmatch.fnmatchcase(column, p) for p in patterns)
    ]
    return view[[name for column in keep for name in (column, column + FLAG)]]


PANELS = (
    ("locust", "Goodput / RPS (req/s)"),
    ("p95", "P95 (ms)"),
    ("caps", "TopFull cap (req/s)"),
    ("rejection", "Inbound rejection"),
    ("rpr", "Retries per request"),
    ("cpu", "CPU (millicores)"),
)
SWITCH_COLORS = {"ON→OFF": "red", "OFF→ON": "green", "1→2": "orange", "2→3": "orange"}
MAX_PLOT_GAP_S = 3


def panel_columns(view: pd.DataFrame, show_all: bool = False) -> dict[str, list[str]]:
    def present(column: str) -> bool:
        return column in view.columns

    def any_positive(column: str) -> bool:
        return present(column) and bool((view[column] > 0).any())

    return {
        "locust": [c for c in ("locust.total.Goodput", "locust.total.RPS") if present(c)],
        "p95": [c for c in ("locust.total.Latency95",) if present(c)],
        "caps": [
            f"throttle.{api}.cap" for api in analysis_score.APIS
            if present(f"throttle.{api}.cap") and view[f"throttle.{api}.cap"].notna().any()
        ],
        "rejection": [
            f"inbound.{service}.rejection" for service in analysis_score.SERVICES
            if present(f"inbound.{service}.rejection")
            and (show_all or any_positive(f"inbound.{service}.rejection"))
        ],
        "rpr": [
            f"edge.{caller}->{target}.rpr" for caller, target in CONTROLLED_EDGES
            if present(f"edge.{caller}->{target}.rpr")
            and (show_all or any_positive(f"edge.{caller}->{target}.retry_per_s"))
        ],
        "retry_cum": [
            f"edge.{caller}->{target}.retry_cum" for caller, target in CONTROLLED_EDGES
            if present(f"edge.{caller}->{target}.retry_cum")
            and (show_all or any_positive(f"edge.{caller}->{target}.retry_cum"))
        ],
        "overload_ticks": sorted(
            column for column in view.columns
            if column.startswith("detect.") and column.endswith(".overload_ticks_cum")
            and not column.endswith(FLAG)
            and (show_all or any_positive(column))
        ),
        "cpu": sorted(
            column for column in view.columns
            if column.startswith("resource.") and column.endswith(".cpu_millicores")
            and column != "resource.__master_node__.cpu_millicores"
        ),
    }


def escape_hold_s(run_dir: Path, clock: dict) -> float | None:
    if not any(part.startswith("S2_") for part in Path(run_dir).resolve().parts):
        return None
    import s2_latch_escape as escape

    inbound = escape.read_inbound(str(Path(run_dir) / "service_inbound.csv"))
    t0 = escape.mesh_t0(inbound)
    if t0 is None:
        return None
    recs = escape.rate_series(escape.service_rows(inbound, "recommendationservice"), t0)
    escape_s = escape.first_sustained(recs, escape.DEFAULT_RATE, escape.DEFAULT_PERSIST, "arrival")
    if escape_s is None:
        return None
    return t0 + escape_s - hold_clock.zero_epoch(clock)


def _plot_points(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Measured points only, joined across gaps up to MAX_PLOT_GAP_S."""
    points = series.dropna()
    x = points.index.to_numpy(dtype=float)
    y = points.to_numpy(dtype=float)
    if x.size > 1:
        breaks = np.flatnonzero(np.diff(x) > MAX_PLOT_GAP_S) + 1
        x, y = np.insert(x, breaks, np.nan), np.insert(y, breaks, np.nan)
    return x, y


def plot_timeline(
    view: pd.DataFrame,
    events: pd.DataFrame,
    out_path: Path,
    title: str = "",
    show_all: bool = False,
    escape_s: float | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    panels = panel_columns(view, show_all)
    fig, axes = plt.subplots(len(PANELS), 1, sharex=True, figsize=(14, 3 * len(PANELS)))
    for ax, (key, ylabel) in zip(axes, PANELS):
        columns = panels[key]
        for column in columns:
            name = column.split(".")[-1] if key in ("locust", "p95") else column.split(".")[1]
            ax.plot(*_plot_points(view[column]), linewidth=0.9, label=name)
        for _, event in events.iterrows():
            ax.axvline(event["hold_s"], color=SWITCH_COLORS.get(event["step"], "gray"),
                       linewidth=0.8, alpha=0.7)
        if key == "locust" and escape_s is not None:
            ax.axvline(escape_s, color="black", linestyle="--", linewidth=1.2, label="escape")
        if not columns:
            ax.text(0.5, 0.5, "none in this run", transform=ax.transAxes,
                    ha="center", va="center", color="gray")
        else:
            ax.legend(loc="upper right", fontsize=7, ncol=min(4, len(columns) + 1))
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Hold clock (s since the first Locust row)")
    if not events.empty:
        steps = sorted(set(events["step"]))
        fig.legend(
            [Line2D([0], [0], color=SWITCH_COLORS.get(step, "gray")) for step in steps],
            [f"RetryGuard {step}" for step in steps],
            loc="upper left", fontsize=8,
        )
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)


def build(
    run_dir: Path,
    show_all: bool = False,
    write_csv: bool = False,
    columns: list[str] | None = None,
) -> Path:
    run_dir = Path(run_dir)
    clock = hold_clock.write_clock(run_dir)
    view = per_second_view(run_dir, clock)
    png = run_dir / PNG_NAME
    plot_timeline(
        view, switch_events(run_dir, clock), png,
        title=run_dir.name, show_all=show_all, escape_s=escape_hold_s(run_dir, clock),
    )
    if write_csv:
        select_columns(view, columns).to_csv(run_dir / CSV_NAME)
    return png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hold-clock timeline for run folders.")
    parser.add_argument("runs", nargs="*", help="Run folders")
    parser.add_argument("--tree", help="Every folder under this path that has total.csv")
    parser.add_argument("--all", action="store_true", help="Every service and edge in panels 4 and 5")
    parser.add_argument("--csv", action="store_true", help="Also write timeline_1s.csv")
    parser.add_argument("--columns", nargs="*", help="Glob patterns for the CSV columns")
    args = parser.parse_args(argv)
    failures = 0
    for run in hold_clock.run_dirs(args.runs, args.tree):
        try:
            png = build(run, show_all=args.all, write_csv=args.csv, columns=args.columns)
        except (ValueError, KeyError) as exc:
            print(f"{run.name}: ERROR {exc}")
            failures += 1
            continue
        clock = hold_clock.read_clock(run)
        print(f"{run.name}: {png.name} ({clock['method']}{', FLAGGED' if clock['flagged'] else ''})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

