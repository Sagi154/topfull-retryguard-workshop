"""Unit tests for rho_frozen_report.py."""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rho_frozen_report as rpt


def _write_csv(path: Path, fields, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


class TestLocustRpsMean(unittest.TestCase):
    def test_mean_of_rps_column(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            _write_csv(
                d / "total.csv",
                ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                [
                    {"RPS": "0.0", "Fail": "0", "Goodput": "0",
                     "Latency95": "0", "Latency99": "0"},
                    {"RPS": "100.0", "Fail": "0", "Goodput": "100",
                     "Latency95": "0", "Latency99": "0"},
                    {"RPS": "200.0", "Fail": "0", "Goodput": "200",
                     "Latency95": "0", "Latency99": "0"},
                ],
            )
            self.assertAlmostEqual(rpt.locust_rps_mean(d), 100.0)

    def test_missing_file_is_none(self):
        with TemporaryDirectory() as raw:
            self.assertIsNone(rpt.locust_rps_mean(Path(raw)))


class TestBackendOfferedLambda(unittest.TestCase):
    def test_sums_callers_and_subtracts_retry(self):
        """Envoy total includes retries; first-attempt = Δtotal − Δretry."""
        with TemporaryDirectory() as raw:
            d = Path(raw)
            fields = ["timestamp", "caller", "target", "total", "2xx", "4xx",
                      "5xx", "retry"]
            _write_csv(
                d / "service_edges.csv",
                fields,
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "cartservice",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "80", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "10"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "cartservice",
                     "target": "checkoutservice", "total": "30", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "cartservice", "total": "999", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            lam, retry, err = rpt.backend_offered_lambda(d, "checkoutservice")
            self.assertIsNone(err)
            # summed Δtotal = 110, Δretry = 10, dt = 1 -> first-attempt 100
            self.assertAlmostEqual(lam, 100.0)
            self.assertAlmostEqual(retry, 10.0)

    def test_missing_edges_has_reason(self):
        with TemporaryDirectory() as raw:
            lam, retry, err = rpt.backend_offered_lambda(
                Path(raw), "checkoutservice"
            )
            self.assertIsNone(lam)
            self.assertIn("service_edges.csv", err)
