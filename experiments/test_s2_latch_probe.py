"""Unit tests for s2_latch_probe. No network, no result folders."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_latch_probe as p


def base_cfg():
    return {
        "scenario_id": 2, "scenario_name": "sustained_overload", "condition": "baseline",
        "run_number": 1, "description": "x", "duration_seconds": 600,
        "locust": {"user_counts": {"getproduct": 275, "postcheckout": 85, "getcart": 100,
                                   "postcart": 90, "emptycart": 5},
                   "spawn_rate": 50, "scripts": ["online_boutique_create_v2.sh"]},
        "paper_cpu_reconcile": False,
        "scale_constraints": [
            {"deployment": "checkoutservice", "namespace": "default", "container": "server",
             "method": "cpu_limit", "cpu_limit_millicores": 800},
            {"deployment": "recommendationservice", "namespace": "default", "container": "server",
             "method": "cpu_limit", "cpu_limit_millicores": 1150},
        ],
        "log_folder": "old",
    }


def cpu(cfg, dep):
    return next(c["cpu_limit_millicores"] for c in cfg["scale_constraints"]
                if c["deployment"] == dep and c["method"] == "cpu_limit")


class TestBuildConfig(unittest.TestCase):
    def test_control_forces_run89_counts_and_names_the_slot(self):
        c = p.build_config(base_cfg(), "control", 111)
        self.assertEqual(c["locust"]["user_counts"], p.BASE_COUNTS)
        self.assertEqual(c["run_number"], 111)
        self.assertEqual(c["log_folder"], "baseline_no_topfull_sustained_overload_run111")
        self.assertEqual(c["locust"]["spawn_rate"], 50)
        self.assertNotIn("restart_before_hold", c)
        self.assertEqual(cpu(c, "checkoutservice"), 800)

    def test_input_is_not_mutated(self):
        b = base_cfg(); snap = copy.deepcopy(b)
        p.build_config(b, "ck_rep2_pc120", 115)
        self.assertEqual(b, snap)

    def test_each_treatment_changes_exactly_its_field(self):
        c = p.build_config(base_cfg(), "spawn10", 109)
        self.assertEqual(c["locust"]["spawn_rate"], 10)
        c = p.build_config(base_cfg(), "recs_users310", 114)
        self.assertEqual(c["locust"]["user_counts"]["getproduct"], 310)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        c = p.build_config(base_cfg(), "pc120", 117)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(c["locust"]["user_counts"]["getproduct"], 275)
        c = p.build_config(base_cfg(), "recs_cpu1000", 110)
        self.assertEqual(cpu(c, "recommendationservice"), 1000)
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        c = p.build_config(base_cfg(), "ck_cpu1000", 113)
        self.assertEqual(cpu(c, "checkoutservice"), 1000)
        self.assertEqual(cpu(c, "recommendationservice"), 1150)

    def test_replica_treatments_add_replicas_constraint_keeping_cpu(self):
        c = p.build_config(base_cfg(), "ck_rep2", 112)
        reps = [x for x in c["scale_constraints"] if x["method"] == "replicas"]
        self.assertEqual(len(reps), 1)
        self.assertEqual((reps[0]["deployment"], reps[0]["replicas"]), ("checkoutservice", 2))
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        c = p.build_config(base_cfg(), "ck_rep2_pc120", 115)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(sum(1 for x in c["scale_constraints"] if x["method"] == "replicas"), 1)

    def test_restart_treatment_sets_restart_key_only(self):
        c = p.build_config(base_cfg(), "restart", 108)
        self.assertEqual(c["restart_before_hold"]["deployments"],
                         ["checkoutservice", "recommendationservice"])
        self.assertEqual(c["restart_before_hold"]["settle_seconds"], 60)
        self.assertEqual(c["locust"]["user_counts"], p.BASE_COUNTS)

    def test_unknown_treatment_raises(self):
        with self.assertRaises(KeyError):
            p.build_config(base_cfg(), "nope", 1)


class TestPrepAndExpected(unittest.TestCase):
    def test_expected_replicas(self):
        e = p.expected_replicas("control")
        self.assertEqual((e["frontend"], e["checkoutservice"]), (4, 1))
        self.assertEqual(p.expected_replicas("ck_rep2")["checkoutservice"], 2)
        self.assertEqual(p.expected_replicas("ck_rep2_pc120")["checkoutservice"], 2)

    def test_prep_script_sets_absolute_state_with_lf_only(self):
        s = p.prep_script("ck_cpu1000")
        self.assertNotIn("\r", s)
        self.assertIn('patch_cpu checkoutservice 1000m', s)
        self.assertIn('patch_cpu recommendationservice 1150m', s)
        self.assertIn('--replicas=1', s)
        s = p.prep_script("ck_rep2")
        self.assertIn('--replicas=2', s)
        self.assertIn('patch_cpu checkoutservice 800m', s)
        s = p.prep_script("recs_cpu1000")
        self.assertIn('patch_cpu recommendationservice 1000m', s)
        self.assertIn("status.phase=Pending", s)


class TestClassify(unittest.TestCase):
    def o(self, ck_streak, rc_streak, rc_ret, ck_ov=0, rc_ov=0, em=0, pay=0):
        return {"svc": {"checkoutservice": {"streak": ck_streak, "ov": ck_ov},
                        "recommendationservice": {"streak": rc_streak, "ov": rc_ov},
                        "emailservice": {"ov": em}, "paymentservice": {"ov": pay}},
                "edges": {("frontend", "recommendationservice"): rc_ret}}

    def test_sticky(self):
        self.assertEqual(p.classify(self.o(551, 0, 0)), "sticky")

    def test_released(self):
        self.assertEqual(p.classify(self.o(58, 238, 224314)), "released")

    def test_run101_recommendations_retries_are_released(self):
        # run101 frontend→recommendations retries are 76303, under the old 100k bar.
        self.assertEqual(p.classify(self.o(375, 77, 76303)), "released")

    def test_other(self):
        self.assertEqual(p.classify(self.o(0, 250, 50000)), "other")

    def test_blend_needs_all_four_bars_and_a_leaf(self):
        self.assertTrue(p.is_blend(self.o(58, 238, 224314, ck_ov=164, rc_ov=485, em=23)))
        self.assertFalse(p.is_blend(self.o(58, 238, 224314, ck_ov=164, rc_ov=485)))
        self.assertFalse(p.is_blend(self.o(5, 238, 224314, ck_ov=164, rc_ov=485, em=23)))
        self.assertTrue(p.is_blend(self.o(20, 30, 1, ck_ov=10, rc_ov=10, pay=10)))


class TestClassifyBoundary(unittest.TestCase):
    def o(self, ck, rc, ret):
        return {"svc": {"checkoutservice": {"streak": ck, "ov": 0},
                        "recommendationservice": {"streak": rc, "ov": 0}},
                "edges": {("frontend", "recommendationservice"): ret}}

    def test_run101_like_76303_is_released(self):
        self.assertEqual(p.classify(self.o(375, 77, 76303)), "released")

    def test_bar_is_70000(self):
        self.assertEqual(p.classify(self.o(10, 10, 69999)), "other")
        self.assertEqual(p.classify(self.o(10, 10, 70000)), "released")

    def test_100000_is_no_longer_the_bar(self):
        self.assertEqual(p.classify(self.o(10, 10, 85000)), "released")


if __name__ == "__main__":
    unittest.main()
