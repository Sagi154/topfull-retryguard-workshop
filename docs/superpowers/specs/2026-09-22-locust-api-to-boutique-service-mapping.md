# Locust API → Boutique service mapping (S1 try runs 28–33)

## Goal

During Task 9 S1 load calibration (2026-09-22), several baseline holds varied
`locust.user_counts` across the five storefront APIs. Use those runs to map
**which Locust APIs drive which Online Boutique services**, so later load
tuning can predict what raising a given tag will stress.

This is a measurement write-up only. It does **not** lock S1 numbers or start
S2.

## Dataset

All under `experiments/results/campaign_48/S1_normal_op/`, condition
**baseline** (TopFull RL ON, RetryGuard OFF), duration **300 s**, loadgen
`online_boutique_create_v2.sh`, `spawn_rate` 45 (run28) or 50 (run29–33).

| Run | getcart | getproduct | postcart | postcheckout | emptycart | spawn_rate |
|---|---:|---:|---:|---:|---:|---:|
| 28 | 50 | 50 | 50 | 10 | 150 | 45 |
| 29 | 100 | 100 | 100 | 100 | 50 | 50 |
| 30 | 100 | 100 | 50 | 50 | 50 | 50 |
| 31 | 50 | 50 | 50 | 25 | 25 | 50 |
| 32 | 50 | 50 | 25 | 20 | 25 | 50 |
| 33 | 50 | 50 | 50 | 20 | 50 | 50 |

Folders: `baseline_topfull_no_retryguard_normal_op_run{28..33}`.

Inputs used:

- Locust 1 s CSVs (`getcart.csv`, `getproduct.csv`, `postcart.csv`,
  `postcheckout.csv`, `emptycart.csv`) — mid-hold mean **RPS** (skip first
  ~10 and last ~5 rows for spawn/shutdown).
- `service_edges.csv` — Envoy caller→target `total` counter deltas over the
  run.
- `service_inbound.csv` — per-service inbound `total` deltas (sanity /
  aggregate view).

## Method

Least-squares fit across the six runs:

```text
edge_delta ≈ Σ coef_api · api_mean_rps
```

**Caveat (still open):** in every one of these six tries, measured
`getcart` RPS ≈ `postcart` RPS (diff &lt; 0.2). They cannot be separated
statistically. The model uses a combined **`cart_family = getcart +
postcart`** term, plus independent `getproduct`, `postcheckout`, and
`emptycart`. Design-matrix condition number with six runs ≈ **16.3**
(improved from ≈19.4 with five runs).

Do **not** treat negative coefficients as “API X suppresses service Y” —
with only six observations they are collinearity / residual artifacts.
Trust near-zero cross-terms and the raw per-run totals that track a single
API.

## Mapping (what to expect when raising each Locust API)

| Locust API | Services it drives | Notes |
|---|---|---|
| **`getproduct`** | `productcatalogservice` (largest coef), `adservice` (**only** driver), `recommendationservice` (+ fan-out `recommendationservice→productcatalogservice`), `currencyservice`, secondary hit on `cartservice` / `frontend` (page chrome) | Product page. Raising this does **not** load checkout / payment / email. |
| **`postcheckout`** | `checkoutservice`, then checkout fan-out: `cartservice`, `currencyservice`, `emailservice`, `paymentservice`, `shippingservice` | **Only** path that stresses checkout / payment / email. Currency/email/payment ≈ 1 call each per checkout; cart/shipping ≈ 2× in these data. |
| **cart-family** (`getcart` and/or `postcart`) | `cartservice`, `frontend→shippingservice` (shipping quote on cart page), secondary `productcatalogservice` / `currencyservice` / `recommendationservice` | Still not split into get vs post. |
| **`emptycart`** | `cartservice` / `frontend` only | No meaningful downstream fan-out. |

Leaves (no outbound edges in these runs): `paymentservice`, `emailservice`,
`shippingservice`, `currencyservice`, `adservice`. `redis-cart` inbound stayed
~0 across all six runs — known collector limitation for cart→Redis, not proof
of zero Redis traffic.

## Hard checks (raw totals, not just regression)

These edges make the attribution obvious even without the fit:

1. **`frontend→adservice`** tracks **getproduct** only. Runs with ~47
   getproduct RPS all land ~14325 ads totals; both ~94 getproduct runs land
   28650 — independent of cart / checkout / emptycart mixes.
2. **`frontend→shippingservice`** / cart_family ≈ **152** in every run —
   shipping quote is a cart-page effect, not getproduct/postcheckout/emptycart.
3. **Checkout fan-out** (`checkoutservice→currency|email|payment`) moves with
   **postcheckout** RPS, not with cart_family or getproduct.

## Practical use for Task 9 / S3–S4 load design

- Need catalog / ads / recommendations pressure → raise **`getproduct`**.
- Need checkout / payment / email pressure → raise **`postcheckout`** only.
- Need cart / cart-page shipping quote → raise **cart-family** (still
  coupled until a deliberate unbalance).
- Raising **`emptycart`** only adds cart empty calls; do not use it to load
  backends.

## Still needed to split getcart vs postcart

None of runs 28–33 unbalanced the two cart tags. A future hold with e.g.
`getcart: 100, postcart: 10` (and the reverse) would let the same regression
attribute `frontend→cartservice` / `frontend→shippingservice` to one or the
other. Until then, treat them as one lever.

## Related

- Task 9 readout / try log:
  [2026-09-21-s1-s6-methodology-and-calibration-implementation.md](../plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md)
  (S1 try status around run28+).
- Remaining-work tracker:
  [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](2026-09-21-s1-s6-loadgen-numbers-remaining-work.md).
- Loadgen shape (v2 independent swarms, Ron spawn divisor):
  [2026-09-21-loadgen-shape-ron-migration-design.md](2026-09-21-loadgen-shape-ron-migration-design.md).
- Earlier getcart/postcart discussion:
  [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md).
