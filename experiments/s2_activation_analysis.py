"""S2 mode matrix, read by what each controller actually did.

    python experiments/s2_activation_analysis.py

Writes experiments/explore_out/s2_activation/ (git-ignored):
  activation.csv       one row per hold: did RetryGuard act, did TopFull cap, outcomes
  by_attempts.csv      per hold and attempts level on frontend->recommendationservice
  s2_activation.html   interactive page (plotly, offline)

A controller "acted" only when its actuator moved: RetryGuard changed attempts on an
edge (ON->OFF, OFF->ON, 1->2, 2->3), or TopFull published a live cap (fresh read,
0 < threshold < 10000). "Running" is not "acting".
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "experiments" / "results" / "final results"
OUT = REPO / "experiments" / "explore_out" / "s2_activation"

CELLS = [
    ("tf_only", "S2_sustained_overload_normal/tf_only", "final_s2_tf_only"),
    ("rg_only_normal", "S2_sustained_overload_normal/rg_only", "final_s2_rg_only_normal"),
    ("both_normal", "S2_sustained_overload_normal/both", "final_s2_both_normal"),
    ("rg_only_burst", "S2_sustained_overload_burst/rg_only", "final_s2_rg_only_burst"),
    ("both_burst", "S2_sustained_overload_burst/both", "final_s2_both_burst"),
]
RUNS = (1, 2)
HOT = "frontend->recommendationservice"
CAP_APIS = ("getproduct", "getcart", "postcheckout")
NO_CAP = 10000
CAP_CARRY_S = 6
ATTEMPT_SETTLE_S = 3
COLORS = {
    "tf_only": "#7f7f7f", "rg_only_normal": "#1f77b4", "both_normal": "#2ca02c",
    "rg_only_burst": "#ff7f0e", "both_burst": "#d62728",
}
TOGGLE = re.compile(r"^(\S+)\s+(\S+)\s+(ON→OFF|OFF→ON|1→2|2→3)\s.*?\battempts=(\d+)")
HOT_CALLEE = HOT.split("->")[1]
OBSERVE = re.compile(r"^(\S+)\s+OBSERVE\s+(\S+)\s+rpr=(\S+).*?attempts=(\d+)")


def _ts(values) -> pd.Series:
    return pd.to_datetime(values, utc=True, format="ISO8601")


def holds():
    for cell in CELLS:
        for run in RUNS:
            yield cell[0], run, BASE / cell[1] / f"{cell[2]}_run{run}"


def hold_clock(directory: Path):
    total = pd.read_csv(directory / "total.csv")
    total["t"] = _ts(total["timestamp"])
    start, end = total["t"].min(), total["t"].max()
    total["s"] = (total["t"] - start).dt.total_seconds()
    return total, start, end


def retryguard(directory: Path, start, end):
    """Toggles, and the attempts timeline on the hot edge.

    OBSERVE lines stop for an edge while it is shed, so the timeline comes from the
    toggle lines: each one carries the attempts in force after it. OFF→ON names the
    callee service, which on the hot edge is recommendationservice.
    """
    path = directory / "retryguard.log"
    if not path.exists():
        return None
    toggles = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TOGGLE.match(line)
        if match:
            toggles.append({"t": match.group(1), "target": match.group(2), "kind": match.group(3),
                            "attempts": int(match.group(4)), "line": line.strip()})
    toggles = pd.DataFrame(toggles, columns=["t", "target", "kind", "attempts", "line"])
    if len(toggles):
        toggles["t"] = _ts(toggles["t"])
        toggles["s"] = (toggles["t"] - start).dt.total_seconds()
    else:
        toggles["s"] = pd.Series(dtype=float)
    hot = toggles[toggles["target"].isin([HOT, HOT_CALLEE])]
    timeline = pd.concat([pd.DataFrame({"s": [-1e9], "attempts": [3]}), hot[["s", "attempts"]]], ignore_index=True)
    return toggles, timeline


def topfull(directory: Path, start, end):
    """Live caps per API, and how much of the hold had a fresh proxy read at all."""
    path = directory / "topfull_throttle.csv"
    if not path.exists():
        return None
    caps = pd.read_csv(path)
    caps["t"] = _ts(caps["timestamp"])
    caps = caps[(caps["t"] >= start) & (caps["t"] <= end)].copy()
    caps["s"] = (caps["t"] - start).dt.total_seconds()
    caps["live"] = (caps["threshold_fresh"] == 1) & (caps["threshold"] > 0) & (caps["threshold"] < NO_CAP)
    return caps


def covered_seconds(stamps: pd.Series, seconds: float, carry: float) -> float:
    """Seconds of the hold within `carry` of a stamp (each stamp covers [s, s+carry))."""
    if stamps.empty:
        return 0.0
    covered, last_end = 0.0, -1.0
    for s in sorted(stamps):
        lo, hi = max(s, last_end), min(s + carry, seconds)
        if hi > lo:
            covered += hi - lo
        last_end = max(last_end, s + carry)
    return covered


def hot_edge_series(directory: Path, start, end) -> pd.DataFrame:
    edges = pd.read_csv(directory / "service_edges.csv")
    edges = edges[(edges["caller"] == "frontend") & (edges["target"] == "recommendationservice")].copy()
    edges["t"] = _ts(edges["timestamp"])
    edges = edges.sort_values("t")
    edges["dt"] = edges["t"].diff().dt.total_seconds()
    edges["d_retry"] = edges["retry"].diff().clip(lower=0)
    edges["d_total"] = edges["total"].diff().clip(lower=0)
    edges = edges[(edges["t"] >= start) & (edges["t"] <= end)].dropna(subset=["dt"])
    edges = edges[edges["dt"] > 0]
    edges["s"] = (edges["t"] - start).dt.total_seconds()
    edges["retry_rps"] = edges["d_retry"] / edges["dt"]
    first = (edges["d_total"] - edges["d_retry"]).clip(lower=0)
    edges["rpr"] = edges["d_retry"] / first.where(first > 0)
    return edges


def detector_share(directory: Path, start, end, service: str) -> float:
    detect = pd.read_csv(directory / "topfull_detect.csv")
    detect["t"] = _ts(detect["timestamp"])
    rows = detect[(detect["service"] == service) & (detect["t"] >= start) & (detect["t"] <= end)]
    return float(rows["overloaded"].mean()) if len(rows) else float("nan")


def cpu_means(directory: Path, start, end) -> pd.Series:
    usage = pd.read_csv(directory / "resource_usage.csv")
    usage["t"] = _ts(usage["timestamp"])
    usage = usage[(usage["t"] >= start) & (usage["t"] <= end) & (usage["service"] != "__master_node__")]
    return usage.groupby("service")["cpu_millicores"].mean()


def all_edge_retries(directory: Path, start, end) -> float:
    edges = pd.read_csv(directory / "service_edges.csv")
    edges["t"] = _ts(edges["timestamp"])
    edges = edges.sort_values(["caller", "target", "t"])
    edges["inc"] = edges.groupby(["caller", "target"])["retry"].diff().clip(lower=0)
    return float(edges[(edges["t"] >= start) & (edges["t"] <= end)]["inc"].sum())


def attempts_at(observe: pd.DataFrame, seconds: pd.Series) -> pd.Series:
    """Attempts in force at each second, from the last change at or before it."""
    if observe is None or observe.empty:
        return pd.Series(3, index=seconds.index)
    ref = observe[["s", "attempts"]].sort_values("s")
    merged = pd.merge_asof(seconds.to_frame("s").reset_index().sort_values("s"), ref, on="s", direction="backward")
    return merged.set_index("index")["attempts"].fillna(3).astype(int).reindex(seconds.index)


def settled(observe: pd.DataFrame, seconds: pd.Series) -> pd.Series:
    """False for the first seconds after an attempts change, while Envoy picks it up."""
    if observe is None or observe.empty:
        return pd.Series(True, index=seconds.index)
    changes = observe["s"].iloc[1:].tolist()
    keep = pd.Series(True, index=seconds.index)
    for s in changes:
        keep &= ~((seconds >= s) & (seconds < s + ATTEMPT_SETTLE_S))
    return keep


def analyse_hold(cell: str, run: int, directory: Path):
    total, start, end = hold_clock(directory)
    seconds = (end - start).total_seconds()
    goodput = float(total["Goodput"].mean())
    rg = retryguard(directory, start, end)
    tf = topfull(directory, start, end)
    hot = hot_edge_series(directory, start, end)
    cpu = cpu_means(directory, start, end)

    row = {
        "cell": cell, "run": run, "hold": directory.name, "hold_s": round(seconds),
        "goodput_rps": goodput,
        "slo_miss": float(total["Fail"].sum() / total["RPS"].sum()),
        "p95_ms": float(total["Latency95"].mean()),
        "hot_retries": float(hot["d_retry"].sum()),
        "all_retries": all_edge_retries(directory, start, end),
        "app_cpu_mc": float(cpu.sum()),
        "rec_cpu_mc": float(cpu.get("recommendationservice", float("nan"))),
        "checkout_cpu_mc": float(cpu.get("checkoutservice", float("nan"))),
        "checkout_overloaded": detector_share(directory, start, end, "checkoutservice"),
    }
    row["retries_per_1k_good"] = 1000 * row["all_retries"] / (goodput * seconds)

    # RetryGuard
    if rg is None:
        row.update(rg_running=False, rg_sheds=0, rg_reenables=0, rg_climbs=0, rg_acted=False,
                   hot_s_at_0=0.0, hot_s_at_1=0.0, hot_s_at_2=0.0, hot_s_at_3=seconds, hot_share_reduced=0.0)
        toggles, observe = pd.DataFrame(columns=["s", "target", "kind", "line"]), None
    else:
        toggles, observe = rg
        toggles = toggles[(toggles["s"] >= 0) & (toggles["s"] <= seconds)] if len(toggles) else toggles
        counts = toggles["kind"].value_counts() if len(toggles) else pd.Series(dtype=int)
        row.update(rg_running=True,
                   rg_sheds=int(counts.get("ON→OFF", 0)),
                   rg_reenables=int(counts.get("OFF→ON", 0)),
                   rg_climbs=int(counts.get("1→2", 0) + counts.get("2→3", 0)))
        row["rg_acted"] = (row["rg_sheds"] + row["rg_reenables"] + row["rg_climbs"]) > 0
        grid = pd.Series(range(int(seconds)), dtype=float)
        level = attempts_at(observe, grid)
        for a in (0, 1, 2, 3):
            row[f"hot_s_at_{a}"] = float((level == a).sum())
        row["hot_share_reduced"] = float((level < 3).mean())

    # TopFull
    if tf is None or not len(tf):
        row.update(tf_running=False, tf_fresh_share=float("nan"), tf_acted=False)
        for api in CAP_APIS:
            row[f"cap_share_{api}"] = 0.0
        caps = None
    else:
        fresh = tf[tf["threshold_fresh"] == 1]
        any_fresh = fresh.groupby("s").size().index.to_series()
        row["tf_fresh_share"] = covered_seconds(any_fresh, seconds, CAP_CARRY_S) / seconds
        for api in CAP_APIS:
            live = tf[(tf["api"] == api) & tf["live"]]["s"]
            row[f"cap_share_{api}"] = covered_seconds(live, seconds, CAP_CARRY_S) / seconds
        row["tf_acted"] = bool(tf["live"].any())
        stale = fresh["s"].max() if len(fresh) else 0.0
        gaps = fresh["s"].drop_duplicates().sort_values().diff()
        row["tf_longest_blind_s"] = float(max(gaps.max() if len(gaps) else 0.0, seconds - stale))
        row["tf_running"] = True
        caps = tf

    # Hot edge by attempts level, settled seconds only
    by_level = []
    if row["rg_running"]:
        hot["attempts"] = attempts_at(observe, hot["s"]).values
        hot["settled"] = settled(observe, hot["s"]).values
        total["attempts"] = attempts_at(observe, total["s"]).values
        total["settled"] = settled(observe, total["s"]).values
        for a in (0, 1, 2, 3):
            h = hot[(hot["attempts"] == a) & hot["settled"]]
            l = total[(total["attempts"] == a) & total["settled"]]
            if h["dt"].sum() < 5:
                continue
            by_level.append({
                "cell": cell, "run": run, "hold": directory.name, "attempts": a,
                "seconds": float(h["dt"].sum()),
                "retry_rps": float(h["d_retry"].sum() / h["dt"].sum()),
                "rpr": float(h["d_retry"].sum() / max((h["d_total"] - h["d_retry"]).sum(), 1)),
                "goodput_rps": float(l["Goodput"].mean()) if len(l) else float("nan"),
                "p95_ms": float(l["Latency95"].mean()) if len(l) else float("nan"),
                "slo_miss": float(l["Fail"].sum() / l["RPS"].sum()) if len(l) and l["RPS"].sum() else float("nan"),
            })
    return row, by_level, {"total": total, "hot": hot, "toggles": toggles, "observe": observe, "caps": caps, "seconds": seconds}


def hold_figure(cell: str, run: int, name: str, series: dict, row: dict) -> go.Figure:
    total, hot, toggles, observe, caps = (series[k] for k in ("total", "hot", "toggles", "observe", "caps"))
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.3, 0.25, 0.2, 0.25],
        subplot_titles=(
            "Goodput (req/s) and P95 (ms, right axis)",
            "frontend → recommendationservice: retries per second",
            "RetryGuard attempts in force on that edge (3 = untouched)",
            "TopFull live cap per entry API (req/s); gaps = no cap or no fresh read",
        ),
        specs=[[{"secondary_y": True}], [{}], [{}], [{}]],
    )
    smooth = total.set_index("s")[["Goodput", "Latency95", "RPS"]].rolling(5, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=smooth.index, y=smooth["RPS"], name="offered RPS", line={"color": "#bbbbbb"}), row=1, col=1)
    fig.add_trace(go.Scatter(x=smooth.index, y=smooth["Goodput"], name="goodput", line={"color": COLORS[cell], "width": 2}), row=1, col=1)
    fig.add_trace(go.Scatter(x=smooth.index, y=smooth["Latency95"], name="P95", line={"color": "black", "width": 1, "dash": "dot"}),
                  row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=hot["s"], y=hot["retry_rps"], name="retries/s", line={"color": "#9467bd"}), row=2, col=1)
    if observe is not None and len(observe):
        steps = observe[observe["s"] >= 0]
        xs = [0.0] + steps["s"].tolist() + [series["seconds"]]
        level = attempts_at(observe, pd.Series([0.0])).iloc[0]
        ys = [level] + steps["attempts"].tolist() + [steps["attempts"].iloc[-1] if len(steps) else level]
        fig.add_trace(go.Scatter(x=xs, y=ys, name="attempts", mode="lines",
                                 line={"shape": "hv", "color": "#d62728"}), row=3, col=1)
    else:
        fig.add_annotation(text="RetryGuard off in this run (attempts fixed at 3)", row=3, col=1,
                           xref="x domain", yref="y domain", x=0.5, y=0.5, showarrow=False)
    if caps is not None:
        for api, color in zip(CAP_APIS, ("#17becf", "#bcbd22", "#8c564b")):
            live = caps[(caps["api"] == api) & caps["live"]]
            fig.add_trace(go.Scatter(x=live["s"], y=live["threshold"], name=f"cap {api}", mode="markers",
                                     marker={"size": 4, "color": color}), row=4, col=1)
        fresh = caps[caps["threshold_fresh"] == 1]["s"]
        if len(fresh):
            last = float(fresh.max())
            if series["seconds"] - last > 30:
                for r in (1, 2, 3, 4):
                    fig.add_vrect(x0=last, x1=series["seconds"], fillcolor="#ffdddd", opacity=0.35, line_width=0, row=r, col=1)
                fig.add_annotation(text=f"no fresh TopFull read after {last:.0f} s: cap unknown, not zero", row=4, col=1,
                                   x=last, xref="x", yref="y domain", y=1.0, xanchor="left", showarrow=False,
                                   font={"color": "#b00000", "size": 11})
    else:
        fig.add_annotation(text="TopFull off in this run", row=4, col=1,
                           xref="x domain", yref="y domain", x=0.5, y=0.5, showarrow=False)
    fig.update_xaxes(range=[0, series["seconds"]])
    for _, event in toggles.iterrows():
        if event["target"] != HOT and event["target"] != "recommendationservice":
            continue
        color = {"ON→OFF": "#d62728", "OFF→ON": "#2ca02c"}.get(event["kind"], "#ff7f0e")
        fig.add_vline(x=event["s"], line={"color": color, "width": 1, "dash": "dash"})
    fig.update_yaxes(title_text="req/s", row=1, col=1)
    fig.update_yaxes(title_text="ms", row=1, col=1, secondary_y=True)
    fig.update_yaxes(range=[-0.2, 3.3], dtick=1, row=3, col=1)
    fig.update_xaxes(title_text="hold clock (s since first Locust row)", row=4, col=1)
    fig.update_layout(height=900, template="simple_white", hovermode="x unified",
                      title=f"{name}   (RetryGuard {'acted' if row['rg_acted'] else ('idle' if row['rg_running'] else 'off')}, "
                            f"TopFull {'capped' if row['tf_acted'] else 'off'})",
                      legend={"orientation": "h", "y": -0.08})
    return fig


def outcome_figure(table: pd.DataFrame) -> go.Figure:
    metrics = [("goodput_rps", "Goodput (req/s)"), ("p95_ms", "P95 (ms)"), ("slo_miss", "SLO-miss (Fail/RPS)"),
               ("retries_per_1k_good", "Retries per 1000 good requests"), ("app_cpu_mc", "App CPU (millicores)")]
    fig = make_subplots(rows=len(metrics), cols=1, subplot_titles=[m[1] for m in metrics], vertical_spacing=0.05)
    labels = [f"{r.cell} r{r.run}<br>RG {'acted' if r.rg_acted else ('idle' if r.rg_running else 'off')} · "
              f"TF {'capped' if r.tf_acted else 'off'}" for r in table.itertuples()]
    for i, (metric, _) in enumerate(metrics, start=1):
        fig.add_trace(go.Bar(x=labels, y=table[metric], marker_color=[COLORS[c] for c in table["cell"]],
                             marker_pattern_shape=["/" if not acted and running else "" for acted, running in zip(table["rg_acted"], table["rg_running"])],
                             showlegend=False, hovertemplate="%{x}<br>%{y:,.3g}<extra></extra>"), row=i, col=1)
    fig.update_layout(height=1500, template="simple_white",
                      title="Outcomes per hold, labelled by what each controller actually did (hatched = RetryGuard running but never acted)")
    return fig


def attempts_figure(levels: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=3, subplot_titles=(
        "Hot-edge retries/s by attempts in force", "Goodput (req/s) in those seconds", "P95 (ms) in those seconds"))
    for hold, sub in levels.groupby("hold", sort=False):
        cell = sub["cell"].iloc[0]
        kw = {"name": hold, "legendgroup": hold, "marker": {"color": COLORS[cell], "size": 9},
              "line": {"color": COLORS[cell], "width": 1}, "mode": "lines+markers",
              "customdata": sub["seconds"], "hovertemplate": "attempts %{x}<br>%{y:,.1f}<br>%{customdata:.0f} s<extra>" + hold + "</extra>"}
        fig.add_trace(go.Scatter(x=sub["attempts"], y=sub["retry_rps"], **kw), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub["attempts"], y=sub["goodput_rps"], showlegend=False, **{k: v for k, v in kw.items() if k != "name"}), row=1, col=2)
        fig.add_trace(go.Scatter(x=sub["attempts"], y=sub["p95_ms"], showlegend=False, **{k: v for k, v in kw.items() if k != "name"}), row=1, col=3)
    fig.update_xaxes(dtick=1, title_text="attempts on frontend → recommendationservice")
    fig.update_layout(height=520, template="simple_white",
                      title="Inside one hold: what changed while RetryGuard held the hot edge at 0, 1, 2 or 3 attempts")
    return fig


EVENT_WINDOW = (-30, 60)


def event_windows(series: dict, kind: str, hold: str, cell: str) -> list[pd.DataFrame]:
    """Goodput, P95 and hot-edge retries/s on a common clock around each hot-edge toggle."""
    toggles = series["toggles"]
    if toggles is None or not len(toggles):
        return []
    events = toggles[(toggles["kind"] == kind) & toggles["target"].isin([HOT, HOT_CALLEE])]
    total = series["total"].set_index("s")
    hot = series["hot"].set_index("s")
    out = []
    for n, s0 in enumerate(events["s"]):
        lo, hi = s0 + EVENT_WINDOW[0], s0 + EVENT_WINDOW[1]
        if lo < 60 or hi > series["seconds"]:
            continue
        frame = pd.DataFrame({"rel": range(EVENT_WINDOW[0], EVENT_WINDOW[1] + 1)})
        grid = frame["rel"] + s0
        locust = total.loc[lo - 1:hi + 1, ["Goodput", "Latency95"]]
        mesh = hot.loc[lo - 3:hi + 3, ["retry_rps"]]
        frame["goodput"] = pd.Series(locust["Goodput"].values, index=locust.index).reindex(grid, method="nearest", tolerance=1.5).values
        frame["p95"] = pd.Series(locust["Latency95"].values, index=locust.index).reindex(grid, method="nearest", tolerance=1.5).values
        frame["retry_rps"] = pd.Series(mesh["retry_rps"].values, index=mesh.index).reindex(grid, method="nearest", tolerance=3).values
        frame["hold"], frame["cell"], frame["event"] = hold, cell, f"{hold} #{n + 1}"
        out.append(frame)
    return out


def event_figure(windows: list[pd.DataFrame], title: str) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=("Goodput (req/s)", "frontend → recommendationservice retries/s", "P95 (ms)"))
    if not windows:
        fig.add_annotation(text="no events far enough from the hold edges", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        return fig
    data = pd.concat(windows, ignore_index=True)
    for event, sub in data.groupby("event", sort=False):
        color = COLORS[sub["cell"].iloc[0]]
        for row, col in enumerate(("goodput", "retry_rps", "p95"), start=1):
            fig.add_trace(go.Scatter(x=sub["rel"], y=sub[col].rolling(5, min_periods=1, center=True).mean(),
                                     mode="lines", line={"color": color, "width": 1}, opacity=0.35,
                                     name=event, legendgroup=event, showlegend=row == 1), row=row, col=1)
    mean = data.groupby("rel")[["goodput", "retry_rps", "p95"]].mean().rolling(5, min_periods=1, center=True).mean()
    for row, col in enumerate(("goodput", "retry_rps", "p95"), start=1):
        fig.add_trace(go.Scatter(x=mean.index, y=mean[col], mode="lines", line={"color": "black", "width": 4},
                                 name=f"mean of {data['event'].nunique()} events", legendgroup="mean", showlegend=row == 1), row=row, col=1)
    fig.add_vline(x=0, line={"color": "#555", "dash": "dash"})
    fig.update_xaxes(title_text="seconds from the toggle", row=3, col=1)
    fig.update_layout(height=820, template="simple_white", hovermode="x unified", title=title)
    return fig


def event_summary(windows: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for frame in windows:
        before = frame[(frame["rel"] >= -25) & (frame["rel"] < -5)]
        after = frame[(frame["rel"] >= 5) & (frame["rel"] < 25)]
        rows.append({"event": frame["event"].iloc[0], "cell": frame["cell"].iloc[0],
                     "goodput_before": before["goodput"].mean(), "goodput_after": after["goodput"].mean(),
                     "retry_before": before["retry_rps"].mean(), "retry_after": after["retry_rps"].mean(),
                     "p95_before": before["p95"].mean(), "p95_after": after["p95"].mean()})
    return pd.DataFrame(rows)


def activation_table_html(table: pd.DataFrame) -> str:
    head = ("<tr><th>Hold</th><th>RetryGuard</th><th>sheds / re-enables / climbs</th><th>hot edge s at 0/1/2/3</th>"
            "<th>TopFull</th><th>fresh-read coverage</th><th>cap share postcheckout / getproduct / getcart</th>"
            "<th>checkout detector-hot</th></tr>")
    rows = []
    for r in table.itertuples():
        rg = "off" if not r.rg_running else ("<b>acted</b>" if r.rg_acted else "running, <b>never acted</b>")
        tf = "off" if not r.tf_running else ("<b>capped</b>" if r.tf_acted else "running, no cap")
        cover = "—" if not r.tf_running else f"{r.tf_fresh_share:.0%}"
        caps = "—" if not r.tf_running else f"{r.cap_share_postcheckout:.0%} / {r.cap_share_getproduct:.0%} / {r.cap_share_getcart:.0%}"
        rows.append(
            f"<tr><td>{html.escape(r.hold)}</td><td>{rg}</td><td>{r.rg_sheds} / {r.rg_reenables} / {r.rg_climbs}</td>"
            f"<td>{r.hot_s_at_0:.0f} / {r.hot_s_at_1:.0f} / {r.hot_s_at_2:.0f} / {r.hot_s_at_3:.0f}</td>"
            f"<td>{tf}</td><td>{cover}</td><td>{caps}</td><td>{r.checkout_overloaded:.0%}</td></tr>")
    return f"<table>{head}{''.join(rows)}</table>"


PAGE_STYLE = """
body { font-family: sans-serif; margin: 16px 24px; color: #222; }
table { border-collapse: collapse; font-size: 13px; margin: 8px 0 24px; }
th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; }
th { background: #f3f3f3; }
h2 { margin-top: 36px; }
p.note { color: #555; font-size: 13px; max-width: 1100px; }
details { margin: 8px 0; }
summary { cursor: pointer; font-weight: bold; padding: 4px 0; }
"""


def write_page(table: pd.DataFrame, levels: pd.DataFrame, series: dict, path: Path) -> None:
    parts = [f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>S2 by controller activation</title>"
             f"<style>{PAGE_STYLE}</style></head><body>",
             "<h1>S2 mode matrix, read by what each controller actually did</h1>",
             "<p class='note'>Ten locked holds (2026-10-14), 600 s each, mix 275/90/100/90/5, Paper-C1. "
             "A controller <b>acted</b> only when its actuator moved: RetryGuard changed attempts on an edge, "
             "or TopFull published a live cap (fresh read, 0 &lt; threshold &lt; 10000). Cap share counts a live read as covering the next 6 s. "
             "Fresh-read coverage below 100% means the collector could not read the TopFull proxy for part of the hold; "
             "caps in that time are unknown, not zero.</p>",
             "<h2>1. Activation per hold</h2>", activation_table_html(table),
             "<h2>2. Outcomes per hold</h2>"]
    include = True
    parts.append(pio.to_html(outcome_figure(table), full_html=False, include_plotlyjs=include))
    include = False
    parts.append("<h2>3. Inside the holds where RetryGuard acted</h2>"
                 "<p class='note'>Each point is the settled seconds (3 s after a change are dropped) while the hot edge "
                 "was at that attempts level. Same hold, same load, so this is the cleanest view of what the actuator does.</p>")
    parts.append(pio.to_html(attempts_figure(levels), full_html=False, include_plotlyjs=include))
    parts.append("<h2>4. Per-hold timelines</h2><p class='note'>Red dashed = shed, green dashed = re-enable, orange = climb. "
                 "Pink band = no fresh TopFull read. Click a hold to open it.</p>")
    for (cell, run, name), data in series.items():
        row = table[table["hold"] == name].iloc[0].to_dict()
        fig = hold_figure(cell, run, name, data, row)
        parts.append(f"<details><summary>{html.escape(name)}</summary>")
        parts.append(pio.to_html(fig, full_html=False, include_plotlyjs=include))
        parts.append("</details>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, levels, series = [], [], {}
    for cell, run, directory in holds():
        row, by_level, data = analyse_hold(cell, run, directory)
        rows.append(row)
        levels.extend(by_level)
        series[(cell, run, directory.name)] = data
    table = pd.DataFrame(rows)
    levels = pd.DataFrame(levels)
    table.to_csv(OUT / "activation.csv", index=False)
    levels.to_csv(OUT / "by_attempts.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(table[["hold", "rg_running", "rg_acted", "rg_sheds", "rg_reenables", "rg_climbs",
                 "hot_s_at_0", "hot_s_at_1", "hot_s_at_2", "hot_s_at_3",
                 "tf_acted", "tf_fresh_share", "cap_share_postcheckout", "cap_share_getproduct", "cap_share_getcart",
                 "checkout_overloaded"]].round(2).to_string(index=False))
    print()
    print(table[["hold", "goodput_rps", "slo_miss", "p95_ms", "retries_per_1k_good", "hot_retries",
                 "app_cpu_mc", "rec_cpu_mc", "checkout_cpu_mc"]].round(3).to_string(index=False))
    print()
    print(levels.round(3).to_string(index=False))
    for kind in ("ON→OFF", "OFF→ON"):
        windows = [w for (cell, run, name), data in series.items() for w in event_windows(data, kind, name, cell)]
        summary = event_summary(windows)
        summary.to_csv(OUT / f"events_{'shed' if kind == 'ON→OFF' else 'reenable'}.csv", index=False)
        print(f"\n{kind}: {len(summary)} events, 5-25 s after vs 25-5 s before")
        print(summary.round(1).to_string(index=False))
        print(summary[["goodput_before", "goodput_after", "retry_before", "retry_after", "p95_before", "p95_after"]].mean().round(1).to_string())
    for name in ("final_s2_tf_only_run2", "final_s2_both_burst_run1", "final_s2_both_burst_run2"):
        data = next(d for (c, r, n), d in series.items() if n == name)
        fresh = data["caps"][data["caps"]["threshold_fresh"] == 1]["s"]
        cut = float(fresh[fresh < data["seconds"] - 30].max())
        total = data["total"]
        before = total[(total["s"] > 60) & (total["s"] < cut)]
        after = total[total["s"] > cut + 10]
        print(f"{name}: last fresh read at {cut:.0f} s; goodput {before['Goodput'].mean():.0f} before, {after['Goodput'].mean():.0f} after;"
              f" P95 {before['Latency95'].mean():.0f} / {after['Latency95'].mean():.0f}")
    write_page(table, levels, series, OUT / "s2_activation.html")
    print(OUT / "s2_activation.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
