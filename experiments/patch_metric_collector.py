#!/usr/bin/env python3
"""
Patch for metric_collector.py on the master VM. Safe to run more than once.

Stage 1 wraps the per-window collection loop in record_online_boutique() with
try/except so a missing Locust metric key (KeyError: 'getcart') no longer
crashes the process before traffic is flowing.

Stage 2 adds a UTC `timestamp` column (milliseconds, last column) to every
Locust CSV row, taken when the Locust poll returns.

    python3 patch_metric_collector.py [--dry-run]
"""

from __future__ import annotations

from pathlib import Path
import sys

TARGET = Path(
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/metric_collector.py"
)

OLD = '''    while True:
        time.sleep(1)
        metric = c.query()
        total_goodput = {}
        total_rps = 0
        total_fail = 0
        total_latency95 = 0
        total_latency99 = 0

        for i, api in enumerate(apis):
            # rps, fail, latency95, latency99 = metric[api]
            rps, fail, latency95 = metric[api]
            latency99 = 0
            total_rps += rps
            total_fail += fail
            total_latency95 += latency95
            total_latency99 += latency99
            with open(log_path + api + ".csv", "a") as f:
                w = csv.writer(f)
                w.writerow([rps, fail, rps-fail, latency95, latency99])
                total_goodput[api] = rps-fail
        with open(log_path + "total.csv", "a") as f:
            w = csv.writer(f)
            w.writerow([total_rps, total_fail, total_rps-total_fail, total_latency95/len(apis), total_latency99/len(apis)])
        out = ""
        for api in apis:
            out += f"{api}={total_goodput[api]}   "
        print(out)
'''

NEW = '''    while True:
        time.sleep(1)
        try:
            metric = c.query()
            total_goodput = {}
            total_rps = 0
            total_fail = 0
            total_latency95 = 0
            total_latency99 = 0

            for i, api in enumerate(apis):
                # rps, fail, latency95, latency99 = metric[api]
                rps, fail, latency95 = metric[api]
                latency99 = 0
                total_rps += rps
                total_fail += fail
                total_latency95 += latency95
                total_latency99 += latency99
                with open(log_path + api + ".csv", "a") as f:
                    w = csv.writer(f)
                    w.writerow([rps, fail, rps-fail, latency95, latency99])
                    total_goodput[api] = rps-fail
            with open(log_path + "total.csv", "a") as f:
                w = csv.writer(f)
                w.writerow([total_rps, total_fail, total_rps-total_fail, total_latency95/len(apis), total_latency99/len(apis)])
            out = ""
            for api in apis:
                out += f"{api}={total_goodput[api]}   "
            print(out)
        except (KeyError, IndexError, ValueError) as e:
            print(f"[metric_collector] waiting for traffic: {e}")
            continue
'''

MARKER = "[metric_collector] waiting for traffic:"

STAMP_MARKER = '"Latency99", "timestamp"]'
STAMP_LINE = (
    '            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"\n'
)
STAMP_EDITS = (
    ("import time\n", "import time\nfrom datetime import datetime, timezone\n", 1),
    (
        'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99"])',
        'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99", "timestamp"])',
        2,
    ),
    ("            metric = c.query()\n", "            metric = c.query()\n" + STAMP_LINE, 1),
    (
        "w.writerow([rps, fail, rps-fail, latency95, latency99])",
        "w.writerow([rps, fail, rps-fail, latency95, latency99, stamp])",
        1,
    ),
    (
        "w.writerow([total_rps, total_fail, total_rps-total_fail, "
        "total_latency95/len(apis), total_latency99/len(apis)])",
        "w.writerow([total_rps, total_fail, total_rps-total_fail, "
        "total_latency95/len(apis), total_latency99/len(apis), stamp])",
        1,
    ),
)


def add_try_guard(text: str) -> str:
    if MARKER in text:
        return text
    if OLD not in text:
        raise SystemExit(
            "ERROR: expected while-loop block not found — "
            "metric_collector.py may have changed; aborting"
        )
    return text.replace(OLD, NEW, 1)


def add_row_timestamps(text: str) -> str:
    if STAMP_MARKER in text:
        return text
    for old, new, count in STAMP_EDITS:
        found = text.count(old)
        if found != count:
            raise SystemExit(
                f"ERROR: expected {count} of {old!r}, found {found} — "
                "metric_collector.py may have changed; aborting"
            )
        text = text.replace(old, new)
    return text


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    text = TARGET.read_text(encoding="utf-8")
    patched = add_row_timestamps(add_try_guard(text))
    if patched == text:
        print("ALREADY_PATCHED")
        return
    if "--dry-run" in args:
        print("WOULD_PATCH")
        return
    TARGET.write_text(patched, encoding="utf-8")
    print("PATCHED_OK")


if __name__ == "__main__":
    main()
