"""
test_mentor_charts_data.py — Unit tests for mentor_charts_data.py (pure
data loading/aggregation, no plotting, no network access).

Run:
    python experiments/test_mentor_charts_data.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mentor_charts_data as mcd


class TestFindRunDirs(unittest.TestCase):
    def test_finds_and_sorts_matching_run_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenario_dir = Path(tmp)
            (scenario_dir / "baseline_foo_run5").mkdir()
            (scenario_dir / "baseline_foo_run4").mkdir()
            (scenario_dir / "baseline_foo_run6").mkdir()
            (scenario_dir / "run_topfull_retryguard_foo_run4").mkdir()
            (scenario_dir / "not_a_match").mkdir()

            result = mcd.find_run_dirs(scenario_dir, "baseline_foo")

            self.assertEqual(
                [p.name for p in result],
                ["baseline_foo_run4", "baseline_foo_run5", "baseline_foo_run6"],
            )

    def test_returns_empty_list_when_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mcd.find_run_dirs(Path(tmp), "baseline_foo")
            self.assertEqual(result, [])


class TestLoadMetricColumn(unittest.TestCase):
    def test_reads_column_from_each_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_a = Path(tmp) / "run_a"
            run_b = Path(tmp) / "run_b"
            run_a.mkdir()
            run_b.mkdir()
            pd.DataFrame({"RPS": [1.0, 2.0], "Goodput": [1.0, 2.0]}).to_csv(
                run_a / "total.csv", index=False
            )
            pd.DataFrame({"RPS": [3.0, 4.0, 5.0], "Goodput": [3.0, 4.0, 5.0]}).to_csv(
                run_b / "total.csv", index=False
            )

            result = mcd.load_metric_column([run_a, run_b], "total.csv", "Goodput")

            self.assertEqual(len(result), 2)
            self.assertEqual(list(result[0]), [1.0, 2.0])
            self.assertEqual(list(result[1]), [3.0, 4.0, 5.0])


class TestAverageSeries(unittest.TestCase):
    def test_truncates_to_shortest_and_averages_pointwise(self):
        series_list = [
            pd.Series([10.0, 20.0, 30.0]),
            pd.Series([0.0, 10.0]),
        ]

        result = mcd.average_series(series_list)

        self.assertEqual(list(result.index), [0, 1])
        self.assertEqual(list(result["mean"]), [5.0, 15.0])
        self.assertEqual(list(result["min"]), [0.0, 10.0])
        self.assertEqual(list(result["max"]), [10.0, 20.0])

    def test_empty_input_returns_empty_dataframe(self):
        result = mcd.average_series([])
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ["mean", "min", "max"])


class TestRejectionRateSeries(unittest.TestCase):
    def test_computes_fail_over_rps_with_zero_rps_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_a"
            run_dir.mkdir()
            pd.DataFrame(
                {"RPS": [0.0, 50.0, 20.0], "Fail": [0.0, 0.0, 19.6]}
            ).to_csv(run_dir / "total.csv", index=False)

            result = mcd.rejection_rate_series([run_dir], "total.csv")

            self.assertEqual(len(result), 1)
            values = list(result[0])
            self.assertAlmostEqual(values[0], 0.0)
            self.assertAlmostEqual(values[1], 0.0)
            self.assertAlmostEqual(values[2], 0.98)


class TestEnvoyRetriesPerRequest(unittest.TestCase):
    def test_diffs_cumulative_counters_per_target_and_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_a"
            run_dir.mkdir()
            rows = [
                # t=0: baseline poll, diffs are 0 (first row per target)
                ("2026-09-05T16:51:25Z", "cartservice", 1000, 0),
                ("2026-09-05T16:51:25Z", "checkoutservice", 2000, 10),
                # t=5: cartservice gets 100 new requests, 5 retries;
                #      checkoutservice gets 100 new requests, 0 new retries
                ("2026-09-05T16:51:30Z", "cartservice", 1100, 5),
                ("2026-09-05T16:51:30Z", "checkoutservice", 2100, 10),
            ]
            pd.DataFrame(
                rows,
                columns=["timestamp", "target_service", "upstream_rq_total", "upstream_rq_retry"],
            ).assign(upstream_rq_retry_success=0, upstream_rq_retry_limit_exceeded=0).to_csv(
                run_dir / "envoy_retries_frontend.csv", index=False
            )

            result = mcd.envoy_retries_per_request(run_dir, "envoy_retries_frontend.csv")

            self.assertEqual(list(result.index), [0.0, 5.0])
            self.assertAlmostEqual(result.loc[0.0, "cartservice"], 0.0)
            self.assertAlmostEqual(result.loc[5.0, "cartservice"], 0.05)
            self.assertAlmostEqual(result.loc[5.0, "checkoutservice"], 0.0)
            # total: (5 + 0) retries over (100 + 100) requests = 0.025
            self.assertAlmostEqual(result.loc[5.0, "total"], 0.025)


class TestResourceUsageSeries(unittest.TestCase):
    def test_pivots_by_service_indexed_by_elapsed_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_a"
            run_dir.mkdir()
            rows = [
                ("2026-09-05T16:51:52Z", "frontend", 10, 1000),
                ("2026-09-05T16:51:52Z", "cartservice", 5, 2000),
                ("2026-09-05T16:51:57Z", "frontend", 12, 1100),
                ("2026-09-05T16:51:57Z", "cartservice", 6, 2100),
            ]
            pd.DataFrame(
                rows,
                columns=["timestamp", "service", "cpu_millicores", "memory_working_set_bytes"],
            ).assign(replica_count=1).to_csv(run_dir / "resource_usage.csv", index=False)

            result = mcd.resource_usage_series(run_dir, "cpu_millicores")

            self.assertEqual(list(result.index), [0.0, 5.0])
            self.assertEqual(list(result["frontend"]), [10, 12])
            self.assertEqual(list(result["cartservice"]), [5, 6])


class TestAverageDataFrames(unittest.TestCase):
    def test_averages_common_columns_positionally(self):
        df_a = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, 20.0, 30.0]})
        df_b = pd.DataFrame({"x": [3.0, 4.0], "z": [100.0, 200.0]})

        result = mcd.average_dataframes([df_a, df_b])

        # only 'x' is common to both; shortest length is 2
        self.assertEqual(list(result.columns), ["x"])
        self.assertEqual(list(result["x"]), [2.0, 3.0])

    def test_empty_list_returns_empty_dataframe(self):
        result = mcd.average_dataframes([])
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
