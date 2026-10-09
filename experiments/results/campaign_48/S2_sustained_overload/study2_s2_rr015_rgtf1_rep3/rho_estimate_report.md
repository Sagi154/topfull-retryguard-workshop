# rho / mu.hat estimate report — `study2_s2_rr015_rgtf1_rep3`

Generated: 2026-10-09T06:56:36Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\study2_s2_rr015_rgtf1_rep3`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              205.2        n/a     1.168      2.829     122      0                     1.57e-05                
cartservice            531.6        n/a     2.81       3.273     122      0                     6.99e-05                
checkoutservice        53.37        72      116.1      122.4     123      0                     0.01084                 
currencyservice        761.5        n/a     2.493      3.19      122      0                     0                       
emailservice           52.23        30.5    19.09      3.799     122      0                     0.001412                
frontend               488.5        440.5   470.4      693.7     241      0.1381                0.1388                  
paymentservice         53.39        132     2.064      3.034     122      0                     0.0005552               
productcatalogservice  2377         n/a     4.09       4.465     123      0                     6.091e-06               
recommendationservice  452.1        431     384.2      419.8     123      0                     0.07112                 
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        178.2        n/a     0.6773     1.414     122      0                     0.0002096               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-09T06:49:03Z | frontend->recommendationservice | ON→OFF | 0.9500 | consecutive_high=27 | 0 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):


