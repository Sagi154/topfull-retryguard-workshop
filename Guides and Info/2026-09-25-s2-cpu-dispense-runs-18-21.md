# S2 both-off runs 18–21: user counts and CPU

600 s holds, both TopFull RL and RetryGuard off, `spawn_rate` 50. Frontend HPA pinned at 4 replicas (sidecar request 90 m). Catalog HPA max 1, so productcatalog stayed at 1 replica. Request equals limit on every service. 300 s cool-off before run18 and between holds.

These four holds replay earlier both-off mixes under one new CPU table. The aim was to keep checkout from being the bottleneck, and to see how user counts and per-service CPU move overload and retries across more of the mesh.

Folders: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run{18,19,20,21}/`. The live limits below are the `service_capacity.json` snapshot taken after the CPU patches, on every run.

## User counts

Order is getproduct / postcheckout / getcart / postcart / emptycart.

| Run | Replays | getproduct | postcheckout | getcart | postcart | emptycart |
|---|---|---:|---:|---:|---:|---:|
| 18 | both-off run6 | 340 | 100 | 240 | 10 | 10 |
| 19 | both-off run10 | 325 | 80 | 100 | 100 | 5 |
| 20 | both-off run11 | 250 | 100 | 100 | 100 | 5 |
| 21 | both-off run12 | 100 | 150 | 100 | 100 | 5 |

## CPU limits (millicores)

Same table on run18, run19, run20, and run21. Frontend is per replica; four replicas were up, so the frontend cap across the deployment is 4 × 1150 m.

| Service | This dispense | Paper table | Replicas |
|---|---:|---:|---:|
| cartservice | 1200 | 1920 | 1 |
| adservice | 800 | 1150 | 1 |
| checkoutservice | 1500 | 615 | 1 |
| emailservice | 155 | 155 | 1 |
| redis-cart | 540 | 540 | 1 |
| shippingservice | 770 | 770 | 1 |
| recommendationservice | 1250 | 1150 | 1 |
| frontend | 1150 | 1150 | 4 |
| currencyservice | 770 | 770 | 1 |
| paymentservice | 155 | 155 | 1 |
| productcatalogservice | 1535 | 1535 | 1 |

Four services differ from the paper table: cart 1920 → 1200, ad 1150 → 800, checkout 615 → 1500, recommendations 1150 → 1250. The other seven stay on the paper limits. Checkout's raise is the change that takes it off the previous bottleneck quota (615 m). Cart and ad are the two tighter caps.

## Related

- (a)/(b)/(c) scorecard for these four holds: [2026-09-25-s2-both-off-abc-runs-18-21.md](2026-09-25-s2-both-off-abc-runs-18-21.md).
- Why these mixes: [2026-09-25-s2-overload-user-count-calibration.md](../docs/superpowers/specs/2026-09-25-s2-overload-user-count-calibration.md).
- Earlier both-off scorecard for mixes 9–13, under the paper CPU table: [2026-09-24-s2-both-off-runs-9-13.md](2026-09-24-s2-both-off-runs-9-13.md).
- Source mix 6 (340/100/240/10/10): [2026-09-24-s2-both-off-runs-summary.md](2026-09-24-s2-both-off-runs-summary.md).
