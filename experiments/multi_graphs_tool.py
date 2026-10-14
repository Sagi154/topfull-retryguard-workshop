"""multi_graphs_tool: N holds as stacked comparison panels with one shared legend.

    python experiments/multi_graphs_tool.py <run_dir> <run_dir> [<run_dir> ...]

Writes experiments/explore_out/multi_<run names>.html (not committed).
Design: docs/superpowers/specs/2026-10-14-multi-graphs-tool-design.md
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import plotly.colors as plotly_colors
import plotly.graph_objects as go
import plotly.io as pio

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graphs_tool  # noqa: E402

OUT_DIR = graphs_tool.OUT_DIR
HOLD_CLOCK_TITLE = "Hold clock (s since the first Locust row)"
PANEL_HEIGHT = 440
SLIDER_EXTRA = 70
# The legend figure starts tall so Plotly never scrolls it. The page script then
# shrinks the figure to the legend's measured height.
LEGEND_HEIGHT = 900
# Room above the plot for the rotated event names.
PANEL_MARGIN = {"t": 80, "r": 36, "b": 48, "l": 64}
GROUP_ORDER = list(graphs_tool.PANEL_KEYS) + [graphs_tool.EVENT_GROUP]
CPU_LIMIT_SUFFIX = re.compile(r" \((\d+)\)$")
PALETTE = plotly_colors.qualitative.Dark24 + plotly_colors.qualitative.Light24


def run_label(run_dir: Path) -> str:
    """Scenario/mode folder, variant folder, and run folder, as one header line."""
    run_dir = Path(run_dir)
    parts = [run_dir.parent.parent.name, run_dir.parent.name, run_dir.name]
    return " / ".join(part for part in parts if part)


def panel_figure(run_dir: Path) -> go.Figure:
    """One run's comparison chart, without its own legend.

    CPU traces lose the limit from the name so the same toggle hits the same line in
    every panel. The limit moves into the hover text.
    """
    fig = graphs_tool.compare_figure(run_dir)
    for trace in fig.data:
        trace.showlegend = False
        if trace.legendgroup != "cpu":
            continue
        match = CPU_LIMIT_SUFFIX.search(trace.name)
        if match is None:
            continue
        base = trace.name[:match.start()]
        trace.hovertemplate = f"%{{y:.0f}} of {match.group(1)}m<extra>{base}</extra>"
        trace.name = base
    fig.update_layout(
        showlegend=False, height=PANEL_HEIGHT, margin=dict(PANEL_MARGIN),
        xaxis_domain=[0, 0.97],
    )
    return fig


def pin_x_range(figs: list[go.Figure]) -> list[float]:
    """Every panel shows the longest run's span, so one second lines up vertically."""
    spans = [fig.layout.xaxis.range for fig in figs if fig.layout.xaxis.range is not None]
    low = min(span[0] for span in spans)
    high = max(span[1] for span in spans)
    for fig in figs:
        fig.update_layout(xaxis_range=[low, high])
    return [low, high]


def decorate_slider(figs: list[go.Figure]) -> None:
    """The range slider and the x title sit on the last panel only.

    Panels that have no height yet take PANEL_HEIGHT. The last panel is that
    height plus the slider, so the extra space is the slider and nothing else.
    """
    for fig in figs[:-1]:
        height = PANEL_HEIGHT if fig.layout.height is None else fig.layout.height
        fig.update_layout(xaxis_title_text="", margin_b=24, height=height)
    last = figs[-1]
    panel_height = PANEL_HEIGHT if figs[0].layout.height is None else figs[0].layout.height
    last.update_layout(
        xaxis_title_text=HOLD_CLOCK_TITLE,
        xaxis_rangeslider={"visible": True, "thickness": 0.06},
        height=panel_height + SLIDER_EXTRA,
    )


def _union_order(item: tuple[tuple[str, str], go.Scatter]) -> tuple[int, int]:
    group, name = item[0]
    step = graphs_tool.COMPARE_EVENT_STEPS.index(name) if group == graphs_tool.EVENT_GROUP else 0
    return GROUP_ORDER.index(group), step


def series_union(figs: list[go.Figure]) -> dict[tuple[str, str], go.Scatter]:
    """Every (legendgroup, name) across the panels, grouped in legend order."""
    found: dict[tuple[str, str], go.Scatter] = {}
    for fig in figs:
        for trace in fig.data:
            found.setdefault((trace.legendgroup, trace.name), trace)
    return dict(sorted(found.items(), key=_union_order))


def assign_colors(figs: list[go.Figure], union: dict) -> dict[tuple[str, str], str]:
    """One colour per series, so a line looks the same in every panel and the legend.

    Plotly colours by trace position, and runs have different trace sets, so the
    default would give the same series different colours in different panels.
    Event lines keep the colour graphs_tool gave them.
    """
    colors = {}
    for index, (key, trace) in enumerate(union.items()):
        if key[0] == graphs_tool.EVENT_GROUP:
            colors[key] = trace.line.color
        else:
            colors[key] = PALETTE[index % len(PALETTE)]
    for fig in figs:
        for trace in fig.data:
            trace.line.color = colors[(trace.legendgroup, trace.name)]
    return colors


def legend_figure(union: dict, colors: dict) -> go.Figure:
    """A figure that draws nothing but the legend of the union of all panels."""
    fig = go.Figure()
    for (group, name), trace in union.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines", name=name,
            visible=True if group == graphs_tool.EVENT_GROUP else "legendonly",
            line={"width": 2, "color": colors[(group, name)]},
            legendgroup=group, meta=trace.meta,
            legendgrouptitle={"text": trace.legendgrouptitle.text, "font": {"color": "black"}},
        ))
    fig.update_layout(
        height=LEGEND_HEIGHT,
        margin={"t": 4, "r": 36, "b": 4, "l": 64},
        xaxis={"visible": False},
        yaxis={"visible": False},
        legend={"groupclick": "toggleitem", "tracegroupgap": 16, "orientation": "h",
                "x": 0, "xanchor": "left", "y": 1, "yanchor": "top",
                "font": {"size": 11}, "grouptitlefont": {"color": "black"}},
    )
    return fig


PAGE_STYLE = """
body { margin: 0; font-family: sans-serif; color: #222; }
h3.run { margin: 14px 16px 0; font-size: 14px; }
div.note { margin: 2px 16px 0; min-height: 15px; font-size: 12px; color: #777; }
"""


def out_path(run_dirs: list[Path]) -> Path:
    """multi_<names>.html. A repeated run folder name gets its position appended."""
    names: list[str] = []
    for index, run_dir in enumerate(run_dirs, start=1):
        name = Path(run_dir).name
        names.append(f"{name}-{index}" if name in names else name)
    return OUT_DIR / f"multi_{'__'.join(names)}.html"


def build_page(run_dirs: list[Path]) -> str:
    run_dirs = [Path(run_dir) for run_dir in run_dirs]
    figs = [panel_figure(run_dir) for run_dir in run_dirs]
    x_pin = pin_x_range(figs)
    union = series_union(figs)
    colors = assign_colors(figs, union)
    decorate_slider(figs)
    legend = legend_figure(union, colors)

    parts = []
    for index, (run_dir, fig) in enumerate(zip(run_dirs, figs)):
        parts.append(f'<h3 class="run">{html.escape(run_label(run_dir))}</h3>')
        parts.append(f'<div id="note-{index}" class="note"></div>')
        parts.append(pio.to_html(
            fig, full_html=False, include_plotlyjs=True if index == 0 else False,
            div_id=f"panel-{index}",
        ))
    parts.append(pio.to_html(legend, full_html=False, include_plotlyjs=False, div_id="legend-graph"))
    parts.append(graphs_tool.legend_html())
    title = html.escape(" vs ".join(run_dir.name for run_dir in run_dirs))
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{PAGE_STYLE}</style></head><body>"
        + "".join(parts)
        + page_script(len(figs), x_pin)
        + "</body></html>"
    )


def write_page(run_dirs: list[Path], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_page(run_dirs), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive hold-clock comparison of several runs, one panel each.")
    parser.add_argument("runs", nargs="+", help="Run folders (at least two)")
    args = parser.parse_args(argv)
    runs = [Path(run) for run in args.runs]
    if len(runs) < 2:
        parser.error("need at least two run folders")
    missing = [str(run) for run in runs if not run.is_dir()]
    if missing:
        parser.error("not a folder: " + ", ".join(missing))
    out = out_path(runs)
    write_page(runs, out)
    print(out)
    return 0


PAGE_JS = r"""
<script>
(function () {
  var PANEL_IDS = __PANEL_IDS__;
  var AXIS = __AXIS__;
  var X_PIN = __X_PIN__;
  // A unit's axis stays hidden until one of its lines is on. Visible units pack
  // against the plot: the first on the right edge, the rest stepping outward.
  var RIGHT = ['ms', 'fraction', 'retries/request', 'millicores', 'retries', 'ticks'];
  var EVENTS = 'events';

  function start() {
    var legend = document.getElementById('legend-graph');
    var panels = PANEL_IDS.map(function (id) { return document.getElementById(id); });
    var ready = legend && legend.data && panels.every(function (panel) { return panel && panel.data; });
    if (!ready) { setTimeout(start, 50); return; }
    wire(legend, panels);
  }

  function wire(legend, panels) {
    var busy = false;

    function key(trace) { return trace.legendgroup + '||' + trace.name; }

    // The legend figure is the only place visibility is decided.
    function legendState() {
      var state = {};
      legend.data.forEach(function (trace) { state[key(trace)] = trace.visible !== 'legendonly'; });
      return state;
    }

    function axisUpdate() {
      var shown = {};
      legend.data.forEach(function (trace) {
        if (!AXIS[trace.meta] || AXIS[trace.meta] === 'yaxis') return;
        if (trace.visible !== 'legendonly') shown[trace.meta] = true;
      });
      var active = RIGHT.filter(function (unit) { return shown[unit]; });
      var edge = active.length ? 1 - 0.07 * active.length : 0.97;
      var update = {'xaxis.domain[1]': Math.max(0.6, edge)};
      RIGHT.forEach(function (unit) {
        var name = AXIS[unit];
        var place = active.indexOf(unit);
        update[name + '.visible'] = place !== -1;
        if (place !== -1) {
          update[name + '.anchor'] = 'free';
          update[name + '.side'] = 'right';
          update[name + '.position'] = edge + 0.07 * place;
        }
      });
      return update;
    }

    // One range per unit, from the largest visible value in any panel, so a
    // height on one panel means the same thing on every other panel.
    function yRanges(state) {
      var top = {};
      panels.forEach(function (panel) {
        panel.data.forEach(function (trace) {
          if (!state[key(trace)] || !AXIS[trace.meta]) return;
          var max = top[trace.meta];
          Array.prototype.forEach.call(trace.y || [], function (value) {
            if (typeof value === 'number' && isFinite(value) && (max === undefined || value > max)) max = value;
          });
          if (max !== undefined) top[trace.meta] = max;
        });
      });
      var update = {};
      Object.keys(top).forEach(function (unit) {
        update[AXIS[unit] + '.range'] = [0, top[unit] > 0 ? top[unit] * 1.05 : 1];
      });
      return update;
    }

    function showNotes(state) {
      panels.forEach(function (panel, index) {
        var present = {};
        panel.data.forEach(function (trace) { present[key(trace)] = true; });
        var missing = {};
        legend.data.forEach(function (trace) {
          if (trace.legendgroup === EVENTS || !state[key(trace)] || present[key(trace)]) return;
          var title = trace.legendgrouptitle.text;
          missing[title] = (missing[title] || 0) + 1;
        });
        var parts = Object.keys(missing).map(function (title) { return title + ' (' + missing[title] + ')'; });
        document.getElementById('note-' + index).textContent =
          parts.length ? 'none in this run: ' + parts.join(', ') : '';
      });
    }

    function apply() {
      var state = legendState();
      var shared = Object.assign({}, axisUpdate(), yRanges(state));
      busy = true;
      var jobs = panels.map(function (panel) {
        var visible = panel.data.map(function (trace) { return state[key(trace)] ? true : 'legendonly'; });
        var update = Object.assign({}, shared);
        // The names on the event lines are annotations. They follow the legend.
        update.annotations = (panel.layout.annotations || []).map(function (item) {
          var k = EVENTS + '||' + item.name;
          if (!Object.prototype.hasOwnProperty.call(state, k)) return item;
          var copy = Object.assign({}, item);
          copy.visible = state[k];
          return copy;
        });
        return Plotly.restyle(panel, {visible: visible}).then(function () {
          return Plotly.relayout(panel, update);
        });
      });
      return Promise.all(jobs).then(function () { busy = false; showNotes(state); });
    }

    // Item click: toggle that one legend trace, then redraw the panels.
    legend.on('plotly_legendclick', function (event) {
      var trace = event.fullData[event.curveNumber];
      var show = trace.visible === 'legendonly';
      Plotly.restyle(legend, {visible: show ? true : 'legendonly'}, [event.curveNumber]).then(apply);
      return false;
    });

    // Title click: toggle the whole group. A title is the legend row without a
    // toggle rect; an axis title can use the same words, so only legend rows count.
    var titleOf = {};
    legend.data.forEach(function (trace) { titleOf[trace.legendgrouptitle.text] = trace.legendgroup; });
    legend.addEventListener('mousedown', function (event) {
      var text = event.target.closest ? event.target.closest('text') : null;
      if (!text || !text.closest('.legend')) return;
      var row = text.parentNode;
      if (!row || row.querySelector('.legendtoggle')) return;
      var group = titleOf[text.textContent];
      if (!group) return;
      event.stopPropagation();
      var indices = [];
      legend.data.forEach(function (trace, index) { if (trace.legendgroup === group) indices.push(index); });
      var allHidden = indices.every(function (index) { return legend.data[index].visible === 'legendonly'; });
      Plotly.restyle(legend, {visible: allHidden ? true : 'legendonly'}, indices).then(apply);
    }, true);

    // Plotly greys a title once every item in its group is hidden. Repaint black.
    function keepTitles() {
      legend.querySelectorAll('.legend .traces').forEach(function (row) {
        if (row.querySelector('.legendtoggle')) return;
        var node = row.querySelector('text');
        if (!node) return;
        node.style.fill = 'black';
        node.style.fillOpacity = '1';
      });
    }

    // The legend is a row of columns that wrap with the window. Size the figure
    // to the legend so there is no empty band and Plotly never scrolls it.
    // Plotly 7 clips the item row and leaves the drag layer on top of it when
    // the figure is only 16px taller than the legend, so the pad is 32.
    var lastHeight = 0;
    function fitLegend() {
      var node = legend.querySelector('.legend');
      if (!node) return;
      var height = Math.ceil(node.getBoundingClientRect().height) + 32;
      if (Math.abs(height - lastHeight) < 3) return;
      lastHeight = height;
      legend.parentElement.style.height = height + 'px';
      legend.style.height = height + 'px';
      Plotly.relayout(legend, {height: height});
    }

    legend.on('plotly_afterplot', function () { keepTitles(); fitLegend(); });
    new MutationObserver(keepTitles).observe(legend, {subtree: true, attributes: true, attributeFilter: ['style']});
    keepTitles();
    fitLegend();
    setTimeout(fitLegend, 0);
    showNotes(legendState());
  }
  start();
})();
</script>
"""


def page_script(panel_count: int, x_pin: list[float]) -> str:
    return (
        PAGE_JS
        .replace("__PANEL_IDS__", json.dumps([f"panel-{i}" for i in range(panel_count)]))
        .replace("__AXIS__", json.dumps(graphs_tool.COMPARE_AXIS))
        .replace("__X_PIN__", json.dumps(x_pin))
    )


if __name__ == "__main__":
    raise SystemExit(main())
