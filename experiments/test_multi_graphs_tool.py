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
        self.assertEqual(list(fig.layout.xaxis.domain), [0, multi_graphs_tool.PLOT_DOMAIN_END])

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

    def test_slider_keeps_the_reserved_plot_edge(self):
        figs = self.figs()
        for fig in figs:
            fig.update_layout(xaxis_domain=[0, multi_graphs_tool.PLOT_DOMAIN_END])
        multi_graphs_tool.decorate_slider(figs)
        for fig in figs:
            self.assertEqual(list(fig.layout.xaxis.domain), [0, multi_graphs_tool.PLOT_DOMAIN_END])

    def test_per_api_names_do_not_take_a_palette_slot(self):
        figs = [synthetic([
            ("locust", "Goodput", [1.0]),
            ("locust", "RPS", [1.0]),
            ("locust", "getproduct Goodput", [1.0]),
            ("locust", "getproduct RPS", [1.0]),
            ("p95", "Latency95", [5.0]),
            ("p95", "getproduct P95", [5.0]),
            ("rejection", "checkoutservice", [0.1]),
        ], 10)]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("locust", "Goodput")], multi_graphs_tool.PALETTE[0])
        self.assertEqual(colors[("locust", "RPS")], multi_graphs_tool.PALETTE[1])
        self.assertEqual(colors[("p95", "Latency95")], multi_graphs_tool.PALETTE[2])
        self.assertEqual(colors[("rejection", "checkoutservice")], multi_graphs_tool.PALETTE[3])
        api = graphs_tool.API_LINE_COLOR["getproduct"]
        self.assertEqual(colors[("locust", "getproduct Goodput")], api)
        self.assertEqual(colors[("locust", "getproduct RPS")], api)
        self.assertEqual(colors[("p95", "getproduct P95")], api)


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
        self.assertIs(legend.layout.dragmode, False)
        self.assertEqual(legend.layout.plot_bgcolor, "rgba(0,0,0,0)")
        self.assertEqual(legend.layout.paper_bgcolor, "rgba(0,0,0,0)")


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

    def test_out_path_bumps_until_the_segment_is_unused(self):
        path = multi_graphs_tool.out_path([Path("x/run"), Path("y/run"), Path("z/run-2")])
        segments = path.stem.removeprefix("multi_").split("__")
        self.assertEqual(segments, ["run", "run-2", "run-2-3"])
        self.assertEqual(len(segments), len(set(segments)))

    def test_cli_needs_two_existing_runs(self):
        with self.assertRaises(SystemExit) as one:
            multi_graphs_tool.main(["only_one"])
        self.assertEqual(one.exception.code, 2)
        with self.assertRaises(SystemExit) as missing:
            multi_graphs_tool.main(["does_not_exist_a", "does_not_exist_b"])
        self.assertEqual(missing.exception.code, 2)


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def two_synthetic_panels():
    """A: 300 s, Goodput peaks at 30, a rejection line. B: 600 s, Goodput peaks at 90,
    a retries-per-request line A lacks, and an ON→OFF event with a name on the line."""
    fig_a = synthetic([("locust", "Goodput", [10.0, 20.0, 30.0]),
                       ("rejection", "checkoutservice", [0.0, 0.5, 0.2])], 300)
    fig_b = synthetic([("locust", "Goodput", [30.0, 60.0, 90.0]),
                       ("rpr", "E3 frontend->checkoutservice", [0.0, 1.0, 2.0])],
                      600, events=("ON→OFF",))
    return fig_a, fig_b


class BrowserCase(unittest.TestCase):
    """Loads the page in Chromium and clicks the legend the way a person does."""

    def setUp(self):
        if sync_playwright is None:
            self.skipTest("playwright is not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        out = Path(self.tmp.name) / "multi.html"
        fig_a, fig_b = two_synthetic_panels()
        with mock.patch.object(graphs_tool, "compare_figure", side_effect=[fig_a, fig_b]):
            multi_graphs_tool.write_page(
                [Path("final/S2/both/run_a"), Path("final/S2/rg_only/run_b")], out)
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        browser = self.playwright.chromium.launch()
        self.addCleanup(browser.close)
        self.page = browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.goto(out.as_uri())
        self.page.wait_for_selector("#legend-graph .legend .traces")
        self.page.wait_for_function(
            "() => ['panel-0','panel-1','legend-graph'].every("
            "id => document.getElementById(id) && document.getElementById(id).data)"
        )

    def click_legend(self, label: str, title: bool) -> None:
        point = self.page.evaluate(
            """(args) => {
              const graph = document.getElementById('legend-graph');
              const row = [...graph.querySelectorAll('.legend .traces')].find(item => {
                const text = item.querySelector('text');
                if (!text || text.textContent !== args.label) return false;
                const isTitle = !item.querySelector('.legendtoggle');
                return args.title ? isTitle : !isTitle;
              });
              if (!row) return null;
              const text = row.querySelector('text');
              text.scrollIntoView({block: 'center', inline: 'center'});
              const box = text.getBoundingClientRect();
              return {x: box.x + box.width / 2, y: box.y + box.height / 2};
            }""",
            {"label": label, "title": title},
        )
        self.assertIsNotNone(point, f"missing legend text {label}")
        self.page.mouse.click(point["x"], point["y"])

    def visible(self, panel: int, name: str) -> bool:
        return self.page.evaluate(
            """(args) => document.getElementById('panel-' + args.panel).data
              .filter(t => t.name === args.name)
              .every(t => t.visible !== 'legendonly')""",
            {"panel": panel, "name": name},
        )

    def wait(self, expression: str, arg=None, timeout: int = 4000) -> None:
        self.page.wait_for_function(expression, arg=arg, timeout=timeout)

    def y_range(self, panel: int, axis: str = "yaxis"):
        return self.page.evaluate(
            "(args) => document.getElementById('panel-' + args.panel).layout[args.axis].range",
            {"panel": panel, "axis": axis},
        )


class TestLegendDrivesPanels(BrowserCase):
    def test_item_click_shows_the_line_in_every_panel_with_one_shared_y_range(self):
        self.assertFalse(self.visible(0, "Goodput"))
        self.assertFalse(self.visible(1, "Goodput"))
        self.click_legend("Goodput", title=False)
        self.wait("() => document.getElementById('panel-1').data"
                  ".every(t => t.name !== 'Goodput' || t.visible === true)")
        self.assertTrue(self.visible(0, "Goodput"))
        self.assertTrue(self.visible(1, "Goodput"))
        # Max over both runs is 90; the range is [0, 90 * 1.05] on both panels.
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.assertEqual(self.y_range(0), self.y_range(1))
        self.assertAlmostEqual(self.y_range(1)[1], 94.5, places=2)
        self.assertEqual(self.y_range(1)[0], 0)

    def test_section_title_toggles_the_whole_group_in_every_panel(self):
        self.click_legend("Goodput / RPS (req/s)", title=True)
        self.wait("() => document.getElementById('panel-0').data"
                  ".filter(t => t.legendgroup === 'locust').every(t => t.visible === true)")
        self.assertTrue(self.visible(1, "Goodput"))
        self.click_legend("Goodput / RPS (req/s)", title=True)
        self.wait("() => document.getElementById('panel-0').data"
                  ".filter(t => t.legendgroup === 'locust').every(t => t.visible === 'legendonly')")
        self.assertFalse(self.visible(1, "Goodput"))

    def test_right_axis_shows_on_every_panel_when_a_line_of_that_unit_is_on(self):
        self.assertFalse(self.page.evaluate(
            "() => document.getElementById('panel-0').layout.yaxis3.visible"))
        self.click_legend("checkoutservice", title=False)
        self.wait("() => document.getElementById('panel-1').layout.yaxis3.visible === true")
        self.assertTrue(self.page.evaluate(
            "() => document.getElementById('panel-0').layout.yaxis3.visible"))
        self.assertEqual(self.y_range(0, "yaxis3"), self.y_range(1, "yaxis3"))
        self.assertAlmostEqual(self.y_range(1, "yaxis3")[1], 0.525, places=3)

    def test_note_names_a_visible_series_the_run_lacks(self):
        self.assertEqual(self.page.inner_text("#note-0"), "")
        self.click_legend("E3 frontend->checkoutservice", title=False)
        self.wait("() => document.getElementById('note-0').textContent.length > 0")
        self.assertIn("none in this run", self.page.inner_text("#note-0"))
        self.assertIn("Retries per request (1)", self.page.inner_text("#note-0"))
        self.assertEqual(self.page.inner_text("#note-1"), "")

    def test_event_item_hides_the_names_on_the_lines(self):
        self.assertTrue(self.page.evaluate(
            "() => document.getElementById('panel-1').layout.annotations[0].visible !== false"))
        self.click_legend("ON→OFF", title=False)
        self.wait("() => document.getElementById('panel-1').layout.annotations[0].visible === false")
        self.click_legend("ON→OFF", title=False)
        self.wait("() => document.getElementById('panel-1').layout.annotations[0].visible === true")

    def test_legend_figure_shrinks_to_its_legend(self):
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        height = self.page.evaluate("() => document.getElementById('legend-graph').offsetHeight")
        self.assertGreater(height, 40)

    def test_plot_stays_put_when_a_right_axis_turns_on(self):
        before = self.page.evaluate("""() => {
          const plot = document.querySelector('#panel-0 .nsewdrag').getBoundingClientRect();
          return {x: plot.x, w: plot.width,
                  domain: document.getElementById('panel-0').layout.xaxis.domain.slice()};
        }""")
        self.click_legend("checkoutservice", title=False)
        self.wait("() => document.getElementById('panel-1').layout.yaxis3.visible === true")
        after = self.page.evaluate("""() => {
          const plot = document.querySelector('#panel-0 .nsewdrag').getBoundingClientRect();
          return {x: plot.x, w: plot.width,
                  domain: document.getElementById('panel-0').layout.xaxis.domain.slice()};
        }""")
        self.assertEqual(after["domain"], before["domain"])
        self.assertEqual(after["domain"][1], multi_graphs_tool.PLOT_DOMAIN_END)
        self.assertAlmostEqual(after["x"], before["x"], delta=1)
        self.assertAlmostEqual(after["w"], before["w"], delta=1)
        self.page.evaluate(
            "() => document.getElementById('legend-graph').scrollIntoView({block: 'center'})")
        self.click_legend("E3 frontend->checkoutservice", title=False)
        self.wait("() => document.getElementById('panel-1').layout.yaxis4.visible === true")
        later = self.page.evaluate("""() => {
          const plot = document.querySelector('#panel-1 .nsewdrag').getBoundingClientRect();
          return {x: plot.x, w: plot.width};
        }""")
        second = self.page.evaluate("""() => {
          const plot = document.querySelector('#panel-0 .nsewdrag').getBoundingClientRect();
          return {x: plot.x, w: plot.width};
        }""")
        self.assertAlmostEqual(later["x"], second["x"], delta=1)
        self.assertAlmostEqual(later["w"], second["w"], delta=1)

    def test_legend_matches_its_rows_without_a_scrollbar(self):
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        state = self.page.evaluate("""() => {
          const legend = document.getElementById('legend-graph');
          const bg = legend.querySelector('.bg');
          const bar = legend.querySelector('.scrollbar');
          const box = legend.querySelector('.scrollbox');
          let bottom = 0;
          if (box) {
            [...box.children].forEach(el => {
              const b = el.getBBox();
              const m = /translate\\(\\s*[-0-9.eE]+(?:\\s*,\\s*|\\s+)([-0-9.eE]+)\\s*\\)/.exec(
                el.getAttribute('transform') || '');
              const y = m ? +m[1] : 0;
              bottom = Math.max(bottom, y + b.y + b.height);
            });
          }
          const fill = bg ? getComputedStyle(bg).fill : '';
          const barBox = bar ? bar.getBoundingClientRect() : null;
          const barShown = !!(bar && getComputedStyle(bar).display !== 'none' && barBox.height > 2);
          return {fig: legend.offsetHeight, bottom: bottom, fill: fill, barShown: barShown};
        }""")
        self.assertNotIn("229, 236, 246", state["fill"])
        self.assertFalse(state["barShown"])
        laid = self.page.evaluate("""() => {
          const legend = document.getElementById('legend-graph')._fullLayout.legend;
          const bar = document.querySelector('#legend-graph .scrollbar');
          return {height: legend._height, max: legend._maxHeight,
                  thumb: bar ? +bar.getAttribute('height') || 0 : 0};
        }""")
        self.assertLessEqual(laid["height"], laid["max"])
        self.assertEqual(laid["thumb"], 0)
        self.assertGreater(state["bottom"], 0)
        self.assertGreater(state["fig"], state["bottom"])
        self.assertLess(state["fig"], state["bottom"] + 80)

    def test_tall_selector_is_not_given_a_scrollbar(self):
        series = [("rejection", f"svc{i}", [0.1, 0.2]) for i in range(30)]
        fig_a = synthetic(series + [("locust", "Goodput", [1.0, 2.0])], 300)
        fig_b = synthetic(series[:3], 600, events=("ON→OFF",))
        out = Path(self.tmp.name) / "tall.html"
        with mock.patch.object(graphs_tool, "compare_figure", side_effect=[fig_a, fig_b]):
            multi_graphs_tool.write_page(
                [Path("final/S2/both/run_a"), Path("final/S2/rg_only/run_b")], out)
        self.page.goto(out.as_uri())
        self.page.wait_for_selector("#legend-graph .legend .traces")
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        laid = self.page.evaluate("""() => {
          const legend = document.getElementById('legend-graph')._fullLayout.legend;
          const bar = document.querySelector('#legend-graph .scrollbar');
          const box = bar ? bar.getBoundingClientRect() : {width: 0, height: 0};
          return {height: legend._height, max: legend._maxHeight,
                  thumb: Math.round(box.height)};
        }""")
        self.assertLessEqual(laid["height"], laid["max"])
        self.assertEqual(laid["thumb"], 0)

    def test_slider_stays_on_the_last_panel_and_a_click_hits_every_panel(self):
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        place = self.page.evaluate("""() => {
          const legend = document.getElementById('legend-graph');
          const slider = document.querySelector('.rangeslider-container');
          const modebar = legend.querySelector('.modebar');
          const sb = slider.getBoundingClientRect();
          const lb = legend.getBoundingClientRect();
          const shown = modebar && getComputedStyle(modebar).display !== 'none'
            && modebar.getBoundingClientRect().height > 2;
          return {
            parent: slider.closest('.plotly-graph-div').id,
            overlap: sb.bottom > lb.top + 2 && sb.top < lb.bottom,
            gap: lb.top - sb.bottom,
            modebar: !!shown,
          };
        }""")
        self.assertEqual(place["parent"], "panel-1")
        self.assertFalse(place["overlap"])
        self.assertGreater(place["gap"], 8)
        self.assertFalse(place["modebar"])
        self.click_legend("Goodput / RPS (req/s)", title=True)
        self.wait("() => document.getElementById('panel-1').data"
                  ".filter(t => t.legendgroup === 'locust').every(t => t.visible === true)")
        self.assertTrue(self.visible(0, "Goodput"))
        self.assertTrue(self.visible(1, "Goodput"))
        self.click_legend("Rejection", title=True)
        self.wait("() => document.getElementById('panel-0').data"
                  ".filter(t => t.name === 'checkoutservice').every(t => t.visible === true)")
        self.assertTrue(self.visible(0, "checkoutservice"))
        # The second click must not turn the first group back off on either panel.
        self.assertTrue(self.visible(0, "Goodput"))
        self.assertTrue(self.visible(1, "Goodput"))

    def test_wheel_over_the_selector_does_not_scroll_its_rows(self):
        self.page.set_viewport_size({"width": 280, "height": 900})
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        before = self.page.evaluate("""() => {
          const graph = document.getElementById('legend-graph');
          graph.scrollIntoView({block: 'center'});
          const box = graph.querySelector('.legend').getBoundingClientRect();
          return {x: box.x + 30, y: box.y + 20, rows: document.querySelector(
            '#legend-graph .scrollbox').getAttribute('transform') || ''};
        }""")
        # A reflow can leave the figure shorter than its rows for a moment. That is
        # when Plotly lets the wheel slide the rows.
        self.page.evaluate("""() => {
          const graph = document.getElementById('legend-graph');
          window.__fits = 99;
          return Plotly.relayout(graph, {height: 120});
        }""")
        self.page.wait_for_timeout(300)
        self.page.mouse.move(before["x"], before["y"])
        self.page.mouse.wheel(0, 300)
        self.page.wait_for_timeout(300)
        after = self.page.evaluate("""() => ({
          rows: document.querySelector('#legend-graph .scrollbox').getAttribute('transform') || '',
          scrollY: document.getElementById('legend-graph')._fullLayout.legend._scrollY || 0})""")
        self.assertEqual(after["scrollY"], 0)
        self.assertEqual(after["rows"], before["rows"])

    def test_wrapped_legend_row_receives_the_click(self):
        # 280px puts CPU or RetryGuard events on a second row. At 400px that row
        # used to fall outside Plotly's clip, so the click never reached it.
        fig_a = synthetic(
            [("locust", "Goodput", [10.0, 20.0, 30.0]),
             ("cpu", "catalogservice", [100.0, 200.0, 150.0])], 300)
        fig_b = synthetic(
            [("locust", "Goodput", [30.0, 60.0, 90.0]),
             ("cpu", "catalogservice", [80.0, 120.0, 90.0])],
            600, events=("ON→OFF",))
        out = Path(self.tmp.name) / "wrapped.html"
        with mock.patch.object(graphs_tool, "compare_figure", side_effect=[fig_a, fig_b]):
            multi_graphs_tool.write_page(
                [Path("final/S2/both/run_a"), Path("final/S2/rg_only/run_b")], out)
        self.page.set_viewport_size({"width": 280, "height": 1200})
        self.page.goto(out.as_uri())
        self.page.wait_for_selector("#legend-graph .legend .traces")
        self.page.wait_for_function(
            "() => ['panel-0','panel-1','legend-graph'].every("
            "id => document.getElementById(id) && document.getElementById(id).data)"
        )
        self.wait("() => document.getElementById('legend-graph').offsetHeight < 900")
        self.wait("""() => {
          const drag = document.querySelector('#legend-graph .nsewdrag');
          return !drag || getComputedStyle(drag).pointerEvents === 'none';
        }""")
        rows = self.page.evaluate("""() => {
          const graph = document.getElementById('legend-graph');
          graph.scrollIntoView({block: 'center'});
          const drag = graph.querySelector('.nsewdrag');
          const dragBox = drag ? drag.getBoundingClientRect() : null;
          return [...graph.querySelectorAll('.legend .traces')].map(row => {
            const text = row.querySelector('text');
            const box = text.getBoundingClientRect();
            const x = box.x + box.width / 2;
            const y = box.y + box.height / 2;
            const hit = document.elementFromPoint(x, y);
            const underDrag = !!(dragBox && x >= dragBox.left && x <= dragBox.right
              && y >= dragBox.top && y <= dragBox.bottom);
            return {
              label: text.textContent,
              top: Math.round(box.top),
              title: !row.querySelector('.legendtoggle'),
              underDrag: underDrag,
              hit: hit ? hit.tagName + '.' + (hit.getAttribute('class') || '') : null,
            };
          });
        }""")
        goodput = next(row for row in rows if row["label"] == "Goodput")
        later_labels = {"ON→OFF", "RetryGuard events", "CPU (millicores)", "catalogservice"}
        later = [row for row in rows
                 if row["underDrag"] and row["hit"] and "legend" in row["hit"]
                 and row["label"] in later_labels and row["top"] > goodput["top"] + 20]
        self.assertTrue(later, ascii(rows))
        target = min(later, key=lambda row: row["top"])
        self.click_legend(target["label"], title=target["title"])
        if target["label"] in ("ON→OFF", "RetryGuard events"):
            self.wait("() => document.getElementById('panel-1').layout.annotations[0].visible === false")
            self.assertFalse(self.visible(1, "ON→OFF"))
        else:
            self.wait("() => document.getElementById('panel-0').data"
                      ".filter(t => t.name === 'catalogservice').every(t => t.visible === true)")
            self.assertTrue(self.visible(1, "catalogservice"))


class TestLinkedZoom(BrowserCase):
    def x_range(self, panel: int):
        return self.page.evaluate(
            "(i) => document.getElementById('panel-' + i).layout.xaxis.range", panel)

    def test_panels_start_on_the_longest_runs_span(self):
        self.assertEqual(list(self.x_range(0)), [0, 600])
        self.assertEqual(list(self.x_range(1)), [0, 600])

    def test_x_zoom_on_one_panel_moves_the_others(self):
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-0'), {'xaxis.range': [10, 40]})")
        self.wait("() => { const r = document.getElementById('panel-1').layout.xaxis.range;"
                  " return r && r[0] === 10 && r[1] === 40; }")

    def test_y_zoom_on_one_panel_moves_the_others(self):
        self.click_legend("Goodput", title=False)
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-1'), {'yaxis.range': [0, 50]})")
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && r[0] === 0 && r[1] === 50; }")

    def test_autorange_reset_returns_every_panel_to_the_pinned_x_and_shared_y(self):
        self.click_legend("Goodput", title=False)
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-0'), {'xaxis.range': [10, 40]})")
        self.wait("() => document.getElementById('panel-1').layout.xaxis.range[0] === 10")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-1'),"
            " {'xaxis.autorange': true, 'yaxis.autorange': true})")
        self.wait("() => { const a = document.getElementById('panel-0').layout.xaxis.range;"
                  " const b = document.getElementById('panel-1').layout.xaxis.range;"
                  " return a[0] === 0 && a[1] === 600 && b[0] === 0 && b[1] === 600; }")
        self.wait("() => { const r = document.getElementById('panel-1').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")

    def test_yaxis_autorange_alone_restores_the_pinned_x_range(self):
        self.click_legend("Goodput", title=False)
        self.wait("() => { const r = document.getElementById('panel-0').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-0'), {'xaxis.range': [10, 40]})")
        self.wait("() => document.getElementById('panel-1').layout.xaxis.range[0] === 10")
        self.page.evaluate(
            "() => Plotly.relayout(document.getElementById('panel-1'), {'yaxis.autorange': true})")
        self.wait("() => { const a = document.getElementById('panel-0').layout.xaxis.range;"
                  " const b = document.getElementById('panel-1').layout.xaxis.range;"
                  " return a[0] === 0 && a[1] === 600 && b[0] === 0 && b[1] === 600; }")
        self.wait("() => { const r = document.getElementById('panel-1').layout.yaxis.range;"
                  " return r && Math.abs(r[1] - 94.5) < 0.01; }")


class TestStaleSeries(unittest.TestCase):
    def stale_figs(self):
        both = synthetic([("caps", "getproduct", [1.0]), ("caps", "getproduct (stale)", [2.0])], 100)
        both.data[1].line.dash = "dash"
        fresh_only = synthetic([("caps", "getproduct", [1.0])], 100)
        return [fresh_only, both]

    def test_stale_series_takes_the_colour_of_its_fresh_line(self):
        figs = self.stale_figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("caps", "getproduct (stale)")], colors[("caps", "getproduct")])
        stale = next(t for t in figs[1].data if t.name == "getproduct (stale)")
        self.assertEqual(stale.line.color, colors[("caps", "getproduct")])
        self.assertEqual(stale.line.dash, "dash")

    def test_colour_is_shared_even_when_the_stale_line_is_seen_first(self):
        stale_first = synthetic([("caps", "getproduct (stale)", [2.0])], 100)
        fresh_second = synthetic([("caps", "getproduct", [1.0])], 100)
        figs = [stale_first, fresh_second]
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        self.assertEqual(colors[("caps", "getproduct (stale)")], colors[("caps", "getproduct")])

    def test_legend_draws_the_stale_entry_dashed_and_the_rest_solid(self):
        figs = self.stale_figs()
        union = multi_graphs_tool.series_union(figs)
        colors = multi_graphs_tool.assign_colors(figs, union)
        legend = multi_graphs_tool.legend_figure(union, colors)
        by_name = {t.name: t for t in legend.data}
        self.assertEqual(by_name["getproduct (stale)"].line.dash, "dash")
        self.assertEqual(by_name["getproduct"].line.dash, "solid")
        self.assertEqual(by_name["getproduct (stale)"].visible, "legendonly")
        self.assertEqual(by_name["getproduct (stale)"].legendgroup, "caps")


if __name__ == "__main__":
    unittest.main()
