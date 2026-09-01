"""
test_resource_usage_collector.py — Unit tests for kubelet stats/summary parsing,
CSV writing, and one poll iteration. No kubectl / network access.

Run:
    python experiments/test_resource_usage_collector.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import resource_usage_collector as ruc

SAMPLE_SUMMARY = {
    "pods": [
        {
            "podRef": {"name": "frontend-abc123-xyz", "namespace": "default"},
            "containers": [
                {
                    "name": "server",
                    "cpu": {"usageNanoCores": 50_000_000},
                    "memory": {"workingSetBytes": 128_000_000},
                },
                {
                    "name": "istio-proxy",
                    "cpu": {"usageNanoCores": 10_000_000},
                    "memory": {"workingSetBytes": 64_000_000},
                },
            ],
        },
        {
            "podRef": {"name": "checkoutservice-def456-uvw", "namespace": "default"},
            "containers": [
                {
                    "name": "server",
                    "cpu": {"usageNanoCores": 100_000_000},
                    "memory": {"workingSetBytes": 256_000_000},
                },
            ],
        },
        {
            "podRef": {"name": "redis-cart-ghi789-rst", "namespace": "default"},
            "containers": [
                {
                    "name": "redis",
                    "cpu": {"usageNanoCores": 5_000_000},
                    "memory": {"workingSetBytes": 32_000_000},
                },
            ],
        },
        {
            "podRef": {"name": "other-ns-pod", "namespace": "kube-system"},
            "containers": [
                {
                    "name": "app",
                    "cpu": {"usageNanoCores": 999_000_000},
                    "memory": {"workingSetBytes": 999},
                },
            ],
        },
    ],
}

SAMPLE_DEPLOYS = {
    "items": [
        {"metadata": {"name": "frontend"}, "status": {"readyReplicas": 1}},
        {"metadata": {"name": "checkoutservice"}, "status": {"readyReplicas": 1}},
        {"metadata": {"name": "redis-cart"}, "status": {"readyReplicas": 1}},
    ],
}

SERVICES = ["frontend", "checkoutservice", "redis-cart", "paymentservice"]


class TestPodNameToService(unittest.TestCase):
    def test_exact_and_prefixed_names(self):
        self.assertEqual(
            ruc.pod_name_to_service("redis-cart-abc-123", SERVICES),
            "redis-cart",
        )
        self.assertEqual(
            ruc.pod_name_to_service("frontend-abc-123", SERVICES),
            "frontend",
        )

    def test_unknown_pod_returns_none(self):
        self.assertIsNone(ruc.pod_name_to_service("unknown-pod", SERVICES))


class TestParseStatsSummary(unittest.TestCase):
    def test_extracts_app_container_skips_sidecar(self):
        usage = ruc.parse_stats_summary(SAMPLE_SUMMARY, SERVICES)
        self.assertEqual(usage["frontend"], (50, 128_000_000))
        self.assertEqual(usage["checkoutservice"], (100, 256_000_000))
        self.assertEqual(usage["redis-cart"], (5, 32_000_000))

    def test_missing_service_omitted_not_zero(self):
        usage = ruc.parse_stats_summary(SAMPLE_SUMMARY, SERVICES)
        self.assertNotIn("paymentservice", usage)

    def test_wrong_namespace_ignored(self):
        usage = ruc.parse_stats_summary(SAMPLE_SUMMARY, ["other-ns-pod"])
        self.assertEqual(usage, {})


class TestParseReplicaCounts(unittest.TestCase):
    def test_ready_replicas(self):
        counts = ruc.parse_replica_counts(SAMPLE_DEPLOYS, SERVICES)
        self.assertEqual(counts["frontend"], 1)
        self.assertEqual(counts["checkoutservice"], 1)
        self.assertNotIn("paymentservice", counts)


class TestWriteCsvRows(unittest.TestCase):
    def test_writes_header_and_skips_missing_services(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "resource_usage.csv"
            usage = {
                "frontend": (50, 128_000_000),
                "checkoutservice": (100, 256_000_000),
            }
            replicas = {"frontend": 1, "checkoutservice": 1}
            n = ruc.write_csv_rows(
                path, "2026-08-20T12:00:00Z", usage, replicas, SERVICES
            )
            self.assertEqual(n, 2)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service"], "frontend")
            self.assertEqual(rows[0]["cpu_millicores"], "50")
            self.assertEqual(rows[0]["memory_working_set_bytes"], "128000000")
            self.assertEqual(rows[0]["replica_count"], "1")


class TestDiscoverWorkerNode(unittest.TestCase):
    def test_prefers_non_control_plane(self):
        nodes_json = json.dumps({
            "items": [
                {
                    "metadata": {
                        "name": "master",
                        "labels": {
                            "node-role.kubernetes.io/control-plane": "",
                        },
                    },
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
                {
                    "metadata": {"name": "worker-1", "labels": {}},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
            ],
        })

        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout=nodes_json, stderr="")

        self.assertEqual(ruc.discover_worker_node(run_cmd=runner), "worker-1")


class TestPollOnce(unittest.TestCase):
    def test_end_to_end_mocked(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            calls = []

            def runner(cmd):
                calls.append(cmd)
                if cmd[:3] == ["kubectl", "get", "nodes"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps({
                            "items": [{
                                "metadata": {"name": "worker-1", "labels": {}},
                                "status": {
                                    "conditions": [
                                        {"type": "Ready", "status": "True"},
                                    ],
                                },
                            }],
                        }),
                        stderr="",
                    )
                if "--raw" in cmd:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(SAMPLE_SUMMARY),
                        stderr="",
                    )
                if cmd[:4] == ["kubectl", "get", "deploy", "-n"]:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(SAMPLE_DEPLOYS),
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="fail")

            ruc.poll_once(
                record_path,
                SERVICES,
                "2026-08-20T12:00:05Z",
                run_cmd=runner,
            )
            csv_path = record_path / "resource_usage.csv"
            self.assertTrue(csv_path.exists())
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            services = {r["service"] for r in rows}
            self.assertEqual(services, {"frontend", "checkoutservice", "redis-cart"})


class TestRunCollector(unittest.TestCase):
    def test_max_polls(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            poll_count = {"n": 0}
            orig = ruc.poll_once

            def counting_poll(*args, **kwargs):
                poll_count["n"] += 1

            ruc.poll_once = counting_poll  # type: ignore[assignment]
            try:
                ruc.run_collector(
                    {"poll_interval_seconds": 1, "services": ["frontend"]},
                    record_path,
                    max_polls=2,
                )
            finally:
                ruc.poll_once = orig  # type: ignore[assignment]
            self.assertEqual(poll_count["n"], 2)


if __name__ == "__main__":
    unittest.main()
