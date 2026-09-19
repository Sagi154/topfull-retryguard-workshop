"""estimate_service_mu.py — offline per-service λ / μ̂ / ρ from mesh inbound
latency + throughput counters.

Corrected 2026-09-16 (see
docs/superpowers/specs/2026-09-16-rho-estimator-correction.md): the
original version of this script computed "mu_cpu = lambda / utilization"
using TopFull's `topfull_detect.csv` `utilization` field (cadvisor CPU busy
fraction relative to a hardcoded paper CPU-limit quota — TopFull's own
admission-control bookkeeping). That is **not** the RetryGuard paper's
rho = lambda/mu (Sec. 5). That CPU-linear estimator was removed entirely.

Corrected-again 2026-09-17 (see
docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md): the
2026-09-16 fix replaced it with `mu_hat_w = lambda + 1/W`, the M/M/1
steady-state sojourn-time relation solved for mu. That formula has been
**removed too** — not fixed, removed — because it is circular by
construction: `W = 1/(mu - lambda)` presupposes `mu > lambda` (stability),
so solving it for `mu` can only ever return a number just above the
observed `lambda`. Algebraically, `rho_w = lambda/mu_hat_w = L/(L+1)`
where `L = lambda * W` is the mean number of in-flight requests (Little's
Law) — a concurrency measure relabeled as a load ratio, capped below 1 by
construction, and unable to represent the `rho > 1` miscoordination regime
this whole exercise exists to detect. See the design doc above for the
derivation, the counter-examples (frontend `rho_w` ~0.99 under both light
and heavy load; productcatalogservice `rho_w` ~0.93 under healthy 6.9ms
latency; the one dataset cell with an independent capacity cross-check
disagreed with `mu_hat_w` there too), and the replacement approach (freeze
`mu_per_millicore` from a dedicated saturation/plateau run, rescale by
each evaluated run's `service_capacity.json` CPU limit, then compute
`rho_hat = lambda_offered / mu_this_run` — see
`experiments/capacity_frozen.py` / `experiments/rho_frozen_report.py`).

This script now reports only quantities that don't presuppose their own
conclusion:

- `lambda_s(t) = Δtotal / Δt` — this service's inbound *admitted* arrival
  rate, from `service_inbound.csv`. Admitted, not offered — see the design
  doc's discussion of why this alone is not a usable `rho` numerator when
  an upstream admission layer (TopFull) is active.
- `W` — this service's own mean inbound sojourn time, from Envoy's
  `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added
  2026-09-16 to `envoy_retry_collector.py`). Reported as a latency
  observation, never as a stand-in for capacity. `w_p50_ms` is the same via
  differenced histogram buckets, for robustness against long-tail outliers.
- `mu_sat = Δ2xx/Δt` on ticks with a high (5xx+resets) fraction — an
  M/M/1/m-adjacent argument (near/at saturation, admitted throughput
  directly approximates capacity) that does not depend on W at all. This is
  the **only** capacity signal this script can produce from an arbitrary
  run, and it is only available on ticks with real rejection — most runs
  will show `mu_sat = n/a`. Still an approximation, not validated ground
  truth.

Older `service_inbound.csv` files (pre-2026-09-16) lack `rq_time_sum_ms` /
`rq_time_count` — `w_mean_ms` / `w_p50_ms` come back as `n/a` with an
explicit "no latency data" note; this is a real, disclosed gap, not
silently papered over. `topfull_detect.csv` is no longer read by this
script at all.

Usage:
    python experiments/estimate_service_mu.py <run_dir>
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional, Tuple


SAT_5XX_FRACTION = 0.05
SAT_TAIL_TRIM_TICKS = 5
INBOUND_NAME = "service_inbound.csv"

# service_inbound.csv columns needed for the latency (W) observation. Older
# files (pre-2026-09-16) lack these two -- detected via NO_LATENCY_COLUMNS_NOTE.
LATENCY_SUM_COL = "rq_time_sum_ms"
LATENCY_COUNT_COL = "rq_time_count"
LATENCY_BUCKETS_COL = "rq_time_buckets"

NO_LATENCY_COLUMNS_NOTE = (
    "no rq_time_sum_ms/rq_time_count columns in service_inbound.csv -- this "
    "run predates the 2026-09-16 envoy_retry_collector.py latency extension "
    "(see docs/superpowers/specs/2026-09-16-rho-estimator-correction.md); "
    "w_mean_ms/w_p50_ms cannot be computed for this run"
)
NO_LATENCY_TICKS_NOTE = (
    "latency columns are present but every tick had "
    "rq_time_count delta == 0 (no completed requests counted in the "
    "histogram this tick) -- w_mean_ms/w_p50_ms unavailable"
)


class MissingInboundError(FileNotFoundError):
    pass


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _int(row: dict, key: str) -> int:
    try:
        return int(float(row[key]))
    except (KeyError, ValueError, TypeError):
        return 0


def _parse_buckets(raw: Optional[str]) -> Dict[str, int]:
    """Parse the JSON `rq_time_buckets` cell into {le_label: cumulative_count}."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, int] = {}
    for k, v in data.items():
        try:
            out[str(k)] = int(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _le_sort_key(le: str) -> float:
    if le == "+Inf":
        return float("inf")
    return float(le)


def histogram_percentile(
    q: float, buckets: Dict[str, int]
) -> Optional[float]:
    """Interpolate percentile q in [0, 1] from a cumulative histogram.

    `buckets` maps Envoy `le` labels (ms as strings, plus "+Inf") to
    cumulative counts. Returns the estimated percentile in milliseconds,
    or None if the histogram is empty / unusable. Standard Prometheus-
    style linear interpolation within the bucket that crosses q*total.
    """
    if not buckets or not (0.0 < q < 1.0):
        return None
    ordered: List[Tuple[float, int]] = sorted(
        ((_le_sort_key(le), count) for le, count in buckets.items()),
        key=lambda pair: pair[0],
    )
    total = ordered[-1][1]
    if total <= 0:
        return None
    rank = q * total
    prev_le = 0.0
    prev_count = 0
    for le, count in ordered:
        if count < prev_count:
            # Non-monotonic cumulative — bail rather than invent a number.
            return None
        if count >= rank:
            if count == prev_count:
                return prev_le if prev_le != float("inf") else None
            if le == float("inf"):
                # Rank falls in the +Inf overflow bucket — report the last
                # finite upper bound rather than inventing a value past it.
                return prev_le if prev_le > 0 else None
            frac = (rank - prev_count) / (count - prev_count)
            return prev_le + frac * (le - prev_le)
        prev_le, prev_count = le, count
    return None


def _delta_buckets(
    prev: Dict[str, int], cur: Dict[str, int]
) -> Dict[str, int]:
    """Per-tick cumulative histogram = cur - prev (same le keys)."""
    keys = set(prev) | set(cur)
    out: Dict[str, int] = {}
    for le in keys:
        delta = cur.get(le, 0) - prev.get(le, 0)
        if delta < 0:
            # Counter reset (pod restart) — treat this tick as unusable.
            return {}
        out[le] = delta
    return out


def difference_inbound(rows: List[dict]) -> List[dict]:
    """Diff consecutive same-service rows into per-tick deltas.

    Skips ticks with non-positive dt or delta_total <= 0 (no new arrivals --
    no information about lambda or W for that tick). Latency columns are
    read defensively: absent/unparsable -> 0, so a tick with no latency data
    yields w_seconds=None (see below), not a crash.
    """
    ordered = sorted(rows, key=lambda r: parse_timestamp(r["timestamp"]))
    out: List[dict] = []
    for prev, cur in zip(ordered, ordered[1:]):
        dt = (
            parse_timestamp(cur["timestamp"]) - parse_timestamp(prev["timestamp"])
        ).total_seconds()
        if dt <= 0:
            continue
        delta_total = _int(cur, "total") - _int(prev, "total")
        if delta_total <= 0:
            continue
        delta_2xx = _int(cur, "2xx") - _int(prev, "2xx")
        delta_5xx = _int(cur, "5xx") - _int(prev, "5xx")
        delta_resets = _int(cur, "resets") - _int(prev, "resets")

        has_latency_cols = LATENCY_SUM_COL in cur and LATENCY_COUNT_COL in cur
        delta_rq_time_sum_ms = _int(cur, LATENCY_SUM_COL) - _int(prev, LATENCY_SUM_COL)
        delta_rq_time_count = _int(cur, LATENCY_COUNT_COL) - _int(prev, LATENCY_COUNT_COL)
        w_seconds: Optional[float] = None
        if has_latency_cols and delta_rq_time_count > 0 and delta_rq_time_sum_ms >= 0:
            w_seconds = (delta_rq_time_sum_ms / delta_rq_time_count) / 1000.0

        w_p50_ms: Optional[float] = None
        if LATENCY_BUCKETS_COL in cur:
            delta_buckets = _delta_buckets(
                _parse_buckets(prev.get(LATENCY_BUCKETS_COL)),
                _parse_buckets(cur.get(LATENCY_BUCKETS_COL)),
            )
            if delta_buckets:
                w_p50_ms = histogram_percentile(0.50, delta_buckets)

        out.append(
            {
                "timestamp": cur["timestamp"],
                "dt_seconds": dt,
                "delta_total": delta_total,
                "delta_2xx": delta_2xx,
                "delta_5xx": delta_5xx,
                "delta_resets": delta_resets,
                "lambda_s": delta_total / dt,
                "has_latency_cols": has_latency_cols,
                "w_seconds": w_seconds,
                "w_p50_ms": w_p50_ms,
            }
        )
    return out


@dataclass(frozen=True)
class Tick:
    timestamp: str
    dt_seconds: float
    lambda_s: float
    delta_total: int
    delta_2xx: int
    delta_5xx: int
    has_latency_cols: bool
    w_seconds: Optional[float]
    w_p50_ms: Optional[float] = None
    delta_resets: int = 0

    @property
    def five_xx_fraction(self) -> float:
        if self.delta_total <= 0:
            return 0.0
        return self.delta_5xx / self.delta_total

    @property
    def failure_fraction(self) -> float:
        if self.delta_total <= 0:
            return 0.0
        return (self.delta_5xx + self.delta_resets) / self.delta_total


@dataclass(frozen=True)
class ServiceEstimate:
    service: str
    lambda_mean: Optional[float]
    mu_sat: Optional[float]
    w_mean_ms: Optional[float]
    n_ticks_with_latency: int
    inbound_5xx_fraction: float
    inbound_failure_fraction: float = 0.0
    note: Optional[str] = None
    w_p50_ms: Optional[float] = None


def ticks_from_rows(rows: List[dict]) -> List[Tick]:
    return [
        Tick(
            timestamp=d["timestamp"],
            dt_seconds=d["dt_seconds"],
            lambda_s=d["lambda_s"],
            delta_total=d["delta_total"],
            delta_2xx=d["delta_2xx"],
            delta_5xx=d["delta_5xx"],
            has_latency_cols=d["has_latency_cols"],
            w_seconds=d["w_seconds"],
            w_p50_ms=d.get("w_p50_ms"),
            delta_resets=d.get("delta_resets", 0),
        )
        for d in difference_inbound(rows)
    ]


def saturating_ticks(ticks: List[Tick]) -> List[Tick]:
    """Ticks eligible for mu_sat: failure_fraction gate, last SAT_TAIL_TRIM_TICKS excluded.

    Run teardown produces a reset burst on the last few inbound rows. Those
    are not saturation. If the series is shorter than the trim, nothing is
    eligible.
    """
    if len(ticks) <= SAT_TAIL_TRIM_TICKS:
        return []
    eligible = ticks[:-SAT_TAIL_TRIM_TICKS]
    return [
        t for t in eligible
        if t.delta_total > 0 and t.failure_fraction >= SAT_5XX_FRACTION
    ]


def summarize_service(service: str, ticks: List[Tick]) -> ServiceEstimate:
    if not ticks:
        return ServiceEstimate(
            service, None, None, None, 0, 0.0, note="no ticks with traffic"
        )

    lambdas = [t.lambda_s for t in ticks]
    lambda_mean = sum(lambdas) / len(lambdas)

    d5 = sum(t.delta_5xx for t in ticks)
    dreset = sum(t.delta_resets for t in ticks)
    dtot = sum(t.delta_total for t in ticks)
    inbound_5xx_fraction = (d5 / dtot) if dtot else 0.0
    inbound_failure_fraction = ((d5 + dreset) / dtot) if dtot else 0.0

    # Only capacity signal this script produces: near-saturation admitted
    # throughput. Requires real rejection; most runs will have no samples.
    sat = saturating_ticks(ticks)
    sat_samples = [t.delta_2xx / t.dt_seconds for t in sat]
    mu_sat = median(sat_samples) if sat_samples else None

    if not any(t.has_latency_cols for t in ticks):
        return ServiceEstimate(
            service=service,
            lambda_mean=lambda_mean,
            mu_sat=mu_sat,
            w_mean_ms=None,
            n_ticks_with_latency=0,
            inbound_5xx_fraction=inbound_5xx_fraction,
            inbound_failure_fraction=inbound_failure_fraction,
            note=NO_LATENCY_COLUMNS_NOTE,
        )

    w_samples_ms = [t.w_seconds * 1000.0 for t in ticks if t.w_seconds is not None]
    p50_samples = [t.w_p50_ms for t in ticks if t.w_p50_ms is not None]
    w_p50_ms = median(p50_samples) if p50_samples else None

    if not w_samples_ms:
        return ServiceEstimate(
            service=service,
            lambda_mean=lambda_mean,
            mu_sat=mu_sat,
            w_mean_ms=None,
            n_ticks_with_latency=0,
            inbound_5xx_fraction=inbound_5xx_fraction,
            inbound_failure_fraction=inbound_failure_fraction,
            note=NO_LATENCY_TICKS_NOTE,
            w_p50_ms=w_p50_ms,
        )

    w_mean_ms = sum(w_samples_ms) / len(w_samples_ms)

    return ServiceEstimate(
        service=service,
        lambda_mean=lambda_mean,
        mu_sat=mu_sat,
        w_mean_ms=w_mean_ms,
        n_ticks_with_latency=len(w_samples_ms),
        inbound_5xx_fraction=inbound_5xx_fraction,
        inbound_failure_fraction=inbound_failure_fraction,
        note=None,
        w_p50_ms=w_p50_ms,
    )


def _read_csv(path: Path) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def estimate_run(run_dir: Path) -> List[ServiceEstimate]:
    """Read `service_inbound.csv` from run_dir and return per-service estimates.

    Only `service_inbound.csv` is required. `topfull_detect.csv` is no
    longer read (the corrected estimator does not use TopFull's CPU-quota
    utilization signal at all).
    """
    run_dir = Path(run_dir)
    inbound_path = run_dir / INBOUND_NAME
    if not inbound_path.is_file():
        raise MissingInboundError(str(inbound_path))
    inbound_by: dict = defaultdict(list)
    for row in _read_csv(inbound_path):
        inbound_by[row["service"]].append(row)
    services = sorted(inbound_by)
    return [
        summarize_service(name, ticks_from_rows(inbound_by[name]))
        for name in services
    ]


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_table(estimates: List[ServiceEstimate]) -> str:
    headers = (
        "service",
        "lambda_mean",
        "mu_sat",
        "w_mean_ms",
        "w_p50_ms",
        "n_ticks",
        "inbound_5xx_fraction",
        "inbound_failure_fraction",
    )
    rows: List[tuple] = [headers]
    for e in estimates:
        rows.append(
            (
                e.service,
                _fmt(e.lambda_mean),
                _fmt(e.mu_sat),
                _fmt(e.w_mean_ms),
                _fmt(e.w_p50_ms),
                str(e.n_ticks_with_latency),
                _fmt(e.inbound_5xx_fraction),
                _fmt(e.inbound_failure_fraction),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    lines = [
        "  ".join(c.ljust(widths[i]) for i, c in enumerate(r)) for r in rows
    ]
    notes = [f"{e.service}: {e.note}" for e in estimates if e.note]
    text = "\n".join(lines) + "\n"
    if notes:
        text += "\nNotes:\n" + "\n".join(f"  - {n}" for n in notes) + "\n"
    return text


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        args = sys.argv[1:]
    else:
        args = list(argv)
        if args and (
            args[0].endswith("estimate_service_mu.py")
            or args[0].endswith("estimate_service_mu")
        ):
            args = args[1:]
    if len(args) != 1:
        sys.stderr.write(
            "usage: python experiments/estimate_service_mu.py <run_dir>\n"
        )
        return 2
    try:
        estimates = estimate_run(Path(args[0]))
    except MissingInboundError as exc:
        sys.stderr.write(f"missing {INBOUND_NAME}: {exc}\n")
        return 1
    sys.stdout.write(format_table(estimates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
