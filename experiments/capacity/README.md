# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-19)

All four entries remain `method: "not_yet_calibrated"`. A best-effort
TopFull-off + RetryGuard-off battery at full paper CPU limits was run:

| Service | Calibration folder | `mu_sat` | Why |
|---|---|---|---|
| frontend | `campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2` | null | inbound 5xx = 0; overload was reset-driven |
| checkoutservice | `campaign_48/calibration_checkout_payment_full_cpu_run1` | null | same (matches S3 RG run8 diagnosis) |
| paymentservice | same as checkout | null | same |
| productcatalogservice | `campaign_48/calibration_productcatalog_full_cpu_run1` | null | inbound 5xx = 0; overload was reset-driven |

`capacity_frozen.py freeze` correctly refused each service
(`mu_sat unavailable … no saturating 5xx ticks`). Per the calibration
plan's best-effort rule: do **not** re-boost Locust or build a direct
gRPC micro-benchmark until the team decides how to handle reset-driven
saturation (v1 `mu_sat` is 5xx-only).

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only. cluster_shape must stay
`topfull-worker-1=e2-standard-16` until a full re-calibration after a
VM resize. This table is not auto-applied by pull_results.py.
