# rho / mu.hat estimate report — `baseline_no_topfull_sustained_overload_run70`

Generated: 2026-09-29T12:14:18Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run70`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              79.58        n/a     1.189      2.843     122      0                     0                       
cartservice            430.6        n/a     2.691      3.217     122      0                     3.788e-06               
checkoutservice        61.24        105     69.37      62.97     210      0                     0.003896                
currencyservice        643.9        n/a     2.308      3.091     123      0                     2.534e-05               
emailservice           61.24        97.5    7.348      3.363     123      0                     0.00555                 
frontend               414.6        239     958.7      982.2     275      0.4213                0.4232                  
paymentservice         61.24        n/a     2.252      3.021     122      0                     0                       
productcatalogservice  1701         n/a     1.895      2.612     123      0                     9.588e-06               
recommendationservice  791.3        644     460.8      641.3     122      0                     0.2185                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        207.3        n/a     0.791      1.685     123      0                     0                       

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log.
