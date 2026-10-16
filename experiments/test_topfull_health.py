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


def fd_csv(path: Path, rows: list[tuple[str, int, int]]) -> None:
    lines = ["timestamp,pid,open_fds,soft_limit"]
    lines += [f"2026-10-14T{hms}Z,4242,{fds},{soft}" for hms, fds, soft in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAssess(unittest.TestCase):
    def _base(self, tmp: Path, end="12:00:20"):
        write(tmp / "topfull_throttle_collector.log", [
            ("12:00:00", "START  poll_interval=1s"),
            (end, "SHUTDOWN  signal=15"),
        ])

    def _healthy_rl(self, tmp: Path):
        rows = [(f"12:00:{s:02d}", f"RL_LOOP_START iter={s // 2}") for s in range(0, 21, 2)]
        rows.append(("12:00:03", "RL_RPS_START caller=agent"))
        rows.append(("12:00:03", "RL_RPS_END caller=agent elapsed_s=0.01 ok=1"))
        write(tmp / "topfull_rl.log", rows)

    def test_a_healthy_patched_hold_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            self._healthy_rl(tmp)
            write(tmp / "topfull_proxy.log", [("12:00:01", TICK)])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 40, 1048576), ("12:00:02", 90, 1048576)])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.assessable)
        self.assertEqual(h.status, "ok")
        self.assertEqual(h.reasons, ())

    def test_rl_silence_flags_even_when_the_throttle_log_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:01:20")  # throttle collector alive to the end
            write(tmp / "topfull_rl.log", [("12:00:00", "RL_LOOP_START iter=1"),
                                           ("12:00:02", "RL_LOOP_START iter=2")])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.rl_stall)
        self.assertFalse(h.proxy_fd)
        self.assertEqual(h.status, "RL STALL")
        self.assertIn("silent 78 s", h.reasons[0])

    def test_a_timeout_line_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_rl.log", [
                ("12:00:01", "RL_LOOP_START iter=1"),
                ("12:00:03", "RL_RPS_TIMEOUT caller=clustering elapsed_s=2.01 timeout_s=2.0 error=ReadTimeout"),
                ("12:00:05", "RL_LOOP_START iter=2"),
            ] + [(f"12:00:{s:02d}", "RL_LOOP_START iter=9") for s in range(7, 21, 2)])
            h = topfull_health.assess(tmp)
        self.assertTrue(h.rl_stall)
        self.assertIn("RL_RPS_TIMEOUT", " ".join(h.reasons))

    def test_a_slow_call_flags_and_a_fast_one_does_not(self):
        for elapsed, expected in (("4.20", True), ("0.01", False)):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self._base(tmp)
                rows = [(f"12:00:{s:02d}", "RL_LOOP_START iter=1") for s in range(0, 21, 2)]
                rows.append(("12:00:05", f"RL_RPS_END caller=agent elapsed_s={elapsed} ok=1"))
                write(tmp / "topfull_rl.log", rows)
                self.assertEqual(topfull_health.assess(tmp).rl_stall, expected, elapsed)

    def test_accept_error_in_the_proxy_log_flags_a_topfull_off_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_proxy.log", [
                ("12:00:01", TICK),
                ("12:00:09", "http: Accept error: accept tcp [::]:8090: accept4: too many open files; retrying in 5ms"),
            ])
            h = topfull_health.assess(tmp, topfull_on=False)
        self.assertTrue(h.proxy_fd)
        self.assertFalse(h.rl_stall)
        self.assertEqual(h.status, "PROXY FD")
        self.assertIn("first 12:00:09Z", h.reasons[0])

    def test_a_topfull_off_hold_is_never_rl_stall(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:05:00")
            write(tmp / "topfull_rl.log", [("12:00:00", "x")])  # would be silent for 300 s
            write(tmp / "topfull_proxy.log", [("12:00:01", TICK)])
            h = topfull_health.assess(tmp, topfull_on=False)
        self.assertFalse(h.rl_stall)

    def test_descriptor_csv_at_the_limit_flags_and_below_it_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 600, 1024), ("12:00:02", 1024, 1024)])
            h = topfull_health.assess(tmp, topfull_on=False)
            self.assertTrue(h.proxy_fd)
            self.assertIn("reached the soft limit 1024", h.reasons[0])
            self.assertIn("peak 1024", h.reasons[0])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 600, 1024), ("12:00:02", 1023, 1024)])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).proxy_fd)

    def test_unlimited_soft_limit_never_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 900000, -1)])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).proxy_fd)

    def test_both_flags_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp, end="12:02:00")
            write(tmp / "topfull_rl.log", [("12:00:00", "RL_LOOP_START iter=1")])
            fd_csv(tmp / "proxy_fds.csv", [("12:00:01", 1024, 1024)])
            self.assertEqual(topfull_health.assess(tmp).status, "RL STALL + PROXY FD")

    def test_an_old_hold_is_not_assessable_and_not_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)  # only the throttle collector log, like every pre-2026-10-15 hold
            h = topfull_health.assess(tmp)
        self.assertFalse(h.assessable)
        self.assertFalse(h.rl_stall or h.proxy_fd)
        self.assertEqual(h.status, topfull_health.NOT_ASSESSABLE)
        self.assertNotEqual(h.status, "ok")

    def test_a_topfull_off_hold_without_proxy_logs_is_not_assessable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            write(tmp / "topfull_rl.log", [("12:00:00", "x")])
            self.assertFalse(topfull_health.assess(tmp, topfull_on=False).assessable)

    def test_report_has_a_health_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._base(tmp)
            self._healthy_rl(tmp)
            self.assertIn("health: ok", topfull_health.report(tmp))


if __name__ == "__main__":
    unittest.main()
