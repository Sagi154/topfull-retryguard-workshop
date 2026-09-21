# Frozen capacity table

`capacity_frozen.json` stores `mu_per_millicore` for the minimum service
set (frontend, checkoutservice, productcatalogservice, paymentservice).

## Calibration status (2026-09-21-v2)

All four minimum-set services were re-frozen from the Task 8b bottleneck-cap
battery on e2-standard-16 under `online_boutique_create_v2.sh` (Ron's float
`count/RATE` divisor; independent per-tag swarms). `method: "mu_sat"`
(`SAT_5XX_FRACTION` still 0.05; `SAT_TAIL_TRIM_TICKS=5`;
`LOW_CONFIDENCE_SAT_TICKS` still 10). **These four values supersede both
the 2026-09-19 pre-migration entries and Task 8's same-day legacy-launcher
freezes (0.26 / 1.47 / 0.24 / 1.62)** — design doc decision 16b. Only this
generation was measured under the correct launcher. Do **not** reuse the
two earlier generations as ground truth.

Frontend and productcatalog HPAs were deleted for those two constrained
runs and restored after pull. Checkout/payment/reference left HPAs live.

v2's default `HOST` was corrected mid-battery from the unreachable
`http://10.8.0.4:30440` to `http://10.128.0.3:30440` (same NodePort the
legacy `create.sh` hardcodes). `calibration_frontend_constrained_50m_run3`
used the bad HOST (mesh counters frozen, no Locust traffic) and is
**discarded** — do not freeze from it.

| Service | Source run | millicores | `mu_per_millicore` | `n_sat_ticks` | peg |
|---|---|---|---|---|---|
| frontend | `campaign_48/calibration_frontend_constrained_50m_run4` | 50m × 1 | 0.79 | 2 (**low_confidence**) | True (cpu_max 56m of 50m) |
| checkoutservice | `campaign_48/calibration_checkout_constrained_50m_run3` | 50m × 1 | 1.34 | 208 (ok) | True (cpu_max 55m of 50m) |
| paymentservice | `campaign_48/calibration_payment_constrained_50m_run3` | 50m × 1 | 0.30 | 157 (ok) | True (cpu_max 51m of 50m) |
| productcatalogservice | `campaign_48/calibration_productcatalog_constrained_run3` | 50m × 1 | 5.35 | 8 (**low_confidence**) | True (cpu_max 51m of 50m) |

**Do not treat the frontend 2-tick freeze as high-confidence.** The 50m
hold CPU-pegged (56m of 50m, `w_mean≈772 ms`) but inbound
`Δ(5xx+resets)/Δtotal` was only 0.001 — two sat ticks is the same
shutdown-tail class previously rejected (do not reuse 2-tick / 9-tick
frontend freezes). Locked only so the table is one v2 generation; a
heavier storefront mix is needed before this number is trustworthy.

Catalog `n_sat=8` is just under the gate (fail only 0.0067) while
`getproduct: 250` crushed frontend (fail 0.94) and recommendations
(fail 0.54). Accepted as low_confidence because no better v2 reading
exists in this battery.

YAML next-free after this battery: frontend 50m **run5**; checkout 50m
**run4**; payment 50m **run4**; productcatalog constrained **run4**;
bottleneck reference **run3**. Unused 100m constrained slots unchanged
(frontend **run3**, payment **run2**, checkout stays **run1**).

### Reference-load decision (Step 6) — **three separate**, not shared

`calibration_bottleneck_reference_run2` combined `getproduct: 250` +
`postcheckout: 220` (light cart-family 10, `spawn_rate: 50`) at
unconstrained Ron-config paper CPU. Re-evaluated fresh under v2 — Task 8's
"three separate" verdict still holds, for different loads:

- Intended bottlenecks at paper CPU: checkout fail 0.55 / CPU max 613m of
  615m (pegged even unconstrained); payment fail 0.12 / 73m of 155m;
  productcatalog fail ≈0 / 623m of 1535m (healthy).
- Collateral overload: frontend inbound fail 0.545 (5xx 0.544, CPU max
  1114m of 1150m); recommendationservice fail 0.237 (CPU max 1153m of
  1150m, pegged). Shipping fail 0.13 (CPU 63m of 770m). Cart was *not*
  the side-effect (fail 0.006, CPU 274m of 1920m). Ad/email/currency/redis-cart
  stayed healthy.

Task 10 must use **three separate reference loads** — one per scenario,
each using only that scenario's own heavy tag (S3: `postcheckout: 220`
alone; S4A: `getproduct: 250` alone; S4B: `postcheckout: 40` alone —
payment's own constrained-hold tag — light everything else). Repeat those
isolated recipes before locking non-bottleneck `user_counts`. Do not copy
this combined recipe into S3/S4A/S4B.

### Compound-bottleneck notes (Steps 3–4)

- **Checkout 50m / payment 155m** (`calibration_checkout_constrained_50m_run3`):
  payment was *not* a second bottleneck. Payment had **no inbound ticks**
  (`lambda` n/a) — the 50m checkout starved PlaceOrder (checkout fail
  0.771, `n_sat=208`, `mu_sat=67`). Frontend fail 0.821 is collateral.
- **Payment 50m / checkout 615m** (`calibration_payment_constrained_50m_run3`):
  **mild compound.** Payment pegged (`n_sat=157`, fail 0.756, `mu_sat=15`,
  cpu_max 51m of 50m). Checkout also elevated (fail 0.197, `mu_sat=34`,
  just under the 0.20 RetryGuard threshold) under `postcheckout: 40`.
  Much milder than Task 8's `postcheckout: 500` compound (checkout fail
  0.764). Pinning payment still does not keep checkout fully healthy.

### Locust CSV caveat (v2 vs metric_collector ports)

v2 serves Locust stats on `ports_v2/` 91xx–93xx. `metric_collector.py`
still scrapes the legacy 8888+ range, so Locust CSVs in these v2 folders
are header-only. Freeze and the ρ report use `service_inbound.csv` (live).
Do not treat empty `getcart.csv` as "no traffic."

Historical (do **not** reuse — Task 8 legacy launcher, 2026-09-21):

- frontend `calibration_frontend_constrained_50m_run2` 50m × 1,
  `mu_per_millicore=0.26`, `n_sat_ticks=54`.
- checkoutservice `calibration_checkout_constrained_50m_run2` 50m × 1,
  `mu_per_millicore=1.47`, `n_sat_ticks=208`.
- paymentservice `calibration_payment_constrained_50m_run2` 50m × 1,
  `mu_per_millicore=0.24`, `n_sat_ticks=20`.
- productcatalogservice `calibration_productcatalog_constrained_run2` 50m × 1,
  `mu_per_millicore=1.62`, `n_sat_ticks=137`.

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
