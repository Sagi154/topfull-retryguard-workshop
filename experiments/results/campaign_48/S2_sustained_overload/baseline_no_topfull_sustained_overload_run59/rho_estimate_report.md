# rho / mu.hat estimate report — `baseline_no_topfull_sustained_overload_run59`

Generated: 2026-09-28T19:43:34Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run59`

## Context

`experiments/retryguard.py`'s live controller does not use anything in this report — it acts on a mesh rejection-rate surrogate (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`), matching the RetryGuard paper's own live Istio deployment (Sec 6.2: mesh rejection rate, 20% threshold, 30s window). Everything below is an offline, supplementary diagnostic, not the controller's decision input.

**No `rho` is computed by this report.** An earlier version reported `rho_w = lambda / mu_hat_w` using `mu_hat_w = lambda + 1/W` (the M/M/1 steady-state relation, rearranged) — removed 2026-09-17 (`docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`) because it is circular by construction: `W = 1/(mu-lambda)` presupposes `mu > lambda`, so solving for `mu` can only ever return a value just above the observed `lambda`. Algebraically `rho_w = lambda/mu_hat_w = L/(L+1)` where `L = lambda*W` is mean concurrency (Little's Law) — always below 1 by construction, unable to represent the `rho > 1` miscoordination regime this whole exercise exists to detect, and it reported ~0.93 for a healthy 6.9ms-latency service under normal load purely from having many requests in flight. Before that, an even earlier estimator, `mu_cpu = lambda / utilization` from `topfull_detect.csv`, conflated TopFull's own CPU-quota admission-control bookkeeping with the RetryGuard paper's queueing-theoretic rho — also removed (`docs/superpowers/specs/2026-09-16-rho-estimator-correction.md`).

**What this report shows instead:** `lambda_mean` (this service's admitted inbound arrival rate, `Δtotal/Δt` from `service_inbound.csv`); `w_mean_ms`/`w_p50_ms` (this service's own mean/P50 inbound sojourn time, from Envoy's `downstream_rq_time` histogram — reported as a latency observation, never as a stand-in for capacity); and `mu_sat` (`Δ 2xx/Δt` on ticks with a high (5xx+resets) fraction — the one capacity signal this report can produce from a single run, but only available on ticks with real rejection, so most runs show `mu_sat = n/a`). A `rho_hat = lambda_offered / mu_this_run` diagnostic that freezes `mu_per_millicore` from a dedicated saturation run and rescales by each run's Kubernetes CPU limit (`service_capacity.json`) is designed but not yet wired into this report — see `docs/superpowers/specs/2026-09-17-frozen-capacity-rho-design.md`.

## Per-service rho / lambda / mu.hat estimates

```
service                lambda_mean  mu_sat  w_mean_ms  w_p50_ms  n_ticks  inbound_5xx_fraction  inbound_failure_fraction
adservice              20.48        n/a     1.891      3.114     93       0                     8.272e-05               
cartservice            527.4        0       9.389      8.068     93       0                     8.043e-05               
checkoutservice        453.2        230     166.4      101.7     127      0                     0.1989                  
currencyservice        534.3        n/a     9.679      4.966     93       0                     1.533e-05               
emailservice           40.1         66.5    21.4       7.136     4        0                     0.08451                 
frontend               452.7        82.25   819.9      779.7     196      0.8225                0.8265                  
paymentservice         255.9        79.5    121.4      87.69     16       0                     0.7535                  
productcatalogservice  2561         0       32.68      36.85     93       0                     0.0002102               
recommendationservice  420.9        0       60.25      54.33     140      0                     0.0004263               
redis-cart             n/a          n/a     n/a        n/a       0        0                     0                       
shippingservice        475          n/a     3.654      3.288     92       0                     0.0006881               

Notes:
  - redis-cart: no ticks with traffic
```

## RetryGuard toggle events

No `retryguard.log` in this run folder — likely a baseline run (RetryGuard not enabled) or a run predating the toggle log.
