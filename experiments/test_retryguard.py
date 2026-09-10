"""
test_retryguard.py — Unit tests for the pure-logic parts of retryguard.py
(Algorithm 1 state machine + raw single-sample rejection-rate reader).
No network/K8s access; retryguard.py's `kubernetes` import is stubbed out
because the `kubernetes` package is not installed in this dev environment
and is never exercised by these tests.

Run:
    python -m unittest experiments.test_retryguard -v
"""
import csv
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

# --- Stub the kubernetes package before importing retryguard --------------- #
# retryguard.py does `import kubernetes`, `from kubernetes import client,
# config`, and `from kubernetes.client.rest import ApiException` at module
# scope. None of these are exercised by the tests below (they only cover
# metric-reading and the Algorithm 1 state machine), so a minimal stub is
# enough to let the module import.
if "kubernetes" not in sys.modules:
    kubernetes_stub = types.ModuleType("kubernetes")
    client_stub = types.ModuleType("kubernetes.client")
    client_rest_stub = types.ModuleType("kubernetes.client.rest")

    class _CustomObjectsApi:  # pragma: no cover - not exercised by these tests
        pass

    class _ConfigException(Exception):
        pass

    class _ApiException(Exception):
        def __init__(self, status=0, reason=""):
            super().__init__(reason)
            self.status = status
            self.reason = reason

    client_stub.CustomObjectsApi = _CustomObjectsApi
    client_rest_stub.ApiException = _ApiException
    config_stub = types.ModuleType("kubernetes.config")
    config_stub.ConfigException = _ConfigException
    config_stub.load_kube_config = lambda: None
    config_stub.load_incluster_config = lambda: None

    kubernetes_stub.client = client_stub
    kubernetes_stub.config = config_stub

    sys.modules["kubernetes"] = kubernetes_stub
    sys.modules["kubernetes.client"] = client_stub
    sys.modules["kubernetes.client.rest"] = client_rest_stub
    sys.modules["kubernetes.config"] = config_stub

import retryguard  # noqa: E402  (import after sys.modules stubbing above)


def _write_csv(path: Path, rows):
    """rows: list of (rps, fail) tuples. Writes a metric_collector-style CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["RPS", "Fail"])
        writer.writeheader()
        for rps, fail in rows:
            writer.writerow({"RPS": rps, "Fail": fail})


class TestReadRejectionRateSingleSample(unittest.TestCase):
    """
    Paper Algorithm 1's measure_value() reads one raw sample per iteration —
    no averaging. read_rejection_rate must therefore return the rejection
    rate of only the LATEST CSV row, regardless of how many rows precede it.
    """

    def test_returns_latest_row_rejection_rate_ignoring_earlier_rows(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            # Earlier rows are 100% rejection; latest row is 10% — if this
            # were averaged over multiple rows the result would be > 0.10.
            _write_csv(csv_path, [(100, 100), (100, 100), (100, 10)])
            rate = retryguard.read_rejection_rate(csv_path)
            self.assertAlmostEqual(rate, 0.10)

    def test_zero_rps_row_contributes_zero_not_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            _write_csv(csv_path, [(100, 50), (0, 0)])
            rate = retryguard.read_rejection_rate(csv_path)
            self.assertEqual(rate, 0.0)

    def test_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "does_not_exist.csv"
            self.assertIsNone(retryguard.read_rejection_rate(csv_path))

    def test_empty_csv_returns_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            _write_csv(csv_path, [])
            self.assertIsNone(retryguard.read_rejection_rate(csv_path))


class TestServiceRejectionRateSingleSample(unittest.TestCase):
    """service_rejection_rate aggregates (max) across the endpoints mapped
    to one K8s service, each read as a single latest-row sample."""

    def test_takes_max_across_endpoints_latest_rows(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            _write_csv(record_path / "getcart.csv", [(100, 5)])       # 0.05
            _write_csv(record_path / "postcart.csv", [(100, 40)])     # 0.40
            _write_csv(record_path / "emptycart.csv", [(100, 10)])    # 0.10
            rate = retryguard.service_rejection_rate(
                "cartservice",
                ["getcart", "postcart", "emptycart"],
                record_path,
            )
            self.assertAlmostEqual(rate, 0.40)

    def test_missing_all_endpoint_csvs_returns_none(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            rate = retryguard.service_rejection_rate(
                "cartservice", ["getcart", "postcart", "emptycart"], record_path
            )
            self.assertIsNone(rate)


if __name__ == "__main__":
    unittest.main()
