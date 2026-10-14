"""Print collector facts for one pulled S3/S4 mode-matrix folder.

    python experiments/s3s4_mode_matrix_gate.py <folder> <normal|burst20|tf> <off|on>
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

NEED = (
    "metric=edge_rpr",
    "rpr_threshold=0.40",
    "rejection_threshold=0.20",
    "reenable_rejection=0.25",
    "climb_rpr_1_to_2=0.16",
    "climb_rpr_2_to_3=0.32",
    "climb_interval_seconds=10s",
    "sample_interval=1s",
    "interval_samples=20s",
)
BURST_NEED = (
    "burst_rpr=2.00",
    "burst_window_seconds=5",
    "burst_min_first_attempts=20",
)


def start_problems(start: str, kind: str) -> list[str]:
    if kind == "tf":
        return []
    missing = [token for token in NEED if token not in start]
    if kind == "normal" and "burst_rpr=" in start:
        missing.append("burst keys present on a normal hold")
    if kind == "burst20":
        missing.extend(token for token in BURST_NEED if token not in start)
    return missing


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise SystemExit(
            "usage: python experiments/s3s4_mode_matrix_gate.py "
            "<folder> <normal|burst20|tf> <off|on>"
        )
    root = Path(argv[1])
    kind = argv[2]
    if kind not in ("normal", "burst20", "tf"):
        raise SystemExit(f"kind must be normal, burst20, or tf, got {kind}")
    total_path = root / "total.csv"
    if not total_path.is_file():
        print("missing=total.csv")
        return
    print(f"locust_rows={len(_rows(total_path))}")
    log_path = root / "retryguard.log"
    if kind == "tf":
        print("start_missing=n/a")
        print("burst_observe=n/a")
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    elif not log_path.is_file():
        print("missing=retryguard.log")
        return
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        start = next((line for line in log_text.splitlines() if " START " in line), "")
        print(start)
        problems = start_problems(start, kind)
        print("start_missing=" + (",".join(problems) if problems else "none"))
        if kind == "burst20":
            print("burst_observe=" + ("yes" if "burst_rpr5=" in log_text else "no"))
        else:
            print("burst_observe=n/a")
    print("patch_fail=" + ("yes" if "PATCH_FAIL" in log_text or "Traceback" in log_text else "no"))
    usage_path = root / "resource_usage.csv"
    throttle_path = root / "topfull_throttle.csv"
    if not usage_path.is_file():
        print("missing=resource_usage.csv")
        return
    if not throttle_path.is_file():
        print("missing=topfull_throttle.csv")
        return
    usage = _rows(usage_path)
    frontend = [row for row in usage if row["service"] == "frontend"]
    catalog = [row for row in usage if row["service"] == "productcatalogservice"]
    print(f"frontend_4={sum(row['replica_count'] == '4' for row in frontend)}/{len(frontend)}")
    print(f"catalog_1={sum(row['replica_count'] == '1' for row in catalog)}/{len(catalog)}")
    # A catalog sample with replica_count 0 is a Not Ready flap (the pod is up
    # and pinned at its CPU limit). It is recorded here and is not a gate.
    not_ready = [row["timestamp"] for row in catalog if row["replica_count"] == "0"]
    print(f"catalog_not_ready={len(not_ready)}" + (f" at {','.join(not_ready)}" if not_ready else ""))
    # Evidence the TopFull RL loop ran: deploy_rl writes num_agent.csv only
    # when it is on. A TopFull-on hold that never capped an API still passes.
    num_agent = root / "num_agent.csv"
    print("topfull_rl_ran=" + ("yes" if num_agent.is_file() and num_agent.stat().st_size > 0 else "no"))
    throttle = _rows(throttle_path)
    live = [row for row in throttle if row["threshold_fresh"] == "1"]

    def as_float(row: dict[str, str]) -> float:
        return float(row["threshold"])

    n10000 = sum(as_float(row) == 10000 for row in live)
    nzero = sum(as_float(row) == 0 for row in live)
    ncaps = sum(0 < as_float(row) < 10000 for row in live)
    other = len(live) - n10000 - nzero - ncaps
    print(f"live5s_10000={n10000} live5s_caps={ncaps} live5s_zero={nzero} other={other}")


if __name__ == "__main__":
    main(sys.argv)
