"""Offered-λ helpers for frozen-capacity ρ reports.

Envoy ``envoy_cluster_upstream_rq_total`` counts every try; subtracting
``retry`` recovers first-attempt λ. This is the spec §7.1 decision (not
``total + retry``, which would double-count).
"""
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_service_mu as mu  # noqa: E402
import capacity_frozen as cf  # noqa: E402

LOCUST_TOTAL_NAME = "total.csv"
EDGES_NAME = "service_edges.csv"


def locust_rps_mean(run_dir: Path) -> Optional[float]:
    path = Path(run_dir) / LOCUST_TOTAL_NAME
    if not path.is_file():
        return None
    values: List[float] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                values.append(float(row["RPS"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not values:
        return None
    return sum(values) / len(values)


def backend_offered_lambda(
    run_dir: Path, service: str
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    path = Path(run_dir) / EDGES_NAME
    if not path.is_file():
        return None, None, f"missing {EDGES_NAME}"
    by_ts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"total": 0, "retry": 0}
    )
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("target") != service:
                continue
            ts = row.get("timestamp") or ""
            try:
                by_ts[ts]["total"] += int(float(row.get("total") or 0))
                by_ts[ts]["retry"] += int(float(row.get("retry") or 0))
            except (TypeError, ValueError):
                continue
    if len(by_ts) < 2:
        return None, None, f"not enough {EDGES_NAME} ticks for {service}"
    ordered = sorted(by_ts, key=mu.parse_timestamp)
    first_rates: List[float] = []
    retry_rates: List[float] = []
    for prev_ts, cur_ts in zip(ordered, ordered[1:]):
        dt = (
            mu.parse_timestamp(cur_ts) - mu.parse_timestamp(prev_ts)
        ).total_seconds()
        if dt <= 0:
            continue
        d_total = by_ts[cur_ts]["total"] - by_ts[prev_ts]["total"]
        d_retry = by_ts[cur_ts]["retry"] - by_ts[prev_ts]["retry"]
        if d_total < 0 or d_retry < 0:
            continue  # counter reset
        first = max(d_total - d_retry, 0)
        if d_total <= 0 and d_retry <= 0:
            continue
        first_rates.append(first / dt)
        retry_rates.append(max(d_retry, 0) / dt)
    if not first_rates:
        return None, None, f"no positive offered-λ ticks for {service}"
    return (
        sum(first_rates) / len(first_rates),
        sum(retry_rates) / len(retry_rates),
        None,
    )
