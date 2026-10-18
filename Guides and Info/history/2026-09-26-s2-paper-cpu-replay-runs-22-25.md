# S2 both-off paper-CPU replay, runs 22–25

600 s holds, both TopFull RL and RetryGuard off, `spawn_rate` 50. Frontend HPA pinned at 4 (sidecar request 90 m). Catalog HPA max 1. CPU is the paper table: checkout 615 m, ad 1150 m, cart 1920 m, recommendations 1150 m. That is the table mixes 9–12 used on 2026-09-24, not the later dispense (cart 1200, ad 800, checkout 1500, recommendations 1250). 6 minutes idle between holds. `service_capacity.json` on every folder matches the paper limits, with frontend at 4 replicas and catalog at 1.

Counts under each run are getproduct / postcheckout / getcart / postcart / emptycart. **Bold** cells clear that signal's bar: a rejection streak of 30, or a detector-overloaded fraction of at least half the hold.

| | run22 | run23 | run24 | run25 |
|---|---|---|---|---|
| Replays | mix 9 | mix 10 | mix 11 | mix 12 |
| Counts | 250/80/250/100/5 | 325/80/100/100/5 | 250/100/100/100/5 | 100/150/100/100/5 |

**The 2026-09-25 failure is still here, on the paper CPU table.** Emptycart plateau P95 is 1305 / 1354 / 1403 / 1434 ms. The Sep 24 reference for this tag is about 14 ms, and the check after run22 was 500 ms. Ads inbound failure is 46% / 53% / 52% / 24%, all above the 20% check, all resets, and the detector share stays 0. Ads streaks are 41, 87, 88, and 13. Frontend→ads retries are 0 except 13 on run24.

Recommendations stays cold on the three mixes that were detector-hot on Sep 24 (90% / 88% / 88% overloaded, retry deltas 266k–344k). Here overloaded is 0 and frontend→recommendations retries are 265 / 72 / 111 / 20. Checkout does not take that place until mix 12, and only partly: run25 detector share is 45% (287/637) against 42% on the Sep 24 mix 12, while the streak is 4 against 89 and the retry delta is 10,718 against 47,538. Layer A stays at the 10000 passthrough sentinel aside from startup zeros (10 / 5 / 85 / 0 samples).

Run22 was scored before the cool-off into run23. Both sides of the check fired (emptycart P95 1305 ms, ads failure 45.5%). The other three mixes were run anyway. Frontend stayed at 4 replicas on every resource sample that was written (133 / 134 / 103 / 134).

## (a) Inbound rejection streak / samples above 0.20

Longest consecutive scraped rows with Δ(5xx+resets)/Δtotal above 0.20, then the count of rows above 0.20. Scored-row counts are about 164 / 159 / 136 / 101. A streak of 30 is a disable for the nine controlled services. Frontend and redis-cart are not controlled.

| Service | run22 | run23 | run24 | run25 |
|---|---:|---:|---:|---:|
| frontend (not controlled) | 1 / 1 | 2 / 2 | 2 / 3 | 2 / 2 |
| checkoutservice | 0 | 1 / 1 | 1 / 1 | 4 / 29 |
| recommendationservice | 0 | 0 | 1 / 1 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 1 / 1 |
| productcatalogservice | 0 | 0 | 1 / 1 | 0 |
| cartservice | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 1 / 1 | 0 |
| shippingservice | 0 | 0 | 0 | 0 |
| adservice | **41 / 149** | **87 / 145** | **88 / 119** | 13 / 55 |
| redis-cart (not controlled) | 0 | 0 | 0 | 0 |

Whole-hold failure fraction, same window. Ads 46% / 53% / 52% / 24%. Checkout 1.5% / 1.3% / 2.5% / 17%. Recommendations under 0.2% on every hold. Frontend 0.6% / 0.6% / 1.1% / 4.6%. Payment and email stay under 5%. Cart, catalog, currency, and shipping stay under 1%.

## (b) Detector overloaded fraction of the hold

Share of `topfull_detect.csv` ticks with `overloaded=1`. Tick counts are 637 / 638 / 454 / 637. Run24's file is shorter than the others. Bold would be at least half the hold. Nothing here is bold.

| Service | run22 | run23 | run24 | run25 |
|---|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 |
| checkoutservice | 0 | 0 | 0.4% | 45.1% |
| recommendationservice | 0 | 0 | 0 | 0 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0.3% |
| productcatalogservice | 0 | 0 | 0 | 0 |
| cartservice | 0 | 0 | 0 | 0 |
| currencyservice | 0 | 0 | 0 | 0 |
| shippingservice | 0 | 0 | 0 | 0 |
| adservice | 0 | 0 | 0 | 0 |
| redis-cart | 0 | 0 | 0 | 0 |

Checkout overloaded ticks: 0/637, 0/638, 2/454, 287/637. Recommendations: 0 on every hold. Sep 24 mixes 9–11 were 576/637, 561/636, and 560/637.

## (c) Outbound retry delta by target, whole hold

Last cumulative `retry` minus first. The caller on every non-zero edge is frontend.

| Service | run22 | run23 | run24 | run25 |
|---|---:|---:|---:|---:|
| frontend | 0 | 0 | 0 | 0 |
| checkoutservice | 561 | 971 | 1,266 | 10,718 |
| recommendationservice | 265 | 72 | 111 | 20 |
| paymentservice | 0 | 0 | 0 | 0 |
| emailservice | 0 | 0 | 0 | 0 |
| productcatalogservice | 3,812 | 5,265 | 4,856 | 3,095 |
| cartservice | 673 | 671 | 1,155 | 740 |
| currencyservice | 1,583 | 2,500 | 1,339 | 989 |
| shippingservice | 118 | 132 | 244 | 242 |
| adservice | 0 | 0 | 13 | 0 |
| redis-cart | 0 | 0 | 0 | 0 |

Emptycart plateau (first 30 rows dropped): 3.59 / 4.45 / 4.18 / 4.36 req/s, P95 1305 / 1354 / 1403 / 1434 ms.

## Related

- Sep 24 scorecard these mixes are compared with: [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
- How (a)/(b)/(c) are read with both controllers off: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- The dispense-table replay of mixes 10–12: [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md).
