# rho / mu.hat estimate report — `run_topfull_retryguard_targeted_bottleneck_run8`

Generated: 2026-09-16T20:56:27Z
Run folder: `experiments\results\campaign_48\S3_targeted_bottleneck\run_topfull_retryguard_targeted_bottleneck_run8`

## Context

`experiments/retryguard.py`'s live controller does not use this rho estimate — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). The rho = lambda/mu.hat estimate below (`experiments/estimate_service_mu.py`) is an offline, supplementary diagnostic, not the controller's decision input and not a validated ground-truth rho.

**Methodology (corrected 2026-09-16 — see `docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`):** `mu_hat_w = lambda + 1/W` (M/M/1 steady-state relation, rearranged), where `lambda` is this service's inbound arrival rate (`Δtotal/Δt` from `service_inbound.csv`) and `W` is this service's own mean inbound sojourn time, from Envoy's `downstream_rq_time` histogram (`rq_time_sum_ms`/`rq_time_count`, added to `envoy_retry_collector.py` on 2026-09-16). `rho_w = lambda / mu_hat_w`. This replaced an earlier, incorrect estimator (`mu_cpu = lambda / utilization` from `topfull_detect.csv`) that conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — a different system's internal signal, not this paper's model. Runs from before 2026-09-16 lack the `rq_time_*` columns; `mu_hat_w`/`rho_w` come back `n/a` with an explicit note in that case, not a silently wrong number. The M/M/1 `W` formula assumes steady state (`rho < 1`); when a service's `lambda_mean` reaches or exceeds its own `mu_hat_w`, the report flags that the assumption is likely violated (finite buffer, admission control upstream, or non-Poisson/non-exponential real traffic) rather than trusting the number at face value. The saturated-goodput cross-check (`mu_sat = Δ 2xx/Δt` on ticks with a high 5xx fraction) is unchanged and independent of the above.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_hat_w  rho_w    mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction
adservice              105.8        862.1     0.1229   n/a     1.347      2.88      122      0                   
cartservice            374.5        795.3     0.4741   n/a     2.461      3.117     122      0                   
checkoutservice        21.71        28.99     0.897    n/a     1178       750       120      0                   
currencyservice        609.1        1021      0.6021   n/a     2.711      3.196     122      0                   
emailservice           8.044        332.3     0.02408  n/a     3.462      3.406     52       0                   
frontend               361.4        370.9     0.9813   346     138.5      93.67     122      0.0162              
paymentservice         7.328        465.2     0.01505  n/a     2.44       3.023     56       0                   
productcatalogservice  1780         2176      0.8243   n/a     2.608      3.045     122      0                   
recommendationservice  251.1        332.4     0.7612   n/a     13.68      11.26     122      0                   
redis-cart             n/a          n/a       n/a      n/a     n/a        n/a       0        0                   
shippingservice        148.8        1290      0.1163   n/a     0.9167     2.278     121      0                   

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-09-16T20:45:47Z | checkoutservice | ON→OFF | 0.5400 | consecutive_high=30 | 0 |
| 2026-09-16T20:46:20Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:46:52Z | checkoutservice | ON→OFF | 0.6900 | consecutive_high=30 | 0 |
| 2026-09-16T20:47:26Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:47:59Z | checkoutservice | ON→OFF | 0.3700 | consecutive_high=30 | 0 |
| 2026-09-16T20:48:32Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:49:08Z | checkoutservice | ON→OFF | 0.5300 | consecutive_high=30 | 0 |
| 2026-09-16T20:49:45Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:50:17Z | checkoutservice | ON→OFF | 0.4500 | consecutive_high=30 | 0 |
| 2026-09-16T20:50:48Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:51:20Z | checkoutservice | ON→OFF | 0.4600 | consecutive_high=30 | 0 |
| 2026-09-16T20:51:52Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:52:49Z | checkoutservice | ON→OFF | 0.5000 | consecutive_high=30 | 0 |
| 2026-09-16T20:53:23Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-16T20:53:55Z | checkoutservice | ON→OFF | 0.5100 | consecutive_high=30 | 0 |
| 2026-09-16T20:54:27Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**rho_w at the services that toggled** (for cross-reference only — see the caveat above; RetryGuard did not use this number):

- `checkoutservice`: rho_w_median=0.897  mu_hat_w=28.99  mu_sat=n/a  w_mean_ms=1178  inbound_5xx_fraction=0

