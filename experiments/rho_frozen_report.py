"""Frozen-capacity ρ̂ report: offered λ, rescaled μ, and rho_hat.

Envoy ``envoy_cluster_upstream_rq_total`` counts every try; subtracting
``retry`` recovers first-attempt λ. This is the spec §7.1 decision (not
``total + retry``, which would double-count).

``rho_hat = lambda_offered / mu_this_run`` uses a frozen
``mu_per_millicore`` from a *different* calibration run, rescaled by this
run's Kubernetes CPU limit in ``service_capacity.json``. Supplementary
offline diagnostic only — not RetryGuard's live input.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import argparse
import csv
import json
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


REPORT_MD_NAME = "rho_frozen_report.md"
REPORT_JSON_NAME = "rho_frozen_report.json"

FRONTEND = "frontend"


def mu_this_run(
    entry: cf.FrozenEntry, cpu_limit_millicores: int, replica_count: int
) -> Optional[float]:
    if entry.mu_per_millicore is None:
        return None
    cores = cf.total_millicores(cpu_limit_millicores, replica_count)
    if cores is None:
        return None
    return entry.mu_per_millicore * cores


@dataclass
class ServiceRhoRow:
    service: str
    lambda_offered: Optional[float] = None
    lambda_retry: Optional[float] = None
    mu_per_millicore: Optional[float] = None
    mu_this_run: Optional[float] = None
    rho_hat: Optional[float] = None
    cpu_limit_millicores: Optional[int] = None
    calibrated_at_cpu_limit_millicores: Optional[int] = None
    replica_count: Optional[int] = None
    n_sat_ticks: Optional[int] = None
    low_confidence: bool = False
    warnings: list = field(default_factory=list)
    na_reason: Optional[str] = None


def _quota_warning(run_dir: Path, service: str, cpu: int) -> Optional[str]:
    manifest = Path(run_dir) / "run_manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    effective = (data.get("effective_cpu_quotas") or {}).get(service)
    if effective is None:
        return None
    try:
        eff_i = int(effective)
    except (TypeError, ValueError):
        return None
    if eff_i != cpu:
        return (
            f"effective_cpu_quotas[{service}]={eff_i} disagrees with "
            f"service_capacity.json cpu_limit_millicores={cpu}; using K8s snapshot"
        )
    return None


def evaluate_run(
    run_dir: Path,
    table: cf.FrozenTable,
    *,
    cluster_shape: str = cf.DEFAULT_CLUSTER_SHAPE,
) -> tuple[list[ServiceRhoRow], list[str]]:
    if table.cluster_shape != cluster_shape:
        raise cf.FrozenCapacityError(
            f"cluster_shape mismatch: table={table.cluster_shape!r} "
            f"requested={cluster_shape!r}"
        )
    run_dir = Path(run_dir)
    table_warnings: list[str] = []
    cap = cf.load_service_capacity(run_dir)
    rows: list[ServiceRhoRow] = []
    for service in cf.MINIMUM_SERVICES:
        entry = table.capacities.get(service) or cf.FrozenEntry(service=service)
        row = ServiceRhoRow(
            service=service,
            mu_per_millicore=entry.mu_per_millicore,
            calibrated_at_cpu_limit_millicores=entry.calibrated_at_cpu_limit_millicores,
            n_sat_ticks=entry.n_sat_ticks,
            low_confidence=(
                entry.n_sat_ticks is not None
                and entry.n_sat_ticks < cf.LOW_CONFIDENCE_SAT_TICKS
            ),
        )
        if entry.mu_per_millicore is None:
            row.na_reason = entry.method or cf.METHOD_NOT_YET
            rows.append(row)
            continue
        cpu, replicas, err = cf.millicores_for(cap, service)
        if err or cpu is None or replicas is None:
            row.na_reason = err or f"no {cf.CAPACITY_JSON_NAME}"
            rows.append(row)
            continue
        row.cpu_limit_millicores = cpu
        row.replica_count = replicas
        qwarn = _quota_warning(run_dir, service, cpu)
        if qwarn:
            row.warnings.append(qwarn)
        cal = entry.calibrated_at_cpu_limit_millicores
        if cal and cal > 0:
            gap = max(cpu, cal) / min(cpu, cal)
            if gap >= cf.MILLICORE_GAP_WARN_RATIO:
                row.warnings.append(
                    f"millicore rescale {cal}m -> {cpu}m "
                    f"(ratio {gap:.1f}); assuming linear CPU scaling"
                )
        row.mu_this_run = mu_this_run(entry, cpu, replicas)
        if service == FRONTEND:
            row.lambda_offered = locust_rps_mean(run_dir)
            if row.lambda_offered is None:
                row.na_reason = f"missing {LOCUST_TOTAL_NAME}"
                rows.append(row)
                continue
        else:
            lam, retry, lerr = backend_offered_lambda(run_dir, service)
            row.lambda_offered = lam
            row.lambda_retry = retry
            if lerr:
                row.na_reason = lerr
                rows.append(row)
                continue
        if row.mu_this_run and row.lambda_offered is not None:
            row.rho_hat = row.lambda_offered / row.mu_this_run
        rows.append(row)
    return rows, table_warnings


def build_markdown_report(
    run_dir: Path,
    rows: list[ServiceRhoRow],
    warnings: list[str],
    table: cf.FrozenTable,
    table_path: Path,
) -> str:
    lines: list[str] = []
    lines.append(f"# frozen-capacity rho_hat report — `{run_dir.name}`")
    lines.append("")
    lines.append(f"Generated: {cf.utc_now()}")
    lines.append(f"Run folder: `{run_dir}`")
    lines.append(f"Frozen table: `{table_path}` (cluster_shape={table.cluster_shape})")
    lines.append("")
    lines.append(
        "This is a **supplementary** offline diagnostic, not RetryGuard's "
        "live input. Frozen μ came from a **different** calibration run, "
        "not from this run's own CSVs. `rho_hat = lambda_offered / "
        "mu_this_run` with `mu_this_run = mu_per_millicore * "
        "cpu_limit_millicores * replica_count` from this run's "
        "`service_capacity.json` (never `effective_cpu_quotas`)."
    )
    lines.append("")
    headers = (
        "service",
        "lambda_offered",
        "lambda_retry",
        "mu_per_millicore",
        "mu_this_run",
        "rho_hat",
        "cpu_limit_m",
        "calibrated_at_m",
        "n_sat_ticks",
        "low_confidence",
        "na_reason",
    )
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        cells = [
            row.service,
            mu._fmt(row.lambda_offered),
            mu._fmt(row.lambda_retry),
            mu._fmt(row.mu_per_millicore),
            mu._fmt(row.mu_this_run),
            mu._fmt(row.rho_hat),
            mu._fmt(row.cpu_limit_millicores),
            mu._fmt(row.calibrated_at_cpu_limit_millicores),
            mu._fmt(row.n_sat_ticks),
            mu._fmt(row.low_confidence),
            mu._fmt(row.na_reason),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    per_service_warnings = [(r.service, w) for r in rows for w in r.warnings]
    if warnings or per_service_warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        for service, w in per_service_warnings:
            lines.append(f"- `{service}`: {w}")
        lines.append("")
    return "\n".join(lines)


def generate_report(
    run_dir: Path,
    table_path: Optional[Path] = None,
    cluster_shape: str = cf.DEFAULT_CLUSTER_SHAPE,
) -> Path:
    run_dir = Path(run_dir)
    path = Path(table_path) if table_path is not None else cf.default_capacity_path()
    if not path.is_file():
        raise cf.FrozenCapacityError(f"missing capacity table: {path}")
    table = cf.load_table(path)
    rows, warnings = evaluate_run(run_dir, table, cluster_shape=cluster_shape)
    md = build_markdown_report(run_dir, rows, warnings, table, path)
    md_path = run_dir / REPORT_MD_NAME
    md_path.write_text(md, encoding="utf-8")
    payload = {
        "generated_at": cf.utc_now(),
        "run_dir": str(run_dir),
        "table_path": str(path),
        "cluster_shape": cluster_shape,
        "table_cluster_shape": table.cluster_shape,
        "rows": [asdict(r) for r in rows],
        "warnings": warnings,
    }
    (run_dir / REPORT_JSON_NAME).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return md_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--capacity", type=Path, default=None)
    parser.add_argument("--cluster-shape", default=cf.DEFAULT_CLUSTER_SHAPE)
    args = parser.parse_args(argv)
    try:
        md_path = generate_report(
            Path(args.run_dir),
            table_path=args.capacity,
            cluster_shape=args.cluster_shape,
        )
    except cf.FrozenCapacityError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write(f"Wrote {md_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
