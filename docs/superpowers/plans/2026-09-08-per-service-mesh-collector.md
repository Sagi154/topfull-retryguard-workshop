# Per-Service Mesh Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement [PER-SERVICE-MESH-COLLECTOR-DESIGN.md](../../../Guides%20and%20Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md) — extend `experiments/envoy_retry_collector.py` into a full-mesh collector that scrapes **every** Boutique pod's Envoy sidecar (not just `frontend`/`checkoutservice`) for both outbound (`upstream_rq_*`) and inbound (`downstream_rq_*`) stats, writes `service_edges.csv` + `service_inbound.csv` with a shared per-poll timestamp, patches the Istio stats-inclusion annotation onto all 11 Deployments as part of `run_scenario.py`'s per-run setup, and snapshots each service's original CPU limit/request/replica count into `service_capacity.json`.

**Architecture:** Extend `envoy_retry_collector.py` in place (same process, new parsing regexes, new CSV schemas, no more hardcoded `CALLER_TARGET_MAP`). Wire deployment annotation patching and the capacity snapshot into `run_scenario.py`'s existing per-run lifecycle (`ensure_envoy_stats_enabled`, and a new `capture_service_capacity` called right after preflight, before any `scale_constraints` are applied). No changes to `resource_usage_collector.py`, `retryguard.py`, or any existing `campaign_48/`/`august_38/` data.

**Tech Stack:** Python 3 stdlib only (`re`, `csv`, `json`, `subprocess`, `argparse`, `logging`), `unittest` for tests, `kubectl`/SSH for cluster interaction — matches the existing `resource_usage_collector.py` / `envoy_retry_collector.py` pattern exactly.

## Global Constraints

- No new pip dependencies. Stdlib only, consistent with every existing collector script.
- All new collector logic must be pure-function-testable with an injected `run_cmd` (no direct `subprocess` calls in test-covered logic) — same convention as `resource_usage_collector.py` / `envoy_retry_collector.py` today.
- Never modify or delete anything under `experiments/results/campaign_48/` or `experiments/results/august_38/` — this plan only affects **future** runs.
- This plan intentionally does **not** update `mentor_charts.py` / `mentor_charts_data.py` to read the new `service_edges.csv` / `service_inbound.csv` files — those still only read the legacy `envoy_retries_{caller}.csv` shape, which keeps working for existing historical data since this plan does not delete or reprocess it. Wiring charts to the new files is an explicit follow-up, out of scope here (call this out in Task 5's doc update, do not silently attempt it).
- Deployment annotation patching (`sidecar.istio.io/statsInclusionRegexps`) is **not restored** after a run — same as the existing `ensure_envoy_stats_enabled` behavior today. It is an inert annotation (only unhides admin-endpoint stats, doesn't change traffic behavior), and re-patching every run is already idempotent (a no-op after the first application). Do not add a teardown/restore step for it.
- Every new/modified pure function needs a unit test in the matching `test_*.py` file before being considered done, run via `python experiments/test_envoy_retry_collector.py` / `python experiments/test_run_scenario.py` (both use `unittest`, no `pytest` dependency).

---

## Task 1: Rewrite the parsing/CSV layer in `envoy_retry_collector.py` (full-mesh edges + inbound)

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (constants + `parse_retry_stats`/`write_csv_row`/`_empty_stats` section only — lines ~34–81 and ~183–230 in the current file)
- Test: `experiments/test_envoy_retry_collector.py` (replace `TestParseRetryStats` and `TestWriteCsvRow` classes)

**Interfaces:**
- Consumes: nothing new (pure text-parsing / CSV-appending, same shape as today).
- Produces (for Task 2 to consume):
  - `ALL_SERVICES: List[str]` — the 11 Boutique service/app-label names.
  - `parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]` — keyed by target service name, values are `{"total": int, "2xx": int, "4xx": int, "5xx": int, "retry": int}`.
  - `parse_inbound(stats_text: str) -> Dict[str, int]` — `{"total": int, "2xx": int, "4xx": int, "5xx": int}`.
  - `write_edges_csv(csv_path: Path, timestamp: str, caller: str, edges: Dict[str, Dict[str, int]]) -> None`
  - `write_inbound_csv(csv_path: Path, timestamp: str, service: str, inbound: Dict[str, int]) -> None`
  - `EDGES_CSV_COLUMNS`, `INBOUND_CSV_COLUMNS` constants.

- [ ] **Step 1: Write the failing tests for `parse_edges` / `parse_inbound`**

Replace the `SAMPLE_STATS` constant and the `TestParseRetryStats` class at the top of `experiments/test_envoy_retry_collector.py` with:

```python
SAMPLE_MESH_STATS = """\
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_total: 100
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_2xx: 90
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_4xx: 8
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_5xx: 2
cluster.outbound|80||cartservice.default.svc.cluster.local.upstream_rq_retry: 12
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_total: 50
cluster.outbound|9555||productcatalogservice.default.svc.cluster.local.upstream_rq_retry: 3
http.inbound_0.0.0.0_8080.downstream_rq_total: 200
http.inbound_0.0.0.0_8080.downstream_rq_2xx: 180
http.inbound_0.0.0.0_8080.downstream_rq_4xx: 15
http.inbound_0.0.0.0_8080.downstream_rq_5xx: 5
"""


class TestParseEdges(unittest.TestCase):
    def test_extracts_every_target_seen(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(set(edges.keys()), {"cartservice", "productcatalogservice"})

    def test_full_metrics_for_cartservice(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["cartservice"],
            {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2, "retry": 12},
        )

    def test_missing_metrics_default_to_zero(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertEqual(
            edges["productcatalogservice"],
            {"total": 50, "2xx": 0, "4xx": 0, "5xx": 0, "retry": 3},
        )

    def test_target_never_seen_is_absent_not_zero_filled(self):
        edges = erc.parse_edges(SAMPLE_MESH_STATS)
        self.assertNotIn("paymentservice", edges)

    def test_empty_stats_text_returns_empty_dict(self):
        self.assertEqual(erc.parse_edges(""), {})


class TestParseInbound(unittest.TestCase):
    def test_extracts_all_four_metrics(self):
        inbound = erc.parse_inbound(SAMPLE_MESH_STATS)
        self.assertEqual(
            inbound, {"total": 200, "2xx": 180, "4xx": 15, "5xx": 5}
        )

    def test_no_inbound_lines_returns_zeros(self):
        inbound = erc.parse_inbound(
            "cluster.outbound|80||cartservice.default.svc.cluster.local."
            "upstream_rq_total: 100\n"
        )
        self.assertEqual(inbound, {"total": 0, "2xx": 0, "4xx": 0, "5xx": 0})

    def test_multiple_listener_ports_are_summed(self):
        text = (
            "http.inbound_0.0.0.0_8080.downstream_rq_total: 100\n"
            "http.inbound_0.0.0.0_9090.downstream_rq_total: 50\n"
        )
        self.assertEqual(erc.parse_inbound(text)["total"], 150)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python experiments/test_envoy_retry_collector.py`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'parse_edges'` (and similarly for `parse_inbound`).

- [ ] **Step 3: Implement `parse_edges` / `parse_inbound` and their constants**

In `experiments/envoy_retry_collector.py`, replace the block from `CALLER_TARGET_MAP` through `STAT_RE` (roughly lines 34–81) with:

```python
# All 11 Boutique Deployments (app label == Kubernetes Service name). Every
# pod is scraped every poll — no more hardcoded caller/target shortlist.
ALL_SERVICES: List[str] = [
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

OUTBOUND_METRICS = ("total", "2xx", "4xx", "5xx", "retry")
INBOUND_METRICS = ("total", "2xx", "4xx", "5xx")

# cluster.outbound|<port>||<target>.default.svc.cluster.local.upstream_rq_<metric>: <value>
OUTBOUND_RE = re.compile(
    r"^cluster\.outbound\|[^|]*\|[^|]*\|"
    r"(?P<target>[\w-]+)\.default\.svc\.cluster\.local\."
    r"upstream_rq_(?P<metric>total|2xx|4xx|5xx|retry): (?P<value>\d+)$"
)

# http.inbound_<listener-id>.downstream_rq_<metric>: <value>
# (listener id is typically "<bind-ip>_<port>", e.g. "0.0.0.0_8080")
INBOUND_RE = re.compile(
    r"^http\.inbound_(?P<listener>[\w.]+)\.downstream_rq_"
    r"(?P<metric>total|2xx|4xx|5xx): (?P<value>\d+)$"
)

EDGES_CSV_COLUMNS = ["timestamp", "caller", "target", "total", "2xx", "4xx", "5xx", "retry"]
INBOUND_CSV_COLUMNS = ["timestamp", "service", "total", "2xx", "4xx", "5xx"]
```

Then replace the `_empty_stats` / `parse_retry_stats` functions (roughly lines 183–204) with:

```python
def parse_edges(stats_text: str) -> Dict[str, Dict[str, int]]:
    """
    Parse outbound cluster stats into per-target metric dicts.

    Only targets that actually appear in stats_text are included — no
    fixed target list. Every distinct <target> seen in a
    cluster.outbound|...upstream_rq_* line gets a row, with any metric
    not present for that target defaulting to 0.
    """
    edges: Dict[str, Dict[str, int]] = {}
    for line in stats_text.splitlines():
        m = OUTBOUND_RE.match(line.strip())
        if not m:
            continue
        target = m.group("target")
        if target not in edges:
            edges[target] = {k: 0 for k in OUTBOUND_METRICS}
        edges[target][m.group("metric")] = int(m.group("value"))
    return edges


def parse_inbound(stats_text: str) -> Dict[str, int]:
    """
    Parse this pod's own inbound listener stats (downstream_rq_*).

    A pod can have more than one HTTP listener (e.g. separate ports);
    totals across listeners are summed into one row per pod/service.
    Always returns all four metrics (missing -> 0).
    """
    inbound = {k: 0 for k in INBOUND_METRICS}
    for line in stats_text.splitlines():
        m = INBOUND_RE.match(line.strip())
        if not m:
            continue
        inbound[m.group("metric")] += int(m.group("value"))
    return inbound
```

Remove the now-unused `METRIC_NAMES` constant and `resolve_caller_map` function (they will be fully replaced in Task 2 — for this step just make sure nothing still references `parse_retry_stats`/`_empty_stats`/`STAT_RE`/`CALLER_TARGET_MAP` inside this file; `poll_once`/`run_collector` still reference them and will not compile correctly until Task 2 — that's expected, Task 2 fixes it immediately after).

- [ ] **Step 4: Run tests to verify the new parsing tests pass**

Run: `python -c "import sys; sys.path.insert(0,'experiments'); import ast; ast.parse(open('experiments/envoy_retry_collector.py').read())"`
Expected: no `SyntaxError` (confirms the file is still valid Python even though `poll_once` references now-removed names — Python only errors on that at call time, not parse time).

Run: `python -m unittest experiments.test_envoy_retry_collector.TestParseEdges experiments.test_envoy_retry_collector.TestParseInbound -v` (run from repo root; add `experiments/__init__.py`-free import via `sys.path` trick already in the test file, so instead run directly: `cd experiments && python test_envoy_retry_collector.py TestParseEdges TestParseInbound` is not valid unittest CLI syntax — use:)

Run: `cd experiments; python -m unittest test_envoy_retry_collector.TestParseEdges test_envoy_retry_collector.TestParseInbound -v`
Expected: all `TestParseEdges` and `TestParseInbound` cases PASS.

- [ ] **Step 5: Write the failing tests for `write_edges_csv` / `write_inbound_csv`**

Replace the `TestWriteCsvRow` class in `experiments/test_envoy_retry_collector.py` with:

```python
class TestWriteEdgesCsv(unittest.TestCase):
    def test_writes_header_once_then_appends_multiple_targets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_edges.csv"
            edges_t0 = {
                "cartservice": {"total": 10, "2xx": 9, "4xx": 1, "5xx": 0, "retry": 2},
                "paymentservice": {"total": 5, "2xx": 5, "4xx": 0, "5xx": 0, "retry": 0},
            }
            erc.write_edges_csv(path, "2026-09-08T12:00:00Z", "checkoutservice", edges_t0)
            edges_t1 = {
                "cartservice": {"total": 20, "2xx": 18, "4xx": 2, "5xx": 0, "retry": 3},
            }
            erc.write_edges_csv(path, "2026-09-08T12:00:05Z", "checkoutservice", edges_t1)

            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["caller"], "checkoutservice")
            self.assertEqual(rows[0]["target"], "cartservice")
            self.assertEqual(rows[0]["retry"], "2")
            self.assertEqual(rows[1]["target"], "paymentservice")
            self.assertEqual(rows[2]["total"], "20")

    def test_empty_edges_writes_no_rows_but_no_error(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_edges.csv"
            erc.write_edges_csv(path, "2026-09-08T12:00:00Z", "frontend", {})
            self.assertFalse(path.exists())


class TestWriteInboundCsv(unittest.TestCase):
    def test_writes_header_once_then_appends(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "service_inbound.csv"
            erc.write_inbound_csv(
                path, "2026-09-08T12:00:00Z", "frontend",
                {"total": 100, "2xx": 90, "4xx": 8, "5xx": 2},
            )
            erc.write_inbound_csv(
                path, "2026-09-08T12:00:05Z", "frontend",
                {"total": 150, "2xx": 140, "4xx": 8, "5xx": 2},
            )
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service"], "frontend")
            self.assertEqual(rows[0]["total"], "100")
            self.assertEqual(rows[1]["total"], "150")
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd experiments; python -m unittest test_envoy_retry_collector.TestWriteEdgesCsv test_envoy_retry_collector.TestWriteInboundCsv -v`
Expected: `AttributeError: module 'envoy_retry_collector' has no attribute 'write_edges_csv'`.

- [ ] **Step 7: Implement `write_edges_csv` / `write_inbound_csv`**

Replace the old `write_csv_row` function (roughly lines 208–230) with:

```python
def write_edges_csv(
    csv_path: Path,
    timestamp: str,
    caller: str,
    edges: Dict[str, Dict[str, int]],
) -> None:
    """Append one row per (caller, target) pair; write header if new file."""
    if not edges:
        return
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EDGES_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for target in sorted(edges):
            m = edges[target]
            writer.writerow({
                "timestamp": timestamp,
                "caller": caller,
                "target": target,
                "total": m["total"],
                "2xx": m["2xx"],
                "4xx": m["4xx"],
                "5xx": m["5xx"],
                "retry": m["retry"],
            })


def write_inbound_csv(
    csv_path: Path,
    timestamp: str,
    service: str,
    inbound: Dict[str, int],
) -> None:
    """Append one row for this service's inbound totals this poll."""
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INBOUND_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "service": service,
            "total": inbound["total"],
            "2xx": inbound["2xx"],
            "4xx": inbound["4xx"],
            "5xx": inbound["5xx"],
        })
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd experiments; python -m unittest test_envoy_retry_collector.TestWriteEdgesCsv test_envoy_retry_collector.TestWriteInboundCsv -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat(envoy-collector): add full-mesh edges/inbound parsing and CSV writers"
```

---

## Task 2: Rewire `poll_once` / `run_collector` / `main` to scrape all services into shared CSVs

**Files:**
- Modify: `experiments/envoy_retry_collector.py` (`resolve_caller_map`, `poll_once`, `run_collector` — roughly lines 140–146 and 306–388; module docstring at top)
- Test: `experiments/test_envoy_retry_collector.py` (replace `TestPollOnce` and `TestRunCollector` classes)

**Interfaces:**
- Consumes: `ALL_SERVICES`, `parse_edges`, `parse_inbound`, `write_edges_csv`, `write_inbound_csv` from Task 1; `discover_pod_name`, `fetch_stats_text` (unchanged, already generic over any app label).
- Produces: `resolve_services(params: dict) -> List[str]`; `poll_once(record_path, services, timestamp, run_cmd=None, pod_cache=None) -> None` (new signature — `services` replaces `caller_map`); `run_collector(params, record_path, run_cmd=None, max_polls=None) -> None` (same signature, new internals). Both files it writes are fixed names: `service_edges.csv`, `service_inbound.csv` in `record_path` (no longer per-caller filenames).

- [ ] **Step 1: Write the failing tests for the new `poll_once` behavior**

Replace `TestPollOnce` in `experiments/test_envoy_retry_collector.py` with:

```python
class TestPollOnce(unittest.TestCase):
    def test_writes_edges_and_inbound_for_every_service(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            services = ["frontend", "checkoutservice"]

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(returncode=0, stdout="frontend-1\n", stderr="")
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(returncode=0, stdout="checkout-1\n", stderr="")
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")
                if "exec" in cmd and "checkout-1" in cmd:
                    stats = (
                        "cluster.outbound|50051||paymentservice.default."
                        "svc.cluster.local.upstream_rq_total: 7\n"
                        "http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n"
                    )
                    return SimpleNamespace(returncode=0, stdout=stats, stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            erc.poll_once(
                record_path, services,
                timestamp="2026-09-08T12:00:00Z",
                run_cmd=run_cmd, pod_cache={},
            )

            with open(record_path / "service_edges.csv", newline="") as f:
                edges_rows = list(csv.DictReader(f))
            with open(record_path / "service_inbound.csv", newline="") as f:
                inbound_rows = list(csv.DictReader(f))

            self.assertEqual(
                {(r["caller"], r["target"]) for r in edges_rows},
                {("frontend", "cartservice"), ("frontend", "productcatalogservice"),
                 ("checkoutservice", "paymentservice")},
            )
            self.assertEqual(
                {r["service"] for r in inbound_rows},
                {"frontend", "checkoutservice"},
            )
            checkout_inbound = next(r for r in inbound_rows if r["service"] == "checkoutservice")
            self.assertEqual(checkout_inbound["total"], "30")

    def test_survives_one_service_fetch_failure(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)
            services = ["frontend", "checkoutservice"]

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined and "app=frontend" in joined:
                    return SimpleNamespace(returncode=0, stdout="frontend-1\n", stderr="")
                if "get pods" in joined and "app=checkoutservice" in joined:
                    return SimpleNamespace(returncode=0, stdout="checkout-1\n", stderr="")
                if "exec" in cmd and "frontend-1" in cmd:
                    return SimpleNamespace(returncode=1, stdout="", stderr="fail")
                if "exec" in cmd and "checkout-1" in cmd:
                    return SimpleNamespace(
                        returncode=0,
                        stdout="http.inbound_0.0.0.0_8080.downstream_rq_total: 30\n",
                        stderr="",
                    )
                return SimpleNamespace(returncode=1, stdout="", stderr="unexpected")

            # Must not raise.
            erc.poll_once(
                record_path, services,
                timestamp="2026-09-08T12:00:00Z",
                run_cmd=run_cmd, pod_cache={},
            )
            self.assertFalse((record_path / "service_edges.csv").exists())
            with open(record_path / "service_inbound.csv", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service"], "checkoutservice")
```

Also replace `TestRunCollector` with:

```python
class TestRunCollector(unittest.TestCase):
    def test_max_polls_writes_and_exits(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            record_path = Path(td)

            def run_cmd(cmd):
                joined = " ".join(cmd)
                if "get pods" in joined:
                    svc = "frontend" if "app=frontend" in joined else "checkoutservice"
                    return SimpleNamespace(returncode=0, stdout=f"{svc}-1\n", stderr="")
                return SimpleNamespace(returncode=0, stdout=SAMPLE_MESH_STATS, stderr="")

            erc.run_collector(
                {"poll_interval_seconds": 1, "services": ["frontend", "checkoutservice"]},
                record_path,
                run_cmd=run_cmd,
                max_polls=1,
            )
            self.assertTrue((record_path / "service_edges.csv").exists())
            self.assertTrue((record_path / "service_inbound.csv").exists())


class TestResolveServices(unittest.TestCase):
    def test_defaults_to_all_services(self):
        self.assertEqual(erc.resolve_services({}), erc.ALL_SERVICES)

    def test_override_via_params(self):
        self.assertEqual(
            erc.resolve_services({"services": ["frontend", "cartservice"]}),
            ["frontend", "cartservice"],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments; python -m unittest test_envoy_retry_collector.TestPollOnce test_envoy_retry_collector.TestRunCollector test_envoy_retry_collector.TestResolveServices -v`
Expected: failures (`poll_once` still has the old `caller_map` signature; `resolve_services` doesn't exist yet).

- [ ] **Step 3: Implement `resolve_services` and rewrite `poll_once` / `run_collector`**

Replace `resolve_caller_map` (roughly lines 140–146) with:

```python
def resolve_services(params: dict) -> List[str]:
    override = params.get("services")
    if override:
        return list(override)
    return list(ALL_SERVICES)
```

Replace `poll_once` and `run_collector` (roughly lines 306–388) with:

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    pod_cache: Optional[Dict[str, str]] = None,
) -> None:
    """
    One scrape of every service's sidecar. Writes rows into
    service_edges.csv and service_inbound.csv. Survives per-service
    failures (a failed exec just skips that service this poll).
    """
    if pod_cache is None:
        pod_cache = {}
    runner = run_cmd or default_run_cmd

    edges_path = record_path / "service_edges.csv"
    inbound_path = record_path / "service_inbound.csv"

    for service in sorted(services):
        pod = pod_cache.get(service)
        if not pod:
            pod = discover_pod_name(service, run_cmd=runner)
            if pod:
                pod_cache[service] = pod
            else:
                log.warning("%s  WARNING  no pod for service=%s", utc_now(), service)
                continue

        stats_text = fetch_stats_text(pod, run_cmd=runner)
        if stats_text is None:
            pod_cache.pop(service, None)
            continue

        edges = parse_edges(stats_text)
        inbound = parse_inbound(stats_text)
        write_edges_csv(edges_path, timestamp, service, edges)
        write_inbound_csv(inbound_path, timestamp, service, inbound)


def run_collector(
    params: dict,
    record_path: Path,
    run_cmd: Optional[CommandRunner] = None,
    max_polls: Optional[int] = None,
) -> None:
    """
    Main loop. Sleeps poll_interval_seconds between scrapes until SIGTERM
    or max_polls (used by tests).
    """
    services = resolve_services(params)
    interval = int(params.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    pod_cache: Dict[str, str] = {}

    log.info(
        "%s  START  poll_interval=%ss services=%d",
        utc_now(), interval, len(services),
    )

    polls = 0
    while not _shutdown:
        if max_polls is not None and polls >= max_polls:
            break
        poll_once(record_path, services, timestamp=utc_now(), run_cmd=run_cmd, pod_cache=pod_cache)
        polls += 1
        if max_polls is not None and polls >= max_polls:
            break
        for _ in range(interval):
            if _shutdown:
                break
            time.sleep(1)

    log.info("%s  EXIT", utc_now())
```

Update the module docstring at the top of the file to describe the new full-mesh behavior and output files (`service_edges.csv`, `service_inbound.csv`) instead of `envoy_retries_{caller}.csv`.

- [ ] **Step 4: Run the full test file to verify everything passes**

Run: `cd experiments; python test_envoy_retry_collector.py -v`
Expected: all tests PASS, zero failures/errors.

- [ ] **Step 5: Commit**

```bash
git add experiments/envoy_retry_collector.py experiments/test_envoy_retry_collector.py
git commit -m "feat(envoy-collector): scrape all 11 services per poll into shared CSVs"
```

---

## Task 3: Widen the stats-inclusion patch to all services in `run_scenario.py`

**Files:**
- Modify: `experiments/run_scenario.py` (`STATS_INCLUSION_REGEX` constant, `start_envoy_retry_collector` — roughly lines 540–623)
- Test: `experiments/test_run_scenario.py` (`TestEnvoyRetryCollectorWiring` class — roughly lines 259–403)

**Interfaces:**
- Consumes: `ensure_envoy_stats_enabled(cfg, caller_pods: list)` (unchanged signature — Task 3 just changes *what list* it's called with and *what regex* it patches).
- Produces: `ALL_BOUTIQUE_SERVICES: list` constant (used again in Task 4), updated `STATS_INCLUSION_REGEX` value, `start_envoy_retry_collector` now reads `cfg["envoy_retry_collector"].get("services", ALL_BOUTIQUE_SERVICES)` instead of `caller_target_map`.

- [ ] **Step 1: Write the failing tests**

In `experiments/test_run_scenario.py`, replace the `TestEnvoyRetryCollectorWiring._cfg` helper and the two tests that reference `caller_target_map` with:

```python
class TestEnvoyRetryCollectorWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "envoy_retry_collector_script":
                    "/home/idozacharia/experiments/envoy_retry_collector.py",
            },
            "envoy_retry_collector": {
                "enabled": enabled,
                "poll_interval_seconds": 5,
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
        run_scenario.start_envoy_retry_collector(cfg)
        mock_deploy.assert_called_once_with(
            "topfull-master", "envoy_retry_collector.py",
            "/home/idozacharia/experiments/envoy_retry_collector.py",
        )
        json_path, params = mock_write_json.call_args[0][1:3]
        self.assertEqual(json_path, "/tmp/envoy_retry_params.json")
        self.assertEqual(params["poll_interval_seconds"], 5)
        self.assertNotIn("services", params)

        script_path, script_body = mock_write_script.call_args[0][1:3]
        self.assertEqual(script_path, "/tmp/rg_envoy_retry.sh")
        self.assertIn("envoy_retry_collector.py --params /tmp/envoy_retry_params.json",
                      script_body)
        tmux_calls = [
            c for c in mock_ssh.call_args_list
            if "tmux new-session" in c.args[1] and "envoyretry" in c.args[1]
        ]
        self.assertEqual(len(tmux_calls), 1)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_start_noop_when_disabled(
        self, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=False)
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ssh.assert_not_called()
        mock_write_json.assert_not_called()
        mock_write_script.assert_not_called()

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_passes_services_override(
        self, mock_deploy, mock_ssh, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["envoy_retry_collector"]["services"] = ["frontend", "cartservice"]
        run_scenario.start_envoy_retry_collector(cfg)
        params = mock_write_json.call_args[0][2]
        self.assertEqual(params["services"], ["frontend", "cartservice"])

    @mock.patch("run_scenario.ssh")
    def test_stop_master_stack_pkills_envoy_collector(self, mock_ssh):
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        run_scenario.stop_master_stack(cfg)
        cmd = mock_ssh.call_args[0][1]
        self.assertIn("[e]nvoy_retry_collector.py", cmd)

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_ensure_envoy_stats_enabled_patches_each_caller(
        self, mock_ssh, mock_write_json
    ):
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        run_scenario.ensure_envoy_stats_enabled(cfg, ["frontend", "checkoutservice"])

        patch_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl patch deployment" in c.args[1]
        ]
        self.assertEqual(len(patch_calls), 2)
        self.assertIn("frontend", patch_calls[0].args[1])
        self.assertIn("checkoutservice", patch_calls[1].args[1])

        rollout_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl rollout status" in c.args[1]
        ]
        self.assertEqual(len(rollout_calls), 2)

        patched_json = mock_write_json.call_args[0][2]
        self.assertEqual(
            patched_json["spec"]["template"]["metadata"]["annotations"]
            ["sidecar.istio.io/statsInclusionRegexps"],
            run_scenario.STATS_INCLUSION_REGEX,
        )
        # Regex must now also cover inbound listener stats, not just outbound.
        self.assertIn("downstream_rq", run_scenario.STATS_INCLUSION_REGEX)
        self.assertIn("upstream_rq", run_scenario.STATS_INCLUSION_REGEX)

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_ensure_envoy_stats_enabled_warns_but_continues_on_patch_failure(
        self, mock_ssh, mock_write_json
    ):
        mock_ssh.return_value = SimpleNamespace(returncode=1, stdout="", stderr="not found")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        run_scenario.ensure_envoy_stats_enabled(cfg, ["frontend"])  # must not raise
        rollout_calls = [
            c for c in mock_ssh.call_args_list
            if "kubectl rollout status" in c.args[1]
        ]
        self.assertEqual(len(rollout_calls), 0)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_envoy_retry_collector_patches_all_services_by_default(
        self, mock_deploy, mock_ssh, mock_ensure, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ensure.assert_called_once_with(cfg, run_scenario.ALL_BOUTIQUE_SERVICES)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ensure_envoy_stats_enabled")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_start_envoy_retry_collector_patches_service_override(
        self, mock_deploy, mock_ssh, mock_ensure, mock_write_json, mock_write_script, mock_wait
    ):
        cfg = self._cfg(enabled=True)
        cfg["envoy_retry_collector"]["services"] = ["frontend"]
        run_scenario.start_envoy_retry_collector(cfg)
        mock_ensure.assert_called_once_with(cfg, ["frontend"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments; python -m unittest test_run_scenario.TestEnvoyRetryCollectorWiring -v`
Expected: several failures — `AttributeError: module 'run_scenario' has no attribute 'ALL_BOUTIQUE_SERVICES'`, and the "patches all services by default" test fails because the current code still calls `ensure_envoy_stats_enabled` with `caller_target_map` keys.

- [ ] **Step 3: Implement the widened constant + wiring**

In `experiments/run_scenario.py`, replace the comment block and `STATS_INCLUSION_REGEX` definition (roughly lines 540–548) with:

```python
# Istio's default proxyStatsMatcher strips detailed per-cluster/listener stats
# (both outbound upstream_rq_* and inbound downstream_rq_*) from the Envoy
# admin /stats endpoint to save memory. Without this annotation, the mesh
# collector silently gets all-zero data forever — confirmed live on
# 2026-08-20 (PHASE7-DATA-GAPS.md Gap 3) for the outbound-only case.
# Applying it via kubectl patch is idempotent: a no-op (no pod restart)
# once already applied with the same value.
STATS_INCLUSION_REGEX = r"(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)"

# All 11 Boutique Deployments — the full mesh collector scrapes every one of
# these every poll (see PER-SERVICE-MESH-COLLECTOR-DESIGN.md). Keep this list
# in sync with envoy_retry_collector.ALL_SERVICES and
# resource_usage_collector.DEFAULT_SERVICES.
ALL_BOUTIQUE_SERVICES = [
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
```

Then, inside `start_envoy_retry_collector` (roughly lines 587–623), replace the caller-pods derivation and the params block:

```python
def start_envoy_retry_collector(cfg: dict):
    """
    Start the full-mesh Envoy sidecar collector on master.

    Scrapes every Boutique pod (not just frontend/checkoutservice) for
    outbound (upstream_rq_*) and inbound (downstream_rq_*) stats, writing
    service_edges.csv / service_inbound.csv. Independent of RetryGuard:
    must run in both baseline and RetryGuard conditions so retry volume
    is comparable across arms.
    """
    erc_cfg = cfg.get("envoy_retry_collector", {})
    if not erc_cfg.get("enabled", False):
        return

    banner("Starting Envoy mesh collector")
    master = cfg["infra"]["master_ssh_host"]
    venv = cfg["infra"]["venv_activate"]
    script = cfg["infra"].get(
        "envoy_retry_collector_script",
        "/home/idozacharia/experiments/envoy_retry_collector.py",
    )
    deploy_repo_script(master, "envoy_retry_collector.py", script)

    services = list(erc_cfg.get("services", ALL_BOUTIQUE_SERVICES))
    ensure_envoy_stats_enabled(cfg, services)

    params = {
        "poll_interval_seconds": int(erc_cfg.get("poll_interval_seconds", 5)),
    }
    if "services" in erc_cfg:
        params["services"] = erc_cfg["services"]

    write_remote_json(master, "/tmp/envoy_retry_params.json", params)
    step(f"Uploaded Envoy mesh collector params: "
         f"poll_interval={params['poll_interval_seconds']}s "
         f"services={len(services)}")

    start_script = (
        f"#!/bin/bash\n"
        f"source {venv}\n"
        f"python3 {script} --params /tmp/envoy_retry_params.json\n"
    )
    write_remote_script(master, "/tmp/rg_envoy_retry.sh", start_script)
    ssh(master, "tmux new-session -d -s envoyretry /tmp/rg_envoy_retry.sh")
    step(f"Started: Envoy mesh collector "
         f"(tmux session: envoyretry, script: {script})")
    wait_with_progress(3, "Envoy mesh collector init")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments; python -m unittest test_run_scenario.TestEnvoyRetryCollectorWiring -v`
Expected: all PASS.

Run: `cd experiments; python test_run_scenario.py -v`
Expected: entire file passes (confirms no other test in the file was relying on the old `caller_target_map` shape).

- [ ] **Step 5: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat(run-scenario): patch stats-inclusion on all 11 services, not just 2"
```

---

## Task 4: Snapshot original CPU limit/request/replica count into `service_capacity.json`

**Files:**
- Modify: `experiments/run_scenario.py` (add `parse_cpu_to_millicores`, `capture_service_capacity` near `apply_constraints`; thread `capacity` through `run()` and `collect_results`)
- Test: `experiments/test_run_scenario.py` (new `TestServiceCapacity` class)

**Interfaces:**
- Consumes: `ALL_BOUTIQUE_SERVICES` (Task 3), `ssh`, `write_remote_json` (existing).
- Produces: `parse_cpu_to_millicores(cpu_str) -> int | None`; `capture_service_capacity(cfg: dict, services: list) -> dict` returning `{service: {"cpu_limit_millicores": int|None, "cpu_request_millicores": int|None, "replica_count": int}}`; `collect_results(cfg: dict, capacity: dict | None = None) -> str` (signature change — capacity is optional so any other caller of `collect_results` doesn't break).

- [ ] **Step 1: Write the failing tests**

Add to `experiments/test_run_scenario.py`:

```python
class TestServiceCapacity(unittest.TestCase):
    def test_parse_cpu_to_millicores_variants(self):
        self.assertEqual(run_scenario.parse_cpu_to_millicores("100m"), 100)
        self.assertEqual(run_scenario.parse_cpu_to_millicores("1"), 1000)
        self.assertEqual(run_scenario.parse_cpu_to_millicores("0.5"), 500)
        self.assertIsNone(run_scenario.parse_cpu_to_millicores(None))
        self.assertIsNone(run_scenario.parse_cpu_to_millicores(""))

    @mock.patch("run_scenario.ssh")
    def test_capture_service_capacity_parses_deployment_json(self, mock_ssh):
        deploy_json = json.dumps({
            "items": [
                {
                    "metadata": {"name": "checkoutservice"},
                    "spec": {
                        "replicas": 1,
                        "template": {"spec": {"containers": [
                            {"name": "server", "resources": {
                                "limits": {"cpu": "100m"},
                                "requests": {"cpu": "100m"},
                            }},
                        ]}},
                    },
                },
                {
                    "metadata": {"name": "frontend"},
                    "spec": {
                        "replicas": 1,
                        "template": {"spec": {"containers": [
                            {"name": "server", "resources": {
                                "limits": {"cpu": "300m"},
                                "requests": {"cpu": "200m"},
                            }},
                        ]}},
                    },
                },
                {
                    "metadata": {"name": "not-requested-service"},
                    "spec": {"replicas": 1, "template": {"spec": {"containers": []}}},
                },
            ],
        })
        mock_ssh.return_value = SimpleNamespace(returncode=0, stdout=deploy_json, stderr="")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}

        capacity = run_scenario.capture_service_capacity(
            cfg, ["checkoutservice", "frontend"]
        )

        self.assertEqual(set(capacity.keys()), {"checkoutservice", "frontend"})
        self.assertEqual(capacity["checkoutservice"], {
            "cpu_limit_millicores": 100,
            "cpu_request_millicores": 100,
            "replica_count": 1,
        })
        self.assertEqual(capacity["frontend"]["cpu_limit_millicores"], 300)
        self.assertEqual(capacity["frontend"]["cpu_request_millicores"], 200)

    @mock.patch("run_scenario.ssh")
    def test_capture_service_capacity_handles_bad_json(self, mock_ssh):
        mock_ssh.return_value = SimpleNamespace(returncode=1, stdout="", stderr="boom")
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        capacity = run_scenario.capture_service_capacity(cfg, ["frontend"])
        self.assertEqual(capacity, {})

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_writes_service_capacity_json(self, mock_ssh, mock_write_json):
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
        capacity = {"frontend": {"cpu_limit_millicores": 300, "cpu_request_millicores": 200, "replica_count": 1}}

        run_scenario.collect_results(cfg, capacity)

        capacity_calls = [
            c for c in mock_write_json.call_args_list
            if c.args[1].endswith("service_capacity.json")
        ]
        self.assertEqual(len(capacity_calls), 1)
        self.assertEqual(capacity_calls[0].args[2], capacity)

    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    def test_collect_results_writes_empty_dict_when_capacity_omitted(self, mock_ssh, mock_write_json):
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
        run_scenario.collect_results(cfg)
        capacity_calls = [
            c for c in mock_write_json.call_args_list
            if c.args[1].endswith("service_capacity.json")
        ]
        self.assertEqual(capacity_calls[0].args[2], {})
```

Make sure `json` is imported at the top of `test_run_scenario.py` (add `import json` alongside the existing `import sys` / `import unittest` if not already present).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments; python -m unittest test_run_scenario.TestServiceCapacity -v`
Expected: `AttributeError: module 'run_scenario' has no attribute 'parse_cpu_to_millicores'` (and similarly for `capture_service_capacity`; the `collect_results` tests fail with a `TypeError` about the extra positional arg).

- [ ] **Step 3: Implement `parse_cpu_to_millicores` and `capture_service_capacity`**

In `experiments/run_scenario.py`, add just above `def apply_constraints(cfg: dict) -> list:` (roughly line 311):

```python
def parse_cpu_to_millicores(cpu_str):
    """Convert a Kubernetes CPU quantity ('100m', '1', '0.5') to millicores."""
    if not cpu_str:
        return None
    s = str(cpu_str).strip()
    if not s:
        return None
    if s.endswith("m"):
        return int(s[:-1])
    return int(float(s) * 1000)


def capture_service_capacity(cfg: dict, services: list) -> dict:
    """
    Snapshot each service's *original* CPU limit/request and declared
    replica count, before any scale_constraints are applied.

    Returns {service: {cpu_limit_millicores, cpu_request_millicores,
    replica_count}}. Missing/unparseable CPU values are None. Services
    with no matching Deployment (or on any kubectl/JSON failure) are
    simply omitted.
    """
    master = cfg["infra"]["master_ssh_host"]
    r = ssh(master, "kubectl get deploy -n default -o json", check=False)
    try:
        data = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        data = {}

    capacity = {}
    for item in data.get("items", []):
        name = (item.get("metadata") or {}).get("name")
        if name not in services:
            continue
        spec = item.get("spec") or {}
        containers = ((spec.get("template") or {}).get("spec") or {}).get("containers", [])
        resources = containers[0].get("resources", {}) if containers else {}
        limits = resources.get("limits", {}) or {}
        requests = resources.get("requests", {}) or {}
        capacity[name] = {
            "cpu_limit_millicores": parse_cpu_to_millicores(limits.get("cpu")),
            "cpu_request_millicores": parse_cpu_to_millicores(requests.get("cpu")),
            "replica_count": int(spec.get("replicas", 1)),
        }
    return capacity
```

- [ ] **Step 4: Run tests to verify the capacity-parsing tests pass**

Run: `cd experiments; python -m unittest test_run_scenario.TestServiceCapacity.test_parse_cpu_to_millicores_variants test_run_scenario.TestServiceCapacity.test_capture_service_capacity_parses_deployment_json test_run_scenario.TestServiceCapacity.test_capture_service_capacity_handles_bad_json -v`
Expected: all PASS. (The two `collect_results` tests still fail — that's Step 5/6.)

- [ ] **Step 5: Wire `capacity` through `collect_results` and `run()`**

In `collect_results` (roughly lines 830–863), change the signature and add the write:

```python
def collect_results(cfg: dict, capacity: dict | None = None) -> str:
    banner("Collecting results")
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    results_base = cfg["infra"]["results_base_path"]
    log_folder = cfg["log_folder"]
    dest = f"{results_base}/{log_folder}"

    ssh(master, f"mkdir -p {dest}")
    ssh(master, f"cp -r {src}/logs/. {dest}/ 2>/dev/null; true", check=False)

    manifest = {
        "scenario_id":   cfg["scenario_id"],
        "scenario_name": cfg["scenario_name"],
        "condition":     cfg["condition"],
        "run_number":    cfg["run_number"],
        "duration_seconds": cfg["duration_seconds"],
        "retryguard":    cfg["retryguard"],
        "envoy_retry_collector": cfg.get("envoy_retry_collector", {}),
        "resource_usage_collector": cfg.get("resource_usage_collector", {}),
        "scale_constraints": cfg.get("scale_constraints", []),
        "log_folder":    log_folder,
        "collected_at":  datetime.utcnow().isoformat() + "Z",
    }
    write_remote_json(master, f"{dest}/run_manifest.json", manifest)
    write_remote_json(master, f"{dest}/service_capacity.json", capacity or {})

    step(f"Results saved to (on master): {dest}")
    step("To pull results to your PC:")
    scen_dir = scenario_dir_name(cfg)
    local_dest = f"experiments/results/campaign_48/{scen_dir}/" if scen_dir else "experiments/results/campaign_48/"
    print(f"    scp -r topfull-master:{dest} {local_dest}")
    return dest
```

Then in `run()` (roughly lines 870–987), initialize `capacity` alongside `restore_records` before the `try`, capture it right after `clear_logs(cfg)` and before `apply_constraints(cfg)`, and pass it to `collect_results`:

```python
    restore_records = []
    capacity = {}
    start_ts = datetime.now()

    try:
        preflight(cfg)
        clear_logs(cfg)
        capacity = capture_service_capacity(cfg, ALL_BOUTIQUE_SERVICES)
        restore_records = apply_constraints(cfg)

        start_master_stack(cfg)
        ...
```

And in the `finally` block, change:

```python
        collect_results(cfg)
```

to:

```python
        collect_results(cfg, capacity)
```

- [ ] **Step 6: Run tests to verify everything passes**

Run: `cd experiments; python test_run_scenario.py -v`
Expected: all tests PASS, including the two `collect_results` capacity tests from Step 1.

- [ ] **Step 7: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat(run-scenario): snapshot per-service CPU/replica capacity into service_capacity.json"
```

---

## Task 5: Update docs to reflect the implementation

**Files:**
- Modify: `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md` ("Status" section at the bottom)
- Modify: `Guides and Info/METRICS-GATHERED.md` (add the three new outputs)
- Modify: `AGENTS.md` (§4 "Current status")

**Interfaces:** None (docs only).

- [ ] **Step 1: Update the design doc's Status section**

In `Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md`, replace the final `## Status` section with:

```markdown
## Status

**Implemented (2026-09-08).** `experiments/envoy_retry_collector.py` now scrapes
all 11 Boutique pods every poll (outbound `upstream_rq_*` **and** inbound
`downstream_rq_*`), writing `service_edges.csv` (`timestamp, caller, target,
total, 2xx, 4xx, 5xx, retry`) and `service_inbound.csv` (`timestamp, service,
total, 2xx, 4xx, 5xx`) into the run's `record_path`. `run_scenario.py` patches
the widened `sidecar.istio.io/statsInclusionRegexps` annotation
(`(cluster\.outbound.*upstream_rq.*)|(http\.inbound.*downstream_rq.*)`) onto
all 11 Deployments before every run (idempotent, not restored — see
`experiments/run_scenario.py::ensure_envoy_stats_enabled`), and snapshots each
service's original CPU limit/request/replica count into
`service_capacity.json` before any `scale_constraints` are applied
(`experiments/run_scenario.py::capture_service_capacity`).

**No backfill.** As before, this does not apply to any existing run —
`campaign_48/` and `august_38/` still have only the old
`envoy_retries_{frontend,checkoutservice}.csv` shape (2 callers, outbound
retries only, no inbound, no capacity snapshot). A **new run** is required to
get `service_edges.csv` / `service_inbound.csv` / `service_capacity.json`.

**Follow-up (not done here):** `experiments/mentor_charts.py` /
`mentor_charts_data.py` still only read the legacy
`envoy_retries_{caller}.csv` shape for chart generation. Wiring them to also
read `service_edges.csv` / `service_inbound.csv` for future campaigns is a
separate task.
```

- [ ] **Step 2: Add the new outputs to METRICS-GATHERED.md**

Read `Guides and Info/METRICS-GATHERED.md` first to find where `envoy_retries_*.csv` is documented, then add a new subsection right after it describing `service_edges.csv`, `service_inbound.csv`, and `service_capacity.json` with their columns and the caveat that they only exist in runs launched after this plan lands (not in `campaign_48/`/`august_38/`).

- [ ] **Step 3: Update AGENTS.md §4**

In `AGENTS.md`, under "❌ Not done yet — remaining work" or "✅ Done" (whichever fits given what's actually been executed by the time this step runs), add one bullet noting: full-mesh Envoy collector (`service_edges.csv`/`service_inbound.csv`) + `service_capacity.json` implemented in `envoy_retry_collector.py`/`run_scenario.py`, unit-tested, live-smoke-tested (Task 6), but **no campaign run yet uses it** — the next new run (not yet scheduled) will be the first with this data.

- [ ] **Step 4: Commit**

```bash
git add "Guides and Info/PER-SERVICE-MESH-COLLECTOR-DESIGN.md" "Guides and Info/METRICS-GATHERED.md" AGENTS.md
git commit -m "docs: mark per-service mesh collector as implemented"
```

---

## Task 6: Live validation against the real cluster

**Files:** None (no code changes — this task only runs commands against `topfull-master`/`topfull-worker-1` and inspects output; if the live regex doesn't match real Envoy stat names, come back and fix `OUTBOUND_RE`/`INBOUND_RE` in Task 1's code and re-run its tests before re-attempting this task).

**Interfaces:** None.

- [ ] **Step 1: Confirm cluster health**

Run: `ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"`
Expected: all nodes `Ready`, all Boutique pods `Running` (2/2 with sidecar). If not, follow `Guides and Info/CONNECT-VMS.md` / `SETUP-GUIDE.md` troubleshooting before continuing — do not proceed against an unhealthy cluster.

- [ ] **Step 2: Clear stale `/tmp` runner scripts**

Run: `ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_locust_launch.sh /tmp/envoy_stats_patch.json"`
Expected: exit code 0 (no-op if files don't exist, per `AGENTS.md` §6).

- [ ] **Step 3: Manually patch two Deployments with the widened regex and confirm it applies cleanly**

Run:
```powershell
ssh topfull-master "kubectl patch deployment frontend -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/statsInclusionRegexps\":\"(cluster\\.outbound.*upstream_rq.*)|(http\\.inbound.*downstream_rq.*)\"}}}}}'"
ssh topfull-master "kubectl rollout status deployment/frontend -n default --timeout=60s"
ssh topfull-master "kubectl patch deployment checkoutservice -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/statsInclusionRegexps\":\"(cluster\\.outbound.*upstream_rq.*)|(http\\.inbound.*downstream_rq.*)\"}}}}}'"
ssh topfull-master "kubectl rollout status deployment/checkoutservice -n default --timeout=60s"
```
Expected: both rollouts complete successfully (`deployment "..." successfully rolled out`).

- [ ] **Step 4: Confirm the annotation actually unhides `downstream_rq_*` stats**

Run: `ssh topfull-master "kubectl exec deploy/frontend -c istio-proxy -n default -- curl -s http://localhost:15000/stats | grep downstream_rq | head -20"`
Expected: non-empty output containing lines like `http.inbound_0.0.0.0_8080.downstream_rq_total: <N>`. **If the listener-id format differs from `<ip>_<port>`** (e.g. no IP prefix, or a different separator), note the actual format and update `INBOUND_RE` in `experiments/envoy_retry_collector.py` (Task 1) to match, then re-run `python experiments/test_envoy_retry_collector.py` before continuing.

Also run: `ssh topfull-master "kubectl exec deploy/checkoutservice -c istio-proxy -n default -- curl -s http://localhost:15000/stats | grep upstream_rq | head -20"`
Expected: non-empty output with `cluster.outbound|...upstream_rq_*` lines for `checkoutservice`'s call targets (cartservice, productcatalogservice, currencyservice, shippingservice, paymentservice, emailservice).

- [ ] **Step 5: Deploy the updated collector and run it standalone for a short window**

```powershell
scp experiments/envoy_retry_collector.py topfull-master:/tmp/envoy_retry_collector_test.py
```
```
ssh topfull-master "cat > /tmp/envoy_retry_test_params.json <<'EOF'
{\"poll_interval_seconds\": 3, \"services\": [\"frontend\", \"checkoutservice\"]}
EOF"
```
Then, in a foreground SSH session (or via `timeout`), run it for ~15 seconds and stop it:
Run: `ssh topfull-master "source /home/idozacharia/TopFull/venv/bin/activate 2>/dev/null; timeout 15 python3 /tmp/envoy_retry_collector_test.py --params /tmp/envoy_retry_test_params.json; true"`
Expected: log lines showing `START` and at least 3–4 poll cycles before `timeout` kills it; no tracebacks.

- [ ] **Step 6: Verify the output CSVs on master**

Run: `ssh topfull-master "cat /home/idozacharia/experiments/results/*/service_edges.csv 2>/dev/null | tail -20; echo ---; cat /home/idozacharia/experiments/results/*/service_inbound.csv 2>/dev/null | tail -20"`

(If `record_path` from `global_config.json` doesn't point where expected, run `ssh topfull-master "cat /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/global_config.json"` first to find the actual `record_path`, then `ls` that directory instead.)

Expected: `service_edges.csv` has the header `timestamp,caller,target,total,2xx,4xx,5xx,retry` with rows for `frontend`/`checkoutservice` as `caller`; `service_inbound.csv` has header `timestamp,service,total,2xx,4xx,5xx` with rows for both services. Row values may legitimately be all-zero if no Locust traffic was running during this smoke test — that's fine, the goal here is confirming the scrape/parse/write mechanism works end-to-end, not exercising real load. (A full non-zero validation happens naturally the next time any scenario is actually run with `envoy_retry_collector.enabled: true`.)

- [ ] **Step 7: Clean up test artifacts**

Run: `ssh topfull-master "rm -f /tmp/envoy_retry_collector_test.py /tmp/envoy_retry_test_params.json"`

- [ ] **Step 8: Re-apply the full annotation patch to all 11 Deployments (not just the 2 tested above) so the next real run doesn't do a first-time rollout mid-experiment**

Run the same `kubectl patch` + `kubectl rollout status` pair from Step 3 for the remaining 9 services: `cartservice`, `productcatalogservice`, `paymentservice`, `recommendationservice`, `shippingservice`, `currencyservice`, `emailservice`, `adservice`, `redis-cart`. (This is exactly what `ensure_envoy_stats_enabled(cfg, ALL_BOUTIQUE_SERVICES)` will also do automatically on the next `run_scenario.py` invocation — doing it now just avoids paying that one-time rollout latency during a real timed scenario run later.)

Expected: all 9 additional rollouts succeed.

- [ ] **Step 9: No commit needed**

This task only touches the live cluster, not the repo. If Step 4 required a regex fix in Task 1, that fix was already committed there — nothing further to commit here.

---

## Plan Self-Review Notes

- **Spec coverage:** Design doc items (a)–(e) → `parse_edges`/`parse_inbound` (Task 1) cover outgoing retries (a), outgoing goodput (c), incoming goodput (d), offered load (e) directly as columns; incoming retries (b) is explicitly *not* a stored column (per the design doc itself — "not a real Envoy counter", computed later by grouping `service_edges.csv` on `target`). "Everyone scrapes everyone" (dropping `CALLER_TARGET_MAP`) → Task 1/2. Stats-inclusion patch on all Deployments + broadened regex → Task 3. Capacity snapshot → Task 4. Same-timestamp-per-poll discipline → already satisfied by `poll_once` calling `parse_edges`/`parse_inbound`/writes with one shared `timestamp` argument per cycle (Task 2), same pattern as the pre-existing collector.
- **Placeholder scan:** no TBD/TODO left in any step; every step has literal file paths, literal code, and literal expected command output.
- **Type consistency:** `services: List[str]` used consistently across `resolve_services`, `poll_once`, `run_collector` (Task 2) and `ALL_BOUTIQUE_SERVICES` / `capture_service_capacity(cfg, services)` (Tasks 3–4); `capacity: dict` flows unchanged from `capture_service_capacity` → `run()` → `collect_results(cfg, capacity)`.
- **Scope check:** deliberately excludes updating `mentor_charts.py`/`mentor_charts_data.py` (called out as an explicit non-goal in Global Constraints and Task 5) and excludes running a full paper-grade campaign with the new collector (Task 6 only smoke-tests the mechanism) — both are reasonable follow-ups, not blockers for "the design is implemented."
