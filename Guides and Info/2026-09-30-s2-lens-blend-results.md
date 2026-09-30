# S2 lens-blend results (runs 80–84)

Runs 80 through 84 were launched, all both-off 600 s holds. The sidecar request that scheduled was 100 m (`sidecar.istio.io/proxyCPU` on all 11 Deployments, no `proxyCPULimit`). Pods went Pending only on the paper CPU reconcile, when cartservice requested 1920 m, and those pods were gone before Locust after the hold limits applied. The three VMs are stopped at the end of this task.

## Pass bar

A blend clears recommendationservice (`streak >= 10` and `ov >= 10`), checkoutservice (`streak >= 10` and `ov >= 10`), and emailservice or paymentservice (`ov >= 10`). A near-miss clears two of those and has the missing one at `streak >= 5` or `ov >= 5`. Anything else is a miss. Series rows are from `s2_canon_80_80.json` through `s2_canon_84_84.json`. Reference rows are from the ranking guide and are not this series.

| Slot | Table | Mix | Sum | Rec streak | Rec ov | Checkout streak | Checkout ov | Email streak | Email ov | Payment streak | Payment ov | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 80 | Paper-C1 | 325/80/100/90/5 | 600 | 0 | 17 | 549 | 579 | 8 | 17 | 1 | 0 | near |
| 81 | Paper-C3 | 250/100/100/100/5 | 555 | 0 | 0 | 563 | 585 | 5 | 5 | 7 | 37 | miss |
| 82 | Hybrid-C2 | 170/210/200/10/10 | 600 | 1 | 492 | 25 | 104 | 1 | 6 | 9 | 0 | miss |
| 83 | tweak of run80 | 375/80/100/90/5 | 650 | 6 | 566 | 0 | 24 | 0 | 8 | 0 | 0 | miss |
| 84 | replay of run80 | 325/80/100/90/5 | 600 | 2 | 540 | 0 | 157 | 0 | 29 | 0 | 0 | miss |
| 10 | Paper, reference | 325/80/100/100/5 | 610 | 56 | 561 | 21 | 53 | not printed | not printed | not printed | not printed | reference |
| 11 | Paper, reference | 250/100/100/100/5 | 555 | 22 | 560 | 38 | 57 | not printed | not printed | not printed | not printed | reference |
| 69 | Hybrid, reference | 200/250/250/10/10 | 720 | 19 | 549 | 23 | 37 | not printed | 14 | not printed | 3 | reference |

The ranking guide prints runs 10 and 11 only for checkout and recommendations. For run 69 it prints email overloaded ticks 14 and payment overloaded ticks 3, and it does not print email or payment streaks.

## Task 5 branch

Branch no blend, one or more near-misses: run80 is the only near-miss (missing recommendationservice, leaf_ov 17); run83 tweaked getproduct +50 and classified as a miss, so run84 replayed run80 and also classified as a miss. No blend survived a replay.

## Sampling

| Slot | gap2_pct | span |
|---|---:|---:|
| 80 | 0 | 695.0 |
| 81 | 0 | 694.0 |
| 82 | 0 | 698.0 |
| 83 | 0 | 694.0 |
| 84 | 0 | 694.0 |
