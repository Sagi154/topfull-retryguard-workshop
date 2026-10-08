#!/usr/bin/env python3
"""
retryguard.py — Rejection-based productive-retry controller (RetryGuard paper, Sec. 4, Algorithm 1).

Usage (on master, with venv active):
    python3 retryguard.py --params /tmp/retryguard_params.json

Reads {record_path}/service_inbound.csv (Δ5xx / Δtotal per service) and
patches Istio VirtualService retries.attempts when a streak of rows
stays past the threshold for Interval seconds of row timestamps
(RetryGuard paper Algorithm 1, one symmetric Interval for both the
disable and re-enable transitions). A skipped row does not count and
does not clear the streak. Rows already in the file at process start
are not replayed.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import kubernetes
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

INBOUND_CSV_NAME = "service_inbound.csv"

EDGES_CSV_NAME = "service_edges.csv"

# The Boutique call graph is fixed, so the controlled edges are a constant.
# HTTP/gRPC edges between Boutique services only: no redis-cart (TCP, no
# VirtualService), nothing into frontend.
CONTROLLED_EDGES = (
    ("frontend", "adservice"),
    ("frontend", "cartservice"),
    ("frontend", "checkoutservice"),
    ("frontend", "currencyservice"),
    ("frontend", "productcatalogservice"),
    ("frontend", "recommendationservice"),
    ("frontend", "shippingservice"),
    ("checkoutservice", "cartservice"),
    ("checkoutservice", "currencyservice"),
    ("checkoutservice", "emailservice"),
    ("checkoutservice", "paymentservice"),
    ("checkoutservice", "productcatalogservice"),
    ("checkoutservice", "shippingservice"),
    ("recommendationservice", "productcatalogservice"),
)

# HTTP Boutique callees that already have a VirtualService.
# frontend (ingress) and redis-cart (TCP) are excluded — see the
# 2026-09-10 mesh measure_value spec.
CONTROLLED_SERVICES = (
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

VS_GROUP = "networking.istio.io"
VS_VERSION = "v1alpha3"
VS_PLURAL = "virtualservices"
VS_NAMESPACE = "default"
RETRY_ON = "5xx,reset,connect-failure"
# Callees whose methods are all reads, so a repeated call only costs load.
# cartservice (AddItem) and shippingservice (ShipOrder) stay on RETRY_ON:
# one route rule cannot split a read from a write, and the rejection rate
# has no per-method split either.
GRPC_RETRY_CALLEES = (
    "adservice",
    "currencyservice",
    "productcatalogservice",
    "recommendationservice",
)
RETRY_ON_GRPC = RETRY_ON + ",unavailable,deadline-exceeded"


def retry_on_for(service: str) -> str:
    return RETRY_ON_GRPC if service in GRPC_RETRY_CALLEES else RETRY_ON

STARTUP_POLL_SECONDS = 5
STARTUP_TIMEOUT_SECONDS = 60

REQUIRED_PARAMS = (
    "rejection_threshold",
    "sample_interval_seconds",
    "interval_samples",
    "retry_attempts_on",
    "retry_attempts_off",
    "per_try_timeout_ms",
)

# --------------------------------------------------------------------------- #
#  Logging
# --------------------------------------------------------------------------- #

log = logging.getLogger("retryguard")


def setup_logging(record_path: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    log_file = record_path / "retryguard.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        # Still run if the log directory is not writable; stdout is enough for tmux.
        print(f"[retryguard] WARN: cannot open {log_file}: {exc}", file=sys.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
#  Algorithm 1 state
# --------------------------------------------------------------------------- #

@dataclass
class ServiceState:
    consecutive_low: int = 0
    consecutive_high: int = 0
    # Workshop deviation from paper: Algorithm 1 initializes Retries ← OFF.
    # We start ON so the controller matches the default VirtualService
    # (attempts=3) and Scenario 1 (healthy load) produces zero patches.
    retries_state: str = "ON"
    # Edge mode only. 0 is off, attempts_on (3) is the full policy, and 1 or 2
    # is a ramp step. Rejection mode does not read this.
    attempts: int = 3
    # Timestamp of the first row in the open streak. The transition fires
    # when the newest row is at least `interval` seconds after this, not
    # when the row count reaches `interval`.
    high_since: Optional[str] = None
    low_since: Optional[str] = None


@dataclass(frozen=True)
class InboundSnapshot:
    timestamp: str
    total: float
    five_xx: float
    resets: float = 0.0  # downstream_rq_rx_reset (per-try timeout aborts)
    grpc_4: float = 0.0  # DEADLINE_EXCEEDED, recorded as HTTP 200
    grpc_14: float = 0.0  # UNAVAILABLE, recorded as HTTP 200


@dataclass(frozen=True)
class EdgeSnapshot:
    timestamp: str
    total: float  # every attempt, retries included (the paper's Lambda)
    retry: float


# --------------------------------------------------------------------------- #
#  Config loading
# --------------------------------------------------------------------------- #

def load_params(path: str) -> dict:
    with open(path, "r") as f:
        params = json.load(f)
    missing = [k for k in REQUIRED_PARAMS if k not in params]
    if missing:
        raise SystemExit(f"[retryguard] params JSON missing keys: {missing}")
    return params


def load_record_path() -> Path:
    with open(GLOBAL_CONFIG_PATH, "r") as f:
        gcfg = json.load(f)
    record_path = Path(gcfg["record_path"])
    return record_path


# --------------------------------------------------------------------------- #
#  Metric reading
# --------------------------------------------------------------------------- #

def read_latest_inbound_row(csv_path: Path, service: str) -> Optional[InboundSnapshot]:
    if not csv_path.is_file():
        return None
    try:
        with open(csv_path, "r", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    latest = None
    for row in rows:
        if row.get("service") != service:
            continue
        try:
            latest = InboundSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                five_xx=float(row["5xx"]),
                resets=float(row.get("resets", 0)),
                grpc_4=float(row.get("grpc_4", 0) or 0),
                grpc_14=float(row.get("grpc_14", 0) or 0),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return latest


def measure_inbound_rejection(
    previous: Optional[InboundSnapshot],
    current: Optional[InboundSnapshot],
    count_grpc: bool = False,
) -> tuple[Optional[float], Optional[InboundSnapshot]]:
    if current is None:
        return None, previous
    if previous is None:
        return None, current
    if current.timestamp <= previous.timestamp:
        return None, previous
    delta_total = current.total - previous.total
    delta_failures = (current.five_xx - previous.five_xx) + (
        current.resets - previous.resets
    )
    if count_grpc:
        delta_failures += (current.grpc_4 - previous.grpc_4) + (
            current.grpc_14 - previous.grpc_14
        )
    if delta_total <= 0:
        return 0.0, current
    return delta_failures / delta_total, current


class InboundCsvTailer:
    """
    Incrementally tails service_inbound.csv. Call poll() once per tick;
    read self.latest[service] afterward. latest always holds the most
    recently seen InboundSnapshot per service, even on ticks where no new
    row arrived. Never re-parses bytes already consumed. Safe to call
    poll() even if the file doesn't exist yet, or was truncated/recreated
    by a collector restart (auto-resyncs from scratch in that case).
    """

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.latest: Dict[str, InboundSnapshot] = {}
        self._offset = 0
        self._fieldnames: Optional[list] = None
        self._pending = ""

    def _reset(self) -> None:
        self._offset = 0
        self._fieldnames = None
        self._pending = ""
        self.latest = {}

    def _apply_line(self, line: str) -> None:
        if not line or self._fieldnames is None:
            return
        try:
            values = next(csv.reader([line]))
        except (csv.Error, StopIteration):
            return
        if len(values) != len(self._fieldnames):
            return
        row = dict(zip(self._fieldnames, values))
        if row.get("service") is None:
            return
        try:
            snapshot = InboundSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                five_xx=float(row["5xx"]),
                resets=float(row.get("resets", 0)),
                grpc_4=float(row.get("grpc_4", 0) or 0),
                grpc_14=float(row.get("grpc_14", 0) or 0),
            )
        except (KeyError, TypeError, ValueError):
            return
        self.latest[row["service"]] = snapshot

    def poll(self) -> None:
        try:
            size = self.csv_path.stat().st_size
        except OSError:
            return

        if size < self._offset:
            # Truncated or recreated (e.g. a collector restart) — resync.
            self._reset()

        try:
            with open(self.csv_path, "r", newline="") as f:
                if self._fieldnames is None:
                    header_line = f.readline()
                    if not header_line:
                        return  # empty file so far
                    try:
                        self._fieldnames = next(csv.reader([header_line.rstrip("\n")]))
                    except (csv.Error, StopIteration):
                        return
                    self._offset = f.tell()
                    self._pending = ""
                else:
                    f.seek(self._offset)

                chunk = f.read()
                self._offset = f.tell()
        except OSError:
            return

        if not chunk:
            return

        buf = self._pending + chunk
        lines = buf.split("\n")
        self._pending = lines.pop()  # trailing fragment (no newline yet)
        for line in lines:
            self._apply_line(line)


class EdgesCsvTailer(InboundCsvTailer):
    """Same append-only tail as InboundCsvTailer; rows keyed by (caller, target)."""

    def _apply_line(self, line: str) -> None:
        if not line or self._fieldnames is None:
            return
        try:
            values = next(csv.reader([line]))
        except (csv.Error, StopIteration):
            return
        if len(values) != len(self._fieldnames):
            return
        row = dict(zip(self._fieldnames, values))
        try:
            snapshot = EdgeSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                retry=float(row["retry"]),
            )
            key = (row["caller"], row["target"])
        except (KeyError, TypeError, ValueError):
            return
        self.latest[key] = snapshot


def measure_edge_rpr(
    previous: Optional[EdgeSnapshot],
    current: Optional[EdgeSnapshot],
) -> tuple[Optional[float], Optional[EdgeSnapshot]]:
    """
    Retries per request on one edge: the paper's (Lambda - lambda) / lambda.
    `total` counts every attempt, so first attempts = delta total - delta retry.
    Returns None (skip the tick) when there is no new row or no first attempts.
    """
    if current is None:
        return None, previous
    if previous is None:
        return None, current
    if current.timestamp <= previous.timestamp:
        return None, previous
    delta_retry = current.retry - previous.retry
    first_attempts = (current.total - previous.total) - delta_retry
    if first_attempts <= 0:
        return None, current
    return delta_retry / first_attempts, current


# --------------------------------------------------------------------------- #
#  VirtualService patching
# --------------------------------------------------------------------------- #

def make_custom_api():
    try:
        config.load_kube_config()
    except config.ConfigException:
        config.load_incluster_config()
    return client.CustomObjectsApi()


def http_retry_fields(
    attempts: int, per_try_timeout_ms: int, retry_on: str = RETRY_ON
) -> dict:
    """
    Retry fields for one HTTP rule.

    attempts > 0: full retry policy. Each try is capped by perTryTimeout, so a
    slow callee becomes a reset and can be retried. No route-level timeout,
    so the request may use every attempt.

    attempts == 0: bare ``retries: {attempts: 0}`` plus a route ``timeout``
    equal to perTryTimeout. Istio rejects attempts 0 combined with retryOn or
    perTryTimeout, and omitting the retries block falls back to Istio's
    default of 2 retries. The route timeout is what still turns a slow callee
    into an inbound reset, so the paper's rejection rate stays visible while
    retries are off. Without it, the request waits and completes as 2xx.
    """
    if int(attempts) > 0:
        return {
            "retries": {
                "attempts": int(attempts),
                "retryOn": retry_on,
                "perTryTimeout": f"{per_try_timeout_ms}ms",
            }
        }
    return {
        "timeout": f"{int(per_try_timeout_ms)}ms",
        "retries": {"attempts": 0},
    }


def build_vs_patch_body(
    route: list, attempts: int, per_try_timeout_ms: int, retry_on: str = RETRY_ON
) -> dict:
    """VirtualService merge-patch body: full retry policy, or attempts 0 with a route timeout."""
    rule = {
        "route": route,
        **http_retry_fields(attempts, per_try_timeout_ms, retry_on=retry_on),
    }
    return {"spec": {"http": [rule]}}


def build_edge_vs_patch_body(
    route: list,
    caller_attempts: dict,
    attempts_on: int,
    per_try_timeout_ms: int,
    retry_on: str = RETRY_ON,
) -> dict:
    """
    Per-edge VirtualService body. ``caller_attempts`` maps a caller to its
    attempt count when that count is not the default ``attempts_on``.
    attempts 0 is a bare retries block plus a route timeout equal to
    perTryTimeout (Istio rejects attempts 0 with a retry policy, and without
    the route timeout a slow callee completes as 2xx). attempts 1 or 2 get
    the full policy at that count and no route timeout.
    The default route, with ``attempts_on``, is last. Match routes come
    first; Istio takes the first rule that matches.
    """
    default = build_vs_patch_body(
        route, attempts_on, per_try_timeout_ms, retry_on=retry_on
    )["spec"]["http"][0]
    rules = []
    for caller in sorted(caller_attempts):
        attempts = int(caller_attempts[caller])
        rules.append(
            {
                "match": [{"sourceLabels": {"app": caller}}],
                "route": route,
                **http_retry_fields(attempts, per_try_timeout_ms, retry_on=retry_on),
            }
        )
    return {"spec": {"http": rules + [default]}}


def patch_virtualservice(
    api: client.CustomObjectsApi,
    service_name: str,
    attempts: int,
    per_try_timeout_ms: int = 500,
    namespace: str = VS_NAMESPACE,
    caller_attempts=None,
) -> None:
    """
    GET the existing VirtualService, then merge-patch retries while
    preserving the existing route (Istio rejects an http rule with no route).

    To disable retries we send ``retries: {attempts: 0}`` plus a route
    ``timeout`` equal to perTryTimeout. Istio's webhook rejects
    ``attempts: 0`` combined with ``retryOn`` or ``perTryTimeout``, but a bare
    ``attempts: 0`` is accepted and yields no Envoy retry policy (true zero
    retries). The route timeout is separate from the retry policy: it cancels
    a slow request so the callee still records an inbound reset. Omitting the
    retries block instead would fall back to Istio's built-in default
    (2 retries on connect-failure, refused-stream, unavailable, cancelled,
    503) — verified 2026-10-06.
    Merge-patch replaces the ``http`` array, so the old retries key is dropped.
    """
    existing = api.get_namespaced_custom_object(
        group=VS_GROUP,
        version=VS_VERSION,
        namespace=namespace,
        plural=VS_PLURAL,
        name=service_name,
    )

    http_rules = existing.get("spec", {}).get("http") or []
    if http_rules and http_rules[0].get("route"):
        route = http_rules[0]["route"]
    else:
        route = [{"destination": {"host": service_name}}]

    retry_on = retry_on_for(service_name)
    if caller_attempts is None:
        body = build_vs_patch_body(
            route, attempts, per_try_timeout_ms, retry_on=retry_on
        )
    else:
        # Edge mode: `attempts` is the default policy. `caller_attempts` overrides
        # callers that are off (0) or on a ramp step (1, 2, ...).
        body = build_edge_vs_patch_body(
            route, caller_attempts, attempts, per_try_timeout_ms, retry_on=retry_on
        )

    api.patch_namespaced_custom_object(
        group=VS_GROUP,
        version=VS_VERSION,
        namespace=namespace,
        plural=VS_PLURAL,
        name=service_name,
        body=body,
    )


# --------------------------------------------------------------------------- #
#  Startup wait / signals
# --------------------------------------------------------------------------- #

_shutdown = False


def _handle_signal(signum, _frame):
    global _shutdown
    log.info("%s  SHUTDOWN  signal=%s", utc_now(), signum)
    _shutdown = True


def wait_for_inbound_csv(
    record_path: Path,
    timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
    poll_seconds: float = STARTUP_POLL_SECONDS,
) -> None:
    """Poll until service_inbound.csv exists and has ≥1 data row."""
    deadline = time.time() + timeout_seconds
    csv_path = record_path / INBOUND_CSV_NAME
    log.info(
        "%s  WAITING  for %s (timeout=%ss)",
        utc_now(),
        csv_path,
        timeout_seconds,
    )
    while time.time() < deadline:
        if _shutdown:
            raise SystemExit(0)
        if csv_path.is_file():
            try:
                with open(csv_path, "r", newline="") as f:
                    rows = list(csv.DictReader(f))
            except OSError:
                rows = []
            if rows:
                log.info("%s  READY  found %s (%d rows)", utc_now(), INBOUND_CSV_NAME, len(rows))
                return
        time.sleep(poll_seconds)
    raise SystemExit(
        f"[retryguard] ERROR: no data in {csv_path} "
        f"after {timeout_seconds}s — is envoy_retry_collector running?"
    )


# --------------------------------------------------------------------------- #
#  Main control loop (Algorithm 1)
# --------------------------------------------------------------------------- #

def format_row_timestamp(epoch_s: int) -> str:
    """UTC timestamp string used by the mesh CSVs and by unit-test clocks."""
    return datetime.fromtimestamp(int(epoch_s), tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_row_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def streak_elapsed_s(since: Optional[str], now: Optional[str]) -> float:
    """Seconds from the first row of a streak to `now`. 0 if either is missing."""
    if not since or not now:
        return 0.0
    return (parse_row_timestamp(now) - parse_row_timestamp(since)).total_seconds()


def streak_met(since: Optional[str], now: Optional[str], interval: int) -> bool:
    """True when the newest row is at least `interval` seconds after the first."""
    if not since or not now:
        return False
    return streak_elapsed_s(since, now) >= int(interval)


def _open_high(state: ServiceState, timestamp: str) -> None:
    state.consecutive_high += 1
    state.consecutive_low = 0
    state.low_since = None
    if state.high_since is None:
        state.high_since = timestamp


def _open_low(state: ServiceState, timestamp: str) -> None:
    state.consecutive_low += 1
    state.consecutive_high = 0
    state.high_since = None
    if state.low_since is None:
        state.low_since = timestamp


def _clear_streaks(state: ServiceState) -> None:
    state.consecutive_low = 0
    state.consecutive_high = 0
    state.low_since = None
    state.high_since = None


def apply_algorithm1(
    state: ServiceState,
    rejection: float,
    threshold: float,
    interval: int,
    timestamp: str,
) -> Optional[str]:
    """
    One Algorithm 1 iteration. Mutates state counters.

    `interval` is seconds of row timestamps, applied symmetrically to both
    the ON and OFF transitions. The row count (`consecutive_low` /
    `consecutive_high`) is recorded, but the transition fires when the
    newest row is at least `interval` seconds after the first row of the
    streak. Returns desired retries state ("ON"/"OFF") if a transition
    should fire, otherwise None (keep current state).
    """
    if rejection < threshold:
        _open_low(state, timestamp)
    elif rejection > threshold:
        _open_high(state, timestamp)
    else:
        # Exactly == Threshold (float rarity): reset both streaks.
        _clear_streaks(state)

    desired = state.retries_state
    if streak_met(state.low_since, timestamp, interval):
        desired = "ON"
    elif streak_met(state.high_since, timestamp, interval):
        desired = "OFF"

    if desired != state.retries_state:
        return desired
    return None


# Stricter than rejection_threshold. Used only for the 0→1 step in edge mode.
# A callee that is merely under the 0.20 disable bar (run15 recommendations
# re-enabled at 0.14) is not quiet enough to start allowing retries again.
REENABLE_REJECTION_THRESHOLD = 0.10

# Quiet time needed for each ramp climb after the first attempt is restored.
# 0 -> 1 keeps the configured interval (interval_samples, 30 s). 1 -> 2 and
# 2 -> 3 use this shorter bar. Shed (rpr above the threshold) keeps the
# configured interval.
CLIMB_INTERVAL_SECONDS = 15


def climb_interval_s(attempts: int, reenable_interval: int) -> int:
    """Seconds of quiet needed to leave `attempts` for the next step up."""
    if int(attempts) <= 0:
        return int(reenable_interval)
    return CLIMB_INTERVAL_SECONDS


def climb_rpr_limit(attempts: int, attempts_on: int, rpr_threshold: float) -> float:
    """
    Highest rpr at which adding attempts is still predicted to land on
    ``rpr_threshold`` once the edge is back at ``attempts_on``.

    rpr is assumed to scale with the attempt cap (every allowed retry is
    used). That is an upper bound: ``rpr_hat(attempts_on) = rpr_now *
    attempts_on / attempts_now``. Rounded to two decimals so attempts 1 and 2
    with threshold 0.5 and attempts_on 3 are 0.17 and 0.33.
    """
    return round(float(rpr_threshold) * int(attempts) / int(attempts_on), 2)


@dataclass
class Change:
    service: str          # callee whose VirtualService must be patched
    transition: str       # "OFF" (shed to 0), "ON" (0→1), or "RAMP" (climb)
    new_off: frozenset    # callers at 0 after the patch
    metric: str           # "rpr" or "rejection"
    # (name, old, new, value, counter, attempts, from_attempts)
    lines: list
    desired_attempts: dict  # caller → attempts this change sets
    caller_attempts: dict   # caller → attempts for every caller not at attempts_on


class EdgeController:
    """
    Edge mode state. step() proposes changes without committing retries
    state; the caller patches the VirtualService and then commit()s, so a
    failed patch is retried on the next tick (the streak timestamp stays).

    Leaving 0 uses the rejection fallback and restores one attempt, but only
    while rejection stays under reenable_rejection_threshold (0.10), not the
    0.20 rejection_threshold. Further attempts climb one at a time while rpr
    stays at or under climb_rpr_limit. Climbs 1→2 and 2→3 each need
    CLIMB_INTERVAL_SECONDS (15 s) of quiet; 0→1 and shed use the full
    interval (30 s). rpr above rpr_threshold for a full interval of row
    timestamps sheds straight to 0 from any attempt count.
    """

    def __init__(
        self, edges, rpr_threshold, rejection_threshold, interval, attempts_on=3,
        reenable_rejection_threshold=REENABLE_REJECTION_THRESHOLD,
    ):
        self.rpr_threshold = rpr_threshold
        self.rejection_threshold = rejection_threshold
        self.reenable_rejection_threshold = reenable_rejection_threshold
        self.interval = interval
        self.attempts_on = int(attempts_on)
        self.edge_state = {
            e: ServiceState(attempts=self.attempts_on) for e in edges
        }
        # Per-callee rejection counters; a key exists only while the callee
        # has at least one edge at 0 attempts.
        self.svc_state: Dict[str, ServiceState] = {}

    def off_callers(self, service: str) -> frozenset:
        return frozenset(
            c
            for (c, t), st in self.edge_state.items()
            if t == service and st.attempts == 0
        )

    def _resulting_attempts(self, service: str, desired: dict) -> dict:
        out = {}
        for (caller, target), st in self.edge_state.items():
            if target != service:
                continue
            out[caller] = desired.get(caller, st.attempts)
        return out

    def _make_change(
        self, service: str, transition: str, metric: str, lines: list, desired: dict
    ) -> Change:
        resulting = self._resulting_attempts(service, desired)
        return Change(
            service,
            transition,
            frozenset(c for c, attempts in resulting.items() if attempts == 0),
            metric,
            lines,
            desired,
            {c: a for c, a in resulting.items() if a != self.attempts_on},
        )

    def _ramp_tick(
        self, state: ServiceState, value: float, timestamp: str
    ) -> Optional[str]:
        """One tick at 1..attempts_on-1. Returns 'shed', 'climb', or None."""
        limit = climb_rpr_limit(state.attempts, self.attempts_on, self.rpr_threshold)
        if value <= limit:
            _open_low(state, timestamp)
        elif value > self.rpr_threshold:
            _open_high(state, timestamp)
        else:
            # Above the climb bar and at or under the shed bar: hold.
            _clear_streaks(state)
        if streak_met(state.high_since, timestamp, self.interval):
            return "shed"
        climb_s = climb_interval_s(state.attempts, self.interval)
        if streak_met(state.low_since, timestamp, climb_s):
            return "climb"
        return None

    def step(
        self,
        rpr: dict,
        rejection: dict,
        rpr_ts: Optional[dict] = None,
        rejection_ts: Optional[dict] = None,
    ) -> list:
        changes = []
        handled = set()
        rpr_ts = rpr_ts or {}
        rejection_ts = rejection_ts or {}

        # Fallback: per-service rejection rate while any edge is at 0 attempts.
        # A quiet interval (rejection under the 0.10 re-enable bar, not the
        # 0.20 rejection_threshold) moves those edges to 1, not to attempts_on.
        for service, st in self.svc_state.items():
            value = rejection.get(service)
            timestamp = rejection_ts.get(service)
            if value is None or not timestamp:
                continue
            if (
                apply_algorithm1(
                    st, value, self.reenable_rejection_threshold, self.interval,
                    timestamp,
                )
                != "ON"
            ):
                continue
            desired = {
                caller: 1
                for (caller, target), est in self.edge_state.items()
                if target == service and est.attempts == 0
            }
            if not desired:
                continue
            elapsed = int(round(streak_elapsed_s(st.low_since, timestamp)))
            changes.append(
                self._make_change(
                    service,
                    "ON",
                    "rejection",
                    [(
                        service, "OFF", "ON", value, st.consecutive_low, 1, 0,
                        elapsed,
                    )],
                    desired,
                )
            )
            handled.add(service)

        pending: Dict[str, dict] = {}
        pending_lines: Dict[str, list] = {}
        for edge, st in self.edge_state.items():
            caller, service = edge
            if st.attempts <= 0 or service in handled:
                continue
            value = rpr.get(edge)
            timestamp = rpr_ts.get(edge)
            if value is None or not timestamp:
                continue
            name = f"{caller}->{service}"
            if st.attempts >= self.attempts_on:
                if (
                    apply_algorithm1(
                        st, value, self.rpr_threshold, self.interval, timestamp
                    )
                    != "OFF"
                ):
                    continue
                elapsed = int(round(streak_elapsed_s(st.high_since, timestamp)))
                pending.setdefault(service, {})[caller] = 0
                pending_lines.setdefault(service, []).append(
                    (
                        name, "ON", "OFF", value, st.consecutive_high, 0,
                        st.attempts, elapsed,
                    )
                )
                continue
            action = self._ramp_tick(st, value, timestamp)
            if action == "shed":
                elapsed = int(round(streak_elapsed_s(st.high_since, timestamp)))
                pending.setdefault(service, {})[caller] = 0
                pending_lines.setdefault(service, []).append(
                    (
                        name, "ON", "OFF", value, st.consecutive_high, 0,
                        st.attempts, elapsed,
                    )
                )
            elif action == "climb":
                elapsed = int(round(streak_elapsed_s(st.low_since, timestamp)))
                nxt = st.attempts + 1
                pending.setdefault(service, {})[caller] = nxt
                pending_lines.setdefault(service, []).append(
                    (
                        name, str(st.attempts), str(nxt), value,
                        st.consecutive_low, nxt, st.attempts, elapsed,
                    )
                )
        for service, desired in pending.items():
            climbs = any(attempts > 0 for attempts in desired.values())
            transition = "RAMP" if climbs and 0 not in desired.values() else "OFF"
            changes.append(
                self._make_change(
                    service, transition, "rpr", pending_lines[service], desired
                )
            )
        return changes

    def commit(self, change: Change) -> None:
        for caller, attempts in change.desired_attempts.items():
            edge = (caller, change.service)
            prev = self.edge_state[edge]
            if attempts == 0:
                prev.retries_state = "OFF"
                prev.attempts = 0
                _clear_streaks(prev)
            elif prev.attempts == 0:
                # Fresh streaks. A sibling that stayed above 0 is not in this map.
                self.edge_state[edge] = ServiceState(attempts=attempts)
            else:
                prev.attempts = attempts
                prev.retries_state = "ON"
                _clear_streaks(prev)
        if self.off_callers(change.service):
            self.svc_state.setdefault(
                change.service, ServiceState(retries_state="OFF", attempts=0)
            )
        else:
            self.svc_state.pop(change.service, None)


def run_edge_rpr(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    """Edge mode: retries per request per edge, rejection rate per callee as fallback."""
    if "retries_threshold" not in params:
        raise SystemExit("[retryguard] retry_metric=edge_rpr needs retries_threshold")
    sample_interval = int(params["sample_interval_seconds"])
    interval = int(params["interval_samples"])
    rejection_threshold = float(params["rejection_threshold"])
    rpr_threshold = float(params["retries_threshold"])
    attempts_on = int(params["retry_attempts_on"])
    per_try_timeout_ms = int(params["per_try_timeout_ms"])

    wait_for_inbound_csv(record_path)

    ctrl = EdgeController(
        CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval, attempts_on
    )
    inbound = InboundCsvTailer(record_path / INBOUND_CSV_NAME)
    edges = EdgesCsvTailer(record_path / EDGES_CSV_NAME)
    prev_in: Dict[str, Optional[InboundSnapshot]] = {s: None for s in CONTROLLED_SERVICES}
    prev_edge: Dict[tuple, Optional[EdgeSnapshot]] = {e: None for e in CONTROLLED_EDGES}
    log.info(
        "%s  START  metric=edge_rpr rpr_threshold=%.2f rejection_threshold=%.2f "
        "reenable_rejection=%.2f sample_interval=%ss interval_samples=%ds "
        "edges=%d attempts_on=%d",
        utc_now(), rpr_threshold, rejection_threshold,
        ctrl.reenable_rejection_threshold,
        sample_interval, interval, len(CONTROLLED_EDGES), attempts_on,
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break
        inbound.poll()
        edges.poll()

        rpr = {}
        rpr_ts = {}
        for edge in CONTROLLED_EDGES:
            rpr[edge], prev_edge[edge] = measure_edge_rpr(
                prev_edge[edge], edges.latest.get(edge)
            )
            snap = prev_edge[edge]
            if rpr[edge] is not None and snap is not None:
                rpr_ts[edge] = snap.timestamp
        rejection = {}
        rejection_ts = {}
        for service in CONTROLLED_SERVICES:
            rejection[service], prev_in[service] = measure_inbound_rejection(
                prev_in[service],
                inbound.latest.get(service),
                service in GRPC_RETRY_CALLEES,
            )
            snap = prev_in[service]
            if rejection[service] is not None and snap is not None:
                rejection_ts[service] = snap.timestamp

        changes = ctrl.step(rpr, rejection, rpr_ts, rejection_ts)

        for edge, st in ctrl.edge_state.items():
            if st.attempts > 0 and rpr.get(edge) is not None:
                since = st.high_since if st.consecutive_high else st.low_since
                elapsed = int(round(streak_elapsed_s(since, rpr_ts.get(edge))))
                log.info(
                    "%s  OBSERVE  %s->%s  rpr=%.4f  low=%d high=%d  elapsed_s=%d  "
                    "attempts=%d  state=ON  metric=rpr",
                    utc_now(), edge[0], edge[1], rpr[edge],
                    st.consecutive_low, st.consecutive_high, elapsed, st.attempts,
                )
        for service, st in ctrl.svc_state.items():
            if rejection.get(service) is not None:
                since = st.high_since if st.consecutive_high else st.low_since
                elapsed = int(round(streak_elapsed_s(since, rejection_ts.get(service))))
                log.info(
                    "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  elapsed_s=%d  "
                    "state=OFF  metric=rejection",
                    utc_now(), service, rejection[service],
                    st.consecutive_low, st.consecutive_high, elapsed,
                )

        for change in changes:
            try:
                patch_virtualservice(
                    api, change.service, attempts_on, per_try_timeout_ms,
                    caller_attempts=change.caller_attempts,
                )
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.info(
                    "%s  PATCH_FAIL  %s  %s  error=%s",
                    utc_now(), change.service, change.transition, exc,
                )
                continue
            label = "rpr" if change.metric == "rpr" else "rejection"
            for (
                name, old, new, value, count, attempts, from_attempts, elapsed_s
            ) in change.lines:
                counter = "consecutive_high" if new == "OFF" else "consecutive_low"
                log.info(
                    "%s  %s  %s→%s   %s=%.2f  %s=%d  attempts=%d  "
                    "from_attempts=%d  metric=%s  elapsed_s=%d",
                    utc_now(), name, old, new, label, value,
                    counter, count, attempts, from_attempts, change.metric,
                    elapsed_s,
                )
            ctrl.commit(change)

    log.info("%s  EXIT", utc_now())


def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    metric = params.get("retry_metric", "rejection")
    if metric == "edge_rpr":
        return run_edge_rpr(params, record_path, api)
    if metric != "rejection":
        raise SystemExit(f"[retryguard] unknown retry_metric: {metric!r}")
    sample_interval = int(params["sample_interval_seconds"])
    interval = int(params["interval_samples"])
    threshold = float(params["rejection_threshold"])
    attempts_on = int(params["retry_attempts_on"])
    attempts_off = int(params["retry_attempts_off"])
    per_try_timeout_ms = int(params["per_try_timeout_ms"])

    wait_for_inbound_csv(record_path)

    states = {svc: ServiceState() for svc in CONTROLLED_SERVICES}
    previous: Dict[str, Optional[InboundSnapshot]] = {
        svc: None for svc in CONTROLLED_SERVICES
    }
    inbound_path = record_path / INBOUND_CSV_NAME
    tailer = InboundCsvTailer(inbound_path)
    log.info(
        "%s  START  threshold=%.2f sample_interval=%ss interval_samples=%ds "
        "services=%s",
        utc_now(),
        threshold,
        sample_interval,
        interval,
        list(CONTROLLED_SERVICES),
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        tailer.poll()
        for service in CONTROLLED_SERVICES:
            current = tailer.latest.get(service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current, service in GRPC_RETRY_CALLEES
            )
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this sample",
                    utc_now(),
                    service,
                )
                continue

            state = states[service]
            row_ts = previous[service].timestamp
            desired = apply_algorithm1(
                state, rejection, threshold, interval, row_ts
            )
            since = state.high_since if state.consecutive_high else state.low_since
            elapsed = int(round(streak_elapsed_s(since, row_ts)))

            log.info(
                "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  elapsed_s=%d  "
                "state=%s",
                utc_now(),
                service,
                rejection,
                state.consecutive_low,
                state.consecutive_high,
                elapsed,
                state.retries_state,
            )

            if desired is None:
                continue

            attempts = attempts_on if desired == "ON" else attempts_off
            old = state.retries_state
            try:
                patch_virtualservice(api, service, attempts, per_try_timeout_ms)
            except ApiException as exc:
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  attempts=%d  "
                    "http=%s  reason=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    attempts,
                    exc.status,
                    exc.reason,
                )
                continue
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  error=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    exc,
                )
                continue

            counter = (
                f"consecutive_low={state.consecutive_low}"
                if desired == "ON"
                else f"consecutive_high={state.consecutive_high}"
            )
            log.info(
                "%s  %s  %s→%s   rejection=%.2f  %s  attempts=%d  elapsed_s=%d",
                utc_now(),
                service,
                old,
                desired,
                rejection,
                counter,
                attempts,
                elapsed,
            )
            state.retries_state = desired

    log.info("%s  EXIT", utc_now())


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RetryGuard Algorithm 1 controller (rejection-based)."
    )
    parser.add_argument(
        "--params",
        required=True,
        help="Path to RetryGuard params JSON "
        "(rejection_threshold, sample_interval_seconds, interval_samples, ...)",
    )
    args = parser.parse_args()

    params = load_params(args.params)
    record_path = load_record_path()
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    api = make_custom_api()
    run(params, record_path, api)


if __name__ == "__main__":
    main()
