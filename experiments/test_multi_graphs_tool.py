"""Unit and browser tests for experiments/multi_graphs_tool.py."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graphs_tool  # noqa: E402
import multi_graphs_tool  # noqa: E402

AXES = {
    "yaxis2": graphs_tool.right_axis("ms", None),
    "yaxis3": graphs_tool.right_axis("fraction", 0.82),
    "yaxis4": graphs_tool.right_axis("retries/req", 0.90),
    "yaxis5": graphs_tool.right_axis("millicores", 0.98),
    "yaxis7": graphs_tool.right_axis("retries", None),
    "yaxis8": graphs_tool.right_axis("ticks", None),
}


def synthetic(series, x_max, events=()):
    """A stand-in for graphs_tool.compare_figure: same axes, same trace conventions.

    series is a list of (legendgroup, name, y values).
    """
    fig = go.Figure()
    for group, name, y in series:
        unit = graphs_tool.UNIT[group]
        fig.add_trace(go.Scatter(
            x=list(range(len(y))), y=y, mode="lines", name=name, visible="legendonly",
            legendgroup=group, meta=unit, yaxis=graphs_tool.trace_yaxis(unit),
            legendgrouptitle={"text": graphs_tool.ylabel(group)}, line={"width": 1.4},
        ))
    for step in events:
        fig.add_trace(go.Scatter(
            x=[1, 1, None], y=[0, 1, None], mode="lines", name=step, visible=True,
            line={"width": 1.2, "color": "red"}, hoverinfo="skip",
            legendgroup=graphs_tool.EVENT_GROUP, meta="event",
            legendgrouptitle={"text": "RetryGuard events"}, yaxis="y6",
        ))
        fig.add_annotation(
            x=1, xref="x", y=1, yref="y domain", text="E3 burst", showarrow=False,
            name=step, hovertext="frontend->checkoutservice ON→OFF",
        )
    fig.update_layout(
        xaxis={"range": [0, x_max]},
        yaxis6={"overlaying": "y", "range": [0, 1], "showticklabels": False},
        **AXES,
    )
    return fig


class TestPanelFigure(unittest.TestCase):
    def test_panel_has_no_legend_and_cpu_name_loses_the_limit(self):
        source = synthetic([("cpu", "frontend (1150)", [1.0, 2.0]),
                            ("locust", "Goodput", [1.0, 2.0])], 10)
        with mock.patch.object(graphs_tool, "compare_figure", return_value=source):
            fig = multi_graphs_tool.panel_figure(Path("final/S2/both/run_a"))
        self.assertFalse(fig.layout.showlegend)
        self.assertTrue(all(trace.showlegend is False for trace in fig.data))
        cpu = next(trace for trace in fig.data if trace.legendgroup == "cpu")
        self.assertEqual(cpu.name, "frontend")
        self.assertIn("of 1150m", cpu.hovertemplate)
        self.assertIn("<extra>frontend</extra>", cpu.hovertemplate)
        goodput = next(trace for trace in fig.data if trace.name == "Goodput")
        self.assertIsNone(goodput.hovertemplate)
        self.assertEqual(fig.layout.height, multi_graphs_tool.PANEL_HEIGHT)

    def test_run_label_names_scenario_variant_and_run(self):
        label = multi_graphs_tool.run_label(Path("x/S2_sustained_overload_burst/both/s2_burst20_rgtf1"))
        self.assertEqual(label, "S2_sustained_overload_burst / both / s2_burst20_rgtf1")


class TestNormalize(unittest.TestCase):
    def figs(self):
        return [
            synthetic([("locust", "Goodput", [1.0]), ("rejection", "checkoutservice", [1.0])], 300),
            synthetic([("locust", "Goodput", [1.0]), ("rpr", "E3 frontend->checkoutservice", [1.0])],
                      600, events=("ON→OFF",)),
        ]

    def test_x_range_is_pinned_to_the_longest_run(self):
        figs = self.figs()
        pinned = multi_graphs_tool.pin_x_range(figs)
        self.assertEqual(pinned, [0, 600])
        for fig in figs:
            self.assertEqual(list(fig.layout.xaxis.range), [0, 600])

    def test_union_is_ordered_by_group_and_keyed_by_group_and_name(self):
        union = multi_graphs_tool.series_union(self.figs())
        self.assertEqual(list(union), [
            ("locust", "Goodput"),
            ("rejection", "checkoutservice"),
            ("rpr", "E3 frontend->checkoutservice"),
            ("events", "ON→OFF"),
        ])

    def test_same_series_gets_the_same_colour_in_every_panel(self):
        figs = self.figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        first = next(t for t in figs[0].data if t.name == "Goodput")
        second = next(t for t in figs[1].data if t.name == "Goodput")
        self.assertEqual(first.line.color, second.line.color)
        self.assertEqual(first.line.color, colors[("locust", "Goodput")])
        reject = next(t for t in figs[0].data if t.name == "checkoutservice")
        self.assertNotEqual(reject.line.color, first.line.color)
        event = next(t for t in figs[1].data if t.name == "ON→OFF")
        self.assertEqual(event.line.color, "red")

    def test_slider_only_on_the_last_panel(self):
        figs = self.figs()
        multi_graphs_tool.decorate_slider(figs)
        self.assertFalse(figs[0].layout.xaxis.rangeslider.visible)
        self.assertTrue(figs[1].layout.xaxis.rangeslider.visible)
        self.assertEqual(figs[1].layout.height, figs[0].layout.height + multi_graphs_tool.SLIDER_EXTRA)
        self.assertEqual(figs[0].layout.xaxis.title.text, "")
        self.assertEqual(figs[1].layout.xaxis.title.text, multi_graphs_tool.HOLD_CLOCK_TITLE)


class TestLegendFigure(unittest.TestCase):
    def test_legend_lists_the_union_off_except_events(self):
        figs = [
            synthetic([("locust", "Goodput", [1.0])], 300),
            synthetic([("rpr", "E3 frontend->checkoutservice", [1.0])], 600, events=("ON→OFF",)),
        ]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        legend = multi_graphs_tool.legend_figure(union, colors)
        self.assertEqual([t.name for t in legend.data],
                         ["Goodput", "E3 frontend->checkoutservice", "ON→OFF"])
        self.assertEqual([t.visible for t in legend.data], ["legendonly", "legendonly", True])
        self.assertEqual([t.meta for t in legend.data], ["req/s", "retries/request", "event"])
        self.assertEqual(legend.data[0].line.color, colors[("locust", "Goodput")])
        self.assertEqual(legend.data[0].legendgrouptitle.font.color, "black")
        self.assertEqual(legend.layout.legend.groupclick, "toggleitem")
        self.assertEqual(legend.layout.height, multi_graphs_tool.LEGEND_HEIGHT)
        self.assertFalse(legend.layout.xaxis.visible)


from test_hold_clock import E, iso, make_run  # noqa: E402


class TestPage(unittest.TestCase):
    def test_real_runs_give_panels_then_legend_then_code_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_a = make_run(Path(tmp) / "a")
            run_b = make_run(Path(tmp) / "b")
            (run_b / "retryguard.log").write_text(
                f"{iso(E + 31)}  frontend->checkoutservice  ON→OFF   rpr=2.10  "
                "consecutive_high=2  attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4\n",
                encoding="utf-8",
            )
            out = Path(tmp) / "multi.html"
            multi_graphs_tool.write_page([run_a, run_b], out)
            page = out.read_text(encoding="utf-8")
            single = Path(tmp) / "single.html"
            graphs_tool.write_html(graphs_tool.build_figure(run_a), single, run_a)
            single_size = len(single.read_text(encoding="utf-8"))
        panel0 = page.index('id="panel-0"')
        panel1 = page.index('id="panel-1"')
        legend = page.index('id="legend-graph"')
        key = page.index("Service codes, OFF→ON")
        self.assertLess(panel0, panel1)
        self.assertLess(panel1, legend)
        self.assertLess(legend, key)
        self.assertEqual(page.count("Plotly.newPlot("), 3)
        self.assertNotIn('id="panel-2"', page)
        self.assertIn("E3 burst", page)
        # One Plotly bundle, not one per figure.
        self.assertLess(len(page), 2 * single_size)

    def test_out_path_joins_names_and_disambiguates_repeats(self):
        path = multi_graphs_tool.out_path([Path("x/run_a"), Path("y/run_b"), Path("z/run_a")])
        self.assertEqual(path.parent, graphs_tool.OUT_DIR)
        self.assertEqual(path.name, "multi_run_a__run_b__run_a-3.html")

    def test_cli_needs_two_existing_runs(self):
        with self.assertRaises(SystemExit) as one:
            multi_graphs_tool.main(["only_one"])
        self.assertEqual(one.exception.code, 2)
        with self.assertRaises(SystemExit) as missing:
            multi_graphs_tool.main(["does_not_exist_a", "does_not_exist_b"])
        self.assertEqual(missing.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
