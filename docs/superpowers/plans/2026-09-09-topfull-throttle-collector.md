# TopFull Throttle Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement [2026-09-09-topfull-throttle-collector-design.md](../specs/2026-09-09-topfull-throttle-collector-design.md) — a new `experiments/topfull_throttle_collector.py` that writes `topfull_throttle.csv` (Layer A: cap + admitted RPS per Locust API) and `topfull_detect.csv` (Layer B: reconstructed detector overload bool) on a **wall-clock-aligned 1s grid**, retrofit the same alignment helpers into `envoy_retry_collector.py` and `resource_usage_collector.py`, bump the mesh collector YAML poll to 1s so throttle and mesh rows share timestamps, wire the new collector into `run_scenario.py` plus all 16 scenario YAMLs, and live-smoke both CSVs (plus same-second join with the mesh collector) on `topfull-master`.

**Architecture:** New self-contained collector script (stdlib only, injected `run_cmd` / `fetch_url`, same shape as `envoy_retry_collector.py`). Alignment is a duplicated two-function helper in each collector — no shared module. Layer B reconstructs `Detector.detect()` from cAdvisor `/api/v2.0/summary` (same source as TopFull's `resource_collector.getStats_v4_two`) plus the hardcoded quota/alpha tables in `overload_detection.py`. Layers C/D are not collected. No TopFull-internal patches. No chart-pipeline changes.

**Tech Stack:** Python 3 stdlib only (`csv`, `json`, `urllib.request`, `subprocess`, `argparse`, `logging`, `unittest`), `kubectl`/SSH for cluster interaction — matches the existing collectors.

## Global Constraints

- No new pip dependencies. Stdlib only.
- All new collector logic must be pure-function-testable with injected `run_cmd` / `fetch_url` (no direct `subprocess` / `urllib` in test-covered logic).
- Never modify or delete anything under `experiments/results/campaign_48/` or `experiments/results/august_38/`.
- Do **not** update `mentor_charts.py` / `mentor_charts_data.py`. Chart wiring is a follow-up, out of scope.
- Do **not** patch TopFull (`deploy_rl.py`, `overload_detection.py`, `resource_collector.py`). Do **not** parse `tmux capture-pane -t toprl`. Do **not** revive `num_agent.csv`.
- Layers C/D (clustering, RL action) are out of scope. Do not add `topfull_rl.csv`.
- Every new/modified pure function needs a unit test in the matching `test_*.py` file. Run via `python experiments/test_topfull_throttle_collector.py` / `python experiments/test_envoy_retry_collector.py` / `python experiments/test_resource_usage_collector.py` / `python experiments/test_run_scenario.py` (`unittest`, no `pytest`).
- Tests that would sleep on a real wall-clock tick (`sleep_until_next_tick` in `run_collector`) must use `max_polls=1` so they do not wait a full interval, or mock `time.sleep`.

## File map

| File | Responsibility |
|---|---|
| Create: `experiments/topfull_throttle_collector.py` | Alignment helpers, Layer A parse/read/write, Layer B detect reconstruction + cAdvisor scrape, poll loop |
| Create: `experiments/test_topfull_throttle_collector.py` | unittest for every new pure function |
| Modify: `experiments/envoy_retry_collector.py` | Same alignment helpers; `run_collector` snaps to wall-clock ticks |
| Modify: `experiments/resource_usage_collector.py` | Same (interval stays 5s) |
| Modify: `experiments/test_envoy_retry_collector.py` | Tests for alignment helpers + `run_collector` still exits on `max_polls` |
| Modify: `experiments/test_resource_usage_collector.py` | Same |
| Modify: `experiments/run_scenario.py` | `start_topfull_throttle_collector`, call it from `run()`, manifest + banner |
| Modify: `experiments/test_run_scenario.py` | Wiring tests for the new starter |
| Modify: `experiments/configs/scenario_*.yaml` (all 16) | New YAML block; mesh poll → 1s |
| Modify: `AGENTS.md`, `Guides and Info/METRICS-GATHERED.md`, `Guides and Info/TOPFULL-THROTTLE-METRICS.md`, `experiments/README.md` | Inventory + wiring docs |

---

### Task 1: Alignment helpers in the new collector

**Files:**
- Create: `experiments/topfull_throttle_collector.py` (constants + helpers + logging/shutdown stubs only)
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: nothing.
- Produces (for later tasks):
  - `sleep_until_next_tick(interval_seconds: int, now: Optional[float] = None, sleeper: Optional[Callable[[float], None]] = None) -> None`
  - `tick_timestamp(interval_seconds: int, now: Optional[float] = None) -> str` — UTC `YYYY-MM-DDTHH:MM:SSZ` of `floor(now / interval) * interval`
  - `utc_now() -> str` — unaligned clock, used only in log lines
  - `LOCUST_APIS: List[str]`, `DEFAULT_POLL_INTERVAL_SECONDS = 1`, `GLOBAL_CONFIG_PATH`

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_topfull_throttle_collector.py`:

```python
"""
test_topfull_throttle_collector.py — Unit tests for TopFull throttle collector.

Run:
    python experiments/test_topfull_throttle_collector.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import topfull_throttle_collector as ttc

# 2023-11-14T22:13:20Z
EPOCH = 1700000000.0


class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = ttc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        # 22:13:20 is already mod 5 == 0; +3s → still 22:13:20
        ts = ttc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_next_bucket(self):
        ts = ttc.tick_timestamp(5, now=EPOCH + 5.0)
        self.assertEqual(ts, "2023-11-14T22:13:25Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        ttc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)

    def test_zero_when_already_on_next_boundary_is_non_negative(self):
        slept = []
        ttc.sleep_until_next_tick(1, now=EPOCH, sleeper=lambda s: slept.append(s))
        self.assertGreaterEqual(slept[0], 0.0)
        self.assertLessEqual(slept[0], 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `ModuleNotFoundError: No module named 'topfull_throttle_collector'` (or `ImportError`).

- [ ] **Step 3: Write the collector skeleton with the helpers**

Create `experiments/topfull_throttle_collector.py`:

```python
#!/usr/bin/env python3
"""
topfull_throttle_collector.py — Layer A (admission cap + admitted RPS) and
Layer B (reconstructed detector overload bool) on a wall-clock-aligned 1s grid.

Usage (on master, with venv active):
    python3 topfull_throttle_collector.py --params /tmp/topfull_throttle_params.json
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

GLOBAL_CONFIG_PATH = (
    "/home/idozacharia/TopFull/TopFull_master/"
    "online_boutique_scripts/src/global_config.json"
)

LOCUST_APIS: List[str] = [
    "getproduct",
    "postcheckout",
    "getcart",
    "postcart",
    "emptycart",
]

DEFAULT_POLL_INTERVAL_SECONDS = 1

THROTTLE_CSV_COLUMNS = ["timestamp", "api", "threshold", "admitted_rps"]
DETECT_CSV_COLUMNS = [
    "timestamp",
    "service",
    "cadvisor_cpu",
    "quota",
    "alpha",
    "utilization",
    "overloaded",
]

CPU_QUOTA: Dict[str, int] = {
    "cartservice": 1000,
    "currencyservice": 1000,
    "frontend": 1000,
    "adservice": 1000,
    "productcatalogservice": 500,
    "checkoutservice": 1000,
    "recommendationservice": 2000,
}
DEFAULT_QUOTA = 200
ALPHA_SPECIAL = frozenset({"productcatalogservice", "cartservice"})
DEFAULT_ALPHA = 0.8
SPECIAL_ALPHA = 0.95

DETECT_SERVICES: List[str] = [
    "frontend",
    "cartservice",
    "checkoutservice",
    "productcatalogservice",
    "paymentservice",
    "recommendationservice",
    "shippingservice",
    "currencyservice",
    "emailservice",
    "adservice",
    "redis-cart",
]

CADVISOR_NAMESPACE = "cadvisor"
CADVISOR_PORT = 8080
CPU_SKIP_BELOW = 2.0

CommandRunner = Callable[[List[str]], object]
UrlFetcher = Callable[[str], str]

log = logging.getLogger("topfull_throttle_collector")
_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    _shutdown = True
    log.info("%s  SHUTDOWN  signal=%s", utc_now(), signum)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tick_timestamp(interval_seconds: int, now: Optional[float] = None) -> str:
    t = time.time() if now is None else now
    aligned = int(t // interval_seconds) * interval_seconds
    return datetime.fromtimestamp(aligned, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def sleep_until_next_tick(
    interval_seconds: int,
    now: Optional[float] = None,
    sleeper: Optional[Callable[[float], None]] = None,
) -> None:
    t = time.time() if now is None else now
    next_tick = (int(t // interval_seconds) + 1) * interval_seconds
    delay = max(0.0, next_tick - t)
    (sleeper or time.sleep)(delay)


def setup_logging(record_path: Path) -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    log_file = record_path / "topfull_throttle_collector.log"
    try:
        fh = logging.FileHandler(str(log_file), mode="a")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as exc:
        print(
            f"[topfull_throttle_collector] WARN: cannot open {log_file}: {exc}",
            file=sys.stderr,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK` — `TestTickTimestamp` (4) and `TestSleepUntilNextTick` (2) pass.

- [ ] **Step 5: Commit**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Add wall-clock tick helpers for TopFull throttle collector"
```

---

### Task 2: Layer A — parse `/stats`, read `rate_config/`, write `topfull_throttle.csv`

**Files:**
- Modify: `experiments/topfull_throttle_collector.py` (append parse/read/write functions)
- Test: `experiments/test_topfull_throttle_collector.py` (add classes)

**Interfaces:**
- Consumes: `LOCUST_APIS`, `THROTTLE_CSV_COLUMNS` from Task 1.
- Produces:
  - `parse_proxy_stats(body: str) -> Dict[str, float]`
  - `read_thresholds(proxy_dir: Path, apis: Optional[List[str]] = None) -> Dict[str, float]`
  - `write_throttle_csv(csv_path: Path, timestamp: str, thresholds: Dict[str, float], admitted: Dict[str, float]) -> None`

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_topfull_throttle_collector.py`:

```python
SAMPLE_STATS = "getproduct=12.5/postcheckout=3.0/getcart=0/postcart=8.25/emptycart=1/"


class TestParseProxyStats(unittest.TestCase):
    def test_parses_name_value_slash_format(self):
        parsed = ttc.parse_proxy_stats(SAMPLE_STATS)
        self.assertEqual(parsed["getproduct"], 12.5)
        self.assertEqual(parsed["postcheckout"], 3.0)
        self.assertEqual(parsed["getcart"], 0.0)
        self.assertEqual(parsed["postcart"], 8.25)
        self.assertEqual(parsed["emptycart"], 1.0)

    def test_empty_body_returns_empty_dict(self):
        self.assertEqual(ttc.parse_proxy_stats(""), {})
        self.assertEqual(ttc.parse_proxy_stats("/"), {})

    def test_ignores_malformed_tokens(self):
        parsed = ttc.parse_proxy_stats("getproduct=12.5/broken/postcart=1/")
        self.assertEqual(parsed["getproduct"], 12.5)
        self.assertEqual(parsed["postcart"], 1.0)
        self.assertNotIn("broken", parsed)


class TestReadThresholds(unittest.TestCase):
    def test_reads_one_number_per_api_file(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "getproduct").write_text("40\n", encoding="utf-8")
            (d / "postcheckout").write_text("12.5\n", encoding="utf-8")
            got = ttc.read_thresholds(d, apis=["getproduct", "postcheckout", "getcart"])
            self.assertEqual(got["getproduct"], 40.0)
            self.assertEqual(got["postcheckout"], 12.5)
            self.assertEqual(got["getcart"], 0.0)

    def test_unreadable_file_is_zero_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            got = ttc.read_thresholds(Path(td), apis=["getproduct"])
            self.assertEqual(got["getproduct"], 0.0)


class TestWriteThrottleCsv(unittest.TestCase):
    def test_writes_header_and_one_row_per_api(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(
                path,
                "2023-11-14T22:13:20Z",
                {"getproduct": 40.0, "postcheckout": 10.0},
                {"getproduct": 37.0},
            )
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(ttc.THROTTLE_CSV_COLUMNS, list(rows[0].keys()) if rows else ttc.THROTTLE_CSV_COLUMNS)
            by_api = {r["api"]: r for r in rows}
            self.assertEqual(len(rows), len(ttc.LOCUST_APIS))
            self.assertEqual(by_api["getproduct"]["threshold"], "40.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "37.0")
            self.assertEqual(by_api["postcheckout"]["admitted_rps"], "0.0")

    def test_appends_without_second_header(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_throttle.csv"
            ttc.write_throttle_csv(path, "2023-11-14T22:13:20Z", {}, {})
            ttc.write_throttle_csv(path, "2023-11-14T22:13:21Z", {}, {})
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("timestamp,api,threshold,admitted_rps"), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: FAIL with `AttributeError: module 'topfull_throttle_collector' has no attribute 'parse_proxy_stats'` (or similar).

- [ ] **Step 3: Implement Layer A functions**

Append to `experiments/topfull_throttle_collector.py`:

```python
def parse_proxy_stats(body: str) -> Dict[str, float]:
    """Parse Go-proxy `/stats` body: `name=value/` tokens."""
    result: Dict[str, float] = {}
    for token in body.strip().split("/"):
        token = token.strip()
        if not token or "=" not in token:
            continue
        name, _, raw = token.partition("=")
        try:
            result[name] = float(raw)
        except ValueError:
            continue
    return result


def read_thresholds(
    proxy_dir: Path, apis: Optional[List[str]] = None
) -> Dict[str, float]:
    """Read `rate_config/<api>` files. Missing/unreadable → 0.0."""
    names = list(apis) if apis is not None else list(LOCUST_APIS)
    out: Dict[str, float] = {}
    for api in names:
        path = proxy_dir / api
        try:
            out[api] = float(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            out[api] = 0.0
    return out


def write_throttle_csv(
    csv_path: Path,
    timestamp: str,
    thresholds: Dict[str, float],
    admitted: Dict[str, float],
) -> None:
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=THROTTLE_CSV_COLUMNS)
        if write_header:
            w.writeheader()
        for api in LOCUST_APIS:
            w.writerow(
                {
                    "timestamp": timestamp,
                    "api": api,
                    "threshold": thresholds.get(api, 0.0),
                    "admitted_rps": admitted.get(api, 0.0),
                }
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`.

- [ ] **Step 5: Commit**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Parse TopFull proxy stats and write topfull_throttle.csv"
```

---

### Task 3: Layer B — quota/alpha reconstruction and cAdvisor scrape

**Files:**
- Modify: `experiments/topfull_throttle_collector.py`
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: `CPU_QUOTA`, `DEFAULT_QUOTA`, `ALPHA_SPECIAL`, `DEFAULT_ALPHA`, `SPECIAL_ALPHA`, `DETECT_SERVICES`, `CPU_SKIP_BELOW` from Task 1.
- Produces:
  - `quota_for(service: str) -> int`
  - `alpha_for(service: str) -> float`
  - `detect_metrics(service: str, cadvisor_cpu: float) -> Dict[str, object]` with keys `cadvisor_cpu`, `quota`, `alpha`, `utilization`, `overloaded` (`overloaded` is `0` or `1`)
  - `parse_cadvisor_summary(body: str) -> Optional[float]` — `latest_usage.cpu` from cAdvisor v2 summary JSON
  - `container_ids_from_pod_list(pod_list: dict, services: List[str]) -> Dict[str, List[str]]`
  - `aggregate_cpu(values: List[float]) -> float` — skip `<= CPU_SKIP_BELOW`, average the rest, else `0.0`
  - `write_detect_csv(csv_path: Path, timestamp: str, rows: Dict[str, Dict[str, object]]) -> None`

**cAdvisor scrape contract (locked):** TopFull's `resource_collector.run()` calls `getStats_v4_two()`, which GETs `http://<cadvisor-pod-ip>:8080/api/v2.0/summary/<containerID>?type=docker` and takes `latest_usage.cpu`. Values `<= 2` are dropped, then remaining values for that service are averaged. Our cluster has 1 worker (upstream hardcodes 5 IPs); discover **all** cadvisor pod IPs in namespace `cadvisor` instead of copying the 5-IP hardcode.

- [ ] **Step 1: Confirm the live scrape on master (non-blocking if VMs are down)**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "python3 - <<'PY'
import ast,inspect,sys
p='/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/resource_collector.py'
src=open(p).read()
print('--- run() snippet ---')
for i,line in enumerate(src.splitlines(),1):
    if 'def run' in line or 'getStats_' in line and 'result =' in line:
        print(f'{i}:{line}')
print('--- cadvisor ns ---')
import subprocess
print(subprocess.check_output(\"kubectl get pod -n cadvisor -o jsonpath='{.items[*].status.podIP}'\", shell=True).decode())
PY"
```

If this succeeds, confirm `run()` still assigns `getStats_v4_two()` (or equivalent summary API). If SSH fails (VM stopped), proceed with the locked contract above — do not invent a kubelet scrape as Layer B.

- [ ] **Step 2: Write the failing tests**

Append:

```python
SAMPLE_CADVISOR_SUMMARY = json.dumps(
    {
        "docker://abc": {
            "latest_usage": {"cpu": 910.0, "memory": 123},
        }
    }
)

SAMPLE_POD_LIST = {
    "items": [
        {
            "metadata": {"name": "checkoutservice-abc-123"},
            "status": {
                "containerStatuses": [
                    {
                        "name": "server",
                        "containerID": "docker://deadbeefcheckout",
                    },
                    {
                        "name": "istio-proxy",
                        "containerID": "docker://proxyid",
                    },
                ]
            },
        },
        {
            "metadata": {"name": "frontend-def-456"},
            "status": {
                "containerStatuses": [
                    {
                        "name": "server",
                        "containerID": "containerd://front123",
                    }
                ]
            },
        },
    ]
}


class TestDetectMetrics(unittest.TestCase):
    def test_quota_overrides_and_default(self):
        self.assertEqual(ttc.quota_for("productcatalogservice"), 500)
        self.assertEqual(ttc.quota_for("checkoutservice"), 1000)
        self.assertEqual(ttc.quota_for("paymentservice"), 200)

    def test_alpha_special_cases(self):
        self.assertEqual(ttc.alpha_for("cartservice"), 0.95)
        self.assertEqual(ttc.alpha_for("productcatalogservice"), 0.95)
        self.assertEqual(ttc.alpha_for("checkoutservice"), 0.8)

    def test_overloaded_when_util_exceeds_alpha(self):
        row = ttc.detect_metrics("checkoutservice", 900.0)
        self.assertEqual(row["quota"], 1000)
        self.assertEqual(row["alpha"], 0.8)
        self.assertEqual(row["utilization"], 0.9)
        self.assertEqual(row["overloaded"], 1)

    def test_not_overloaded_at_boundary(self):
        # 800 / 1000 = 0.8, overloaded is strictly greater than alpha
        row = ttc.detect_metrics("checkoutservice", 800.0)
        self.assertEqual(row["overloaded"], 0)

    def test_cartservice_uses_0_95(self):
        row = ttc.detect_metrics("cartservice", 940.0)
        self.assertEqual(row["alpha"], 0.95)
        self.assertEqual(row["overloaded"], 0)
        row2 = ttc.detect_metrics("cartservice", 960.0)
        self.assertEqual(row2["overloaded"], 1)


class TestParseCadvisorSummary(unittest.TestCase):
    def test_reads_latest_usage_cpu(self):
        self.assertEqual(ttc.parse_cadvisor_summary(SAMPLE_CADVISOR_SUMMARY), 910.0)

    def test_bad_json_returns_none(self):
        self.assertIsNone(ttc.parse_cadvisor_summary("not-json"))
        self.assertIsNone(ttc.parse_cadvisor_summary("{}"))


class TestContainerIdsFromPodList(unittest.TestCase):
    def test_skips_proxy_and_strips_runtime_prefix(self):
        ids = ttc.container_ids_from_pod_list(
            SAMPLE_POD_LIST, ["checkoutservice", "frontend", "adservice"]
        )
        self.assertEqual(ids["checkoutservice"], ["deadbeefcheckout"])
        self.assertEqual(ids["frontend"], ["front123"])
        self.assertEqual(ids["adservice"], [])


class TestAggregateCpu(unittest.TestCase):
    def test_skips_values_at_or_below_threshold_then_averages(self):
        self.assertEqual(ttc.aggregate_cpu([1.0, 2.0, 10.0, 20.0]), 15.0)

    def test_all_skipped_is_zero(self):
        self.assertEqual(ttc.aggregate_cpu([0.0, 1.5]), 0.0)
        self.assertEqual(ttc.aggregate_cpu([]), 0.0)


class TestWriteDetectCsv(unittest.TestCase):
    def test_one_row_per_service_in_DETECT_SERVICES(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "topfull_detect.csv"
            rows = {
                "checkoutservice": ttc.detect_metrics("checkoutservice", 900.0),
            }
            ttc.write_detect_csv(path, "2023-11-14T22:13:20Z", rows)
            with open(path, newline="", encoding="utf-8") as f:
                got = list(csv.DictReader(f))
            self.assertEqual(len(got), len(ttc.DETECT_SERVICES))
            by = {r["service"]: r for r in got}
            self.assertEqual(by["checkoutservice"]["overloaded"], "1")
            self.assertEqual(by["frontend"]["cadvisor_cpu"], "0.0")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: FAIL — `quota_for` / `detect_metrics` missing.

- [ ] **Step 4: Implement Layer B functions**

Append to `experiments/topfull_throttle_collector.py`:

```python
def quota_for(service: str) -> int:
    return int(CPU_QUOTA.get(service, DEFAULT_QUOTA))


def alpha_for(service: str) -> float:
    return SPECIAL_ALPHA if service in ALPHA_SPECIAL else DEFAULT_ALPHA


def detect_metrics(service: str, cadvisor_cpu: float) -> Dict[str, object]:
    quota = quota_for(service)
    alpha = alpha_for(service)
    utilization = (cadvisor_cpu / quota) if quota else 0.0
    overloaded = 1 if utilization > alpha else 0
    return {
        "cadvisor_cpu": float(cadvisor_cpu),
        "quota": quota,
        "alpha": alpha,
        "utilization": utilization,
        "overloaded": overloaded,
    }


def parse_cadvisor_summary(body: str) -> Optional[float]:
    try:
        data = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    first = next(iter(data.values()))
    if not isinstance(first, dict):
        return None
    usage = first.get("latest_usage") or {}
    cpu = usage.get("cpu")
    try:
        return float(cpu)
    except (TypeError, ValueError):
        return None


def _pod_service_name(pod_name: str, services: List[str]) -> Optional[str]:
    for svc in sorted(services, key=len, reverse=True):
        if pod_name == svc or pod_name.startswith(svc + "-"):
            return svc
    return None


def container_ids_from_pod_list(
    pod_list: dict, services: List[str]
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {s: [] for s in services}
    for item in pod_list.get("items") or []:
        name = (item.get("metadata") or {}).get("name") or ""
        svc = _pod_service_name(name, services)
        if svc is None:
            continue
        for cs in (item.get("status") or {}).get("containerStatuses") or []:
            cname = cs.get("name") or ""
            if "proxy" in cname:
                continue
            cid = cs.get("containerID") or ""
            if "://" in cid:
                cid = cid.split("://", 1)[1]
            if cid:
                out[svc].append(cid)
    return out


def aggregate_cpu(values: List[float]) -> float:
    kept = [v for v in values if v > CPU_SKIP_BELOW]
    if not kept:
        return 0.0
    return sum(kept) / len(kept)


def write_detect_csv(
    csv_path: Path,
    timestamp: str,
    rows: Dict[str, Dict[str, object]],
) -> None:
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DETECT_CSV_COLUMNS)
        if write_header:
            w.writeheader()
        for service in DETECT_SERVICES:
            metrics = rows.get(service) or detect_metrics(service, 0.0)
            w.writerow(
                {
                    "timestamp": timestamp,
                    "service": service,
                    "cadvisor_cpu": metrics["cadvisor_cpu"],
                    "quota": metrics["quota"],
                    "alpha": metrics["alpha"],
                    "utilization": metrics["utilization"],
                    "overloaded": metrics["overloaded"],
                }
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`.

- [ ] **Step 6: Commit**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Reconstruct TopFull detector overload bool for topfull_detect.csv"
```

---

### Task 4: `poll_once` + `run_collector` main loop

**Files:**
- Modify: `experiments/topfull_throttle_collector.py` (I/O glue + main)
- Test: `experiments/test_topfull_throttle_collector.py`

**Interfaces:**
- Consumes: all Task 1–3 functions.
- Produces:
  - `load_params(path: str) -> dict`
  - `load_global_config(global_config_path: str = GLOBAL_CONFIG_PATH) -> dict`
  - `default_run_cmd(cmd: List[str]) -> SimpleResult`
  - `default_fetch_url(url: str, timeout: float = 5.0) -> str`
  - `poll_once(record_path: Path, proxy_dir: Path, stats_url: str, timestamp: str, run_cmd: Optional[CommandRunner] = None, fetch_url: Optional[UrlFetcher] = None) -> None`
  - `run_collector(params: dict, record_path: Path, proxy_dir: Path, stats_url: str, run_cmd=None, fetch_url=None, max_polls=None) -> None`
  - `main() -> None`

`poll_once` must: read thresholds; GET `stats_url`; write `topfull_throttle.csv`; discover cadvisor IPs + pod list via `run_cmd`; GET each summary URL via `fetch_url`; write `topfull_detect.csv`. A failed stats fetch writes zeros for admitted_rps (still write Layer A rows). A failed cAdvisor fetch writes zeros for that service (still write all `DETECT_SERVICES` rows). Never raise out of `poll_once`.

- [ ] **Step 1: Write the failing tests**

Append:

```python
class TestPollOnce(unittest.TestCase):
    def test_writes_both_csvs_with_shared_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()
            (proxy_dir / "getproduct").write_text("40\n", encoding="utf-8")

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "cadvisor" in joined and "podIP" in joined:
                    return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")
                if "get" in cmd and "po" in cmd or "pods" in joined:
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(SAMPLE_POD_LIST),
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="no")

            def fetch_url(url: str) -> str:
                if url.endswith("/stats"):
                    return SAMPLE_STATS
                if "deadbeefcheckout" in url:
                    return SAMPLE_CADVISOR_SUMMARY
                raise OSError("no such container")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )
            throttle = list(
                csv.DictReader(
                    (record_path / "topfull_throttle.csv").open(newline="", encoding="utf-8")
                )
            )
            detect = list(
                csv.DictReader(
                    (record_path / "topfull_detect.csv").open(newline="", encoding="utf-8")
                )
            )
            self.assertTrue(all(r["timestamp"] == "2023-11-14T22:13:20Z" for r in throttle))
            self.assertTrue(all(r["timestamp"] == "2023-11-14T22:13:20Z" for r in detect))
            by_api = {r["api"]: r for r in throttle}
            self.assertEqual(by_api["getproduct"]["threshold"], "40.0")
            self.assertEqual(by_api["getproduct"]["admitted_rps"], "12.5")
            by_svc = {r["service"]: r for r in detect}
            self.assertEqual(by_svc["checkoutservice"]["cadvisor_cpu"], "910.0")
            self.assertEqual(by_svc["checkoutservice"]["overloaded"], "1")

    def test_stats_fetch_failure_still_writes_zero_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="fail")

            def fetch_url(_url: str) -> str:
                raise OSError("proxy down")

            ttc.poll_once(
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                timestamp="2023-11-14T22:13:20Z",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
            )
            throttle = list(
                csv.DictReader(
                    (record_path / "topfull_throttle.csv").open(newline="", encoding="utf-8")
                )
            )
            self.assertEqual(len(throttle), len(ttc.LOCUST_APIS))
            self.assertTrue(all(r["admitted_rps"] == "0.0" for r in throttle))


class TestRunCollector(unittest.TestCase):
    def test_max_polls_writes_and_exits(self):
        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            proxy_dir = record_path / "rate_config"
            proxy_dir.mkdir()

            def run_cmd(_cmd):
                return SimpleNamespace(returncode=1, stdout="", stderr="")

            def fetch_url(_url: str) -> str:
                return SAMPLE_STATS if _url.endswith("/stats") else "{}"

            ttc.run_collector(
                {"poll_interval_seconds": 1},
                record_path,
                proxy_dir,
                "http://127.0.0.1:8090/stats",
                run_cmd=run_cmd,
                fetch_url=fetch_url,
                max_polls=1,
            )
            self.assertTrue((record_path / "topfull_throttle.csv").exists())
            self.assertTrue((record_path / "topfull_detect.csv").exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: FAIL — `poll_once` missing.

- [ ] **Step 3: Implement I/O glue and main**

Append to `experiments/topfull_throttle_collector.py`. `SimpleResult` matches `envoy_retry_collector.py`. `run_collector` **must** call `sleep_until_next_tick(interval)` then stamp with `tick_timestamp(interval)` — except when `max_polls` is set, skip the opening sleep so tests do not wait a wall-clock second:

```python
class SimpleResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_global_config(global_config_path: str = GLOBAL_CONFIG_PATH) -> dict:
    with open(global_config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_run_cmd(cmd: List[str]) -> SimpleResult:
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(str(exc)) from exc
    return SimpleResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def default_fetch_url(url: str, timeout: float = 5.0) -> str:
    with urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _cadvisor_ips(run_cmd: CommandRunner) -> List[str]:
    r = run_cmd(
        [
            "kubectl",
            "get",
            "pod",
            "-n",
            CADVISOR_NAMESPACE,
            "-o",
            "jsonpath={.items[*].status.podIP}",
        ]
    )
    if getattr(r, "returncode", 1) != 0:
        return []
    return [p for p in (r.stdout or "").split() if p]


def _pod_list(run_cmd: CommandRunner) -> dict:
    r = run_cmd(["kubectl", "get", "po", "-n", "default", "-o", "json"])
    if getattr(r, "returncode", 1) != 0:
        return {}
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def scrape_cadvisor_cpu(
    run_cmd: CommandRunner, fetch_url: UrlFetcher
) -> Dict[str, float]:
    ips = _cadvisor_ips(run_cmd)
    ids = container_ids_from_pod_list(_pod_list(run_cmd), DETECT_SERVICES)
    out: Dict[str, float] = {}
    for service, cids in ids.items():
        values: List[float] = []
        for cid in cids:
            cpu: Optional[float] = None
            for ip in ips:
                url = f"http://{ip}:{CADVISOR_PORT}/api/v2.0/summary/{cid}?type=docker"
                try:
                    cpu = parse_cadvisor_summary(fetch_url(url))
                except (OSError, URLError, TimeoutError):
                    cpu = None
                if cpu is not None:
                    break
            if cpu is not None:
                values.append(cpu)
        out[service] = aggregate_cpu(values)
    return out


def poll_once(
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
) -> None:
    runner = run_cmd or default_run_cmd
    fetcher = fetch_url or default_fetch_url
    thresholds = read_thresholds(proxy_dir)
    admitted: Dict[str, float] = {}
    try:
        admitted = parse_proxy_stats(fetcher(stats_url))
    except (OSError, URLError, TimeoutError) as exc:
        log.warning("%s  WARNING  stats fetch failed: %s", timestamp, exc)
    write_throttle_csv(
        record_path / "topfull_throttle.csv", timestamp, thresholds, admitted
    )
    cpu_by_svc: Dict[str, float] = {}
    try:
        cpu_by_svc = scrape_cadvisor_cpu(runner, fetcher)
    except (OSError, TimeoutError) as exc:
        log.warning("%s  WARNING  cadvisor scrape failed: %s", timestamp, exc)
    rows = {
        svc: detect_metrics(svc, cpu_by_svc.get(svc, 0.0)) for svc in DETECT_SERVICES
    }
    write_detect_csv(record_path / "topfull_detect.csv", timestamp, rows)


def run_collector(
    params: dict,
    record_path: Path,
    proxy_dir: Path,
    stats_url: str,
    run_cmd: Optional[CommandRunner] = None,
    fetch_url: Optional[UrlFetcher] = None,
    max_polls: Optional[int] = None,
) -> None:
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    log.info("%s  START  poll_interval=%ss", utc_now(), interval)
    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        ts = tick_timestamp(interval)
        poll_once(
            record_path,
            proxy_dir,
            stats_url,
            timestamp=ts,
            run_cmd=run_cmd,
            fetch_url=fetch_url,
        )
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
    log.info("%s  EXIT", utc_now())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TopFull throttle (Layer A) and detector (Layer B) collector."
    )
    parser.add_argument("--params", required=True, help="Path to collector params JSON")
    args = parser.parse_args()
    params = load_params(args.params)
    gcfg = load_global_config()
    record_path = Path(gcfg["record_path"])
    proxy_dir = Path(gcfg["proxy_dir"])
    stats_url = gcfg["proxy_url"].rstrip("/") + "/stats"
    record_path.mkdir(parents=True, exist_ok=True)
    setup_logging(record_path)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_collector(params, record_path, proxy_dir, stats_url)


if __name__ == "__main__":
    main()
```

Fix `_pod_list`'s `run_cmd` detection in `TestPollOnce`: the mock checks `"pods" in joined` **or** `"po" in cmd`. `["kubectl", "get", "po", "-n", "default", "-o", "json"]` contains `"po"` as an argv element. Keep the mock as written.

If `TestPollOnce.test_writes_both_csvs` fails because the mock treats the cadvisor IP command as a pod-list command (`"po"` is a substring of `"pod"`), change the mock to:

```python
if "-n" in cmd and CADVISOR_NAMESPACE in cmd:
    return SimpleNamespace(returncode=0, stdout="10.0.0.9\n", stderr="")
if cmd[-2:] == ["-o", "json"] or (len(cmd) >= 2 and cmd[-1] == "json"):
    return SimpleNamespace(returncode=0, stdout=json.dumps(SAMPLE_POD_LIST), stderr="")
```

Use `ttc.CADVISOR_NAMESPACE` in the test mock.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_topfull_throttle_collector.py`

Expected: `OK`. If `TestPollOnce` fails on the kubectl mock, apply the stricter mock from Step 3 and re-run — do not weaken `poll_once`.

- [ ] **Step 5: Commit**

```
git add experiments/topfull_throttle_collector.py experiments/test_topfull_throttle_collector.py
git commit -m "Poll TopFull throttle and detector metrics on a 1s wall-clock grid"
```

---

### Task 5: Wire the collector into `run_scenario.py`

**Files:**
- Modify: `experiments/run_scenario.py` (`start_topfull_throttle_collector` after `start_resource_usage_collector`; call from `run()`; `collect_results` manifest; banner in `run()`)
- Test: `experiments/test_run_scenario.py` (new class mirroring `TestEnvoyRetryCollectorWiring`)

**Interfaces:**
- Consumes: YAML key `topfull_throttle_collector: {enabled, poll_interval_seconds}`; `infra.topfull_throttle_collector_script`.
- Produces: tmux session `throttle`, remote `/tmp/topfull_throttle_params.json`, `/tmp/rg_topfull_throttle.sh`.

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_run_scenario.py` (copy the resource-usage wiring class shape):

```python
class TestTopfullThrottleCollectorWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "topfull_throttle_collector_script":
                    "/home/idozacharia/experiments/topfull_throttle_collector.py",
            },
            "topfull_throttle_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 1,
            },
        }

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_uploads_params_and_launches_tmux(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_topfull_throttle_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master",
            "topfull_throttle_collector.py",
            "/home/idozacharia/experiments/topfull_throttle_collector.py",
        )
        json_path, params = mock_write_json.call_args[0][1:3]
        self.assertEqual(json_path, "/tmp/topfull_throttle_params.json")
        self.assertEqual(params["poll_interval_seconds"], 1)
        script_path, script_body = mock_write_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_topfull_throttle.sh")
        self.assertIn(
            "topfull_throttle_collector.py --params /tmp/topfull_throttle_params.json",
            script_body,
        )
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if "tmux new-session" in c.args[1] and "throttle" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_start_noop_when_disabled(
        self, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        run_scenario.start_topfull_throttle_collector(self._cfg(enabled=False))
        mock_ssh.assert_not_called()
        mock_write_json.assert_not_called()
```

Also extend whatever test covers `collect_results` / the manifest dict: add `"topfull_throttle_collector"` to the expected manifest keys. If no existing test asserts those keys, add an assertion in a new test that `collect_results` writes the key — grep `test_run_scenario.py` for `collect_results` first; if none exists, do **not** invent a full `collect_results` integration test; the banner/start tests above are enough, and the manifest one-liner is verified by reading the function after edit.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_run_scenario.py TestTopfullThrottleCollectorWiring`

Expected: FAIL — `start_topfull_throttle_collector` missing.

- [ ] **Step 3: Implement wiring**

Add this function immediately after `start_resource_usage_collector` in `experiments/run_scenario.py` (before the Locust section):

```python
def start_topfull_throttle_collector(cfg: dict):
    """
    Start the TopFull throttle / detector collector on master.

    Independent of RetryGuard: must run in both baseline and RetryGuard arms.
    Read-only against rate_config/ and :8090/stats — no teardown.
    """
    ttc_cfg = cfg.get("topfull_throttle_collector", {})
    if not ttc_cfg.get("enabled", False):
        return

    banner("Starting TopFull throttle collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "topfull_throttle_collector_script",
        "/home/idozacharia/experiments/topfull_throttle_collector.py",
    )
    deploy_repo_script(master, "topfull_throttle_collector.py", script)
    params = {
        "poll_interval_seconds": int(ttc_cfg.get("poll_interval_seconds", 1)),
    }
    write_remote_json(master, "/tmp/topfull_throttle_params.json", params)
    step(
        "Uploaded TopFull throttle collector params: "
        f"poll_interval={params['poll_interval_seconds']}s"
    )
    start_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/topfull_throttle_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_topfull_throttle.sh", start_script)
    ssh(master, "tmux new-session -d -s throttle /tmp/rg_topfull_throttle.sh")
    step("Started: TopFull throttle collector "
         f"(tmux session: throttle, script: {script})")
    wait_with_progress(3, "TopFull throttle collector init")
```

In `run()`, after `start_resource_usage_collector(cfg)` add:

```python
        start_topfull_throttle_collector(cfg)
```

In the banner block (next to `ruc_enabled`), add:

```python
    ttc_enabled = cfg.get("topfull_throttle_collector", {}).get("enabled", False)
    print(f"  TopFull throttle collector: {'ON' if ttc_enabled else 'OFF'}")
    if ttc_enabled:
        print(f"    poll_interval  : "
              f"{cfg['topfull_throttle_collector'].get('poll_interval_seconds', 1)}s")
```

In `collect_results` `manifest` dict, add:

```python
        "topfull_throttle_collector": cfg.get("topfull_throttle_collector", {}),
```

Do **not** add a copy step — `collect_results()` already `cp -r src/logs/.` into the dest folder.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python experiments/test_run_scenario.py`

Expected: `OK` (existing tests plus the new class).

- [ ] **Step 5: Commit**

```
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "Wire TopFull throttle collector into run_scenario.py"
```

---

### Task 6: Scenario YAMLs and docs

**Files:**
- Modify: all 16 files under `experiments/configs/scenario_*.yaml`
- Modify: `AGENTS.md` (§3 table for TOPFULL-THROTTLE-METRICS, §4 remaining-work if needed, §6 `/tmp` cleanup)
- Modify: `Guides and Info/METRICS-GATHERED.md`
- Modify: `Guides and Info/TOPFULL-THROTTLE-METRICS.md` (status: design implemented, awaiting first run)
- Modify: `experiments/README.md` (YAML schema rows)
- Modify: `docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md` Status section

**Interfaces:** none. YAML block:

```yaml
# ── TopFull throttle collector (Layer A cap/admitted + Layer B detector) ────
topfull_throttle_collector:
  enabled: true
  poll_interval_seconds: 1
```

Also change **only** the `envoy_retry_collector.poll_interval_seconds` value from `5` to `1` in every YAML (resource_usage stays `5`). Add `infra.topfull_throttle_collector_script: /home/idozacharia/experiments/topfull_throttle_collector.py` next to the other script paths.

- [ ] **Step 1: Update all 16 scenario YAMLs**

For each file in `experiments/configs/`:
1. After the `resource_usage_collector` block, insert the `topfull_throttle_collector` block above.
2. Set `envoy_retry_collector.poll_interval_seconds: 1`.
3. Add `topfull_throttle_collector_script` under `infra:`.

Do not bump `run_number` / `log_folder`. Do not touch S6 run3 overwrite warning — that is unrelated.

- [ ] **Step 2: Docs**

`AGENTS.md` §6 cleanup command — add `/tmp/rg_topfull_throttle.sh`:

```
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh"
```

`AGENTS.md` §3 row for TOPFULL-THROTTLE-METRICS — change from inventory-only wording to: implemented collector, writes `topfull_throttle.csv` + `topfull_detect.csv`, no campaign data yet.

`METRICS-GATHERED.md` — add a short section **after** Layer 2 / before Layer 3:

```
## Layer 3 supplement — TopFull throttle (future runs)

**Writer:** `experiments/topfull_throttle_collector.py` on master, 1s wall-clock ticks
shared with the mesh collector.

**Present only in runs launched after this collector landed** — not in
`campaign_48/` or `august_38/`.

### `topfull_throttle.csv`
timestamp, api, threshold, admitted_rps

### `topfull_detect.csv`
timestamp, service, cadvisor_cpu, quota, alpha, utilization, overloaded

`overloaded` reconstructs `Detector.detect()` (cAdvisor CPU vs TopFull's
hardcoded quota × alpha). It is not kubelet `resource_usage.csv`. Layers C/D
are not collected. `mentor_charts.py` does not read these files.
```

Also note in the clocks subsection: Envoy mesh + throttle collectors now stamp `floor(unix_time / interval) * interval` UTC seconds (aligned). `resource_usage.csv` uses interval=5 on the same grid. Locust CSVs remain index-based with no timestamp column.

`TOPFULL-THROTTLE-METRICS.md` Status / "How to keep this" — say the collector is implemented; campaign folders still lack the files until the next run.

`experiments/README.md` schema table — add `topfull_throttle_collector.enabled` / `poll_interval_seconds` (default 1) and `infra.topfull_throttle_collector_script`. Change envoy poll default in that table from 5 to 1.

Design spec Status section: change "Design only" to "Implemented (2026-09-09). No campaign folder has this data yet."

Do **not** edit `mentor_charts.py`. Do **not** claim campaign_48 has these CSVs.

- [ ] **Step 3: Commit**

```
git add experiments/configs AGENTS.md "Guides and Info/METRICS-GATHERED.md" "Guides and Info/TOPFULL-THROTTLE-METRICS.md" experiments/README.md docs/superpowers/specs/2026-09-09-topfull-throttle-collector-design.md
git commit -m "Enable TopFull throttle collector in scenario configs and docs"
```

---

### Task 7: Retrofit wall-clock alignment into the two existing collectors

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`tick_timestamp`, `sleep_until_next_tick`; `run_collector` uses them)
- Modify: `experiments/resource_usage_collector.py` (same)
- Test: `experiments/test_envoy_retry_collector.py`, `experiments/test_resource_usage_collector.py`

**Interfaces:**
- Consumes: the helper signatures from Task 1 (duplicate the functions; do not import `topfull_throttle_collector`).
- Produces: `run_collector` stamps `tick_timestamp(interval)` instead of `utc_now()`. When `max_polls is None`, sleep with `sleep_until_next_tick` instead of `for _ in range(interval): time.sleep(1)`. When `max_polls is not None`, skip the opening sleep (same as Task 4) so existing `test_max_polls_writes_and_exits` does not hang.

CSV schemas/columns stay unchanged. `resource_usage` default interval stays **5**. Envoy Python `DEFAULT_POLL_INTERVAL_SECONDS` may stay 5 (YAML now passes 1); do not change that constant unless a test requires it.

- [ ] **Step 1: Write failing tests for the helpers in each existing test file**

Add `EPOCH = 1700000000.0` near the top of each test module if it is not already there. Append these two classes to `experiments/test_envoy_retry_collector.py` (using `erc`) **and** the same two classes to `experiments/test_resource_usage_collector.py` (replace `erc` with `ruc`):

```python
class TestTickTimestamp(unittest.TestCase):
    def test_floors_to_interval_boundary(self):
        ts = erc.tick_timestamp(1, now=EPOCH + 0.4)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_already_on_boundary(self):
        ts = erc.tick_timestamp(1, now=EPOCH)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")

    def test_five_second_interval_floors_to_mod_5(self):
        ts = erc.tick_timestamp(5, now=EPOCH + 3.0)
        self.assertEqual(ts, "2023-11-14T22:13:20Z")


class TestSleepUntilNextTick(unittest.TestCase):
    def test_sleeps_the_remainder_of_the_interval(self):
        slept = []
        erc.sleep_until_next_tick(
            1, now=EPOCH + 0.25, sleeper=lambda s: slept.append(s)
        )
        self.assertEqual(len(slept), 1)
        self.assertAlmostEqual(slept[0], 0.75, places=6)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py TestTickTimestamp`

Expected: FAIL — `tick_timestamp` missing.

- [ ] **Step 3: Copy helpers and switch `run_collector`**

In **both** `envoy_retry_collector.py` and `resource_usage_collector.py`, add `tick_timestamp` and `sleep_until_next_tick` next to `utc_now()` (identical bodies to Task 1).

Replace the poll loop body so it matches Task 4:

```python
        if max_polls is None:
            sleep_until_next_tick(interval)
            if _shutdown:
                break
        ts = tick_timestamp(interval)
        poll_once(..., timestamp=ts, ...)
```

Keep `utc_now()` for START/EXIT/WARNING log lines. Delete the `for _ in range(interval): time.sleep(1)` block.

- [ ] **Step 4: Run all collector tests**

```
python experiments/test_topfull_throttle_collector.py
python experiments/test_envoy_retry_collector.py
python experiments/test_resource_usage_collector.py
python experiments/test_run_scenario.py
```

Expected: all `OK`.

- [ ] **Step 5: Commit**

```
git add experiments/envoy_retry_collector.py experiments/resource_usage_collector.py experiments/test_envoy_retry_collector.py experiments/test_resource_usage_collector.py
git commit -m "Align Envoy and resource-usage collectors to wall-clock ticks"
```

---

### Task 8: Live validation against the real cluster

**Files:** None (no repo changes — commands against `topfull-master` only). If the live cAdvisor summary JSON or `/stats` body does not match what Tasks 2–3 parse, fix `parse_proxy_stats` / `parse_cadvisor_summary` in `experiments/topfull_throttle_collector.py`, re-run `python experiments/test_topfull_throttle_collector.py`, commit that fix, then re-attempt this task.

**Interfaces:** None.

Do **not** launch `run_scenario.py`. S6 YAMLs still point at completed `run3` and would overwrite that folder on master. This smoke writes only under `/tmp/throttle_smoke/` on master.

- [ ] **Step 1: Confirm cluster health**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get pods -n cadvisor"
```

Expected: nodes `Ready`; Boutique pods `Running` (2/2 with sidecar); at least one `cadvisor` pod `Running`. If SSH times out, follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) (ephemeral IP / VM `TERMINATED`) — do not mark this task passed against a down cluster.

- [ ] **Step 2: Confirm Layer A sources exist (proxy optional for a zeros-OK write-path smoke)**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "python3 -c \"import json; p='/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/global_config.json'; g=json.load(open(p)); print('proxy_dir='+g['proxy_dir']); print('proxy_url='+g['proxy_url']); print('record_path='+g['record_path'])\"; echo '--- rate_config ---'; ls -l /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/proxy/rate_config/ 2>/dev/null || ls -l \"\$(python3 -c \"import json; print(json.load(open('/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/global_config.json'))['proxy_dir'])\")\"; echo '--- stats ---'; curl -sS -m 3 http://127.0.0.1:8090/stats || echo PROXY_DOWN"
```

Expected: `proxy_dir` and `proxy_url` print; `rate_config/` may be empty if no proxy has run this boot. `PROXY_DOWN` is allowed — Layer A rows will be zeros; the smoke still validates parse/write/alignment. If `/stats` returns `name=value/` text, note one API name so Step 6 can check a non-zero `admitted_rps` when present.

- [ ] **Step 3: Confirm cAdvisor summary API matches the locked scrape**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "IP=\$(kubectl get pod -n cadvisor -o jsonpath='{.items[0].status.podIP}'); echo cadvisor_ip=\$IP; CID=\$(kubectl get po -n default -o json | python3 -c \"import json,sys; d=json.load(sys.stdin); 
for it in d.get('items',[]):
  name=it.get('metadata',{}).get('name','')
  if not name.startswith('checkoutservice'): continue
  for cs in it.get('status',{}).get('containerStatuses',[]):
    if 'proxy' in cs.get('name',''): continue
    cid=cs.get('containerID','')
    print(cid.split('://',1)[-1]); break
\"); echo container_id=\$CID; curl -sS -m 5 \"http://\${IP}:8080/api/v2.0/summary/\${CID}?type=docker\" | python3 -c \"import json,sys; d=json.load(sys.stdin); print(list(d.values())[0]['latest_usage']['cpu'])\""
```

Expected: a floating-point CPU number prints. If the JSON shape differs (`latest_usage` missing, or CPU under another key), update `parse_cadvisor_summary` to match the live body, add a unit-test fixture with that body, commit, then continue. If namespace `cadvisor` is empty, stop — do not fall back to kubelet `resource_usage.csv` as Layer B.

- [ ] **Step 4: Copy both aligned collectors to master and run an 8s scratch smoke (no `max_polls` — that path skips `sleep_until_next_tick`)**

```
scp experiments/topfull_throttle_collector.py experiments/envoy_retry_collector.py topfull-master:/tmp/
```

Then:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "python3 - <<'PY'
import json, sys, threading
from pathlib import Path
sys.path.insert(0, '/tmp')
import topfull_throttle_collector as ttc
import envoy_retry_collector as erc

g = json.load(open('/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/global_config.json'))
scratch = Path('/tmp/throttle_smoke')
if scratch.exists():
    for p in scratch.glob('*.csv'):
        p.unlink()
scratch.mkdir(parents=True, exist_ok=True)
proxy_dir = Path(g['proxy_dir'])
stats_url = g['proxy_url'].rstrip('/') + '/stats'
params = {'poll_interval_seconds': 1, 'services': ['frontend', 'checkoutservice']}

def run_throttle():
    ttc.run_collector(params, scratch, proxy_dir, stats_url)

def run_mesh():
    erc.run_collector(params, scratch)

th = threading.Thread(target=run_throttle, daemon=True)
mh = threading.Thread(target=run_mesh, daemon=True)
th.start(); mh.start()
th.join(); mh.join()
PY"
```

That script never returns on its own (`run_collector` loops forever). Wrap it:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "timeout 8 python3 /tmp/throttle_align_smoke.py; true"
```

Write `/tmp/throttle_align_smoke.py` on master first (same body as the heredoc above, without the never-return surprise — the `timeout` is what stops it).

Expected: exit 124 from `timeout` (or 0 if `true` swallows it); no Python traceback on stderr; `/tmp/throttle_smoke/` exists.

- [ ] **Step 5: Verify Layer A / Layer B schemas and 1s timestamps**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "python3 - <<'PY'
import csv
from pathlib import Path
d = Path('/tmp/throttle_smoke')
th = list(csv.DictReader((d/'topfull_throttle.csv').open()))
de = list(csv.DictReader((d/'topfull_detect.csv').open()))
print('throttle_header', list(th[0].keys()) if th else None)
print('detect_header', list(de[0].keys()) if de else None)
print('throttle_rows', len(th), 'apis', sorted({r['api'] for r in th}))
print('detect_rows', len(de), 'services', sorted({r['service'] for r in de}))
print('throttle_ts', sorted({r['timestamp'] for r in th}))
print('detect_ts', sorted({r['timestamp'] for r in de}))
assert list(th[0].keys()) == ['timestamp','api','threshold','admitted_rps']
assert list(de[0].keys()) == ['timestamp','service','cadvisor_cpu','quota','alpha','utilization','overloaded']
assert {r['api'] for r in th} == set(['getproduct','postcheckout','getcart','postcart','emptycart'])
assert {r['service'] for r in de} == set(['frontend','cartservice','checkoutservice','productcatalogservice','paymentservice','recommendationservice','shippingservice','currencyservice','emailservice','adservice','redis-cart'])
assert {r['timestamp'] for r in th} == {r['timestamp'] for r in de}
for ts in {r['timestamp'] for r in th}:
    assert ts.endswith('Z') and len(ts) == 20
print('LAYER_OK')
PY"
```

Expected: `LAYER_OK`. Thresholds/admitted may be `0.0` if the proxy is down — that is a pass for this step. If Step 2 had a live `/stats` body, at least one `admitted_rps` should be non-zero.

- [ ] **Step 6: Verify same-second join with the mesh collector**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "python3 - <<'PY'
import csv
from pathlib import Path
d = Path('/tmp/throttle_smoke')
th_ts = {r['timestamp'] for r in csv.DictReader((d/'topfull_throttle.csv').open())}
# mesh files may be service_edges.csv / service_inbound.csv (post-mesh-plan) or missing if Task 7 envoy copy is old
edges = d/'service_edges.csv'
if not edges.exists():
    raise SystemExit('NO_MESH_CSV — confirm Task 7 envoy_retry_collector.py was the file scp-ed')
mesh_ts = {r['timestamp'] for r in csv.DictReader(edges.open())}
shared = th_ts & mesh_ts
print('throttle_ticks', sorted(th_ts))
print('mesh_ticks', sorted(mesh_ts))
print('shared', sorted(shared))
assert shared, 'no shared timestamp — collectors did not snap to the same wall-clock second'
print('ALIGN_OK')
PY"
```

Expected: `ALIGN_OK` and at least one timestamp in `shared`. Mesh row values may be zero (no Locust) — that is fine. If `service_edges.csv` is missing, the scp in Step 4 used a stale collector; recopy `experiments/envoy_retry_collector.py` from the Task 7 tree and re-run Steps 4–6.

- [ ] **Step 7: Confirm campaign folders were not touched**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls /home/idozacharia/experiments/results/ | grep -E 'topfull_throttle|topfull_detect' || echo NONE_IN_RESULTS_ROOT; test -f /tmp/throttle_smoke/topfull_throttle.csv && echo SMOKE_ONLY_OK"
```

Expected: `NONE_IN_RESULTS_ROOT` (or no new run folders) and `SMOKE_ONLY_OK`. If `global_config.json` `record_path` accidentally received new `topfull_*.csv` because someone ran `main()` instead of the scratch script, delete **only** those two filenames from `record_path` — do not delete Locust CSVs or anything under a named `log_folder`.

- [ ] **Step 8: Clean up test artifacts**

Run:

```
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "rm -rf /tmp/throttle_smoke /tmp/throttle_align_smoke.py /tmp/topfull_throttle_collector.py /tmp/envoy_retry_collector.py"
```

Expected: exit 0.

- [ ] **Step 9: No commit needed**

This task only touches the live cluster and `/tmp` on master. If Step 3 required a parser fix, that commit already happened on the collector file — nothing further to commit here.

---

## Self-review (spec coverage)

| Spec item | Task |
|---|---|
| Layer A `topfull_throttle.csv` (`timestamp, api, threshold, admitted_rps`) | Task 2 + 4 |
| Layer B `topfull_detect.csv` (cAdvisor + quota/alpha, not kubelet) | Task 3 + 4 |
| Wall-clock `sleep_until_next_tick` / `tick_timestamp` | Task 1 |
| Mesh collector also on 1s grid (YAML poll 1s + helper retrofit) | Task 6 + 7 |
| `resource_usage` stays 5s on the same grid | Task 7 (interval unchanged) |
| New script + `run_scenario.py` tmux/YAML/`deploy_repo_script` | Task 5 + 6 |
| Manifest key + `/tmp/rg_topfull_throttle.sh` cleanup | Task 5 + 6 |
| No Layers C/D, no TopFull patches, no charts, no campaign overwrite | Global Constraints |
| cAdvisor scrape verified / locked to `getStats_v4_two` summary API | Task 3 Step 1 + Task 8 Step 3 |
| Stdlib + unittest + injected `run_cmd`/`fetch_url` | Tasks 1–4 |
| Live write-path + same-second join with mesh CSVs | Task 8 |

Out of scope left unplanned on purpose: `topfull_rl.csv`, `tmux capture-pane`, `/thresholds` primary source, `mentor_charts.py`, backfill, a full `run_scenario.py` campaign run (Task 8 is a scratch-dir smoke only).
