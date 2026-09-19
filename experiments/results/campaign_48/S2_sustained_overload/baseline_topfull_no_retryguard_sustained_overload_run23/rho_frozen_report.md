# frozen-capacity rho_hat report — `baseline_topfull_no_retryguard_sustained_overload_run23`

Generated: 2026-09-19T11:27:28Z
Run folder: `experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run23`
Frozen table: `C:\Users\sagi1\Projects\Workshop\experiments\capacity\capacity_frozen.json` (cluster_shape=topfull-worker-1=e2-standard-16)

This is a **supplementary** offline diagnostic, not RetryGuard's live input. Frozen μ came from a **different** calibration run, not from this run's own CSVs. `rho_hat = lambda_offered / mu_this_run` with `mu_this_run = mu_per_millicore * cpu_limit_millicores * replica_count` from this run's `service_capacity.json` (never `effective_cpu_quotas`).

| service | lambda_offered | lambda_retry | mu_per_millicore | mu_this_run | rho_hat | cpu_limit_m | calibrated_at_m | n_sat_ticks | low_confidence | na_reason |
|---|---|---|---|---|---|---|---|---|---|---|
| frontend | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | False | not_yet_calibrated |
| checkoutservice | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | False | not_yet_calibrated |
| productcatalogservice | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | False | not_yet_calibrated |
| paymentservice | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | False | not_yet_calibrated |
