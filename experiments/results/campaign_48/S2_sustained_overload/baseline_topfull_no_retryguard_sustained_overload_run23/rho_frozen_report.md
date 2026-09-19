# frozen-capacity rho_hat report — `baseline_topfull_no_retryguard_sustained_overload_run23`

Generated: 2026-09-19T16:19:17Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run23`
Frozen table: `C:\Users\sagi1\Projects\Workshop\experiments\capacity\capacity_frozen.json` (cluster_shape=topfull-worker-1=e2-standard-16)

This is a **supplementary** offline diagnostic, not RetryGuard's live input. Frozen μ came from a **different** calibration run, not from this run's own CSVs. `rho_hat = lambda_offered / mu_this_run` with `mu_this_run = mu_per_millicore * cpu_limit_millicores * replica_count` from this run's `service_capacity.json` (never `effective_cpu_quotas`).

| service | lambda_offered | lambda_retry | mu_per_millicore | mu_this_run | rho_hat | cpu_limit_m | calibrated_at_m | n_sat_ticks | low_confidence | na_reason |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend | 551.2 | n/a | 0.37 | 370 | 1.49 | 1000 | 100 | 9 | True | n/a |
| checkoutservice | 19.91 | 0 | 0.1615 | 161.5 | 0.1233 | 1000 | 1000 | 34 | False | n/a |
| productcatalogservice | 2424 | 0 | 8.95 | 4475 | 0.5418 | 500 | 50 | 60 | False | n/a |
| paymentservice | 19.9 | 0 | 0.0195 | 19.5 | 1.021 | 1000 | 1000 | 20 | False | n/a |

## Warnings

- `frontend`: millicore rescale 100m -> 1000m (ratio 10.0); assuming linear CPU scaling
- `productcatalogservice`: millicore rescale 50m -> 500m (ratio 10.0); assuming linear CPU scaling
