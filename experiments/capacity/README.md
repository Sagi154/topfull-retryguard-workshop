# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-19)

All four minimum-set services are `method: "mu_sat"`. Productcatalog is
the constrained 50m freeze. Frontend is the 50m constrained winner
(`n_sat_ticks=26`). Payment and checkout were re-frozen the same day
from CPU-pegged TopFull-off + RetryGuard-off constrained 50m holds
(`SAT_5XX_FRACTION` still 0.05; `SAT_TAIL_TRIM_TICKS=5`;
`LOW_CONFIDENCE_SAT_TICKS` still 10). Do **not** reuse the full-CPU
checkout/payment freeze (`calibration_checkout_payment_full_cpu_run1`:
checkout 0.1615 / payment 0.0195 at 1000m — payment never pegged CPU;
those payment resets were PlaceOrder / 500 ms `perTryTimeout` bleed).
Do **not** reuse the earlier 9-tick
`calibration_frontend_constrained_run1` freeze (0.37 at 100m,
`low_confidence`) or the full-CPU 2-tick freezes (frontend 0.238 at
1000m, productcatalog 1.399 at 500m). Do **not** freeze from S3 RG run8
(checkout is 100m there, not paper 1000m). YAML next-free: payment 100m
constrained **run2**, payment 50m constrained **run2**, checkout 50m
constrained **run2**, unused checkout 100m constrained stays **run1**;
frontend 100m constrained **run3**, frontend 50m constrained **run2**.

| Service | Source run | millicores | `mu_per_millicore` | `n_sat_ticks` | peg |
|---|---|---|---|---|---|
| frontend | `campaign_48/calibration_frontend_constrained_50m_run1` | 50m × 1 | 0.3 | 26 (ok) | — |
| checkoutservice | `campaign_48/calibration_checkout_constrained_50m_run1` | 50m × 1 | 10.82 | 210 (ok) | True (cpu_max 56m of 50m) |
| paymentservice | `campaign_48/calibration_payment_constrained_50m_run1` | 50m × 1 | 0.72 | 26 (ok) | True (cpu_max 49m of 50m) |
| productcatalogservice | `campaign_48/calibration_productcatalog_constrained_run1` | 50m × 1 | 8.95 | 60 (ok) | — |

Historical (do not reuse):

- frontend `calibration_frontend_constrained_run1` 100m × 1,
  `mu_per_millicore=0.37`, `n_sat_ticks=9` (low confidence).
- checkoutservice `calibration_checkout_payment_full_cpu_run1` 1000m × 1,
  `mu_per_millicore=0.1615`, `n_sat_ticks=34`.
- paymentservice same full-CPU folder 1000m × 1,
  `mu_per_millicore=0.0195`, `n_sat_ticks=20` (CPU never pegged).

Sanity `rho_frozen_report.py` on S1 baseline run24 / S2 baseline run23:
frontend `rho_hat` 1.295 / 1.837 (unchanged vs 50m frontend freeze);
productcatalog `rho_hat` 0.398 / 0.5418 (unchanged); checkout 0.0009206 /
0.00184 (was 0.06168 / 0.1233 from the 1000m 0.1615 freeze); payment
0.01384 / 0.02764 (was 0.5108 / 1.021 from the 1000m 0.0195 freeze).
Checkout `mu_per_millicore` 10.82 vs historical 0.1615 is a linearity
check only — the constrained value is the freeze. Informal band was S1
entry ~0.5–0.8, S2 entry >1 — frontend is still above the S1 band. Do
not treat that band as a pass/fail gate.

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only (reset-aware trigger).
cluster_shape must stay `topfull-worker-1=e2-standard-16` until a full
re-calibration after a VM resize. This table is not auto-applied by
pull_results.py.
