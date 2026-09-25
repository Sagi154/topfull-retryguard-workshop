# S2 overload-scale user-count calibration (2026-09-25)

## Goal

Runs 9–13 (`baseline_no_topfull_sustained_overload_run{9..13}`, both TopFull
and RetryGuard off) were five S2-scale holds trying different Locust
`user_counts` mixes, scored against Task 9's three S2 criteria
([2026-09-21-s1-s6-methodology-and-calibration-implementation.md](../plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md)
Step 2a/2b; criteria defined in
[2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md)):

- **(a)** RetryGuard-kind overload — `Δ(5xx+resets)/Δtotal` on `service_inbound.csv`
  stays above 0.20 for ≥30 consecutive 1 s samples, on one of the 9 controlled
  services.
- **(b)** TopFull Layer A / detector engagement — `topfull_detect.csv`
  `overloaded=1` fraction of the hold (Layer A itself stays at the 10000
  passthrough sentinel with both controllers off; only the detector-side
  signal moves).
- **(c)** Retry volume — `service_edges.csv` outbound `retry` deltas on the
  stressed edges: a storm, not noise.

Summary tables for runs 9–13 already exist:
[2026-09-24-s2-both-off-runs-9-13.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-runs-9-13.md).
This doc goes one level deeper — per-service CPU vs quota, achieved vs
configured RPS, and full edge/latency detail pulled from the raw CSVs by
five parallel subagents (grok-4.7-high-fast), one per run — to explain *why*
the pattern in that doc happens and to propose the next untested mix. It
also folds in [LOCUST-API-PATHS.md](../../../Guides%20and%20Info/LOCUST-API-PATHS.md)'s
call-order detail, which turns out to matter (§4).

This is analysis only. No live run happened this session (VMs were left
`TERMINATED` after the run9–13 sweep). It does not modify
[2026-09-22-locust-api-to-boutique-service-mapping.md](2026-09-22-locust-api-to-boutique-service-mapping.md),
which stays scoped to S1 normal-load, non-saturating tries (20–95 rps/tag).
This doc's regime is S2-scale (50–325 configured users/tag, into real CPU
saturation).

## Dataset

| Run | getproduct | postcheckout | getcart | postcart | emptycart |
|---|---:|---:|---:|---:|---:|
| 9 | 250 | 80 | 250 | 100 | 5 |
| 10 | 325 | 80 | 100 | 100 | 5 |
| 11 | 250 | 100 | 100 | 100 | 5 |
| 12 | 100 | 150 | 100 | 100 | 5 |
| 13 | 50 | 150 | 50 | 100 | 5 |

600 s holds, `scale_constraints: []` (no CPU caps beyond the standard
per-service K8s limits), `retryguard.enabled=false`, `topfull_rl.enabled=false`.
**`run_manifest.json` does not record `user_counts` or `spawn_rate` for any
of the 5 runs** — confirmed by all five subagents independently. The counts
above are taken from the runs-9–13 doc (i.e. the session record), not from
the manifests. **Open item:** the `spawn_rate` divisor these runs actually
used is not recoverable from the pulled folders; confirm with whoever ran
them before reusing these exact configs. Assume 50 (the project default)
unless told otherwise.

## What the raw data adds beyond the summary tables

### Achieved RPS is well below configured count on the heavy tags — and it's a latency effect, not admission control

`topfull_throttle.csv` confirms Layer A stayed at the 10000 sentinel in
every run (2–4 startup samples at 0, then 10000 for the rest) — nothing is
being admission-limited. Yet Locust's own mid-hold mean RPS falls well short
of the configured count whenever P95 latency is high:

| Run | Tag | Configured | Achieved RPS | Achieved/Configured | Mean P95 |
|---|---|---:|---:|---:|---:|
| 11 | getproduct | 250 | 141.8 | 0.567 | ~2100 ms |
| 11 | postcart | 100 | 92.3 | 0.923 | ~80 ms |
| 11 | emptycart | 5 | 4.9 | 0.985 | ~14 ms |

Locust's `constant_throughput(1)` makes each virtual user wait after a
request to hit 1 req/s — but if a request itself takes >1 s, that user
can't reach the target rate. Fast tags (`postcart`, `emptycart`, P95 in the
tens of ms) land near 95–98% of configured; slow tags (`getproduct`,
`getcart`, `postcheckout`, P95 in the seconds) land at 45–70%. **This means
raising a configured count past the point where its own P95 explodes buys
little extra achieved throughput** — the achieved rate is capped by the
handler's own latency, not by how many users you throw at it.

### Frontend is not the bottleneck in any of the 5 runs

Frontend stayed at its HPA-pinned **4 replicas** on every sample in every
run (`resource_usage.csv`, 133–134 samples, `replica_count` a constant 4).
Summed CPU across those 4 replicas never exceeded **1563 m** of a 4600 m
cap (4×1150 m) — max 20–34% utilization, in the highest-load run (run10).
Frontend's own detector `overloaded` is 0 in every run. Whatever limits
achieved throughput, it isn't frontend CPU.

### Checkout overload tracks `postcheckout`'s *achieved* rps almost linearly

| Run | postcheckout achieved rps | checkout (a) longest streak | checkout (b) overloaded % | checkout (c) retries |
|---|---:|---:|---:|---:|
| 9 | 34.5 | 5 | 3.45% | 384 |
| 10 | 50.2 | 21 | 8.33% | 1,458 |
| 11 | 55.1 | **38** | 8.95% | 2,854 |
| 12 | 116.6 | **89** | **41.8%** | **47,538** |
| 13 | 120.3 | **65** | **38.3%** | **45,209** |

Checkout's own CPU caps out at 615–655 m (quota 615 m) in every single
run — even run9's lightly-loaded checkout still spikes to 625 m — but its
*mean* CPU only sustains near-cap (mean 344–368 m) once achieved
`postcheckout` crosses roughly 100 rps. That's the real inflection: once
checkout's steady-state throughput saturates around ~615 m worth of CPU,
more configured `postcheckout` mostly increases the **offered/achieved
gap** (more attempts fail rather than more succeed), which is exactly what
(a)/(c) measure. `postcheckout: 150` (achieved ~117–120) reliably clears
(a) and (b); `postcheckout: 100` (achieved ~55) clears (a) at 38 but stays
under half the hold on (b).

### Recommendations overload tracks `getproduct`+`getcart` *achieved* combined rps — capped by recs's own CPU ceiling

Both `getproduct` and `getcart` call `recommendationservice`
(`LOCUST-API-PATHS.md`), and recs itself calls
`productcatalogservice.ListProducts` — so recs is the **shared** bottleneck
for both page types, not two independent loads.

| Run | getproduct+getcart achieved sum | recs (a) longest streak | recs (b) overloaded % | recs (c) retries | recs max CPU (quota 1150) |
|---|---:|---:|---:|---:|---:|
| 9 | 216.4 | 25 | **90.4%** | 343,801 | 1,169 |
| 10 | 282.3 | **56** | **88.2%** | 265,285 | 1,150 |
| 11 | 200.5 | 22 | **87.9%** | 286,223 | 1,168 |
| 12 | 195.2 | 0 | 0% | 0 | 916 |
| 13 | 97.8 | 0 | 0% | 0 | 787 |

Recs pegs at ~1150 m CPU (its own quota) once achieved combined throughput
crosses roughly ~200 rps, giving 88–90% detector-overloaded consistently in
runs 9/10/11 — but the **30-sample streak** for (a) only cleared once (run10,
56). Runs 9 and 11 landed at 25 and 22 — close misses, not a stable pass.
Run10's mix (`getproduct` 325, `getcart` 100 — a *skewed* heavy-getproduct
mix) gave the biggest streak despite a similar achieved sum to run9's
balanced 250/250. Single-run noise is plausible here; it isn't yet enough
data to call the skew itself causal.

### New finding: `postcheckout`'s confirmation page also loads recommendations — runs 12/13 prove it

`LOCUST-API-PATHS.md` documents that after checkout completes, "the frontend
renders the confirmation page: `recommendationservice` ... and
`currencyservice` again." The existing mapping doc doesn't call this out as
a load driver. Runs 12/13 show it's not negligible:

| Run | getproduct+getcart configured | recs mean util | recs max util | postcheckout achieved |
|---|---:|---:|---:|---:|
| 12 | 100+100 | **0.579** | **0.7965** | 116.6 |
| 13 | 50+50 | 0.443 | 0.684 | 120.3 |

Recs is sitting at **80% of alpha's own threshold** in run12 — right at the
edge of tipping into `overloaded=1` — from `getproduct`/`getcart` at only
100 each, driven substantially by the confirmation-page load from
`postcheckout=150`. This is the key practical implication: **`postcheckout`
is not orthogonal to recs.** Raising it helps push recs toward overload too,
not only checkout — the "breadth" problem isn't as hard as trading off
checkout against recommendations forever.

### Payment/email: structurally capped, not reachable via Locust counts alone

Neither service's detector `overloaded` count is ever nonzero across all 5
runs. Max CPU utilization never exceeds 0.70 of their 155 m quota, even in
run12/13 where checkout's own streak reaches 65–89 and detector-overloaded
41.8%/38.3%. Max rejection streak on either service across all 5 runs is 4
samples — nowhere near 30.

`LOCUST-API-PATHS.md` confirms why: payment and email are only reachable via
`checkoutservice`'s own chain, and checkout's real admitted throughput is
capped at roughly the same ~615 m-CPU-worth of requests/sec regardless of
how much more `postcheckout` you configure (the achieved-vs-configured gap
above). Payment/email downstream of that gate can never see more absolute
volume than checkout itself sustainably processes — and that volume is
evidently too small in per-request CPU cost to threaten either service's
tiny 155 m quota. **This is a structural ceiling, not a tuning problem** —
more `postcheckout` will widen the streak/detector numbers on checkout
further, but will not make payment or email overload. Getting them there
would need either a smaller CPU limit on those services (out of scope for
S2 per the design doc — bottleneck-capping is S3/S4's job) or is simply not
achievable in this topology.

### Shipping/currency: same shared-ceiling problem as recs, not an independent lever

`getcart` is `shippingservice`'s only unique driver (per the mapping doc),
but shipping's CPU never exceeds 122 m of its 770 m quota across all 5 runs
— roughly 16% even at the highest tested `getcart` (run9, achieved 109.9).
Currency gets closer (max mean util 0.44 in run10) but is still well under
the 0.8 alpha line, and — this is the important part — currency is called
*before* recs completes inside the same synchronous handler, so its call
volume is bound to the same page-throughput ceiling recs already saturates.
**Raising `getproduct`/`getcart` further is unlikely to move currency much
past run10's 0.44**, since recs' own CPU cap (already pegged at ~1150 m in
runs 9–11) limits how many page completions per second are even possible,
and currency rides on that same completion rate. Treat this as a low-
confidence secondary target, not a promising third win.

### Cart/catalog/ad: nowhere close

Catalog's quota is 1535 m; max CPU seen across all 5 runs is 631 m (41%).
Ad's quota is 1150 m; max CPU is 229 m (20%). Cart's quota is 1920 m; max
CPU is 594 m (31%). None of the three shows any meaningful rejection streak
in any run. Not reachable via this lever at any tested load level.

## Breadth scorecard

Bold = clears that criterion's bar on its own.

| Run | Mix | checkout (a)/(b)/(c) | recs (a)/(b)/(c) | payment/email/shipping/currency/cart/catalog/ad |
|---|---|---|---|---|
| 9 | 250/80/250/100/5 | 5 / 3.5% / 384 | 25 / **90.4%** / 343,801 | all 0 / 0% / 0 |
| 10 | 325/80/100/100/5 | 21 / 8.3% / 1,458 | **56** / **88.2%** / 265,285 | all 0 / 0% / 0 |
| 11 | 250/100/100/100/5 | **38** / 8.9% / 2,854 | 22 / **87.9%** / 286,223 | all 0 / 0% / 0 |
| 12 | 100/150/100/100/5 | **89** / **41.8%** / 47,538 | 0 / 0% / 0 (util 0.58/**0.80**) | all 0 / 0% / 0 |
| 13 | 50/150/50/100/5 | **65** / **38.3%** / 45,209 | 0 / 0% / 0 (util 0.44/0.68) | all 0 / 0% / 0 |

No run so far has two services both clearing criterion (a) simultaneously.
Every run trades checkout against recommendations because every mix moved
`postcheckout` and `getproduct`/`getcart` in opposite directions. **That
trade-off has never actually been tested against a mix that raises both.**

## Candidate mix for the next try

```
getproduct:   325
postcheckout: 100
getcart:      100
postcart:     100
emptycart:    5
spawn_rate:   50   (unconfirmed — see dataset note above)
```

This is not a new guess — it's a direct interpolation of the two nearest
already-tested points, changing exactly one axis from each:

- **From run10** (325/**80**/100/100/5): keep `getproduct=325` — the mix that
  produced the only streak-≥30 result on recommendations (56).
- **From run11** (250/**100**/100/100/5): raise `postcheckout` to the value
  that produced the only streak-≥30 result on checkout (38).
- `getcart` (100), `postcart` (100), `emptycart` (5) are identical in both
  neighbors — no interpolation needed there, which removes one axis of
  uncertainty.

**Why this should plausibly clear both bars at once, not just one:**
checkout's overload is driven by `postcheckout`'s achieved rps, which
`getproduct`/`getcart` don't touch (confirmed: payment/email/checkout never
moved with those tags in any run). So checkout should behave like run11
(streak ≈38). Recommendations' overload is driven by
`getproduct`+`getcart` achieved throughput, which should behave like run10
(streak ≈56) — and per the confirmation-page finding above, the *higher*
`postcheckout` in this candidate (100 vs run10's 80) adds *more* load to
recs, not less, so if anything this should make recs's streak more robust
than run10's, not weaker.

**Caveat:** this is still an untested combination. `getproduct`'s achieved
throughput could come in lower than run10's 214.3 rps if the extra
`postcheckout` contention drags frontend/recs latency up further (the
achieved-rps-vs-P95 relationship above cuts both ways) — but even a modest
shortfall likely still clears recs' streak bar, since run10's margin (56 vs
the 30 threshold) has room to spare. Recommend this as **try 1** of a
capped-at-3 S2-breadth exploration, not a lock.

## Optional secondary candidate (higher uncertainty, not recommended as the primary try)

Run12 (100/150/100/100/5) already put recs at max util **0.7965** — just
under the 0.8 alpha line — purely from the confirmation-page effect. A
smaller, more surgical nudge worth trying *after* the primary candidate
above: keep `postcheckout=150` (run12's proven checkout-overload level) and
raise `getproduct`/`getcart` modestly (e.g. to 150 each, well under run9–11's
250–325) to see if that's enough to tip recs over 0.8 without needing the
full run10-level `getproduct=325`. This wasn't tested in any of the 5 runs
and carries more uncertainty than the primary candidate, since we don't
have a data point at this specific getproduct/getcart level combined with a
150 postcheckout.

## What this doesn't solve

Payment, email, shipping, currency, cartservice, productcatalogservice, and
adservice are not realistically reachable as a 3rd/4th/5th overloaded
service via `user_counts` tuning alone in this topology, per the structural
ceilings above (§ payment/email, § shipping/currency, § cart/catalog/ad).
If "several" needs to mean more than checkout+recommendations, that
requires a different lever (CPU-limit changes are S3/S4's job, not S2's).

## Related

- Summary tables this doc extends:
  [2026-09-24-s2-both-off-runs-9-13.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-runs-9-13.md),
  [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md).
- Path-level call order (source of the confirmation-page finding):
  [LOCUST-API-PATHS.md](../../../Guides%20and%20Info/LOCUST-API-PATHS.md).
- S1-scale (non-saturating) API→service mapping, different regime, not
  superseded by this doc:
  [2026-09-22-locust-api-to-boutique-service-mapping.md](2026-09-22-locust-api-to-boutique-service-mapping.md).
- Task 9 S2 gate this feeds:
  [2026-09-21-s1-s6-methodology-and-calibration-implementation.md](../plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md)
  Step 2a/2b.
