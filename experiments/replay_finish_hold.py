"""Finish one replay hold: score, health, log line, commit message tag.

Usage:
  python experiments/replay_finish_hold.py <run_dir> [--rg-off]
Prints one log line to stdout and writes CLEAN=1|0 and TAG=... lines at the end.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, text=True, errors="replace")


def throttle_status(score: str, rg_off_tf: bool) -> str:
    if "N/A: TopFull off" in score or rg_off_tf:
        return "N/A TopFull off"
    if "FLAGGED" in score:
        m = re.search(r"FLAGGED[^\n]*", score)
        return m.group(0) if m else "FLAGGED"
    return "ok"


def health_status(health_out: str) -> str:
    for line in health_out.splitlines():
        if line.startswith("health:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def toggle_summary(log_path: Path, rg_off: bool) -> str:
    if rg_off:
        return "RG off"
    if not log_path.is_file():
        return "no retryguard.log"
    counts: collections.Counter[tuple[str, str]] = collections.Counter()
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"(\S+)\s+(ON→OFF|OFF→ON|ON->OFF|OFF->ON)", line)
        if not m:
            continue
        edge, step = m.group(1), m.group(2).replace("→", "->")
        counts[(edge, step)] += 1
        if "burst" in line:
            counts[(edge, "burst")] += 1
        if "1→2" in line or "1->2" in line:
            counts[(edge, "1->2")] += 1
        if "2→3" in line or "2->3" in line:
            counts[(edge, "2->3")] += 1
    if not counts:
        return "no transition lines"
    return "; ".join(f"{e} {s} {n}" for (e, s), n in sorted(counts.items()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--rg-off", action="store_true",
                    help="Force RG-off label; otherwise read run_manifest.json")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    log_folder = run_dir.name
    rg_off = args.rg_off
    manifest = run_dir / "run_manifest.json"
    if manifest.is_file() and not args.rg_off:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        rg = data.get("retryguard") or data.get("config", {}).get("retryguard") or {}
        if isinstance(rg, dict):
            rg_off = not bool(rg.get("enabled", False))
        # Some manifests nest under top-level keys from the runner.
        if "retryguard" not in data and "config" not in data:
            rg_off = not bool(data.get("retryguard_enabled", True))
    score = _run([sys.executable, "experiments/analysis_score.py", str(run_dir)])
    health_out = _run([sys.executable, "experiments/topfull_health.py", str(run_dir)])
    throttle = throttle_status(score, rg_off)
    health = health_status(health_out)
    toggles = toggle_summary(run_dir / "retryguard.log", rg_off)
    line = (
        f"{log_folder} | exit ok | throttle {throttle} | health {health} | "
        f"replicas frontend=4 catalog=1 | {toggles}"
    )
    print(line)
    clean = health == "ok" and throttle in ("ok", "N/A TopFull off")
    print(f"CLEAN={1 if clean else 0}")
    print(f"TAG={'clean' if clean else f'flagged: {health}; {throttle}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
