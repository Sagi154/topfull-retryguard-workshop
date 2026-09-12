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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, build_opener

import topfull_cpu_quotas

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
# Keep proxy scrapes well under the 1s tick. A 5s urlopen timeout
# (the previous default) stalled Layer A+B onto a ~6s grid whenever
# :8090/stats hung, which is what happened on S2 run7.
PROXY_FETCH_TIMEOUT_SECONDS = 0.8

THROTTLE_CSV_COLUMNS = [
    "timestamp",
    "api",
    "threshold",
    "admitted_rps",
    "threshold_fresh",
    "admitted_fresh",
]
DETECT_CSV_COLUMNS = [
    "timestamp",
    "service",
    "cadvisor_cpu",
    "quota",
    "alpha",
    "utilization",
    "overloaded",
]

# Paper table lives in topfull_cpu_quotas; keep DEFAULT_QUOTA as the
# Detector for-loop default (1000), never the unused module constant 200.
DEFAULT_QUOTA = topfull_cpu_quotas.DEFAULT_PAPER_LIMIT_MILLICORES
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


def proxy_scrape_config(proxy_url: str) -> Dict[str, str]:
    """How to scrape goproxy `/stats` and `/thresholds`.

    `:8090` is `goproxy`. Admin endpoints are OnRequest hooks that only fire
    for a *proxied* GET whose path contains `/stats` or `/thresholds` — the
    same pattern as `Detector.current_rps()`. A direct GET to
    `http://127.0.0.1:8090/stats` is a non-proxy request and returns HTTP 500
    (S2 run7 / run9 Layer A zeros).

    Use loopback as the HTTP *proxy* address; request `proxy_url + "/stats"`
    (GCE internal host, not 127.0.0.1) so NO_PROXY does not skip the proxy.
    """
    parsed = urlparse(proxy_url)
    port = parsed.port or 8090
    base = proxy_url.rstrip("/")
    return {
        "proxy": f"http://127.0.0.1:{port}",
        "stats_url": f"{base}/stats",
        "thresholds_url": f"{base}/thresholds",
    }


def local_proxy_urls(proxy_url: str) -> Tuple[str, str]:
    """Backward-compatible alias: (stats_url, thresholds_url)."""
    cfg = proxy_scrape_config(proxy_url)
    return cfg["stats_url"], cfg["thresholds_url"]


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


def rate_config_has_any(
    proxy_dir: Path, apis: Optional[List[str]] = None
) -> bool:
    """True if at least one rate_config/<api> file exists and parses as float."""
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    for api in names:
        path = proxy_dir / api
        try:
            float(path.read_text(encoding="utf-8").strip())
            return True
        except (OSError, ValueError):
            continue
    return False


def read_live_thresholds(
    proxy_dir: Path,
    fetch_url: UrlFetcher,
    thresholds_url: str,
    apis: Optional[List[str]] = None,
    error_ts: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """Live cap via proxied `GET …/thresholds`.

    Returns a per-API map on success, or None on HTTP failure / empty body.
    Does **not** fall back to empty `rate_config/` zeros (that looked like a
    measured cap of 0 under S2 timeouts). File fallback is handled by
    `resolve_thresholds` only when at least one file actually exists.
    """
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    try:
        parsed = parse_proxy_stats(fetch_url(thresholds_url))
        if parsed:
            return {api: float(parsed.get(api, 0.0)) for api in names}
    except Exception as exc:
        if error_ts is not None:
            log.warning("%s  WARNING  thresholds fetch failed: %s", error_ts, exc)
    return None


@dataclass
class LastGoodThrottle:
    """Per-API last successful threshold / admitted values across ticks."""

    thresholds: Dict[str, float] = field(default_factory=dict)
    admitted: Dict[str, float] = field(default_factory=dict)


def resolve_thresholds(
    http_map: Optional[Dict[str, float]],
    proxy_dir: Path,
    last_good: LastGoodThrottle,
    apis: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], Dict[str, int]]:
    """Apply HTTP → rate_config (if any file) → last-good → 0.0."""
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    if http_map is not None:
        out = {api: float(http_map.get(api, 0.0)) for api in names}
        last_good.thresholds.update(out)
        return out, {api: 1 for api in names}
    if rate_config_has_any(proxy_dir, names):
        out = read_thresholds(proxy_dir, apis=names)
        last_good.thresholds.update(out)
        return out, {api: 1 for api in names}
    if last_good.thresholds:
        return (
            {api: float(last_good.thresholds.get(api, 0.0)) for api in names},
            {api: 0 for api in names},
        )
    return {api: 0.0 for api in names}, {api: 0 for api in names}


def resolve_admitted(
    http_map: Optional[Dict[str, float]],
    last_good: LastGoodThrottle,
    apis: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], Dict[str, int]]:
    """Apply HTTP /stats → last-good → 0.0."""
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    if http_map is not None:
        out = {api: float(http_map.get(api, 0.0)) for api in names}
        last_good.admitted.update(out)
        return out, {api: 1 for api in names}
    if last_good.admitted:
        return (
            {api: float(last_good.admitted.get(api, 0.0)) for api in names},
            {api: 0 for api in names},
        )
    return {api: 0.0 for api in names}, {api: 0 for api in names}


def fetch_proxy_admin(
    fetch_url: UrlFetcher,
    stats_url: str,
    thresholds_url: str,
    error_ts: Optional[str] = None,
) -> Tuple[
    Optional[Dict[str, float]],
    Optional[Dict[str, float]],
    Optional[BaseException],
    Optional[BaseException],
]:
    """Fetch `/thresholds` and `/stats` in parallel. Returns maps or None."""
    thresh_map: Optional[Dict[str, float]] = None
    admitted_map: Optional[Dict[str, float]] = None
    thresh_exc: Optional[BaseException] = None
    stats_exc: Optional[BaseException] = None

    def _thresholds() -> Optional[Dict[str, float]]:
        parsed = parse_proxy_stats(fetch_url(thresholds_url))
        if not parsed:
            return None
        return {api: float(parsed.get(api, 0.0)) for api in LOCUST_APIS}

    def _stats() -> Optional[Dict[str, float]]:
        parsed = parse_proxy_stats(fetch_url(stats_url))
        if not parsed:
            return None
        return {api: float(parsed.get(api, 0.0)) for api in LOCUST_APIS}

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_t = pool.submit(_thresholds)
        fut_s = pool.submit(_stats)
        try:
            thresh_map = fut_t.result()
        except Exception as exc:
            thresh_exc = exc
            if error_ts is not None:
                log.warning(
                    "%s  WARNING  thresholds fetch failed: %s", error_ts, exc
                )
        try:
            admitted_map = fut_s.result()
        except Exception as exc:
            stats_exc = exc
            if error_ts is not None:
                log.warning("%s  WARNING  stats fetch failed: %s", error_ts, exc)
    return thresh_map, admitted_map, thresh_exc, stats_exc


def write_throttle_csv(
    csv_path: Path,
    timestamp: str,
    thresholds: Dict[str, float],
    admitted: Dict[str, float],
    threshold_fresh: Optional[Dict[str, int]] = None,
    admitted_fresh: Optional[Dict[str, int]] = None,
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
                    "threshold_fresh": (threshold_fresh or {}).get(api, 0),
                    "admitted_fresh": (admitted_fresh or {}).get(api, 0),
                }
            )


def quota_for(service: str, quotas: Optional[Dict[str, int]] = None) -> int:
    if quotas and service in quotas:
        return int(quotas[service])
    return topfull_cpu_quotas.paper_limit_for(service)


def alpha_for(service: str) -> float:
    return SPECIAL_ALPHA if service in ALPHA_SPECIAL else DEFAULT_ALPHA


def detect_metrics(
    service: str,
    cadvisor_cpu: float,
    quotas: Optional[Dict[str, int]] = None,
) -> Dict[str, object]:
    quota = quota_for(service, quotas)
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


def default_fetch_url(
    url: str,
    timeout: float = PROXY_FETCH_TIMEOUT_SECONDS,
    proxy: Optional[str] = None,
) -> str:
    """Fetch `url`. If `proxy` is set, send the request *through* that HTTP proxy
    (required for goproxy `/stats` / `/thresholds`). Otherwise open directly
    with an empty ProxyHandler so env HTTP_PROXY does not capture cAdvisor."""
    if proxy:
        handler = ProxyHandler({"http": proxy, "https": proxy})
    else:
        handler = ProxyHandler({})
    opener = build_opener(handler)
    with opener.open(url, timeout=timeout) as resp:
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


def _admin_aware_fetch(http_proxy: Optional[str]) -> UrlFetcher:
    """Admin `/stats`/`/thresholds` go through goproxy; everything else direct."""

    def fetch(url: str) -> str:
        path = urlparse(url).path or ""
        if http_proxy and (
            path.endswith("/stats") or path.endswith("/thresholds")
        ):
            return default_fetch_url(url, proxy=http_proxy)
        return default_fetch_url(url)

    return fetch


def poll_once(
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    cpu_quotas: Optional[Dict[str, int]] = None,
    thresholds_url: Optional[str] = None,
    http_proxy: Optional[str] = None,
    last_good: Optional[LastGoodThrottle] = None,
) -> None:
    ts = timestamp or utc_now()
    thresh_url = thresholds_url or (stats_url.rsplit("/", 1)[0] + "/thresholds")
    store = last_good if last_good is not None else LastGoodThrottle()
    try:
        runner = run_cmd or default_run_cmd
        fetcher = fetch_url or _admin_aware_fetch(http_proxy)
        thresh_map: Optional[Dict[str, float]] = None
        admitted_map: Optional[Dict[str, float]] = None
        cpu_by_svc: Dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_admin = pool.submit(
                fetch_proxy_admin, fetcher, stats_url, thresh_url, ts
            )
            fut_cpu = pool.submit(scrape_cadvisor_cpu, runner, fetcher)
            try:
                thresh_map, admitted_map, _te, _se = fut_admin.result()
            except Exception as exc:
                log.warning("%s  WARNING  admin fetch failed: %s", ts, exc)
            try:
                cpu_by_svc = fut_cpu.result()
            except Exception as exc:
                log.warning("%s  WARNING  cadvisor scrape failed: %s", ts, exc)

        thresholds, t_fresh = resolve_thresholds(thresh_map, proxy_dir, store)
        admitted, a_fresh = resolve_admitted(admitted_map, store)
        write_throttle_csv(
            record_path / "topfull_throttle.csv",
            ts,
            thresholds,
            admitted,
            threshold_fresh=t_fresh,
            admitted_fresh=a_fresh,
        )
        rows = {
            svc: detect_metrics(
                svc, cpu_by_svc.get(svc, 0.0), quotas=cpu_quotas
            )
            for svc in DETECT_SERVICES
        }
        write_detect_csv(record_path / "topfull_detect.csv", ts, rows)
    except Exception as exc:
        log.warning("%s  WARNING  poll_once failed: %s", ts, exc)


def run_collector(
    params: dict,
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    max_polls: Optional[int] = None,
    thresholds_url: Optional[str] = None,
    http_proxy: Optional[str] = None,
) -> None:
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    cpu_quotas = params.get("cpu_quotas")
    if cpu_quotas is not None:
        cpu_quotas = {str(k): int(v) for k, v in cpu_quotas.items()}
    thresh_url = thresholds_url or (stats_url.rsplit("/", 1)[0] + "/thresholds")
    last_good = LastGoodThrottle()
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
            cpu_quotas=cpu_quotas,
            thresholds_url=thresh_url,
            http_proxy=http_proxy,
            last_good=last_good,
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
    scrape = proxy_scrape_config(gcfg["proxy_url"])
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_collector(
        params,
        record_path,
        proxy_dir,
        scrape["stats_url"],
        thresholds_url=scrape["thresholds_url"],
        http_proxy=scrape["proxy"],
    )


if __name__ == "__main__":
    main()
