# rho / mu.hat estimate report — `run_topfull_retryguard_normal_op_run7`

Generated: 2026-09-16T21:57:43Z
Run folder: `experiments\results\campaign_48\S1_normal_op\run_topfull_retryguard_normal_op_run7`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              95.85        662.9     0.1493   n/a     1.895      2.968     62       0                   
cartservice            401.9        570       0.7316   n/a     6.517      5.74      62       0                   
checkoutservice        10.75        27.78     0.36     n/a     58.62      61.71     58       0                   
currencyservice        624.4        782.6     0.8255   n/a     7.03       6.496     62       0                   
emailservice           10.15        299       0.03344  n/a     3.48       3.592     60       0                   
frontend               392          413.6     0.9913   n/a     263.1      277.2     62       0                   
paymentservice         10.94        479.7     0.02085  n/a     2.158      3         54       0                   
productcatalogservice  1781         2000      0.9213   n/a     7.251      7.251     62       0                   
recommendationservice  248.8        270       0.9593   n/a     81.11      73.2      62       0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        163.2        593.1     0.2833   n/a     2.355      2.973     62       0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

`retryguard.log` is present but no `ON→OFF` / `OFF→ON` toggle events were found (RetryGuard ran but never crossed its threshold for the required `interval_samples` — this is expected on many flat baseline/RG-inert runs).
