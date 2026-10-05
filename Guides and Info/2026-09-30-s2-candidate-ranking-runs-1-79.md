# S2 candidate ranking, both-off runs 1-153 (2026-09-30, extended 2026-10-02, 2026-10-03, 2026-10-05)

The file name still says 1-79 so existing links keep working. Runs 1-79 are ranked in the sections below (unchanged). The covered range is runs 1-153. **Runs 80-93, added 2026-10-02, are ranked in [Runs 80-93](#runs-80-93-added-2026-10-02)**, because they were scored against a third bar (the blend bar) and include the first replayed blend. **Runs 94-107, added 2026-10-03, are ranked in [Runs 94-107](#runs-94-107-added-2026-10-03).** **Runs 108-153, added 2026-10-05, are the two latch-probe series and are ranked in [Runs 108-153](#runs-108-153-added-2026-10-05).**

Goal: decide which both-off hold (CPU table plus Locust user mix) should be the S2 load. Every number comes from the raw CSVs under `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run<N>/`. Nothing is locked; replays are a later decision.

Scorer: [`experiments/s2_both_off_canon.py`](../experiments/s2_both_off_canon.py) (`python experiments/s2_both_off_canon.py 1 93` writes `s2_canon_1_93.json` into the current directory). It keeps every service and every edge; thresholds are applied afterwards. Streak, overloaded ticks, retry edges, sampling gaps and replica dips were cross-checked against eight independent per-range scorings (runs 1-10, 11-20, 21-29, 30-39, 40-49, 50-59, 60-69, 70-79) and agree. Locust per-API figures below come from those scorings, not from the canonical script.

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

- **Run 85 (campaign), added 2026-10-02:** mesh span 903 s (over the 900 s gate), one 132 s all-service scrape hole, recommendationservice missing from 79 kubelet polls. **Copy-verification run85 and run86** (`experiments/results/copy verification/`, a different cluster; copy 85 had frontend at 3 replicas, copy 86 is Hybrid with 65% 2 s gaps) are reference only, not ranked.

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

## Runs 80-93 (added 2026-10-02)

Runs 80-93 are scored with the same canon script and the same sampling gate (`gap2_pct` at most 10, span 480-900 s, at least 500 Locust rows). The streaks below match `s2_canon_80_93.json`; four independent rescorings of the raw CSVs agreed on all 14 runs with no mismatch. Per-run detail (CPU tables, Locust, caveats): [Paper-C1 scorecard](2026-10-01-s2-paper-c1-runs-80-84-88.md), [lens-blend results](2026-09-30-s2-lens-blend-results.md), and the copy-verification notes ([run85](2026-10-01-s2-copy-verification-run85.md), [run86](2026-10-01-s2-copy-verification-run86.md)) for the two reference holds. No guide covers the per-service tables of runs 89-93 yet; their numbers are here.

### The blend bar

The lens-blend series needed one more bar than Lens A or Lens B: **recommendations streak and ov at least 10, checkout streak and ov at least 10, and email or payment ov at least 10** (a leaf streak is better but not required). All three is a **blend**. Two cleared, with the missing row at streak or ov of at least 5, is a **near-miss**. Retries, goodput and utilization decide nothing. Frontend is excluded.

### Tables

All runs: both controllers off, 600 s, `spawn_rate` 50, frontend pinned at 4 (HPA 4/4) on every resource poll. **Paper-C1** = paper CPU except checkout 800 m, catalog 800 m, cart 800 m, email 120 m; recommendations 1150 m x 1; sidecar request 100 m, no limit. Runs 80-84 ran on 2026-09-30 and 85-93 on 2026-10-01, after an 18 h stop. Mixes are getproduct / postcheckout / getcart / postcart / emptycart. Retries on streaking targets = summed edges of at least 1000 whose target has a streak of at least 10. No backend-to-backend retry edge of 100 or more exists on any run 80-93 (every large edge is frontend to one target).

| Run | Table, mix | Recs streak / ov | Checkout streak / ov | Email ov | Payment ov | Verdict | Retries on streaking targets | Replay |
|---|---|---|---|---|---|---|---|---|
| 86 | Paper-C1, 275/80/100/90/5 | 226 / 456 | 108 / 163 | 22 | 16 | **blend** | 228k | 88 also a blend |
| 89 | Paper-C1, 275/90/100/90/5 | 238 / 485 | 58 / 164 | 23 | 0 | **blend** | 234k | 92 near-miss |
| 87 | Paper-C1, 275/70/100/90/5 | 118 / 449 | 19 / 86 | 28 | 2 | **blend** | 222k | none |
| 88 | replay of 86 | 175 / 446 | 15 / 58 | 21 | 1 | **blend** | 238k | of 86 |
| 93 | replay of 90 | 359 / 544 | 18 / 50 | 8 | 18 | **blend** (leaf is payment) | 261k | of 90 (near-miss) |
| 92 | replay of 89 | 454 / 480 | 59 / 128 | 6 | 5 | near-miss (leaf 6 ticks) | 245k | of 89 (blend) |
| 90 | Paper-C1, 265/90/100/90/5 | 281 / 305 | 228 / 303 | 8 | 2 | near-miss (leaf 8 ticks) | 174k | 93 blend |
| 91 | Paper-C1, 275/80/100/50/50 | 0 / 29 | 564 / 591 | 10 | 19 | near-miss (recs streak 0) | 56k | none |
| 80 | Paper-C1, 325/80/100/90/5 | 0 / 17 | 549 / 579 | 17 | 0 | near-miss (recs streak 0) | 52k | 84 miss |
| 81 | Paper-C3, 250/100/100/100/5 | 0 / 0 | 563 / 585 | 5 | 37 | miss | 63k | none |
| 82 | Hybrid-C2, 170/210/200/10/10 | 1 / 492 | 25 / 104 | 6 | 0 | miss (recs streak 1) | 20k | none |
| 83 | Paper-C1, 375/80/100/90/5 | 6 / 566 | 0 / 24 | 8 | 0 | miss | 0 | none |
| 84 | replay of 80 | 2 / 540 | 0 / 157 | 29 | 0 | miss | 0 | of 80 (near-miss) |
| 85 | Paper-C1, 325/60/100/90/5 (mix uncertain) | 70 / 298 | 3 / 33 | 12 | 0 | near-miss, **fails sampling** | 178k | none |

Run 85's mix comes from `AGENTS.md`; the YAML before the hold says postcheckout 80, so treat the postcheckout count as uncertain. The 2026-10-01 scorecard and `AGENTS.md` quote some streaks without the last-5 trim (run 86 recommendations 229, run 90 284, run 91 567); the canon values above are 226, 281, 564.

### Ranking of the new runs

1. **Run 86** is the best single row on the new bars. Recommendations 226 / 456 and checkout 108 / 163 both clear 30 streak and 100 ticks, and email (22) and payment (16) are both over 10 ticks, so it is the first run with **four** services at 10 or more overloaded ticks. Its replay (88) also blended.
2. **Run 89.** Recommendations 238 and checkout 58 both clear 30; the leaf (email 23 ticks) is thin, and the replay (92) fell to a near-miss by 4 ticks (email 6).
3. **Run 87**, then **run 88** and **run 93.** All three blend, but checkout streaks are 15-19 (above the soft bar of 10, below the RetryGuard bar of 30).
4. Near-misses, in order of how close: **92** (recs 454, checkout 59, leaf 6 ticks), **90** (checkout 228, recs 281, leaf 8 ticks), **91** and **80** (checkout only, recs streak 0), then **85**.
5. Misses: 81, 82, 83, 84.

**Both lenses, deliberately kept apart.** Runs 86, 87, 88 and 89 also satisfy Lens A (checkout plus recommendations both at streak and ov of at least 10). Run 86 and 93 add a payment tick count in the chain. Run 91 and run 80 are Lens B only, with long checkout streaks and no recommendations streak, and retries only on frontend to checkout. Nothing in 80-93 beats runs 34, 43 or 63 on backend-to-backend retries.

### What the new runs change

- **Reproducibility is still weak, but the family is better than a single hold.** Runs 86, 87 and 88 (the 275 getproduct, 70-80 postcheckout mix) are three blends in a row. Of the four replay pairs: 80 to 84 did not reproduce (checkout 549 became 0; recommendations ov 17 became 540), 86 to 88 did (blend both times, but the checkout streak fell from 108 to 15), 89 to 92 did not (blend, then near-miss), 90 to 93 did not (near-miss, then blend). Only one replay of a blend stayed a blend.
- **The recommendations streak moved from 0 or 1-6 (runs 80-84) to 70-454 (runs 85-93, except run 91) without a large mix change.** Runs 80 and 84 share a mix and a pin and landed in opposite regimes: run 80 is the checkout-latched regime (checkout sojourn 482 ms, 549 reset polls, recommendations sojourn 111 ms), run 84 the unlatched one (checkout 95 ms; recommendations retries 149,129 but only 42 polls above 0.20). Runs 86 and 88 sit in the second regime with a higher reset fraction (0.23 and 0.30 against 0.15), which pushes the mean over 0.20. The cause of the higher reset fraction after the 18 h stop is not identified. Run 91 (275/80/100/50/50, same three browse counts as run 86) returned to the checkout-latched regime, which fits the bistable latch described in the calibration spec better than a proportional load effect. That is an inference, not a demonstrated cause.
- **The leaf service is thin.** Email and payment ov values of 16-28 on the blends sit between the 10-tick bar and the "most hot pairs are under 10 or over 30" gap noted earlier. Run 92 lost its blend by 4 ticks. Treat the leaf as weaker evidence than the recommendations and checkout rows.
- **Retries are large on every blend (222k-261k on frontend to recommendations).** You said you do not want to recreate retry counts near 100k or more for recommendations. Every row that clears the recommendations bar here has them; the only low-retry rows (51-63k, runs 80, 81, 91) are checkout-only. Retry volume was not used for ranking, but it is a cost of choosing any of runs 86-93.
- **The ceiling of "three services" no longer holds.** Run 86 has four services at 10 or more overloaded ticks (recommendations, checkout, email, payment). The streak ceiling of three (only run 34) still holds; no new run has more than two services at a streak of 10 or more.
- **Goodput.** `postcheckout` goodput per run is 1.3-9.7 req/s (Fail ratio 0.84-0.97) on runs 85-93 and browse Fail ratios are 0.38-0.93, except run 91 where getproduct Fail is 0. Goodput did not change the order.

### Where a replay would add information (updated)

The replays of run 86 and run 89 are runs 99–104, and [Runs 94-107](#runs-94-107-added-2026-10-03) is where their result lives. Run 87 has no replay. Run 85 would need a full re-run to pass sampling.

## Runs 94-107 (added 2026-10-03)

These numbers are canon streaks (last 5 inbound polls dropped), so they can differ by a few from [2026-10-03-s2-paper-c1-runs-99-107.md](2026-10-03-s2-paper-c1-runs-99-107.md) and from [2026-10-02-s2-paper-c1-run86-run89-replay.md](2026-10-02-s2-paper-c1-run86-run89-replay.md), which use `s2_both_off_abc.py`. Folders for 94–107 are `experiments/results/new vms/`.

Verdict uses the blend bar from [Runs 80-93](#runs-80-93-added-2026-10-02): recommendations streak and ov at least 10, checkout streak and ov at least 10, and email or payment ov at least 10. Two of those three, with the missing row at streak or ov of at least 5, is a near-miss. Retries on streaking targets are summed edges of at least 1000 whose target has a streak of at least 10. Mixes are getproduct / postcheckout / getcart / postcart / emptycart. Every row is Paper-C1, both controllers off, 600 s.

No run in 94–107 failed the sampling gate. Every span is 687–693 s and every `gap2_pct` is 0, except run 100 at 2.

| Run | Table, mix | Recs streak / ov | Checkout streak / ov | Email ov | Payment ov | Verdict | Retries on streaking targets | Replay |
|---|---|---|---|---|---|---|---|---|
| 94 | Paper-C1, 275/90/100/90/5 | 0 / 0 | 561 / 590 | 16 | 10 | miss | 61k | of 89 |
| 95 | Paper-C1, 275/90/100/90/5 | 0 / 0 | 564 / 591 | 11 | 0 | miss | 62k | of 89 |
| 96 | Paper-C1, 275/90/100/90/5 | 0 / 0 | 566 / 592 | 10 | 0 | miss | 62k | of 89 |
| 97 | Paper-C1, 275/90/100/90/5 | 64 / 545 | 23 / 123 | 36 | 7 | **blend** | 218k | of 89 |
| 98 | Paper-C1, 275/80/100/90/5 | 250 / 567 | 0 / 24 | 14 | 0 | near-miss (checkout streak 0) | 311k | of 86 |
| 99 | Paper-C1, 275/90/100/90/5 | 97 / 274 | 290 / 318 | 18 | 7 | **blend** | 152k | of 89 |
| 100 | Paper-C1, 275/90/100/90/5 | 0 / 0 | 548 / 590 | 13 | 4 | miss | 63k | of 89 |
| 101 | Paper-C1, 275/90/100/90/5 | 77 / 192 | 375 / 412 | 20 | 4 | **blend** | 118k | of 89 |
| 102 | Paper-C1, 275/80/100/90/5 | 0 / 0 | 537 / 586 | 32 | 0 | miss | 53k | of 86 |
| 103 | Paper-C1, 275/80/100/90/5 | 0 / 0 | 546 / 585 | 26 | 0 | miss | 54k | of 86 |
| 104 | Paper-C1, 275/80/100/90/5 | 0 / 0 | 546 / 584 | 25 | 0 | miss | 54k | of 86 |
| 105 | Paper-C1, 275/85/100/90/5 | 207 / 522 | 42 / 74 | 15 | 0 | **blend** | 242k | none |
| 106 | Paper-C1, 275/85/100/90/5 | 0 / 0 | 559 / 593 | 17 | 0 | miss | 58k | of 105 |
| 107 | Paper-C1, 275/85/100/90/5 | 0 / 0 | 561 / 594 | 16 | 1 | miss | 59k | of 105 |

### Ranking of these rows

Runs 99–101 are the run 89 mix (275/90/100/90/5). Run 89 was a blend. Run 99 and run 101 agreed: both are blends (99 is recommendations 97 / 274 and checkout 290 / 318, email 18; 101 is recommendations 77 / 192 and checkout 375 / 412, email 20). Run 100 did not: it is a miss, recommendations 0 / 0, checkout latched at 548 / 590.

Runs 102–104 are the run 86 mix (275/80/100/90/5). Run 86 was a blend. None of the three agreed. Run 102, run 103, and run 104 are misses: recommendations stays 0 / 0 and checkout is latched (streaks 537, 546, and 546).

Runs 105–107 are the first holds of 275/85/100/90/5. Run 105 blended (recommendations 207 / 522, checkout 42 / 74, email 15). Run 106 and run 107 did not blend: both are misses, with checkout latched and recommendations at 0 / 0.


## Runs 108-153 (added 2026-10-05)

Two latch-probe series on the run 89 mix (275/90/100/90/5, Paper-C1, both controllers off, 600 s). Plans: [2026-10-03-s2-latch-probe-holds.md](../docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md) (runs 108-127) and [2026-10-04-s2-latch-probe-v2-holds.md](../docs/superpowers/plans/2026-10-04-s2-latch-probe-v2-holds.md) (runs 132-153). Runs 128-131 are the `ck_rep2_pc120` and control follow-up between them. Service tables: [2026-10-04-s2-latch-probe-abc.md](2026-10-04-s2-latch-probe-abc.md) and [2026-10-04-s2-latch-probe-v2-abc.md](2026-10-04-s2-latch-probe-v2-abc.md). Class and arm verdicts: [2026-10-03-s2-latch-probe-results.md](2026-10-03-s2-latch-probe-results.md) and [2026-10-04-s2-latch-probe-v2-results.md](2026-10-04-s2-latch-probe-v2-results.md). Folders are under `experiments/results/new vms/`.

These are not a candidate search. Each hold changes one lever from the run 89 mix to find what decides the mode, so the Treatment column names the lever. The numbers are canon streaks (last 5 inbound polls dropped) from `s2_both_off_canon.py`, scored with the same blend bar as [Runs 80-93](#runs-80-93-added-2026-10-02). Retries on streaking targets are summed `service_edges.csv` increments of at least 1000 whose target has a streak of at least 10. Class is the label from `s2_latch_probe.py`: sticky is checkout streak at least 400 with recommendations streak 0, released is frontend to recommendations retries of at least 70,000 and not sticky, anything else is other. Streaks can differ by a few from the probe guides, which use their own scorer.

Excluded: run 116 (sampling gate, `total.csv` 4 rows), run 127 (not run), and runs 136 and 138 (sampling gate, 152 and 169 Locust rows; runs 152 and 153 replaced them). Run 143 has a 134 s inbound hole but kept a 697 s span, so it is kept. Forty-two holds are ranked.

| Run | Treatment | Change from the run 89 mix | Mix | Recs streak / ov | Checkout streak / ov | Email ov | Payment ov | Verdict | Retries on streaking targets | Class |
|---|---|---|---|---|---|---|---|---|---|---|
| 108 | restart | pods rolled in-run | 275/90/100/90/5 | 555 / 558 | 12 / 36 | 11 | 4 | **blend** | 293k | released |
| 109 | spawn10 | spawn_rate 10 | 275/90/100/90/5 | 11 / 321 | 283 / 379 | 24 | 1 | **blend** | 133k | released |
| 110 | recs_cpu1000 | recs 1000 m | 275/90/100/90/5 | 42 / 506 | 496 / 548 | 13 | 1 | **blend** | 80k | other |
| 111 | control | none | 275/90/100/90/5 | 69 / 387 | 181 / 252 | 21 | 0 | **blend** | 160k | released |
| 112 | ck_rep2 | checkout 2x800 m | 275/90/100/90/5 | 145 / 558 | 0 / 0 | 34 | 0 | miss | 225k | released |
| 113 | ck_cpu1000 | checkout 1000 m | 275/90/100/90/5 | 143 / 557 | 0 / 25 | 28 | 0 | near-miss (checkout) | 239k | released |
| 114 | recs_users310 | getproduct 310 | 310/90/100/90/5 | 185 / 561 | 9 / 40 | 12 | 0 | near-miss (checkout) | 227k | released |
| 115 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 116 / 547 | 11 / 12 | 142 | 4 | **blend** | 219k | released |
| 117 | pc120 | postcheckout 120 | 275/120/100/90/5 | 136 / 561 | 19 / 92 | 36 | 0 | **blend** | 233k | released |
| 118 | recs_users310 | getproduct 310 | 310/90/100/90/5 | 124 / 564 | 0 / 31 | 16 | 0 | near-miss (checkout) | 241k | released |
| 119 | ck_rep2 | checkout 2x800 m | 275/90/100/90/5 | 21 / 449 | 0 / 0 | 125 | 0 | miss | 170k | released |
| 120 | spawn10 | spawn_rate 10 | 275/90/100/90/5 | 45 / 593 | 14 / 69 | 15 | 0 | **blend** | 214k | released |
| 121 | control | none | 275/90/100/90/5 | 156 / 560 | 11 / 48 | 12 | 0 | **blend** | 228k | released |
| 122 | ck_cpu1000 | checkout 1000 m | 275/90/100/90/5 | 560 / 563 | 0 / 23 | 21 | 0 | near-miss (checkout) | 279k | released |
| 123 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 20 / 530 | 20 / 19 | 204 | 12 | **blend** | 197k | released |
| 124 | restart | pods rolled in-run | 275/90/100/90/5 | 0 / 0 | 567 / 590 | 10 | 2 | miss | 64k | sticky |
| 125 | pc120 | postcheckout 120 | 275/120/100/90/5 | 0 / 0 | 549 / 589 | 13 | 0 | miss | 87k | sticky |
| 126 | recs_cpu1000 | recs 1000 m | 275/90/100/90/5 | 0 / 98 | 564 / 591 | 14 | 4 | near-miss (recs) | 64k | sticky |
| 128 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 55 / 472 | 20 / 39 | 431 | 30 | **blend** | 190k | released |
| 129 | control | none | 275/90/100/90/5 | 0 / 0 | 558 / 590 | 17 | 0 | miss | 62k | sticky |
| 130 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 19 / 495 | 11 / 12 | 332 | 10 | **blend** | 190k | released |
| 131 | control | none | 275/90/100/90/5 | 0 / 1 | 559 / 590 | 18 | 0 | miss | 62k | sticky |
| 132 | control | none | 275/90/100/90/5 | 50 / 508 | 10 / 329 | 109 | 0 | **blend** | 168k | released |
| 133 | spawn10 | spawn_rate 10 | 275/90/100/90/5 | 38 / 584 | 8 / 164 | 37 | 0 | near-miss (checkout) | 202k | released |
| 134 | control | none | 275/90/100/90/5 | 23 / 379 | 158 / 271 | 51 | 0 | **blend** | 164k | released |
| 135 | ck_cpu1000_pc120 | checkout 1000 m, postcheckout 120 | 275/120/100/90/5 | 6 / 388 | 116 / 262 | 156 | 0 | near-miss (recs) | 23k | released |
| 137 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 15 / 541 | 14 / 19 | 350 | 9 | **blend** | 190k | released |
| 139 | control | none | 275/90/100/90/5 | 0 / 0 | 562 / 589 | 12 | 1 | miss | 61k | sticky |
| 140 | ck_rep2_pc120_spawn10 | checkout 2x800 m, postcheckout 120, spawn_rate 10 | 275/120/100/90/5 | 3 / 301 | 16 / 24 | 411 | 2 | near-miss (recs) | 2k | released |
| 141 | ck_cpu1000_pc120_spawn10 | checkout 1000 m, postcheckout 120, spawn_rate 10 | 275/120/100/90/5 | 0 / 0 | 303 / 599 | 4 | 0 | miss | 77k | other |
| 142 | spawn10 | spawn_rate 10 | 275/90/100/90/5 | 0 / 0 | 599 / 606 | 1 | 1 | miss | 61k | sticky |
| 143 | control | none | 275/90/100/90/5 | 0 / 0 | 368 / 410 | 11 | 0 | miss | 57k | other |
| 144 | recs_cpu1000_spawn10 | recs 1000 m, spawn_rate 10 | 275/90/100/90/5 | 0 / 19 | 600 / 606 | 1 | 0 | miss | 61k | sticky |
| 145 | ck_rep2_pc120_spawn10 | checkout 2x800 m, postcheckout 120, spawn_rate 10 | 275/120/100/90/5 | 9 / 398 | 9 / 10 | 345 | 1 | miss | 0k | released |
| 146 | ck_cpu1000_pc120 | checkout 1000 m, postcheckout 120 | 275/120/100/90/5 | 19 / 364 | 113 / 254 | 142 | 0 | **blend** | 158k | released |
| 147 | control | none | 275/90/100/90/5 | 0 / 0 | 558 / 591 | 19 | 0 | miss | 62k | sticky |
| 148 | recs_cpu1000 | recs 1000 m | 275/90/100/90/5 | 0 / 156 | 561 / 590 | 16 | 0 | near-miss (recs) | 63k | sticky |
| 149 | ck_cpu1000_pc120_spawn10 | checkout 1000 m, postcheckout 120, spawn_rate 10 | 275/120/100/90/5 | 0 / 2 | 601 / 604 | 4 | 0 | miss | 77k | sticky |
| 150 | ck_rep2_pc120 | checkout 2x800 m, postcheckout 120 | 275/120/100/90/5 | 24 / 551 | 15 / 17 | 223 | 13 | **blend** | 215k | released |
| 151 | control | none | 275/90/100/90/5 | 4 / 515 | 53 / 154 | 34 | 0 | near-miss (recs) | 5k | released |
| 152 | recs_cpu1000_spawn10 | recs 1000 m, spawn_rate 10 | 275/90/100/90/5 | 0 / 266 | 302 / 600 | 0 | 0 | miss | 56k | other |
| 153 | recs_cpu1000 | recs 1000 m | 275/90/100/90/5 | 17 / 449 | 121 / 148 | 15 | 0 | **blend** | 212k | released |

### Ranking of these rows

- **Blends: 17 of 42.** Runs 108, 109, 110, 111, 115, 117, 120, 121, 123, 128, 130, 132, 134, 137, 146, 150, 153. Every blend has 80k to 293k retries on streaking targets, in line with runs 80-107.
- **Deepest checkout streaks among the blends.** Run 110 (checkout 496 / 548, recommendations 42 / 506, email 13), run 109 (283 / 379, recommendations 11 / 321, email 24), run 111 (181 / 252, recommendations 69 / 387, email 21), and run 134 (158 / 271, recommendations 23 / 379, email 51). Run 86 (checkout 108 / 163, four services at 10 or more) stays the best row overall from runs 80-93. Run 108 has the longest recommendations streak (555 / 558) but checkout is only 12 / 36.
- **`ck_rep2_pc120` blended every time it ran: 6 of 6** (runs 115, 123, 128, 130, 137, 150). It does so with checkout streaks of only 11 to 20, recommendations streaks of 15 to 116, email overloaded 142 to 431 ticks, and payment 4 to 30 ticks. Checkout is never latched on these holds. It is a reliable blend with a shallow checkout streak: none reaches 30.
- **Latched and blended are separate states.** The sticky holds (124, 125, 126, 129, 131, 139, 142, 144, 147, 148, 149) have recommendations at 0 / 0 to 0 / 156 and checkout streaks of 549 to 601. None blend. This repeats runs 94-107.
- **Same-mix repeatability.** The untouched control mix (runs 111, 121, 129, 131, 132, 134, 139, 143, 147, 151) gave 4 blends, 4 sticky holds, 1 other (143), and 1 near-miss (151). With runs 89, 92, 94-97, and 99-101, the mix is a blend on 8 of 19 holds. No single replay of this mix can be treated as the S2 load.
- **Levers.** `recs_users310` (114, 118) and `ck_cpu1000` (113, 122) turned the blend into a near-miss on both holds (checkout streak under 10 with a recommendations streak of 124 to 560). `ck_cpu1000_pc120` (135, 146) blended once. `spawn10` blended on 109 and 120 and did not on 133 and 142. `pc120` blended on 117 and latched on 125. `restart` blended on 108 and latched on 124. `recs_cpu1000` blended on 110 and 153 and latched on 126 and 148. `recs_cpu1000_spawn10` (144, 152) and `ck_cpu1000_pc120_spawn10` (141, 149) never blended. `ck_rep2_pc120_spawn10` (140, 145) did not blend, with checkout streaks of 16 and 9.
- **Lens A, independent pair.** The best new rows are 134, 111, 109, and 110. **Lens B, chain depth.** Runs 128, 123, and 150 have payment overloaded 30, 12, and 13 ticks beside email in the hundreds, but their checkout streaks are 20, 20, and 15, so they do not give the deep checkout streak that lens wants.
- **Nothing is locked.** These probes answer what decides the mode, not which hold should be the S2 load. The mechanism and the hidden-state checks are in [2026-10-04-s2-checkout-latch.md](2026-10-04-s2-checkout-latch.md) and [2026-10-03-s2-same-mix-replays-differ.md](2026-10-03-s2-same-mix-replays-differ.md).

### Where a replay would add information (updated again)

`ck_rep2_pc120` already blends reliably, so another replay of it adds little. A blend with a checkout streak of 30 or more has not been reproduced twice: runs 111 and 134 are controls that landed there once each, runs 109 and 110 are single holds, and runs 135 and 146 (`ck_cpu1000_pc120`) show checkout latched for minutes before a late recommendations storm, with a blend only on 146. Any replay of those should be interleaved with controls, because the control mix changes mode between holds with no hidden state in the saved snapshots to explain it.
