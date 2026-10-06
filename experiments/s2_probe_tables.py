"""Per-service comparison tables for a both-off S2 series (the layout of
Guides and Info/2026-10-04-s2-latch-probe-abc.md).

CLI:
  python experiments/s2_probe_tables.py --out <file.md> --block "A=128,129,130" --block "B=138,139"
Runs are read from experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>/.
(a)/(b)/(c) come from s2_both_off_abc.score_run; the other tables come from service_inbound.csv,
resource_usage.csv, service_capacity.json, topfull_detect.csv and the five Locust CSVs.
Locust rows drop the first 30 and the last 5; inbound rows drop the last 5 polls.
"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_both_off_abc as abc  # noqa: E402
import steal_stat  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "experiments" / "results" / "new vms"
SERVICES = ["frontend", "checkoutservice", "recommendationservice", "paymentservice",
            "emailservice", "productcatalogservice", "cartservice", "currencyservice",
            "shippingservice", "adservice", "redis-cart"]
UNCONTROLLED = {"frontend", "redis-cart"}
APIS = ["getproduct", "postcheckout", "getcart", "postcart", "emptycart"]


def run_dir(n: int) -> Path:
    return ROOT / f"baseline_no_topfull_sustained_overload_run{n}"


def _rows(path: Path) -> list:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ts(s: str) -> float:
    return steal_stat._utc(s)


def inbound_metrics(rows: list) -> dict:
    """Cumulative Envoy inbound counters for one service, time-sorted. Last 5 polls dropped."""
    rows = rows[:-5]
    if len(rows) < 2:
        return {}
    a, b = rows[0], rows[-1]
    dt = _ts(b["timestamp"]) - _ts(a["timestamp"])
    dtotal = float(b["total"]) - float(a["total"])
    out = {"arrival": dtotal / dt if dt > 0 else None}
    if dtotal > 0:
        out["fail5xx"] = (float(b["5xx"]) - float(a["5xx"])) / dtotal
        out["reset"] = (float(b["resets"]) - float(a["resets"])) / dtotal
    dc = float(b["rq_time_count"]) - float(a["rq_time_count"])
    ds = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
    if dc > 0:
        out["sojourn_ms"] = ds / dc
        try:
            le500 = json.loads(b["rq_time_buckets"])["500"] - json.loads(a["rq_time_buckets"])["500"]
            out["over500"] = max(0.0, 1.0 - le500 / dc)
        except (KeyError, ValueError, TypeError):
            pass
    return out


def locust_metrics(path: Path) -> dict:
    rows = _rows(path)[30:-5]
    if not rows:
        return {}
    rps = sum(float(r["RPS"]) for r in rows)
    fail = sum(float(r["Fail"]) for r in rows)
    return {"goodput": st.mean(float(r["Goodput"]) for r in rows),
            "fail": fail / rps if rps else None,
            "p95": st.mean(float(r["Latency95"]) for r in rows)}


def load(n: int) -> dict:
    d = run_dir(n)
    out = {"abc": abc.score_run(d), "inbound": {}, "cpu": {}, "util": {}, "locust": {}}
    by = defaultdict(list)
    for r in _rows(d / "service_inbound.csv"):
        by[r["service"]].append(r)
    for svc, rows in by.items():
        out["inbound"][svc] = inbound_metrics(rows)
    cap = json.loads((d / "service_capacity.json").read_text(encoding="utf-8"))
    cpu = defaultdict(list)
    for r in _rows(d / "resource_usage.csv"):
        cpu[r["service"]].append(float(r["cpu_millicores"]))
    for svc, vals in cpu.items():
        quota = None
        if svc in cap:
            quota = cap[svc]["cpu_limit_millicores"] * cap[svc]["replica_count"]
        out["cpu"][svc] = {"mean": st.mean(vals), "max": max(vals), "quota": quota}
    umax = defaultdict(float)
    for r in _rows(d / "topfull_detect.csv"):
        umax[r["service"]] = max(umax[r["service"]], float(r["utilization"]))
    out["util"] = dict(umax)
    for api in APIS:
        p = d / f"{api}.csv"
        if p.exists():
            out["locust"][api] = locust_metrics(p)
    return out


def _fmt(x, spec):
    return "" if x is None else format(x, spec)


def _bold(s, on):
    return f"**{s}**" if on else s


def cell_a(data, svc):
    v = data["abc"]["inbound"].get(svc)
    if not v:
        return ""
    return _bold(f"{v['streak']} / {v['high_samples']}", v["streak"] >= 30 and svc not in UNCONTROLLED)


def cell_b(data, svc):
    v = data["abc"]["overloaded"].get(svc)
    if not v:
        return ""
    return _bold(f"{v['overloaded_ticks']}/{v['ticks']} ({v['share']:.0%})", v["share"] >= 0.5)


def cell_c(data, svc):
    return str(data["abc"]["retry_by_target"].get(svc, 0))


def cell_cpu(data, svc):
    v = data["cpu"].get(svc)
    return "" if not v else f"{v['mean']:.0f} / {v['max']:.0f}"


def cell_cpu_frac(data, svc):
    v = data["cpu"].get(svc)
    if not v or not v["quota"]:
        return ""
    return f"{v['mean'] / v['quota']:.2f} / {v['max'] / v['quota']:.2f}"


def _inb(key, spec):
    return lambda data, svc: _fmt(data["inbound"].get(svc, {}).get(key), spec)


def cell_util(data, svc):
    return _fmt(data["util"].get(svc), ".2f")


# (title, per-service cell function). Locust tables are per API and handled separately.
SERVICE_TABLES = [
    ("(a) Inbound rejection streak / samples above 0.20", cell_a),
    ("(b) Detector overloaded ticks / ticks (share)", cell_b),
    ("(c) Outbound retry delta by target", cell_c),
    ("CPU mean / max (m, summed over replicas)", cell_cpu),
    ("Inbound arrival rate (req/s)", _inb("arrival", ".1f")),
    ("Inbound 5xx fraction", _inb("fail5xx", ".3f")),
    ("Inbound reset fraction", _inb("reset", ".3f")),
    ("Inbound sojourn (ms)", _inb("sojourn_ms", ".0f")),
    ("Share of inbound requests above 500 ms", _inb("over500", ".2f")),
    ("CPU use as a fraction of per-pod quota x replicas (mean / max)", cell_cpu_frac),
    ("Detector max utilization", cell_util),
]
LOCUST_TABLES = [("Locust goodput (req/s)", "goodput", ".1f"),
                 ("Locust fail rate (Fail / RPS)", "fail", ".3f"),
                 ("Locust P95 (ms)", "p95", ".0f")]


def _table(header, rows_spec, runs, data):
    lines = ["| " + " | ".join([header] + [f"run{n}" for n in runs]) + " |",
             "|" + "---|" * (len(runs) + 1)]
    for label, fn in rows_spec:
        lines.append("| " + " | ".join([label] + [fn(data[n]) for n in runs]) + " |")
    return "\n".join(lines)


def build(blocks: list) -> str:
    """blocks: [(name, [run numbers])]."""
    data = {n: load(n) for _, runs in blocks for n in runs}
    out = []
    for title, fn in SERVICE_TABLES:
        out.append(f"## {title}\n")
        for name, runs in blocks:
            out.append(f"### Block {name}\n")
            spec = [(svc + (" (not controlled)" if svc in UNCONTROLLED else ""),
                     (lambda d, s=svc, f=fn: f(d, s))) for svc in SERVICES]
            out.append(_table("Service", spec, runs, data) + "\n")
    for title, key, spec_fmt in LOCUST_TABLES:
        out.append(f"## {title}\n")
        for name, runs in blocks:
            out.append(f"### Block {name}\n")
            spec = [(api, (lambda d, a=api, k=key, f=spec_fmt: _fmt(d["locust"].get(a, {}).get(k), f)))
                    for api in APIS]
            out.append(_table("API", spec, runs, data) + "\n")
    out.append("## CPU steal % over the hold (hold % / worst 5 s interval)\n")
    for name, runs in blocks:
        out.append(f"### Block {name}\n")
        out.append("| Run | master | worker | load |\n|---|---|---|---|")
        for n in runs:
            row = steal_stat.md_row(f"run{n}", steal_stat.score_run(run_dir(n)))
            out.append(row)
        out.append("")
    return "\n".join(out)


def main(argv):
    blocks, out_path = [], None
    i = 1
    while i < len(argv):
        if argv[i] == "--out":
            out_path = argv[i + 1]
            i += 2
        elif argv[i] == "--block":
            name, runs = argv[i + 1].split("=")
            blocks.append((name, [int(x) for x in runs.split(",")]))
            i += 2
        else:
            print(__doc__)
            return 2
    if not blocks:
        print(__doc__)
        return 2
    text = build(blocks)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"wrote {out_path} ({len(text)} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
