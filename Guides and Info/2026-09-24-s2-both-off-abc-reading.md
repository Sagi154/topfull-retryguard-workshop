# Reading (a) / (b) / (c)

Current reading for a hold scored with `experiments/analysis_score.py`. The layout that uses it is [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md).

This file used to define (a) as an inbound rejection streak above 0.20 for 30 samples, for both-off runs 3–7 (2026-09-24). Edge mode replaced that. The shed signal is retries per request on a caller→callee edge. `experiments/s2_both_off_abc.py` still computes the old streak. New guides use the definitions below.

`experiments/rho_estimate_report.py` is retired. It is not part of this reading.

## (a) Edge shed

RetryGuard sheds an edge to 0 attempts when `rpr > 0.5` (`retries_threshold`) holds for the interval. `rpr = Δretry / (Δtotal − Δretry)` on one caller→callee edge in `service_edges.csv`. A tick with no first attempts is skipped and does not break the streak.

The file streak is seconds from the first consecutive scored tick above 0.5 to the last. One tick is 0 seconds. **Bold** is a file streak of at least 30 seconds. The parenthetical is the controller's max `high` on that edge's `OBSERVE` lines in `retryguard.log`. On holds before the timestamp interval, that counter had to reach 30 samples. On later holds the shed fires when `elapsed_s` reaches 30.

Climb is part of (a). From 0 attempts, 0→1 needs the callee's inbound rejection strictly under 0.10 for the interval. 1→2 needs `rpr ≤ 0.17`. 2→3 needs `rpr ≤ 0.33`. Those two limits are `retries_threshold × attempts / 3`. Between the climb bar and 0.5 the attempt count holds. An em dash means the edge never sat at that attempt count.

The 0.20 rejection streak is printed next to (a). It is not the shed bar. **Bold** there is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain. `grpc_4` and `grpc_14` are a separate sum for the four read callees (recommendationservice, productcatalogservice, currencyservice, adservice). They are not in the 0.20 streak numerator.

## (b) Detector overloaded fraction

`topfull_detect.csv` `overloaded=1` ticks over the rows for that service. **Bold** is a share of at least 0.5. That is the detector's CPU-versus-quota call.

Layer A is separate. A live threshold of 10000 is no cap. A live 0 is an empty read. Both stay out of the cap series. With the RL loop off, the threshold stays at 10000, so (b) is the engagement signal that still moves.

## (c) Retry volume

Outbound retry delta is the sum of positive `retry` increments on `service_edges.csv`, reported by target. Inbound resets (`downstream_rq_rx_reset`) are the failures the 5xx+resets rejection rate counts. `grpc_4 / grpc_14` on the four read callees is what their retry policy also counts (`deadline-exceeded` and `unavailable`). Checkout, payment, email, cart, and shipping stay on `5xx,reset,connect-failure`.
