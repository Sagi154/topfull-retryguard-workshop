# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run6`

Generated: 2026-10-05T15:14:22Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run6`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              151.2        4       1.575      2.986     105      0                     6.157e-05               
cartservice            449.9        3       3.329      3.282     122      0                     0.003362                
checkoutservice        69.74        47      291.1      246.4     104      0                     0.4355                  
currencyservice        630.8        n/a     3.201      3.394     122      0                     0                       
emailservice           25.44        5       20.68      3.625     97       0                     0.05617                 
frontend               418.2        262     917.9      918.9     356      0.3204                0.3221                  
paymentservice         67.45        99.5    18.42      3.578     104      0                     0.08058                 
productcatalogservice  1757         n/a     2.691      2.798     122      0                     2.743e-06               
recommendationservice  607.6        564     573.3      729.2     122      0                     0.2053                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        190          n/a     1.23       2.353     104      0                     0.009579                

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-05T15:04:48Z | recommendationservice | ON→OFF | 0.2700 | consecutive_high=30 | 0 |
| 2026-10-05T15:05:23Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:05:25Z | checkoutservice | ON→OFF | 0.6700 | consecutive_high=30 | 0 |
| 2026-10-05T15:05:56Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:07:45Z | recommendationservice | ON→OFF | 0.2600 | consecutive_high=30 | 0 |
| 2026-10-05T15:08:21Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:08:53Z | recommendationservice | ON→OFF | 0.3100 | consecutive_high=30 | 0 |
| 2026-10-05T15:09:36Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:09:37Z | checkoutservice | ON→OFF | 0.6500 | consecutive_high=30 | 0 |
| 2026-10-05T15:10:15Z | recommendationservice | ON→OFF | 0.3000 | consecutive_high=30 | 0 |
| 2026-10-05T15:10:18Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:10:56Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:11:00Z | checkoutservice | ON→OFF | 0.6800 | consecutive_high=30 | 0 |
| 2026-10-05T15:11:32Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:11:32Z | recommendationservice | ON→OFF | 0.3900 | consecutive_high=30 | 0 |
| 2026-10-05T15:12:08Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:12:12Z | checkoutservice | ON→OFF | 0.5000 | consecutive_high=30 | 0 |
| 2026-10-05T15:12:43Z | recommendationservice | ON→OFF | 0.3700 | consecutive_high=30 | 0 |
| 2026-10-05T15:12:45Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T15:13:17Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `recommendationservice`: lambda_mean=607.6  mu_sat=564  w_mean_ms=573.3  inbound_5xx_fraction=0 inbound_failure_fraction=0.2053
- `checkoutservice`: lambda_mean=69.74  mu_sat=47  w_mean_ms=291.1  inbound_5xx_fraction=0 inbound_failure_fraction=0.4355

