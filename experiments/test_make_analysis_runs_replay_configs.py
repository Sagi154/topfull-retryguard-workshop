import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_analysis_runs_replay_configs as replay  # noqa: E402
import run_scenario  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results" / "final_runs_results"
CONFIGS = ROOT / "experiments" / "configs"


class TestReplaySlots(unittest.TestCase):
    def test_fifteen_slots_and_the_run4_exception(self):
        self.assertEqual(len(replay.SLOTS), 15)
        by_name = {f"analysis_{p}_{v}_run{n}": (g, n)
                   for g, _s, p, v, n in replay.SLOTS}
        self.assertEqual(len(by_name), 15)
        self.assertEqual(by_name["analysis_s2_both_normal_run4"], ("s2", 4))
        self.assertNotIn("analysis_s2_both_normal_run3", by_name)
        run3 = [name for name, (_g, n) in by_name.items() if n == 3]
        self.assertEqual(len(run3), 14)

    def test_groups_are_only_s2_s3_and_4a_unconstrained(self):
        groups = {g for g, _s, _p, _v, _n in replay.SLOTS}
        self.assertEqual(groups, {"s2", "s3", "s4a_unconstrained"})

    def test_each_built_yaml_matches_its_source(self):
        for group, src_dir, prefix, variant, n in replay.SLOTS:
            src = CONFIGS / "final_configs" / src_dir / f"{prefix}_{variant}.yaml"
            log_folder = f"analysis_{prefix}_{variant}_run{n}"
            built = yaml.safe_load(replay.build_text(
                src.read_text(encoding="utf-8"), log_folder, n))
            old = yaml.safe_load(src.read_text(encoding="utf-8"))
            self.assertEqual(built["run_number"], n)
            self.assertEqual(built["log_folder"], log_folder)
            for key in ("run_number", "log_folder"):
                old.pop(key)
                built.pop(key)
            self.assertEqual(built, old, msg=log_folder)

    def test_locked_mixes_and_constrained_rows(self):
        def cfg(group, prefix, variant, n):
            src = next(s for s in replay.SLOTS
                       if s[0] == group and s[3] == variant)
            text = (CONFIGS / "final_configs" / src[1] / f"{prefix}_{variant}.yaml"
                    ).read_text(encoding="utf-8")
            return yaml.safe_load(replay.build_text(
                text, f"analysis_{prefix}_{variant}_run{n}", n))

        s2 = cfg("s2", "s2", "rg_only_normal", 3)
        s3 = cfg("s3", "s3", "tf_only", 3)
        a = cfg("s4a_unconstrained", "4a_unconstrained", "both_burst", 3)
        self.assertEqual(s2["locust"]["user_counts"], {
            "getproduct": 275, "postcheckout": 90, "getcart": 100,
            "postcart": 90, "emptycart": 5})
        self.assertEqual(s3["locust"]["user_counts"], {
            "getproduct": 175, "postcheckout": 30, "getcart": 70,
            "postcart": 90, "emptycart": 5})
        self.assertEqual(a["locust"]["user_counts"], {
            "getproduct": 50, "postcheckout": 20, "getcart": 50,
            "postcart": 600, "emptycart": 5})
        def limit(doc, dep):
            return next(r["cpu_limit_millicores"] for r in doc["scale_constraints"]
                        if r["deployment"] == dep)
        self.assertEqual(limit(s3, "checkoutservice"), 200)
        self.assertNotEqual(limit(a, "productcatalogservice"), 100)
        self.assertNotIn("burst_rpr", s2["retryguard"])
        self.assertEqual(a["retryguard"]["burst_rpr"], 2.0)

    def test_pull_paths_and_no_collision(self):
        occupied = {p.name for p in RESULTS.rglob("analysis_*") if p.is_dir()}
        self.assertIn("analysis_s2_both_normal_run3", occupied)
        for group, src_dir, prefix, variant, n in replay.SLOTS:
            log_folder = f"analysis_{prefix}_{variant}_run{n}"
            self.assertNotIn(log_folder, occupied, msg=log_folder)
            src = CONFIGS / "final_configs" / src_dir / f"{prefix}_{variant}.yaml"
            built = yaml.safe_load(replay.build_text(
                src.read_text(encoding="utf-8"), log_folder, n))
            dest = run_scenario.local_results_dir(built)
            self.assertTrue(
                dest.startswith("experiments/results/final_runs_results/"),
                msg=log_folder)
            self.assertTrue(dest.endswith("/"), msg=log_folder)

    def test_generate_writes_fifteen_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = replay.generate(Path(tmp))
            self.assertEqual(len(paths), 15)
            names = sorted(p.name for p in paths)
            self.assertIn("s2_both_normal_run4.yaml", names)
            self.assertNotIn("s2_both_normal_run3.yaml", names)


if __name__ == "__main__":
    unittest.main()
