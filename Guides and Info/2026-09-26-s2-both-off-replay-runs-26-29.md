# S2 both-off replay of mixes 14–17, runs 26–29

600 s holds, both TopFull RL and RetryGuard off, `spawn_rate` 50. Frontend HPA pinned at 4. Catalog HPA max 1. Paper CPU table. Sidecar request **90m**, `proxyCPULimit` unset, so the frontend `istio-proxy` had no CPU limit. 360 s idle between holds. Runs 14–17 used the same user counts with `proxyCPULimit=90m` and stay historical.

Counts are getproduct / postcheckout / getcart / postcart / emptycart. **Bold** cells clear that signal's bar: a rejection streak of 30 consecutive inbound rows, or a detector-overloaded fraction of at least half the hold.

| | run26 | run27 | run28 | run29 |
|---|---|---|---|---|
| Replays | run14 | run15 | run16 | run17 |
| Counts | 325/100/100/100/5 | 325/100/100/20/5 | 50/100/100/400/5 | 50/50/50/50/430 |

**The ads-only signature from runs 14–17 is gone.** Ads inbound failure stays under 1% and its streak is 0 on every hold. Emptycart plateau P95 is 19 / 14 / 23 / 31 ms. Frontend stayed at 4 replicas on every resource sample (134 / 134 / 133 / 134). Layer A stayed at the 10000 passthrough sentinel aside from startup zeros (5 / 0 / 15 / 20 samples).

Checkout is the service that clears a disable-length streak on every hold (592 / 43 / 471 / 566), all resets, and it is detector-hot on run26, run28, and run29 (93% / 91% / 90%). Run27 is the recommendations hold: detector share 87% (556/637) and frontend→recommendations retries **233,125**, while checkout's streak is 43 and its detector share is 38%. That split matches the Sep 24 runs 9–13 pattern, where recommendations carried the 265k–344k retry edge on the browse-heavy mixes and checkout took the streak once postcheckout rose. Runs 14–17 had neither: checkout streaks were 1 / 3 / 1 / 2, recommendations streaks were at most 1, and no service was detector-hot for half the hold.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive scraped rows with Δ(5xx+resets)/Δtotal above 0.20, then the count of rows above 0.20. Scored-row counts are about 613 per service. A streak of 30 is a disable for the nine controlled services. Frontend and redis-cart are not controlled. Services omitted from a row stayed at streak 0.

| Service | run26 | run27 | run28 | run29 |
|---|---:|---:|---:|---:|
| frontend (not controlled) | **72 / 517** | **558 / 558** | 1 / 2 | 1 / 1 |
| checkoutservice | **592 / 592** | **43 / 44** | **471 / 590** | **566 / 568** |
| recommendationservice | 2 / 43 | 5 / 206 | 0 | 0 |
| paymentservice | 2 / 13 | 2 / 3 | 14 / 364 | 0 |
| emailservice | 8 / 156 | 3 / 13 | 2 / 4 | 6 / 209 |
| adservice | 0 | 0 | 0 | 0 |

Whole-hold failure fraction, same window. Checkout 43% / 9% / 42% / 37%, all resets. Recommendations 15% / 19% / under 1% / under 1%. Ads under 1% on every hold. Frontend 26% / 44% / 9% / 5%. Payment 6% / 1% / 24% / 2%. Email 22% / 1% / 7% / 18%, on a small arrival count (run26 Δtotal 1,599).

## (b) Detector overloaded fraction of the hold

Share of `topfull_detect.csv` ticks with `overloaded=1`. Tick counts are 637 / 637 / 638 / 637. Bold is at least half the hold.

| Service | run26 | run27 | run28 | run29 |
|---|---:|---:|---:|
| checkoutservice | **592 / 637 (93%)** | 241 / 637 (38%) | **578 / 638 (91%)** | **575 / 637 (90%)** |
| recommendationservice | **364 / 637 (57%)** | **556 / 637 (87%)** | 0 | 0 |
| every other service | 0 | 0 | 0 | 0 |

## (c) Outbound retry delta, whole hold

Positive Envoy retry increments. The only edges at or above 1 are frontend → recommendationservice and frontend → checkoutservice. Ads, catalog, and cart stay at 0. On runs 14–16 the largest edge was frontend → productcatalog (7k–16k) with ads failure and zero ads retries.

| Edge | run26 | run27 | run28 | run29 |
|---|---:|---:|---:|---:|
| frontend → recommendationservice | 120,541 | 233,125 | 0 | 0 |
| frontend → checkoutservice | 45,182 | 3,586 | 69,857 | 33,672 |

Plateau Locust (first 30 rows dropped). Emptycart goodput tracks its offer on every hold. Postcheckout goodput is 0.1 / 20.4 / 0.0 / 1.0 req/s with P95 3453 / 2209 / 2368 / 2187 ms.
