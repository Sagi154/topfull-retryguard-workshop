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
