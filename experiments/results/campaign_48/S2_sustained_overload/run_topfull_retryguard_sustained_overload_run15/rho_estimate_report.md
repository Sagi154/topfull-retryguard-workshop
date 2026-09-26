# rho / mu.hat estimate report — `run_topfull_retryguard_sustained_overload_run15`

Generated: 2026-09-24T15:58:34Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run15`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              186          n/a     1.264      2.905     122      0                     8.747e-06               
cartservice            445          n/a     2.322      3.129     123      0                     2.916e-05               
checkoutservice        23.19        31.5    82.26      48.45     122      0                     0.01488                 
currencyservice        798.9        n/a     3.371      3.45      123      0                     1.827e-05               
emailservice           22.96        30      4.63       3.177     123      0                     0.01127                 
frontend               424.9        319.8   834.7      849.2     284      0.1681                0.1697                  
paymentservice         23.16        n/a     2.168      3.036     123      0                     0                       
productcatalogservice  2425         n/a     2.692      3.001     123      0                     1.07e-05                
recommendationservice  624.6        571.5   527.7      534.4     123      0                     0.1826                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        183.8        n/a     0.7152     1.611     122      0                     1.766e-05               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-09-24T15:48:24Z | recommendationservice | ON→OFF | 0.2300 | consecutive_high=30 | 0 |
| 2026-09-24T15:49:27Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-24T15:50:29Z | recommendationservice | ON→OFF | 0.2300 | consecutive_high=30 | 0 |
| 2026-09-24T15:51:30Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-09-24T15:53:54Z | recommendationservice | ON→OFF | 0.2700 | consecutive_high=30 | 0 |
| 2026-09-24T15:54:56Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `recommendationservice`: lambda_mean=624.6  mu_sat=571.5  w_mean_ms=527.7  inbound_5xx_fraction=0 inbound_failure_fraction=0.1826

