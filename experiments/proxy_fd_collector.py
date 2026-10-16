#!/usr/bin/env python3
"""
proxy_fd_collector.py — open file descriptors of the TopFull Go proxy, once a second.

The proxy ran out of descriptors (soft limit 1024) 50-190 s into load on 2026-10-15; the cause
had to be inferred from `accept4: too many open files`. This puts the count in the data.
Stdlib only. Reads /proc, never touches the proxy.

Usage (on master):
    python3 proxy_fd_collector.py --params /tmp/proxy_fd_params.json
params: {"output_dir": "<src>/logs", "poll_interval_seconds": 1}
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

CSV_NAME = "proxy_fds.csv"
LOG_NAME = "proxy_fd_collector.log"
CSV_COLUMNS = ["timestamp", "pid", "open_fds", "soft_limit"]
# `go run` execs the compiled binary at /tmp/go-build.../exe/proxy_online_boutique.
PROXY_EXE_MARK = "/exe/proxy_online_boutique"
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
NO_PROXY_WARN_EVERY_S = 30.0
UNLIMITED = -1
_LIMITS = re.compile(r"^Max open files\s+(\S+)\s+(\S+)", re.MULTILINE)

_shutdown = False
log = logging.getLogger("proxy_fd_collector")


def utc_stamp(now: float) -> str:
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_proxy_pids(proc_root: str = "/proc") -> list[int]:
    pids = []
    try:
        names = os.listdir(proc_root)
    except OSError:
        return pids
    for name in names:
        if not name.isdigit():
            continue
        try:
            raw = Path(proc_root, name, "cmdline").read_bytes()
        except OSError:
            continue
        if PROXY_EXE_MARK in raw.replace(b"\0", b" ").decode("utf-8", "replace"):
            pids.append(int(name))
    return sorted(pids)


def count_open_fds(pid: int, proc_root: str = "/proc") -> Optional[int]:
    try:
        return len(os.listdir(Path(proc_root, str(pid), "fd")))
    except OSError:
        return None


def read_soft_limit(pid: int, proc_root: str = "/proc") -> Optional[int]:
    try:
        text = Path(proc_root, str(pid), "limits").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _LIMITS.search(text)
    if not match:
        return None
    return UNLIMITED if match.group(1) == "unlimited" else int(match.group(1))


def sample_once(now: float, proc_root: str = "/proc") -> list[dict]:
    rows = []
    for pid in find_proxy_pids(proc_root):
        fds = count_open_fds(pid, proc_root)
        soft = read_soft_limit(pid, proc_root)
        if fds is None or soft is None:
            continue  # the process exited between the listing and the read
        rows.append({"timestamp": utc_stamp(now), "pid": pid, "open_fds": fds, "soft_limit": soft})
    return rows


def append_rows(path: Path, rows: list[dict]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerows(rows)


def run_collector(
    params: dict,
    out_dir: Path,
    proc_root: str = "/proc",
    max_polls: Optional[int] = None,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    interval = float(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    csv_path = Path(out_dir) / CSV_NAME
    last_warn: Optional[float] = None
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        now = clock()
        rows = sample_once(now, proc_root)
        if rows:
            append_rows(csv_path, rows)
        elif last_warn is None or now - last_warn >= NO_PROXY_WARN_EVERY_S:
            log.warning("%s  WARNING  no process matching %s", utc_stamp(now), PROXY_EXE_MARK)
            last_warn = now
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
        sleep(max(0.0, interval - (now % interval)))


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_stamp(time.time()), signum)


def setup_logging(out_dir: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    log.addHandler(stream)
    try:
        handler = logging.FileHandler(str(Path(out_dir) / LOG_NAME), mode="a")
        handler.setFormatter(fmt)
        log.addHandler(handler)
    except OSError as exc:
        print(f"could not open {LOG_NAME}: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="TopFull proxy open-descriptor sampler.")
    parser.add_argument("--params", required=True, help="Path to collector params JSON")
    args = parser.parse_args()
    params = json.loads(Path(args.params).read_text(encoding="utf-8"))
    out_dir = Path(params["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(out_dir)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("%s  START  poll_interval=%ss", utc_stamp(time.time()),
             params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    run_collector(params, out_dir)
    log.info("%s  EXIT", utc_stamp(time.time()))


if __name__ == "__main__":
    main()
