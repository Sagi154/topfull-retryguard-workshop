"""Unit tests for experiments/run_timeline.py."""
import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402
import run_timeline  # noqa: E402
from test_hold_clock import write_csv  # noqa: E402

E = 1_760_000_000.0
CLOCK = {"method": "fit", "start_utc": hold_clock.format_utc(E), "spacing_s": 0.6, "rows": 4}
FLAG = run_timeline.FLAG


def iso(seconds_after: float) -> str:
    return datetime.fromtimestamp(E + seconds_after, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


class TestPerSecondView(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.run = Path(self._tmp.name) / "run"
        self.run.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def view(self):
        return run_timeline.per_second_view(self.run, CLOCK)

    def test_two_locust_rows_in_one_second_are_averaged(self):
        write_csv(self.run / "total.csv", ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                  [[10, 0, 10, 1, 0], [20, 0, 20, 1, 0], [30, 0, 30, 1, 0], [40, 0, 40, 1, 0]])
        view = self.view()
        self.assertEqual(view.loc[0, "locust.total.RPS"], 15)
        self.assertEqual(view.loc[1, "locust.total.RPS"], 35)
        self.assertEqual(view.loc[0, "locust.total.RPS" + FLAG], 0)

    def test_counter_rates_gaps_resets_and_rejection(self):
        header = ["timestamp", "service", "total", "2xx", "5xx", "resets", "grpc_4", "grpc_14"]
        write_csv(self.run / "service_inbound.csv", header, [
            [iso(0), "recommendationservice", 0, 0, 0, 0, 0, 0],
            [iso(1), "recommendationservice", 10, 9, 1, 0, 1, 1],
            [iso(3), "recommendationservice", 30, 29, 1, 0, 1, 1],
            [iso(0), "cartservice", 0, 0, 0, 0, 0, 0],
            [iso(1), "cartservice", 10, 9, 1, 0, 1, 1],
            [iso(2), "cartservice", 5, 5, 1, 0, 1, 1],
        ])
        view = self.view()
        recs = "inbound.recommendationservice"
        self.assertEqual(view.loc[1, f"{recs}.total_per_s"], 10)
        self.assertTrue(empty(view.loc[2, f"{recs}.total_per_s"]))
        self.assertTrue(empty(view.loc[2, f"{recs}.total_per_s" + FLAG]))
        self.assertEqual(view.loc[3, f"{recs}.total_per_s"], 10)
        self.assertAlmostEqual(view.loc[1, f"{recs}.rejection"], 0.3)
        self.assertEqual(view.loc[3, f"{recs}.rejection"], 0.0)
        self.assertAlmostEqual(view.loc[1, "inbound.cartservice.rejection"], 0.1)
        self.assertTrue(empty(view.loc[2, "inbound.cartservice.total_per_s"]))

    def test_cap_carry_rules(self):
        header = ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"]
        rows = [
            [iso(0), "getproduct", 300, 0, 1, 0],
            [iso(1), "getproduct", 0, 0, 1, 0],
            [iso(2), "getproduct", 0, 0, 0, 0],
            [iso(3), "getproduct", 10000, 0, 1, 0],
            [iso(4), "getproduct", 0, 0, 0, 0],
            [iso(0), "getcart", 300, 0, 1, 0],
        ]
        rows += [[iso(s), "getcart", 0, 0, 0, 0] for s in range(1, 10)]
        write_csv(self.run / "topfull_throttle.csv", header, rows)
        view = self.view()
        cap = "throttle.getproduct.cap"
        self.assertEqual((view.loc[0, cap], view.loc[0, cap + FLAG]), (300, 0))
        self.assertEqual((view.loc[1, cap], view.loc[1, cap + FLAG]), (300, 1))
        self.assertEqual(view.loc[2, cap], 300)
        self.assertTrue(empty(view.loc[3, cap]))
        self.assertTrue(empty(view.loc[4, cap]))
        self.assertEqual(view.loc[6, "throttle.getcart.cap"], 300)
        self.assertTrue(empty(view.loc[7, "throttle.getcart.cap"]))

    def test_retryguard_observe_and_switches(self):
        (self.run / "retryguard.log").write_text("\n".join([
            f"{iso(1)}  OBSERVE  frontend->checkoutservice  rpr=0.5000  attempts=3  state=ON",
            f"{iso(2)}  frontend->checkoutservice  ON→OFF   rpr=2.10  metric=rpr_burst",
        ]), encoding="utf-8")
        view = self.view()
        self.assertEqual(view.loc[1, "rg.frontend->checkoutservice.rpr"], 0.5)
        self.assertEqual(view.loc[2, "rg.switches"], "frontend->checkoutservice ON→OFF")
        events = run_timeline.switch_events(self.run, CLOCK)
        self.assertEqual(events["hold_s"].iloc[0], 2.0)


if __name__ == "__main__":
    unittest.main()
