# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run12`

Generated: 2026-09-16T22:42:51Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run12`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              121.2        601.3     0.2046   n/a     2.136      3.058     122      0                   
cartservice            560.7        690.3     0.8214   n/a     8.574      6.139     122      0                   
checkoutservice        19.81        32.19     0.6213   n/a     80.59      79.39     122      0                   
currencyservice        829          940.5     0.8889   n/a     10.24      7.72      122      0                   
emailservice           19.8         306.5     0.06525  n/a     3.551      3.633     121      0                   
frontend               541.2        546.8     0.9985   n/a     305.1      257       122      0                   
paymentservice         19.77        478       0.04184  n/a     2.178      3.021     121      0                   
productcatalogservice  2365         2508      0.9526   n/a     8.123      7.624     121      0                   
recommendationservice  329          344.2     0.9647   n/a     88.79      55.53     122      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        227.4        727.5     0.3134   n/a     2.025      2.843     122      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

`retryguard.log` is present but no `ON→OFF` / `OFF→ON` toggle events were found (RetryGuard ran but never crossed its threshold for the required `interval_samples` — this is expected on many flat baseline/RG-inert runs).
