"""Numbers for the 600 req/s ceiling snapshot, from one pulled run folder."""
import csv
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

TAGS = ["getproduct", "postcheckout", "getcart", "postcart", "emptycart"]
DROP_HEAD, DROP_TAIL = 60, 5


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def tag_stats(d, tag):
    rows = list(csv.DictReader(open(d / f"{tag}.csv")))
    rows = rows[DROP_HEAD:-DROP_TAIL]
    rps = statistics.mean(float(r["RPS"]) for r in rows)
    p95 = statistics.mean(float(r["Latency95"]) for r in rows)
    return rps, p95


def main(d):
    d = Path(d)
    gates = []

    total_rows = sum(1 for _ in open(d / "total.csv")) - 1
    gates.append(("total.csv rows >= 540", total_rows >= 540, total_rows))

    inbound = list(csv.DictReader(open(d / "service_inbound.csv")))
    stamps = [ts(r["timestamp"]) for r in inbound]
    span = (max(stamps) - min(stamps)).total_seconds()
    gates.append(("mesh span 480-900 s", 480 <= span <= 900, round(span)))

    fe = [r for r in inbound if r["service"] == "frontend"]
    gaps = [(ts(b["timestamp"]) - ts(a["timestamp"])).total_seconds() for a, b in zip(fe, fe[1:])]
    gap2 = 100 * sum(g >= 2 for g in gaps) / max(len(gaps), 1)
    gates.append(("frontend inbound gap2 <= 10%", gap2 <= 10, round(gap2, 1)))

    modal = {}
    for r in csv.DictReader(open(d / "resource_usage.csv")):
        modal.setdefault(r["service"], Counter())[r["replica_count"]] += 1
    reps = {s: int(c.most_common(1)[0][0]) for s, c in modal.items()}
    bad = {s: n for s, n in reps.items() if n != (4 if s == "frontend" else 1)}
    gates.append(("replica pin (frontend 4, others 1)", not bad, bad or "ok"))

    thr = [float(r["threshold"]) for r in csv.DictReader(open(d / "topfull_throttle.csv"))]
    low = 100 * sum(t < 10000 for t in thr) / max(len(thr), 1)
    gates.append(("Layer A below 10000 on <= 1% of rows", low <= 1, round(low, 2)))

    print("== gates")
    for name, ok, val in gates:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {val}")

    print("== per tag (mean over rows 60..end-5)")
    sums = 0.0
    p95s = {}
    for tag in TAGS:
        rps, p95 = tag_stats(d, tag)
        sums += rps
        p95s[tag] = p95
        print(f"{tag:13s} mean RPS {rps:7.1f}  mean P95 {p95:7.0f} ms")
    print(f"sum of tag mean RPS: {sums:.1f}")

    lam = [
        (int(b["total"]) - int(a["total"])) / (ts(b["timestamp"]) - ts(a["timestamp"])).total_seconds()
        for a, b in zip(fe, fe[1:])
        if ts(b["timestamp"]) > ts(a["timestamp"])
    ]
    print(f"frontend inbound lambda (mean of deltas): {statistics.mean(lam):.1f} req/s")
    return 0 if all(ok for _, ok, _ in gates) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
