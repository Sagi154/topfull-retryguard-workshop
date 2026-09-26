# Locust API → Boutique service mapping (S1 try runs 28–42)

## Goal

During Task 9 S1 load calibration (2026-09-22 → 2026-09-23), several baseline
holds varied `locust.user_counts` across the five storefront APIs. Use those
runs to map **which Locust APIs drive which Online Boutique services**, so
later load tuning can predict what raising a given tag will stress.

This is a measurement write-up only. It does **not** lock S1 numbers or start
S2. Path-level expectations (call graph, empty-cart checkout): 
[LOCUST-API-PATHS.md](../../../Guides%20and%20Info/LOCUST-API-PATHS.md).

**Regime change at S2 scale — read before reusing this mapping to design
S2/S3/S4 loads.** Every relationship below was measured at S1 scale
(configured counts 15–150/tag, mid-hold RPS all within a few percent of
configured, failure fractions near 0, no sustained retries). At S2 scale
(configured counts 50–400/tag, real CPU saturation), two of the
relationships documented here **stop holding**, confirmed by per-tick
analysis of runs 26–29 in
[2026-09-25-s2-overload-user-count-calibration.md](2026-09-25-s2-overload-user-count-calibration.md):

1. **`postcheckout` → `checkoutservice` is not linear once checkout
   saturates.** At S1 scale (this doc, §"Checkout fan-out moves with
   postcheckout"), raising `postcheckout` raises checkout's edge totals
   roughly proportionally, with no retries in the picture. At S2 scale,
   whether checkout is overloaded depends on a threshold/latching effect:
   if checkout's own completed-request sojourn time settles above Istio's
   500 ms `perTryTimeout`, its own retries (`attempts: 3`) multiply the
   admitted arrival rate 2.3×–3× and pin its CPU at ~99% of quota for the
   rest of the hold, regardless of further changes to `postcheckout`; if
   sojourn settles below 500 ms, the retry multiplier disappears and
   `postcheckout` passes through almost unmultiplied. Configured
   `postcheckout` as low as 50 was enough to fully latch checkout in one
   S2 run, while configured 100 failed to latch in another — the
   determining factor looks like shared frontend/mesh contention with a
   simultaneous `recommendationservice` retry storm, not `postcheckout`'s
   own value. Do not use this doc's postcheckout coefficient to predict
   checkout's overload state at S2 scale.
2. **The confirmation-page contribution to `recommendationservice`
   (documented below under `postcheckout`) only appears when checkout is
   actually completing PlaceOrder requests.** At S1 scale this is true by
   default (checkout isn't saturated, so requests complete). At S2 scale,
   if checkout is in the retry-latched state above, its own goodput can
   fall to ≈0 req/s and the confirmation page essentially never renders —
   recommendations' load reverts to being driven by `getproduct`+`getcart`
   alone, with no measurable `postcheckout` contribution.

Everything else in this doc — the unique-edge attributions (`getproduct`↔
`adservice`, `getcart`↔`frontend→shippingservice`, `postcheckout`↔
checkout/payment/email as a gate, `postcart`/`emptycart`↔cartservice-only)
— held up at S2 scale too: run28 (`postcart=400`) and run29
(`emptycart=430`) both stayed at ~99.4–99.7% achieved/configured with no
spillover into any service outside cartservice/redis-cart, confirming
those two tags' fast-path, no-fan-out behavior extends at least 4×–86×
beyond the S1 range tested here.

**Third caveat, added 2026-09-26:** at S2 scale, even *identical* configured
counts replayed back-to-back have produced substantially different
per-service overload outcomes (two exact-count reruns 300 s apart,
documented in the calibration doc's "runs 3–7" section — one pair moved
checkout's streak 592→90 and recommendations' streak 1→288 on the same
mix). This doc's own S1-scale coefficients were derived from single runs
per matched pair too, at a regime where failure rates are near 0 and this
kind of instability has not been observed — but it is a reason not to
extrapolate this doc's numeric coefficients (not just the two structural
relationships above) as exact multipliers without expecting some run-to-run
noise, at either regime.

## Dataset

All under `experiments/results/campaign_48/S1_normal_op/`, condition
**baseline** (TopFull RL ON, RetryGuard OFF), duration **300 s**, loadgen
`online_boutique_create_v2.sh`, `spawn_rate` 45 (run28) or 50 (run29–42).

| Run | getcart | getproduct | postcart | postcheckout | emptycart | spawn_rate | Role |
|---|---:|---:|---:|---:|---:|---:|---|
| 28 | 50 | 50 | 50 | 10 | 150 | 45 | early mix |
| 29 | 100 | 100 | 100 | 100 | 50 | 50 | early mix |
| 30 | 100 | 100 | 50 | 50 | 50 | 50 | early mix |
| 31 | 50 | 50 | 50 | 25 | 25 | 50 | early mix |
| 32 | 50 | 50 | 25 | 20 | 25 | 50 | early mix |
| 33 | 50 | 50 | 50 | 20 | 50 | 50 | early mix |
| 34 | 75 | 50 | 50 | 20 | 50 | 50 | getcart↔postcart pair |
| 35 | 50 | 50 | 75 | 20 | 50 | 50 | getcart↔postcart pair |
| 36 | 50 | 50 | 50 | **75** | **20** | 50 | postcheckout↔emptycart pair1 |
| 37 | 50 | 50 | 50 | **20** | **75** | 50 | postcheckout↔emptycart pair1 |
| 38 | 50 | 50 | 50 | **100** | **15** | 50 | postcheckout↔emptycart pair2 (wider) |
| 39 | 50 | 50 | 50 | **15** | **100** | 50 | postcheckout↔emptycart pair2 (wider) |
| 40 | **20** | **75** | 50 | 20 | 50 | 50 | getproduct↔getcart pair3 |
| 41 | — | — | — | — | — | 50 | **discarded** (Locust RPS all-zero; mesh partial) |
| 42 | **75** | **20** | 50 | 20 | 50 | 50 | getproduct↔getcart pair3 (retry of run41) |

Folders: `baseline_topfull_no_retryguard_normal_op_run{28..40,42}`. Do not
analyze run41.

**Measured mid-hold mean RPS** (skip first ~10 and last ~5 Locust rows) for
the matched pairs:

| Run | getcart | getproduct | postcart | postcheckout | emptycart |
|---|---:|---:|---:|---:|---:|
| 34 | **70.86** | 47.10 | 47.24 | 18.85 | 47.25 |
| 35 | 47.29 | 47.14 | **70.96** | 18.91 | 47.29 |
| 36 | 47.22 | 47.08 | 47.23 | **64.56** | 18.95 |
| 37 | 47.30 | 47.16 | 47.31 | 18.92 | **71.06** |
| 38 | 47.33 | 47.19 | 47.33 | **87.64** | 14.26 |
| 39 | 47.31 | 47.17 | 47.31 | 14.21 | **94.63** |
| 40 | 18.96 | **70.75** | 47.28 | 18.90 | 47.28 |
| 42 | **70.82** | 18.88 | 47.23 | 18.72 | 47.23 |

Inputs used:

- Locust 1 s CSVs — mid-hold mean **RPS**.
- `service_edges.csv` — Envoy caller→target `total` counter deltas over the
  run.
- `service_inbound.csv` — per-service inbound `total` deltas (sanity /
  aggregate view).

## Method

Least-squares fit:

```text
edge_delta ≈ Σ coef_api · api_mean_rps
```

Across **14 usable runs** (28–40, 42; excl. failed 41) the 5-variable
condition number is ≈ **14.7** (was ≈14.2 on runs 28–35 alone). Matched-pair
deltas, not the condition number, are what closed the remaining splits:

1. **run34 − run35** — getcart↔postcart (held everything else).
2. **run36 − run37** and **run38 − run39** — postcheckout↔emptycart (held
   getproduct/getcart/postcart at 50).
3. **run40 − run42** — getproduct↔getcart (held postcart 50, postcheckout 20,
   emptycart 50).

Do **not** treat negative LS coefficients as “API X suppresses service Y” —
they remain residual artifacts on some checkout fan-out edges (especially
email). Trust near-zero cross-terms, the matched-pair deltas, and the raw
per-run totals that track a single API.

## Mapping (what to expect when raising each Locust API)

| Locust API | Services it drives | Notes |
|---|---|---|
| **`getproduct`** | `adservice` (**only** driver), `productcatalogservice` (higher per-request weight than getcart on `frontend→catalog`), equal share with getcart of `currencyservice` / `recommendationservice`, secondary `cartservice` (cart badge) | Product page. Does **not** load checkout / payment / email. Does **not** hit `frontend→shippingservice`. |
| **`getcart`** | `frontend→shippingservice` (**only** driver of that quote edge), equal share with getproduct of currency / recommendations, `cartservice` (shared with postcart/emptycart), some catalog (per-item) | Cart **view**. Shipping quote is getcart-only. Currency/recommendations are **not** getcart-dominated once getproduct is swapped independently. |
| **`postcart`** | `cartservice` only (shared equally with getcart) | Add-to-cart does **not** re-trigger shipping / currency / recommendation / catalog fan-out. |
| **`emptycart`** | `frontend→cartservice` only | No checkout / payment / email / shipping / catalog fan-out. |
| **`postcheckout`** | `checkoutservice`, then checkout fan-out: `paymentservice`, `emailservice`, `shippingservice` (quote+ship), `currencyservice`, `cartservice` (GetCart + EmptyCart), confirmation-page recommendations | **Only** path to checkout / payment / email. Per-item catalog inside checkout is usually empty (Locust checkout users never add items — see LOCUST-API-PATHS.md). |

Leaves (no outbound edges in these runs): `paymentservice`, `emailservice`,
`shippingservice`, `currencyservice`, `adservice`. `redis-cart` inbound stayed
~0 — known collector limitation for cart→Redis, not proof of zero Redis traffic.

## Hard checks (raw totals, not just regression)

1. **`frontend→adservice`** tracks **getproduct** only. Flat across every
   checkout/emptycart swap (14325 when getproduct ≈47). Pair3: 21500
   (getproduct-heavy) vs 5750 (getcart-heavy).
2. **`frontend→shippingservice`** tracks **getcart** only. Flat across every
   checkout/emptycart swap (14375 when getcart ≈47). Pair3: 5770 vs 21550.
   Runs 34–35: ~305 per unit of getcart, ~0 from postcart.
3. **Checkout fan-out** (`frontend→checkoutservice`,
   `checkoutservice→payment|email|shipping|currency`) moves with
   **postcheckout**. Ads and cart-page shipping stay flat on those swaps.
4. **`frontend→cartservice`** moves with **emptycart** on the
   checkout/empty swaps (and equally with getcart/postcart otherwise). Do
   not use cart totals as a checkout discriminator.

## Practical use for Task 9 / S3–S4 load design

- Need **ads** or extra **catalog** (product-page weight) → raise
  **`getproduct`**.
- Need **cart-page shipping quote** → raise **`getcart`**, not `postcart`.
- Need **currency / recommendations** → either `getproduct` or `getcart`
  works about equally per request; choose based on ads vs shipping quote.
- Need checkout / payment / email → raise **`postcheckout`** only.
- Need only `cartservice` with no fan-out → raise **`postcart`** or
  **`emptycart`**.

## getcart vs postcart split — resolved (runs 34–35, 2026-09-22)

Matched-pair delta (run34 minus run35; getcart↔postcart swapped, everything
else held within noise):

| Edge | run34 (getcart-heavy) | run35 (postcart-heavy) | delta | Attribution |
|---|---:|---:|---:|---|
| `frontend→cartservice` | 64650 | 64643 | **7** (noise) | Roughly **equal** — both GET and POST /cart call GetCart |
| `frontend→shippingservice` | 21575 | 14375 | **7200** | **getcart-only** — shipping quote on cart *view* |
| `frontend→productcatalogservice` | 236950 | 208145 | **28805** | Mostly getcart vs postcart (postcart fetches far fewer) |
| `frontend→currencyservice` | 77550 | 63150 | **14400** | Moves with getcart when postcart is the other arm |
| `frontend→recommendationservice` | 41650 | 34450 | **7200** | Same magnitude as shipping delta vs postcart |
| `recommendationservice→productcatalogservice` | 41650 | 34450 | **7200** | Tracks recommendationservice |

**Conclusion vs postcart:** `getcart` drives the cart-page fan-out;
`postcart` mostly adds one more `cartservice` call. They are not
interchangeable. A bigger getcart/postcart swing is **not** needed (noise
floor already 20–60× below the real deltas).

## postcheckout vs emptycart split — resolved (runs 36–39, 2026-09-23)

Held getproduct/getcart/postcart at 50. Pair1 swaps through 75/20; pair2
through 100/15.

| Edge | run36−37 delta | run38−39 delta | Attribution |
|---|---:|---:|---|
| `frontend→checkoutservice` | +8301 | +10312 | **postcheckout** |
| `checkoutservice→paymentservice` | +5599 | +6470 | **postcheckout** |
| `checkoutservice→emailservice` | +531 | +1475 | **postcheckout** (smaller than payment; still tracks) |
| `checkoutservice→shippingservice` | +11234 | +14148 | **postcheckout** (~2× payment) |
| `checkoutservice→currencyservice` | +8265 | +10202 | **postcheckout** |
| `frontend→cartservice` | −15805 | −24420 | **emptycart** (more empty → more cart calls) |
| `frontend→adservice` | **0** | **0** | held getproduct |
| `frontend→shippingservice` | **0** | **0** | held getcart |
| `checkoutservice→productcatalogservice` | **0** | **0** | empty-cart checkout (expected) |

Pair2’s per-request multipliers are in the same direction as pair1 but not
identical (e.g. `frontend→checkoutservice` delta / Δpostcheckout_rps ≈ 182
on pair1 vs ≈ 140 on pair2). Treat as mild nonlinearity / hold noise; do
**not** average into one coefficient. Direction and unique-edge attribution
are solid. The 5-variable LS still shows an occasional sign flip on
`checkoutservice→emailservice`; trust the matched pairs for that edge.

## getproduct vs getcart split — resolved (runs 40 & 42, 2026-09-23)

Held postcart 50, postcheckout 20, emptycart 50. Swapped getproduct/getcart
through 75/20. (run41 discarded — Locust CSVs all-zero; rerun as run42.)

| Edge | run40 (product-heavy) | run42 (cart-heavy) | delta | Attribution |
|---|---:|---:|---:|---|
| `frontend→adservice` | 21500 | 5750 | **+15750** | **getproduct-only** |
| `frontend→shippingservice` | 5770 | 21550 | **−15780** | **getcart-only** |
| `frontend→productcatalogservice` | 200975 | 185375 | **+15600** | **Mostly getproduct** per request at this mix |
| `frontend→currencyservice` | 60290 | 60344 | **−54** (noise) | **Equal** — both pages convert / list currency |
| `frontend→recommendationservice` | 33020 | 33050 | **−30** (noise) | **Equal** — both pages recommend |
| `frontend→cartservice` | 56020 | 56050 | **−30** (noise) | Both touch cart (badge vs GetCart) |
| `frontend→checkoutservice` / payment / email | flat | flat | **0** | held postcheckout |

**Conclusion:** Unique edges match the path guide (ads vs cart-page shipping
quote). On the **shared** services, currency and recommendations are
essentially equal per request between getproduct and getcart — raising either
loads them the same. Catalog has a getproduct bias at this mix (product page
always hits GetProduct + recommendations→ListProducts; getcart’s per-item
loop depends on cart contents under concurrent emptycart). Earlier runs 34–35
could not see this: they held getproduct fixed while swapping getcart/postcart,
so currency/recommendation deltas looked “mostly getcart” only relative to
postcart.

## Related

- Path guide:
  [LOCUST-API-PATHS.md](../../../Guides%20and%20Info/LOCUST-API-PATHS.md).
- Task 9 readout / try log:
  [2026-09-21-s1-s6-methodology-and-calibration-implementation.md](../plans/2026-09-21-s1-s6-methodology-and-calibration-implementation.md).
- Remaining-work tracker:
  [2026-09-21-s1-s6-loadgen-numbers-remaining-work.md](2026-09-21-s1-s6-loadgen-numbers-remaining-work.md).
- Loadgen shape (v2 independent swarms, Ron spawn divisor):
  [2026-09-21-loadgen-shape-ron-migration-design.md](2026-09-21-loadgen-shape-ron-migration-design.md).
- Earlier getcart/postcart discussion:
  [2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md](2026-09-20-loadgen-getcart-postcart-and-load-scaling-design.md).
