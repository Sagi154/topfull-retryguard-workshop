# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run26`

Generated: 2026-10-08T09:22:32Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run26`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              246.1        n/a     1.258      2.859     176      0                     0                       
cartservice            569.1        n/a     4.08       3.923     177      0                     0.001675                
checkoutservice        71.4         67      232.9      190.8     174      0                     0.187                   
currencyservice        820.7        n/a     3.945      3.725     176      0                     2.322e-06               
emailservice           52.8         6.5     26.06      4.797     175      0                     0.01492                 
frontend               505.8        460.5   335.5      201.7     437      0.05694               0.05804                 
paymentservice         69.58        120.5   3.882      3.22      176      0                     0.0134                  
productcatalogservice  2731         n/a     2.342      3.074     176      0                     2.086e-06               
recommendationservice  452.8        556.2   196.4      119.8     175      0                     0.02589                 
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        223.2        n/a     1.082      2.274     176      0                     0.00478                 

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-08T09:12:40Z | frontend->checkoutservice | ON→OFF | 1.7700 | consecutive_high=30 | 0 |
| 2026-10-08T09:13:47Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 1 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `checkoutservice`: lambda_mean=71.4  mu_sat=67  w_mean_ms=232.9  inbound_5xx_fraction=0 inbound_failure_fraction=0.187

