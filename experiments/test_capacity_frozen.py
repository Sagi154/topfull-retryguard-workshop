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
