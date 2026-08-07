#!/usr/bin/env python3
"""
retryguard.py — Rejection-based productive-retry controller (RetryGuard paper, Sec. 4, Algorithm 1).

Usage (on master, with venv active):
    python3 retryguard.py --params /tmp/retryguard_params.json

Reads per-endpoint rejection rates from metric_collector CSV logs, aggregates
them to Online Boutique services, and patches Istio VirtualService
retries.attempts when consecutive windows cross the threshold.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import signal
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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

# Locust endpoint → Online Boutique K8s service name.
# Multiple endpoints may map to the same service; aggregation uses max().
ENDPOINT_SERVICE_MAP = {
    "getproduct": "productcatalogservice",
    "postcheckout": "checkoutservice",
    "getcart": "cartservice",
    "postcart": "cartservice",
    "emptycart": "cartservice",
}

VS_GROUP = "networking.istio.io"
VS_VERSION = "v1alpha3"
VS_PLURAL = "virtualservices"
VS_NAMESPACE = "default"
RETRY_ON = "5xx,reset,connect-failure"

STARTUP_POLL_SECONDS = 5
STARTUP_TIMEOUT_SECONDS = 60

REQUIRED_PARAMS = (
    "rejection_threshold",
    "window_duration_seconds",
    "disable_windows",
    "re_enable_windows",
    "retry_attempts_on",
    "retry_attempts_off",
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


def service_endpoint_map() -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = defaultdict(list)
    for endpoint, service in ENDPOINT_SERVICE_MAP.items():
        mapping[service].append(endpoint)
    return dict(mapping)


# --------------------------------------------------------------------------- #
#  Metric reading
# --------------------------------------------------------------------------- #

def read_rejection_rate(csv_path: Path, window_rows: int) -> Optional[float]:
    """
    Mean(Fail / RPS) over the last window_rows data rows.
    Returns None if the file is missing or has no usable data rows.
    Rows with RPS == 0 contribute rejection rate 0 (no load ≠ overload).
    """
    if not csv_path.is_file():
        return None

    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except OSError:
        return None

    if not rows:
        return None

    window = rows[-window_rows:]
    rates = []
    for row in window:
        try:
            rps = float(row["RPS"])
            fail = float(row["Fail"])
        except (KeyError, TypeError, ValueError):
            continue
        if rps <= 0:
            rates.append(0.0)
        else:
            rates.append(fail / rps)

    if not rates:
        return None
    return sum(rates) / len(rates)


def service_rejection_rate(
    service: str,
    endpoints: List[str],
    record_path: Path,
    window_rows: int,
) -> Optional[float]:
    """Max rejection rate across endpoints mapped to this service."""
    rates = []
    for ep in endpoints:
        rate = read_rejection_rate(record_path / f"{ep}.csv", window_rows)
        if rate is not None:
            rates.append(rate)
    if not rates:
        return None
    return max(rates)


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


def wait_for_csvs(record_path: Path, endpoints: List[str]) -> None:
    """Poll until at least one endpoint CSV exists, or exit after timeout."""
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    log.info(
        "%s  WAITING  for metric_collector CSVs under %s (timeout=%ss)",
        utc_now(),
        record_path,
        STARTUP_TIMEOUT_SECONDS,
    )
    while time.time() < deadline:
        if _shutdown:
            raise SystemExit(0)
        for ep in endpoints:
            if (record_path / f"{ep}.csv").is_file():
                log.info("%s  READY  found %s.csv", utc_now(), ep)
                return
        time.sleep(STARTUP_POLL_SECONDS)
    raise SystemExit(
        f"[retryguard] ERROR: no CSV files under {record_path} "
        f"after {STARTUP_TIMEOUT_SECONDS}s — is metric_collector running?"
    )


# --------------------------------------------------------------------------- #
#  Main control loop (Algorithm 1)
# --------------------------------------------------------------------------- #

def apply_algorithm1(
    state: ServiceState,
    rejection: float,
    threshold: float,
    re_enable_windows: int,
    disable_windows: int,
) -> Optional[str]:
    """
    One Algorithm 1 iteration. Mutates state counters.
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

    # Lines 13–14 (asymmetric Interval: re_enable vs disable)
    desired = state.retries_state
    if state.consecutive_low >= re_enable_windows:
        desired = "ON"
    elif state.consecutive_high >= disable_windows:
        desired = "OFF"

    if desired != state.retries_state:
        return desired
    return None


def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    svc_map = service_endpoint_map()
    endpoints = list(ENDPOINT_SERVICE_MAP.keys())
    window_rows = int(params["window_duration_seconds"])
    threshold = float(params["rejection_threshold"])
    re_enable_windows = int(params["re_enable_windows"])
    disable_windows = int(params["disable_windows"])
    attempts_on = int(params["retry_attempts_on"])
    attempts_off = int(params["retry_attempts_off"])

    wait_for_csvs(record_path, endpoints)

    states = {svc: ServiceState() for svc in svc_map}
    log.info(
        "%s  START  threshold=%.2f window=%ss disable_windows=%d "
        "re_enable_windows=%d services=%s",
        utc_now(),
        threshold,
        window_rows,
        disable_windows,
        re_enable_windows,
        sorted(svc_map.keys()),
    )

    while not _shutdown:
        time.sleep(window_rows)
        if _shutdown:
            break

        for service, eps in sorted(svc_map.items()):
            rejection = service_rejection_rate(
                service, eps, record_path, window_rows
            )
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this window",
                    utc_now(),
                    service,
                )
                continue

            state = states[service]
            desired = apply_algorithm1(
                state,
                rejection,
                threshold,
                re_enable_windows,
                disable_windows,
            )

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
                patch_virtualservice(api, service, attempts)
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
        "(rejection_threshold, window_duration_seconds, ...)",
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
