#!/usr/bin/env python3
"""
resource_usage_collector.py — Scrapes per-service CPU/memory via kubelet stats/summary.

Usage (on master, with venv active):
    python3 resource_usage_collector.py --params /tmp/resource_usage_params.json

Writes one row per service per poll to:
    {record_path}/resource_usage.csv

Columns: timestamp, service, cpu_millicores, memory_working_set_bytes, replica_count
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

DEFAULT_SERVICES: List[str] = [
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

SKIP_CONTAINER_NAMES = frozenset({"istio-proxy", "POD"})

DEFAULT_POLL_INTERVAL_SECONDS = 5
KUBECTL_TIMEOUT_SECONDS = 30
NAMESPACE = "default"

CSV_COLUMNS = [
    "timestamp",
    "service",
    "cpu_millicores",
    "memory_working_set_bytes",
    "replica_count",
]

CommandRunner = Callable[[List[str]], object]

# --------------------------------------------------------------------------- #
#  Logging / shutdown
# --------------------------------------------------------------------------- #

log = logging.getLogger("resource_usage_collector")
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

    log_file = record_path / "resource_usage_collector.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        print(
            f"[resource_usage_collector] WARN: cannot open {log_file}: {exc}",
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


def resolve_services(params: dict) -> List[str]:
    override = params.get("services")
    if override:
        return list(override)
    return list(DEFAULT_SERVICES)


# --------------------------------------------------------------------------- #
#  Default command runner
# --------------------------------------------------------------------------- #

class SimpleResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def default_run_cmd(cmd: List[str]) -> SimpleResult:
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


# --------------------------------------------------------------------------- #
#  Pure parsing
# --------------------------------------------------------------------------- #

def pod_name_to_service(pod_name: str, services: List[str]) -> Optional[str]:
    """Map a pod name to a Boutique deployment/service name."""
    for svc in sorted(services, key=len, reverse=True):
        if pod_name == svc or pod_name.startswith(svc + "-"):
            return svc
    return None


def _container_usage(container: dict) -> Tuple[int, int]:
    """Return (cpu_millicores, memory_working_set_bytes) for one container."""
    cpu = container.get("cpu") or {}
    mem = container.get("memory") or {}
    nano = int(cpu.get("usageNanoCores") or 0)
    millicores = int(round(nano / 1_000_000))
    memory = int(mem.get("workingSetBytes") or 0)
    return millicores, memory


def parse_stats_summary(
    summary: dict,
    services: List[str],
    namespace: str = NAMESPACE,
) -> Dict[str, Tuple[int, int]]:
    """
    Extract per-service CPU (millicores) and memory (working set bytes).

    Sums app-container usage across replicas; skips istio-proxy and POD.
    Services with no matching pod are omitted (not zero-filled).
    """
    totals: Dict[str, Tuple[int, int]] = {}

    for pod in summary.get("pods") or []:
        pod_ref = pod.get("podRef") or {}
        if pod_ref.get("namespace") != namespace:
            continue
        pod_name = pod_ref.get("name") or ""
        service = pod_name_to_service(pod_name, services)
        if service is None:
            continue

        cpu_sum = 0
        mem_sum = 0
        found_app = False
        for container in pod.get("containers") or []:
            cname = container.get("name") or ""
            if cname in SKIP_CONTAINER_NAMES:
                continue
            millicores, memory = _container_usage(container)
            cpu_sum += millicores
            mem_sum += memory
            found_app = True

        if not found_app:
            continue

        prev_cpu, prev_mem = totals.get(service, (0, 0))
        totals[service] = (prev_cpu + cpu_sum, prev_mem + mem_sum)

    return totals


def parse_replica_counts(deploy_json: dict, services: List[str]) -> Dict[str, int]:
    """Ready replica count per deployment name."""
    counts: Dict[str, int] = {}
    for item in deploy_json.get("items") or []:
        name = (item.get("metadata") or {}).get("name")
        if name not in services:
            continue
        status = item.get("status") or {}
        ready = status.get("readyReplicas")
        counts[name] = int(ready) if ready is not None else 0
    return counts


def write_csv_rows(
    csv_path: Path,
    timestamp: str,
    usage_by_service: Dict[str, Tuple[int, int]],
    replica_counts: Dict[str, int],
    services: List[str],
) -> int:
    """
    Append one row per service that has usage data this poll.
    Returns number of rows written.
    """
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    rows_written = 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for service in services:
            if service not in usage_by_service:
                continue
            cpu_mc, mem_bytes = usage_by_service[service]
            writer.writerow({
                "timestamp": timestamp,
                "service": service,
                "cpu_millicores": cpu_mc,
                "memory_working_set_bytes": mem_bytes,
                "replica_count": replica_counts.get(service, 0),
            })
            rows_written += 1
    return rows_written


# --------------------------------------------------------------------------- #
#  kubectl helpers
# --------------------------------------------------------------------------- #

def discover_worker_node(
    run_cmd: Optional[CommandRunner] = None,
) -> Optional[str]:
    """
    Return the first Ready worker node name (non-control-plane), or any Ready
    node if only one exists.
    """
    runner = run_cmd or default_run_cmd
    cmd = ["kubectl", "get", "nodes", "-o", "json"]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover node failed: %s", utc_now(), exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  kubectl get nodes exit=%s stderr=%s",
            utc_now(),
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    try:
        data = json.loads(getattr(result, "stdout", "") or "{}")
    except json.JSONDecodeError as exc:
        log.warning("%s  WARNING  nodes JSON parse failed: %s", utc_now(), exc)
        return None

    workers: List[str] = []
    fallback: List[str] = []
    for item in data.get("items") or []:
        name = (item.get("metadata") or {}).get("name")
        if not name:
            continue
        labels = (item.get("metadata") or {}).get("labels") or {}
        ready = False
        for cond in (item.get("status") or {}).get("conditions") or []:
            if cond.get("type") == "Ready" and cond.get("status") == "True":
                ready = True
                break
        if not ready:
            continue
        fallback.append(name)
        is_control_plane = any(
            k.startswith("node-role.kubernetes.io/control-plane")
            or k.startswith("node-role.kubernetes.io/master")
            for k in labels
        )
        if not is_control_plane:
            workers.append(name)

    if workers:
        return workers[0]
    return fallback[0] if fallback else None


def fetch_stats_summary(
    node_name: str,
    run_cmd: Optional[CommandRunner] = None,
) -> Optional[dict]:
    runner = run_cmd or default_run_cmd
    path = f"/api/v1/nodes/{node_name}/proxy/stats/summary"
    cmd = ["kubectl", "get", "--raw", path]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "%s  WARNING  stats/summary node=%s failed: %s",
            utc_now(),
            node_name,
            exc,
        )
        return None

    if getattr(result, "returncode", 1) != 0:
        log.warning(
            "%s  WARNING  stats/summary node=%s exit=%s stderr=%s",
            utc_now(),
            node_name,
            getattr(result, "returncode", "?"),
            (getattr(result, "stderr", "") or "").strip(),
        )
        return None

    try:
        return json.loads(getattr(result, "stdout", "") or "{}")
    except json.JSONDecodeError as exc:
        log.warning(
            "%s  WARNING  stats/summary JSON parse failed: %s", utc_now(), exc
        )
        return None


def fetch_deployments_json(
    run_cmd: Optional[CommandRunner] = None,
    namespace: str = NAMESPACE,
) -> Optional[dict]:
    runner = run_cmd or default_run_cmd
    cmd = ["kubectl", "get", "deploy", "-n", namespace, "-o", "json"]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  get deploy failed: %s", utc_now(), exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        return None

    try:
        return json.loads(getattr(result, "stdout", "") or "{}")
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
#  Poll loop
# --------------------------------------------------------------------------- #

def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    node_cache: Optional[Dict[str, str]] = None,
) -> None:
    if node_cache is None:
        node_cache = {}

    runner = run_cmd or default_run_cmd
    node = node_cache.get("worker")
    if not node:
        node = discover_worker_node(run_cmd=runner)
        if node:
            node_cache["worker"] = node
        else:
            log.warning("%s  WARNING  no worker node discovered", utc_now())
            return

    summary = fetch_stats_summary(node, run_cmd=runner)
    if summary is None:
        node_cache.pop("worker", None)
        return

    usage = parse_stats_summary(summary, services)
    deploy_json = fetch_deployments_json(run_cmd=runner) or {}
    replicas = parse_replica_counts(deploy_json, services)

    csv_path = record_path / "resource_usage.csv"
    written = write_csv_rows(csv_path, timestamp, usage, replicas, services)
    if written == 0:
        log.warning(
            "%s  WARNING  no service rows written (pods=%d)",
            utc_now(),
            len(summary.get("pods") or []),
        )


def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    max_polls: Optional[int] = None,
) -> None:
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    node_cache: Dict[str, str] = {}

    log.info(
        "%s  START  poll_interval=%ss services=%d",
        utc_now(),
        interval,
        len(services),
    )

    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        poll_once(
            record_path,
            services,
            timestamp=utc_now(),
            run_cmd=run_cmd,
            node_cache=node_cache,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
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
        description="Per-service CPU/memory collector via kubelet stats/summary."
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
