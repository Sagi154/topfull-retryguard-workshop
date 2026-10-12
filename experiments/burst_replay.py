"""
burst_replay.py - read-only replay of RetryGuard burst mode over finished runs.

Reads service_edges.csv from each run folder and counts how often the burst
test (sliding window, volume floor, bar at 3 attempts) would have fired, using
the same BurstWindow code as the live controller. Recovery is not modelled:
the edge is assumed to stay at 3 attempts and the window is cleared after each
fire. Only the FIRST fire per edge predicts a live run; later fires assume
instant recovery.

Usage:
    python experiments/burst_replay.py RUN_DIR [RUN_DIR ...] \
        [--bars 1.0 1.5 2.0] [--window 5] [--min-first 20] [--edge frontend->checkoutservice]
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import types
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # retryguard.py imports kubernetes at module scope; replay never uses it.
    import kubernetes  # noqa: F401
except ImportError:
    _k = types.ModuleType("kubernetes")
    _client = types.ModuleType("kubernetes.client")
    _rest = types.ModuleType("kubernetes.client.rest")
    _config = types.ModuleType("kubernetes.config")
    _client.CustomObjectsApi = type("CustomObjectsApi", (), {})
    _rest.ApiException = type("ApiException", (Exception,), {})
    _k.client, _k.config = _client, _config
    sys.modules.update({
        "kubernetes": _k, "kubernetes.client": _client,
        "kubernetes.client.rest": _rest, "kubernetes.config": _config,
    })

import retryguard  # noqa: E402


def load_edges(run_dir: Path) -> dict:
    """{(caller, target): [EdgeSnapshot, ...]} sorted by time, from service_edges.csv."""
    out: dict = defaultdict(list)
    with open(run_dir / "service_edges.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                snap = retryguard.EdgeSnapshot(
                    row["timestamp"], float(row["total"]), float(row["retry"]),
                )
            except (KeyError, ValueError):
                continue
            out[(row["caller"], row["target"])].append(snap)
    return out


def replay_edge(snapshots, burst_rpr: float, window_s: int, min_first: int) -> list:
    """Timestamps where the burst test would fire at 3 attempts. Window clears after a fire."""
    window = retryguard.BurstWindow(window_s, min_first)
    fires = []
    previous = None
    for current in snapshots:
        delta = retryguard.edge_tick_deltas(previous, current)
        previous = current
        if delta is None:
            continue
        window.add(current.timestamp, delta[0], delta[1])
        value = window.rpr()
        if value is not None and value >= burst_rpr:
            fires.append(current.timestamp)
            window.clear()
    return fires


def window_first_sums(snapshots, window_s: int) -> list:
    """Sum of first attempts per sliding window, to sanity-check the volume floor."""
    window = retryguard.BurstWindow(window_s, 0)
    sums = []
    previous = None
    for current in snapshots:
        delta = retryguard.edge_tick_deltas(previous, current)
        previous = current
        if delta is None:
            continue
        window.add(current.timestamp, delta[0], delta[1])
        sums.append(sum(t[2] for t in window._ticks))
    return sums


def offset_s(first_row: str, ts: str) -> int:
    return int(
        (retryguard.parse_row_timestamp(ts) - retryguard.parse_row_timestamp(first_row))
        .total_seconds()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--bars", nargs="+", type=float, default=[1.0, 1.5, 2.0])
    parser.add_argument("--window", type=int, default=retryguard.BURST_WINDOW_SECONDS_DEFAULT)
    parser.add_argument("--min-first", type=int, default=retryguard.BURST_MIN_FIRST_ATTEMPTS_DEFAULT)
    parser.add_argument("--edge", default=None, help="caller->target; default all edges")
    args = parser.parse_args()

    print(f"window={args.window}s min_first={args.min_first} (bar is at 3 attempts)\n")
    print("| Run | Bar | Edge | Fires | First fire (s from first row) |")
    print("| --- | ---: | --- | ---: | ---: |")
    for run_dir in args.run_dirs:
        edges = load_edges(run_dir)
        for bar in args.bars:
            for (caller, target), snaps in sorted(edges.items()):
                name = f"{caller}->{target}"
                if args.edge and name != args.edge:
                    continue
                fires = replay_edge(snaps, bar, args.window, args.min_first)
                if not fires:
                    continue
                first = offset_s(snaps[0].timestamp, fires[0])
                print(f"| {run_dir.name} | {bar:.1f} | {name} | {len(fires)} | {first} |")

    focus = args.edge or "frontend->checkoutservice"
    print(f"\nWindow first-attempt sums on {focus} (is the floor {args.min_first} sane?)")
    for run_dir in args.run_dirs:
        edges = load_edges(run_dir)
        caller, target = focus.split("->")
        sums = window_first_sums(edges.get((caller, target), []), args.window)
        if sums:
            ordered = sorted(sums)
            p5 = ordered[int(0.05 * (len(ordered) - 1))]
            print(
                f"{run_dir.name}: median={statistics.median(sums):.0f} "
                f"p5={p5:.0f} min={min(sums):.0f}"
            )


if __name__ == "__main__":
    main()
