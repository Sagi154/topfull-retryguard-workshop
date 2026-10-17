"""Unit tests for experiments/topfull_cap_median.py."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cap_median as t  # noqa: E402


class TestSummary(unittest.TestCase):
    def test_median_effective_drops_unknown_and_uses_offered_when_uncapped(self):
        rps = [90.0, 40.0, 70.0, 10.0]
        kinds = np.array(["capped", "capped", "nocap", "unknown"])
        caps = np.array([60.0, 80.0, np.nan, np.nan])
        s = t.api_summary(rps, kinds, caps)
        self.assertEqual(s["median_effective"], 60.0)
        self.assertEqual(s["median_offered"], 70.0)
        self.assertEqual(s["median_cap_when_capped"], 70.0)
        self.assertEqual(s["unknown_s"], 1)

    def test_even_count_is_the_midpoint(self):
        rps = [10.0, 20.0, 30.0, 40.0]
        kinds = np.array(["nocap"] * 4)
        s = t.api_summary(rps, kinds, np.full(4, np.nan))
        self.assertEqual(s["median_offered"], 25.0)
        self.assertEqual(s["median_effective"], 25.0)

    def test_all_unknown_has_no_median(self):
        s = t.api_summary([5.0], np.array(["unknown"]), np.array([np.nan]))
        self.assertIsNone(s["median_effective"])
        self.assertIsNone(t.effective_pct(s))

    def test_effective_pct(self):
        self.assertEqual(t.effective_pct({"median_offered": 80.0, "median_effective": 40.0}), 50.0)

    def test_cell_median_of_two_runs_is_their_midpoint(self):
        def row(offered, effective):
            return {k: 0 for k in t.FIELDS} | {
                "median_offered": offered, "median_effective": effective}
        cell = t.cell_median([
            {"getproduct": row(100.0, 40.0)},
            {"getproduct": row(200.0, 60.0)},
        ])
        self.assertEqual(cell["getproduct"]["median_offered"], 150.0)
        self.assertEqual(cell["getproduct"]["median_effective"], 50.0)
        self.assertEqual(t.effective_pct(cell["getproduct"]), 100.0 * 50.0 / 150.0)


if __name__ == "__main__":
    unittest.main()
