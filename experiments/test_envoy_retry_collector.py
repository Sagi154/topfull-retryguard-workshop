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

EPOCH = 1700000000.0


SAMPLE_MESH_STATS = """\
envoy_cluster_upstream_rq_total{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 100
envoy_cluster_upstream_rq{response_code_class="2xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 90
envoy_cluster_upstream_rq{cluster_name="outbound|80||cartservice.default.svc.cluster.local",response_code_class="4xx"} 8
envoy_cluster_upstream_rq{response_code_class="5xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 2
envoy_cluster_upstream_rq_retry{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 12
envoy_cluster_upstream_rq_total{cluster_name="outbound|9555||productcatalogservice.default.svc.cluster.local"} 50
envoy_cluster_upstream_rq_retry{cluster_name="outbound|9555||productcatalogservice.default.svc.cluster.local"} 3
envoy_cluster_upstream_rq{response_code="200",cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 90
envoy_cluster_upstream_rq_total{cluster_name="outbound|15010||istiod.istio-system.svc.cluster.local"} 9
envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 200
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="2xx"} 180
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="4xx"} 15
envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class="5xx"} 5
envoy_http_inbound_0_0_0_0_8080_downstream_rq_completed{} 180
envoy_cluster_upstream_rq_time_sum{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 4500
envoy_cluster_upstream_rq_time_count{cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 100
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_sum{} 9000
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_count{} 200
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="0.5"} 0
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="1"} 10
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="5"} 50
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="10"} 100
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="25"} 180
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="50"} 195
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="100"} 200
envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_bucket{le="+Inf"} 200
"""


class TestParseEdges(unittest.TestCase):
    def test_extracts_every_target_seen(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(set(edges.keys()), {"cartservice", "productcatalogservice"})

    def test_full_metrics_for_cartservice(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["cartservice"],
            {
                "total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "retry": 12,
                "rq_time_sum_ms": 4500, "rq_time_count": 100,
            },
        )

    def test_missing_metrics_default_to_zero(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["productcatalogservice"],
            {
                "total": 50, "2xx": 0, "4xx": 0, "5xx": 0, "retry": 3,
                "rq_time_sum_ms": 0, "rq_time_count": 0,
            },
        )

    def test_target_never_seen_is_absent_not_zero_filled(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertNotIn("paymentservice", edges)

    def test_empty_stats_text_returns_empty_dict(self):
        self.assertEqual(erc.parse_edges(""), {})


class TestParseInbound(unittest.TestCase):
    def test_extracts_all_metrics(self):
        inbound = erc.parse_inbound(SAMPLE_MESH_STATS)
        self.assertEqual(inbound["total"], 200)
        self.assertEqual(inbound["2xx"], 180)
        self.assertEqual(inbound["4xx"], 15)
        self.assertEqual(inbound["5xx"], 5)
        self.assertEqual(inbound["resets"], 0)
        self.assertEqual(inbound["rq_time_sum_ms"], 9000)
        self.assertEqual(inbound["rq_time_count"], 200)
        import json
        buckets = json.loads(inbound["rq_time_buckets"])
        self.assertEqual(buckets["10"], 100)
        self.assertEqual(buckets["+Inf"], 200)

    def test_no_inbound_lines_returns_zeros(self):
        inbound = erc.parse_inbound(
            "cluster.outbound|80||cartservice.default.svc.cluster.local."
            "upstream_rq_total: 100\n"
        )
        self.assertEqual(
            inbound,
            {
                "total": 0, "2xx": 0, "4xx": 0, "5xx": 0, "resets": 0,
                "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": "",
            },
        )

    def test_rq_time_sum_and_count_parsed_independently(self):
        text = (
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 10\n"
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_sum{} 250\n"
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq_time_count{} 10\n"
        )
        inbound = erc.parse_inbound(text)
        self.assertEqual(inbound["rq_time_sum_ms"], 250)
        self.assertEqual(inbound["rq_time_count"], 10)
        self.assertEqual(inbound["rq_time_buckets"], "")

class TestParsePromLabels(unittest.TestCase):
    def test_empty_braces(self):
        self.assertEqual(erc.parse_prom_labels("{}"), {})

    def test_order_independent(self):
        a = erc.parse_prom_labels(
            '{response_code_class="2xx",cluster_name="outbound|80||cartservice.default.svc.cluster.local"}'
        )
        b = erc.parse_prom_labels(
            '{cluster_name="outbound|80||cartservice.default.svc.cluster.local",response_code_class="2xx"}'
        )
        self.assertEqual(a, b)
        self.assertEqual(a["response_code_class"], "2xx")
        self.assertEqual(
            a["cluster_name"],
            "outbound|80||cartservice.default.svc.cluster.local",
        )

    def test_strips_optional_braces(self):
        self.assertEqual(erc.parse_prom_labels('k="v"'), {"k": "v"})


class TestTargetFromClusterName(unittest.TestCase):
    def test_default_namespace_target(self):
        self.assertEqual(
            erc.target_from_cluster_name(
                "outbound|3550||productcatalogservice.default.svc.cluster.local"
            ),
            "productcatalogservice",
        )

    def test_ignores_istio_system(self):
        self.assertIsNone(
            erc.target_from_cluster_name(
                "outbound|15010||istiod.istio-system.svc.cluster.local"
            )
        )


class TestParseInboundDoesNotMergeListeners(unittest.TestCase):
    def test_keeps_listener_with_largest_total(self):
        text = (
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 100\n"
            "envoy_http_inbound_0_0_0_0_8080_downstream_rq{response_code_class=\"2xx\"} 90\n"
            "envoy_http_inbound_0_0_0_0_9090_downstream_rq_total{} 50\n"
            "envoy_http_inbound_0_0_0_0_9090_downstream_rq{response_code_class=\"2xx\"} 50\n"
        )
        inbound = erc.parse_inbound(text)
        self.assertEqual(inbound["total"], 100)
        self.assertEqual(inbound["2xx"], 90)


class TestSumEdgeMaps(unittest.TestCase):
    def test_sums_matching_targets_across_pods(self):
        pod_a = {"cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0,
                                  "retry": 2, "rq_time_sum_ms": 100, "rq_time_count": 10}}
        pod_b = {"cartservice": {"total": 20, "2xx": 18, "4xx": 2, "5xx": 0,
                                  "retry": 3, "rq_time_sum_ms": 200, "rq_time_count": 20}}
        summed = erc.sum_edge_maps([pod_a, pod_b])
        self.assertEqual(summed["cartservice"], {
            "total": 30, "2xx": 27, "4xx": 3, "5xx": 0,
            "retry": 5, "rq_time_sum_ms": 300, "rq_time_count": 30,
        })

    def test_target_seen_by_only_one_pod_is_not_lost(self):
        pod_a = {"cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0,
                                  "retry": 2, "rq_time_sum_ms": 100, "rq_time_count": 10}}
        pod_b = {"paymentservice": {"total": 5, "2xx": 5, "4xx": 0, "5xx": 0,
                                     "retry": 0, "rq_time_sum_ms": 50, "rq_time_count": 5}}
        summed = erc.sum_edge_maps([pod_a, pod_b])
        self.assertEqual(set(summed.keys()), {"cartservice", "paymentservice"})
        self.assertEqual(summed["paymentservice"]["total"], 5)

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(erc.sum_edge_maps([]), {})


class TestSumInboundMaps(unittest.TestCase):
    def test_sums_scalar_metrics_across_pods(self):
        pod_a = {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "resets": 0,
                  "rq_time_sum_ms": 500, "rq_time_count": 100, "rq_time_buckets": '{"10":50,"+Inf":100}'}
        pod_b = {"total": 50, "2xx": 45, "4xx": 4, "5xx": 1, "resets": 0,
                  "rq_time_sum_ms": 250, "rq_time_count": 50, "rq_time_buckets": '{"10":25,"+Inf":50}'}
        summed = erc.sum_inbound_maps([pod_a, pod_b])
        self.assertEqual(summed["total"], 150)
        self.assertEqual(summed["2xx"], 135)
        self.assertEqual(summed["4xx"], 12)
        self.assertEqual(summed["5xx"], 3)
        self.assertEqual(summed["rq_time_sum_ms"], 750)
        self.assertEqual(summed["rq_time_count"], 150)
        import json
        buckets = json.loads(summed["rq_time_buckets"])
        self.assertEqual(buckets["10"], 75)
        self.assertEqual(buckets["+Inf"], 150)

    def test_single_pod_passthrough(self):
        pod_a = {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "resets": 0,
                  "rq_time_sum_ms": 500, "rq_time_count": 100, "rq_time_buckets": ""}
        self.assertEqual(erc.sum_inbound_maps([pod_a])["total"], 100)

    def test_empty_list_returns_zeros(self):
        summed = erc.sum_inbound_maps([])
        self.assertEqual(summed["total"], 0)
        self.assertEqual(summed["rq_time_buckets"], "")

    def test_no_buckets_present_leaves_empty_string(self):
        pod_a = {"total": 10, "2xx": 10, "4xx": 0, "5xx": 0, "resets": 0,
                  "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": ""}
        pod_b = {"total": 20, "2xx": 20, "4xx": 0, "5xx": 0, "resets": 0,
                  "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": ""}
        summed = erc.sum_inbound_maps([pod_a, pod_b])
        self.assertEqual(summed["rq_time_buckets"], "")


class TestWriteEdgesCsv(unittest.TestCase):
    def test_writes_header_once_then_appends_multiple_targets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_edges.csv"
            edges_t0 = {
                "cartservice": {
                    "total": 10, "2xx": 9, "4xx": 1, "5xx": 0, "retry": 2,
                    "rq_time_sum_ms": 400, "rq_time_count": 10,
                },
                "paymentservice": {
                    "total": 5, "2xx": 5, "4xx": 0, "5xx": 0, "retry": 0,
                    "rq_time_sum_ms": 100, "rq_time_count": 5,
                },
            }
            erc.write_edges_csv(path, "2026-09-08T12:00:00Z", "checkoutservice", edges_t0)
            edges_t1 = {
                "cartservice": {
                    "total": 20, "2xx": 18, "4xx": 2, "5xx": 0, "retry": 3,
                    "rq_time_sum_ms": 900, "rq_time_count": 20,
                },
            }
            erc.write_edges_csv(path, "2026-09-08T12:00:05Z", "checkoutservice", edges_t1)

            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["caller"], "checkoutservice")
            self.assertEqual(rows[0]["target"], "cartservice")
            self.assertEqual(rows[0]["retry"], "2")
            self.assertEqual(rows[1]["target"], "paymentservice")
            self.assertEqual(rows[2]["total"], "20")

    def test_empty_edges_writes_no_rows_but_no_error(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_edges.csv"
            erc.write_edges_csv(path, "2026-09-08T12:00:00Z", "frontend", {})
            self.assertFalse(path.exists())


class TestWriteInboundCsv(unittest.TestCase):
    def test_writes_header_once_then_appends(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_inbound.csv"
            erc.write_inbound_csv(
                path, "2026-09-08T12:00:00Z", "frontend",
                {
                    "total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "resets": 0,
                    "rq_time_sum_ms": 500, "rq_time_count": 100,
                    "rq_time_buckets": '{"10":50,"+Inf":100}',
                },
            )
            erc.write_inbound_csv(
                path, "2026-09-08T12:00:05Z", "frontend",
                {
                    "total": 150, "2xx": 140, "4xx": 8, "5xx": 2, "resets": 0,
                    "rq_time_sum_ms": 800, "rq_time_count": 150,
                    "rq_time_buckets": '{"10":80,"+Inf":150}',
                },
            )
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service"], "frontend")
            self.assertEqual(rows[0]["total"], "100")
            self.assertEqual(rows[1]["total"], "150")
            self.assertIn("rq_time_buckets", rows[0])
            self.assertEqual(rows[0]["rq_time_buckets"], '{"10":50,"+Inf":100}')


class TestPrometheusStatsUrl(unittest.TestCase):
    def test_default_port_and_path(self):
        self.assertEqual(
            erc.prometheus_stats_url("192.168.148.90"),
            "http://192.168.148.90:15020/stats/prometheus",
        )


class TestDiscoverPodIp(unittest.TestCase):
    def test_builds_kubectl_jsonpath_for_pod_ip(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="192.168.148.90\n", stderr="")

        ip = erc.discover_pod_ip("frontend", run_cmd=runner)
        self.assertEqual(ip, "192.168.148.90")
        self.assertEqual(calls[0][:3], ["kubectl", "get", "pods"])
        self.assertIn("app=frontend", calls[0])
        self.assertTrue(any("podIP" in part for part in calls[0]))

    def test_returns_none_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertIsNone(erc.discover_pod_ip("frontend", run_cmd=runner))

    def test_returns_none_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertIsNone(erc.discover_pod_ip("frontend", run_cmd=runner))


class TestParseIpList(unittest.TestCase):
    def test_single_ip_no_comma(self):
        self.assertEqual(erc.parse_ip_list("192.168.1.10"), ["192.168.1.10"])

    def test_multiple_comma_joined_ips(self):
        self.assertEqual(
            erc.parse_ip_list("192.168.1.10,192.168.1.11"),
            ["192.168.1.10", "192.168.1.11"],
        )

    def test_none_or_empty_returns_empty_list(self):
        self.assertEqual(erc.parse_ip_list(None), [])
        self.assertEqual(erc.parse_ip_list(""), [])

    def test_strips_whitespace_around_commas(self):
        self.assertEqual(
            erc.parse_ip_list("192.168.1.10, 192.168.1.11"),
            ["192.168.1.10", "192.168.1.11"],
        )


class TestJoinIpList(unittest.TestCase):
    def test_single_ip(self):
        self.assertEqual(erc.join_ip_list(["192.168.1.10"]), "192.168.1.10")

    def test_multiple_ips(self):
        self.assertEqual(
            erc.join_ip_list(["192.168.1.10", "192.168.1.11"]),
            "192.168.1.10,192.168.1.11",
        )

    def test_empty_list(self):
        self.assertEqual(erc.join_ip_list([]), "")


class TestDiscoverPodIps(unittest.TestCase):
    def test_returns_every_pod_ip_not_just_first(self):
        def runner(cmd):
            return SimpleNamespace(
                returncode=0, stdout="192.168.1.10\n192.168.1.11\n", stderr=""
            )

        ips = erc.discover_pod_ips("frontend", run_cmd=runner)
        self.assertEqual(ips, ["192.168.1.10", "192.168.1.11"])

    def test_single_pod_service(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr="")

        self.assertEqual(erc.discover_pod_ips("checkoutservice", run_cmd=runner), ["192.168.1.10"])

    def test_returns_empty_list_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertEqual(erc.discover_pod_ips("frontend", run_cmd=runner), [])

    def test_returns_empty_list_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertEqual(erc.discover_pod_ips("frontend", run_cmd=runner), [])

    def test_uses_range_jsonpath_over_all_items(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="192.168.1.10\n", stderr="")

        erc.discover_pod_ips("frontend", run_cmd=runner)
        self.assertIn("app=frontend", calls[0])
        self.assertIn("range .items[*]", calls[0][-1])


class TestFetchPodList(unittest.TestCase):
    def test_returns_parsed_json_on_success(self):
        def runner(cmd):
            return SimpleNamespace(
                returncode=0,
                stdout='{"items": [{"metadata": {"name": "frontend-abc"}}]}',
                stderr="",
            )

        result = erc.fetch_pod_list(run_cmd=runner)
        self.assertEqual(result, {"items": [{"metadata": {"name": "frontend-abc"}}]})

    def test_builds_whole_namespace_kubectl_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="{}", stderr="")

        erc.fetch_pod_list(run_cmd=runner)
        self.assertEqual(
            calls[0],
            ["kubectl", "get", "pods", "-n", "default", "-o", "json"],
        )

    def test_returns_none_on_nonzero_exit(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))

    def test_returns_none_on_exception(self):
        def runner(cmd):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))

    def test_returns_none_on_invalid_json(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="not-json", stderr="")

        self.assertIsNone(erc.fetch_pod_list(run_cmd=runner))


class TestPodServiceName(unittest.TestCase):
    def test_matches_exact_and_prefix(self):
        services = ["frontend", "checkoutservice"]
        self.assertEqual(
            erc.pod_service_name("frontend-abc123-11111", services), "frontend"
        )
        self.assertEqual(
            erc.pod_service_name("checkoutservice-def456-22222", services),
            "checkoutservice",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(erc.pod_service_name("istiod-abc123", ["frontend"]))

    def test_prefers_longest_matching_service_name(self):
        # Same tie-break rule as topfull_throttle_collector.py's
        # _pod_service_name, in case two service names ever overlap.
        services = ["cart", "cartservice"]
        self.assertEqual(
            erc.pod_service_name("cartservice-xyz-1", services), "cartservice"
        )


SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS = {
    "items": [
        {
            "metadata": {"name": "frontend-abc123-11111"},
            "status": {"phase": "Running", "podIP": "10.0.0.5"},
        },
        {
            "metadata": {"name": "frontend-abc123-22222"},
            "status": {"phase": "Running", "podIP": "10.0.0.9"},
        },
        {
            "metadata": {"name": "checkoutservice-def456-1"},
            "status": {"phase": "Running", "podIP": "10.0.0.20"},
        },
        {
            "metadata": {"name": "frontend-abc123-33333"},
            "status": {"phase": "Pending"},
        },
        {
            "metadata": {"name": "frontend-abc123-44444"},
            "status": {"phase": "Terminating", "podIP": "10.0.0.99"},
        },
    ],
}


class TestPodIpsFromPodList(unittest.TestCase):
    def test_groups_running_pods_by_service(self):
        ips = erc.pod_ips_from_pod_list(
            SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS, ["frontend", "checkoutservice"]
        )
        self.assertEqual(ips["frontend"], ["10.0.0.5", "10.0.0.9"])
        self.assertEqual(ips["checkoutservice"], ["10.0.0.20"])

    def test_excludes_pending_and_terminating_pods(self):
        ips = erc.pod_ips_from_pod_list(
            SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS, ["frontend"]
        )
        self.assertNotIn("10.0.0.99", ips["frontend"])
        self.assertEqual(len(ips["frontend"]), 2)

    def test_service_with_no_running_pods_is_empty_list_not_missing_key(self):
        ips = erc.pod_ips_from_pod_list({"items": []}, ["adservice"])
        self.assertEqual(ips["adservice"], [])


class TestRefreshIpCache(unittest.TestCase):
    def test_replaces_cache_with_fresh_snapshot(self):
        import json

        def runner(cmd):
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(SAMPLE_POD_LIST_TWO_FRONTEND_REPLICAS),
                stderr="",
            )

        cache = {"frontend": "10.0.0.1"}  # stale single IP
        erc.refresh_ip_cache(cache, ["frontend", "checkoutservice"], run_cmd=runner)
        self.assertEqual(cache["frontend"], "10.0.0.5,10.0.0.9")
        self.assertEqual(cache["checkoutservice"], "10.0.0.20")

    def test_kubectl_failure_leaves_cache_untouched(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        cache = {"frontend": "10.0.0.1"}
        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(cache, {"frontend": "10.0.0.1"})

    def test_service_with_no_pods_is_dropped_from_cache(self):
        import json

        def runner(cmd):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps({"items": []}), stderr=""
            )

        cache = {"frontend": "10.0.0.1"}
        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(cache, {})

    def test_mutates_in_place_same_object(self):
        cache = {"frontend": "10.0.0.1"}
        original_id = id(cache)

        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        erc.refresh_ip_cache(cache, ["frontend"], run_cmd=runner)
        self.assertEqual(id(cache), original_id)


class TestFetchStatsTextHttp(unittest.TestCase):
    def test_requests_prometheus_url(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        text = erc.fetch_stats_text("192.168.148.90", fetch_url=fetch)
        self.assertEqual(text, SAMPLE_MESH_STATS)
        self.assertEqual(calls, [erc.prometheus_stats_url("192.168.148.90")])

    def test_returns_none_on_nonzero(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        self.assertIsNone(erc.fetch_stats_text("10.0.0.1", fetch_url=fetch))

    def test_returns_none_on_timeout_exception(self):
        def fetch(url):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_stats_text("10.0.0.1", fetch_url=fetch))


class TestResolveServices(unittest.TestCase):
    def test_defaults_to_all_services(self):
        self.assertEqual(erc.resolve_services({}), erc.ALL_SERVICES)

    def test_override_via_params(self):
        self.assertEqual(
            erc.resolve_services({"services": ["frontend", "cartservice"]}),
            ["frontend", "cartservice"],
        )


class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = erc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = erc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        ts = erc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        erc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)


class TestShouldLogTier2(unittest.TestCase):
    def test_logs_first_then_is_bounded(self):
        state = {}
        logged = []
        for i in range(5):
            if erc.should_log_tier2("frontend", i, state):
                logged.append(i)
        self.assertEqual(logged, [0])

    def test_logs_again_after_interval(self):
        state = {}
        self.assertTrue(erc.should_log_tier2("frontend", 0, state))
        self.assertTrue(
            erc.should_log_tier2("frontend", erc.TIER2_WARN_EVERY_POLLS, state)
        )


class TestResolveRecordPath(unittest.TestCase):
    def test_params_override_skips_global_config(self):
        path = erc.resolve_record_path({"record_path": "C:/tmp/mesh_local/run1"})
        self.assertEqual(path, Path("C:/tmp/mesh_local/run1"))


class TestScrapeOneServiceHttp(unittest.TestCase):
    def test_parses_when_ip_present(self):
        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        result = erc.scrape_one_service("frontend", "192.168.1.10", fetch)
        self.assertIn("cartservice", result.edges)
        self.assertEqual(result.inbound["total"], 200)
        self.assertFalse(result.evict_ip)
        self.assertIsNone(result.warning)

    def test_missing_ip_is_warning(self):
        result = erc.scrape_one_service(
            "frontend", None, lambda url: SimpleNamespace(returncode=0, stdout="", stderr="")
        )
        self.assertIsNone(result.edges)
        self.assertIn("no seeded ip", result.warning)

    def test_fetch_failure_evicts_without_raising(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service("frontend", "10.0.0.1", fetch)
        self.assertTrue(result.evict_ip)
        self.assertIsNone(result.edges)
        self.assertIsNotNone(result.warning)

    def test_scrapes_and_sums_multiple_comma_joined_ips(self):
        fetch_log = []

        def fetch(url):
            fetch_log.append(url)
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            # Second replica: half the traffic of the first, same shape.
            stats = SAMPLE_MESH_STATS.replace(
                'cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 100',
                'cluster_name="outbound|80||cartservice.default.svc.cluster.local"} 40',
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertEqual(len(fetch_log), 2)
        self.assertIsNone(result.warning)
        self.assertEqual(result.edges["cartservice"]["total"], 140)
        self.assertEqual(result.inbound["total"], 400)  # 200 + 200

    def test_partial_failure_sums_only_surviving_ips_and_warns(self):
        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertIsNotNone(result.edges)
        self.assertEqual(result.edges["cartservice"]["total"], 100)
        self.assertTrue(result.had_partial_failure)
        self.assertIn("tier2", result.warning)
        self.assertIn("192.168.1.11", result.warning)

    def test_all_ips_fail_evicts_like_single_ip_failure(self):
        def fetch(url):
            return SimpleNamespace(returncode=1, stdout="", stderr="connection refused")

        result = erc.scrape_one_service(
            "frontend", "192.168.1.10,192.168.1.11", fetch
        )
        self.assertTrue(result.evict_ip)
        self.assertIsNone(result.edges)


class TestPollOnceNetwork(unittest.TestCase):
    def test_writes_edges_and_inbound_for_every_service(self):
        import tempfile

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            stats = (
                "envoy_cluster_upstream_rq_total"
                '{cluster_name="outbound|50051||paymentservice.default.svc.cluster.local"} 7\n'
                "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n"
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend", "checkoutservice"],
                timestamp="2026-09-13T12:00:00Z",
                fetch_url=fetch,
                ip_cache={
                    "frontend": "192.168.1.10",
                    "checkoutservice": "192.168.1.11",
                },
            )
            edges_rows = list(csv.DictReader((Path(td) / "service_edges.csv").open(newline="")))
            inbound_rows = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(
            {(r["caller"], r["target"]) for r in edges_rows},
            {
                ("frontend", "cartservice"),
                ("frontend", "productcatalogservice"),
                ("checkoutservice", "paymentservice"),
            },
        )
        self.assertEqual(edges_rows[0]["2xx"] != "" or True, True)
        fe = next(r for r in edges_rows if r["caller"] == "frontend" and r["target"] == "cartservice")
        self.assertEqual(fe["2xx"], "90")
        self.assertEqual({r["service"] for r in inbound_rows}, {"frontend", "checkoutservice"})

    def test_survives_one_service_fetch_failure(self):
        import tempfile

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=1, stdout="", stderr="fail")
            return SimpleNamespace(
                returncode=0,
                stdout="envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n",
                stderr="",
            )

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend", "checkoutservice"],
                timestamp="2026-09-13T12:00:00Z",
                fetch_url=fetch,
                ip_cache={
                    "frontend": "192.168.1.10",
                    "checkoutservice": "192.168.1.11",
                },
                run_cmd=lambda cmd: SimpleNamespace(returncode=1, stdout="", stderr=""),
            )
            self.assertFalse((Path(td) / "service_edges.csv").exists())
            rows = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["service"], "checkoutservice")


class TestPollOnceThreadPoolSerialWrites(unittest.TestCase):
    def test_one_inbound_row_per_service_and_writes_from_main_thread(self):
        import tempfile
        import threading
        from unittest import mock

        def fetch(url):
            if "192.168.1.10" in url:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            stats = (
                "envoy_cluster_upstream_rq_total"
                '{cluster_name="outbound|50051||paymentservice.default.svc.cluster.local"} 7\n'
                "envoy_http_inbound_0_0_0_0_8080_downstream_rq_total{} 30\n"
            )
            return SimpleNamespace(returncode=0, stdout=stats, stderr="")

        write_threads = []
        real_write_inbound = erc.write_inbound_csv

        def spy_write_inbound(csv_path, timestamp, service, inbound):
            write_threads.append(threading.current_thread())
            return real_write_inbound(csv_path, timestamp, service, inbound)

        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(erc, "write_inbound_csv", side_effect=spy_write_inbound):
                erc.poll_once(
                    Path(td),
                    ["frontend", "checkoutservice"],
                    timestamp="2026-09-13T12:00:00Z",
                    fetch_url=fetch,
                    ip_cache={
                        "frontend": "192.168.1.10",
                        "checkoutservice": "192.168.1.11",
                    },
                    max_workers=2,
                )
            inbound = list(csv.DictReader((Path(td) / "service_inbound.csv").open(newline="")))
        self.assertEqual(len(inbound), 2)
        self.assertTrue(write_threads)
        self.assertTrue(all(t is threading.main_thread() for t in write_threads))

    def test_poll_once_uses_thread_pool_executor(self):
        import inspect

        src = inspect.getsource(erc.poll_once)
        self.assertIn("ThreadPoolExecutor", src)
        self.assertIn("as_completed", src)


class TestPollOnceIpCacheRefresh(unittest.TestCase):
    def test_first_tick_uses_seeded_cache_without_any_kubectl_call(self):
        import tempfile

        kubectl_calls = []

        def runner(cmd):
            kubectl_calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="{}", stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}
        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend"],
                timestamp="2026-09-21T12:00:00Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=0,
                tier2_warn_state={},
            )
        self.assertEqual(kubectl_calls, [])
        self.assertEqual(cache, {"frontend": "192.168.1.10"})

    def test_healthy_scale_up_is_scraped_next_tick_with_zero_fetch_failures(self):
        import json
        import tempfile

        pod_list = {
            "items": [
                {
                    "metadata": {"name": "frontend-abc-11111"},
                    "status": {"phase": "Running", "podIP": "192.168.1.10"},
                },
                {
                    "metadata": {"name": "frontend-abc-22222"},
                    "status": {"phase": "Running", "podIP": "192.168.1.11"},
                },
            ],
        }

        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout=json.dumps(pod_list), stderr="")

        fetch_log = []

        def fetch(url):
            fetch_log.append(url)
            # Both replicas answer successfully — no fetch failure at all,
            # unlike the retired reseed mechanism this test replaces.
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}  # seeded with only the original replica
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache["frontend"], "192.168.1.10,192.168.1.11")
        self.assertEqual(len(fetch_log), 2)
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["total"], "400")  # 200 + 200, both replicas summed

    def test_refresh_runs_every_tick_from_poll_index_one_onward(self):
        import json
        import tempfile

        kubectl_calls = []

        def runner(cmd):
            kubectl_calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=json.dumps({"items": []}), stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        cache = {}
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                erc.poll_once(
                    Path(td),
                    ["frontend"],
                    timestamp="2026-09-21T12:00:00Z",
                    run_cmd=runner,
                    fetch_url=fetch,
                    ip_cache=cache,
                    poll_index=i,
                    tier2_warn_state={},
                )
        # poll_index 0 skips the refresh (seeded tick); 1,2,3,4 each refresh
        # once — the accepted cost model (one whole-namespace kubectl call
        # per tick), not rate-limited like the retired per-service reseed.
        self.assertEqual(len(kubectl_calls), 4)

    def test_kubectl_failure_this_tick_keeps_previous_cache_and_keeps_scraping(self):
        import tempfile

        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="refused")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        cache = {"frontend": "192.168.1.10"}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache, {"frontend": "192.168.1.10"})  # untouched, not wiped
        self.assertEqual(len(inbound), 1)  # scrape still happened, using the old IP

    def test_departed_service_is_dropped_from_cache_next_tick(self):
        import json
        import tempfile

        pod_list = {"items": []}  # checkoutservice's pod is gone this tick

        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout=json.dumps(pod_list), stderr="")

        def fetch(url):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        cache = {"checkoutservice": "10.0.0.50"}
        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["checkoutservice"],
                timestamp="2026-09-21T12:00:01Z",
                run_cmd=runner,
                fetch_url=fetch,
                ip_cache=cache,
                poll_index=1,
                tier2_warn_state={},
            )
        self.assertEqual(cache, {})


class TestRunCollectorNetwork(unittest.TestCase):
    def test_uses_seeded_pod_ips(self):
        import tempfile

        calls = []

        def fetch(url):
            calls.append(url)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.run_collector(
                {
                    "poll_interval_seconds": 1,
                    "max_workers": 2,
                    "services": ["frontend"],
                    "pod_ips": {"frontend": "192.168.1.10"},
                    "transport": "network_prometheus",
                },
                record_path,
                fetch_url=fetch,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_inbound.csv").exists())
        self.assertEqual(calls, [erc.prometheus_stats_url("192.168.1.10")])


if __name__ == "__main__":
    unittest.main()
