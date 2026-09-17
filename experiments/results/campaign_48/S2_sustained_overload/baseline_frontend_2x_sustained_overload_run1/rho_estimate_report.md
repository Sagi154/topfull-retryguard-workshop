# rho / mu.hat estimate report — `baseline_frontend_2x_sustained_overload_run1`

Generated: 2026-09-17T20:02:45Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_frontend_2x_sustained_overload_run1`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              143.4        554.9     0.2613   n/a     2.731      3.171     121      0                   
cartservice            610.2        812.3     0.762    n/a     5.904      4.854     121      0                   
checkoutservice        19.91        31.12     0.6426   n/a     90.23      89.77     122      0                   
currencyservice        943.7        1108      0.86     n/a     7.591      6.633     122      0                   
emailservice           19.91        268.1     0.07459  n/a     4.21       3.941     122      0                   
frontend               590.7        602.7     0.9955   n/a     334.2      337.5     122      0                   
paymentservice         19.91        403.1     0.04961  n/a     2.868      3.247     121      0                   
productcatalogservice  2698         2824      0.9661   n/a     9.18       8.468     121      0                   
recommendationservice  378          395.4     0.966    n/a     77.75      60.54     121      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        254.5        732.2     0.3469   n/a     2.166      2.942     121      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
