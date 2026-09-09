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


SAMPLE_STATS = "getproduct=12.5/postcheckout=3.0/getcart=0/postcart=8.25/emptycart=1/"


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


class TestWriteThrottleCsv(unittest.TestCase):
    def test_writes_header_and_one_row_per_api(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(
                path,
                "2023-11-14T22:13:20Z",
                {"getproduct": 40.0, "postcheckout": 10.0},
                {"getproduct": 37.0},
            )
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(ttc.THROTTLE_CSV_COLUMNS, list(rows[0].keys()) if rows else ttc.THROTTLE_CSV_COLUMNS)
            by_api = {r["api"]: r for r in rows}
            self.assertEqual(len(rows), len(ttc.LOCUST_APIS))
            self.assertEqual(by_api["getproduct"]["threshold"], "40.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "37.0")
            self.assertEqual(by_api["postcheckout"]["admitted_rps"], "0.0")

    def test_appends_without_second_header(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(path, "2023-11-14T22:13:20Z", {}, {})
            ttc.write_throttle_csv(path, "2023-11-14T22:13:21Z", {}, {})
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("timestamp,api,threshold,admitted_rps"), 1)


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
        self.assertEqual(ttc.quota_for("paymentservice"), 200)

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


if __name__ == "__main__":
    unittest.main()
