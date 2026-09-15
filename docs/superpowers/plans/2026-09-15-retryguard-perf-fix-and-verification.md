# RetryGuard Perf Fix + Master-Node Visibility + Re-Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix RetryGuard's per-tick full-CSV-reparse inefficiency, give the metrics stack visibility into master's own CPU/memory, then re-run `S2_sustained_overload` RetryGuard to check whether the `run10`-style mid-run collector restart and ~2x P95 gap reproduce.

**Architecture:** Task 1 implements [2026-09-15-retryguard-inbound-csv-tailer-design.md](../specs/2026-09-15-retryguard-inbound-csv-tailer-design.md) — an incremental tailer replacing 9 full-file re-parses/second with one incremental read/second. Task 2 extends the already-running `resource_usage_collector.py` to also poll the **master** node's own kubelet `stats/summary` (not just the worker's Boutique pods), writing one extra pseudo-service row per poll so we can finally see master's CPU/memory during a run instead of inferring contention from collector timeouts. Task 3 is operational: start the VMs, re-run `S2_sustained_overload` RetryGuard (config is already parked at the next free slot, `run11`) back-to-back with a fresh baseline (`run22`), and compare against `run10`/`run21`.

**Tech Stack:** Python 3 (stdlib `csv`, `json`, `subprocess`), `unittest`, existing `run_scenario.py` orchestrator (PowerShell/SSH), no new dependencies.

## Global Constraints

- Do not change Algorithm 1 (`apply_algorithm1`), `interval_samples`, `rejection_threshold`, or the `Δ(5xx+resets)/Δtotal` formula — this plan only touches I/O efficiency and observability.
- Do not modify `read_latest_inbound_row()` — it stays as-is for `experiments/test_retryguard.py`'s existing `TestReadLatestInboundRow` coverage; only the hot loop in `run()` stops calling it.
- Never reuse a `run_number` / `log_folder` already used by `campaign_48/` or `august_38/`. Before Task 3, re-check `experiments/configs/scenario_2_baseline.yaml` and `scenario_2_retryguard.yaml` still say `run22` / `run11` (they did as of 2026-09-15 — confirm again in case another session bumped them since).
- Follow `.cursor/rules/topfull-ssh.mdc`: always use SSH host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`), never hardcode IPs.
- VMs cost money while running — Task 3 starts them; stop them again at the end of Task 3 unless the user says otherwise.
- Update `AGENTS.md` §4 ("Current status") after Task 3 completes, per its own "Keeping this file useful" instruction.

---

### Task 1: `InboundCsvTailer` — incremental read of `service_inbound.csv`

**Files:**
- Modify: `experiments/retryguard.py`
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Produces: `InboundCsvTailer` class with `__init__(self, csv_path: Path)` and `poll(self) -> None`, exposing `self.latest: Dict[str, InboundSnapshot]`.
- Consumes: `InboundSnapshot` dataclass (already defined in `retryguard.py`, unchanged).

- [ ] **Step 1: Write the failing tests for `InboundCsvTailer`**

Add to `experiments/test_retryguard.py`, after the existing `TestReadLatestInboundRow` class:

```python
class TestInboundCsvTailer(unittest.TestCase):
    def test_missing_file_is_a_noop(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(tailer.latest, {})

    def test_picks_up_rows_written_before_construction(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:00:00Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 100.0)

    def test_second_poll_only_advances_for_new_rows(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            offset_after_first = tailer._offset

            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
                writer.writerow(
                    _row("2026-09-15T10:00:01Z", "checkoutservice", 180, 40)
                )
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:00:01Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 180.0)
            self.assertGreater(tailer._offset, offset_after_first)

    def test_poll_with_no_new_bytes_is_a_true_noop(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            offset_after_first = tailer._offset
            snapshot_after_first = tailer.latest["checkoutservice"]

            tailer.poll()  # no new bytes appended
            self.assertEqual(tailer._offset, offset_after_first)
            self.assertEqual(tailer.latest["checkoutservice"], snapshot_after_first)

    def test_file_shrinking_triggers_a_full_resync(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10),
                    _row("2026-09-15T10:00:01Z", "checkoutservice", 180, 40),
                ],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()
            self.assertEqual(
                tailer.latest["checkoutservice"].total, 180.0
            )

            # Simulate a collector restart recreating the file from scratch.
            _write_inbound(
                path,
                [_row("2026-09-15T10:05:00Z", "checkoutservice", 5, 0)],
            )
            tailer.poll()
            self.assertEqual(tailer._offset, path.stat().st_size)
            self.assertEqual(
                tailer.latest["checkoutservice"].timestamp, "2026-09-15T10:05:00Z"
            )
            self.assertEqual(tailer.latest["checkoutservice"].total, 5.0)

    def test_partial_trailing_line_is_buffered_and_completed_later(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [_row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10)],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()

            # Write a row without a trailing newline (writer mid-flush).
            with open(path, "a", newline="") as f:
                f.write("2026-09-15T10:00:01Z,checkoutservice,180,40,0,0,0")
            tailer.poll()
            # No newline yet -> not a complete row -> latest unchanged.
            self.assertEqual(tailer.latest["checkoutservice"].total, 100.0)

            with open(path, "a", newline="") as f:
                f.write("\n")
            tailer.poll()
            self.assertEqual(tailer.latest["checkoutservice"].total, 180.0)

    def test_multiple_services_interleaved_match_read_latest_inbound_row(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "service_inbound.csv"
            _write_inbound(
                path,
                [
                    _row("2026-09-15T10:00:00Z", "checkoutservice", 100, 10),
                    _row("2026-09-15T10:00:00Z", "paymentservice", 50, 5),
                ],
            )
            tailer = retryguard.InboundCsvTailer(path)
            tailer.poll()

            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=INBOUND_FIELDS)
                writer.writerow(
                    _row("2026-09-15T10:00:01Z", "paymentservice", 90, 9)
                )
            tailer.poll()

            for service in ("checkoutservice", "paymentservice"):
                expected = retryguard.read_latest_inbound_row(path, service)
                self.assertEqual(tailer.latest[service], expected)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m unittest experiments.test_retryguard.TestInboundCsvTailer -v`
Expected: `AttributeError: module 'retryguard' has no attribute 'InboundCsvTailer'` (or similar) — all 7 tests error/fail.

- [ ] **Step 3: Implement `InboundCsvTailer` in `retryguard.py`**

Add `import os` to the existing import block at the top of `experiments/retryguard.py` (next to `import csv`, `import json`, etc.). Then add this class right after `measure_inbound_rejection()` (i.e. after line ~192, before the `VirtualService patching` section header):

```python
class InboundCsvTailer:
    """
    Incrementally tails service_inbound.csv. Call poll() once per tick;
    read self.latest[service] afterward. latest always holds the most
    recently seen InboundSnapshot per service, even on ticks where no new
    row arrived. Never re-parses bytes already consumed. Safe to call
    poll() even if the file doesn't exist yet, or was truncated/recreated
    by a collector restart (auto-resyncs from scratch in that case).
    """

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.latest: Dict[str, InboundSnapshot] = {}
        self._offset = 0
        self._fieldnames: Optional[list] = None
        self._pending = ""

    def _reset(self) -> None:
        self._offset = 0
        self._fieldnames = None
        self._pending = ""
        self.latest = {}

    def _apply_line(self, line: str) -> None:
        if not line or self._fieldnames is None:
            return
        try:
            values = next(csv.reader([line]))
        except (csv.Error, StopIteration):
            return
        if len(values) != len(self._fieldnames):
            return
        row = dict(zip(self._fieldnames, values))
        if row.get("service") is None:
            return
        try:
            snapshot = InboundSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                five_xx=float(row["5xx"]),
                resets=float(row.get("resets", 0)),
            )
        except (KeyError, TypeError, ValueError):
            return
        self.latest[row["service"]] = snapshot

    def poll(self) -> None:
        try:
            size = self.csv_path.stat().st_size
        except OSError:
            return

        if size < self._offset:
            # Truncated or recreated (e.g. a collector restart) — resync.
            self._reset()

        try:
            with open(self.csv_path, "r", newline="") as f:
                if self._fieldnames is None:
                    header_line = f.readline()
                    if not header_line:
                        return  # empty file so far
                    try:
                        self._fieldnames = next(csv.reader([header_line.rstrip("\n")]))
                    except (csv.Error, StopIteration):
                        return
                    self._offset = f.tell()
                    self._pending = ""
                else:
                    f.seek(self._offset)

                chunk = f.read()
                self._offset = f.tell()
        except OSError:
            return

        if not chunk:
            return

        buf = self._pending + chunk
        lines = buf.split("\n")
        self._pending = lines.pop()  # trailing fragment (no newline yet)
        for line in lines:
            self._apply_line(line)
```

- [ ] **Step 4: Run the tests again to verify they pass**

Run: `python -m unittest experiments.test_retryguard.TestInboundCsvTailer -v`
Expected: all 7 tests `ok`.

- [ ] **Step 5: Run the full existing test file to verify no regressions**

Run: `python -m unittest experiments.test_retryguard -v`
Expected: every test (old `TestReadLatestInboundRow`, `TestMeasureInboundRejection`, `TestApplyAlgorithm1Symmetric`, etc., plus the 7 new ones) passes. `read_latest_inbound_row()` itself is untouched, so its tests must still pass unchanged.

- [ ] **Step 6: Wire the tailer into the hot loop**

In `experiments/retryguard.py`'s `run()` function, replace:

```python
    inbound_path = record_path / INBOUND_CSV_NAME
```

with:

```python
    inbound_path = record_path / INBOUND_CSV_NAME
    tailer = InboundCsvTailer(inbound_path)
```

(directly below the existing `inbound_path = ...` line — keep that line, just add the new one after it). Then replace the loop body:

```python
        for service in CONTROLLED_SERVICES:
            current = read_latest_inbound_row(inbound_path, service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
```

with:

```python
        tailer.poll()
        for service in CONTROLLED_SERVICES:
            current = tailer.latest.get(service)
            rejection, previous[service] = measure_inbound_rejection(
                previous[service], current
            )
```

- [ ] **Step 7: Re-run the full test suite one more time**

Run: `python -m unittest experiments.test_retryguard -v`
Expected: all tests still pass (Step 6 only changed `run()`, which isn't unit-tested directly — this step is a final sanity pass after the wiring change).

- [ ] **Step 8: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py docs/superpowers/specs/2026-09-15-retryguard-inbound-csv-tailer-design.md
git commit -m "fix(retryguard): tail service_inbound.csv incrementally instead of re-parsing it 9x/sec"
```

---

### Task 2: Master-node CPU/memory visibility in `resource_usage_collector.py`

**Files:**
- Modify: `experiments/resource_usage_collector.py`
- Test: create `experiments/test_resource_usage_collector.py` (does not exist yet — no prior test file for this collector)

**Interfaces:**
- Produces: `discover_master_node(run_cmd=None) -> Optional[str]`, `parse_node_level_usage(summary: dict) -> Tuple[int, int]`, and a new pseudo-service label `MASTER_NODE_SERVICE_LABEL = "__master_node__"` written into the same `resource_usage.csv` (same 5 columns: `timestamp, service, cpu_millicores, memory_working_set_bytes, replica_count` — `replica_count` is always `1` for this row).
- Consumes: existing `_container_usage(container: dict) -> Tuple[int, int]` (unchanged — the kubelet `stats/summary` top-level `"node"` object has the same `{"cpu": {"usageNanoCores": ...}, "memory": {"workingSetBytes": ...}}` shape as a container entry, so it's reused as-is), existing `write_csv_rows()`, existing `fetch_stats_summary(node_name, run_cmd)`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_resource_usage_collector.py`:

```python
"""
test_resource_usage_collector.py — Unit tests for the master-node CPU/memory
sampling added to resource_usage_collector.py (Task 2 of the 2026-09-15
retryguard-perf-fix-and-verification plan). Pure-logic tests only — no
kubectl/network access.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import resource_usage_collector as ruc  # noqa: E402


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestDiscoverMasterNode(unittest.TestCase):
    def test_returns_the_control_plane_labeled_node(self):
        nodes_json = {
            "items": [
                {
                    "metadata": {
                        "name": "topfull-worker-1",
                        "labels": {},
                    },
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                },
                {
                    "metadata": {
                        "name": "topfull-master",
                        "labels": {
                            "node-role.kubernetes.io/control-plane": ""
                        },
                    },
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                },
            ]
        }

        import json

        def fake_run_cmd(cmd):
            return _FakeResult(stdout=json.dumps(nodes_json))

        self.assertEqual(
            ruc.discover_master_node(run_cmd=fake_run_cmd), "topfull-master"
        )

    def test_returns_none_when_no_control_plane_node_is_ready(self):
        nodes_json = {
            "items": [
                {
                    "metadata": {"name": "topfull-worker-1", "labels": {}},
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}]
                    },
                }
            ]
        }

        import json

        def fake_run_cmd(cmd):
            return _FakeResult(stdout=json.dumps(nodes_json))

        self.assertIsNone(ruc.discover_master_node(run_cmd=fake_run_cmd))


class TestParseNodeLevelUsage(unittest.TestCase):
    def test_extracts_node_level_cpu_and_memory(self):
        summary = {
            "node": {
                "cpu": {"usageNanoCores": 937000000},
                "memory": {"workingSetBytes": 2147483648},
            },
            "pods": [],
        }
        cpu_mc, mem_bytes = ruc.parse_node_level_usage(summary)
        self.assertEqual(cpu_mc, 937)
        self.assertEqual(mem_bytes, 2147483648)

    def test_missing_node_key_returns_zeros(self):
        cpu_mc, mem_bytes = ruc.parse_node_level_usage({"pods": []})
        self.assertEqual((cpu_mc, mem_bytes), (0, 0))


class TestPollOnceWritesMasterRow(unittest.TestCase):
    def test_master_row_is_written_alongside_service_rows(self):
        import json
        from tempfile import TemporaryDirectory

        worker_summary = {
            "node": {"cpu": {"usageNanoCores": 0}, "memory": {"workingSetBytes": 0}},
            "pods": [
                {
                    "podRef": {"name": "cartservice-abc123", "namespace": "default"},
                    "containers": [
                        {
                            "name": "server",
                            "cpu": {"usageNanoCores": 5000000},
                            "memory": {"workingSetBytes": 1000},
                        }
                    ],
                }
            ],
        }
        master_summary = {
            "node": {
                "cpu": {"usageNanoCores": 937000000},
                "memory": {"workingSetBytes": 2000000000},
            },
            "pods": [],
        }

        calls = {"n": 0}

        def fake_run_cmd(cmd):
            # kubectl get nodes -o json
            if cmd[:3] == ["kubectl", "get", "nodes"]:
                nodes_json = {
                    "items": [
                        {
                            "metadata": {
                                "name": "topfull-worker-1",
                                "labels": {},
                            },
                            "status": {
                                "conditions": [
                                    {"type": "Ready", "status": "True"}
                                ]
                            },
                        },
                        {
                            "metadata": {
                                "name": "topfull-master",
                                "labels": {
                                    "node-role.kubernetes.io/control-plane": ""
                                },
                            },
                            "status": {
                                "conditions": [
                                    {"type": "Ready", "status": "True"}
                                ]
                            },
                        },
                    ]
                }
                return _FakeResult(stdout=json.dumps(nodes_json))
            if cmd[:3] == ["kubectl", "get", "--raw"] and "topfull-worker-1" in cmd[3]:
                return _FakeResult(stdout=json.dumps(worker_summary))
            if cmd[:3] == ["kubectl", "get", "--raw"] and "topfull-master" in cmd[3]:
                return _FakeResult(stdout=json.dumps(master_summary))
            if cmd[:3] == ["kubectl", "get", "deploy"]:
                return _FakeResult(stdout=json.dumps({"items": []}))
            calls["n"] += 1
            return _FakeResult(returncode=1)

        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            ruc.poll_once(
                record_path,
                ["cartservice"],
                timestamp="2026-09-15T10:00:00Z",
                run_cmd=fake_run_cmd,
                node_cache={},
            )
            rows = (record_path / "resource_usage.csv").read_text().splitlines()
            self.assertIn("cartservice", rows[1])
            self.assertTrue(
                any(ruc.MASTER_NODE_SERVICE_LABEL in row for row in rows[1:])
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m unittest experiments.test_resource_usage_collector -v`
Expected: `AttributeError: module 'resource_usage_collector' has no attribute 'discover_master_node'` (and similarly for `parse_node_level_usage`, `MASTER_NODE_SERVICE_LABEL`) — all new tests error.

- [ ] **Step 3: Add the master-node constant and discovery function**

In `experiments/resource_usage_collector.py`, add this constant right after `SKIP_CONTAINER_NAMES` (near line 50):

```python
MASTER_NODE_SERVICE_LABEL = "__master_node__"
```

Add `discover_master_node()` right after `discover_worker_node()` (after its closing `return fallback[0] if fallback else None` line):

```python
def discover_master_node(
    run_cmd: Optional[CommandRunner] = None,
) -> Optional[str]:
    """Return the first Ready control-plane node name, or None if none is Ready."""
    runner = run_cmd or default_run_cmd
    cmd = ["kubectl", "get", "nodes", "-o", "json"]
    try:
        result = runner(cmd)
    except Exception as exc:  # noqa: BLE001
        log.warning("%s  WARNING  discover master node failed: %s", utc_now(), exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        return None

    try:
        data = json.loads(getattr(result, "stdout", "") or "{}")
    except json.JSONDecodeError as exc:
        log.warning("%s  WARNING  nodes JSON parse failed: %s", utc_now(), exc)
        return None

    for item in data.get("items") or []:
        name = (item.get("metadata") or {}).get("name")
        if not name:
            continue
        labels = (item.get("metadata") or {}).get("labels") or {}
        ready = any(
            cond.get("type") == "Ready" and cond.get("status") == "True"
            for cond in (item.get("status") or {}).get("conditions") or []
        )
        if not ready:
            continue
        is_control_plane = any(
            k.startswith("node-role.kubernetes.io/control-plane")
            or k.startswith("node-role.kubernetes.io/master")
            for k in labels
        )
        if is_control_plane:
            return name
    return None
```

- [ ] **Step 4: Add `parse_node_level_usage()`**

Add right after `parse_stats_summary()` (after its `return totals` line):

```python
def parse_node_level_usage(summary: dict) -> Tuple[int, int]:
    """
    Extract node-level (not per-pod) CPU/memory from a stats/summary
    response's top-level "node" object. Used for master's own usage,
    where we don't care about individual system pods — just the whole
    node's CPU/memory, the same numbers `kubectl top node` would show.
    """
    node = summary.get("node") or {}
    return _container_usage(node)
```

- [ ] **Step 5: Wire master-node polling into `poll_once()`**

Replace the body of `poll_once()`:

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    node_cache: Optional[Dict[str, str]] = None,
) -> None:
    if node_cache is None:
        node_cache = {}

    runner = run_cmd or default_run_cmd
    node = node_cache.get("worker")
    if not node:
        node = discover_worker_node(run_cmd=runner)
        if node:
            node_cache["worker"] = node
        else:
            log.warning("%s  WARNING  no worker node discovered", utc_now())
            return

    summary = fetch_stats_summary(node, run_cmd=runner)
    if summary is None:
        node_cache.pop("worker", None)
        return

    usage = parse_stats_summary(summary, services)
    deploy_json = fetch_deployments_json(run_cmd=runner) or {}
    replicas = parse_replica_counts(deploy_json, services)

    csv_path = record_path / "resource_usage.csv"
    written = write_csv_rows(csv_path, timestamp, usage, replicas, services)
    if written == 0:
        log.warning(
            "%s  WARNING  no service rows written (pods=%d)",
            utc_now(),
            len(summary.get("pods") or []),
        )
```

with:

```python
def poll_once(
    record_path: Path,
    services: List[str],
    timestamp: str,
    run_cmd: Optional[CommandRunner] = None,
    node_cache: Optional[Dict[str, str]] = None,
) -> None:
    if node_cache is None:
        node_cache = {}

    runner = run_cmd or default_run_cmd
    node = node_cache.get("worker")
    if not node:
        node = discover_worker_node(run_cmd=runner)
        if node:
            node_cache["worker"] = node
        else:
            log.warning("%s  WARNING  no worker node discovered", utc_now())
            return

    summary = fetch_stats_summary(node, run_cmd=runner)
    if summary is None:
        node_cache.pop("worker", None)
        return

    usage = parse_stats_summary(summary, services)
    deploy_json = fetch_deployments_json(run_cmd=runner) or {}
    replicas = parse_replica_counts(deploy_json, services)

    master_node = node_cache.get("master")
    if not master_node:
        master_node = discover_master_node(run_cmd=runner)
        if master_node:
            node_cache["master"] = master_node
        else:
            log.warning("%s  WARNING  no control-plane node discovered", utc_now())

    all_services = list(services)
    if master_node:
        master_summary = fetch_stats_summary(master_node, run_cmd=runner)
        if master_summary is None:
            node_cache.pop("master", None)
        else:
            cpu_mc, mem_bytes = parse_node_level_usage(master_summary)
            usage[MASTER_NODE_SERVICE_LABEL] = (cpu_mc, mem_bytes)
            replicas[MASTER_NODE_SERVICE_LABEL] = 1
            all_services = all_services + [MASTER_NODE_SERVICE_LABEL]

    csv_path = record_path / "resource_usage.csv"
    written = write_csv_rows(csv_path, timestamp, usage, replicas, all_services)
    if written == 0:
        log.warning(
            "%s  WARNING  no service rows written (pods=%d)",
            utc_now(),
            len(summary.get("pods") or []),
        )
```

- [ ] **Step 6: Run the tests again to verify they pass**

Run: `python -m unittest experiments.test_resource_usage_collector -v`
Expected: all 4 tests `ok`.

- [ ] **Step 7: Sanity-check `resolve_services()` callers aren't affected**

Run: `python -m unittest experiments.test_retryguard experiments.test_resource_usage_collector -v` (if `test_run_scenario.py` exists and imports `resource_usage_collector`, include it too: `python -m unittest experiments.test_retryguard experiments.test_resource_usage_collector experiments.test_run_scenario -v`)
Expected: everything passes — `MASTER_NODE_SERVICE_LABEL` (`"__master_node__"`) can't collide with any real Boutique deployment name, so `DEFAULT_SERVICES`/`resolve_services()` and downstream chart/analysis code that filters by known service names is unaffected; it just gains one extra row per poll that existing readers will ignore unless they specifically look for it.

- [ ] **Step 8: Commit**

```bash
git add experiments/resource_usage_collector.py experiments/test_resource_usage_collector.py
git commit -m "feat(resource_usage_collector): also sample master node's own CPU/memory"
```

---

### Task 3: Re-run S2 RetryGuard and compare against `run10`/`run21`

**Files:**
- None modified — this task runs the fixed code from Tasks 1–2 live and records results under `experiments/results/campaign_48/S2_sustained_overload/`.
- Modify (at the end): `AGENTS.md` (§4 "Current status")

**Interfaces:**
- Consumes: `experiments/run_scenario.py`, `experiments/configs/scenario_2_baseline.yaml` (already at `run22`), `experiments/configs/scenario_2_retryguard.yaml` (already at `run11`).
- Produces: `experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run22/` and `.../run_topfull_retryguard_sustained_overload_run11/`, each now including a `service=__master_node__` row per poll in `resource_usage.csv` (Task 2).

> **Pre-req done ahead of time (2026-09-15, before Tasks 1–2 were implemented):** VMs were started early so they're warm by the time this task runs, rather than eating ~2-3 min of boot/API-server-recovery time mid-task. If Tasks 1–2 take long enough that the VMs might have been stopped again in between (e.g. a new session, or someone ran `gcloud compute instances stop`), just redo Step 1 — it's idempotent (`gcloud ... list` first; only `start` if `TERMINATED`).
>
> What was done: `gcloud compute instances start topfull-master topfull-worker-1 topfull-load --project=networks-workshop --zone=us-central1-a`, then `~/.ssh/config`'s three `HostName` lines updated to the fresh IPs (master `34.41.126.95`, worker `34.60.212.68`, load `34.69.195.113` as of this start — **will be different** if the VMs get stopped/started again; always re-check with `gcloud compute instances list` rather than trusting these specific IPs). Cluster health was verified healthy: `kubectl get nodes` → both `topfull-master` / `topfull-worker1` `Ready`; `kubectl get pods -n default` → all 11 Boutique pods `2/2 Running` (adservice needed ~40s longer than the rest — its sidecar readiness probe failed a few times right after the cold boot before settling; that's normal, not a fix-required issue); `kubectl get virtualservices -n default` → all 9 present. Stale `/tmp/rg_*.sh` runner scripts on master were also cleared already. **Known noise, not a problem:** `kubectl` commands print `metrics.k8s.io/v1beta1` `memcache` errors for the first minute or two after a cold boot — the metrics-server pod just hasn't come up yet; this clears on its own and does not block `run_scenario.py` (which doesn't depend on the metrics API).

- [ ] **Step 1: Confirm VM state and refresh SSH config (skip the `start` if already running from the pre-req above)**

```powershell
gcloud compute instances list --project=networks-workshop --format="table(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

If any of `topfull-master` / `topfull-worker-1` / `topfull-load` show `TERMINATED`:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --project=networks-workshop --zone=us-central1-a
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update the three `HostName` lines in `~/.ssh/config` (`C:\Users\idoza\.ssh\config`) with the fresh IPs (per [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md)). Give the control plane 1-2 minutes after a cold boot before trusting a `kubectl` failure — `kube-apiserver`'s static pod container commonly exits once and restarts clean on the first real boot after a stop; check with `ssh topfull-master "sudo docker ps -a | grep kube-apiserver"` if in doubt (look for one entry `Up ...`, ignore older `Exited` ones from before the stop).

- [ ] **Step 2: Verify cluster health**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`, all Boutique pods `Running` (2/2 with sidecar — give a newly-restarted pod ~30-60s if it briefly shows `1/2`), 9 VirtualServices present with default `retries.attempts: 3`. If `kubectl` fails with `connection to localhost:8080 refused` for more than ~2-3 minutes, follow the multi-user kubeconfig fix in `AGENTS.md` §7 (or [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md)) before continuing.

- [ ] **Step 3: Clear stale `/tmp` runner scripts on master (skip if already done from the pre-req above)**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

- [ ] **Step 4: Confirm the YAML slots are still free**

```powershell
Select-String -Path "experiments\configs\scenario_2_baseline.yaml" -Pattern "run_number|log_folder"
Select-String -Path "experiments\configs\scenario_2_retryguard.yaml" -Pattern "run_number|log_folder"
```

Expected: `run_number: 22` / `baseline_topfull_no_retryguard_sustained_overload_run22` and `run_number: 11` / `run_topfull_retryguard_sustained_overload_run11`. If a different session already bumped these, use whatever the *current* free slot is instead — do not overwrite an existing folder.

- [ ] **Step 5: Run S2 baseline (fresh reference point, same machine sizes as `run21`)**

```powershell
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
```

Wait for completion (~600s + setup/teardown). Confirm success:

```powershell
Get-ChildItem "experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run22"
```

Expected: same file set as `run21` (Locust CSVs, `resource_usage.csv` — now with `__master_node__` rows, `service_inbound.csv`, etc.).

- [ ] **Step 6: Cool off 5 minutes, then run S2 RetryGuard**

```powershell
Start-Sleep -Seconds 300
python experiments/run_scenario.py experiments/configs/scenario_2_retryguard.yaml
```

- [ ] **Step 7: Check for the `run10`-style mid-run restart signature**

```powershell
$dir = "experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run11"
foreach ($f in @("retryguard.log","envoy_retry_collector.log","resource_usage_collector.log","topfull_throttle_collector.log")) {
    Write-Host "--- $f ---"
    Select-String -Path "$dir\$f" -Pattern "START|WAITING|READY|SHUTDOWN|EXIT"
}
```

Expected (fix working / incident did not recur): exactly one `START` (or `WAITING`→`READY`→`START`) block per file, at the beginning, and one `SHUTDOWN`/`EXIT` at the very end — no mid-file restart.
If a restart signature **does** reappear: the fix in Task 1 reduced RetryGuard's own CPU/disk footprint but did not eliminate the incident — treat this as a separate, still-open investigation (see the master-node CPU/memory data from Task 2's new `__master_node__` rows, captured next in Step 8, as the next diagnostic input) rather than a Task 1 regression.

- [ ] **Step 8: Compare master-node CPU/memory and P95 against `run10`/`run21`**

```powershell
$r11 = Import-Csv "experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run11\resource_usage.csv" | Where-Object { $_.service -eq "__master_node__" }
$r22 = Import-Csv "experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run22\resource_usage.csv" | Where-Object { $_.service -eq "__master_node__" }
Write-Host "run11 (RG) master CPU max/mean (millicores):" ($r11 | ForEach-Object {[int]$_.cpu_millicores} | Measure-Object -Maximum -Average)
Write-Host "run22 (baseline) master CPU max/mean (millicores):" ($r22 | ForEach-Object {[int]$_.cpu_millicores} | Measure-Object -Maximum -Average)

$g11 = Import-Csv "experiments\results\campaign_48\S2_sustained_overload\run_topfull_retryguard_sustained_overload_run11\getcart.csv"
$g22 = Import-Csv "experiments\results\campaign_48\S2_sustained_overload\baseline_topfull_no_retryguard_sustained_overload_run22\getcart.csv"
Write-Host "run11 (RG) getcart P95 mean/median:" ($g11 | ForEach-Object {[double]$_.Latency95} | Measure-Object -Average).Average
Write-Host "run22 (baseline) getcart P95 mean/median:" ($g22 | ForEach-Object {[double]$_.Latency95} | Measure-Object -Average).Average
```

Record these numbers alongside `run10`'s (mean P95 ≈1256ms) and `run21`'s (mean P95 ≈633ms) for the writeup in Step 9.

- [ ] **Step 9: Write up findings and stop the VMs**

Append a dated entry to `Guides and Info/2026-09-15-TOPFULL-E2-16-RETRY-SUMMARY.md` (or a new dated doc if this session is on a different date) covering: whether the restart signature reproduced, the master-node CPU/memory numbers now visible via `__master_node__`, and the `run11` vs `run22` P95/goodput comparison vs `run10`/`run21`. Then:

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
```

- [ ] **Step 10: Update `AGENTS.md` and commit**

Update `AGENTS.md` §4 with a new bullet summarizing the outcome (per its own "keep this file useful" instruction), then:

```bash
git add "Guides and Info" AGENTS.md experiments/results/campaign_48
git commit -m "chore: re-run S2 RetryGuard (run11) + fresh baseline (run22) after retryguard.py perf fix"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 implements every part of [2026-09-15-retryguard-inbound-csv-tailer-design.md](../specs/2026-09-15-retryguard-inbound-csv-tailer-design.md) §3 (tailer class + `run()` wiring) and §4 (all 6 described test scenarios are present in Step 1's test list, plus the truncation/partial-line/multi-service-agreement cases).
- **Type consistency:** `InboundCsvTailer.latest` is `Dict[str, InboundSnapshot]` in both the spec and Task 1 Step 3; `tailer.latest.get(service)` in Task 1 Step 6 returns `Optional[InboundSnapshot]`, matching what `measure_inbound_rejection()` already expects as its `current` argument (no signature change needed there).
- **No placeholders:** every step has literal runnable code/commands; nothing deferred to "add appropriate handling."
- **Scope:** Tasks 1 and 2 are independent (2 is not needed for 1 to work) and each produces working, independently-testable code; Task 3 depends on both being merged first, which the task ordering enforces.
