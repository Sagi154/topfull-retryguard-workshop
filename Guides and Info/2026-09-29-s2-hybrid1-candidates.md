# S2 Hybrid-1 candidates

Proposal for the next both-off series. Nothing here has been run. The goal is one hold where `recommendationservice` and `checkoutservice` are both hot, on limits that earlier tables already used. Payment and email stay at 200 m. This doc does not shrink them to force a detector hit.

Counts are getproduct / postcheckout / getcart / postcart / emptycart. Holds are 600 s, both controllers off, `spawn_rate` 50, 360 s cool-off between holds. Sidecar request is 100 m with no CPU limit, the same setting as the Hybrid holds (run67–run70).

Next free both-off slot is **run74**. `experiments/configs/scenario_2_baseline_no_topfull.yaml` is already `run_number: 74` / `log_folder: baseline_no_topfull_sustained_overload_run74`, with `scale_constraints: []`. Local folders exist through `baseline_no_topfull_sustained_overload_run73`. `TestBothOffYamlRestored` expects run74. These six holds would be run74 through run79, and the YAML would move to run80 afterward.

## Why this table

Inbound arrival (req/s) and failure fraction are the steady window 120–500 s of `service_inbound.csv`. `postcheckout` RPS is the mean Locust `RPS` over that same window. The frontend column is that service's inbound failure fraction, from the same file.

| Hold | Table | postcheckout RPS | checkout in | email in | recs in | frontend fail |
|---|---|---:|---:|---:|---:|---:|
| run6 | Paper | 58 | 50 / 0.35 | 23 / 0.02 | 726 / 0.24 | 0.35 |
| run67 | Hybrid | 113 | 53 / 0.00 | 53 / 0.00 | 824 / 0.23 | 0.51 |
| run68 | Hybrid | 112 | 57 / 0.00 | 57 / 0.00 | 830 / 0.22 | 0.47 |
| run69 | Hybrid | 137 | 76 / 0.06 | 68 / 0.00 | 777 / 0.22 | 0.47 |
| run61 | Checkout-3 | 125 | 293 / 0.39 | 287 / 0.60 | 401 / 0.00 | 0.14 |
| run60 | Checkout-3 | 144 | 368 / 0.48 | 109 / 0.26 | 397 / 0.00 | 0.21 |

Four Hybrid holds (run67–run70) put recommendations at 777–830 inbound with a failure fraction near 0.22. That is the 1150 m × 1 shape. On those same holds the frontend failure fraction is about 0.5, and checkout only sees about half of the Locust `postcheckout` rate (53–76 req/s). Checkout at 800 m × 2 needs about 107 req/s before it is hot, so it stayed cold.

Checkout, payment, and email only sat near 300 req/s together on the Checkout-3 chain holds (run60, run61), after checkout itself saturated and retries multiplied its arrival. Run 6 is the one hold where checkout was hot during a recommendations storm, and its checkout quota was 615 m × 1. Email on that hold saw 23 req/s.

The change from Hybrid on checkout is the replica count, not the leaf quotas. 800 m × 1 is hot near 53 req/s (0.8 × 800 / 12), which is the arrival the storm already leaves on checkout. Frontend on this table is 1150 m × 6, not the 4-replica pin those Hybrid numbers were measured on.

## Hybrid-1

Per-pod millicores. Request equals limit. One replica except frontend. Every limit is one that Paper, Checkout-3, or Hybrid already used.

| Service | Quota | Replicas |
|---|---:|---:|
| frontend | 1150 | 6 |
| checkoutservice | 800 | 1 |
| recommendationservice | 1150 | 1 |
| productcatalogservice | 600 | 1 |
| cartservice | 600 | 1 |
| currencyservice | 650 | 1 |
| shippingservice | 400 | 1 |
| adservice | 600 | 1 |
| paymentservice | 200 | 1 |
| emailservice | 200 | 1 |
| redis-cart | 300 | 1 |

Deployment total is 12,400 m, under the paper four-frontend ceiling of 13,360 m. H3 raises checkout to 1000 m × 1 and nothing else; that total is 12,600 m.

Frontend stays off `scale_constraints` (1150 m is the paper limit). `paper_cpu_reconcile: false` for the holds. `redis-cart` container name is `redis`. Pin frontend HPA `minReplicas = maxReplicas = 6` and catalog HPA `minReplicas = maxReplicas = 1` for the series. Every other deployment stays at 1 replica, so no `kubectl scale` beyond that pin. Six frontend pods at 1150 m plus a 100 m sidecar on each of the 16 pods is 14,000 m of CPU requests before system pods, on a 16-vCPU worker. If a pod stays Pending, that is a scheduling failure for this table.

## Holds

Expected checkout arrival is arithmetic from the Hybrid ratio above (checkout inbound ≈ 0.5 × Locust `postcheckout` RPS, and that RPS ≈ 0.56 × configured users on the storming holds). Recommendations first-attempt is the same kind of estimate from getproduct + getcart + postcheckout. Those ratios were measured with frontend pinned at 4 replicas. This table pins it at 6, so the expected column is a guide from that ratio, not a prediction for 6 replicas. Saturation used for the "over the line" call is about 67 req/s at 800 m and about 83 req/s at 1000 m (quota / 12).

| Slot | Hold | Table | Mix | Expected checkout in | Expected recs first-attempt |
|---|---|---|---|---:|---:|
| run74 | H1 | Hybrid-1 | 300 / 300 / 200 / 10 / 10 | ~84 | ~450 |
| run75 | H2 | Hybrid-1 | 250 / 350 / 150 / 10 / 10 | ~98 | ~420 |
| run76 | H3 | Hybrid-1, checkout 1000 m | 250 / 350 / 150 / 10 / 10 | ~98 | ~420 |
| run77 | H4 | Hybrid-1 | 340 / 100 / 240 / 10 / 10 | ~28 | ~380 |
| run78 | H5 | Hybrid-1 | 320 / 120 / 200 / 10 / 10 | ~34 | ~360 |
| run79 | H6 | Hybrid-1 | 320 / 150 / 220 / 10 / 10 | ~42 | ~390 |

H4 is run 6's mix (340 / 100 / 240 / 10 / 10) on this table. H5 and H6 keep the browse pair near that mix and raise `postcheckout` from 100 to 120, then to 150.

H1 is the high-`postcheckout` hold. Checkout at ~84 req/s is over the ~67 line on the 4-replica ratio, and recommendations stays on the shape that stormed on run67–run70. H2 raises `postcheckout` further and cuts the browse tags. H3 is the same mix as H2 with checkout at 1000 m, to separate "the arrival was too small" from "800 m was the wrong quota."

H4–H6 sit under that ~67 line if the 4-replica ratio still applies (~28, ~34, ~42). They are the run 6 neighbourhood: same recommendations shape, checkout at 800 m × 1 instead of paper 615 m × 1, frontend at 6 replicas instead of 4. Whether checkout still heats at a `postcheckout` of 100–150 is what those three measure.

H1 and H2 use `postcheckout` counts (300 and 350) higher than any both-off hold so far. The recommendations storm may push frontend failure above the ~0.5 seen on Hybrid and cut checkout's arrival back under the line. Six frontend replicas gives more storefront capacity than the 4-replica Hybrid holds, so checkout may see a larger share of `postcheckout` than the ~0.5 ratio.

## What a result would mean

Checkout and recommendations both hot has a measured precedent: run 6, on Paper, with checkout at 615 m × 1 and frontend pinned at 4. Hybrid-1 keeps that recommendations shape, moves checkout from 615 m to 800 m × 1, and pins frontend at 6 replicas. The 6-replica pin is not a measured condition on any hold in the table above.

Payment and email at 200 m are not predicted to clear. On the chain holds they only reached ~100–300 req/s after checkout latched, and the one storm-plus-hot-checkout hold (run 6) left email at 23 req/s. If H1 shows checkout hot and email cold, that is the result for this table. The leaf quotas stay at 200 m.

## Related

- Hybrid holds these numbers come from: [2026-09-29-s2-runs-60-70.md](2026-09-29-s2-runs-60-70.md), [2026-09-29-s2-final-candidate-abc-report.md](2026-09-29-s2-final-candidate-abc-report.md).
- The series that produced Hybrid: [2026-09-29-s2-final-candidate-holds.md](2026-09-29-s2-final-candidate-holds.md).
- CPU tables, including Hybrid: [2026-09-26-s2-cpu-limits-for-spread.md](2026-09-26-s2-cpu-limits-for-spread.md).
- How (a)/(b)/(c) are read: [2026-09-24-s2-both-off-abc-reading.md](2026-09-24-s2-both-off-abc-reading.md).

## Results

Scored with `python experiments/s2_both_off_abc.py` on the six pulled folders. Streak is the longest inbound rejection streak above 0.20. Overloaded share is Layer B `overloaded` ticks over detector ticks. The largest retry edge is the biggest outbound retry delta.

| Slot | Hold | Checkout streak | Recommendations streak | Checkout overloaded | Recommendations overloaded | Largest retry edge |
|---|---|---:|---:|---:|---:|---|
| run74 | H1 | 7 | 51 | 64/640 (10.0%) | 268/640 (41.9%) | frontend→recommendationservice 139,318 |
| run75 | H2 | 14 | 78 | 71/639 (11.1%) | 220/639 (34.4%) | frontend→recommendationservice 107,716 |
| run76 | H3 | 12 | 23 | 26/639 (4.1%) | 183/639 (28.6%) | frontend→recommendationservice 100,198 |
| run77 | H4 | 3 | 83 | 20/639 (3.1%) | 259/639 (40.5%) | frontend→recommendationservice 135,814 |
| run78 | H5 | 4 | 40 | 28/639 (4.4%) | 245/639 (38.3%) | frontend→recommendationservice 132,112 |
| run79 | H6 | 7 | 77 | 21/639 (3.3%) | 258/639 (40.4%) | frontend→recommendationservice 137,660 |

No hold had both checkout and recommendations at streak ≥ 30. Recommendations cleared 30 on run74, run75, run77, run78, and run79. Checkout's longest streak was 14, on run75. Run76 cleared neither bar. Paper CPU, the HPAs (frontend 1–4, catalog 1–2), and sidecar `proxyCPU` 100 m with `proxyCPULimit` absent are restored. Next free both-off slot is **run80**.
