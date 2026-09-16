# rho / mu.hat estimate report — `baseline_topfull_no_retryguard_normal_op_run24`

Generated: 2026-09-16T21:39:46Z
Run folder: `experiments\results\campaign_48\S1_normal_op\baseline_topfull_no_retryguard_normal_op_run24`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              95.46        587.9     0.1701   n/a     2.129      3.038     62       0                   
cartservice            402          590.5     0.7112   n/a     6.019      5.388     62       0                   
checkoutservice        9.961        21.32     0.469    n/a     87.48      89.06     62       0                   
currencyservice        621.1        806.5     0.796    n/a     6.655      6.082     62       0                   
emailservice           10.33        343.2     0.02914  n/a     3.127      3.381     60       0                   
frontend               392.1        413.6     0.9912   n/a     249.2      262.1     62       0                   
paymentservice         10.09        541.9     0.01845  n/a     1.991      3         61       0                   
productcatalogservice  1781         1992      0.9253   n/a     6.913      6.813     62       0                   
recommendationservice  248.5        270.2     0.9474   n/a     75.45      56.41     61       0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        162.1        719       0.2323   n/a     1.818      2.798     62       0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
