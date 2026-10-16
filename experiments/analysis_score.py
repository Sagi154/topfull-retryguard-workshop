"""Score one run folder, or a group of them, in the layout of
Guides and Info/ANALYSIS-TEMPLATE.md.

Reads the mesh CSVs and retryguard.log. Prints the tables an analysis
guide pastes. Setup prose, the gate verdict, per-arm prose, and the
related-links section stay with the agent.

    python experiments/analysis_score.py <run_dir> [<run_dir> ...]
    python experiments/analysis_score.py --sep 2 <run_a> <run_b> <run_c> <run_d>

--sep N inserts a bold bar after every N runs. Labels are the run number
at the end of the folder name.

Edge rpr uses the same formula as retryguard.measure_edge_rpr:
delta retry / (delta total - delta retry). A tick with no first attempts
is skipped and does not break a streak. The file streak is seconds from
the first consecutive scored tick with rpr above the shed bar to the last.
One tick is 0 seconds. The shed bar is rpr_threshold on the START line,
or 0.5 when the log has no START line.

Climb limits are climb_rpr_1_to_2 and climb_rpr_2_to_3 on the START
line. A log from before those fields existed uses retryguard.climb_rpr_limit
for the START line's rpr_threshold and attempts_on (0.17 and 0.33 at the
defaults). A climb streak is a count of OBSERVE samples, not seconds.

Rejection streaks use (delta 5xx + delta resets) / delta total, plus
delta grpc_4 + delta grpc_14 on the four read callees. That is the
controller's own formula (retryguard.measure_inbound_rejection). The
HTTP-only value for those four is kept in "rejection_http". A
non-positive total delta breaks a streak.
"""
from __future__ import annotations

import csv
import json
import re
import sys

import topfull_health
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SHED_RPR = 0.5
ATTEMPTS_ON = 3
REJECTION_HIGH = 0.20
REENABLE_REJECTION = 0.10
STREAK_BOLD_S = 30
REJECTION_BOLD = 30
OVERLOAD_BOLD = 0.5
# A live threshold at or above this is no cap: 10000 is the passthrough, and the RL can step a
# little below it (9999.55, 9997.5). Keep in step with run_timeline.NO_CAP and throttle_stale.NO_CAP.
NO_CAP_FROM = 9900
GAP_S = 1.5
THROTTLE_STALE_S = 10

SERVICES = (
    "frontend",
    "checkoutservice",
    "recommendationservice",
    "paymentservice",
    "emailservice",
    "productcatalogservice",
    "cartservice",
    "currencyservice",
    "shippingservice",
    "adservice",
    "redis-cart",
)
UNCONTROLLED = {"frontend", "redis-cart"}
APIS = ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")
GRPC_CALLEES = (
    "recommendationservice",
    "productcatalogservice",
    "currencyservice",
    "adservice",
)


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _num(row: dict, key: str) -> float:
    raw = row.get(key, "")
    if raw is None or raw == "":
        return 0.0
    return float(raw)


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _kv(tokens: list[str]) -> dict[str, str]:
    fields = {}
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return fields


def climb_limits(rpr_threshold: float, attempts_on: int) -> tuple[float, float]:
    """Match retryguard.climb_rpr_limit for attempts 1 and 2."""
    on = int(attempts_on)
    return (
        round(float(rpr_threshold) * 1 / on, 2),
        round(float(rpr_threshold) * 2 / on, 2),
    )


def edge_ticks(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Scored rpr ticks per caller, target. Unscored rows do not appear."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        caller = row.get("caller", "")
        target = row.get("target", "")
        if not caller or not target:
            continue
        grouped[(caller, target)].append(row)
    out: dict[tuple[str, str], list[dict]] = {}
    for key, series in grouped.items():
        series.sort(key=lambda row: row.get("timestamp", ""))
        ticks = []
        prev = None
        for row in series:
            ts = row.get("timestamp", "")
            total = _num(row, "total")
            retry = _num(row, "retry")
            if prev is None:
                prev = (ts, total, retry)
                continue
            if ts <= prev[0]:
                continue
            delta_retry = retry - prev[2]
            first = (total - prev[1]) - delta_retry
            prev = (ts, total, retry)
            if first <= 0:
                continue
            ticks.append(
                {
                    "timestamp": ts,
                    "rpr": delta_retry / first,
                    "delta_retry": delta_retry,
                    "first": first,
                }
            )
        out[key] = ticks
    return out


def file_streak(ticks: list[dict], shed: float) -> tuple[float, int]:
    """Seconds from the first consecutive high tick to the last, and the
    count of high ticks. One high tick is 0 seconds. A tick at or under
    the shed bar breaks the streak.
    """
    longest = 0.0
    high = 0
    start = None
    last = None
    for tick in ticks:
        if tick["rpr"] > shed:
            high += 1
            if start is None:
                start = tick["timestamp"]
            last = tick["timestamp"]
            span = (parse_ts(last) - parse_ts(start)).total_seconds()
            longest = max(longest, span)
        else:
            start = None
            last = None
    return longest, high


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def rpr_summary(ticks: list[dict]) -> tuple[float | None, float | None, float | None, float | None]:
    if not ticks:
        return None, None, None, None
    values = [tick["rpr"] for tick in ticks]
    first = sum(tick["first"] for tick in ticks)
    retry = sum(tick["delta_retry"] for tick in ticks)
    volume = (retry / first) if first else None
    return sum(values) / len(values), _median(values), max(values), volume


def positive_retry_delta(rows: list[dict]) -> dict[tuple[str, str], int]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("caller", ""), row.get("target", ""))].append(_num(row, "retry"))
    out = {}
    for key, values in grouped.items():
        delta = 0
        prev = None
        for value in values:
            if prev is not None and value > prev:
                delta += int(value - prev)
            prev = value
        out[key] = delta
    return out


def parse_log(text: str) -> dict:
    """OBSERVE samples, transition lines, and the thresholds on START."""
    observes: dict[str, list[dict]] = defaultdict(list)
    transitions = []
    params = {
        "rpr_threshold": SHED_RPR,
        "attempts_on": ATTEMPTS_ON,
        "rejection_threshold": REJECTION_HIGH,
        "reenable_rejection": REENABLE_REJECTION,
        "climb_rpr_1_to_2": None,
        "climb_rpr_2_to_3": None,
        "burst_rpr": None,
        "start": None,
    }
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if len(parts) >= 3 and parts[1] == "START":
            fields = _kv(parts[2:])
            params["start"] = parts[0]
            if "rpr_threshold" in fields:
                params["rpr_threshold"] = float(fields["rpr_threshold"])
            if "attempts_on" in fields:
                params["attempts_on"] = int(fields["attempts_on"])
            if "rejection_threshold" in fields:
                params["rejection_threshold"] = float(fields["rejection_threshold"])
            if "reenable_rejection" in fields:
                params["reenable_rejection"] = float(fields["reenable_rejection"])
            if "climb_rpr_1_to_2" in fields:
                params["climb_rpr_1_to_2"] = float(fields["climb_rpr_1_to_2"])
            if "climb_rpr_2_to_3" in fields:
                params["climb_rpr_2_to_3"] = float(fields["climb_rpr_2_to_3"])
            if "burst_rpr" in fields:
                params["burst_rpr"] = float(fields["burst_rpr"])
            continue
        if len(parts) >= 4 and parts[1] == "OBSERVE":
            fields = _kv(parts[3:])
            sample = {
                "timestamp": parts[0],
                "name": parts[2],
                "rpr": float(fields["rpr"]) if "rpr" in fields else None,
                "rejection": float(fields["rejection"]) if "rejection" in fields else None,
                "high": int(fields["high"]) if "high" in fields else 0,
                "attempts": int(fields["attempts"]) if "attempts" in fields else None,
                "burst": float(fields["burst_rpr5"]) if "burst_rpr5" in fields else None,
            }
            observes[parts[2]].append(sample)
            continue
        if len(parts) >= 3 and ("→" in parts[2] or "->" in parts[2]):
            step = parts[2].replace("->", "→")
            if "→" not in step:
                continue
            old, new = step.split("→", 1)
            fields = _kv(parts[3:])
            value = fields.get("rpr", fields.get("rejection"))
            transitions.append(
                {
                    "timestamp": parts[0],
                    "name": parts[1],
                    "old": old,
                    "new": new,
                    "step": f"{old}→{new}",
                    "value": float(value) if value is not None else None,
                    "metric": "rpr" if "rpr" in fields else "rejection",
                    "burst": fields.get("metric") == "rpr_burst",
                    "from_attempts": int(fields["from_attempts"]) if "from_attempts" in fields else None,
                    "attempts": int(fields["attempts"]) if "attempts" in fields else None,
                    "elapsed_s": int(fields["elapsed_s"]) if "elapsed_s" in fields else None,
                }
            )
    return {"observes": observes, "transitions": transitions, "params": params}


def climb_streak(samples: list[dict], attempts: int, limit: float) -> int | None:
    """Longest run of rpr <= limit while the edge is at `attempts`.
    A sample above the limit, or a sample at another attempt count, ends it.
    None when the edge never sat at that count.
    """
    seen = False
    current = 0
    longest = 0
    for sample in samples:
        if sample.get("attempts") != attempts or sample.get("rpr") is None:
            current = 0
            continue
        seen = True
        if sample["rpr"] <= limit:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    if not seen:
        return None
    return longest


def burst_summary(
    samples: list[dict], transitions: list[dict], name: str,
    burst_rpr: float, attempts_on: int,
) -> dict | None:
    """Peak / median burst_rpr5, samples at or above the bar in force, burst sheds.
    The bar is burst_rpr * attempts / attempts_on on each sample's own attempts.
    None when the edge has no burst_rpr5 samples and no burst shed."""
    values = [s["burst"] for s in samples if s.get("burst") is not None]
    sheds = sum(
        1 for t in transitions
        if t.get("burst") and t["step"] == "ON→OFF" and t["name"] == name
    )
    if not values and not sheds:
        return None
    at_bar = sum(
        1 for s in samples
        if s.get("burst") is not None and s.get("attempts")
        and s["burst"] >= burst_rpr * s["attempts"] / attempts_on
    )
    return {
        "samples": len(values),
        "peak": max(values) if values else None,
        "median": _median(values) if values else None,
        "at_bar": at_bar,
        "sheds": sheds,
    }


def controller_high(samples: list[dict]) -> int | None:
    highs = [sample["high"] for sample in samples if sample.get("rpr") is not None]
    if not highs:
        return None
    return max(highs)


def rejection_streaks(
    rows: list[dict], high_bar: float, low_bar: float, count_grpc: bool = False
) -> dict:
    """Longest / count above high_bar, and longest / count strictly under low_bar.

    Rows are one service, time-sorted. A non-positive total delta breaks
    both streaks and counts for neither. count_grpc adds grpc_4 + grpc_14
    and is the controller's formula on the four read callees
    (retryguard.measure_inbound_rejection(..., count_grpc=True)).
    """
    ordered = sorted(rows, key=lambda row: row.get("timestamp", ""))
    high_longest = high_count = 0
    low_longest = low_count = 0
    high_run = low_run = 0
    prev = None
    for row in ordered:
        total = _num(row, "total")
        failed = _num(row, "5xx") + _num(row, "resets")
        if count_grpc:
            failed += _num(row, "grpc_4") + _num(row, "grpc_14")
        if prev is None:
            prev = (total, failed)
            continue
        d_total = total - prev[0]
        d_fail = failed - prev[1]
        prev = (total, failed)
        if d_total <= 0:
            high_run = 0
            low_run = 0
            continue
        rate = d_fail / d_total
        if rate > high_bar:
            high_count += 1
            high_run += 1
            high_longest = max(high_longest, high_run)
        else:
            high_run = 0
        if rate < low_bar:
            low_count += 1
            low_run += 1
            low_longest = max(low_longest, low_run)
        else:
            low_run = 0
    return {
        "high_streak": high_longest,
        "high_count": high_count,
        "low_streak": low_longest,
        "low_count": low_count,
    }


def positive_column_delta(rows: list[dict], key: str) -> int:
    ordered = sorted(rows, key=lambda row: row.get("timestamp", ""))
    delta = 0
    prev = None
    for row in ordered:
        if key not in row:
            return 0
        value = _num(row, key)
        if prev is not None and value > prev:
            delta += int(value - prev)
        prev = value
    return delta


def inbound_hold(rows: list[dict]) -> dict:
    """Arrival (req/s), sojourn (ms), and the share of completions above 500 ms.

    Arrival is the sum of positive total deltas over the elapsed time.
    Sojourn is the sum of rq_time_sum_ms deltas over the sum of rq_time_count
    deltas, on ticks where the count rose. The share above 500 ms is
    1 - (delta of the cumulative le=500 bucket) / (delta rq_time_count).
    """
    ordered = sorted(rows, key=lambda row: row.get("timestamp", ""))
    if len(ordered) < 2:
        return {"arrival": None, "sojourn_ms": None, "over500": None}
    elapsed = (parse_ts(ordered[-1]["timestamp"]) - parse_ts(ordered[0]["timestamp"])).total_seconds()
    arrived = 0.0
    sum_ms = 0.0
    sum_count = 0.0
    le500 = 0.0
    le_count = 0.0
    prev = None
    for row in ordered:
        if prev is None:
            prev = row
            continue
        d_total = _num(row, "total") - _num(prev, "total")
        if d_total > 0:
            arrived += d_total
        d_count = _num(row, "rq_time_count") - _num(prev, "rq_time_count")
        d_sum = _num(row, "rq_time_sum_ms") - _num(prev, "rq_time_sum_ms")
        if d_count > 0 and d_sum >= 0:
            sum_count += d_count
            sum_ms += d_sum
            try:
                cur_b = json.loads(row.get("rq_time_buckets") or "{}")
                prev_b = json.loads(prev.get("rq_time_buckets") or "{}")
                if "500" in cur_b and "500" in prev_b:
                    d_le = float(cur_b["500"]) - float(prev_b["500"])
                    if d_le >= 0:
                        le500 += d_le
                        le_count += d_count
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        prev = row
    over = None
    if le_count > 0:
        over = max(0.0, 1.0 - le500 / le_count)
    return {
        "arrival": (arrived / elapsed) if elapsed > 0 else None,
        "sojourn_ms": (sum_ms / sum_count) if sum_count > 0 else None,
        "over500": over,
    }


def locust_table(path: Path) -> dict | None:
    """Mean Goodput, mean Fail/RPS, and mean Latency95 on rows with RPS > 0."""
    rows = [row for row in _rows(path) if _num(row, "RPS") > 0]
    if not rows:
        return None
    fail_rates = [_num(row, "Fail") / _num(row, "RPS") for row in rows]
    return {
        "rows": len(_rows(path)),
        "goodput": sum(_num(row, "Goodput") for row in rows) / len(rows),
        "fail": sum(fail_rates) / len(fail_rates),
        "p95": sum(_num(row, "Latency95") for row in rows) / len(rows),
    }


def mode(values: list[float]) -> float | None:
    if not values:
        return None
    counts: dict[float, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return max(counts, key=lambda item: (counts[item], item))


def live_caps(rows: list[dict]) -> dict[str, list[dict]]:
    """Distinct live TopFull caps per API.

    A live read has threshold_fresh=1 and threshold > 0. 9900 and above is no cap.
    A live 0 is an empty read and is left out.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if int(float(row.get("threshold_fresh") or 0)) != 1:
            continue
        threshold = float(row.get("threshold") or 0)
        if threshold <= 0:
            continue
        api = row.get("api", "")
        value = None if threshold >= NO_CAP_FROM else threshold
        grouped[api].append({"timestamp": row.get("timestamp", ""), "value": value})
    out = {}
    for api, series in grouped.items():
        series.sort(key=lambda item: item["timestamp"])
        spans = []
        for item in series:
            if spans and spans[-1]["value"] == item["value"]:
                spans[-1]["end"] = item["timestamp"]
                continue
            spans.append({"start": item["timestamp"], "end": item["timestamp"], "value": item["value"]})
        out[api] = spans
    return out


def _longest_gap(stamps: list[datetime], fresh: list[bool]) -> float | None:
    """Longest stretch (s) with no fresh read, including the head and the tail."""
    if not stamps:
        return None
    last = stamps[0]
    worst = 0.0
    for stamp, ok in zip(stamps, fresh):
        if ok:
            worst = max(worst, (stamp - last).total_seconds())
            last = stamp
    return max(worst, (stamps[-1] - last).total_seconds())


def topfull_enabled(run_dir: Path) -> bool:
    """True unless run_manifest.json says topfull_rl.enabled is false.

    A missing file, a read error, or a body that is not JSON means on.
    """
    path = Path(run_dir) / "run_manifest.json"
    if not path.is_file():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(data, dict):
        return True
    block = data.get("topfull_rl")
    if not isinstance(block, dict):
        return True
    return bool(block.get("enabled", True))


def throttle_quality(rows: list[dict], log_path: Path, topfull_on: bool = True) -> dict:
    """How trustworthy topfull_throttle.csv is for this hold.

    Live reads of the TopFull proxy (/thresholds, /stats) normally land every 5 s.
    A TopFull-on hold is flagged when topfull_throttle_collector.log has any fetch
    WARNING, or when any API goes longer than THROTTLE_STALE_S without a fresh
    threshold or admitted read. A TopFull-off hold is never flagged. Warnings and
    gaps are still reported.
    """
    warnings = 0
    first_warning = None
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "WARNING" in line and "fetch failed" in line:
                warnings += 1
                if first_warning is None:
                    first_warning = line.split()[0]
    by_api: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("timestamp"):
            by_api[row.get("api", "")].append(row)
    gaps: dict[str, float | None] = {"threshold_fresh": None, "admitted_fresh": None}
    for series in by_api.values():
        series.sort(key=lambda r: r["timestamp"])
        stamps = [parse_ts(r["timestamp"]) for r in series]
        for key in gaps:
            gap = _longest_gap(stamps, [int(float(r.get(key) or 0)) == 1 for r in series])
            if gap is not None and (gaps[key] is None or gap > gaps[key]):
                gaps[key] = gap
    worst = max([g for g in gaps.values() if g is not None], default=None)
    would_flag = warnings > 0 or (worst is not None and worst > THROTTLE_STALE_S)
    return {
        "has_csv": bool(rows),
        "warnings": warnings,
        "first_warning": first_warning,
        "threshold_gap_s": gaps["threshold_fresh"],
        "admitted_gap_s": gaps["admitted_fresh"],
        "topfull_on": bool(topfull_on),
        "flagged": bool(would_flag and topfull_on),
        "would_flag": bool(would_flag),
    }


SUSPECTED = "PROXY STALL SUSPECTED"


def proxy_stall_status(quality: dict, health) -> tuple[str, str]:
    """(status, detail) for one row of the Proxy and RL health table.

    Direct evidence (`PROXY FD`, `RL STALL`) wins. Without a proxy, descriptor, or RL
    log (every hold before 2026-10-15) the throttle collector's own warnings and stale
    stretches are the only record of a proxy stall, and they exist on every variant,
    TopFull off included. A hold with logs and collector warnings but no descriptor
    exhaustion is named, not accused: the timeouts then have another cause.
    """
    if health.rl_stall or health.proxy_fd:
        return f"**{health.status}**", "; ".join(health.reasons) or "—"
    evidence = bool(quality.get("would_flag") and quality.get("has_csv"))
    worst = max([g for g in (quality.get("threshold_gap_s"), quality.get("admitted_gap_s"))
                 if g is not None], default=0.0)
    seen = (f"throttle collector: {quality.get('warnings', 0)} fetch warning(s), "
            f"longest no-fresh read {worst:.0f} s")
    if not health.assessable:
        if evidence:
            return f"**{SUSPECTED}**", f"{seen}; no proxy or descriptor log to confirm"
        return "not assessable", "no proxy, descriptor, or RL log"
    if evidence:
        return "admin timeouts, no fd cause", f"{seen}; the proxy log and descriptor file show no exhaustion"
    return "ok", "—"


def mesh_gate(inbound_rows: list[dict]) -> dict:
    by_service: dict[str, list[str]] = defaultdict(list)
    for row in inbound_rows:
        by_service[row.get("service", "")].append(row.get("timestamp", ""))
    gaps = 0
    pairs = 0
    stamps = []
    for stamps_for in by_service.values():
        ordered = sorted(stamp for stamp in stamps_for if stamp)
        stamps.extend(ordered)
        for prev, cur in zip(ordered, ordered[1:]):
            pairs += 1
            if (parse_ts(cur) - parse_ts(prev)).total_seconds() >= GAP_S:
                gaps += 1
    span = None
    if stamps:
        ordered = sorted(stamps)
        span = (parse_ts(ordered[-1]) - parse_ts(ordered[0])).total_seconds()
    return {"span_s": span, "gaps": gaps, "pairs": pairs}


def score_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    edge_rows = _rows(run_dir / "service_edges.csv")
    inbound_rows = _rows(run_dir / "service_inbound.csv")
    detect_rows = _rows(run_dir / "topfull_detect.csv")
    usage_rows = _rows(run_dir / "resource_usage.csv")
    throttle_rows = _rows(run_dir / "topfull_throttle.csv")
    log_path = run_dir / "retryguard.log"
    log = parse_log(log_path.read_text(encoding="utf-8", errors="replace")) if log_path.is_file() else parse_log("")
    shed = log["params"]["rpr_threshold"]
    formula_1, formula_2 = climb_limits(shed, log["params"]["attempts_on"])
    limit_1 = log["params"]["climb_rpr_1_to_2"]
    limit_2 = log["params"]["climb_rpr_2_to_3"]
    if limit_1 is None:
        limit_1 = formula_1
    if limit_2 is None:
        limit_2 = formula_2
    high_bar = log["params"]["rejection_threshold"]
    low_bar = log["params"]["reenable_rejection"]

    ticks = edge_ticks(edge_rows)
    retry_by_edge = positive_retry_delta(edge_rows)
    edges = {}
    names = set(ticks) | set(retry_by_edge)
    for caller, target in names:
        if not caller:
            continue
        series = ticks.get((caller, target), [])
        streak_s, high_ticks = file_streak(series, shed)
        mean_rpr, median_rpr, max_rpr, volume = rpr_summary(series)
        log_name = f"{caller}->{target}"
        samples = log["observes"].get(log_name, [])
        burst = None
        if log["params"]["burst_rpr"] is not None:
            burst = burst_summary(
                samples, log["transitions"], log_name,
                log["params"]["burst_rpr"], log["params"]["attempts_on"],
            )
        edges[log_name] = {
            "burst": burst,
            "streak_s": streak_s,
            "high_ticks": high_ticks,
            "controller_high": controller_high(samples),
            "mean_rpr": mean_rpr,
            "median_rpr": median_rpr,
            "max_rpr": max_rpr,
            "volume_rpr": volume,
            "climb_1": climb_streak(samples, 1, limit_1),
            "climb_2": climb_streak(samples, 2, limit_2),
            "retry_delta": retry_by_edge.get((caller, target), 0),
        }

    if log["params"]["burst_rpr"] is not None:
        for log_name, samples in log["observes"].items():
            if "->" not in log_name or log_name in edges:
                continue
            burst = burst_summary(
                samples, log["transitions"], log_name,
                log["params"]["burst_rpr"], log["params"]["attempts_on"],
            )
            if burst is not None:
                edges[log_name] = {
                    "burst": burst, "streak_s": 0.0, "high_ticks": 0,
                    "controller_high": controller_high(samples),
                    "mean_rpr": None, "median_rpr": None, "max_rpr": None,
                    "volume_rpr": None, "climb_1": None, "climb_2": None,
                    "retry_delta": 0,
                }

    by_service: dict[str, list[dict]] = defaultdict(list)
    for row in inbound_rows:
        by_service[row.get("service", "")].append(row)
    rejection = {}
    rejection_http = {}
    resets = {}
    grpc = {}
    inbound = {}
    for service, rows in by_service.items():
        matched = service in GRPC_CALLEES
        rejection[service] = rejection_streaks(rows, high_bar, low_bar, count_grpc=matched)
        if matched:
            rejection_http[service] = rejection_streaks(rows, high_bar, low_bar)
        resets[service] = positive_column_delta(rows, "resets")
        grpc[service] = {
            "grpc_4": positive_column_delta(rows, "grpc_4"),
            "grpc_14": positive_column_delta(rows, "grpc_14"),
        }
        inbound[service] = inbound_hold(rows)

    flags: dict[str, list[int]] = defaultdict(list)
    quotas: dict[str, list[float]] = defaultdict(list)
    utils: dict[str, list[float]] = defaultdict(list)
    alphas: dict[str, list[float]] = defaultdict(list)
    for row in detect_rows:
        service = row.get("service", "")
        flags[service].append(int(float(row.get("overloaded") or 0)))
        quotas[service].append(_num(row, "quota"))
        utils[service].append(_num(row, "utilization"))
        alphas[service].append(_num(row, "alpha"))
    overloaded = {}
    for service, series in flags.items():
        hot = sum(series)
        ticks_n = len(series)
        overloaded[service] = {
            "hot": hot,
            "ticks": ticks_n,
            "share": (hot / ticks_n) if ticks_n else 0.0,
            "util_max": max(utils[service]) if utils[service] else None,
            "quota": mode(quotas[service]),
            "alpha": mode(alphas[service]),
        }

    cpu_values: dict[str, list[float]] = defaultdict(list)
    replicas: dict[str, list[int]] = defaultdict(list)
    fractions: dict[str, list[float]] = defaultdict(list)
    for row in usage_rows:
        service = row.get("service", "")
        cpu = _num(row, "cpu_millicores")
        replica = int(float(row.get("replica_count") or 0))
        cpu_values[service].append(cpu)
        replicas[service].append(replica)
        quota = overloaded.get(service, {}).get("quota")
        if quota and replica > 0:
            fractions[service].append(cpu / (quota * replica))
    cpu = {}
    for service, values in cpu_values.items():
        frac = fractions.get(service, [])
        reps = replicas[service]
        cpu[service] = {
            "mean": sum(values) / len(values),
            "max": max(values),
            "replicas": mode([float(item) for item in reps]),
            "replica_min": min(reps),
            "replica_max": max(reps),
            "samples": len(reps),
            "fraction_mean": (sum(frac) / len(frac)) if frac else None,
            "fraction_max": max(frac) if frac else None,
        }

    locust = {}
    for api in APIS:
        table = locust_table(run_dir / f"{api}.csv")
        if table is not None:
            locust[api] = table
    total_rows = _rows(run_dir / "total.csv")
    return {
        "dir": str(run_dir),
        "params": log["params"],
        "climb_limits": (limit_1, limit_2),
        "has_log": log_path.is_file(),
        "edges": edges,
        "rejection": rejection,
        "rejection_http": rejection_http,
        "resets": resets,
        "grpc": grpc,
        "inbound": inbound,
        "overloaded": overloaded,
        "cpu": cpu,
        "locust": locust,
        "locust_total_rows": len(total_rows),
        "transitions": log["transitions"],
        "caps": live_caps(throttle_rows),
        "throttle_quality": throttle_quality(
            throttle_rows, run_dir / "topfull_throttle_collector.log",
            topfull_on=topfull_enabled(run_dir),
        ),
        "proxy_rl_health": topfull_health.assess(run_dir, topfull_on=topfull_enabled(run_dir)),
        "gate": mesh_gate(inbound_rows),
    }


def label_for(path: Path) -> str:
    match = re.search(r"run(\d+)$", path.name)
    return match.group(1) if match else path.name


def labels_for(paths: list[Path]) -> list[str]:
    raw = [label_for(path) for path in paths]
    if len(raw) == len(set(raw)):
        return raw
    return [f"{path.parent.name}/{label_for(path)}" for path in paths]


def _fmt(value, spec: str) -> str:
    if value is None:
        return "—"
    return format(value, spec)


def _int_cell(value: float | None) -> str:
    if value is None:
        return "—"
    return str(int(round(value)))


def _bold(text: str, on: bool) -> str:
    return f"**{text}**" if on else text


def _groups(n: int, sep: int | None) -> list[int]:
    """Column counts. A None sep is one group."""
    if not sep or sep >= n:
        return [n]
    counts = []
    left = n
    while left > 0:
        take = min(sep, left)
        counts.append(take)
        left -= take
    return counts


def _header(labels: list[str], sep: int | None) -> tuple[str, str]:
    heads = ["|"]
    align = ["|"]
    for index, label in enumerate(labels):
        if index and sep and index % sep == 0:
            heads.append(" **┃** |")
            align.append(" :---: |")
        heads.append(f" {label} |")
        align.append(" ---: |")
    return "".join(heads), "".join(align)


def _cells(values: list[str], sep: int | None) -> str:
    parts = ["|"]
    for index, value in enumerate(values):
        if index and sep and index % sep == 0:
            parts.append(" **┃** |")
        parts.append(f" {value} |")
    return "".join(parts)


def _table(title: str, row_name: str, labels: list[str], rows: list[tuple[str, list[str]]], sep: int | None) -> str:
    head, align = _header(labels, sep)
    lines = [f"## {title}", "", f"| {row_name} {head}", f"| --- {align}"]
    for name, values in rows:
        lines.append(f"| {name} {_cells(values, sep)}")
    lines.append("")
    return "\n".join(lines)


def _active_edges(scored: list[dict]) -> list[str]:
    names = []
    for item in scored:
        for name, edge in item["edges"].items():
            if name in names:
                continue
            if edge["high_ticks"] or edge["retry_delta"] or edge["mean_rpr"]:
                names.append(name)
    return names


def _edge_label(name: str) -> str:
    return name.replace("->", " → ")


def render(scored: list[dict], labels: list[str], sep: int | None = None) -> str:
    lines = []
    first = scored[0]
    limit_1, limit_2 = first["climb_limits"]
    lines.append(
        f"Shed bar rpr > {first['params']['rpr_threshold']:.2f}. "
        f"Climb bars rpr ≤ {limit_1:.2f} at 1 attempt and rpr ≤ {limit_2:.2f} at 2 attempts. "
        f"Rejection high bar {first['params']['rejection_threshold']:.2f}, "
        f"re-enable bar {first['params']['reenable_rejection']:.2f}."
    )
    lines.append("")
    lines.append("## Gate numbers")
    lines.append("")
    for label, item in zip(labels, scored):
        gate = item["gate"]
        span = "—" if gate["span_s"] is None else f"{gate['span_s']:.0f} s"
        lines.append(
            f"- {label}: Locust total.csv {item['locust_total_rows']} rows, "
            f"mesh span {span}, inbound gaps ≥ {GAP_S:g} s: {gate['gaps']} of {gate['pairs']}, "
            f"retryguard.log {'present' if item['has_log'] else 'absent'}."
        )
        for service in SERVICES:
            cpu = item["cpu"].get(service)
            if not cpu:
                continue
            if cpu["replica_min"] != cpu["replica_max"] or cpu["replica_min"] == 0:
                lines.append(
                    f"  - {service} replicas {cpu['replica_min']}–{cpu['replica_max']} "
                    f"on {cpu['samples']} samples"
                )
    lines.append("")

    edges = _active_edges(scored)
    if not edges:
        lines.append("## (a) Edge rpr")
        lines.append("")
        lines.append("No controlled edge has a tick above the shed bar or a retry delta.")
        lines.append("")
    else:
        streak_rows = []
        summary_rows = []
        climb_rows = []
        for name in edges:
            streak_cells = []
            summary_cells = []
            climb_cells = []
            for item in scored:
                edge = item["edges"].get(name)
                if not edge:
                    streak_cells.append("—")
                    summary_cells.append("—")
                    climb_cells.append("— / —")
                    continue
                high = edge["controller_high"]
                parenthetical = "" if high is None else f" ({high})"
                cell = f"{_int_cell(edge['streak_s'])} / {edge['high_ticks']}{parenthetical}"
                if edge["streak_s"] >= STREAK_BOLD_S:
                    cell = _bold(cell, True)
                streak_cells.append(cell)
                summary_cells.append(
                    f"{_fmt(edge['mean_rpr'], '.3f')} / {_fmt(edge['median_rpr'], '.3f')} / {_fmt(edge['max_rpr'], '.2f')} / {_fmt(edge['volume_rpr'], '.3f')}"
                )
                climb_cells.append(f"{_fmt(edge['climb_1'], 'd')} / {_fmt(edge['climb_2'], 'd')}")
            streak_rows.append((_edge_label(name), streak_cells))
            summary_rows.append((_edge_label(name), summary_cells))
            climb_rows.append((_edge_label(name), climb_cells))
        lines.append(_table(
            "(a) Edge rpr, file streak seconds / ticks above the shed bar (controller high)",
            "Edge", labels, streak_rows, sep,
        ))
        lines.append("Mean rpr / median rpr / max rpr / volume rpr. Median is the median of the scored per-tick rpr values. Volume is the hold's delta retry / first attempts.")
        lines.append("")
        lines.append(_table("(a) Mean / median / max / volume rpr", "Edge", labels, summary_rows, sep))
        lines.append(
            "Climb streaks are OBSERVE samples while that attempt cap is in force. "
            "An em dash means the edge never ran at that cap."
        )
        lines.append("")
        lines.append(_table("(a) Climb streaks, 1-attempt / 2-attempt", "Edge", labels, climb_rows, sep))

    if any(item["params"].get("burst_rpr") is not None for item in scored):
        bars = [
            (label, item["params"]["burst_rpr"])
            for label, item in zip(labels, scored)
            if item["params"].get("burst_rpr") is not None
        ]
        lines.append(
            "Burst bars: "
            + "; ".join(
                f"{label} burst_rpr {bar:.2f} (bar at 3 / 2 / 1 attempts "
                f"{bar:.2f} / {bar * 2 / 3:.2f} / {bar / 3:.2f})"
                for label, bar in bars
            )
            + ". Window and volume floor are on the START line."
        )
        lines.append("")
        burst_names = []
        for item in scored:
            for name, edge in item["edges"].items():
                if edge.get("burst") and name not in burst_names:
                    burst_names.append(name)
        if not burst_names:
            lines.append("## (a2) Burst window")
            lines.append("")
            lines.append("No edge has a burst_rpr5 sample or a burst shed.")
            lines.append("")
        else:
            burst_rows = []
            for name in burst_names:
                cells = []
                for item in scored:
                    burst = (item["edges"].get(name) or {}).get("burst")
                    if not burst:
                        cells.append("—")
                        continue
                    cells.append(
                        f"{_fmt(burst['peak'], '.2f')} / {_fmt(burst['median'], '.2f')} / "
                        f"{burst['at_bar']} / {burst['sheds']} ({burst['samples']})"
                    )
                burst_rows.append((_edge_label(name), cells))
            lines.append(
                "Peak burst_rpr5 / median burst_rpr5 / OBSERVE samples at or above the bar in force "
                "(burst_rpr × attempts / attempts_on) / burst sheds, with the burst_rpr5 sample count "
                "in parentheses. Samples exist only while the edge is above 0 attempts and the "
                "window meets the volume floor."
            )
            lines.append("")
            lines.append(_table("(a2) Burst window", "Edge", labels, burst_rows, sep))

    def rejection_rows(
        key_streak: str,
        key_count: str,
        bold_at: int | None,
        source: str = "rejection",
        services: tuple[str, ...] = SERVICES,
    ) -> list[tuple[str, list[str]]]:
        rows = []
        for service in services:
            cells = []
            for item in scored:
                stats = item[source].get(service)
                if not stats:
                    cells.append("—")
                    continue
                text = f"{stats[key_streak]} / {stats[key_count]}"
                if bold_at is not None and stats[key_streak] >= bold_at and service not in UNCONTROLLED:
                    text = _bold(text, True)
                cells.append(text)
            label = service
            if service in UNCONTROLLED:
                label = f"{service} (not controlled)"
            rows.append((label, cells))
        return rows

    lines.append(_table(
        "(a) context: rejection streak above 0.20 / count. Not the shed signal",
        "Service", labels, rejection_rows("high_streak", "high_count", REJECTION_BOLD), sep,
    ))
    lines.append(_table(
        "(a) context: rejection streak under the re-enable bar / count",
        "Service", labels, rejection_rows("low_streak", "low_count", None), sep,
    ))
    lines.append(_table(
        "(a) context: HTTP-only rejection (5xx + resets) streak above 0.20 / count, four read callees",
        "Service", labels,
        rejection_rows("high_streak", "high_count", None, "rejection_http", GRPC_CALLEES), sep,
    ))
    lines.append(_table(
        "(a) context: HTTP-only rejection (5xx + resets) streak under the re-enable bar / count, four read callees",
        "Service", labels,
        rejection_rows("low_streak", "low_count", None, "rejection_http", GRPC_CALLEES), sep,
    ))
    grpc_rows = []
    for service in GRPC_CALLEES:
        cells = []
        for item in scored:
            pair = item["grpc"].get(service, {})
            cells.append(f"{pair.get('grpc_4', 0):,} / {pair.get('grpc_14', 0):,}")
        grpc_rows.append((service, cells))
    lines.append("gRPC counted in the rejection rate on the four read callees (main rejection tables above) and in the retry policy. Cell is grpc_4 / grpc_14.")
    lines.append("")
    lines.append(_table("grpc_4 / grpc_14", "Service", labels, grpc_rows, sep))

    over_rows = []
    for service in SERVICES:
        cells = []
        for item in scored:
            stats = item["overloaded"].get(service)
            if not stats:
                cells.append("—")
                continue
            text = f"{stats['hot']}/{stats['ticks']} ({stats['share']:.1%})"
            if stats["share"] >= OVERLOAD_BOLD:
                text = _bold(text, True)
            cells.append(text)
        over_rows.append((service, cells))
    lines.append(_table("(b) Detector overloaded fraction", "Service", labels, over_rows, sep))

    retry_targets: dict[str, list[int]] = defaultdict(lambda: [0] * len(scored))
    for index, item in enumerate(scored):
        for name, edge in item["edges"].items():
            target = name.split("->", 1)[1]
            retry_targets[target][index] += edge["retry_delta"]
    retry_rows = []
    for service in SERVICES:
        values = retry_targets.get(service, [0] * len(scored))
        if not any(values):
            continue
        retry_rows.append((service, [f"{value:,}" for value in values]))
    if not retry_rows:
        lines.append("## (c) Outbound retry delta")
        lines.append("")
        lines.append("Outbound retry delta is 0 on every target.")
        lines.append("")
    else:
        lines.append(_table("(c) Outbound retry delta by target", "Service", labels, retry_rows, sep))
    reset_rows = []
    for service in SERVICES:
        cells = [f"{item['resets'].get(service, 0):,}" for item in scored]
        reset_rows.append((service, cells))
    lines.append(_table("(c) Inbound resets", "Service", labels, reset_rows, sep))

    lines.append("## RetryGuard toggles")
    lines.append("")
    any_toggle = False
    for label, item in zip(labels, scored):
        if not item["transitions"]:
            lines.append(f"{label}: no transition lines.")
            continue
        any_toggle = True
        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"ON→OFF": 0, "OFF→ON": 0, "1→2": 0, "2→3": 0, "burst": 0}
        )
        for event in item["transitions"]:
            step = event["step"]
            if step in counts[event["name"]]:
                counts[event["name"]][step] += 1
            if event.get("burst") and step == "ON→OFF":
                counts[event["name"]]["burst"] += 1
        has_burst = any(count["burst"] for count in counts.values())
        lines.append(f"### {label}")
        lines.append("")
        lines.append(
            "| Name | ON→OFF | 0→1 | 1→2 | 2→3 |" + (" ON→OFF burst |" if has_burst else "")
        )
        lines.append("| --- | ---: | ---: | ---: | ---: |" + (" ---: |" if has_burst else ""))
        for name, count in counts.items():
            row = (
                f"| {_edge_label(name)} | {count['ON→OFF']} | {count['OFF→ON']} | "
                f"{count['1→2']} | {count['2→3']} |"
            )
            if has_burst:
                row += f" {count['burst']} |"
            lines.append(row)
        lines.append("")
        lines.append("| Time (UTC) | Name | Step | From | Value |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for event in item["transitions"]:
            value = "—"
            if event["value"] is not None:
                kind = "rpr" if event["metric"] == "rpr" else "rejection"
                value = f"{kind} {event['value']:.2f}"
            origin = event["from_attempts"]
            if origin is None and event["old"].isdigit():
                origin = int(event["old"])
            lines.append(
                f"| {event['timestamp']} | {_edge_label(event['name'])} | "
                f"{event['step']}{' (burst)' if event.get('burst') else ''} | "
                f"{'—' if origin is None else origin} | {value} |"
            )
        lines.append("")
    if not any_toggle:
        lines.append("")

    for title, key, spec in (
        ("Locust goodput", "goodput", ".1f"),
        ("Locust fail rate", "fail", ".3f"),
        ("Locust P95", "p95", ".0f"),
    ):
        rows = []
        for api in APIS:
            cells = []
            for item in scored:
                table = item["locust"].get(api)
                cells.append(_fmt(None if table is None else table[key], spec))
            rows.append((api, cells))
        lines.append(_table(title, "API", labels, rows, sep))

    for title, key, spec in (
        ("Inbound arrival rate", "arrival", ".1f"),
        ("Inbound sojourn (ms)", "sojourn_ms", ".0f"),
        ("Share of inbound requests above 500 ms", "over500", ".3f"),
    ):
        rows = []
        for service in SERVICES:
            cells = []
            for item in scored:
                stats = item["inbound"].get(service, {})
                cells.append(_fmt(stats.get(key), spec))
            rows.append((service, cells))
        lines.append(_table(title, "Service", labels, rows, sep))

    cpu_rows = []
    frac_rows = []
    util_rows = []
    for service in SERVICES:
        cpu_cells = []
        frac_cells = []
        util_cells = []
        for item in scored:
            cpu = item["cpu"].get(service)
            over = item["overloaded"].get(service, {})
            if not cpu:
                cpu_cells.append("—")
                frac_cells.append("—")
            else:
                quota = over.get("quota")
                reps = _int_cell(cpu["replicas"])
                quota_text = "—" if quota is None else str(int(quota))
                cpu_cells.append(f"{quota_text} / {reps} / {cpu['mean']:.0f} / {cpu['max']:.0f}")
                frac_cells.append(
                    f"{_fmt(cpu['fraction_mean'], '.2f')} / {_fmt(cpu['fraction_max'], '.2f')}"
                )
            util_cells.append(_fmt(over.get("util_max"), ".3f"))
        cpu_rows.append((service, cpu_cells))
        frac_rows.append((service, frac_cells))
        util_rows.append((service, util_cells))
    lines.append(
        "CPU cells are per-pod quota / replica mode / mean millicores / max millicores. "
        "Mean and max sum usage across replicas."
    )
    lines.append("")
    lines.append(_table("CPU quota / replicas / mean / max", "Service", labels, cpu_rows, sep))
    lines.append(_table(
        "CPU as a fraction of per-pod quota × replicas (mean / max)",
        "Service", labels, frac_rows, sep,
    ))
    lines.append(_table("Detector max utilization", "Service", labels, util_rows, sep))

    lines.append("## Throttle data quality")
    lines.append("")
    lines.append(
        f"Live reads of the TopFull proxy normally land every 5 s. A hold is **FLAGGED** only "
        f"when TopFull is on and `topfull_throttle_collector.log` has any `fetch failed` WARNING, "
        f"or an API goes longer than {THROTTLE_STALE_S} s without a fresh threshold or admitted "
        f"read. A TopFull-off hold (`rg_only`, `both_off`) is `N/A: TopFull off`, not a flag. "
        f"Cap and admitted-rate numbers on a flagged hold are carried values; filter on "
        f"`*_fresh==1`. The rows stay in the file. Goodput, P95 and rejection do not use this file."
    )
    lines.append("")
    lines.append(
        "| Hold | Status | Fetch warnings | First warning | "
        "Longest no-fresh threshold (s) | Longest no-fresh admitted (s) |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for label, item in zip(labels, scored):
        q = item["throttle_quality"]
        if not q["has_csv"]:
            lines.append(f"| {label} | no topfull_throttle.csv | — | — | — | — |")
            continue
        if not q.get("topfull_on", True):
            status = "N/A: TopFull off"
        elif q["flagged"]:
            status = "**FLAGGED**"
        else:
            status = "ok"
        first = q["first_warning"][11:19] if q["first_warning"] else "—"
        lines.append(
            f"| {label} | {status} | {q['warnings']} | {first} | "
            f"{_fmt(q['threshold_gap_s'], '.0f')} | {_fmt(q['admitted_gap_s'], '.0f')} |"
        )
    lines.append("")
    lines.append("## Proxy and RL health")
    lines.append("")
    lines.append(
        "Separate from the throttle flag. **PROXY FD**: the Go proxy ran out of file descriptors "
        "(`too many open files` in `topfull_proxy.log`, or `proxy_fds.csv` reached its soft limit). "
        "It refuses new connections on every variant, `rg_only` and `both_off` included, so "
        "goodput, P95, rejection, and retry numbers of that hold are not assumed clean. "
        "**RL STALL** (TopFull on only): the RL loop was silent over 30 s, a `current_rps` call "
        "timed out or took over 3 s; caps stopped moving. `not assessable` means the hold has no "
        "proxy, descriptor, or RL log (every hold before 2026-10-15). "
        "**PROXY STALL SUSPECTED**: no proxy or descriptor log exists, but the throttle collector "
        "saw fetch warnings or a stale stretch, which on any variant (TopFull off included) is the "
        "only trace of a proxy stall; do not assume the hold's goodput, P95, rejection, and retry "
        "numbers are clean."
    )
    lines.append("")
    lines.append("| Hold | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for label, item in zip(labels, scored):
        health = item["proxy_rl_health"]
        status, detail = proxy_stall_status(item["throttle_quality"], health)
        lines.append(f"| {label} | {status} | {detail} |")
    lines.append("")
    lines.append("## TopFull live caps")
    lines.append("")
    lines.append("A live read has threshold_fresh=1 and threshold above 0. 9900 and above is no cap. A live 0 is left out.")
    lines.append("")
    for label, item in zip(labels, scored):
        lines.append(f"### {label}")
        lines.append("")
        if not item["caps"]:
            lines.append("No live threshold reads.")
            lines.append("")
            continue
        lines.append("| API | Live caps |")
        lines.append("| --- | --- |")
        for api in APIS:
            spans = item["caps"].get(api, [])
            if not spans:
                lines.append(f"| {api} | no live read |")
                continue
            bits = []
            for span in spans:
                text = "no cap" if span["value"] is None else f"{span['value']:g}"
                if span["start"] == span["end"]:
                    bits.append(f"{text} at {span['start'][11:19]}")
                else:
                    bits.append(f"{text} {span['start'][11:19]}–{span['end'][11:19]}")
            lines.append(f"| {api} | {'; '.join(bits)} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    # Windows consoles default to cp1252, which cannot encode the ≤ used in the report.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sep = None
    paths: list[str] = []
    args = argv[1:]
    index = 0
    while index < len(args):
        if args[index] == "--sep":
            sep = int(args[index + 1])
            index += 2
            continue
        paths.append(args[index])
        index += 1
    if not paths:
        print("usage: python experiments/analysis_score.py [--sep N] <run_dir> [...]", file=sys.stderr)
        return 2
    folders = [Path(path) for path in paths]
    scored = [score_run(folder) for folder in folders]
    print(render(scored, labels_for(folders), sep), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
