#!/usr/bin/env python3
"""
One-shot patch for metric_collector.py on the master VM.

Wraps the per-window collection loop in record_online_boutique() with
try/except so a missing Locust metric key (KeyError: 'getcart') no longer
crashes the process before traffic is flowing.
"""

from pathlib import Path

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


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("ALREADY_PATCHED")
        return
    if OLD not in text:
        raise SystemExit(
            "ERROR: expected while-loop block not found — "
            "metric_collector.py may have changed; aborting"
        )
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("PATCHED_OK")


if __name__ == "__main__":
    main()
