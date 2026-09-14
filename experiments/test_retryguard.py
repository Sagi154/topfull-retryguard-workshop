"""
test_retryguard.py — Unit tests for the pure-logic parts of retryguard.py
(Algorithm 1 state machine + inbound measure_value() + 9-service allow-list).
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


INBOUND_FIELDS = ["timestamp", "service", "total", "2xx", "4xx", "5xx", "resets"]


def _write_inbound(path: Path, rows):
    """rows: iterable of dicts with INBOUND_FIELDS keys."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(ts, service, total, five_xx, four_xx=0, two_xx=0, resets=0):
    return {
        "timestamp": ts,
        "service": service,
        "total": total,
        "2xx": two_xx,
        "4xx": four_xx,
        "5xx": five_xx,
        "resets": resets,
    }


class TestControlledServices(unittest.TestCase):
    def test_includes_paymentservice_and_the_eight_other_backends(self):
        expected = (
            "adservice",
            "cartservice",
            "checkoutservice",
            "currencyservice",
            "emailservice",
            "paymentservice",
            "productcatalogservice",
            "recommendationservice",
            "shippingservice",
        )
        self.assertEqual(retryguard.CONTROLLED_SERVICES, expected)

    def test_excludes_frontend_and_redis_cart(self):
        self.assertNotIn("frontend", retryguard.CONTROLLED_SERVICES)
        self.assertNotIn("redis-cart", retryguard.CONTROLLED_SERVICES)


class TestReadLatestInboundRow(unittest.TestCase):
    def test_returns_newest_row_for_that_service_only(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-10T18:30:01Z", "checkoutservice", 100, 10),
                    _row("2026-09-10T18:30:01Z", "paymentservice", 50, 40),
                    _row("2026-09-10T18:30:02Z", "checkoutservice", 180, 40),
                ],
            )
            snap = retryguard.read_latest_inbound_row(path, "checkoutservice")
            self.assertEqual(snap.timestamp, "2026-09-10T18:30:02Z")
            self.assertEqual(snap.total, 180.0)
            self.assertEqual(snap.five_xx, 40.0)

    def test_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            self.assertIsNone(
                retryguard.read_latest_inbound_row(path, "checkoutservice")
            )

    def test_service_absent_from_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path, [_row("2026-09-10T18:30:01Z", "cartservice", 10, 0)]
            )
            self.assertIsNone(
                retryguard.read_latest_inbound_row(path, "paymentservice")
            )


class TestMeasureInboundRejection(unittest.TestCase):
    def test_delta_5xx_over_delta_total(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:02Z", 200.0, 30.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertAlmostEqual(rate, 0.20)
        self.assertEqual(new_prev, curr)

    def test_zero_delta_total_is_zero_not_none(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:02Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertEqual(rate, 0.0)
        self.assertEqual(new_prev, curr)

    def test_same_timestamp_does_not_double_count(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, prev)

    def test_first_row_stores_and_skips(self):
        curr = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(None, curr)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, curr)

    def test_missing_current_skips_and_keeps_previous(self):
        prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 10.0)
        rate, new_prev = retryguard.measure_inbound_rejection(prev, None)
        self.assertIsNone(rate)
        self.assertEqual(new_prev, prev)

    def test_four_xx_does_not_enter_the_formula(self):
        """4xx lives on the CSV row but must not affect Failures."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-10T18:30:01Z", "paymentservice", 100, 0, four_xx=50),
                    _row("2026-09-10T18:30:02Z", "paymentservice", 200, 0, four_xx=90),
                ],
            )
            first = retryguard.read_latest_inbound_row(path, "paymentservice")
            # After only the latest row exists in-file, reconstruct the
            # previous snapshot the controller would have stored at t1.
            prev = retryguard.InboundSnapshot("2026-09-10T18:30:01Z", 100.0, 0.0)
            rate, _ = retryguard.measure_inbound_rejection(prev, first)
            self.assertEqual(rate, 0.0)

    def test_resets_counted_as_failures(self):
        """Δresets alone (no 5xx) should produce a non-zero failure rate."""
        prev = retryguard.InboundSnapshot(
            "2026-09-14T18:30:01Z", total=100.0, five_xx=0.0, resets=5.0
        )
        curr = retryguard.InboundSnapshot(
            "2026-09-14T18:30:02Z", total=200.0, five_xx=0.0, resets=25.0
        )
        rate, new_prev = retryguard.measure_inbound_rejection(prev, curr)
        # Δresets=20, Δtotal=100 → 20/100 = 0.20
        self.assertAlmostEqual(rate, 0.20)
        self.assertEqual(new_prev, curr)

    def test_resets_and_five_xx_summed(self):
        """Δ5xx and Δresets are summed before dividing by Δtotal."""
        prev = retryguard.InboundSnapshot(
            "2026-09-14T18:30:01Z", total=100.0, five_xx=5.0, resets=5.0
        )
        curr = retryguard.InboundSnapshot(
            "2026-09-14T18:30:02Z", total=200.0, five_xx=15.0, resets=15.0
        )
        rate, _ = retryguard.measure_inbound_rejection(prev, curr)
        # Δ5xx=10, Δresets=10, Δtotal=100 → 20/100 = 0.20
        self.assertAlmostEqual(rate, 0.20)


class TestApplyAlgorithm1Symmetric(unittest.TestCase):
    """
    Paper Algorithm 1 uses ONE Interval for both transitions:
        13: if Consecutive_low >= Interval then Retries <- ON
        14: else if Consecutive_high >= Interval then Retries <- OFF
    apply_algorithm1 must take a single `interval` argument applied
    symmetrically to both directions.
    """

    def _state(self, initial="ON"):
        state = retryguard.ServiceState()
        state.retries_state = initial
        return state

    def test_no_transition_below_interval_low(self):
        state = self._state(initial="OFF")
        for _ in range(2):
            result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_low, 2)

    def test_turns_on_after_interval_consecutive_low_samples(self):
        state = self._state(initial="OFF")
        result = None
        for _ in range(3):
            result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)
        self.assertEqual(result, "ON")

    def test_turns_off_after_interval_consecutive_high_samples(self):
        state = self._state(initial="ON")
        result = None
        for _ in range(3):
            result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        self.assertEqual(result, "OFF")

    def test_same_interval_value_governs_both_directions(self):
        # A single dip resets the high-streak (paper lines 9-10), so with
        # interval=2, two highs then one low then two highs never reaches 2
        # consecutive highs until the streak restarts cleanly.
        state = self._state(initial="ON")
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=2)  # high=1
        result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=2)  # resets to low=1
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 0)
        self.assertEqual(state.consecutive_low, 1)

    def test_single_dip_resets_consecutive_high_streak(self):
        state = self._state(initial="ON")
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=1
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=2
        retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)  # dip -> high resets to 0
        result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=1 again
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 1)

    def test_no_repeat_transition_once_already_in_target_state(self):
        state = self._state(initial="OFF")
        for _ in range(3):
            retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        # already OFF and still above threshold: no further transition fires
        result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        self.assertIsNone(result)


class TestLoadParamsRequiredKeys(unittest.TestCase):
    def test_new_param_names_are_required(self):
        self.assertIn("sample_interval_seconds", retryguard.REQUIRED_PARAMS)
        self.assertIn("interval_samples", retryguard.REQUIRED_PARAMS)
        self.assertIn("per_try_timeout_ms", retryguard.REQUIRED_PARAMS)

    def test_old_param_names_are_no_longer_required(self):
        self.assertNotIn("window_duration_seconds", retryguard.REQUIRED_PARAMS)
        self.assertNotIn("disable_windows", retryguard.REQUIRED_PARAMS)
        self.assertNotIn("re_enable_windows", retryguard.REQUIRED_PARAMS)

    def test_load_params_rejects_missing_new_keys(self):
        import json
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            params_path = Path(tmp) / "params.json"
            with open(params_path, "w") as f:
                json.dump(
                    {
                        "rejection_threshold": 0.2,
                        "retry_attempts_on": 3,
                        "retry_attempts_off": 0,
                        # sample_interval_seconds, interval_samples, per_try_timeout_ms deliberately missing
                    },
                    f,
                )
            with self.assertRaises(SystemExit):
                retryguard.load_params(str(params_path))

    def test_load_params_rejects_missing_per_try_timeout_ms(self):
        import json
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            params_path = Path(tmp) / "params.json"
            with open(params_path, "w") as f:
                json.dump(
                    {
                        "rejection_threshold": 0.2,
                        "sample_interval_seconds": 1,
                        "interval_samples": 30,
                        "retry_attempts_on": 3,
                        "retry_attempts_off": 0,
                        # per_try_timeout_ms deliberately missing
                    },
                    f,
                )
            with self.assertRaises(SystemExit):
                retryguard.load_params(str(params_path))


class TestWaitForInboundCsv(unittest.TestCase):
    def test_returns_immediately_when_file_has_a_data_row(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            _write_inbound(
                record_path / retryguard.INBOUND_CSV_NAME,
                [_row("2026-09-10T18:30:01Z", "checkoutservice", 10, 1)],
            )
            retryguard.wait_for_inbound_csv(
                record_path, timeout_seconds=0.2, poll_seconds=0.05
            )

    def test_times_out_when_file_missing(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                retryguard.wait_for_inbound_csv(
                    Path(tmp), timeout_seconds=0.15, poll_seconds=0.05
                )


class TestLocustReaderRemoved(unittest.TestCase):
    def test_locust_helpers_and_endpoint_map_are_gone(self):
        self.assertFalse(hasattr(retryguard, "ENDPOINT_SERVICE_MAP"))
        self.assertFalse(hasattr(retryguard, "read_rejection_rate"))
        self.assertFalse(hasattr(retryguard, "service_rejection_rate"))
        self.assertFalse(hasattr(retryguard, "service_endpoint_map"))
        self.assertFalse(hasattr(retryguard, "wait_for_csvs"))


if __name__ == "__main__":
    unittest.main()

