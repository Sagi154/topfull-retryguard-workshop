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


class TestV2Treatments(unittest.TestCase):
    def test_four_new_treatments(self):
        c = p.build_config(base_cfg(), "ck_rep2_pc120_spawn10", 130)
        self.assertEqual(c["locust"]["spawn_rate"], 10)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual([x["replicas"] for x in c["scale_constraints"] if x["method"] == "replicas"], [2])
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        c = p.build_config(base_cfg(), "ck_cpu1000_pc120", 131)
        self.assertEqual(cpu(c, "checkoutservice"), 1000)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(c["locust"]["spawn_rate"], 50)
        self.assertFalse([x for x in c["scale_constraints"] if x["method"] == "replicas"])
        c = p.build_config(base_cfg(), "ck_cpu1000_pc120_spawn10", 137)
        self.assertEqual((cpu(c, "checkoutservice"), c["locust"]["spawn_rate"]), (1000, 10))
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        c = p.build_config(base_cfg(), "recs_cpu1000_spawn10", 132)
        self.assertEqual((cpu(c, "recommendationservice"), c["locust"]["spawn_rate"]), (1000, 10))
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        self.assertEqual(cpu(c, "checkoutservice"), 800)

    def test_expected_replicas_for_new_arms(self):
        self.assertEqual(p.expected_replicas("ck_rep2_pc120_spawn10")["checkoutservice"], 2)
        self.assertEqual(p.expected_replicas("ck_cpu1000_pc120_spawn10")["checkoutservice"], 1)


class TestFitAndPrepV2(unittest.TestCase):
    def test_projected_requests(self):
        self.assertEqual(p.projected_requests_mc("control"), 14305)
        self.assertEqual(p.projected_requests_mc("spawn10"), 14305)
        self.assertEqual(p.projected_requests_mc("ck_rep2_pc120"), 15205)   # run123 t0 showed 15205
        self.assertEqual(p.projected_requests_mc("ck_cpu1000_pc120"), 14505)
        self.assertEqual(p.projected_requests_mc("recs_cpu1000"), 14155)

    def test_every_v2_arm_fits_under_the_ceiling(self):
        for t in p.ARMS_V2 + ["control"]:
            self.assertLessEqual(p.projected_requests_mc(t), p.REQUEST_CEILING_MC, t)

    def test_the_pending_combination_would_not_fit(self):
        p.TREATMENTS["_bad"] = {"checkout_cpu": 1000, "checkout_replicas": 2}
        try:
            self.assertGreater(p.projected_requests_mc("_bad"), p.REQUEST_CEILING_MC)
        finally:
            del p.TREATMENTS["_bad"]

    def test_prep_scales_down_before_patching_then_rolls_then_scales_up(self):
        s = p.prep_script("ck_rep2_pc120")
        self.assertNotIn("\r", s)
        down = s.index("--replicas=1")
        patch = s.index("patch_cpu checkoutservice 800m")
        roll = s.index("rollout restart deployment/checkoutservice")
        up = s.index("--replicas=2")
        self.assertTrue(down < patch < roll < up)
        self.assertIn("rollout restart deployment/recommendationservice", s)

    def test_prep_node_line_precedes_pending_and_ceiling_exits_3(self):
        s = p.prep_script("control")
        self.assertLess(s.index("--- node_cpu_requests_m"), s.index("--- pending"))
        self.assertLess(s.index("--- pending"), s.index("--- end"))
        self.assertIn('-gt 15600', s)
        self.assertIn("exit 3", s)
        self.assertIn("topfull-worker1", s)


class TestHoldOrder(unittest.TestCase):
    def setUp(self):
        self.order = p.hold_order(20261004, 128)

    def test_twenty_holds_slots_128_to_147(self):
        self.assertEqual([x[0] for x in self.order], list(range(128, 148)))

    def test_each_arm_once_per_block_and_three_controls_per_block(self):
        for blk in "AB":
            ts = [t for _, b, t in self.order if b == blk]
            self.assertEqual(len(ts), 10)
            self.assertEqual(sorted(t for t in ts if t != "control"), sorted(p.ARMS_V2))
            self.assertEqual(ts.count("control"), 3)

    def test_first_and_last_holds_are_controls(self):
        self.assertEqual(self.order[0][2], "control")
        self.assertEqual(self.order[-1][2], "control")

    def test_no_same_family_back_to_back_including_block_boundary(self):
        ts = [t for _, _, t in self.order]
        for a, b in zip(ts, ts[1:]):
            self.assertNotEqual(p.family(a), p.family(b), (a, b))

    def test_deterministic_for_a_seed_and_different_for_another(self):
        self.assertEqual(self.order, p.hold_order(20261004, 128))
        self.assertNotEqual([t for _, _, t in self.order],
                            [t for _, _, t in p.hold_order(1, 128)])

    def test_pinned_order_for_seed_20261004(self):
        self.assertEqual([t for _, _, t in self.order], [
            "control", "spawn10", "control", "ck_cpu1000_pc120", "recs_cpu1000_spawn10",
            "ck_rep2_pc120", "recs_cpu1000", "control", "ck_rep2_pc120_spawn10",
            "ck_cpu1000_pc120_spawn10",
            "spawn10", "control", "recs_cpu1000_spawn10", "ck_rep2_pc120_spawn10",
            "ck_cpu1000_pc120", "control", "recs_cpu1000", "ck_cpu1000_pc120_spawn10",
            "ck_rep2_pc120", "control"])


class TestPodAges(unittest.TestCase):
    T0 = (
        "### pods\n"
        "NAME  READY STATUS RESTARTS AGE IP NODE\n"
        "checkoutservice-85fb96fbf-76zdj          2/2     Running   2 (6h6m ago)   6h15m   192.168.148.111   topfull-worker1   <none>   <none>\n"
        "checkoutservice-85fb96fbf-p27c4          2/2     Running   0              40m     192.168.148.110   topfull-worker1   <none>   <none>\n"
        "recommendationservice-566f644686-jwsxh   2/2     Running   0              6m22s   192.168.148.92    topfull-worker1   <none>   <none>\n"
        "frontend-85ff4b5b6d-8zjvs                2/2     Running   22 (6h6m ago)  4d15h   192.168.148.118   topfull-worker1   <none>   <none>\n")

    def test_parse_age_seconds(self):
        self.assertEqual(p.parse_age_seconds("6m22s"), 382)
        self.assertEqual(p.parse_age_seconds("6h15m"), 22500)
        self.assertEqual(p.parse_age_seconds("2d14h"), 2 * 86400 + 14 * 3600)
        self.assertEqual(p.parse_age_seconds("45s"), 45)
        with self.assertRaises(ValueError):
            p.parse_age_seconds("old")

    def test_pod_ages_picks_only_checkout_and_recs_and_skips_restart_age(self):
        a = p.pod_ages(self.T0)
        self.assertEqual(sorted(a["checkoutservice"]), [2400, 22500])
        self.assertEqual(a["recommendationservice"], [382])


if __name__ == "__main__":
    unittest.main()
