# Frontend / productcatalog μ recalibration — design

## 1. Problem

`capacity_frozen.json`'s `frontend` and `productcatalogservice` entries are
both flagged `low_confidence` (`n_sat_ticks=2`), but the real problem is
worse than "too few samples" — the two samples that *did* trigger `mu_sat`
are not saturation at all.

Evidence from the two calibration folders' `service_inbound.csv`:

- **frontend** (`baseline_no_topfull_sustained_overload_run2`, 691 ticks
  over ~600s at CPU limit 1000m): from roughly tick 100 through tick ~688
  the service held a steady **~480–580 req/s with zero 5xx and zero
  resets** — a clean, healthy plateau, never overloaded. The only 2 ticks
  where `failure_fraction >= 0.05` are `10:32:28Z` / `10:32:29Z`, and the
  file's last row is `10:32:30Z` — i.e. these are the **last 2 rows of the
  entire series**, coincident with run/collector shutdown, not mid-run
  overload.
- **productcatalogservice** (`calibration_productcatalog_full_cpu_run1`,
  990 ticks over ~900s at CPU limit 500m, `getproduct: 800` users): steady
  **~2,400–2,900 req/s, zero 5xx/resets**, for essentially the whole run.
  The 2 sat ticks are `11:25:27Z` / `11:25:28Z`; the file's last row is
  `11:25:29Z` — again the literal tail of the series.

Both services' offered load in those runs was simply never enough to
overload them at their real (paper) CPU limits — they are cheap per
request compared to `checkoutservice` (0.1615 req/s/millicore) and
`paymentservice` (0.0195), which saturated naturally at 1000m with normal
load and gave 34 / 20 genuine mid-run sat ticks. The frozen
`mu_per_millicore` for frontend (0.238 → 238 req/s at 1000m) is
demonstrably wrong: the service ran at ~500 req/s with zero errors
*moments before* the "saturating" tick fired. This is why the resulting
`rho_hat` values (S1 frontend 1.632, productcatalog 2.546) look absurd —
the frozen ceiling is below real, already-observed healthy throughput.

Root cause of the false trigger: `run_scenario.py`'s run teardown (proxy /
collector / pod stop sequence) produces a burst of connection resets on
whichever services are still receiving in-flight traffic, and
`estimate_service_mu.py` has no way to distinguish that from genuine
overload — it just sees `failure_fraction >= SAT_5XX_FRACTION` and takes
the tick.

## 2. Fix — two independent pieces

### 2a. Estimator: trim the trailing shutdown window

`estimate_service_mu.py`'s `summarize_service()` computes `sat_samples`
from `Tick.failure_fraction` over the full tick list. Change: **exclude
the last 5 ticks of the series from `sat_samples` candidacy**, for every
service, unconditionally. This is a fixed, small trim — not a heuristic
that tries to detect "was this actually a shutdown," which would be
over-engineering for a problem that only shows up in the last handful of
rows.

- Applies globally (all services, all future runs, not special-cased to
  frontend/productcatalog) — the failure mode is structural to how any run
  ends, not specific to these two services.
- Real mid-run saturation windows are unaffected: checkout's 34 sat ticks
  and payment's 20 are all mid-run, far from the tail, so trimming 5 ticks
  off the end changes nothing there (verified by re-running the CLI after
  the change — see §4).
- If a service's *only* sat ticks happen to fall in the last 5 rows (as
  with frontend/productcatalog today), `mu_sat` now correctly comes back
  `None` / `not_yet_calibrated` instead of a poisoned number — that is the
  intended, honest behavior; §2b is what actually gets these two services
  a real value.
- `Tick` list is already time-ordered (one row per second, as written by
  the collector); "last 5 ticks" means "last 5 rows for that service,"
  not last 5 seconds of wall-clock time. No new fields, no new CLI flags.

### 2b. Recalibration: constrain CPU so today's load actually saturates

Reuse this project's existing `cpu_limit_fraction` mechanism (already used
by S3/S4 to constrain `checkoutservice`/`productcatalogservice`/
`paymentservice`) to bring frontend and productcatalog's CPU ceiling down
to where the load we can already generate genuinely overloads them:

- **frontend**: constrain to **`cpu_limit_fraction: 0.1`** of its 1000m
  paper limit → **100m**. No existing precedent value for frontend in this
  repo; chosen because the service demonstrably handled ~550 req/s
  error-free at 1000m, so even a conservative true ceiling is far below
  100m's implied ceiling at the load levels already used.
- **productcatalogservice**: constrain to **`cpu_limit_fraction: 0.1`** of
  its 500m paper limit → **50m** — this is the *same* value already used
  by Scenario 4A (topology-position calibration) for this exact service,
  so it is a proven-safe constraint, not a new guess. At 500m the service
  handled ~2,700 req/s error-free, so 50m should overload readily with the
  existing `getproduct: 800` load.
- Everything else about the two calibration runs stays as-is: same load
  profile, same duration, TopFull RL off, RetryGuard off, same collector
  set, 300s cool-off before/after. Only the CPU constraint changes.
- This relies on the same linearity assumption the whole frozen-capacity
  design already depends on (`mu_per_millicore` constant across CPU
  levels) — no new assumption is introduced, just applied in the other
  direction from how checkout/payment used it (they calibrated at full CPU
  and the assumption lets that number apply at S3/S4's lower constrained
  CPU; here we calibrate at lower CPU and the same assumption lets that
  number apply at S1/S2's full CPU).
- `capacity_frozen.py freeze` already records
  `calibrated_at_cpu_limit_millicores` per entry, so the frozen table will
  correctly show 100m/50m for these two (vs. 1000m/500m today) — no schema
  change needed.

## 3. What stays out of scope

- No change to `SAT_5XX_FRACTION` (still 0.05).
- No change to `retryguard.py`'s live controller (unaffected either way —
  it never reads `mu_sat`).
- No attempt to detect "is this tick a shutdown artifact" via any signal
  other than position-in-series (e.g. no correlation with process-exit
  logs, no cross-referencing collector SHUTDOWN timestamps). Position-based
  trim is sufficient for the observed failure mode and simpler.
- No load-generation changes (Locust user counts / spawn rate / workers)
  — the CPU-constraint lever avoids needing more raw offered load.
- No re-calibration of checkoutservice/paymentservice — their existing
  34/20-tick freezes are genuine and unaffected by either fix.
- No change to the `n_sat_ticks < 10 → low_confidence` threshold or the
  `cluster_shape` guard.

## 4. Verification plan

1. **Estimator trim**: add a unit test to `test_estimate_service_mu.py`
   confirming a tick sequence where the only high-`failure_fraction` ticks
   are the last 1–3 entries produces `mu_sat=None` after the trim, while an
   equivalent sequence with the same failing ticks placed mid-series still
   produces a real `mu_sat`. Re-run
   `python experiments/estimate_service_mu.py <run_dir>` against
   `calibration_checkout_payment_full_cpu_run1` and confirm checkout/payment
   `mu_sat` and `n_sat_ticks` are unchanged (34 / 20) after the trim.
2. **Recalibration runs**: after VM health check (Task 0 pattern from the
   prior calibration plan) and a 300s cool-off, run the two constrained
   configs (bumped `run_number`/`log_folder`, do not overwrite `run1`/
   `run2`), 300s cool-off between them. Pull results, run
   `estimate_service_mu.py` on each, confirm real mid-run `mu_sat` samples
   (ideally ≥10 ticks, i.e. not `low_confidence`) with the shutdown tail
   already excluded by §2a.
3. **Freeze + re-check ρ**: `capacity_frozen.py freeze --force` for
   `frontend` and `productcatalogservice` from the new runs, confirm
   `calibrated_at_cpu_limit_millicores` shows 100/50, and `note` no longer
   says `low_confidence` (or, if genuinely still under 10 ticks, report
   that honestly rather than loosening anything to force a pass).
4. Re-run `rho_frozen_report.py` on S1 baseline `run24` and S2 baseline
   `run23` and report the updated `rho_hat` for all four services —
   expect frontend/productcatalog to drop into a more plausible range
   given the corrected (higher) `mu_per_millicore`.
5. Update `experiments/capacity/README.md` and `AGENTS.md` with the new
   numbers/confidence and the corrected calibration CPU levels, same as
   the previous calibration round.
