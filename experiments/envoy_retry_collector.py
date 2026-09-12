#!/usr/bin/env python3
"""
envoy_retry_collector.py — Scrapes Envoy sidecar stats for all Boutique services.

Usage (on master, with venv active):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json

Usage (on worker, docker_local):
    python3 envoy_retry_collector.py --params /tmp/envoy_retry_params.json --exec-mode docker_local

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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
EXEC_MODE_KUBECTL = "kubectl"
EXEC_MODE_DOCKER_LOCAL = "docker_local"
DEFAULT_MAX_WORKERS = 4
TIER2_WARN_EVERY_POLLS = 30
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


def resolve_exec_mode(params: dict, cli_exec_mode: Optional[str] = None) -> str:
    if cli_exec_mode:
        return cli_exec_mode
    mode = params.get("exec_mode") or EXEC_MODE_KUBECTL
    if mode not in (EXEC_MODE_KUBECTL, EXEC_MODE_DOCKER_LOCAL):
        return EXEC_MODE_KUBECTL
    return mode


def resolve_record_path(
    params: dict, global_config_path: str = GLOBAL_CONFIG_PATH
) -> Path:
    override = params.get("record_path")
    if override:
        return Path(override)
    return load_record_path(global_config_path)


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


def docker_ps_container_id_cmd(pod_name: str, namespace: str = NAMESPACE) -> List[str]:
    return [
        "docker",
        "ps",
        "--filter",
        f"label=io.kubernetes.pod.name={pod_name}",
        "--filter",
        f"label=io.kubernetes.pod.namespace={namespace}",
        "--filter",
        "label=io.kubernetes.container.name=istio-proxy",
        "--format",
        "{{.ID}}",
    ]


def docker_exec_stats_cmd(container_id: str) -> List[str]:
    return [
        "docker",
        "exec",
        container_id,
        "curl",
        "-s",
        "http://localhost:15000/stats",
    ]


def discover_container_id(
    pod_name: str,
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[str]:
    """Return the live istio-proxy container ID for pod_name, or None."""
    runner = run_cmd or default_run_cmd
    cmd = docker_ps_container_id_cmd(pod_name, namespace=namespace)
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — keep poll loop alive
        log.warning("%s  WARNING  docker ps %s failed: %s", utc_now(), pod_name, exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  docker ps %s exit=%s stderr=%s",
            utc_now(),
            pod_name,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    lines = [
        line.strip()
        for line in (getattr(result, "stdout", "") or "").splitlines()
        if line.strip()
    ]
    return lines[0] if lines else None


def fetch_stats_text_docker(
    container_id: str,
    run_cmd: Optional[CommandRunner] = None,
) -> Optional[str]:
    """docker exec into the local istio-proxy container and curl /stats."""
    runner = run_cmd or default_run_cmd
    cmd = docker_exec_stats_cmd(container_id)
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001 — TimeoutError etc.
        log.warning(
            "%s  WARNING  docker exec %s failed: %s", utc_now(), container_id, exc
        )
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  docker exec %s exit=%s stderr=%s",
            utc_now(),
            container_id,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    return getattr(result, "stdout", None)


@dataclass
class ServiceScrapeResult:
    service: str
    edges: Optional[Dict[str, Dict[str, int]]] = None
    inbound: Optional[Dict[str, int]] = None
    container_id: Optional[str] = None
    evict_container: bool = False
    warning: Optional[str] = None


def should_log_tier2(service: str, poll_index: int, state: Dict[str, int]) -> bool:
    last = state.get(service)
    if last is None or poll_index - last >= TIER2_WARN_EVERY_POLLS:
        state[service] = poll_index
        return True
    return False


def scrape_one_service(
    service: str,
    pod_name: Optional[str],
    cached_container_id: Optional[str],
    run_cmd: CommandRunner,
) -> ServiceScrapeResult:
    """
    Read-only scrape for one service in docker_local mode.

    Does not write CSVs and does not mutate caches. Main thread applies
    evict / container_id after the batch completes.
    """
    if not pod_name:
        return ServiceScrapeResult(
            service=service, warning=f"no seeded pod for service={service}"
        )

    container_id = cached_container_id
    if not container_id:
        container_id = discover_container_id(pod_name, run_cmd=run_cmd)
        if not container_id:
            return ServiceScrapeResult(
                service=service,
                evict_container=True,
                warning=(
                    f"tier2 stale pod service={service} pod={pod_name} "
                    "(pod recreated? v1 does not re-seed)"
                ),
            )

    stats_text = fetch_stats_text_docker(container_id, run_cmd=run_cmd)
    if stats_text is None:
        return ServiceScrapeResult(
            service=service,
            evict_container=True,
            warning=f"docker exec failed service={service} container={container_id}",
        )

    return ServiceScrapeResult(
        service=service,
        edges=parse_edges(stats_text),
        inbound=parse_inbound(stats_text),
        container_id=container_id,
    )


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
    exec_mode: str = EXEC_MODE_KUBECTL,
    container_cache: Optional[Dict[str, str]] = None,
    pod_names: Optional[Dict[str, str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    poll_index: int = 0,
    tier2_warn_state: Optional[Dict[str, int]] = None,
) -> None:
    """
    One scrape of every service's sidecar. Writes rows into
    service_edges.csv and service_inbound.csv. Survives per-service
    failures (a failed exec just skips that service this poll).
    """
    if pod_cache is None:
        pod_cache = {}
    if container_cache is None:
        container_cache = {}
    if pod_names is None:
        pod_names = {}
    if tier2_warn_state is None:
        tier2_warn_state = {}
    runner = run_cmd or default_run_cmd

    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"

    if exec_mode == EXEC_MODE_DOCKER_LOCAL:
        workers = max(1, int(max_workers or DEFAULT_MAX_WORKERS))

        def _submit(service: str) -> ServiceScrapeResult:
            pod = pod_names.get(service)
            cached = container_cache.get(pod) if pod else None
            return scrape_one_service(service, pod, cached, runner)

        results: List[ServiceScrapeResult] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_submit, service): service for service in services}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001 — never crash poll_once
                    svc = futs[fut]
                    log.warning(
                        "%s  WARNING  scrape %s raised: %s", utc_now(), svc, exc
                    )
        _apply_scrape_results(
            results,
            pod_names,
            container_cache,
            edges_path,
            inbound_path,
            timestamp,
            poll_index,
            tier2_warn_state,
        )
        return

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


def _apply_scrape_results(
    results: List[ServiceScrapeResult],
    pod_names: Dict[str, str],
    container_cache: Dict[str, str],
    edges_path: Path,
    inbound_path: Path,
    timestamp: str,
    poll_index: int,
    tier2_warn_state: Dict[str, int],
) -> None:
    for result in sorted(results, key=lambda r: r.service):
        pod = pod_names.get(result.service)
        if result.evict_container and pod:
            container_cache.pop(pod, None)
        if result.container_id and pod and result.edges is not None:
            container_cache[pod] = result.container_id
        if result.warning:
            if "tier2" in result.warning:
                if should_log_tier2(result.service, poll_index, tier2_warn_state):
                    log.warning("%s  WARNING  %s", utc_now(), result.warning)
            else:
                log.warning("%s  WARNING  %s", utc_now(), result.warning)
        if result.edges is not None and result.inbound is not None:
            write_edges_csv(edges_path, timestamp, result.service, result.edges)
            write_inbound_csv(inbound_path, timestamp, result.service, result.inbound)


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
    exec_mode = resolve_exec_mode(params)
    pod_names = dict(params.get("pod_names") or {})
    max_workers = int(params.get("max_workers", DEFAULT_MAX_WORKERS))
    pod_cache: Dict[str, str] = dict(pod_names) if exec_mode == EXEC_MODE_KUBECTL else {}
    container_cache: Dict[str, str] = {}
    tier2_warn_state: Dict[str, int] = {}

    log.info(
        "%s  START  poll_interval=%ss services=%d exec_mode=%s max_workers=%s",
        utc_now(), interval, len(services), exec_mode, max_workers,
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
        poll_once(
            record_path,
            services,
            timestamp=ts,
            run_cmd=run_cmd,
            pod_cache=pod_cache,
            exec_mode=exec_mode,
            container_cache=container_cache,
            pod_names=pod_names,
            max_workers=max_workers,
            poll_index=polls,
            tier2_warn_state=tier2_warn_state,
        )
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
        "(poll_interval_seconds, optional services list, optional exec_mode)",
    )
    parser.add_argument(
        "--exec-mode",
        choices=[EXEC_MODE_KUBECTL, EXEC_MODE_DOCKER_LOCAL],
        default=None,
        help="Transport used to reach istio-proxy (default: params or kubectl)",
    )
    args = parser.parse_args()

    params = load_params(args.params)
    if args.exec_mode:
        params["exec_mode"] = args.exec_mode
    record_path = resolve_record_path(params)
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    run_collector(params, record_path)


if __name__ == "__main__":
    main()
