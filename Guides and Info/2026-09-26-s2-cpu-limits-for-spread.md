# S2 both-off CPU limits for spreading load off checkout and recommendations

## Goal

Spread the load that sits on `checkoutservice` and `recommendationservice` onto the other backend services.

Both controllers stay off on these holds. The three S2 signals are still the ones in [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md): a 30-sample inbound rejection streak, a detector `overloaded` share of at least half the hold, and a retry storm on those same edges. The CPU table is a way to move those signals off checkout and recommendations and onto more of the nine controlled services.

## Three tables

Millicores. Request equals limit. Frontend is per replica (4 replicas when pinned). Paper is the table on the both-off holds before run18. Dispense is the table on runs 18–21, from [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md). Suggested is the table for the goal above.

| Service | Paper | Dispense (runs 18–21) | Suggested |
|---|---:|---:|---:|
| frontend | 1150 | 1150 | 1150 |
| checkoutservice | 615 | 1500 | 1500 |
| recommendationservice | 1150 | 1250 | 1800 |
| productcatalogservice | 1535 | 1535 | 600 |
| cartservice | 1920 | 1200 | 1920 |
| currencyservice | 770 | 770 | 500 |
| shippingservice | 770 | 770 | 770 |
| adservice | 1150 | 800 | 1150 |
| paymentservice | 155 | 155 | 155 |
| emailservice | 155 | 155 | 155 |
| redis-cart | 540 | 540 | 540 |

Paper pegs checkout at 615 m and recommendations at 1150 m. Every other backend has stayed under its paper quota on the both-off holds, so the detector only calls checkout and recommendations hot.

Dispense raises checkout 615 → 1500 and recommendations 1150 → 1250, and tightens cart 1920 → 1200 and ad 1150 → 800. The other seven services stay on paper. That raise on checkout is large enough to leave the 615 m peg. The recommendations step is not: run 6 already reached 1130 m, which is 90% of 1250 m and still above the detector’s 0.8 line. Cart’s highest paper-CPU peak is 601 m (run 7) and ad’s is 467 m (run 3), so 1200 m and 800 m stay above the CPU those services used.

Suggested keeps the checkout raise, moves recommendations to 1800 m so the run 6 peak (1130 m) sits under 0.8, and cuts the two backends that already draw the most CPU behind those chokes: currency to 500 m and catalog to 600 m. Cart, ad, shipping, payment, and email stay on paper for the first hold. A cart cap only bites near 500 m, an ad or shipping cap near 150 m, and a payment or email cap under 80 m. Those cuts are targeted bottlenecks, which is Scenario 3/4’s job, so they stay out of this table.

## Where the suggested numbers come from

Mean and max app-container CPU on the two candidate holds, from `resource_usage.csv`. Quotas are the paper table.

| Service | run6 mean / max | run7 mean / max |
|---|---:|---:|
| checkoutservice | 492 / 613 | 521 / 613 |
| recommendationservice | 911 / 1130 | 863 / 1072 |
| productcatalogservice | 480 / 613 | 490 / 588 |
| currencyservice | 373 / 510 | 396 / 503 |
| cartservice | 393 / 498 | 423 / 601 |
| shippingservice | 98 / 136 | 109 / 144 |
| adservice | 110 / 162 | 122 / 265 |
| paymentservice | 46 / 75 | 47 / 70 |
| emailservice | 35 / 72 | 45 / 85 |

Currency’s mean on these two holds is about 370–400 m, so a 500 m cap puts that mean near the 0.8 line. Catalog’s mean is about 480–490 m, so 600 m does the same. Recommendations at 1800 m leaves room above 1130 m because the 1150 m quota was clipping the series.

## Which mixes to run under the suggested table

**Run 6** (340/100/240/10/10) and **run 7** (380/100/270/20/20). Counts are getproduct / postcheckout / getcart / postcart / emptycart. Both already peg checkout and recommendations, and they put the most CPU on catalog, currency, cart, and shipping at the same time. That is the traffic a higher checkout and recommendations quota can pass downstream.

Run 10, run 11, and run 26 peg one of the two chokes and leave catalog, currency, and shipping cooler, so they are the weaker mixes for this goal. Runs 18–21 already applied the dispense table to mixes 6, 10, 11, and 12, with the frontend sidecar CPU limit still set. Checkout on those holds reached 286–557 m of 1500 m. They do not stand in for a clean replay.

The first hold should change four limits: checkout 1500, recommendations 1800, currency 500, catalog 600. Leaving cart, ad, shipping, payment, and email on paper keeps the result attributable to those four.

## Related

- Dispense table and the mixes it replayed: [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md).
- (a)/(b)/(c) on those dispense holds: [2026-09-25-s2-both-off-abc-runs-18-21.md](2026-09-25-s2-both-off-abc-runs-18-21.md).
- How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Run 6 in the run3–run7 set: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
