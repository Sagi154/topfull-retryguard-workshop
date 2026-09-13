"""test_estimate_service_mu.py — unit tests for offline μ / ρ estimator.

Run:
    python -m unittest experiments.test_estimate_service_mu -v
"""
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import estimate_service_mu as mu


def _in(ts, total, two=None, five=0):
    if two is None:
        two = total
    return {
        "timestamp": ts,
        "service": "cartservice",
        "total": str(total),
        "2xx": str(two),
        "4xx": "0",
        "5xx": str(five),
    }


class TestParseTimestamp(unittest.TestCase):
    def test_zulu(self):
        dt = mu.parse_timestamp("2026-09-13T13:52:10Z")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 13)
        self.assertEqual(dt.second, 10)


class TestDifferenceInbound(unittest.TestCase):
    def test_lambda_is_delta_total_over_dt(self):
        rows = [
            _in("2026-09-13T13:52:10Z", 100),
            _in("2026-09-13T13:52:11Z", 200),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0]["delta_total"], 100)
        self.assertEqual(ticks[0]["lambda_s"], 100.0)
        self.assertEqual(ticks[0]["dt_seconds"], 1.0)

    def test_skips_zero_delta_total(self):
        rows = [
            _in("2026-09-13T13:52:10Z", 100),
            _in("2026-09-13T13:52:11Z", 100),
            _in("2026-09-13T13:52:12Z", 130),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0]["delta_total"], 30)
        self.assertEqual(ticks[0]["timestamp"], "2026-09-13T13:52:12Z")

    def test_unsorted_input_is_sorted(self):
        rows = [
            _in("2026-09-13T13:52:11Z", 200),
            _in("2026-09-13T13:52:10Z", 100),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertEqual(ticks[0]["lambda_s"], 100.0)


def _tick(
    lambda_s,
    util,
    alpha=0.8,
    dtotal=100,
    d2xx=100,
    d5xx=0,
    dt=1.0,
    ts="2026-09-13T13:52:11Z",
):
    return mu.Tick(
        timestamp=ts,
        dt_seconds=dt,
        lambda_s=lambda_s,
        utilization=util,
        alpha=alpha,
        delta_total=dtotal,
        delta_2xx=d2xx,
        delta_5xx=d5xx,
    )


class TestSummarizeService(unittest.TestCase):
    def test_cpu_linear_util_half_lambda_100(self):
        est = mu.summarize_service("cartservice", [_tick(100.0, 0.5)])
        self.assertEqual(est.mu_cpu, 200.0)
        self.assertIsNone(est.mu_sat)
        self.assertEqual(est.rho_cpu_median, 0.5)
        self.assertEqual(est.inbound_5xx_fraction, 0.0)

    def test_zero_five_xx_means_no_sat_mu(self):
        ticks = [_tick(80.0, 0.4), _tick(90.0, 0.45)]
        est = mu.summarize_service("frontend", ticks)
        self.assertIsNone(est.mu_sat)

    def test_high_five_xx_uses_sat_mu(self):
        # Δ5xx/Δtotal = 10/100 = 0.10 >= 0.05; μ_sat = Δ2xx/Δt = 90
        est = mu.summarize_service(
            "checkoutservice",
            [_tick(100.0, 0.9, alpha=0.8, dtotal=100, d2xx=90, d5xx=10)],
        )
        self.assertEqual(est.mu_sat, 90.0)
        self.assertIsNone(est.mu_cpu)  # util 0.9 is not < alpha 0.8

    def test_prefer_sat_when_both_exist(self):
        ticks = [
            _tick(100.0, 0.5, dtotal=100, d2xx=100, d5xx=0),
            _tick(100.0, 0.5, dtotal=100, d2xx=80, d5xx=20),
        ]
        est = mu.summarize_service("adservice", ticks)
        self.assertEqual(est.mu_cpu, 200.0)
        self.assertEqual(est.mu_sat, 80.0)

    def test_no_unsaturated_ticks_is_na(self):
        est = mu.summarize_service("frontend", [_tick(100.0, 0.9, alpha=0.8)])
        self.assertIsNone(est.mu_cpu)
        self.assertEqual(est.util_peak, 0.9)


class TestJoinTicks(unittest.TestCase):
    def test_inner_join_on_timestamp(self):
        inbound = [
            _in("2026-09-13T13:52:10Z", 0),
            _in("2026-09-13T13:52:11Z", 100),
        ]
        detect = [
            {
                "timestamp": "2026-09-13T13:52:11Z",
                "service": "cartservice",
                "cadvisor_cpu": "500",
                "quota": "1000",
                "alpha": "0.8",
                "utilization": "0.5",
                "overloaded": "0",
            }
        ]
        ticks = mu.join_ticks(inbound, detect)
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0].lambda_s, 100.0)
        self.assertEqual(ticks[0].utilization, 0.5)
        self.assertEqual(ticks[0].alpha, 0.8)

    def test_skips_inbound_tick_without_detect(self):
        inbound = [
            _in("2026-09-13T13:52:10Z", 0),
            _in("2026-09-13T13:52:11Z", 100),
        ]
        ticks = mu.join_ticks(inbound, [])
        self.assertEqual(ticks, [])


def _write(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


class TestEstimateRun(unittest.TestCase):
    def test_missing_detect_errors_and_ignores_locust(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "getcart.csv").write_text(
                "RPS,Fail,Goodput\n10,10,0\n", encoding="utf-8"
            )
            _write(
                d / "service_inbound.csv",
                ["timestamp", "service", "total", "2xx", "4xx", "5xx"],
                [
                    {
                        "timestamp": "2026-09-13T13:52:10Z",
                        "service": "cartservice",
                        "total": "100",
                        "2xx": "100",
                        "4xx": "0",
                        "5xx": "0",
                    }
                ],
            )
            with self.assertRaises(mu.MissingDetectError):
                mu.estimate_run(d)

    def test_folder_with_both_csvs(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write(
                d / "service_inbound.csv",
                ["timestamp", "service", "total", "2xx", "4xx", "5xx"],
                [
                    {
                        "timestamp": "2026-09-13T13:52:10Z",
                        "service": "cartservice",
                        "total": "0",
                        "2xx": "0",
                        "4xx": "0",
                        "5xx": "0",
                    },
                    {
                        "timestamp": "2026-09-13T13:52:11Z",
                        "service": "cartservice",
                        "total": "100",
                        "2xx": "100",
                        "4xx": "0",
                        "5xx": "0",
                    },
                ],
            )
            _write(
                d / "topfull_detect.csv",
                [
                    "timestamp",
                    "service",
                    "cadvisor_cpu",
                    "quota",
                    "alpha",
                    "utilization",
                    "overloaded",
                ],
                [
                    {
                        "timestamp": "2026-09-13T13:52:11Z",
                        "service": "cartservice",
                        "cadvisor_cpu": "500",
                        "quota": "1000",
                        "alpha": "0.8",
                        "utilization": "0.5",
                        "overloaded": "0",
                    }
                ],
            )
            estimates = mu.estimate_run(d)
            by_name = {e.service: e for e in estimates}
            self.assertEqual(by_name["cartservice"].mu_cpu, 200.0)
            self.assertIsNone(by_name["cartservice"].mu_sat)

    def test_format_table_prints_na_for_sat(self):
        est = mu.ServiceEstimate(
            "cartservice", 100.0, 0.5, 200.0, None, 0.5, 0.0
        )
        text = mu.format_table([est])
        self.assertIn("cartservice", text)
        self.assertIn("n/a", text)
        self.assertNotIn("getcart", text)


class TestMain(unittest.TestCase):
    def test_usage_exit_2(self):
        self.assertEqual(mu.main([]), 2)
        self.assertEqual(mu.main(["estimate_service_mu.py"]), 2)


if __name__ == "__main__":
    unittest.main()
