# rho / mu.hat estimate report — `baseline_frontend_2x_users2_sustained_overload_run1`

Generated: 2026-09-17T21:16:35Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_frontend_2x_users2_sustained_overload_run1`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              202.1        686.5     0.2957   n/a     2.145      3.043     121      0                   
cartservice            587          799.4     0.7393   n/a     5.443      4.277     121      0                   
checkoutservice        12           27.04     0.4438   n/a     67.5       71.15     121      0                   
currencyservice        948.2        1079      0.8838   n/a     8.302      6.451     122      0                   
emailservice           13.14        314       0.03822  n/a     3.468      3.625     113      0                   
frontend               574.5        582.3     0.9944   n/a     335.3      330.9     122      7.71e-05            
paymentservice         12.06        520.5     0.02306  n/a     1.999      2.966     120      0                   
productcatalogservice  2812         2942      0.9608   n/a     8.602      8.235     122      0                   
recommendationservice  394.6        408       0.9731   n/a     114.1      88.51     122      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        204.4        800       0.2587   n/a     1.734      2.812     121      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
