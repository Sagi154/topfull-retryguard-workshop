---
name: rho-estimate-report
description: >-
  Generate a combined rho/lambda/mu.hat estimate report (per-service, from
  service_inbound.csv alone — mu_hat_w = lambda + 1/W via Envoy inbound
  rq_time_* latency columns) plus a RetryGuard ON/OFF toggle summary (from
  retryguard.log) for one TopFull + RetryGuard workshop run folder. Writes
  rho_estimate_report.md (+ .json) into the run folder itself. Use when the
  user asks to analyze/estimate rho or mu for a run, compare RetryGuard's
  toggle behavior against the rho estimate, or wants "the rho numbers in the
  run results folder" for a scenario_1/2/3/4/5/6 run under experiments/results/.
---

# rho / mu.hat estimate report

Combines two existing pieces of tooling for one run folder into a single
report file, written **into that run folder**:

1. `experiments/estimate_service_mu.py` — offline per-service
   lambda / mu.hat / rho from `service_inbound.csv` alone (`mu_hat_w = lambda
   + 1/W`, the M/M/1 steady-state relation, using a per-service latency
   signal — `rq_time_sum_ms`/`rq_time_count`, added 2026-09-16 — plus a
   saturated-goodput cross-check when 5xx is high). Also reports `w_p50_ms`
   when `rq_time_buckets` is present (per-tick P50 from differenced Envoy
   histogram buckets — robustness check alongside the mean; μ̂/ρ still use
   mean W). Corrected 2026-09-16: see
   `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md` — the
   estimator no longer reads `topfull_detect.csv` at all; the old
   `mu_cpu = lambda / utilization` estimator (TopFull's CPU-quota bookkeeping,
   not the paper's rho) was removed entirely, not kept as a fallback.
2. `retryguard.log` in the same folder (if present) — RetryGuard's own
   `ON→OFF` / `OFF→ON` toggle events, with the rejection value and
   sample counter that triggered each one.

## When to use this

- The user gives you (or you already know) a run folder path under
  `experiments/results/campaign_48/<scenario>/<log_folder>/` and asks for a
  rho/mu estimate, or to compare it against RetryGuard's toggle log.
- Right after pulling a fresh run's results (see `experiments/pull_results.py`,
  which calls this same logic automatically after every `scp` pull).

## How to run it

Prefer calling the script directly — it already handles both parts and all
the graceful-degradation cases:

```bash
python experiments/rho_estimate_report.py <run_dir>
```

This writes `rho_estimate_report.md` and `rho_estimate_report.json` inside
`<run_dir>`, and prints the path it wrote. Report back to the user:
- The per-service `mu_hat_w` / `rho_w` / `w_mean_ms` / `w_p50_ms` table (or
  the "not computed" reason if `service_inbound.csv` is missing entirely —
  expected for pre-2026-09-09 folders like the original `campaign_48/` 48
  rows or `august_38/`). If `service_inbound.csv` exists but predates the
  2026-09-16 `rq_time_sum_ms`/`rq_time_count` columns (any folder pulled
  before that date), `mu_hat_w`/`rho_w` show as `n/a` with an explicit
  per-service note — the report still generates, this is not an error.
  `w_p50_ms` is `n/a` when `rq_time_buckets` is absent (same date cutoff, or
  a collector revision before the bucket column).
- The RetryGuard toggle events, if any (or that no `retryguard.log` exists —
  expected for baseline runs, which never enable RetryGuard).

If asked to do this programmatically instead (e.g. in a larger script), import
the module rather than re-implementing the parsing:

```python
import sys
sys.path.insert(0, "experiments")
import rho_estimate_report as report

md_path = report.generate_report(run_dir)  # Path to the .md written
```

## Context to include when relaying results (do not omit)

`experiments/retryguard.py`'s live controller does **not** use rho — it acts
on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from
`service_inbound.csv`), matching the RetryGuard paper's own live Istio
deployment (Sec 6.2: 20% rejection-rate threshold, 30s window). The rho
estimate here is a **supplementary, offline diagnostic**, not the
controller's decision input and not a validated ground-truth rho:

- `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation) is only valid
  under `rho < 1`. If a service's `lambda_mean` reaches/exceeds its own
  `mu_hat_w_median`, the report flags a saturation note rather than
  trusting the number at face value — a finite observed `W` at that point
  more likely reflects a finite buffer, upstream admission control, or
  non-Poisson/non-exponential real traffic than a valid M/M/1 steady state.
- Treat `rho_w` as directional / good for relative comparisons across
  scenarios or services, not as a precise absolute rho — real traffic is
  not exactly Poisson/exponential (this workshop's Locust
  `WebsiteUser` uses `constant_throughput(1)`, not exponential inter-arrivals),
  and every Boutique service is modeled as M/M/1 even though each pod handles
  concurrent in-flight requests (TopFull CPU quotas make that abstraction
  more defensible here than for an unconstrained multi-core service; M/M/c
  is not implemented).
- Inbound Envoy latency metrics are **live-verified** on this cluster
  (2026-09-16). Outbound `upstream_rq_time` is excluded by Istio's default
  minimal proxy-stats — `service_edges.csv` `rq_time_*` stay structurally
  zero; the estimator only needs inbound.
- `mu_sat` (saturated-goodput cross-check, unaffected by the 2026-09-16
  correction) still exists independently and is worth comparing against
  `mu_hat_w` when both are available.

## Graceful-degradation behavior (already implemented, don't re-derive)

- Missing `service_inbound.csv` → the report notes why (pre-mesh-collector
  folder or collector disabled that run); it does not raise, and it still
  checks for `retryguard.log`. `topfull_detect.csv` is **not** required and
  is never read.
- Missing `retryguard.log` → the report notes RetryGuard was not enabled
  (baseline run) or predates the toggle log; it still computes rho/mu if
  `service_inbound.csv` exists.
- `retryguard.log` present but zero toggle events → reported explicitly as
  "RetryGuard ran but never crossed threshold for `interval_samples`" (a
  real, expected outcome on many flat baseline/RG-inert runs — not a bug).

## Related files

- `experiments/estimate_service_mu.py` — the underlying estimator (reused,
  not duplicated).
- `experiments/rho_estimate_report.py` — this skill's actual logic (CLI +
  importable `generate_report(run_dir)`).
- `experiments/pull_results.py` — scp-pulls a run then calls this
  automatically.
- `experiments/test_rho_estimate_report.py` — unit tests, including the
  graceful-degradation cases above.
- `docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md` —
  original design spec (Locust `Fail`-is-SLO-miss finding still valid;
  its Estimator B is superseded, see below).
- `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md` — the
  correction: what was wrong with the CPU-linear estimator, the
  `mu_hat_w = lambda + 1/W` methodology, live verification findings, P50
  buckets, and remaining limitations.
