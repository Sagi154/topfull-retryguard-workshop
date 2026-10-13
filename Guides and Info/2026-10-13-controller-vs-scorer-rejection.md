# Controller rejection and scorer rejection

Date: 2026-10-13. Status: resolved 2026-10-13. The scorer uses the controller formula. HTTP-only values stay beside it for the four read callees. See [docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md](../docs/superpowers/plans/2026-10-13-scorer-matches-controller-rejection.md).

`retryguard.py` and `analysis_score.py` both compute inbound rejection from `service_inbound.csv`. They use the same formula.

| | Formula |
|---|---|
| Both | `(Δ5xx + Δresets + Δgrpc_4 + Δgrpc_14) / Δtotal` on the four read callees. `(Δ5xx + Δresets) / Δtotal` on every other service. |
| HTTP-only companion | `(Δ5xx + Δresets) / Δtotal` on those four callees. Printed so guides written before 2026-10-13 can be compared. Rescored copies end in `-rescored.md`. |

The four read callees (`GRPC_RETRY_CALLEES`): `adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`.

## Why the gRPC codes are in the rate

- On those four callees the VirtualService retry policy is `retryOn: 5xx,reset,connect-failure,unavailable,deadline-exceeded` (`RETRY_ON_GRPC` in `retryguard.py` and `run_scenario.py`). Every method on them is a read, so a repeat only costs load. `cartservice` and `shippingservice` stay on the plain `RETRY_ON` because one route rule cannot split a read from a write.
- A gRPC `UNAVAILABLE` (status 14) or `DEADLINE_EXCEEDED` (status 4) reaches Envoy as HTTP 200 with a `grpc-status` trailer. Envoy's inbound `5xx` and `resets` counters do not see it, yet the retry policy retries on it.
- `envoy_retry_collector.py` writes `grpc_4` and `grpc_14` (and `grpc_2`, `grpc_13`) as `istio_requests_total` rows with `response_code=200` and one `grpc_response_status` each. The controller and the scorer both add `grpc_4` and `grpc_14` on the four read callees.

## How to read a guide

- Item 5 of [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) is the controller's number. The HTTP-only tables next to it are `5xx + resets` only.
- A guide dated before 2026-10-13 shows the HTTP-only number in the main table. Use its `-rescored.md` copy when comparing with a new hold.
- Edge rpr (shed and climb) is a separate signal from `service_edges.csv`.

## What was chosen

The scorer was changed to match the controller (option 2), and it still prints the HTTP-only tables (option 3). Document-only was not enough: item 5 and the log would have kept disagreeing on the four read callees.

## Related

- [ANALYSIS-TEMPLATE.md](ANALYSIS-TEMPLATE.md) items 5, 7, 8
- [RETRYGUARD-IMPLEMENTATION.md](RETRYGUARD-IMPLEMENTATION.md)
- [METRICS-GATHERED.md](METRICS-GATHERED.md) (`service_inbound.csv` columns)
