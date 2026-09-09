"""
test_topfull_throttle_collector.py — Unit tests for TopFull throttle collector.

Run:
    python experiments/test_topfull_throttle_collector.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_throttle_collector as ttc

# 2023-11-14T22:13:20Z
EPOCH = 1700000000.0


class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        # 22:13:20 is already mod 5 == 0; +3s → still 22:13:20
        ts = ttc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_next_bucket(self):
        ts = ttc.tick_timestamp(5, now=EPOCH + 5.0)
        self.assertEqual(ts, "2023-11-14T22:13:25Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        ttc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)

    def test_zero_when_already_on_next_boundary_is_non_negative(self):
        slept = []
        ttc.sleep_until_next_tick(1, now=EPOCH, sleeper=lambda s: slept.append(s))
        self.assertGreaterEqual(slept[0], 0.0)
        self.assertLessEqual(slept[0], 1.0)


if __name__ == "__main__":
    unittest.main()
