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

    def test_guide_records_the_cap_floor(self):
        text = (ROOT / "Guides and Info" / "TOPFULL-THROTTLE-METRICS.md").read_text(encoding="utf-8")
        self.assertIn("floors every entry API at 0 req/s", text)


class TestPatchSources(unittest.TestCase):
    SRC = ROOT / "TopFull" / "TopFull_master" / "online_boutique_scripts" / "src"

    def test_overload_detection_floors_every_api_at_zero(self):
        source = (self.SRC / "overload_detection.py").read_text(encoding="utf-8")
        patched = floor.patch_overload_detection(source)
        self.assertNotIn(floor.OVERLOAD_FLOOR_OLD, patched)
        self.assertIn(floor.overload_floor_new(), patched)
        self.assertEqual(floor.patch_overload_detection(patched), patched)

    def test_deploy_rl_keeps_a_zero_cap(self):
        source = (self.SRC / "deploy_rl.py").read_text(encoding="utf-8")
        patched = floor.patch_deploy_rl(source)
        self.assertNotIn(floor.DEPLOY_RL_ZERO_OLD, patched)
        self.assertNotIn('print("zero threshold")', patched)
        self.assertNotIn(floor.DEPLOY_RL_RATIO_OLD, patched)
        self.assertIn(floor.deploy_rl_zero_block(), patched)
        self.assertIn(floor.deploy_rl_ratio_block(), patched)
        self.assertIn('print("All APIs clean")', patched)
        self.assertEqual(floor.patch_deploy_rl(patched), patched)

    def test_proxy_burst_allows_a_fraction_and_rejects_zero(self):
        source = (self.SRC / "proxy" / "proxy_online_boutique.go").read_text(encoding="utf-8")
        patched = floor.patch_proxy_burst(source)
        self.assertNotIn(floor.PROXY_BURST_OLD, patched)
        self.assertIn(floor.proxy_burst_new(), patched)
        self.assertIn("SetBurst(int(newRateFloat))", patched)
        self.assertEqual(floor.patch_proxy_burst(patched), patched)

    def test_missing_site_aborts(self):
        with self.assertRaises(RuntimeError):
            floor.patch_overload_detection("no floor here\n")
        with self.assertRaises(RuntimeError):
            floor.patch_deploy_rl("no zero check\n")
        with self.assertRaises(RuntimeError):
            floor.patch_proxy_burst("package main\n")


if __name__ == "__main__":
    unittest.main()
