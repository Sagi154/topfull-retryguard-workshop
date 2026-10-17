"""Unit tests for experiments/locust_goodput.py."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import locust_goodput as g  # noqa: E402


class TestGoodput(unittest.TestCase):
    def test_rps_zero_is_left_out(self):
        values = g.scored([0.0, 10.0, 20.0], [99.0, 4.0, 8.0])
        self.assertEqual(list(values), [4.0, 8.0])

    def test_mean_and_even_median(self):
        s = g.summarize([1.0, 2.0, 3.0, 10.0])
        self.assertEqual(s["scored_s"], 4)
        self.assertEqual(s["mean_goodput"], 4.0)
        self.assertEqual(s["median_goodput"], 2.5)

    def test_empty(self):
        s = g.summarize([])
        self.assertEqual(s["scored_s"], 0)
        self.assertIsNone(s["mean_goodput"])
        self.assertIsNone(s["median_goodput"])

    def test_pooled_concatenates_seconds(self):
        s = g.summarize(np.concatenate([
            g.scored([10.0, 0.0], [4.0, 99.0]),
            g.scored([10.0, 10.0], [6.0, 10.0]),
        ]))
        self.assertEqual(s["scored_s"], 3)
        self.assertEqual(s["mean_goodput"], 20.0 / 3)
        self.assertEqual(s["median_goodput"], 6.0)


if __name__ == "__main__":
    unittest.main()
