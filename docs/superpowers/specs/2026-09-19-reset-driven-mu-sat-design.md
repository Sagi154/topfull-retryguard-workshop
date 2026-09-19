# Reset-driven `mu_sat` — design

## 1. Problem

`estimate_service_mu.py`'s only capacity signal, `mu_sat`, only samples ticks
where `Δ5xx/Δtotal >= SAT_5XX_FRACTION` (0.05). `capacity_frozen.py freeze`
requires at least one such sample to freeze `mu_per_millicore`.

Task 1 (2026-09-19, diagnosing S3 RetryGuard `run8`) and the same day's
3-run best-effort full-CPU TopFull/RetryGuard-off calibration battery both
found `inbound_5xx_fraction = 0.0` for the entire run on every target
service (frontend, checkoutservice, paymentservice, productcatalogservice),
even though `service_inbound.csv`'s `resets` column showed heavy load
(`Δresets/Δtotal` up to ~2.6, i.e. resets outnumbering completed requests).
`mu_sat` never populated. Root cause: Envoy's `downstream_rq_total` (the
`total` column) only increments on a *completed* response (status code
assigned); a connection reset (`downstream_rq_rx_reset`) never completes,
so it is invisible to a 5xx-only saturation trigger no matter how much load
is applied.

## 2. Fix — generalize the trigger, not the numerator

RetryGuard's own live controller already treats this correctly —
`measure_inbound_rejection()` (`retryguard.py`) computes its rejection
surrogate as `(Δ5xx + Δresets) / Δtotal`, not 5xx-only. Apply the same
generalization to the saturation trigger in `estimate_service_mu.py`:

- `Tick` gains `delta_resets: int`, differenced from the existing
  `service_inbound.csv` `resets` column. Missing/absent `resets` (older
  CSVs) is treated as 0 — same as `retryguard.py`'s `row.get("resets", 0)`.
  No collector change.
- `Tick.failure_fraction` is the new saturation trigger:
  `(delta_5xx + delta_resets) / delta_total`. Denominator stays `Δtotal`
  (completed requests only), matching RetryGuard's live surrogate exactly —
  do **not** rewrite it as `Δ(5xx+resets)/Δ(total+resets)`. That fraction
  can exceed 1.0 when resets outnumber completions (calibration runs saw
  ~2.6); that is expected and still correctly fires `>= 0.05`.
- Keep `Tick.five_xx_fraction` as a diagnostic; stop using it to gate
  `sat_samples`.
- `sat_samples` (and therefore `mu_sat = median(Δ2xx/dt)`) is now taken on
  ticks where `failure_fraction >= SAT_5XX_FRACTION` (constant kept, still
  0.05 — arbitrary threshold, no new tuning in this change).
- **Numerator unchanged.** `Δ2xx/dt` (successfully-completed throughput
  during the saturated tick) remains the estimate of capacity — a reset
  request never contributes a 2xx or a `total` increment, so this is still
  the same "admitted goodput near saturation" approximation as before, just
  triggered on the right ticks.
- `ServiceEstimate` gains `inbound_failure_fraction` (aggregate
  `(Σ5xx + Σresets)/Σtotal` over the whole run) alongside the existing
  `inbound_5xx_fraction`, so a report stays honest about *why* `mu_sat`
  populated (or didn't) — a report showing `inbound_5xx_fraction=0` but
  `inbound_failure_fraction=0.4` is self-explanatory.
- `format_table()` and `rho_estimate_report.py` print the new field (one
  extra column / one extra token on the toggle-summary line). Methodology
  sentence in `rho_estimate_report.py` that currently says "high 5xx
  fraction" becomes "high (5xx+resets) fraction".
- `capacity_frozen.py`'s `count_sat_ticks()` switches its filter from
  `t.five_xx_fraction` to `t.failure_fraction` (same constant,
  `mu.SAT_5XX_FRACTION`). The freeze error string
  `"no saturating 5xx ticks"` becomes `"no saturating 5xx/reset ticks"`.

No new collector fields, no new CLI flags, no new scenario configs.
`retryguard.py` is not touched. Docs that currently say "v1 freeze is
5xx-only" (`experiments/capacity/README.md`, `AGENTS.md`) are updated
after a successful freeze, not as a separate design.

## 3. What stays out of scope

- No separate "reset-only" vs "5xx-only" `mu_sat` variant — a single
  generalized trigger is enough; splitting it would double the reported
  fields for no decision this project currently needs to make.
- No change to the `SAT_5XX_FRACTION` threshold value.
- No change to `retryguard.py` (unaffected either way).
- No new VM runs for verification — re-run the existing CLI against
  already-pulled local run folders.

## 4. Verification plan

Re-run `python experiments/estimate_service_mu.py <run_dir>` and
`python experiments/capacity_frozen.py freeze <run_dir> --service <svc>
--force` against the 4 local folders that already have high resets / zero
5xx:

1. `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2` — `frontend`
2. `experiments/results/campaign_48/calibration_checkout_payment_full_cpu_run1` — `checkoutservice`, `paymentservice`
3. `experiments/results/campaign_48/calibration_productcatalog_full_cpu_run1` — `productcatalogservice`
4. `experiments/results/campaign_48/S3_targeted_bottleneck/run_topfull_retryguard_targeted_bottleneck_run8` — `checkoutservice` (extra cross-check, this is the run Task 1 originally diagnosed)

Expect `mu_sat` to now be a real number for services with genuinely high
reset-fraction ticks. If any of the four still comes back `null`, that is a
legitimate finding (not enough reset-saturation even by the generalized
definition) — record it as such, do not loosen the threshold further to
force a number.

Update unit tests:

- `experiments/test_estimate_service_mu.py` — a tick with `delta_5xx=0`,
  `delta_resets` large enough that `failure_fraction >= 0.05`, and
  `delta_2xx > 0` must produce a real `mu_sat`. Existing 5xx-only
  saturation test still passes. A healthy tick (5xx=0, resets=0) still
  has `mu_sat=None`.
- `experiments/test_capacity_frozen.py` — freeze succeeds on a
  reset-only-saturated inbound CSV (5xx all 0, resets high); still
  refuses when both 5xx and resets stay 0.
- `experiments/test_rho_estimate_report.py` — only if a constructor /
  table assertion hard-codes the `ServiceEstimate` field list and would
  break when `inbound_failure_fraction` is added; otherwise leave it.
