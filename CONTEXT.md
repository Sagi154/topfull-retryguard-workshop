# Workshop experiments

Language for how this lab runs TopFull, RetryGuard, and Online Boutique. Implementation details live in the migration spec and the guides, not here.

## Language

### Trees and recipes

**Ron's setup**:
The experiment recipe Ron Nezer actually used: cluster manifests, Detector CPU beliefs, Boutique Deployment resources, replica/HPA shape, and loadgen mix. The inherited VMs are not this; they are only the machines.
_Avoid_: copied environment, his cluster, working TopFull environment (when those mean the VMs)

**Workshop tree**:
The TopFull checkout the runner drives (`idozacharia`'s clone). Canonical after the migration: Ron's *values* are ported here; the runner does not point at Ron's home directory.
_Avoid_: his tree, `/home/user/TopFull`, swapping trees

**KAIST upstream**:
The paper scripts at git commit `0c7af21`, before either Ron's or the workshop's local patches.
_Avoid_: stock TopFull (ambiguous between paper quotas and paper images)

**Experiment base**:
The configuration later scenarios are deviations from. After the migration, that base is Ron's setup, not the paper CPU table or 1-replica Boutique.
_Avoid_: default, current cluster, live path (those mix infra leftover with recipe)

### Capacity beliefs

**CPU source of truth**:
The millicores a service is actually allowed to use on the cluster (the live Deployment limit). The Detector's per-service CPU field is a copy of this, not an independent table.
_Avoid_: Detector table, paper CPU table, ResourceQuota (as if any of those were the real limit)

**Detector CPU table**:
The Detector's hardcoded per-service millicores. It is supposed to match the CPU source of truth. On Ron's disk it does not; that mismatch is drift, not a second convention.
_Avoid_: quota overlay, paper quotas (when you mean this field)

**Quota-sync**:
Keeping the Detector CPU table equal to the live Kubernetes limits on every run, not only when a scenario deliberately squeezes one service.
_Avoid_: S3/S4 overlay, `cpu_limit_fraction` (those are scenario knobs, not the sync itself)

**`mu_per_millicore`'s trust boundary**:
A per-service throughput-per-millicore rate frozen at one specific CPU limit (`capacity_frozen.json`). Valid only *at* that same CPU value — checkoutservice's own two-point comparison (50m vs. 1000m) diverged 67×, paymentservice's 37×, both in the same direction, too consistent to be noise. Never extrapolate it to size a different CPU value; only reuse it directly when a scenario caps the service to the exact millicore value it was frozen at.
_Avoid_: "capacity model", "rho estimate" (this is a single frozen rate, not a general queueing model)

### Regimes

**Paper-config regime**:
The 1-replica, paper-quota setup used for `campaign_48/` and the frozen-capacity calibration. Historical once the migration lands.
_Avoid_: baseline, current results (ambiguous with a future Ron-base campaign)

**Ron-config regime**:
The post-migration setup: Ron's setup as experiment base, workshop instrumentation on top, numbers fitted to this project's worker. The next campaign lives here.
_Avoid_: his exact cluster (we cannot grow to his replica/CPU footprint)

**Provisional numbers**:
The millicores and frontend replica ceiling in the migration spec, taken from Ron's January Boutique YAML and trimmed to fit this node, until Ron confirms what was live when TopFull engaged.
_Avoid_: final CPU table, calibrated limits

### Loadgen

**Loadgen shape**:
How Locust tags are grouped into swarms: one independent single-tag swarm per tag (no `@task` weight ever arbitrates between tags) versus a merged swarm where several tags share one pool and weights split it. Ron's `frontend.sh` uses the independent shape; his `online_boutique_create.sh` merges the cart family into one weighted swarm. We adopt the independent shape.
_Avoid_: launcher script, split-cart (both conflate the shape decision with one specific file or one specific tag family)

**Loadgen numbers**:
The actual per-tag user counts and spawn rate. Decided separately from shape. Not copied from either of Ron's scripts — deferred to a fresh calibration pass run under the Ron-config regime, together with the S1–S6 scenario methodology rework. `spawn_rate` is Ron's `RATE` divisor: Locust `-r` = that tag's user count / `spawn_rate`, computed with awk so the result is a float. It is not users/sec. Steady offered load is still about one request per second per user (`constant_throughput(1)`); `-r` only sets the ramp.
_Avoid_: sizing, load level (too vague to mean this specifically)

**Task-weight remix**:
Ron's edited `@task()` values in `locust_online_boutique.py` (postcheckout 500, getcart 100, postcart 1, emptycart 1, getproduct 100, vs. the paper's 50/30/15/15/150). Adopted for fidelity with his tree, but inert under our loadgen shape: no scenario ever merges tags into one swarm where a weight would matter.
_Avoid_: "the mix" (ambiguous with loadgen numbers)

### Targeted-bottleneck sizing

**Bottleneck cap**:
The deliberate CPU limit applied to one Deployment's replicas in Scenarios 3/4A/4B to force it into overload — an absolute millicore value (`cpu_limit_millicores`), not a fraction of that service's normal quota. S3 and S4A use 50m, the one CPU point the recalibration battery actually measured saturation at, since `mu_per_millicore` doesn't extrapolate across CPU values (see Capacity beliefs). S4B constrains `emailservice` at 40m (Checkout-mediated: Frontend → Checkout → Email).
Changed from paymentservice on 2026-10-09; `campaign_48/` S4B runs used paymentservice and are not comparable.
_Avoid_: `cpu_limit_fraction` (superseded for S3/S4A/S4B specifically — still valid elsewhere), "the constraint" alone (ambiguous with `scale_constraints` in general)

**Recalibration battery**:
A coordinated set of live runs used to (re)establish S1–S6's real load numbers under the Ron-config regime. Two distinct halves, different method: the **bottleneck-cap** half (TopFull-off/RetryGuard-off, one run per S3/S4A/S4B target service plus one unconstrained reference run) refreezes `capacity_frozen.json`'s `mu_per_millicore`/`mu_sat`; the **system-load** half (TopFull-on, live dry runs, no model input) sizes S1/S2/S6. Needed again whenever the surrounding cluster's CPU numbers change, even if a target's own cap value (50m) doesn't — the September bottleneck-cap freezes predate the Ron-config regime and are not reusable as-is.
_Avoid_: "the calibration" alone (ambiguous with a single run), "recalibrate" as a synonym for adjusting one number by hand

**System-load calibration**:
The empirical-only half of the recalibration battery, for S1/S2/S6 — no `mu_per_millicore`/`mu_sat` model input exists at full (uncapped) CPU, so sizing is pure live ramp-and-observe: start from the current YAML numbers, run, check against each scenario's target criteria (see RetryGuard-kind overload), adjust, repeat (capped at 3 tries per scenario for a given session). Distinct from bottleneck-cap sizing, which *does* have a trustworthy model input at the one CPU value (50m) it was frozen at.
_Avoid_: "calibration" alone for this half specifically (confusable with the model-based bottleneck-cap half)

**RetryGuard-kind overload**:
A service's live rejection signal (`Δ(5xx+resets)/Δtotal` on `service_inbound.csv`) sustaining above `rejection_threshold` (0.20) for `interval_samples` (30) consecutive 1s samples — i.e. "would trigger `ON→OFF` if RetryGuard were running," checkable on a plain baseline (RetryGuard-off) run without RetryGuard needing to be enabled at all. Distinct from TopFull's own `overloaded` flag (`topfull_throttle_collector.py`'s `utilization > alpha`), which is a different signal on a different cadence — a scenario can trip one without the other.
_Avoid_: "overloaded" alone (ambiguous between this and TopFull's Layer A flag)

**Bottleneck reference load**:
The one Locust load recipe, run with zero `scale_constraints`, used as the shared comparison point for Scenarios 3/4A/4B — sized so each target service would saturate if capped to its bottleneck cap, while every other service stays healthy at that same load with nothing capped. Distinct from Scenario 2's "sustained overload" load (a different scenario, a different load character) and from `condition: baseline` (that's the RetryGuard-off arm, not this).
_Avoid_: "S2's load", "baseline" alone (both already mean something else in this project)

### S2 candidate selection

**Both-off hold**:
A 600 s S2 run with TopFull RL and RetryGuard both disabled, used to judge whether a CPU table plus Locust user mix produces the overload S2 needs before any controller is involved. Scored on the signals the controllers would have used (RetryGuard-kind overload, detector `overloaded`, retry deltas), not on goodput.
_Avoid_: baseline (that means the RetryGuard-off arm with TopFull on)

**Rejection streak**:
The longest run of consecutive 1 s inbound polls on one service where RetryGuard-kind overload's rejection signal is above 0.20, with the last 5 polls dropped. 30 is the RetryGuard bar; 10 or more counts as a real streak because the noise ceiling across valid runs is 8.
_Avoid_: overloaded (that is TopFull's detector flag, a different signal)

**Overloaded tick**:
One detector sample where a service's `overloaded` flag is 1 (`utilization > alpha`). The working cutoff for "overloaded during the run" is 10 ticks. 30 ticks is a lot for this signal. Most hot pairs are either under 10 or at 30 or more.
_Avoid_: rejection streak, RetryGuard-kind overload

**Independent pair**:
Two services that overload on separate call paths and both show a rejection streak of 10 or more and 10 or more overloaded ticks, for example checkout and recommendations. Reflects two separate overloads.
_Avoid_: chain (payment and email arrivals equal checkout arrivals, so they overload with it)

**Chain**:
Checkout plus the downstream services (payment, email) whose arrival rate equals checkout's. Overload shows up in several services but has one root cause. The only place backend-to-backend retries appear.
_Avoid_: independent pair

**Valid sampling**:
A both-off run where `service_inbound.csv` polls are 1 s apart and the collectors span about the 600 s hold. Runs whose inbound polls are mostly 2 s or longer are excluded from S2 candidate ranking, because a 30-sample streak would no longer mean 30 s.
_Avoid_: truncated run (a separate failure: too few rows)

**Blend**:
A both-off hold that clears recommendations (streak and overloaded ticks both at least 10), checkout (same), and at least one leaf service (email or payment, 10 or more overloaded ticks), so it shows the independent pair and a chain service together. A **near-miss** clears exactly two of those three rows and has the missing one at streak or ticks of 5 or more. Retries and goodput do not decide either.
_Avoid_: independent pair (that is only recommendations plus checkout), candidate (nothing is locked)

**Latch**:
Checkout's own completed-request sojourn settling above 500 ms (Istio's perTryTimeout), so its retries multiply its own arrival and pin its CPU; unlatched, the retries land on recommendations instead. The same mix and CPU table has landed on both sides (runs 80 and 84), so treat it as bistable. This is an inference from the raw CSVs, not a demonstrated cause.
_Avoid_: overload (the latch is one mechanism for it)

**Escape time**:
Seconds after the first mesh inbound poll when recommendations arrival first stays above 560 req/s for 5 consecutive 1 s ticks, ending a latch; **never** if it does not within the hold. Scrape holes reset the streak instead of counting as zero. It replaces sticky/released as the primary description of a latch hold: on runs 132–153 every released hold escapes, and sticky and "other" holds are never. Computed by `experiments/s2_latch_escape.py`.
_Avoid_: release time (a hold can release without ever having latched)

**Edge**:
One caller-to-callee pair of Boutique services, for example frontend to recommendationservice. RetryGuard's edge mode keeps retry state per edge: 14 fixed edges between the HTTP/gRPC services, none to `redis-cart` or into `frontend`.
_Avoid_: service (an edge is a pair, a service is one node)

**Retries per request (rpr)**:
On one edge, retries divided by first attempts in a 1 s tick: `Δretry / (Δtotal − Δretry)`, the paper's normalized retry rate. Above the 0.5 threshold for 30 ticks sets that edge OFF. A tick with no first attempts is skipped, it counts as neither high nor low. Meaningless once the edge is OFF, so re-enabling falls back to the callee's rejection rate.
_Avoid_: rejection rate (that is per service, from inbound counts)
