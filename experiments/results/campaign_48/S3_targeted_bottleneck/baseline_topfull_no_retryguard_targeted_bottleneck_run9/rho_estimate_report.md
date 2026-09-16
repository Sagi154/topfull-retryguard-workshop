# rho / mu.hat estimate report — `baseline_topfull_no_retryguard_targeted_bottleneck_run9`

Generated: 2026-09-16T20:33:09Z
Run folder: `experiments\results\campaign_48\S3_targeted_bottleneck\baseline_topfull_no_retryguard_targeted_bottleneck_run9`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w     mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              126.8        625.5     0.2046    n/a     2.073      3.044     122      0                   
cartservice            539.3        763.3     0.7114    n/a     4.906      4.336     122      0                   
checkoutservice        22.89        24.98     0.9206    n/a     500.8      750       121      0                   
currencyservice        783.9        948.3     0.8278    n/a     6.817      5.895     122      0                   
emailservice           1.529        n/a       n/a       n/a     n/a        n/a       0        0                   
frontend               527.5        533.7     0.9949    n/a     268.9      256.9     122      0.01881             
paymentservice         2.621        603       0.003317  n/a     2.022      3         47       0                   
productcatalogservice  2289         2416      0.9525    n/a     7.875      7.414     122      0                   
recommendationservice  317.8        335.5     0.9508    n/a     63.17      48.98     122      0                   
redis-cart             n/a          n/a       n/a       n/a     n/a        n/a       0        0                   
shippingservice        194.2        627.6     0.3107    n/a     2.298      2.993     122      0                   

Notes:
  - emailservice: latency columns are present but every tick had rq_time_count delta == 0 (no completed requests counted in the histogram this tick) -- mu_hat_w/rho_w unavailable
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log. Skipping toggle-vs-rho comparison.
