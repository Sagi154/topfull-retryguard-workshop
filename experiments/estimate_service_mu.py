"""estimate_service_mu.py — offline per-service λ / μ̂ / ρ from mesh inbound + detect.

Usage:
    python experiments/estimate_service_mu.py <run_dir>
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median


SAT_5XX_FRACTION = 0.05
INBOUND_NAME = "service_inbound.csv"
DETECT_NAME = "topfull_detect.csv"


class MissingDetectError(FileNotFoundError):
    pass


class MissingInboundError(FileNotFoundError):
    pass


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def difference_inbound(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda r: parse_timestamp(r["timestamp"]))
    out: list[dict] = []
    for prev, cur in zip(ordered, ordered[1:]):
        dt = (
            parse_timestamp(cur["timestamp"]) - parse_timestamp(prev["timestamp"])
        ).total_seconds()
        if dt <= 0:
            continue
        delta_total = int(cur["total"]) - int(prev["total"])
        if delta_total == 0:
            continue
        if delta_total < 0:
            continue
        delta_2xx = int(cur["2xx"]) - int(prev["2xx"])
        delta_5xx = int(cur["5xx"]) - int(prev["5xx"])
        out.append(
            {
                "timestamp": cur["timestamp"],
                "dt_seconds": dt,
                "delta_total": delta_total,
                "delta_2xx": delta_2xx,
                "delta_5xx": delta_5xx,
                "lambda_s": delta_total / dt,
            }
        )
    return out


@dataclass(frozen=True)
class Tick:
    timestamp: str
    dt_seconds: float
    lambda_s: float
    utilization: float
    alpha: float
    delta_total: int
    delta_2xx: int
    delta_5xx: int

    @property
    def five_xx_fraction(self) -> float:
        if self.delta_total <= 0:
            return 0.0
        return self.delta_5xx / self.delta_total


@dataclass(frozen=True)
class ServiceEstimate:
    service: str
    lambda_mean: float | None
    util_peak: float | None
    mu_cpu: float | None
    mu_sat: float | None
    rho_cpu_median: float | None
    inbound_5xx_fraction: float


def join_ticks(inbound_rows: list[dict], detect_rows: list[dict]) -> list[Tick]:
    detect_by_ts = {row["timestamp"]: row for row in detect_rows}
    ticks: list[Tick] = []
    for diff in difference_inbound(inbound_rows):
        det = detect_by_ts.get(diff["timestamp"])
        if det is None:
            continue
        ticks.append(
            Tick(
                timestamp=diff["timestamp"],
                dt_seconds=diff["dt_seconds"],
                lambda_s=diff["lambda_s"],
                utilization=float(det["utilization"]),
                alpha=float(det["alpha"]),
                delta_total=diff["delta_total"],
                delta_2xx=diff["delta_2xx"],
                delta_5xx=diff["delta_5xx"],
            )
        )
    return ticks


def summarize_service(service: str, ticks: list[Tick]) -> ServiceEstimate:
    if not ticks:
        return ServiceEstimate(service, None, None, None, None, None, 0.0)
    cpu_samples = [
        t.lambda_s / t.utilization
        for t in ticks
        if t.lambda_s > 0 and 0 < t.utilization < t.alpha
    ]
    sat_samples = [
        t.delta_2xx / t.dt_seconds
        for t in ticks
        if t.delta_total > 0 and t.five_xx_fraction >= SAT_5XX_FRACTION
    ]
    mu_cpu = median(cpu_samples) if cpu_samples else None
    mu_sat = median(sat_samples) if sat_samples else None
    rho_samples = [t.lambda_s / mu_cpu for t in ticks] if mu_cpu else []
    d5 = sum(t.delta_5xx for t in ticks)
    dtot = sum(t.delta_total for t in ticks)
    lambdas = [t.lambda_s for t in ticks]
    lambda_mean = (sum(lambdas) / len(lambdas)) if lambdas else None
    return ServiceEstimate(
        service=service,
        lambda_mean=lambda_mean,
        util_peak=max(t.utilization for t in ticks),
        mu_cpu=mu_cpu,
        mu_sat=mu_sat,
        rho_cpu_median=median(rho_samples) if rho_samples else None,
        inbound_5xx_fraction=(d5 / dtot) if dtot else 0.0,
    )


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def estimate_run(run_dir: Path) -> list[ServiceEstimate]:
    run_dir = Path(run_dir)
    inbound_path = run_dir / INBOUND_NAME
    detect_path = run_dir / DETECT_NAME
    if not inbound_path.is_file():
        raise MissingInboundError(str(inbound_path))
    if not detect_path.is_file():
        raise MissingDetectError(str(detect_path))
    inbound_by: dict[str, list[dict]] = defaultdict(list)
    for row in _read_csv(inbound_path):
        inbound_by[row["service"]].append(row)
    detect_by: dict[str, list[dict]] = defaultdict(list)
    for row in _read_csv(detect_path):
        detect_by[row["service"]].append(row)
    services = sorted(set(inbound_by) | set(detect_by))
    return [
        summarize_service(name, join_ticks(inbound_by[name], detect_by[name]))
        for name in services
    ]


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_table(estimates: list[ServiceEstimate]) -> str:
    headers = (
        "service",
        "lambda_mean",
        "util_peak",
        "mu_cpu",
        "mu_sat",
        "rho_cpu_median",
        "inbound_5xx_fraction",
    )
    rows: list[tuple[str, ...]] = [headers]
    for e in estimates:
        rows.append(
            (
                e.service,
                _fmt(e.lambda_mean),
                _fmt(e.util_peak),
                _fmt(e.mu_cpu),
                _fmt(e.mu_sat),
                _fmt(e.rho_cpu_median),
                _fmt(e.inbound_5xx_fraction),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    lines = [
        "  ".join(c.ljust(widths[i]) for i, c in enumerate(r)) for r in rows
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
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
    except MissingDetectError as exc:
        sys.stderr.write(f"missing {DETECT_NAME}: {exc}\n")
        return 1
    except MissingInboundError as exc:
        sys.stderr.write(f"missing {INBOUND_NAME}: {exc}\n")
        return 1
    sys.stdout.write(format_table(estimates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
