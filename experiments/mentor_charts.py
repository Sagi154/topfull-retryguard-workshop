"""
mentor_charts.py — Orchestration script: reads
experiments/results/campaign_48/ and writes two sets of PNG charts:
  - "Guides and Info/mentor-update/charts/"          curated subset (embedded in the doc)
  - "Guides and Info/mentor-update/charts_gallery/"  every endpoint/service/metric combination

Run (from repo root):
    python experiments/mentor_charts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mentor_charts_data as mcd
import mentor_charts_plots as mcp

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_ROOT = REPO_ROOT / "experiments" / "results" / "campaign_48"
CURATED_ROOT = REPO_ROOT / "Guides and Info" / "mentor-update" / "charts"
GALLERY_ROOT = REPO_ROOT / "Guides and Info" / "mentor-update" / "charts_gallery"

# Scenarios with no single named bottleneck endpoint: only the system-wide
# total.csv view is generated (curated == gallery for these three metrics).
SCENARIOS: dict[str, dict] = {
    "S1_normal_op": {
        "baseline_prefix": "baseline_topfull_no_retryguard_normal_op",
        "rg_prefix": "run_topfull_retryguard_normal_op",
    },
    "S2_sustained_overload": {
        "baseline_prefix": "baseline_topfull_no_retryguard_sustained_overload",
        "rg_prefix": "run_topfull_retryguard_sustained_overload",
    },
    "S6_forced_recovery": {
        "baseline_prefix": "baseline_topfull_no_retryguard_forced_recovery",
        "rg_prefix": "run_topfull_retryguard_forced_recovery",
    },
}

_METRIC_LABELS = {
    "goodput": "Goodput (req/s)",
    "p95_latency": "P95 latency (ms)",
    "rejection_rate": "Rejection rate",
}


def _load_group_average(run_dirs: list[Path], csv_name: str, metric: str) -> "pd.DataFrame":
    if metric == "rejection_rate":
        series_list = mcd.rejection_rate_series(run_dirs, csv_name)
    else:
        column = {"goodput": "Goodput", "p95_latency": "Latency95"}[metric]
        series_list = mcd.load_metric_column(run_dirs, csv_name, column)
    return mcd.average_series(series_list)


def _first_toggle_events(run_dirs: list[Path]) -> list[dict]:
    for run_dir in run_dirs:
        log_path = run_dir / "retryguard.log"
        if log_path.exists():
            return mcd.parse_toggle_events(log_path)
    return []


def generate_simple_scenario(
    scenario_key: str, campaign_root: Path, curated_dir: Path, gallery_dir: Path
) -> None:
    """Generate the system-wide (total.csv) Goodput/P95/Rejection charts
    for a scenario with no bottleneck-endpoint split (S1, S2, S6). Writes
    identical output to curated_dir and gallery_dir (there is nothing
    additional to show in the gallery for these three scenarios beyond
    what the doc already embeds)."""
    config = SCENARIOS[scenario_key]
    scenario_dir = campaign_root / scenario_key
    baseline_dirs = mcd.find_run_dirs(scenario_dir, config["baseline_prefix"])
    rg_dirs = mcd.find_run_dirs(scenario_dir, config["rg_prefix"])
    toggle_events = _first_toggle_events(rg_dirs)

    for metric, ylabel in _METRIC_LABELS.items():
        baseline_avg = _load_group_average(baseline_dirs, "total.csv", metric)
        rg_avg = _load_group_average(rg_dirs, "total.csv", metric)
        for target_dir in (curated_dir, gallery_dir):
            out_path = target_dir / scenario_key / f"total_{metric}.png"
            mcp.plot_timeseries_comparison(
                baseline_avg,
                rg_avg,
                title=f"{scenario_key} — {ylabel} (system-wide)",
                ylabel=ylabel,
                out_path=out_path,
                toggle_events=toggle_events,
            )


def main() -> None:
    for scenario_key in ("S1_normal_op", "S2_sustained_overload", "S6_forced_recovery"):
        generate_simple_scenario(scenario_key, CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT)
        print(f"Generated charts for {scenario_key}")


if __name__ == "__main__":
    main()
