# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run17`

Generated: 2026-10-05T13:42:53Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run17`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              161.3        n/a     1.118      2.752     122      0                     0                       
cartservice            507          n/a     2.61       3.193     122      0                     0                       
checkoutservice        42.61        45      100.3      82.6      123      0                     0.000497                
currencyservice        732.3        n/a     2.208      3.047     122      0                     4.459e-06               
emailservice           42.74        50      14.96      3.522     122      0                     0.0008029               
frontend               485.1        357     721.4      816.2     373      0.2531                0.2545                  
paymentservice         42.62        n/a     2.036      3.035     122      0                     0                       
productcatalogservice  2152         n/a     1.777      2.575     123      0                     9.847e-06               
recommendationservice  687.4        590.5   462.4      580.5     122      0                     0.1893                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        161.1        n/a     0.6526     1.203     122      0                     0                       

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-05T13:33:06Z | recommendationservice | ON→OFF | 0.2300 | consecutive_high=30 | 0 |
| 2026-10-05T13:33:41Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `recommendationservice`: lambda_mean=687.4  mu_sat=590.5  w_mean_ms=462.4  inbound_5xx_fraction=0 inbound_failure_fraction=0.1893

