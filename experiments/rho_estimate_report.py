"""rho_estimate_report.py — combine estimate_service_mu.py's offline rho/mu
estimates with a run folder's RetryGuard toggle log into one report.

Writes `rho_estimate_report.md` (+ `rho_estimate_report.json`) into the run
folder itself, so the numbers live alongside the run's other result files.

This is a read-only, local-only tool: it never touches topfull-master, never
modifies existing run CSVs, and degrades gracefully (never raises) when a
run folder is missing service_inbound.csv / topfull_detect.csv (pre-2026-09-09
folders) or retryguard.log (baseline runs, or RetryGuard not enabled).

Usage:
    python experiments/rho_estimate_report.py <run_dir>

Design notes (Part A context — why this exists as a *supplementary*
diagnostic, not ground truth):

- `experiments/retryguard.py`'s live controller does NOT use rho = lambda/mu.
  It acts on a mesh rejection-rate surrogate (Delta(5xx+resets)/Delta total
  from service_inbound.csv), matching the RetryGuard paper's own live Istio
  deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window).
- Corrected 2026-09-16 (see
  docs/superpowers/specs/2026-09-16-rho-estimator-correction.md):
  `estimate_service_mu.py` used to compute `mu_cpu = lambda / utilization`
  from `topfull_detect.csv`'s `utilization` (TopFull's own CPU-quota
  admission-control bookkeeping) and called that "rho". That is a
  different system's internal signal, not the RetryGuard paper's
  queueing-theoretic rho = lambda/mu (Sec 5, M/M/1(/m) load ratio). It has
  been removed entirely. The estimator now computes `mu_hat_w = lambda +
  1/W` (the standard M/M/1 steady-state relation, rearranged), where W is
  this service's own mean inbound sojourn time from Envoy's
  `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count` in
  `service_inbound.csv`, added to `envoy_retry_collector.py` on
  2026-09-16). `rho_w = lambda / mu_hat_w`. Runs from before 2026-09-16
  lack those two columns and report `mu_hat_w`/`rho_w` as `n/a` with an
  explicit note, not a silent wrong number.
- The saturated-goodput cross-check (`mu_sat = Delta2xx/Delta t` on ticks
  with a high 5xx fraction) is unchanged and kept as an independent sanity
  check — it does not depend on the CPU-quota signal and did not need
  correcting.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import estimate_service_mu as mu  # noqa: E402

RETRYGUARD_LOG_NAME = "retryguard.log"
REPORT_MD_NAME = "rho_estimate_report.md"
REPORT_JSON_NAME = "rho_estimate_report.json"

# Matches lines like:
#   2026-09-15T20:16:57Z  checkoutservice  ON\u2192OFF   rejection=0.48  consecutive_high=30  attempts=0
TOGGLE_LINE_RE = re.compile(
    r"^(?P<timestamp>\S+)\s+"
    r"(?P<service>\S+)\s+"
    r"(?P<old>ON|OFF)\u2192(?P<new>ON|OFF)\s+"
    r"rejection=(?P<rejection>[\d.]+)\s+"
    r"(?P<counter>\S+)\s+"
    r"attempts=(?P<attempts>\d+)"
)

CONTEXT_NOTE = (
    "`experiments/retryguard.py`'s live controller does not use this rho estimate — "
    "it acts on a mesh rejection-rate surrogate (`\u0394(5xx+resets)/\u0394total` from "
    "`service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment "
    "(Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat "
    "estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary "
    "diagnostic, not the controller's decision input and not a validated ground-truth rho.\n\n"
    "**Methodology (corrected 2026-09-16 — see "
    "`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** "
    "`mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is "
    "this service's inbound arrival rate (`\u0394total/\u0394t` from `service_inbound.csv`) "
    "and `W` is this service's own mean inbound sojourn time, from Envoy's "
    "`downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to "
    "`envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced "
    "an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from "
    "`topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control "
    "bookkeeping with the RetryGuard paper's queueing-theoretic rho \u2014 a different "
    "system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the "
    "`rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that "
    "case, not a silently wrong number. The M/M/1 `W` formula assumes steady state "
    "(`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the "
    "report flags that the assumption is likely violated (finite buffer, admission control "
    "upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number "
    "at face value. The saturated-goodput cross-check (`mu_sat = \u0394 2xx/\u0394t` on ticks "
    "with a high 5xx fraction) is unchanged and independent of the above."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_retryguard_log(log_path: Path) -> list[dict]:
    """Extract ON<->OFF toggle events from a retryguard.log file.

    Returns [] if the file does not exist or has no toggle lines. Never
    raises — a malformed/partial log just yields fewer/no events.
    """
    if not log_path.is_file():
        return []
    events: list[dict] = []
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        m = TOGGLE_LINE_RE.match(line.strip())
        if not m:
            continue
        events.append(
            {
                "timestamp": m.group("timestamp"),
                "service": m.group("service"),
                "direction": f"{m.group('old')}\u2192{m.group('new')}",
                "rejection": float(m.group("rejection")),
                "counter": m.group("counter"),
                "attempts": int(m.group("attempts")),
            }
        )
    return events


def compute_rho_estimates(
    run_dir: Path,
) -> tuple[Optional[list["mu.ServiceEstimate"]], Optional[str]]:
    """Run estimate_service_mu on run_dir. Returns (estimates, error_message).

    Exactly one of the two return values is not None (unless there is no
    per-service data at all, in which case estimates is an empty list).

    Only `service_inbound.csv` is required (since the 2026-09-16 correction,
    `topfull_detect.csv` is no longer read by `estimate_service_mu.py` at
    all). A folder that has `service_inbound.csv` but predates the
    2026-09-16 `rq_time_sum_ms`/`rq_time_count` columns still returns
    estimates — just with `mu_hat_w`/`rho_w` as `n/a` and a note on each
    ServiceEstimate (see NO_LATENCY_COLUMNS_NOTE), not an error here.
    """
    try:
        estimates = mu.estimate_run(run_dir)
    except mu.MissingInboundError:
        return None, (
            f"missing {mu.INBOUND_NAME} — pre-2026-09-09 folder "
            "(no per-service mesh collector) or a run with mesh collector disabled."
        )
    return estimates, None


def build_markdown_report(
    run_dir: Path,
    estimates: Optional[list["mu.ServiceEstimate"]],
    estimate_error: Optional[str],
    toggles: list[dict],
    retryguard_log_present: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"# rho / mu.hat estimate report — `{run_dir.name}`")
    lines.append("")
    lines.append(f"Generated: {utc_now()}")
    lines.append(f"Run folder: `{run_dir}`")
    lines.append("")
    lines.append("## Context")
    lines.append("")
    lines.append(CONTEXT_NOTE)
    lines.append("")
    lines.append("## Per-service rho / lambda / mu.hat estimates")
    lines.append("")
    if estimate_error is not None:
        lines.append(f"**Not computed:** {estimate_error}")
    elif not estimates:
        lines.append("No per-service rows found in `service_inbound.csv` / `topfull_detect.csv`.")
    else:
        lines.append("```")
        lines.append(mu.format_table(estimates).rstrip("\n"))
        lines.append("```")
    lines.append("")
    lines.append("## RetryGuard toggle events")
    lines.append("")
    if not retryguard_log_present:
        lines.append(
            "No `retryguard.log` in this run folder — likely a baseline run "
            "(RetryGuard not enabled) or a run predating the toggle log. "
            "Skipping toggle-vs-rho comparison."
        )
    elif not toggles:
        lines.append(
            "`retryguard.log` is present but no `ON\u2192OFF` / `OFF\u2192ON` toggle events "
            "were found (RetryGuard ran but never crossed its threshold for the required "
            "`interval_samples` — this is expected on many flat baseline/RG-inert runs)."
        )
    else:
        lines.append("| timestamp | service | direction | rejection | counter | attempts |")
        lines.append("|---|---|---|---|---|---|")
        for ev in toggles:
            lines.append(
                f"| {ev['timestamp']} | {ev['service']} | {ev['direction']} | "
                f"{ev['rejection']:.4f} | {ev['counter']} | {ev['attempts']} |"
            )
        lines.append("")
        if estimates:
            by_service = {e.service: e for e in estimates}
            lines.append("**rho_w at the services that toggled** (for cross-reference only "
                          "— see the caveat above; RetryGuard did not use this number):")
            lines.append("")
            seen = set()
            for ev in toggles:
                svc = ev["service"]
                if svc in seen:
                    continue
                seen.add(svc)
                est = by_service.get(svc)
                if est is None:
                    continue
                lines.append(
                    f"- `{svc}`: rho_w_median={mu._fmt(est.rho_w_median)}  "
                    f"mu_hat_w={mu._fmt(est.mu_hat_w_median)}  "
                    f"mu_sat={mu._fmt(est.mu_sat)}  "
                    f"w_mean_ms={mu._fmt(est.w_mean_ms)}  "
                    f"inbound_5xx_fraction={mu._fmt(est.inbound_5xx_fraction)}"
                    + (f"  note: {est.note}" if est.note else "")
                )
            lines.append("")
    lines.append("")
    return "\n".join(lines)


def build_json_report(
    run_dir: Path,
    estimates: Optional[list["mu.ServiceEstimate"]],
    estimate_error: Optional[str],
    toggles: list[dict],
    retryguard_log_present: bool,
) -> dict:
    return {
        "generated_at": utc_now(),
        "run_dir": str(run_dir),
        "estimates": [asdict(e) for e in estimates] if estimates else [],
        "estimate_error": estimate_error,
        "retryguard_log_present": retryguard_log_present,
        "toggle_events": toggles,
    }


def generate_report(run_dir: Path, write_json: bool = True) -> Path:
    """Build and write rho_estimate_report.md (+ .json) into run_dir.

    Never raises: missing inputs are reported inside the markdown/json, not
    surfaced as exceptions, so this is safe to call unconditionally after a
    results pull.
    """
    run_dir = Path(run_dir)
    estimates, estimate_error = compute_rho_estimates(run_dir)
    log_path = run_dir / RETRYGUARD_LOG_NAME
    retryguard_log_present = log_path.is_file()
    toggles = parse_retryguard_log(log_path)

    md = build_markdown_report(run_dir, estimates, estimate_error, toggles, retryguard_log_present)
    md_path = run_dir / REPORT_MD_NAME
    md_path.write_text(md, encoding="utf-8")

    if write_json:
        payload = build_json_report(run_dir, estimates, estimate_error, toggles, retryguard_log_present)
        json_path = run_dir / REPORT_JSON_NAME
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return md_path


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        sys.stderr.write("usage: python experiments/rho_estimate_report.py <run_dir>\n")
        return 2
    run_dir = Path(args[0])
    if not run_dir.is_dir():
        sys.stderr.write(f"not a directory: {run_dir}\n")
        return 1
    md_path = generate_report(run_dir)
    sys.stdout.write(f"Wrote {md_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
