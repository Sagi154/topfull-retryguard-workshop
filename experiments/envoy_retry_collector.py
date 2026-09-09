#!/usr/bin/env python3
"""
envoy_retry_collector.py — Scrapes Envoy sidecar stats for all Boutique services.

Usage (on master, with venv active):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json

Every poll scrapes each service's istio-proxy sidecar via:

    kubectl exec <pod> -c istio-proxy -- curl -s http://localhost:15000/stats

and appends rows to two shared CSVs under {record_path}/:
    service_edges.csv   — outbound upstream_rq_* per (caller, target)
    service_inbound.csv — inbound downstream_rq_* per service

Retries-per-request and offered-load deltas are derived at analysis time.
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

# All 11 Boutique Deployments (app label == Kubernetes Service name). Every
# pod is scraped every poll — no more hardcoded caller/target shortlist.
ALL_SERVICES: List[str] = [
    "frontend",
    "cartservice",
    "checkoutservice",
    "productcatalogservice",
    "paymentservice",
    "recommendationservice",
    "shippingservice",
    "currencyservice",
    "emailservice",
    "adservice",
    "redis-cart",
]

OUTBOUND_METRICS = ("total", "2xx", "4xx", "5xx", "retry")
INBOUND_METRICS = ("total", "2xx", "4xx", "5xx")

# cluster.outbound|<port>||<target>.default.svc.cluster.local.upstream_rq_<metric>: <value>
OUTBOUND_RE = re.compile(
    r"^cluster\.outbound\|[^|]*\|[^|]*\|"
    r"(?P<target>[\w-]+)\.default\.svc\.cluster\.local\."
    r"upstream_rq_(?P<metric>total|2xx|4xx|5xx|retry): (?P<value>\d+)$"
)

# http.inbound_<listener-id>.downstream_rq_<metric>: <value>
# (listener id is typically "<bind-ip>_<port>", e.g. "0.0.0.0_8080")
INBOUND_RE = re.compile(
    r"^http\.inbound_(?P<listener>[\w.]+)\.downstream_rq_"
    r"(?P<metric>total|2xx|4xx|5xx): (?P<value>\d+)$"
)

EDGES_CSV_COLUMNS = ["timestamp", "caller", "target", "total", "2xx", "4xx", "5xx", "retry"]
INBOUND_CSV_COLUMNS = ["timestamp", "service", "total", "2xx", "4xx", "5xx"]

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


def tick_timestamp(interval_seconds: int, now: Optional[float] = None) -> str:
    t = time.time() if now is None else now
    aligned = int(t // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(aligned, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def sleep_until_next_tick(
    interval_seconds: int,
    now: Optional[float] = None,
    sleeper: Optional[Callable[[float], None]] = None,
) -> None:
    t = time.time() if now is None else now
    next_tick = (int(t // interval_seconds) + 1) * interval_seconds
    delay = max(0.0, next_tick - t)
    (sleeper or time.sleep)(delay)


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

def parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]:
    """
    Parse outbound cluster stats into per-target metric dicts.

    Only targets that actually appear in stats_text are included — no
    fixed target list. Every distinct <target> seen in a
    cluster.outbound|...upstream_rq_* line gets a row, with any metric
    not present for that target defaulting to 0.
    """
    edges: Dict[str, Dict[str, int]] = {}
    for line in stats_text.splitlines():
        m = OUTBOUND_RE.match(line.strip())
        if not m:
            continue
        target = m.group("target")
        if target not in edges:
            edges[target] = {k: 0 for k in OUTBOUND_METRICS}
        edges[target][m.group("metric")] = int(m.group("value"))
    return edges


def parse_inbound(stats_text: str) -> Dict[str, int]:
    """
    Parse this pod's own inbound listener stats (downstream_rq_*).

    A pod can have more than one HTTP listener (e.g. separate ports);
    totals across listeners are summed into one row per pod/service.
    Always returns all four metrics (missing -> 0).
    """
    inbound = {k: 0 for k in INBOUND_METRICS}
    for line in stats_text.splitlines():
        m = INBOUND_RE.match(line.strip())
        if not m:
            continue
        inbound[m.group("metric")] += int(m.group("value"))
    return inbound


def write_edges_csv(
    csv_path: Path,
    timestamp: str,
    caller: str,
    edges: Dict[str, Dict[str, int]],
) -> None:
    """Append one row per (caller, target) pair; write header if new file."""
    if not edges:
        return
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EDGES_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for target in sorted(edges):
            m = edges[target]
            writer.writerow({
                "timestamp": timestamp,
                "caller": caller,
                "target": target,
                "total": m["total"],
                "2xx": m["2xx"],
                "4xx": m["4xx"],
                "5xx": m["5xx"],
                "retry": m["retry"],
            })


def write_inbound_csv(
    csv_path: Path,
    timestamp: str,
    service: str,
    inbound: Dict[str, int],
) -> None:
    """Append one row for this service's inbound totals this poll."""
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INBOUND_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "service": service,
            "total": inbound["total"],
            "2xx": inbound["2xx"],
            "4xx": inbound["4xx"],
            "5xx": inbound["5xx"],
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
#  Service list / poll loop
# --------------------------------------------------------------------------- #

def resolve_services(params: dict) -> List[str]:
    override = params.get("services")
    if override:
        return list(override)
    return list(ALL_SERVICES)


def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    pod_cache: Optional[Dict[str, str]] = None,
) -> None:
    """
    One scrape of every service's sidecar. Writes rows into
    service_edges.csv and service_inbound.csv. Survives per-service
    failures (a failed exec just skips that service this poll).
    """
    if pod_cache is None:
        pod_cache = {}
    runner = run_cmd or default_run_cmd

    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"

    for service in sorted(services):
        pod = pod_cache.get(service)
        if not pod:
            pod = discover_pod_name(service, run_cmd=runner)
            if pod:
                pod_cache[service] = pod
            else:
                log.warning("%s  WARNING  no pod for service=%s", utc_now(), service)
                continue

        stats_text = fetch_stats_text(pod, run_cmd=runner)
        if stats_text is None:
            pod_cache.pop(service, None)
            continue

        edges = parse_edges(stats_text)
        inbound = parse_inbound(stats_text)
        write_edges_csv(edges_path, timestamp, service, edges)
        write_inbound_csv(inbound_path, timestamp, service, inbound)


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
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    pod_cache: Dict[str, str] = {}

    log.info(
        "%s  START  poll_interval=%ss services=%d",
        utc_now(), interval, len(services),
    )

    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        ts = tick_timestamp(interval)
        poll_once(record_path, services, timestamp=ts, run_cmd=run_cmd, pod_cache=pod_cache)
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break

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
        "(poll_interval_seconds, optional services list)",
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
