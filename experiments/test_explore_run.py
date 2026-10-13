"""Unit tests for experiments/explore_run.py."""
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import explore_run  # noqa: E402
import run_timeline  # noqa: E402

NAN = float("nan")


def events(rows):
    return pd.DataFrame(rows, columns=run_timeline.SWITCH_EVENT_COLUMNS)


class TestCodes(unittest.TestCase):
    def test_codes_follow_controlled_edges_order(self):
        codes = explore_run.EDGE_CODES
        self.assertEqual(len(codes), 14)
        self.assertEqual(codes["frontend->adservice"], "E1")
        self.assertEqual(codes["frontend->checkoutservice"], "E3")
        self.assertEqual(codes["frontend->productcatalogservice"], "E5")
        self.assertEqual(codes["recommendationservice->productcatalogservice"], "E14")
        services = explore_run.SERVICE_CODES
        self.assertEqual(len(services), 9)
        self.assertEqual(services["adservice"], "V1")
        self.assertEqual(services["checkoutservice"], "V3")
        self.assertEqual(services["emailservice"], "V8")
        self.assertEqual(services["paymentservice"], "V9")


class TestMarkers(unittest.TestCase):
    def test_labels_hover_and_climb_exclusion(self):
        found = explore_run.markers(events([
            [10.0, "frontend->productcatalogservice", "ON→OFF", "rpr_burst", "2.46", NAN, "3", NAN],
            [20.0, "checkoutservice", "OFF→ON", "rejection", NAN, "0.03", "0", "11"],
            [30.0, "frontend->checkoutservice", "ON→OFF", "rpr", "0.90", NAN, "1", NAN],
            [40.0, "frontend->cartservice", "1→2", "rpr", NAN, NAN, "1", NAN],
            [50.0, "frontend->cartservice", "2→3", "rpr", NAN, NAN, "2", NAN],
        ]))
        self.assertEqual([m["label"] for m in found], ["E5 burst", "V3", "E3 normal"])
        self.assertEqual([m["x"] for m in found], [10.0, 20.0, 30.0])
        self.assertIn("rpr=2.46", found[0]["hover"])
        self.assertIn("from_attempts=3", found[0]["hover"])
        self.assertNotIn("rejection", found[0]["hover"])
        self.assertIn("consecutive_low=11", found[1]["hover"])
        self.assertNotEqual(found[0]["color"], found[1]["color"])


class TestSloMiss(unittest.TestCase):
    def test_fail_over_rps_empty_when_no_load(self):
        view = pd.DataFrame({"locust.total.Fail": [0.0, 5.0, 3.0],
                             "locust.total.RPS": [10.0, 0.0, 6.0]})
        result = explore_run.slo_miss(view)
        self.assertEqual(result.iloc[0], 0.0)
        self.assertTrue(math.isnan(result.iloc[1]))
        self.assertEqual(result.iloc[2], 0.5)
        self.assertIsNone(explore_run.slo_miss(pd.DataFrame({"x": [1]})))


class TestStrip(unittest.TestCase):
    def test_rows_follow_edge_order_and_off_runs_have_none(self):
        view = pd.DataFrame({
            "rg.frontend->checkoutservice.attempts": [3.0, 0.0],
            "rg.frontend->adservice.attempts": [3.0, 3.0],
        })
        matrix = explore_run.strip_matrix(view)
        self.assertEqual(list(matrix.index), ["E1", "E3"])
        self.assertEqual(matrix.loc["E3"].tolist(), [3.0, 0.0])
        self.assertIsNone(explore_run.strip_matrix(pd.DataFrame({"locust.total.RPS": [1.0]})))


class TestLineSpecs(unittest.TestCase):
    def view(self):
        return pd.DataFrame({
            "locust.total.Goodput": [1.0, 2.0],
            "locust.total.RPS": [1.0, 2.0],
            "locust.total.Latency95": [5.0, 6.0],
            "inbound.cartservice.rejection": [0.0, 0.0],
            "inbound.checkoutservice.rejection": [0.0, 0.1],
            "edge.frontend->checkoutservice.rpr": [0.0, 0.4],
            "edge.frontend->checkoutservice.retry_per_s": [0.0, 2.0],
            "resource.frontend.cpu_millicores": [10.0, 20.0],
        })

    def test_quiet_lines_are_legend_only_unless_all(self):
        by_column = {s[1]: s for s in explore_run.line_specs(self.view())}
        self.assertIs(by_column["inbound.checkoutservice.rejection"][3], True)
        self.assertEqual(by_column["inbound.cartservice.rejection"][3], "legendonly")
        self.assertEqual(by_column["edge.frontend->checkoutservice.rpr"][2], "E3 frontend->checkoutservice")
        self.assertEqual(by_column["inbound.cartservice.rejection"][2], "cartservice")
        self.assertEqual(by_column["locust.total.Goodput"][2], "Goodput")
        every = {s[1]: s for s in explore_run.line_specs(self.view(), show_all=True)}
        self.assertIs(every["inbound.cartservice.rejection"][3], True)


if __name__ == "__main__":
    unittest.main()
