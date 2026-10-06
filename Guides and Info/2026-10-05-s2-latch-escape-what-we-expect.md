# What the escape-time rescore can tell us

What we expected to learn from the offline plan that re-scores existing S2 latch holds by escape time and reconstructs frontend concurrency from `service_inbound.csv`. No new holds. Written before the script ran; the **Outcome** section below records what the analysis found.

Related: [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md), [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md), [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md), [2026-10-05-s2-latch-escape-time-rescore.md](2026-10-05-s2-latch-escape-time-rescore.md).

Labels below: **(m)** already measured on the v2 CSVs, **(i)** what this analysis could add.

## Outcome (after the analysis ran)

Results: [2026-10-05-s2-latch-escape-time-rescore.md](2026-10-05-s2-latch-escape-time-rescore.md).

- Escape-time scoring agrees with sticky/released on every v2 hold; the three "other" holds are `never`. Latch duration separates early releases from the five late escapes. Sensitivity to 520/560/600 and 3/5/10 s is flat.
- Frontend concurrency by Little's law rises in the last ~30 s before escape, but its pre-escape level does **not** separate escapers from sticky holds (escaped median 279 vs never 327). That is outcome 2 of the three listed below: the proxy does not give a forecasting threshold. A direct queue gauge remains optional confirmation work.

## Short answer

The plan can tell us two things: whether "sticky vs released" describes the system correctly, and whether frontend load is the trigger. Either can come out negative. A negative result is still useful, because it decides whether about 6–8 more holds with a direct queue gauge are worth running.

## Whether sticky/released was the wrong description (step A)

The v2 data already hints that the two-bucket label is coarse (m). Five holds (134, 135, 146, 151, 153) were latched for 45–170 s and then escaped. The old label counts them as "released", the same as holds that never latched.

Scoring by escape time (the first second recommendations arrival stays above 560 req/s for 5 s, or "never") turns that label into a distribution (i). Two shapes would mean different things:

- Escape times spread over the hold. That is a constant hazard: the latch is a random exit over time, not a coin flip decided in the ramp.
- Escape times cluster. That is a deterministic delay in some slow process.

This should also resolve the "other" holds (141, 143, 152). If they come out as "never", they are the same latch as the sticky holds, and the streak ≥ 400 cutoff was a labelling artifact (m that their streaks were cut by a cool blip or a scrape hole; i that they belong with the sticky class).

The old 4 / 5 / 1 split on the 10 untouched controls was about 40% sticky, with a Wilson 95% interval of 0.17–0.69. An escape-time view says more than that: the fraction not yet escaped at 120, 300, and 600 s, and which treatment arms shift the timing even when they do not change the final label. Repeating the cut at 520 and 600 req/s, and at 3 s and 10 s of persistence, says whether 560 req/s is a real feature or a convenient threshold.

## Whether frontend concurrency is a plausible trigger (steps B and C)

Frontend concurrency here is a proxy, not a queue gauge: mean requests in flight from `Δrq_time_sum_ms / 1000 / Δt` on frontend inbound rows (Little's law). Three outcomes:

1. **It leads the escape and separates the classes.** Frontend concurrency rises seconds before recommendations crosses 560 req/s, and a level exists that the escaped holds reach and the sticky holds do not. That names a candidate mechanism: frontend concurrency builds, recommendations starts retrying, checkout is starved, and the latch breaks. The lead time would be a measured number. It would still be a proxy finding, not a confirmed cause.
2. **It does not separate them.** Concurrency looks the same on escaped and sticky holds. The trigger is something else (recommendations pod behavior, retry timing, or a state we do not record).
3. **The proxy is too noisy.** Scrape holes or sampling gaps leave too few clean seconds. The honest result is that a direct gauge (`downstream_rq_active` or a pending gauge on the frontend sidecar) is needed before the trigger question can be answered. That is the decision that would justify new holds.

## What this will not tell us

- It cannot prove causation. Frontend concurrency may rise because recommendations is already storming.
- With about five late escapes, the tests have low power. A positive result is "consistent with", not proven.
- It cannot explain why identical mixes diverge at the start of the hold. That needs a signal at the moment the ramp ends, and no hidden state (pod placement, steal, pod age, hour of day) has correlated with the outcome so far (m).
