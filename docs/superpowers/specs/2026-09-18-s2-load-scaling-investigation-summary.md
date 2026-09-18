# S2 load-scaling investigation — summary (2026-09-18)

## Goal

Under Scenario 2 (Sustained Overload) with the frontend CPU quota doubled to
2000m, push offered load high enough that a backend trips TopFull's
Detector / mesh 5xx appear / RetryGuard has something to react to. The lever
tried throughout: increase Locust user count.

All runs below use `scenario_2_baseline_frontend_2x*.yaml` variants —
frontend `cpu_limit_fraction: 2.0` (2000m), TopFull RL **ON**, RetryGuard
**OFF** (baseline only), 600s hold. Compared against the informal target
"frontend inbound λ leaves the 570–600 band" (the λ observed at 1.0× users).

## What we tried, in order, and what happened

### 1. Frontend 2× CPU quota alone (1.0× users)
- `baseline_frontend_2x_sustained_overload_run1`
- Frontend quota confirmed 2000m; frontend max CPU **~1058m** (well under
  quota, `overloaded=0`); catalog CPU got closer to its 475m gate than the
  paper-quota S2 baseline, but still no backend tripped `overloaded=1`.
- Outbound retries: `Δretry ≈ +3` (near zero).
- **Result: extra frontend headroom alone doesn't create a bottleneck
  elsewhere.**

### 2. + Locust 1.5× / 2× users (`run1`, before the spawn-rate fix)
- `baseline_frontend_2x_users15_sustained_overload_run1`,
  `baseline_frontend_2x_users2_sustained_overload_run1`
- Frontend still under 1600m (1.5× max 959m, 2× max 1143m); catalog closest
  at 2× (435m vs 475m gate) but still no `overloaded=1`.
- Layer A fresh thresholds stayed at the disabled sentinel **10000**.
- **Result: no signal, and it turned out these runs were spawn-capped (see
  below), so they don't even reflect the intended offered load.**

### 3. + Locust 6× users (`run1`)
- `baseline_frontend_2x_users6_sustained_overload_run1` (3720 users, spawn
  540).
- Frontend inbound λ **563.9** — still *below* the 570–600 band despite 6×
  the user count. **λ gate failed.**
- **Result: uniform user-count scaling was not moving the needle at all —
  first sign something structural was capping offered load, not just "not
  enough users yet."**

### 4. Root cause: Locust spawn-rate bug
- Investigated why λ wasn't rising. Found the shared launcher
  `online_boutique_create.sh` computes spawn rate as `-r $((count / RATE))`
  — i.e. it *divides* the user count by the YAML's `spawn_rate` instead of
  using `spawn_rate` directly. Scaling `user_counts` and `spawn_rate`
  together left the actual Locust `-r` (users spawned/sec) roughly flat, so
  higher-count runs took far longer to ramp and often never reached target
  population within the 600s hold.
- Fix: added a **probe-only** launcher,
  `experiments/loadgen/online_boutique_create_probe.sh` (uses `-r $RATE`
  directly). Did **not** touch the shared launcher (would affect S1–S6 for
  the whole team) — this was a deliberate scope decision.
- Spec: `docs/superpowers/specs/2026-09-18-locust-spawn-rate-fix.md`.

### 5. Re-ran 1.5× / 2× with the fixed probe launcher (`run2`)
- `baseline_frontend_2x_users15_sustained_overload_run2`,
  `baseline_frontend_2x_users2_sustained_overload_run2`
- Ramp-up confirmed fast (~3s to target population) — the spawn fix worked
  as intended.
- But frontend inbound λ: **529** (1.5×) / **490** (2×) — *still below* the
  570–600 band, and actually **lower** than the 1.0× run's λ of 591.
  **λ gate failed again, worse than before.**
- Frontend `W` (mean sojourn time) rose alongside: 721ms (1.5×) → 816ms
  (2×). CPU stayed under quota (993m / 1027m of 2000m). Catalog `ov=0`.
  Outbound retries near zero (0 / +34).
- **Result: fixing the ramp-up bug did not fix the underlying problem.**
  Skipped the planned 3× run per the λ gate (no point burning VM time on a
  lever that's already going the wrong direction).

### 6. Root-cause hypothesis: closed-loop load model
- Locust's `wait_time` for this locustfile is `constant_throughput(1)`: each
  simulated user tries to do exactly 1 request/sec; if a request takes
  longer than 1 second, the wait collapses to zero and that user just runs
  requests back-to-back instead of going faster. This is a **closed-loop**
  model — more users doesn't necessarily mean more concurrent load if
  latency is rising, because each user is still capped near 1 req/sec.
- Correlated with the data: frontend `W`/P95 rose across the 1.0×→1.5×→2×
  series while λ fell. Frontend CPU never got close to its quota, so the
  frontend itself isn't CPU-bottlenecked — some other fixed capacity
  (connection pool, `GOMAXPROCS`, downstream latency) is capping how fast it
  can serve, and Locust's closed loop translates that latency directly into
  a throughput ceiling instead of piling up queue depth.
- At this point there were two candidate explanations left un-disambiguated:
  (a) the closed-loop Locust model itself, or (b) the `topfull-load` VM
  simply running out of its own CPU as more Locust processes were spawned
  (never directly measured before this).

### 7. Loadgen CPU diagnostic (`run3`)
- Re-ran the 2× probe (`baseline_frontend_2x_users2_sustained_overload_run3`)
  while independently sampling `topfull-load`'s own `/proc/stat` over SSH
  at 1s resolution for the full 600s hold, plus one mid-run `top`/`ps`
  snapshot.
- **Result: `topfull-load` was not the bottleneck.** Mean busy CPU **18.1%**
  (median 17.8%, max 40.8% for one brief spike, otherwise steady ~17%) on an
  8-vCPU machine running 46 Locust processes; `top` showed 89% idle,
  loadavg 1.35, hottest single Locust process ~21% of one core.
- Same run's λ was **460** (even lower than run2's 490); frontend `W`
  **918ms**; frontend CPU max **981m**; Layer A thresholds stayed **10000**;
  frontend→recommendation `Δretry` **+43275** (retries fired, but that's a
  side effect of rising latency + Istio's default retry policy, not
  evidence of a resolved bottleneck).
- **This closes candidate (b).** The load generator has plenty of headroom;
  it is not why λ is flat/falling. Candidate (a) — Locust's closed-loop
  `constant_throughput(1)` interacting with rising frontend/downstream
  latency — is the only explanation still standing, but it has not been
  independently proven, only correlated.

### 8. Frontend sidecar (`istio-proxy`) CPU check (live burst, 2026-09-18)
- Motivation: the "frontend CPU max ~1000m of 2000m — plenty of headroom"
  claims in this investigation only ever measured the **app container**.
  `resource_usage_collector.py` hardcodes
  `SKIP_CONTAINER_NAMES = {"istio-proxy", "POD"}`, so Envoy sidecar CPU
  was never in `resource_usage.csv`. This is a different machine and a
  different resource than the loadgen check in §7 (`topfull-load`
  `/proc/stat` vs `istio-proxy` inside Boutique pods on
  `topfull-worker-1`).
- Method: VMs were `TERMINATED`; started them, refreshed SSH `HostName`,
  confirmed nodes Ready and all Boutique pods `2/2 Running`. `kubectl top`
  was unavailable (metrics-server still coming up), so CPU came from
  kubelet `stats/summary` (`usageNanoCores`) via
  `/api/v1/nodes/topfull-worker1/proxy/stats/summary`. Idle snapshot
  first, then a ~25 s concurrent `curl` burst from master at the frontend
  ClusterIP (`http://10.111.112.191/`, 60 in-flight requests per batch).
  Not a Locust/S2 scenario run — isolates sidecar vs app on one hop.
- Sidecar quota on the live frontend pod: request **100m**, limit **2000m**
  (`cpu: "2"`). App-container quota is a separate cgroup; saturating the
  sidecar would not show up as the frontend server hitting 2000m.
- Idle (no Locust): frontend `server` **0.2m**, `istio-proxy` **2.7m**.
  Warm single-request latency after the first cold hit (~765 ms) was
  **31–45 ms**.
- Under the burst (two independent samples, ~2200 logged responses in the
  first successful burst):

  | container | idle | burst sample 1 | burst sample 2 |
  |---|---|---|---|
  | frontend `server` | 0.2m | **592.5m** | **614.9m** |
  | frontend `istio-proxy` | 2.6–2.7m | **558.0m** | **575.4m** |
  | worker node total | — | — | **3497m** of 16000m allocatable |

- **Result: the sidecar CPU tax is real and roughly 1:1 with the app on
  this hop.** App-container headroom is not the full picture; every
  request also pays Envoy CPU that our collector never recorded. The
  sidecar itself was **not** saturating here (575m of a 2000m limit).
  Node CPU was **~22%** of 16 vCPU, so this isolated frontend-only burst
  also does **not** show node-level contention as the limiter.
- What this does **not** close: why λ *fell* as Locust user count rose in
  the frontend-2× probes. A full Boutique page load fans out across
  several backend hops, each with its own sidecar tax, which can still
  add wall-clock `W` without any one container hitting its quota. That
  still feeds candidate (a) (closed-loop `constant_throughput(1)`), which
  remains unproven. This check only shows that "the app has CPU headroom"
  was an incomplete measurement, not that the sidecar was the bottleneck
  on this cluster.

## Current state (end of this investigation)

- Uniform Locust user-count scaling under S2 frontend-2× is a **closed
  lever** — confirmed dead after the spawn-rate fix, the loadgen-CPU
  check, and the sidecar CPU check. Do not add more users or more loadgen
  VMs to try to raise S2 load further. The Envoy sidecar is a real
  per-request CPU cost (~1:1 with the frontend app under a curl burst)
  that `resource_usage.csv` never recorded, but it was not saturating in
  the live check (sidecar ~575m of 2000m; worker ~3.5 / 16 cores).
- No backend has tripped `overloaded=1` in any of these probes; TopFull
  Layer A thresholds stayed at the disabled sentinel (10000) throughout.
- RetryGuard was never enabled in any of these probes (baseline-only) — this
  investigation is upstream of the RetryGuard question; it's about whether
  we can generate a genuine S2 overload signal at all via user-count scaling.
- All probe folders are preserved under
  `experiments/results/campaign_48/S2_sustained_overload/` and are excluded
  from overwrite in `AGENTS.md` §4 ("Not done yet" callout).
- Related specs: `2026-09-17-s2-frontend-2x-quota-design.md`,
  `2026-09-17-s2-frontend-2x-user-scale-design.md`,
  `2026-09-18-locust-spawn-rate-fix.md`.

## What to check next, and why

1. **Get a team decision on changing Locust's `wait_time`.** This is the
   single highest-value next step: it directly tests the standing
   hypothesis (closed-loop throttling) rather than continuing to correlate
   around it. Options to bring to the team: switch to `between(a, b)` (open
   waiting, not throughput-locked) or a fixed-rate/Poisson generator. This
   has been flagged as **out of scope for solo agent action** in multiple
   prior specs (`AGENTS.md`: "team-discussion only, do not change load-gen
   without a separate decision") because it would change the load model for
   every scenario (S1–S6), not just this S2 probe — a decision with
   cross-cutting consequences that shouldn't be made unilaterally.
   - *Why this first:* it's the only remaining candidate cause that hasn't
     been tested, and every other lever (frontend quota, user count, spawn
     rate, loadgen CPU, frontend sidecar CPU) has now been ruled out or
     exhausted as *the* limiter. Sidecar CPU is a real uncounted tax, but
     was not saturating in the live burst.

2. **If `wait_time` is off the table, try a mix reweight instead of a
   uniform user-count bump.** Increase only the heaviest/most latency-sensitive
   endpoint's user count (e.g. `getcart`/`getproduct`) rather than scaling
   all five endpoints uniformly, since uniform scaling may just be
   spreading the same aggregate closed-loop ceiling across more users
   without changing per-endpoint pressure.
   - *Why:* cheaper to test than a load-model change, no team decision
     needed (each scenario YAML already parameterizes `user_counts` per
     endpoint independently), and it directly probes whether the ceiling is
     endpoint-specific or genuinely aggregate.

3. **Try TopFull-off S2 at 2× users** (there's already a precedent:
   `scenario_2_baseline_no_topfull.yaml` from the 2026-09-15 TopFull-off
   control experiment). If λ still doesn't rise with TopFull removed, that
   would independently confirm the ceiling is in the load generator/frontend
   path, not in TopFull's admission control — further narrowing the
   diagnosis without touching Locust's wait model.
   - *Why:* isolates one more variable (TopFull's own throttling) cheaply,
     reusing an existing YAML instead of building something new.

4. **Only after 1–3, if the goal is still "make S2 overload for RetryGuard
   evaluation":** fall back to the S3 path, which is already known to work.
   Scenario 3 (targeted-bottleneck at `checkoutservice`, `cpu_limit_fraction:
   0.1`) has repeatedly produced real RetryGuard `ON→OFF`/`OFF→ON` toggles
   (`S3 run7/run8/run9`, `run9`), whereas S2 has never produced a single
   toggle under live TopFull across a dozen+ variants. If S2 remains
   unmovable after the above, S3 is the scenario that actually answers the
   "does RetryGuard help" question with live data today.
   - *Why last:* it doesn't fix S2, but it means the overall project isn't
     blocked on solving this specific lever — there's already a working
     scenario to build the Phase 7 RetryGuard narrative around while S2 is
     revisited later with a team decision.

## Explicitly not recommended

- **Do not** add more Locust users, more `user_counts`, or spin up
  additional loadgen VMs under the current `constant_throughput(1)` model —
  three separate probes (1.5×, 2×, 6×), a loadgen-CPU check, and a
  frontend sidecar-CPU check have already shown this doesn't move λ.
  The loadgen VM has 80%+ headroom, the frontend sidecar was ~575m of
  2000m under a curl burst, and the worker was ~22% busy, so "more
  capacity" isn't the constraint being tested.
- **Do not** edit the shared `online_boutique_create.sh` launcher to fix the
  spawn-rate bug for every scenario without a team decision — it's a global
  change affecting S1–S6 and all teammates' configs, and the probe-only
  launcher already isolates the fix for this investigation.
