"""Unit tests for steal_stat. No network, no result folders."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import steal_stat as s

A = "cpu  1000 0 500 8000 100 0 50 100 0 0"
B = "cpu  1400 0 700 8600 100 0 50 250 0 0"


class TestParse(unittest.TestCase):
    def test_parse_with_leading_epoch(self):
        d = s.parse_cpu_line("1759570000 " + A)
        self.assertEqual(d["epoch"], 1759570000.0)
        self.assertEqual((d["user"], d["idle"], d["steal"]), (1000, 8000, 100))

    def test_parse_without_epoch(self):
        self.assertIsNone(s.parse_cpu_line(A)["epoch"])

    def test_short_line_defaults_missing_fields_to_zero(self):
        d = s.parse_cpu_line("cpu  10 0 5 80 1 0 0")  # 7 fields: pre-2.6.11 kernels have no steal
        self.assertEqual(d["steal"], 0)

    def test_not_a_cpu_line_raises(self):
        with self.assertRaises(ValueError):
            s.parse_cpu_line("cpu0 1 2 3")
        with self.assertRaises(ValueError):
            s.parse_cpu_line("intr 12345")


class TestStealPct(unittest.TestCase):
    def test_known_value(self):
        # total went 9750 -> 11100 (+1350); steal went 100 -> 250 (+150): 11.111%
        self.assertAlmostEqual(s.steal_pct(s.parse_cpu_line(A), s.parse_cpu_line(B)), 11.1111, places=3)

    def test_zero_steal(self):
        a = s.parse_cpu_line("cpu  10 0 10 100 0 0 0 7")
        b = s.parse_cpu_line("cpu  20 0 20 200 0 0 0 7")
        self.assertEqual(s.steal_pct(a, b), 0.0)

    def test_guest_is_not_double_counted(self):
        a = s.parse_cpu_line("cpu  100 0 0 100 0 0 0 0 50 0")
        b = s.parse_cpu_line("cpu  200 0 0 200 0 0 0 10 100 0")
        # total delta = 100 + 100 + 10 = 210 (guest ignored); steal delta 10
        self.assertAlmostEqual(s.steal_pct(a, b), 100 * 10 / 210, places=4)

    def test_counter_reset_raises(self):
        with self.assertRaises(ValueError):
            s.steal_pct(s.parse_cpu_line(B), s.parse_cpu_line(A))


class TestSnapshot(unittest.TestCase):
    TEXT = ("### proc_stat_a\n1759570000 " + A + "\n### vmstat_10s\nprocs ---memory---\n"
            " 1  0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n### mpstat\nmpstat unavailable\n"
            "### proc_stat_b\n1759570010 " + B + "\n")

    def test_parse_snapshot_returns_a_then_b(self):
        a, b = s.parse_snapshot(self.TEXT)
        self.assertEqual((a["epoch"], b["epoch"]), (1759570000.0, 1759570010.0))
        self.assertAlmostEqual(s.steal_pct(a, b), 11.1111, places=3)

    def test_missing_section_raises(self):
        with self.assertRaises(ValueError):
            s.parse_snapshot("### proc_stat_a\n1759570000 " + A + "\n")


def _series_lines(start_epoch, n, step, steal_per_step, busy_per_step):
    lines, user, steal, idle = [], 0, 0, 0
    for i in range(n):
        lines.append(f"{start_epoch + i * step} cpu  {user} 0 0 {idle} 0 0 0 {steal} 0 0")
        user += busy_per_step
        steal += steal_per_step
        idle += 100 - busy_per_step - steal_per_step
    return lines


class TestWindowAndScore(unittest.TestCase):
    def test_window_stats_uses_only_samples_inside_window(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "series.txt"
            # 11 samples, 5 s apart, 5% steal each step (100 jiffies per step)
            p.write_text("\n".join(_series_lines(1000, 11, 5, 5, 45)) + "\ngarbage line\n")
            ser = s.read_series(p)
            self.assertEqual(len(ser), 11)
            w = s.window_stats(ser, 1010, 1040)
            self.assertEqual(w["samples"], 7)
            self.assertAlmostEqual(w["pct"], 5.0, places=6)
            self.assertAlmostEqual(w["max_interval_pct"], 5.0, places=6)
            self.assertIsNone(s.window_stats(ser, 5000, 6000))

    def test_score_run_reads_all_three_nodes(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            lo = s._utc("2026-10-04T10:00:00Z")
            (run / "service_inbound.csv").write_text(
                "timestamp,service,total\n2026-10-04T10:00:00Z,frontend,1\n"
                "2026-10-04T10:01:00Z,frontend,2\n", encoding="utf-8")
            st = run / "state"
            st.mkdir()
            for node, steal_step in (("master", 0), ("worker", 10), ("load", 1)):
                (st / f"steal_series_{node}.txt").write_text(
                    "\n".join(_series_lines(int(lo) - 20, 15, 5, steal_step, 50 - steal_step)),
                    encoding="utf-8")
                (st / f"steal_t0_{node}.txt").write_text(
                    "### proc_stat_a\n1759570000 " + A + "\n### proc_stat_b\n1759570010 " + B + "\n",
                    encoding="utf-8-sig")
            r = s.score_run(run)
            self.assertAlmostEqual(r["master"]["hold_pct"], 0.0)
            self.assertAlmostEqual(r["worker"]["hold_pct"], 10.0, places=6)
            self.assertAlmostEqual(r["load"]["hold_pct"], 1.0, places=6)
            self.assertAlmostEqual(r["worker"]["t0_pct"], 11.1111, places=3)
            self.assertIsNone(r["worker"]["end_pct"])
            self.assertIn("worker 10.00%", s.format_line("run128", r))
            self.assertTrue(s.md_row("run128", r).startswith("| run128 |"))


class TestNodeStealScript(unittest.TestCase):
    def test_script_has_no_carriage_returns(self):
        # A CR in a script piped to "ssh bash -s" breaks it (see Global Constraints).
        data = (Path(__file__).resolve().parent / "node_steal.sh").read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertIn(b"### proc_stat_a", data)
        self.assertIn(b"### proc_stat_b", data)


if __name__ == "__main__":
    unittest.main()
