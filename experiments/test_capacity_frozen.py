"""Unit tests for capacity_frozen.py (schema + millicores + freeze)."""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capacity_frozen as cf
import estimate_service_mu as mu


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


def _saturating_then_healthy_tail(
    service: str, *, two="50", five="50", resets="0",
) -> list[dict]:
    """One saturating second at t=1, then 5 healthy seconds so the sat
    tick is not in SAT_TAIL_TRIM_TICKS."""
    rows = [
        {"timestamp": "2026-09-17T00:00:00Z", "service": service,
         "total": "0", "2xx": "0", "4xx": "0", "5xx": "0", "resets": "0",
         "rq_time_sum_ms": "0", "rq_time_count": "0"},
        {"timestamp": "2026-09-17T00:00:01Z", "service": service,
         "total": "100", "2xx": two, "4xx": "0", "5xx": five, "resets": resets,
         "rq_time_sum_ms": "0", "rq_time_count": "0"},
    ]
    total, two_i, five_i, reset_i = 100, int(two), int(five), int(resets)
    for i in range(5):
        total += 100
        two_i += 100
        rows.append({
            "timestamp": f"2026-09-17T00:00:{i + 2:02d}Z",
            "service": service,
            "total": str(total),
            "2xx": str(two_i),
            "4xx": "0",
            "5xx": str(five_i),
            "resets": str(reset_i),
            "rq_time_sum_ms": "0",
            "rq_time_count": "0",
        })
    return rows


def _write_inbound(d: Path, rows: list[dict]) -> None:
    fields = ["timestamp", "service", "total", "2xx", "4xx", "5xx",
              "resets", "rq_time_sum_ms", "rq_time_count"]
    with open(d / "service_inbound.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            row.setdefault("resets", "0")
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
            _write_inbound(d, _saturating_then_healthy_tail("checkoutservice"))
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
            self.assertEqual(entry.n_sat_ticks, 1)
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

    def test_freeze_succeeds_on_reset_only_saturation(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_capacity(d, "checkoutservice", 100)
            _write_inbound(
                d,
                _saturating_then_healthy_tail(
                    "checkoutservice", five="0", resets="50",
                ),
            )
            out = d / "capacity_frozen.json"
            cf.save_table(cf.empty_table(), out)
            entry = cf.freeze_service(
                d, "checkoutservice", table_path=out, force=True
            )
            self.assertAlmostEqual(entry.throughput_at_calibration, 50.0)
            self.assertAlmostEqual(entry.mu_per_millicore, 0.5)
            self.assertEqual(entry.n_sat_ticks, 1)

    def test_refuses_overwrite_without_force(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_capacity(d, "checkoutservice", 100)
            _write_inbound(d, _saturating_then_healthy_tail("checkoutservice"))
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


if __name__ == "__main__":
    unittest.main()
