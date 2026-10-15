"""Unit tests for experiments/throttle_flags.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import throttle_flags  # noqa: E402
from test_hold_clock import E, iso, write_csv  # noqa: E402

HEADER = ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"]


def make_hold(root, scenario_dir, variant, name, fresh_until=99, warnings=0,
              total=100, csv=True):
    run = Path(root) / scenario_dir / variant / name
    run.mkdir(parents=True)
    if csv:
        rows = []
        for s in range(total):
            ok = int(s % 5 == 0 and s <= fresh_until)
            rows.append([iso(E + s), "getproduct", 150.0, 10.0, ok, ok])
        write_csv(run / "topfull_throttle.csv", HEADER, rows)
    lines = ["2026-10-13T00:00:00Z  START  x"]
    lines += [f"2026-10-13T00:00:{i % 60:02d}Z  WARNING  thresholds fetch failed: timed out"
              for i in range(warnings)]
    (run / "topfull_throttle_collector.log").write_text("\n".join(lines), encoding="utf-8")
    return run


def hold(name, on=True, flagged=True, warnings=5, tgap=60.0, agap=60.0, tpct=50.0, apct=50.0,
         scenario="S2", mode="burst", variant=None):
    variant = variant or ("both" if on else "rg_only")
    return throttle_flags.HoldFlag(
        path=f"S2_sustained_overload_{mode}/{variant}/{name}", scenario=scenario, mode=mode,
        variant=variant, name=name, topfull_on=on, flagged=flagged, warnings=warnings,
        first_warning="2026-10-13T00:00:00Z" if warnings else None,
        threshold_gap_s=tgap, admitted_gap_s=agap,
        threshold_stale_pct=tpct, admitted_stale_pct=apct,
    )


class TestScan(unittest.TestCase):
    def scan(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp))
            return throttle_flags.scan(Path(tmp))

    def test_clean_hold_is_not_flagged(self):
        flags = self.scan(lambda r: make_hold(r, "S2_sustained_overload_burst", "both", "run_a"))
        self.assertEqual(len(flags), 1)
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertTrue(h.topfull_on)
        self.assertEqual((h.scenario, h.mode, h.variant, h.name),
                         ("S2", "burst", "both", "run_a"))

    def test_tail_stale_hold_reports_gap_and_percent_of_span(self):
        flags = self.scan(lambda r: make_hold(
            r, "S4A_topology_position_normal", "tf_only", "run_b", fresh_until=20))
        h = flags[0]
        self.assertTrue(h.flagged)
        self.assertEqual(h.scenario, "S4A")
        self.assertEqual(h.mode, "normal")
        self.assertEqual(h.threshold_gap_s, 79.0)
        self.assertAlmostEqual(h.threshold_stale_pct, 79 / 99 * 100, places=1)
        self.assertAlmostEqual(h.admitted_stale_pct, 79 / 99 * 100, places=1)
        self.assertEqual(h.warnings, 0)

    def test_fetch_warnings_on_a_topfull_off_hold_do_not_flag_it(self):
        flags = self.scan(lambda r: make_hold(
            r, "S2_sustained_overload_burst", "rg_only", "run_c", warnings=3))
        h = flags[0]
        self.assertFalse(h.flagged)
        self.assertFalse(h.topfull_on)
        self.assertEqual(h.warnings, 3)
        self.assertEqual(h.threshold_stale_pct, 0.0)
        self.assertEqual(h.first_warning, "2026-10-13T00:00:00Z")

    def test_missing_csv_is_not_a_flag_even_with_log_warnings(self):
        flags = self.scan(lambda r: make_hold(
            r, "S1_normal_operation_normal", "tf_only", "run_d", csv=False, warnings=2))
        self.assertFalse(flags[0].flagged)

    def test_scan_is_sorted_and_uses_forward_slashes(self):
        def build(root):
            make_hold(root, "S2_sustained_overload_burst", "both", "b")
            make_hold(root, "S1_normal_operation_normal", "both", "a")
        flags = self.scan(build)
        self.assertEqual([h.path for h in flags], [
            "S1_normal_operation_normal/both/a", "S2_sustained_overload_burst/both/b"])


class TestLabels(unittest.TestCase):
    def test_label_separates_topfull_on_and_off(self):
        self.assertEqual(throttle_flags.label(hold("a", on=True)), throttle_flags.TF_ON_LABEL)
        self.assertEqual(throttle_flags.label(hold("a", on=False)), throttle_flags.TF_OFF_LABEL)

    def test_name_pattern_does_not_match_a_longer_name(self):
        pattern = throttle_flags.name_pattern("final_4a_x_run1")
        self.assertTrue(pattern.search("folders `final_4a_x_run1` and more"))
        self.assertFalse(pattern.search("folder final_4a_x_run1_r2"))


if __name__ == "__main__":
    unittest.main()
