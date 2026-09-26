"""Score one both-off run directory the way
Guides and Info/2026-09-24-s2-both-off-abc-reading.md defines (a)/(b)/(c).

(a) longest consecutive inbound samples with (d5xx + dresets) / dtotal > 0.20
(b) share of topfull_detect.csv rows with overloaded == 1
(c) sum of positive service_edges.csv retry increments per caller->target

Also reports Layer A rows whose threshold is neither 0 nor 10000, and
per-service CPU mean/max from resource_usage.csv. Prints markdown.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


HIGH = 0.20


def _num(row: dict, key: str) -> float:
    raw = row.get(key, "")
    if raw is None or raw == "":
        return 0.0
    return float(raw)


def rejection_streak(rows: list[dict]) -> tuple[int, int, int, float]:
    """Cumulative counters, already time-sorted for one service.

    Returns (longest_streak, high_samples, scored_samples, failure_fraction).
    A non-positive total delta scores as not-high and breaks the streak.
    Negative counter jumps are not added into the fraction.
    """
    longest = 0
    current = 0
    high = 0
    scored = 0
    fail_num = 0.0
    fail_den = 0.0
    prev = None
    for row in rows:
        total = _num(row, "total")
        failed = _num(row, "5xx") + _num(row, "resets")
        if prev is None:
            prev = (total, failed)
            continue
        d_total = total - prev[0]
        d_fail = failed - prev[1]
        prev = (total, failed)
        scored += 1
        is_high = d_total > 0 and (d_fail / d_total) > HIGH
        if d_total > 0 and d_fail > 0:
            fail_num += d_fail
            fail_den += d_total
        elif d_total > 0:
            fail_den += d_total
        if is_high:
            high += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    fraction = (fail_num / fail_den) if fail_den else 0.0
    return longest, high, scored, fraction


def overloaded_fraction(flags: list[int]) -> tuple[int, int, float]:
    ticks = len(flags)
    hot = sum(1 for flag in flags if int(flag) == 1)
    share = (hot / ticks) if ticks else 0.0
    return ticks, hot, share


def retry_deltas(edges: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in edges:
        grouped[(row.get("caller", ""), row.get("target", ""))].append(_num(row, "retry"))
    by_edge: dict[str, int] = {}
    by_target: dict[str, int] = defaultdict(int)
    for (caller, target), values in grouped.items():
        delta = 0
        prev = None
        for value in values:
            if prev is not None and value > prev:
                delta += int(value - prev)
            prev = value
        key = f"{caller}->{target}"
        by_edge[key] = delta
        by_target[target] += delta
    return dict(by_edge), dict(by_target)


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def score_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    inbound_rows: dict[str, list[dict]] = defaultdict(list)
    for row in _rows(run_dir / "service_inbound.csv"):
        inbound_rows[row["service"]].append(row)
    inbound = {}
    for service, rows in inbound_rows.items():
        streak, high, scored, frac = rejection_streak(rows)
        inbound[service] = {
            "streak": streak,
            "high_samples": high,
            "samples": scored,
            "failure_fraction": frac,
        }

    detect_flags: dict[str, list[int]] = defaultdict(list)
    for row in _rows(run_dir / "topfull_detect.csv"):
        detect_flags[row["service"]].append(int(float(row.get("overloaded") or 0)))
    overloaded = {}
    for service, flags in detect_flags.items():
        ticks, hot, share = overloaded_fraction(flags)
        overloaded[service] = {
            "ticks": ticks,
            "overloaded_ticks": hot,
            "share": share,
        }

    by_edge, by_target = retry_deltas(_rows(run_dir / "service_edges.csv"))
    admitting = 0
    for row in _rows(run_dir / "topfull_throttle.csv"):
        threshold = int(float(row.get("threshold") or 0))
        if threshold not in (0, 10000):
            admitting += 1

    cpu: dict[str, list[float]] = defaultdict(list)
    for row in _rows(run_dir / "resource_usage.csv"):
        cpu[row["service"]].append(_num(row, "cpu_millicores"))
    cpu_mean_max = {
        service: (sum(values) / len(values), max(values))
        for service, values in cpu.items()
        if values
    }
    return {
        "inbound": inbound,
        "overloaded": overloaded,
        "retry_by_edge": by_edge,
        "retry_by_target": by_target,
        "layer_a_admitting_rows": admitting,
        "cpu_mean_max": cpu_mean_max,
    }


def _md(scored: dict) -> str:
    lines = ["| Service | streak / high | failure | overloaded | CPU mean / max | retry |",
             "|---|---:|---:|---:|---:|---:|"]
    names = sorted(set(scored["inbound"]) | set(scored["overloaded"]) | set(scored["cpu_mean_max"]) | set(scored["retry_by_target"]))
    for name in names:
        inbound = scored["inbound"].get(name, {})
        over = scored["overloaded"].get(name, {})
        cpu = scored["cpu_mean_max"].get(name)
        streak = inbound.get("streak", 0)
        high = inbound.get("high_samples", 0)
        frac = inbound.get("failure_fraction", 0.0)
        share = over.get("share", 0.0)
        hot = over.get("overloaded_ticks", 0)
        ticks = over.get("ticks", 0)
        cpu_cell = "" if cpu is None else f"{cpu[0]:.0f} / {cpu[1]:.0f}"
        lines.append(
            f"| {name} | {streak} / {high} | {frac:.3f} | {hot}/{ticks} ({share:.1%}) | {cpu_cell} | {scored['retry_by_target'].get(name, 0)} |"
        )
    lines.append("")
    lines.append(f"Layer A admitting rows (threshold not 0 or 10000): {scored['layer_a_admitting_rows']}")
    nonzero = [(k, v) for k, v in scored["retry_by_edge"].items() if v]
    nonzero.sort(key=lambda item: item[1], reverse=True)
    lines.append("Retry edges: " + ", ".join(f"{k} {v}" for k, v in nonzero[:12]))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python experiments/s2_both_off_abc.py <run_dir> [...]", file=sys.stderr)
        return 2
    for raw in argv[1:]:
        path = Path(raw)
        print(f"## {path.name}")
        print()
        print(_md(score_run(path)))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
