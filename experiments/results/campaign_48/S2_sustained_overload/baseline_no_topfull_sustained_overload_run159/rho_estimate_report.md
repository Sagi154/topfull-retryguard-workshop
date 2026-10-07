# rho / mu.hat estimate report — `baseline_no_topfull_sustained_overload_run159`

Generated: 2026-10-07T21:00:52Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run159`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              74.74        n/a     1.177      2.905     123      0                     0                       
cartservice            351.7        n/a     2.571      3.131     123      0                     0.0002481               
checkoutservice        26.53        70.75   103.4      84.15     123      0                     0.05634                 
currencyservice        446.2        n/a     1.789      2.981     123      0                     0                       
emailservice           23.73        4.5     11.03      3.42      122      0                     0.004041                
frontend               349.6        199     1124       1240      258      0.392                 0.394                   
paymentservice         26.28        123.2   2.57       3.06      122      0                     0.004386                
productcatalogservice  1237         n/a     1.535      2.189     123      0                     1.309e-06               
recommendationservice  755.2        679.5   459.8      715.8     122      0                     0.1656                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        78.71        n/a     0.8108     2.048     123      0                     0.001857                

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log.
