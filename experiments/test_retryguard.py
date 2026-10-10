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


class TestInboundCsvTailer(unittest.TestCase):
    def test_missing_file_is_a_noop(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(tailer.latest, {})

    def test_picks_up_rows_written_before_construction(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:00:00Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 100.0)

    def test_second_poll_only_advances_for_new_rows(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            offset_after_first = tailer._offset

            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
                writer.writerow(
                    _row("2026-09-15T10:00:01Z", "checkoutservice", 180, 40)
                )
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:00:01Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 180.0)
            self.assertGreater(tailer._offset, offset_after_first)

    def test_poll_with_no_new_bytes_is_a_true_noop(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            offset_after_first = tailer._offset
            snapshot_after_first = tailer.latest["checkoutservice"]

            tailer.poll()  # no new bytes appended
            self.assertEqual(tailer._offset, offset_after_first)
            self.assertEqual(tailer.latest["checkoutservice"], snapshot_after_first)

    def test_file_shrinking_triggers_a_full_resync(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10),
                    _row("2026-09-15T10:00:01Z", "checkoutservice", 180, 40),
                ],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].total, 180.0
            )

            # Simulate a collector restart recreating the file from scratch.
            _write_inbound(
                path,
                [_row("2026-09-15T10:05:00Z", "checkoutservice", 5, 0)],
            )
            tailer.poll()
            self.assertEqual(tailer._offset, path.stat().st_size)
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:05:00Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 5.0)

    def test_partial_trailing_line_is_buffered_and_completed_later(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()

            # Write a row without a trailing newline (writer mid-flush).
            with open(path, "a", newline="") as f:
                f.write("2026-09-15T10:00:01Z,checkoutservice,180,40,0,0,0")
            tailer.poll()
            # No newline yet -> not a complete row -> latest unchanged.
            self.assertEqual(tailer.latest["checkoutservice"].total, 100.0)

            with open(path, "a", newline="") as f:
                f.write("\n")
            tailer.poll()
            self.assertEqual(tailer.latest["checkoutservice"].total, 180.0)

    def test_multiple_services_interleaved_match_read_latest_inbound_row(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10),
                    _row("2026-09-15T10:00:00Z", "paymentservice", 50, 5),
                ],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()

            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
                writer.writerow(
                    _row("2026-09-15T10:00:01Z", "paymentservice", 90, 9)
                )
            tailer.poll()

            for service in ("checkoutservice", "paymentservice"):
                expected = retryguard.read_latest_inbound_row(path, service)
                self.assertEqual(tailer.latest[service], expected)


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
    Paper Algorithm 1 uses ONE Interval for both transitions. The interval
    is seconds from the first row of a streak to the newest row.
    """

    def setUp(self):
        self.clock = 0

    def _state(self, initial="ON"):
        state = retryguard.ServiceState()
        state.retries_state = initial
        return state

    def tick(self, state, value, threshold=0.20, interval=3, step=1):
        ts = retryguard.format_row_timestamp(self.clock)
        self.clock += step
        return retryguard.apply_algorithm1(
            state, value, threshold, interval, ts
        )

    def test_no_transition_below_interval_low(self):
        state = self._state(initial="OFF")
        for _ in range(2):
            result = self.tick(state, 0.05)
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_low, 2)

    def test_turns_on_when_row_span_reaches_interval(self):
        state = self._state(initial="OFF")
        result = None
        for _ in range(3):
            result = self.tick(state, 0.05)
            self.assertIsNone(result)
        result = self.tick(state, 0.05)
        self.assertEqual(result, "ON")

    def test_turns_off_when_row_span_reaches_interval(self):
        state = self._state(initial="ON")
        result = None
        for _ in range(3):
            result = self.tick(state, 0.50)
            self.assertIsNone(result)
        result = self.tick(state, 0.50)
        self.assertEqual(result, "OFF")

    def test_same_interval_value_governs_both_directions(self):
        state = self._state(initial="ON")
        self.tick(state, 0.50, interval=2)
        result = self.tick(state, 0.05, interval=2)
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 0)
        self.assertEqual(state.consecutive_low, 1)
        self.assertIsNone(state.high_since)

    def test_single_dip_resets_consecutive_high_streak(self):
        state = self._state(initial="ON")
        self.tick(state, 0.50)
        self.tick(state, 0.50)
        self.tick(state, 0.05)
        self.assertIsNone(state.high_since)
        result = self.tick(state, 0.50)
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 1)

    def test_no_repeat_transition_once_already_in_target_state(self):
        state = self._state(initial="OFF")
        for _ in range(4):
            self.tick(state, 0.50)
        result = self.tick(state, 0.50)
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


class TestVirtualServicePatchBody(unittest.TestCase):
    ROUTE = [{"destination": {"host": "checkoutservice"}}]

    def test_on_has_full_retry_policy(self):
        body = retryguard.build_vs_patch_body(self.ROUTE, 3, 500)
        rule = body["spec"]["http"][0]
        self.assertEqual(rule["route"], self.ROUTE)
        self.assertEqual(
            rule["retries"],
            {
                "attempts": 3,
                "retryOn": "5xx,reset,connect-failure",
                "perTryTimeout": "500ms",
            },
        )
        self.assertNotIn("timeout", rule)

    def test_off_keeps_a_route_timeout(self):
        # Istio's webhook rejects attempts: 0 with retryOn/perTryTimeout, and
        # omitting the block falls back to Istio's default of 2 retries.
        # The route timeout is what still turns a slow callee into a reset.
        body = retryguard.build_vs_patch_body(self.ROUTE, 0, 500)
        rule = body["spec"]["http"][0]
        self.assertEqual(rule["retries"], {"attempts": 0})
        self.assertEqual(rule["timeout"], "500ms")
        self.assertEqual(rule["route"], self.ROUTE)


class TestEdgeMeasurement(unittest.TestCase):
    def test_controlled_edges_shape(self):
        self.assertEqual(len(retryguard.CONTROLLED_EDGES), 14)
        for caller, target in retryguard.CONTROLLED_EDGES:
            self.assertIn(target, retryguard.CONTROLLED_SERVICES)
            self.assertNotEqual(caller, "redis-cart")

    def test_rpr_divides_by_first_attempts(self):
        S = retryguard.EdgeSnapshot
        prev = S("2026-01-01T00:00:00Z", total=100, retry=10)
        cur = S("2026-01-01T00:00:01Z", total=160, retry=30)
        # delta total 60, delta retry 20 -> first attempts 40 -> rpr 0.5
        rpr, _ = retryguard.measure_edge_rpr(prev, cur)
        self.assertAlmostEqual(rpr, 0.5)

    def test_no_first_attempts_is_skipped(self):
        S = retryguard.EdgeSnapshot
        prev = S("2026-01-01T00:00:00Z", total=100, retry=10)
        cur = S("2026-01-01T00:00:01Z", total=100, retry=10)
        rpr, _ = retryguard.measure_edge_rpr(prev, cur)
        self.assertIsNone(rpr)

    def test_tailer_keys_by_caller_and_target(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "service_edges.csv"
            p.write_text(
                "timestamp,caller,target,total,2xx,4xx,5xx,retry\n"
                "2026-01-01T00:00:00Z,frontend,adservice,10,10,0,0,2\n",
                encoding="utf-8",
            )
            t = retryguard.EdgesCsvTailer(p)
            t.poll()
            snap = t.latest[("frontend", "adservice")]
            self.assertEqual((snap.total, snap.retry), (10.0, 2.0))


class TestEdgePatchBody(unittest.TestCase):
    ROUTE = [{"destination": {"host": "productcatalogservice"}}]

    def test_off_callers_get_match_routes_before_default(self):
        body = retryguard.build_edge_vs_patch_body(
            self.ROUTE, {"frontend": 0, "checkoutservice": 0}, 3, 500
        )
        http = body["spec"]["http"]
        self.assertEqual(len(http), 3)
        self.assertEqual(
            http[0]["match"], [{"sourceLabels": {"app": "checkoutservice"}}]
        )
        self.assertEqual(http[1]["match"], [{"sourceLabels": {"app": "frontend"}}])
        self.assertEqual(http[0]["retries"], {"attempts": 0})
        self.assertEqual(http[0]["timeout"], "500ms")
        self.assertEqual(http[1]["timeout"], "500ms")
        self.assertNotIn("match", http[2])
        self.assertEqual(http[2]["retries"]["attempts"], 3)
        self.assertNotIn("timeout", http[2])
        self.assertEqual(http[2]["route"], self.ROUTE)

    def test_ramp_step_keeps_retry_policy(self):
        body = retryguard.build_edge_vs_patch_body(
            self.ROUTE, {"frontend": 1, "checkoutservice": 0}, 3, 500
        )
        http = body["spec"]["http"]
        self.assertEqual(http[0]["retries"], {"attempts": 0})
        self.assertEqual(http[0]["timeout"], "500ms")
        self.assertEqual(
            http[1]["retries"],
            {
                "attempts": 1,
                "retryOn": "5xx,reset,connect-failure",
                "perTryTimeout": "500ms",
            },
        )
        self.assertNotIn("timeout", http[1])
        self.assertEqual(http[2]["retries"]["attempts"], 3)
        self.assertNotIn("timeout", http[2])

    def test_no_overrides_is_plain_default(self):
        body = retryguard.build_edge_vs_patch_body(self.ROUTE, {}, 3, 500)
        self.assertEqual(len(body["spec"]["http"]), 1)
        self.assertNotIn("match", body["spec"]["http"][0])


class TestEdgeController(unittest.TestCase):
    EDGE = ("frontend", "recommendationservice")
    EDGES = (EDGE, ("recommendationservice", "productcatalogservice"))

    def setUp(self):
        self.clock = 0

    def make(self):
        return retryguard.EdgeController(self.EDGES, 0.5, 0.2, 30)

    def feed(self, ctrl, ticks, rpr, rejection=None, step=1):
        out = []
        rejection = rejection or {}
        for _ in range(ticks):
            ts = retryguard.format_row_timestamp(self.clock)
            self.clock += step
            rpr_map = {}
            rpr_ts = {}
            if rpr is not None:
                rpr_map[self.EDGE] = rpr
                rpr_ts[self.EDGE] = ts
            rej_ts = {svc: ts for svc in rejection}
            out += ctrl.step(rpr_map, rejection, rpr_ts, rej_ts)
        return out

    def test_streak_fires_30s_after_the_first_row(self):
        ctrl = self.make()
        self.assertEqual(self.feed(ctrl, 30, 0.9), [])
        changes = self.feed(ctrl, 1, 0.9)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].service, "recommendationservice")
        self.assertEqual(changes[0].transition, "OFF")
        self.assertEqual(changes[0].new_off, frozenset({"frontend"}))
        self.assertEqual(changes[0].metric, "rpr")
        self.assertEqual(changes[0].lines[0][-1], 30)

    def test_two_second_rows_fire_at_30s_with_fewer_than_30_rows(self):
        ctrl = self.make()
        self.assertEqual(self.feed(ctrl, 15, 0.9, step=2), [])
        changes = self.feed(ctrl, 1, 0.9, step=2)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].lines[0][-1], 30)
        self.assertLess(changes[0].lines[0][4], 30)

    def test_under_bar_row_clears_high_since(self):
        ctrl = self.make()
        self.feed(ctrl, 5, 0.9)
        self.assertIsNotNone(ctrl.edge_state[self.EDGE].high_since)
        self.feed(ctrl, 1, 0.1)
        state = ctrl.edge_state[self.EDGE]
        self.assertIsNone(state.high_since)
        self.assertEqual(state.consecutive_high, 0)

    def test_low_tick_resets_streak(self):
        ctrl = self.make()
        self.feed(ctrl, 30, 0.9)
        self.feed(ctrl, 1, 0.1)
        self.assertEqual(self.feed(ctrl, 30, 0.9), [])

    def test_skipped_ticks_change_nothing(self):
        ctrl = self.make()
        self.feed(ctrl, 30, 0.9)
        since = ctrl.edge_state[self.EDGE].high_since
        self.feed(ctrl, 5, None)
        self.assertEqual(ctrl.edge_state[self.EDGE].high_since, since)
        self.assertEqual(ctrl.edge_state[self.EDGE].consecutive_high, 30)
        self.assertEqual(len(self.feed(ctrl, 1, 0.9)), 1)

    def test_rejection_fallback_idle_until_an_edge_is_off(self):
        ctrl = self.make()
        rej = {"recommendationservice": 0.0}
        self.assertEqual(self.feed(ctrl, 40, 0.1, rej), [])
        self.assertEqual(ctrl.svc_state, {})

    def test_fallback_reenables_all_off_edges_together(self):
        ctrl = self.make()
        change = self.feed(ctrl, 31, 0.9)[0]
        ctrl.commit(change)
        self.assertEqual(ctrl.off_callers("recommendationservice"), {"frontend"})
        rej = {"recommendationservice": 0.05}
        self.assertEqual(self.feed(ctrl, 30, None, rej), [])
        back = self.feed(ctrl, 1, None, rej)
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0].transition, "ON")
        self.assertEqual(back[0].metric, "rejection")
        self.assertEqual(back[0].new_off, frozenset())
        ctrl.commit(back[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 1)
        self.assertEqual(ctrl.off_callers("recommendationservice"), frozenset())
        self.assertEqual(ctrl.svc_state, {})

    def test_reenable_resets_only_off_edges(self):
        catalog = "productcatalogservice"
        off_a = ("frontend", catalog)
        off_b = ("checkoutservice", catalog)
        sibling = ("recommendationservice", catalog)
        ctrl = retryguard.EdgeController(
            (off_a, off_b, sibling), 0.5, 0.2, 30
        )
        changes = []
        for i in range(31):
            ts = retryguard.format_row_timestamp(i)
            rpr = {off_a: 0.9, off_b: 0.9}
            rpr_ts = {off_a: ts, off_b: ts}
            if i < 10:
                rpr[sibling] = 0.9
                rpr_ts[sibling] = ts
            changes += ctrl.step(rpr, {}, rpr_ts, {})
        offs = [c for c in changes if c.transition == "OFF"]
        self.assertEqual(len(offs), 1)
        self.assertEqual(
            offs[0].new_off, frozenset({"frontend", "checkoutservice"})
        )
        self.assertEqual(ctrl.edge_state[sibling].consecutive_high, 10)
        ctrl.commit(offs[0])
        self.assertEqual(ctrl.edge_state[off_a].retries_state, "OFF")
        self.assertEqual(ctrl.edge_state[off_b].retries_state, "OFF")
        self.assertEqual(ctrl.edge_state[sibling].retries_state, "ON")
        self.assertEqual(ctrl.edge_state[sibling].consecutive_high, 10)

        backs = []
        for i in range(31):
            ts = retryguard.format_row_timestamp(100 + i)
            backs += ctrl.step({}, {catalog: 0.05}, {}, {catalog: ts})
        ons = [c for c in backs if c.transition == "ON"]
        self.assertEqual(len(ons), 1)
        self.assertEqual(ctrl.edge_state[sibling].consecutive_high, 10)
        ctrl.commit(ons[0])

        for edge in (off_a, off_b):
            st = ctrl.edge_state[edge]
            self.assertEqual(st.retries_state, "ON")
            self.assertEqual(st.attempts, 1)
            self.assertEqual(st.consecutive_high, 0)
            self.assertEqual(st.consecutive_low, 0)
        self.assertEqual(ctrl.edge_state[sibling].retries_state, "ON")
        self.assertEqual(ctrl.edge_state[sibling].attempts, 3)
        self.assertEqual(ctrl.edge_state[sibling].consecutive_high, 10)
        self.assertEqual(ctrl.off_callers(catalog), frozenset())
        self.assertEqual(ctrl.svc_state, {})
        self.assertEqual(ons[0].caller_attempts, {"frontend": 1, "checkoutservice": 1})


class TestAttemptRamp(unittest.TestCase):
    EDGE = ("frontend", "checkoutservice")

    def make(self, interval=3):
        return retryguard.EdgeController((self.EDGE,), 0.5, 0.2, interval)

    def setUp(self):
        self.clock = 0

    def to_attempts(self, ctrl, attempts):
        # One row to open the streak, then N seconds of 1s rows.
        reenable_span = ctrl.interval + 1                      # 0 -> 1: 30 s
        climb_span = retryguard.CLIMB_INTERVAL_SECONDS + 1     # 1 -> 2, 2 -> 3: 15 s
        if attempts == 0:
            change = self.feed(ctrl, reenable_span, 0.9)[0]
            ctrl.commit(change)
            return
        self.to_attempts(ctrl, 0)
        back = self.feed(ctrl, reenable_span, None, {"checkoutservice": 0.05})[0]
        ctrl.commit(back)
        while ctrl.edge_state[self.EDGE].attempts < attempts:
            climbed = self.feed(ctrl, climb_span, 0.05)[0]
            ctrl.commit(climbed)

    def feed(self, ctrl, ticks, rpr, rejection=None, step=1):
        out = []
        rejection = rejection or {}
        for _ in range(ticks):
            ts = retryguard.format_row_timestamp(self.clock)
            self.clock += step
            rpr_map = {}
            rpr_ts = {}
            if rpr is not None:
                rpr_map[self.EDGE] = rpr
                rpr_ts[self.EDGE] = ts
            rej_ts = {svc: ts for svc in rejection}
            out += ctrl.step(rpr_map, rejection, rpr_ts, rej_ts)
        return out

    def test_climb_limits_are_0_17_and_0_33(self):
        self.assertEqual(retryguard.climb_rpr_limit(1, 3, 0.5), 0.17)
        self.assertEqual(retryguard.climb_rpr_limit(2, 3, 0.5), 0.33)

    def test_missing_climb_keys_use_the_formula(self):
        self.assertEqual(
            retryguard.climb_limits_from_params({
                "retry_attempts_on": 3, "retries_threshold": 0.5,
            }),
            (0.17, 0.33),
        )
        self.assertEqual(
            retryguard.climb_limits_from_params({
                "retry_attempts_on": 3,
                "retries_threshold": 0.5,
                "climb_rpr_1_to_2": 0.10,
                "climb_rpr_2_to_3": 0.25,
            }),
            (0.10, 0.25),
        )

    def test_configured_climb_bars_replace_the_formula(self):
        ctrl = retryguard.EdgeController(
            (self.EDGE,), 0.5, 0.2, 3,
            climb_rpr_1_to_2=0.10, climb_rpr_2_to_3=0.25,
        )
        self.to_attempts(ctrl, 1)
        # 0.17 used to climb from 1. It is above 0.10 and at or under 0.5, so it holds.
        self.assertEqual(self.feed(ctrl, 16, 0.17), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 1)
        self.assertEqual(ctrl.edge_state[self.EDGE].consecutive_low, 0)
        climb = self.feed(ctrl, 16, 0.10)
        self.assertEqual(climb[0].desired_attempts, {"frontend": 2})
        ctrl.commit(climb[0])
        # 0.33 used to climb from 2. It is above 0.25, so it holds.
        self.assertEqual(self.feed(ctrl, 16, 0.33), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 2)
        climb3 = self.feed(ctrl, 16, 0.25)
        self.assertEqual(climb3[0].desired_attempts, {"frontend": 3})

    def test_climb_interval_per_step(self):
        self.assertEqual(retryguard.CLIMB_INTERVAL_SECONDS, 15)
        self.assertEqual(retryguard.climb_interval_s(0, 30), 30)
        self.assertEqual(retryguard.climb_interval_s(1, 30), 15)
        self.assertEqual(retryguard.climb_interval_s(2, 30), 15)

    def test_reenable_needs_rejection_under_0_10(self):
        # 0.15 is under the 0.20 rejection bar and must still not restore.
        ctrl = self.make()
        self.to_attempts(ctrl, 0)
        self.assertEqual(self.feed(ctrl, 5, None, {"checkoutservice": 0.15}), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 0)
        # A tick at 0.15 breaks a quiet streak that was about to fire.
        self.feed(ctrl, 3, None, {"checkoutservice": 0.05})
        self.assertEqual(self.feed(ctrl, 1, None, {"checkoutservice": 0.15}), [])
        self.assertEqual(self.feed(ctrl, 3, None, {"checkoutservice": 0.05}), [])
        back = self.feed(ctrl, 1, None, {"checkoutservice": 0.09})
        self.assertEqual(back[0].transition, "ON")
        self.assertEqual(back[0].lines[0][5], 1)

    def test_rejection_restores_one_attempt(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 0)
        self.assertEqual(self.feed(ctrl, 3, None, {"checkoutservice": 0.05}), [])
        back = self.feed(ctrl, 1, None, {"checkoutservice": 0.05})
        self.assertEqual(back[0].transition, "ON")
        self.assertEqual(back[0].lines[0][5], 1)
        ctrl.commit(back[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 1)
        self.assertEqual(ctrl.svc_state, {})

    def test_quiet_rpr_climbs_one_step_at_a_time(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        self.assertEqual(self.feed(ctrl, 15, 0.10), [])      # rows 1..15 = 14 s elapsed
        climb = self.feed(ctrl, 1, 0.10)                      # row 16 = 15 s elapsed
        self.assertEqual(climb[0].transition, "RAMP")
        self.assertEqual(climb[0].desired_attempts, {"frontend": 2})
        self.assertEqual(climb[0].lines[0][1:3], ("1", "2"))
        ctrl.commit(climb[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 2)
        self.assertEqual(ctrl.edge_state[self.EDGE].consecutive_low, 0)
        self.assertEqual(self.feed(ctrl, 15, 0.10), [])
        climb3 = self.feed(ctrl, 1, 0.10)
        self.assertEqual(climb3[0].desired_attempts, {"frontend": 3})
        self.assertEqual(climb3[0].caller_attempts, {})
        ctrl.commit(climb3[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 3)
        self.assertEqual(self.feed(ctrl, 5, 0.10), [])

    def test_between_climb_bar_and_0_5_holds(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        self.feed(ctrl, 2, 0.10)
        self.assertEqual(self.feed(ctrl, 1, 0.20), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].consecutive_low, 0)
        self.assertEqual(self.feed(ctrl, 2, 0.10), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 1)
        self.to_attempts(ctrl, 2)
        self.assertEqual(self.feed(ctrl, 5, 0.40), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 2)

    def test_above_0_5_sheds_from_a_ramp_step(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        self.assertEqual(self.feed(ctrl, 3, 0.90), [])
        shed = self.feed(ctrl, 1, 0.90)
        self.assertEqual(shed[0].transition, "OFF")
        self.assertEqual(shed[0].new_off, frozenset({"frontend"}))
        self.assertEqual(shed[0].lines[0][6], 1)
        ctrl.commit(shed[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 0)
        self.assertIn("checkoutservice", ctrl.svc_state)

    def test_shed_from_ramp_step_still_needs_30_seconds(self):
        # The class fixture uses a 3 s interval. This regression needs the
        # production 30 s bar, or shed fires on the fourth row.
        ctrl = self.make(interval=30)
        self.to_attempts(ctrl, 1)
        self.assertEqual(self.feed(ctrl, 29, 0.90), [])      # 28 s elapsed
        self.assertEqual(self.feed(ctrl, 1, 0.90), [])       # 29 s elapsed
        shed = self.feed(ctrl, 2, 0.90)                       # reaches 30 s
        self.assertEqual(shed[0].transition, "OFF")

    def test_uncommitted_climb_is_proposed_again(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        first = self.feed(ctrl, 16, 0.05)
        self.assertEqual(len(first), 1)
        again = self.feed(ctrl, 1, 0.05)
        self.assertEqual(again[0].desired_attempts, {"frontend": 2})

    def test_zero_to_one_still_needs_30_seconds(self):
        # Same as the shed regression: 0→1 follows ctrl.interval, which is
        # 3 s on the class fixture and 30 s in production.
        ctrl = self.make(interval=30)
        self.to_attempts(ctrl, 0)
        self.assertEqual(self.feed(ctrl, 16, None, {"checkoutservice": 0.05}), [])  # 15 s
        self.assertEqual(self.feed(ctrl, 14, None, {"checkoutservice": 0.05}), [])  # 29 s
        back = self.feed(ctrl, 2, None, {"checkoutservice": 0.05})                  # 30 s
        self.assertEqual(back[0].transition, "ON")


class TestGrpcRetryCallees(unittest.TestCase):
    def test_retry_on_for(self):
        self.assertEqual(
            retryguard.retry_on_for("recommendationservice"),
            "5xx,reset,connect-failure,unavailable,deadline-exceeded",
        )
        for svc in ("checkoutservice", "paymentservice", "emailservice",
                    "cartservice", "shippingservice", "frontend"):
            self.assertEqual(retryguard.retry_on_for(svc), "5xx,reset,connect-failure")

    def test_patch_body_uses_given_retry_on(self):
        route = [{"destination": {"host": "recommendationservice"}}]
        body = retryguard.build_vs_patch_body(
            route, 3, 500, retry_on=retryguard.retry_on_for("recommendationservice")
        )
        self.assertEqual(len(body["spec"]["http"]), 1)
        self.assertIn("deadline-exceeded", body["spec"]["http"][0]["retries"]["retryOn"])

    def test_rejection_counts_grpc_only_when_asked(self):
        prev = retryguard.InboundSnapshot("2026-10-07T10:00:01Z", 100.0, 0.0)
        curr = retryguard.InboundSnapshot(
            "2026-10-07T10:00:02Z", 200.0, 0.0, resets=0.0, grpc_4=30.0, grpc_14=10.0
        )
        off, _ = retryguard.measure_inbound_rejection(prev, curr)
        on, _ = retryguard.measure_inbound_rejection(prev, curr, count_grpc=True)
        self.assertAlmostEqual(off, 0.0)
        self.assertAlmostEqual(on, 0.40)


class TestRunScenarioRetryOnMatches(unittest.TestCase):
    def test_same_string_as_controller(self):
        import run_scenario
        for svc in (
            "adservice", "cartservice", "checkoutservice", "currencyservice",
            "emailservice", "frontend", "paymentservice", "productcatalogservice",
            "recommendationservice", "shippingservice",
        ):
            self.assertEqual(run_scenario.retry_on_for(svc), retryguard.retry_on_for(svc))


def test_reenable_rejection_param_overrides_default():
    import retryguard as rg
    assert rg.reenable_threshold_from_params({}) == rg.REENABLE_REJECTION_THRESHOLD
    assert rg.reenable_threshold_from_params({"reenable_rejection": 0.15}) == 0.15


if __name__ == "__main__":
    unittest.main()

