# Hold Clock and Run Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put every metric of a run on one shared clock (the hold clock), so all collectors can be read and plotted together second by second.

**Architecture:** `experiments/hold_clock.py` fits (or reads) each run's Locust clock, writes `locust_clock.json`, and loads any source with a `hold_s` column added. `experiments/run_timeline.py` builds the per-second view from those sources and draws `timeline.png`. New holds get real Locust timestamps from a patch to TopFull's `metric_collector.py` on master plus `locust_started_at` in `run_manifest.json`, and `pull_results.py` builds the timeline after each pull.

**Tech Stack:** Python 3.11+ locally (pandas 3.0.5, numpy 2.4.6, matplotlib 3.11 already installed), `unittest` tests run with `python -m pytest`. Master runs Python 3.8 for `metric_collector.py`.

Spec: [docs/superpowers/specs/2026-10-13-hold-clock-design.md](../specs/2026-10-13-hold-clock-design.md). Glossary terms: **Hold clock**, **Locust clock fit** in [CONTEXT.md](../../../CONTEXT.md).

## Global Constraints

- Scope is runs under `experiments/results/final results/` only. `campaign_48/` and `august_38/` are not touched.
- Hold clock: seconds since the first Locust row, in master's UTC. Rows before load starts keep negative `hold_s`.
- Raw run files are never modified. The only new files in a run folder are `locust_clock.json` (committed), `timeline.png` (committed), and `timeline_1s.csv` (gitignored, written only with `--csv`).
- Locust clock fit anchors: the first and last value above **20%** of the median positive value (`LOAD_FRACTION = 0.2`), in Locust `total.csv` `RPS` and in the frontend inbound rate from `service_inbound.csv`. Rows are spread evenly between the anchors.
- Correlation check: Locust `RPS` against the frontend inbound rate at the Locust row times; `flagged` when below **0.8** or not computable.
- Stamped runs (Locust CSVs with a `timestamp` column) use the stamps as truth and record the fit's error against them in `fit_check`.
- Per-second rules: Locust rows averaged when two land in one second. Running totals become rate = Δ/Δt at the later poll's second; a gap is never split or zero-filled, and a counter that went down drops that gap. Current readings are carried forward at most **6 s** for throttle-collector readings (cap, admitted RPS, detector) and **5 s** for `resource_usage.csv` readings (CPU, memory, replicas). A fresh cap of **10000** is no cap and ends a carry; a fresh **0** is an empty read and does not end it. RetryGuard switches are exact-time events. Empty means no sample, never 0. Every value column has a `<column>__carried` companion: 0 measured, 1 carried, empty when the value is empty.
- Rejection uses the controller formula: `(Δ5xx + Δresets) / Δtotal`, plus `Δgrpc_4 + Δgrpc_14` on `adservice`, `currencyservice`, `productcatalogservice`, `recommendationservice`. Δtotal ≤ 0 is empty.
- Chart panels, top to bottom: (1) Locust total goodput and `RPS`, (2) Locust total P95, (3) TopFull cap per API where a cap is applied, (4) rejection for services with any rejection above 0, (5) retries per request for RetryGuard's 14 edges that have any retry, (6) CPU for every service (`__master_node__` is the master VM, not a service, and stays out of the panel). `--all` shows every service in panel 4 and all 14 edges in panel 5. An empty panel says "none in this run". Vertical lines at each RetryGuard switch. On S2 runs, escape time (first-mesh-poll definition, `s2_latch_escape.py`) is drawn converted to the hold clock.
- The chart connects measured points across gaps of at most **3 s** (mesh polls are often 2 s apart); longer gaps break the line. The CSV keeps the empty seconds.
- `pull_results.py` builds the timeline after a pull; a failure only prints a warning.
- Tests: one test per rule that could go wrong silently (the fit, the per-second rules, panel selection, the master patch, the manifest field, the pull hook). No tests for argument parsing, trivial helpers, or plot styling.
- Master access uses the SSH alias `topfull-master`, never IPs. Do not patch master while a hold is running.
- Code comments only state constraints the code can't show.

---

## File structure

| File | Responsibility |
|---|---|
| Create `experiments/hold_clock.py` | UTC parsing, Locust clock fit, `locust_clock.json`, `load_source()` with `hold_s`, run-folder discovery, CLI |
| Create `experiments/test_hold_clock.py` | Fit, stamped, loader tests (also exports the `make_run` and `write_csv` fixtures) |
| Create `experiments/run_timeline.py` | Per-second view, panel selection, chart, `build()`, CLI |
| Create `experiments/test_run_timeline.py` | Per-second rules, panel rules, build smoke test |
| Modify `experiments/patch_metric_collector.py` | Second, idempotent stage that adds the `timestamp` column |
| Create `experiments/test_patch_metric_collector.py` | One patch test |
| Modify `experiments/run_scenario.py` (`start_locust` ~L1202, `collect_results` ~L1436, run body ~L1564–1621) | `master_utc_now()`, `locust_started_at` in the manifest |
| Modify `experiments/test_run_scenario.py` (~L232–240, after ~L927) | Keep the `start_locust` test off real SSH; one manifest test |
| Modify `experiments/pull_results.py` | Call `run_timeline.build()` after a pull |
| Create `experiments/test_pull_results.py` | One pull-hook test |
| Modify `.gitignore`, `Guides and Info/METRICS-GATHERED.md`, `AGENTS.md`, `STATUS.md` | Ignore the CSV, fix the clock section, link the tool, Done bullet |

---

### Task 1: Locust clock fit and `locust_clock.json`

**Files:**
- Create: `experiments/hold_clock.py`
- Test: `experiments/test_hold_clock.py`

**Interfaces:**
- Produces:
  - `parse_utc(value: str) -> float`, `format_utc(epoch: float) -> str` (`YYYY-MM-DDTHH:MM:SS.mmmZ`)
  - `read_csv(path: Path) -> pd.DataFrame` (empty frame when missing or empty), `epochs(column: pd.Series) -> np.ndarray`
  - `compute_clock(run_dir) -> dict`, `write_clock(run_dir) -> dict`, `read_clock(run_dir) -> dict`, `zero_epoch(clock) -> float`
  - `run_dirs(paths: list[str], tree: str | None) -> list[Path]`
  - Constants `CLOCK_JSON`, `LOCUST_FILES`, `COLLECTOR_FILES`, `LOAD_FRACTION`, `MIN_CORRELATION`
  - Clock dict keys: `method` (`"fit"` or `"stamped"`), `start_utc`, `spacing_s`, `rows`, `correlation`, `flagged`; fit adds `anchor_rows`, `anchor_utc`; stamped adds `fit_check` (`start_error_s`, `anchor_errors_s`, `spacing_s`, or `None`)
  - Test fixtures `E`, `write_csv(path, header, rows)`, `make_run(root, stamped=False) -> Path` in `test_hold_clock.py`

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_hold_clock.py`:

```python
"""Unit tests for experiments/hold_clock.py."""
import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402

E = 1_760_000_000.0
LOCUST_HEADER = ["RPS", "Fail", "Goodput", "Latency95", "Latency99"]


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def frontend_total(epoch: float) -> float:
    """Cumulative frontend requests: load on from E+20 to E+80, rate 50 + (t - E - 20)."""
    x = min(max(epoch - E - 20, 0.0), 60.0)
    return 50 * x + 0.5 * x * x


def make_run(root: Path, stamped: bool = False) -> Path:
    """Synthetic run: 1 s mesh polls E..E+100, 55 Locust rows 1.1 s apart from E+20."""
    run = root / "run"
    write_csv(run / "service_inbound.csv",
              ["timestamp", "service", "total", "2xx", "5xx", "resets"],
              [[iso(E + k), "frontend", frontend_total(E + k), frontend_total(E + k), 0, 0]
               for k in range(101)])
    rows = []
    for i in range(55):
        rps = 50 + 1.1 * i
        row = [rps, 0, rps, 100, 0]
        if stamped:
            row.append(hold_clock.format_utc(E + 20 + 1.1 * i))
        rows.append(row)
    header = LOCUST_HEADER + (["timestamp"] if stamped else [])
    for name in hold_clock.LOCUST_FILES:
        write_csv(run / f"{name}.csv", header, rows)
    return run


class TestFit(unittest.TestCase):
    def test_fit_recovers_start_and_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = hold_clock.compute_clock(make_run(Path(tmp)))
        self.assertEqual(clock["method"], "fit")
        self.assertEqual(clock["anchor_rows"], [0, 54])
        start = hold_clock.parse_utc(clock["start_utc"])
        self.assertLessEqual(abs(start - (E + 20)), 1.5)
        self.assertLess(abs(clock["spacing_s"] - 1.1), 0.01)
        self.assertGreater(clock["correlation"], 0.99)
        self.assertFalse(clock["flagged"])

    def test_stamped_run_uses_stamps_and_records_fit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = hold_clock.compute_clock(make_run(Path(tmp), stamped=True))
        self.assertEqual(clock["method"], "stamped")
        self.assertEqual(clock["start_utc"], hold_clock.format_utc(E + 20))
        self.assertAlmostEqual(clock["spacing_s"], 1.1, delta=0.002)
        self.assertLessEqual(abs(clock["fit_check"]["start_error_s"]), 1.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_hold_clock.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hold_clock'`

- [ ] **Step 3: Write the implementation**

Create `experiments/hold_clock.py`:

```python
"""Hold clock for one run folder.

The hold clock is seconds since the first Locust row, in master's UTC.
Locust CSVs from before the timestamp patch have no clock column, so each
run gets a Locust clock fit: a start time plus a row spacing, anchored on
the first and last moment load is above 20% of its median in both Locust
RPS and the frontend inbound rate. Design:
docs/superpowers/specs/2026-10-13-hold-clock-design.md.

    python experiments/hold_clock.py <run_dir> [<run_dir> ...]
    python experiments/hold_clock.py --tree "experiments/results/final results"

Writes locust_clock.json into each run folder and prints one line per run.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

CLOCK_JSON = "locust_clock.json"
LOCUST_FILES = ("total", "getproduct", "postcheckout", "getcart", "postcart", "emptycart")
COLLECTOR_FILES = (
    "service_inbound",
    "service_edges",
    "resource_usage",
    "topfull_throttle",
    "topfull_detect",
)
LOAD_FRACTION = 0.2
MIN_CORRELATION = 0.8


def parse_utc(value: str) -> float:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def format_utc(epoch: float) -> str:
    moment = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def epochs(column: pd.Series) -> np.ndarray:
    text = column.astype(str)
    lookup = {value: parse_utc(value) for value in text.unique()}
    return text.map(lookup).to_numpy(dtype=float)


def frontend_rate(inbound: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Frontend inbound arrival rate per poll gap, stamped at the later poll."""
    rows = inbound[inbound["service"] == "frontend"]
    t = epochs(rows["timestamp"])
    total = rows["total"].to_numpy(dtype=float)
    order = np.argsort(t, kind="stable")
    t, total = t[order], total[order]
    dt = np.diff(t)
    delta = np.diff(total)
    keep = (dt > 0) & (delta >= 0)
    return t[1:][keep], delta[keep] / dt[keep]


def load_span(values: np.ndarray) -> tuple[int, int] | None:
    positive = values[values > 0]
    if positive.size == 0:
        return None
    above = np.flatnonzero(values > LOAD_FRACTION * np.median(positive))
    if above.size < 2:
        return None
    return int(above[0]), int(above[-1])


def fit_from_anchors(
    locust_rps: np.ndarray, mesh_t: np.ndarray, mesh_rate: np.ndarray
) -> dict | None:
    rows = load_span(locust_rps)
    mesh = load_span(mesh_rate)
    if rows is None or mesh is None or rows[1] == rows[0]:
        return None
    first_t, last_t = float(mesh_t[mesh[0]]), float(mesh_t[mesh[1]])
    spacing = (last_t - first_t) / (rows[1] - rows[0])
    return {
        "start_epoch": first_t - rows[0] * spacing,
        "spacing_s": spacing,
        "anchor_rows": [rows[0], rows[1]],
        "anchor_epochs": [first_t, last_t],
    }


def correlation(
    locust_rps: np.ndarray, row_epochs: np.ndarray, mesh_t: np.ndarray, mesh_rate: np.ndarray
) -> float | None:
    if mesh_t.size < 2:
        return None
    inside = (row_epochs >= mesh_t[0]) & (row_epochs <= mesh_t[-1])
    if inside.sum() < 3:
        return None
    a = locust_rps[inside]
    b = np.interp(row_epochs[inside], mesh_t, mesh_rate)
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _flagged(corr: float | None) -> bool:
    return corr is None or corr < MIN_CORRELATION


def compute_clock(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    total = read_csv(run_dir / "total.csv")
    inbound = read_csv(run_dir / "service_inbound.csv")
    if total.empty:
        raise ValueError(f"{run_dir}: total.csv missing or empty")
    if inbound.empty:
        raise ValueError(f"{run_dir}: service_inbound.csv missing or empty")
    rps = total["RPS"].to_numpy(dtype=float)
    mesh_t, mesh_rate = frontend_rate(inbound)
    fit = fit_from_anchors(rps, mesh_t, mesh_rate)

    if "timestamp" in total.columns:
        stamps = epochs(total["timestamp"])
        corr = correlation(rps, stamps, mesh_t, mesh_rate)
        check = None
        if fit is not None:
            first_row, last_row = fit["anchor_rows"]
            check = {
                "start_error_s": float(fit["start_epoch"] - stamps[0]),
                "anchor_errors_s": [
                    float(fit["anchor_epochs"][0] - stamps[first_row]),
                    float(fit["anchor_epochs"][1] - stamps[last_row]),
                ],
                "spacing_s": float(fit["spacing_s"]),
            }
        return {
            "method": "stamped",
            "start_utc": format_utc(stamps[0]),
            "spacing_s": float(np.median(np.diff(stamps))) if stamps.size > 1 else None,
            "rows": int(stamps.size),
            "correlation": corr,
            "flagged": _flagged(corr),
            "fit_check": check,
        }

    if fit is None:
        raise ValueError(f"{run_dir}: no load start/stop found to anchor the fit")
    row_epochs = fit["start_epoch"] + np.arange(rps.size) * fit["spacing_s"]
    corr = correlation(rps, row_epochs, mesh_t, mesh_rate)
    return {
        "method": "fit",
        "start_utc": format_utc(fit["start_epoch"]),
        "spacing_s": float(fit["spacing_s"]),
        "rows": int(rps.size),
        "anchor_rows": fit["anchor_rows"],
        "anchor_utc": [format_utc(e) for e in fit["anchor_epochs"]],
        "correlation": corr,
        "flagged": _flagged(corr),
    }


def write_clock(run_dir: Path) -> dict:
    clock = compute_clock(run_dir)
    (Path(run_dir) / CLOCK_JSON).write_text(json.dumps(clock, indent=2) + "\n", encoding="utf-8")
    return clock


def read_clock(run_dir: Path) -> dict:
    path = Path(run_dir) / CLOCK_JSON
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return write_clock(run_dir)


def zero_epoch(clock: dict) -> float:
    return parse_utc(clock["start_utc"])


def run_dirs(paths: list[str], tree: str | None) -> list[Path]:
    found = [Path(p) for p in paths]
    if tree:
        found += sorted(p.parent for p in Path(tree).rglob("total.csv"))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write locust_clock.json for run folders.")
    parser.add_argument("runs", nargs="*", help="Run folders")
    parser.add_argument("--tree", help="Every folder under this path that has total.csv")
    args = parser.parse_args(argv)
    failures = 0
    for run in run_dirs(args.runs, args.tree):
        try:
            clock = write_clock(run)
        except ValueError as exc:
            print(f"{run.name}: ERROR {exc}")
            failures += 1
            continue
        corr = clock["correlation"]
        corr_text = "n/a" if corr is None else f"{corr:.3f}"
        print(
            f"{run.name}: {clock['method']} start={clock['start_utc']} "
            f"spacing={clock['spacing_s']:.4f}s corr={corr_text} "
            f"{'FLAGGED' if clock['flagged'] else 'ok'}"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_hold_clock.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add experiments/hold_clock.py experiments/test_hold_clock.py
git commit -m "feat(hold-clock): fit the Locust clock per run and write locust_clock.json"
```

---

### Task 2: `load_source()` with `hold_s`, including `retryguard.log`

**Files:**
- Modify: `experiments/hold_clock.py`
- Test: `experiments/test_hold_clock.py`

**Interfaces:**
- Consumes: Task 1 `read_csv`, `epochs`, `parse_utc`, `read_clock`, `zero_epoch`, `LOCUST_FILES`, `COLLECTOR_FILES`.
- Produces:
  - `locust_epochs(df: pd.DataFrame, clock: dict) -> np.ndarray`
  - `retryguard_rows(text: str) -> pd.DataFrame` with columns `timestamp`, `line`, `kind` (`"OBSERVE"`, `"switch"`, or the log word such as `"START"`), `name` (edge or service when present), `step` (switches only, `→` form), plus every `key=value` field as a string column
  - `load_source(run_dir, name: str, clock: dict | None = None) -> pd.DataFrame` — `name` is one of `LOCUST_FILES`, `COLLECTOR_FILES`, or `"retryguard"`; returns the raw rows and columns plus `hold_s` (NaN when a log timestamp can't be parsed); empty frame when the file is missing; `ValueError` for an unknown name

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_hold_clock.py` (above the `if __name__` block):

```python
RG_LOG = "\n".join([
    "2026-10-12T13:09:01Z  START  metric=edge_rpr rpr_threshold=0.40",
    "2026-10-12T13:09:28Z  OBSERVE  frontend->cartservice  rpr=0.5000  attempts=3  state=ON",
    "2026-10-12T13:09:29Z  frontend->checkoutservice  ON→OFF   rpr=2.10  metric=rpr_burst",
    "2026-10-12T13:09:30Z  checkoutservice  OFF->ON   rejection=0.00  metric=rejection",
])


class TestLoadSource(unittest.TestCase):
    def test_retryguard_rows_kinds_and_fields(self):
        rows = hold_clock.retryguard_rows(RG_LOG)
        self.assertEqual(list(rows["kind"]), ["START", "OBSERVE", "switch", "switch"])
        self.assertEqual(rows.loc[1, "name"], "frontend->cartservice")
        self.assertEqual(rows.loc[1, "rpr"], "0.5000")
        self.assertEqual(list(rows.loc[2:3, "step"]), ["ON→OFF", "OFF→ON"])
        self.assertEqual(rows.loc[2, "metric"], "rpr_burst")

    def test_sources_get_hold_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            clock = hold_clock.write_clock(run)
            locust = hold_clock.load_source(run, "getcart", clock)
            inbound = hold_clock.load_source(run, "service_inbound", clock)
            missing = hold_clock.load_source(run, "topfull_throttle", clock)
        self.assertEqual(locust["hold_s"].iloc[0], 0.0)
        self.assertAlmostEqual(locust["hold_s"].iloc[10], 10 * clock["spacing_s"], places=6)
        self.assertEqual(list(locust.columns), LOCUST_HEADER + ["hold_s"])
        self.assertAlmostEqual(inbound["hold_s"].iloc[0], E - hold_clock.zero_epoch(clock), places=6)
        self.assertLess(inbound["hold_s"].iloc[0], 0)
        self.assertTrue(missing.empty)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_hold_clock.py -v -k LoadSource`
Expected: FAIL with `AttributeError: module 'hold_clock' has no attribute 'retryguard_rows'`

- [ ] **Step 3: Write the implementation**

Add to `experiments/hold_clock.py` after `zero_epoch`:

```python
def locust_epochs(df: pd.DataFrame, clock: dict) -> np.ndarray:
    if "timestamp" in df.columns:
        return epochs(df["timestamp"])
    return zero_epoch(clock) + np.arange(len(df)) * float(clock["spacing_s"])


def _safe_epoch(value: str) -> float:
    try:
        return parse_utc(value)
    except ValueError:
        return float("nan")


def retryguard_rows(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        row = {"timestamp": parts[0], "line": line}
        if parts[1] == "OBSERVE" and len(parts) >= 3:
            row.update(kind="OBSERVE", name=parts[2])
            fields = parts[3:]
        elif len(parts) >= 3 and ("→" in parts[2] or "->" in parts[2]):
            row.update(kind="switch", name=parts[1], step=parts[2].replace("->", "→"))
            fields = parts[3:]
        else:
            row["kind"] = parts[1]
            fields = parts[2:]
        for token in fields:
            if "=" in token:
                key, value = token.split("=", 1)
                row.setdefault(key, value)
        rows.append(row)
    return pd.DataFrame(rows)


def load_source(run_dir: Path, name: str, clock: dict | None = None) -> pd.DataFrame:
    run_dir = Path(run_dir)
    clock = clock or read_clock(run_dir)
    zero = zero_epoch(clock)
    if name in LOCUST_FILES:
        df = read_csv(run_dir / f"{name}.csv")
        if not df.empty:
            df["hold_s"] = locust_epochs(df, clock) - zero
        return df
    if name in COLLECTOR_FILES:
        df = read_csv(run_dir / f"{name}.csv")
        if not df.empty:
            df["hold_s"] = epochs(df["timestamp"]) - zero
        return df
    if name == "retryguard":
        path = run_dir / "retryguard.log"
        if not path.is_file():
            return pd.DataFrame()
        df = retryguard_rows(path.read_text(encoding="utf-8", errors="replace"))
        if not df.empty:
            df["hold_s"] = df["timestamp"].map(_safe_epoch) - zero
        return df
    raise ValueError(f"unknown source {name!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_hold_clock.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add experiments/hold_clock.py experiments/test_hold_clock.py
git commit -m "feat(hold-clock): load any run source with a hold_s column"
```

---

### Task 3: Per-second view

**Files:**
- Create: `experiments/run_timeline.py`
- Test: `experiments/test_run_timeline.py`

**Interfaces:**
- Consumes: Tasks 1–2 `hold_clock.load_source`, `read_clock`, `format_utc`, `LOCUST_FILES`; `analysis_score.GRPC_CALLEES`.
- Produces:
  - `per_second_view(run_dir, clock: dict | None = None) -> pd.DataFrame` — index `hold_s` (int seconds, contiguous), value columns plus `<col>__carried`
  - Column names: `locust.<file>.<RPS|Fail|Goodput|Latency95|Latency99>`; `inbound.<service>.<counter>_per_s`, `inbound.<service>.rejection`, `inbound.<service>.sojourn_ms`; `edge.<caller>-><target>.<counter>_per_s`, `edge.<caller>-><target>.rpr`, `edge.<caller>-><target>.sojourn_ms`; `throttle.<api>.cap`, `throttle.<api>.admitted_rps`; `detect.<service>.<cadvisor_cpu|quota|alpha|utilization|overloaded>`; `resource.<service>.<cpu_millicores|memory_working_set_bytes|replica_count>`; `rg.<name>.<rpr|rejection|attempts|high|low|burst_rpr5>`; `rg.switches` (text, `"<name> <step>"` joined by `"; "`)
  - `switch_events(run_dir, clock: dict) -> pd.DataFrame` with columns `hold_s`, `name`, `step`
  - `select_columns(view, patterns: list[str] | None) -> pd.DataFrame` (keeps each matching column with its flag)
  - Constants `FLAG = "__carried"`, `CONTROLLED_EDGES`, `THROTTLE_CARRY_S = 6`, `RESOURCE_CARRY_S = 5`, `NO_CAP = 10000.0`

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_run_timeline.py`:

```python
"""Unit tests for experiments/run_timeline.py."""
import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hold_clock  # noqa: E402
import run_timeline  # noqa: E402
from test_hold_clock import write_csv  # noqa: E402

E = 1_760_000_000.0
CLOCK = {"method": "fit", "start_utc": hold_clock.format_utc(E), "spacing_s": 0.6, "rows": 4}
FLAG = run_timeline.FLAG


def iso(seconds_after: float) -> str:
    return datetime.fromtimestamp(E + seconds_after, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


class TestPerSecondView(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.run = Path(self._tmp.name) / "run"
        self.run.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def view(self):
        return run_timeline.per_second_view(self.run, CLOCK)

    def test_two_locust_rows_in_one_second_are_averaged(self):
        write_csv(self.run / "total.csv", ["RPS", "Fail", "Goodput", "Latency95", "Latency99"],
                  [[10, 0, 10, 1, 0], [20, 0, 20, 1, 0], [30, 0, 30, 1, 0], [40, 0, 40, 1, 0]])
        view = self.view()
        self.assertEqual(view.loc[0, "locust.total.RPS"], 15)
        self.assertEqual(view.loc[1, "locust.total.RPS"], 35)
        self.assertEqual(view.loc[0, "locust.total.RPS" + FLAG], 0)

    def test_counter_rates_gaps_resets_and_rejection(self):
        header = ["timestamp", "service", "total", "2xx", "5xx", "resets", "grpc_4", "grpc_14"]
        write_csv(self.run / "service_inbound.csv", header, [
            [iso(0), "recommendationservice", 0, 0, 0, 0, 0, 0],
            [iso(1), "recommendationservice", 10, 9, 1, 0, 1, 1],
            [iso(3), "recommendationservice", 30, 29, 1, 0, 1, 1],
            [iso(0), "cartservice", 0, 0, 0, 0, 0, 0],
            [iso(1), "cartservice", 10, 9, 1, 0, 1, 1],
            [iso(2), "cartservice", 5, 5, 1, 0, 1, 1],
        ])
        view = self.view()
        recs = "inbound.recommendationservice"
        self.assertEqual(view.loc[1, f"{recs}.total_per_s"], 10)
        self.assertTrue(empty(view.loc[2, f"{recs}.total_per_s"]))
        self.assertTrue(empty(view.loc[2, f"{recs}.total_per_s" + FLAG]))
        self.assertEqual(view.loc[3, f"{recs}.total_per_s"], 10)
        self.assertAlmostEqual(view.loc[1, f"{recs}.rejection"], 0.3)
        self.assertEqual(view.loc[3, f"{recs}.rejection"], 0.0)
        self.assertAlmostEqual(view.loc[1, "inbound.cartservice.rejection"], 0.1)
        self.assertTrue(empty(view.loc[2, "inbound.cartservice.total_per_s"]))

    def test_cap_carry_rules(self):
        header = ["timestamp", "api", "threshold", "admitted_rps", "threshold_fresh", "admitted_fresh"]
        rows = [
            [iso(0), "getproduct", 300, 0, 1, 0],
            [iso(1), "getproduct", 0, 0, 1, 0],
            [iso(2), "getproduct", 0, 0, 0, 0],
            [iso(3), "getproduct", 10000, 0, 1, 0],
            [iso(4), "getproduct", 0, 0, 0, 0],
            [iso(0), "getcart", 300, 0, 1, 0],
        ]
        rows += [[iso(s), "getcart", 0, 0, 0, 0] for s in range(1, 10)]
        write_csv(self.run / "topfull_throttle.csv", header, rows)
        view = self.view()
        cap = "throttle.getproduct.cap"
        self.assertEqual((view.loc[0, cap], view.loc[0, cap + FLAG]), (300, 0))
        self.assertEqual((view.loc[1, cap], view.loc[1, cap + FLAG]), (300, 1))
        self.assertEqual(view.loc[2, cap], 300)
        self.assertTrue(empty(view.loc[3, cap]))
        self.assertTrue(empty(view.loc[4, cap]))
        self.assertEqual(view.loc[6, "throttle.getcart.cap"], 300)
        self.assertTrue(empty(view.loc[7, "throttle.getcart.cap"]))

    def test_retryguard_observe_and_switches(self):
        (self.run / "retryguard.log").write_text("\n".join([
            f"{iso(1)}  OBSERVE  frontend->checkoutservice  rpr=0.5000  attempts=3  state=ON",
            f"{iso(2)}  frontend->checkoutservice  ON→OFF   rpr=2.10  metric=rpr_burst",
        ]), encoding="utf-8")
        view = self.view()
        self.assertEqual(view.loc[1, "rg.frontend->checkoutservice.rpr"], 0.5)
        self.assertEqual(view.loc[2, "rg.switches"], "frontend->checkoutservice ON→OFF")
        events = run_timeline.switch_events(self.run, CLOCK)
        self.assertEqual(events["hold_s"].iloc[0], 2.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_run_timeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'run_timeline'`

- [ ] **Step 3: Write the implementation**

Create `experiments/run_timeline.py`:

```python
"""Per-second view and stacked chart for one run, on the hold clock.

    python experiments/run_timeline.py <run_dir> [<run_dir> ...] [--all] [--csv] [--columns PATTERN ...]
    python experiments/run_timeline.py --tree "experiments/results/final results"

Writes locust_clock.json and timeline.png into each run folder. --csv also
writes timeline_1s.csv, which is not committed. Rules for one second:
docs/superpowers/specs/2026-10-13-hold-clock-design.md (the Q5 table).
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_score  # noqa: E402
import hold_clock  # noqa: E402

PNG_NAME = "timeline.png"
CSV_NAME = "timeline_1s.csv"
FLAG = "__carried"
NO_CAP = 10000.0
THROTTLE_CARRY_S = 6
RESOURCE_CARRY_S = 5
LOCUST_COLUMNS = ("RPS", "Fail", "Goodput", "Latency95", "Latency99")
INBOUND_COUNTERS = (
    "total", "2xx", "4xx", "5xx", "resets",
    "grpc_2", "grpc_4", "grpc_13", "grpc_14",
    "rq_time_sum_ms", "rq_time_count",
)
EDGE_COUNTERS = ("total", "2xx", "4xx", "5xx", "retry", "rq_time_sum_ms", "rq_time_count")
DETECT_READINGS = ("cadvisor_cpu", "quota", "alpha", "utilization", "overloaded")
RESOURCE_READINGS = ("cpu_millicores", "memory_working_set_bytes", "replica_count")
RG_NUMERIC_FIELDS = ("rpr", "rejection", "attempts", "high", "low", "burst_rpr5")

# Keep in step with retryguard.CONTROLLED_EDGES (retryguard imports kubernetes,
# so it is not imported here).
CONTROLLED_EDGES = (
    ("frontend", "adservice"),
    ("frontend", "cartservice"),
    ("frontend", "checkoutservice"),
    ("frontend", "currencyservice"),
    ("frontend", "productcatalogservice"),
    ("frontend", "recommendationservice"),
    ("frontend", "shippingservice"),
    ("checkoutservice", "cartservice"),
    ("checkoutservice", "currencyservice"),
    ("checkoutservice", "emailservice"),
    ("checkoutservice", "paymentservice"),
    ("checkoutservice", "productcatalogservice"),
    ("checkoutservice", "shippingservice"),
    ("recommendationservice", "productcatalogservice"),
)


def seconds(hold_s) -> np.ndarray:
    return np.floor(np.asarray(hold_s, dtype=float)).astype(int)


def label(key) -> str:
    return "->".join(key) if isinstance(key, tuple) else str(key)


def measured(secs: np.ndarray, values, name: str) -> pd.DataFrame:
    series = pd.Series(np.asarray(values, dtype=float), index=secs)
    return series.groupby(level=0).mean().rename(name).to_frame()


def ratio(num, den) -> np.ndarray:
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    out = np.full(num.shape, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def carried(secs: np.ndarray, values, name: str, limit: int, ends=None) -> pd.DataFrame:
    """Latest reading per second, carried forward at most `limit` seconds.
    A NaN value is no reading. `ends` marks readings that clear the carry."""
    values = np.asarray(values, dtype=float)
    ends = np.zeros(values.size, dtype=bool) if ends is None else np.asarray(ends, dtype=bool)
    frame = pd.DataFrame({"value": values, "end": ends}, index=secs)
    last = frame["value"].groupby(level=0).last()
    ended = frame["end"].groupby(level=0).any()
    grid = np.arange(int(secs.min()), int(secs.max()) + limit + 1)
    out_value = np.full(grid.size, np.nan)
    out_flag = np.full(grid.size, np.nan)
    current, since = np.nan, None
    for i, sec in enumerate(grid):
        reading = last.get(sec, np.nan)
        if not np.isnan(reading):
            current, since = reading, sec
            out_value[i], out_flag[i] = reading, 0.0
            continue
        if bool(ended.get(sec, False)):
            current, since = np.nan, None
            continue
        if since is not None and sec - since <= limit:
            out_value[i], out_flag[i] = current, 1.0
    return pd.DataFrame({name: out_value, name + FLAG: out_flag}, index=grid)


def poll_deltas(group: pd.DataFrame, columns) -> tuple[np.ndarray, np.ndarray, dict]:
    """Deltas between consecutive polls, at the later poll's second.
    Gaps with a non-positive dt or any counter that went down are dropped."""
    group = group.sort_values("hold_s")
    t = group["hold_s"].to_numpy(dtype=float)
    dt = np.diff(t)
    deltas = {c: np.diff(group[c].to_numpy(dtype=float)) for c in columns}
    keep = dt > 0
    for delta in deltas.values():
        keep &= delta >= 0
    return seconds(t[1:])[keep], dt[keep], {c: d[keep] for c, d in deltas.items()}


def _counters(group: pd.DataFrame, names) -> list[str]:
    return [c for c in names if c in group.columns and group[c].notna().all()]


def locust_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    frames = []
    for name in hold_clock.LOCUST_FILES:
        df = hold_clock.load_source(run_dir, name, clock)
        if df.empty:
            continue
        secs = seconds(df["hold_s"])
        for column in LOCUST_COLUMNS:
            if column in df.columns:
                frames.append(measured(secs, df[column], f"locust.{name}.{column}"))
    return frames


def inbound_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "service_inbound", clock)
    frames = []
    if df.empty:
        return frames
    for service, group in df.groupby("service", sort=True):
        counters = _counters(group, INBOUND_COUNTERS)
        secs, dt, d = poll_deltas(group, counters)
        if secs.size == 0:
            continue
        prefix = f"inbound.{label(service)}"
        for column in counters:
            frames.append(measured(secs, d[column] / dt, f"{prefix}.{column}_per_s"))
        if {"total", "5xx", "resets"} <= set(d):
            failures = d["5xx"] + d["resets"]
            if label(service) in analysis_score.GRPC_CALLEES and {"grpc_4", "grpc_14"} <= set(d):
                failures = failures + d["grpc_4"] + d["grpc_14"]
            frames.append(measured(secs, ratio(failures, d["total"]), f"{prefix}.rejection"))
        if {"rq_time_sum_ms", "rq_time_count"} <= set(d):
            frames.append(measured(
                secs, ratio(d["rq_time_sum_ms"], d["rq_time_count"]), f"{prefix}.sojourn_ms"))
    return frames


def edge_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "service_edges", clock)
    frames = []
    if df.empty:
        return frames
    for key, group in df.groupby(["caller", "target"], sort=True):
        counters = _counters(group, EDGE_COUNTERS)
        secs, dt, d = poll_deltas(group, counters)
        if secs.size == 0:
            continue
        prefix = f"edge.{label(key)}"
        for column in counters:
            frames.append(measured(secs, d[column] / dt, f"{prefix}.{column}_per_s"))
        if {"total", "retry"} <= set(d):
            frames.append(measured(
                secs, ratio(d["retry"], d["total"] - d["retry"]), f"{prefix}.rpr"))
        if {"rq_time_sum_ms", "rq_time_count"} <= set(d):
            frames.append(measured(
                secs, ratio(d["rq_time_sum_ms"], d["rq_time_count"]), f"{prefix}.sojourn_ms"))
    return frames


def throttle_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "topfull_throttle", clock)
    frames = []
    if df.empty:
        return frames
    for api, group in df.groupby("api", sort=True):
        group = group.sort_values("hold_s")
        secs = seconds(group["hold_s"])
        cap = group["threshold"].to_numpy(dtype=float)
        fresh = group["threshold_fresh"].to_numpy(dtype=float) == 1
        live = fresh & (cap > 0) & (cap < NO_CAP)
        frames.append(carried(
            secs, np.where(live, cap, np.nan), f"throttle.{label(api)}.cap",
            THROTTLE_CARRY_S, ends=fresh & (cap >= NO_CAP)))
        admitted_fresh = group["admitted_fresh"].to_numpy(dtype=float) == 1
        frames.append(carried(
            secs, np.where(admitted_fresh, group["admitted_rps"].to_numpy(dtype=float), np.nan),
            f"throttle.{label(api)}.admitted_rps", THROTTLE_CARRY_S))
    return frames


def reading_frames(
    run_dir: Path, clock: dict, source: str, prefix: str, readings, limit: int
) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, source, clock)
    frames = []
    if df.empty:
        return frames
    for service, group in df.groupby("service", sort=True):
        group = group.sort_values("hold_s")
        secs = seconds(group["hold_s"])
        for column in readings:
            if column in group.columns:
                frames.append(carried(
                    secs, pd.to_numeric(group[column], errors="coerce"),
                    f"{prefix}.{label(service)}.{column}", limit))
    return frames


def retryguard_frames(run_dir: Path, clock: dict) -> list[pd.DataFrame]:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty:
        return []
    df = df[df["hold_s"].notna()]
    frames = []
    for name, group in df[df["kind"] == "OBSERVE"].groupby("name", sort=True):
        secs = seconds(group["hold_s"])
        for field in RG_NUMERIC_FIELDS:
            if field in group.columns:
                values = pd.to_numeric(group[field], errors="coerce")
                if values.notna().any():
                    frames.append(measured(secs, values, f"rg.{label(name)}.{field}"))
    switches = df[df["kind"] == "switch"]
    if not switches.empty:
        text = switches["name"] + " " + switches["step"]
        joined = text.groupby(seconds(switches["hold_s"])).agg("; ".join)
        frames.append(joined.rename("rg.switches").to_frame())
    return frames


def with_flags(view: pd.DataFrame) -> pd.DataFrame:
    columns = {}
    for column in view.columns:
        if column.endswith(FLAG):
            continue
        flag = view[column + FLAG] if column + FLAG in view.columns else pd.Series(0.0, index=view.index)
        columns[column] = view[column]
        columns[column + FLAG] = flag.where(view[column].notna())
    return pd.DataFrame(columns, index=view.index)


def per_second_view(run_dir: Path, clock: dict | None = None) -> pd.DataFrame:
    run_dir = Path(run_dir)
    clock = clock or hold_clock.read_clock(run_dir)
    frames = (
        locust_frames(run_dir, clock)
        + inbound_frames(run_dir, clock)
        + edge_frames(run_dir, clock)
        + throttle_frames(run_dir, clock)
        + reading_frames(run_dir, clock, "topfull_detect", "detect", DETECT_READINGS, THROTTLE_CARRY_S)
        + reading_frames(run_dir, clock, "resource_usage", "resource", RESOURCE_READINGS, RESOURCE_CARRY_S)
        + retryguard_frames(run_dir, clock)
    )
    if not frames:
        return pd.DataFrame()
    view = pd.concat(frames, axis=1)
    view = view.reindex(range(int(view.index.min()), int(view.index.max()) + 1))
    view.index.name = "hold_s"
    return with_flags(view)


def switch_events(run_dir: Path, clock: dict) -> pd.DataFrame:
    df = hold_clock.load_source(run_dir, "retryguard", clock)
    if df.empty or "step" not in df.columns:
        return pd.DataFrame(columns=["hold_s", "name", "step"])
    switches = df[(df["kind"] == "switch") & df["hold_s"].notna()]
    return switches[["hold_s", "name", "step"]].reset_index(drop=True)


def select_columns(view: pd.DataFrame, patterns: list[str] | None) -> pd.DataFrame:
    if not patterns:
        return view
    keep = [
        column for column in view.columns
        if not column.endswith(FLAG) and any(fnmatch.fnmatchcase(column, p) for p in patterns)
    ]
    return view[[name for column in keep for name in (column, column + FLAG)]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_run_timeline.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add experiments/run_timeline.py experiments/test_run_timeline.py
git commit -m "feat(timeline): per-second view of every collector on the hold clock"
```

---

### Task 4: Panel rules, `timeline.png`, `build()`, and CLI

**Files:**
- Modify: `experiments/run_timeline.py`
- Modify: `.gitignore`
- Test: `experiments/test_run_timeline.py`

**Interfaces:**
- Consumes: Task 3 `per_second_view`, `switch_events`, `select_columns`, `CONTROLLED_EDGES`; Task 1 `hold_clock.write_clock`, `read_clock`, `zero_epoch`, `run_dirs`; `analysis_score.SERVICES`, `analysis_score.APIS`; `s2_latch_escape.read_inbound`, `mesh_t0`, `service_rows`, `rate_series`, `first_sustained`, `DEFAULT_RATE`, `DEFAULT_PERSIST`.
- Produces:
  - `PANELS` (ordered `(key, ylabel)` tuples: `locust`, `p95`, `caps`, `rejection`, `rpr`, `cpu`)
  - `panel_columns(view, show_all: bool = False) -> dict[str, list[str]]`
  - `escape_hold_s(run_dir, clock) -> float | None`
  - `plot_timeline(view, events, out_path, title="", show_all=False, escape_s=None) -> None`
  - `build(run_dir, show_all=False, write_csv=False, columns=None) -> Path` (returns the PNG path)
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_run_timeline.py` (above the `if __name__` block):

```python
import pandas as pd  # noqa: E402
from test_hold_clock import make_run  # noqa: E402


class TestChart(unittest.TestCase):
    def test_panel_rules(self):
        nan_ = float("nan")
        view = pd.DataFrame({
            "locust.total.Goodput": [1.0, 2.0],
            "locust.total.RPS": [1.0, 2.0],
            "locust.total.Latency95": [5.0, 6.0],
            "inbound.cartservice.rejection": [0.0, 0.0],
            "inbound.checkoutservice.rejection": [0.0, 0.1],
            "edge.frontend->cartservice.rpr": [nan_, nan_],
            "edge.frontend->cartservice.retry_per_s": [0.0, 0.0],
            "edge.frontend->checkoutservice.rpr": [0.0, 0.4],
            "edge.frontend->checkoutservice.retry_per_s": [0.0, 2.0],
            "resource.frontend.cpu_millicores": [10.0, 20.0],
            "resource.adservice.cpu_millicores": [1.0, 1.0],
            "resource.__master_node__.cpu_millicores": [4000.0, 5000.0],
            "throttle.getproduct.cap": [nan_, nan_],
            "throttle.getcart.cap": [nan_, 300.0],
        })
        panels = run_timeline.panel_columns(view)
        self.assertEqual(panels["caps"], ["throttle.getcart.cap"])
        self.assertEqual(panels["rejection"], ["inbound.checkoutservice.rejection"])
        self.assertEqual(panels["rpr"], ["edge.frontend->checkoutservice.rpr"])
        self.assertEqual(panels["cpu"], ["resource.adservice.cpu_millicores",
                                         "resource.frontend.cpu_millicores"])
        every = run_timeline.panel_columns(view, show_all=True)
        self.assertEqual(len(every["rejection"]), 2)
        self.assertEqual(len(every["rpr"]), 2)

    def test_build_writes_clock_png_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = make_run(Path(tmp))
            png = run_timeline.build(run, write_csv=True, columns=["locust.total.*"])
            self.assertGreater(png.stat().st_size, 0)
            self.assertTrue((run / hold_clock.CLOCK_JSON).is_file())
            header = (run / run_timeline.CSV_NAME).read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(header.startswith("hold_s,locust.total.RPS,"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_run_timeline.py -v -k Chart`
Expected: FAIL with `AttributeError: module 'run_timeline' has no attribute 'panel_columns'`

- [ ] **Step 3: Write the implementation**

Append to `experiments/run_timeline.py`:

```python
PANELS = (
    ("locust", "Goodput / RPS (req/s)"),
    ("p95", "P95 (ms)"),
    ("caps", "TopFull cap (req/s)"),
    ("rejection", "Inbound rejection"),
    ("rpr", "Retries per request"),
    ("cpu", "CPU (millicores)"),
)
SWITCH_COLORS = {"ON→OFF": "red", "OFF→ON": "green", "1→2": "orange", "2→3": "orange"}
MAX_PLOT_GAP_S = 3


def panel_columns(view: pd.DataFrame, show_all: bool = False) -> dict[str, list[str]]:
    def present(column: str) -> bool:
        return column in view.columns

    def any_positive(column: str) -> bool:
        return present(column) and bool((view[column] > 0).any())

    return {
        "locust": [c for c in ("locust.total.Goodput", "locust.total.RPS") if present(c)],
        "p95": [c for c in ("locust.total.Latency95",) if present(c)],
        "caps": [
            f"throttle.{api}.cap" for api in analysis_score.APIS
            if present(f"throttle.{api}.cap") and view[f"throttle.{api}.cap"].notna().any()
        ],
        "rejection": [
            f"inbound.{service}.rejection" for service in analysis_score.SERVICES
            if present(f"inbound.{service}.rejection")
            and (show_all or any_positive(f"inbound.{service}.rejection"))
        ],
        "rpr": [
            f"edge.{caller}->{target}.rpr" for caller, target in CONTROLLED_EDGES
            if present(f"edge.{caller}->{target}.rpr")
            and (show_all or any_positive(f"edge.{caller}->{target}.retry_per_s"))
        ],
        "cpu": sorted(
            column for column in view.columns
            if column.startswith("resource.") and column.endswith(".cpu_millicores")
            and column != "resource.__master_node__.cpu_millicores"
        ),
    }


def escape_hold_s(run_dir: Path, clock: dict) -> float | None:
    if not any(part.startswith("S2_") for part in Path(run_dir).resolve().parts):
        return None
    import s2_latch_escape as escape

    inbound = escape.read_inbound(str(Path(run_dir) / "service_inbound.csv"))
    t0 = escape.mesh_t0(inbound)
    if t0 is None:
        return None
    recs = escape.rate_series(escape.service_rows(inbound, "recommendationservice"), t0)
    escape_s = escape.first_sustained(recs, escape.DEFAULT_RATE, escape.DEFAULT_PERSIST, "arrival")
    if escape_s is None:
        return None
    return t0 + escape_s - hold_clock.zero_epoch(clock)


def _plot_points(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Measured points only, joined across gaps up to MAX_PLOT_GAP_S."""
    points = series.dropna()
    x = points.index.to_numpy(dtype=float)
    y = points.to_numpy(dtype=float)
    if x.size > 1:
        breaks = np.flatnonzero(np.diff(x) > MAX_PLOT_GAP_S) + 1
        x, y = np.insert(x, breaks, np.nan), np.insert(y, breaks, np.nan)
    return x, y


def plot_timeline(
    view: pd.DataFrame,
    events: pd.DataFrame,
    out_path: Path,
    title: str = "",
    show_all: bool = False,
    escape_s: float | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    panels = panel_columns(view, show_all)
    fig, axes = plt.subplots(len(PANELS), 1, sharex=True, figsize=(14, 3 * len(PANELS)))
    for ax, (key, ylabel) in zip(axes, PANELS):
        columns = panels[key]
        for column in columns:
            name = column.split(".")[-1] if key in ("locust", "p95") else column.split(".")[1]
            ax.plot(*_plot_points(view[column]), linewidth=0.9, label=name)
        for _, event in events.iterrows():
            ax.axvline(event["hold_s"], color=SWITCH_COLORS.get(event["step"], "gray"),
                       linewidth=0.8, alpha=0.7)
        if key == "locust" and escape_s is not None:
            ax.axvline(escape_s, color="black", linestyle="--", linewidth=1.2, label="escape")
        if not columns:
            ax.text(0.5, 0.5, "none in this run", transform=ax.transAxes,
                    ha="center", va="center", color="gray")
        else:
            ax.legend(loc="upper right", fontsize=7, ncol=min(4, len(columns) + 1))
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Hold clock (s since the first Locust row)")
    if not events.empty:
        steps = sorted(set(events["step"]))
        fig.legend(
            [Line2D([0], [0], color=SWITCH_COLORS.get(step, "gray")) for step in steps],
            [f"RetryGuard {step}" for step in steps],
            loc="upper left", fontsize=8,
        )
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)


def build(
    run_dir: Path,
    show_all: bool = False,
    write_csv: bool = False,
    columns: list[str] | None = None,
) -> Path:
    run_dir = Path(run_dir)
    clock = hold_clock.write_clock(run_dir)
    view = per_second_view(run_dir, clock)
    png = run_dir / PNG_NAME
    plot_timeline(
        view, switch_events(run_dir, clock), png,
        title=run_dir.name, show_all=show_all, escape_s=escape_hold_s(run_dir, clock),
    )
    if write_csv:
        select_columns(view, columns).to_csv(run_dir / CSV_NAME)
    return png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hold-clock timeline for run folders.")
    parser.add_argument("runs", nargs="*", help="Run folders")
    parser.add_argument("--tree", help="Every folder under this path that has total.csv")
    parser.add_argument("--all", action="store_true", help="Every service and edge in panels 4 and 5")
    parser.add_argument("--csv", action="store_true", help="Also write timeline_1s.csv")
    parser.add_argument("--columns", nargs="*", help="Glob patterns for the CSV columns")
    args = parser.parse_args(argv)
    failures = 0
    for run in hold_clock.run_dirs(args.runs, args.tree):
        try:
            png = build(run, show_all=args.all, write_csv=args.csv, columns=args.columns)
        except (ValueError, KeyError) as exc:
            print(f"{run.name}: ERROR {exc}")
            failures += 1
            continue
        clock = hold_clock.read_clock(run)
        print(f"{run.name}: {png.name} ({clock['method']}{', FLAGGED' if clock['flagged'] else ''})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Append one line to `.gitignore`:

```
timeline_1s.csv
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_run_timeline.py experiments/test_hold_clock.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add experiments/run_timeline.py experiments/test_run_timeline.py .gitignore
git commit -m "feat(timeline): stacked hold-clock chart with active-panel rules"
```

---

### Task 5: Timestamp column in `metric_collector.py` on master

**Files:**
- Modify: `experiments/patch_metric_collector.py`
- Test: `experiments/test_patch_metric_collector.py`

**Interfaces:**
- Produces:
  - `add_try_guard(text: str) -> str` (the existing stage, unchanged behaviour)
  - `add_row_timestamps(text: str) -> str` (new stage; no-op when already applied; `SystemExit` when the source doesn't match)
  - `main(argv: list[str] | None = None) -> None` with `--dry-run`

- [ ] **Step 1: Write the failing test**

Create `experiments/test_patch_metric_collector.py`:

```python
"""Unit tests for experiments/patch_metric_collector.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_metric_collector as patch  # noqa: E402

HEADER = 'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99"])'
SOURCE = (
    "import requests\nimport time\nimport csv\n\n"
    "def record():\n"
    "    for api in apis:\n"
    "        with open(filename, \"a\") as f:\n"
    "            w = csv.writer(f)\n"
    f"            {HEADER}\n"
    "    with open(filename, \"a\") as f:\n"
    "        w = csv.writer(f)\n"
    f"        {HEADER}\n"
) + patch.OLD


class TestPatch(unittest.TestCase):
    def test_adds_a_last_timestamp_column_once(self):
        text = patch.add_row_timestamps(patch.add_try_guard(SOURCE))
        self.assertIn("from datetime import datetime, timezone\n", text)
        self.assertEqual(text.count('"Latency99", "timestamp"])'), 2)
        self.assertIn("w.writerow([rps, fail, rps-fail, latency95, latency99, stamp])", text)
        self.assertIn("total_latency99/len(apis), stamp])", text)
        self.assertLess(text.index("            metric = c.query()\n"),
                        text.index("            stamp = datetime.now(timezone.utc)"))
        self.assertEqual(patch.add_row_timestamps(patch.add_try_guard(text)), text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest experiments/test_patch_metric_collector.py -v`
Expected: FAIL with `AttributeError: module 'patch_metric_collector' has no attribute 'add_row_timestamps'`

- [ ] **Step 3: Write the implementation**

In `experiments/patch_metric_collector.py`, replace the module docstring with:

```python
"""
Patch for metric_collector.py on the master VM. Safe to run more than once.

Stage 1 wraps the per-window collection loop in record_online_boutique() with
try/except so a missing Locust metric key (KeyError: 'getcart') no longer
crashes the process before traffic is flowing.

Stage 2 adds a UTC `timestamp` column (milliseconds, last column) to every
Locust CSV row, taken when the Locust poll returns.

    python3 patch_metric_collector.py [--dry-run]
"""
```

Directly under the docstring add `from __future__ import annotations` (master runs Python 3.8), and add `import sys` under `from pathlib import Path`. Keep `TARGET`, `OLD`, `NEW`, `MARKER` as they are. Replace `main()` and the `__main__` block with:

```python
STAMP_MARKER = '"Latency99", "timestamp"]'
STAMP_LINE = (
    '            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"\n'
)
STAMP_EDITS = (
    ("import time\n", "import time\nfrom datetime import datetime, timezone\n", 1),
    (
        'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99"])',
        'w.writerow(["RPS", "Fail", "Goodput", "Latency95", "Latency99", "timestamp"])',
        2,
    ),
    ("            metric = c.query()\n", "            metric = c.query()\n" + STAMP_LINE, 1),
    (
        "w.writerow([rps, fail, rps-fail, latency95, latency99])",
        "w.writerow([rps, fail, rps-fail, latency95, latency99, stamp])",
        1,
    ),
    (
        "w.writerow([total_rps, total_fail, total_rps-total_fail, "
        "total_latency95/len(apis), total_latency99/len(apis)])",
        "w.writerow([total_rps, total_fail, total_rps-total_fail, "
        "total_latency95/len(apis), total_latency99/len(apis), stamp])",
        1,
    ),
)


def add_try_guard(text: str) -> str:
    if MARKER in text:
        return text
    if OLD not in text:
        raise SystemExit(
            "ERROR: expected while-loop block not found — "
            "metric_collector.py may have changed; aborting"
        )
    return text.replace(OLD, NEW, 1)


def add_row_timestamps(text: str) -> str:
    if STAMP_MARKER in text:
        return text
    for old, new, count in STAMP_EDITS:
        found = text.count(old)
        if found != count:
            raise SystemExit(
                f"ERROR: expected {count} of {old!r}, found {found} — "
                "metric_collector.py may have changed; aborting"
            )
        text = text.replace(old, new)
    return text


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    text = TARGET.read_text(encoding="utf-8")
    patched = add_row_timestamps(add_try_guard(text))
    if patched == text:
        print("ALREADY_PATCHED")
        return
    if "--dry-run" in args:
        print("WOULD_PATCH")
        return
    TARGET.write_text(patched, encoding="utf-8")
    print("PATCHED_OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest experiments/test_patch_metric_collector.py -v`
Expected: 1 passed

- [ ] **Step 5: Apply on master (no hold running)**

Each command must print the noted output before you run the next one.

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py' || echo collector-clear"
```
Expected: `collector-clear`

```powershell
scp -o BatchMode=yes -o ControlMaster=no experiments/patch_metric_collector.py topfull-master:/tmp/patch_metric_collector.py
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "cp /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/metric_collector.py /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/metric_collector.py.bak-20261013 && python3 /tmp/patch_metric_collector.py --dry-run"
```
Expected: `WOULD_PATCH`. If it prints `ERROR: expected ...`, stop and report: the live file differs from what the patcher expects.

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "python3 /tmp/patch_metric_collector.py && python3 -m py_compile /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/metric_collector.py && grep -n 'stamp' /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/metric_collector.py"
```
Expected: `PATCHED_OK`, no compile error, and grep shows the import, the `stamp = ...` line, both header rows with `"timestamp"`, and both data rows ending `, stamp])`.

- [ ] **Step 6: Commit**

```bash
git add experiments/patch_metric_collector.py experiments/test_patch_metric_collector.py
git commit -m "feat(locust): stamp each Locust CSV row with master UTC"
```

---

### Task 6: `locust_started_at` in `run_manifest.json`

**Files:**
- Modify: `experiments/run_scenario.py` (`start_locust` ~L1202, `collect_results` ~L1436–1478, run body ~L1564–1621)
- Test: `experiments/test_run_scenario.py` (~L232–240, after ~L927)

**Interfaces:**
- Produces:
  - `master_utc_now(cfg: dict) -> str | None`
  - `start_locust(cfg: dict, phases: list[dict]) -> str | None` (master UTC read just before launch)
  - `collect_results(cfg, capacity=None, effective_quotas=None, locust_started_at: str | None = None) -> str`; manifest key `locust_started_at`

- [ ] **Step 1: Write the failing test and keep the old one off real SSH**

In `experiments/test_run_scenario.py`, replace `test_start_locust_launches_only_phase_zero` (~L232–240) with the version below. It mocks `master_utc_now` so the test never reaches real SSH, and checks the returned value:

```python
    @mock.patch("run_scenario.master_utc_now", return_value="2026-10-13T12:00:00.000Z")
    @mock.patch("run_scenario._launch_locust")
    def test_start_locust_launches_only_phase_zero(self, mock_launch, _mock_now):
        cfg = self._base_cfg()
        phases = [
            {"at_seconds": 0, "user_counts": {"getproduct": 100}, "spawn_rate": 90},
            {"at_seconds": 300, "user_counts": {"getproduct": 25}, "spawn_rate": 90},
        ]
        started_at = run_scenario.start_locust(cfg, phases)
        mock_launch.assert_called_once_with(cfg, {"getproduct": 100}, 90)
        self.assertEqual(started_at, "2026-10-13T12:00:00.000Z")
```

After `test_collect_results_writes_service_capacity_json` (~L927), add:

```python
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_records_locust_started_at(self, mock_ssh, mock_write_json):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {
            "infra": {
                "master_ssh_host": "topfull-master",
                "topfull_src_path": "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src",
                "results_base_path": "/home/idozacharia/experiments/results",
            },
            "scenario_id": 1, "scenario_name": "scenario_1_baseline",
            "condition": "baseline", "run_number": 7, "duration_seconds": 300,
            "retryguard": {"enabled": False},
            "log_folder": "test_run",
        }
        run_scenario.collect_results(cfg, locust_started_at="2026-10-13T12:00:00.000Z")
        manifest = [
            c.args[2] for c in mock_write_json.call_args_list
            if c.args[1].endswith("run_manifest.json")
        ][0]
        self.assertEqual(manifest["locust_started_at"], "2026-10-13T12:00:00.000Z")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest experiments/test_run_scenario.py -v -k "start_locust_launches or locust_started_at"`
Expected: FAIL with `AttributeError: ... does not have the attribute 'master_utc_now'`

- [ ] **Step 3: Write the implementation**

In `experiments/run_scenario.py`, replace `start_locust` (~L1202–1205) with:

```python
def master_utc_now(cfg: dict) -> str | None:
    """Master's UTC clock to the millisecond, or None when the read fails."""
    result = ssh(cfg["infra"]["master_ssh_host"],
                 "date -u +%Y-%m-%dT%H:%M:%S.%3NZ", check=False)
    text = (result.stdout or "").strip()
    return text if result.returncode == 0 and text else None


def start_locust(cfg: dict, phases: list[dict]) -> str | None:
    banner("Starting Locust load")
    first = phases[0]
    started_at = master_utc_now(cfg)
    _launch_locust(cfg, first["user_counts"], first["spawn_rate"])
    return started_at
```

Change the `collect_results` signature (~L1436) to:

```python
def collect_results(
    cfg: dict,
    capacity: dict | None = None,
    effective_quotas: dict | None = None,
    locust_started_at: str | None = None,
) -> str:
```

In its `manifest` dict, add after `"log_folder":    log_folder,`:

```python
        "locust_started_at": locust_started_at,
```

In the run body, next to `start_ts = datetime.now()` (~L1567) add:

```python
    locust_started_at = None
```

Replace `start_locust(cfg, phases)` (~L1588) with:

```python
        locust_started_at = start_locust(cfg, phases)
```

Replace `collect_results(cfg, capacity, effective_quotas=effective_quotas)` (~L1621) with:

```python
        collect_results(cfg, capacity, effective_quotas=effective_quotas,
                        locust_started_at=locust_started_at)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_run_scenario.py -v`
Expected: all pass. The `_run_startup` tests use a fake `ssh` that returns empty stdout for the `date` call, so `start_locust` returns `None` there.

- [ ] **Step 5: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat(runner): record master UTC at Locust start in run_manifest.json"
```

---

### Task 7: Build the timeline after every pull

**Files:**
- Modify: `experiments/pull_results.py`
- Test: `experiments/test_pull_results.py`

**Interfaces:**
- Consumes: Task 4 `run_timeline.build(run_dir) -> Path`.
- Produces: `build_timeline(run_dir: Path) -> None` (never raises an `Exception`).

- [ ] **Step 1: Write the failing test**

Create `experiments/test_pull_results.py`:

```python
"""Unit tests for experiments/pull_results.py."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pull_results  # noqa: E402

CONFIG = (
    "infra:\n"
    "  master_ssh_host: topfull-master\n"
    "  results_base_path: /remote/results\n"
    "log_folder: run_x\n"
)


class TestPullBuildsTimeline(unittest.TestCase):
    def test_timeline_is_built_and_its_failure_does_not_fail_the_pull(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dest" / "run_x").mkdir(parents=True)
            config = root / "cfg.yaml"
            config.write_text(CONFIG, encoding="utf-8")
            with mock.patch.object(pull_results.run_scenario, "local_results_dir",
                                   return_value=str(root / "dest")), \
                 mock.patch.object(pull_results.subprocess, "run",
                                   return_value=SimpleNamespace(returncode=0)), \
                 mock.patch("run_timeline.build", side_effect=ValueError("no load")) as build:
                out = pull_results.pull_results(str(config))
        self.assertEqual(out, root / "dest" / "run_x")
        build.assert_called_once_with(root / "dest" / "run_x")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest experiments/test_pull_results.py -v`
Expected: FAIL with `AssertionError: Expected 'build' to be called once. Called 0 times.`

- [ ] **Step 3: Write the implementation**

In `experiments/pull_results.py`, change the docstring's first paragraph to:

```python
"""pull_results.py — scp a finished run's results down from topfull-master.

The rho report is retired. After the pull this writes locust_clock.json and
timeline.png into the run folder (experiments/run_timeline.py); a failure
there only prints a warning. Score the folder with
experiments/analysis_score.py.
```

(keep the rest of the docstring as is). Add this function above `pull_results`:

```python
def build_timeline(run_dir: Path) -> None:
    """Write locust_clock.json and timeline.png. Never fails the pull."""
    try:
        import run_timeline

        png = run_timeline.build(run_dir)
        print(f"[pull_results] Timeline: {png}")
    except Exception as exc:  # noqa: BLE001
        print(f"[pull_results] WARNING: timeline not built for {run_dir}: {exc}",
              file=sys.stderr)
```

In `pull_results`, right after `print(f"[pull_results] Pulled to {local_run_dir}")`, add:

```python
    build_timeline(local_run_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest experiments/test_pull_results.py experiments/test_run_scenario.py -v -k "pull"`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add experiments/pull_results.py experiments/test_pull_results.py
git commit -m "feat(pull): build the hold-clock timeline after each pull"
```

---

### Task 8: Backfill `final results/` and update the docs

**Files:**
- Create (generated): `experiments/results/final results/**/locust_clock.json`, `**/timeline.png`
- Modify: `Guides and Info/METRICS-GATHERED.md` (Clock alignment section, ~L366–370)
- Modify: `AGENTS.md` (§3 "Where to find metrics" table)
- Modify: `STATUS.md` (Done list)

- [ ] **Step 1: Backfill every run**

Run: `python experiments/run_timeline.py --tree "experiments/results/final results"`
Expected: 36 lines, one per run, each `<run>: timeline.png (fit)`; exit code 0. A 2026-10-13 dry run of this code on `s2_burst20_rgtf1` took about 4 s and gave spacing 1.099 s, correlation 0.946. If any run prints `ERROR` or `FLAGGED`, note it for Step 4.

- [ ] **Step 2: Check the fits**

Run: `python experiments/hold_clock.py --tree "experiments/results/final results"`
Expected: every spacing between 1.04 and 1.11 s (the 2026-10-13 survey measured 1.049–1.102) and every line ending `ok`.

- [ ] **Step 3: Eyeball one chart**

Open `experiments/results/final results/S2_sustained_overload_burst/both/s2_burst20_rgtf1/timeline.png` with the Read tool. Check: six panels; goodput/RPS ramps up from 0 s and stops near 600 s; rejection and retries panels show connected lines, not isolated dots; the CPU panel has no line above about 2000 millicores (that would be `__master_node__`); RetryGuard switch lines run through every panel.

- [ ] **Step 4: Update the docs**

In `Guides and Info/METRICS-GATHERED.md`, replace the three bullets under `## Clock alignment (important)` with:

```markdown
- Read every run on the **hold clock**: seconds since the first Locust row, in master's UTC. `experiments/hold_clock.py` adds a `hold_s` column to any source; `experiments/run_timeline.py` writes `timeline.png` (and `timeline_1s.csv` with `--csv`). Design and per-second rules: [2026-10-13-hold-clock-design.md](../docs/superpowers/specs/2026-10-13-hold-clock-design.md).
- Locust CSVs: rows are about 1.05–1.10 s apart, not 1 s, and the first row is the first poll with traffic. Folders without a Locust `timestamp` column use that run's Locust clock fit in `locust_clock.json` (start, spacing, anchors, correlation, flag). Holds after the 2026-10-13 patch have a `timestamp` column (last column, UTC milliseconds) and `locust_started_at` in `run_manifest.json`.
- Envoy mesh + throttle collectors stamp `floor(unix_time / interval) * interval` UTC seconds (aligned). `resource_usage.csv` uses interval=5 on the same grid. Throttle **rows** stay 1 s; Layer A live `/thresholds`+`/stats` attempts use `layer_a_poll_interval_seconds` (default 5) on that same aligned grid. Skipped ticks still write a `topfull_throttle.csv` row with `*_fresh=0`.
- Each collector starts on its own. On `final results/` holds the first mesh inbound poll is roughly 25–60 s before the first Locust row, and the throttle and CPU collectors start earlier still (up to about two minutes). A file's own first poll is not t = 0. Escape time is the exception: it keeps its first-mesh-poll definition.
```

In `AGENTS.md` §3 "Where to find metrics", add a row after "What do we collect, and in which file/column?":

```markdown
| How do I line up metrics in time / see a run second by second? | `python experiments/run_timeline.py <run_dir>` → `timeline.png`; design in [2026-10-13-hold-clock-design.md](docs/superpowers/specs/2026-10-13-hold-clock-design.md) |
```

In `STATUS.md`, append one bullet at the end of the Done list:

```markdown
- **2026-10-13 — Hold clock.** Every `final results/` run now has `locust_clock.json` (per-run Locust clock fit) and `timeline.png` (six panels on one hold-clock axis). Locust rows are about 1.05–1.10 s apart, so "row i = second i" drifts 30–50 s by the end of a hold. New holds stamp Locust rows on master and record `locust_started_at`; `pull_results.py` builds the timeline after each pull. Tools: `experiments/hold_clock.py`, `experiments/run_timeline.py`.
```

If Step 1 reported any `ERROR` or `FLAGGED` runs, add their folder names to the end of that bullet.

- [ ] **Step 5: Run the touched test files**

Run: `python -m pytest experiments/test_hold_clock.py experiments/test_run_timeline.py experiments/test_patch_metric_collector.py experiments/test_pull_results.py experiments/test_run_scenario.py experiments/test_analysis_score.py -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add "experiments/results/final results" "Guides and Info/METRICS-GATHERED.md" AGENTS.md STATUS.md
git commit -m "docs(hold-clock): backfill final results timelines and fix the clock section"
```

- [ ] **Step 7: First stamped hold (when the next hold runs)**

After the next hold is pulled, confirm that `total.csv` ends with a `timestamp` column, `run_manifest.json` has a non-null `locust_started_at`, and `locust_clock.json` says `"method": "stamped"` with `fit_check.start_error_s` within ±2 s. Record that error in the hold's STATUS bullet; it is the measured accuracy of the fit on the older runs.
