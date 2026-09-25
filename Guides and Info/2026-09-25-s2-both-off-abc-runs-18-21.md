# S2 both-off runs 18–21

CPU-dispense replays of source mixes 6, 10, 11, and 12. Counts under each run are getproduct / postcheckout / getcart / postcart / emptycart. Frontend stayed at 4 replicas. Cart 1200 m, ad 800 m, checkout 1500 m, recommendations 1250 m. **Bold** cells clear that signal's bar: a rejection streak of 30. No detector cell reaches half the hold.

| | run18 | run19 | run20 | run21 |
|---|---|---|---|---|
| Source mix | mix 6 | mix 10 | mix 11 | mix 12 |
| Counts | 340/100/240/10/10 | 325/80/100/100/5 | 250/100/100/100/5 | 100/150/100/100/5 |

**One service would disable, and the retries are elsewhere.** adservice is the only controlled service with a streak of 30 or more, on run18 (44 samples, 195 s, 53% inbound failure) and run19 (38 samples, 201 s, 49%). run20 stops at 25 and run21 at 22. The detector overloaded flag stays at a handful of ticks, and the Layer A threshold stays at the 10000 passthrough sentinel. Outbound retries are 15k–45k, all from frontend, into productcatalog, cart, currency, and checkout. frontend→adservice retry delta is 0 on every hold. Storefront goodput stays at 3–9 req/s.

adservice rejection streak (longest consecutive inbound samples above 0.20; 30 is the disable bar): run18 **44**, run19 **38**, run20 25, run21 22. Source: `service_inbound.csv`, 2026-09-25. These are samples, not seconds.

Outbound retry delta on the four largest targets (caller is frontend on every edge):

| Target | run18 | run19 | run20 | run21 |
|---|---:|---:|---:|---:|
| productcatalogservice | 13,120 | 24,877 | 12,505 | 7,381 |
| cartservice | 2,747 | 8,796 | 5,136 | 2,326 |
| currencyservice | 4,151 | 8,117 | 4,560 | 2,601 |
| checkoutservice | 1,361 | 2,923 | 2,122 | 3,089 |

Source: `service_edges.csv` retry, whole hold, 2026-09-25.

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. The inbound series is 183–277 samples across ~690 s (median gap 3–5 s), so a streak of 30 is a longer wall-clock stretch than 30 seconds. A streak of 30 is a disable for the nine controlled services.

| Service | run18 | run19 | run20 | run21 |
|---|---:|---:|---:|---:|
| frontend (not controlled) | 1 / 1 | 1 / 1 | 2 / 2 | 1 / 1 |
| checkoutservice | 1 / 2 | 2 / 5 | 1 / 2 | 1 / 2 |
| recommendationservice | 0 | 1 / 1 | 1 / 1 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 |
| productcatalogservice | 0 | 1 / 1 | 1 / 1 | 1 / 1 |
| cartservice | 0 | 1 / 2 | 1 / 1 | 1 / 1 |
| currencyservice | 0 | 1 / 1 | 0 | 1 / 1 |
| shippingservice | 0 | 0 | 0 | 1 / 1 |
| adservice | **44 / 132** | **38 / 95** | 25 / 152 | 22 / 63 |
| redis-cart (not controlled) | 0 | 0 | 0 | 0 |

Whole-hold failure fraction, same window. adservice 53.3% / 49.3% / 39.5% / 25.8%, all of it resets (inbound 5xx is 0). Checkout 2.2% / 5.3% / 2.3% / 3.1%. Every other service stays under 2%. adservice high-sample counts are 132, 95, 152, and 63. Source: `service_inbound.csv`, 2026-09-25.

## (b) Detector overloaded fraction of the hold

Share of `topfull_detect.csv` ticks with `overloaded=1`. 640, 640, 638, and 637 ticks. Bold would be at least half the hold. Layer A threshold is 10000 on every API after a few leading zeros at collector start (run20 is 10000 on all 638 ticks).

| Service | run18 | run19 | run20 | run21 |
|---|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 |
| checkoutservice | 0 | 0 | 0 | 0 |
| recommendationservice | 0 | 0 | 0 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0.2% | 0 | 1.3% |
| productcatalogservice | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 |
| adservice | 0.3% | 0 | 0.3% | 0 |
| redis-cart | 0 | 0 | 0 | 0 |

Nonzero counts: adservice 2/640 on run18 and 2/638 on run20; emailservice 1/640 on run19 and 8/637 on run21. Measured CPU stays under the dispensed quota: ad max 170–232 m of 800 m, checkout max 286–557 m of 1500 m, recommendations max 149–255 m of 1250 m. Source: `topfull_detect.csv` and `resource_usage.csv`, 2026-09-25.

## (c) Outbound retry delta by target, whole hold

Sum of positive Envoy retry increments on every caller→target edge into that service. The caller on every non-zero edge is frontend. Hold totals are 21,710 / 45,171 / 24,340 / 15,397.

| Service | run18 | run19 | run20 | run21 |
|---|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 |
| checkoutservice | 1,361 | 2,923 | 2,122 | 3,089 |
| recommendationservice | 127 | 404 | 0 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 |
| productcatalogservice | 13,120 | 24,877 | 12,505 | 7,381 |
| cartservice | 2,747 | 8,796 | 5,136 | 2,326 |
| currencyservice | 4,151 | 8,117 | 4,560 | 2,601 |
| shippingservice | 204 | 54 | 17 | 0 |
| adservice | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 |

Source: `service_edges.csv` retry, positive deltas, 2026-09-25. User counts are the source mixes named in `scenario_2_baseline_no_topfull.yaml`. Locust mean goodput / Fail / P95 on `total.csv`: run18 3.6 / 83.3 / 5093 ms, run19 3.0 / 83.4 / 6922 ms, run20 6.6 / 107.5 / 5263 ms, run21 9.3 / 113.5 / 4726 ms. Frontend mean sojourn 5394 / 5426 / 4056 / 3260 ms.

## Related

- User counts and the CPU table: [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md).
- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Same scorecard for runs 9–13, under the paper CPU table: [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
