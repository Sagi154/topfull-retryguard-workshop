"""Unit tests for experiments/throttle_stale.py."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import throttle_stale  # noqa: E402


def frame(fresh_until, total=100, api="getproduct", cap=150.0):
    rows = [{
        "api": api, "hold_s": float(s), "threshold": cap,
        "threshold_fresh": int(s % 5 == 0 and s <= fresh_until),
    } for s in range(total)]
    return pd.DataFrame(rows)


class TestStretches(unittest.TestCase):
    def test_a_gap_over_30_s_to_the_end_is_a_stretch(self):
        t = list(range(0, 100, 5))
        fresh = [x <= 20 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(20.0, 95.0)])

    def test_normal_five_second_polls_have_no_stretch(self):
        t = list(range(100))
        fresh = [x % 5 == 0 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [])

    def test_a_gap_before_the_first_fresh_read_counts(self):
        t = list(range(100))
        fresh = [x >= 40 for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(0.0, 40.0)])

    def test_exactly_10_s_is_not_stale(self):
        t = list(range(11))
        fresh = [x in (0, 10) for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [])

    def test_eleven_seconds_is_a_stretch(self):
        t = list(range(12))
        fresh = [x in (0, 11) for x in t]
        self.assertEqual(throttle_stale.stale_stretches(t, fresh), [(0.0, 11.0)])

    def test_empty_input_gives_nothing(self):
        self.assertEqual(throttle_stale.stale_stretches([], []), [])


class TestCapSeries(unittest.TestCase):
    def test_stale_points_start_after_the_carry_window(self):
        series = throttle_stale.stale_cap_series(frame(fresh_until=20))
        x, y = series["getproduct"]
        self.assertEqual(float(x[0]), 27.0)
        self.assertEqual(float(x[-1]), 99.0)
        self.assertTrue(np.all(y == 150.0))

    def test_clean_hold_has_no_stale_series_and_no_band(self):
        df = frame(fresh_until=99)
        self.assertEqual(throttle_stale.stale_cap_series(df), {})
        self.assertEqual(throttle_stale.stale_bands(df), [])

    def test_no_cap_and_empty_reads_are_not_drawn(self):
        self.assertEqual(throttle_stale.stale_cap_series(frame(20, cap=10000.0)), {})
        self.assertEqual(throttle_stale.stale_cap_series(frame(20, cap=0.0)), {})

    def test_missing_or_old_csv_does_not_crash(self):
        self.assertEqual(throttle_stale.stale_cap_series(pd.DataFrame()), {})
        old = pd.DataFrame({"api": ["a"], "hold_s": [1.0], "threshold": [5.0]})
        self.assertEqual(throttle_stale.stale_cap_series(old), {})
        self.assertEqual(throttle_stale.stale_bands(old), [])


class TestBands(unittest.TestCase):
    def test_bands_merge_across_apis(self):
        df = pd.concat([frame(20, api="getproduct"), frame(40, api="getcart")])
        self.assertEqual(throttle_stale.stale_bands(df), [(20.0, 99.0)])

    def test_separate_stretches_stay_separate(self):
        rows = []
        for s in range(200):
            fresh = s % 5 == 0 and not (20 < s < 80) and not (100 < s < 160)
            rows.append({"api": "getproduct", "hold_s": float(s), "threshold": 150.0,
                         "threshold_fresh": int(fresh)})
        self.assertEqual(throttle_stale.stale_bands(pd.DataFrame(rows)),
                         [(20.0, 80.0), (100.0, 160.0)])


if __name__ == "__main__":
    unittest.main()
