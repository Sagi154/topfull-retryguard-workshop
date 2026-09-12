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
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_total: 100
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_2xx: 90
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_4xx: 8
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_5xx: 2
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_retry: 12
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_total: 50
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_retry: 3
http.inbound_0.0.0.0_8080.downstream_rq_total: 200
http.inbound_0.0.0.0_8080.downstream_rq_2xx: 180
http.inbound_0.0.0.0_8080.downstream_rq_4xx: 15
http.inbound_0.0.0.0_8080.downstream_rq_5xx: 5
"""


class TestParseEdges(unittest.TestCase):
    def test_extracts_every_target_seen(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(set(edges.keys()), {"cartservice", "productcatalogservice"})

    def test_full_metrics_for_cartservice(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["cartservice"],
            {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "retry": 12},
        )

    def test_missing_metrics_default_to_zero(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["productcatalogservice"],
            {"total": 50, "2xx": 0, "4xx": 0, "5xx": 0, "retry": 3},
        )

    def test_target_never_seen_is_absent_not_zero_filled(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertNotIn("paymentservice", edges)

    def test_empty_stats_text_returns_empty_dict(self):
        self.assertEqual(erc.parse_edges(""), {})


class TestParseInbound(unittest.TestCase):
    def test_extracts_all_four_metrics(self):
        inbound = erc.parse_inbound(SAMPLE_MESH_STATS)
        self.assertEqual(
            inbound, {"total": 200, "2xx": 180, "4xx": 15, "5xx": 5}
        )

    def test_no_inbound_lines_returns_zeros(self):
        inbound = erc.parse_inbound(
            "cluster.outbound|80||cartservice.default.svc.cluster.local."
            "upstream_rq_total: 100\n"
        )
        self.assertEqual(inbound, {"total": 0, "2xx": 0, "4xx": 0, "5xx": 0})

    def test_multiple_listener_ports_are_summed(self):
        text = (
            "http.inbound_0.0.0.0_8080.downstream_rq_total: 100\n"
            "http.inbound_0.0.0.0_9090.downstream_rq_total: 50\n"
        )
        self.assertEqual(erc.parse_inbound(text)["total"], 150)


class TestWriteEdgesCsv(unittest.TestCase):
    def test_writes_header_once_then_appends_multiple_targets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_edges.csv"
            edges_t0 = {
                "cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0, "retry": 2},
                "paymentservice": {"total": 5, "2xx": 5, "4xx": 0, "5xx": 0, "retry": 0},
            }
            erc.write_edges_csv(path, "2026-09-08T12:00:00Z", "checkoutservice", edges_t0)
            edges_t1 = {
                "cartservice": {"total": 20, "2xx": 18, "4xx": 2, "5xx": 0, "retry": 3},
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
                {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2},
            )
            erc.write_inbound_csv(
                path, "2026-09-08T12:00:05Z", "frontend",
                {"total": 150, "2xx": 140, "4xx": 8, "5xx": 2},
            )
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service"], "frontend")
            self.assertEqual(rows[0]["total"], "100")
            self.assertEqual(rows[1]["total"], "150")


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
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        text = erc.fetch_stats_text("frontend-abc123", run_cmd=runner)
        self.assertEqual(text, SAMPLE_MESH_STATS)
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
    def test_writes_edges_and_inbound_for_every_service(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            services = ["frontend", "checkoutservice"]

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(returncode=0, stdout="frontend-1\n", stderr="")
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(returncode=0, stdout="checkout-1\n", stderr="")
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
                if "exec" in cmd and "checkout-1" in cmd:
                    stats = (
                        "cluster.outbound|50051||paymentservice.default."
                        "svc.cluster.local.upstream_rq_total: 7\n"
                        "http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n"
                    )
                    return SimpleNamespace(returncode=0, stdout=stats, stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            erc.poll_once(
                record_path, services,
                timestamp="2026-09-08T12:00:00Z",
                run_cmd=run_cmd, pod_cache={},
            )

            with open(record_path / "service_edges.csv", newline="") as f:
                edges_rows = list(csv.DictReader(f))
            with open(record_path / "service_inbound.csv", newline="") as f:
                inbound_rows = list(csv.DictReader(f))

            self.assertEqual(
                {(r["caller"], r["target"]) for r in edges_rows},
                {("frontend", "cartservice"), ("frontend", "productcatalogservice"),
                 ("checkoutservice", "paymentservice")},
            )
            self.assertEqual(
                {r["service"] for r in inbound_rows},
                {"frontend", "checkoutservice"},
            )
            checkout_inbound = next(r for r in inbound_rows if r["service"] == "checkoutservice")
            self.assertEqual(checkout_inbound["total"], "30")

    def test_survives_one_service_fetch_failure(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            services = ["frontend", "checkoutservice"]

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(returncode=0, stdout="frontend-1\n", stderr="")
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(returncode=0, stdout="checkout-1\n", stderr="")
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(returncode=1, stdout="", stderr="fail")
                if "exec" in cmd and "checkout-1" in cmd:
                    return SimpleNamespace(
                        returncode=0,
                        stdout="http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n",
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            # Must not raise.
            erc.poll_once(
                record_path, services,
                timestamp="2026-09-08T12:00:00Z",
                run_cmd=run_cmd, pod_cache={},
            )
            self.assertFalse((record_path / "service_edges.csv").exists())
            with open(record_path / "service_inbound.csv", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service"], "checkoutservice")


class TestRunCollector(unittest.TestCase):
    def test_max_polls_writes_and_exits(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined:
                    svc = "frontend" if "app=frontend" in joined else "checkoutservice"
                    return SimpleNamespace(returncode=0, stdout=f"{svc}-1\n", stderr="")
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

            erc.run_collector(
                {"poll_interval_seconds": 1, "services": ["frontend", "checkoutservice"]},
                record_path,
                run_cmd=run_cmd,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_edges.csv").exists())
            self.assertTrue((record_path / "service_inbound.csv").exists())


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


class TestDockerPsContainerIdCmd(unittest.TestCase):
    def test_filters_three_k8s_labels(self):
        cmd = erc.docker_ps_container_id_cmd("frontend-abc123")
        self.assertEqual(cmd[0], "docker")
        self.assertIn("ps", cmd)
        self.assertIn("--filter", cmd)
        joined = " ".join(cmd)
        self.assertIn("label=io.kubernetes.pod.name=frontend-abc123", joined)
        self.assertIn("label=io.kubernetes.pod.namespace=default", joined)
        self.assertIn("label=io.kubernetes.container.name=istio-proxy", joined)
        self.assertIn("--format", cmd)
        self.assertIn("{{.ID}}", cmd)


class TestDiscoverContainerId(unittest.TestCase):
    def test_builds_docker_ps_and_returns_id(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="deadbeef12ab\n", stderr="")

        cid = erc.discover_container_id("frontend-abc123", run_cmd=runner)
        self.assertEqual(cid, "deadbeef12ab")
        self.assertEqual(calls[0], erc.docker_ps_container_id_cmd("frontend-abc123"))

    def test_returns_none_on_failure(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="error")

        self.assertIsNone(erc.discover_container_id("frontend-abc123", run_cmd=runner))

    def test_returns_none_on_empty_stdout(self):
        def runner(cmd):
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")

        self.assertIsNone(erc.discover_container_id("frontend-abc123", run_cmd=runner))


class TestDockerExecStatsCmd(unittest.TestCase):
    def test_exact_argv(self):
        self.assertEqual(
            erc.docker_exec_stats_cmd("deadbeef12ab"),
            ["docker", "exec", "deadbeef12ab", "curl", "-s", "http://localhost:15000/stats"],
        )


class TestFetchStatsTextDocker(unittest.TestCase):
    def test_builds_docker_exec_command(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

        text = erc.fetch_stats_text_docker("deadbeef12ab", run_cmd=runner)
        self.assertEqual(text, SAMPLE_MESH_STATS)
        self.assertEqual(calls[0], ["docker", "exec", "deadbeef12ab", "curl", "-s", "http://localhost:15000/stats"])

    def test_returns_none_on_nonzero_exit(self):
        def runner(cmd):
            return SimpleNamespace(returncode=1, stdout="", stderr="No such container")

        self.assertIsNone(erc.fetch_stats_text_docker("oldid", run_cmd=runner))

    def test_returns_none_on_timeout_exception(self):
        def runner(cmd):
            raise TimeoutError("timed out")

        self.assertIsNone(erc.fetch_stats_text_docker("oldid", run_cmd=runner))


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


class TestScrapeOneServiceDocker(unittest.TestCase):
    def test_uses_cached_id_without_docker_ps(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id="cid-old",
            run_cmd=runner,
        )
        self.assertEqual(result.service, "frontend")
        self.assertIn("cartservice", result.edges)
        self.assertEqual(result.inbound["total"], 200)
        self.assertEqual(result.container_id, "cid-old")
        self.assertFalse(result.evict_container)
        self.assertIsNone(result.warning)
        self.assertTrue(all(c[:2] != ["docker", "ps"] for c in calls))

    def test_resolves_id_via_docker_ps_on_cache_miss(self):
        def runner(cmd):
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-new\n", stderr="")
            if cmd[:3] == ["docker", "exec", "cid-new"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id=None,
            run_cmd=runner,
        )
        self.assertEqual(result.container_id, "cid-new")
        self.assertIsNotNone(result.edges)

    def test_exec_failure_evicts_without_raising(self):
        def runner(cmd):
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="No such container")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        result = erc.scrape_one_service(
            "frontend",
            pod_name="frontend-1",
            cached_container_id="cid-old",
            run_cmd=runner,
        )
        self.assertTrue(result.evict_container)
        self.assertIsNone(result.edges)
        self.assertIsNotNone(result.warning)

    def test_missing_pod_name_is_warning_not_raise(self):
        result = erc.scrape_one_service(
            "frontend",
            pod_name=None,
            cached_container_id=None,
            run_cmd=lambda cmd: SimpleNamespace(returncode=0, stdout="", stderr=""),
        )
        self.assertIsNone(result.edges)
        self.assertIn("no seeded pod", result.warning)


class TestPollOnceDockerLocal(unittest.TestCase):
    def test_seeded_pod_names_skip_kubectl(self):
        import tempfile

        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-fe\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        with tempfile.TemporaryDirectory() as td:
            erc.poll_once(
                Path(td),
                ["frontend"],
                timestamp="2026-09-12T12:00:00Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache={},
            )
            inbound = list(
                csv.DictReader((Path(td) / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]["service"], "frontend")
        self.assertTrue(all(c[0] != "kubectl" for c in calls))

    def test_tier1_recovers_on_next_poll(self):
        import tempfile

        state = {"execs": 0}

        def runner(cmd):
            if cmd[:2] == ["docker", "exec"]:
                state["execs"] += 1
                if cmd[2] == "cid-old":
                    return SimpleNamespace(returncode=1, stdout="", stderr="No such container")
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-new\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        cache = {"frontend-1": "cid-old"}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-12T12:00:00Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache=cache,
            )
            self.assertFalse((record_path / "service_inbound.csv").exists())
            self.assertNotIn("frontend-1", cache)

            erc.poll_once(
                record_path,
                ["frontend"],
                timestamp="2026-09-12T12:00:01Z",
                run_cmd=runner,
                exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                pod_names={"frontend": "frontend-1"},
                container_cache=cache,
            )
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual(cache.get("frontend-1"), "cid-new")
        self.assertEqual(len(inbound), 1)

    def test_tier2_warns_and_continues_other_services(self):
        import tempfile
        from unittest import mock

        def runner(cmd):
            joined = " ".join(cmd)
            if cmd[:2] == ["docker", "ps"] and "missing-pod" in joined:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-ok\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        warn_state = {}
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            with mock.patch.object(erc.log, "warning") as warn:
                for i in range(5):
                    erc.poll_once(
                        record_path,
                        ["frontend", "checkoutservice"],
                        timestamp="2026-09-12T12:00:00Z",
                        run_cmd=runner,
                        exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                        pod_names={
                            "frontend": "missing-pod",
                            "checkoutservice": "checkout-1",
                        },
                        container_cache={},
                        poll_index=i,
                        tier2_warn_state=warn_state,
                    )
                self.assertLessEqual(warn.call_count, 2)
            inbound = list(
                csv.DictReader((record_path / "service_inbound.csv").open(newline=""))
            )
        self.assertEqual({r["service"] for r in inbound}, {"checkoutservice"})
        self.assertEqual(len(inbound), 5)


class TestPollOnceThreadPoolSerialWrites(unittest.TestCase):
    def test_one_inbound_row_per_service_and_writes_from_main_thread(self):
        import tempfile
        import threading
        from unittest import mock

        def runner(cmd):
            if cmd[:2] == ["docker", "ps"]:
                pod = "frontend-1" if "frontend-1" in " ".join(cmd) else "checkout-1"
                return SimpleNamespace(
                    returncode=0,
                    stdout=("cid-fe\n" if pod == "frontend-1" else "cid-co\n"),
                    stderr="",
                )
            if cmd[:2] == ["docker", "exec"]:
                if cmd[2] == "cid-fe":
                    return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
                stats = (
                    "cluster.outbound|50051||paymentservice.default."
                    "svc.cluster.local.upstream_rq_total: 7\n"
                    "http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n"
                )
                return SimpleNamespace(returncode=0, stdout=stats, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

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
                    timestamp="2026-09-12T12:00:00Z",
                    run_cmd=runner,
                    exec_mode=erc.EXEC_MODE_DOCKER_LOCAL,
                    pod_names={
                        "frontend": "frontend-1",
                        "checkoutservice": "checkout-1",
                    },
                    container_cache={},
                    max_workers=2,
                )
            inbound = list(
                csv.DictReader((Path(td) / "service_inbound.csv").open(newline=""))
            )
            edges = list(
                csv.DictReader((Path(td) / "service_edges.csv").open(newline=""))
            )

        self.assertEqual(
            {r["service"] for r in inbound},
            {"frontend", "checkoutservice"},
        )
        self.assertEqual(len(inbound), 2)
        self.assertEqual(
            {(r["caller"], r["target"]) for r in edges},
            {
                ("frontend", "cartservice"),
                ("frontend", "productcatalogservice"),
                ("checkoutservice", "paymentservice"),
            },
        )
        self.assertTrue(write_threads)
        self.assertTrue(all(t is threading.main_thread() for t in write_threads))

    def test_docker_local_branch_uses_thread_pool_executor(self):
        import inspect

        src = inspect.getsource(erc.poll_once)
        self.assertIn("ThreadPoolExecutor", src)
        self.assertIn("as_completed", src)


class TestResolveExecMode(unittest.TestCase):
    def test_defaults_to_kubectl(self):
        self.assertEqual(erc.resolve_exec_mode({}), erc.EXEC_MODE_KUBECTL)

    def test_params_then_cli_override(self):
        self.assertEqual(
            erc.resolve_exec_mode({"exec_mode": "docker_local"}),
            erc.EXEC_MODE_DOCKER_LOCAL,
        )
        self.assertEqual(
            erc.resolve_exec_mode(
                {"exec_mode": "docker_local"}, cli_exec_mode="kubectl"
            ),
            erc.EXEC_MODE_KUBECTL,
        )


class TestResolveRecordPath(unittest.TestCase):
    def test_params_override_skips_global_config(self):
        path = erc.resolve_record_path({"record_path": "C:/tmp/mesh_local/run1"})
        self.assertEqual(path, Path("C:/tmp/mesh_local/run1"))


class TestRunCollectorDockerLocal(unittest.TestCase):
    def test_uses_seeded_pod_names_and_record_path(self):
        import tempfile

        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[:2] == ["docker", "ps"]:
                return SimpleNamespace(returncode=0, stdout="cid-fe\n", stderr="")
            if cmd[:2] == ["docker", "exec"]:
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            erc.run_collector(
                {
                    "poll_interval_seconds": 1,
                    "exec_mode": "docker_local",
                    "max_workers": 2,
                    "services": ["frontend"],
                    "pod_names": {"frontend": "frontend-1"},
                    "record_path": str(record_path),
                },
                record_path,
                run_cmd=runner,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_inbound.csv").exists())
        self.assertTrue(all(c[0] != "kubectl" for c in calls))


if __name__ == "__main__":
    unittest.main()
