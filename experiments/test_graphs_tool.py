"""Unit tests for experiments/graphs_tool.py."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graphs_tool  # noqa: E402
import run_timeline  # noqa: E402

NAN = float("nan")


def events(rows):
    return pd.DataFrame(rows, columns=run_timeline.SWITCH_EVENT_COLUMNS)


class TestCodes(unittest.TestCase):
    def test_codes_follow_controlled_edges_order(self):
        codes = graphs_tool.EDGE_CODES
        self.assertEqual(len(codes), 14)
        self.assertEqual(codes["frontend->adservice"], "E1")
        self.assertEqual(codes["frontend->checkoutservice"], "E3")
        self.assertEqual(codes["frontend->productcatalogservice"], "E5")
        self.assertEqual(codes["recommendationservice->productcatalogservice"], "E14")
        services = graphs_tool.SERVICE_CODES
        self.assertEqual(len(services), 9)
        self.assertEqual(services["adservice"], "V1")
        self.assertEqual(services["checkoutservice"], "V3")
        self.assertEqual(services["emailservice"], "V8")
        self.assertEqual(services["paymentservice"], "V9")


class TestMarkers(unittest.TestCase):
    def test_labels_hover_and_climb_exclusion(self):
        found = graphs_tool.markers(events([
            [10.0, "frontend->productcatalogservice", "ON→OFF", "rpr_burst", "2.46", NAN, "3", NAN],
            [20.0, "checkoutservice", "OFF→ON", "rejection", NAN, "0.03", "0", "11"],
            [30.0, "frontend->checkoutservice", "ON→OFF", "rpr", "0.90", NAN, "1", NAN],
            [40.0, "frontend->cartservice", "1→2", "rpr", NAN, NAN, "1", NAN],
            [50.0, "frontend->cartservice", "2→3", "rpr", NAN, NAN, "2", NAN],
        ]))
        self.assertEqual([m["label"] for m in found], ["E5 burst", "V3", "E3 normal"])
        self.assertEqual([m["x"] for m in found], [10.0, 20.0, 30.0])
        self.assertIn("rpr=2.46", found[0]["hover"])
        self.assertIn("from_attempts=3", found[0]["hover"])
        self.assertNotIn("rejection", found[0]["hover"])
        self.assertIn("consecutive_low=11", found[1]["hover"])
        self.assertNotEqual(found[0]["color"], found[1]["color"])

    def test_comparison_series_keeps_climbs_as_their_own_lines(self):
        series = graphs_tool.event_series(events([
            [10.0, "frontend->productcatalogservice", "ON→OFF", "rpr_burst", "2.46", NAN, "3", NAN],
            [30.0, "frontend->checkoutservice", "ON→OFF", "rpr", "0.90", NAN, "1", NAN],
            [20.0, "checkoutservice", "OFF→ON", "rejection", NAN, "0.03", "0", "11"],
            [40.0, "frontend->cartservice", "1→2", "rpr", NAN, NAN, "1", NAN],
            [50.0, "frontend->cartservice", "2→3", "rpr", NAN, NAN, "2", NAN],
        ]))
        self.assertEqual([item[0] for item in series], ["ON→OFF", "OFF→ON", "1→2", "2→3"])
        self.assertEqual(series[0][1][:2], [10.0, 10.0])
        self.assertIn(30.0, series[0][1])
        climb = graphs_tool.markers(events([
            [40.0, "frontend->cartservice", "1→2", "rpr", NAN, NAN, "1", NAN],
        ]), steps=graphs_tool.COMPARE_EVENT_STEPS)[0]
        self.assertEqual(graphs_tool.event_caption(climb), "E2 1→2")
        self.assertIn("frontend->cartservice 1→2", climb["hover"])


class TestSloMiss(unittest.TestCase):
    def test_fail_over_rps_empty_when_no_load(self):
        view = pd.DataFrame({"locust.total.Fail": [0.0, 5.0, 3.0],
                             "locust.total.RPS": [10.0, 0.0, 6.0]})
        result = graphs_tool.slo_miss(view)
        self.assertEqual(result.iloc[0], 0.0)
        self.assertTrue(math.isnan(result.iloc[1]))
        self.assertEqual(result.iloc[2], 0.5)
        self.assertIsNone(graphs_tool.slo_miss(pd.DataFrame({"x": [1]})))


class TestStrip(unittest.TestCase):
    def test_rows_follow_edge_order_and_off_runs_have_none(self):
        view = pd.DataFrame({
            "rg.frontend->checkoutservice.attempts": [3.0, 0.0],
            "rg.frontend->adservice.attempts": [3.0, 3.0],
        })
        matrix = graphs_tool.strip_matrix(view)
        self.assertEqual(list(matrix.index), ["E1", "E3"])
        self.assertEqual(matrix.loc["E3"].tolist(), [3.0, 0.0])
        self.assertIsNone(graphs_tool.strip_matrix(pd.DataFrame({"locust.total.RPS": [1.0]})))


class TestLineSpecs(unittest.TestCase):
    def view(self):
        return pd.DataFrame({
            "locust.total.Goodput": [1.0, 2.0],
            "locust.total.RPS": [1.0, 2.0],
            "locust.total.Latency95": [5.0, 6.0],
            "inbound.cartservice.rejection": [0.0, 0.0],
            "inbound.checkoutservice.rejection": [0.0, 0.1],
            "edge.frontend->checkoutservice.rpr": [0.0, 0.4],
            "edge.frontend->checkoutservice.retry_per_s": [0.0, 2.0],
            "resource.frontend.cpu_millicores": [10.0, 20.0],
        })

    def test_quiet_lines_are_legend_only_unless_all(self):
        by_column = {s[1]: s for s in graphs_tool.line_specs(self.view())}
        self.assertIs(by_column["inbound.checkoutservice.rejection"][3], True)
        self.assertEqual(by_column["inbound.cartservice.rejection"][3], "legendonly")
        self.assertEqual(by_column["edge.frontend->checkoutservice.rpr"][2], "E3 frontend->checkoutservice")
        self.assertEqual(by_column["inbound.cartservice.rejection"][2], "cartservice")
        self.assertEqual(by_column["locust.total.Goodput"][2], "Goodput")
        every = {s[1]: s for s in graphs_tool.line_specs(self.view(), show_all=True)}
        self.assertIs(every["inbound.cartservice.rejection"][3], True)

    def test_cpu_name_carries_the_table_limit(self):
        named = graphs_tool.line_specs(self.view(), limits={"frontend": 1150})
        cpu = next(spec for spec in named if spec[1] == "resource.frontend.cpu_millicores")
        self.assertEqual(cpu[2], "frontend (1150)")
        plain = graphs_tool.line_specs(self.view())
        cpu = next(spec for spec in plain if spec[1] == "resource.frontend.cpu_millicores")
        self.assertEqual(cpu[2], "frontend")


from test_hold_clock import E, iso, make_run  # noqa: E402


def render(run: Path) -> str:
    out = run / "explore.html"
    graphs_tool.write_html(graphs_tool.build_figure(run), out)
    return out.read_text(encoding="utf-8")


def strip_note_texts(fig) -> list[str]:
    xref = f"{graphs_tool.axis(graphs_tool.ROW['strip'], 'x')} domain"
    return [annotation.text for annotation in fig.layout.annotations if annotation.xref == xref]


class TestCpuLimits(unittest.TestCase):
    def test_manifest_row_overrides_the_paper_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "run_manifest.json"
            manifest.write_text(json.dumps({"scale_constraints": [{
                "deployment": "checkoutservice",
                "method": "cpu_limit",
                "cpu_limit_millicores": 200,
            }]}), encoding="utf-8")
            limits = graphs_tool.cpu_limits(Path(tmp))
        self.assertEqual(limits["checkoutservice"], 200)
        self.assertEqual(limits["frontend"], 1150)


class TestBuild(unittest.TestCase):
    def test_html_has_codes_markers_and_retryguard_off_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            off_fig = graphs_tool.build_figure(run)
            off = render(run)
            self.assertEqual(strip_note_texts(off_fig), ["RetryGuard off in this run"])
            self.assertIn("RetryGuard off in this run", off)
            self.assertNotIn("E3 burst", off)
            (run / "retryguard.log").write_text("\n".join([
                f"{iso(E + 30)}  OBSERVE  frontend->checkoutservice  rpr=0.5000  attempts=3  "
                "state=ON  metric=rpr",
                f"{iso(E + 31)}  frontend->checkoutservice  ON→OFF   rpr=2.10  consecutive_high=2  "
                "attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4",
                f"{iso(E + 32)}  OBSERVE  frontend->checkoutservice  rpr=0.0000  attempts=0  "
                "state=OFF  metric=rpr",
                f"{iso(E + 60)}  checkoutservice  OFF→ON   rejection=0.03  consecutive_low=11  "
                "attempts=1  from_attempts=0  metric=rejection  elapsed_s=20",
            ]), encoding="utf-8")
            on_fig = graphs_tool.build_figure(run)
            on = render(run)
            self.assertNotIn("RetryGuard off in this run", on)
            self.assertIn("E3 burst", on)
            self.assertIn("V3", on)
            self.assertIn("E14", on)
            self.assertIn("V9", on)
            labels = [annotation.text for annotation in on_fig.layout.annotations]
            self.assertIn("E3 burst", labels)
            self.assertIn("V3", labels)
            compare = graphs_tool.compare_figure(run)
            named = {
                annotation.text: annotation.hovertext
                for annotation in compare.layout.annotations
            }
            self.assertIn("frontend->checkoutservice ON→OFF", named["E3 burst"])
            self.assertIn("rpr=", named["E3 burst"])
            self.assertIn("from_attempts=", named["E3 burst"])
            self.assertIn("checkoutservice OFF→ON", named["V3"])
            self.assertIn("consecutive_low=", named["V3"])
            burst = next(annotation for annotation in compare.layout.annotations if annotation.text == "E3 burst")
            self.assertEqual(burst.yanchor, "bottom")
            self.assertEqual(burst.y, 1)
            strip_x = graphs_tool.axis(graphs_tool.ROW["strip"], "x")
            switch_lines = [shape for shape in on_fig.layout.shapes if shape.line.width == 1]
            self.assertEqual(graphs_tool.axis(graphs_tool.ROW["locust"], "x"), "x")
            self.assertTrue(any(shape.xref == "x" for shape in switch_lines))
            self.assertTrue(any(shape.name == "ON→OFF" for shape in switch_lines))
            self.assertTrue(switch_lines)
            for shape in switch_lines:
                expected = "above" if shape.xref == strip_x else "below"
                self.assertEqual(shape.layer, expected, shape.xref)

    def test_code_key_follows_a_chart_that_can_grow(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            out = Path(tmp) / "explore.html"
            graphs_tool.write_html(graphs_tool.build_figure(run), out, run)
            page = out.read_text(encoding="utf-8")
        chart = page.index('id="compare-graph"')
        key = page.index("Service codes, OFF→ON")
        self.assertLess(chart, key)
        wrapper = page[page.index("<body>") + len("<body>"):chart]
        self.assertNotIn("height:", wrapper)
        self.assertIn(
            'id="compare-graph" class="plotly-graph-div" style="height:',
            page,
        )
        self.assertGreater(page.find("function fitBox()"), 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


class TestLegendClicks(unittest.TestCase):
    """Clicks the legend the way the page does. A string check cannot see that
    Plotly dropped the class the handler used to look for."""

    def test_section_title_toggles_the_group_and_an_axis_title_does_not(self):
        if sync_playwright is None:
            self.skipTest("playwright is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            out = Path(tmp) / "explore.html"
            graphs_tool.write_html(graphs_tool.build_figure(run), out, run)
            self._click(out)

    def _click(self, out: Path) -> None:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(out.as_uri())
            page.wait_for_selector("#compare-graph .legend .traces")
            page.wait_for_selector("#graph .legend .traces")
            page.wait_for_function(
                """() => {
                  const graph = document.getElementById('compare-graph');
                  const svg = graph.querySelector('.main-svg');
                  return svg && Math.abs(graph.offsetHeight - svg.getBoundingClientRect().height) < 2;
                }"""
            )
            self._expect_toggle(page, "compare-graph", "locust", start_on=False)
            self._expect_toggle(page, "graph", "locust", start_on=True)
            self._item_toggles_only_itself(page)
            self._axis_title_leaves_the_group(page)
            browser.close()

    def _expect_toggle(self, page, graph_id: str, group: str, start_on: bool) -> None:
        names = self._names(page, graph_id, group)
        self.assertTrue(names)
        shown = start_on
        self.assertEqual(self._state(page, graph_id, group), self._flags(names, shown))
        self._click_legend(page, graph_id, "Goodput / RPS (req/s)", title=True)
        shown = not shown
        self._wait_state(page, graph_id, group, self._flags(names, shown), "section title")
        self._click_legend(page, graph_id, "Goodput / RPS (req/s)", title=True)
        shown = not shown
        self._wait_state(page, graph_id, group, self._flags(names, shown), "section title again")

    def _item_toggles_only_itself(self, page) -> None:
        names = self._names(page, "compare-graph", "locust")
        self._click_legend(page, "compare-graph", "Goodput", title=False)
        expected = ["Goodput=on" if name == "Goodput" else f"{name}=off" for name in names]
        self._wait_state(page, "compare-graph", "locust", expected, "Goodput item")

    def _axis_title_leaves_the_group(self, page) -> None:
        # The axis title uses the same word as the Rejection section. Plotly
        # draws it with pointer-events:none, so a pointer click does not land
        # on it; deliver the event to the title itself, which is the case the
        # handler used to get wrong.
        before = self._state(page, "graph", "rejection")
        delivered = page.evaluate(
            """() => {
              const graph = document.getElementById('graph');
              const node = [...graph.querySelectorAll('text')].find(item =>
                item.textContent === 'Rejection' && !item.closest('.legend'));
              if (!node) return false;
              node.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
              return true;
            }"""
        )
        self.assertTrue(delivered)
        page.wait_for_timeout(300)
        self.assertEqual(self._state(page, "graph", "rejection"), before)

    def _click_legend(self, page, graph_id: str, label: str, title: bool) -> None:
        point = page.evaluate(
            """(args) => {
              const graph = document.getElementById(args.id);
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
            {"id": graph_id, "label": label, "title": title},
        )
        self.assertIsNotNone(point, f"missing legend text {label} on {graph_id}")
        page.mouse.click(point["x"], point["y"])

    def _names(self, page, graph_id: str, group: str) -> list[str]:
        return page.evaluate(
            """(args) => document.getElementById(args.id).data
              .filter(trace => trace.legendgroup === args.group)
              .map(trace => trace.name)""",
            {"id": graph_id, "group": group},
        )

    def _state(self, page, graph_id: str, group: str) -> list[str]:
        return page.evaluate(
            """(args) => document.getElementById(args.id).data
              .filter(trace => trace.legendgroup === args.group)
              .map(trace => trace.name + '=' + (trace.visible === 'legendonly' ? 'off' : 'on'))""",
            {"id": graph_id, "group": group},
        )

    def _flags(self, names: list[str], shown: bool) -> list[str]:
        mark = "on" if shown else "off"
        return [f"{name}={mark}" for name in names]

    def _wait_state(self, page, graph_id: str, group: str, expected: list[str], what: str) -> None:
        try:
            page.wait_for_function(
                """(args) => {
                  const got = document.getElementById(args.id).data
                    .filter(trace => trace.legendgroup === args.group)
                    .map(trace => trace.name + '=' + (trace.visible === 'legendonly' ? 'off' : 'on'));
                  return JSON.stringify(got) === JSON.stringify(args.expected);
                }""",
                arg={"id": graph_id, "group": group, "expected": expected},
                timeout=3000,
            )
        except Exception:
            self.fail(f"after {what}: {self._state(page, graph_id, group)} != {expected}")


if __name__ == "__main__":
    unittest.main()
