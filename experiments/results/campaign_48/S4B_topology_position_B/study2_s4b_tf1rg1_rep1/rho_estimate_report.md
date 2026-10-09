# rho / mu.hat estimate report — `study2_s4b_tf1rg1_rep1`

Generated: 2026-10-09T11:10:46Z
Run folder: `experiments\results\campaign_48\S4B_topology_position_B\study2_s4b_tf1rg1_rep1`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              167.7        n/a     0.9455     2.543     122      0                     0                       
cartservice            383          n/a     2.198      3.077     122      0                     2.555e-05               
checkoutservice        28.78        16      68.92      49.27     122      0                     0.0002838               
currencyservice        526.6        n/a     1.546      2.862     122      0                     0                       
emailservice           8.933        11      78.86      4.103     6        0                     0.04478                 
frontend               354.3        n/a     51.53      56.6      295      0                     8.747e-05               
paymentservice         28.78        n/a     1.597      2.987     122      0                     0                       
productcatalogservice  1833         n/a     0.8691     1.826     122      0                     3.559e-06               
recommendationservice  263.2        n/a     10.76      9.36      122      0                     0                       
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        124.6        n/a     0.4937     0.4407    122      0                     0                       

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

`retryguard.log` is present but no `ON→OFF` / `OFF→ON` toggle events were found (RetryGuard ran but never crossed its threshold for the required `interval_samples` — this is expected on many flat baseline/RG-inert runs).
