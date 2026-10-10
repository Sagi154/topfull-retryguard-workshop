"""Unit tests for experiments/analysis_score.py."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score as score


def _write(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class TestEdgeRpr(unittest.TestCase):
    def test_streak_is_seconds_and_skips_a_tick_with_no_first_attempts(self):
        rows = [
            {"timestamp": "2026-10-08T00:00:00Z", "caller": "frontend", "target": "checkoutservice", "total": 0, "retry": 0},
            {"timestamp": "2026-10-08T00:00:10Z", "caller": "frontend", "target": "checkoutservice", "total": 30, "retry": 20},
            # first attempts 0: delta total 10, delta retry 10. Skipped, streak holds.
            {"timestamp": "2026-10-08T00:00:20Z", "caller": "frontend", "target": "checkoutservice", "total": 40, "retry": 30},
            {"timestamp": "2026-10-08T00:00:30Z", "caller": "frontend", "target": "checkoutservice", "total": 80, "retry": 50},
            # cool tick, rpr 0. Breaks.
            {"timestamp": "2026-10-08T00:00:40Z", "caller": "frontend", "target": "checkoutservice", "total": 90, "retry": 50},
            {"timestamp": "2026-10-08T00:00:50Z", "caller": "frontend", "target": "checkoutservice", "total": 100, "retry": 58},
        ]
        ticks = score.edge_ticks(rows)[("frontend", "checkoutservice")]
        # 00:00:10 rpr = 20/10 = 2
        # 00:00:30 rpr = 20/20 = 1, 20 s after the first high tick
        # 00:00:40 rpr = 0
        # 00:00:50 rpr = 8/2 = 4, a one-tick streak of 0 s
        self.assertEqual(len(ticks), 4)
        streak_s, high = score.file_streak(ticks, 0.5)
        self.assertEqual(streak_s, 20)
        self.assertEqual(high, 3)
        mean, maximum, volume = score.rpr_summary(ticks)
        self.assertAlmostEqual(maximum, 4)
        self.assertAlmostEqual(volume, (20 + 20 + 0 + 8) / (10 + 20 + 10 + 2))
        self.assertAlmostEqual(mean, (2 + 1 + 0 + 4) / 4)

    def test_one_high_tick_is_zero_seconds(self):
        ticks = [{"timestamp": "2026-10-08T00:00:00Z", "rpr": 1.0, "delta_retry": 1, "first": 1}]
        streak_s, high = score.file_streak(ticks, 0.5)
        self.assertEqual(streak_s, 0)
        self.assertEqual(high, 1)


class TestLog(unittest.TestCase):
    def test_climb_and_transitions_including_attempt_steps(self):
        text = "\n".join([
            "2026-10-08T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.50 rejection_threshold=0.20 reenable_rejection=0.10 attempts_on=3",
            "2026-10-08T00:00:01Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=1 high=0  attempts=1  state=ON  metric=rpr",
            "2026-10-08T00:00:02Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=2 high=0  attempts=1  state=ON  metric=rpr",
            "2026-10-08T00:00:03Z  OBSERVE  frontend->checkoutservice  rpr=0.90  low=0 high=1  attempts=1  state=ON  metric=rpr",
            "2026-10-08T00:00:04Z  OBSERVE  frontend->checkoutservice  rpr=0.20  low=1 high=0  attempts=2  state=ON  metric=rpr",
            "2026-10-08T00:01:00Z  frontend->checkoutservice  ON→OFF   rpr=1.77  consecutive_high=30  attempts=0  from_attempts=3  metric=rpr  elapsed_s=30",
            "2026-10-08T00:01:30Z  checkoutservice  OFF→ON   rejection=0.00  consecutive_low=30  attempts=1  from_attempts=0  metric=rejection  elapsed_s=30",
            "2026-10-08T00:02:00Z  frontend->checkoutservice  1→2   rpr=0.00  consecutive_low=16  attempts=2  from_attempts=1  metric=rpr  elapsed_s=15",
            "2026-10-08T00:02:15Z  frontend->checkoutservice  2→3   rpr=0.00  consecutive_low=16  attempts=3  from_attempts=2  metric=rpr  elapsed_s=15",
        ])
        parsed = score.parse_log(text)
        self.assertEqual(parsed["params"]["rpr_threshold"], 0.5)
        samples = parsed["observes"]["frontend->checkoutservice"]
        self.assertEqual(score.controller_high(samples), 1)
        self.assertEqual(score.climb_streak(samples, 1, 0.17), 2)
        self.assertEqual(score.climb_streak(samples, 2, 0.33), 1)
        steps = [event["step"] for event in parsed["transitions"]]
        self.assertEqual(steps, ["ON→OFF", "OFF→ON", "1→2", "2→3"])
        self.assertIsNone(parsed["params"]["climb_rpr_1_to_2"])
        self.assertIsNone(parsed["params"]["climb_rpr_2_to_3"])

    def test_score_uses_start_climb_bars_and_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom = root / "custom"
            custom.mkdir()
            (custom / "retryguard.log").write_text(
                "2026-10-08T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.50 "
                "attempts_on=3 climb_rpr_1_to_2=0.10 climb_rpr_2_to_3=0.25\n",
                encoding="utf-8",
            )
            old = root / "old"
            old.mkdir()
            (old / "retryguard.log").write_text(
                "2026-10-08T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.50 attempts_on=3\n",
                encoding="utf-8",
            )
            self.assertEqual(score.score_run(custom)["climb_limits"], (0.10, 0.25))
            self.assertEqual(score.score_run(old)["climb_limits"], (0.17, 0.33))

    def test_climb_is_absent_when_the_edge_never_leaves_three(self):
        samples = [{"attempts": 3, "rpr": 0.0, "high": 4}]
        self.assertIsNone(score.climb_streak(samples, 1, 0.17))
        self.assertIsNone(score.climb_streak(samples, 2, 0.33))
        self.assertEqual(score.controller_high(samples), 4)


class TestRejectionAndInbound(unittest.TestCase):
    def test_non_positive_total_breaks_both_streaks(self):
        rows = [
            {"timestamp": "2026-10-08T00:00:00Z", "total": 0, "5xx": 0, "resets": 0},
            {"timestamp": "2026-10-08T00:00:01Z", "total": 10, "5xx": 0, "resets": 3},  # 0.30 high
            {"timestamp": "2026-10-08T00:00:02Z", "total": 10, "5xx": 0, "resets": 3},  # no arrivals
            {"timestamp": "2026-10-08T00:00:03Z", "total": 20, "5xx": 0, "resets": 3},  # 0.00 under 0.10
        ]
        stats = score.rejection_streaks(rows, 0.20, 0.10)
        self.assertEqual(stats["high_streak"], 1)
        self.assertEqual(stats["high_count"], 1)
        self.assertEqual(stats["low_streak"], 1)
        self.assertEqual(stats["low_count"], 1)

    def test_sojourn_and_share_above_500(self):
        buckets_a = json.dumps({"500": 80, "+Inf": 100})
        buckets_b = json.dumps({"500": 170, "+Inf": 200})
        rows = [
            {"timestamp": "2026-10-08T00:00:00Z", "total": 0, "rq_time_sum_ms": 0, "rq_time_count": 0, "rq_time_buckets": buckets_a},
            {"timestamp": "2026-10-08T00:00:10Z", "total": 100, "rq_time_sum_ms": 5000, "rq_time_count": 100, "rq_time_buckets": buckets_b},
        ]
        # The first row's buckets are the baseline; the delta le=500 is 90 of 100 completions.
        hold = score.inbound_hold(rows)
        self.assertAlmostEqual(hold["arrival"], 10.0)
        self.assertAlmostEqual(hold["sojourn_ms"], 50.0)
        self.assertAlmostEqual(hold["over500"], 0.10)


class TestScoreAndRender(unittest.TestCase):
    def test_folder_and_group_bar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "run1"
            second = root / "run2"
            for folder, rpr_retry in ((first, 8), (second, 0)):
                _write(
                    folder / "service_edges.csv",
                    ["timestamp", "caller", "target", "total", "retry"],
                    [
                        ["2026-10-08T00:00:00Z", "frontend", "checkoutservice", 0, 0],
                        ["2026-10-08T00:00:30Z", "frontend", "checkoutservice", 10, rpr_retry],
                    ],
                )
                _write(
                    folder / "service_inbound.csv",
                    ["timestamp", "service", "total", "5xx", "resets", "rq_time_sum_ms", "rq_time_count", "rq_time_buckets", "grpc_4", "grpc_14"],
                    [[
                        "2026-10-08T00:00:00Z", "checkoutservice", 0, 0, 0, 0, 0,
                        json.dumps({"500": 0}), 0, 0,
                    ], [
                        "2026-10-08T00:00:10Z", "checkoutservice", 10, 0, 4, 1000, 10,
                        json.dumps({"500": 8}), 3, 0,
                    ]],
                )
                _write(
                    folder / "topfull_detect.csv",
                    ["timestamp", "service", "quota", "alpha", "utilization", "overloaded"],
                    [
                        ["2026-10-08T00:00:00Z", "checkoutservice", 800, 0.8, 0.9, 1],
                        ["2026-10-08T00:00:01Z", "checkoutservice", 800, 0.8, 0.1, 0],
                    ],
                )
                _write(
                    folder / "resource_usage.csv",
                    ["timestamp", "service", "cpu_millicores", "replica_count"],
                    [["2026-10-08T00:00:00Z", "checkoutservice", 400, 1]],
                )
                _write(
                    folder / "topfull_throttle.csv",
                    ["timestamp", "api", "threshold", "threshold_fresh"],
                    [
                        ["2026-10-08T00:00:00Z", "postcheckout", 10000, 1],
                        ["2026-10-08T00:00:05Z", "postcheckout", 33, 1],
                        ["2026-10-08T00:00:10Z", "postcheckout", 0, 1],
                    ],
                )
                _write(
                    folder / "postcheckout.csv",
                    ["RPS", "Fail", "Goodput", "Latency95"],
                    [["0", "0", "0", "0"], ["10", "2", "8", "400"]],
                )
                (folder / "retryguard.log").write_text(
                    "2026-10-08T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.50 attempts_on=3 "
                    "rejection_threshold=0.20 reenable_rejection=0.10\n"
                    "2026-10-08T00:00:31Z  OBSERVE  frontend->checkoutservice  rpr=4.0000  low=0 high=5  attempts=3  state=ON  metric=rpr\n",
                    encoding="utf-8",
                )
            scored = [score.score_run(first), score.score_run(second)]
            edge = scored[0]["edges"]["frontend->checkoutservice"]
            # delta retry 8, first attempts 2, rpr 4, one tick so streak 0 s
            self.assertEqual(edge["high_ticks"], 1)
            self.assertEqual(edge["streak_s"], 0)
            self.assertEqual(edge["controller_high"], 5)
            self.assertAlmostEqual(edge["volume_rpr"], 4)
            self.assertEqual(scored[0]["rejection"]["checkoutservice"]["high_streak"], 1)
            self.assertEqual(scored[0]["grpc"]["checkoutservice"]["grpc_4"], 3)
            self.assertEqual(scored[0]["resets"]["checkoutservice"], 4)
            self.assertAlmostEqual(scored[0]["cpu"]["checkoutservice"]["fraction_mean"], 0.5)
            self.assertEqual(scored[0]["locust"]["postcheckout"]["goodput"], 8)
            self.assertAlmostEqual(scored[0]["locust"]["postcheckout"]["fail"], 0.2)
            caps = scored[0]["caps"]["postcheckout"]
            self.assertEqual([span["value"] for span in caps], [None, 33.0])
            text = score.render(scored, ["1", "2"], sep=1)
            self.assertIn("**┃**", text)
            self.assertIn("frontend → checkoutservice", text)
            self.assertIn("no cap", text)


if __name__ == "__main__":
    unittest.main()
