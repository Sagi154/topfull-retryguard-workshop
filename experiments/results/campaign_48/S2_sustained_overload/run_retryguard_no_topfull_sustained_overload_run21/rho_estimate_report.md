# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run21`

Generated: 2026-10-08T00:06:48Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run21`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              173          n/a     1.226      2.909     122      0                     0                       
cartservice            533.5        n/a     3.598      3.604     123      0                     0.0004548               
checkoutservice        55.35        71.5    163.4      150.1     122      0                     0.06379                 
currencyservice        752          n/a     2.769      3.286     123      0                     6.411e-06               
emailservice           48.89        5.5     23.71      4.184     121      0                     0.00412                 
frontend               507.8        400.2   498.6      689.6     268      0.2706                0.2715                  
paymentservice         54.74        120.5   3.398      3.121     122      0                     0.003978                
productcatalogservice  2163         n/a     2.599      3.194     123      0                     6.689e-06               
recommendationservice  468.7        417.5   426.3      455.3     122      0                     0.112                   
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        168          n/a     0.9347     2.137     123      0                     0.001638                

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-07T23:57:32Z | frontend->recommendationservice | ON→OFF | 1.2500 | consecutive_high=30 | 0 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):


