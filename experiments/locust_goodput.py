"""Mean and median Locust goodput per entry API, for one run or a variant's runs.

    python experiments/locust_goodput.py <run_dir> [<run_dir> ...] [--csv out.csv]

Goodput is the Locust Goodput column (RPS - Fail), per API file. Seconds with RPS
of 0 are left out, the same rows analysis_score.locust_table averages. An even
count uses the midpoint of the two central values.

One directory prints that run. Several directories are one variant: each run is
printed, then one pooled row per API, the mean and median of every scored second
from those runs.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402
import topfull_cap_avg as avg  # noqa: E402

APIS = avg.APIS
FIELDS = ("scored_s", "mean_goodput", "median_goodput")


def scored(rps, goodput) -> np.ndarray:
    """Goodput on seconds with RPS > 0."""
    rps = np.asarray(rps, dtype=float)
    goodput = np.asarray(goodput, dtype=float)
    return goodput[rps > 0]


def summarize(values) -> dict:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return {"scored_s": 0, "mean_goodput": None, "median_goodput": None}
    return {
        "scored_s": int(values.size),
        "mean_goodput": float(values.mean()),
        "median_goodput": float(np.median(values)),
    }


def goodput_values(run_dir: Path) -> dict[str, np.ndarray]:
    run_dir = Path(run_dir)
    out = {}
    for api in APIS:
        df = hold_clock.read_csv(run_dir / f"{api}.csv")
        if df.empty or "Goodput" not in df.columns or "RPS" not in df.columns:
            continue
        out[api] = scored(df["RPS"], df["Goodput"])
    return out


def run_summary(run_dir: Path) -> dict | None:
    values = goodput_values(run_dir)
    if not values:
        return None
    return {api: summarize(series) for api, series in values.items()}


def pooled_summary(run_dirs: list[Path]) -> dict:
    """Mean and median of every scored second from the given runs, per API."""
    buckets: dict[str, list] = {api: [] for api in APIS}
    for run_dir in run_dirs:
        for api, series in goodput_values(run_dir).items():
            buckets[api].append(series)
    return {
        api: summarize(np.concatenate(parts))
        for api, parts in buckets.items() if parts
    }


def _f(v) -> str:
    return "-" if v is None else (f"{v:.1f}" if isinstance(v, float) else str(v))


def render(title: str, summary: dict) -> str:
    head = ["api", *FIELDS]
    lines = [title, " | ".join(head), " | ".join("---" for _ in head)]
    for api in APIS:
        if api in summary:
            row = summary[api]
            lines.append(" | ".join([api, *(_f(row[k]) for k in FIELDS)]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--csv", help="write one row per run and API, then a pooled row")
    args = parser.parse_args(argv)
    done: dict[str, dict] = {}
    for run in args.runs:
        summary = run_summary(Path(run))
        name = Path(run).name
        if summary is None:
            print(f"{name}: skipped (no Locust API csv)\n")
            continue
        done[name] = summary
        print(render(name, summary) + "\n")
    if len(done) > 1:
        print(render(
            f"pooled across {len(done)} runs (every scored second)",
            pooled_summary([Path(run) for run in args.runs if Path(run).name in done])))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["run", "api", *FIELDS])
            for name, summary in done.items():
                for api, row in summary.items():
                    writer.writerow([name, api, *(row[k] for k in FIELDS)])
            if len(done) > 1:
                pooled = pooled_summary([Path(run) for run in args.runs if Path(run).name in done])
                for api, row in pooled.items():
                    writer.writerow([f"pooled_{len(done)}", api, *(row[k] for k in FIELDS)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
