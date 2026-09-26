"""compare_runs.py — side-by-side readout of replica-scaling (or any) holds.

Usage:
    python experiments/compare_runs.py <run_dir> <run_dir> [...]
    python experiments/compare_runs.py --labels ref,A,B --out out.md dir1 dir2 dir3

Every metric uses the same steady window: drop the first 60 s (ramp-up)
and the last 10 s (shutdown tail). Missing files degrade to n/a with a
note; the script never raises on incomplete folders.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

STEADY_HEAD_SECONDS = 60
STEADY_TAIL_SECONDS = 10
HOT_UTIL_P95 = 0.85
THROTTLE_PASSTHROUGH = 10000.0
LOCUST_APIS = ("getproduct", "getcart", "postcart", "emptycart", "postcheckout")
MASTER_SERVICE = "__master_node__"
CPU_IDLE_RE = re.compile(r"([\d.]+)\s+id")
LOCUST_CMD_RE = re.compile(r"\blocust\b", re.IGNORECASE)


def parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return default


def _int(row: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(row[key]))
    except (KeyError, TypeError, ValueError):
        return default


def _p95(values: list[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[int(0.95 * (len(ordered) - 1))]


def _mean(values: Iterable[float]) -> Optional[float]:
    vals = list(values)
    if not vals:
        return None
    return statistics.mean(vals)


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def timestamped_rows(rows: list[dict]) -> list[tuple[datetime, dict]]:
    out = []
    for row in rows:
        ts = parse_timestamp(row.get("timestamp", ""))
        if ts is not None:
            out.append((ts, row))
    out.sort(key=lambda item: item[0])
    return out


def steady_bounds(times: list[datetime]) -> Optional[tuple[datetime, datetime]]:
    if not times:
        return None
    start = min(times) + timedelta(seconds=STEADY_HEAD_SECONDS)
    end = max(times) - timedelta(seconds=STEADY_TAIL_SECONDS)
    if end <= start:
        return None
    return start, end


def in_window(ts: datetime, bounds: Optional[tuple[datetime, datetime]]) -> bool:
    if bounds is None:
        return False
    return bounds[0] <= ts <= bounds[1]


def locust_steady_rows(rows: list[dict]) -> list[dict]:
    if len(rows) <= STEADY_HEAD_SECONDS + STEADY_TAIL_SECONDS:
        return []
    return rows[STEADY_HEAD_SECONDS : len(rows) - STEADY_TAIL_SECONDS]


def missing(reason: str) -> dict:
    return {"available": False, "reason": reason}


def simultaneous_overload(run_dir: Path) -> dict:
    rows = timestamped_rows(read_csv(run_dir / "topfull_detect.csv"))
    if not rows:
        return missing("no topfull_detect.csv")
    bounds = steady_bounds([ts for ts, _ in rows])
    if bounds is None:
        return missing("topfull_detect.csv too short for the 60s/10s window")
    by_ts: dict[datetime, int] = defaultdict(int)
    for ts, row in rows:
        if not in_window(ts, bounds):
            continue
        if _int(row, "overloaded") == 1:
            by_ts[ts] += 1
        else:
            by_ts.setdefault(ts, 0)
    counts = list(by_ts.values())
    if not counts:
        return missing("no detect ticks in the steady window")
    return {
        "available": True,
        "max": max(counts),
        "mean": statistics.mean(counts),
        "n_ticks": len(counts),
    }


def locust_summary(run_dir: Path) -> dict:
    apis = {}
    notes = []
    for api in LOCUST_APIS:
        rows = locust_steady_rows(read_csv(run_dir / f"{api}.csv"))
        if not rows:
            apis[api] = None
            notes.append(f"{api}.csv missing or too short")
            continue
        apis[api] = {
            "rps": _mean(_float(r, "RPS") for r in rows),
            "goodput": _mean(_float(r, "Goodput") for r in rows),
            "p95": _mean(_float(r, "Latency95") for r in rows),
        }
    return {"available": any(v is not None for v in apis.values()), "apis": apis, "notes": notes}


def throttle_summary(run_dir: Path) -> dict:
    rows = timestamped_rows(read_csv(run_dir / "topfull_throttle.csv"))
    if not rows:
        return missing("no topfull_throttle.csv")
    bounds = steady_bounds([ts for ts, _ in rows])
    if bounds is None:
        return missing("topfull_throttle.csv too short for the 60s/10s window")
    by_api: dict[str, list[dict]] = defaultdict(list)
    for ts, row in rows:
        if in_window(ts, bounds):
            by_api[row.get("api", "")].append(row)
    apis = {}
    for api, ticks in by_api.items():
        if not api:
            continue
        thresholds = [_float(r, "threshold") for r in ticks]
        capped = [t < THROTTLE_PASSTHROUGH for t in thresholds]
        apis[api] = {
            "share_capped": sum(1 for c in capped if c) / len(ticks),
            "mean_threshold": statistics.mean(thresholds),
            "mean_admitted": statistics.mean(_float(r, "admitted_rps") for r in ticks),
        }
    return {"available": True, "apis": apis}


def _delta_series(pairs: list[tuple[datetime, dict]], keys: list[str]) -> list[dict]:
    out = []
    for (t0, a), (t1, b) in zip(pairs, pairs[1:]):
        dt = (t1 - t0).total_seconds()
        if dt <= 0:
            continue
        item = {"dt": dt}
        for key in keys:
            item[key] = _float(b, key) - _float(a, key)
        out.append(item)
    return out


def inbound_summary(run_dir: Path) -> dict:
    rows = timestamped_rows(read_csv(run_dir / "service_inbound.csv"))
    if not rows:
        return missing("no service_inbound.csv")
    bounds = steady_bounds([ts for ts, _ in rows])
    if bounds is None:
        return missing("service_inbound.csv too short for the 60s/10s window")
    by_svc: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)
    for ts, row in rows:
        if in_window(ts, bounds):
            by_svc[row.get("service", "")].append((ts, row))
    services = {}
    for svc, pairs in by_svc.items():
        if not svc:
            continue
        deltas = _delta_series(pairs, ["total", "5xx", "resets", "rq_time_sum_ms", "rq_time_count"])
        total_dt = sum(d["dt"] for d in deltas)
        d_total = sum(d["total"] for d in deltas)
        d_fail = sum(d["5xx"] + d["resets"] for d in deltas)
        d_time = sum(d["rq_time_sum_ms"] for d in deltas)
        d_count = sum(d["rq_time_count"] for d in deltas)
        services[svc] = {
            "arrival_rps": (d_total / total_dt) if total_dt else None,
            "failure": (d_fail / d_total) if d_total else 0.0,
            "sojourn_ms": (d_time / d_count) if d_count else None,
        }
    retry_delta = _retry_delta(run_dir, bounds)
    return {"available": True, "services": services, "retry_delta": retry_delta}


def _retry_delta(run_dir: Path, bounds: Optional[tuple[datetime, datetime]]) -> Optional[int]:
    rows = timestamped_rows(read_csv(run_dir / "service_edges.csv"))
    if not rows or bounds is None:
        return None
    by_edge: dict[tuple[str, str], list[tuple[datetime, dict]]] = defaultdict(list)
    for ts, row in rows:
        if in_window(ts, bounds):
            by_edge[(row.get("caller", ""), row.get("target", ""))].append((ts, row))
    total = 0
    saw = False
    for pairs in by_edge.values():
        if len(pairs) < 2:
            continue
        saw = True
        total += _int(pairs[-1][1], "retry") - _int(pairs[0][1], "retry")
    return total if saw else None


def utilization_summary(run_dir: Path) -> dict:
    capacity = load_json(run_dir / "service_capacity.json")
    rows = timestamped_rows(read_csv(run_dir / "resource_usage.csv"))
    if not rows:
        return missing("no resource_usage.csv")
    bounds = steady_bounds([ts for ts, _ in rows])
    if bounds is None:
        return missing("resource_usage.csv too short for the 60s/10s window")
    by_svc: dict[str, list[float]] = defaultdict(list)
    for ts, row in rows:
        if not in_window(ts, bounds):
            continue
        svc = row.get("service", "")
        if not svc or svc == MASTER_SERVICE:
            continue
        limit = 0.0
        if isinstance(capacity.get(svc), dict):
            limit = float(capacity[svc].get("cpu_limit_millicores") or 0)
        replicas = _float(row, "replica_count", 1.0) or 1.0
        denom = limit * replicas
        if denom <= 0:
            continue
        by_svc[svc].append(_float(row, "cpu_millicores") / denom)

    detect_rows = timestamped_rows(read_csv(run_dir / "topfull_detect.csv"))
    detect_bounds = steady_bounds([ts for ts, _ in detect_rows]) if detect_rows else None
    overloaded_share: dict[str, Optional[float]] = {}
    detect_by_svc: dict[str, list[int]] = defaultdict(list)
    for ts, row in detect_rows:
        if in_window(ts, detect_bounds):
            detect_by_svc[row.get("service", "")].append(_int(row, "overloaded"))
    for svc, flags in detect_by_svc.items():
        overloaded_share[svc] = (sum(flags) / len(flags)) if flags else None

    services = {}
    hot = []
    for svc, utils in by_svc.items():
        p95 = _p95(utils)
        services[svc] = {
            "util_p95": p95,
            "overloaded_share": overloaded_share.get(svc),
        }
        if p95 is not None and p95 >= HOT_UTIL_P95:
            hot.append(svc)
    return {"available": True, "services": services, "hot": sorted(hot)}


def parse_top_log(text: str, ncpus: int) -> dict:
    cores = []
    locust_cpu = []
    for line in text.splitlines():
        if "%Cpu" in line:
            match = CPU_IDLE_RE.search(line)
            if match:
                idle = float(match.group(1))
                cores.append((1.0 - idle / 100.0) * ncpus)
            continue
        if LOCUST_CMD_RE.search(line):
            parts = line.split()
            if len(parts) >= 9:
                try:
                    locust_cpu.append(float(parts[8]))
                except ValueError:
                    pass
    if not cores:
        return missing("no %Cpu(s) lines in top log")
    return {
        "available": True,
        "cores_p95": _p95(cores),
        "cores_max": max(cores),
        "locust_cpu_max": max(locust_cpu) if locust_cpu else None,
        "ncpus": ncpus,
    }


def machine_summary(run_dir: Path) -> dict:
    rows = timestamped_rows(read_csv(run_dir / "resource_usage.csv"))
    master = missing("no __master_node__ rows")
    if rows:
        bounds = steady_bounds([ts for ts, _ in rows])
        millicores = [
            _float(row, "cpu_millicores")
            for ts, row in rows
            if in_window(ts, bounds) and row.get("service") == MASTER_SERVICE
        ]
        if millicores:
            cores = [m / 1000.0 for m in millicores]
            master = {
                "available": True,
                "cores_p95": _p95(cores),
                "cores_max": max(cores),
            }
        elif bounds is None:
            master = missing("resource_usage.csv too short for the 60s/10s window")

    worker_path = run_dir / "worker_cpu.txt"
    load_path = run_dir / "load_cpu.txt"
    worker = (
        parse_top_log(worker_path.read_text(encoding="utf-8", errors="replace"), 16)
        if worker_path.is_file()
        else missing("no worker_cpu.txt")
    )
    load = (
        parse_top_log(load_path.read_text(encoding="utf-8", errors="replace"), 8)
        if load_path.is_file()
        else missing("no load_cpu.txt")
    )
    return {"master": master, "worker": worker, "load": load}


def analyze_run(run_dir: Path, label: str) -> dict:
    return {
        "label": label,
        "path": str(run_dir),
        "simultaneous": simultaneous_overload(run_dir),
        "locust": locust_summary(run_dir),
        "throttle": throttle_summary(run_dir),
        "inbound": inbound_summary(run_dir),
        "utilization": utilization_summary(run_dir),
        "machines": machine_summary(run_dir),
    }


def _hot_cell(report: dict) -> str:
    util = report["utilization"]
    if not util.get("available"):
        return f"n/a ({util.get('reason', 'missing')})"
    hot = util.get("hot") or []
    return ", ".join(hot) if hot else "(none >= 0.85)"


def _sim_cell(report: dict) -> str:
    sim = report["simultaneous"]
    if not sim.get("available"):
        return f"n/a ({sim.get('reason', 'missing')})"
    return f"max {sim['max']}, mean {_fmt(sim['mean'])}"


def render_markdown(reports: list[dict]) -> str:
    lines = [
        "# Run comparison",
        "",
        "Steady window: drop first 60 s and last 10 s.",
        "",
        "## Headline",
        "",
        "| Run | Services overloaded at once | Hot services (util p95 >= 0.85) |",
        "|---|---|---|",
    ]
    for report in reports:
        lines.append(
            f"| {report['label']} | {_sim_cell(report)} | {_hot_cell(report)} |"
        )

    lines.extend(["", "## 1. Load sent", ""])
    header = "| Run | " + " | ".join(
        f"{api} RPS / goodput / P95" for api in LOCUST_APIS
    ) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (1 + len(LOCUST_APIS)))
    for report in reports:
        locust = report["locust"]
        cells = [report["label"]]
        for api in LOCUST_APIS:
            row = (locust.get("apis") or {}).get(api)
            if row is None:
                cells.append("n/a")
            else:
                cells.append(
                    f"{_fmt(row['rps'], 1)} / {_fmt(row['goodput'], 1)} / {_fmt(row['p95'], 1)}"
                )
        lines.append("| " + " | ".join(cells) + " |")
        if locust.get("notes"):
            lines.append("")
            lines.append("- notes: " + "; ".join(locust["notes"]))

    lines.extend(["", "## 2. TopFull cap", ""])
    all_apis = sorted({
        api
        for report in reports
        for api in (report["throttle"].get("apis") or {})
    })
    if not all_apis:
        lines.append("n/a (no topfull_throttle.csv)")
    else:
        lines.append(
            "| Run | "
            + " | ".join(f"{api} share-capped / thresh / admitted" for api in all_apis)
            + " |"
        )
        lines.append("|" + "---|" * (1 + len(all_apis)))
        for report in reports:
            throttle = report["throttle"]
            if not throttle.get("available"):
                lines.append(
                    f"| {report['label']} | "
                    + " | ".join(["n/a"] * len(all_apis))
                    + f" |  ({throttle.get('reason')})"
                )
                continue
            cells = [report["label"]]
            for api in all_apis:
                row = (throttle.get("apis") or {}).get(api)
                if row is None:
                    cells.append("n/a")
                else:
                    cells.append(
                        f"{_fmt(row['share_capped'])} / "
                        f"{_fmt(row['mean_threshold'], 1)} / "
                        f"{_fmt(row['mean_admitted'], 1)}"
                    )
            lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## 3. Backend arrivals", ""])
    all_svcs = sorted({
        svc
        for report in reports
        for svc in (report["inbound"].get("services") or {})
    })
    if not all_svcs:
        lines.append("n/a (no service_inbound.csv)")
    else:
        lines.append(
            "| Run | "
            + " | ".join(f"{svc} λ / fail / Wms" for svc in all_svcs)
            + " | Δretry |"
        )
        lines.append("|" + "---|" * (2 + len(all_svcs)))
        for report in reports:
            inbound = report["inbound"]
            if not inbound.get("available"):
                lines.append(
                    f"| {report['label']} | "
                    + " | ".join(["n/a"] * (len(all_svcs) + 1))
                    + f" |  ({inbound.get('reason')})"
                )
                continue
            cells = [report["label"]]
            for svc in all_svcs:
                row = (inbound.get("services") or {}).get(svc)
                if row is None:
                    cells.append("n/a")
                else:
                    cells.append(
                        f"{_fmt(row['arrival_rps'], 2)} / "
                        f"{_fmt(row['failure'])} / "
                        f"{_fmt(row['sojourn_ms'], 1)}"
                    )
            cells.append(_fmt(inbound.get("retry_delta"), 0))
            lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## 4. Utilization", ""])
    util_svcs = sorted({
        svc
        for report in reports
        for svc in (report["utilization"].get("services") or {})
    })
    if not util_svcs:
        lines.append("n/a (no resource_usage.csv)")
    else:
        lines.append(
            "| Run | "
            + " | ".join(f"{svc} p95 / ovl-share" for svc in util_svcs)
            + " |"
        )
        lines.append("|" + "---|" * (1 + len(util_svcs)))
        for report in reports:
            util = report["utilization"]
            if not util.get("available"):
                lines.append(
                    f"| {report['label']} | "
                    + " | ".join(["n/a"] * len(util_svcs))
                    + f" |  ({util.get('reason')})"
                )
                continue
            cells = [report["label"]]
            for svc in util_svcs:
                row = (util.get("services") or {}).get(svc)
                if row is None:
                    cells.append("n/a")
                else:
                    cells.append(
                        f"{_fmt(row['util_p95'])} / {_fmt(row['overloaded_share'])}"
                    )
            lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## 5. Machines", "",
                  "| Run | Master cores p95 / max | Worker cores p95 / max | Load cores p95 / max | Locust %CPU max |",
                  "|---|---|---|---|---|"])
    for report in reports:
        machines = report["machines"]

        def machine_cell(block: dict) -> str:
            if not block.get("available"):
                return f"n/a ({block.get('reason', 'missing')})"
            return f"{_fmt(block.get('cores_p95'), 2)} / {_fmt(block.get('cores_max'), 2)}"

        locust_max = machines["load"].get("locust_cpu_max")
        locust_cell = (
            "n/a"
            if not machines["load"].get("available")
            else _fmt(locust_max, 1)
        )
        lines.append(
            f"| {report['label']} | "
            f"{machine_cell(machines['master'])} | "
            f"{machine_cell(machines['worker'])} | "
            f"{machine_cell(machines['load'])} | "
            f"{locust_cell} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--labels", default="", help="Comma-separated labels, same order as run_dirs")
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    labels = [part.strip() for part in args.labels.split(",") if part.strip()]
    if labels and len(labels) != len(args.run_dirs):
        print("error: --labels count must match run_dirs", file=sys.stderr)
        return 2
    reports = []
    for i, run_dir in enumerate(args.run_dirs):
        label = labels[i] if labels else run_dir.name
        reports.append(analyze_run(run_dir, label))
    text = render_markdown(reports)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
