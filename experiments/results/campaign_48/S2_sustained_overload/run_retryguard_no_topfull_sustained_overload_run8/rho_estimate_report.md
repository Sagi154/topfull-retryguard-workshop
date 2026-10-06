# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run8`

Generated: 2026-10-05T21:21:05Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run8`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              119.5        n/a     1.529      2.985     96       0                     0                       
cartservice            389.1        n/a     2.812      3.187     123      0                     0.002896                
checkoutservice        52.57        48.5    256.2      140.6     97       0                     0.414                   
currencyservice        632.5        n/a     4.277      3.51      123      0                     4.561e-05               
emailservice           19.2         6.25    24.07      3.75      97       0                     0.05783                 
frontend               390.5        103     921.7      1388      295      0.6039                0.6044                  
paymentservice         49.83        103.5   6.486      3.427     96       0                     0.03                    
productcatalogservice  1315         n/a     2.549      2.431     123      0                     5.756e-05               
recommendationservice  650.7        607.5   533.5      720       104      0                     0.2286                  
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        141.2        n/a     1.179      2.54      99       0                     0.00873                 

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-05T21:13:17Z | recommendationservice | ON→OFF | 0.3200 | consecutive_high=30 | 0 |
| 2026-10-05T21:14:19Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T21:16:31Z | recommendationservice | ON→OFF | 0.3100 | consecutive_high=30 | 0 |
| 2026-10-05T21:17:33Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-05T21:18:35Z | recommendationservice | ON→OFF | 0.3200 | consecutive_high=30 | 0 |
| 2026-10-05T21:19:37Z | recommendationservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `recommendationservice`: lambda_mean=650.7  mu_sat=607.5  w_mean_ms=533.5  inbound_5xx_fraction=0 inbound_failure_fraction=0.2286

