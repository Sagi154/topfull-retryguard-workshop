# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run25`

Generated: 2026-10-08T01:51:50Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run25`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              92.1         n/a     1.102      2.915     171      0                     0                       
cartservice            312.4        n/a     2.687      3.133     174      0                     5.329e-05               
checkoutservice        30.49        10.92   57.27      40.67     162      0                     0.006453                
currencyservice        374.9        n/a     1.723      2.995     174      0                     2.608e-06               
emailservice           30.47        n/a     8.53       3.2       163      0                     0.001493                
frontend               291          175.5   362.2      45.78     350      0.2272                0.2302                  
paymentservice         30.41        n/a     1.758      3.012     168      0                     0.000369                
productcatalogservice  1199         n/a     1.102      1.397     175      0                     0                       
recommendationservice  326.7        684.5   158.6      8.125     175      0                     0.1222                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        93.48        n/a     0.7998     2.171     169      0                     0.0001877               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

`retryguard.log` is present but no `ON→OFF` / `OFF→ON` toggle events were found (RetryGuard ran but never crossed its threshold for the required `interval_samples` — this is expected on many flat baseline/RG-inert runs).
