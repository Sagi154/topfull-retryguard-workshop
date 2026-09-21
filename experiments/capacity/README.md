# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-21)

All four minimum-set services were re-frozen from the post-Ron-Nezer
bottleneck-cap recalibration battery on e2-standard-16 (Tasks 1–7
`cpu_limit_millicores: 50` + productcatalog HPA; this battery is Task 8).
`method: "mu_sat"` (`SAT_5XX_FRACTION` still 0.05; `SAT_TAIL_TRIM_TICKS=5`;
`LOW_CONFIDENCE_SAT_TICKS` still 10). **These four values supersede every
2026-09-19 entry** — those freezes predate the Ron-config CPU/replica/HPA
topology and are no longer valid (design doc decision 2). Do **not** reuse
them.

Frontend and productcatalog HPAs were deleted for those two constrained
runs and restored after pull. Checkout/payment/reference left HPAs live.

| Service | Source run | millicores | `mu_per_millicore` | `n_sat_ticks` | peg |
|---|---|---|---|---|---|
| frontend | `campaign_48/calibration_frontend_constrained_50m_run2` | 50m × 1 | 0.26 | 54 (ok) | True (cpu_max 55m of 50m) |
| checkoutservice | `campaign_48/calibration_checkout_constrained_50m_run2` | 50m × 1 | 1.47 | 208 (ok) | True (cpu_max 55m of 50m) |
| paymentservice | `campaign_48/calibration_payment_constrained_50m_run2` | 50m × 1 | 0.24 | 20 (ok) | True (cpu_max 50m of 50m) |
| productcatalogservice | `campaign_48/calibration_productcatalog_constrained_run2` | 50m × 1 | 1.62 | 137 (ok) | True (cpu_max 54m of 50m) |

YAML next-free after this battery: frontend 50m **run3**; checkout 50m
**run3**; payment 50m **run3**; productcatalog constrained **run3**;
bottleneck reference **run2**. Unused 100m constrained slots unchanged
(frontend **run3**, payment **run2**, checkout stays **run1**).

### Reference-load decision (Step 6) — **three separate**, not shared

`calibration_bottleneck_reference_run1` combined `getproduct: 800` +
`postcheckout: 500` (light cart-family 50) at unconstrained Ron-config
paper CPU. That recipe is **not** a shared S3/S4A/S4B baseline:

- Intended bottleneck services stayed healthy at paper CPU:
  checkout fail 0 / CPU max 412m of 615m; payment fail 0 / 37m of 155m;
  productcatalog fail ≈0 / 461m of 1535m.
- Collateral overload: frontend inbound fail 0.664 (5xx 0.660, CPU max
  991m of 1150m); recommendationservice fail 0.384 (CPU max 1155m of
  1150m, pegged). Cart was *not* the side-effect (fail 0, CPU 409m of
  1920m). Ad/email/shipping/currency/redis-cart stayed healthy.

Task 10 must use **three separate reference loads** — one per scenario,
each using only that scenario's own heavy tag (S3: `postcheckout: 500`
alone; S4A: `getproduct: 800` alone; S4B: `postcheckout: 500` alone, light
everything else). Repeat those isolated recipes before locking
non-bottleneck `user_counts`. Do not copy this combined recipe into
S3/S4A/S4B.

### Compound-bottleneck notes (Steps 3–4)

- **Checkout 50m / payment 155m** (`calibration_checkout_constrained_50m_run2`):
  payment was *not* a second bottleneck. Payment `lambda≈2`, fail/5xx=0,
  CPU max 7m of 155m — the 50m checkout starved PlaceOrder.
- **Payment 50m / checkout 615m** (`calibration_payment_constrained_50m_run2`):
  **compound.** Checkout also overloaded (fail 0.764, `n_sat=78`, CPU max
  613m of 615m) while payment was pegged at 50m under `postcheckout: 500`.
  Cart fail 0.027. Pinning payment does not keep checkout healthy at this
  load.

Historical (do **not** reuse — pre-migration 2026-09-19):

- frontend `calibration_frontend_constrained_50m_run1` 50m × 1,
  `mu_per_millicore=0.3`, `n_sat_ticks=26`.
- checkoutservice `calibration_checkout_constrained_50m_run1` 50m × 1,
  `mu_per_millicore=10.82`, `n_sat_ticks=210`.
- paymentservice `calibration_payment_constrained_50m_run1` 50m × 1,
  `mu_per_millicore=0.72`, `n_sat_ticks=26`.
- productcatalogservice `calibration_productcatalog_constrained_run1` 50m × 1,
  `mu_per_millicore=8.95`, `n_sat_ticks=60`.
- frontend `calibration_frontend_constrained_run1` 100m × 1,
  `mu_per_millicore=0.37`, `n_sat_ticks=9` (low confidence).
- checkoutservice `calibration_checkout_payment_full_cpu_run1` 1000m × 1,
  `mu_per_millicore=0.1615`, `n_sat_ticks=34`.
- paymentservice same full-CPU folder 1000m × 1,
  `mu_per_millicore=0.0195`, `n_sat_ticks=20` (CPU never pegged).

Do **not** freeze from S3 RG run8 (checkout is 100m there, not paper).

Freeze (does not modify the run folder):

    python experiments/capacity_frozen.py freeze <run_dir> --service frontend --force

Report (writes rho_frozen_report.md into the run folder):

    python experiments/rho_frozen_report.py <run_dir>

Do not freeze from a TopFull-on plateau and call it the service's true
ceiling. v1 freeze method is mu_sat only (reset-aware trigger).
cluster_shape must stay `topfull-worker-1=e2-standard-16` until a full
re-calibration after a VM resize. This table is not auto-applied by
pull_results.py.
