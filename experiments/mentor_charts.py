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

import pandas as pd

import mentor_charts_data as mcd
import mentor_charts_plots as mcp

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_ROOT = REPO_ROOT / "experiments" / "results" / "campaign_48"
CURATED_ROOT = REPO_ROOT / "Guides and Info" / "mentor-update" / "charts"
GALLERY_ROOT = REPO_ROOT / "Guides and Info" / "mentor-update" / "charts_gallery"

SCENARIOS: dict[str, dict] = {
    "S1_normal_op": {
        "baseline_prefix": "baseline_topfull_no_retryguard_normal_op",
        "rg_prefix": "run_topfull_retryguard_normal_op",
    },
    "S2_sustained_overload": {
        "baseline_prefix": "baseline_topfull_no_retryguard_sustained_overload",
        "rg_prefix": "run_topfull_retryguard_sustained_overload",
    },
    "S3_targeted_bottleneck": {
        "baseline_prefix": "baseline_topfull_no_retryguard_targeted_bottleneck",
        "rg_prefix": "run_topfull_retryguard_targeted_bottleneck",
        "bottleneck_csv": "postcheckout.csv",
    },
    "S4A_topology_position_A": {
        "baseline_prefix": "baseline_topfull_no_retryguard_topology_position_A",
        "rg_prefix": "run_topfull_retryguard_topology_position_A",
        "bottleneck_csv": "getproduct.csv",
    },
    "S4B_topology_position_B": {
        "baseline_prefix": "baseline_topfull_no_retryguard_topology_position_B",
        "rg_prefix": "run_topfull_retryguard_topology_position_B",
        "bottleneck_csv": "postcheckout.csv",
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

# Locust CSVs are 1 row/second; plot every Nth second so comparison
# charts are less dense. Envoy/resource charts poll ~5s — downsample
# those to one point per COLLECTOR_PLOT_STEP_SECONDS of elapsed time.
LOCUST_PLOT_STEP_SECONDS = 10
COLLECTOR_PLOT_STEP_SECONDS = 20


def _load_group_average(run_dirs: list[Path], csv_name: str, metric: str) -> "pd.DataFrame":
    if metric == "rejection_rate":
        series_list = mcd.rejection_rate_series(run_dirs, csv_name)
    else:
        column = {"goodput": "Goodput", "p95_latency": "Latency95"}[metric]
        series_list = mcd.load_metric_column(run_dirs, csv_name, column)
    averaged = mcd.average_series(series_list)
    # Real Locust CSVs have RPS=0 rows; rejection_rate_series uses pd.NA there,
    # so mean/min/max can be object dtype and matplotlib fill_between raises.
    if not averaged.empty:
        averaged = averaged.astype("float64")
    return mcd.downsample_series(averaged, LOCUST_PLOT_STEP_SECONDS)


def _collect_toggle_events(run_dirs: list[Path]) -> list[dict]:
    collected: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for run_dir in run_dirs:
        log_path = run_dir / "retryguard.log"
        if not log_path.exists():
            continue
        for event in mcd.parse_toggle_events(log_path):
            key = (event["service"], event["direction"], round(event["elapsed_seconds"]))
            if key in seen:
                continue
            seen.add(key)
            collected.append(event)
    collected.sort(key=lambda e: e["elapsed_seconds"])
    return collected


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
    toggle_events = _collect_toggle_events(rg_dirs)

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


def generate_bottleneck_scenario(
    scenario_key: str, campaign_root: Path, curated_dir: Path, gallery_dir: Path
) -> None:
    """Like generate_simple_scenario, plus a second Goodput/P95/Rejection
    panel for the scenario's bottleneck endpoint (S3, S4A, S4B)."""
    generate_simple_scenario(scenario_key, campaign_root, curated_dir, gallery_dir)

    config = SCENARIOS[scenario_key]
    bottleneck_csv = config["bottleneck_csv"]
    endpoint_name = Path(bottleneck_csv).stem
    scenario_dir = campaign_root / scenario_key
    baseline_dirs = mcd.find_run_dirs(scenario_dir, config["baseline_prefix"])
    rg_dirs = mcd.find_run_dirs(scenario_dir, config["rg_prefix"])
    toggle_events = _collect_toggle_events(rg_dirs)

    for metric, ylabel in _METRIC_LABELS.items():
        baseline_avg = _load_group_average(baseline_dirs, bottleneck_csv, metric)
        rg_avg = _load_group_average(rg_dirs, bottleneck_csv, metric)
        for target_dir in (curated_dir, gallery_dir):
            out_path = target_dir / scenario_key / f"{endpoint_name}_{metric}.png"
            mcp.plot_timeseries_comparison(
                baseline_avg,
                rg_avg,
                title=f"{scenario_key} — {ylabel} ({endpoint_name})",
                ylabel=ylabel,
                out_path=out_path,
                toggle_events=toggle_events,
            )


def generate_retries_and_resources(
    scenario_key: str,
    config: dict,
    campaign_root: Path,
    curated_dir: Path,
    gallery_dir: Path,
) -> None:
    """Generate the retries-per-request (per-target and summed views, for
    each of the two Envoy-instrumented callers) and CPU/memory overlay
    charts for one scenario group. Used for every scenario, including
    S1/S2/S6 which have no bottleneck endpoint but still have retries
    and resource data."""
    scenario_dir = campaign_root / scenario_key
    rg_dirs = mcd.find_run_dirs(scenario_dir, config["rg_prefix"])
    if not rg_dirs:
        return

    for caller_csv in ("envoy_retries_frontend.csv", "envoy_retries_checkoutservice.csv"):
        caller_name = Path(caller_csv).stem
        per_repeat = [
            mcd.envoy_retries_per_request(run_dir, caller_csv)
            for run_dir in rg_dirs
            if (run_dir / caller_csv).exists()
        ]
        if not per_repeat:
            continue
        averaged = mcd.downsample_series(
            mcd.average_dataframes(per_repeat), COLLECTOR_PLOT_STEP_SECONDS
        )
        per_target_columns = [c for c in averaged.columns if c != "total"]
        for target_dir in (curated_dir, gallery_dir):
            mcp.plot_multi_line(
                averaged[per_target_columns],
                title=f"{scenario_key} — {caller_name} retries/request per target",
                ylabel="Retries per request",
                out_path=target_dir / scenario_key / f"{caller_name}_per_target.png",
            )
            mcp.plot_multi_line(
                averaged[["total"]],
                title=f"{scenario_key} — {caller_name} retries/request (summed)",
                ylabel="Retries per request",
                out_path=target_dir / scenario_key / f"{caller_name}_summed.png",
            )

    for column, label in (
        ("cpu_millicores", "CPU (millicores)"),
        ("memory_working_set_bytes", "Memory (bytes)"),
    ):
        per_repeat = [mcd.resource_usage_series(run_dir, column) for run_dir in rg_dirs]
        averaged = mcd.downsample_series(
            mcd.average_dataframes(per_repeat), COLLECTOR_PLOT_STEP_SECONDS
        )
        for target_dir in (curated_dir, gallery_dir):
            mcp.plot_multi_line(
                averaged,
                title=f"{scenario_key} — {label} per service (RetryGuard run)",
                ylabel=label,
                out_path=target_dir / scenario_key / f"resource_{column}.png",
            )


def generate_s4_combined(campaign_root: Path, curated_dir: Path, gallery_dir: Path) -> None:
    """Generate the combined S4A-vs-S4B side-by-side Goodput/P95/Rejection
    charts (system-wide total.csv only; the bottleneck-endpoint panels
    for A and B individually are still produced by
    generate_bottleneck_scenario for each)."""
    config_a = SCENARIOS["S4A_topology_position_A"]
    config_b = SCENARIOS["S4B_topology_position_B"]
    dir_a = campaign_root / "S4A_topology_position_A"
    dir_b = campaign_root / "S4B_topology_position_B"

    baseline_a = mcd.find_run_dirs(dir_a, config_a["baseline_prefix"])
    rg_a = mcd.find_run_dirs(dir_a, config_a["rg_prefix"])
    baseline_b = mcd.find_run_dirs(dir_b, config_b["baseline_prefix"])
    rg_b = mcd.find_run_dirs(dir_b, config_b["rg_prefix"])

    for metric, ylabel in _METRIC_LABELS.items():
        pair_a = (
            _load_group_average(baseline_a, "total.csv", metric),
            _load_group_average(rg_a, "total.csv", metric),
        )
        pair_b = (
            _load_group_average(baseline_b, "total.csv", metric),
            _load_group_average(rg_b, "total.csv", metric),
        )
        for target_dir in (curated_dir, gallery_dir):
            mcp.plot_side_by_side_comparison(
                pair_a=pair_a,
                pair_b=pair_b,
                title=f"Scenario 4 — {ylabel} (system-wide)",
                ylabel=ylabel,
                label_a="S4A: ProductCatalog constrained",
                label_b="S4B: Payment constrained",
                out_path=target_dir / "S4_topology_position" / f"total_{metric}.png",
            )


_S5_INTERVALS = ("10s", "20s", "30s", "60s")


def generate_s5_s6_merge(
    campaign_root: Path, curated_dir: Path, gallery_dir: Path
) -> tuple[Path, Path]:
    """Generate the S6 recovery-phase Goodput/Rejection overlay charts
    with 6 lines (baseline, RetryGuard, and the 4 S5 interval variants),
    plus a disable/re-enable toggle-timeline markdown table comparing
    all six run groups. Returns (goodput_chart_path, rejection_chart_path)."""
    s6_config = SCENARIOS["S6_forced_recovery"]
    s6_dir = campaign_root / "S6_forced_recovery"
    s5_dir = campaign_root / "S5_interval_tuning"

    groups: dict[str, list[Path]] = {
        "Baseline (S6)": mcd.find_run_dirs(s6_dir, s6_config["baseline_prefix"]),
        "RetryGuard (S6, 30s default)": mcd.find_run_dirs(s6_dir, s6_config["rg_prefix"]),
    }
    for interval in _S5_INTERVALS:
        groups[f"RetryGuard interval {interval}"] = mcd.find_run_dirs(
            s5_dir, f"run_topfull_retryguard_interval_{interval}"
        )

    chart_paths = {}
    for metric, ylabel in (("goodput", _METRIC_LABELS["goodput"]), ("rejection_rate", _METRIC_LABELS["rejection_rate"])):
        fig_columns = {}
        for label, run_dirs in groups.items():
            if not run_dirs:
                continue
            avg = _load_group_average(run_dirs, "total.csv", metric)
            if not avg.empty:
                fig_columns[label] = avg["mean"]
        combined = pd.DataFrame(fig_columns)
        for target_dir in (curated_dir, gallery_dir):
            out_path = target_dir / "S6_forced_recovery" / f"s5_s6_{metric}_by_interval.png"
            mcp.plot_multi_line(
                combined,
                title=f"S6 recovery load — {ylabel} by re-enable interval",
                ylabel=ylabel,
                out_path=out_path,
            )
            if target_dir is curated_dir:
                chart_paths[metric] = out_path

    timeline_rows = ["| Run group | Toggle events (elapsed s, service, direction) |", "|---|---|"]
    for label, run_dirs in groups.items():
        events_by_run = []
        for run_dir in run_dirs:
            log_path = run_dir / "retryguard.log"
            if log_path.exists():
                events = mcd.parse_toggle_events(log_path)
                formatted = "; ".join(
                    f"{e['elapsed_seconds']:.0f}s {e['service']} {e['direction']}" for e in events
                )
                events_by_run.append(f"{run_dir.name}: {formatted or 'none'}")
        timeline_rows.append(f"| {label} | {' <br> '.join(events_by_run) or 'n/a'} |")

    timeline_path = curated_dir / "S6_forced_recovery" / "s5_toggle_timeline.md"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline_path.write_text("\n".join(timeline_rows) + "\n", encoding="utf-8")

    return chart_paths["goodput"], chart_paths["rejection_rate"]


def main() -> None:
    simple_scenarios = ("S1_normal_op", "S2_sustained_overload", "S6_forced_recovery")
    bottleneck_scenarios = ("S3_targeted_bottleneck", "S4A_topology_position_A", "S4B_topology_position_B")

    for scenario_key in simple_scenarios:
        generate_simple_scenario(scenario_key, CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT)
        print(f"Generated system-wide charts for {scenario_key}")

    for scenario_key in bottleneck_scenarios:
        generate_bottleneck_scenario(scenario_key, CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT)
        print(f"Generated system-wide + bottleneck-endpoint charts for {scenario_key}")

    for scenario_key in simple_scenarios + bottleneck_scenarios:
        generate_retries_and_resources(
            scenario_key, SCENARIOS[scenario_key], CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT
        )
        print(f"Generated retries/resource charts for {scenario_key}")

    generate_s4_combined(CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT)
    print("Generated S4 combined side-by-side charts")

    generate_s5_s6_merge(CAMPAIGN_ROOT, CURATED_ROOT, GALLERY_ROOT)
    print("Generated S5 interval sweep merged into S6")


if __name__ == "__main__":
    main()
