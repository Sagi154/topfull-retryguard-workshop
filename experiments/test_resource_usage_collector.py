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

EPOCH = 1700000000.0

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

    def test_sums_across_multiple_pods_of_the_same_service(self):
        # Regression guard for the 2026-09-20 Ron-Nezer migration: frontend
        # can have up to 4 replicas under its new HPA. This collector must
        # keep summing across every matching pod, not just the first.
        summary = {
            "pods": [
                {
                    "podRef": {"name": "frontend-abc123-11111", "namespace": "default"},
                    "containers": [
                        {"name": "server",
                         "cpu": {"usageNanoCores": 200_000_000},
                         "memory": {"workingSetBytes": 1000}},
                    ],
                },
                {
                    "podRef": {"name": "frontend-abc123-22222", "namespace": "default"},
                    "containers": [
                        {"name": "server",
                         "cpu": {"usageNanoCores": 300_000_000},
                         "memory": {"workingSetBytes": 1500}},
                    ],
                },
            ],
        }
        totals = ruc.parse_stats_summary(summary, ["frontend"])
        self.assertEqual(totals["frontend"], (500, 2500))


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


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestDiscoverMasterNode(unittest.TestCase):
    def test_returns_the_control_plane_labeled_node(self):
        nodes_json = {
            "items": [
                {
                    "metadata": {
                        "name": "topfull-worker-1",
                        "labels": {},
                    },
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                },
                {
                    "metadata": {
                        "name": "topfull-master",
                        "labels": {
                            "node-role.kubernetes.io/control-plane": ""
                        },
                    },
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                },
            ]
        }

        def fake_run_cmd(cmd):
            return _FakeResult(stdout=json.dumps(nodes_json))

        self.assertEqual(
            ruc.discover_master_node(run_cmd=fake_run_cmd), "topfull-master"
        )

    def test_returns_none_when_no_control_plane_node_is_ready(self):
        nodes_json = {
            "items": [
                {
                    "metadata": {"name": "topfull-worker-1", "labels": {}},
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                }
            ]
        }

        def fake_run_cmd(cmd):
            return _FakeResult(stdout=json.dumps(nodes_json))

        self.assertIsNone(ruc.discover_master_node(run_cmd=fake_run_cmd))


class TestParseNodeLevelUsage(unittest.TestCase):
    def test_extracts_node_level_cpu_and_memory(self):
        summary = {
            "node": {
                "cpu": {"usageNanoCores": 937000000},
                "memory": {"workingSetBytes": 2147483648},
            },
            "pods": [],
        }
        cpu_mc, mem_bytes = ruc.parse_node_level_usage(summary)
        self.assertEqual(cpu_mc, 937)
        self.assertEqual(mem_bytes, 2147483648)

    def test_missing_node_key_returns_zeros(self):
        cpu_mc, mem_bytes = ruc.parse_node_level_usage({"pods": []})
        self.assertEqual((cpu_mc, mem_bytes), (0, 0))


class TestPollOnceWritesMasterRow(unittest.TestCase):
    def test_master_row_is_written_alongside_service_rows(self):
        worker_summary = {
            "node": {"cpu": {"usageNanoCores": 0}, "memory": {"workingSetBytes": 0}},
            "pods": [
                {
                    "podRef": {"name": "cartservice-abc123", "namespace": "default"},
                    "containers": [
                        {
                            "name": "server",
                            "cpu": {"usageNanoCores": 5000000},
                            "memory": {"workingSetBytes": 1000},
                        }
                    ],
                }
            ],
        }
        master_summary = {
            "node": {
                "cpu": {"usageNanoCores": 937000000},
                "memory": {"workingSetBytes": 2000000000},
            },
            "pods": [],
        }

        def fake_run_cmd(cmd):
            if cmd[:3] == ["kubectl", "get", "nodes"]:
                nodes_json = {
                    "items": [
                        {
                            "metadata": {
                                "name": "topfull-worker-1",
                                "labels": {},
                            },
                            "status": {
                                "conditions": [
                                    {"type": "Ready", "status": "True"}
                                ]
                            },
                        },
                        {
                            "metadata": {
                                "name": "topfull-master",
                                "labels": {
                                    "node-role.kubernetes.io/control-plane": ""
                                },
                            },
                            "status": {
                                "conditions": [
                                    {"type": "Ready", "status": "True"}
                                ]
                            },
                        },
                    ]
                }
                return _FakeResult(stdout=json.dumps(nodes_json))
            if cmd[:3] == ["kubectl", "get", "--raw"] and "topfull-worker-1" in cmd[3]:
                return _FakeResult(stdout=json.dumps(worker_summary))
            if cmd[:3] == ["kubectl", "get", "--raw"] and "topfull-master" in cmd[3]:
                return _FakeResult(stdout=json.dumps(master_summary))
            if cmd[:3] == ["kubectl", "get", "deploy"]:
                return _FakeResult(stdout=json.dumps({"items": []}))
            return _FakeResult(returncode=1)

        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            ruc.poll_once(
                record_path,
                ["cartservice"],
                timestamp="2026-09-15T10:00:00Z",
                run_cmd=fake_run_cmd,
                node_cache={},
            )
            rows = (record_path / "resource_usage.csv").read_text().splitlines()
            self.assertIn("cartservice", rows[1])
            self.assertTrue(
                any(ruc.MASTER_NODE_SERVICE_LABEL in row for row in rows[1:])
            )


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


class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = ruc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = ruc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        ts = ruc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        ruc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)


if __name__ == "__main__":
    unittest.main()
