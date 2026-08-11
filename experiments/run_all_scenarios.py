#!/usr/bin/env python3
"""
run_all_scenarios.py — Execute the full Phase 5 + Phase 6 experiment matrix.

Runs 38 scenarios in per-scenario order: baseline x3, RetryGuard x3, then next
scenario. Scenario 5 is RetryGuard-only (4 intervals x 2 runs each).

Usage (from repo root):
    python experiments/run_all_scenarios.py --dry-run
    python experiments/run_all_scenarios.py --yes
    python experiments/run_all_scenarios.py --yes --resume 5
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = REPO_ROOT / "experiments" / "configs"
LOCAL_RESULTS = REPO_ROOT / "experiments" / "results"
RUN_SCENARIO = REPO_ROOT / "experiments" / "run_scenario.py"

MASTER = "topfull-master"
MASTER_RESULTS = "/home/idozacharia/experiments/results"

CSV_FILES = [
    "getproduct.csv",
    "postcheckout.csv",
    "getcart.csv",
    "postcart.csv",
    "emptycart.csv",
]

COOLDOWN_SECONDS = 90


@dataclass(frozen=True)
class RunSlot:
    """One entry in the execution matrix."""
    slot: int
    config: str
    run_number: int
    scenario_label: str


def build_matrix() -> list[RunSlot]:
    """38 runs: per-scenario baseline x3 then RetryGuard x3; S5 intervals x2."""
    entries: list[tuple[str, int, str]] = []

    def add_pair(baseline: str, retryguard: str, label: str, runs: int = 3) -> None:
        for n in range(1, runs + 1):
            entries.append((baseline, n, label))
        for n in range(1, runs + 1):
            entries.append((retryguard, n, label))

    add_pair(
        "scenario_1_baseline.yaml",
        "scenario_1_retryguard.yaml",
        "S1 Normal Operation",
    )
    add_pair(
        "scenario_2_baseline.yaml",
        "scenario_2_retryguard.yaml",
        "S2 Sustained Overload",
    )
    add_pair(
        "scenario_3_baseline.yaml",
        "scenario_3_retryguard.yaml",
        "S3 Targeted Bottleneck",
    )
    add_pair(
        "scenario_4a_baseline.yaml",
        "scenario_4a_retryguard.yaml",
        "S4A Topology ProductCatalog",
    )
    add_pair(
        "scenario_4b_baseline.yaml",
        "scenario_4b_retryguard.yaml",
        "S4B Topology Payment",
    )

    for cfg in (
        "scenario_5_interval_10s.yaml",
        "scenario_5_interval_20s.yaml",
        "scenario_5_interval_30s.yaml",
        "scenario_5_interval_60s.yaml",
    ):
        for n in (1, 2):
            entries.append((cfg, n, "S5 Interval Sweep"))

    return [
        RunSlot(slot=i + 1, config=cfg, run_number=run_n, scenario_label=label)
        for i, (cfg, run_n, label) in enumerate(entries)
    ]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def ssh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-o", "ControlMaster=no",
            MASTER,
            cmd,
        ],
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        log(f"[ERROR] SSH failed (rc={result.returncode}): {cmd}")
        if result.stderr.strip():
            log(f"  stderr: {result.stderr.strip()}")
        sys.exit(1)
    return result


def log_folder_prefix(config_path: Path) -> str:
    """Strip trailing _runN from log_folder in YAML."""
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    folder = cfg["log_folder"]
    prefix = re.sub(r"_run\d+$", "", folder)
    if not prefix:
        raise ValueError(f"Could not derive log_folder prefix from {folder}")
    return prefix


def patch_config(config_path: Path, run_number: int, log_folder: str) -> None:
    """Update run_number and log_folder in YAML, preserving other content."""
    text = config_path.read_text(encoding="utf-8")
    text = re.sub(
        r"^run_number:\s*\d+.*$",
        f"run_number: {run_number}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^log_folder:\s*\S+.*$",
        f"log_folder: {log_folder}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    config_path.write_text(text, encoding="utf-8")


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def preflight_cluster() -> None:
    log("Pre-flight: SSH to master...")
    r = ssh("echo ok")
    if "ok" not in r.stdout:
        log("[ERROR] Master not reachable.")
        sys.exit(1)

    log("Pre-flight: checking nodes...")
    r = ssh("kubectl get nodes --no-headers 2>/dev/null")
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    if not lines:
        log("[ERROR] No nodes returned — is kubectl configured?")
        sys.exit(1)
    not_ready = [l for l in lines if "NotReady" in l]
    if not_ready:
        log("[ERROR] Nodes not Ready:")
        for line in not_ready:
            log(f"  {line}")
        sys.exit(1)
    log(f"Pre-flight: {len(lines)} node(s) Ready")

    log("Pre-flight: checking pods...")
    r = ssh(
        "kubectl get pods --no-headers 2>/dev/null | grep -v Running || true",
        check=False,
    )
    non_running = [
        l for l in r.stdout.strip().splitlines()
        if l.strip() and "NAME" not in l
    ]
    if non_running:
        log("[WARN] Some pods not Running:")
        for line in non_running:
            log(f"  {line}")
    else:
        log("Pre-flight: all pods Running")

    log("Pre-flight: SSH to loadgen...")
    subprocess.run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-o", "ControlMaster=no",
            "topfull-load",
            "echo ok",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    log("Pre-flight: loadgen reachable")


def clear_master_results(yes: bool) -> None:
    log(f"Listing contents of {MASTER_RESULTS} on master...")
    r = ssh(f"ls -1 {MASTER_RESULTS} 2>/dev/null || true", check=False)
    items = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    if not items:
        log("Master results directory is already empty.")
        return

    log(f"Found {len(items)} item(s) to delete:")
    for name in items:
        log(f"  {name}")

    if not yes:
        answer = input("Delete all of the above? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            log("Aborted — not clearing master results.")
            sys.exit(1)

    # sudo: smoke-run files may be owned by another Linux user on shared master
    ssh(f"sudo rm -rf {MASTER_RESULTS}/*")
    r = ssh(f"ls -1 {MASTER_RESULTS} 2>/dev/null | wc -l")
    count = r.stdout.strip()
    if count != "0":
        log(f"[WARN] Master results dir not empty after clear (count={count})")
    else:
        log("Master results directory cleared.")


def clear_tmp_scripts() -> None:
    ssh(
        "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh "
        "/tmp/rg_retryguard.sh /tmp/rg_locust_launch.sh",
        check=False,
    )


def verify_run_on_master(
    log_folder: str,
    duration_seconds: int,
    retryguard_enabled: bool,
) -> list[str]:
    """Return list of verification warnings (empty if all checks pass)."""
    warnings: list[str] = []
    dest = f"{MASTER_RESULTS}/{log_folder}"
    min_rows = int(duration_seconds * 0.8)

    for csv_name in CSV_FILES:
        path = f"{dest}/{csv_name}"
        r = ssh(f"test -f {path} && wc -l < {path} || echo MISSING", check=False)
        out = r.stdout.strip()
        if out == "MISSING" or not out.isdigit():
            warnings.append(f"Missing or unreadable: {csv_name}")
            continue
        rows = int(out)
        if rows < min_rows:
            warnings.append(
                f"{csv_name}: {rows} rows (expected >= {min_rows})"
            )
        # Spot-check RPS > 0 in first 60 data rows (skip header)
        r2 = ssh(
            f"tail -n +2 {path} | head -60 | cut -d, -f1 | grep -v '^0$' | head -1",
            check=False,
        )
        if not r2.stdout.strip():
            warnings.append(f"{csv_name}: no non-zero RPS in first 60 rows")

    if retryguard_enabled:
        rg_path = f"{dest}/retryguard.log"
        r = ssh(f"test -f {rg_path} && head -1 {rg_path} || echo MISSING", check=False)
        if r.stdout.strip() == "MISSING":
            warnings.append("Missing retryguard.log")
        elif "START" not in r.stdout:
            warnings.append("retryguard.log missing START line")

    manifest = f"{dest}/run_manifest.json"
    r = ssh(f"test -f {manifest} && echo ok || echo MISSING", check=False)
    if r.stdout.strip() != "ok":
        warnings.append("Missing run_manifest.json")

    return warnings


def scp_results(log_folder: str) -> None:
    LOCAL_RESULTS.mkdir(parents=True, exist_ok=True)
    remote = f"{MASTER}:{MASTER_RESULTS}/{log_folder}"
    local_dest = LOCAL_RESULTS / log_folder
    if local_dest.exists():
        import shutil
        shutil.rmtree(local_dest)
    subprocess.run(
        [
            "scp",
            "-r",
            "-o", "BatchMode=yes",
            "-o", "ControlMaster=no",
            remote,
            str(LOCAL_RESULTS) + "/",
        ],
        check=True,
    )
    log(f"Pulled results to {local_dest}")


def run_scenario(config_path: Path) -> int:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(RUN_SCENARIO), str(config_path)],
        cwd=str(REPO_ROOT),
        env=env,
    )
    return result.returncode


def finalize_config_next_run(config_path: Path, last_run_number: int) -> None:
    """Leave YAML at next-available run number after matrix completes for this slot."""
    prefix = log_folder_prefix(config_path)
    next_n = last_run_number + 1
    patch_config(config_path, next_n, f"{prefix}_run{next_n}")


def print_matrix(matrix: list[RunSlot]) -> None:
    print(f"\n{'='*72}")
    print("  Full experiment matrix (38 runs)")
    print(f"{'='*72}")
    current_label = ""
    for slot in matrix:
        if slot.scenario_label != current_label:
            current_label = slot.scenario_label
            print(f"\n  --- {current_label} ---")
        prefix = log_folder_prefix(CONFIGS_DIR / slot.config)
        folder = f"{prefix}_run{slot.run_number}"
        print(
            f"  Slot {slot.slot:2d}: {slot.config:40s}  "
            f"run{slot.run_number}  ->  {folder}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full Phase 5+6 experiment matrix (38 runs)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the matrix and exit without executing.",
    )
    parser.add_argument(
        "--resume",
        type=int,
        default=0,
        metavar="N",
        help="Skip the first N run slots (0-indexed: --resume 5 starts at slot 6).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation when clearing master results.",
    )
    parser.add_argument(
        "--no-cooldown",
        action="store_true",
        help="Skip 90s cool-down between runs (for testing only).",
    )
    args = parser.parse_args()

    matrix = build_matrix()
    if len(matrix) != 38:
        log(f"[ERROR] Matrix size is {len(matrix)}, expected 38")
        sys.exit(1)

    print_matrix(matrix)

    if args.dry_run:
        log("Dry run — exiting.")
        return

    if args.resume < 0 or args.resume >= len(matrix):
        log(f"[ERROR] --resume must be between 0 and {len(matrix) - 1}")
        sys.exit(1)

    preflight_cluster()
    if args.resume == 0:
        clear_master_results(args.yes)
    else:
        log(f"Skipping master results clear (--resume {args.resume})")
    LOCAL_RESULTS.mkdir(parents=True, exist_ok=True)
    log(f"Local results directory: {LOCAL_RESULTS}")

    # Track last run number per config for final YAML bump
    last_run_by_config: dict[str, int] = {}

    failed_slots: list[int] = []
    start_time = datetime.now()

    for slot in matrix:
        if slot.slot <= args.resume:
            log(f"Skipping slot {slot.slot} (--resume {args.resume})")
            continue

        config_path = CONFIGS_DIR / slot.config
        if not config_path.exists():
            log(f"[ERROR] Config not found: {config_path}")
            sys.exit(1)

        prefix = log_folder_prefix(config_path)
        log_folder = f"{prefix}_run{slot.run_number}"

        print(f"\n{'='*72}")
        log(
            f"Slot {slot.slot}/38 — {slot.scenario_label} — "
            f"{slot.config} run{slot.run_number}"
        )
        log(f"log_folder: {log_folder}")
        print(f"{'='*72}")

        patch_config(config_path, slot.run_number, log_folder)
        clear_tmp_scripts()

        rc = run_scenario(config_path)
        if rc != 0:
            log(f"[ERROR] run_scenario.py exited with code {rc} for slot {slot.slot}")
            failed_slots.append(slot.slot)
            # Still try verify/scp if folder exists

        cfg = load_config(config_path)
        duration = cfg["duration_seconds"]
        rg_on = cfg.get("retryguard", {}).get("enabled", False)

        warnings = verify_run_on_master(log_folder, duration, rg_on)
        if warnings:
            log(f"[WARN] Verification issues for slot {slot.slot}:")
            for w in warnings:
                log(f"  - {w}")
        else:
            log(f"Verification passed for slot {slot.slot}")

        try:
            scp_results(log_folder)
        except subprocess.CalledProcessError as e:
            log(f"[ERROR] SCP failed for slot {slot.slot}: {e}")
            failed_slots.append(slot.slot)

        last_run_by_config[slot.config] = slot.run_number

        if slot.slot < len(matrix) and not args.no_cooldown:
            log(f"Cool-down {COOLDOWN_SECONDS}s before next run...")
            time.sleep(COOLDOWN_SECONDS)

    # Bump each touched config to next available run number
    for config_name, last_n in last_run_by_config.items():
        finalize_config_next_run(CONFIGS_DIR / config_name, last_n)
        log(f"Updated {config_name} -> next run_number {last_n + 1}")

    elapsed = datetime.now() - start_time
    print(f"\n{'='*72}")
    log(f"Matrix complete. Elapsed: {elapsed}")
    if failed_slots:
        log(f"Failed or partial slots: {failed_slots}")
        sys.exit(1)
    log("All 38 runs completed successfully.")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
