# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-19)

All four minimum-set services are `method: "mu_sat"`. Checkout and
payment remain the full-CPU reset-driven freeze (`SAT_5XX_FRACTION`
still 0.05). Productcatalog is the constrained 50m freeze. Frontend was
re-frozen the same day from the higher-`n_sat` of two TopFull-off +
RetryGuard-off constrained replays after `SAT_TAIL_TRIM_TICKS=5`
(unconditional last-5-row trim; `LOW_CONFIDENCE_SAT_TICKS` still 10):
**winner** `calibration_frontend_constrained_50m_run1` (`n_sat_ticks=26`,
ok confidence) over `calibration_frontend_constrained_run2` (`n_sat=16`
at 100m). Do **not** reuse the earlier 9-tick
`calibration_frontend_constrained_run1` freeze (0.37 at 100m,
`low_confidence`) or the full-CPU 2-tick freezes (frontend 0.238 at
1000m, productcatalog 1.399 at 500m). Do **not** freeze from S3 RG run8
(checkout is 100m there, not paper 1000m). Next free YAML slots: 100m
constrained **run3**, 50m constrained **run2**.

| Service | Source run | millicores | `mu_per_millicore` | `n_sat_ticks` |
|---|---|---|---|---|
| frontend | `campaign_48/calibration_frontend_constrained_50m_run1` | 50m × 1 | 0.3 | 26 (ok) |
| checkoutservice | `campaign_48/calibration_checkout_payment_full_cpu_run1` | 1000m × 1 | 0.1615 | 34 |
| paymentservice | same as checkout | 1000m × 1 | 0.0195 | 20 |
| productcatalogservice | `campaign_48/calibration_productcatalog_constrained_run1` | 50m × 1 | 8.95 | 60 |

Historical (do not reuse): frontend `calibration_frontend_constrained_run1`
100m × 1, `mu_per_millicore=0.37`, `n_sat_ticks=9` (low confidence).

Sanity `rho_frozen_report.py` on S1 baseline run24 / S2 baseline run23:
frontend `rho_hat` 1.295 / 1.837 (was 1.05 / 1.49 from the 9-tick freeze);
productcatalog `rho_hat` 0.398 / 0.5418; checkout 0.06168 / 0.1233 and
payment 0.5108 / 1.021 unchanged. Informal band was S1 entry ~0.5–0.8,
S2 entry >1 — frontend is still above the S1 band. Do not treat that
band as a pass/fail gate.

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only (reset-aware trigger).
cluster_shape must stay `topfull-worker-1=e2-standard-16` until a full
re-calibration after a VM resize. This table is not auto-applied by
pull_results.py.
