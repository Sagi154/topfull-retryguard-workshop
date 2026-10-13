# Interactive run explorer: design

Date: 2026-10-13. Status: agreed in a grilling session, not yet built. Builds on [2026-10-13-hold-clock-design.md](2026-10-13-hold-clock-design.md), which is implemented (`experiments/hold_clock.py`, `experiments/run_timeline.py`). Glossary terms: **Hold clock**, **Edge code**, **Service code**, **RetryGuard state strip** in [CONTEXT.md](../../../CONTEXT.md).

## Purpose

A personal tool for exploring one run at a time: zoom, hover, toggle lines. It is not a report figure and not part of the standard pull. The committed `timeline.png` stays the static record.

## Scope

- Only runs under `experiments/results/final results/` (S1–S4). `campaign_48/`, `august_38/`, S5 and S6 are out.
- One run per page. No multi-run overlay in v1.
- RetryGuard-off runs (`tf_only`, `both_off`): the strip and marker panels say "RetryGuard off in this run".

## Shape

- New file `experiments/explore_run.py`:
  `python experiments/explore_run.py <run_dir> [--all]`
- Output: `experiments/explore_out/<log_folder>.html`, git-ignored, self-contained (`include_plotlyjs=True`, about 3 MB, works offline).
- It imports `run_timeline` (`per_second_view`, `panel_columns`, `switch_events`, `escape_hold_s`) and never reads the CSVs itself. All clock alignment, per-second rules, carry limits and the rejection formula come from there.
- `plotly` is a new dependency: add it to `experiments/requirements.txt`.
- One change to existing code: `run_timeline.switch_events()` also returns the `metric` column (it already exists in the loaded rows). `metric=rpr_burst` marks a burst shed, `rpr` a normal shed.
- The mentor-chart loaders (`mentor_charts_data.py`) are not reused. They are tied to `campaign_48/`, use per-file elapsed time, read the legacy `envoy_retries_*.csv`, compute rejection as `Fail/RPS` only, and drop shed mode and attempts.

## Panels

Shared hold-clock x-axis, range slider on the bottom panel, unified hover.

| # | Panel | Contents |
|---|---|---|
| 1 | Goodput and RPS | Locust `total.csv` |
| 2 | P95 | Locust `total.csv` `Latency95` |
| 3 | Rejection | Solid: controller-formula rejection per service. Dashed: **Locust SLO-miss** (`Fail/RPS` of the total). Separate names, so the gap is visible. |
| 4 | Retries per request | Per edge (`rpr`) |
| 5 | TopFull cap | Per API, only where a cap is applied |
| 6 | RetryGuard state strip | Heatmap, rows E1–E14, colour = attempts 0–3, from the per-tick `OBSERVE` lines |
| 7 | CPU | Per service. `__master_node__` excluded, as in the static chart. |

A "series" is one line on a chart. Panels 3, 4 and 5 can hold many (11 services, 14 edges). Default is the static chart's rule: show only lines with any rejection or retry in the run. `--all` shows every line, and the legend toggles any line on or off.

## Markers

Vertical lines on all panels, at the exact switch time:

| Log line | Marker | Hover |
|---|---|---|
| `ON→OFF`, `metric=rpr_burst` | `E5 burst` | edge name, rpr, `from_attempts` |
| `ON→OFF`, `metric=rpr` | `E5 normal` | edge name, rpr, `from_attempts` |
| `OFF→ON` (logged against a service) | `V3` | service name, rejection, `consecutive_low` |

On S2 runs only, one extra dashed black line marks **escape time**: when the recommendationservice arrival rate first stays above 560 req/s for 5 consecutive 1 s ticks, which ends a "latch" (see `CONTEXT.md`). It is drawn on panel 1 only, converted to the hold clock, as in the static chart. It is absent when the run never escapes. A legend table on the page maps every code to its name.

### Codes

Edge codes follow `CONTROLLED_EDGES` order, fixed on every run:

| Code | Edge | Code | Edge |
|---|---|---|---|
| E1 | frontend→adservice | E8 | checkoutservice→cartservice |
| E2 | frontend→cartservice | E9 | checkoutservice→currencyservice |
| E3 | frontend→checkoutservice | E10 | checkoutservice→emailservice |
| E4 | frontend→currencyservice | E11 | checkoutservice→paymentservice |
| E5 | frontend→productcatalogservice | E12 | checkoutservice→productcatalogservice |
| E6 | frontend→recommendationservice | E13 | checkoutservice→shippingservice |
| E7 | frontend→shippingservice | E14 | recommendationservice→productcatalogservice |

Service codes follow the order callees first appear in that list: V1 adservice, V2 cartservice, V3 checkoutservice, V4 currencyservice, V5 productcatalogservice, V6 recommendationservice, V7 shippingservice, V8 emailservice, V9 paymentservice. `V`, not `S`, because `S1`–`S6` already mean scenarios.

A re-enable is a service event, not an edge event, so it gets one `V` marker. It is not copied onto the strip. The strip reads the real `attempts=` values, so the 0→1 step shows up by itself.

## Decisions

**Attempts climbs (`1→2`, `2→3`) are not vertical lines.** They are logged as per-edge switches (9 in the 31 current `final results/` logs, against 65 sheds and 57 re-enables) and are already visible on the state strip. They also appear as hover text. Reason: marker clutter on every panel, and the strip shows the same information per edge. To reverse this, add `"1→2"` and `"2→3"` to `VERTICAL_LINE_STEPS` in `explore_run.py` (the constant is `("ON→OFF", "OFF→ON")`). The colour for them already exists in `run_timeline.SWITCH_COLORS`. A future agent should not treat the missing lines as a bug.

**Rejection means two things on one panel.** The solid lines use the controller's formula `(Δ5xx + Δresets) / Δtotal` (plus the gRPC term on four services). The dashed line is the shopper-visible SLO miss. They differ, and S2 can show SLO-miss near 1 with mesh 5xx at 0. See [2026-10-13-controller-vs-scorer-rejection.md](../../../Guides%20and%20Info/2026-10-13-controller-vs-scorer-rejection.md).

**TopFull-side events are not markers.** The cap and the detector `overloaded` flag are continuous readings, not discrete switches. The cap has its own panel. The detector flag is not shown in v1.

## First checks on real runs

- `S2_sustained_overload_burst/both/s2_burst20_rgtf1`: 28 sheds and re-enables, mesh polls every 2 s (tests gap handling and `E3 burst`).
- A normal-mode run under `S2_sustained_overload_normal/both/`: confirms the `E<n> normal` label (`metric=rpr` sheds appear in the logs; pick a run that has at least one).

## Out of scope for v1

Multi-run overlay, S5/S6, `campaign_48/` and `august_38/`, the detector `overloaded` strip, any change to `pull_results.py` (the explorer is run by hand).
