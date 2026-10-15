"""Tests for topfull_health.py. Run: python experiments/test_topfull_health.py"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_health

TICK = "-------------------------"


def ts(hms: str) -> datetime:
    return datetime.strptime(f"2026-10-14T{hms}Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def write(path: Path, rows: list[tuple[str, str]]) -> None:
    path.write_text("".join(f"2026-10-14T{hms}Z  {text}\n" for hms, text in rows), encoding="utf-8")


class TestParsing(unittest.TestCase):
    def test_read_stamped_skips_unstamped_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.log"
            p.write_text("garbage\n2026-10-14T12:00:01Z  hello world\n", encoding="utf-8")
            self.assertEqual(topfull_health.read_stamped(p), [(ts("12:00:01"), "hello world")])

    def test_longest_gap_counts_trailing_gap_to_end(self):
        gap = topfull_health.longest_gap([ts("12:00:00"), ts("12:00:01")], ts("12:00:31"))
        self.assertEqual(gap.seconds, 30)
        self.assertEqual(gap.start, ts("12:00:01"))

    def test_longest_gap_empty(self):
        self.assertEqual(topfull_health.longest_gap([], None).seconds, 0)


class TestReport(unittest.TestCase):
    def _hold(self, tmp: Path, *, proxy=True, rl=True):
        write(tmp / "topfull_throttle_collector.log", [
            ("12:00:00", "START  poll_interval=1s"),
            ("12:00:05", "WARNING  thresholds fetch failed: timed out"),
            ("12:00:20", "SHUTDOWN  signal=15"),
        ])
        if proxy:
            write(tmp / "topfull_proxy.log", [
                ("12:00:00", "Start"),
                ("12:00:01", TICK),
                ("12:00:02", TICK),
                ("12:00:03", "Apply threshold to  postcheckout  :  +7.000000e+001"),
                ("12:00:03", TICK),
                ("12:00:12", TICK),
            ])
        if rl:
            write(tmp / "topfull_rl.log", [
                ("12:00:01", "No overloaded services"),
                ("12:00:03", "['postcheckout'] running"),
            ])

    def test_report_on_a_new_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._hold(tmp)
            text = topfull_health.report(tmp)
        self.assertIn("throttle: first_fetch_failure=12:00:05Z end=12:00:20Z", text)
        self.assertIn("proxy: lines=6 ticks=4 longest_tick_gap_s=9 from 12:00:03Z tick_gap_over_5s=yes", text)
        self.assertIn("applies=1 last_apply=12:00:03Z", text)
        self.assertIn("rl: lines=2 longest_silence_s=17 from 12:00:03Z rl_silent_over_30s=no", text)

    def test_report_on_an_old_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._hold(tmp, proxy=False, rl=False)
            text = topfull_health.report(tmp)
        self.assertIn("proxy: topfull_proxy.log missing", text)
        self.assertIn("rl: topfull_rl.log missing", text)

    def test_cli_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._hold(Path(tmp))
            self.assertEqual(topfull_health.main([tmp]), 0)


if __name__ == "__main__":
    unittest.main()
