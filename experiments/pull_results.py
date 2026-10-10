"""pull_results.py — scp a finished run's results down from topfull-master.

The rho report is retired. This command only pulls. Score the folder with
experiments/analysis_score.py.

This is the automated version of the manual step `run_scenario.py` prints at
the end of every run ("To pull results to your PC: scp -r ..."). It reuses
`run_scenario.scenario_dir_name()` for the local destination mapping, so the
scenario_id -> campaign_48/<subfolder> mapping lives in exactly one place.

Read-only w.r.t. the remote VMs: this only runs `scp -r` FROM topfull-master.
It never SSHes in to touch the live collector/runner processes, and it never
modifies existing result files. It does not write rho_estimate_report.

Usage (mirrors `run_scenario.py`'s own argument):
    python experiments/pull_results.py experiments/configs/scenario_2_baseline.yaml

`--no-report` is accepted and does nothing. The rho report stays off.

This does NOT change the existing printed-scp-command behavior of
`run_scenario.py` — it is an additive, opt-in convenience for whoever wants
one command instead of copy/pasting the printed line.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_scenario  # noqa: E402 — reuse scenario_dir_name(), not duplicate it


def resolve_pull_paths(cfg: dict) -> tuple[str, str, str]:
    """Compute (master_ssh_host, remote_dest, local_dest_dir) exactly like
    `run_scenario.collect_results()` does when it prints its scp command."""
    master = cfg["infra"]["master_ssh_host"]
    results_base = cfg["infra"]["results_base_path"]
    log_folder = cfg["log_folder"]
    remote_dest = f"{results_base}/{log_folder}"
    scen_dir = run_scenario.scenario_dir_name(cfg)
    local_dest_dir = (
        f"experiments/results/campaign_48/{scen_dir}/"
        if scen_dir
        else "experiments/results/campaign_48/"
    )
    return master, remote_dest, local_dest_dir


def pull_results(config_path: str, run_report: bool = False, dry_run: bool = False) -> Path:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    master, remote_dest, local_dest_dir = resolve_pull_paths(cfg)
    log_folder = cfg["log_folder"]
    local_dest_path = Path(local_dest_dir)
    local_dest_path.mkdir(parents=True, exist_ok=True)

    cmd = ["scp", "-r", f"{master}:{remote_dest}", str(local_dest_path)]
    print(f"    {' '.join(cmd)}")
    if dry_run:
        return local_dest_path / log_folder

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"[pull_results] scp failed with exit code {result.returncode}", file=sys.stderr)
        raise SystemExit(result.returncode)

    local_run_dir = local_dest_path / log_folder
    if not local_run_dir.is_dir():
        print(
            f"[pull_results] WARNING: expected pulled folder not found: {local_run_dir}",
            file=sys.stderr,
        )
        return local_run_dir

    print(f"[pull_results] Pulled to {local_run_dir}")
    if run_report:
        print(
            "[pull_results] rho_estimate_report is retired; "
            "score with experiments/analysis_score.py",
            file=sys.stderr,
        )

    return local_run_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pull a finished run's results from topfull-master."
    )
    parser.add_argument("config", help="Path to the scenario YAML config used for the run")
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Accepted for old commands. The rho report is already off.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the scp command without running it",
    )
    args = parser.parse_args()
    pull_results(args.config, run_report=False, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
