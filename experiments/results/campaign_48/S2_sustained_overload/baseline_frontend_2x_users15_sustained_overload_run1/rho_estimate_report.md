# rho / mu.hat estimate report — `baseline_frontend_2x_users15_sustained_overload_run1`

Generated: 2026-09-17T20:53:48Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_frontend_2x_users15_sustained_overload_run1`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              152.6        424.3     0.3654   n/a     3.81       3.743     122      0                   
cartservice            585.6        839.5     0.7075   n/a     4.472      4.076     122      0                   
checkoutservice        18.23        30.73     0.5857   n/a     80.08      77.78     121      0                   
currencyservice        919.4        998.1     0.9308   n/a     16.58      16.11     122      0                   
emailservice           18.63        254.2     0.07082  n/a     4.375      4.138     119      0                   
frontend               568.1        580.9     0.9916   n/a     575        637.5     121      0                   
paymentservice         18.23        428.6     0.04199  n/a     2.471      3.127     121      0                   
productcatalogservice  2645         2769      0.9648   n/a     13.41      13.79     121      0                   
recommendationservice  370.5        404.7     0.9242   n/a     31.48      24.38     121      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        235.6        563.3     0.4207   n/a     3.125      3.382     122      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
