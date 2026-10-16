# graphs_tool — what the page shows

One hold, one HTML page, on the hold clock. Use it for every analysis of a single run: zoom, hover, and turn lines on or off. It is not a report figure. The committed `timeline.png` from `run_timeline.py` stays the static record, and it stays totals only.

Checked against `s2_burst20_rgtf1` on 2026-10-14. Build record: [2026-10-13-interactive-run-explorer-design.md](../docs/superpowers/specs/2026-10-13-interactive-run-explorer-design.md). Per-API Locust lines added 2026-10-15: [2026-10-15-per-api-locust-graphs.md](../docs/superpowers/plans/2026-10-15-per-api-locust-graphs.md).

## What it is and how to run it

```powershell
pip install -r experiments/requirements.txt   # once; needs plotly
python experiments/graphs_tool.py "<run_dir>"
python experiments/graphs_tool.py "<run_dir>" --all
```

The page is `experiments/explore_out/<run folder name>.html`. It is git-ignored, self-contained, and works offline.

The run folder is one hold under `experiments/results/final results/` (S1–S4). `campaign_48/`, `august_38/`, S5, and S6 are out of scope.

`--all` draws every service and every RetryGuard edge on the stacked panels. Without it, a mesh, retry, or overload line that never leaves zero stays in the legend only, so a quiet edge does not flatten the axis. Per-API Locust lines are outside that rule: an API file that exists is drawn on the stacked page even when every value is 0.

## Page layout

Top to bottom:

1. **Comparison chart.** One plot. Every line starts hidden. Turn on any mix of series; each unit keeps its own y-axis.
2. **Code key.** Edge codes E1–E14 (sheds) and service codes V1–V9 (re-enables).
3. **Stacked panels.** Nine panels, one shared hold-clock x-axis. The bottom panel has the range slider. Hover is unified: one x position shows every visible line.

Event names sit above each plot, not inside it. A section title in the legend turns the whole group on or off. One item turns only that line. An axis title that uses the same word as a section (the Rejection panel) does not toggle the group.

## Hold clock

t = 0 is the first Locust row of the hold, not the first mesh poll and not wall-clock midnight. Every panel uses that same zero, so a shed line on the retry panel is the same instant as the line on goodput.

How the fit works, and why a Locust row is not "second i": [2026-10-13-hold-clock-design.md](../docs/superpowers/specs/2026-10-13-hold-clock-design.md).

## Panels

| # | Panel | What a point is | Source | Unit | Shown by default |
|---|---|---|---|---|---|
| 1 | Goodput / RPS | Locust goodput and offered RPS. Totals, then each entry API. | `total.csv` and `{api}.csv` columns `Goodput`, `RPS` | req/s | totals and each API whose file is present |
| 2 | P95 | Shopper-visible latency. The total, then each entry API. | `total.csv` and `{api}.csv` column `Latency95` | ms | the total line and each API whose file is present |
| 3 | Rejection | Solid: controller rejection per service. Dashed black: Locust SLO-miss | `service_inbound.csv`; SLO-miss is `Fail/RPS` from `total.csv` | fraction | services with any rejection above 0 |
| 4 | Retries per request | `Δretry / (Δtotal − Δretry)` on one caller→callee edge | `service_edges.csv` | retries/request | RetryGuard edges with any retry increase |
| 5 | Cumulative retries | Running sum of positive `retry` increases since the first mesh poll | `service_edges.csv` `retry` | retries | same edges as panel 4 |
| 6 | TopFull cap | Live admission cap per entry API | `topfull_throttle.csv` `threshold` | req/s | APIs that had a real cap |
| 7 | Overload ticks | Running count of detector polls with `overloaded=1` | `topfull_detect.csv` | ticks | services with at least one such poll |
| 8 | Attempts | Heatmap. Row = edge, colour = attempts 0–3 | `retryguard.log` `OBSERVE` | attempts | every controlled edge, when RetryGuard ran |
| 9 | CPU | App-container CPU | `resource_usage.csv` | millicores | every Boutique service except `__master_node__` |

**Per-API Locust lines.** The five entry APIs are `getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`. Legend names are `getproduct Goodput`, `getproduct RPS`, and `getproduct P95`, and the same shape for the other four. The total lines stay `Goodput`, `RPS`, and `Latency95`. `Latency95` is the unweighted mean of the five API P95s. `getproduct P95` is that API's own percentile. One colour belongs to one API on both pages, and that API's RPS line is dashed. Goodput and P95 for that API are solid. An API whose CSV is missing has no line. `Latency99` is not drawn. On the stacked page these lines start on. On the comparison chart and on the multi page they start off, and the section title turns them on with the totals.

A line going up means more of that quantity at that second. On panels 5 and 7 the line is a step: it stays flat until the next poll, then jumps by what that poll added. It does not fall. On the other line panels a rise is a rate or a reading, and it can fall.

**Cumulative retries** count increases during this hold. The Envoy counter is a lifetime total, and a previous run can leave a large number in the first row. Those leftovers are not drawn. A poll where the counter goes backwards is dropped and does not add. The fourteen lines are RetryGuard's controlled edges, named `E3 frontend->checkoutservice` and so on.

**Overload ticks** count detector rows, not seconds. The detector writes about once a second. A carried flag (the last 0/1 held for up to 6 s when a poll is missing) is not an extra tick. The services are the eleven the detector scrapes, including `redis-cart`. On `s2_burst20_rgtf1`, checkout and email are the lines that climb; the others stay at zero and are hidden until `--all`.

**Rejection** uses the controller formula: `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on adservice, currencyservice, productcatalogservice, and recommendationservice. The dashed line is shopper-visible failure, `Fail/RPS` of the Locust total. They are different. S2 can show SLO-miss near 1 while mesh 5xx is 0. See [2026-10-13-controller-vs-scorer-rejection.md](2026-10-13-controller-vs-scorer-rejection.md).

**TopFull cap.** A reading of 9900 or more means no cap and is not drawn (10000 is the passthrough, and the RL can step a little below it, for example 9997.5). A fresh 0 is an empty read, not a cap of zero. The last usable cap is held for at most 6 s as a solid line. If the collector then goes more than 10 s without a fresh threshold read (the same rule `analysis_score.py` uses to flag a TopFull-on hold in `Throttle data quality`; a TopFull-off hold is `N/A: TopFull off` and is not flagged), the cap panel shows the stretch as a **grey band labelled "no fresh cap read"**, and the cap the collector kept repeating is drawn as a **dashed line** named `<api> (stale)` in the same colour as that API's solid line. The dashed value is a carried number, not a measurement. Rows are not dropped; the band and the dashes are the only difference. A hold that is flagged only because admitted-rate reads went stale (threshold reads stayed fresh) shows no band, because the cap line itself is measured. A clean hold shows neither. Goodput, P95, rejection, retries, and overload ticks do not use that file.

**Attempts.** Colour runs from red (0, retries off) through orange and yellow to green (3, full). A run with RetryGuard off says "RetryGuard off in this run" instead of the heatmap.

**CPU.** The legend name includes the limit in millicores, for example `frontend (1150)`, from the run manifest when it sets one and otherwise from the paper table. `__master_node__` is the master VM and is left out so it does not squash the service lines.

A panel with nothing to draw says "none in this run".

## Comparison chart

Same series as the line panels, overlaid. Nothing is on until you turn it on.

| Unit | Axis | Series |
|---|---|---|
| req/s | left, always there | Goodput, RPS, each API Goodput, each API RPS, TopFull cap, TopFull cap (stale) |
| ms | right, while a P95 line is on | Latency95, each API P95 |
| fraction | right | Rejection, Locust SLO-miss |
| retries/request | right | Retries per request |
| millicores | right | CPU |
| retries | right | Cumulative retries |
| ticks | right | Overload ticks |

A right-hand axis is hidden until one of its lines is on, then it packs against the plot. Cumulative retries and overload ticks do not share an axis: a retry total is often thousands, and an overload count is at most about one per second of the hold. Turning on one group does not move the other onto that scale.

RetryGuard event lines use a hidden 0–1 axis, so a shed stays full height no matter which units are on.

## Event lines and codes

Vertical lines mark RetryGuard switches, on every panel and on the comparison chart.

| Log line | Colour | Name on the line | Hover |
|---|---|---|---|
| `ON→OFF`, `metric=rpr_burst` | red | `E5 burst` | edge, step, rpr, `from_attempts` |
| `ON→OFF`, `metric=rpr` | red | `E5 normal` | edge, step, rpr, `from_attempts` |
| `OFF→ON` | green | `V3` | service, step, rejection, `consecutive_low` |
| `1→2`, `2→3` | orange | `E5 1→2` on the comparison chart | edge, step |

Hover fields appear only when that log line has them. The legend entries `ON→OFF`, `OFF→ON`, `1→2`, and `2→3` show or hide that step everywhere. Climbs are drawn on the stacked panels as well; only the comparison chart prints the `E5 1→2` name on the line.

On an S2 run only, a dashed black line on the goodput panel marks **escape**: the first time recommendationservice arrivals stay above 560 req/s for 5 seconds. It is absent when the run never escapes. It is not on the other panels.

Edge codes follow RetryGuard's controlled-edge order. Service codes follow the order those callees first appear. `V`, not `S`, because S1–S6 already mean scenarios.

| Code | Edge | Code | Edge |
|---|---|---|---|
| E1 | frontend→adservice | E8 | checkoutservice→cartservice |
| E2 | frontend→cartservice | E9 | checkoutservice→currencyservice |
| E3 | frontend→checkoutservice | E10 | checkoutservice→emailservice |
| E4 | frontend→currencyservice | E11 | checkoutservice→paymentservice |
| E5 | frontend→productcatalogservice | E12 | checkoutservice→productcatalogservice |
| E6 | frontend→recommendationservice | E13 | checkoutservice→shippingservice |
| E7 | frontend→shippingservice | E14 | recommendationservice→productcatalogservice |

| Code | Service | Code | Service |
|---|---|---|---|
| V1 | adservice | V6 | recommendationservice |
| V2 | cartservice | V7 | shippingservice |
| V3 | checkoutservice | V8 | emailservice |
| V4 | currencyservice | V9 | paymentservice |
| V5 | productcatalogservice | | |

## Reading it honestly

- An empty second is "no sample", not zero. A rate line breaks when the gap is longer than 3 s, so a 2 s mesh poll stays connected and a multi-second hole does not. Cumulative retries and overload ticks are steps and stay joined across the mesh poll (2 s on `s2_burst20_rgtf1`, 5 s when the collector is on its default).
- Caps are carried at most 6 s. CPU is carried at most 5 s. A carried point is the previous reading, not a new measurement.
- Do not treat a cap line as measured on a hold that `analysis_score.py` flags for throttle data quality.
- P99 is not on the page. `Latency99` in the Locust files is empty; P95 is the latency number.
- `campaign_48/` and `august_38/` are a different collector generation. Do not point graphs_tool at them and read the page as if it were a `final results/` hold.

## Which panel answers which question

| Question | Look at |
|---|---|
| Did the shop keep completing work, and at what latency? | Goodput / RPS, P95 |
| Which entry API completed work, and at what latency? | That API's Goodput, RPS, and P95 on the first two panels |
| Did shoppers see failures the mesh did not? | Rejection: dashed SLO-miss against the solid service lines |
| Did retries pile up before a shed? | Cumulative retries, with the red `E<n> burst` or `E<n> normal` line |
| Was the shed a rate spike or a slow climb? | Retries per request at the same line |
| Which edges were actually turned down, and when did they come back? | Attempts strip, plus the red and green event lines |
| Where did TopFull place a cap? | TopFull cap |
| Which services did the detector call overloaded, and for how many polls? | Overload ticks. The slope is how often the flag was on, not a CPU value |
| Who was near their CPU limit? | CPU, names in parentheses are the limit |

## multi_graphs_tool: several holds, one legend

```powershell
python experiments/multi_graphs_tool.py "<run_dir>" "<run_dir>" ["<run_dir>" ...]
```

Two or more holds from `experiments/results/final results/` (S1–S4). The page is `experiments/explore_out/multi_<run names>.html` (git-ignored, offline). Built from [2026-10-14-multi-graphs-tool-design.md](../docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md).

Top to bottom: one comparison panel per run (the run label sits above it), then one legend, then the E/V code key. The legend is the only control. A click on a legend item or a section title changes every panel, so all panels always show the same metrics. Everything starts off except the RetryGuard event lines.

The Goodput / RPS and P95 sections list each entry API as well as the totals: `getproduct Goodput`, `getproduct RPS`, `getproduct P95`, and the same three names for `postcheckout`, `getcart`, `postcart`, and `emptycart`. One colour belongs to one API in every panel. That API's RPS line is dashed. A run whose `{api}.csv` is missing has no trace of that name; turning the name on shows "none in this run" on that panel.

- **x** is linked. Zoom, pan, or the range slider (under the last panel) on one panel moves all of them. t = 0 is each run's own hold clock, and every panel shows the longest run's span, so a shorter run has empty space on the right.
- **y** is shared per unit. The range is 0 to 1.05 times the largest visible value in any panel, so equal heights mean equal values across runs. Turning on a line that peaks high in one run rescales all panels. A manual y range on one panel is copied to the others.
- **Names are the same in every panel.** CPU lines carry the service name only; the limit is in the hover (`… of 1150m`). The same series has the same colour in every panel.
- **"none in this run"** above a panel means a line you turned on does not exist in that run (for example RetryGuard edges on a `tf_only` run). It is not a zero.
- Each panel draws its own run's RetryGuard events and names. Hover over a name for the detail. A run with no `retryguard.log`, such as a `tf_only` hold, has no event lines. That is by design, not a drawing fault, and "none in this run" does not list events.
- **The plot edge is fixed.** Every panel's plot ends at the same x. A right-hand unit axis (ms, fraction, retries/request, millicores, retries, ticks) takes the next free lane to the right of it when its first line is turned on, so adding a metric does not shift the plot left.
- **The selector does not scroll, and it has no scrollbar of its own.** Plotly's legend slides its rows on a mouse wheel and, once the rows pass half the figure, draws a scrollbar. The page blocks the wheel and gives the selector the full height of its rows, so that bar is never created. Scrolling over the selector scrolls the page, and the group titles stay in place.

Not in this page: the nine stacked panels, `--all`, S5/S6/`campaign_48/`/`august_38/`.

**Stale caps in the comparison panels.** A flagged run's panel carries the same grey band and the same dashed `<api> (stale)` line. The shared legend lists `<api> (stale)` as its own entry under the cap group, drawn dashed, in the colour of `<api>`. It starts hidden like every other line. A run with no stale stretch has no such series, so turning the entry on shows the usual "none in this run" note for that run. Use it to see at a glance which of the compared holds have measured caps and which have carried ones.
