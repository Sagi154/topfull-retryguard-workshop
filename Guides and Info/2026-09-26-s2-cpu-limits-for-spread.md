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
| recommendationservice | 1150 | 1250 | 2300 |
| productcatalogservice | 1535 | 1535 | 600 |
| cartservice | 1920 | 1200 | 1920 |
| currencyservice | 770 | 770 | 500 |
| shippingservice | 770 | 770 | 400 |
| adservice | 1150 | 800 | 600 |
| paymentservice | 155 | 155 | 155 |
| emailservice | 155 | 155 | 155 |
| redis-cart | 540 | 540 | 540 |
| **Deployment total** | **13360** | **13275** | **13270** |

Paper pegs checkout at 615 m and recommendations at 1150 m. Every other backend has stayed under its paper quota on the both-off holds, so the detector only calls checkout and recommendations hot.

Dispense raises checkout 615 → 1500 and recommendations 1150 → 1250, and tightens cart 1920 → 1200 and ad 1150 → 800. The other seven services stay on paper. That raise on checkout is large enough to leave the 615 m peg. The recommendations step is not: run 6 already reached 1130 m, which is 90% of 1250 m and still above the detector’s 0.8 line. Cart’s highest paper-CPU peak is 601 m (run 7) and ad’s is 467 m (run 3), so 1200 m and 800 m stay above the CPU those services used.

Quota that a service does not use can move to a service that does. Ad does not need 800 m: its highest paper-CPU peak is 467 m (run 3), and on runs 6 and 7 it peaked at 162 m and 265 m. Shipping does not need 770 m: its highest peak on the paper-CPU holds is 144 m (run 7). Suggested sets ad to 600 m and shipping to 400 m. Those caps still sit above the measured peaks (467 / 600 is 0.78, 144 / 400 is 0.36), so this is spare quota, not a new bottleneck. A cap near 150 m on either service would be a targeted bottleneck, which stays Scenario 3/4’s job. Cart’s peak is 601 m of 1920 m, so the same move is available there later; this table leaves cart on paper.

The millicores taken from ad (550 m) and shipping (370 m), together with the currency and catalog cuts, pay for the raises. Checkout goes to 1500 m. Recommendations goes to 2300 m, because the 1150 m quota was clipping it (run 6 peaked at 1130 m). Currency goes to 500 m and catalog to 600 m so those two, which already draw the most CPU behind the chokes, sit near the detector’s 0.8 line. Payment and email stay on paper. Their means are 30–55 m, and a hot cap would be under 80 m.

The deployment total counts frontend at 4 × 1150 m and every other service once. Paper sums to 13,360 m. That is the ceiling. Dispense sums to 13,275 m. Suggested sums to 13,270 m, 90 m under paper. Run 6’s checkout peak (613 m) is 41% of 1500 m. Its recommendations peak (1130 m) is 49% of 2300 m.

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

Currency’s mean on these two holds is about 370–400 m, so a 500 m cap puts that mean near the 0.8 line. Catalog’s mean is about 480–490 m, so 600 m does the same. Ad’s mean is about 110–120 m and shipping’s is about 100–110 m, which is why 600 m and 400 m are spare and can be diverted.

## Which mixes to run under the suggested table

**Run 6** (340/100/240/10/10) and **run 7** (380/100/270/20/20). Counts are getproduct / postcheckout / getcart / postcart / emptycart. Both already peg checkout and recommendations, and they put the most CPU on catalog, currency, cart, and shipping at the same time. That is the traffic a higher checkout and recommendations quota can pass downstream.

Run 10, run 11, and run 26 peg one of the two chokes and leave catalog, currency, and shipping cooler, so they are the weaker mixes for this goal. Runs 18–21 already applied the dispense table to mixes 6, 10, 11, and 12, with the frontend sidecar CPU limit still set. Checkout on those holds reached 286–557 m of 1500 m. They do not stand in for a clean replay.

The first hold should change six limits: checkout 1500, recommendations 2300, currency 500, catalog 600, ad 600, shipping 400. Ad and shipping are in that set because their cut is the diverted quota, and their measured peaks stay under the new caps. Cart, payment, and email stay on paper. The deployment total stays at 13,270 m.

## Related

- Dispense table and the mixes it replayed: [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md).
- (a)/(b)/(c) on those dispense holds: [2026-09-25-s2-both-off-abc-runs-18-21.md](2026-09-25-s2-both-off-abc-runs-18-21.md).
- How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Run 6 in the run3–run7 set: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
