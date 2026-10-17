"""Median effective TopFull cap per Locust entry API, for one or more run folders.

    python experiments/topfull_cap_median.py <run_dir> [<run_dir> ...] [--csv out.csv]

Same seconds and same effective value as topfull_cap_avg.py (see TOPFULL-CAP-AVG.md).
The summary is the median instead of the mean. An even count uses the midpoint of the
two central values. effective_pct is 100 * median_effective / median_offered on that
row, including the cell row. Several folders print the median of the per-run medians
(with two runs, that is the midpoint of the two).
A TopFull-off run is skipped.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cap_avg as avg  # noqa: E402

APIS = avg.APIS
FIELDS = ("rows", "capped_s", "nocap_s", "empty_s", "unknown_s",
          "median_offered", "median_effective", "median_cap_when_capped")


def _median(values) -> float | None:
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return None
    return float(np.median(values))


def api_summary(rps, kinds, caps) -> dict:
    rps = np.asarray(rps, dtype=float)
    capped = kinds == "capped"
    nocap = kinds == "nocap"
    used = capped | nocap
    effective = np.where(capped, np.minimum(caps, rps), rps)
    return {
        "rows": int(rps.size),
        "capped_s": int(capped.sum()),
        "nocap_s": int(nocap.sum()),
        "empty_s": int((kinds == "empty").sum()),
        "unknown_s": int((kinds == "unknown").sum()),
        "median_offered": _median(rps[used]),
        "median_effective": _median(effective[used]),
        "median_cap_when_capped": _median(caps[capped]),
    }


def run_summary(run_dir: Path) -> dict | None:
    series = avg.series_by_api(run_dir)
    if series is None:
        return None
    return {api: api_summary(*parts) for api, parts in series.items()}


def cell_median(runs: list[dict]) -> dict:
    """Median of each run's per-API numbers (None values skipped)."""
    out = {}
    for api in APIS:
        parts = [r[api] for r in runs if api in r]
        if not parts:
            continue
        out[api] = {}
        for key in FIELDS:
            vals = [p[key] for p in parts if p[key] is not None]
            out[api][key] = _median(vals)
    return out


def effective_pct(row: dict) -> float | None:
    """100 * median_effective / median_offered. None when offered is missing or 0."""
    offered, effective = row.get("median_offered"), row.get("median_effective")
    if offered is None or effective is None or offered == 0:
        return None
    return 100.0 * effective / offered


def _f(v) -> str:
    return "-" if v is None else (f"{v:.1f}" if isinstance(v, float) else str(v))


def render(title: str, summary: dict) -> str:
    head = ["api", *FIELDS, "effective_pct"]
    lines = [title, " | ".join(head), " | ".join("---" for _ in head)]
    for api in APIS:
        if api in summary:
            row = summary[api]
            lines.append(" | ".join([api, *(_f(row[k]) for k in FIELDS), _f(effective_pct(row))]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--csv", help="write one row per run and API here")
    args = parser.parse_args(argv)
    done: dict[str, dict] = {}
    for run in args.runs:
        summary = run_summary(Path(run))
        name = Path(run).name
        if summary is None:
            print(f"{name}: skipped (TopFull off or no topfull_throttle.csv)\n")
            continue
        done[name] = summary
        print(render(name, summary) + "\n")
    if len(done) > 1:
        print(render(
            f"cell median of {len(done)} runs (median of run medians)",
            cell_median(list(done.values()))))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["run", "api", *FIELDS, "effective_pct"])
            for name, summary in done.items():
                for api, row in summary.items():
                    writer.writerow([name, api, *(row[k] for k in FIELDS), effective_pct(row)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
