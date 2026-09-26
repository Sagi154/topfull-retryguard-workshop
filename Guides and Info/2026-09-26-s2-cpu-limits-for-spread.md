# S2 both-off CPU limits for spreading load off checkout and recommendations

## Goal

Spread the load that sits on `checkoutservice` and `recommendationservice` onto the other backend services.

Both controllers stay off on these holds. The three S2 signals are still the ones in [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md): a 30-sample inbound rejection streak, a detector `overloaded` share of at least half the hold, and a retry storm on those same edges. The CPU table is a way to move those signals off checkout and recommendations and onto more of the nine controlled services.

## Three tables

Millicores. Request equals limit. Paper is the table on the both-off holds before run18. Dispense is the table on runs 18–21, from [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md). Agreed is the table this series runs (runs 30–34). Paper and Dispense pin frontend at 4 replicas, so their deployment totals use 4 × 1150 m. Agreed pins frontend at 5 replicas, so its deployment total uses 5 × 1150 m.

| Service | Paper | Dispense (runs 18–21) | Agreed (runs 30–34) |
|---|---:|---:|---:|
| frontend | 1150 | 1150 | 1150 × 5 replicas |
| checkoutservice | 615 | 1500 | 1500 |
| recommendationservice | 1150 | 1250 | 2000 |
| productcatalogservice | 1535 | 1535 | 600 |
| cartservice | 1920 | 1200 | 1000 |
| currencyservice | 770 | 770 | 500 |
| shippingservice | 770 | 770 | 400 |
| adservice | 1150 | 800 | 600 |
| paymentservice | 155 | 155 | 150 |
| emailservice | 155 | 155 | 150 |
| redis-cart | 540 | 540 | 500 |
| **Deployment total** | **13360** | **13275** | **13150** |

Paper pegs checkout at 615 m and recommendations at 1150 m. Every other backend has stayed under its paper quota on the both-off holds, so the detector only calls checkout and recommendations hot.

Dispense raises checkout 615 → 1500 and recommendations 1150 → 1250, and tightens cart 1920 → 1200 and ad 1150 → 800. The other seven services stay on paper. That raise on checkout is large enough to leave the 615 m peg. The recommendations step is not: run 6 already reached 1130 m, which is 90% of 1250 m and still above the detector’s 0.8 line. Cart’s highest paper-CPU peak is 601 m (run 7) and ad’s is 467 m (run 3), so 1200 m and 800 m stay above the CPU those services used.

Quota that a service does not use can move to a service that does. Ad does not need 800 m: its highest paper-CPU peak is 467 m (run 3), and on runs 6 and 7 it peaked at 162 m and 265 m. Shipping does not need 770 m: its highest peak on the paper-CPU holds is 144 m (run 7). Agreed sets ad to 600 m and shipping to 400 m. Those caps still sit above the measured peaks (467 / 600 is 0.78, 144 / 400 is 0.36), so this is spare quota, not a new bottleneck. A cap near 150 m on either service would be a targeted bottleneck, which stays Scenario 3/4’s job. Cart’s highest paper-CPU peak is 601 m (run 7). Agreed sets cart to 1000 m.

Agreed sets checkout to 1500 m and recommendations to 2000 m. The 1150 m paper quota was clipping recommendations (run 6 peaked at 1130 m). Currency goes to 500 m and catalog to 600 m so those two, which already draw the most CPU behind the chokes, sit near the detector’s 0.8 line. Payment goes to 150 m and email goes to 150 m. Their means are 30–55 m. Redis-cart goes to 500 m. Request equals limit.

Paper and Dispense pin frontend at 4 replicas and count every other service once, so their deployment totals use 4 × 1150 m. Paper sums to 13,360 m. That four-replica total is the ceiling. Dispense sums to 13,275 m. Agreed (runs 30–34) pins frontend at 5 replicas, so its deployment total uses 5 × 1150 m and is 13,150 m, under the paper four-replica ceiling of 13,360 m. Run 6’s checkout peak (613 m) is 41% of 1500 m. Its recommendations peak (1130 m) sits under the agreed 2000 m cap.

## Measured CPU on the candidate holds

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

## Which mixes to run under the agreed table

Order is fixed. Cool-off between holds is 360 s.

| Slot | Source mix | Counts (getproduct / postcheckout / getcart / postcart / emptycart) |
|---|---|---|
| run30 | 6 | 340 / 100 / 240 / 10 / 10 |
| run31 | 7 | 380 / 100 / 270 / 20 / 20 |
| run32 | 10 | 325 / 80 / 100 / 100 / 5 |
| run33 | 26 | 325 / 100 / 100 / 100 / 5 |
| run34 | 12 | 100 / 150 / 100 / 100 / 5 |

## Related

- Dispense table and the mixes it replayed: [2026-09-25-s2-cpu-dispense-runs-18-21.md](2026-09-25-s2-cpu-dispense-runs-18-21.md).
- (a)/(b)/(c) on those dispense holds: [2026-09-25-s2-both-off-abc-runs-18-21.md](2026-09-25-s2-both-off-abc-runs-18-21.md).
- How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).
- Run 6 in the run3–run7 set: [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
