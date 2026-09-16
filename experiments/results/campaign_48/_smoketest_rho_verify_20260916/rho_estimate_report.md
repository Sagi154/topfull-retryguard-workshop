# rho / mu.hat estimate report — `_smoketest_rho_verify_20260916`

Generated: 2026-09-16T19:40:22Z
Run folder: `experiments\results\campaign_48\_smoketest_rho_verify_20260916`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w   rho_w      mu_sat  w_mean_ms  n_ticks  inbound_5xx_fraction
adservice              8.046        664.5      0.00918    n/a     1.765      26       0                   
cartservice            14.42        604.5      0.01853    n/a     1.794      26       0                   
checkoutservice        n/a          n/a        n/a        n/a     n/a        0        0                   
currencyservice        48.01        1244       0.0315     n/a     0.8327     26       0                   
emailservice           n/a          n/a        n/a        n/a     n/a        0        0                   
frontend               14.42        51.78      0.2163     n/a     25.16      26       0                   
paymentservice         n/a          n/a        n/a        n/a     n/a        0        0                   
productcatalogservice  59.46        2.348e+04  0.001908   n/a     0.04824    26       0                   
recommendationservice  8.038        285.4      0.02138    n/a     3.861      26       0                   
redis-cart             n/a          n/a        n/a        n/a     n/a        0        0                   
shippingservice        3.192        1.15e+04   0.0002347  n/a     0.1059     20       0                   

Notes:
  - checkoutservice: no ticks with traffic
  - emailservice: no ticks with traffic
  - paymentservice: no ticks with traffic
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
