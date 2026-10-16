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
        mean, median, maximum, volume = score.rpr_summary(ticks)
        self.assertAlmostEqual(maximum, 4)
        self.assertAlmostEqual(volume, (20 + 20 + 0 + 8) / (10 + 20 + 10 + 2))
        self.assertAlmostEqual(mean, (2 + 1 + 0 + 4) / 4)
        self.assertAlmostEqual(median, 1.5)

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

    def test_burst_shed_is_flagged(self):
        text = "\n".join([
            "2026-10-11T16:00:05Z  frontend->checkoutservice  ON→OFF   rpr=1.62  consecutive_high=3  attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4",
            "2026-10-11T16:01:00Z  frontend->checkoutservice  ON→OFF   rpr=1.77  consecutive_high=30  attempts=0  from_attempts=3  metric=rpr  elapsed_s=30",
        ])
        events = score.parse_log(text)["transitions"]
        self.assertEqual([e["burst"] for e in events], [True, False])
        self.assertEqual(events[0]["metric"], "rpr")

    def test_burst_summary_uses_bar_in_force_and_counts_sheds(self):
        text = "\n".join([
            "2026-10-11T16:00:00Z  START  metric=edge_rpr rpr_threshold=0.40 attempts_on=3 burst_rpr=1.50 burst_window_seconds=5 burst_min_first_attempts=20",
            "2026-10-11T16:00:01Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=1 high=0  elapsed_s=0  attempts=3  state=ON  metric=rpr  burst_rpr5=0.2000",
            "2026-10-11T16:00:02Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=2 high=0  elapsed_s=0  attempts=3  state=ON  metric=rpr  burst_rpr5=1.6000",
            "2026-10-11T16:00:03Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=3 high=0  elapsed_s=0  attempts=2  state=ON  metric=rpr  burst_rpr5=1.0000",
            "2026-10-11T16:00:04Z  OBSERVE  frontend->checkoutservice  rpr=0.10  low=4 high=0  elapsed_s=0  attempts=3  state=ON  metric=rpr",
            "2026-10-11T16:00:05Z  frontend->checkoutservice  ON→OFF   rpr=1.60  consecutive_high=0  attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4",
        ])
        parsed = score.parse_log(text)
        self.assertEqual(parsed["params"]["burst_rpr"], 1.5)
        name = "frontend->checkoutservice"
        summary = score.burst_summary(
            parsed["observes"][name], parsed["transitions"], name, 1.5, 3,
        )
        self.assertEqual(summary["samples"], 3)
        self.assertAlmostEqual(summary["peak"], 1.6)
        self.assertAlmostEqual(summary["median"], 1.0)
        # 1.6 >= 1.5 at 3 attempts, 1.0 >= 1.0 at 2 attempts, 0.2 < 1.5
        self.assertEqual(summary["at_bar"], 2)
        self.assertEqual(summary["sheds"], 1)
        self.assertIsNone(score.burst_summary([], [], name, 1.5, 3))


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

    def test_count_grpc_adds_grpc_failures(self):
        rows = [
            {"timestamp": "2026-10-13T00:00:00Z", "total": 0, "5xx": 0, "resets": 0, "grpc_4": 0, "grpc_14": 0},
            {"timestamp": "2026-10-13T00:00:01Z", "total": 100, "5xx": 0, "resets": 0, "grpc_4": 30, "grpc_14": 10},  # 0.40 with grpc
        ]
        http = score.rejection_streaks(rows, 0.20, 0.10)
        matched = score.rejection_streaks(rows, 0.20, 0.10, count_grpc=True)
        self.assertEqual(http["high_count"], 0)
        self.assertEqual(http["low_count"], 1)
        self.assertEqual(matched["high_count"], 1)
        self.assertEqual(matched["high_streak"], 1)
        self.assertEqual(matched["low_count"], 0)

    def test_count_grpc_without_grpc_columns_equals_http(self):
        rows = [
            {"timestamp": "2026-10-13T00:00:00Z", "total": 0, "5xx": 0, "resets": 0},
            {"timestamp": "2026-10-13T00:00:01Z", "total": 10, "5xx": 0, "resets": 3},
        ]
        self.assertEqual(
            score.rejection_streaks(rows, 0.20, 0.10, count_grpc=True),
            score.rejection_streaks(rows, 0.20, 0.10),
        )

    def test_score_run_matches_only_on_read_callees(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "run1"
            fields = ["timestamp", "service", "total", "5xx", "resets", "grpc_4", "grpc_14"]
            rows = []
            for service in ("productcatalogservice", "checkoutservice"):
                rows.append(["2026-10-13T00:00:00Z", service, 0, 0, 0, 0, 0])
                rows.append(["2026-10-13T00:00:01Z", service, 100, 0, 0, 30, 10])
            _write(folder / "service_inbound.csv", fields, rows)
            result = score.score_run(folder)
            self.assertEqual(result["rejection"]["productcatalogservice"]["high_count"], 1)
            self.assertEqual(result["rejection_http"]["productcatalogservice"]["high_count"], 0)
            self.assertEqual(result["rejection"]["checkoutservice"]["high_count"], 0)
            self.assertNotIn("checkoutservice", result["rejection_http"])

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

    def test_live_caps_treat_9900_and_above_as_no_cap(self):
        rows = [
            {"timestamp": "2026-10-16T00:00:00Z", "api": "getproduct", "threshold": "175", "threshold_fresh": "1"},
            {"timestamp": "2026-10-16T00:00:05Z", "api": "getproduct", "threshold": "9999.9", "threshold_fresh": "1"},
            {"timestamp": "2026-10-16T00:00:10Z", "api": "getproduct", "threshold": "9997.53", "threshold_fresh": "1"},
            {"timestamp": "2026-10-16T00:00:15Z", "api": "getproduct", "threshold": "9900", "threshold_fresh": "1"},
            {"timestamp": "2026-10-16T00:00:20Z", "api": "getproduct", "threshold": "9899.9", "threshold_fresh": "1"},
        ]
        spans = score.live_caps(rows)["getproduct"]
        self.assertEqual([span["value"] for span in spans], [175.0, None, 9899.9])

    def test_http_only_table_lists_only_read_callees(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "run1"
            fields = ["timestamp", "service", "total", "5xx", "resets", "grpc_4", "grpc_14"]
            rows = []
            for service in ("productcatalogservice", "checkoutservice"):
                rows.append(["2026-10-13T00:00:00Z", service, 0, 0, 0, 0, 0])
                rows.append(["2026-10-13T00:00:01Z", service, 100, 0, 0, 30, 10])
            _write(folder / "service_inbound.csv", fields, rows)
            text = score.render([score.score_run(folder)], ["1"])
        marker = "HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees"
        self.assertIn(marker, text)
        section = text.split(marker, 1)[1].split("\n\n", 2)[1]
        self.assertIn("productcatalogservice", section)
        self.assertNotIn("checkoutservice", section)


if __name__ == "__main__":
    unittest.main()


class TestThrottleQuality(unittest.TestCase):
    def _rows(self, fresh_until: int, total: int = 120):
        rows = []
        for sec in range(total):
            ok = int(sec % 5 == 0 and sec <= fresh_until)
            rows.append({
                "timestamp": f"2026-10-13T00:{sec // 60:02d}:{sec % 60:02d}Z",
                "api": "getproduct", "threshold_fresh": ok, "admitted_fresh": ok,
            })
        return rows

    def test_healthy_hold_is_not_flagged(self):
        q = score.throttle_quality(self._rows(fresh_until=119), Path("missing.log"))
        self.assertFalse(q["flagged"])
        self.assertLessEqual(q["threshold_gap_s"], 5)

    def test_reads_that_stop_flag_the_hold(self):
        q = score.throttle_quality(self._rows(fresh_until=20), Path("missing.log"))
        self.assertTrue(q["flagged"])
        self.assertGreater(q["threshold_gap_s"], score.THROTTLE_STALE_S)

    def test_fetch_warning_in_log_flags_the_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "topfull_throttle_collector.log"
            log.write_text(
                "2026-10-13T00:00:00Z  START  x\n"
                "2026-10-13T00:00:05Z  WARNING  stats fetch failed: timed out\n",
                encoding="utf-8",
            )
            q = score.throttle_quality(self._rows(fresh_until=119), log)
        self.assertTrue(q["flagged"])
        self.assertEqual(q["warnings"], 1)
        self.assertEqual(q["first_warning"], "2026-10-13T00:00:05Z")

    def test_topfull_off_hold_is_not_flagged_but_still_reports_the_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "topfull_throttle_collector.log"
            log.write_text(
                "2026-10-13T00:00:05Z  WARNING  stats fetch failed: timed out\n",
                encoding="utf-8",
            )
            q = score.throttle_quality(self._rows(fresh_until=20), log, topfull_on=False)
        self.assertFalse(q["flagged"])
        self.assertFalse(q["topfull_on"])
        self.assertEqual(q["warnings"], 1)
        self.assertGreater(q["threshold_gap_s"], score.THROTTLE_STALE_S)

    def test_topfull_on_is_the_default(self):
        q = score.throttle_quality(self._rows(fresh_until=20), Path("missing.log"))
        self.assertTrue(q["topfull_on"])

    def test_topfull_enabled_reads_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertTrue(score.topfull_enabled(folder))  # no manifest
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": false}}', encoding="utf-8")
            self.assertFalse(score.topfull_enabled(folder))
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": true}}', encoding="utf-8")
            self.assertTrue(score.topfull_enabled(folder))
            (folder / "run_manifest.json").write_text("not json", encoding="utf-8")
            self.assertTrue(score.topfull_enabled(folder))

    def test_ten_seconds_is_not_a_flag_and_eleven_is(self):
        def rows(gap):
            return [
                {"timestamp": "2026-10-13T00:00:00Z", "api": "getproduct",
                 "threshold_fresh": 1, "admitted_fresh": 1},
                {"timestamp": f"2026-10-13T00:00:{gap:02d}Z", "api": "getproduct",
                 "threshold_fresh": 1, "admitted_fresh": 1},
            ]
        ten = score.throttle_quality(rows(10), Path("missing.log"))
        self.assertFalse(ten["flagged"])
        self.assertEqual(ten["threshold_gap_s"], 10)
        eleven = score.throttle_quality(rows(11), Path("missing.log"))
        self.assertTrue(eleven["flagged"])
        self.assertEqual(eleven["threshold_gap_s"], 11)

    def test_stale_gap_matches_the_marker(self):
        import throttle_stale
        self.assertEqual(score.THROTTLE_STALE_S, 10)
        self.assertEqual(throttle_stale.STALE_GAP_S, float(score.THROTTLE_STALE_S))

    def test_rendered_table_says_na_for_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "final_s2_rg_only_burst_run9"
            folder.mkdir()
            (folder / "run_manifest.json").write_text(
                '{"topfull_rl": {"enabled": false}}', encoding="utf-8")
            (folder / "topfull_throttle_collector.log").write_text(
                "2026-10-13T00:00:05Z  WARNING  stats fetch failed: timed out\n",
                encoding="utf-8")
            _write(
                folder / "topfull_throttle.csv",
                ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
                [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
                 ["2026-10-13T00:01:00Z", "getproduct", 10000, 0, 0, 0]],
            )
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | N/A: TopFull off |", text)
        self.assertNotIn("| 9 | **FLAGGED** |", text)


class TestProxyRlHealth(unittest.TestCase):
    def _hold(self, tmp: str, *, topfull_on: bool, proxy_lines: list[str]):
        folder = Path(tmp) / "final_s2_rg_only_normal_run9"
        folder.mkdir()
        (folder / "run_manifest.json").write_text(
            '{"topfull_rl": {"enabled": %s}}' % ("true" if topfull_on else "false"), encoding="utf-8")
        _write(
            folder / "topfull_throttle.csv",
            ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
            [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
             ["2026-10-13T00:00:05Z", "getproduct", 10000, 0, 1, 1]],
        )
        if proxy_lines:
            (folder / "topfull_proxy.log").write_text("\n".join(proxy_lines) + "\n", encoding="utf-8")
        return folder

    def test_proxy_fd_is_a_separate_table_and_flags_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, proxy_lines=[
                "2026-10-13T00:00:02Z  http: Accept error: accept tcp [::]:8090: accept4: too many open files",
            ])
            item = score.score_run(folder)
            text = score.render([item], ["9"])
        self.assertEqual(item["proxy_rl_health"].status, "PROXY FD")
        self.assertIn("## Proxy and RL health", text)
        self.assertIn("| 9 | **PROXY FD** |", text)
        self.assertIn("| 9 | N/A: TopFull off |", text)  # the throttle table is unchanged

    def test_old_hold_reads_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=True, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | not assessable |", text)
        self.assertNotIn("| 9 | ok |", text.split("## Proxy and RL health")[1].split("##")[0])


class TestProxyStallSuspected(unittest.TestCase):
    def _hold(self, tmp: str, *, topfull_on: bool, warnings: int, proxy_lines: list[str]):
        folder = Path(tmp) / "final_s2_rg_only_normal_run9"
        folder.mkdir()
        (folder / "run_manifest.json").write_text(
            '{"topfull_rl": {"enabled": %s}}' % ("true" if topfull_on else "false"), encoding="utf-8")
        _write(
            folder / "topfull_throttle.csv",
            ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"],
            [["2026-10-13T00:00:00Z", "getproduct", 10000, 0, 1, 1],
             ["2026-10-13T00:00:05Z", "getproduct", 10000, 0, 1, 1]],
        )
        lines = ["2026-10-13T00:00:00Z  START  x"]
        lines += [f"2026-10-13T00:00:0{i % 10}Z  WARNING  stats fetch failed: timed out"
                  for i in range(warnings)]
        (folder / "topfull_throttle_collector.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if proxy_lines:
            (folder / "topfull_proxy.log").write_text("\n".join(proxy_lines) + "\n", encoding="utf-8")
        return folder

    def test_throttle_quality_reports_would_flag_for_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[])
            q = score.score_run(folder)["throttle_quality"]
        self.assertFalse(q["flagged"])        # the throttle flag is unchanged: TopFull off
        self.assertTrue(q["would_flag"])      # the collector evidence is still there

    def test_topfull_off_hold_with_collector_warnings_is_suspected_not_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        self.assertIn("| 9 | N/A: TopFull off |", text)             # throttle table unchanged
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | **PROXY STALL SUSPECTED** |", health)
        self.assertIn("3 fetch warning", health)
        self.assertIn("no proxy or descriptor log", health)

    def test_clean_old_hold_stays_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=0, proxy_lines=[])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | not assessable |", health)
        row = next(line for line in health.splitlines() if line.startswith("| 9 |"))
        self.assertNotIn("SUSPECTED", row)

    def test_logged_hold_with_timeouts_but_no_fd_cause_is_named_not_suspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[
                "2026-10-13T00:00:01Z  monitor tick"])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | admin timeouts, no fd cause |", health)
        row = next(line for line in health.splitlines() if line.startswith("| 9 |"))
        self.assertNotIn("SUSPECTED", row)

    def test_proxy_fd_still_wins_over_suspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._hold(tmp, topfull_on=False, warnings=3, proxy_lines=[
                "2026-10-13T00:00:02Z  http: Accept error: accept tcp [::]:8090: accept4: too many open files"])
            text = score.render([score.score_run(folder)], ["9"])
        health = text.split("## Proxy and RL health")[1]
        self.assertIn("| 9 | **PROXY FD** |", health)
        row = next(line for line in health.splitlines() if line.startswith("| 9 |"))
        self.assertNotIn("SUSPECTED", row)
