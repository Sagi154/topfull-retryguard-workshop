# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run16`

Generated: 2026-10-07T12:23:14Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run16`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              253.8        n/a     1.638      2.974     121      0                     0                       
cartservice            607.8        19      3.628      3.611     122      0                     0.001272                
checkoutservice        88.72        74      371.7      396       121      0                     0.2042                  
currencyservice        845.6        n/a     3.518      3.593     122      0                     3.865e-06               
emailservice           70.36        65      62.5       58.68     119      0                     0.1286                  
frontend               525.7        505     300.9      223.8     379      0.06883               0.06922                 
paymentservice         87.66        125     6.461      3.541     122      0                     0.01324                 
productcatalogservice  2907         n/a     6.923      6.747     122      0                     0                       
recommendationservice  458.4        585     82.73      37.65     122      0                     0.02026                 
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        262.7        n/a     1.315      2.495     122      0                     0.002427                

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-07T12:13:05Z | frontend->checkoutservice | ON→OFF | 1.5700 | consecutive_high=30 | 0 |
| 2026-10-07T12:17:07Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 1 |
| 2026-10-07T12:17:07Z | frontend->recommendationservice | ON→OFF | 1.5400 | consecutive_high=30 | 0 |
| 2026-10-07T12:17:44Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 1 |
| 2026-10-07T12:17:45Z | frontend->checkoutservice | ON→OFF | 0.9300 | consecutive_high=30 | 0 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `checkoutservice`: lambda_mean=88.72  mu_sat=74  w_mean_ms=371.7  inbound_5xx_fraction=0 inbound_failure_fraction=0.2042
- `recommendationservice`: lambda_mean=458.4  mu_sat=585  w_mean_ms=82.73  inbound_5xx_fraction=0 inbound_failure_fraction=0.02026

