"""Unit tests for experiments/topfull_cap_avg.py."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cap_avg as t  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_kinds(self):
        reads_t = [0, 5, 10, 15]
        reads_cap = [100.0, 10000.0, 0.0, 9950.0]
        kinds, caps = t.classify([1, 6, 11, 16, 30], reads_t, reads_cap)
        self.assertEqual(list(kinds), ["capped", "nocap", "empty", "nocap", "unknown"])
        self.assertEqual(caps[0], 100.0)

    def test_row_before_first_read_is_unknown(self):
        kinds, _ = t.classify([0.0], [2.0], [50.0])
        self.assertEqual(kinds[0], "unknown")

    def test_carry_limit(self):
        kinds, _ = t.classify([6.0, 6.5], [0.0], [50.0])
        self.assertEqual(list(kinds), ["capped", "unknown"])


class TestSummary(unittest.TestCase):
    def test_effective_is_min_of_cap_and_offered_and_nocap_uses_offered(self):
        rps = [90.0, 40.0, 70.0, 10.0]
        kinds = np.array(["capped", "capped", "nocap", "unknown"])
        caps = np.array([60.0, 80.0, np.nan, np.nan])
        s = t.api_summary(rps, kinds, caps)
        self.assertEqual(s["mean_effective"], (60 + 40 + 70) / 3)
        self.assertEqual(s["mean_offered"], (90 + 40 + 70) / 3)
        self.assertEqual(s["mean_cap_when_capped"], 70.0)
        self.assertEqual((s["capped_s"], s["nocap_s"], s["unknown_s"]), (2, 1, 1))

    def test_all_unknown_has_no_mean(self):
        s = t.api_summary([5.0], np.array(["unknown"]), np.array([np.nan]))
        self.assertIsNone(s["mean_effective"])
        self.assertIsNone(t.effective_pct(s))

    def test_effective_pct_is_effective_over_offered(self):
        self.assertEqual(t.effective_pct({"mean_offered": 80.0, "mean_effective": 40.0}), 50.0)
        self.assertIsNone(t.effective_pct({"mean_offered": 0.0, "mean_effective": 0.0}))

    def test_cell_mean_percentage_uses_the_averaged_means(self):
        def row(offered, effective):
            return {k: 0 for k in t.FIELDS} | {"mean_offered": offered, "mean_effective": effective}
        cell = t.cell_mean([
            {"getproduct": row(100.0, 50.0)},
            {"getproduct": row(200.0, 50.0)},
        ])
        self.assertAlmostEqual(t.effective_pct(cell["getproduct"]), 100.0 * 50.0 / 150.0)


if __name__ == "__main__":
    unittest.main()
