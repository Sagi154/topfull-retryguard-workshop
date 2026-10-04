# S2 checkout latch

How the checkout latch works on the Paper-C1 mixes of runs 86, 89, and 105, and on their replays. Both-off holds, 600 s, `spawn_rate` 50 unless a later probe changed it. Paper-C1 is frontend 1150 m × 4, checkout 800 m × 1, recommendations 1150 m × 1, sidecar request 100 m with no CPU limit. Istio retries are `attempts: 3` and `perTryTimeout: 500ms`.

Related tables: [2026-10-03-s2-paper-c1-runs-99-107.md](2026-10-03-s2-paper-c1-runs-99-107.md), [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md), [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md). The earlier mechanism write-up for runs 26–29 is the "checkout retry-latching mechanism" section of [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md).

Labels: **(m)** measured on the CSVs or taken from those guides, **(i)** inference built on those measurements.

## Short answer

The latch is a timeout-retry loop at checkout. It competes with a recommendations retry storm for the same Locust users. Whichever loop takes hold during the ramp usually stays for the rest of the hold. The same user-count mix and the same CPU table can land in either state.

## What a latched hold looks like (m)

Runs 94–96, 100, 102–104, 106, and 107, and the same shape on runs 26–29:

- Checkout inbound is about 148–160 req/s, failure about 0.53–0.57, mean sojourn 501–502 ms. About 91–95% of requests take longer than 500 ms. CPU sits near 0.88 of the 800 m quota and peaks at 1.00.
- Frontend → checkout retries are 53k–63k (run 100 is 62,775; run 106 is 58,302).
- Recommendations stays at about 357–420 req/s, sojourn 66–99 ms, failure 0, CPU max 0.70–0.74 of 1150 m, and zero retries.
- Frontend sojourn is about 260–300 ms and frontend CPU is about 0.3 of quota. getproduct goodput is about 264 req/s with 0 failures.
- On runs 26–29 a latched checkout admits 2.3–3× its first-attempt rate. Run 29 latched with configured `postcheckout` of 50, so the loop holds on a small input once it has started.

## What a blend looks like (m)

Runs 86, 88, 89, 92, 97, and 105:

- Recommendations is about 560–630 req/s, sojourn 430–464 ms, failure 0.23–0.30, CPU pegged at 1150 m. Frontend → recommendations retries are 217k–238k.
- Frontend sojourn is about 820–880 ms. getproduct goodput falls to 26–75 req/s. Total frontend rate falls to about 360 req/s, against about 440 req/s on a latched hold.
- Checkout arrival is only 10–36 req/s and sojourn is 200–280 ms. That input is too small to keep the checkout loop going.

Minute traces from `service_inbound.csv`:

- Run 105 (blend). In minute 2 checkout hit 110 req/s, failure 0.39, sojourn 410 ms. Recommendations then went from 492 to 787–810 req/s with sojourn about 500 ms. Checkout fell to 4–28 req/s, sojourn about 50 ms, and stayed there.
- Run 106 (same mix, latched). Checkout went to 138 then 148 req/s with sojourn 501 ms from minute 2 through the end. Recommendations stayed near 420 req/s with sojourn 91 ms.
- Run 101 (late switch). Checkout stayed latched for minutes 2–7 (about 158 req/s, sojourn 501 ms). At minute 8 checkout fell to 51 req/s and sojourn 284 ms, and recommendations jumped from 422 to 687 req/s with sojourn 406 ms.

## How the loop closes (m for the numbers, i for the causal steps)

1. During the ramp, checkout's admitted rate reaches the 800 m cap at about 110–150 req/s. Completed-request sojourn lands on the 500 ms `perTryTimeout`.
2. About half of the attempts time out and are counted as resets. Each uses one of the three Istio attempts, so frontend → checkout traffic is multiplied about 3×.
3. That retry volume keeps checkout's CPU pegged, which keeps sojourn at 500 ms, which keeps the retries coming.
4. Mean sojourn stays near 500 ms for the rest of the hold. The loop is stable at that sojourn.

Recommendations is cold while this is running because its load is first-attempt traffic (getproduct + getcart + the confirmation page), about 360–420 req/s. That is about 60–70% of one 1150 m pod. With no retries, sojourn stays at 66–99 ms and recommendations never starts its own loop. Checkout's retries add work on the frontend, and frontend CPU is only about 0.3 of quota, so they do not push recommendations over its trip point.

## Why the two states exclude each other (i)

Both states are self-sustaining loops with a threshold. They share one pool of Locust users (`constant_throughput(1)` per user).

- In the recommendations storm, a page that calls recommendations can take about 1.5 s (up to 3 attempts × 500 ms). The closed loop spends its users waiting. Browse goodput falls (getproduct 26–75 req/s against 264 req/s on a latch), and postcheckout's offered rate falls with it. Checkout's first-attempt input drops below the level that keeps its own loop alive. That is the shape of run 105: checkout went from 110 req/s to 5–28 req/s and stayed there.
- In the latch, checkout burns frontend time on postcheckout (goodput about 3 req/s) while browse stays fast. Recommendations stays under its trip point, near 360–420 req/s.
- A full recommendations storm and a full checkout latch at the same time is unstable. Blends such as run 89 show checkout's overload as intermittent episodes (164 overloaded ticks, streak 58) beside a full recommendations storm.

A late switch from checkout to recommendations does happen (runs 99 and 101). Run 91 is a checkout-only hold after blends, so the latch can reappear after a recommendations hold.

## What tips a hold (m for the times, i for the race)

Checkout trips first on every one of these holds, at about 116–155 s (first 5 consecutive inbound samples with failure above 0.20).

- On a blend, recommendations trips 10–50 s later: run 97 at 151 s, run 105 at 173 s, run 88 at 136 s, run 92 at 151 s, run 93 at 134 s. Checkout's high-failure share for the rest of the hold is then only 0.03–0.17.
- On a latched hold, recommendations never trips, and checkout's share is 0.78–0.83.
- Late switches: recommendations tripped at 418 s on run 99 and at 504 s on run 101, after checkout had already been latched for minutes.

The inferred race: a blend needs recommendations to cross about 560–620 req/s inside that short window, before checkout's loop is self-sustaining. The latched runs never give recommendations that push.

Holds of the same mix cluster in time (94–96 latch, 102–104 latch, 106–107 latch) (m). Carry-over from the previous hold (pod warmth, throttling history, JIT) is a possible cause and was not established by the CSVs available when this was written. Cool-off was a fixed 360 s.

The same mix on the original VMs and on the disk copy landed differently: 275/80/100/90/5 was a blend on runs 86 and 88 and a three-run latch on runs 102–104. Inside a mode the two clusters match. That comparison is [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md).

## Levers, as ranked before the probe (i, untested at the time)

Each one needs at least three replays of one mix.

1. Push recommendations harder: cut its CPU (1150 m → about 950 m) or add 10–15% getproduct and getcart users, so it reaches about 600 req/s inside checkout's window. Risk: earlier holds showed a higher recommendations arrival rate did not always produce a streak.
2. Give checkout a little more room: 800 m → 900–1000 m, or fewer postcheckout users, so its sojourn stays under 500 ms. Too much room drops the hold into a recommendations-only near-miss like run 98 (checkout streak 0, overloaded 24 ticks). The blend bar still needs checkout streak ≥ 10 and overloaded ticks ≥ 10.
3. Raise `perTryTimeout` to 600–700 ms. The latch sits on the 500 ms value. This changes both arms of any later comparison.
4. Change `spawn_rate` (the base is 50) or add a warm-up. The race is decided in the ramp. The direction of the effect was unknown.
5. Restart the checkout and recommendations pods before each hold, alternating with holds that do not restart, to test carry-over.
6. Change the frontend replica count. Ranked below the others: frontend failure on these holds follows recommendations' state.
7. Interleave mixes. Three identical holds in a row (94–96, 102–104) let one cluster state dominate a block of results.

The first experiment proposed here was levers 1 and 5 together: a 10% recommendations CPU cut plus a pod restart before each hold, on 275/85/100/90/5, against the 1-of-3 baseline of runs 105–107.

## What the latch probe later measured

Runs 108–126 tested several of those levers on the run 89 mix. Scores and the per-lever verdicts are in [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md).

- Checkout at 2 × 800 m, checkout at 1000 m × 1, and the pair of checkout × 2 plus postcheckout 120 all avoided the latch on both holds. Checkout sojourn on those holds stayed under 500 ms (71–235 ms).
- getproduct 310 and `spawn_rate` 10 each moved the outcome on both holds. Both `spawn_rate` 10 holds were released blends.
- A recommendations CPU cut to 1000 m, postcheckout 120, and a pod restart were mixed: one hold each way.
- A restart does not explain the original-vs-copy difference. Run 108 (restart) was released; run 124 (restart) was sticky.
- Checkout sojourn in the 90–150 s window does not separate sticky from released across runs 86–126. The two ranges overlap. The "sojourn already above 500 ms in that window predicts a sticky hold" check from the replays-differ note is refuted for that window. Hold-mean sojourn near 501 ms remains the signature of a hold that stayed latched.
