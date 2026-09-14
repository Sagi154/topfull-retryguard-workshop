#!/usr/bin/env python3
"""
retryguard.py — Rejection-based productive-retry controller (RetryGuard paper, Sec. 4, Algorithm 1).

Usage (on master, with venv active):
    python3 retryguard.py --params /tmp/retryguard_params.json

Reads {record_path}/service_inbound.csv (Δ5xx / Δtotal per service) and
patches Istio VirtualService retries.attempts when Interval consecutive
samples cross the threshold (RetryGuard paper Algorithm 1, applied
literally: 1 raw sample per second, one symmetric Interval for both the
disable and re-enable transitions).
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


@dataclass(frozen=True)
class InboundSnapshot:
    timestamp: str
    total: float
    five_xx: float
    resets: float = 0.0  # downstream_rq_rx_reset (per-try timeout aborts)


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
            )
        except (KeyError, TypeError, ValueError):
            continue
    return latest


def measure_inbound_rejection(
    previous: Optional[InboundSnapshot],
    current: Optional[InboundSnapshot],
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
    if delta_total <= 0:
        return 0.0, current
    return delta_failures / delta_total, current


# --------------------------------------------------------------------------- #
#  VirtualService patching
# --------------------------------------------------------------------------- #

def make_custom_api():
    try:
        config.load_kube_config()
    except config.ConfigException:
        config.load_incluster_config()
    return client.CustomObjectsApi()


def patch_virtualservice(
    api: client.CustomObjectsApi,
    service_name: str,
    attempts: int,
    per_try_timeout_ms: int = 500,
    namespace: str = VS_NAMESPACE,
) -> None:
    """
    GET the existing VirtualService, then merge-patch retries while
    preserving the existing route (Istio rejects an http rule with no route).

    Istio validation rejects ``retries.attempts: 0`` while a retry policy is
    still present (``retryOn`` etc.). To disable retries we omit the
    ``retries`` block entirely; merge-patch replaces the ``http`` array so
    the old retries key is dropped.
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

    http_rule: dict = {"route": route}
    if int(attempts) > 0:
        http_rule["retries"] = {
            "attempts": int(attempts),
            "retryOn": RETRY_ON,
            "perTryTimeout": f"{per_try_timeout_ms}ms",
        }

    body = {"spec": {"http": [http_rule]}}

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

def apply_algorithm1(
    state: ServiceState,
    rejection: float,
    threshold: float,
    interval: int,
) -> Optional[str]:
    """
    One Algorithm 1 iteration. Mutates state counters.
    `interval` is the paper's single `Interval` parameter, applied
    symmetrically to both the ON (line 13) and OFF (line 14) transitions.
    Returns desired retries state ("ON"/"OFF") if a transition should fire,
    otherwise None (keep current state).
    """
    # Lines 5–12
    if rejection < threshold:
        state.consecutive_low += 1
        state.consecutive_high = 0
    elif rejection > threshold:
        state.consecutive_high += 1
        state.consecutive_low = 0
    else:
        # Exactly == Threshold (float rarity): reset both counters
        state.consecutive_low = 0
        state.consecutive_high = 0

    # Lines 13–14 (single symmetric Interval, per the paper)
    desired = state.retries_state
    if state.consecutive_low >= interval:
        desired = "ON"
    elif state.consecutive_high >= interval:
        desired = "OFF"

    if desired != state.retries_state:
        return desired
    return None


def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
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
    log.info(
        "%s  START  threshold=%.2f sample_interval=%ss interval_samples=%d "
        "(%ds) services=%s",
        utc_now(),
        threshold,
        sample_interval,
        interval,
        sample_interval * interval,
        list(CONTROLLED_SERVICES),
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        for service in CONTROLLED_SERVICES:
            current = read_latest_inbound_row(inbound_path, service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this sample",
                    utc_now(),
                    service,
                )
                continue

            state = states[service]
            desired = apply_algorithm1(state, rejection, threshold, interval)

            log.info(
                "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  state=%s",
                utc_now(),
                service,
                rejection,
                state.consecutive_low,
                state.consecutive_high,
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
                "%s  %s  %s→%s   rejection=%.2f  %s  attempts=%d",
                utc_now(),
                service,
                old,
                desired,
                rejection,
                counter,
                attempts,
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
