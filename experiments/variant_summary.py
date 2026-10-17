"""Goodput and effective-cap percentage per Locust API, per run and per variant.

    python experiments/variant_summary.py <run_dir-or-variant_dir> [...]

A path that contains run_manifest.json is one run. A path whose children are runs
is a variant directory; those runs are included. Runs are grouped by
<scenario>/<variant> (the two parent folders).

Each run table, per API:
  mean_goodput, median_goodput     Locust Goodput on seconds with RPS > 0
  mean_effective_pct               100 * mean(min(cap, offered)) / mean(offered)
  median_effective_pct             the same with medians

The variant table gives each run equal weight:
  mean_goodput          mean of the runs' mean goodputs
  median_goodput        median of the runs' median goodputs
  mean_effective_pct    recomputed from the mean of the run means (offered and effective)
  median_effective_pct  recomputed from the median of the run medians

TopFull-off runs have goodput and a blank percentage. The definitions match
locust_goodput.py, topfull_cap_avg.py, and topfull_cap_median.py.
postcart and emptycart are left out. This summary is getproduct, getcart, and postcheckout.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import locust_goodput  # noqa: E402
import topfull_cap_avg as avg  # noqa: E402
import topfull_cap_median as med  # noqa: E402

# postcart and emptycart are left out of this summary.
APIS = ("getproduct", "getcart", "postcheckout")
FIELDS = ("mean_goodput", "median_goodput", "mean_effective_pct", "median_effective_pct")


def is_run(path: Path) -> bool:
    return (path / "run_manifest.json").is_file() or (path / "getproduct.csv").is_file()


def variant_name(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    return f"{run_dir.parent.parent.name}/{run_dir.parent.name}"


def collect_runs(paths: list[Path]) -> list[Path]:
    found = []
    for path in paths:
        path = Path(path)
        if is_run(path):
            found.append(path)
            continue
        if path.is_dir():
            found.extend(child for child in sorted(path.iterdir()) if child.is_dir() and is_run(child))
    return found


def group_runs(paths: list[Path]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {}
    for run in collect_runs(paths):
        grouped.setdefault(variant_name(run), []).append(run)
    for runs in grouped.values():
        runs.sort(key=lambda path: path.name)
    return dict(sorted(grouped.items()))


def load_run(run_dir: Path) -> tuple[dict, dict | None, dict | None]:
    good = {
        api: locust_goodput.summarize(values)
        for api, values in locust_goodput.goodput_values(run_dir).items()
    }
    series = avg.series_by_api(run_dir)
    if not series:
        return good, None, None
    return (
        good,
        {api: avg.api_summary(*parts) for api, parts in series.items()},
        {api: med.api_summary(*parts) for api, parts in series.items()},
    )


def run_metrics(good: dict, avg_sum: dict | None, med_sum: dict | None) -> dict:
    out = {}
    for api in APIS:
        if api not in good and not (avg_sum and api in avg_sum):
            continue
        out[api] = {
            "mean_goodput": good.get(api, {}).get("mean_goodput"),
            "median_goodput": good.get(api, {}).get("median_goodput"),
            "mean_effective_pct": avg.effective_pct(avg_sum[api]) if avg_sum and api in avg_sum else None,
            "median_effective_pct": med.effective_pct(med_sum[api]) if med_sum and api in med_sum else None,
        }
    return out


def variant_metrics(loaded: list[tuple[dict, dict | None, dict | None]]) -> dict:
    """Equal weight per run. Percentages are recomputed from the aggregated caps."""
    goods = [item[0] for item in loaded]
    cell_avg = avg.cell_mean([item[1] for item in loaded if item[1]])
    cell_med = med.cell_median([item[2] for item in loaded if item[2]])
    out = {}
    for api in APIS:
        means = [g[api]["mean_goodput"] for g in goods if api in g and g[api]["mean_goodput"] is not None]
        medians = [g[api]["median_goodput"] for g in goods if api in g and g[api]["median_goodput"] is not None]
        if not means and api not in cell_avg:
            continue
        out[api] = {
            "mean_goodput": float(np.mean(means)) if means else None,
            "median_goodput": float(np.median(medians)) if medians else None,
            "mean_effective_pct": avg.effective_pct(cell_avg[api]) if api in cell_avg else None,
            "median_effective_pct": med.effective_pct(cell_med[api]) if api in cell_med else None,
        }
    return out


def _f(value) -> str:
    return "-" if value is None else f"{value:.1f}"


def render(title: str, summary: dict) -> str:
    head = ["api", *FIELDS]
    lines = [title, " | ".join(head), " | ".join("---" for _ in head)]
    for api in APIS:
        if api in summary:
            lines.append(" | ".join([api, *(_f(summary[api][k]) for k in FIELDS)]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print(__doc__.split("\n")[2].strip())
        return 1
    for name, runs in group_runs(paths).items():
        loaded = [load_run(run) for run in runs]
        print(render(f"{name}  ({len(runs)} runs, equal weight)", variant_metrics(loaded)))
        print()
        for run, item in zip(runs, loaded):
            print(render(run.name, run_metrics(*item)))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
