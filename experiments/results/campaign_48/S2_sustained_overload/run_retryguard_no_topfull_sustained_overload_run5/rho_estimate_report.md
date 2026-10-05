# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run5`

Generated: 2026-10-05T12:54:35Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run5`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              185.1        n/a     1.154      2.818     122      0                     3.53e-05                
cartservice            508.2        n/a     2.815      3.275     123      0                     3.21e-06                
checkoutservice        48.72        49      112        92.61     123      0                     0.001174                
currencyservice        745          n/a     2.585      3.189     122      0                     2.19e-06                
emailservice           48.71        34.5    18.02      3.794     122      0                     0.001006                
frontend               472.4        410     669.9      757.7     431      0.1546                0.1558                  
paymentservice         48.71        n/a     2.072      3.057     122      0                     0                       
productcatalogservice  2351         n/a     1.918      2.747     123      0                     6.234e-06               
recommendationservice  616.4        533     433.7      471.6     122      0                     0.1742                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        185          n/a     0.7327     1.685     123      0                     0                       

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

`retryguard.log` is present but no `ON→OFF` / `OFF→ON` toggle events were found (RetryGuard ran but never crossed its threshold for the required `interval_samples` — this is expected on many flat baseline/RG-inert runs).
