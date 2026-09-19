"""capacity_frozen.py — freeze mu_per_millicore from a saturating run.

See docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md.
Read-only wrt run folders (never modifies CSVs). Does not talk to VMs.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_service_mu as mu  # noqa: E402

MINIMUM_SERVICES: tuple[str, ...] = (
    "frontend",
    "checkoutservice",
    "productcatalogservice",
    "paymentservice",
)
DEFAULT_CLUSTER_SHAPE = "topfull-worker-1=e2-standard-16"
SCHEMA_VERSION = 1
METHOD_MU_SAT = "mu_sat"
METHOD_NOT_YET = "not_yet_calibrated"
CPU_SOURCE = "service_capacity.json"
CAPACITY_JSON_NAME = "service_capacity.json"
LOW_CONFIDENCE_SAT_TICKS = 10
MILLICORE_GAP_WARN_RATIO = 2.0


def default_capacity_path() -> Path:
    return Path(__file__).resolve().parent / "capacity" / "capacity_frozen.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def total_millicores(
    cpu_limit_millicores: Optional[int], replica_count: Optional[int]
) -> Optional[int]:
    if cpu_limit_millicores is None or replica_count is None:
        return None
    if cpu_limit_millicores <= 0 or replica_count <= 0:
        return None
    return int(cpu_limit_millicores) * int(replica_count)


def load_service_capacity(run_dir: Path) -> dict:
    path = Path(run_dir) / CAPACITY_JSON_NAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def millicores_for(
    capacity: dict, service: str
) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    if service not in capacity:
        return None, None, f"service omitted from {CAPACITY_JSON_NAME}"
    row = capacity[service] or {}
    cpu = row.get("cpu_limit_millicores")
    replicas = row.get("replica_count", 1)
    if cpu is None:
        return None, None, f"null cpu_limit_millicores in {CAPACITY_JSON_NAME}"
    try:
        cpu_i = int(cpu)
        rep_i = int(replicas)
    except (TypeError, ValueError):
        return None, None, f"unparseable millicores in {CAPACITY_JSON_NAME}"
    if total_millicores(cpu_i, rep_i) is None:
        return None, None, f"non-positive millicores in {CAPACITY_JSON_NAME}"
    return cpu_i, rep_i, None


@dataclass
class FrozenEntry:
    service: str
    mu_per_millicore: Optional[float] = None
    unit: str = "req/s per millicore"
    calibrated_at_cpu_limit_millicores: Optional[int] = None
    calibrated_at_replica_count: Optional[int] = None
    throughput_at_calibration: Optional[float] = None
    method: str = METHOD_NOT_YET
    cpu_source: str = CPU_SOURCE
    source_run: Optional[str] = None
    n_sat_ticks: Optional[int] = None
    note: Optional[str] = None


@dataclass
class FrozenTable:
    generated_at: str
    cluster_shape: str
    schema_version: int = SCHEMA_VERSION
    capacities: Dict[str, FrozenEntry] = field(default_factory=dict)


def empty_table(cluster_shape: str = DEFAULT_CLUSTER_SHAPE) -> FrozenTable:
    return FrozenTable(
        generated_at=utc_now(),
        cluster_shape=cluster_shape,
        schema_version=SCHEMA_VERSION,
        capacities={
            name: FrozenEntry(service=name, method=METHOD_NOT_YET)
            for name in MINIMUM_SERVICES
        },
    )


def _entry_from_dict(name: str, raw: dict) -> FrozenEntry:
    return FrozenEntry(
        service=name,
        mu_per_millicore=raw.get("mu_per_millicore"),
        unit=raw.get("unit", "req/s per millicore"),
        calibrated_at_cpu_limit_millicores=raw.get(
            "calibrated_at_cpu_limit_millicores"
        ),
        calibrated_at_replica_count=raw.get("calibrated_at_replica_count"),
        throughput_at_calibration=raw.get("throughput_at_calibration"),
        method=raw.get("method", METHOD_NOT_YET),
        cpu_source=raw.get("cpu_source", CPU_SOURCE),
        source_run=raw.get("source_run"),
        n_sat_ticks=raw.get("n_sat_ticks"),
        note=raw.get("note"),
    )


def load_table(path: Path) -> FrozenTable:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    caps_raw = data.get("capacities") or {}
    capacities = {
        name: _entry_from_dict(name, caps_raw[name])
        for name in MINIMUM_SERVICES
        if name in caps_raw
    }
    for name in MINIMUM_SERVICES:
        capacities.setdefault(name, FrozenEntry(service=name))
    return FrozenTable(
        generated_at=data.get("generated_at") or utc_now(),
        cluster_shape=data.get("cluster_shape") or DEFAULT_CLUSTER_SHAPE,
        schema_version=int(data.get("schema_version") or SCHEMA_VERSION),
        capacities=capacities,
    )


def save_table(table: FrozenTable, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": table.generated_at,
        "cluster_shape": table.cluster_shape,
        "schema_version": table.schema_version,
        "capacities": {
            name: asdict(table.capacities[name]) for name in MINIMUM_SERVICES
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class FrozenCapacityError(Exception):
    pass


def count_sat_ticks(run_dir: Path, service: str) -> int:
    inbound = Path(run_dir) / mu.INBOUND_NAME
    if not inbound.is_file():
        return 0
    rows = [r for r in mu._read_csv(inbound) if r.get("service") == service]
    ticks = mu.ticks_from_rows(rows)
    return sum(
        1 for t in ticks
        if t.delta_total > 0 and t.failure_fraction >= mu.SAT_5XX_FRACTION
    )


def freeze_service(
    run_dir: Path,
    service: str,
    *,
    method: str = METHOD_MU_SAT,
    force: bool = False,
    table_path: Path,
    cluster_shape: str = DEFAULT_CLUSTER_SHAPE,
) -> FrozenEntry:
    if service not in MINIMUM_SERVICES:
        raise FrozenCapacityError(
            f"{service} is not in the minimum set {MINIMUM_SERVICES}"
        )
    if method != METHOD_MU_SAT:
        raise FrozenCapacityError(
            f"unsupported method {method!r}; v1 only implements {METHOD_MU_SAT}"
        )
    table_path = Path(table_path)
    if table_path.is_file():
        table = load_table(table_path)
    else:
        table = empty_table(cluster_shape)
    if table.cluster_shape != cluster_shape:
        raise FrozenCapacityError(
            f"cluster_shape mismatch: table={table.cluster_shape!r} "
            f"requested={cluster_shape!r}"
        )
    existing = table.capacities[service]
    if existing.mu_per_millicore is not None and not force:
        raise FrozenCapacityError(
            f"{service} already frozen; pass force=True to overwrite"
        )
    cap = load_service_capacity(run_dir)
    cpu, replicas, err = millicores_for(cap, service)
    if err or cpu is None or replicas is None:
        raise FrozenCapacityError(err or f"no millicores for {service}")
    cores = total_millicores(cpu, replicas)
    try:
        estimates = mu.estimate_run(run_dir)
    except mu.MissingInboundError as exc:
        raise FrozenCapacityError(str(exc)) from exc
    by_name = {e.service: e for e in estimates}
    if service not in by_name or by_name[service].mu_sat is None:
        raise FrozenCapacityError(
            f"mu_sat unavailable for {service} (no saturating 5xx/reset ticks)"
        )
    throughput = float(by_name[service].mu_sat)
    n_sat = count_sat_ticks(run_dir, service)
    entry = FrozenEntry(
        service=service,
        mu_per_millicore=throughput / cores,
        method=METHOD_MU_SAT,
        cpu_source=CPU_SOURCE,
        source_run=str(Path(run_dir).resolve()),
        n_sat_ticks=n_sat,
        calibrated_at_cpu_limit_millicores=cpu,
        calibrated_at_replica_count=replicas,
        throughput_at_calibration=throughput,
        note=None if n_sat >= LOW_CONFIDENCE_SAT_TICKS else (
            f"low confidence: n_sat_ticks={n_sat} < {LOW_CONFIDENCE_SAT_TICKS}"
        ),
    )
    table.capacities[service] = entry
    table.generated_at = utc_now()
    save_table(table, table_path)
    return entry


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("run_dir")
    freeze.add_argument("--service", required=True)
    freeze.add_argument("--method", default=METHOD_MU_SAT)
    freeze.add_argument("--force", action="store_true")
    freeze.add_argument("--output", type=Path, default=None)
    freeze.add_argument("--cluster-shape", default=DEFAULT_CLUSTER_SHAPE)
    args = parser.parse_args(argv)
    path = args.output or default_capacity_path()
    try:
        entry = freeze_service(
            Path(args.run_dir),
            args.service,
            method=args.method,
            force=args.force,
            table_path=path,
            cluster_shape=args.cluster_shape,
        )
    except FrozenCapacityError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write(
        f"froze {entry.service} mu_per_millicore={entry.mu_per_millicore} "
        f"-> {path}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
