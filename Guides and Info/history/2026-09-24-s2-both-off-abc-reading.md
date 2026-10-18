# Reading (a) / (b) / (c)

Current reading for a hold scored with `experiments/analysis_score.py`. The layout that uses it is [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md).

This file used to define (a) as an inbound rejection streak above 0.20 for 30 samples, for both-off runs 3–7 (2026-09-24). Edge mode replaced that. The shed signal is retries per request on a caller→callee edge. `experiments/s2_both_off_abc.py` still computes the old streak. New guides use the definitions below.

`experiments/rho_estimate_report.py` is retired. It is not part of this reading.

Burst mode (2026-10-12) adds (a2) below. It applies only to holds with `burst_rpr` set.

## (a) Edge shed

RetryGuard sheds an edge to 0 attempts when `rpr > 0.5` (`retries_threshold`) holds for the interval. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge in `service_edges.csv`. A tick with no first attempts is skipped and does not break the streak.

The file streak is seconds from the first consecutive scored tick above 0.5 to the last. One tick is 0 seconds. **Bold** is a file streak of at least 30 seconds. The parenthetical is the controller's max `high` on that edge's `OBSERVE` lines in `retryguard.log`. On holds before the timestamp interval, that counter had to reach 30 samples. On later holds the shed fires when `elapsed_s` reaches 30.

Climb is part of (a). From 0 attempts, 0→1 needs the callee's inbound rejection strictly under 0.10 for the interval. 1→2 needs `rpr ≤ 0.17`. 2→3 needs `rpr ≤ 0.33`. Those two limits are `retries_threshold × attempts / 3`. Between the climb bar and 0.5 the attempt count holds. An em dash means the edge never sat at that attempt count.

The 0.20 rejection streak is printed next to (a). It is not the shed bar. **Bold** there is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. `grpc_4` and `grpc_14` are a separate sum for the four read callees (recommendationservice, productcatalogservice, currencyservice, adservice). They are not in the 0.20 streak numerator.

## (a2) Burst shed (opt-in, 2026-10-12)

Only when the hold's `START` line has `burst_rpr=`. It is a second shed test on the same edge, beside (a), and it does not replace the streak above. The streak asks "was rpr high for the whole interval". Burst asks "did retries pile up in a short window", which is what checkout looks like with TopFull on: per-tick rpr median 0, max 3.7–6.6, longest streak above 0.4 only 8–12 s, so (a) logged zero sheds on `study4_s2_tune_rgtf1_rep1`–`rep4`. Reason and rejected options: [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md).

- **Test.** `ΣΔretry / ΣΔfirst` over a sliding window (5 s of row timestamps) at or above `burst_rpr × attempts / attempts_on`, with at least 20 first attempts in the window. At `burst_rpr` 1.5 the bar is 1.5 at 3 attempts, 1.0 at 2, 0.5 at 1. The floor keeps thin edges from shedding on a handful of requests.
- **Effect.** The edge goes straight to 0 attempts (not one step down). Recovery is the normal path: callee rejection under the re-enable bar for the interval, then the 0→1, 1→2, 2→3 climbs. A burst shed can therefore leave retries off for a long time when rejection stays high.
- **In the logs.** The shed line is `metric=rpr_burst`; `rpr=` on it is the window aggregate and `elapsed_s` is the window span. Every `OBSERVE` line for an edge above 0 attempts carries `burst_rpr5=` (empty when the floor is not met).
- **How to read it.** A burst shed is not evidence that the (a) streak was met. Count the two separately (`ON→OFF burst` in the scorer's count table). The (a) file streak and `high` for the same edge still show why the normal handler stayed quiet. For the effect of the shed, read what follows: attempts after re-enable, time OFF, and the OFF-window rejection rows in the per-callee table, and retry volume (c) on that edge compared with a no-burst hold of the same arm.

### What has happened with burst mode so far

No live burst hold has been run yet (branch `retryguard-burst-mode`; planned: [S2 bar 1.5 plan](../../docs/superpowers/plans/2026-10-12-s2-burst15-holds.md), TopFull off then on). What exists is a replay of the four tuned both-on S2 holds ([2026-10-12-s2-burst-replay.md](2026-10-12-s2-burst-replay.md)): only `frontend → checkoutservice` crosses, first at 104–113 s into the hold, at bars 1.0, 1.5, and 2.0. The volume floor of 20 sits under the 5th percentile of the window sums on every hold (66–84), so it does not blind checkout. The replay assumes the edge stays at 3 attempts, so only the first fire predicts a live run. Fill this subsection with the live shed times, burst counts, and recovery once a hold exists, using [ANALYSIS-TEMPLATE.md](../ANALYSIS-TEMPLATE.md) item 5a.

## (b) Detector overloaded fraction

`topfull_detect.csv` `overloaded=1` ticks over the rows for that service. **Bold** is a share of at least 0.5. That is the detector's CPU-versus-quota call.

Layer A is separate. A live threshold of 10000 is no cap. A live 0 is an empty read. Both stay out of the cap series. With the RL loop off, the threshold stays at 10000, so (b) is the engagement signal that still moves.

## (c) Retry volume

Outbound retry delta is the sum of positive `retry` increments on `service_edges.csv`, reported by target. Inbound resets (`downstream_rq_rx_reset`) are the failures the 5xx+resets rejection rate counts. `grpc_4 / grpc_14` on the four read callees is what their retry policy also counts (`deadline-exceeded` and `unavailable`). Checkout, payment, email, cart, and shipping stay on `5xx,reset,connect-failure`.
