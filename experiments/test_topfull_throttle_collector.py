"""
test_topfull_throttle_collector.py — Unit tests for TopFull throttle collector.

Run:
    python experiments/test_topfull_throttle_collector.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_throttle_collector as ttc

# 2023-11-14T22:13:20Z
EPOCH = 1700000000.0


class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        # 22:13:20 is already mod 5 == 0; +3s → still 22:13:20
        ts = ttc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_next_bucket(self):
        ts = ttc.tick_timestamp(5, now=EPOCH + 5.0)
        self.assertEqual(ts, "2023-11-14T22:13:25Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        ttc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)

    def test_zero_when_already_on_next_boundary_is_non_negative(self):
        slept = []
        ttc.sleep_until_next_tick(1, now=EPOCH, sleeper=lambda s: slept.append(s))
        self.assertGreaterEqual(slept[0], 0.0)
        self.assertLessEqual(slept[0], 1.0)


class TestIsLayerAAttemptTick(unittest.TestCase):
    def test_true_only_on_multiples_of_five(self):
        # Spec §5: poll_interval=1, layer_a=5, epochs 0..9 → True only at 0 and 5.
        got = [
            ttc.is_layer_a_attempt_tick(epoch, 5) for epoch in range(10)
        ]
        self.assertEqual(
            got,
            [True, False, False, False, False, True, False, False, False, False],
        )

    def test_interval_one_is_every_tick(self):
        self.assertTrue(
            all(ttc.is_layer_a_attempt_tick(epoch, 1) for epoch in range(10))
        )

    def test_constant_default_is_five(self):
        self.assertEqual(ttc.DEFAULT_LAYER_A_POLL_INTERVAL_SECONDS, 5)


SAMPLE_STATS = "getproduct=12.5/postcheckout=3.0/getcart=0/postcart=8.25/emptycart=1/"
SAMPLE_THRESHOLDS = (
    "getproduct=10000.0/postcheckout=40.0/getcart=80.0/"
    "postcart=10000.0/emptycart=10000.0/"
)


class TestParseProxyStats(unittest.TestCase):
    def test_parses_name_value_slash_format(self):
        parsed = ttc.parse_proxy_stats(SAMPLE_STATS)
        self.assertEqual(parsed["getproduct"], 12.5)
        self.assertEqual(parsed["postcheckout"], 3.0)
        self.assertEqual(parsed["getcart"], 0.0)
        self.assertEqual(parsed["postcart"], 8.25)
        self.assertEqual(parsed["emptycart"], 1.0)

    def test_empty_body_returns_empty_dict(self):
        self.assertEqual(ttc.parse_proxy_stats(""), {})
        self.assertEqual(ttc.parse_proxy_stats("/"), {})

    def test_ignores_malformed_tokens(self):
        parsed = ttc.parse_proxy_stats("getproduct=12.5/broken/postcart=1/")
        self.assertEqual(parsed["getproduct"], 12.5)
        self.assertEqual(parsed["postcart"], 1.0)
        self.assertNotIn("broken", parsed)


class TestReadThresholds(unittest.TestCase):
    def test_reads_one_number_per_api_file(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "getproduct").write_text("40\n", encoding="utf-8")
            (d / "postcheckout").write_text("12.5\n", encoding="utf-8")
            got = ttc.read_thresholds(d, apis=["getproduct", "postcheckout", "getcart"])
            self.assertEqual(got["getproduct"], 40.0)
            self.assertEqual(got["postcheckout"], 12.5)
            self.assertEqual(got["getcart"], 0.0)

    def test_unreadable_file_is_zero_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            got = ttc.read_thresholds(Path(td), apis=["getproduct"])
            self.assertEqual(got["getproduct"], 0.0)


class TestProxyScrapeConfig(unittest.TestCase):
    def test_loopback_proxy_and_admin_urls_on_proxy_host(self):
        cfg = ttc.proxy_scrape_config("http://10.128.0.3:8090")
        self.assertEqual(cfg["proxy"], "http://127.0.0.1:8090")
        self.assertEqual(cfg["stats_url"], "http://10.128.0.3:8090/stats")
        self.assertEqual(cfg["thresholds_url"], "http://10.128.0.3:8090/thresholds")

    def test_keeps_nondefault_port(self):
        cfg = ttc.proxy_scrape_config("http://10.128.0.3:9090")
        self.assertEqual(cfg["proxy"], "http://127.0.0.1:9090")
        self.assertEqual(cfg["stats_url"], "http://10.128.0.3:9090/stats")
        self.assertEqual(cfg["thresholds_url"], "http://10.128.0.3:9090/thresholds")


class TestFetchUrlProxyChoice(unittest.TestCase):
    def test_admin_urls_use_goproxy_handler_cadvisor_uses_direct(self):
        handlers = []
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = b"ok"
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = mock.Mock(return_value=False)

        def fake_build_opener(*args):
            handlers.append(args)
            opener = mock.MagicMock()
            opener.open.return_value = fake_resp
            return opener

        with mock.patch.object(ttc, "build_opener", side_effect=fake_build_opener):
            ttc.default_fetch_url(
                "http://10.128.0.3:8090/stats",
                proxy="http://127.0.0.1:8090",
            )
            ttc.default_fetch_url(
                "http://10.0.0.9:8080/api/v2.0/summary/abc?type=docker",
            )

        self.assertEqual(len(handlers), 2)
        admin_handler = handlers[0][0]
        self.assertEqual(
            admin_handler.proxies,
            {"http": "http://127.0.0.1:8090", "https": "http://127.0.0.1:8090"},
        )
        direct_handler = handlers[1][0]
        self.assertEqual(direct_handler.proxies, {})


class TestReadLiveThresholds(unittest.TestCase):
    def test_http_wins_when_rate_config_files_are_empty(self):
        with tempfile.TemporaryDirectory() as td:
            fetched = []

            def fetch(url: str) -> str:
                fetched.append(url)
                return SAMPLE_THRESHOLDS

            got = ttc.read_live_thresholds(
                Path(td), fetch, "http://127.0.0.1:8090/thresholds"
            )
            self.assertEqual(fetched, ["http://127.0.0.1:8090/thresholds"])
            self.assertEqual(got["getproduct"], 10000.0)
            self.assertEqual(got["getcart"], 80.0)
            self.assertEqual(got["postcheckout"], 40.0)

    def test_http_overrides_stale_or_racing_files(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "getproduct").write_text("12\n", encoding="utf-8")

            def fetch(_url: str) -> str:
                return SAMPLE_THRESHOLDS

            got = ttc.read_live_thresholds(
                d, fetch, "http://127.0.0.1:8090/thresholds"
            )
            self.assertEqual(got["getproduct"], 10000.0)

    def test_returns_none_when_http_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "getproduct").write_text("40\n", encoding="utf-8")

            def fetch(_url: str) -> str:
                raise OSError("thresholds down")

            got = ttc.read_live_thresholds(
                d, fetch, "http://127.0.0.1:8090/thresholds"
            )
            self.assertIsNone(got)


class TestWriteThrottleCsv(unittest.TestCase):
    def test_writes_header_and_one_row_per_api(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(
                path,
                "2023-11-14T22:13:20Z",
                {"getproduct": 40.0, "postcheckout": 10.0},
                {"getproduct": 37.0},
                threshold_fresh={"getproduct": 1, "postcheckout": 1},
                admitted_fresh={"getproduct": 1},
            )
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(
                ttc.THROTTLE_CSV_COLUMNS,
                list(rows[0].keys()) if rows else ttc.THROTTLE_CSV_COLUMNS,
            )
            by_api = {r["api"]: r for r in rows}
            self.assertEqual(len(rows), len(ttc.LOCUST_APIS))
            self.assertEqual(by_api["getproduct"]["threshold"], "40.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "37.0")
            self.assertEqual(by_api["postcheckout"]["admitted_rps"], "0.0")
            self.assertEqual(by_api["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(by_api["getproduct"]["admitted_fresh"], "1")
            self.assertEqual(by_api["postcheckout"]["admitted_fresh"], "0")

    def test_appends_without_second_header(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(path, "2023-11-14T22:13:20Z", {}, {})
            ttc.write_throttle_csv(path, "2023-11-14T22:13:21Z", {}, {})
            text = path.read_text(encoding="utf-8")
            header = ",".join(ttc.THROTTLE_CSV_COLUMNS)
            self.assertEqual(text.count(header), 1)
            self.assertIn("threshold_fresh", header)
            self.assertIn("admitted_fresh", header)


SAMPLE_CADVISOR_SUMMARY = json.dumps(
    {
        "docker://abc": {
            "latest_usage": {"cpu": 910.0, "memory": 123},
        }
    }
)

SAMPLE_POD_LIST = {
    "items": [
        {
            "metadata": {"name": "checkoutservice-abc-123"},
            "status": {
                "containerStatuses": [
                    {
                        "name": "server",
                        "containerID": "docker://deadbeefcheckout",
                    },
                    {
                        "name": "istio-proxy",
                        "containerID": "docker://proxyid",
                    },
                ]
            },
        },
        {
            "metadata": {"name": "frontend-def-456"},
            "status": {
                "containerStatuses": [
                    {
                        "name": "server",
                        "containerID": "containerd://front123",
                    }
                ]
            },
        },
    ]
}


class TestDetectMetrics(unittest.TestCase):
    def test_quota_overrides_and_default(self):
        self.assertEqual(ttc.quota_for("productcatalogservice"), 500)
        self.assertEqual(ttc.quota_for("checkoutservice"), 1000)
        self.assertEqual(ttc.quota_for("paymentservice"), 1000)

    def test_alpha_special_cases(self):
        self.assertEqual(ttc.alpha_for("cartservice"), 0.95)
        self.assertEqual(ttc.alpha_for("productcatalogservice"), 0.95)
        self.assertEqual(ttc.alpha_for("checkoutservice"), 0.8)

    def test_overloaded_when_util_exceeds_alpha(self):
        row = ttc.detect_metrics("checkoutservice", 900.0)
        self.assertEqual(row["quota"], 1000)
        self.assertEqual(row["alpha"], 0.8)
        self.assertEqual(row["utilization"], 0.9)
        self.assertEqual(row["overloaded"], 1)

    def test_not_overloaded_at_boundary(self):
        # 800 / 1000 = 0.8, overloaded is strictly greater than alpha
        row = ttc.detect_metrics("checkoutservice", 800.0)
        self.assertEqual(row["overloaded"], 0)

    def test_cartservice_uses_0_95(self):
        row = ttc.detect_metrics("cartservice", 940.0)
        self.assertEqual(row["alpha"], 0.95)
        self.assertEqual(row["overloaded"], 0)
        row2 = ttc.detect_metrics("cartservice", 960.0)
        self.assertEqual(row2["overloaded"], 1)


class TestQuotaForEffectiveMap(unittest.TestCase):
    def test_override_wins(self):
        self.assertEqual(
            ttc.quota_for("checkoutservice", {"checkoutservice": 100}),
            100,
        )

    def test_paper_default_not_200(self):
        self.assertEqual(ttc.quota_for("paymentservice"), 1000)
        self.assertNotEqual(ttc.DEFAULT_QUOTA, 200)

    def test_overloaded_against_fraction_quota(self):
        row = ttc.detect_metrics(
            "checkoutservice", 90.0, quotas={"checkoutservice": 100}
        )
        self.assertEqual(row["quota"], 100)
        self.assertEqual(row["overloaded"], 1)


class TestParseCadvisorSummary(unittest.TestCase):
    def test_reads_latest_usage_cpu(self):
        self.assertEqual(ttc.parse_cadvisor_summary(SAMPLE_CADVISOR_SUMMARY), 910.0)

    def test_bad_json_returns_none(self):
        self.assertIsNone(ttc.parse_cadvisor_summary("not-json"))
        self.assertIsNone(ttc.parse_cadvisor_summary("{}"))


class TestContainerIdsFromPodList(unittest.TestCase):
    def test_skips_proxy_and_strips_runtime_prefix(self):
        ids = ttc.container_ids_from_pod_list(
            SAMPLE_POD_LIST, ["checkoutservice", "frontend", "adservice"]
        )
        self.assertEqual(ids["checkoutservice"], ["deadbeefcheckout"])
        self.assertEqual(ids["frontend"], ["front123"])
        self.assertEqual(ids["adservice"], [])


class TestAggregateCpu(unittest.TestCase):
    def test_skips_values_at_or_below_threshold_then_averages(self):
        self.assertEqual(ttc.aggregate_cpu([1.0, 2.0, 10.0, 20.0]), 15.0)

    def test_all_skipped_is_zero(self):
        self.assertEqual(ttc.aggregate_cpu([0.0, 1.5]), 0.0)
        self.assertEqual(ttc.aggregate_cpu([]), 0.0)


class TestWriteDetectCsv(unittest.TestCase):
    def test_one_row_per_service_in_DETECT_SERVICES(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_detect.csv"
            rows = {
                "checkoutservice": ttc.detect_metrics("checkoutservice", 900.0),
            }
            ttc.write_detect_csv(path, "2023-11-14T22:13:20Z", rows)
            with open(path, newline="", encoding="utf-8") as f:
                got = list(csv.DictReader(f))
            self.assertEqual(len(got), len(ttc.DETECT_SERVICES))
            by = {r["service"]: r for r in got}
            self.assertEqual(by["checkoutservice"]["overloaded"], "1")
            self.assertEqual(by["frontend"]["cadvisor_cpu"], "0.0")


class TestPollOnce(unittest.TestCase):
    def test_writes_both_csvs_with_shared_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            (proxy_dir / "getproduct").write_text("40\n", encoding="utf-8")

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "cadvisor" in joined and "podIP" in joined:
                    return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")
                if "get" in cmd and "po" in cmd or "pods" in joined:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(SAMPLE_POD_LIST),
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="no")

            def fetch_url(url: str) -> str:
                if url.endswith("/stats"):
                    return SAMPLE_STATS
                if "deadbeefcheckout" in url:
                    return SAMPLE_CADVISOR_SUMMARY
                raise OSError("no such container")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            self.assertTrue(
                all(r["timestamp"] == "2023-11-14T22:13:20Z" for r in throttle)
            )
            self.assertTrue(
                all(r["timestamp"] == "2023-11-14T22:13:20Z" for r in detect)
            )
            by_api = {r["api"]: r for r in throttle}
            self.assertEqual(by_api["getproduct"]["threshold"], "40.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(by_api["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(by_api["getproduct"]["admitted_fresh"], "1")
            by_svc = {r["service"]: r for r in detect}
            self.assertEqual(by_svc["checkoutservice"]["cadvisor_cpu"], "910.0")
            self.assertEqual(by_svc["checkoutservice"]["overloaded"], "1")

    def test_empty_rate_config_uses_thresholds_http_for_cap(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            fetched = []
            lock = threading.Lock()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(url: str) -> str:
                with lock:
                    fetched.append(url)
                if url.endswith("/thresholds"):
                    return SAMPLE_THRESHOLDS
                if url.endswith("/stats"):
                    return SAMPLE_STATS
                raise OSError("no such container")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
            )
            self.assertIn("http://10.128.0.3:8090/thresholds", fetched)
            self.assertIn("http://10.128.0.3:8090/stats", fetched)
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                by_api = {r["api"]: r for r in csv.DictReader(f)}
            self.assertEqual(by_api["getproduct"]["threshold"], "10000.0")
            self.assertEqual(by_api["getcart"]["threshold"], "80.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(by_api["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(by_api["getproduct"]["admitted_fresh"], "1")

    def test_stats_fetch_failure_still_writes_zero_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="fail")

            def fetch_url(_url: str) -> str:
                raise OSError("proxy down")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            self.assertEqual(len(throttle), len(ttc.LOCUST_APIS))
            self.assertTrue(all(r["admitted_rps"] == "0.0" for r in throttle))
            self.assertTrue(all(r["threshold"] == "0.0" for r in throttle))
            self.assertTrue(all(r["admitted_fresh"] == "0" for r in throttle))
            self.assertTrue(all(r["threshold_fresh"] == "0" for r in throttle))

    def test_does_not_raise_when_record_path_is_file_or_proxy_dir_is_file(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            record_file = base / "not_a_dir"
            record_file.write_text("block\n", encoding="utf-8")
            proxy_file = base / "also_not_a_dir"
            proxy_file.write_text("99\n", encoding="utf-8")

            def fetch_url(_url: str) -> str:
                return SAMPLE_STATS

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            ttc.poll_once(
                record_file,
                proxy_file,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )

    def test_runtime_error_from_injected_deps_does_not_propagate(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()

            def run_cmd(_cmd):
                raise RuntimeError("kubectl exploded")

            def fetch_url(_url: str) -> str:
                raise RuntimeError("stats endpoint exploded")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            self.assertEqual(len(throttle), len(ttc.LOCUST_APIS))
            self.assertTrue(all(r["admitted_rps"] == "0.0" for r in throttle))
            self.assertEqual(len(detect), len(ttc.DETECT_SERVICES))
            self.assertTrue(all(r["cadvisor_cpu"] == "0.0" for r in detect))
            self.assertTrue(all(r["overloaded"] == "0" for r in detect))


class TestParallelAdminFetch(unittest.TestCase):
    def test_stats_and_thresholds_fetched_in_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            barrier = threading.Barrier(2, timeout=2.0)
            fetched = []
            lock = threading.Lock()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(url: str) -> str:
                with lock:
                    fetched.append(url)
                if url.endswith("/thresholds") or url.endswith("/stats"):
                    barrier.wait()
                    if url.endswith("/thresholds"):
                        return SAMPLE_THRESHOLDS
                    return SAMPLE_STATS
                raise OSError("no cadvisor")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
            )
            self.assertIn("http://10.128.0.3:8090/thresholds", fetched)
            self.assertIn("http://10.128.0.3:8090/stats", fetched)
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                by_api = {r["api"]: r for r in csv.DictReader(f)}
            self.assertEqual(by_api["getproduct"]["threshold"], "10000.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")


class TestLastGoodThrottle(unittest.TestCase):
    def test_timeout_carries_last_good_with_fresh_flags(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            last_good = ttc.LastGoodThrottle()
            phase = {"fail_admin": False}

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(url: str) -> str:
                if url.endswith("/thresholds") or url.endswith("/stats"):
                    if phase["fail_admin"]:
                        raise OSError("timed out")
                    if url.endswith("/thresholds"):
                        return SAMPLE_THRESHOLDS
                    return SAMPLE_STATS
                raise OSError("no cadvisor")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
            )
            phase["fail_admin"] = True
            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:21Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
            )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                rows = list(csv.DictReader(f))
            tick1 = {
                r["api"]: r for r in rows if r["timestamp"] == "2023-11-14T22:13:20Z"
            }
            tick2 = {
                r["api"]: r for r in rows if r["timestamp"] == "2023-11-14T22:13:21Z"
            }
            self.assertEqual(tick1["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick1["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick1["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(tick1["getproduct"]["admitted_fresh"], "1")
            self.assertEqual(tick2["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick2["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick2["getproduct"]["threshold_fresh"], "0")
            self.assertEqual(tick2["getproduct"]["admitted_fresh"], "0")
            self.assertEqual(tick2["getcart"]["threshold"], "80.0")
            self.assertTrue((record_path / "topfull_detect.csv").exists())

    def test_empty_rate_config_on_http_fail_is_not_measured(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            last_good = ttc.LastGoodThrottle()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(_url: str) -> str:
                raise OSError("timed out")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                last_good=last_good,
            )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            self.assertTrue(all(r["threshold"] == "0.0" for r in throttle))
            self.assertTrue(all(r["admitted_rps"] == "0.0" for r in throttle))
            self.assertTrue(all(r["threshold_fresh"] == "0" for r in throttle))
            self.assertTrue(all(r["admitted_fresh"] == "0" for r in throttle))


class TestLayerBNotBlocked(unittest.TestCase):
    def test_cadvisor_runs_while_admin_waits(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            # Admin pair waits on this barrier; Layer B must start without joining it.
            admin_release = threading.Event()
            cadvisor_started = threading.Event()

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "cadvisor" in joined and "podIP" in joined:
                    cadvisor_started.set()
                    return SimpleNamespace(
                        returncode=0, stdout="10.0.0.9\n", stderr=""
                    )
                if "get" in cmd and ("po" in cmd or "pods" in joined):
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(SAMPLE_POD_LIST),
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="no")

            def fetch_url(url: str) -> str:
                if url.endswith("/thresholds") or url.endswith("/stats"):
                    # Block until Layer B has proven it started (or timeout).
                    if not cadvisor_started.wait(timeout=2.0):
                        raise AssertionError(
                            "Layer B did not start while admin waited"
                        )
                    admin_release.set()
                    if url.endswith("/thresholds"):
                        return SAMPLE_THRESHOLDS
                    return SAMPLE_STATS
                if "deadbeefcheckout" in url:
                    return SAMPLE_CADVISOR_SUMMARY
                raise OSError("no such container")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
            )
            self.assertTrue(cadvisor_started.is_set())
            self.assertTrue(admin_release.is_set())
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                by_svc = {r["service"]: r for r in csv.DictReader(f)}
            self.assertEqual(by_svc["checkoutservice"]["cadvisor_cpu"], "910.0")


class TestRunCollector(unittest.TestCase):
    def test_max_polls_writes_and_exits(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(_url: str) -> str:
                return SAMPLE_STATS if _url.endswith("/stats") else "{}"

            ttc.run_collector(
                {"poll_interval_seconds": 1},
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                max_polls=1,
            )
            self.assertTrue((record_path / "topfull_throttle.csv").exists())
            self.assertTrue((record_path / "topfull_detect.csv").exists())


SPLIT_EPOCHS = [int(EPOCH) + i for i in range(10)]


def _split_run_cmd(cmd):
    joined = " ".join(cmd)
    if "cadvisor" in joined and "podIP" in joined:
        return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")
    if "get" in cmd and ("po" in cmd or "pods" in joined):
        return SimpleNamespace(
            returncode=0, stdout=json.dumps(SAMPLE_POD_LIST), stderr=""
        )
    return SimpleNamespace(returncode=1, stdout="", stderr="no")


def _split_fetch_factory(fetched):
    lock = threading.Lock()

    def fetch_url(url: str) -> str:
        with lock:
            fetched.append(url)
        if url.endswith("/thresholds"):
            return SAMPLE_THRESHOLDS
        if url.endswith("/stats"):
            return SAMPLE_STATS
        if "deadbeefcheckout" in url:
            return SAMPLE_CADVISOR_SUMMARY
        raise OSError("no such container")

    return fetch_url


class TestPollOnceLayerASkip(unittest.TestCase):
    def _drive_ten_ticks(self, fetched, last_good=None):
        store = last_good if last_good is not None else ttc.LastGoodThrottle()
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            fetch_url = _split_fetch_factory(fetched)
            for epoch in SPLIT_EPOCHS:
                ts = ttc.tick_timestamp(1, now=float(epoch))
                ttc.poll_once(
                    record_path,
                    proxy_dir,
                    "http://10.128.0.3:8090/stats",
                    timestamp=ts,
                    run_cmd=_split_run_cmd,
                    fetch_url=fetch_url,
                    thresholds_url="http://10.128.0.3:8090/thresholds",
                    last_good=store,
                    attempt_layer_a=ttc.is_layer_a_attempt_tick(epoch, 5),
                )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            return throttle, detect

    def test_admin_fetch_twice_over_ten_ticks_csv_still_ten_rows(self):
        # Spec §5: /thresholds+/stats invoked on ticks 0 and 5 only;
        # topfull_throttle.csv still has 10 rows per API; skipped ticks *_fresh=0.
        fetched = []
        throttle, detect = self._drive_ten_ticks(fetched)
        stats_calls = sum(1 for url in fetched if url.endswith("/stats"))
        thresh_calls = sum(1 for url in fetched if url.endswith("/thresholds"))
        self.assertEqual(stats_calls, 2)
        self.assertEqual(thresh_calls, 2)
        by_ts = {}
        for row in throttle:
            by_ts.setdefault(row["timestamp"], []).append(row)
        self.assertEqual(len(by_ts), 10)
        for rows in by_ts.values():
            self.assertEqual(len(rows), len(ttc.LOCUST_APIS))
        attempt_ts = {
            ttc.tick_timestamp(1, now=float(SPLIT_EPOCHS[0])),
            ttc.tick_timestamp(1, now=float(SPLIT_EPOCHS[5])),
        }
        for ts, rows in by_ts.items():
            if ts in attempt_ts:
                self.assertTrue(all(r["threshold_fresh"] == "1" for r in rows))
                self.assertTrue(all(r["admitted_fresh"] == "1" for r in rows))
            else:
                self.assertTrue(all(r["threshold_fresh"] == "0" for r in rows))
                self.assertTrue(all(r["admitted_fresh"] == "0" for r in rows))
            by_api = {r["api"]: r for r in rows}
            self.assertEqual(by_api["getproduct"]["threshold"], "10000.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(by_api["getcart"]["threshold"], "80.0")

    def test_layer_b_unaffected_ten_detect_ticks(self):
        # Spec §5: topfull_detect.csv is 10 × DETECT_SERVICES; scrape_cadvisor_cpu
        # (and its cAdvisor fetch_url calls) happen every tick. SAMPLE_POD_LIST
        # has two app containers, so fetch_url cAdvisor hits are >10; count the
        # scrape function itself.
        fetched = []
        scrape_calls = {"n": 0}
        orig_scrape = ttc.scrape_cadvisor_cpu

        def counting_scrape(*args, **kwargs):
            scrape_calls["n"] += 1
            return orig_scrape(*args, **kwargs)

        with mock.patch.object(
            ttc, "scrape_cadvisor_cpu", side_effect=counting_scrape
        ):
            _throttle, detect = self._drive_ten_ticks(fetched)
        self.assertEqual(len(detect), 10 * len(ttc.DETECT_SERVICES))
        self.assertEqual(scrape_calls["n"], 10)
        cadvisor_urls = [
            url for url in fetched if "/api/v2.0/summary/" in url
        ]
        self.assertTrue(cadvisor_urls)
        by_ts = {r["timestamp"] for r in detect}
        self.assertEqual(len(by_ts), 10)
        checkout = [
            r for r in detect if r["service"] == "checkoutservice"
        ]
        self.assertEqual(len(checkout), 10)
        self.assertTrue(all(r["cadvisor_cpu"] == "910.0" for r in checkout))


class TestFreshnessSkippedByDesign(unittest.TestCase):
    def test_skipped_tick_carries_last_good_even_if_fetch_would_succeed(self):
        # Spec §5: admin fetch *would* succeed, but non-attempt tick still
        # writes *_fresh=0 and carries the previous attempt's values.
        fetched = []
        last_good = ttc.LastGoodThrottle()
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            fetch_url = _split_fetch_factory(fetched)
            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=_split_run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
                attempt_layer_a=True,
            )
            fetched_after_attempt = list(fetched)
            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://10.128.0.3:8090/stats",
                timestamp="2023-11-14T22:13:21Z",
                run_cmd=_split_run_cmd,
                fetch_url=fetch_url,
                thresholds_url="http://10.128.0.3:8090/thresholds",
                last_good=last_good,
                attempt_layer_a=False,
            )
            admin_after_skip = [
                url
                for url in fetched[len(fetched_after_attempt) :]
                if url.endswith("/thresholds") or url.endswith("/stats")
            ]
            self.assertEqual(admin_after_skip, [])
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                rows = list(csv.DictReader(f))
            tick1 = {
                r["api"]: r
                for r in rows
                if r["timestamp"] == "2023-11-14T22:13:20Z"
            }
            tick2 = {
                r["api"]: r
                for r in rows
                if r["timestamp"] == "2023-11-14T22:13:21Z"
            }
            self.assertEqual(tick1["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick1["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick1["getproduct"]["threshold_fresh"], "1")
            self.assertEqual(tick1["getproduct"]["admitted_fresh"], "1")
            self.assertEqual(tick2["getproduct"]["threshold"], "10000.0")
            self.assertEqual(tick2["getproduct"]["admitted_rps"], "12.5")
            self.assertEqual(tick2["getproduct"]["threshold_fresh"], "0")
            self.assertEqual(tick2["getproduct"]["admitted_fresh"], "0")
            self.assertEqual(tick2["getcart"]["threshold"], "80.0")
            self.assertNotIn("2", {r["threshold_fresh"] for r in rows})
            self.assertNotIn("2", {r["admitted_fresh"] for r in rows})


class TestRunCollectorLayerAInterval(unittest.TestCase):
    def _run_with_clock(self, params, fetched):
        times = iter(float(EPOCH) + i for i in range(20))
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            with mock.patch.object(ttc.time, "time", side_effect=lambda: next(times)):
                ttc.run_collector(
                    params,
                    record_path,
                    proxy_dir,
                    "http://10.128.0.3:8090/stats",
                    run_cmd=_split_run_cmd,
                    fetch_url=_split_fetch_factory(fetched),
                    thresholds_url="http://10.128.0.3:8090/thresholds",
                    max_polls=10,
                )
            with (record_path / "topfull_throttle.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                throttle = list(csv.DictReader(f))
            with (record_path / "topfull_detect.csv").open(
                newline="", encoding="utf-8"
            ) as f:
                detect = list(csv.DictReader(f))
            return throttle, detect

    def test_absent_key_defaults_to_five(self):
        # Spec §5: params has only poll_interval_seconds; implicit default 5
        # → admin fetch exactly 2 times over 10 polls.
        fetched = []
        throttle, detect = self._run_with_clock(
            {"poll_interval_seconds": 1}, fetched
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/stats")), 2
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/thresholds")), 2
        )
        self.assertEqual(
            len({r["timestamp"] for r in throttle}), 10
        )
        self.assertEqual(len(detect), 10 * len(ttc.DETECT_SERVICES))

    def test_explicit_one_reproduces_every_tick(self):
        # Spec §5: layer_a_poll_interval_seconds=1 → admin fetch on all 10 polls.
        fetched = []
        throttle, _detect = self._run_with_clock(
            {
                "poll_interval_seconds": 1,
                "layer_a_poll_interval_seconds": 1,
            },
            fetched,
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/stats")), 10
        )
        self.assertEqual(
            sum(1 for url in fetched if url.endswith("/thresholds")), 10
        )
        self.assertEqual(len({r["timestamp"] for r in throttle}), 10)

    def test_start_log_mentions_layer_a_interval(self):
        fetched = []
        with self.assertLogs(ttc.log, level="INFO") as cm:
            self._run_with_clock({"poll_interval_seconds": 1}, fetched)
        start_lines = [line for line in cm.output if "START" in line]
        self.assertTrue(start_lines)
        self.assertIn("layer_a_poll_interval=5s", start_lines[0])
        self.assertIn("poll_interval=1s", start_lines[0])


if __name__ == "__main__":
    unittest.main()
