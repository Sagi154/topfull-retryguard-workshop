"""Average effective TopFull cap per Locust entry API, for one or more run folders.

    python experiments/topfull_cap_avg.py <run_dir> [<run_dir> ...] [--csv out.csv]

Walks every Locust row of each API, starting at the first row. For each row:
  - cap in force: the latest FRESH threshold read at or before the row, at most
    CARRY_S (6 s) old. A threshold of 9900 or more is no cap. A fresh 0 is an empty
    read. No read inside the carry window is unknown. Same rules as run_timeline.
  - effective = RPS            when there is no cap (nothing is blocked below demand)
                min(cap, RPS)  when there is a real cap
                (row left out)  when the cap is unknown or an empty read
RPS is the offered rate: Locust RPS already includes the failed requests (Goodput = RPS - Fail).
Mean effective is in req/s. effective_pct is 100 * mean_effective / mean_offered on that same row,
including the cell-mean row (ratio of the averaged means). Runs with several folders also
print the mean of the run means.
A TopFull-off run (run_manifest.json topfull_rl.enabled false) has no cap and is skipped.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import hold_clock  # noqa: E402

APIS = ("getproduct", "getcart", "postcart", "emptycart", "postcheckout")
NO_CAP = 9900.0
CARRY_S = 6.0
FIELDS = ("rows", "capped_s", "nocap_s", "empty_s", "unknown_s",
          "mean_offered", "mean_effective", "mean_cap_when_capped")


def classify(row_t, read_t, read_cap, carry_s: float = CARRY_S, no_cap: float = NO_CAP):
    """Per Locust row: (kind, cap). kind is capped, nocap, empty, or unknown."""
    row_t = np.asarray(row_t, dtype=float)
    read_t = np.asarray(read_t, dtype=float)
    read_cap = np.asarray(read_cap, dtype=float)
    kinds, caps = [], []
    for t in row_t:
        i = int(np.searchsorted(read_t, t, side="right")) - 1
        if i < 0 or t - read_t[i] > carry_s:
            kinds.append("unknown"); caps.append(np.nan)
        elif read_cap[i] <= 0:
            kinds.append("empty"); caps.append(np.nan)
        elif read_cap[i] >= no_cap:
            kinds.append("nocap"); caps.append(np.nan)
        else:
            kinds.append("capped"); caps.append(float(read_cap[i]))
    return np.array(kinds), np.array(caps)


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
        "mean_offered": float(rps[used].mean()) if used.any() else None,
        "mean_effective": float(effective[used].mean()) if used.any() else None,
        "mean_cap_when_capped": float(caps[capped].mean()) if capped.any() else None,
    }


def run_summary(run_dir: Path) -> dict | None:
    """{api: summary} for one run, or None when TopFull is off or has no throttle file."""
    run_dir = Path(run_dir)
    if not analysis_score.topfull_enabled(run_dir):
        return None
    clock = hold_clock.read_clock(run_dir)
    throttle = hold_clock.load_source(run_dir, "topfull_throttle", clock)
    if throttle.empty:
        return None
    out = {}
    for api in APIS:
        locust = hold_clock.load_source(run_dir, api, clock)
        group = throttle[throttle["api"] == api].sort_values("hold_s")
        if locust.empty or group.empty:
            continue
        reads = group[group["threshold_fresh"].astype(float) == 1]
        kinds, caps = classify(
            locust["hold_s"], reads["hold_s"].to_numpy(dtype=float),
            reads["threshold"].to_numpy(dtype=float))
        out[api] = api_summary(locust["RPS"].to_numpy(dtype=float), kinds, caps)
    return out


def cell_mean(runs: list[dict]) -> dict:
    """Mean of each run's per-API numbers (None values skipped)."""
    out = {}
    for api in APIS:
        parts = [r[api] for r in runs if api in r]
        if not parts:
            continue
        out[api] = {}
        for key in FIELDS:
            vals = [p[key] for p in parts if p[key] is not None]
            out[api][key] = float(np.mean(vals)) if vals else None
    return out


def effective_pct(row: dict) -> float | None:
    """100 * mean_effective / mean_offered. None when offered is missing or 0."""
    offered, effective = row.get("mean_offered"), row.get("mean_effective")
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
        print(render(f"cell mean of {len(done)} runs (mean of run means)", cell_mean(list(done.values()))))
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
