# Frozen-capacity ρ diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline frozen-capacity ρ diagnostic (`rho_hat = lambda_offered / mu_this_run`) that freezes `mu_per_millicore` from a dedicated saturating run and rescales it by each evaluated run’s Kubernetes CPU limit.

**Architecture:** Two new local, read-only-wrt-VMs tools. `experiments/capacity_frozen.py` writes/updates `experiments/capacity/capacity_frozen.json` from a calibration run’s `mu_sat` and `service_capacity.json`. `experiments/rho_frozen_report.py` reads that table plus an evaluated run’s Locust/`service_edges.csv`/`service_capacity.json` and writes `rho_frozen_report.md`/`.json` into the run folder. Shared types and millicore helpers live in `capacity_frozen.py`; the report imports them. Existing `rho_estimate_report.py` / `retryguard.py` / `pull_results.py` stay unchanged.

**Tech Stack:** Python 3 stdlib (`csv`, `json`, `dataclasses`, `argparse`, `pathlib`, `statistics`), `unittest` matching `experiments/test_estimate_service_mu.py` / `experiments/test_rho_estimate_report.py`. No new dependencies. No VM/SSH work.

## Global Constraints

- Do **not** change `experiments/retryguard.py` (live controller stays on mesh rejection-rate).
- Do **not** resurrect `mu_hat_w` / `rho_w` / CPU-linear `mu_cpu`.
- Do **not** derive μ from the same run that supplies `lambda_offered`.
- Do **not** put Locust user counts into μ. User counts are λ (frontend λ is Locust `total.csv` mean `RPS`).
- Do **not** read millicores from `topfull_run_quotas.json` or use `run_manifest.json` `effective_cpu_quotas` as a fallback. Millicores come only from `service_capacity.json`. Quota disagreement is a **warning**, never a substitute number.
- Do **not** auto-invoke the frozen report from `experiments/pull_results.py` (spec §5.4 — table will be mostly `not_yet_calibrated` at first).
- Freeze μ only for the **minimum set**: `frontend`, `checkoutservice`, `productcatalogservice`, `paymentservice`. All other Boutique services are omitted from the table and never guessed.
- Backend λ is first-attempt, **not** `total + retry`. Implementation formula (Envoy `upstream_rq_total` counts every try, including retries): `max(Δtotal − Δretry, 0) / Δt`, summed across callers per timestamp. Report `lambda_retry = mean(Δretry/Δt)` as a separate column.
- v1 freeze method is **`mu_sat` only**. Ramp-to-plateau (§3.2) is out of scope (needs plateau detection and a TopFull-off calibration run). Refuse freeze if `mu_sat` is `None`.
- Do **not** run live cluster calibration in this plan. Do **not** check a real campaign-derived `mu_per_millicore` into git. Tests use temp directories.
- Implementation defaults for still-open spec §7 items (lock these; Task 5 writes them back into the spec):
  - **§7.2 location:** `experiments/capacity/capacity_frozen.json` (path resolved from `Path(__file__).parent / "capacity" / "capacity_frozen.json"`).
  - **§7.4 confidence:** store `n_sat_ticks`; report `low_confidence: true` when `n_sat_ticks < 10`.
  - **§7.5 cluster shape:** default `"topfull-worker-1=e2-standard-16"`; **hard error** if the table’s `cluster_shape` ≠ the CLI/default (do not write a ρ report).
  - **§7.6 millicore gap:** warn and still rescale when `max(eval,cal) / min(eval,cal) >= 2.0`; print both millicores.
- Existing `rho_estimate_report.py` stays a single-run λ/W/`mu_sat` tool. Do not merge the two reports.
- Windows: run tests with `python -m pytest experiments/test_….py -v` (or `python -m unittest experiments.test_… -v`). Do not use bash heredocs in shell commands.

## File structure

| File | Responsibility |
|---|---|
| Create: `experiments/capacity_frozen.py` | Frozen table schema, millicore helpers, `freeze_service()`, freeze CLI |
| Create: `experiments/rho_frozen_report.py` | Offered-λ, `mu_this_run`, `rho_hat`, report writer + CLI |
| Create: `experiments/test_capacity_frozen.py` | Unit tests for freeze + millicores + table IO |
| Create: `experiments/test_rho_frozen_report.py` | Unit tests for λ, rescale, warnings, n/a reasons |
| Create: `experiments/capacity/capacity_frozen.json` | Skeleton table, all four services `not_yet_calibrated` |
| Create: `experiments/capacity/README.md` | How to freeze / report; cluster-shape rule |
| Modify: `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md` | Status = implemented (tools); lock §7.2/4/5/6 defaults |
| Modify: `AGENTS.md` | §4 status: tools exist, table uncalibrated, not in pull flow |
| Modify: `.cursor/skills/rho-estimate-report/SKILL.md` | Point at the new tool as implemented (separate) |

Reuse, do not copy: `experiments/estimate_service_mu.py` (`estimate_run`, `SAT_5XX_FRACTION`, `ticks_from_rows`, `_read_csv`, `parse_timestamp`).

---

### Task 1: Frozen table schema + millicore helpers

**Files:**
- Create: `experiments/capacity_frozen.py`
- Test: `experiments/test_capacity_frozen.py`

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces: constants `MINIMUM_SERVICES`, `DEFAULT_CLUSTER_SHAPE`, `SCHEMA_VERSION`, `METHOD_MU_SAT`, `METHOD_NOT_YET`, `CPU_SOURCE`, `CAPACITY_JSON_NAME`; functions `default_capacity_path() -> Path`, `total_millicores(cpu_limit_millicores: Optional[int], replica_count: Optional[int]) -> Optional[int]`, `load_service_capacity(run_dir: Path) -> dict`, `millicores_for(capacity: dict, service: str) -> tuple[Optional[int], Optional[int], Optional[str]]`, dataclasses `FrozenEntry` and `FrozenTable`, `empty_table(cluster_shape: str = DEFAULT_CLUSTER_SHAPE) -> FrozenTable`, `load_table(path: Path) -> FrozenTable`, `save_table(table: FrozenTable, path: Path) -> None`, `utc_now() -> str`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_capacity_frozen.py`:

```python
"""Unit tests for capacity_frozen.py (schema + millicores + freeze)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capacity_frozen as cf


class TestTotalMillicores(unittest.TestCase):
    def test_product(self):
        self.assertEqual(cf.total_millicores(100, 1), 100)
        self.assertEqual(cf.total_millicores(1000, 2), 2000)

    def test_none_or_non_positive_is_none(self):
        self.assertIsNone(cf.total_millicores(None, 1))
        self.assertIsNone(cf.total_millicores(100, None))
        self.assertIsNone(cf.total_millicores(0, 1))
        self.assertIsNone(cf.total_millicores(100, 0))


class TestLoadServiceCapacity(unittest.TestCase):
    def test_missing_file_is_empty_dict(self):
        with TemporaryDirectory() as raw:
            self.assertEqual(cf.load_service_capacity(Path(raw)), {})

    def test_reads_cpu_limit_and_replicas(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 100,
                        "cpu_request_millicores": 100,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            cap = cf.load_service_capacity(d)
            cpu, replicas, err = cf.millicores_for(cap, "checkoutservice")
            self.assertEqual(cpu, 100)
            self.assertEqual(replicas, 1)
            self.assertIsNone(err)

    def test_missing_service_has_reason(self):
        cpu, replicas, err = cf.millicores_for({}, "checkoutservice")
        self.assertIsNone(cpu)
        self.assertIsNone(replicas)
        self.assertIn("omitted", err)

    def test_null_cpu_limit_has_reason(self):
        cap = {"checkoutservice": {"cpu_limit_millicores": None, "replica_count": 1}}
        cpu, replicas, err = cf.millicores_for(cap, "checkoutservice")
        self.assertIsNone(cpu)
        self.assertIn("null", err.lower())


class TestFrozenTableRoundTrip(unittest.TestCase):
    def test_empty_table_has_all_minimum_services_uncalibrated(self):
        table = cf.empty_table()
        self.assertEqual(table.cluster_shape, cf.DEFAULT_CLUSTER_SHAPE)
        self.assertEqual(set(table.capacities), set(cf.MINIMUM_SERVICES))
        for name in cf.MINIMUM_SERVICES:
            self.assertIsNone(table.capacities[name].mu_per_millicore)
            self.assertEqual(table.capacities[name].method, cf.METHOD_NOT_YET)
        self.assertNotIn("cartservice", table.capacities)

    def test_save_and_load(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "capacity_frozen.json"
            table = cf.empty_table("topfull-worker-1=e2-standard-16")
            cf.save_table(table, path)
            loaded = cf.load_table(path)
            self.assertEqual(loaded.cluster_shape, table.cluster_shape)
            self.assertEqual(loaded.capacities["frontend"].method, cf.METHOD_NOT_YET)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_capacity_frozen.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'capacity_frozen'` (or import error).

- [ ] **Step 3: Write the schema + millicore implementation**

Create `experiments/capacity_frozen.py` with this library portion (CLI / `freeze_service` come in Task 2; leave stubs that raise `NotImplementedError` if you add them early — better: do not add `freeze_service` yet):

```python
"""capacity_frozen.py — freeze mu_per_millicore from a saturating run.

See docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md.
Read-only wrt run folders (never modifies CSVs). Does not talk to VMs.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_capacity_frozen.py -v`

Expected: PASS (all Task 1 tests).

- [ ] **Step 5: Commit**

```
git add experiments/capacity_frozen.py experiments/test_capacity_frozen.py
git commit -m "Add frozen-capacity table schema and millicore helpers."
```

---

### Task 2: Freeze `mu_per_millicore` from `mu_sat`

**Files:**
- Modify: `experiments/capacity_frozen.py`
- Modify: `experiments/test_capacity_frozen.py`

**Interfaces:**
- Consumes: Task 1 types; `estimate_service_mu.estimate_run`, `estimate_service_mu.SAT_5XX_FRACTION`, `estimate_service_mu.ticks_from_rows`, `estimate_service_mu._read_csv`, `INBOUND_NAME`.
- Produces: `class FrozenCapacityError(Exception)`, `count_sat_ticks(run_dir: Path, service: str) -> int`, `freeze_service(run_dir: Path, service: str, *, method: str = METHOD_MU_SAT, force: bool = False, table_path: Path, cluster_shape: str = DEFAULT_CLUSTER_SHAPE) -> FrozenEntry`, CLI `python experiments/capacity_frozen.py freeze <run_dir> --service NAME [--force] [--output PATH] [--cluster-shape STR]`.

- [ ] **Step 1: Write the failing freeze tests**

Append to `experiments/test_capacity_frozen.py` (reuse a small inbound CSV writer like `test_estimate_service_mu._in`, but for `checkoutservice`). Helper:

```python
import csv
import estimate_service_mu as mu


def _write_inbound(d: Path, rows: list[dict]) -> None:
    fields = ["timestamp", "service", "total", "2xx", "4xx", "5xx",
              "rq_time_sum_ms", "rq_time_count"]
    with open(d / "service_inbound.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _write_capacity(d: Path, service: str, millicores: int) -> None:
    (d / "service_capacity.json").write_text(
        json.dumps({
            service: {
                "cpu_limit_millicores": millicores,
                "cpu_request_millicores": millicores,
                "replica_count": 1,
            }
        }),
        encoding="utf-8",
    )


class TestFreezeService(unittest.TestCase):
    def test_freeze_mu_sat_divides_by_millicores(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_capacity(d, "checkoutservice", 100)
            _write_inbound(d, [
                {"timestamp": "2026-09-17T00:00:00Z", "service": "checkoutservice",
                 "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
                {"timestamp": "2026-09-17T00:00:01Z", "service": "checkoutservice",
                 "total": "100", "2xx": "50", "4xx": "0", "5xx": "50",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
            ])
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            entry = cf.freeze_service(
                d, "checkoutservice", table_path=out, force=True
            )
            # 5xx fraction 0.5 >= 0.05; mu_sat = delta_2xx/dt = 50/1 = 50
            self.assertAlmostEqual(entry.throughput_at_calibration, 50.0)
            self.assertEqual(entry.calibrated_at_cpu_limit_millicores, 100)
            self.assertAlmostEqual(entry.mu_per_millicore, 0.5)
            self.assertEqual(entry.method, cf.METHOD_MU_SAT)
            self.assertGreaterEqual(entry.n_sat_ticks, 1)
            loaded = cf.load_table(out)
            self.assertAlmostEqual(
                loaded.capacities["checkoutservice"].mu_per_millicore, 0.5
            )

    def test_refuses_out_of_set_service(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            with self.assertRaises(cf.FrozenCapacityError) as ctx:
                cf.freeze_service(d, "cartservice", table_path=out)
            self.assertIn("minimum set", str(ctx.exception).lower())

    def test_refuses_when_mu_sat_missing(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_capacity(d, "checkoutservice", 100)
            _write_inbound(d, [
                {"timestamp": "2026-09-17T00:00:00Z", "service": "checkoutservice",
                 "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
                {"timestamp": "2026-09-17T00:00:01Z", "service": "checkoutservice",
                 "total": "100", "2xx": "100", "4xx": "0", "5xx": "0",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
            ])
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            with self.assertRaises(cf.FrozenCapacityError) as ctx:
                cf.freeze_service(d, "checkoutservice", table_path=out)
            self.assertIn("mu_sat", str(ctx.exception))

    def test_refuses_overwrite_without_force(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_capacity(d, "checkoutservice", 100)
            _write_inbound(d, [
                {"timestamp": "2026-09-17T00:00:00Z", "service": "checkoutservice",
                 "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
                {"timestamp": "2026-09-17T00:00:01Z", "service": "checkoutservice",
                 "total": "100", "2xx": "50", "4xx": "0", "5xx": "50",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
            ])
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            cf.freeze_service(d, "checkoutservice", table_path=out, force=True)
            with self.assertRaises(cf.FrozenCapacityError):
                cf.freeze_service(d, "checkoutservice", table_path=out, force=False)

    def test_refuses_missing_service_capacity(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_inbound(d, [
                {"timestamp": "2026-09-17T00:00:00Z", "service": "checkoutservice",
                 "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
                {"timestamp": "2026-09-17T00:00:01Z", "service": "checkoutservice",
                 "total": "100", "2xx": "50", "4xx": "0", "5xx": "50",
                 "rq_time_sum_ms": "0", "rq_time_count": "0"},
            ])
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            with self.assertRaises(cf.FrozenCapacityError) as ctx:
                cf.freeze_service(d, "checkoutservice", table_path=out)
            self.assertIn("service_capacity.json", str(ctx.exception))

    def test_cluster_shape_mismatch_refuses(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table("topfull-worker-1=e2-standard-8"), out)
            with self.assertRaises(cf.FrozenCapacityError) as ctx:
                cf.freeze_service(
                    d, "checkoutservice", table_path=out,
                    cluster_shape=cf.DEFAULT_CLUSTER_SHAPE,
                )
            self.assertIn("cluster_shape", str(ctx.exception))
```

- [ ] **Step 2: Run freeze tests to verify they fail**

Run: `python -m pytest experiments/test_capacity_frozen.py::TestFreezeService -v`

Expected: FAIL with `AttributeError: freeze_service` (or `FrozenCapacityError` missing).

- [ ] **Step 3: Implement `freeze_service` and CLI**

Add to `experiments/capacity_frozen.py` (keep stdlib-only; import estimator after `sys.path` insert in `main` or relative to this file):

```python
import sys
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_service_mu as mu  # noqa: E402


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
        if t.delta_total > 0 and t.five_xx_fraction >= mu.SAT_5XX_FRACTION
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
            f"mu_sat unavailable for {service} (no saturating 5xx ticks)"
        )
    throughput = float(by_name[service].mu_sat)
    n_sat = count_sat_ticks(run_dir, service)
    entry = FrozenEntry(
        service=service,
        mu_per_millicore=throughput / cores,
        unit="req/s per millicore",
        calibrated_at_cpu_limit_millicores=cpu,
        calibrated_at_replica_count=replicas,
        throughput_at_calibration=throughput,
        method=METHOD_MU_SAT,
        cpu_source=CPU_SOURCE,
        source_run=str(Path(run_dir).resolve()),
        n_sat_ticks=n_sat,
        note=None if n_sat >= LOW_CONFIDENCE_SAT_TICKS else (
            f"low confidence: n_sat_ticks={n_sat} < {LOW_CONFIDENCE_SAT_TICKS}"
        ),
    )
    table.capacities[service] = entry
    table.generated_at = utc_now()
    save_table(table, table_path)
    return entry
```

CLI `main`:

```python
import argparse

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
```

- [ ] **Step 4: Run freeze tests to verify they pass**

Run: `python -m pytest experiments/test_capacity_frozen.py -v`

Expected: PASS.

Optional smoke (do **not** write into `experiments/capacity/`): from repo root, freeze frontend from S3 RG run8 into a temp file if you want to confirm real `mu_sat` works. Discard the temp file. Checkout on that run has `mu_sat=n/a` — freeze must refuse. Do not commit campaign-derived values.

- [ ] **Step 5: Commit**

```
git add experiments/capacity_frozen.py experiments/test_capacity_frozen.py
git commit -m "Freeze mu_per_millicore from mu_sat and service_capacity.json."
```

---

### Task 3: Offered λ (Locust entry + edges first-attempt)

**Files:**
- Create: `experiments/rho_frozen_report.py` (λ helpers only in this task; report writer in Task 4)
- Test: `experiments/test_rho_frozen_report.py`

**Interfaces:**
- Consumes: `capacity_frozen.parse_timestamp` is in `estimate_service_mu.parse_timestamp` — use that. `capacity_frozen.MINIMUM_SERVICES`.
- Produces: `LOCUST_TOTAL_NAME = "total.csv"`, `EDGES_NAME = "service_edges.csv"`, `locust_rps_mean(run_dir: Path) -> Optional[float]`, `backend_offered_lambda(run_dir: Path, service: str) -> tuple[Optional[float], Optional[float], Optional[str]]` where the tuple is `(lambda_first_attempt_mean, lambda_retry_mean, error_reason)`.

- [ ] **Step 1: Write the failing λ tests**

Create `experiments/test_rho_frozen_report.py`:

```python
"""Unit tests for rho_frozen_report.py."""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rho_frozen_report as rpt


def _write_csv(path: Path, fields, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


class TestLocustRpsMean(unittest.TestCase):
    def test_mean_of_rps_column(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_csv(
                d / "total.csv",
                ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                [
                    {"RPS": "0.0", "Fail": "0", "Goodput": "0",
                     "Latency95": "0", "Latency99": "0"},
                    {"RPS": "100.0", "Fail": "0", "Goodput": "100",
                     "Latency95": "0", "Latency99": "0"},
                    {"RPS": "200.0", "Fail": "0", "Goodput": "200",
                     "Latency95": "0", "Latency99": "0"},
                ],
            )
            self.assertAlmostEqual(rpt.locust_rps_mean(d), 100.0)

    def test_missing_file_is_none(self):
        with TemporaryDirectory() as raw:
            self.assertIsNone(rpt.locust_rps_mean(Path(raw)))


class TestBackendOfferedLambda(unittest.TestCase):
    def test_sums_callers_and_subtracts_retry(self):
        """Envoy total includes retries; first-attempt = Δtotal − Δretry."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            fields = ["timestamp", "caller", "target", "total", "2xx", "4xx",
                      "5xx", "retry"]
            _write_csv(
                d / "service_edges.csv",
                fields,
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "cartservice",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "80", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "10"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "cartservice",
                     "target": "checkoutservice", "total": "30", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "cartservice", "total": "999", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            lam, retry, err = rpt.backend_offered_lambda(d, "checkoutservice")
            self.assertIsNone(err)
            # summed Δtotal = 110, Δretry = 10, dt = 1 -> first-attempt 100
            self.assertAlmostEqual(lam, 100.0)
            self.assertAlmostEqual(retry, 10.0)

    def test_missing_edges_has_reason(self):
        with TemporaryDirectory() as raw:
            lam, retry, err = rpt.backend_offered_lambda(
                Path(raw), "checkoutservice"
            )
            self.assertIsNone(lam)
            self.assertIn("service_edges.csv", err)
```

- [ ] **Step 2: Run λ tests to verify they fail**

Run: `python -m pytest experiments/test_rho_frozen_report.py -v`

Expected: FAIL importing `rho_frozen_report`.

- [ ] **Step 3: Implement λ helpers**

Create `experiments/rho_frozen_report.py` with:

```python
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
```

Document in the module docstring: Envoy `envoy_cluster_upstream_rq_total` counts every try; subtracting `retry` recovers first-attempt λ. This is the spec §7.1 decision (not `total + retry`, which would double-count).

- [ ] **Step 4: Run λ tests to verify they pass**

Run: `python -m pytest experiments/test_rho_frozen_report.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```
git add experiments/rho_frozen_report.py experiments/test_rho_frozen_report.py
git commit -m "Compute offered lambda from Locust RPS and first-attempt edges."
```

---

### Task 4: `rho_hat` report (rescale + warnings + n/a)

**Files:**
- Modify: `experiments/rho_frozen_report.py`
- Modify: `experiments/test_rho_frozen_report.py`

**Interfaces:**
- Consumes: Task 1 `FrozenTable` / `FrozenEntry` / millicores / `MILLICORE_GAP_WARN_RATIO` / `LOW_CONFIDENCE_SAT_TICKS` / `FrozenCapacityError`; Task 2 frozen values; Task 3 λ helpers.
- Produces: `mu_this_run(entry: FrozenEntry, cpu_limit_millicores: int, replica_count: int) -> Optional[float]`, dataclass `ServiceRhoRow`, `evaluate_run(run_dir: Path, table: FrozenTable, *, cluster_shape: str = DEFAULT_CLUSTER_SHAPE) -> tuple[list[ServiceRhoRow], list[str]]` (raises `FrozenCapacityError` on cluster_shape mismatch), `generate_report(run_dir: Path, table_path: Optional[Path] = None, cluster_shape: str = …) -> Path` writing `rho_frozen_report.md` and `rho_frozen_report.json` into `run_dir`, CLI `python experiments/rho_frozen_report.py <run_dir> [--capacity PATH] [--cluster-shape STR]`.

- [ ] **Step 1: Write the failing report tests**

Append to `experiments/test_rho_frozen_report.py`:

```python
import capacity_frozen as cf


def _calibrated_checkout(mu_per_m: float = 0.5, at_m: int = 100) -> cf.FrozenTable:
    table = cf.empty_table()
    table.capacities["checkoutservice"] = cf.FrozenEntry(
        service="checkoutservice",
        mu_per_millicore=mu_per_m,
        calibrated_at_cpu_limit_millicores=at_m,
        calibrated_at_replica_count=1,
        throughput_at_calibration=mu_per_m * at_m,
        method=cf.METHOD_MU_SAT,
        source_run="/tmp/cal",
        n_sat_ticks=12,
    )
    return table


class TestMuThisRun(unittest.TestCase):
    def test_rescale_100m_to_1000m(self):
        entry = _calibrated_checkout().capacities["checkoutservice"]
        self.assertAlmostEqual(rpt.mu_this_run(entry, 100, 1), 50.0)
        self.assertAlmostEqual(rpt.mu_this_run(entry, 1000, 1), 500.0)


class TestEvaluateRun(unittest.TestCase):
    def test_rho_hat_uses_rescaled_mu(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 1000,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            _write_csv(
                d / "service_edges.csv",
                ["timestamp", "caller", "target", "total", "2xx", "4xx",
                 "5xx", "retry"],
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "200", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            _write_csv(
                d / "total.csv",
                ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                [{"RPS": "10", "Fail": "0", "Goodput": "10",
                  "Latency95": "0", "Latency99": "0"}],
            )
            rows, warnings = rpt.evaluate_run(d, _calibrated_checkout())
            by = {r.service: r for r in rows}
            chk = by["checkoutservice"]
            self.assertAlmostEqual(chk.lambda_offered, 200.0)
            self.assertAlmostEqual(chk.mu_this_run, 500.0)
            self.assertAlmostEqual(chk.rho_hat, 200.0 / 500.0)
            self.assertEqual(chk.cpu_limit_millicores, 1000)
            self.assertEqual(chk.calibrated_at_cpu_limit_millicores, 100)
            self.assertTrue(any("millicore" in w.lower() for w in chk.warnings))
            self.assertIsNone(by["frontend"].rho_hat)
            self.assertEqual(by["frontend"].na_reason, "not_yet_calibrated")
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r.service in cf.MINIMUM_SERVICES for r in rows))

    def test_cluster_shape_mismatch_raises(self):
        with TemporaryDirectory() as raw:
            table = cf.empty_table("topfull-worker-1=e2-standard-8")
            with self.assertRaises(cf.FrozenCapacityError):
                rpt.evaluate_run(
                    Path(raw), table, cluster_shape=cf.DEFAULT_CLUSTER_SHAPE
                )

    def test_missing_service_capacity_is_na_not_quota_fallback(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "run_manifest.json").write_text(
                json.dumps({"effective_cpu_quotas": {"checkoutservice": 1000}}),
                encoding="utf-8",
            )
            rows, _ = rpt.evaluate_run(d, _calibrated_checkout())
            chk = {r.service: r for r in rows}["checkoutservice"]
            self.assertIsNone(chk.rho_hat)
            self.assertIn("service_capacity.json", chk.na_reason)

    def test_quota_disagreement_warns_but_uses_k8s(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 100,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            (d / "run_manifest.json").write_text(
                json.dumps({"effective_cpu_quotas": {"checkoutservice": 1000}}),
                encoding="utf-8",
            )
            _write_csv(
                d / "service_edges.csv",
                ["timestamp", "caller", "target", "total", "2xx", "4xx",
                 "5xx", "retry"],
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "10", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            rows, _ = rpt.evaluate_run(d, _calibrated_checkout())
            chk = {r.service: r for r in rows}["checkoutservice"]
            self.assertEqual(chk.cpu_limit_millicores, 100)
            self.assertAlmostEqual(chk.mu_this_run, 50.0)
            self.assertTrue(any("effective_cpu_quotas" in w for w in chk.warnings))

    def test_generate_report_writes_md_and_json(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            table_path = d / "capacity_frozen.json"
            cf.save_table(_calibrated_checkout(), table_path)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 100,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            md = rpt.generate_report(d, table_path=table_path)
            self.assertTrue(md.is_file())
            text = md.read_text(encoding="utf-8")
            self.assertIn("rho_hat", text)
            self.assertIn("checkoutservice", text)
            self.assertNotIn("cartservice", text)
            self.assertIn("supplementary", text.lower())
            payload = json.loads((d / "rho_frozen_report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["rows"]), 4)
```

- [ ] **Step 2: Run report tests to verify they fail**

Run: `python -m pytest experiments/test_rho_frozen_report.py -v`

Expected: FAIL on missing `evaluate_run` / `mu_this_run`.

- [ ] **Step 3: Implement report evaluation + writer + CLI**

Add to `experiments/rho_frozen_report.py`:

```python
from dataclasses import asdict, dataclass, field
import json

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
```

`build_markdown_report` must:
- Title `frozen-capacity rho_hat report`
- State this is a supplementary offline diagnostic, not RetryGuard’s input, and that μ came from a **different** calibration run
- Table columns: `service`, `lambda_offered`, `lambda_retry`, `mu_per_millicore`, `mu_this_run`, `rho_hat`, `cpu_limit_m`, `calibrated_at_m`, `n_sat_ticks`, `low_confidence`, `na_reason`
- List per-service warnings underneath
- Format numbers like `estimate_service_mu._fmt` (`n/a` for None, 4 significant figures)

`generate_report`: load table from `table_path or cf.default_capacity_path()`. If that file is missing, raise `FrozenCapacityError` (do not invent ρ). Tests that call `generate_report` pass an explicit temp `table_path`.

CLI argparse: `run_dir`, `--capacity`, `--cluster-shape`. Catch `FrozenCapacityError`, print to stderr, exit 1.

- [ ] **Step 4: Run all new tests plus existing estimator tests**

Run:

```
python -m pytest experiments/test_rho_frozen_report.py experiments/test_capacity_frozen.py experiments/test_estimate_service_mu.py experiments/test_rho_estimate_report.py -v
```

Expected: all PASS. Existing reports must still omit `rho_w_median`.

- [ ] **Step 5: Commit**

```
git add experiments/rho_frozen_report.py experiments/test_rho_frozen_report.py
git commit -m "Report rho_hat from frozen mu_per_millicore and offered lambda."
```

---

### Task 5: Skeleton table + docs (no pull-flow wiring)

**Files:**
- Create: `experiments/capacity/capacity_frozen.json`
- Create: `experiments/capacity/README.md`
- Modify: `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`
- Modify: `AGENTS.md`
- Modify: `.cursor/skills/rho-estimate-report/SKILL.md`

**Interfaces:**
- Consumes: Task 1 `empty_table()` / `save_table()` shape.
- Produces: git-tracked skeleton (all four services `not_yet_calibrated`, `cluster_shape` = `topfull-worker-1=e2-standard-16`); spec/AGENTS/skill updated.

- [ ] **Step 1: Write the skeleton JSON**

`experiments/capacity/capacity_frozen.json` — contents must match `empty_table()` (four services, `mu_per_millicore: null`, `method: "not_yet_calibrated"`). No invented throughput. Include `"schema_version": 1` and `"cluster_shape": "topfull-worker-1=e2-standard-16"`.

`experiments/capacity/README.md` — short:

```markdown
# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only. cluster_shape must stay
`topfull-worker-1=e2-standard-16` until a full re-calibration after a
VM resize. This table is not auto-applied by pull_results.py.
```

- [ ] **Step 2: Update the spec status + lock §7 defaults**

In `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`:
- Change the status banner from “design only / no code implements” to: tools exist (`capacity_frozen.py`, `rho_frozen_report.py`); table is a skeleton (`not_yet_calibrated`); not wired into `pull_results.py`; controller unchanged.
- §7.2/4/5/6: mark **decided at implementation** with the Global Constraints defaults (path, `n_sat_ticks < 10`, hard error on `cluster_shape`, warn-and-rescale at ratio ≥ 2).
- Keep §3.2 ramp-to-plateau as not implemented.

- [ ] **Step 3: Update AGENTS.md and the existing skill**

`AGENTS.md` §4 Done: add a short bullet that the frozen-ρ **tools** exist, the JSON is an uncalibrated skeleton, real μ still needs saturating runs, `pull_results.py` does not call it, `retryguard.py` unchanged.

`AGENTS.md` remaining-work SLO-Fail paragraph: replace “no capacity_frozen.py exist yet” with “tools exist; freeze μ via saturating calibration still outstanding.”

`.cursor/skills/rho-estimate-report/SKILL.md`: change “designed but not yet wired” to: frozen report is a **separate** command `python experiments/rho_frozen_report.py <run_dir>`; do not merge into this skill’s report; do not tell the user there is no ρ tool.

Do **not** add a `pull_results.py` flag in this task.

- [ ] **Step 4: Re-run the full related test set**

Run:

```
python -m pytest experiments/test_capacity_frozen.py experiments/test_rho_frozen_report.py experiments/test_estimate_service_mu.py experiments/test_rho_estimate_report.py -v
```

Expected: PASS. Confirm `experiments/capacity/capacity_frozen.json` loads via `cf.load_table(cf.default_capacity_path())` in a one-liner if you want — all four methods `not_yet_calibrated`.

- [ ] **Step 5: Commit**

```
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md AGENTS.md .cursor/skills/rho-estimate-report/SKILL.md
git commit -m "Add uncalibrated frozen-capacity skeleton and document the new rho tools."
```

---

## Self-review (spec coverage)

| Spec requirement | Task |
|---|---|
| `rho_hat = λ_offered / mu_this_run`, μ from another run | 2 + 4 |
| Freeze `mu_per_millicore`, not absolute μ | 2 |
| Millicores from `service_capacity.json` only | 1, 4 |
| Warn on `effective_cpu_quotas` disagreement, never fall back | 4 |
| Minimum service set; others omitted | 1, 2, 4, 5 |
| Backend λ = first-attempt, not `total+retry` | 3 (`Δtotal − Δretry`) |
| Frontend λ = Locust `total.csv` mean RPS | 3 |
| `capacity_frozen.py` append-only unless `--force` | 2 |
| Report shows `mu_per_millicore`, `mu_this_run`, `rho_hat`, both millicores | 4 |
| n/a with reason when uncalibrated / missing files | 4 |
| cluster_shape hard error | 2, 4 |
| Millicore-gap warn and still rescale | 4 |
| Confidence via `n_sat_ticks` | 2, 4 |
| Not merged into `rho_estimate_report.py` | 4, 5 |
| Not auto-run from `pull_results.py` | Global + 5 |
| Do not change `retryguard.py` | Global |
| `mu_sat` freeze method | 2 |
| Ramp-to-plateau | explicitly out of scope |
| Live calibration runs / raising Locust users | out of scope |

No TBD/TODO left in tasks. Types: `FrozenEntry.mu_per_millicore`, `ServiceRhoRow.rho_hat`, `freeze_service(...)`, `evaluate_run(...)` are named consistently across tasks.
