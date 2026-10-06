# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run20`

Generated: 2026-10-05T22:09:54Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run20`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              170.8        n/a     1.659      3.011     113      0                     0                       
cartservice            390.5        n/a     3.038      3.292     122      0                     5.859e-05               
checkoutservice        28.98        49.75   93.51      77.3      113      0                     0.02457                 
currencyservice        681.2        n/a     5.457      3.916     123      0                     7.172e-06               
emailservice           27.82        28.25   15.97      3.571     113      0                     0.002088                
frontend               373.2        153.5   957.2      913.4     304      0.3003                0.302                   
paymentservice         28.76        100.5   3.06       3.075     112      0                     0.003122                
productcatalogservice  1930         n/a     3.135      2.675     123      0                     1.35e-05                
recommendationservice  595.9        510     488.2      704.1     122      0                     0.2001                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        131.2        n/a     0.9285     2.308     114      0                     0.0004397               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-05T22:00:31Z | recommendationservice | ON→OFF | 0.2700 | consecutive_high=30 | 0 |
| 2026-10-05T22:01:35Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T22:02:36Z | recommendationservice | ON→OFF | 0.3000 | consecutive_high=30 | 0 |
| 2026-10-05T22:03:38Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T22:04:40Z | recommendationservice | ON→OFF | 0.2800 | consecutive_high=30 | 0 |
| 2026-10-05T22:05:43Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T22:08:28Z | recommendationservice | ON→OFF | 0.3200 | consecutive_high=30 | 0 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `recommendationservice`: lambda_mean=595.9  mu_sat=510  w_mean_ms=488.2  inbound_5xx_fraction=0 inbound_failure_fraction=0.2001

