#!/usr/bin/env python3
"""
topfull_throttle_collector.py — Layer A (admission cap + admitted RPS) and
Layer B (reconstructed detector overload bool) on a wall-clock-aligned 1s grid.

Usage (on master, with venv active):
    python3 topfull_throttle_collector.py --params /tmp/topfull_throttle_params.json
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
from typing import Callable, Dict, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

LOCUST_APIS: List[str] = [
    "getproduct",
    "postcheckout",
    "getcart",
    "postcart",
    "emptycart",
]

DEFAULT_POLL_INTERVAL_SECONDS = 1

THROTTLE_CSV_COLUMNS = ["timestamp", "api", "threshold", "admitted_rps"]
DETECT_CSV_COLUMNS = [
    "timestamp",
    "service",
    "cadvisor_cpu",
    "quota",
    "alpha",
    "utilization",
    "overloaded",
]

CPU_QUOTA: Dict[str, int] = {
    "cartservice": 1000,
    "currencyservice": 1000,
    "frontend": 1000,
    "adservice": 1000,
    "productcatalogservice": 500,
    "checkoutservice": 1000,
    "recommendationservice": 2000,
}
DEFAULT_QUOTA = 200
ALPHA_SPECIAL = frozenset({"productcatalogservice", "cartservice"})
DEFAULT_ALPHA = 0.8
SPECIAL_ALPHA = 0.95

DETECT_SERVICES: List[str] = [
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

CADVISOR_NAMESPACE = "cadvisor"
CADVISOR_PORT = 8080
CPU_SKIP_BELOW = 2.0

CommandRunner = Callable[[List[str]], object]
UrlFetcher = Callable[[str], str]

log = logging.getLogger("topfull_throttle_collector")
_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_now(), signum)


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


def setup_logging(record_path: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    log_file = record_path / "topfull_throttle_collector.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        print(
            f"[topfull_throttle_collector] WARN: cannot open {log_file}: {exc}",
            file=sys.stderr,
        )


def parse_proxy_stats(body: str) -> Dict[str, float]:
    """Parse Go-proxy `/stats` body: `name=value/` tokens."""
    result: Dict[str, float] = {}
    for token in body.strip().split("/"):
        token = token.strip()
        if not token or "=" not in token:
            continue
        name, _, raw = token.partition("=")
        try:
            result[name] = float(raw)
        except ValueError:
            continue
    return result


def read_thresholds(
    proxy_dir: Path, apis: Optional[List[str]] = None
) -> Dict[str, float]:
    """Read `rate_config/<api>` files. Missing/unreadable → 0.0."""
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    out: Dict[str, float] = {}
    for api in names:
        path = proxy_dir / api
        try:
            out[api] = float(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            out[api] = 0.0
    return out


def write_throttle_csv(
    csv_path: Path,
    timestamp: str,
    thresholds: Dict[str, float],
    admitted: Dict[str, float],
) -> None:
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=THROTTLE_CSV_COLUMNS)
        if write_header:
            w.writeheader()
        for api in LOCUST_APIS:
            w.writerow(
                {
                    "timestamp": timestamp,
                    "api": api,
                    "threshold": thresholds.get(api, 0.0),
                    "admitted_rps": admitted.get(api, 0.0),
                }
            )


def quota_for(service: str) -> int:
    return int(CPU_QUOTA.get(service, DEFAULT_QUOTA))


def alpha_for(service: str) -> float:
    return SPECIAL_ALPHA if service in ALPHA_SPECIAL else DEFAULT_ALPHA


def detect_metrics(service: str, cadvisor_cpu: float) -> Dict[str, object]:
    quota = quota_for(service)
    alpha = alpha_for(service)
    utilization = (cadvisor_cpu / quota) if quota else 0.0
    overloaded = 1 if utilization > alpha else 0
    return {
        "cadvisor_cpu": float(cadvisor_cpu),
        "quota": quota,
        "alpha": alpha,
        "utilization": utilization,
        "overloaded": overloaded,
    }


def parse_cadvisor_summary(body: str) -> Optional[float]:
    try:
        data = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    first = next(iter(data.values()))
    if not isinstance(first, dict):
        return None
    usage = first.get("latest_usage") or {}
    cpu = usage.get("cpu")
    try:
        return float(cpu)
    except (TypeError, ValueError):
        return None


def _pod_service_name(pod_name: str, services: List[str]) -> Optional[str]:
    for svc in sorted(services, key=len, reverse=True):
        if pod_name == svc or pod_name.startswith(svc + "-"):
            return svc
    return None


def container_ids_from_pod_list(
    pod_list: dict, services: List[str]
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {s: [] for s in services}
    for item in pod_list.get("items") or []:
        name = (item.get("metadata") or {}).get("name") or ""
        svc = _pod_service_name(name, services)
        if svc is None:
            continue
        for cs in (item.get("status") or {}).get("containerStatuses") or []:
            cname = cs.get("name") or ""
            if "proxy" in cname:
                continue
            cid = cs.get("containerID") or ""
            if "://" in cid:
                cid = cid.split("://", 1)[1]
            if cid:
                out[svc].append(cid)
    return out


def aggregate_cpu(values: List[float]) -> float:
    kept = [v for v in values if v > CPU_SKIP_BELOW]
    if not kept:
        return 0.0
    return sum(kept) / len(kept)


def write_detect_csv(
    csv_path: Path,
    timestamp: str,
    rows: Dict[str, Dict[str, object]],
) -> None:
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DETECT_CSV_COLUMNS)
        if write_header:
            w.writeheader()
        for service in DETECT_SERVICES:
            metrics = rows.get(service) or detect_metrics(service, 0.0)
            w.writerow(
                {
                    "timestamp": timestamp,
                    "service": service,
                    "cadvisor_cpu": metrics["cadvisor_cpu"],
                    "quota": metrics["quota"],
                    "alpha": metrics["alpha"],
                    "utilization": metrics["utilization"],
                    "overloaded": metrics["overloaded"],
                }
            )


class SimpleResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_global_config(global_config_path: str = GLOBAL_CONFIG_PATH) -> dict:
    with open(global_config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_run_cmd(cmd: List[str]) -> SimpleResult:
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(str(exc)) from exc
    return SimpleResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def default_fetch_url(url: str, timeout: float = 5.0) -> str:
    with urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _cadvisor_ips(run_cmd: CommandRunner) -> List[str]:
    r = run_cmd(
        [
            "kubectl",
            "get",
            "pod",
            "-n",
            CADVISOR_NAMESPACE,
            "-o",
            "jsonpath={.items[*].status.podIP}",
        ]
    )
    if getattr(r, "returncode", 1) != 0:
        return []
    return [p for p in (r.stdout or "").split() if p]


def _pod_list(run_cmd: CommandRunner) -> dict:
    r = run_cmd(["kubectl", "get", "po", "-n", "default", "-o", "json"])
    if getattr(r, "returncode", 1) != 0:
        return {}
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def scrape_cadvisor_cpu(
    run_cmd: CommandRunner, fetch_url: UrlFetcher
) -> Dict[str, float]:
    ips = _cadvisor_ips(run_cmd)
    ids = container_ids_from_pod_list(_pod_list(run_cmd), DETECT_SERVICES)
    out: Dict[str, float] = {}
    for service, cids in ids.items():
        values: List[float] = []
        for cid in cids:
            cpu: Optional[float] = None
            for ip in ips:
                url = (
                    f"http://{ip}:{CADVISOR_PORT}/api/v2.0/summary/"
                    f"{cid}?type=docker"
                )
                try:
                    cpu = parse_cadvisor_summary(fetch_url(url))
                except (OSError, URLError, TimeoutError):
                    cpu = None
                if cpu is not None:
                    break
            if cpu is not None:
                values.append(cpu)
        out[service] = aggregate_cpu(values)
    return out


def poll_once(
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
) -> None:
    runner = run_cmd or default_run_cmd
    fetcher = fetch_url or default_fetch_url
    thresholds = read_thresholds(proxy_dir)
    admitted: Dict[str, float] = {}
    try:
        admitted = parse_proxy_stats(fetcher(stats_url))
    except (OSError, URLError, TimeoutError) as exc:
        log.warning("%s  WARNING  stats fetch failed: %s", timestamp, exc)
    write_throttle_csv(
        record_path / "topfull_throttle.csv", timestamp, thresholds, admitted
    )
    cpu_by_svc: Dict[str, float] = {}
    try:
        cpu_by_svc = scrape_cadvisor_cpu(runner, fetcher)
    except (OSError, TimeoutError) as exc:
        log.warning("%s  WARNING  cadvisor scrape failed: %s", timestamp, exc)
    rows = {
        svc: detect_metrics(svc, cpu_by_svc.get(svc, 0.0))
        for svc in DETECT_SERVICES
    }
    write_detect_csv(record_path / "topfull_detect.csv", timestamp, rows)


def run_collector(
    params: dict,
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    max_polls: Optional[int] = None,
) -> None:
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    log.info("%s  START  poll_interval=%ss", utc_now(), interval)
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
            proxy_dir,
            stats_url,
            timestamp=ts,
            run_cmd=run_cmd,
            fetch_url=fetch_url,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
    log.info("%s  EXIT", utc_now())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TopFull throttle (Layer A) and detector (Layer B) collector."
    )
    parser.add_argument("--params", required=True, help="Path to collector params JSON")
    args = parser.parse_args()
    params = load_params(args.params)
    gcfg = load_global_config()
    record_path = Path(gcfg["record_path"])
    proxy_dir = Path(gcfg["proxy_dir"])
    stats_url = gcfg["proxy_url"].rstrip("/") + "/stats"
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_collector(params, record_path, proxy_dir, stats_url)


if __name__ == "__main__":
    main()
