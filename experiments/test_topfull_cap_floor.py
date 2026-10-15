"""Floor rule for the TopFull admission cap. Every API may be 0."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cap_floor as floor


ROOT = Path(__file__).resolve().parents[1]
APIS = ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")


class TestFloorThreshold(unittest.TestCase):
    def test_every_api_can_sit_at_zero(self):
        for name in APIS:
            for value, expected in ((0, 0), (-3, 0), (0.4, 0.4), (10, 10), (15.4, 15.4)):
                with self.subTest(name=name, value=value):
                    self.assertEqual(floor.floor_threshold(value), expected)

    def test_inlined_floor_matches_helper(self):
        src = "def apply(api):\n" + floor.overload_floor_new() + "        return api['threshold']\n"
        ns = {}
        exec(src, ns)
        for name in APIS:
            for value in (0, -3, 0.4, 10, 15.4):
                api = {"name": name, "threshold": value}
                self.assertEqual(ns["apply"](api), floor.floor_threshold(value))

    def test_zero_threshold_ratio_is_zero(self):
        self.assertEqual(floor.goodput_ratio(22.0, 0), 0.0)
        self.assertEqual(floor.goodput_ratio(22.0, 10), 2.2)

    def test_generated_blocks_use_the_floor(self):
        block = floor.overload_floor_new()
        self.assertIn("TOPFULL_CAP_FLOOR", block)
        self.assertIn("if api['threshold'] <= 0:", block)
        self.assertIn("api['threshold'] = 0", block)
        self.assertNotIn("10", block)
        zero = floor.deploy_rl_zero_block()
        self.assertIn("TOPFULL_CAP_FLOOR", zero)
        self.assertNotIn("stop(reset=True)", zero)
        self.assertNotIn("zero threshold", zero)
        ratio = floor.deploy_rl_ratio_block()
        self.assertEqual(
            ratio,
            "        state = 0.0 if self.threshold == 0 else goodput / self.threshold\n",
        )
        proxy = floor.proxy_burst_new()
        self.assertIn("if newRate > 0 && burst < 1", proxy)
        self.assertIn("targetLimiter.SetBurst(burst)", proxy)
        self.assertNotIn("SetBurst(int(newRate))", proxy)


if __name__ == "__main__":
    unittest.main()
