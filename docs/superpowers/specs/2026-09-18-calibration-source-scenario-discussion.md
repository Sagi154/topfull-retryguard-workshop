# Which run should freeze μ — discussion after "why only S3?"

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Write-up of the 2026-09-18 discussion that started from a question about
> `2026-09-17-frozen-capacity-rho-design.md`'s calibration plan: "why are we
> running it only for S3?" and "why is the baseline for this calculation not
> another scenario?" **No code or spec was changed.** This document records
> the reasoning, the data that grounds it, and the open fork it leaves for a
> later decision. It supersedes nothing — it is a pre-implementation
> discussion for §3.1/§3.2 of the frozen-capacity design.

Related:
[2026-09-17-frozen-capacity-rho-design.md](2026-09-17-frozen-capacity-rho-design.md)
(the design being discussed — §3.0–3.2 calibration methods),
[2026-09-17-rho-paper-mismatch-discussion.md](2026-09-17-rho-paper-mismatch-discussion.md)
(prior discussion that motivated frozen capacity in the first place),
[RetryGuard.pdf](../../../context/RetryGuard.pdf) §5,
[AGENTS.md](../../../AGENTS.md) (load-calibration constraint: do not raise
Locust user counts without a separate decision),
[`experiments/estimate_service_mu.py`](../../../experiments/estimate_service_mu.py),
[`experiments/capacity_frozen.py`](../../../experiments/capacity_frozen.py),
[`experiments/rho_frozen_report.py`](../../../experiments/rho_frozen_report.py).

**Status:** discussion / design notes. No calibration run has been
performed. `experiments/capacity/capacity_frozen.json` remains the
`not_yet_calibrated` skeleton. Controller (`retryguard.py`) is unaffected.

---

## 1. The two questions, and what data answered them

Q1: **"Why are we running it only for S3?"**
Q2: **"Why is the baseline for this calculation not another scenario?"**

To answer both, every `rho_estimate_report.json` currently in
`experiments/results/campaign_48/` was scanned for `mu_sat` and
`inbound_5xx_fraction` on the four minimum-set services
(`frontend`, `checkoutservice`, `productcatalogservice`, `paymentservice`).
Result:

| Folder | checkout `mu_sat` | checkout 5xx | productcatalog `mu_sat` | payment `mu_sat` | frontend `mu_sat` |
|---|---|---|---|---|---|
| S1 baseline run23/run24 | null | 0.0 | null | null | null |
| S1 RG run7 | null | 0.0 | null | null | null |
| S2 baseline run23 | null | 0.0 | null | null | null |
| S2 RG run12 | null | 0.0 | null | null | null |
| S3 baseline run9 | null | 0.0 | null | null | null |
| **S3 RG run8** | null | 0.0 | null | null | **346.0** |

Every S1/S2 row is flat zero for the three constrained backends — `mu_sat`
requires a tick where ≥5% of that service's inbound traffic is 5xx
(`SAT_5XX_FRACTION = 0.05` in `estimate_service_mu.py`), and at full CPU
(1000m) these services never see meaningful rejection under current load
levels (checkout inbound λ tops out at ~20 req/s across every S1/S2 run —
nowhere near a 1000m ceiling).

The **only** non-null `mu_sat` anywhere in the dataset is `frontend=346.0`,
and it comes from **S3's RetryGuard arm** (`run8`), not the baseline arm
(`run9`). Even S3's own baseline run, which is supposed to be the
"targeted bottleneck" scenario, shows `checkoutservice mu_sat=null` despite
`retryguard.log` recording **8× ON→OFF / 8× OFF→ON** toggles at checkout in
the RG arm with rejection 0.37–0.69 (RetryGuard's own surrogate,
`Δ(5xx+resets)/Δtotal`). `estimate_service_mu.py`'s saturation gate only
counts raw 5xx status codes, not stream resets — so a checkout overload
that manifests mostly as resets can trigger RetryGuard's controller while
still reporting `mu_sat=null` here. This mismatch has not been resolved;
it is a candidate explanation, not a confirmed root cause.

---

## 2. Answer to Q1 — why S3/S4 only

`mu_sat` cannot exist without a saturation tick, and a saturation tick
cannot exist without real 5xx traffic at that service. S1 and S2 leave
`checkoutservice` / `productcatalogservice` / `paymentservice` at their
full paper CPU limits (1000m), and no load level exercised so far pushes
them anywhere near overload there (see table above — flat 0.0 5xx
fraction, every run). S3 (`cpu_limit_fraction: 0.1` on checkout) and S4A/B
(50m / 100m on productcatalog / payment) are the **only** scenarios in the
current matrix that deliberately cripple one of these three services
enough to make saturation observable at all. This is not an arbitrary
choice of calibration source — it is the only source that currently
exists for these three services' `mu_sat` signal.

Frontend is the exception: it *can* saturate without any artificial
constraint (S2/S3 both show frontend under real load), so it does not
need a crippled scenario — but per §3.2 of the frozen-capacity design, a
TopFull-on plateau at frontend measures TopFull's admission cap, not
frontend's own ceiling, so a TopFull-off run is still the right
calibration source for it, not S1/S2 as-is.

---

## 3. Answer to Q2 — the baseline-arm concern is real, and current data violates it

The one existing `mu_sat` sample (`frontend=346`, S3 RG run8) is
contaminated by the exact thing the frozen-μ diagnostic is meant to be
independent of: **RetryGuard was actively toggling retries during that
run.** RetryGuard's whole purpose is to reduce offered/retried load into a
service once it detects high rejection. If `Δ2xx/Δt` on a saturation tick
is computed from an RG-arm run, the observed "saturated throughput" is
throughput *while a controller is actively mitigating the overload* — not
the service's raw, unmitigated ceiling under sustained full retry
pressure. That is a different, smaller quantity than the μ the design
wants to freeze, and it would make any later `rho_hat` computed against
downstream RG-arm data circular in a new way (evaluating RetryGuard's own
effect using a μ shaped by RetryGuard's own effect).

**Conclusion: calibration should only ever use the baseline arm**
(TopFull on, RetryGuard off, Istio's flat default retries) for a given
scenario — never the RetryGuard arm. This was implicit in the
2026-09-17 design's phrasing ("a dedicated saturating run") but not
stated explicitly, and the one real data point that exists violates it.
Practically this means: S3's baseline (`run9`) needs to actually produce a
`mu_sat` for checkout before it's usable — right now it does not (see §1),
which is itself a gap to close, not just a source-selection rule to state.

---

## 4. A second issue this surfaces: the 10× rescale itself is unvalidated

Freezing from S3 at 100m and rescaling ×10 up to a 1000m run (S1/S2) is
exactly the extrapolation `2026-09-17-frozen-capacity-rho-design.md` §3.4
flags as an assumption, not a validated fact: Envoy sidecar / per-process
overhead is roughly fixed regardless of the CPU limit, so it is a
proportionally larger tax at 100m than at 1000m. The spec's only guard is
a warn-and-rescale at a ≥2× millicore gap (§7.6) — it warns, it does not
refuse or independently confirm linearity. The spec's own suggested
remedy, §3.2 "ramp-to-plateau" (get a *second* saturation point at full
CPU, without an artificial constraint), is explicitly **not implemented**
in v1.

### 4a. Why a full-CPU saturation point is harder to get than it sounds

For frontend, TopFull-off + existing S2-style load should suffice (the
`baseline_no_topfull_sustained_overload_run1` config already exists for
this). For `checkoutservice` / `productcatalogservice` / `paymentservice`,
two compounding problems appear:

1. **TopFull may throttle these backends too, not just frontend.** If
   TopFull's RL agents act per-service (suggested by `num_agent.csv`
   being per-service in the collector design), a TopFull-on run could be
   suppressing checkout's admitted rate the same way it suppresses
   frontend's — the TopFull-off requirement from the frontend case may
   apply here as well.
2. **Reaching real saturation at 1000m via normal storefront traffic may
   not be reachable without raising Locust load far beyond current
   scenarios**, and even then, risks two contamination modes:
   - overloading frontend/productcatalog/other backends first, so
     checkout's own ceiling is never isolated on its own terms;
   - saturating the shared `topfull-worker-1` node itself (all 11
     Boutique pods share one node — §3.4's "node-level contention"
     caveat), which would measure node contention, not checkout's
     per-replica ceiling.

   Raising Locust user counts to force this is also exactly the move
   AGENTS.md already flags as requiring "a separate load-calibration
   decision" — this discussion surfaces that decision, it does not
   resolve it.

### 4b. The alternative floated: a direct per-service micro-benchmark

Instead of routing enough *storefront* traffic through checkout to
overload it, hit `checkoutservice`'s gRPC endpoint directly with a small
standalone load generator (e.g. `ghz`, or a short gRPC client script),
bypassing frontend and the rest of the storefront mix. This would:

- isolate the target service's own ceiling from cross-service and
  shared-node contention,
- avoid touching Locust/storefront user counts at all (sidesteps the
  AGENTS.md constraint entirely, since it is not a storefront load
  change),
- resemble a standard single-service capacity benchmark rather than a
  scenario-driven measurement.

Tradeoff: it requires new tooling (not `run_scenario.py`/Locust), and it
measures the service **in isolation**, which is a different notion of
"capacity" than "checkout's throughput while embedded in the full
storefront traffic mix and sharing the node with the other 10 services" —
arguably less representative of what the S1–S4 scenarios actually report
on, even though it produces a cleaner number.

---

## 5. Fork left open (not decided here)

Two independent decisions remain, deliberately not resolved by this
discussion:

1. **Calibration traffic source for the full-CPU point on
   checkout/productcatalog/payment:** elevated storefront load
   (TopFull-off, higher Locust — needs the AGENTS.md load-calibration
   decision) vs. a dedicated direct micro-benchmark harness (new tooling,
   isolates the ceiling, changes what "capacity" means for this
   diagnostic).
2. **Whether to proceed with S3/S4-baseline-only (100m/50m/100m) as the
   sole calibration source for v1**, accepting the warn-and-rescale
   guard as the only protection against the linearity assumption, versus
   blocking on getting a second, full-CPU saturation point first to
   validate — or refute — that assumption before trusting any rescaled
   `rho_hat` on S1/S2.

The user selected, when asked: get a second full-CPU saturation point
before trusting the rescale (i.e., do not settle for S3/S4-only), but has
not yet chosen between "elevated storefront load" and "direct
micro-benchmark" for how to obtain it. That choice, plus the still-open
gap that even S3's own **baseline** arm does not currently produce a
`checkoutservice mu_sat` (§1, §3), are both prerequisites to write an
implementation/execution plan for the calibration work.

---

## 6. What not to do

- Do not freeze a minimum-set service's μ from a RetryGuard-arm run —
  baseline arm only (§3).
- Do not treat S3 RG run8's `frontend mu_sat=346` as a validated
  calibration point; it is the wrong arm and should not be frozen as-is.
- Do not raise Locust user counts to reach a full-CPU saturation point
  without treating that as the explicit load-calibration decision
  AGENTS.md already asks for.
- Do not assume a TopFull-on plateau at any of the four minimum-set
  services is that service's true ceiling (§3.2 of the frozen-capacity
  design; §4a above extends the same caution to backends, not just
  frontend).
- Do not skip validating the 100m→1000m linearity assumption and quietly
  trust a rescaled `rho_hat` on S1/S2 — the ≥2× warn-and-rescale guard is
  a visibility mechanism, not a validation.
