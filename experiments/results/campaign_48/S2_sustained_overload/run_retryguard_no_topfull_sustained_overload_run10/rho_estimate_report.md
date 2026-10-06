# rho / mu.hat estimate report — `run_retryguard_no_topfull_sustained_overload_run10`

Generated: 2026-10-06T21:04:05Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\run_retryguard_no_topfull_sustained_overload_run10`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              258.1        n/a     1.639      2.942     122      0                     0                       
cartservice            602.7        5       3.715      3.673     122      0                     0.002876                
checkoutservice        108.5        75      574.7      747.9     122      0                     0.3356                  
currencyservice        856.8        n/a     3.749      3.683     122      0                     0                       
emailservice           59.1         58      145.4      9.4       91       0                     0.2299                  
frontend               508          469     317.7      177.2     475      0.05239               0.05289                 
paymentservice         100.1        123     5.866      3.835     122      0                     0.03157                 
productcatalogservice  2830         n/a     6.458      4.859     122      0                     2.313e-06               
recommendationservice  431.5        534     63.08      28.34     122      0                     0.01635                 
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        273          322     1.47       2.579     122      0                     0.01303                 

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

| timestamp | service | direction | rejection | counter | attempts |
|---|---|---|---|---|---|
| 2026-10-06T20:53:40Z | frontend->checkoutservice | ON→OFF | 2.2700 | consecutive_high=30 | 0 |
| 2026-10-06T20:54:13Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T20:54:45Z | frontend->checkoutservice | ON→OFF | 2.0000 | consecutive_high=30 | 0 |
| 2026-10-06T20:55:18Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T20:56:17Z | frontend->checkoutservice | ON→OFF | 1.9200 | consecutive_high=30 | 0 |
| 2026-10-06T20:56:50Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T20:57:27Z | frontend->checkoutservice | ON→OFF | 1.6400 | consecutive_high=30 | 0 |
| 2026-10-06T20:58:00Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T20:58:31Z | frontend->checkoutservice | ON→OFF | 1.5700 | consecutive_high=30 | 0 |
| 2026-10-06T20:59:04Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T20:59:38Z | frontend->checkoutservice | ON→OFF | 1.8900 | consecutive_high=30 | 0 |
| 2026-10-06T21:00:11Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T21:00:44Z | frontend->checkoutservice | ON→OFF | 2.0600 | consecutive_high=30 | 0 |
| 2026-10-06T21:01:17Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |
| 2026-10-06T21:01:51Z | frontend->checkoutservice | ON→OFF | 1.8800 | consecutive_high=30 | 0 |
| 2026-10-06T21:02:25Z | checkoutservice | OFF→ON | 0.0000 | consecutive_low=30 | 3 |

**lambda/W/mu_sat at the services that toggled** (for cross-reference only; RetryGuard did not use these numbers — no `rho` is reported, see the caveat above):

- `checkoutservice`: lambda_mean=108.5  mu_sat=75  w_mean_ms=574.7  inbound_5xx_fraction=0 inbound_failure_fraction=0.3356

