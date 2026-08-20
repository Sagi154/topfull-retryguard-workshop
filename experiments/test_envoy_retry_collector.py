"""
test_envoy_retry_collector.py — Unit tests for Envoy retry-stats parsing,
CSV writing, kubectl command builders, and one poll iteration.

No kubectl / network access; all subprocess calls are injected mocks.

Run:
    python experiments/test_envoy_retry_collector.py
"""
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import envoy_retry_collector as erc


SAMPLE_STATS = """\
cluster.inbound|8080||.upstream_rq_total: 999
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_total: 100
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_retry: 12
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_retry_success: 8
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_retry_limit_exceeded: 1
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_total: 50
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_retry: 3
cluster.outbound|50051||paymentservice.default.svc.cluster.local.upstream_rq_total: 20
cluster.outbound|50051||emailservice.default.svc.cluster.local.upstream_rq_total: 5
cluster.outbound|50051||emailservice.default.svc.cluster.local.upstream_rq_retry: 2
"""


class TestParseRetryStats(unittest.TestCase):
    def test_extracts_only_requested_targets(self):
        result = erc.parse_retry_stats(
            SAMPLE_STATS,
            ["cartservice", "productcatalogservice", "paymentservice"],
        )
        self.assertEqual(
            set(result.keys()),
            {"cartservice", "productcatalogservice", "paymentservice"},
        )
        self.assertNotIn("emailservice", result)

    def test_cartservice_full_metrics(self):
        result = erc.parse_retry_stats(SAMPLE_STATS, ["cartservice"])
        self.assertEqual(
            result["cartservice"],
            {
                "upstream_rq_total": 100,
                "upstream_rq_retry": 12,
                "upstream_rq_retry_success": 8,
                "upstream_rq_retry_limit_exceeded": 1,
            },
        )

    def test_missing_metrics_default_to_zero(self):
        result = erc.parse_retry_stats(SAMPLE_STATS, ["paymentservice"])
        self.assertEqual(
            result["paymentservice"],
            {
                "upstream_rq_total": 20,
                "upstream_rq_retry": 0,
                "upstream_rq_retry_success": 0,
                "upstream_rq_retry_limit_exceeded": 0,
            },
        )

    def test_target_absent_from_stats_still_emitted_with_zeros(self):
        result = erc.parse_retry_stats(SAMPLE_STATS, ["checkoutservice"])
        self.assertEqual(
            result["checkoutservice"],
            {
                "upstream_rq_total": 0,
                "upstream_rq_retry": 0,
                "upstream_rq_retry_success": 0,
                "upstream_rq_retry_limit_exceeded": 0,
            },
        )

    def test_empty_stats_text(self):
        result = erc.parse_retry_stats("", ["cartservice"])
        self.assertEqual(result["cartservice"]["upstream_rq_total"], 0)


class TestWriteCsvRow(unittest.TestCase):
    def test_writes_header_once_then_appends(self, tmp_path=None):
        # pytest-style tmp_path not available under unittest; use TemporaryDirectory
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "envoy_retries_frontend.csv"
            stats = {
                "upstream_rq_total": 10,
                "upstream_rq_retry": 2,
                "upstream_rq_retry_success": 1,
                "upstream_rq_retry_limit_exceeded": 0,
            }
            erc.write_csv_row(path, "2026-08-20T12:00:00Z", "cartservice", stats)
            erc.write_csv_row(path, "2026-08-20T12:00:05Z", "cartservice", {
                **stats, "upstream_rq_total": 15, "upstream_rq_retry": 3,
            })

            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["timestamp"], "2026-08-20T12:00:00Z")
            self.assertEqual(rows[0]["target_service"], "cartservice")
            self.assertEqual(rows[0]["upstream_rq_retry"], "2")
            self.assertEqual(rows[1]["upstream_rq_total"], "15")
            self.assertEqual(rows[1]["upstream_rq_retry"], "3")


class TestDiscoverPodName(unittest.TestCase):
    def test_builds_correct_kubectl_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="frontend-abc123\n", stderr="")

        pod = erc.discover_pod_name("frontend", run_cmd=runner)
        self.assertEqual(pod, "frontend-abc123")
        self.assertEqual(calls[0][:3], ["kubectl", "get", "pods"])
        self.assertIn("-l", calls[0])
        self.assertIn("app=frontend", calls[0])

    def test_returns_none_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertIsNone(erc.discover_pod_name("frontend", run_cmd=runner))

    def test_returns_none_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertIsNone(erc.discover_pod_name("frontend", run_cmd=runner))


class TestFetchStatsText(unittest.TestCase):
    def test_builds_correct_kubectl_exec_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_STATS, stderr="")

        text = erc.fetch_stats_text("frontend-abc123", run_cmd=runner)
        self.assertEqual(text, SAMPLE_STATS)
        cmd = calls[0]
        self.assertEqual(cmd[:3], ["kubectl", "exec", "frontend-abc123"])
        self.assertIn("-c", cmd)
        self.assertIn("istio-proxy", cmd)
        self.assertIn("http://localhost:15000/stats", cmd)

    def test_returns_none_on_nonzero_exit(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")

        self.assertIsNone(erc.fetch_stats_text("pod", run_cmd=runner))

    def test_returns_none_on_timeout_exception(self):
        def runner(cmd):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_stats_text("pod", run_cmd=runner))


class TestPollOnce(unittest.TestCase):
    def test_writes_rows_for_both_callers(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            caller_map = {
                "frontend": ["cartservice", "productcatalogservice"],
                "checkoutservice": ["paymentservice"],
            }

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(
                        returncode=0, stdout="frontend-1\n", stderr=""
                    )
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(
                        returncode=0, stdout="checkout-1\n", stderr=""
                    )
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(
                        returncode=0, stdout=SAMPLE_STATS, stderr=""
                    )
                if "exec" in cmd and "checkout-1" in cmd:
                    # paymentservice total only
                    stats = (
                        "cluster.outbound|50051||paymentservice.default."
                        "svc.cluster.local.upstream_rq_total: 7\n"
                        "cluster.outbound|50051||paymentservice.default."
                        "svc.cluster.local.upstream_rq_retry: 1\n"
                    )
                    return SimpleNamespace(returncode=0, stdout=stats, stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            erc.poll_once(
                record_path,
                caller_map,
                timestamp="2026-08-20T12:00:00Z",
                run_cmd=run_cmd,
                pod_cache={},
            )

            with open(record_path / "envoy_retries_frontend.csv", newline="") as f:
                fe = list(csv.DictReader(f))
            with open(
                record_path / "envoy_retries_checkoutservice.csv", newline=""
            ) as f:
                co = list(csv.DictReader(f))
            self.assertEqual(
                {r["target_service"] for r in fe},
                {"cartservice", "productcatalogservice"},
            )
            self.assertEqual(co[0]["target_service"], "paymentservice")
            self.assertEqual(co[0]["upstream_rq_retry"], "1")

    def test_survives_one_caller_fetch_failure(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            caller_map = {
                "frontend": ["cartservice"],
                "checkoutservice": ["paymentservice"],
            }

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(
                        returncode=0, stdout="frontend-1\n", stderr=""
                    )
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(
                        returncode=0, stdout="checkout-1\n", stderr=""
                    )
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(returncode=1, stdout="", stderr="fail")
                if "exec" in cmd and "checkout-1" in cmd:
                    stats = (
                        "cluster.outbound|50051||paymentservice.default."
                        "svc.cluster.local.upstream_rq_total: 7\n"
                    )
                    return SimpleNamespace(returncode=0, stdout=stats, stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            # Must not raise
            erc.poll_once(
                record_path,
                caller_map,
                timestamp="2026-08-20T12:00:00Z",
                run_cmd=run_cmd,
                pod_cache={},
            )
            self.assertFalse(
                (record_path / "envoy_retries_frontend.csv").exists()
            )
            with open(
                record_path / "envoy_retries_checkoutservice.csv", newline=""
            ) as f:
                co = list(csv.DictReader(f))
            self.assertEqual(len(co), 1)


class TestRunCollector(unittest.TestCase):
    def test_max_polls_writes_and_exits(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined:
                    caller = "frontend" if "app=frontend" in joined else "checkoutservice"
                    return SimpleNamespace(
                        returncode=0, stdout=f"{caller}-1\n", stderr=""
                    )
                return SimpleNamespace(returncode=0, stdout=SAMPLE_STATS, stderr="")

            erc.run_collector(
                {"poll_interval_seconds": 1},
                record_path,
                run_cmd=run_cmd,
                max_polls=1,
            )
            self.assertTrue(
                (record_path / "envoy_retries_frontend.csv").exists()
            )
            self.assertTrue(
                (record_path / "envoy_retries_checkoutservice.csv").exists()
            )


if __name__ == "__main__":
    unittest.main()
