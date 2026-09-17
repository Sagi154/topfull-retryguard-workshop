"""Unit tests for rho_frozen_report.py."""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capacity_frozen as cf
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


def _calibrated_checkout(mu_per_m: float = 0.5, at_m: int = 100) -> cf.FrozenTable:
    table = cf.empty_table()
    table.capacities["checkoutservice"] = cf.FrozenEntry(
        service="checkoutservice",
        mu_per_millicore=mu_per_m,
        calibrated_at_cpu_limit_millicores=at_m,
        calibrated_at_replica_count=1,
        throughput_at_calibration=mu_per_m * at_m,
        method=cf.METHOD_MU_SAT,
        source_run="/tmp/cal",
        n_sat_ticks=12,
    )
    return table


class TestMuThisRun(unittest.TestCase):
    def test_rescale_100m_to_1000m(self):
        entry = _calibrated_checkout().capacities["checkoutservice"]
        self.assertAlmostEqual(rpt.mu_this_run(entry, 100, 1), 50.0)
        self.assertAlmostEqual(rpt.mu_this_run(entry, 1000, 1), 500.0)


class TestEvaluateRun(unittest.TestCase):
    def test_rho_hat_uses_rescaled_mu(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 1000,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            _write_csv(
                d / "service_edges.csv",
                ["timestamp", "caller", "target", "total", "2xx", "4xx",
                 "5xx", "retry"],
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "200", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            _write_csv(
                d / "total.csv",
                ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                [{"RPS": "10", "Fail": "0", "Goodput": "10",
                  "Latency95": "0", "Latency99": "0"}],
            )
            rows, warnings = rpt.evaluate_run(d, _calibrated_checkout())
            by = {r.service: r for r in rows}
            chk = by["checkoutservice"]
            self.assertAlmostEqual(chk.lambda_offered, 200.0)
            self.assertAlmostEqual(chk.mu_this_run, 500.0)
            self.assertAlmostEqual(chk.rho_hat, 200.0 / 500.0)
            self.assertEqual(chk.cpu_limit_millicores, 1000)
            self.assertEqual(chk.calibrated_at_cpu_limit_millicores, 100)
            self.assertTrue(any("millicore" in w.lower() for w in chk.warnings))
            self.assertIsNone(by["frontend"].rho_hat)
            self.assertEqual(by["frontend"].na_reason, "not_yet_calibrated")
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r.service in cf.MINIMUM_SERVICES for r in rows))

    def test_cluster_shape_mismatch_raises(self):
        with TemporaryDirectory() as raw:
            table = cf.empty_table("topfull-worker-1=e2-standard-8")
            with self.assertRaises(cf.FrozenCapacityError):
                rpt.evaluate_run(
                    Path(raw), table, cluster_shape=cf.DEFAULT_CLUSTER_SHAPE
                )

    def test_missing_service_capacity_is_na_not_quota_fallback(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "run_manifest.json").write_text(
                json.dumps({"effective_cpu_quotas": {"checkoutservice": 1000}}),
                encoding="utf-8",
            )
            rows, _ = rpt.evaluate_run(d, _calibrated_checkout())
            chk = {r.service: r for r in rows}["checkoutservice"]
            self.assertIsNone(chk.rho_hat)
            self.assertIn("service_capacity.json", chk.na_reason)

    def test_quota_disagreement_warns_but_uses_k8s(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 100,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            (d / "run_manifest.json").write_text(
                json.dumps({"effective_cpu_quotas": {"checkoutservice": 1000}}),
                encoding="utf-8",
            )
            _write_csv(
                d / "service_edges.csv",
                ["timestamp", "caller", "target", "total", "2xx", "4xx",
                 "5xx", "retry"],
                [
                    {"timestamp": "2026-09-17T00:00:00Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "0", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                    {"timestamp": "2026-09-17T00:00:01Z", "caller": "frontend",
                     "target": "checkoutservice", "total": "10", "2xx": "0",
                     "4xx": "0", "5xx": "0", "retry": "0"},
                ],
            )
            rows, _ = rpt.evaluate_run(d, _calibrated_checkout())
            chk = {r.service: r for r in rows}["checkoutservice"]
            self.assertEqual(chk.cpu_limit_millicores, 100)
            self.assertAlmostEqual(chk.mu_this_run, 50.0)
            self.assertTrue(any("effective_cpu_quotas" in w for w in chk.warnings))

    def test_generate_report_writes_md_and_json(self):
        with TemporaryDirectory() as raw:
            d = Path(raw)
            table_path = d / "capacity_frozen.json"
            cf.save_table(_calibrated_checkout(), table_path)
            (d / "service_capacity.json").write_text(
                json.dumps({
                    "checkoutservice": {
                        "cpu_limit_millicores": 100,
                        "replica_count": 1,
                    }
                }),
                encoding="utf-8",
            )
            md = rpt.generate_report(d, table_path=table_path)
            self.assertTrue(md.is_file())
            text = md.read_text(encoding="utf-8")
            self.assertIn("rho_hat", text)
            self.assertIn("checkoutservice", text)
            self.assertNotIn("cartservice", text)
            self.assertIn("supplementary", text.lower())
            payload = json.loads((d / "rho_frozen_report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["rows"]), 4)
