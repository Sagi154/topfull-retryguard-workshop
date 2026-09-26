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

This started as analysis-only (no live run in the original 2026-09-25
session; VMs were left `TERMINATED` after the run9–13 sweep). This doc's
regime is S2-scale (50–325 configured users/tag, into real CPU saturation),
distinct from [2026-09-22-locust-api-to-boutique-service-mapping.md](2026-09-22-locust-api-to-boutique-service-mapping.md)'s
S1 normal-load, non-saturating regime (20–95 rps/tag). **Update
(2026-09-26):** the candidate mix proposed below was tested live as run26,
plus three more mixes as runs 27–29 (a separate session, on already
`RUNNING` VMs) — see the new "Runs 26–29" section below the candidate mix.
That section's findings **do** now add a scoped caveat to the mapping doc
(its S1-scale `postcheckout`→checkout linearity claim doesn't survive S2
saturation) — see that doc's own "Regime change at S2 scale" note.

## Dataset

**Runs 3–7 predate this dataset** (2026-09-24, same day, before runs 9–13)
and are covered in their own write-up,
[2026-09-24-s2-both-off-runs-summary.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-runs-summary.md),
not repeated in full here — see the dedicated section below ("Runs 3–7")
for why they matter to this doc's conclusions.

| Run | getproduct | postcheckout | getcart | postcart | emptycart |
|---|---:|---:|---:|---:|---:|
| 3 | 300 | 100 | 210 | 20 | 20 |
| 4 | 380 | 100 | 270 | 20 | 20 |
| 5 | 300 | 100 | 210 | 20 | 20 |
| 6 | 340 | 100 | 240 | 10 | 10 |
| 7 | 380 | 100 | 270 | 20 | 20 |
| 9 | 250 | 80 | 250 | 100 | 5 |
| 10 | 325 | 80 | 100 | 100 | 5 |
| 11 | 250 | 100 | 100 | 100 | 5 |
| 12 | 100 | 150 | 100 | 100 | 5 |
| 13 | 50 | 150 | 50 | 100 | 5 |
| 26 | 325 | 100 | 100 | 100 | 5 |
| 27 | 325 | 100 | 100 | 20 | 5 |
| 28 | 50 | 100 | 100 | 400 | 5 |
| 29 | 50 | 50 | 50 | 50 | 430 |

600 s holds, `scale_constraints: []` (no CPU caps beyond the standard
per-service K8s limits), `retryguard.enabled=false`, `topfull_rl.enabled=false`.
Runs 26–29 are `baseline_no_topfull_sustained_overload_run{26..29}`,
confirmed `spawn_rate: 50` (`run_manifest.json` still omits `user_counts`
but the YAML history is known for these four). Run26 is this doc's own
"candidate mix" (§ below), tested live; runs 27–29 replay the three other
mixes from the 2026-09-24 both-off series (originally runs 15/16/17) at the
same valid (unset) sidecar CPU limit as run26, so they are directly
comparable to runs 9–13 and to each other, not to the invalid
sidecar-limited runs 14–17.
**`run_manifest.json` does not record `user_counts` or `spawn_rate` for any
of the 5 runs** — confirmed by all five subagents independently. The counts
above are taken from the runs-9–13 doc (i.e. the session record), not from
the manifests. **Open item:** the `spawn_rate` divisor these runs actually
used is not recoverable from the pulled folders; confirm with whoever ran
them before reusing these exact configs. Assume 50 (the project default)
unless told otherwise.

## Runs 3–7: run6 already cleared two services at once — correcting this doc's earlier "no run has" claims

An earlier section below (written from runs 9–13 and 26–29 alone) says "no
run so far has two services both clearing criterion (a) simultaneously"
and "no run in this series ... has cleared the (a) 30-tick streak bar on
two services simultaneously." **Both statements are wrong once runs 3–7
are counted.** `baseline_no_topfull_sustained_overload_run6`
(`340/100/240/10/10`, run before run9 on the same day) is the only both-off
hold across the whole 3–29 dataset where **both** checkout and
recommendations clear a 30-tick inbound-rejection streak **and** both stay
Layer B `overloaded` for most of the hold:

| Run | Checkout streak / Layer B overloaded | Recommendations streak / Layer B overloaded | Both ≥30 and both Layer B-hot? |
|---|---|---|---|
| 3 | **592** / 591 of 636 | 1 / 38 of 636 | No — checkout only |
| 4 | 49 / 552 of 636 | 13 / **565** of 636 | No — rec streak short |
| 5 | 90 / 106 of 638 | **288** / 515 of 638 | No — checkout not Layer B-hot |
| **6** | **177** / **476** of 637 | **44** / **558** of 637 | **Yes** |
| 7 | **230** / 572 of 636 | 15 / 511 of 636 | No — rec streak short |

Run6's mix, `getproduct=340, postcheckout=100, getcart=240, postcart=10,
emptycart=10`, is meaningfully different from every mix tried in runs
9–13/26–29: it is the only one that cuts `postcart`/`emptycart` down to 10
each while keeping browse (`getproduct`+`getcart`) high (580 combined) and
`postcheckout` at a moderate 100. **This mix, or something close to it,
deserves a direct retest under the runs 9–13/26–29 collector stack**
(mesh `service_edges.csv`/`service_inbound.csv` etc. were already present
in this earlier session too, so the numbers above are directly comparable
in kind, just not re-verified at the same per-tick depth as the §"checkout
retry-latching mechanism" analysis below).

### Same counts, different results: a reproducibility warning

Two pairs in this same 3–7 series reran the *identical* configured counts
with a 300 s cool-off between, on the same pinned frontend/HPA setup, and
got substantially different outcomes:

- **run3 vs run5** (`300/100/210/20/20`, both): checkout streak **592 → 90**;
  recommendations streak **1 → 288**; frontend inbound failure **0.09 →
  0.61**. The hot service flipped entirely.
- **run4 vs run7** (`380/100/270/20/20`, both): more stable but still
  moved — checkout streak **49 → 230**; recommendations streak **13 → 15**
  (both stayed short).

This directly bears on how much weight to put on any single run in this
whole dataset, including run26 (this doc's own candidate mix, tested only
once): **a mix that clears a bar on one try is not guaranteed to clear it
on a replay.** No mix anywhere in the 3–29 series (including run6) has
been independently replayed and reconfirmed. Treat every "streak = X"
number in this doc — run6's included — as a single data point, not a
verified stable property of that mix.

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

Bold = clears that criterion's bar on its own. Streak values are
longest-consecutive-samples-above-0.20, out of ~611–613 scored 1 s ticks;
retry Δ is whole-hold `service_edges.csv` positive-delta sum.

| Run | Mix | checkout (a)/(b)/(c) | recs (a)/(b)/(c) | payment/email/shipping/currency/cart/catalog/ad |
|---|---|---|---|---|
| 9 | 250/80/250/100/5 | 5 / 3.5% / 384 | 25 / **90.4%** / 343,801 | all 0 / 0% / 0 |
| 10 | 325/80/100/100/5 | 21 / 8.3% / 1,458 | **56** / **88.2%** / 265,285 | all 0 / 0% / 0 |
| 11 | 250/100/100/100/5 | **38** / 8.9% / 2,854 | 22 / **87.9%** / 286,223 | all 0 / 0% / 0 |
| 12 | 100/150/100/100/5 | **89** / **41.8%** / 47,538 | 0 / 0% / 0 (util 0.58/**0.80**) | all 0 / 0% / 0 |
| 13 | 50/150/50/100/5 | **65** / **38.3%** / 45,209 | 0 / 0% / 0 (util 0.44/0.68) | all 0 / 0% / 0 |
| **26** | 325/100/100/100/5 | **592** / **92.9%** / 45,182 | 2 / **57.1%** / 120,541 | payment streak 2 (5.9%), email 8 (22%); rest 0 |
| **27** | 325/100/100/20/5 | 43 / 37.8% / 3,586 | 5 / **87.3%** / 233,125 | all 0 |
| **28** | 50/100/100/400/5 | **471+119** / **90.7%** / 69,857 | 0 / 0% / 0 | payment streak 14 (0%), email 2; rest 0 |
| **29** | 50/50/50/50/430 | **566** / **90.3%** / 33,672 | 0 / 0% / 0 | all 0 |

Run 26 is the first mix **in this 9–13/26–29 series** with two services
simultaneously clearing a criterion: checkout clears (a)/(b)/(c) outright,
and recommendations clears (b) (57.1%, well past the half-hold bar) and
produces a real six-figure retry storm (c), but its (a) streak stays at
2 — see § below for why. **Counting the earlier run3–7 series (above),
run6 already put two services over the (a) 30-tick bar at the same time**
(checkout 177, recommendations 44) — the only mix anywhere in the 3–29
dataset to do so on criterion (a) specifically. Runs 28 and 29 are the
strongest single-service checkout results in the whole dataset (retry Δ
69,857 and detector 90.7%/90.3%), but confirm §"the checkout retry-latching
mechanism" below: neither `postcart=400` nor `emptycart=430` add anything
to that — checkout's own overload is set entirely by whether its retry
loop is "latched," which both runs are.

## Candidate mix for the next try (tested live as run26 — see results below)

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

**Caveat (as written before the run):** this was an untested combination.
`getproduct`'s achieved throughput could come in lower than run10's 214.3
rps if the extra `postcheckout` contention drags frontend/recs latency up
further — but even a modest shortfall likely still clears recs' streak
bar, since run10's margin (56 vs the 30 threshold) has room to spare.

### Actual result (run26, live)

The prediction was half right. Checkout **exceeded** the run11 prediction
by a wide margin — streak 592 (the whole hold) instead of ≈38, detector
93% instead of 9%, retries 45,182 instead of 2,854. Recommendations did
**not** clear the streak bar the prediction expected: streak 2, not ≥56,
even though its detector share (57%) and retry volume (120,541) are both
real and substantial. The reasoning that failed was "checkout's overload
is driven by `postcheckout`'s achieved rps" — checkout's overload turned
out to depend on a threshold/latching dynamic (whether its own sojourn time
sits above or below the 500 ms per-try timeout), not on a roughly-linear
function of achieved throughput. See the next section for the mechanism,
confirmed across runs 26–29 by four independent subagent analyses of the
raw CSVs.

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

## Runs 26–29: the checkout retry-latching mechanism (supersedes the "linear in postcheckout" story above)

Four subagents independently re-read `service_inbound.csv`, `service_edges.csv`,
`resource_usage.csv`, and the Locust CSVs for runs 26–29 at the per-tick level.
The consistent finding overturns the §"Checkout overload tracks
`postcheckout`'s achieved rps almost linearly" claim above (which was based
on runs 9–13 alone, where achieved postcheckout only ever moved between
34 and 120 rps).

### The mechanism

Checkout's mean completed-request sojourn time (`rq_time_sum_ms` /
`rq_time_count` on `service_inbound.csv`) sits right on **Istio's 500 ms
`perTryTimeout`**. Which side of that line it lands on determines whether
checkout is overloaded for the whole hold or barely at all — almost
independent of how much `postcheckout` is configured:

- **Latched (retry loop self-sustains):** sojourn ≈ 500–510 ms. A large
  share of attempts (≈0.42–0.44) time out and get counted as resets, each
  one already consumed part of Istio's `attempts: 3` budget, so checkout's
  *admitted* arrival rate becomes **2.3×–3×** the client's first-attempt
  rate. That retried volume is enough on its own to pin checkout's CPU at
  **608–614 m of its 615 m quota** (98–99.8%) for the rest of the hold,
  which keeps sojourn on the timeout, which keeps the retries coming — a
  closed loop that, once started, does not need help from any other tag.
- **Unlatched (loop never starts / breaks):** sojourn ≈ 190–200 ms, well
  under the timeout. Almost no attempts time out, checkout's CPU sits at
  429–480 m (not pinned), and the client's first-attempt rate passes
  through almost unmultiplied.

### Evidence: same first-attempt rate, opposite outcome

| Run | postcheckout configured | Checkout first-attempt rate (edge total − retry) | Regime | Sojourn | CPU (of 615 m) | Streak |
|---|---:|---:|---|---:|---:|---:|
| 26 | 100 | 32.87 req/s | **latched, whole hold** | 502 ms | median 609 | **592** |
| 27 | 100 | 29.93 req/s (33.0 first-min) | **latched for 43 s, then unlatched** | 502 ms → 196 ms after min 2 | 542→429 mean | 43 |
| 29 | **50** | ~29.9 req/s (retry-multiplied to 88.8 admitted) | **latched, whole hold** | 503 ms | median 608 | **566** |
| 11 (parent) | 100 | ~15.8 req/s | **latched for ~2 min, then unlatched** | ~500 ms → idle | pinned then idle | 38 |
| 28 | 100 (achieved 55.7) | 50.1 req/s | **latched, whole hold, with two 21-tick unlatch gaps** | 502 ms | median 609 | 471+119 |

Run 29 is the clearest single data point: **configured `postcheckout=50`
still fully latches checkout** (streak 566, CPU median 608 m) — the
first-attempt rate (~30 req/s) is essentially the same as runs 26/27's, but
retries multiply it to ~89 admitted req/s, which is already enough. This
means **checkout's overload is close to insensitive to `postcheckout`
above some low threshold** (well under 50) once the loop latches — raising
it further mostly raises the *absolute* retry count (run28's 69,857 vs
run26's 45,182, because run28's achieved postcheckout was higher at 55.7
vs 47.6), not the *severity* (failure fraction stays ~0.42–0.44 and CPU
stays pinned at ~609 m in both).

What flips a hold between latched and unlatched is not yet fully
explained, but the runs suggest **shared frontend/mesh contention with a
simultaneous recommendations retry storm** is one driver: run11 and run27
both unlatch after roughly a minute, and both are holds where
recommendations is independently retry-storming for frontend concurrency
(run11: recs streak 22, 88% detector; run27: recs streak 5, 87% detector).
Run26, where recommendations never enters its own full storm (streak 2),
stays latched the whole hold. This is a plausible-but-unconfirmed causal
link, not a proven one — no run has isolated frontend contention as the
sole variable.

**Practical implication:** targeting checkout via `postcheckout` count is
not a reliable dial once past a low threshold (~50). What actually
controls the checkout result is whether the retry loop latches, and that
looks more sensitive to overall hold shape (what else is happening to
frontend/recs) than to `postcheckout`'s own configured or achieved value.

### Recommendations: run10 (streak 56) remains unbeaten; the near-miss shape is now understood

Runs 26 and 27 both raise recommendations' *first-attempt* arrival rate
above run10's (run26: 380 req/s vs run10's 299; run27: 343 req/s, the
highest first-attempt rate seen in the whole series) — and both raise the
detector-overloaded share to 57–87%, real CPU pressure. Neither clears the
30-tick streak (run26: 2, run27: 5). Per-tick histograms explain why:

- Run10 (the best result): median failure fraction **0.245**, mass sits
  mostly *above* 0.20 (356 of 641 ticks in [0.20, 0.30), 127 in
  [0.30, 0.50)) — it camps above the line.
- Run26: median **0.15**, mass sits in [0.10, 0.20) (470 of 573 ticks);
  only 43 ticks (mostly singletons) poke above 0.20.
- Run27: median **0.185**, right up against the line — 144 of 613 ticks in
  [0.18, 0.20) alone, 206 above 0.20, but almost all excursions are 1–5
  ticks long (88 of 130 excursions are singletons).

So recommendations in runs 26/27 is a **higher-arrival, lower-failure-rate**
regime than run10/run11: more requests get through as 2xx (more retries
succeed, fewer time out), because checkout is soaking up the retry budget
in run26 while recs itself isn't as deeply saturated as in run10/run11
(CPU max 963–1066 m vs run10's 1104 m / run11's 1148 m). Raising
`getproduct`/`getcart` past run10's level, or pairing it with a higher
`postcheckout`, did not push recommendations further into overload — if
anything it kept it slightly further away, because that arrangement
happens to leave more slack in recs' own retry budget. **Run10's specific
mix (325/80/100/100/5) is still the best untouched lever for recommendations
in this series; nothing tested since has beaten it.**

The confirmation-page contribution to recommendations (flagged in runs
12/13 as a "new finding" above) requires checkout to actually **complete**
PlaceOrder requests. On run26, postcheckout's Locust goodput is ≈0.09 req/s
(checkout is too overloaded for almost any request to finish inside the
1 s SLO), so the confirmation-page render essentially never fires:
recommendations' first-attempt rate divided by (`getproduct`+`getcart`
achieved) comes out to 1.011 — a near-exact match with **no** measurable
extra contribution from postcheckout. Contrast with parent run12, where
checkout *is* completing requests (its own regime is intermittent, not a
sustained CPU-pinned latch) and recommendations' zero-retry arrival rate
equals `getproduct + getcart + postcheckout` to within 0.1%. **The
confirmation-page effect on recommendations only shows up when checkout is
succeeding, not when it's fully retry-latched** — the two S2 criteria
(checkout overload vs. recommendations getting confirmation-page load)
are in mild tension for that specific pathway, on top of the CPU-sharing
tension already documented in the run9–13 section above.

### postcart and emptycart at extreme counts: confirmed fast-path, no latency wall even at 4–86× the earlier tested range

Run28 tests `postcart=400` (vs. 100 in every earlier run) and run29 tests
`emptycart=430` (vs. 5 everywhere else) — both far outside the previously
tested range.

| Tag | Run | Configured | Achieved RPS | Achieved/configured | Mean P95 |
|---|---|---:|---:|---:|---:|
| postcart | 28 | 400 | 397.7 | 0.994 | 160 ms |
| emptycart | 29 | 430 | 427.6 | 0.995 | 31 ms |
| postcart (reference) | 26 | 100 | 99.5 | 0.995 | 77 ms |
| emptycart (reference) | 26 | 5 | 5.0 | 0.997 | 19 ms |

Both tags hold the same ~99.4–99.7% achieved/configured ratio at 4× and 86×
their earlier tested levels, with only a small P95 increase (77→160 ms,
19→31 ms) — confirming (and extending) the run9–13 finding that fast,
cheap tags don't hit `constant_throughput(1)`'s latency wall the way
`getproduct`/`getcart`/`postcheckout` do. Neither addition measurably
moved any other service: cartservice stayed at 17.7–25.1% of its 1920 m
quota in both runs, redis-cart stayed under 7% of quota, and neither
service's rejection streak left 0.

### Payment/email under `postcart=400` (run28): traffic went *down*, not up — the "structural ceiling" finding was incomplete

The run9–13 analysis (above) called payment/email "structurally capped,
not reachable via Locust counts alone," treating the ceiling as fixed
regardless of what else is configured. Run28 shows the ceiling can also
move **downward**: payment's plateau admitted rate fell to **20.6 req/s**
(13% of checkout's 155.5 req/s inbound rate) versus run26's **77.6 req/s**
(79% of checkout's 98.2 req/s inbound rate) — even though run28's checkout
is seeing *more* total admitted volume (155.5 vs 109.5 req/s) than run26.
The reason: checkout's PlaceOrder handler calls shipping (quote) early and
payment/email (Charge, SendOrderConfirmation) later in its own internal
sequence; when checkout's retry-latched loop is running hottest, more of
its own attempts get aborted (by the per-try timeout) before reaching the
later payment/email calls, so a *higher* checkout retry-storm intensity
can mean *less* absolute traffic reaches payment/email, not more. Payment's
CPU stayed at 57 m of 155 m quota (37%) on run28, below even run26's 77 m
(50%). **Payment/email remain unreachable via `postcheckout` — but not
because more `postcheckout` monotonically "tries harder" to reach them; it
can do the opposite once checkout is already deep in its own retry
latch.**

## What this doesn't solve

Payment, email, shipping, currency, cartservice, productcatalogservice, and
adservice are not realistically reachable as a 3rd/4th/5th overloaded
service via `user_counts` tuning alone in this topology, per the structural
ceilings above (§ payment/email, § shipping/currency, § cart/catalog/ad).
If "several" needs to mean more than checkout+recommendations, that
requires a different lever (CPU-limit changes are S3/S4's job, not S2's).

## Open question after runs 26–29

Within the 9–13/26–29 series alone, no mix cleared the (a) 30-tick streak
bar on two services simultaneously; run26 comes closest — checkout clears
all three criteria and recommendations clears (b)/(c) — but the checkout
retry-latching mechanism means `postcheckout` count is not the reliable
dial for reproducing or tuning that result that it appeared to be after
runs 9–13 alone. **Counting the full 3–29 dataset, run6 already did clear
two services on (a)** (checkout 177, recommendations 44) — see the § above
— so the practical open question is narrower than "find a mix that clears
two services": it is **"can run6's result (or run26's) be reproduced on a
second try, and does it survive the same collector-stack/per-tick scrutiny
this doc gave runs 26–29?"** The run3-vs-run5 and run4-vs-run7 replay
instability (same section) means neither run6 nor run26 should be treated
as a locked-in S2 candidate mix without at least one confirming rerun.

Any future S2 breadth attempt should also treat "does checkout latch" as
its own (currently unexplained) variable, not assume it follows linearly
from `postcheckout`. Testing a mix that deliberately suppresses
recommendations' own retry storm (to keep it from unlatching checkout, per
the run11/run27 pattern) while keeping `postcheckout` at run29's proof that
even 50 is enough once latched, is one plausible lever — not yet tried.
Retesting run6's mix (`340/100/240/10/10`, low `postcart`/`emptycart`,
moderate `postcheckout`) under the same per-tick scrutiny as runs 26–29 is
another, and arguably higher priority given it already has one clean
double-clear.

## Related

- Summary tables this doc extends:
  [2026-09-24-s2-both-off-runs-9-13.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-runs-9-13.md),
  [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md).
- Runs 3–7 (earlier same-day series; source of run6's double-clear and the
  replay-instability finding, both folded in above):
  [2026-09-24-s2-both-off-runs-summary.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-runs-summary.md).
- Runs 26–29 coarse summary (streaks/detector/retries only — this doc adds
  the per-tick mechanism above it):
  [2026-09-26-s2-both-off-replay-runs-26-29.md](../../../Guides%20and%20Info/2026-09-26-s2-both-off-replay-runs-26-29.md).
- Path-level call order (source of the confirmation-page finding):
  [LOCUST-API-PATHS.md](../../../Guides%20and%20Info/LOCUST-API-PATHS.md).
- S1-scale (non-saturating) API→service mapping — different regime; see
  its own "Regime change at S2 scale" note for what carries over and what
  does not:
  [2026-09-22-locust-api-to-boutique-service-mapping.md](2026-09-22-locust-api-to-boutique-service-mapping.md).
- Task 9 S2 gate this feeds:
  [2026-09-21-s1-s6-methodology-and-calibration-implementation.md](../plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md)
  Step 2a/2b.
