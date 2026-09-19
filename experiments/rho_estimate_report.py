"""rho_estimate_report.py — combine estimate_service_mu.py's offline
lambda/W/mu_sat observations with a run folder's RetryGuard toggle log into
one report.

Writes `rho_estimate_report.md` (+ `rho_estimate_report.json`) into the run
folder itself, so the numbers live alongside the run's other result files.

This is a read-only, local-only tool: it never touches topfull-master, never
modifies existing run CSVs, and degrades gracefully (never raises) when a
run folder is missing service_inbound.csv (pre-2026-09-09 folders) or
retryguard.log (baseline runs, or RetryGuard not enabled).

Usage:
    python experiments/rho_estimate_report.py <run_dir>

Design notes (why this report does NOT compute a `rho` today):

- `experiments/retryguard.py`'s live controller does NOT use rho = lambda/mu.
  It acts on a mesh rejection-rate surrogate (Delta(5xx+resets)/Delta total
  from service_inbound.csv), matching the RetryGuard paper's own live Istio
  deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). That
  is unaffected by anything below.
- Corrected 2026-09-16 (see
  docs/superpowers/specs/2026-09-16-rho-estimator-correction.md):
  `estimate_service_mu.py` used to compute `mu_cpu = lambda / utilization`
  from `topfull_detect.csv`'s `utilization` (TopFull's own CPU-quota
  admission-control bookkeeping) and called that "rho". That was a
  different system's internal signal, not the RetryGuard paper's
  queueing-theoretic rho = lambda/mu (Sec 5, M/M/1(/m) load ratio). Removed.
- Corrected-again 2026-09-17 (see
  docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md): the
  2026-09-16 replacement, `mu_hat_w = lambda + 1/W` (M/M/1 steady-state
  relation, rearranged), was itself removed. It is circular by
  construction — solving `W = 1/(mu - lambda)` for `mu` can only return a
  value just above the observed `lambda`, so the resulting
  `rho_w = lambda/mu_hat_w` reduces algebraically to `L/(L+1)` (Little's
  Law concurrency, `L = lambda*W`), a quantity that is always below 1 and
  therefore cannot represent the `rho > 1` miscoordination regime the paper
  (and this project) cares about. It also reported ~0.93 for a healthy,
  6.9ms-latency service under normal load, purely from having many
  requests in flight — see the design doc for the full derivation and
  worked counter-examples.
- This report now shows only what `estimate_service_mu.py` can honestly
  compute from a single run: `lambda_mean` (admitted arrival rate),
  `w_mean_ms`/`w_p50_ms` (this service's own inbound sojourn time — a
  latency observation, not a capacity stand-in), and `mu_sat`
  (Δ2xx/Δt on ticks with real 5xx — an independent, though sparse,
  saturation-based capacity signal). No `rho` is reported here.
- A `rho_hat = lambda_offered / mu_this_run` diagnostic, freezing
  `mu_per_millicore` from a dedicated saturation run and rescaling by
  each run's Kubernetes CPU limit (`service_capacity.json`), is designed
  in docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md
  (`experiments/capacity_frozen.py` / `experiments/rho_frozen_report.py`)
  but is a separate tool from this one — not yet wired in here.
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
    "`experiments/retryguard.py`'s live controller does not use anything in this report — "
    "it acts on a mesh rejection-rate surrogate (`\u0394(5xx+resets)/\u0394total` from "
    "`service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment "
    "(Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an "
    "offline, supplementary diagnostic, not the controller's decision input.\n\n"
    "**No `rho` is computed by this report.** An earlier version reported "
    "`rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state "
    "relation, rearranged) \u2014 removed 2026-09-17 "
    "(`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is "
    "circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving "
    "for `mu` can only ever return a value just above the observed `lambda`. Algebraically "
    "`rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's "
    "Law) \u2014 always below 1 by construction, unable to represent the `rho > 1` "
    "miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for "
    "a healthy 6.9ms-latency service under normal load purely from having many requests in "
    "flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from "
    "`topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping "
    "with the RetryGuard paper's queueing-theoretic rho \u2014 also removed "
    "(`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).\n\n"
    "**What this report shows instead:** `lambda_mean` (this service's admitted inbound "
    "arrival rate, `\u0394total/\u0394t` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` "
    "(this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` "
    "histogram \u2014 reported as a latency observation, never as a stand-in for capacity); "
    "and `mu_sat` (`\u0394 2xx/\u0394t` on ticks with a high (5xx+resets) fraction \u2014 the one "
    "capacity signal this report can produce from a single run, but only available on ticks "
    "with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / "
    "mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation "
    "run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is "
    "designed but not yet wired into this report \u2014 see "
    "`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`."
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

    Only `service_inbound.csv` is required (`topfull_detect.csv` is not
    read by `estimate_service_mu.py` at all). A folder that has
    `service_inbound.csv` but predates the 2026-09-16 `rq_time_sum_ms`/
    `rq_time_count` columns still returns estimates — just with
    `w_mean_ms`/`w_p50_ms` as `n/a` and a note on each ServiceEstimate (see
    NO_LATENCY_COLUMNS_NOTE), not an error here.
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
        lines.append("No per-service rows found in `service_inbound.csv`.")
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
            "(RetryGuard not enabled) or a run predating the toggle log."
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
            lines.append("**lambda/W/mu_sat at the services that toggled** (for "
                          "cross-reference only; RetryGuard did not use these numbers — "
                          "no `rho` is reported, see the caveat above):")
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
                    f"- `{svc}`: lambda_mean={mu._fmt(est.lambda_mean)}  "
                    f"mu_sat={mu._fmt(est.mu_sat)}  "
                    f"w_mean_ms={mu._fmt(est.w_mean_ms)}  "
                    f"inbound_5xx_fraction={mu._fmt(est.inbound_5xx_fraction)}"
                    f" inbound_failure_fraction={mu._fmt(est.inbound_failure_fraction)}"
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
