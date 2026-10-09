# S2 re-enable rejection sweep, Set A

600 s holds on the locked S2 mix, getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5, `spawn_rate` 50, Paper-C1, Istio `attempts: 3`, `perTryTimeout` 500 ms. Frontend HPA pinned at 4, catalog HPA at 1. Checkout and recommendations were rolled before each hold. 360 s cool-off between every pair of holds. RetryGuard is on for every hold here (`retry_metric: edge_rpr`, `retries_threshold` 0.5, `rejection_threshold` 0.20, `interval_samples` 30). The varied setting is the 0→1 re-enable bar, `reenable_rejection` ∈ {0.10, 0.15, 0.20}. Each bar has a RetryGuard-only arm (TopFull off) and a both-on arm. How the three signals are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).

(a), (b), and (c) are from `experiments/s2_both_off_abc.py` on the full inbound file. The other inbound tables drop the last 5 polls. Locust tables drop the first 30 rows and the last 5. **Bold** in (a) is a streak of at least 30 on a controlled service. Frontend and redis-cart stay plain there. **Bold** in (b) is an overloaded share of at least 0.5.

A shed takes an edge from its current attempt count to 0 after `rpr > 0.5` for 30 s. The 0→1 step needs that callee's inbound rejection, `(Δ5xx + Δresets) / Δtotal`, strictly under the hold's `reenable_rejection` for 30 s, and it restores 1 attempt. Climbing continues on rpr. The OFF-window rejection figures below are the `state=OFF` samples in `retryguard.log`.

Checkout and recommendations gap2 are 0.0% on every RetryGuard-only hold. On the first both-on hold of each bar they are 2.0% (0.10), 0.8% (0.15), and 6.1% (0.20). Those columns are 1 s samples. The both-on repeat-2 columns are slower: gap2 is 23.0% (010 on2), 32.1% (015 on2), 27.2% (015 on3), 47.8% (020 on2), and 29.2% (020 on3). Signal (a) on those five columns counts the slow polls. Signal (b) stays on the 1 s detector clock.

`015 off2` is `study2_s2_rr015_rgtf0_rep3`: the rep2 folder ran long (Locust 3288 rows, mesh span 3621 s) and stays out of the tables. `010 on2` is `study2_s2_rr010_rgtf1_rep3`. For 0.15 and 0.20 both full both-on repeat-2 copies are in the tables (`015 on2` / `015 on3`, `020 on2` / `020 on3`).

## Hold index


| Bar  | Arm             | Column   | Folder                     | Locust rows | Mesh span | Checkout gap2 |
| ---- | --------------- | -------- | -------------------------- | ----------- | --------- | ------------- |
| 0.10 | RetryGuard only | 010 off1 | study2_s2_rr010_rgtf0_rep1 | 573         | 716 s     | 0.0%          |
| 0.10 | RetryGuard only | 010 off2 | study2_s2_rr010_rgtf0_rep2 | 574         | 714 s     | 0.0%          |
| 0.10 | Both on         | 010 on1  | study2_s2_rr010_rgtf1_rep1 | 565         | 717 s     | 2.0%          |
| 0.10 | Both on         | 010 on2  | study2_s2_rr010_rgtf1_rep3 | 568         | 717 s     | 23.0%         |
| 0.15 | RetryGuard only | 015 off1 | study2_s2_rr015_rgtf0_rep1 | 573         | 715 s     | 0.0%          |
| 0.15 | RetryGuard only | 015 off2 | study2_s2_rr015_rgtf0_rep3 | 573         | 715 s     | 0.0%          |
| 0.15 | Both on         | 015 on1  | study2_s2_rr015_rgtf1_rep1 | 566         | 718 s     | 0.8%          |
| 0.15 | Both on         | 015 on2  | study2_s2_rr015_rgtf1_rep2 | 568         | 716 s     | 32.1%         |
| 0.15 | Both on         | 015 on3  | study2_s2_rr015_rgtf1_rep3 | 568         | 716 s     | 27.2%         |
| 0.20 | RetryGuard only | 020 off1 | study2_s2_rr020_rgtf0_rep1 | 573         | 717 s     | 0.0%          |
| 0.20 | RetryGuard only | 020 off2 | study2_s2_rr020_rgtf0_rep2 | 573         | 716 s     | 0.0%          |
| 0.20 | Both on         | 020 on1  | study2_s2_rr020_rgtf1_rep1 | 565         | 718 s     | 6.1%          |
| 0.20 | Both on         | 020 on2  | study2_s2_rr020_rgtf1_rep3 | 566         | 717 s     | 47.8%         |
| 0.20 | Both on         | 020 on3  | study2_s2_rr020_rgtf1_rep4 | 567         | 717 s     | 29.2%         |


The tables use that column order. A bold bar separates the three re-enable settings. Each `START` line matches the column's bar. No hold has a `PATCH_FAIL`.

Invalid folders, kept and left out of the tables:


| Folder                     | Locust rows | Mesh span | Checkout gap2 |
| -------------------------- | ----------- | --------- | ------------- |
| study2_s2_rr015_rgtf0_rep2 | 3288        | 3621 s    | 0.0%          |
| study2_s2_rr010_rgtf1_rep2 | 0           | 715 s     | 0.0%          |
| study2_s2_rr020_rgtf1_rep2 | 0           | 80 s      | 0.0%          |


`rr010_rgtf1_rep2` has a header-only Locust file. `rr020_rgtf1_rep2` has no `retryguard.log`. The scored both-on copy for 0.10 is rep3. For 0.15 the scored copies are rep2 and rep3. For 0.20 they are rep3 and rep4.

Per-pod millicores, request equals limit. Replicas are the Paper-C1 pin. Frontend is 4; every other service is 1. `cpu_millicores` in `resource_usage.csv` is the sum across replicas. Frontend stayed at 4 replicas on every resource sample of all fourteen holds. No service has a 0-replica sample. `service_capacity.json` matches this table on every hold.


| Service               | Quota | Replicas |
| --------------------- | ----- | -------- |
| frontend              | 1150  | 4        |
| checkoutservice       | 800   | 1        |
| recommendationservice | 1150  | 1        |
| productcatalogservice | 800   | 1        |
| cartservice           | 800   | 1        |
| currencyservice       | 770   | 1        |
| shippingservice       | 770   | 1        |
| adservice             | 1150  | 1        |
| paymentservice        | 155   | 1        |
| emailservice          | 120   | 1        |
| redis-cart            | 540   | 1        |




## RetryGuard toggles

Only `frontend → checkoutservice` and `frontend → recommendationservice` change attempt counts. Every shed starts from 3 attempts. An em dash means that edge never went to 0, so the re-enable bar was not in force. Time OFF is seconds from the shed to the re-enable, or to controller exit when the edge stays at 0. The streak under the bar counts consecutive OFF-window rejection samples strictly below that column's `reenable_rejection`. A streak of 30 is the 0→1 step.

### checkoutservice


|                            | 010 off1      | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2      | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1      | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| -------------------------- | ------------- | -------- | ------- | ------- | ----- | -------- | ------------- | ------- | ------- | ------- | ----- | ------------- | -------- | ------- | ------- | ------- |
| ON→OFF / OFF→ON            | 1 / 1         | 0 / 0    | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 1 / 0         | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 1 / 1         | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| shed rpr                   | 2.14          | —        | —       | —       | **┃** | —        | 2.60          | —       | —       | —       | **┃** | 2.61          | —        | —       | —       | —       |
| attempts after re-enable   | 3             | —        | —       | —       | **┃** | —        | —             | —       | —       | —       | **┃** | 3             | —        | —       | —       | —       |
| time OFF (s)               | 35            | —        | —       | —       | **┃** | —        | 532           | —       | —       | —       | **┃** | 35            | —        | —       | —       | —       |
| OFF rejection min / median | 0.000 / 0.000 | —        | —       | —       | **┃** | —        | 0.000 / 0.096 | —       | —       | —       | **┃** | 0.000 / 0.000 | —        | —       | —       | —       |
| streak under the bar       | 31            | —        | —       | —       | **┃** | —        | 14            | —       | —       | —       | **┃** | 31            | —        | —       | —       | —       |


010 off1 and 020 off1 re-enable at logged rejection 0.00 and then climb 1→2→3. 015 off2 stays at 0 for the rest of the hold: 378 of 524 OFF samples are under 0.15, and the longest such streak is 14.

### recommendationservice


|                            | 010 off1      | 010 off2      | 010 on1 | 010 on2       | **┃** | 015 off1      | 015 off2 | 015 on1 | 015 on2 | 015 on3       | **┃** | 020 off1      | 020 off2      | 020 on1 | 020 on2 | 020 on3 |
| -------------------------- | ------------- | ------------- | ------- | ------------- | ----- | ------------- | -------- | ------- | ------- | ------------- | ----- | ------------- | ------------- | ------- | ------- | ------- |
| ON→OFF / OFF→ON            | 1 / 0         | 1 / 0         | 0 / 0   | 1 / 0         | **┃** | 1 / 0         | 0 / 0    | 0 / 0   | 0 / 0   | 1 / 0         | **┃** | 1 / 0         | 1 / 0         | 0 / 0   | 0 / 0   | 0 / 0   |
| shed rpr                   | 0.72          | 0.90          | —       | 1.96          | **┃** | 1.38          | —        | —       | —       | 0.95          | **┃** | 1.20          | 1.20          | —       | —       | —       |
| attempts after re-enable   | —             | —             | —       | —             | **┃** | —             | —        | —       | —       | —             | **┃** | —             | —             | —       | —       | —       |
| time OFF (s)               | 496           | 527           | —       | 420           | **┃** | 534           | —        | —       | —       | 379           | **┃** | 502           | 532           | —       | —       | —       |
| OFF rejection min / median | 0.080 / 0.198 | 0.000 / 0.306 | —       | 0.003 / 0.178 | **┃** | 0.000 / 0.271 | —        | —       | —       | 0.006 / 0.207 | **┃** | 0.000 / 0.253 | 0.000 / 0.259 | —       | —       | —       |
| streak under the bar       | 1             | 1             | —       | 2             | **┃** | 1             | —        | —       | —       | 2             | **┃** | 3             | 3             | —       | —       | —       |


Recommendations does not re-enable on any hold. The longest OFF streak under the bar is 3 samples (020 off1 and 020 off2). 010 on2 sheds recommendations from 3 at rpr 1.96 and leaves it off for 420 s (OFF rejection min 0.003, median 0.178, under-bar streak 2). 015 on3 sheds recommendations from 3 at rpr 0.95 and leaves it off for 379 s (min 0.006, median 0.207, under-bar streak 2).

010 on1, 015 on1, 015 on2, 020 on1, 020 on2, and 020 on3 have no `ON→OFF` and no `OFF→ON`.

## Storefront total

Mean `Goodput`, `Fail / RPS`, and `Latency95` on `total.csv`, rows 30 through the fifth from the end. The per-API goodput tables below sum to this goodput.


|                  | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| ---------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| goodput (req/s)  | 454.1    | 401.1    | 499.9   | 421.5   | **┃** | 414.0    | 533.0    | 453.8   | 498.1   | 422.9   | **┃** | 427.3    | 426.5    | 502.9   | 497.5   | 500.8   |
| failure fraction | 0.171    | 0.269    | 0.086   | 0.221   | **┃** | 0.243    | 0.038    | 0.168   | 0.088   | 0.216   | **┃** | 0.218    | 0.223    | 0.083   | 0.090   | 0.084   |
| P95 (ms)         | 503      | 491      | 357     | 516     | **┃** | 481      | 338      | 338     | 352     | 536     | **┃** | 491      | 479      | 358     | 360     | 353     |




## (a) Inbound rejection streak / samples above 0.20

Longest consecutive inbound samples with Δ(5xx+resets)/Δtotal above 0.20, then the count of samples above 0.20. A streak of 30 is a disable for the nine controlled services. **Bold** marks streak ≥ 30 on a controlled service. Frontend and redis-cart sit outside that set, so their cells stay plain. On 010 on2, 015 on2, 015 on3, 020 on2, and 020 on3 the inbound gap is often 2 s, so those streaks count slow polls.


| Service                     | 010 off1    | 010 off2  | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2     | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1    | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------------- | ----------- | --------- | ------- | ------- | ----- | -------- | ------------ | ------- | ------- | ------- | ----- | ----------- | -------- | ------- | ------- | ------- |
| frontend (not controlled)   | 8 / 132     | 143 / 463 | 1 / 1   | 16 / 90 | **┃** | 31 / 443 | 1 / 1        | 1 / 1   | 0 / 0   | 11 / 92 | **┃** | 33 / 332    | 25 / 370 | 1 / 1   | 0 / 0   | 0 / 0   |
| checkoutservice             | **35 / 37** | 9 / 9     | 8 / 152 | 5 / 5   | **┃** | 1 / 1    | **35 / 115** | 8 / 183 | 7 / 125 | 6 / 6   | **┃** | **34 / 38** | 0 / 0    | 9 / 133 | 6 / 104 | 7 / 126 |
| recommendationservice       | 1 / 2       | 3 / 21    | 0 / 0   | 2 / 11  | **┃** | 2 / 8    | 0 / 0        | 0 / 0   | 0 / 0   | 1 / 3   | **┃** | 1 / 6       | 3 / 4    | 0 / 0   | 0 / 0   | 0 / 0   |
| paymentservice              | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 1 / 1   | 1 / 1   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| emailservice                | 4 / 20      | 2 / 6     | 5 / 75  | 2 / 3   | **┃** | 1 / 1    | 2 / 116      | 3 / 71  | 4 / 55  | 1 / 2   | **┃** | 2 / 13      | 0 / 0    | 6 / 66  | 4 / 44  | 5 / 53  |
| productcatalogservice       | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| cartservice                 | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| currencyservice             | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| shippingservice             | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| adservice                   | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |
| redis-cart (not controlled) | 0 / 0       | 0 / 0     | 0 / 0   | 0 / 0   | **┃** | 0 / 0    | 0 / 0        | 0 / 0   | 0 / 0   | 0 / 0   | **┃** | 0 / 0       | 0 / 0    | 0 / 0   | 0 / 0   | 0 / 0   |




## (b) Detector overloaded fraction of the hold

`overloaded=1` ticks over `topfull_detect.csv` rows. **Bold** is a share of at least 0.5.

A fresh threshold of 10000 is the passthrough and a fresh 0 is an empty read. On 010 off1, 015 off1, and 020 off1, fresh getproduct stays at 240 and fresh getcart stays at 91, and postcheckout's fresh values are 0 or 10000. On 010 off2, 015 off2, and 020 off2 every fresh read is 10000. The both-on holds move postcheckout: 010 on1 has 152 fresh caps from 10.0 to 89.8, ending at 83.9; 015 on1 has 143 from 10.0 to 99.0, ending at 44.9; 020 on1 has 146 from 10.0 to 94.6, ending at 19.3. 020 on1 also has 5 fresh getproduct caps (275.0–295.8) and 4 fresh getcart caps (98.0–107.8); both of those series end at 10000. 015 on1 still shows getproduct at 240 and getcart at 91 next to the moving postcheckout cap. 010 on2 has 495 postcheckout caps from 10.6 to 71.1, ending at 38.5, plus 13 getproduct caps (146.7–272.0, ending at 272.0) and 12 getcart caps (52.0–110.0, ending at 99.0). 015 on2 has 152 postcheckout caps from 10.0 to 97.5, ending at 19.3; its getproduct and getcart fresh values are 0 or 10000. 015 on3 has 452 postcheckout caps from 11.2 to 77.3, ending at 47.6, plus 27 getproduct caps (134.7–302.5) and 24 getcart caps (38.3–110.0); the last fresh read on those two APIs is 0. 020 on2 has 152 postcheckout caps from 10.0 to 93.4, ending at 13.9. 020 on3 has 148 from 10.0 to 98.8, ending at 48.7. On 020 on2 and 020 on3, getproduct and getcart fresh values are 0 or 10000.


| Service               | 010 off1            | 010 off2            | 010 on1             | 010 on2             | **┃** | 015 off1            | 015 off2            | 015 on1             | 015 on2             | 015 on3             | **┃** | 020 off1            | 020 off2            | 020 on1             | 020 on2             | 020 on3             |
| --------------------- | ------------------- | ------------------- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ------------------- | ------------------- | ------------------- | ----- | ------------------- | ------------------- | ------------------- | ------------------- | ------------------- |
| frontend              | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| checkoutservice       | **586/662 (88.5%)** | **566/661 (85.6%)** | **366/662 (55.3%)** | **483/662 (73.0%)** | **┃** | **561/662 (84.7%)** | **588/661 (89.0%)** | **364/663 (54.9%)** | **353/662 (53.3%)** | **470/662 (71.0%)** | **┃** | **573/664 (86.3%)** | **572/661 (86.5%)** | **390/662 (58.9%)** | **355/662 (53.6%)** | **381/662 (57.6%)** |
| recommendationservice | 9/662 (1.4%)        | 22/661 (3.3%)       | 0/662 (0.0%)        | 41/662 (6.2%)       | **┃** | 38/662 (5.7%)       | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 46/662 (6.9%)       | **┃** | 29/664 (4.4%)       | 26/661 (3.9%)       | 15/662 (2.3%)       | 0/662 (0.0%)        | 0/662 (0.0%)        |
| paymentservice        | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 1/662 (0.2%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| emailservice          | **413/662 (62.4%)** | 319/661 (48.3%)     | 140/662 (21.1%)     | 148/662 (22.4%)     | **┃** | **428/662 (64.7%)** | **535/661 (80.9%)** | 105/663 (15.8%)     | 113/662 (17.1%)     | 271/662 (40.9%)     | **┃** | **368/664 (55.4%)** | 287/661 (43.4%)     | 163/662 (24.6%)     | 122/662 (18.4%)     | 135/662 (20.4%)     |
| productcatalogservice | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| cartservice           | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| currencyservice       | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| shippingservice       | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| adservice             | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |
| redis-cart            | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/662 (0.0%)        | 0/661 (0.0%)        | 0/663 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | **┃** | 0/664 (0.0%)        | 0/661 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        | 0/662 (0.0%)        |




## (c) Outbound retry delta

The table is retry by target: the sum of positive Envoy `retry` increments into that service.

- **010 off1.** frontend → recommendationservice 10,732, frontend → checkoutservice 3,579.
- **010 off2.** frontend → recommendationservice 12,777, frontend → checkoutservice 887.
- **010 on1.** frontend → checkoutservice 15,209.
- **010 on2.** frontend → recommendationservice 27,627, frontend → checkoutservice 477.
- **015 off1.** frontend → recommendationservice 16,013, frontend → checkoutservice 21.
- **015 off2.** frontend → checkoutservice 3,644.
- **015 on1.** frontend → checkoutservice 18,077.
- **015 on2.** frontend → checkoutservice 16,860.
- **015 on3.** frontend → recommendationservice 30,600, frontend → checkoutservice 520.
- **020 off1.** frontend → recommendationservice 13,378, frontend → checkoutservice 3,586.
- **020 off2.** frontend → recommendationservice 13,007, frontend → checkoutservice 35.
- **020 on1.** frontend → checkoutservice 13,500.
- **020 on2.** frontend → checkoutservice 15,188.
- **020 on3.** frontend → checkoutservice 16,010, frontend → recommendationservice 2.


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| checkoutservice       | 3,579    | 887      | 15,209  | 477     | **┃** | 21       | 3,644    | 18,077  | 16,860  | 520     | **┃** | 3,586    | 35       | 13,500  | 15,188  | 16,010  |
| recommendationservice | 10,732   | 12,777   | 0       | 27,627  | **┃** | 16,013   | 0        | 0       | 0       | 30,600  | **┃** | 13,378   | 13,007   | 0       | 0       | 2       |
| paymentservice        | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| emailservice          | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| productcatalogservice | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| cartservice           | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| currencyservice       | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| shippingservice       | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| adservice             | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |
| redis-cart            | 0        | 0        | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       | **┃** | 0        | 0        | 0       | 0       | 0       |




## CPU mean / max

App-container millicores, mean / max. Quota is the per-pod CPU limit. The mean / max cells sum that usage across replicas. Frontend is 4 replicas, so its mean can sit above 1150.


| Service               | Quota | Replicas | 010 off1    | 010 off2    | 010 on1     | 010 on2     | **┃** | 015 off1    | 015 off2    | 015 on1     | 015 on2     | 015 on3     | **┃** | 020 off1    | 020 off2    | 020 on1     | 020 on2     | 020 on3     |
| --------------------- | ----- | -------- | ----------- | ----------- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- |
| frontend              | 1150  | 4        | 1245 / 1501 | 1241 / 1515 | 1219 / 1477 | 1241 / 1531 | **┃** | 1261 / 1515 | 1212 / 1458 | 1212 / 1494 | 1238 / 1511 | 1218 / 1533 | **┃** | 1243 / 1500 | 1244 / 1507 | 1237 / 1558 | 1246 / 1527 | 1239 / 1533 |
| checkoutservice       | 800   | 1        | 661 / 796   | 648 / 797   | 538 / 788   | 586 / 777   | **┃** | 662 / 797   | 676 / 797   | 537 / 795   | 535 / 796   | 604 / 789   | **┃** | 658 / 797   | 639 / 789   | 548 / 788   | 532 / 792   | 547 / 791   |
| recommendationservice | 1150  | 1        | 665 / 906   | 689 / 1008  | 636 / 836   | 662 / 989   | **┃** | 708 / 1042  | 677 / 837   | 594 / 774   | 625 / 805   | 666 / 968   | **┃** | 686 / 986   | 677 / 963   | 654 / 944   | 654 / 841   | 637 / 802   |
| paymentservice        | 155   | 1        | 47 / 80     | 45 / 75     | 43 / 74     | 40 / 59     | **┃** | 45 / 58     | 55 / 82     | 44 / 83     | 42 / 77     | 41 / 64     | **┃** | 46 / 94     | 43 / 59     | 45 / 79     | 42 / 73     | 43 / 76     |
| emailservice          | 120   | 1        | 84 / 112    | 83 / 109    | 55 / 108    | 74 / 98     | **┃** | 88 / 111    | 92 / 117    | 50 / 101    | 52 / 112    | 77 / 106    | **┃** | 81 / 111    | 83 / 113    | 59 / 112    | 54 / 104    | 54 / 109    |
| productcatalogservice | 800   | 1        | 332 / 415   | 324 / 406   | 408 / 503   | 328 / 422   | **┃** | 335 / 428   | 403 / 481   | 410 / 501   | 413 / 506   | 331 / 429   | **┃** | 330 / 418   | 323 / 424   | 410 / 503   | 413 / 506   | 412 / 506   |
| cartservice           | 800   | 1        | 302 / 382   | 311 / 398   | 295 / 447   | 314 / 414   | **┃** | 336 / 489   | 285 / 438   | 283 / 362   | 275 / 345   | 311 / 416   | **┃** | 333 / 476   | 312 / 399   | 288 / 462   | 275 / 350   | 294 / 458   |
| currencyservice       | 770   | 1        | 346 / 425   | 352 / 453   | 321 / 402   | 344 / 435   | **┃** | 356 / 439   | 329 / 439   | 314 / 387   | 323 / 400   | 335 / 423   | **┃** | 352 / 435   | 349 / 436   | 329 / 418   | 329 / 408   | 323 / 401   |
| shippingservice       | 770   | 1        | 92 / 113    | 90 / 112    | 76 / 105    | 88 / 114    | **┃** | 90 / 111    | 88 / 108    | 74 / 103    | 77 / 109    | 86 / 112    | **┃** | 90 / 114    | 89 / 112    | 78 / 107    | 77 / 105    | 77 / 106    |
| adservice             | 1150  | 1        | 115 / 151   | 107 / 141   | 126 / 154   | 121 / 165   | **┃** | 114 / 140   | 119 / 145   | 124 / 158   | 126 / 153   | 118 / 164   | **┃** | 115 / 156   | 113 / 143   | 129 / 164   | 130 / 162   | 128 / 155   |
| redis-cart            | 540   | 1        | 38 / 52     | 39 / 55     | 34 / 47     | 40 / 53     | **┃** | 40 / 53     | 34 / 46     | 35 / 50     | 35 / 47     | 39 / 53     | **┃** | 39 / 53     | 39 / 53     | 35 / 49     | 35 / 49     | 34 / 47     |




## Locust goodput

Mean `Goodput` (req/s) on rows 30 through the fifth from the end.


| API          | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| getproduct   | 212.2    | 176.7    | 273.3   | 202.7   | **┃** | 188.9    | 273.4    | 239.7   | 273.3   | 204.9   | **┃** | 202.8    | 197.3    | 273.4   | 273.2   | 273.4   |
| postcheckout | 61.2     | 56.5     | 32.7    | 45.9    | **┃** | 62.0     | 65.6     | 28.9    | 30.8    | 50.9    | **┃** | 56.7     | 58.4     | 35.6    | 30.4    | 33.3    |
| getcart      | 86.2     | 73.4     | 99.4    | 78.3    | **┃** | 68.7     | 99.5     | 90.7    | 99.4    | 72.6    | **┃** | 73.3     | 76.2     | 99.5    | 99.5    | 99.5    |
| postcart     | 89.5     | 89.5     | 89.5    | 89.5    | **┃** | 89.5     | 89.5     | 89.5    | 89.5    | 89.5    | **┃** | 89.5     | 89.5     | 89.5    | 89.5    | 89.5    |
| emptycart    | 5.0      | 5.0      | 5.0     | 5.0     | **┃** | 5.0      | 5.0      | 5.0     | 5.0     | 5.0     | **┃** | 5.0      | 5.0      | 5.0     | 5.0     | 5.0     |




## Locust fail rate

`Fail / RPS` on the same trimmed rows. Locust `Fail` is a 1 s SLO miss.


| API          | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| getproduct   | 0.214    | 0.344    | 0.000   | 0.233   | **┃** | 0.294    | 0.000    | 0.123   | 0.000   | 0.221   | **┃** | 0.246    | 0.266    | 0.000   | 0.000   | 0.000   |
| postcheckout | 0.283    | 0.350    | 0.591   | 0.468   | **┃** | 0.292    | 0.245    | 0.631   | 0.609   | 0.409   | **┃** | 0.332    | 0.334    | 0.561   | 0.617   | 0.580   |
| getcart      | 0.121    | 0.250    | 0.000   | 0.184   | **┃** | 0.295    | 0.000    | 0.088   | 0.000   | 0.242   | **┃** | 0.250    | 0.221    | 0.000   | 0.000   | 0.000   |
| postcart     | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| emptycart    | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |




## Locust P95

Mean `P95` (ms) on the same trimmed rows.


| API          | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| ------------ | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| getproduct   | 708      | 737      | 357     | 822     | **┃** | 717      | 412      | 293     | 327     | 834     | **┃** | 700      | 712      | 368     | 351     | 332     |
| postcheckout | 1035     | 924      | 976     | 880     | **┃** | 894      | 773      | 996     | 1013    | 949     | **┃** | 985      | 898      | 958     | 993     | 988     |
| getcart      | 679      | 698      | 360     | 784     | **┃** | 696      | 396      | 300     | 322     | 801     | **┃** | 676      | 690      | 365     | 362     | 335     |
| postcart     | 76       | 78       | 81      | 77      | **┃** | 76       | 82       | 76      | 77      | 76      | **┃** | 76       | 76       | 81      | 80      | 79      |
| emptycart    | 17       | 20       | 12      | 18      | **┃** | 20       | 28       | 26      | 20      | 19      | **┃** | 18       | 20       | 16      | 13      | 31      |




## Inbound arrival rate

Mean first-attempt arrivals per second from `service_inbound.csv`, last 5 polls dropped.


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 453.0    | 454.6    | 423.0   | 417.7   | **┃** | 453.2    | 459.1    | 387.3   | 423.5   | 423.0   | **┃** | 451.8    | 453.8    | 423.7   | 421.4   | 424.3   |
| checkoutservice       | 59.4     | 50.0     | 58.9    | 40.8    | **┃** | 52.4     | 77.2     | 61.3    | 60.8    | 45.5    | **┃** | 55.8     | 49.7     | 57.8    | 57.1    | 61.2    |
| recommendationservice | 389.9    | 394.2    | 344.8   | 378.2   | **┃** | 397.3    | 380.6    | 309.2   | 345.1   | 387.7   | **┃** | 392.4    | 393.9    | 345.7   | 343.2   | 346.0   |
| paymentservice        | 58.9     | 50.0     | 57.1    | 40.8    | **┃** | 52.4     | 76.3     | 59.1    | 59.0    | 45.4    | **┃** | 55.3     | 49.7     | 56.6    | 55.1    | 59.4    |
| emailservice          | 52.5     | 48.6     | 33.4    | 40.1    | **┃** | 52.4     | 68.6     | 29.4    | 31.7    | 44.6    | **┃** | 49.0     | 49.7     | 35.5    | 31.7    | 33.0    |
| productcatalogservice | 2187.8   | 1955.0   | 2367.1  | 2043.4  | **┃** | 2016.9   | 2583.1   | 2126.0  | 2369.8  | 2069.3  | **┃** | 2083.4   | 2059.3   | 2372.0  | 2357.4  | 2375.1  |
| cartservice           | 495.2    | 481.3    | 482.4   | 452.8   | **┃** | 485.4    | 534.3    | 447.1   | 484.3   | 460.8   | **┃** | 487.1    | 480.5    | 482.3   | 478.6   | 484.7   |
| currencyservice       | 711.1    | 687.4    | 703.3   | 657.4   | **┃** | 687.0    | 748.9    | 633.6   | 705.2   | 660.0   | **┃** | 692.0    | 688.9    | 703.4   | 699.5   | 706.2   |
| shippingservice       | 188.0    | 161.7    | 189.2   | 148.6   | **┃** | 163.0    | 232.8    | 183.8   | 191.9   | 153.7   | **┃** | 170.4    | 163.5    | 188.5   | 185.3   | 192.9   |
| adservice             | 178.7    | 150.4    | 225.2   | 175.7   | **┃** | 160.0    | 226.1    | 197.9   | 225.9   | 178.5   | **┃** | 171.4    | 166.9    | 225.0   | 225.3   | 225.4   |
| redis-cart            | 0.0      | 0.0      | 0.0     | 0.0     | **┃** | 0.0      | 0.0      | 0.0     | 0.0     | 0.0     | **┃** | 0.0      | 0.0      | 0.0     | 0.0     | 0.0     |




## Inbound 5xx fraction


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 0.158    | 0.253    | 0.019   | 0.135   | **┃** | 0.230    | 0.038    | 0.026   | 0.021   | 0.138   | **┃** | 0.202    | 0.209    | 0.017   | 0.019   | 0.021   |
| checkoutservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| recommendationservice | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| paymentservice        | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| emailservice          | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| productcatalogservice | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| cartservice           | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| currencyservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| shippingservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| adservice             | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| redis-cart            | n/a      | n/a      | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     |




## Inbound reset fraction


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| checkoutservice       | 0.061    | 0.017    | 0.246   | 0.010   | **┃** | 0.000    | 0.145    | 0.280   | 0.270   | 0.011   | **┃** | 0.064    | 0.001    | 0.230   | 0.255   | 0.254   |
| recommendationservice | 0.062    | 0.107    | 0.000   | 0.076   | **┃** | 0.084    | 0.000    | 0.000   | 0.000   | 0.071   | **┃** | 0.070    | 0.081    | 0.000   | 0.000   | 0.000   |
| paymentservice        | 0.003    | 0.000    | 0.013   | 0.000   | **┃** | 0.000    | 0.004    | 0.019   | 0.016   | 0.001   | **┃** | 0.004    | 0.000    | 0.012   | 0.012   | 0.012   |
| emailservice          | 0.005    | 0.003    | 0.055   | 0.002   | **┃** | 0.000    | 0.129    | 0.044   | 0.053   | 0.001   | **┃** | 0.004    | 0.001    | 0.056   | 0.063   | 0.049   |
| productcatalogservice | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| cartservice           | 0.000    | 0.000    | 0.002   | 0.000   | **┃** | 0.000    | 0.000    | 0.002   | 0.002   | 0.000   | **┃** | 0.001    | 0.000    | 0.002   | 0.002   | 0.002   |
| currencyservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| shippingservice       | 0.002    | 0.000    | 0.006   | 0.000   | **┃** | 0.000    | 0.001    | 0.009   | 0.006   | 0.000   | **┃** | 0.002    | 0.000    | 0.005   | 0.006   | 0.007   |
| adservice             | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| redis-cart            | n/a      | n/a      | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     |




## Inbound sojourn

Mean `rq_time` sojourn, milliseconds.


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 486      | 490      | 203     | 477     | **┃** | 496      | 243      | 180     | 190     | 479     | **┃** | 482      | 491      | 210     | 207     | 197     |
| checkoutservice       | 198      | 153      | 310     | 109     | **┃** | 144      | 382      | 324     | 318     | 125     | **┃** | 162      | 144      | 303     | 309     | 323     |
| recommendationservice | 431      | 449      | 49      | 409     | **┃** | 461      | 46       | 39      | 40      | 408     | **┃** | 435      | 455      | 54      | 54      | 43      |
| paymentservice        | 3        | 3        | 5       | 2       | **┃** | 3        | 5        | 6       | 5       | 2       | **┃** | 3        | 3        | 6       | 5       | 5       |
| emailservice          | 32       | 25       | 38      | 20      | **┃** | 26       | 85       | 33      | 36      | 21      | **┃** | 24       | 23       | 41      | 38      | 41      |
| productcatalogservice | 4        | 4        | 5       | 5       | **┃** | 4        | 6        | 4       | 4       | 4       | **┃** | 4        | 4        | 5       | 5       | 5       |
| cartservice           | 3        | 3        | 4       | 3       | **┃** | 3        | 4        | 3       | 3       | 3       | **┃** | 3        | 3        | 4       | 4       | 4       |
| currencyservice       | 3        | 3        | 4       | 3       | **┃** | 2        | 4        | 3       | 3       | 3       | **┃** | 2        | 2        | 4       | 4       | 3       |
| shippingservice       | 1        | 1        | 1       | 1       | **┃** | 1        | 1        | 1       | 1       | 1       | **┃** | 1        | 1        | 1       | 1       | 1       |
| adservice             | 1        | 1        | 1       | 1       | **┃** | 1        | 1        | 1       | 1       | 1       | **┃** | 1        | 1        | 1       | 1       | 1       |
| redis-cart            | n/a      | n/a      | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     |




## Share of inbound requests above 500 ms


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 0.749    | 0.789    | 0.040   | 0.699   | **┃** | 0.795    | 0.114    | 0.040   | 0.039   | 0.677   | **┃** | 0.755    | 0.793    | 0.046   | 0.039   | 0.042   |
| checkoutservice       | 0.068    | 0.017    | 0.340   | 0.012   | **┃** | 0.001    | 0.193    | 0.411   | 0.376   | 0.012   | **┃** | 0.071    | 0.001    | 0.296   | 0.346   | 0.356   |
| recommendationservice | 0.264    | 0.326    | 0.000   | 0.234   | **┃** | 0.380    | 0.000    | 0.000   | 0.000   | 0.286   | **┃** | 0.315    | 0.312    | 0.000   | 0.000   | 0.000   |
| paymentservice        | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| emailservice          | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| productcatalogservice | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| cartservice           | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| currencyservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| shippingservice       | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| adservice             | 0.000    | 0.000    | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   | **┃** | 0.000    | 0.000    | 0.000   | 0.000   | 0.000   |
| redis-cart            | n/a      | n/a      | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     | **┃** | n/a      | n/a      | n/a     | n/a     | n/a     |




## CPU use as a fraction of per-pod quota × replicas

Mean / max of `cpu_millicores / (per-pod limit × replica_count)`.


| Service               | 010 off1    | 010 off2    | 010 on1     | 010 on2     | **┃** | 015 off1    | 015 off2    | 015 on1     | 015 on2     | 015 on3     | **┃** | 020 off1    | 020 off2    | 020 on1     | 020 on2     | 020 on3     |
| --------------------- | ----------- | ----------- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- |
| frontend              | 0.27 / 0.33 | 0.27 / 0.33 | 0.27 / 0.32 | 0.27 / 0.33 | **┃** | 0.27 / 0.33 | 0.26 / 0.32 | 0.26 / 0.32 | 0.27 / 0.33 | 0.26 / 0.33 | **┃** | 0.27 / 0.33 | 0.27 / 0.33 | 0.27 / 0.34 | 0.27 / 0.33 | 0.27 / 0.33 |
| checkoutservice       | 0.83 / 0.99 | 0.81 / 1.00 | 0.67 / 0.98 | 0.73 / 0.97 | **┃** | 0.83 / 1.00 | 0.84 / 1.00 | 0.67 / 0.99 | 0.67 / 0.99 | 0.76 / 0.99 | **┃** | 0.82 / 1.00 | 0.80 / 0.99 | 0.69 / 0.98 | 0.66 / 0.99 | 0.68 / 0.99 |
| recommendationservice | 0.58 / 0.79 | 0.60 / 0.88 | 0.55 / 0.73 | 0.58 / 0.86 | **┃** | 0.62 / 0.91 | 0.59 / 0.73 | 0.52 / 0.67 | 0.54 / 0.70 | 0.58 / 0.84 | **┃** | 0.60 / 0.86 | 0.59 / 0.84 | 0.57 / 0.82 | 0.57 / 0.73 | 0.55 / 0.70 |
| paymentservice        | 0.30 / 0.52 | 0.29 / 0.48 | 0.27 / 0.48 | 0.26 / 0.38 | **┃** | 0.29 / 0.37 | 0.35 / 0.53 | 0.28 / 0.54 | 0.27 / 0.50 | 0.26 / 0.41 | **┃** | 0.29 / 0.61 | 0.28 / 0.38 | 0.29 / 0.51 | 0.27 / 0.47 | 0.28 / 0.49 |
| emailservice          | 0.70 / 0.93 | 0.70 / 0.91 | 0.45 / 0.90 | 0.61 / 0.82 | **┃** | 0.73 / 0.93 | 0.77 / 0.97 | 0.42 / 0.84 | 0.44 / 0.93 | 0.64 / 0.88 | **┃** | 0.68 / 0.93 | 0.69 / 0.94 | 0.49 / 0.93 | 0.45 / 0.87 | 0.45 / 0.91 |
| productcatalogservice | 0.41 / 0.52 | 0.41 / 0.51 | 0.51 / 0.63 | 0.41 / 0.53 | **┃** | 0.42 / 0.54 | 0.50 / 0.60 | 0.51 / 0.63 | 0.52 / 0.63 | 0.41 / 0.54 | **┃** | 0.41 / 0.52 | 0.40 / 0.53 | 0.51 / 0.63 | 0.52 / 0.63 | 0.51 / 0.63 |
| cartservice           | 0.38 / 0.48 | 0.39 / 0.50 | 0.37 / 0.56 | 0.39 / 0.52 | **┃** | 0.42 / 0.61 | 0.36 / 0.55 | 0.35 / 0.45 | 0.34 / 0.43 | 0.39 / 0.52 | **┃** | 0.42 / 0.59 | 0.39 / 0.50 | 0.36 / 0.58 | 0.34 / 0.44 | 0.37 / 0.57 |
| currencyservice       | 0.45 / 0.55 | 0.46 / 0.59 | 0.42 / 0.52 | 0.45 / 0.56 | **┃** | 0.46 / 0.57 | 0.43 / 0.57 | 0.41 / 0.50 | 0.42 / 0.52 | 0.43 / 0.55 | **┃** | 0.46 / 0.56 | 0.45 / 0.57 | 0.43 / 0.54 | 0.43 / 0.53 | 0.42 / 0.52 |
| shippingservice       | 0.12 / 0.15 | 0.12 / 0.15 | 0.10 / 0.14 | 0.11 / 0.15 | **┃** | 0.12 / 0.14 | 0.11 / 0.14 | 0.10 / 0.13 | 0.10 / 0.14 | 0.11 / 0.15 | **┃** | 0.12 / 0.15 | 0.12 / 0.15 | 0.10 / 0.14 | 0.10 / 0.14 | 0.10 / 0.14 |
| adservice             | 0.10 / 0.13 | 0.09 / 0.12 | 0.11 / 0.13 | 0.11 / 0.14 | **┃** | 0.10 / 0.12 | 0.10 / 0.13 | 0.11 / 0.14 | 0.11 / 0.13 | 0.10 / 0.14 | **┃** | 0.10 / 0.14 | 0.10 / 0.12 | 0.11 / 0.14 | 0.11 / 0.14 | 0.11 / 0.13 |
| redis-cart            | 0.07 / 0.10 | 0.07 / 0.10 | 0.06 / 0.09 | 0.07 / 0.10 | **┃** | 0.07 / 0.10 | 0.06 / 0.09 | 0.07 / 0.09 | 0.06 / 0.09 | 0.07 / 0.10 | **┃** | 0.07 / 0.10 | 0.07 / 0.10 | 0.06 / 0.09 | 0.06 / 0.09 | 0.06 / 0.09 |




## Detector max utilization

Max `utilization` in `topfull_detect.csv` (cAdvisor CPU / per-pod quota).


| Service               | 010 off1 | 010 off2 | 010 on1 | 010 on2 | **┃** | 015 off1 | 015 off2 | 015 on1 | 015 on2 | 015 on3 | **┃** | 020 off1 | 020 off2 | 020 on1 | 020 on2 | 020 on3 |
| --------------------- | -------- | -------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- | ----- | -------- | -------- | ------- | ------- | ------- |
| frontend              | 0.337    | 0.342    | 0.357   | 0.346   | **┃** | 0.344    | 0.338    | 0.359   | 0.378   | 0.348   | **┃** | 0.338    | 0.340    | 0.368   | 0.369   | 0.366   |
| checkoutservice       | 1.048    | 1.041    | 1.036   | 1.029   | **┃** | 1.049    | 1.039    | 1.052   | 1.036   | 1.039   | **┃** | 1.046    | 1.031    | 1.034   | 1.049   | 1.046   |
| recommendationservice | 0.828    | 0.930    | 0.790   | 0.929   | **┃** | 0.956    | 0.768    | 0.729   | 0.737   | 0.973   | **┃** | 0.949    | 0.884    | 0.870   | 0.773   | 0.757   |
| paymentservice        | 0.587    | 0.555    | 0.665   | 0.510   | **┃** | 0.561    | 0.632    | 0.774   | 0.735   | 0.542   | **┃** | 0.716    | 0.529    | 0.923   | 0.703   | 0.665   |
| emailservice          | 1.033    | 1.042    | 1.050   | 1.000   | **┃** | 1.025    | 1.058    | 1.008   | 1.025   | 1.017   | **┃** | 1.017    | 1.008    | 1.033   | 1.067   | 1.050   |
| productcatalogservice | 0.552    | 0.530    | 0.667   | 0.583   | **┃** | 0.564    | 0.642    | 0.664   | 0.662   | 0.583   | **┃** | 0.541    | 0.566    | 0.667   | 0.682   | 0.674   |
| cartservice           | 0.515    | 0.574    | 0.579   | 0.580   | **┃** | 0.680    | 0.573    | 0.542   | 0.465   | 0.579   | **┃** | 0.624    | 0.569    | 0.621   | 0.490   | 0.608   |
| currencyservice       | 0.613    | 0.666    | 0.587   | 0.630   | **┃** | 0.629    | 0.640    | 0.566   | 0.562   | 0.603   | **┃** | 0.626    | 0.629    | 0.601   | 0.587   | 0.569   |
| shippingservice       | 0.184    | 0.179    | 0.173   | 0.175   | **┃** | 0.182    | 0.174    | 0.178   | 0.179   | 0.183   | **┃** | 0.183    | 0.171    | 0.178   | 0.170   | 0.175   |
| adservice             | 0.154    | 0.149    | 0.164   | 0.161   | **┃** | 0.141    | 0.163    | 0.177   | 0.160   | 0.167   | **┃** | 0.156    | 0.177    | 0.189   | 0.162   | 0.165   |
| redis-cart            | 0.202    | 0.226    | 0.206   | 0.220   | **┃** | 0.193    | 0.183    | 0.189   | 0.202   | 0.204   | **┃** | 0.202    | 0.189    | 0.172   | 0.206   | 0.202   |


