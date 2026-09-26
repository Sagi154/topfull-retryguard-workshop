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

    def test_request_fraction_halves_checkout(self):
        self.assertEqual(q.paper_request_for("checkoutservice", 0.5), 307)
        self.assertEqual(q.paper_limit_for("checkoutservice"), 615)

    def test_request_fraction_default_is_one(self):
        self.assertEqual(
            q.paper_request_for("frontend"),
            q.paper_request_for("frontend", 1.0),
        )

    def test_request_fraction_rejects_zero(self):
        with self.assertRaises(ValueError):
            q.paper_request_for("frontend", 0.0)

    def test_request_fraction_rejects_above_one(self):
        with self.assertRaises(ValueError):
            q.validate_request_fraction(1.1)

    def test_request_fraction_rejects_non_number(self):
        with self.assertRaises(ValueError):
            q.validate_request_fraction("half")

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

    def test_productcatalog_replicas_constraint_is_rejected(self):
        # HPA enabled on productcatalog (design doc decision 6 / ADR-0005) —
        # same reasoning as the frontend guard above.
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "productcatalogservice", "method": "replicas", "replicas": 1}
            ])

    def test_other_services_replicas_constraint_is_still_allowed(self):
        q.validate_scale_constraints([
            {"deployment": "checkoutservice", "method": "replicas", "replicas": 2}
        ])

    def test_millicores_ok(self):
        q.validate_scale_constraints(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                    "container": "server",
                }
            ]
        )

    def test_millicores_and_fraction_together_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_fraction": 0.1,
                    "cpu_limit_millicores": 50,
                }
            ])

    def test_neither_millicores_nor_fraction_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {"deployment": "checkoutservice", "method": "cpu_limit"}
            ])

    def test_unknown_service_millicores_is_error(self):
        with self.assertRaises(ValueError):
            q.validate_scale_constraints([
                {
                    "deployment": "not-a-boutique-service",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                }
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

    def test_millicores_overwrite(self):
        got = q.effective_cpu_quotas(
            [
                {
                    "deployment": "checkoutservice",
                    "method": "cpu_limit",
                    "cpu_limit_millicores": 50,
                }
            ]
        )
        self.assertEqual(got["checkoutservice"], 50)
        self.assertEqual(got["productcatalogservice"], 1535)


class TestCpuLimitMillicoresFor(unittest.TestCase):
    def test_millicores_key_used_directly(self):
        got = q.cpu_limit_millicores_for(
            {"deployment": "checkoutservice", "cpu_limit_millicores": 50}
        )
        self.assertEqual(got, 50)

    def test_fraction_key_still_computed_from_paper_limit(self):
        got = q.cpu_limit_millicores_for(
            {"deployment": "checkoutservice", "cpu_limit_fraction": 0.1}
        )
        self.assertEqual(got, 61)  # int(615 * 0.1)

    def test_both_keys_is_error(self):
        with self.assertRaises(ValueError):
            q.cpu_limit_millicores_for({
                "deployment": "checkoutservice",
                "cpu_limit_fraction": 0.1,
                "cpu_limit_millicores": 50,
            })

    def test_neither_key_is_error(self):
        with self.assertRaises(ValueError):
            q.cpu_limit_millicores_for({"deployment": "checkoutservice"})


class TestBothOffYamlRestored(unittest.TestCase):
    def test_next_slot_is_paper_and_unused(self):
        import yaml
        from pathlib import Path

        path = Path(__file__).resolve().parent / "configs" / "scenario_2_baseline_no_topfull.yaml"
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertTrue(cfg.get("paper_cpu_reconcile", True))
        self.assertEqual(cfg.get("scale_constraints") or [], [])
        self.assertEqual(cfg["run_number"], 35)
        self.assertEqual(cfg["log_folder"], "baseline_no_topfull_sustained_overload_run35")
        self.assertIs(cfg["topfull_rl"]["enabled"], False)
        self.assertIs(cfg["retryguard"]["enabled"], False)


if __name__ == "__main__":
    unittest.main()
