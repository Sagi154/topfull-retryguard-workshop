"""Unit tests for experiments/variant_summary.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_cap_avg as avg  # noqa: E402
import topfull_cap_median as med  # noqa: E402
import variant_summary as vs  # noqa: E402


def _avg(offered, effective):
    return {k: 0 for k in avg.FIELDS} | {"mean_offered": offered, "mean_effective": effective}


def _med(offered, effective):
    return {k: 0 for k in med.FIELDS} | {"median_offered": offered, "median_effective": effective}


def _good(mean, median):
    return {"getproduct": {"mean_goodput": mean, "median_goodput": median}}


class TestVariant(unittest.TestCase):
    def test_postcart_and_emptycart_are_left_out(self):
        row = {k: 1.0 for k in vs.FIELDS}
        text = vs.render("t", {"getproduct": row, "postcart": row, "emptycart": row, "postcheckout": row})
        self.assertIn("getproduct", text)
        self.assertIn("postcheckout", text)
        self.assertNotIn("postcart", text)
        self.assertNotIn("emptycart", text)
    def test_groups_a_run_and_a_variant_directory(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root) / "S2_burst" / "both" / "run1"
            other = Path(root) / "S2_normal" / "tf_only" / "run2"
            run.mkdir(parents=True)
            other.mkdir(parents=True)
            (run / "run_manifest.json").write_text("{}", encoding="utf-8")
            (other / "getproduct.csv").write_text("RPS,Goodput\n", encoding="utf-8")
            grouped = vs.group_runs([run.parent, other])
        self.assertEqual(list(grouped), ["S2_burst/both", "S2_normal/tf_only"])
        self.assertEqual(grouped["S2_burst/both"], [run])

    def test_variant_percentage_uses_the_aggregated_caps(self):
        loaded = [
            (_good(10.0, 40.0), {"getproduct": _avg(100.0, 50.0)}, {"getproduct": _med(80.0, 40.0)}),
            (_good(30.0, 60.0), {"getproduct": _avg(200.0, 50.0)}, {"getproduct": _med(120.0, 60.0)}),
        ]
        row = vs.variant_metrics(loaded)["getproduct"]
        self.assertEqual(row["mean_goodput"], 20.0)
        self.assertEqual(row["median_goodput"], 50.0)
        self.assertAlmostEqual(row["mean_effective_pct"], 100.0 * 50.0 / 150.0)
        self.assertAlmostEqual(row["median_effective_pct"], 100.0 * 50.0 / 100.0)

    def test_run_row_blanks_the_percentage_when_topfull_is_off(self):
        row = vs.run_metrics(_good(10.0, 12.0), None, None)["getproduct"]
        self.assertEqual(row["mean_goodput"], 10.0)
        self.assertIsNone(row["mean_effective_pct"])
        self.assertIsNone(row["median_effective_pct"])


if __name__ == "__main__":
    unittest.main()
