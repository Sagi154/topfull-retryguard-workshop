"""
test_topfull_cpu_quotas.py — Unit tests for paper CPU quota table and fraction helpers.

Run:
    python experiments/test_topfull_cpu_quotas.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cpu_quotas as q


class TestMillicoresFromFraction(unittest.TestCase):
    def test_checkout_tenth(self):
        self.assertEqual(q.millicores_from_fraction(1000, 0.1), 100)

    def test_catalog_tenth(self):
        self.assertEqual(q.millicores_from_fraction(500, 0.1), 50)

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            q.millicores_from_fraction(1000, 0.0)

    def test_frontend_double(self):
        self.assertEqual(q.millicores_from_fraction(1000, 2.0), 2000)

    def test_allows_above_one_within_cap(self):
        self.assertEqual(q.millicores_from_fraction(1000, 1.1), 1100)

    def test_rejects_above_max(self):
        with self.assertRaises(ValueError):
            q.millicores_from_fraction(1000, 5.0)


class TestPaperTable(unittest.TestCase):
    def test_known_and_default(self):
        self.assertEqual(q.paper_limit_for("checkoutservice"), 1000)
        self.assertEqual(q.paper_limit_for("productcatalogservice"), 500)
        self.assertEqual(q.paper_limit_for("paymentservice"), 1000)
        self.assertEqual(q.paper_request_for("paymentservice"), 200)
        self.assertEqual(q.paper_request_for("checkoutservice"), 500)


class TestValidateScaleConstraints(unittest.TestCase):
    def test_legacy_cpu_limit_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit": "100m",
                }
            ])

    def test_both_keys_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints(
                [
                    {
                        "deployment": "checkoutservice",
                        "method": "cpu_limit",
                        "cpu_limit": "100m",
                        "cpu_limit_fraction": 0.1,
                    }
                ]
            )

    def test_fraction_ok(self):
        q.validate_scale_constraints(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 0.1,
                    "container": "server",
                }
            ]
        )

    def test_unknown_service_fraction_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints(
                [
                    {
                        "deployment": "not-a-boutique-service",
                        "method": "cpu_limit",
                        "cpu_limit_fraction": 0.1,
                    }
                ]
            )


class TestEffectiveCpuQuotas(unittest.TestCase):
    def test_paper_plus_overwrite(self):
        got = q.effective_cpu_quotas(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 0.1,
                }
            ]
        )
        self.assertEqual(got["checkoutservice"], 100)
        self.assertEqual(got["productcatalogservice"], 500)
        self.assertEqual(got["paymentservice"], 1000)

    def test_frontend_2x_raises_quota(self):
        got = q.effective_cpu_quotas(
            [
                {
                    "deployment": "frontend",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 2.0,
                }
            ]
        )
        self.assertEqual(got["frontend"], 2000)
        self.assertEqual(got["checkoutservice"], 1000)
        self.assertEqual(got["productcatalogservice"], 500)


if __name__ == "__main__":
    unittest.main()
