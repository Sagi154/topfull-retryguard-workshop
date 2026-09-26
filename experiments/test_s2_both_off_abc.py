import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_both_off_abc as abc


class TestRejectionStreak(unittest.TestCase):
    def test_streak_breaks_on_a_cool_sample(self):
        # cumulative counters. Two high samples, one cool, one high.
        rows = [
            {"total": 0, "5xx": 0, "resets": 0},
            {"total": 10, "5xx": 0, "resets": 4},   # 0.40 high
            {"total": 20, "5xx": 0, "resets": 8},   # 0.40 high
            {"total": 30, "5xx": 0, "resets": 8},   # 0.00 cool, breaks
            {"total": 40, "5xx": 0, "resets": 12},  # 0.40 high
        ]
        streak, high, samples, frac = abc.rejection_streak(rows)
        self.assertEqual(streak, 2)
        self.assertEqual(high, 3)
        self.assertEqual(samples, 4)
        self.assertAlmostEqual(frac, 12 / 40)

    def test_negative_delta_breaks_and_is_not_counted(self):
        rows = [
            {"total": 100, "5xx": 0, "resets": 50},
            {"total": 10, "5xx": 0, "resets": 4},  # counter restart
            {"total": 20, "5xx": 0, "resets": 8},  # 0.40
        ]
        streak, high, samples, frac = abc.rejection_streak(rows)
        self.assertEqual(streak, 1)
        self.assertEqual(high, 1)
        self.assertAlmostEqual(frac, 4 / 10)


class TestRetryAndDetect(unittest.TestCase):
    def test_positive_retry_deltas_group_by_target(self):
        edges = [
            {"caller": "frontend", "target": "checkoutservice", "retry": 0},
            {"caller": "frontend", "target": "checkoutservice", "retry": 10},
            {"caller": "frontend", "target": "checkoutservice", "retry": 10},
            {"caller": "frontend", "target": "recommendationservice", "retry": 0},
            {"caller": "frontend", "target": "recommendationservice", "retry": 5},
        ]
        by_edge, by_target = abc.retry_deltas(edges)
        self.assertEqual(by_edge["frontend->checkoutservice"], 10)
        self.assertEqual(by_target["recommendationservice"], 5)

    def test_overloaded_share(self):
        ticks, hot, share = abc.overloaded_fraction([0, 1, 1, 0])
        self.assertEqual((ticks, hot), (4, 2))
        self.assertAlmostEqual(share, 0.5)


class TestScoreRun(unittest.TestCase):
    def test_reads_the_five_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "service_inbound.csv",
                   ["timestamp", "service", "total", "2xx", "4xx", "5xx", "resets"],
                   [
                       ["t0", "checkoutservice", "0", "0", "0", "0", "0"],
                       ["t1", "checkoutservice", "10", "6", "0", "0", "4"],
                   ])
            _write(root / "topfull_detect.csv",
                   ["timestamp", "service", "cadvisor_cpu", "quota", "alpha", "utilization", "overloaded"],
                   [
                       ["t0", "checkoutservice", "1", "1500", "0.8", "0.9", "1"],
                       ["t1", "checkoutservice", "1", "1500", "0.8", "0.1", "0"],
                   ])
            _write(root / "service_edges.csv",
                   ["timestamp", "caller", "target", "total", "2xx", "4xx", "5xx", "retry"],
                   [["t0", "frontend", "checkoutservice", "0", "0", "0", "0", "0"],
                    ["t1", "frontend", "checkoutservice", "10", "6", "0", "0", "3"]])
            _write(root / "topfull_throttle.csv",
                   ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
                   [["t0", "postcheckout", "0", "0", "0", "0"],
                    ["t1", "postcheckout", "10000", "1", "1", "1"],
                    ["t2", "postcheckout", "40", "1", "1", "1"]])
            _write(root / "resource_usage.csv",
                   ["timestamp", "service", "cpu_millicores", "memory_working_set_bytes", "replica_count"],
                   [["t0", "checkoutservice", "100", "1", "1"],
                    ["t1", "checkoutservice", "300", "1", "1"]])
            got = abc.score_run(root)
        self.assertEqual(got["inbound"]["checkoutservice"]["streak"], 1)
        self.assertEqual(got["overloaded"]["checkoutservice"]["overloaded_ticks"], 1)
        self.assertEqual(got["retry_by_target"]["checkoutservice"], 3)
        self.assertEqual(got["layer_a_admitting_rows"], 1)
        self.assertEqual(got["cpu_mean_max"]["checkoutservice"], (200.0, 300.0))


def _write(path: Path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
