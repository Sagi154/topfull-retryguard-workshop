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
