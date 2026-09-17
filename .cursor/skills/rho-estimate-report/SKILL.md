---
name: rho-estimate-report
description: >-
  Generate a per-service lambda/W/mu_sat observation report (from
  service_inbound.csv alone — admitted arrival rate, Envoy inbound
  rq_time_* sojourn-time latency, and a sparse saturated-goodput capacity
  cross-check) plus a RetryGuard ON/OFF toggle summary (from
  retryguard.log) for one TopFull + RetryGuard workshop run folder. Writes
  rho_estimate_report.md (+ .json) into the run folder itself. Does NOT
  compute a rho/mu.hat number today (removed 2026-09-17, see below — it was
  circular by construction). Use when the user asks to inspect per-service
  load/latency for a run, compare RetryGuard's toggle behavior against
  those observations, or wants "the lambda/latency numbers in the run
  results folder" for a scenario_1/2/3/4/5/6 run under
  experiments/results/.
---

# Per-service lambda / W / mu_sat report

Combines two existing pieces of tooling for one run folder into a single
report file, written **into that run folder**:

1. `experiments/estimate_service_mu.py` — offline per-service
   `lambda_mean` (admitted arrival rate), `w_mean_ms`/`w_p50_ms` (this
   service's own inbound sojourn time, from Envoy's `downstream_rq_time`
   histogram — `rq_time_sum_ms`/`rq_time_count`, added 2026-09-16 — a
   latency observation, not a capacity stand-in), and `mu_sat` (a sparse
   saturated-goodput capacity cross-check, only populated on ticks with
   real 5xx). **Does not report a `rho` or `mu.hat`** — see "Why no rho"
   below.
2. `retryguard.log` in the same folder (if present) — RetryGuard's own
   `ON→OFF` / `OFF→ON` toggle events, with the rejection value and
   sample counter that triggered each one.

## When to use this

- The user gives you (or you already know) a run folder path under
  `experiments/results/campaign_48/<scenario>/<log_folder>/` and asks to
  inspect per-service load/latency, or to compare it against RetryGuard's
  toggle log.
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
- The per-service `lambda_mean` / `mu_sat` / `w_mean_ms` / `w_p50_ms` table
  (or the "not computed" reason if `service_inbound.csv` is missing
  entirely — expected for pre-2026-09-09 folders like the original
  `campaign_48/` 48 rows or `august_38/`). If `service_inbound.csv` exists
  but predates the 2026-09-16 `rq_time_sum_ms`/`rq_time_count` columns (any
  folder pulled before that date), `w_mean_ms`/`w_p50_ms` show as `n/a`
  with an explicit per-service note — the report still generates, this is
  not an error. `mu_sat` will read `n/a` on almost every run — it needs
  real 5xx to populate at all.
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

## Why no `rho` (do not re-add `mu_hat_w`/`rho_w`)

`experiments/retryguard.py`'s live controller does **not** use rho — it
acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from
`service_inbound.csv`), matching the RetryGuard paper's own live Istio
deployment (Sec 6.2: 20% rejection-rate threshold, 30s window). That is
unaffected by any of the below.

This report went through two rho estimators, both removed:

1. `mu_cpu = lambda / utilization` (from `topfull_detect.csv`) — conflated
   TopFull's own CPU-quota admission bookkeeping with the paper's
   queueing-theoretic `rho = lambda/mu`. Removed 2026-09-16, see
   `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`.
2. `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state sojourn-time relation,
   solved for `mu`), with `rho_w = lambda/mu_hat_w`. Removed 2026-09-17 —
   **circular by construction**, not just imprecise: `W = 1/(mu-lambda)`
   presupposes `mu > lambda` (stability) as an input, so solving it for
   `mu` can only ever return a value just above the observed `lambda`.
   Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W`
   is mean concurrency (Little's Law) — a quantity that is always `< 1` and
   therefore structurally cannot represent the `rho > 1` miscoordination
   regime this whole diagnostic exists to detect. It also reported ~0.93
   for `productcatalogservice` under normal S1 load with 6.9ms latency and
   zero errors — purely from serving ~1800 req/s, not from being
   overloaded. See
   `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md` for
   the full derivation, worked counter-examples across the S1/S2/S3
   dataset, and the one cell with an independent capacity cross-check
   (`mu_sat`) where the two estimates disagreed.

What remains is what can be honestly computed from a single run without
presupposing its answer: `lambda_mean` (admitted, not offered — see the
design doc for why that distinction matters when TopFull is active),
`w_mean_ms`/`w_p50_ms` (reported as latency, never as capacity), and
`mu_sat` (an independent but sparse saturation-based capacity signal).

**If you want an actual `rho_hat = lambda_offered / mu_this_run`:** run
the **separate** command `python experiments/rho_frozen_report.py
<run_dir>` (table + freeze CLI: `experiments/capacity_frozen.py`,
`experiments/capacity/capacity_frozen.json`). That uses
`mu_per_millicore` frozen from a *different* saturating run, then
rescales by this run's Kubernetes CPU limit in
`service_capacity.json` — not inferring μ from the same run being
evaluated, and not using `topfull_run_quotas.json` as the CPU source.
Do **not** merge that output into this skill's `rho_estimate_report.md`.
The table is currently an uncalibrated skeleton (`not_yet_calibrated`);
freeze via saturating calibration before treating numbers as real μ.
Do not tell the user there is no ρ tool.

## Graceful-degradation behavior (already implemented, don't re-derive)

- Missing `service_inbound.csv` → the report notes why (pre-mesh-collector
  folder or collector disabled that run); it does not raise, and it still
  checks for `retryguard.log`. `topfull_detect.csv` is **not** required and
  is never read.
- Missing `retryguard.log` → the report notes RetryGuard was not enabled
  (baseline run) or predates the toggle log; it still computes
  lambda/W/mu_sat if `service_inbound.csv` exists.
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
- `experiments/test_rho_estimate_report.py` / `test_estimate_service_mu.py`
  — unit tests, including the graceful-degradation cases above.
- `docs/superpowers/specs/2026-09-11-slo-fail-and-mu-estimator-design.md` —
  original design spec (Locust `Fail`-is-SLO-miss finding still valid;
  its Estimator B is superseded, see below).
- `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md` — first
  correction: removed the CPU-linear estimator, introduced (and later
  retracted) `mu_hat_w = lambda + 1/W`.
- `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md` —
  second correction: why `mu_hat_w`/`rho_w` was circular; freeze
  `mu_per_millicore` from `service_capacity.json` (not TopFull quotas).
- `experiments/rho_frozen_report.py` — **separate** `rho_hat` command
  (`python experiments/rho_frozen_report.py <run_dir>`); not this
  skill's report; not called from `pull_results.py`.
- `experiments/capacity_frozen.py` /
  `experiments/capacity/capacity_frozen.json` — freeze CLI + skeleton
  table (all four minimum-set services `not_yet_calibrated` until a
  saturating calibration).
