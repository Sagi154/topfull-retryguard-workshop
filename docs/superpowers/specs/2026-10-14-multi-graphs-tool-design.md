# multi_graphs_tool: design

Date: 2026-10-14. Status: agreed in a brainstorming session, built. Builds on [2026-10-13-interactive-run-explorer-design.md](2026-10-13-interactive-run-explorer-design.md) (graphs_tool, implemented in `experiments/graphs_tool.py`). What graphs_tool shows: [GRAPHS-TOOL.md](../../../Guides%20and%20Info/GRAPHS-TOOL.md).

## Purpose

Inspect several holds side by side on the hold clock. One run per comparison panel, one shared Plotly legend, so every panel shows the same metrics. A personal exploration tool like graphs_tool, not a report figure.

## Scope

- Runs under `experiments/results/final results/` (S1–S4) only. `campaign_48/`, `august_38/`, S5, and S6 are out.
- Any N >= 2 runs. Panels are generated per run.
- Out of v1: the nine stacked panels, `--all`, any change to `pull_results.py`, a cursor synced across panels.

## Shape

- New file `experiments/multi_graphs_tool.py`:
  `python experiments/multi_graphs_tool.py "<runA>" "<runB>" ["<runC>" ...]`
- Output: `experiments/explore_out/multi_<nameA>__<nameB>[__<nameC>...].html`. Git-ignored, self-contained, works offline (same as graphs_tool).
- It imports series building from `graphs_tool` (`line_specs`, `series_of`, `plot_points`, `event_series`, `markers`, `UNIT`, `ylabel`, and related helpers) and never reads CSVs itself. Alignment, carry limits, and the rejection formula stay identical to the single-run tool.
- `graphs_tool.py` is not modified. Its legend stays above its own comparison chart. `multi_graphs_tool.py` calls `graphs_tool.compare_figure` for each run and post-processes the figure, and carries its own page script. This replaces the earlier idea of extracting `graphs_tool`'s legend JS: extraction risked changing single-run pages for no gain.

## Page layout

Top to bottom:

1. **N comparison panels, stacked vertically**, full width. Each has a header with the run name, scenario, and variant. No legend on a panel.
2. **One Plotly legend**, the same comparison-chart legend graphs_tool uses, sitting under the last panel. It is the only control for what the panels draw.
3. **Code key** (E1–E14, V1–V9), same as graphs_tool, under the legend.

## Shared legend

The legend is a Plotly legend, not a custom checkbox bar. It keeps the comparison chart's behaviour: section titles, item clicks, titles that stay black, and every line starting off (`legendonly`).

- Sections are Goodput/RPS, P95, Rejection, Retries per request, Cumulative retries, TopFull cap, Overload ticks, CPU, and RetryGuard events. The item list is the union of series across the runs.
- A section title toggles the whole group. An item toggles one line.
- The legend is its own figure after the panels, with the plot area collapsed so only the legend shows. Each panel is a figure with `showlegend` false. A click on the legend runs `Plotly.restyle` on every panel, keyed by trace name, and updates the legend's own visibility to match.
- A run that lacks a series (for example RetryGuard edges on a `tf_only` run) draws nothing for it. The legend item stays on, and that panel shows "none in this run".
- **Trace names must be identical across runs**, or one toggle will not hit the same line everywhere. The CPU legend name in graphs_tool includes the limit, for example `frontend (1150)`. In this tool the CPU trace uses the plain service name, and the limit moves into hover. This matters on S3, S4A, and S4B, where a constrained service has a different limit than in other runs.
- Right-hand axes (ms, fraction, retries/req, millicores, retries, ticks) show or hide with the same rule as graphs_tool. The rule is applied to all panels together so their layouts stay aligned.

## Linking

- **x:** linked across all panels (zoom, pan, range slider on the last panel). t = 0 is each run's own hold clock. The range is pinned to the longest run, so a shorter run shows empty space and the same second lines up vertically.
- **y:** one shared range per unit across all panels, so heights are directly comparable. It is the max over currently visible traces in all runs, recomputed on every toggle. A manual y-zoom on one panel sets the same range on every panel. Consequence: turning on a line that peaks high in one run rescales all panels.

## Events and hover

- Each panel draws its own run's RetryGuard events (red sheds, green re-enables, orange climbs) and its own name annotations. The legend's "RetryGuard events" section toggles them.
- Hover is `x unified` per panel. A cursor synced across panels is not in v1.

## Testing

Same pattern as `experiments/test_graphs_tool.py`, in a new `experiments/test_multi_graphs_tool.py`:

Browser tests use synthetic figures patched in for `graphs_tool.compare_figure`, so they do not depend on run data; one test uses real synthetic runs from `test_hold_clock.make_run`.

- Trace-name parity across runs, including the CPU plain-name rule.
- Shared-y range computation (max over visible traces per unit, across runs).
- Missing-series fallback ("none in this run", no error).
- HTML smoke: N panel divs, one legend figure under them, and the code key after the legend.

First real check: three holds of one scenario, for example S2 burst `both`, `rg_only`, and `tf_only`. Also one pair with different run lengths, to confirm the x pin.

## Open points for the implementation plan

- Resolved in the plan: a `busy` flag is set while the page relayouts panels, so a panel ignores the relayout events its own update causes. A y-only autorange restores the pinned x range, and busy is cleared in finally.
- Resolved in the plan: a click on the legend-only figure rebuilds every panel's `visible` array from the legend's state by `(legendgroup, name)`, then relayouts axes, event names, and y ranges in one call per panel.
