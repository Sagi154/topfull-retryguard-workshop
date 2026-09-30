# S2 candidate ranking, both-off runs 1-79 (2026-09-30)

Goal: decide which both-off hold (CPU table plus Locust user mix) should be the S2 load. No run was executed for this. Every number comes from the raw CSVs under `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run<N>/`. Nothing is locked; replays are a later decision.

Scorer: [`experiments/s2_both_off_canon.py`](../experiments/s2_both_off_canon.py) (`python experiments/s2_both_off_canon.py 1 79` writes `s2_canon_1_79.json` into the current directory). It keeps every service and every edge; thresholds are applied afterwards. Streak, overloaded ticks, retry edges, sampling gaps and replica dips were cross-checked against eight independent per-range scorings (runs 1-10, 11-20, 21-29, 30-39, 40-49, 50-59, 60-69, 70-79) and agree. Locust per-API figures below come from those scorings, not from the canonical script.

## What you asked to see

| Criterion | How it is measured | Bar used here |
|---|---|---|
| (a) inbound rejection streak | `service_inbound.csv`, `(d5xx + dresets) / dtotal > 0.20`, consecutive 1 s polls, last 5 polls dropped, nine controlled backends | Several services. 30 is the RetryGuard bar; 10 or more is the soft bar because the noise ceiling is 8 |
| (b) overloaded | `topfull_detect.csv` `overloaded=1` ticks per service | 10 or more ticks. 30 is a lot of ticks for this signal; 10 is the bar. Most hot pairs are either under 10 or at 30 or more (of 110 on valid runs, 77 have 10 or more and 73 have 30 or more). Share of at least 0.5 is not required |
| (c) retry storms | `service_edges.csv` positive increments of the cumulative `retry` column per caller to target | Several edges with thousands, preferably backend to backend; retries count most when their target has a streak |
| Locust goodput, Fail, P95 | per-API CSVs | Last priority. A dip is acceptable when it is the overload itself |

## Runs excluded and why

- **Runs 1-2:** old regime (frontend x1, other load recipe); no streaks anywhere.
- **Runs 14-25:** inbound sampling is mostly 2 s or longer (53-70% of gaps at least 1.5 s), and the storefront failed (getproduct, getcart and postcheckout Fail ratio 0.99-1.0, P95 6-10 s). Their only streak is adservice. These are the runs invalid under the sidecar CPU limit, plus the dispense replay.
- **Runs 55-59, 64, 74-79:** 2 s inbound sampling (69-100% of gaps), so a streak of 30 samples is about 60 s and RetryGuard would measure differently.
- **Runs 46, 47, 53:** truncated (337 s mesh span), long (1167 s), and about 70 minutes.

Kept despite minor issues: run 43 (15% of gaps at 2 s, email replica dip), run 54 (8% 2 s gaps), runs 48 and 49 (7% and 9% 2 s gaps), runs 34, 63 (payment replica dip).

## Two lenses, and how they differ

**Lens A, independent pair.** Checkout and recommendations are separate services on separate call paths, so two genuinely separate overloads appear. It has the biggest retry storms (130k-290k on frontend to recommendations), but recommendations streaks are mostly short (13-56; run 5 is 288). Only the frontend retries.

**Lens B, chain depth.** Checkout, payment and email are one chain (payment and email arrival equals checkout arrival), so it shows overload propagating downstream. Streaks are long, and it is the only place with backend-to-backend retries (checkout to payment or email). It is one root cause showing up in several places.

Both lenses rank the same way: services with streak at least 10 and overloaded at least 10 ticks, then streak breadth, then retries on edges whose target has a streak of 10 or more. You wanted both kept in view; this guide does not pick between them.

### Lens A, independent pair

Retries on streaking targets = summed retry delta of edges with at least 1000 retries whose target has a streak of at least 10. `postcheckout` is goodput per configured user.

| Run | Table and mix (getproduct / postcheckout / getcart / postcart / emptycart) | Streaks >= 10 | Overloaded ticks (services at 10 or more) | Retries on streaking targets | Notes |
|---|---|---|---|---|---|
| 11 | Paper, 250/100/100/100/5 | checkout 38, recommendations 22 | checkout 57, recommendations 560 | 289k | postcheckout 0.02 |
| 10 | Paper, 325/80/100/100/5 | checkout 21, recommendations 56 | checkout 53, recommendations 561 | 267k | postcheckout 0.14 |
| 5 | Paper, 300/100/210/20/20 | checkout 90, recommendations 288 | checkout 106, recommendations 515 | 261k | run 3 has the same mix and gave checkout 588, recommendations 1 |
| 69 | Hybrid, 200/250/250/10/10 | checkout 23, recommendations 19 | recommendations 549, checkout 37, email 14 | 230k | one-off on a different table; postcheckout 0.165 |
| 6 | Paper, 340/100/240/10/10 | checkout 173, recommendations 44 | checkout 476, recommendations 558 | 190k | run 65, same counts with frontend x4 only, lost the recommendations streak (2) |
| 4 | Paper, 380/100/270/20/20 | checkout 49, recommendations 13 | checkout 552, recommendations 565 | 160k | marginal recommendations streak |
| 7 | Paper, 380/100/270/20/20 | checkout 230, recommendations 15 | checkout 572, recommendations 511 | 151k | marginal recommendations streak |

Paper table, frontend x4, in runs 4-7, 10 and 11: frontend 1150 m, checkout 615 m, recommendations 1150 m, catalog 1535 m, cart 1920 m, currency 770 m, shipping 770 m, ads 1150 m, payment 155 m, email 155 m, redis-cart 540 m. Run 69 uses the Hybrid table (see [the runs 60-70 guide](2026-09-29-s2-runs-60-70.md)).

### Lens B, chain depth

| Run | Table and mix | Streaks >= 10 | Overloaded ticks (services at 10 or more) | Retries on streaking targets | Backend to backend | Notes |
|---|---|---|---|---|---|---|
| 34 | Agreed, 100/150/100/100/5 | checkout 122, payment 30, email 11 | checkout 386, payment 256, email 18 | 65k | checkout to payment 3,865 | payment at 0 replicas on 6 samples; postcheckout 0.007 |
| 43 | Checkout-4, 200/250/200/50/50 | checkout 147, email 147 | checkout 481, email 566, payment 509 | 85k | checkout to email 2,652 | email at 0 replicas on 2 samples; 15% 2 s gaps; postcheckout 0.16 |
| 63 | Checkout-3 with email 180 m, 150/250/150/20/20 | checkout 549, email 17 | checkout 582, payment 563, email 119 | 139k | checkout to payment 175 | payment at 0 replicas on 1 sample; postcheckout 0.05 |
| 61 | Checkout-3, 200/250/200/50/50 | checkout 271, email 272 | checkout 578, email 588, payment 486 | 98k | checkout to email 99 | no caveats; postcheckout 0.12 |
| 42 | Checkout-3, 150/250/150/20/20 | checkout 185, email 29 | checkout 579, payment 547, email 432 | 115k | none | postcheckout 0.07 |
| 54 | Recs-3, 100/300/100/200/200 | checkout 66, email 176 | checkout 397, email 583, payment 208 | 62k | none | 8% 2 s gaps; postcheckout 0.31 |

Other valid runs that clear only one lens marginally: run 28 (checkout 471, payment 14), run 9 (recommendations 25 only, 344k retries), runs 60, 36, 3, 12, 13, 26, 27, 29, 65, 66 (checkout only), runs 67, 68, 70, 72 (recommendations only). At 10 overloaded ticks, a second service is hot with no streak of 10 on it in runs 9 (checkout 22), 26, 27, 65, 66, and 67 (checkout 10).

## Criterion (b) by itself: how many services are overloaded, and for how many ticks

Counts `overloaded=1` ticks per service (frontend excluded, it is always hot) on the 50 valid runs. Max utilization is not a criterion and is not used anywhere in this guide.

| Services with at least this many overloaded ticks | 5 | 10 | 30 |
|---|---|---|---|
| Runs with 0 | 2 | 2 | 2 |
| Runs with 1 | 21 | 27 | 29 |
| Runs with 2 | 15 | 13 | 13 |
| Runs with 3 | 11 | 8 | 6 |
| Runs with 4 | 1 | 0 | 0 |

Runs with three or more services at 10 or more ticks: 34, 42, 43, 54, 60, 61, 63, 69 (and run 3 has checkout 591, recommendations 38, payment 5, ads 3). Per-service ticks:

| Run | Overloaded ticks per service (3 or more) |
|---|---|
| 43 | email 566, payment 509, checkout 481, ads 6 |
| 63 | checkout 582, payment 563, email 119 |
| 61 | email 588, checkout 578, payment 486 |
| 60 | checkout 580, payment 573, email 176 |
| 54 | email 583, checkout 397, payment 208 |
| 42 | checkout 579, payment 547, email 432 |
| 69 | recommendations 549, checkout 37, email 14, payment 3 |
| 34 | checkout 386, payment 256, email 18 |
| 3 | checkout 591, recommendations 38, payment 5, ads 3 |
| 4, 5, 6, 7, 10, 11 | checkout and recommendations only (checkout 53-572, recommendations 511-565) |
| 26, 27, 65, 66 | checkout and recommendations only (207-592) |

The bar for (b) is 10 overloaded ticks. 30 ticks is a lot for this signal. At 10, run 34's email (18) and run 69's email (14) count, so both of those runs have three services. Three is still the ceiling. It is the checkout chain (checkout, payment, email) except run 69 (recommendations, checkout, email). No run has recommendations plus a chain service plus a third independent service overloaded. The streak soft bar of 10 (criterion a) is a separate number on a different signal.

## Facts that hold across both lenses

- **Backend-to-backend retries:** checkout is the only backend that ever retries into another service. Edges of 100 or more on valid runs: run 34 (checkout to payment 3,865), run 43 (checkout to email 2,652), run 63 (checkout to payment 175). Run 61 (checkout to email 99) is just below 100. Runs 55-59 and 64 also have them but are 2 s sampled.
- **Breadth of streaks:** no valid run has more than three services with a streak of 10 or more, and only run 34 reaches three.
- **Reproducibility:** runs 3 and 5 share a mix and differ (checkout 588 vs 90, recommendations 1 vs 288). Runs 4 and 7 share a mix (checkout 49 vs 230, recommendations 13 vs 15). Runs 42 and 60 share a mix (checkout 185 vs 574, email 29 vs 8). Runs 43 and 61 share counts on different tables (Checkout-4 vs Checkout-3).
- **Goodput:** `postcheckout` goodput per user is 0.001-0.31 in these runs; it is low whenever checkout is the latched service. On Lens B runs the other APIs are mostly healthy (Fail ratio under about 0.2). On Lens A runs browse-API Fail ratios are about 0.5-0.9 (runs 4, 5, 6, 7, 10, 11). Goodput did not change any ordering.

## Where a replay would add information

No replay is planned. If you decide to run some, these rows have the weakest evidence:

- Lens A: runs 4 and 7 (recommendations streak of 13-15), run 69 (single hold on a different table), the paper-table family generally (runs 3 and 5 disagree).
- Lens B: runs 34, 43, 63 (replica dips), run 43 and run 54 (2 s gaps), run 61 (cleanest row; a replay would show whether it is stable).

## Errors found and fixed while writing this

An earlier version of the analysis (same day, chat) contained these mistakes. They are corrected above.

- "Only runs 34 and 43 show backend-to-backend retries": wrong. Counting edges of at least 100, valid runs are 34, 43, 63 (and 61 at 99). I had only counted edges of at least 1000.
- "Run 34 has three services overloaded for at least 30 ticks": wrong at a 30-tick bar. Email has 18, so only checkout and payment cleared 30. The bar is now 10, and at 10 email counts, so run 34 has three. Run 69's email (14) counts the same way; its payment (3) does not.
- "Run 6 is the only independent checkout-plus-recommendations pair": wrong. Runs 4, 5, 6, 7, 10, 11 (and 69) all qualify.
- "Runs 55-59, 64, 74-79 are the only 2 s sampled runs": wrong. Runs 14-25 are as well.
- Run 64 was listed as a breadth outlier; it is 2 s sampled and excluded.
