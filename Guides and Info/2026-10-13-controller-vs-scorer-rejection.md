# Controller rejection and scorer rejection are not the same number

Date: 2026-10-13. Status: resolved 2026-10-13. The scorer now uses the controller formula; HTTP-only values are kept for the four read callees. See [docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md](../docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md).

`retryguard.py` and `analysis_score.py` both compute an "inbound rejection" per service from `service_inbound.csv`. On four callees they disagree by design. This file says where, why, what it affects, and what the options are.

## The two definitions

Both use the diff of two consecutive inbound polls of the same service.

| | Formula | Where |
|---|---|---|
| Controller | `(Δ5xx + Δresets + Δgrpc_4 + Δgrpc_14) / Δtotal` on the four read callees. `(Δ5xx + Δresets) / Δtotal` on every other service. | `measure_inbound_rejection(..., count_grpc)` in `experiments/retryguard.py`, called with `service in GRPC_RETRY_CALLEES` |
| Scorer | `(Δ5xx + Δresets) / Δtotal` on every service. | `rejection_streaks` in `experiments/analysis_score.py` (`failed = 5xx + resets`) |

The four read callees (`GRPC_RETRY_CALLEES`): `adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`.

## Why the controller adds the gRPC codes

- On those four callees the VirtualService retry policy is `retryOn: 5xx,reset,connect-failure,unavailable,deadline-exceeded` (`RETRY_ON_GRPC` in `retryguard.py` and `run_scenario.py`). Every method on them is a read, so a repeat only costs load. `cartservice` and `shippingservice` stay on the plain `RETRY_ON` because one route rule cannot split a read from a write.
- A gRPC `UNAVAILABLE` (status 14) or `DEADLINE_EXCEEDED` (status 4) reaches Envoy as HTTP 200 with a `grpc-status` trailer. Envoy's inbound `5xx` and `resets` counters do not see it, yet the retry policy retries on it.
- If the controller measured only `5xx + resets` there, it would be blind to the failures that cause the retries on those callees. `envoy_retry_collector.py` therefore writes `grpc_4` and `grpc_14` (and `grpc_2`, `grpc_13`) as `istio_requests_total` rows with `response_code=200` and one `grpc_response_status` each. The controller reads only `grpc_4` and `grpc_14`.

## What the mismatch affects

- **Scorer "Rejection, beside (a)" table** (ANALYSIS-TEMPLATE item 5): longest streak and count above 0.20, from `5xx + resets` only. On the four read callees it can be lower than the controller's value for the same seconds. A callee with a controller-side shed or a long OFF window can show a short or empty streak here.
- **OFF-window rejection rows** (ANALYSIS-TEMPLATE item 8, Part 2): these are read from `retryguard.log` `metric=rejection` samples, so they are the controller's value, not the scorer's. A guide can show one number in item 5 and a different one in item 8 for the same callee. That is expected, not a bug.
- **Re-enable reading:** the 0→1 step needs `interval_samples` consecutive controller-rejection samples under `reenable_rejection`. Checking that streak against the scorer's CSV-based rejection on a read callee can look as if the bar was met earlier or later than the log shows.
- **Not affected:** `cartservice`, `shippingservice`, `checkoutservice`, `emailservice`, `paymentservice`. The two definitions are identical there. Edge rpr (shed and climb) is a separate signal from `service_edges.csv` and is unaffected.

The scorer does print the pair: the `grpc_4 / grpc_14` table lists the hold's summed positive deltas per service (`analysis_score.py`, the "gRPC counted in the rejection rate and in the retry policy" line). That makes the gap visible, but it does not fold the numbers into the rejection streaks.

## How to read a guide today

- Treat item 5 as the HTTP-visible rejection. Treat the log's `metric=rejection` samples as what RetryGuard acted on.
- On the four read callees, compare against the `grpc_4 / grpc_14` table before saying a shed or re-enable "had no matching rejection".
- When the two disagree on one of those callees, the log wins for controller behaviour.

## Options

**Chosen: 2, plus the HTTP-only column from 3.**

1. **Document only (current plan).** Note the difference in `ANALYSIS-TEMPLATE.md` and the metrics docs. No code change. Keeps the scorer's numbers comparable with every earlier guide.
2. **Make the scorer match the controller.** In `rejection_streaks`, add `grpc_4 + grpc_14` to `failed` for the four read callees only. Item 5 and the controller then agree, but numbers in new guides stop being comparable to older ones for those callees. It needs a template note and a test in `test_analysis_score.py`.
3. **Print both.** Keep item 5 as is and add a second column or table for the controller-equivalent rejection on the four callees. Costs some table width and keeps old comparisons.

No option is chosen yet. Option 1 is in the metrics-docs refresh plan; options 2 and 3 are open.

## Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) items 5, 7, 8
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md)
- [METRICS-GATHERED.md](METRICS-GATHERED.md) (`service_inbound.csv` columns)
