# Reading S2 criteria (a)/(b)/(c) when TopFull and RetryGuard are both off

Applies to `baseline_no_topfull_sustained_overload` runs 3–7. Source of the three criteria: [2026-09-21-s1-s6-methodology-and-calibration-design.md](../docs/superpowers/specs/2026-09-21-s1-s6-methodology-and-calibration-design.md) §3b (S2 target, lines 105–109).

Both controllers being off is the right place to score the load itself. The three S2 criteria are about whether the traffic would have given RetryGuard and TopFull something to act on, and whether the mesh would have produced a real retry storm. On these runs the controllers do not act, so (a) and (b) are read from the signals they would have used, and (c) is the storm that actually happened.

## (a) RetryGuard-kind overload

RetryGuard disables retries on a controlled service only after that service’s inbound failure fraction, `Δ(5xx + resets) / Δtotal` from `service_inbound.csv`, stays above **0.20 for 30 consecutive 1-second samples**. With RetryGuard off there is no `ON→OFF` line to read. Rebuild that test from the inbound series: for each of the 9 controlled services (`paymentservice` included; `frontend` and `redis-cart` excluded), the longest streak above 0.20, and whether that streak reaches 30. A streak of 30 or more means RetryGuard would have disabled that service during the hold. “Several” of those 9 is the qualitative target, so the comparison across runs is how many services clear 30, and how far the near-misses get.

## (b) TopFull Layer A

Two different signals live in this criterion, and only one of them can move while the RL loop is off. `topfull_detect.csv`’s `overloaded=1` flag is the detector’s own CPU-versus-quota call, and that column is still written on these runs. Count, per service, what fraction of the ~600 one-second ticks are `overloaded=1`, and how many services stay hot for a large share of the hold. That is “would the detector have told Layer A this service is overloaded.”

The other half — admitted rate sitting well below offered rate in `topfull_throttle.csv` — does not appear here: with RL off the Layer A threshold stays at the 10000 passthrough sentinel, so admission does not cut traffic. Confirm that sentinel, then treat the detect-side overloaded fraction as the engagement proxy.

## (c) Retry volume

This one is measured directly. `service_edges.csv` outbound `retry` deltas on the stressed caller→service edges are the actual retry traffic, with neither TopFull shedding load at the proxy nor RetryGuard turning retries off. The bar is a storm on the edges that (a) and (b) say are hot, rather than a handful of retries.

## How to compare runs 3–7

Line the five Locust user counts up against those three pictures and judge which mix looks most overloaded: more services with a ≥30 high-rejection streak, more services overloaded for a large fraction of the 600 seconds, and a larger retry delta on those same edges. Replays of the same counts stay in the comparison, because the note says to judge the candidates against each other.
