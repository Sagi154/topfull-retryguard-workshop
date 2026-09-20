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

    def test_rejects_above_one(self):
        with self.assertRaises(ValueError):
            q.millicores_from_fraction(1000, 1.1)


class TestPaperTable(unittest.TestCase):
    # Ron-Nezer base migration (2026-09-20 design spec §4d): all 11
    # Boutique services, request == limit for every one (Ron's own
    # January YAML has request == limit; the workshop trims his numbers
    # by ~77% to fit topfull-worker1's 16 vCPU — see spec §4).
    def test_all_eleven_services_have_explicit_trimmed_values(self):
        self.assertEqual(q.paper_limit_for("frontend"), 1150)
        self.assertEqual(q.paper_limit_for("checkoutservice"), 615)
        self.assertEqual(q.paper_limit_for("recommendationservice"), 1150)
        self.assertEqual(q.paper_limit_for("productcatalogservice"), 1535)
        self.assertEqual(q.paper_limit_for("cartservice"), 1920)
        self.assertEqual(q.paper_limit_for("currencyservice"), 770)
        self.assertEqual(q.paper_limit_for("shippingservice"), 770)
        self.assertEqual(q.paper_limit_for("redis-cart"), 540)
        self.assertEqual(q.paper_limit_for("emailservice"), 155)
        self.assertEqual(q.paper_limit_for("paymentservice"), 155)
        self.assertEqual(q.paper_limit_for("adservice"), 1150)

    def test_request_equals_limit_for_every_service(self):
        for svc in q.PAPER_CPU_LIMIT_MILLICORES:
            self.assertEqual(
                q.paper_request_for(svc), q.paper_limit_for(svc),
                msg=f"{svc}: request must equal limit in the Ron-config regime",
            )

    def test_reconcile_services_covers_all_eleven(self):
        self.assertEqual(
            set(q.RECONCILE_SERVICES),
            {
                "frontend", "checkoutservice", "recommendationservice",
                "productcatalogservice", "cartservice", "currencyservice",
                "shippingservice", "redis-cart", "emailservice",
                "paymentservice", "adservice",
            },
        )


class TestContainerNameFor(unittest.TestCase):
    def test_redis_cart_container_is_named_redis(self):
        self.assertEqual(q.container_name_for("redis-cart"), "redis")

    def test_default_container_name_is_server(self):
        self.assertEqual(q.container_name_for("frontend"), "server")
        self.assertEqual(q.container_name_for("checkoutservice"), "server")


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

    def test_frontend_replicas_constraint_is_rejected(self):
        # Ron-Nezer migration (2026-09-20): frontend's replica count is
        # HPA-managed (spec §4c/§10 #5) — a scenario YAML that still
        # tries to pin it would fight the autoscaler.
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "frontend", "method": "replicas", "replicas": 1}
            ])

    def test_other_services_replicas_constraint_is_still_allowed(self):
        q.validate_scale_constraints([
            {"deployment": "checkoutservice", "method": "replicas", "replicas": 2}
        ])


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
        self.assertEqual(got["checkoutservice"], 61)  # int(615 * 0.1)
        self.assertEqual(got["productcatalogservice"], 1535)
        self.assertEqual(got["paymentservice"], 155)


if __name__ == "__main__":
    unittest.main()
