"""Unit tests for s2_probe_tables. Synthetic rows only."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_probe_tables as t


def inbound_rows(n=12):
    rows = []
    for i in range(n):
        total = 100 * i
        rows.append({
            "timestamp": f"2026-10-04T10:00:{i:02d}Z", "service": "checkoutservice",
            "total": str(total), "5xx": str(10 * i), "resets": str(5 * i),
            "rq_time_sum_ms": str(20000 * i), "rq_time_count": str(100 * i),
            "rq_time_buckets": json.dumps({"500": 90 * i, "+Inf": 100 * i}),
        })
    return rows


class TestInboundMetrics(unittest.TestCase):
    def test_known_rates(self):
        m = t.inbound_metrics(inbound_rows())        # 12 rows, last 5 dropped -> rows 0..6, 6 s
        self.assertAlmostEqual(m["arrival"], 100.0)
        self.assertAlmostEqual(m["fail5xx"], 0.10)
        self.assertAlmostEqual(m["reset"], 0.05)
        self.assertAlmostEqual(m["sojourn_ms"], 200.0)
        self.assertAlmostEqual(m["over500"], 0.10)   # 90 of every 100 are <= 500 ms

    def test_too_few_rows_returns_empty(self):
        self.assertEqual(t.inbound_metrics(inbound_rows(3)), {})

    def test_missing_bucket_key_skips_over500_only(self):
        rows = inbound_rows()
        for r in rows:
            r["rq_time_buckets"] = "{}"
        m = t.inbound_metrics(rows)
        self.assertNotIn("over500", m)
        self.assertIn("sojourn_ms", m)


class TestCells(unittest.TestCase):
    def data(self, streak, svc="checkoutservice"):
        return {"abc": {"inbound": {svc: {"streak": streak, "high_samples": streak + 3}},
                        "overloaded": {svc: {"overloaded_ticks": 300, "ticks": 600, "share": 0.5}},
                        "retry_by_target": {svc: 42}}}

    def test_a_bold_only_for_controlled_service_at_30(self):
        self.assertEqual(t.cell_a(self.data(30), "checkoutservice"), "**30 / 33**")
        self.assertEqual(t.cell_a(self.data(29), "checkoutservice"), "29 / 32")
        self.assertEqual(t.cell_a(self.data(500, "frontend"), "frontend"), "500 / 503")

    def test_b_bold_at_half_and_c_is_the_target_sum(self):
        self.assertEqual(t.cell_b(self.data(1), "checkoutservice"), "**300/600 (50%)**")
        self.assertEqual(t.cell_c(self.data(1), "checkoutservice"), "42")
        self.assertEqual(t.cell_c(self.data(1), "adservice"), "0")

    def test_cpu_fraction_uses_quota_times_replicas(self):
        d = {"cpu": {"checkoutservice": {"mean": 800.0, "max": 1600.0, "quota": 1600}}}
        self.assertEqual(t.cell_cpu_frac(d, "checkoutservice"), "0.50 / 1.00")
        self.assertEqual(t.cell_cpu_frac({"cpu": {}}, "checkoutservice"), "")


if __name__ == "__main__":
    unittest.main()
