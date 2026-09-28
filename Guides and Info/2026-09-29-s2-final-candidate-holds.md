# S2 final-candidate holds: CPU tables and user-count mixes

Proposal for the next both-off series. The current best holds are run 6 (Paper), run 42 (Checkout-3), and run 43 (Checkout-4). This file turns those three, plus the load model in the calibration spec, into eight holds in three rounds, then adds one more mix (300 / 200 / 200 / 10 / 10) on three tables. Round 0 is a ceiling check that runs with them and does not gate them. Nothing here has been run.

Sources: [2026-09-29-s2-abc-runs-6-42-43-54.md](2026-09-29-s2-abc-runs-6-42-43-54.md), [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md) ("Runs 30–56"), [2026-09-22-locust-api-to-boutique-service-mapping.md](../docs/superpowers/specs/2026-09-22-locust-api-to-boutique-service-mapping.md), [LOCUST-API-PATHS.md](LOCUST-API-PATHS.md). How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md). CPU tables: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).

Runs 58–59 add one fact that changes how a failed replica gate is read. The payment readiness probe is `grpc_health_probe` with a 1 s timeout, so a leaf pegged at its CPU cap drops out of Ready while the process is still running. That is why the replica gates keep failing on leaves. Write-up: [2026-09-28-s2-recs3-cpu-runs-58-59.md](2026-09-28-s2-recs3-cpu-runs-58-59.md).

Counts below are getproduct / postcheckout / getcart / postcart / emptycart. Holds are 600 s, both controllers off, `spawn_rate` 50, 360 s cool-off between holds.

## What separates run 6 from runs 42 and 43

| | Run 6 (Paper) | Runs 42 / 43 (Checkout-3 / Checkout-4) |
|---|---|---|
| Hot services | checkout + recommendations (independent) | checkout + payment + email (one call chain) |
| Why | checkout at 615 m × 1 gets hot near 41 req/s, and it saw 59; recommendations at 1150 m × 1 gets hot near 560 req/s, and it saw 592 | checkout has 2,400–3,200 m, so it needs about 225 req/s of checkout traffic before it saturates |
| Cost | a latched checkout starves email (email arrival 15 req/s), so the leaves stay cold | `postcheckout` 250 eats the ~600 req/s storefront ceiling, so browse cannot heat recommendations |
| Weakness | never replayed; earlier same-count replays (run 3 vs run 5, run 4 vs run 7) diverged | run 42's email streak is 29, one short of 30; run 43 failed the replica gate |

The load model predicts run 6's two hot services from those quotas and arrivals, so the tables below are built from it.

Checkout costs about 12 millicores per admitted req/s, roughly 7× the next backend. Recommendations on one pod tops out near 1,000–1,100 m whatever its quota, so replicas, not millicores, are what stop its retry storm. Total achieved Locust load caps near 600 req/s on every table tried so far; raising the configured user sum past about 650 buys a different split, not more load.

## Round 0 — where the ~600 req/s ceiling sits

Round 0 does not gate rounds A–D. Those holds run either way. It names the limiter behind the ~600 req/s cap so a later mix is read against the right one.

Two places are already ruled out. Frontend app CPU sits at 20–30% of quota on the holds that hit the ceiling, so the app-container limit is not it. On run 51 every tag achieved about 0.70–0.72 of its configured users, including `emptycart` at a P95 of 53 ms (144 req/s from 200 users). `constant_throughput(1)` misses one request per second per user only when the request itself lasts longer than a second, so those missing requests were never sent. A sidecar or frontend queue would have shown up in `Latency95`. `resource_usage.csv` cannot settle the sidecar on its own: `resource_usage_collector.py` skips the `istio-proxy` container.

### Snapshot, during the first 600 s hold

Take this about two minutes into whichever hold runs first. It needs no extra hold.

1. **Did the users start?** On `topfull-load`, read each tag's Locust stats port (8888–8930). Compare `user_count` with the configured count, and read `total_rps / user_count`. A `user_count` below the configured count means the ramp (`-r = count / 50`) never finished. A matching `user_count` with a ratio near 0.7 on a fast tag means the users are up and are not woken once a second.
2. **Is the load generator out of CPU?** Per-process CPU of the five Locust processes, and idle CPU on `topfull-load`. One process near a full core with a low ratio means gevent is missing the `constant_throughput` wakeups. A mostly idle VM means the generator is not the limit.
3. **Is the sidecar busy?** On `topfull-master`, `kubectl top pod --containers` for `istio-proxy` on the frontend pods. High proxy CPU accounts for the ceiling only together with `emptycart` latency that rises with it. Flat `emptycart` latency means the proxy is busy on the slow tags.

### Short holds, only if the snapshot does not separate the causes

Both controllers off, 180 s so the ~50 s ramp is over before the reading, 120 s cool-off. Skip these when the snapshot already names the limiter. They still do not block A–D.

| Hold | Mix | Reading |
|---|---|---|
| E1 | `emptycart` only, three holds: 200, then 400, then 600 | Reaching about 1 req/s per user at a P95 of a few tens of ms means one swarm is not capped at 600. Capping well below 600 at a flat P95 pins it on one Locust process, and E2 is unnecessary. |
| E2 | run 52's mix, 200 / 250 / 200 / 200 / 200 | If `emptycart` falls to about 0.7 of its users while its P95 stays flat, the five swarms are contending on the load VM. If its P95 rises into the hundreds of ms, the shared path (frontend, sidecar, or the node) is the limit, and the sidecar number from the snapshot says which. |

## Round A — replay the three candidates (3 holds)

| Hold | Table | Mix | Question |
|---|---|---|---|
| A1 | Paper, sidecar request 90 m | 340 / 100 / 240 / 10 / 10 | Does run 6's double-clear reproduce? Highest priority. |
| A2 | Checkout-3, sidecar request 100 m | 150 / 250 / 150 / 20 / 20 | Does run 42 reproduce? |
| A3 | Checkout-3 with email 180 m and redis-cart 320 m (total stays 12,950 m) | 150 / 250 / 150 / 20 / 20 | Does the email trim push its streak past 30? |

A3 is the edit already suggested in the calibration spec. It is a prediction from run 42's one-sample near-miss, not a measured result.

## Round B — separate the table from the mix (2 holds)

Runs 42 and 43 differ in both the table (checkout 3 vs 4 replicas, recommendations 3 vs 2) and the mix. The other two cells of that 2×2:

| Hold | Table | Mix |
|---|---|---|
| B1 | Checkout-3 | 200 / 250 / 200 / 50 / 50 |
| B2 | Checkout-4 | 150 / 250 / 150 / 20 / 20 |

If the checkout + payment + email result follows the mix, keep Checkout-3. If it follows the table, keep Checkout-4.

## Round C — hybrid table, independent pair plus leaves (3 holds)

Keep recommendations at the paper shape (1150 m × 1) so it can go hot. Give checkout 800 m × 2, which goes hot near 107 req/s. Keep the leaves at 200 m. Everything else stays on the Checkout-3 limits. Deployment total is 10,900 m, under the paper ceiling of 13,360 m.

| Service | Quota | Replicas |
|---|---:|---:|
| frontend | 1150 | 4 |
| checkoutservice | 800 | 2 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 600 | 1 |
| cartservice | 600 | 1 |
| currencyservice | 650 | 1 |
| shippingservice | 400 | 1 |
| adservice | 600 | 1 |
| paymentservice | 200 | 1 |
| emailservice | 200 | 1 |
| redis-cart | 300 | 1 |

Sidecar request 100 m, no CPU limit, matching Checkout-3. This table has fewer backend pods than Checkout-3 (checkout 2, recommendations 1), so the fourth frontend pod has more room than it did on Checkout-3.

Recommendations load is `getproduct + getcart + postcheckout`, so a high `postcheckout` heats checkout and recommendations together. `postcart` and `emptycart` stay at 10 so they do not consume the 600 req/s ceiling.

| Hold | Mix | What it probes |
|---|---|---|
| C1 | 270 / 200 / 280 / 10 / 10 | expected achieved rates near 150 / 225 / 190 |
| C2 | 200 / 250 / 250 / 10 / 10 | shifts load toward checkout; probes the recommendations-storm vs checkout-latch trade-off |
| C3 | replay of the better of C1 and C2 | reproducibility |

The main risk is that a recommendations storm and a latched checkout rarely coincide: 10 of 11 holds in runs 30–56 had one or the other. Run 6 is the counterexample, and its checkout quota (615 m × 1) was much tighter than 800 m × 2.

The C mixes come from the coefficient model. They are not measured holds, and this table's pod fit and scenario config have not been checked.

## Round D — mix 300 / 200 / 200 / 10 / 10 on three tables

Configured sum is 720, just over the ~650 point where the storefront stops gaining total throughput. The closest measured hold is run 38 (250 / 150 / 250 / 50 / 50, sum 750, Replica table): achieved about 170 / 105 / 175, sum 519, checkout unlatched so its arrival equalled postcheckout. This mix raises postcheckout by 50 users, raises getproduct by 50, and drops getcart by 50 relative to a 250 / 150 / 250 browse pair, with the fast cart tags at 10. Unlatched, a reasonable expectation is postcheckout around 130–150 req/s and recommendations around 470–520, because recommendations tracks getproduct + getcart + postcheckout and those three tags still sum to 700 users. A latch would multiply checkout's arrival by about 2–3× and can cut email well below postcheckout.

Swapping 50 users from getcart to getproduct does not change the table choice. Checkout, payment, and email track postcheckout, which stays at 200. Recommendations tracks the sum of the two browse tags plus postcheckout, which stays at 700. The swap moves load onto adservice (getproduct only) and off the cart-page shipping quote (getcart only). Both sit far under their quotas at this load: ads goes hot near 1,000 req/s on 600 m, shipping near 970 req/s on 400 m.

| Hold | Table | Why this table, for this mix |
|---|---|---|
| D1 | Hybrid (Round C), sidecar 100 m | Best fit. Checkout at 800 m × 2 goes hot near 107 req/s, and 130–150 arrives even before a latch. Recommendations at 1150 m × 1 goes hot near 560 and saw 592 on run 6; 470–520 sits just under that, so (a) and (b) on recommendations are a near-miss risk, not a sure clear. Email at 200 m goes hot near 100 req/s, so an unlatched ~140 should put it over the detector line (run 42's email cleared (b) at 162). |
| D2 | Paper, sidecar 90 m | Run 6's table with postcheckout doubled (100 → 200) and the browse sum lowered (340 + 240 → 300 + 200). Checkout at 615 m × 1 cannot absorb 130 req/s, so it should latch. Recommendations falls from run 6's 592 toward ~500, which can drop it off the bar run 6 cleared. Answers whether the extra postcheckout keeps the independent pair or only deepens the checkout latch. |
| D3 | Checkout-3, sidecar 100 m | Chain comparison at a lower postcheckout than run 42 (200 vs 250). Checkout at 800 m × 3 goes hot near 160, so 130–150 unlatched is under the line and a latch is what makes it hot. Recommendations at 800 m × 3 stays cold (around 30% of quota at ~500 req/s). Email at 200 m is the service most likely to clear if checkout does not latch. |

D1 is the one to keep if only one of these three is run. D2 is the second. D3 is the chain control.

Checkout-4, Agreed, Replica, Pay-250, and Recs-3 are worse fits for this mix:

- Checkout-4 gives checkout 3,200 m, so 130–150 req/s is about half a quota and the service stays cool unless it latches. Recommendations at 800 m × 2 retries (runs 44–46) but its CPU stays near half of quota, under the 0.8 detector line.
- Agreed gives recommendations 2,000 m on one pod. That pod still tops out near 1,100 m, so detector utilization stays near 0.5 and (b) cannot fire.
- Replica matches the hybrid on checkout (800 m × 2) but puts recommendations on 800 m × 3, where it stays cold, and splits email across 150 m × 2, which holds a ~140 req/s leaf under the 0.8 line.
- Pay-250 and Recs-3 raise the leaves to 250 m (email then needs ~125 req/s, payment ~225) and do not put recommendations on a single ~1,150 m pod.

On the hybrid table this mix is close to C1 (270 / 200 / 280 / 10 / 10). Postcheckout is the same. The recommendations feeder sum is 700 users here and 750 on C1, so C1 pushes recommendations harder toward run 6's 592. Running both is a two-point probe of that edge. Running this mix on Paper as well is what C1 does not cover.

## How to pick

Take the candidate that clears (a) on at least 2 controlled services, (b) on at least 2 services, and (c) with tens of thousands of retries, in at least 2 of its replays.

Prefer an independent pair (checkout + recommendations) over the checkout + payment + email chain when both reproduce. The chain is one PlaceOrder path; the pair is two services deciding on their own.

Keep each existing table's sidecar setting: 90 m on Paper, 100 m on Checkout-3 and Checkout-4.

Leave Pay-250 and Recs-3 (run 54) out of this series. Pay-250 did not reproduce run 43, and run 54 is a single hold whose neighbouring mixes on the same table split between latched and unlatched.

On any replica-gate failure, capture pod events before treating it as an infrastructure fault. The runs 58–59 note says a pegged leaf drops Ready on the 1 s health probe while the process keeps running.

## Cost

The Round 0 snapshot is taken inside the first 600 s hold, so it adds no cluster time. E1 and E2 add about 15 minutes, and only when the snapshot does not already name the limiter. Eight holds (rounds A–C) at 600 s plus 360 s cool-offs is about 2 hours 10 minutes of cluster time, plus the cool-off before the first hold. Round D adds three holds, about 50 minutes more, for about 3 hours in total. Round 0 does not change that schedule.

## Related

- Scorecard of the four reference holds: [2026-09-29-s2-abc-runs-6-42-43-54.md](2026-09-29-s2-abc-runs-6-42-43-54.md).
- Load model, latch groups, and the email-180 suggestion: [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md), section "Runs 30–56".
- Per-tag to service coefficients: [2026-09-22-locust-api-to-boutique-service-mapping.md](../docs/superpowers/specs/2026-09-22-locust-api-to-boutique-service-mapping.md).
- Call graph those coefficients count: [LOCUST-API-PATHS.md](LOCUST-API-PATHS.md).
