#!/usr/bin/env python3
"""One-shot latency probe: GET/POST /cart, direct vs via HTTP proxy. 20 samples each.

Disposable helper for Phase 3 latency-path checks. Curl exit 28 (max-time)
is recorded as time_total=30.0 / http_code=0 so the matrix does not abort.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

POST_CART_BODY = "product_id=0PUK6V6EV0&quantity=1"


def curl_once(
    url: str,
    *,
    method: str = "GET",
    data: Optional[str] = None,
    proxy: Optional[str] = None,
    cookie_jar: Optional[Path] = None,
) -> Tuple[int, float]:
    cmd = [
        "curl",
        "-o",
        "/dev/null",
        "-s",
        "-S",
        "-w",
        "%{http_code} %{time_total}",
        "-m",
        "30",
    ]
    if cookie_jar is not None:
        cmd += ["-c", str(cookie_jar), "-b", str(cookie_jar)]
    if proxy:
        cmd += ["-x", proxy]
    if method != "GET":
        cmd += ["-X", method]
    if data is not None:
        cmd += ["-d", data]
    cmd.append(url)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Exit 28 = operation timed out (--max-time). Do not abort the matrix.
    if proc.returncode == 28:
        return 0, 30.0
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 and not out:
        return 0, 30.0
    parts = out.split()
    if len(parts) < 2:
        return 0, 30.0
    try:
        code = int(parts[0])
        total = float(parts[1])
    except ValueError:
        return 0, 30.0
    if proc.returncode != 0 and code == 0:
        return 0, 30.0 if total <= 0 else total
    return code, total


def cell_summary(label: str, samples: List[Tuple[int, float]]) -> Dict[str, Any]:
    times = [t for _, t in samples]
    codes = [c for c, _ in samples]
    n_timeout = sum(1 for c, t in samples if c == 0 and t >= 30.0)
    rec = {
        "label": label,
        "n": len(times),
        "median_s": statistics.median(times) if times else None,
        "max_s": max(times) if times else None,
        "min_s": min(times) if times else None,
        "codes": sorted(set(codes)),
        "n_timeout": n_timeout,
        "samples": [{"http_code": c, "time_total": t} for c, t in samples],
    }
    print(
        f"{label}: n={rec['n']} median={rec['median_s']:.4f}s "
        f"max={rec['max_s']:.4f}s min={rec['min_s']:.4f}s "
        f"codes={rec['codes']} timeouts={n_timeout}"
    )
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frontend", required=True, help="e.g. http://10.128.0.3:30440")
    p.add_argument("--proxy", required=True, help="e.g. http://10.128.0.3:8090")
    p.add_argument("--mode", choices=("idle", "loaded"), required=True)
    p.add_argument("--out", default="", help="optional JSON output path")
    p.add_argument("--n", type=int, default=20)
    args = p.parse_args()

    frontend = args.frontend.strip()
    if not frontend.startswith("http"):
        frontend = "http://" + frontend
    frontend = frontend.rstrip("/")
    proxy = args.proxy.strip()
    if proxy and not proxy.startswith("http"):
        proxy = "http://" + proxy

    started = time.time()
    cells_out: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as td:
        jar = Path(td) / "cookie.jar"
        curl_once(f"{frontend}/", cookie_jar=jar)
        curl_once(
            f"{frontend}/cart",
            method="POST",
            data=POST_CART_BODY,
            cookie_jar=jar,
        )

        cells = [
            ("GET /cart direct", "GET", None, None),
            ("GET /cart via-proxy", "GET", None, proxy),
            ("POST /cart direct", "POST", POST_CART_BODY, None),
            ("POST /cart via-proxy", "POST", POST_CART_BODY, proxy),
        ]
        for label, method, data, use_proxy in cells:
            samples = []
            for _ in range(args.n):
                samples.append(
                    curl_once(
                        f"{frontend}/cart",
                        method=method,
                        data=data,
                        proxy=use_proxy,
                        cookie_jar=jar,
                    )
                )
            cells_out.append(cell_summary(label, samples))

    payload = {
        "mode": args.mode,
        "frontend": frontend,
        "proxy": proxy,
        "n": args.n,
        "started_unix": started,
        "elapsed_s": time.time() - started,
        "cells": cells_out,
    }
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
