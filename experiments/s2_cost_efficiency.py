"""S2 cost-efficiency table and figures for the ten locked S2 mode-matrix holds.

    python experiments/s2_cost_efficiency.py

Writes to experiments/explore_out/s2_cost/ (git-ignored):
  cost_table.csv / cost_table.md   per hold and per cell (mean, min, max over the two repeats)
  fig_*.png                        static figures (needs kaleido)

Cost here means: retries sent per good request, and CPU spent per unit of goodput.
Goodput, retry and CPU numbers do not use topfull_throttle.csv, so the throttle FLAG
holds stay valid for this table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "experiments" / "results" / "final results"
OUT = REPO / "experiments" / "explore_out" / "s2_cost"

CELLS = [
    # label, folder under final results, log_folder stem
    ("tf_only", "S2_sustained_overload_normal/tf_only", "final_s2_tf_only"),
    ("rg_only_normal", "S2_sustained_overload_normal/rg_only", "final_s2_rg_only_normal"),
    ("both_normal", "S2_sustained_overload_normal/both", "final_s2_both_normal"),
    ("rg_only_burst", "S2_sustained_overload_burst/rg_only", "final_s2_rg_only_burst"),
    ("both_burst", "S2_sustained_overload_burst/both", "final_s2_both_burst"),
]
RUNS = (1, 2)
HOT_EDGE = ("frontend", "recommendationservice")
CPU_FOCUS = ("recommendationservice", "checkoutservice")
COLORS = {
    "tf_only": "#7f7f7f", "rg_only_normal": "#1f77b4", "both_normal": "#2ca02c",
    "rg_only_burst": "#ff7f0e", "both_burst": "#d62728",
}
FLAGGED = {
    "final_s2_tf_only_run2", "final_s2_rg_only_burst_run2",
    "final_s2_both_burst_run1", "final_s2_both_burst_run2",
}


def run_dir(cell: tuple, run: int) -> Path:
    return BASE / cell[1] / f"{cell[2]}_run{run}"


def _ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, format="ISO8601")


def hold_window(total: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    stamps = _ts(total["timestamp"])
    return stamps.min(), stamps.max()


def retry_increments(edges: pd.DataFrame, start, end) -> pd.DataFrame:
    """Positive per-poll increase of the lifetime `retry` counter on each edge.

    The counter is a lifetime total, so the first row of an edge is a leftover and is
    not counted. A poll where the counter goes backwards adds nothing. Same rule as
    graphs_tool. Polls are kept from the hold window (plus the one before it as baseline).
    """
    edges = edges.copy()
    edges["t"] = _ts(edges["timestamp"])
    edges = edges.sort_values(["caller", "target", "t"])
    edges["inc"] = edges.groupby(["caller", "target"])["retry"].diff().clip(lower=0)
    edges["tot_inc"] = edges.groupby(["caller", "target"])["total"].diff().clip(lower=0)
    return edges[(edges["t"] >= start) & (edges["t"] <= end)].dropna(subset=["inc"])


def hold_metrics(directory: Path) -> dict:
    total = pd.read_csv(directory / "total.csv")
    start, end = hold_window(total)
    seconds = (end - start).total_seconds()
    mean_goodput = float(total["Goodput"].mean())
    mean_rps = float(total["RPS"].mean())
    good_requests = mean_goodput * seconds
    slo_miss = float(total["Fail"].sum() / total["RPS"].sum()) if total["RPS"].sum() else float("nan")

    edges = retry_increments(pd.read_csv(directory / "service_edges.csv"), start, end)
    hot = edges[(edges["caller"] == HOT_EDGE[0]) & (edges["target"] == HOT_EDGE[1])]
    hot_retries = float(hot["inc"].sum())
    all_retries = float(edges["inc"].sum())
    hot_first = float((hot["tot_inc"] - hot["inc"]).clip(lower=0).sum())

    usage = pd.read_csv(directory / "resource_usage.csv")
    usage["t"] = _ts(usage["timestamp"])
    usage = usage[(usage["t"] >= start) & (usage["t"] <= end) & (usage["service"] != "__master_node__")]
    # one value per poll per service = sum over replicas already; mean over the hold
    per_service = usage.groupby("service")["cpu_millicores"].mean()
    app_cpu = float(per_service.sum())
    focus_cpu = float(per_service[list(CPU_FOCUS)].sum())

    return {
        "hold_s": seconds,
        "goodput_rps": mean_goodput,
        "rps": mean_rps,
        "slo_miss": slo_miss,
        "p95_ms": float(total["Latency95"].mean()),
        "good_requests": good_requests,
        "hot_retries": hot_retries,
        "all_retries": all_retries,
        "hot_retries_per_first_attempt": hot_retries / hot_first if hot_first else float("nan"),
        "retries_per_1k_good": 1000 * all_retries / good_requests if good_requests else float("nan"),
        "hot_retries_per_1k_good": 1000 * hot_retries / good_requests if good_requests else float("nan"),
        "app_cpu_mc": app_cpu,
        "focus_cpu_mc": focus_cpu,
        "mc_per_goodput": app_cpu / mean_goodput if mean_goodput else float("nan"),
        "focus_mc_per_goodput": focus_cpu / mean_goodput if mean_goodput else float("nan"),
    }


def build_table() -> pd.DataFrame:
    rows = []
    for cell in CELLS:
        for run in RUNS:
            directory = run_dir(cell, run)
            metrics = hold_metrics(directory)
            metrics.update(cell=cell[0], run=run, hold=directory.name,
                           throttle_flag=directory.name in FLAGGED)
            rows.append(metrics)
    return pd.DataFrame(rows)


def cell_summary(table: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    grouped = table.groupby("cell", sort=False)[columns]
    return pd.concat({"mean": grouped.mean(), "min": grouped.min(), "max": grouped.max()}, axis=1)


def write_markdown(table: pd.DataFrame, path: Path) -> None:
    per_hold_cols = ["goodput_rps", "slo_miss", "p95_ms", "all_retries", "hot_retries",
                     "retries_per_1k_good", "app_cpu_mc", "mc_per_goodput"]
    lines = ["# S2 cost-efficiency table (generated)", "",
             "Per hold. `retries_per_1k_good` = all-edge retries per 1000 good requests. "
             "`mc_per_goodput` = summed app CPU millicores per req/s of goodput.", "",
             "| hold | " + " | ".join(per_hold_cols) + " | throttle |",
             "| --- | " + " | ".join(["---:"] * len(per_hold_cols)) + " | --- |"]
    for _, row in table.iterrows():
        cells = [f"{row[c]:,.3f}" if c in ("slo_miss",) else f"{row[c]:,.1f}" for c in per_hold_cols]
        lines.append(f"| {row['hold']} | " + " | ".join(cells) + f" | {'FLAG' if row['throttle_flag'] else 'ok'} |")
    lines += ["", "## Per cell, mean [min, max] over the two repeats", "",
              "| cell | goodput req/s | SLO-miss | P95 ms | retries / 1k good | hot-edge retries | mc per req/s |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for cell in CELLS:
        sub = table[table["cell"] == cell[0]]

        def span(col: str, fmt: str = ",.1f") -> str:
            return f"{sub[col].mean():{fmt}} [{sub[col].min():{fmt}}, {sub[col].max():{fmt}}]"

        lines.append(f"| {cell[0]} | {span('goodput_rps')} | {span('slo_miss', '.3f')} | {span('p95_ms', ',.0f')} "
                     f"| {span('retries_per_1k_good')} | {span('hot_retries', ',.0f')} | {span('mc_per_goodput', '.2f')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def bar_figure(table: pd.DataFrame, metric: str, title: str, ytitle: str) -> go.Figure:
    fig = go.Figure()
    for cell in CELLS:
        sub = table[table["cell"] == cell[0]].sort_values("run")
        labels = [f"{cell[0]}<br>run{r}{'*' if f else ''}" for r, f in zip(sub["run"], sub["throttle_flag"])]
        fig.add_trace(go.Bar(
            x=labels, y=sub[metric], marker_color=COLORS[cell[0]], showlegend=False,
            text=[f"{v:,.1f}" for v in sub[metric]], textposition="outside",
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=[sub[metric].mean()] * len(labels), mode="lines", showlegend=False,
            line={"color": "black", "width": 3, "dash": "dash"},
            hovertemplate="cell mean %{y:,.1f}<extra></extra>",
        ))
    fig.update_layout(title=title, yaxis_title=ytitle, template="simple_white",
                      width=1100, height=540, bargap=0.2,
                      annotations=[{"text": "Dashed line = mean of the two repeats. * = TopFull cap data stale on that hold (this metric does not use it).",
                                    "xref": "paper", "yref": "paper", "x": 0, "y": -0.22,
                                    "showarrow": False, "font": {"size": 11}}])
    return fig


def timeseries_figure(table: pd.DataFrame, run: int) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=("Goodput (req/s, 10 s mean)", "P95 latency (ms, 10 s mean)",
                                        "Cumulative retries, all edges"))
    for cell in CELLS:
        directory = run_dir(cell, run)
        total = pd.read_csv(directory / "total.csv")
        start, _ = hold_window(total)
        total["t"] = (_ts(total["timestamp"]) - start).dt.total_seconds()
        total["bin"] = (total["t"] // 10) * 10
        binned = total.groupby("bin")[["Goodput", "Latency95"]].mean()
        edges = retry_increments(pd.read_csv(directory / "service_edges.csv"), start, hold_window(total)[1])
        edges["t"] = (edges["t"] - start).dt.total_seconds()
        cum = edges.groupby("t")["inc"].sum().sort_index().cumsum()
        kw = {"name": cell[0], "legendgroup": cell[0], "line": {"color": COLORS[cell[0]], "width": 2}}
        fig.add_trace(go.Scatter(x=binned.index, y=binned["Goodput"], **kw), row=1, col=1)
        fig.add_trace(go.Scatter(x=binned.index, y=binned["Latency95"], showlegend=False, **{k: v for k, v in kw.items() if k != "name"}), row=2, col=1)
        fig.add_trace(go.Scatter(x=cum.index, y=cum.values, showlegend=False, **{k: v for k, v in kw.items() if k != "name"}), row=3, col=1)
    fig.update_xaxes(title_text="hold clock (s)", row=3, col=1)
    fig.update_layout(title=f"S2, repeat {run}: all five cells on the hold clock",
                      template="simple_white", width=1000, height=900)
    return fig


def cpu_figure(table: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for metric, label in (("app_cpu_mc", "all app services"), ("focus_cpu_mc", "recommendation + checkout")):
        means = table.groupby("cell", sort=False)[metric].mean()
        fig.add_trace(go.Bar(name=label, x=list(means.index), y=list(means.values)))
    fig.update_layout(title="Mean CPU over the hold (millicores, summed over replicas)", barmode="group",
                      template="simple_white", width=900, height=480, yaxis_title="millicores")
    return fig


def save(fig: go.Figure, name: str) -> None:
    fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(OUT / f"{name}.png", scale=2)
    except Exception as err:  # kaleido needs a Chrome install
        print(f"PNG skipped for {name}: {type(err).__name__}: {str(err)[:120]}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    table = build_table()
    table.to_csv(OUT / "cost_table.csv", index=False)
    write_markdown(table, OUT / "cost_table.md")
    print((OUT / "cost_table.md").read_text(encoding="utf-8"))
    save(bar_figure(table, "goodput_rps", "Goodput per cell", "mean goodput (req/s)"), "fig_goodput")
    save(bar_figure(table, "retries_per_1k_good", "Retries sent per 1000 good requests (all edges)",
                    "retries per 1000 good requests"), "fig_retries_per_good")
    save(bar_figure(table, "mc_per_goodput", "CPU spent per unit of goodput",
                    "app millicores per (req/s of goodput)"), "fig_cpu_per_goodput")
    save(cpu_figure(table), "fig_cpu_absolute")
    for run in RUNS:
        save(timeseries_figure(table, run), f"fig_timeline_run{run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
