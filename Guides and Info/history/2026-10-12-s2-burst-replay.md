# Burst replay on the four S2 both-on holds (2026-10-12)

Read-only replay of burst mode over the finished tuned both-on S2 holds. No live hold. The controller code is [RETRYGUARD-IMPLEMENTATION.md](../RETRYGUARD-IMPLEMENTATION.md); the decision is [ADR 0007](../../docs/adr/0007-burst-mode-sliding-aggregate.md).

## 1. Setup

- **Folders:** `experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep1` through `rep4`. All four have `service_edges.csv`.
- **Holds.** RetryGuard on, TopFull on, Paper-C1, mix **275 / 90 / 100 / 90 / 5**. Tuned parameters: `retry_metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.4`, climb `0.16/0.32` at 10 s, `reenable_rejection=0.25`. Those holds logged zero toggles. Score: [2026-10-11-s2-rgtf1-rep3-rep4-abc.md](2026-10-11-s2-rgtf1-rep3-rep4-abc.md).
- **Replay rule.** Sliding 5 s window, volume floor 20 first attempts, bar at 3 attempts (`burst_rpr` of 1.0, 1.5, or 2.0). The window clears after each fire. Recovery is not modelled, so the edge is assumed to stay at 3 attempts. Only the first fire per edge predicts a live run. Later fires assume instant recovery.
- **Command:**

```powershell
$base = "experiments/results/campaign_48/S2_sustained_overload"
python experiments/burst_replay.py "$base/study4_s2_tune_rgtf1_rep1" "$base/study4_s2_tune_rgtf1_rep2" "$base/study4_s2_tune_rgtf1_rep3" "$base/study4_s2_tune_rgtf1_rep4" --bars 1.0 1.5 2.0
```

## 2. Fires

Only `frontend → checkoutservice` fired. Every other edge is omitted because its count is 0. **Fires** is how many times the 5 s window crossed that bar. **First fire** is seconds after the first mesh row.

| Run | Bar | Edge | Fires | First fire (s) |
| --- | ---: | --- | ---: | ---: |
| study4_s2_tune_rgtf1_rep1 | 1.0 | frontend → checkoutservice | 121 | 104 |
| study4_s2_tune_rgtf1_rep1 | 1.5 | frontend → checkoutservice | 91 | 105 |
| study4_s2_tune_rgtf1_rep1 | 2.0 | frontend → checkoutservice | 63 | 106 |
| study4_s2_tune_rgtf1_rep2 | 1.0 | frontend → checkoutservice | 116 | 108 |
| study4_s2_tune_rgtf1_rep2 | 1.5 | frontend → checkoutservice | 84 | 109 |
| study4_s2_tune_rgtf1_rep2 | 2.0 | frontend → checkoutservice | 59 | 110 |
| study4_s2_tune_rgtf1_rep3 | 1.0 | frontend → checkoutservice | 54 | 109 |
| study4_s2_tune_rgtf1_rep3 | 1.5 | frontend → checkoutservice | 39 | 111 |
| study4_s2_tune_rgtf1_rep3 | 2.0 | frontend → checkoutservice | 29 | 111 |
| study4_s2_tune_rgtf1_rep4 | 1.0 | frontend → checkoutservice | 61 | 111 |
| study4_s2_tune_rgtf1_rep4 | 1.5 | frontend → checkoutservice | 40 | 113 |
| study4_s2_tune_rgtf1_rep4 | 2.0 | frontend → checkoutservice | 31 | 113 |

The first fire is 104–113 s on every hold, at every bar. The live prediction is one checkout shed per hold, about that far in. Whether retries come back on depends on the existing recovery path (rejection at or under 0.25 for 20 s, then the climbs). The replay does not model that, so the later counts are not a live toggle forecast.

## 3. Volume floor

Window first-attempt sums on `frontend → checkoutservice`. The floor of 20 sits under the 5th percentile on every hold, so it does not blind checkout.

| Run | Median | p5 | Min |
| --- | ---: | ---: | ---: |
| study4_s2_tune_rgtf1_rep1 | 210 | 69 | 1 |
| study4_s2_tune_rgtf1_rep2 | 215 | 66 | 1 |
| study4_s2_tune_rgtf1_rep3 | 247 | 81 | 1 |
| study4_s2_tune_rgtf1_rep4 | 268 | 84 | 8 |

The minimum is the opening window, before 5 s of ticks have arrived. It does not pull the 5th percentile under 20.
