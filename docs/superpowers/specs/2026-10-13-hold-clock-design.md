# Hold clock and run timeline: design

Date: 2026-10-13. Status: agreed. Plan: [2026-10-13-hold-clock-implementation.md](../plans/2026-10-13-hold-clock-implementation.md).

Here is the full design for confirmation.

**Clock**
- The **hold clock** is seconds since the first Locust row, in master's UTC. Collector rows from before load starts keep negative times. Both terms are now in `CONTEXT.md`.
- **Existing runs** (only `experiments/results/final results/`) each get their own Locust clock fit:
  - Two anchors: the first and last moment the rate is above 20% of its typical value, in both Locust `RPS` and the mesh frontend inbound rate.
  - The start and the row spacing follow from the two anchors, with rows spread evenly.
  - Correlation is the check, flagged below 0.8.
  - The fit applies to `total.csv` and all five API CSVs, since one loop writes them all.
- **New runs:** `metric_collector.py` on master adds a `timestamp` column, the last column, at millisecond precision, via the existing patcher. `run_manifest.json` also gets `locust_started_at`. The fit still runs as a cross-check, and the gap between its anchors and the real stamps is recorded.
- **Escape time** keeps its first-mesh-poll definition and is shown converted on charts.

**Data**
- Raw files are never replaced or merged into a stored copy.
- `experiments/hold_clock.py` loads any source with a `hold_s` column added to every row.
- The per-second view follows the Q5 table:
  - Locust: the row whose time falls in that second, averaged if two do.
  - Running totals: a rate over the gap between polls, assigned to the later poll's second.
  - Current readings: carried forward for up to 6 s for caps and 5 s for CPU.
  - RetryGuard switches: exact-time markers.
  - Each cell is flagged as measured or carried forward; empty means no sample, never 0.

**Outputs** (per run folder)
- `locust_clock.json` (committed): start, spacing, anchors, correlation, flag, or "stamped".
- `timeline.png` (committed): six stacked panels on one hold-clock axis, with lines at RetryGuard switches:
  1. goodput and `RPS`;
  2. P95;
  3. TopFull cap per API, only where a cap is applied;
  4. rejection, for services with any rejection;
  5. retries per request, for edges with any retry among RetryGuard's 14 edges;
  6. CPU, for every Boutique service. `__master_node__` stays in the per-second CSV and stays out of this panel.
  
  An `--all` flag shows everything in panels 4 and 5.
- `timeline_1s.csv`: generated on demand, not committed.
- `pull_results.py` runs the tool after each pull. A failure only prints a warning and never blocks the pull.

**Docs**
- The "few seconds" line in `METRICS-GATHERED.md`'s clock section gets corrected, with a link to the new tool.

## Decisions made after the grilling rounds

**Chart line joining (found while checking the plan's code on a real hold, `s2_burst20_rgtf1`).** The rejection and retries panels looked empty. The mesh collector polled every 2 s there, so every other second has no value, and the chart drew nothing for a point with gaps on both sides. The chart now joins points across gaps of up to 3 s and breaks the line on longer ones. The per-second CSV still leaves those seconds empty, so the Q5 rule "empty means no sample, never 0" is unchanged. The 3 s limit is `MAX_PLOT_GAP_S` in `run_timeline.py`.

**CPU panel leaves out `__master_node__` (same check, `s2_burst20_rgtf1`).** `resource_usage.csv` includes `__master_node__`, the master VM, at 3,500–7,200 millicores. Drawn on the same axis it squashed every Boutique service line (those sit between 0 and about 2,000 millicores). Panel 6 in `run_timeline.py` drops that series. The per-second CSV still has `resource.__master_node__.cpu_millicores`.

## The Q5 table (per-second view rules)

| Kind | Sources | Rule for second t |
|---|---|---|
| Locust per-second values | goodput, RPS, fail, P95 | The Locust row whose fitted time falls in t. Two rows in one second: keep both in the long view, and average in the per-second view. None: empty. |
| Running totals | mesh `total` / `5xx` / `retry`, request-time sums | Rate = change ÷ time between polls, assigned to the second the later poll lands in. A 2 s gap gives one rate covering both seconds and leaves the earlier second empty. Not split, not zero. |
| Current readings | TopFull cap, admitted RPS, CPU, memory, replicas, detector utilization | The latest reading, carried forward up to a limit: 6 s for caps (already documented) and 5 s for CPU. Cap value 10000 = no cap, and a 0 read is empty. |
| Events | RetryGuard switches (`ON→OFF`, `OFF→ON`, `1→2`, `2→3`) | Listed at their exact time and drawn as markers. Never resampled. `OBSERVE` lines are carried as per-edge readings, not events. |

Rejection uses the controller formula (see [2026-10-13-controller-vs-scorer-rejection.md](../../../Guides%20and%20Info/2026-10-13-controller-vs-scorer-rejection.md)). A run with no matching edges or services shows the panel with a "none in this run" note.
