# Frozen-capacity ρ diagnostic

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Status:** tools exist (`experiments/capacity_frozen.py`,
> `experiments/rho_frozen_report.py`). The git-tracked table at
> `experiments/capacity/capacity_frozen.json` is an uncalibrated
> skeleton (all four minimum-set services `method: not_yet_calibrated`;
> no real campaign μ frozen into it). Not wired into `pull_results.py`.
> `retryguard.py` is unchanged. `estimate_service_mu.py` /
> `rho_estimate_report.py` have had their `mu_hat_w`/`rho_w` fields
> **removed** (not deprecated) as of this doc — see §1. §3.2
> ramp-to-plateau is **not implemented** (v1 freeze method is `mu_sat`
> only).
>
> **Revision (same day, 2026-09-17):** freeze **throughput per millicore**
> (`mu_per_millicore`), not an absolute req/s μ. The CPU limit that μ
> must reflect is Kubernetes' `resources.limits.cpu` as snapshotted in
> each run's `service_capacity.json`. `topfull_run_quotas.json` is a
> Detector overlay, not the source of that limit — see §3.0 / §3.3.
>
> **Revision (same day, 2026-09-17, decisions):** backend λ is
> first-attempt `service_edges.csv` `total` (§4 / §7.1); freeze μ for
> the **minimum set** only — `frontend`, `checkoutservice`,
> `productcatalogservice`, `paymentservice` (§7.3). §7.2 / §7.4 /
> §7.5 / §7.6 were **decided at implementation** (path, `n_sat_ticks <
> 10` → `low_confidence`, hard error on `cluster_shape`, millicore-gap
> warn-and-rescale at ratio ≥ 2.0) — see §7.

Related: [2026-09-16-rho-estimator-correction.md](2026-09-16-rho-estimator-correction.md)
(first correction: removed the CPU-linear estimator, introduced
`mu_hat_w = lambda + 1/W`), [2026-09-17-rho-paper-mismatch-discussion.md](2026-09-17-rho-paper-mismatch-discussion.md)
(discussion that first flagged the flattening symptom and proposed
"Option A" — this doc is that option, worked out in detail),
[RetryGuard.pdf](../../../context/RetryGuard.pdf) §5,
[`experiments/estimate_service_mu.py`](../../../experiments/estimate_service_mu.py),
[`experiments/rho_estimate_report.py`](../../../experiments/rho_estimate_report.py),
[`experiments/capacity_frozen.py`](../../../experiments/capacity_frozen.py),
[`experiments/rho_frozen_report.py`](../../../experiments/rho_frozen_report.py),
[`experiments/capacity/capacity_frozen.json`](../../../experiments/capacity/capacity_frozen.json),
[`experiments/run_scenario.py`](../../../experiments/run_scenario.py)
(`capture_service_capacity()` → per-run `service_capacity.json`).

---

## 1. Why `mu_hat_w = lambda + 1/W` was removed, not fixed

The 2026-09-16 correction replaced a CPU-quota-based estimator with an
M/M/1 steady-state inversion:

```
W = 1 / (mu - lambda)      # only defined when mu > lambda
mu_hat_w = lambda + 1/W
rho_w = lambda / mu_hat_w
```

This is **circular by construction**, not merely imprecise. The formula's
own derivation requires `mu > lambda` as a precondition — that is what
makes the queue stable enough to have a finite mean sojourn time in the
first place. Solving it for `mu` given an *observed*, finite `W` can
therefore only ever produce a `mu` just above the `lambda` that produced
that `W`. There is no way to feed it real numbers and get `lambda >= mu`
out, except by an averaging artifact (see below) — the equation doesn't
have room to say "this service is overloaded."

Substituting the definition of `W` back into `rho_w` makes this exact.
By Little's Law, `L := lambda * W` is the mean number of requests in
flight at that service. Then:

```
rho_w = lambda / (lambda + 1/W) = (lambda*W) / (lambda*W + 1) = L / (L+1)
```

`rho_w` is a strictly monotone function of concurrency alone, always in
`[0, 1)`, and carries no information about how close the service is to its
actual processing limit — only about how many requests happen to be
in flight, which for a fan-out or slow service can be large even when
perfectly healthy.

**Worked counter-example (S1 baseline, run24):** `productcatalogservice`
handled 1781 req/s at 6.9ms mean latency, 0% errors — as healthy a
tick as this dataset has. `L = 1781 * 0.0069 ≈ 12.3`, so
`rho_w = 12.3/13.3 ≈ 0.925`. The same service under S2 (2425 req/s, 9.5ms)
reports `rho_w ≈ 0.960`. A ~15% jump in `rho_w` for a 36% jump in load on a
service running comfortably below its real limit both times.

**Worked counter-example (frontend, S1 vs S2):** frontend `rho_w` was
0.991 on S1 baseline (λ=392, W=249ms) and 0.996 on S2 baseline (λ=536,
W=334ms) — see
[2026-09-17-rho-paper-mismatch-discussion.md](2026-09-17-rho-paper-mismatch-discussion.md)
§1–§3 for the full numbers. Both near 1 because `λW ≫ 1` (98 and 179
respectively) drives `L/(L+1)` to saturate near 1 regardless of actual
headroom.

**The one place this can be checked against an independent estimate:**
`mu_sat` (`Δ2xx/Δt` on ticks with real 5xx, unaffected by any of the
above — see `estimate_service_mu.py`) is populated in exactly one cell of
the whole `campaign_48/` checkpoint dataset: `frontend` in S3 RetryGuard
run8. There, `mu_hat_w` reported 371 (rho_w = 0.981) while `mu_sat`
reported 346 (giving `lambda/mu_sat = 361/346 ≈ 1.044`) — the independent
estimator says the service was actually over capacity; the W-inversion,
by construction, could not have said that.

**Conclusion:** `mu_hat_w`/`rho_w` are removed entirely from
`estimate_service_mu.py` and `rho_estimate_report.py` (2026-09-17). What
remains — `lambda_mean`, `w_mean_ms`/`w_p50_ms` (reported as a latency
observation, not repurposed as capacity), and `mu_sat` — are the
quantities that don't presuppose their own answer.

---

## 2. What "resembling the paper's ρ" actually requires

RetryGuard.pdf §5.1 defines `rho = lambda / mu` where `mu` is "the rate at
which Service B can process requests, i.e., its capacity" — a property of
the service, not something inferable from one snapshot of it running below
capacity. The paper itself never estimates `mu` live (§4.3.1: production
deployments should use a rejection-rate/retry-volume/delay surrogate
instead — which is exactly what `retryguard.py`'s controller already
does). Building a `rho` diagnostic here is our own, admittedly
approximate, engineering task — but it should at least avoid the trap both
prior attempts fell into: **using the same run to supply both the
numerator and the denominator.**

The fix is structural, not a better formula: get `mu` from measurements
that are independent of the `lambda` you're dividing by. On this stack
μ is a **capacity** (how many req/s the service can finish), and the
lever that actually changes that capacity between scenarios is the
Kubernetes CPU limit we give the pod — not Locust user counts. User
counts change λ. CPU limits change μ. Those must not be mixed.

So freeze a **throughput-per-CPU** constant from a dedicated
calibration run, then rescale it to the CPU the *evaluated* run
actually had:

```
mu_per_millicore(service)
    = throughput_at_saturation(calibration_run)
      / total_millicores(calibration_run)

total_millicores(run)
    = cpu_limit_millicores * replica_count
      # both from that run's service_capacity.json

mu_this_run(service)
    = mu_per_millicore(service) * total_millicores(evaluated_run)

rho_hat(service, evaluated_run)
    = lambda_offered(evaluated_run) / mu_this_run(service)
```

- `mu_per_millicore(service)` comes from a **different run**,
  deliberately designed to observe that service near or at its real
  ceiling. It does not change with S1 vs S2 load. It *is* reused across
  S3/S4, whose CPU limits differ, by multiplying by *that run's*
  millicores rather than by storing a second absolute μ.
- `lambda_offered` uses the *same* rate definition the calibration
  throughput was measured with — see §4 for why this must be stated
  explicitly per service tier (entry vs backend).
- `cpu_limit_millicores` / `replica_count` come from each run's
  **`service_capacity.json`** (a `kubectl get deploy` snapshot). Not
  from Locust, and not from `topfull_run_quotas.json` — see §3.3.

This breaks the circularity: nothing stops `lambda_offered` from
exceeding `mu_this_run`, because `mu_per_millicore` isn't computed from
`lambda_offered`'s own run. It also lets one calibration serve both an
unconstrained S1/S2 checkout (1000m in current campaign files) and an
S3 checkout (100m) without pretending those two have the same capacity.

---

## 3. Freezing μ: candidate methods, ranked

### 3.0 What is frozen (throughput per millicore, not an absolute rate)

μ is capacity. On this deployment the control we have over a service's
capacity is the CPU we allocate to its pod (`resources.limits.cpu`,
plus replica count). Locust user counts are demand (λ); they do not
belong in μ.

An earlier draft of this spec froze an **absolute** req/s μ per
service. That only works if every later run of that service has the
same CPU limit as the calibration run. It does not: S3 sets
`checkoutservice` to `cpu_limit_fraction: 0.1` (100m in the current
paper table), while S1/S2 leave it at the reconciled paper limit
(1000m). A μ taken from S3 checkout saturation is `μ_at_100m`, not a
universal checkout μ. Applying it to S1/S2 would divide unconstrained
load by a deliberately crippled capacity.

The frozen artifact is therefore a **rate per millicore**:

```
mu_per_millicore = throughput_at_saturation / (cpu_limit_millicores * replica_count)
```

`rho_frozen_report.py` then multiplies by the *evaluated* run's
millicores from **that run's** `service_capacity.json`. One calibration
point, reusable across S1/S2/S3/S4 as long as:

1. Cluster shape is unchanged (same worker SKU — already in
   `cluster_shape`, §5.1).
2. Throughput is assumed linear in CPU limit over the range we
   rescale (100m ↔ 1000m is a 10× jump). That assumption is
   **falsifiable**: a second saturating run at a different limit for
   the same service should produce a compatible `mu_per_millicore`. If
   it does not (sidecar / fixed overhead / cache effects), stop
   rescaling and treat each (service, millicores) pair as its own
   frozen entry instead.

**Source of millicores: `service_capacity.json`, not TopFull.**
`run_scenario.py`'s `capture_service_capacity()` does `kubectl get
deploy -n default -o json` and records `cpu_limit_millicores`,
`cpu_request_millicores`, `replica_count` per Boutique Deployment.
Campaign files confirm this is the live cgroup limit for that run —
S1 baseline run24 `checkoutservice` is 1000m; S3 RG run8
`checkoutservice` is 100m. (Some older notes say this snapshot is
taken *before* constraints; the live call order is
`apply_constraints` then `capture_service_capacity`, and the files
match the post-constraint spec. That post-constraint snapshot is what
this diagnostic needs.)

### 3.1 `mu_sat` from a saturating run (preferred where available)

`Δ2xx/Δt` on ticks where the 5xx fraction is high — already implemented,
already in `estimate_service_mu.py`, unaffected by anything in §1. Its
logic: near/at saturation, a service's *admitted* throughput plateaus at
its actual capacity because blocking absorbs the excess (an M/M/1/m-
adjacent argument). This is the strongest capacity signal currently
collectible on this stack, but it is sparse — most runs never generate
sustained 5xx at a given service, so most services in most runs will have
no `mu_sat` sample at all (0 of 76 service-run cells in the 2026-09-16/17
checkpoint dataset had it, except the one S3-checkout-driven frontend
cell).

**Calibration implication:** to get `mu_sat` for a service that doesn't
naturally saturate under a scenario's load (e.g. `cartservice`,
`currencyservice` — comfortably under capacity in every S1/S2/S3 run so
far), a *dedicated* calibration run is needed that specifically drives
that service into 5xx — e.g. a targeted-bottleneck config
(`cpu_limit_fraction`, as S3/S4 already do for `checkoutservice`/
`productcatalogservice`/`paymentservice`) or a ramp-until-failure load
profile aimed at that one service.

The number `mu_sat` itself is still a **throughput** (req/s) at the
CPU limit of that calibration run. What gets written to
`capacity_frozen.json` is `mu_sat / total_millicores` from that same
run's `service_capacity.json`, not the raw `mu_sat`.

### 3.2 Ramp-to-plateau goodput (fallback when `mu_sat` has no samples)

Run a scenario with load high enough to exceed the service's true
capacity (not just TopFull's admission cap), and take the plateau of
`Δ2xx/Δt` even without 5xx — i.e., generalize `mu_sat`'s argument to
"goodput plateaus once further load only adds queueing, not throughput."
Requires confirming a plateau exists (goodput stops rising as offered load
rises) rather than assuming a single high-load run is already past it.

**Known trap (flagged in the mismatch discussion, §5):** on this stack,
TopFull's own admission control (Layer A, CPU-quota-driven) usually caps
goodput before the target service's *own* processing capacity does. A
plateau observed while TopFull is active measures TopFull's cap, not the
service's ceiling. The `baseline_no_topfull_sustained_overload_run1`
control config already exists for this reason (see AGENTS.md §4,
"TopFull-off S2 control") — a TopFull-off ramp-to-plateau run is the
correct source for this method, not a TopFull-on run.

Same as §3.1: the plateau is a throughput; divide by that run's
`service_capacity.json` millicores before freezing.

**Not implemented.** v1 freeze method is `mu_sat` only
(`capacity_frozen.py freeze`). Ramp-to-plateau needs plateau detection
and a TopFull-off calibration run; it is out of scope until a later
spec.

### 3.3 Kubernetes CPU limit is the scale factor; TopFull quota is a cross-check only

Do **not** treat millicores as a third way to *invent* μ. The paper's
μ is a request rate. CPU is how we *scale* a measured request-rate
capacity across scenarios.

| File | What it is | Use for this diagnostic |
|---|---|---|
| **`service_capacity.json`** | `kubectl get deploy` snapshot of `resources.limits.cpu` / `requests.cpu` / `replicas` | **Source of truth** for `cpu_limit_millicores` and `replica_count` on both the calibration run and the evaluated run |
| **`topfull_run_quotas.json`** | Python-computed millicores (`paper_limit × cpu_limit_fraction`) written so TopFull's Detector overlay agrees with what `run_scenario.py` *intended* to patch | **Cross-check only.** If it disagrees with `service_capacity.json` for the same service, that is a quota-sync bug, not a better μ |
| **`run_manifest.json` `effective_cpu_quotas` / `paper_cpu_quotas`** | Same computed table, copied into the results folder | Same as `topfull_run_quotas.json` — audit, not input |

`rho_frozen_report.py` must read millicores from
`service_capacity.json`. It may **warn** (not silently swap in) if
`run_manifest.json`'s `effective_cpu_quotas` or a copied
`topfull_run_quotas.json` disagrees. It must not fall back to those
computed numbers when the kubectl snapshot is missing — report `n/a`
with "no `service_capacity.json`" instead.

The S3/S4 `cpu_limit_fraction` constraints remain the *reason* a
backend often saturates and can be calibrated; they are not an
alternate capacity unit.

### 3.4 Residual error even after per-millicore rescaling

Per-millicore freezing removes the S1-vs-S3 quota mismatch. It does
not make μ a perfect constant:

- **Node-level contention.** All Boutique pods share
  `topfull-worker-1`. S2 puts more total load on the node than S1, so
  a service with the same CPU *limit* can still get less *achieved*
  throughput because neighbors are busier. Calibration should be run
  with otherwise-typical contention, not treated as isolated-core
  capacity.
- **TopFull's admission cap (§3.2).** A TopFull-on plateau measures
  Layer A's allowed rate, which itself depends on cluster-wide CPU
  pressure. That is not the service's own ceiling.
- **Linearity.** Rescaling 100m → 1000m assumes req/s ∝ millicores.
  Envoy sidecars and per-process overheads are not strictly linear.
  Flag a millicore-gap warning (and still rescale) when
  `max(eval,cal) / min(eval,cal) >= 2.0` (§7.6, decided at
  implementation) until a second saturation point confirms the slope.

### 3.5 Rejected: anything derived from the same-run's own admitted λ

Explicitly ruled out (this is exactly what made both prior estimators
circular): using a service's own inbound `lambda` from the run being
*evaluated* to derive its `mu`. `mu_per_millicore` must come from a
run that is not also supplying the `lambda_offered` on the right-hand
side of `rho_hat`. Locust user counts never enter the denominator.

---

## 4. λ: two tiers, stated explicitly (do not conflate)

The mismatch discussion (§2, §5) already identified that "offered load"
means different things at different points in the mesh, and that
conflating them is part of why S1/S2 didn't separate under the old
estimator. This design makes the tiers explicit inputs, not an implicit
assumption baked into one formula:

| Tier | λ source | Use for |
|---|---|---|
| **Entry (storefront)** | Locust total mean RPS (already in `*.csv` per endpoint), or intended `sum(user_counts)` at `constant_throughput(1)` if testing generator intent rather than admitted outcome | `rho_hat` at `frontend` |
| **Backend (per-service)** | Caller-side `service_edges.csv` `total` (first attempts) into that target, summed across all callers — not `total + retry`. Retry volume stays a **separate column**, not in the ρ numerator. | `rho_hat` at the minimum-set backends (`checkoutservice`, `productcatalogservice`, `paymentservice`). Other Boutique services stay `n/a` (§7.3). |

**Why not `service_inbound.csv`'s `total` for backends:** that column is
what the service actually *admitted*, downstream of Envoy's own connection
handling. It systematically understates offered load under overload
(exactly the S1-vs-S2 frontend problem in the mismatch discussion, §2
point 1: admitted ≠ offered once TopFull or a saturated backend is
truncating arrivals upstream of the measurement point). `service_edges.csv`
(caller-side, pre-truncation-at-target) is the closer analogue of offered
load.

**Decided: first-attempt `total`, not `total + retry`.** The paper's
`rho = lambda/mu` (§5.1) uses `lambda`, the *original* request rate,
before retries are added — `Lambda` (capital) is the total including
retries, used to derive rejection probability, not `rho` itself. So
`rho_hat` for a backend uses first-attempt `lambda` from
`service_edges.csv` `total`. Retry volume is reported alongside, not
folded into the numerator. (Confirm at implementation time that
`envoy_cluster_upstream_rq_total` is first-attempt as the collector
already documents; that is a column-definition check, not a reopening
of this choice.)

---

## 5. Proposed artifacts

### 5.1 `capacity_frozen.json` (git-tracked at
`experiments/capacity/capacity_frozen.json` — §7.2 decided at
implementation)

```json
{
  "generated_at": "2026-09-20T12:00:00Z",
  "cluster_shape": "topfull-worker-1=e2-standard-16",
  "capacities": {
    "frontend": {
      "mu_per_millicore": 0.53,
      "unit": "req/s per millicore",
      "calibrated_at_cpu_limit_millicores": 1000,
      "calibrated_at_replica_count": 1,
      "throughput_at_calibration": 530.0,
      "method": "mu_sat",
      "cpu_source": "service_capacity.json",
      "source_run": "campaign_48/S3_targeted_bottleneck/run_topfull_retryguard_targeted_bottleneck_run8",
      "note": "illustrative only — placeholder throughput, not a validated calibration"
    },
    "checkoutservice": {
      "mu_per_millicore": null,
      "method": "not_yet_calibrated",
      "note": "minimum-set backend; needs a dedicated saturating run; rescale later using each run's service_capacity.json (S1/S2 = 1000m, S3 = 100m in current campaign files)"
    },
    "productcatalogservice": {
      "mu_per_millicore": null,
      "method": "not_yet_calibrated",
      "note": "minimum-set backend (S4A constrained); not yet calibrated — no throughput number invented here"
    },
    "paymentservice": {
      "mu_per_millicore": null,
      "method": "not_yet_calibrated",
      "note": "minimum-set backend (S4B constrained); not yet calibrated — no throughput number invented here"
    }
  }
}
```

Key design points:
- **Frozen field is `mu_per_millicore`, not a bare `mu`.** Also store
  the millicores / replica count / throughput it was measured at, so
  a later report can show `mu_this_run` explicitly and can refuse to
  silently rescale across a huge millicore gap without a warning.
- **CPU source is `service_capacity.json`.** Do not persist
  millicores copied from `topfull_run_quotas.json` as if they were
  measured.
- **Versioned by cluster shape.** `mu_per_millicore` is a property of
  the deployed hardware + the service's code, not of the paper's
  model alone — a VM resize (e2-8 → e2-16, already happened once
  mid-project per AGENTS.md §4) invalidates every frozen value. The
  file must record what cluster shape it was calibrated on and refuse
  (or loudly warn) when used against a report from a different shape.
- **Explicit `method` and `source_run` per service**, not a single
  global calibration pass — different services will likely need
  different calibration methods (§3.1–§3.2). The file covers the
  **minimum set only** (§7.3): `frontend`, `checkoutservice`,
  `productcatalogservice`, `paymentservice`. Partial coverage
  (`null` / `not_yet_calibrated` until a saturating run exists) is
  expected inside that set. Services outside it
  (`cartservice`, `currencyservice`, `recommendationservice`,
  `shippingservice`, `adservice`, `emailservice`, `redis-cart`) are
  omitted from the frozen table and reported `n/a` (not guessed) —
  do not add placeholder entries that imply they will be calibrated.
- **Not auto-generated from every run.** Only from runs explicitly
  marked as calibration runs (to avoid quietly overwriting a good
  frozen value with a worse one from an unrelated flat run).

### 5.2 `experiments/capacity_frozen.py` (new)

Builds/updates `capacity_frozen.json` from one or more calibration run
folders. Given a run dir + service + method, reads that run's
`service_capacity.json` millicores, computes
`mu_per_millicore = throughput / (cpu_limit_millicores * replica_count)`,
and writes/updates that one entry (append-only per service unless
`--force`). Refuses to freeze a service whose `service_capacity.json`
row is missing or has a null CPU limit. Read-only with respect to the
run folders themselves (same posture as `rho_estimate_report.py` /
`pull_results.py`).

### 5.3 `experiments/rho_frozen_report.py` (new)

Given a run dir and `capacity_frozen.json`, computes `rho_hat` per
service using the tiered λ from §4 and `mu_this_run` from §2, and
writes a report (same `run_dir`-local convention as
`rho_estimate_report.py` — `rho_frozen_report.md` / `.json`, kept
separate from the existing λ/W/`mu_sat` report). Must:

- Read **this run's** `service_capacity.json` for millicores; report
  `n/a` with "no `service_capacity.json`" (or "service omitted from
  snapshot") rather than inventing a CPU limit.
- Compute `mu_this_run = mu_per_millicore * cpu_limit_millicores *
  replica_count` and show all three of `mu_per_millicore`,
  `mu_this_run`, `rho_hat` — so S3 checkout at 100m is visibly a
  different denominator from S1 checkout at 1000m.
- Report `n/a` with an explicit reason for any service with no frozen
  `mu_per_millicore` — `not_yet_calibrated` for a minimum-set service
  (§7.3) that still lacks a saturating run; out-of-set services
  (`cartservice`, `currencyservice`, `recommendationservice`,
  `shippingservice`, `adservice`, `emailservice`, `redis-cart`) stay
  `n/a` (not guessed), not a fabricated number.
- **Hard error** (do not write a ρ report) if the table's
  `cluster_shape` does not match the CLI/default
  (`topfull-worker-1=e2-standard-16`).
- Warn (not swap sources) if `run_manifest.json` `effective_cpu_quotas`
  disagrees with `service_capacity.json` millicores.
- Warn when evaluated millicores differ from
  `calibrated_at_cpu_limit_millicores` by a large factor (§3.4
  linearity).
- Keep this as visibly a "second-run-informed" number — it should not
  be presented as more authoritative than it is; a single calibration
  run per service is a small sample.

### 5.4 Relationship to the existing `rho_estimate_report.py`

Kept **separate**, not merged. `rho_estimate_report.py` stays a
single-run, no-cross-run-dependency tool (lambda/W/mu_sat, always
computable from just that run's own CSVs). `rho_frozen_report.py`
additionally depends on a calibration artifact from a different run and
should not be silently invoked as part of the automatic post-pull flow in
`pull_results.py` until `capacity_frozen.json` has enough real coverage to
be useful — an empty/mostly-null frozen table would just add a second file
saying "n/a" everywhere.

---

## 6. Illustrative numbers (already available, not yet calibrated)

Using the existing checkpoint dataset (see mismatch discussion §6),
*if* we treat S2's admitted goodput plateau as a rough stand-in for
`mu_entry` (a placeholder, not a proper calibration run per §3.2's
TopFull-off caveat):

| | λ (Locust total mean RPS) | Illustrative `rho_hat` (μ≈530) |
|---|---|---|
| S1 baseline run24 | 388 | 388/530 ≈ **0.73** |
| S2 baseline run23 | 551 | 551/530 ≈ **1.04** |

This lands in the target band the team discussion wanted (S1 in
0.5–0.8, S2 just over 1) — but it uses a TopFull-on plateau as `mu`,
which §3.2 already flags as likely measuring TopFull's cap rather than
frontend's true ceiling. Frontend's CPU limit is 1000m in both of
those folders, so per-millicore rescaling would not change this table
(same millicores on both runs). This table is included to show the
shape of a usable result, **not** as a validated `mu_entry` — a real
calibration run (TopFull-off ramp-to-plateau, or an actual `mu_sat`
sample at frontend under a scenario that drives frontend into
sustained 5xx) is still needed before trusting a number like this.

**Why per-millicore matters for backends (qualitative):** suppose
checkout saturates at some throughput `X` req/s in an S3 run where
`service_capacity.json` says 100m / 1 replica. Then
`mu_per_millicore = X/100`. The *same* frozen constant gives
`mu_this_run = X` on S3 and `mu_this_run = 10X` on S1/S2 (1000m). The
same offered λ therefore yields a 10× higher `rho_hat` under S3 —
which is the targeted-bottleneck story — without storing two
different μ values or letting Locust user counts leak into the
denominator. No campaign folder currently has a real checkout
`mu_sat`, so this remains a shape argument, not a number.

---

## 7. Decisions before implementation

1. **Which λ definition for backends** — first-attempt only vs
   `total + retry` from `service_edges.csv` (§4).
   **Decided (2026-09-17):** first-attempt only. Use `service_edges.csv`
   `total` (first attempts), **not** `total + retry`. Retry volume
   stays a separate column, not in the ρ numerator. Rationale:
   RetryGuard.pdf §5.1 ρ uses original λ, not capital-Lambda (retries).
2. **Where `capacity_frozen.json` lives** — inside `experiments/results/`
   (versioned per campaign) vs a standalone `experiments/capacity/`
   directory outside the results tree.
   **Decided at implementation (2026-09-17):**
   `experiments/capacity/capacity_frozen.json`, resolved from
   `capacity_frozen.py` as
   `Path(__file__).parent / "capacity" / "capacity_frozen.json"`
   (`capacity_frozen.default_capacity_path()`).
3. **Which services get a frozen μ / calibration run design** — do we
   need new dedicated per-service-saturating scenario configs (extending
   the S3/S4 `cpu_limit_fraction` pattern to more services), or is
   ramp-to-plateau on the existing TopFull-off control config sufficient
   for the entry tier and S3/S4 sufficient for their three constrained
   backends, leaving the rest (`cartservice`, `currencyservice`,
   `recommendationservice`, `shippingservice`, `adservice`,
   `emailservice`, `redis-cart`) uncalibrated indefinitely (explicitly
   represented as `n/a`, not guessed at)?
   **Decided (2026-09-17): minimum set only.** Freeze μ for:
   `frontend`, `checkoutservice`, `productcatalogservice`,
   `paymentservice`. Leave `n/a` (not guessed): `cartservice`,
   `currencyservice`, `recommendationservice`, `shippingservice`,
   `adservice`, `emailservice`, `redis-cart`. Rationale: enough for
   S1 vs S2 entry ρ and S3/S4 constrained backends; extra services
   would each need a dedicated saturating calibration run.
4. **Confidence reporting** — a frozen `mu_per_millicore` from a
   single run, single `mu_sat` tick-median is a small sample; should
   the report surface a confidence/sample-size caveat per service, and
   if so what threshold (e.g. minimum number of saturating ticks)
   triggers a "low confidence" flag instead of a bare number?
   **Decided at implementation (2026-09-17):** store `n_sat_ticks`;
   report `low_confidence: true` when `n_sat_ticks < 10`.
5. **Re-calibration cadence** — VM resizes already happened once
   mid-project (AGENTS.md §4, e2-8 → e2-16). Does every infra change
   require a full re-calibration pass, and how do we make a stale
   `capacity_frozen.json` (calibrated pre-resize) impossible to
   accidentally use post-resize? (§5.1's `cluster_shape` field is a
   first step; enforcement — hard error vs warning — is undecided.)
   **Decided at implementation (2026-09-17):** default
   `cluster_shape` is `"topfull-worker-1=e2-standard-16"`; **hard
   error** if the table's `cluster_shape` ≠ the CLI/default (do not
   write a ρ report). Full re-calibration after a VM resize; do not
   silently reuse a pre-resize table.
6. **Linearity / millicore-gap warning** — when the evaluated run's
   `cpu_limit_millicores` differs from
   `calibrated_at_cpu_limit_millicores` (S3 100m vs S1 1000m is the
   live case), warn vs refuse vs require a second saturation point
   before rescaling.
   **Decided at implementation (2026-09-17):** warn and still rescale
   when `max(eval,cal) / min(eval,cal) >= 2.0`; print both millicores
   so the jump is visible.

(1)–(6) are now decided. §3.2 ramp-to-plateau remains **not
implemented** (v1 freeze is `mu_sat` only). Live saturating
calibration runs are still outstanding — the git-tracked table is a
`not_yet_calibrated` skeleton.

The millicore-source question (K8s `service_capacity.json` vs TopFull
quota overlay) is **closed**: use `service_capacity.json` (§3.3).

---

## 8. What not to do

- Do not resurrect `mu_hat_w = lambda + 1/W` or any other same-run
  λ→μ inversion as a "quick fix" — the circularity is structural, not a
  parameter-tuning problem (§1).
- Do not freeze an **absolute** req/s μ and reuse it across S1/S2 vs
  S3/S4 — those runs do not give the service the same CPU (§3.0).
- Do not take millicores from `topfull_run_quotas.json` /
  `effective_cpu_quotas` as the scale factor. Those are TopFull's
  Detector overlay (intended paper-table × fraction). The cgroup
  limit is `service_capacity.json` (§3.3).
- Do not put Locust user counts into μ. User counts are λ.
- Do not compute `mu_per_millicore` from a TopFull-on plateau and
  present it as the service's true capacity without flagging the
  TopFull-cap caveat (§3.2).
- Do not change `experiments/retryguard.py`'s live controller to use
  any `rho_hat` from this design — it stays on the paper's own
  §4.3.1/§6.2 rejection-rate surrogate, unaffected by any of the
  above.
- Do not raise Locust user counts to try to force a paper-`rho > 1`
  result without a separate load-calibration decision (existing
  AGENTS.md constraint, unrelated to this design but easy to
  conflate with it).
