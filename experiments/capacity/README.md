# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-19)

All four minimum-set services are `method: "mu_sat"`, frozen from the
three full-CPU TopFull-off + RetryGuard-off calibration folders after
`mu_sat` started gating on `(Δ5xx+Δresets)/Δtotal` (reset-driven
trigger; `SAT_5XX_FRACTION` still 0.05). Do **not** freeze from S3 RG
run8 (checkout is 100m there, not paper 1000m).

| Service | Source run | millicores | `mu_per_millicore` | `n_sat_ticks` |
|---|---|---|---|---|
| frontend | `campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2` | 1000m × 1 | 0.238 | 2 (low confidence) |
| checkoutservice | `campaign_48/calibration_checkout_payment_full_cpu_run1` | 1000m × 1 | 0.1615 | 34 |
| paymentservice | same as checkout | 1000m × 1 | 0.0195 | 20 |
| productcatalogservice | `campaign_48/calibration_productcatalog_full_cpu_run1` | 500m × 1 | 1.399 | 2 (low confidence) |

Sanity `rho_frozen_report.py` on S1 baseline run24 / S2 baseline run23:
frontend `rho_hat` 1.632 / 2.316. Informal band was S1 entry ~0.5–0.8,
S2 entry >1 — S2 matches; S1 is above the band, consistent with
frontend/productcatalog μ coming from only two saturating ticks.

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only (reset-aware trigger).
cluster_shape must stay `topfull-worker-1=e2-standard-16` until a full
re-calibration after a VM resize. This table is not auto-applied by
pull_results.py.
