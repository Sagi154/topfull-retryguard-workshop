"""test_estimate_service_mu.py — unit tests for the offline lambda/W/mu_sat
per-service estimator.

Corrected 2026-09-16: estimator read only service_inbound.csv (lambda from
total, W from rq_time_sum_ms/rq_time_count); the old CPU-linear "mu_cpu"
estimator (topfull_detect.csv utilization) was removed.

Corrected-again 2026-09-17 (see
docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md): the
2026-09-16 `mu_hat_w = lambda + 1/W` / `rho_w` estimator was removed too —
it is circular by construction (solving `W = 1/(mu-lambda)` for `mu` can
only return a value just above the observed `lambda`). This script now
reports only `lambda_mean`, `w_mean_ms`/`w_p50_ms` (a latency observation,
not a capacity stand-in), and `mu_sat` (an independent, sparse,
saturation-based capacity signal). These tests reflect that: no test
asserts a `mu_hat_w`/`rho_w` value.

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


def _in(ts, total, two=None, five=0, rq_sum=None, rq_count=None):
    if two is None:
        two = total
    row = {
        "timestamp": ts,
        "service": "cartservice",
        "total": str(total),
        "2xx": str(two),
        "4xx": "0",
        "5xx": str(five),
    }
    if rq_sum is not None:
        row["rq_time_sum_ms"] = str(rq_sum)
    if rq_count is not None:
        row["rq_time_count"] = str(rq_count)
    return row


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

    def test_no_latency_columns_gives_none_w(self):
        rows = [
            _in("2026-09-13T13:52:10Z", 0),
            _in("2026-09-13T13:52:11Z", 100),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertFalse(ticks[0]["has_latency_cols"])
        self.assertIsNone(ticks[0]["w_seconds"])

    def test_latency_columns_give_w_seconds(self):
        # Delta rq_time_sum_ms = 500, delta rq_time_count = 100 -> W = 5ms = 0.005s
        rows = [
            _in("2026-09-13T13:52:10Z", 0, rq_sum=0, rq_count=0),
            _in("2026-09-13T13:52:11Z", 100, rq_sum=500, rq_count=100),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertTrue(ticks[0]["has_latency_cols"])
        self.assertAlmostEqual(ticks[0]["w_seconds"], 0.005)

    def test_zero_delta_count_gives_none_w(self):
        rows = [
            _in("2026-09-13T13:52:10Z", 0, rq_sum=0, rq_count=0),
            _in("2026-09-13T13:52:11Z", 100, rq_sum=0, rq_count=0),
        ]
        ticks = mu.difference_inbound(rows)
        self.assertTrue(ticks[0]["has_latency_cols"])
        self.assertIsNone(ticks[0]["w_seconds"])


def _tick(lambda_s, w_seconds, dtotal=100, d2xx=100, d5xx=0, dt=1.0,
          ts="2026-09-13T13:52:11Z", has_latency_cols=True):
    return mu.Tick(
        timestamp=ts,
        dt_seconds=dt,
        lambda_s=lambda_s,
        delta_total=dtotal,
        delta_2xx=d2xx,
        delta_5xx=d5xx,
        has_latency_cols=has_latency_cols,
        w_seconds=w_seconds,
    )


class TestTickFiveXxFraction(unittest.TestCase):
    def test_fraction_computed_from_deltas(self):
        t = _tick(80.0, 0.02, dtotal=100, d5xx=10)
        self.assertAlmostEqual(t.five_xx_fraction, 0.10)

    def test_zero_when_no_total(self):
        t = _tick(0.0, None, dtotal=0)
        self.assertEqual(t.five_xx_fraction, 0.0)


class TestSummarizeService(unittest.TestCase):
    def test_lambda_and_w_from_single_tick(self):
        # lambda=80, W=0.02s (20ms)
        est = mu.summarize_service("cartservice", [_tick(80.0, 0.02)])
        self.assertAlmostEqual(est.lambda_mean, 80.0)
        self.assertAlmostEqual(est.w_mean_ms, 20.0)
        self.assertIsNone(est.mu_sat)
        self.assertEqual(est.n_ticks_with_latency, 1)
        self.assertIsNone(est.note)

    def test_w_mean_averages_multiple_ticks(self):
        ticks = [_tick(80.0, 0.02), _tick(80.0, 0.01)]  # 20ms, 10ms
        est = mu.summarize_service("frontend", ticks)
        self.assertAlmostEqual(est.w_mean_ms, 15.0)

    def test_no_latency_columns_at_all_is_explicit_gap(self):
        ticks = [_tick(80.0, None, has_latency_cols=False)]
        est = mu.summarize_service("frontend", ticks)
        self.assertIsNone(est.w_mean_ms)
        self.assertEqual(est.n_ticks_with_latency, 0)
        self.assertEqual(est.note, mu.NO_LATENCY_COLUMNS_NOTE)

    def test_latency_columns_present_but_all_zero_count(self):
        ticks = [_tick(80.0, None, has_latency_cols=True)]
        est = mu.summarize_service("frontend", ticks)
        self.assertIsNone(est.w_mean_ms)
        self.assertEqual(est.note, mu.NO_LATENCY_TICKS_NOTE)

    def test_high_five_xx_uses_sat_mu_independent_of_latency(self):
        # Delta5xx/Deltatotal = 10/100 = 0.10 >= 0.05; mu_sat = Delta2xx/Deltat = 90
        est = mu.summarize_service(
            "checkoutservice",
            [_tick(100.0, 0.01, dtotal=100, d2xx=90, d5xx=10)],
        )
        self.assertEqual(est.mu_sat, 90.0)
        # w_mean_ms still computed independently of mu_sat.
        self.assertAlmostEqual(est.w_mean_ms, 10.0)

    def test_zero_five_xx_means_no_sat_mu(self):
        ticks = [_tick(80.0, 0.02), _tick(90.0, 0.02)]
        est = mu.summarize_service("frontend", ticks)
        self.assertIsNone(est.mu_sat)

    def test_no_ticks_at_all(self):
        est = mu.summarize_service("frontend", [])
        self.assertIsNone(est.lambda_mean)
        self.assertIsNone(est.w_mean_ms)
        self.assertIsNone(est.mu_sat)
        self.assertEqual(est.n_ticks_with_latency, 0)
        self.assertEqual(est.note, "no ticks with traffic")


def _write(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


class TestEstimateRun(unittest.TestCase):
    def test_missing_inbound_raises(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            with self.assertRaises(mu.MissingInboundError):
                mu.estimate_run(d)

    def test_does_not_require_topfull_detect_csv(self):
        """The estimator does not read topfull_detect.csv at all."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write(
                d / "service_inbound.csv",
                ["timestamp", "service", "total", "2xx", "4xx", "5xx",
                 "rq_time_sum_ms", "rq_time_count"],
                [
                    {"timestamp": "2026-09-13T13:52:10Z", "service": "cartservice",
                     "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                     "rq_time_sum_ms": "0", "rq_time_count": "0"},
                    {"timestamp": "2026-09-13T13:52:11Z", "service": "cartservice",
                     "total": "100", "2xx": "100", "4xx": "0", "5xx": "0",
                     "rq_time_sum_ms": "2000", "rq_time_count": "100"},
                ],
            )
            # No topfull_detect.csv written at all -- must not raise / not needed.
            estimates = mu.estimate_run(d)
            by_name = {e.service: e for e in estimates}
            # W = 2000ms/100 = 20ms; lambda = 100
            self.assertAlmostEqual(by_name["cartservice"].lambda_mean, 100.0)
            self.assertAlmostEqual(by_name["cartservice"].w_mean_ms, 20.0)

    def test_folder_without_latency_columns_reports_gap(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write(
                d / "service_inbound.csv",
                ["timestamp", "service", "total", "2xx", "4xx", "5xx"],
                [
                    {"timestamp": "2026-09-13T13:52:10Z", "service": "cartservice",
                     "total": "0", "2xx": "0", "4xx": "0", "5xx": "0"},
                    {"timestamp": "2026-09-13T13:52:11Z", "service": "cartservice",
                     "total": "100", "2xx": "100", "4xx": "0", "5xx": "0"},
                ],
            )
            estimates = mu.estimate_run(d)
            self.assertEqual(len(estimates), 1)
            self.assertIsNone(estimates[0].w_mean_ms)
            self.assertEqual(estimates[0].note, mu.NO_LATENCY_COLUMNS_NOTE)

    def test_format_table_prints_na_and_notes(self):
        est = mu.ServiceEstimate(
            "cartservice", 100.0, None, None, 0, 0.0,
            note=mu.NO_LATENCY_COLUMNS_NOTE,
        )
        text = mu.format_table([est])
        self.assertIn("cartservice", text)
        self.assertIn("n/a", text)
        self.assertIn("Notes:", text)
        self.assertIn(mu.NO_LATENCY_COLUMNS_NOTE, text)
        self.assertIn("w_p50_ms", text)
        self.assertNotIn("mu_hat_w", text)
        self.assertNotIn("rho_w", text)


class TestHistogramPercentile(unittest.TestCase):
    def test_p50_interpolates_within_bucket(self):
        # 100 samples: 40 under 10ms, 100 under 50ms -> P50 is in [10, 50]
        buckets = {"10": 40, "50": 100, "+Inf": 100}
        p50 = mu.histogram_percentile(0.50, buckets)
        self.assertIsNotNone(p50)
        # rank=50; prev_le=10,prev_count=40; le=50,count=100
        # frac=(50-40)/(100-40)=10/60; p50=10+10/60*40 ≈ 16.667
        self.assertAlmostEqual(p50, 10.0 + (10.0 / 60.0) * 40.0, places=5)

    def test_empty_or_zero_returns_none(self):
        self.assertIsNone(mu.histogram_percentile(0.5, {}))
        self.assertIsNone(mu.histogram_percentile(0.5, {"10": 0, "+Inf": 0}))

    def test_delta_buckets_and_p50_from_rows(self):
        import json
        import tempfile
        from pathlib import Path

        b0 = {"10": 0, "50": 0, "+Inf": 0}
        b1 = {"10": 40, "50": 100, "+Inf": 100}
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            with open(d / "service_inbound.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp", "service", "total", "2xx", "4xx", "5xx",
                        "resets", "rq_time_sum_ms", "rq_time_count", "rq_time_buckets",
                    ],
                )
                w.writeheader()
                w.writerow({
                    "timestamp": "2026-09-16T12:00:00Z", "service": "frontend",
                    "total": "0", "2xx": "0", "4xx": "0", "5xx": "0", "resets": "0",
                    "rq_time_sum_ms": "0", "rq_time_count": "0",
                    "rq_time_buckets": json.dumps(b0),
                })
                w.writerow({
                    "timestamp": "2026-09-16T12:00:01Z", "service": "frontend",
                    "total": "100", "2xx": "100", "4xx": "0", "5xx": "0", "resets": "0",
                    # mean W = 2000/100 = 20ms
                    "rq_time_sum_ms": "2000", "rq_time_count": "100",
                    "rq_time_buckets": json.dumps(b1),
                })
            estimates = mu.estimate_run(d)
            self.assertEqual(len(estimates), 1)
            self.assertIsNotNone(estimates[0].w_p50_ms)
            self.assertAlmostEqual(
                estimates[0].w_p50_ms,
                10.0 + (10.0 / 60.0) * 40.0,
                places=5,
            )


class TestMain(unittest.TestCase):
    def test_usage_exit_2(self):
        self.assertEqual(mu.main([]), 2)
        self.assertEqual(mu.main(["estimate_service_mu.py"]), 2)


if __name__ == "__main__":
    unittest.main()
