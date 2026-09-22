# Locust API → Boutique service mapping (S1 try runs 28–35)

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
| 34 | 75 | 50 | 50 | 20 | 50 | 50 |
| 35 | *(measured, not committed — see below)* | | | | | 50 |

Folders: `baseline_topfull_no_retryguard_normal_op_run{28..35}`.

**Run 34/35 measured RPS** (mid-hold mean, not configured `user_counts` —
run35's YAML edit was not committed before the next try overwrote it, so
this uses the same measured-CSV method as the rest of the table):

| Run | getcart | postcart | getproduct | postcheckout | emptycart |
|---|---:|---:|---:|---:|---:|
| 34 | **70.86** | 47.24 | 47.10 | 18.85 | 47.25 |
| 35 | 47.29 | **70.96** | 47.14 | 18.91 | 47.29 |

Runs 34/35 are a matched pair: `getproduct`/`postcheckout`/`emptycart` are
within noise of each other between the two, and `getcart`/`postcart` are
**swapped** (34 favors getcart ~1.5×, 35 favors postcart ~1.5×, both other
tag pegged near the run33 baseline of ~47). This is the first pair in the
dataset that breaks the getcart≈postcart collinearity called out below.

Inputs used:

- Locust 1 s CSVs (`getcart.csv`, `getproduct.csv`, `postcart.csv`,
  `postcheckout.csv`, `emptycart.csv`) — mid-hold mean **RPS** (skip first
  ~10 and last ~5 rows for spawn/shutdown).
- `service_edges.csv` — Envoy caller→target `total` counter deltas over the
  run.
- `service_inbound.csv` — per-service inbound `total` deltas (sanity /
  aggregate view).

## Method

Least-squares fit across all eight runs:

```text
edge_delta ≈ Σ coef_api · api_mean_rps
```

**Runs 28–33:** measured `getcart` RPS ≈ `postcart` RPS every time (diff
&lt; 0.2), so those six alone cannot separate them — treated as a combined
`cart_family = getcart + postcart` term there. **Runs 34–35 break this**
(see above) and are analyzed two ways:

1. **Full 5-variable least squares** across all 8 runs (`getcart`,
   `getproduct`, `postcart`, `postcheckout`, `emptycart` as independent
   columns). Condition number ≈ **14.2** — better than the 6-run
   `cart_family` fit (≈16.3), but `postcheckout`/`emptycart` coefficients on
   checkout's own fan-out edges are still noisy (sign flips), because those
   two tags are still correlated with each other across the 8 tries.
2. **Matched-pair delta (run34 − run35)** — since every tag *except*
   getcart/postcart is within noise between the two runs, `edge(run34) −
   edge(run35)` isolates the getcart/postcart difference directly, with no
   regression needed. This is the highest-confidence read for that specific
   split and is reported below alongside the 5-variable fit.

Do **not** treat negative coefficients as “API X suppresses service Y” —
with only 8 observations they are collinearity / residual artifacts on the
edges where multiple APIs still move together. Trust near-zero cross-terms,
the matched-pair delta, and the raw per-run totals that track a single API.

## Mapping (what to expect when raising each Locust API)

| Locust API | Services it drives | Notes |
|---|---|---|
| **`getproduct`** | `productcatalogservice` (largest coef), `adservice` (**only** driver), `recommendationservice` (+ fan-out `recommendationservice→productcatalogservice`), `currencyservice`, secondary hit on `cartservice` / `frontend` (page chrome) | Product page. Raising this does **not** load checkout / payment / email. |
| **`postcheckout`** | `checkoutservice`, then checkout fan-out: `cartservice`, `currencyservice`, `emailservice`, `paymentservice`, `shippingservice` | **Only** path that stresses checkout / payment / email. Currency/email/payment ≈ 1 call each per checkout; cart/shipping ≈ 2× in these data. |
| **`getcart`** | `cartservice` (shared with postcart), `frontend→shippingservice` (**getcart-only**, near-zero from postcart), `productcatalogservice`, `currencyservice`, `recommendationservice` (all mostly getcart, see split below) | Viewing the cart is the real fan-out trigger. |
| **`postcart`** | `cartservice` only (shared equally with getcart) | Adding an item barely re-triggers shipping/currency/recommendation/catalog fan-out — see split below. |
| **`emptycart`** | `cartservice` / `frontend` only | No meaningful downstream fan-out. |

Leaves (no outbound edges in these runs): `paymentservice`, `emailservice`,
`shippingservice`, `currencyservice`, `adservice`. `redis-cart` inbound stayed
~0 across all eight runs — known collector limitation for cart→Redis, not
proof of zero Redis traffic.

## Hard checks (raw totals, not just regression)

These edges make the attribution obvious even without the fit:

1. **`frontend→adservice`** tracks **getproduct** only. Runs with ~47
   getproduct RPS all land ~14325 ads totals; both ~94 getproduct runs land
   28650 — independent of cart / checkout / emptycart mixes.
2. **`frontend→shippingservice`** / cart_family ≈ **152** in every run of
   28–33 — shipping quote is a cart-page effect, not
   getproduct/postcheckout/emptycart. Runs 34–35 refine this further: the
   152 was an average over roughly-equal getcart/postcart; it's actually
   ~305 per unit of `getcart` and ~0 per unit of `postcart` (see the
   getcart/postcart split section below).
3. **Checkout fan-out** (`checkoutservice→currency|email|payment`) moves with
   **postcheckout** RPS, not with cart_family or getproduct.

## Practical use for Task 9 / S3–S4 load design

- Need catalog / ads / recommendations pressure → raise **`getproduct`**.
- Need checkout / payment / email pressure → raise **`postcheckout`** only.
- Need cart-page fan-out (shipping quote, currency, recommendations, per-item
  product lookups) → raise **`getcart`**, not `postcart` (see split below).
- Need only `cartservice` load with no fan-out → raise **`postcart`** or
  **`emptycart`** (both hit only `cartservice`).

## getcart vs postcart split — resolved (runs 34–35, 2026-09-22)

Matched-pair delta (run34 minus run35; getcart↔postcart swapped, everything
else held within noise):

| Edge | run34 (getcart-heavy) | run35 (postcart-heavy) | delta | Attribution |
|---|---:|---:|---:|---|
| `frontend→cartservice` | 64650 | 64643 | **7** (noise) | Roughly **equal** — both GET and POST /cart call GetCart |
| `frontend→shippingservice` | 21575 | 14375 | **7200** | **getcart-only** — shipping quote computed on cart *view*, not on add-to-cart |
| `frontend→productcatalogservice` | 236950 | 208145 | **28805** | Mostly getcart — cart view fetches per-item product details; add-to-cart fetches far fewer |
| `frontend→currencyservice` | 77550 | 63150 | **14400** | Mostly getcart — price conversion is a view-render concern |
| `frontend→recommendationservice` | 41650 | 34450 | **7200** | Mostly getcart, and identical in magnitude to the shipping delta |
| `recommendationservice→productcatalogservice` | 41650 | 34450 | **7200** | Tracks recommendationservice exactly (its own fan-out) |

The 5-variable least-squares fit (all 8 runs) agrees with this pattern —
`getcart` coefficients dominate `postcart` on every one of these edges
(e.g. `frontend→shippingservice`: getcart 304.98 vs postcart −0.53;
`frontend→currencyservice`: getcart 659.2 vs postcart 47.5;
`frontend→productcatalogservice`: getcart 1707.4 vs postcart 481.2), while
`frontend→cartservice` gets nearly equal weight from both (306.9 vs 303.7).

**Conclusion:** `getcart` (viewing the cart) is the real driver of the
downstream fan-out (shipping quote, currency conversion, recommendations,
per-item product lookups). `postcart` (adding an item) mostly only adds
one more `cartservice` call and does **not** meaningfully re-trigger that
fan-out. The two are not interchangeable — the old "cart-family" grouping
undercounted `getcart`'s per-request weight and overcounted `postcart`'s.

### Do we need to be more aggressive on the getcart/postcart difference?

**No — the current split (run34 ≈1.5× baseline getcart / run35 ≈1.5×
baseline postcart, a swing of ±~23.6 rps around a ~47 rps baseline) is
already more than enough signal.** Sanity check: the near-zero edges
(`frontend→cartservice`'s delta of 7, and every "wrong-side" coefficient in
the 5-variable fit) sit at ~0.01–1% of the edge's total count, while the
real deltas (7200–28805) are 15–35% of the edge's total count and roughly
20–60× the Poisson noise floor (`sqrt(count)` on totals of 14k–237k is only
~120–490). A bigger swap wouldn't sharpen the conclusion, just spend more
VM time. One optional confirmatory run at a more extreme ratio (e.g.
`getcart: 150, postcart: 10`) would only be useful to check for
**nonlinearity** (e.g. does the productcatalog fan-out scale linearly with
cart size at higher getcart), not to get a cleaner attribution — that's
already solid.

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
