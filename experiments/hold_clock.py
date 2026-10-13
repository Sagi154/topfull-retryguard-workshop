"""Hold clock for one run folder.

The hold clock is seconds since the first Locust row, in master's UTC.
Locust CSVs from before the timestamp patch have no clock column, so each
run gets a Locust clock fit: a start time plus a row spacing, anchored on
the first and last moment load is above 20% of its median in both Locust
RPS and the frontend inbound rate. Design:
docs/superpowers/specs/2026-10-13-hold-clock-design.md.

    python experiments/hold_clock.py <run_dir> [<run_dir> ...]
    python experiments/hold_clock.py --tree "experiments/results/final results"

Writes locust_clock.json into each run folder and prints one line per run.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

CLOCK_JSON = "locust_clock.json"
LOCUST_FILES = ("total", "getproduct", "postcheckout", "getcart", "postcart", "emptycart")
COLLECTOR_FILES = (
    "service_inbound",
    "service_edges",
    "resource_usage",
    "topfull_throttle",
    "topfull_detect",
)
LOAD_FRACTION = 0.2
MIN_CORRELATION = 0.8


def parse_utc(value: str) -> float:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def format_utc(epoch: float) -> str:
    moment = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def epochs(column: pd.Series) -> np.ndarray:
    text = column.astype(str)
    lookup = {value: parse_utc(value) for value in text.unique()}
    return text.map(lookup).to_numpy(dtype=float)


def frontend_rate(inbound: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Frontend inbound arrival rate per poll gap, stamped at the later poll."""
    rows = inbound[inbound["service"] == "frontend"]
    t = epochs(rows["timestamp"])
    total = rows["total"].to_numpy(dtype=float)
    order = np.argsort(t, kind="stable")
    t, total = t[order], total[order]
    dt = np.diff(t)
    delta = np.diff(total)
    keep = (dt > 0) & (delta >= 0)
    return t[1:][keep], delta[keep] / dt[keep]


def load_span(values: np.ndarray) -> tuple[int, int] | None:
    positive = values[values > 0]
    if positive.size == 0:
        return None
    above = np.flatnonzero(values > LOAD_FRACTION * np.median(positive))
    if above.size < 2:
        return None
    return int(above[0]), int(above[-1])


def fit_from_anchors(
    locust_rps: np.ndarray, mesh_t: np.ndarray, mesh_rate: np.ndarray
) -> dict | None:
    rows = load_span(locust_rps)
    mesh = load_span(mesh_rate)
    if rows is None or mesh is None or rows[1] == rows[0]:
        return None
    first_t, last_t = float(mesh_t[mesh[0]]), float(mesh_t[mesh[1]])
    spacing = (last_t - first_t) / (rows[1] - rows[0])
    return {
        "start_epoch": first_t - rows[0] * spacing,
        "spacing_s": spacing,
        "anchor_rows": [rows[0], rows[1]],
        "anchor_epochs": [first_t, last_t],
    }


def correlation(
    locust_rps: np.ndarray, row_epochs: np.ndarray, mesh_t: np.ndarray, mesh_rate: np.ndarray
) -> float | None:
    if mesh_t.size < 2:
        return None
    inside = (row_epochs >= mesh_t[0]) & (row_epochs <= mesh_t[-1])
    if inside.sum() < 3:
        return None
    a = locust_rps[inside]
    b = np.interp(row_epochs[inside], mesh_t, mesh_rate)
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _flagged(corr: float | None) -> bool:
    return corr is None or corr < MIN_CORRELATION


def compute_clock(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    total = read_csv(run_dir / "total.csv")
    inbound = read_csv(run_dir / "service_inbound.csv")
    if total.empty:
        raise ValueError(f"{run_dir}: total.csv missing or empty")
    if inbound.empty:
        raise ValueError(f"{run_dir}: service_inbound.csv missing or empty")
    rps = total["RPS"].to_numpy(dtype=float)
    mesh_t, mesh_rate = frontend_rate(inbound)
    fit = fit_from_anchors(rps, mesh_t, mesh_rate)

    if "timestamp" in total.columns:
        stamps = epochs(total["timestamp"])
        corr = correlation(rps, stamps, mesh_t, mesh_rate)
        check = None
        if fit is not None:
            first_row, last_row = fit["anchor_rows"]
            check = {
                "start_error_s": float(fit["start_epoch"] - stamps[0]),
                "anchor_errors_s": [
                    float(fit["anchor_epochs"][0] - stamps[first_row]),
                    float(fit["anchor_epochs"][1] - stamps[last_row]),
                ],
                "spacing_s": float(fit["spacing_s"]),
            }
        return {
            "method": "stamped",
            "start_utc": format_utc(stamps[0]),
            "spacing_s": float(np.median(np.diff(stamps))) if stamps.size > 1 else None,
            "rows": int(stamps.size),
            "correlation": corr,
            "flagged": _flagged(corr),
            "fit_check": check,
        }

    if fit is None:
        raise ValueError(f"{run_dir}: no load start/stop found to anchor the fit")
    row_epochs = fit["start_epoch"] + np.arange(rps.size) * fit["spacing_s"]
    corr = correlation(rps, row_epochs, mesh_t, mesh_rate)
    return {
        "method": "fit",
        "start_utc": format_utc(fit["start_epoch"]),
        "spacing_s": float(fit["spacing_s"]),
        "rows": int(rps.size),
        "anchor_rows": fit["anchor_rows"],
        "anchor_utc": [format_utc(e) for e in fit["anchor_epochs"]],
        "correlation": corr,
        "flagged": _flagged(corr),
    }


def write_clock(run_dir: Path) -> dict:
    clock = compute_clock(run_dir)
    (Path(run_dir) / CLOCK_JSON).write_text(json.dumps(clock, indent=2) + "\n", encoding="utf-8")
    return clock


def read_clock(run_dir: Path) -> dict:
    path = Path(run_dir) / CLOCK_JSON
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return write_clock(run_dir)


def zero_epoch(clock: dict) -> float:
    return parse_utc(clock["start_utc"])


def locust_epochs(df: pd.DataFrame, clock: dict) -> np.ndarray:
    if "timestamp" in df.columns:
        return epochs(df["timestamp"])
    return zero_epoch(clock) + np.arange(len(df)) * float(clock["spacing_s"])


def _safe_epoch(value: str) -> float:
    try:
        return parse_utc(value)
    except ValueError:
        return float("nan")


def retryguard_rows(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        row = {"timestamp": parts[0], "line": line}
        if parts[1] == "OBSERVE" and len(parts) >= 3:
            row.update(kind="OBSERVE", name=parts[2])
            fields = parts[3:]
        elif len(parts) >= 3 and ("→" in parts[2] or "->" in parts[2]):
            row.update(kind="switch", name=parts[1], step=parts[2].replace("->", "→"))
            fields = parts[3:]
        else:
            row["kind"] = parts[1]
            fields = parts[2:]
        for token in fields:
            if "=" in token:
                key, value = token.split("=", 1)
                row.setdefault(key, value)
        rows.append(row)
    return pd.DataFrame(rows)


def load_source(run_dir: Path, name: str, clock: dict | None = None) -> pd.DataFrame:
    run_dir = Path(run_dir)
    clock = clock or read_clock(run_dir)
    zero = zero_epoch(clock)
    if name in LOCUST_FILES:
        df = read_csv(run_dir / f"{name}.csv")
        if not df.empty:
            df["hold_s"] = locust_epochs(df, clock) - zero
        return df
    if name in COLLECTOR_FILES:
        df = read_csv(run_dir / f"{name}.csv")
        if not df.empty:
            df["hold_s"] = epochs(df["timestamp"]) - zero
        return df
    if name == "retryguard":
        path = run_dir / "retryguard.log"
        if not path.is_file():
            return pd.DataFrame()
        df = retryguard_rows(path.read_text(encoding="utf-8", errors="replace"))
        if not df.empty:
            df["hold_s"] = df["timestamp"].map(_safe_epoch) - zero
        return df
    raise ValueError(f"unknown source {name!r}")


def run_dirs(paths: list[str], tree: str | None) -> list[Path]:
    found = [Path(p) for p in paths]
    if tree:
        found += sorted(p.parent for p in Path(tree).rglob("total.csv"))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write locust_clock.json for run folders.")
    parser.add_argument("runs", nargs="*", help="Run folders")
    parser.add_argument("--tree", help="Every folder under this path that has total.csv")
    args = parser.parse_args(argv)
    failures = 0
    for run in run_dirs(args.runs, args.tree):
        try:
            clock = write_clock(run)
        except ValueError as exc:
            print(f"{run.name}: ERROR {exc}")
            failures += 1
            continue
        corr = clock["correlation"]
        corr_text = "n/a" if corr is None else f"{corr:.3f}"
        print(
            f"{run.name}: {clock['method']} start={clock['start_utc']} "
            f"spacing={clock['spacing_s']:.4f}s corr={corr_text} "
            f"{'FLAGGED' if clock['flagged'] else 'ok'}"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
