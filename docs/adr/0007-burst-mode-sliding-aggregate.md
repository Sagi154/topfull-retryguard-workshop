# Burst mode sheds on a sliding aggregate with a volume floor, not a consecutive streak

RetryGuard's normal handler needs rpr above the bar for 20 s of consecutive ticks. With TopFull on, checkout's per-tick rpr has a median of 0 and a max of 3.7–6.6, and its longest ticks-above-0.4 streak is 8–12 s, so the normal handler never fires (zero toggles on `study4_s2_tune_rgtf1_rep1`–`rep4`). Burst mode adds a second handler per edge: the sum of retries over the sum of first attempts across a sliding 5 s window must reach `burst_rpr × attempts / attempts_on`, with at least 20 first attempts in the window.

**Status:** proposed (see [2026-10-11-retryguard-burst-mode.md](../superpowers/plans/2026-10-11-retryguard-burst-mode.md)).

**Considered options:** a consecutive-5-tick streak above the bar (a zero tick between two bursts resets it, so it would almost never fire at 1.0 or more); fixed non-overlapping 5 s blocks (a burst straddling a boundary is split); an absolute bar at every cap (unreachable at 1 and 2 attempts, where rpr cannot exceed the cap); a burst-specific recovery (declined for now: the normal recovery stays).

**Consequences:** Burst sheds go to 0 attempts and recover through the normal path (rejection under the re-enable bar for 20 s, then the 10 s climbs). Checkout rejection is above 0.2 about half the time, so retries may stay off for a long stretch after a burst shed. That risk is accepted. The volume floor protects thin edges (cartservice) from shedding on a handful of requests. The replay script `experiments/burst_replay.py` estimates fires per hold before any cluster time is spent.
