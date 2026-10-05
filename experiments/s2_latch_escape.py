"""Escape-time rescore and frontend concurrency for S2 latch holds.

Offline only. Reads pulled folders under experiments/results/new vms/.
Reuses trim conventions from s2_both_off_canon (drop last 5 inbound polls)
and sticky/released classify from s2_latch_probe.

CLI:
  python experiments/s2_latch_escape.py score [--set v2|v1|same_mix|all]
  python experiments/s2_latch_escape.py align [--set v2]
  python experiments/s2_latch_escape.py json [--set v2]   # machine-readable dump
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_service_mu as mu  # noqa: E402
import s2_both_off_canon as canon  # noqa: E402
import s2_latch_probe as probe  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
NEW_VMS = probe.NEW_VMS

# Default escape rule (plan).
DEFAULT_RATE = 560.0
DEFAULT_PERSIST = 5
SENSITIVITY_RATES = (520.0, 560.0, 600.0)
SENSITIVITY_PERSIST = (3, 5, 10)

TAIL_TRIM = 5
GAP_DT = 1.5  # seconds; dt >= this is a scrape hole
MAX_GAP2_PCT = 10  # concurrency usable if gap2_pct <= this
LATCH_SOJOURN_MS = 480.0
LATCH_ARRIVAL = 50.0
LATCH_PERSIST = 5

# v2 scored holds (run136 / run138 failed sampling). Treatments from the
# results guide: shuffle of hold_order(20261004, 128) applied to slots 132-151,
# with replacements 152/153 for the failed arms.
V2_TREATMENT = {
    132: "control", 133: "spawn10", 134: "control", 135: "ck_cpu1000_pc120",
    137: "ck_rep2_pc120", 139: "control", 140: "ck_rep2_pc120_spawn10",
    141: "ck_cpu1000_pc120_spawn10", 142: "spawn10", 143: "control",
    144: "recs_cpu1000_spawn10", 145: "ck_rep2_pc120_spawn10",
    146: "ck_cpu1000_pc120", 147: "control", 148: "recs_cpu1000",
    149: "ck_cpu1000_pc120_spawn10", 150: "ck_rep2_pc120", 151: "control",
    152: "recs_cpu1000_spawn10", 153: "recs_cpu1000",
}
V2_SCORED = sorted(V2_TREATMENT)

# First latch probe (seed 20261003). Run116 failed; run127 not run.
V1_TREATMENT = {
    108: "restart", 109: "spawn10", 110: "recs_cpu1000", 111: "control",
    112: "ck_rep2", 113: "ck_cpu1000", 114: "recs_users310", 115: "ck_rep2_pc120",
    117: "pc120", 118: "ck_rep2", 119: "recs_users310", 120: "spawn10",
    121: "control", 122: "ck_cpu1000", 123: "ck_rep2_pc120", 124: "restart",
    125: "pc120", 126: "recs_cpu1000",
    128: "ck_rep2_pc120", 129: "control", 130: "ck_rep2_pc120", 131: "control",
}
V1_SCORED = sorted(V1_TREATMENT)

# Earlier Paper-C1 same-mix holds (run 89 mix or close). No treatment label.
SAME_MIX = [89, 92] + list(range(94, 108))  # 94-107 inclusive


def ts(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc).timestamp()


def run_dir(n: int, root: str = NEW_VMS) -> str:
    return root % n


def read_inbound(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def service_rows(inbound: list[dict], service: str) -> list[dict]:
    rows = [r for r in inbound if r["service"] == service]
    rows.sort(key=lambda r: r["timestamp"])
    if len(rows) > TAIL_TRIM:
        rows = rows[:-TAIL_TRIM]
    return rows


def mesh_t0(inbound: list[dict]) -> Optional[float]:
    """First inbound poll timestamp. Locust CSVs have no clock; this is the
    hold clock used in prior latch write-ups."""
    if not inbound:
        return None
    return min(ts(r["timestamp"]) for r in inbound)


def parse_t0_txt(path: str) -> Optional[float]:
    """Parse '# captured <iso>' from state/t0.txt if present."""
    if not os.path.exists(path):
        return None
    line = open(path, encoding="utf-8-sig", errors="replace").readline().strip()
    if not line.startswith("# captured"):
        return None
    raw = line.split("captured", 1)[1].strip()
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).timestamp()


def rate_series(rows: list[dict], t0: float) -> list[dict]:
    """Per-tick arrival / sojourn / concurrency from consecutive inbound rows.

    Scrape holes (dt >= GAP_DT) are emitted with usable=False so callers can
    censor them instead of treating the gap as arrival 0.
    """
    out = []
    has_lat = rows and "rq_time_sum_ms" in rows[0]
    has_buckets = rows and "rq_time_buckets" in rows[0]
    for a, b in zip(rows, rows[1:]):
        dt = ts(b["timestamp"]) - ts(a["timestamp"])
        if dt <= 0:
            continue
        d_total = float(b["total"]) - float(a["total"])
        hole = dt >= GAP_DT
        arrival = (d_total / dt) if (not hole and d_total >= 0) else None
        sojourn_ms = None
        concurrency = None
        p50_ms = None
        d_count = 0
        d_sum = 0.0
        if has_lat and not hole:
            d_sum = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
            d_count = float(b["rq_time_count"]) - float(a["rq_time_count"])
            if d_count > 0 and d_sum >= 0:
                sojourn_ms = d_sum / d_count
                # Little's law: L = (sum of sojourn in the tick) / wall time.
                concurrency = (d_sum / 1000.0) / dt
            if has_buckets and d_count > 0:
                delta_b = mu._delta_buckets(
                    mu._parse_buckets(a.get("rq_time_buckets")),
                    mu._parse_buckets(b.get("rq_time_buckets")),
                )
                if delta_b:
                    p50_ms = mu.histogram_percentile(0.50, delta_b)
        out.append({
            "t": ts(b["timestamp"]) - t0,
            "timestamp": b["timestamp"],
            "dt": dt,
            "hole": hole,
            "usable": (not hole) and arrival is not None,
            "arrival": arrival,
            "sojourn_ms": sojourn_ms,
            "concurrency": concurrency,
            "p50_ms": p50_ms,
            "d_count": d_count,
        })
    return out


def first_sustained(
    series: list[dict],
    threshold: float,
    persist: int,
    value_key: str = "arrival",
) -> Optional[float]:
    """First offset where value_key stays > threshold for `persist` usable ticks.

    Holes reset the streak (censored, not zero). Returns the offset of the
    first tick of the successful streak, or None if never.
    """
    streak = 0
    streak_start: Optional[float] = None
    for tick in series:
        if tick["hole"] or not tick["usable"]:
            streak = 0
            streak_start = None
            continue
        val = tick.get(value_key)
        if val is None or val <= threshold:
            streak = 0
            streak_start = None
            continue
        if streak == 0:
            streak_start = tick["t"]
        streak += 1
        if streak >= persist:
            return streak_start
    return None


def latch_onset(checkout: list[dict]) -> Optional[float]:
    """First offset where the checkout latch signature appears.

    Envoy rq_time_* on checkout often updates only every ~5 s while total
    advances every 1 s, so a consecutive sojourn streak is usually length 1.
    Onset is therefore:
      1) the first usable tick with sojourn_ms >= LATCH_SOJOURN_MS and
         arrival > LATCH_ARRIVAL, or else
      2) the first sustained arrival > 120 for LATCH_PERSIST usable ticks.
    """
    for tick in checkout:
        if tick["hole"] or not tick["usable"]:
            continue
        soj = tick.get("sojourn_ms")
        arr = tick.get("arrival")
        if (soj is not None and arr is not None
                and soj >= LATCH_SOJOURN_MS and arr > LATCH_ARRIVAL):
            return tick["t"]
    return first_sustained(checkout, 120.0, LATCH_PERSIST, "arrival")


def gap2_pct(rows: list[dict]) -> Optional[float]:
    if len(rows) < 2:
        return None
    gaps = [ts(b["timestamp"]) - ts(a["timestamp"])
            for a, b in zip(rows, rows[1:])]
    if not gaps:
        return None
    return 100.0 * sum(g >= GAP_DT for g in gaps) / len(gaps)


def frontend_cpu_series(path: str, t0: float) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8"))
            if r["service"] == "frontend"]
    out = []
    for r in rows:
        out.append({
            "t": ts(r["timestamp"]) - t0,
            "cpu_m": float(r["cpu_millicores"]),
        })
    return out


def nearest_cpu(cpu_series: list[dict], t: float, tol: float = 3.0) -> Optional[float]:
    if not cpu_series:
        return None
    best = min(cpu_series, key=lambda r: abs(r["t"] - t))
    if abs(best["t"] - t) > tol:
        return None
    return best["cpu_m"]


def escape_from_series(
    recs: list[dict],
    checkout: list[dict],
    rate: float = DEFAULT_RATE,
    persist: int = DEFAULT_PERSIST,
) -> dict:
    """Escape / onset from already-built series (no disk I/O)."""
    escape_s = first_sustained(recs, rate, persist, "arrival")
    onset = latch_onset(checkout)
    duration = None
    if escape_s is not None and onset is not None:
        duration = escape_s - onset
    peaks = [t["arrival"] for t in recs if t["usable"] and t["arrival"] is not None]
    return {
        "escape_s": escape_s,
        "escaped": escape_s is not None,
        "latch_onset_s": onset,
        "latch_duration_s": duration,
        "recs_peak": max(peaks) if peaks else None,
        "recs_median": st.median(peaks) if peaks else None,
        "rate": rate,
        "persist": persist,
    }


def load_hold_series(n: int, root: str = NEW_VMS) -> dict:
    """Load inbound series once per hold for score + sensitivity + align."""
    d = run_dir(n, root)
    inbound = read_inbound(os.path.join(d, "service_inbound.csv"))
    out: dict = {"run": n, "exists": bool(inbound), "dir": d}
    if not inbound:
        out["error"] = "no service_inbound.csv"
        return out
    t0 = mesh_t0(inbound)
    out["t0_mesh"] = t0
    out["t0_txt"] = parse_t0_txt(os.path.join(d, "state", "t0.txt"))
    out["recs"] = rate_series(service_rows(inbound, "recommendationservice"), t0)
    out["checkout"] = rate_series(service_rows(inbound, "checkoutservice"), t0)
    out["frontend"] = rate_series(service_rows(inbound, "frontend"), t0)
    out["recs_gap2_pct"] = gap2_pct(service_rows(inbound, "recommendationservice"))
    out["fe_gap2_pct"] = gap2_pct(service_rows(inbound, "frontend"))
    frontend = out["frontend"]
    usable_fe = [t for t in frontend if t["usable"] and t["concurrency"] is not None]
    out["fe_usable_frac"] = (
        len(usable_fe) / max(1, len([t for t in frontend if not t["hole"]]))
        if frontend else 0.0)
    out["fe_concurrency_ok"] = (
        out["fe_gap2_pct"] is not None
        and out["fe_gap2_pct"] <= MAX_GAP2_PCT
        and out["fe_usable_frac"] >= 0.5)
    canon.ROOT = root
    try:
        o = canon.score(n)
        out["old_label"] = probe.classify(o)
        out["blend"] = probe.is_blend(o)
        out["ck_streak"] = o["svc"].get("checkoutservice", {}).get("streak")
        out["recs_streak"] = o["svc"].get("recommendationservice", {}).get("streak")
        out["ret_recs"] = o["edges"].get(("frontend", "recommendationservice"), 0)
    except Exception as exc:  # noqa: BLE001
        out["old_label"] = None
        out["score_error"] = str(exc)
    return out


def escape_score(
    n: int,
    root: str = NEW_VMS,
    rate: float = DEFAULT_RATE,
    persist: int = DEFAULT_PERSIST,
    hold: Optional[dict] = None,
) -> dict:
    hold = hold or load_hold_series(n, root=root)
    out = {
        "run": n, "exists": hold.get("exists"), "rate": rate, "persist": persist,
        "t0_mesh": hold.get("t0_mesh"), "t0_txt": hold.get("t0_txt"),
        "recs_gap2_pct": hold.get("recs_gap2_pct"),
        "fe_gap2_pct": hold.get("fe_gap2_pct"),
        "fe_usable_frac": hold.get("fe_usable_frac"),
        "fe_concurrency_ok": hold.get("fe_concurrency_ok"),
        "old_label": hold.get("old_label"),
        "blend": hold.get("blend"),
        "ck_streak": hold.get("ck_streak"),
        "recs_streak": hold.get("recs_streak"),
        "ret_recs": hold.get("ret_recs"),
    }
    if not hold.get("exists"):
        out["error"] = hold.get("error", "missing")
        return out
    out.update(escape_from_series(hold["recs"], hold["checkout"], rate, persist))
    return out


def sensitivity(n: int, root: str = NEW_VMS, hold: Optional[dict] = None) -> list[dict]:
    hold = hold or load_hold_series(n, root=root)
    rows = []
    for rate in SENSITIVITY_RATES:
        for persist in SENSITIVITY_PERSIST:
            s = escape_from_series(hold["recs"], hold["checkout"], rate, persist)
            rows.append({
                "run": n, "rate": rate, "persist": persist,
                "escape_s": s.get("escape_s"), "escaped": s.get("escaped"),
            })
    return rows


def window_stats(series: list[dict], key: str, lo: float, hi: float) -> dict:
    vals = [t[key] for t in series
            if t["usable"] and t.get(key) is not None and lo <= t["t"] <= hi]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "max": None}
    return {
        "n": len(vals),
        "mean": st.mean(vals),
        "median": st.median(vals),
        "max": max(vals),
    }


def align_escape(
    n: int,
    root: str = NEW_VMS,
    pre: float = 60.0,
    post: float = 30.0,
    rate: float = DEFAULT_RATE,
    persist: int = DEFAULT_PERSIST,
) -> Optional[dict]:
    """Event-aligned series around escape time. Returns None if no escape."""
    d = run_dir(n, root)
    inbound = read_inbound(os.path.join(d, "service_inbound.csv"))
    if not inbound:
        return None
    t0 = mesh_t0(inbound)
    recs = rate_series(service_rows(inbound, "recommendationservice"), t0)
    checkout = rate_series(service_rows(inbound, "checkoutservice"), t0)
    frontend = rate_series(service_rows(inbound, "frontend"), t0)
    escape = first_sustained(recs, rate, persist, "arrival")
    if escape is None:
        return None
    cpu = frontend_cpu_series(os.path.join(d, "resource_usage.csv"), t0)

    def slice_series(series, key):
        pts = []
        for tick in series:
            if not (escape - pre <= tick["t"] <= escape + post):
                continue
            if not tick["usable"] or tick.get(key) is None:
                continue
            pts.append({"rel": tick["t"] - escape, "t": tick["t"], "v": tick[key]})
        return pts

    # Lead time: when does frontend concurrency first exceed its pre-escape
    # median by 20%, looking back from escape.
    fe_pre = [t["concurrency"] for t in frontend
              if t["usable"] and t["concurrency"] is not None
              and escape - pre <= t["t"] < escape - 10]
    fe_at = [t for t in frontend
             if t["usable"] and t["concurrency"] is not None
             and escape - 30 <= t["t"] <= escape]
    lead = None
    if fe_pre and fe_at:
        basem = st.median(fe_pre)
        thresh = basem * 1.2 if basem > 0 else None
        if thresh is not None:
            for tick in fe_at:
                if tick["concurrency"] >= thresh:
                    lead = escape - tick["t"]
                    break
    return {
        "run": n,
        "escape_s": escape,
        "fe_concurrency": slice_series(frontend, "concurrency"),
        "fe_arrival": slice_series(frontend, "arrival"),
        "fe_p50": slice_series(frontend, "p50_ms"),
        "recs_arrival": slice_series(recs, "arrival"),
        "ck_arrival": slice_series(checkout, "arrival"),
        "fe_cpu_at_escape": nearest_cpu(cpu, escape),
        "fe_concurrency_pre": window_stats(frontend, "concurrency",
                                           escape - pre, escape - 5),
        "fe_concurrency_at": window_stats(frontend, "concurrency",
                                          escape - 5, escape + 5),
        "lead_s": lead,
    }


def matched_window_stats(
    n: int,
    lo: float,
    hi: float,
    root: str = NEW_VMS,
) -> dict:
    d = run_dir(n, root)
    inbound = read_inbound(os.path.join(d, "service_inbound.csv"))
    if not inbound:
        return {"run": n, "error": "missing"}
    t0 = mesh_t0(inbound)
    frontend = rate_series(service_rows(inbound, "frontend"), t0)
    recs = rate_series(service_rows(inbound, "recommendationservice"), t0)
    checkout = rate_series(service_rows(inbound, "checkoutservice"), t0)
    cpu = frontend_cpu_series(os.path.join(d, "resource_usage.csv"), t0)
    cpu_vals = [c["cpu_m"] for c in cpu if lo <= c["t"] <= hi]
    return {
        "run": n,
        "fe_concurrency": window_stats(frontend, "concurrency", lo, hi),
        "fe_arrival": window_stats(frontend, "arrival", lo, hi),
        "fe_p50": window_stats(frontend, "p50_ms", lo, hi),
        "recs_arrival": window_stats(recs, "arrival", lo, hi),
        "ck_arrival": window_stats(checkout, "arrival", lo, hi),
        "fe_cpu_mean": st.mean(cpu_vals) if cpu_vals else None,
        "fe_gap2_pct": gap2_pct(service_rows(inbound, "frontend")),
    }


def set_runs(name: str) -> list[int]:
    if name == "v2":
        return list(V2_SCORED)
    if name == "v1":
        return list(V1_SCORED)
    if name == "same_mix":
        return [n for n in SAME_MIX if os.path.isdir(run_dir(n))]
    if name == "all":
        seen = set()
        out = []
        for n in V2_SCORED + V1_SCORED + SAME_MIX:
            if n not in seen and os.path.isdir(run_dir(n)):
                seen.add(n)
                out.append(n)
        return out
    raise ValueError(name)


def treatment_for(n: int) -> Optional[str]:
    if n in V2_TREATMENT:
        return V2_TREATMENT[n]
    if n in V1_TREATMENT:
        return V1_TREATMENT[n]
    return None


def survival(scores: list[dict], horizons=(120, 300, 600)) -> dict:
    """Kaplan-Meier style: fraction not yet escaped by each horizon.
    Holds that never escape count as still latched at every horizon.
    Holds whose mesh span ends before the horizon are right-censored there
    only if they did not escape earlier (we treat end-of-hold as 600)."""
    n = len(scores)
    if n == 0:
        return {h: None for h in horizons}
    out = {}
    for h in horizons:
        still = sum(
            1 for s in scores
            if (not s.get("escaped")) or (s.get("escape_s") is not None and s["escape_s"] > h)
        )
        out[h] = still / n
    return out


def reconcile_label(score: dict) -> str:
    """Compare escape result with sticky/released/other. Return note."""
    old = score.get("old_label")
    escaped = score.get("escaped")
    if old == "released" and escaped:
        return "agree"
    if old == "sticky" and not escaped:
        return "agree"
    if old == "other" and not escaped:
        return "other_as_never"
    if old == "other" and escaped:
        return "other_escaped"
    if old == "released" and not escaped:
        return "disagree_released_no_escape"
    if old == "sticky" and escaped:
        return "disagree_sticky_escaped"
    return f"odd:{old}/{escaped}"


def fmt_escape(s: Optional[float]) -> str:
    if s is None:
        return "never"
    return f"{s:.0f}"


def print_score_table(scores: list[dict], title: str) -> None:
    print(f"\n## {title}\n")
    print("| run | treatment | old | escape_s | onset_s | duration_s | reconcile | peak_recs |")
    print("|---|---|---|---|---|---|---|---|")
    for s in scores:
        dur = (f"{s['latch_duration_s']:.0f}"
               if s.get("latch_duration_s") is not None else "-")
        peak = f"{s['recs_peak']:.0f}" if s.get("recs_peak") is not None else "-"
        print(
            f"| {s['run']} | {treatment_for(s['run']) or '-'} | {s.get('old_label')} | "
            f"{fmt_escape(s.get('escape_s'))} | {fmt_escape(s.get('latch_onset_s'))} | "
            f"{dur} | {reconcile_label(s)} | {peak} |"
        )
    surv = survival(scores)
    escaped = [s for s in scores if s.get("escaped")]
    print(f"\nEscaped {len(escaped)}/{len(scores)}. "
          f"Survival (not yet escaped) at 120/300/600 s: "
          f"{surv[120]:.2f} / {surv[300]:.2f} / {surv[600]:.2f}")
    if escaped:
        times = sorted(s["escape_s"] for s in escaped)
        print(f"Escape times (s): median {st.median(times):.0f}, "
              f"min {times[0]:.0f}, max {times[-1]:.0f}")


def cmd_score(args) -> int:
    runs = set_runs(args.set)
    holds = {n: load_hold_series(n) for n in runs}
    scores = [escape_score(n, hold=holds[n]) for n in runs]
    print_score_table(scores, f"Escape-time rescore ({args.set})")
    print("\n### Sensitivity (fraction escaped)\n")
    print("| rate | persist | escaped |")
    print("|---|---|---|")
    for rate in SENSITIVITY_RATES:
        for persist in SENSITIVITY_PERSIST:
            ss = [escape_score(n, rate=rate, persist=persist, hold=holds[n])
                  for n in runs]
            n_esc = sum(1 for s in ss if s.get("escaped"))
            frac = n_esc / max(1, len(ss))
            print(f"| {rate:.0f} | {persist} | {frac:.2f} ({n_esc}/{len(ss)}) |")
    if args.set == "v2":
        controls = [s for s in scores if treatment_for(s["run"]) == "control"]
        print_score_table(controls, "v2 controls")
    return 0


def cmd_align(args) -> int:
    runs = set_runs(args.set)
    holds = {n: load_hold_series(n) for n in runs}
    scores = [escape_score(n, hold=holds[n]) for n in runs]
    escaped = [s for s in scores if s.get("escaped")]
    never = [s for s in scores if not s.get("escaped")]
    print(f"\n## Align ({args.set}): {len(escaped)} escaped, {len(never)} never\n")
    leads = []
    for s in escaped:
        a = align_escape(s["run"])
        if not a:
            continue
        print(f"run{a['run']} escape={a['escape_s']:.0f}s "
              f"onset={scores and next((x.get('latch_onset_s') for x in scores if x['run']==a['run']), None)} "
              f"fe_conc_pre med={a['fe_concurrency_pre']['median']} "
              f"fe_conc_at med={a['fe_concurrency_at']['median']} "
              f"lead_s={a['lead_s']} fe_cpu={a['fe_cpu_at_escape']}")
        if a["lead_s"] is not None:
            leads.append(a["lead_s"])
    print("\n### Matched window 120-300 s (never escaped)\n")
    never_fe = []
    for s in never:
        w = matched_window_stats(s["run"], 120, 300)
        med = w["fe_concurrency"]["median"]
        print(f"run{s['run']} fe_conc_med={med} "
              f"recs_med={w['recs_arrival']['median']} "
              f"ck_med={w['ck_arrival']['median']} "
              f"fe_cpu={w['fe_cpu_mean']} gap2={w['fe_gap2_pct']}")
        if med is not None:
            never_fe.append(med)
    print("\n### Matched window 120-300 s (escaped, clipped before escape)\n")
    esc_fe = []
    for s in escaped:
        esc_t = s["escape_s"]
        hi = min(300.0, esc_t - 10) if esc_t is not None else 300.0
        if hi <= 120:
            print(f"run{s['run']} skip (escape {esc_t:.0f}s too early)")
            continue
        w = matched_window_stats(s["run"], 120, hi)
        med = w["fe_concurrency"]["median"]
        print(f"run{s['run']} window=120-{hi:.0f} fe_conc_med={med} "
              f"recs_med={w['recs_arrival']['median']}")
        if med is not None:
            esc_fe.append(med)
    print("\n### Separation summary\n")
    if leads:
        print(f"Lead times (s) where fe concurrency rose 20% before escape: "
              f"n={len(leads)} median={st.median(leads):.1f} "
              f"min={min(leads):.1f} max={max(leads):.1f}")
    else:
        print("No lead times detected under the 20% rule.")
    if esc_fe and never_fe:
        print(f"Pre-escape fe concurrency median: escaped n={len(esc_fe)} "
              f"med={st.median(esc_fe):.1f}; never n={len(never_fe)} "
              f"med={st.median(never_fe):.1f}")
        never_med = st.median(never_fe)
        above = sum(1 for x in esc_fe if x > never_med)
        print(f"Escaped pre-escape medians above never-median ({never_med:.1f}): "
              f"{above}/{len(esc_fe)}")
    # Proxy validation: correlation of concurrency vs CPU and P50 on one sticky
    # and one escaped hold.
    print("\n### Proxy validation (fe concurrency vs CPU / P50)\n")
    for n in ([escaped[0]["run"]] if escaped else []) + ([never[0]["run"]] if never else []):
        hold = holds[n]
        cpu = frontend_cpu_series(os.path.join(hold["dir"], "resource_usage.csv"),
                                  hold["t0_mesh"])
        pairs_cpu, pairs_p50 = [], []
        for t in hold["frontend"]:
            if not t["usable"] or t["concurrency"] is None:
                continue
            c = nearest_cpu(cpu, t["t"])
            if c is not None:
                pairs_cpu.append((t["concurrency"], c))
            if t["p50_ms"] is not None:
                pairs_p50.append((t["concurrency"], t["p50_ms"]))
        def pearson(pairs):
            if len(pairs) < 5:
                return None
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            mx, my = st.mean(xs), st.mean(ys)
            num = sum((x - mx) * (y - my) for x, y in pairs)
            denx = sum((x - mx) ** 2 for x in xs) ** 0.5
            deny = sum((y - my) ** 2 for y in ys) ** 0.5
            if denx == 0 or deny == 0:
                return None
            return num / (denx * deny)
        print(f"run{n} usable_frac={hold['fe_usable_frac']:.2f} "
              f"gap2={hold['fe_gap2_pct']} "
              f"r(conc,cpu)={pearson(pairs_cpu)} "
              f"r(conc,p50)={pearson(pairs_p50)} "
              f"n_cpu={len(pairs_cpu)} n_p50={len(pairs_p50)}")
    return 0


def cmd_json(args) -> int:
    runs = set_runs(args.set)
    payload = {
        "set": args.set,
        "scores": [escape_score(n) for n in runs],
        "sensitivity": {n: sensitivity(n) for n in runs},
    }
    json.dump(payload, sys.stdout, indent=2, default=str)
    print()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("score", cmd_score), ("align", cmd_align), ("json", cmd_json)):
        sp = sub.add_parser(name)
        sp.add_argument("--set", default="v2",
                        choices=["v2", "v1", "same_mix", "all"])
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
