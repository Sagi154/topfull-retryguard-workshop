# rho / mu.hat estimate report — `baseline_no_topfull_sustained_overload_run109`

Generated: 2026-10-03T18:45:51Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run109`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              197          n/a     1.461      2.927     122      0                     0                       
cartservice            549.8        n/a     6.708      3.665     122      0                     0.003388                
checkoutservice        88.59        72.5    292        132.4     122      0                     0.3776                  
currencyservice        763.2        n/a     9.303      3.151     123      0                     0                       
emailservice           25.65        2       10.8       3.448     114      0                     0.02297                 
frontend               489.1        393     631.6      519.7     295      0.2187                0.2199                  
paymentservice         81.67        120     5.238      3.164     122      0                     0.03087                 
productcatalogservice  2317         n/a     2.9        3.091     122      0                     7.037e-07               
recommendationservice  568.9        538     371        498.5     123      0                     0.1485                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        213.1        283     1.193      1.804     123      0                     0.01339                 

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log.
