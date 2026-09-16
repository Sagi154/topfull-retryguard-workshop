# rho / mu.hat estimate report — `baseline_topfull_no_retryguard_sustained_overload_run23`

Generated: 2026-09-16T22:19:50Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run23`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              129.1        514       0.2529   n/a     2.625      3.21      122      0                   
cartservice            555.2        785.6     0.7128   n/a     5.17       3.922     122      0                   
checkoutservice        19.91        29.61     0.6755   n/a     104.3      122.9     122      0                   
currencyservice        849          953.8     0.8975   n/a     11.26      8.496     122      0                   
emailservice           19.88        226.4     0.08834  n/a     5.025      4.333     122      0                   
frontend               535.5        542.3     0.9958   n/a     333.8      337.5     122      0                   
paymentservice         19.93        377.1     0.05303  n/a     2.874      3.316     122      0                   
productcatalogservice  2424         2545      0.9598   n/a     9.468      9.015     122      0                   
recommendationservice  338.6        346.3     0.9818   n/a     93.4       72.71     122      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        229.2        632.2     0.3646   n/a     2.465      3.059     122      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
