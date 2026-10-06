# RetryGuard: per-edge retries-per-request mode

Date: 2026-10-06. Status: design agreed, not implemented.

## Goal

Add a second RetryGuard mode that follows the paper's preferred metric (retry volume per request, RetryGuard.pdf §4.3.1 and Fig. 7) and acts per call edge. The current per-service rejection-rate mode stays as the default and as the fallback.

## Decisions

1. **Edge list is fixed.** The Boutique call graph does not change, so the controlled edges are a constant in `retryguard.py` (`CONTROLLED_EDGES`), not discovered from the CSV and not in the scenario YAMLs. 14 edges, from the Boutique source and checked against `service_edges.csv` of `baseline_no_topfull_sustained_overload_run100`:
   - frontend → adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice
   - checkoutservice → cartservice, currencyservice, emailservice, paymentservice, productcatalogservice, shippingservice
   - recommendationservice → productcatalogservice

   Excluded: edges to `redis-cart` (TCP, no VirtualService) and edges into `frontend`.
2. **Metric, per edge, per 1 s tick:** `rpr = Δretry / (Δtotal − Δretry)` from `service_edges.csv`. This is the paper's normalized retry rate (Λ − λ)/λ: `total` counts every attempt (Λ), `retry` counts the retried ones (Λ − λ), so first attempts λ = total − retry. Dividing by Δtotal instead would be a different metric and the 0.5 threshold would not apply. A tick with 0 first attempts is skipped and changes no counter. No minimum traffic floor.
3. **Threshold:** `retries_threshold = 0.5`. Derived from Fig. 7 (knee at ρ≈1.03–1.05) scaled for `attempts: 3`. The paper does not state a per-edge value; report it as our choice.
4. **Algorithm:** the existing `apply_algorithm1` and `ServiceState` counters, one instance per edge, with the YAML's `interval_samples` for both transitions (paper default 30; Scenario 5's 10/20/30/60 still apply to both the edge streak and the rejection fallback).
5. **Edge OFF:** `rpr` above 0.5 on 30 *consecutive* ticks (a streak, as in Algorithm 1; any tick at or below 0.5 resets the counter, no averaging) sets that edge OFF. The callee's VirtualService gets a match route `sourceLabels: {app: <caller>}` with `retries: {attempts: 0}` placed before the default route. Other callers keep the default policy. Verified on the live cluster 2026-10-06: the matched caller got no retry policy, the others kept 3 retries at 500 ms.
6. **Fallback (per service):** the callee's rejection counter (`Δ(5xx+resets)/Δtotal` from `service_inbound.csv`, threshold `rejection_threshold` 0.20, same 30 ticks) runs only while at least one of that callee's edges is OFF. Counters start at 0 when its first edge goes OFF. When rejection stays below 0.20 for 30 ticks, all that callee's OFF edges go back ON in one patch, and the edges restart with fresh counters. When no edge is OFF the callee's rejection logic is idle.
7. **Switch:** new param `retry_metric` with values `rejection` (code default, current behaviour) and `edge_rpr`. `retries_threshold` is read only in `edge_rpr` mode. Every YAML that starts RetryGuard (`retryguard.enabled: true`) sets `retry_metric: edge_rpr` and `retries_threshold: 0.5`. Baseline and calibration YAMLs stay `enabled: false` and are not changed. No new scenario files.
8. **Log format:** keep the existing transition line shape. For edges the name field is `caller->target` and the line ends with `metric=rpr`. Service-level lines get `metric=rejection`. `OBSERVE` lines follow the same convention. Check that `s2_both_off_canon.py`, `rho_estimate_report.py`, and `run_scenario.py` parsers still read the lines.

## Changes

- `experiments/retryguard.py`
  - `CONTROLLED_EDGES` constant.
  - Edges tailer (same append-only pattern as `InboundCsvTailer`) and `measure_edge_rpr`.
  - Per-edge state dict next to the per-service one.
  - `build_vs_patch_body` takes the set of OFF callers and builds the ordered route list (match routes first, default route last). Re-enabling all edges rebuilds the single default rule with full retries.
  - `run()` branches on `retry_metric`.
  - `retries_threshold` and `retry_metric` params. `REQUIRED_PARAMS` stays unchanged, so the default mode keeps working.
- `experiments/run_scenario.py`: pass the two params through to the params JSON.
- The 11 RetryGuard YAMLs (S1, S2, S2 without TopFull, S3, S4A, S4B, S5 ×4 intervals, S6) gain `retry_metric: edge_rpr` and `retries_threshold: 0.5`. `run_number` and `log_folder` stay as they are.
- Docs: `RETRYGUARD-IMPLEMENTATION.md` (new mode, labelled a workshop extension of the paper), `AGENTS.md` status bullet.

## Tests (`experiments/test_retryguard.py`)

- `rpr` computation, including 0 first attempts (skipped) and counter reset on a CSV restart.
- Edge ON→OFF after 30 high ticks, and no transition at 29.
- Rejection counter idle with all edges ON, starts when the first edge goes OFF, re-enables all of that callee's OFF edges together.
- Patch body: ordered match routes for one and for two OFF callers, default route last with the full retry policy, empty OFF set yields the plain default.
- `retry_metric: rejection` leaves behaviour identical to today.

## Not in scope

- Hybrid use of both metrics while ON (the paper's preference order applies: rpr if available, otherwise rejection).
- Discovering edges at runtime, a traffic floor, plotting of the new log lines.
- Running a campaign. The one live check is a single S2 hold after the unit tests pass: run 89 mix (275/90/100/90/5), Paper-C1 CPU table, RetryGuard on, TopFull off.

## Caveats to state in the report

- The 0.5 threshold, the per-edge scope, and the per-callee fallback are workshop choices on top of Algorithm 1. They do not contradict the paper but are not in it.
- `service_edges.csv` outbound latency histograms are absent in this mesh, so only counts (`total`, `retry`) are used.
