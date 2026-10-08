# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run24`

Generated: 2026-10-08T01:17:11Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run24`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              144.8        n/a     1.335      2.959     123      0                     0                       
cartservice            481.2        n/a     3.511      3.619     123      0                     9.836e-05               
checkoutservice        35.04        66.5    100.5      88.92     121      0                     0.02489                 
currencyservice        686.9        n/a     2.97       3.463     123      0                     0                       
emailservice           33.5         2.5     14.84      3.723     121      0                     0.002815                
frontend               459.4        364.5   580.5      692.8     241      0.2873                0.2882                  
paymentservice         34.87        117.5   2.379      3.065     121      0                     0.001424                
productcatalogservice  1894         n/a     2.577      3.318     123      0                     3.445e-06               
recommendationservice  478.6        391     427.4      454.1     122      0                     0.1221                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        128.4        n/a     0.952      2.44      122      0                     0.0004591               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-08T01:09:08Z | frontend->recommendationservice | ON→OFF | 2.4000 | consecutive_high=30 | 0 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):


