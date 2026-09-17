# Why `rho_w` cannot be the paper’s ρ — discussion after the S3→S1→S2 checkpoint

TopFull + RetryGuard Workshop — TAU Deepness Lab

> Write-up of the 2026-09-17 discussion that started from the S3→S1→S2
> checkpoint readout. **No estimator change was implemented.** This document
> records the finding, the algebra, the conflict with RetryGuard.pdf and with
> Scenario 2’s “ρ > 1” language, and the options for a later diagnostic that
> could actually match the paper’s ρ.

Related: [2026-09-16-rho-estimator-correction.md](2026-09-16-rho-estimator-correction.md)
(the `mu_hat_w = lambda + 1/W` estimator that this discussion critiques),
[RetryGuard.pdf](../../../context/RetryGuard.pdf) §5 / §4.3.1 / §6.2,
[SCENARIOS-GUIDE.md](../../../Guides%20and%20Info/SCENARIOS-GUIDE.md) Scenarios 1–3,
[`experiments/estimate_service_mu.py`](../../../experiments/estimate_service_mu.py),
[`experiments/rho_estimate_report.py`](../../../experiments/rho_estimate_report.py).

**Status:** discussion / design notes. Controller (`retryguard.py`) is unchanged
and must stay on the mesh rejection-rate surrogate.

---

## 0. Where this sits in the timeline

The 2026-09-16 → 2026-09-17 checkpoint sextet on the e2-standard-16 worker
produced the first full-duration S1/S2/S3 pair with live `rq_time_*` columns
and a `rho_estimate_report.md` in every folder:

| Order | Usable folder | Locust rows | RG toggles |
|---|---|---|---|
| S3 baseline | `…/targeted_bottleneck_run9` | 486 | n/a |
| S3 RG | `…/targeted_bottleneck_run8` | 493 | 8× ON→OFF, 8× OFF→ON at checkout |
| S1 baseline | `…/normal_op_run24` (run23 Locust-truncated; discarded) | 260 | n/a |
| S1 RG | `…/normal_op_run7` | 262 | 0 (PASS) |
| S2 baseline | `…/sustained_overload_run23` | 511 | n/a |
| S2 RG | `…/sustained_overload_run12` | 514 | 0 (TopFull upstream of mesh) |

VMs were stopped after the sequence. The ρ reports were generated automatically
by `pull_results.py`. This document starts from reading those reports.

---

## 1. The puzzle from the readout

Frontend `rho_w` sat at **≈ 1 on both S1 and S2**, even though S2 is defined as
twice the Locust users of S1 (“sustained overload”, ρ > 1) and S1 as normal
operation (well inside capacity, never approaching ρ > 1).

Frontend numbers from the baseline arms:

| Run | inbound λ (req/s) | W mean | `rho_w` | Locust total mean RPS / Goodput |
|---|---|---|---|---|
| S1 baseline run24 | 392 | 249 ms | **0.991** | 388 / 387 |
| S2 baseline run23 | 536 | 334 ms | **0.996** | 551 / 530 |

S2 *did* take more load than S1: higher λ, higher W, higher Locust RPS
(388 → 551), frontend CPU 837 m → 950 m (both over the 800 m Detector gate).
`rho_w` barely moved. Checkout on the same folders *did* separate (S1 ρ_w ≈
0.47 vs S3 checkout ρ_w ≈ 0.90–0.92), so the reports are not uniformly
useless — frontend is the pathological case.

---

## 2. Why `rho_w` flattens (and why S1 already looks “full”)

The live estimator is the M/M/1 **steady-state inversion** from the 2026-09-16
correction:

```
W = 1 / (mu - lambda)          # only valid for rho < 1
mu_hat_w = lambda + 1/W
rho_w    = lambda / mu_hat_w
         = lambda W / (lambda W + 1)
```

Once **λW ≫ 1**, that fraction is forced next to 1. A few req/s of leftover
`1/W` is all that keeps it below 1.

- S1: λ = 392, W = 0.249 s → λW ≈ **98** → ρ_w = 98/99 = 0.990
- S2: λ = 536, W = 0.334 s → λW ≈ **179** → ρ_w = 179/180 = 0.994

You would need W on the order of **1/λ** (~2–3 ms at these rates) to see
ρ_w ≈ 0.5–0.8. Frontend inbound sojourn is hundreds of milliseconds even in
“normal op” (S1 getcart P95 ~611 ms), because Envoy `downstream_rq_time` at
frontend includes **waiting on downstream RPCs** (cart / catalog / checkout /
…). The 2026-09-16 spec already noted frontend W is higher because it fans
out; treating that W as an M/M/1 sojourn of a single server makes
`mu_hat_w ≈ λ + a few req/s`.

Two further mismatches with “S2 is 2× S1”:

1. **Admitted ≠ offered.** S1 Locust users are half of S2 (e.g. getcart 50 vs
   100; total users 310 vs 620), but frontend inbound λ only went **392 → 536
   (~1.4×)**. TopFull is live on e2-16 (thresholds leave 10000). Extra users
   are shed at the proxy.
2. **Completed RPS is not 2× either.** Locust total mean RPS 388 vs 551.
   `constant_throughput(1)` per user does not survive overload: users wait,
   Fail/SLO-miss rises, TopFull caps entry.

So S2 was heavier than S1. `rho_w` cannot show it.

---

## 3. The formula always sits below 1

This is not an empirical accident. For any finite positive λ and W:

```
rho_w = λ / (λ + 1/W)  <  1
```

`1/W` is always positive, so **the inversion cannot report ρ ≥ 1**. It
inverts `W = 1/(μ − λ)`, which exists only when `μ > λ`. Overload has already
been assumed away.

A true infinite-buffer M/M/1 at ρ ≥ 1 has unbounded W. A finite observed W
(hundreds of ms) plus λ ≈ μ_hat_w means a finite buffer, upstream admission,
concurrency, or a non-M/M/1 service — not “μ = λ + 1/W.” The estimator’s
`SATURATION_NOTE` exists for that case; it still emits a number that *looks*
like 0.99.

`estimate_service_mu.py`’s λ is **mesh inbound** `Δtotal/Δt` (admitted
arrivals at the sidecar), not Locust offered users and not the paper’s
retry-amplified Λ. Under TopFull, admitted λ is pulled toward whatever Layer
A will let through, so this λ is structurally ≲ capacity.

---

## 4. Conflict with the paper and with Scenario 2

**RetryGuard.pdf §5** defines `rho = lambda / mu` as offered arrival rate
over processing capacity. λ is allowed to exceed μ. That is the point of
the section: ρ > 1 is miscoordination / overload; the M/M/1/m formulas then
give blocking and retries. μ is a property of the service (req/s it can
process), not something inferred from a finite wait.

The paper **never** gives a live μ-estimation procedure (`lambda` / `mu` /
`m` / `k` are simulation parameters). §4.3.1 / §6.2 say a live deployment
should use a **surrogate** (rejection rate, retry volume, delay). That is
what `retryguard.py` already does. Building a ρ diagnostic is our own
engineering task; the 2026-09-16 inversion is consistent with the *stable*
M/M/1 identity, not with the paper’s overload definition.

**Scenario 1** (SCENARIOS-GUIDE): flat load well inside capacity; the system
should never approach ρ > 1.

**Scenario 2**: ramp until offered load exceeds capacity (ρ > 1) and hold.
That “ρ > 1” is a **load-generator claim** (offered Locust vs cluster
capacity), not “run `estimate_service_mu.py` and look for a number above 1.”

**Scenario 3** already encodes that global ρ > 1 on every microservice is
not the design: only the constrained node (checkout at 100 m) is supposed
to sit above capacity.

Agreed target from the 2026-09-17 discussion (not implemented):

| | Bottleneck (frontend / entry) | Other services |
|---|---|---|
| **S1** | ρ ≈ **0.5–0.8** (headroom) | lower, often ≪ 1 |
| **S2** | ρ **> 1** at entry | not required; backends may stay &lt; 1 because TopFull cuts arrivals |
| **S3** | checkout ρ > 1; rest of cluster need not be globally saturated | |

If S2 users = 2 × S1 users and μ is the same, then
`ρ_S1 < 1 < ρ_S2 ≈ 2 ρ_S1` implies **ρ_S1 ∈ (0.5, 1)**. An S1 bottleneck
ρ of 0.99 leaves no room for S2 to look like overload on the same scale.

ρ > 1 on all 11 Boutique services is **not** the goal and is probably not
achievable: unconstrained overload hits the entry aggregator; cart / catalog /
payment often stay below capacity. That is why S3 exists.

**Caveat already visible in the checkpoint:** S1 baseline run24 frontend CPU
max was **837 m** (over the 800 m Detector gate). In TopFull-Detector terms
S1 is not a cool “ρ ≪ 1” hold on e2-16. Two issues are mixed: (1) the
W-inversion cannot report ρ > 1, and (2) current S1 Locust may already be
too close to the frontend CPU gate.

---

## 5. What a paper-matching diagnostic would need

Paper ρ needs an **independent μ** and an **offered λ** that can exceed it.

μ **cannot** be taken from:

- the same run’s admitted λ (ρ becomes identically ~1),
- or `λ + 1/W` (ρ is identically &lt; 1).

μ has to sit *between* S1 offered and S2 offered for the S1/S2 story to work.

Suggested roles (discussion only):

| Piece | Candidate signal |
|---|---|
| λ at entry | Locust total RPS, or intended `sum(user_counts)` at `constant_throughput(1)` |
| λ at a backend | caller-side `service_edges` total (+ retry) into that target — closer to the paper’s Λ |
| μ at entry | plateau goodput when offered is clearly above completed (S2 goodput ~530, or a TopFull-off / ramp-until-plateau hold) |
| μ at checkout | S3 `mu_sat` / inbound 2xx plateau under the 100 m cap |

**Circular-μ trap:** if μ_entry is set to the *same* S2 admitted λ (~535),
S2 ρ is 1 by construction. The TopFull-on goodput plateau is an **admission
cap**, not necessarily unconstrained processing capacity. A TopFull-off or
ramp-until-plateau hold is the cleaner μ.

**e2-16 may still refuse paper-ρ > 1.** If unconstrained frontend capacity
is well above 551 req/s, a *correct* paper ρ on S2 stays &lt; 1 even though
TopFull fires on CPU (quota × α). Detector overload is **CPU/quota**, not
request ρ. Fixing the formula will not invent ρ > 1; that would need more
offered load, TopFull-off, or a smaller worker. Load-calibration is a
separate decision (existing AGENTS.md note: do not raise Locust users
without a spec).

W stays useful as **sojourn**. It must not be the denominator of ρ.

The live controller stays on `Δ(5xx+resets)/Δtotal`. Any new ρ remains an
offline diagnostic.

---

## 6. Options discussed (not implemented)

**A — Freeze μ, then ρ̂ = λ_offered / μ (preferred in discussion)**  
One independent capacity per service (at least for frontend). Drop
`μ = λ + 1/W` as the ρ formula. Keep W as latency.

Illustrative with μ_entry ≈ 530 req/s (S2 total goodput plateau, same stack):

- S1 ρ ≈ 388 / 530 ≈ **0.73** (inside the 0.5–0.8 band)
- S2 ρ ≈ 551 / 530 ≈ **1.04**, or ~**1.17** if λ is intended 620 users/s

If unconstrained μ is higher, S2 paper-ρ may stay &lt; 1 (see §5).

**B — Don’t estimate μ; report offered / admitted**  
S2 “ρ > 1” becomes “Locust offered &gt; TopFull-admitted / goodput.” Honest,
no fake μ, not comparable to §5’s λ/μ. Fine as a scenario check, weak as
“paper ρ.”

**C — Hybrid**  
W-based only on unsaturated backends with small W (λW not ≫ 1); A’s frozen
μ / `mu_sat` at the bottleneck. Two different quantities named ρ — easy to
misread S1 frontend.

**Recommendation from the discussion: A**, labeled as an offline diagnostic.
Treat “is S2 really paper-ρ > 1 on e2-16?” as a second, load-calibration
question.

---

## 7. What not to do

- Do not treat frontend `rho_w ≈ 0.99` on S1 and S2 as “S1 was already as
  loaded as S2” or as “S2 failed to overload.”
- Do not use `rho_w` as a test for Scenario 2’s ρ > 1.
- Do not change `retryguard.py` to act on this (or any) computed ρ.
- Do not raise Locust users until a separate load-calibration spec says so.
- Do not revive `mu_cpu = lambda / utilization` (removed 2026-09-16).

---

## 8. Folders this discussion used

Do not overwrite these. S1 baseline **run23** is Locust-truncated; use
**run24**.

- `experiments/results/campaign_48/S3_targeted_bottleneck/baseline_topfull_no_retryguard_targeted_bottleneck_run9`
- `experiments/results/campaign_48/S3_targeted_bottleneck/run_topfull_retryguard_targeted_bottleneck_run8`
- `experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24`
- `experiments/results/campaign_48/S1_normal_op/run_topfull_retryguard_normal_op_run7`
- `experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23`
- `experiments/results/campaign_48/S2_sustained_overload/run_topfull_retryguard_sustained_overload_run12`
