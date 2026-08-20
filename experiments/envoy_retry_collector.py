#!/usr/bin/env python3
"""
envoy_retry_collector.py — Scrapes Envoy sidecar outbound retry counters.

Usage (on master, with venv active):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json

Envoy records retry stats on the *caller's* outbound cluster, not the callee.
This collector scrapes frontend and checkoutservice sidecars via:

    kubectl exec <pod> -c istio-proxy -- curl -s http://localhost:15000/stats

and writes cumulative counters to:
    {record_path}/envoy_retries_{caller}.csv

Retries-per-request is derived at analysis time by differencing consecutive rows.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

# Caller deployment (app label) → outbound target services whose retry
# counters we extract from that caller's Envoy sidecar.
CALLER_TARGET_MAP: Dict[str, List[str]] = {
    "frontend": [
        "cartservice",
        "productcatalogservice",
        "checkoutservice",
    ],
    "checkoutservice": [
        "cartservice",
        "productcatalogservice",
        "paymentservice",
    ],
}

METRIC_NAMES = (
    "upstream_rq_total",
    "upstream_rq_retry",
    "upstream_rq_retry_success",
    "upstream_rq_retry_limit_exceeded",
)

CSV_COLUMNS = [
    "timestamp",
    "target_service",
    "upstream_rq_total",
    "upstream_rq_retry",
    "upstream_rq_retry_success",
    "upstream_rq_retry_limit_exceeded",
]

# cluster.outbound|<port>||<svc>.default.svc.cluster.local.<metric>: <value>
STAT_RE = re.compile(
    r"^cluster\.outbound\|[^|]*\|[^|]*\|"
    r"(?P<target>[\w-]+)\.default\.svc\.cluster\.local\."
    r"(?P<metric>"
    + "|".join(METRIC_NAMES)
    + r"): (?P<value>\d+)$"
)

DEFAULT_POLL_INTERVAL_SECONDS = 5
KUBECTL_TIMEOUT_SECONDS = 15
NAMESPACE = "default"

CommandRunner = Callable[[List[str]], object]

# --------------------------------------------------------------------------- #
#  Logging / shutdown
# --------------------------------------------------------------------------- #

log = logging.getLogger("envoy_retry_collector")
_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_now(), signum)


def setup_logging(record_path: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    log_file = record_path / "envoy_retry_collector.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        print(
            f"[envoy_retry_collector] WARN: cannot open {log_file}: {exc}",
            file=sys.stderr,
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #

def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_record_path(global_config_path: str = GLOBAL_CONFIG_PATH) -> Path:
    with open(global_config_path, "r", encoding="utf-8") as f:
        gcfg = json.load(f)
    return Path(gcfg["record_path"])


def resolve_caller_map(params: dict) -> Dict[str, List[str]]:
    override = params.get("caller_target_map")
    if override:
        return {str(k): list(v) for k, v in override.items()}
    return {k: list(v) for k, v in CALLER_TARGET_MAP.items()}


# --------------------------------------------------------------------------- #
#  Default command runner (subprocess)
# --------------------------------------------------------------------------- #

def default_run_cmd(cmd: List[str]) -> SimpleResult:
    """Run a kubectl command; raises TimeoutError on timeout."""
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(str(exc)) from exc
    return SimpleResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


class SimpleResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# --------------------------------------------------------------------------- #
#  Pure parsing / CSV
# --------------------------------------------------------------------------- #

def _empty_stats() -> Dict[str, int]:
    return {name: 0 for name in METRIC_NAMES}


def parse_retry_stats(
    stats_text: str, targets: List[str]
) -> Dict[str, Dict[str, int]]:
    """
    Extract outbound retry counters for the given target services.

    Always returns an entry for every target (missing metrics → 0).
    """
    result: Dict[str, Dict[str, int]] = {t: _empty_stats() for t in targets}
    target_set = set(targets)

    for line in stats_text.splitlines():
        m = STAT_RE.match(line.strip())
        if not m:
            continue
        target = m.group("target")
        if target not in target_set:
            continue
        result[target][m.group("metric")] = int(m.group("value"))

    return result


def write_csv_row(
    csv_path: Path,
    timestamp: str,
    target: str,
    stats: Dict[str, int],
) -> None:
    """Append one row; write header if the file does not yet exist."""
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "target_service": target,
            "upstream_rq_total": stats.get("upstream_rq_total", 0),
            "upstream_rq_retry": stats.get("upstream_rq_retry", 0),
            "upstream_rq_retry_success": stats.get("upstream_rq_retry_success", 0),
            "upstream_rq_retry_limit_exceeded": stats.get(
                "upstream_rq_retry_limit_exceeded", 0
            ),
        })


# --------------------------------------------------------------------------- #
#  kubectl helpers
# --------------------------------------------------------------------------- #

def discover_pod_name(
    caller: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    """Return the first Running-ish pod name for app=<caller>, or None."""
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"app={caller}",
        "-o", "jsonpath={.items[0].metadata.name}",
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — keep poll loop alive
        log.warning("%s  WARNING  discover %s failed: %s", utc_now(), caller, exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  discover %s exit=%s stderr=%s",
            utc_now(),
            caller,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    name = (getattr(result, "stdout", "") or "").strip()
    return name or None


def fetch_stats_text(
    pod: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    """kubectl exec into istio-proxy and curl Envoy admin /stats."""
    runner = run_cmd or default_run_cmd
    cmd = [
        "kubectl", "exec", pod,
        "-n", namespace,
        "-c", "istio-proxy",
        "--",
        "curl", "-s", "http://localhost:15000/stats",
    ]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — TimeoutError etc.
        log.warning("%s  WARNING  fetch stats %s failed: %s", utc_now(), pod, exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  fetch stats %s exit=%s stderr=%s",
            utc_now(),
            pod,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    return getattr(result, "stdout", None)


# --------------------------------------------------------------------------- #
#  Poll loop
# --------------------------------------------------------------------------- #

def poll_once(
    record_path: Path,
    caller_map: Dict[str, List[str]],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    pod_cache: Optional[Dict[str, str]] = None,
) -> None:
    """
    One scrape of every caller sidecar. Writes rows into
    envoy_retries_{caller}.csv. Survives per-caller failures.
    """
    if pod_cache is None:
        pod_cache = {}
    runner = run_cmd or default_run_cmd

    for caller, targets in sorted(caller_map.items()):
        pod = pod_cache.get(caller)
        if not pod:
            pod = discover_pod_name(caller, run_cmd=runner)
            if pod:
                pod_cache[caller] = pod
            else:
                log.warning(
                    "%s  WARNING  no pod for caller=%s", utc_now(), caller
                )
                continue

        stats_text = fetch_stats_text(pod, run_cmd=runner)
        if stats_text is None:
            # Pod may have restarted — drop cache so next poll rediscovers.
            pod_cache.pop(caller, None)
            continue

        parsed = parse_retry_stats(stats_text, targets)
        csv_path = record_path / f"envoy_retries_{caller}.csv"
        for target in targets:
            write_csv_row(csv_path, timestamp, target, parsed[target])


def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    max_polls: Optional[int] = None,
) -> None:
    """
    Main loop. Sleeps poll_interval_seconds between scrapes until SIGTERM
    or max_polls (used by tests).
    """
    caller_map = resolve_caller_map(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    pod_cache: Dict[str, str] = {}

    log.info(
        "%s  START  poll_interval=%ss callers=%s",
        utc_now(),
        interval,
        sorted(caller_map.keys()),
    )

    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        poll_once(
            record_path,
            caller_map,
            timestamp=utc_now(),
            run_cmd=run_cmd,
            pod_cache=pod_cache,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
        # Sleep in 1s slices so SIGTERM is noticed promptly.
        for _ in range(interval):
            if _shutdown:
                break
            time.sleep(1)

    log.info("%s  EXIT", utc_now())


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envoy sidecar outbound retry-stats collector."
    )
    parser.add_argument(
        "--params",
        required=True,
        help="Path to collector params JSON "
        "(poll_interval_seconds, optional caller_target_map)",
    )
    args = parser.parse_args()

    params = load_params(args.params)
    record_path = load_record_path()
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    run_collector(params, record_path)


if __name__ == "__main__":
    main()
