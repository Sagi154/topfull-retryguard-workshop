"""test_rho_estimate_report.py — unit tests for the combined lambda/W/mu_sat
+ toggle-log report.

Corrected 2026-09-16: estimate_service_mu.py no longer reads
topfull_detect.csv. Corrected-again 2026-09-17 (see
docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md): the
mu_hat_w/rho_w fields were removed entirely (circular by construction —
see the design doc). Fixtures below write only service_inbound.csv, with
the rq_time_sum_ms/rq_time_count columns; assertions check for
lambda/w_mean_ms/mu_sat, not mu_hat_w/rho_w.

Run:
    python -m pytest experiments/test_rho_estimate_report.py -v
    (or)
    python -m unittest experiments.test_rho_estimate_report -v
"""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rho_estimate_report as report  # noqa: E402
import estimate_service_mu as mu  # noqa: E402


TOGGLE_LOG_TEXT = (
    "2026-09-15T20:15:33Z  START  threshold=0.20 sample_interval=1s "
    "interval_samples=30 (30s) services=['checkoutservice']\n"
    "2026-09-15T20:16:00Z  OBSERVE  checkoutservice  rejection=0.10  "
    "low=5 high=0  state=ON\n"
    "2026-09-15T20:16:57Z  checkoutservice  ON\u2192OFF   rejection=0.48  "
    "consecutive_high=30  attempts=0\n"
    "2026-09-15T20:17:28Z  checkoutservice  OFF\u2192ON   rejection=0.00  "
    "consecutive_low=30  attempts=3\n"
    "2026-09-15T20:20:00Z  EXIT\n"
)


def _write_csv(path: Path, fieldnames, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


INBOUND_FIELDS = ["timestamp", "service", "total", "2xx", "4xx", "5xx",
                   "rq_time_sum_ms", "rq_time_count"]


def _write_valid_inputs(d: Path) -> None:
    _write_csv(
        d / "service_inbound.csv",
        INBOUND_FIELDS,
        [
            {
                "timestamp": "2026-09-15T20:16:00Z",
                "service": "checkoutservice",
                "total": "0", "2xx": "0", "4xx": "0", "5xx": "0",
                "rq_time_sum_ms": "0", "rq_time_count": "0",
            },
            {
                "timestamp": "2026-09-15T20:16:01Z",
                "service": "checkoutservice",
                "total": "100", "2xx": "100", "4xx": "0", "5xx": "0",
                "rq_time_sum_ms": "2000", "rq_time_count": "100",
            },
        ],
    )


def _write_valid_inputs_no_latency_cols(d: Path) -> None:
    """Pre-2026-09-16 shape: service_inbound.csv without rq_time_* columns."""
    _write_csv(
        d / "service_inbound.csv",
        ["timestamp", "service", "total", "2xx", "4xx", "5xx"],
        [
            {"timestamp": "2026-09-15T20:16:00Z", "service": "checkoutservice",
             "total": "0", "2xx": "0", "4xx": "0", "5xx": "0"},
            {"timestamp": "2026-09-15T20:16:01Z", "service": "checkoutservice",
             "total": "100", "2xx": "100", "4xx": "0", "5xx": "0"},
        ],
    )


class TestParseRetryguardLog(unittest.TestCase):
    def test_extracts_toggle_events(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            log_path = d / "retryguard.log"
            log_path.write_text(TOGGLE_LOG_TEXT, encoding="utf-8")
            events = report.parse_retryguard_log(log_path)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["service"], "checkoutservice")
            self.assertEqual(events[0]["direction"], "ON\u2192OFF")
            self.assertAlmostEqual(events[0]["rejection"], 0.48)
            self.assertEqual(events[0]["counter"], "consecutive_high=30")
            self.assertEqual(events[0]["attempts"], 0)
            self.assertEqual(events[1]["direction"], "OFF\u2192ON")
            self.assertEqual(events[1]["attempts"], 3)

    def test_missing_file_returns_empty_list(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            events = report.parse_retryguard_log(d / "retryguard.log")
            self.assertEqual(events, [])

    def test_log_with_no_toggles_returns_empty_list(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            log_path = d / "retryguard.log"
            log_path.write_text(
                "2026-09-15T20:15:33Z  START  threshold=0.20\n"
                "2026-09-15T20:16:00Z  SKIP  frontend  no metric data this sample\n",
                encoding="utf-8",
            )
            events = report.parse_retryguard_log(log_path)
            self.assertEqual(events, [])


class TestComputeRhoEstimates(unittest.TestCase):
    def test_missing_inbound_reports_error_not_exception(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            estimates, err = report.compute_rho_estimates(d)
            self.assertIsNone(estimates)
            self.assertIn(mu.INBOUND_NAME, err)

    def test_valid_inputs_return_estimates(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs(d)
            estimates, err = report.compute_rho_estimates(d)
            self.assertIsNone(err)
            self.assertEqual(len(estimates), 1)
            self.assertEqual(estimates[0].service, "checkoutservice")
            # W = 2000ms/100 = 20ms; lambda=100
            self.assertAlmostEqual(estimates[0].w_mean_ms, 20.0)
            self.assertAlmostEqual(estimates[0].lambda_mean, 100.0)

    def test_no_topfull_detect_csv_needed_at_all(self):
        """The corrected estimator does not require topfull_detect.csv."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs(d)
            self.assertFalse((d / "topfull_detect.csv").exists())
            estimates, err = report.compute_rho_estimates(d)
            self.assertIsNone(err)
            self.assertEqual(len(estimates), 1)

    def test_missing_latency_columns_reports_note_not_error(self):
        """Pre-2026-09-16 folders: inbound CSV exists but lacks rq_time_* cols."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs_no_latency_cols(d)
            estimates, err = report.compute_rho_estimates(d)
            self.assertIsNone(err)
            self.assertEqual(len(estimates), 1)
            self.assertIsNone(estimates[0].w_mean_ms)
            self.assertEqual(estimates[0].note, mu.NO_LATENCY_COLUMNS_NOTE)


class TestGenerateReport(unittest.TestCase):
    def test_degrades_gracefully_with_no_inputs_at_all(self):
        """Folder with neither mesh CSV nor retryguard.log."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            md_path = report.generate_report(d)
            self.assertTrue(md_path.is_file())
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("Not computed", text)
            self.assertIn(mu.INBOUND_NAME, text)
            self.assertIn("No `retryguard.log`", text)
            json_path = d / report.REPORT_JSON_NAME
            self.assertTrue(json_path.is_file())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["retryguard_log_present"])
            self.assertEqual(payload["estimates"], [])
            self.assertIsNotNone(payload["estimate_error"])

    def test_degrades_gracefully_missing_retryguard_log_only(self):
        """Baseline-run shape: mesh CSV present, no retryguard.log."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs(d)
            md_path = report.generate_report(d)
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("checkoutservice", text)
            self.assertNotIn("Not computed", text)
            self.assertIn("No `retryguard.log`", text)

    def test_degrades_gracefully_missing_latency_columns_only(self):
        """Pre-2026-09-16 folder shape: estimates present, mu_hat_w n/a."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs_no_latency_cols(d)
            md_path = report.generate_report(d)
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("checkoutservice", text)
            self.assertIn(mu.NO_LATENCY_COLUMNS_NOTE, text)

    def test_full_run_with_toggles(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs(d)
            (d / "retryguard.log").write_text(TOGGLE_LOG_TEXT, encoding="utf-8")
            md_path = report.generate_report(d)
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("ON\u2192OFF", text)
            self.assertIn("OFF\u2192ON", text)
            self.assertIn("checkoutservice", text)
            self.assertIn("lambda_mean", text)
            self.assertNotIn("rho_w_median", text)
            payload = json.loads((d / report.REPORT_JSON_NAME).read_text(encoding="utf-8"))
            self.assertTrue(payload["retryguard_log_present"])
            self.assertEqual(len(payload["toggle_events"]), 2)

    def test_retryguard_log_present_but_no_toggles(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_valid_inputs(d)
            (d / "retryguard.log").write_text(
                "2026-09-15T20:15:33Z  START  threshold=0.20\n", encoding="utf-8"
            )
            md_path = report.generate_report(d)
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("never crossed its threshold", text)


if __name__ == "__main__":
    unittest.main()
