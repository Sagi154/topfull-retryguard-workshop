import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_analysis_runs_configs as gen  # noqa: E402
import run_scenario  # noqa: E402

CONFIGS = Path(__file__).resolve().parent / "configs"
OUT = CONFIGS / "analysis_runs"
ROOT = "experiments/results/final_runs_results"


class TestBuildText(unittest.TestCase):
    def setUp(self):
        self.src = (CONFIGS / "final_configs" / "3" / "s3_both_burst.yaml"
                    ).read_text(encoding="utf-8")

    def test_sets_slot(self):
        cfg = yaml.safe_load(gen.build_text(
            self.src, "analysis_s3_both_burst_run2", 2))
        self.assertEqual(cfg["run_number"], 2)
        self.assertEqual(cfg["log_folder"], "analysis_s3_both_burst_run2")
    def test_everything_else_is_unchanged(self):
        new = yaml.safe_load(gen.build_text(self.src, "x_run1", 1))
        old = yaml.safe_load(self.src)
        for k in ("run_number", "log_folder"):
            old.pop(k)
            new.pop(k)
        self.assertEqual(new, old)


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(OUT.rglob("*.yaml"))

    def test_sixty_files(self):
        self.assertEqual(len(self.paths), 60)

    def test_unique_log_folders_with_analysis_prefix(self):
        names = [yaml.safe_load(p.read_text(encoding="utf-8"))["log_folder"]
                 for p in self.paths]
        self.assertEqual(len(set(names)), 60)
        self.assertTrue(all(n.startswith("analysis_") for n in names))

    def test_all_resolve_under_analysis_root(self):
        for p in self.paths:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            self.assertTrue(
                run_scenario.local_results_dir(cfg).startswith(ROOT + "/"),
                msg=p.name)

    def test_each_group_has_all_variants_twice(self):
        for group, _src, prefix in gen.GROUPS:
            got = sorted(q.name for q in (OUT / group).glob("*.yaml"))
            want = sorted(f"{prefix}_{v}_run{n}.yaml"
                          for v in gen.VARIANTS for n in gen.REPEATS)
            self.assertEqual(got, want, msg=group)

    def test_variant_destinations(self):
        want = {
            "rg_only_normal": "_normal/rg_only/",
            "both_normal": "_normal/both/",
            "tf_only": "_normal/tf_only/",
            "rg_only_burst": "_burst/rg_only/",
            "both_burst": "_burst/both/",
        }
        for p in self.paths:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            dest = run_scenario.local_results_dir(cfg)
            variant = next(v for v in want if f"_{v}_run" in p.name)
            self.assertTrue(dest.endswith(want[variant]), msg=p.name)

    def test_constrained_rows(self):
        def limit(p, dep):
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            return next(r["cpu_limit_millicores"]
                        for r in cfg["scale_constraints"]
                        if r["deployment"] == dep)
        self.assertEqual(
            limit(OUT / "s3" / "s3_tf_only_run1.yaml", "checkoutservice"), 200)
        self.assertEqual(
            limit(OUT / "s4a_constrained" / "4a_constrained_tf_only_run1.yaml",
                  "productcatalogservice"), 100)
        self.assertEqual(
            limit(OUT / "s4b" / "4b_tf_only_run1.yaml", "emailservice"), 50)
        self.assertNotEqual(
            limit(OUT / "s4a_unconstrained" / "4a_unconstrained_tf_only_run1.yaml",
                  "productcatalogservice"), 100)


if __name__ == "__main__":
    unittest.main()
