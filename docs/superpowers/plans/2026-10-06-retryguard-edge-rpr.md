# RetryGuard edge-rpr mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `retry_metric: edge_rpr` mode to `experiments/retryguard.py` that disables retries per caller→callee edge on retries-per-request, and re-enables per callee on rejection rate.

**Architecture:** Reuse `apply_algorithm1` and `ServiceState`. A small pure `EdgeController` holds per-edge state and per-callee fallback state and returns proposed changes. `run_edge_rpr()` feeds it from two CSV tailers, patches the VirtualService with `sourceLabels` match routes, and commits state only after a successful patch. The default mode (`rejection`) is untouched.

**Tech Stack:** Python 3.8+ (stdlib `unittest`), kubernetes client, Istio VirtualService.

Spec: `docs/superpowers/specs/2026-10-06-retryguard-edge-rpr-design.md`. Terms: `CONTEXT.md` (Edge, Retries per request).

## Global Constraints

- `rpr = Δretry / (Δtotal − Δretry)`; a tick with 0 first attempts is skipped (no counter change).
- `retries_threshold = 0.5`; `interval_samples = 30` consecutive 1 s ticks (streak, no averaging) for both transitions.
- 14 fixed edges (`CONTROLLED_EDGES`); no edges to `redis-cart` or into `frontend`.
- Edge OFF = match route `sourceLabels: {app: <caller>}` with bare `retries: {attempts: 0}`, placed before the default route.
- Service rejection counter (`Δ(5xx+resets)/Δtotal`, threshold `rejection_threshold`) runs only while the callee has at least one OFF edge; on re-enable all its OFF edges return together with fresh counters.
- `retry_metric` defaults to `rejection`; existing YAMLs, `REQUIRED_PARAMS`, and tests keep working.
- Log line shape stays `<ts>  <name>  <old>→<new> ...` (parsed by `mentor_charts_data.py` regex `^ts\s+\S+\s+(ON→OFF|OFF→ON)`); edge name is `caller->target`; lines end with `metric=rpr|rejection`.
- Run tests with: `python -m unittest experiments.test_retryguard` from the repo root.

## File Structure

- Modify `experiments/retryguard.py`: edge constants, `EdgeSnapshot`, `EdgesCsvTailer`, `measure_edge_rpr`, `build_edge_vs_patch_body`, `patch_virtualservice(off_callers=...)`, `Change`, `EdgeController`, `run_edge_rpr`, dispatch in `run()`.
- Modify `experiments/test_retryguard.py`: tests for the above.
- Modify `experiments/run_scenario.py` (params dict at ~line 723): pass `retry_metric` and `retries_threshold`.
- Modify the 11 YAMLs with `retryguard.enabled: true`: `scenario_1_retryguard.yaml`, `scenario_2_retryguard.yaml`, `scenario_2_retryguard_no_topfull.yaml`, `scenario_3_retryguard.yaml`, `scenario_4a_retryguard.yaml`, `scenario_4b_retryguard.yaml`, `scenario_5_interval_{10,20,30,60}s.yaml`, `scenario_6_recovery_retryguard.yaml`. Add two keys under `retryguard:`. Do not change `run_number`, `log_folder`, or `interval_samples`.
- Modify `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` and `AGENTS.md` (one status bullet).

---

### Task 1: Branch and edge measurement

**Files:**
- Modify: `experiments/retryguard.py`
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Produces: `CONTROLLED_EDGES: tuple[tuple[str,str],...]`, `EDGES_CSV_NAME`, `EdgeSnapshot(timestamp, total, retry)`, `EdgesCsvTailer(csv_path)` with `.poll()` and `.latest: dict[(caller,target), EdgeSnapshot]`, `measure_edge_rpr(previous, current) -> (Optional[float], Optional[EdgeSnapshot])`.

- [ ] **Step 1: Create the branch from updated main, carrying the spec and CONTEXT.md**

```bash
git checkout main
git pull origin main
git checkout -b retryguard-edge-rpr
git add CONTEXT.md docs/superpowers/specs/2026-10-06-retryguard-edge-rpr-design.md docs/superpowers/plans/2026-10-06-retryguard-edge-rpr.md
git commit -m "docs: spec, plan and glossary terms for RetryGuard edge-rpr mode"
```

(`git checkout main` carries the uncommitted `CONTEXT.md` change and the untracked files across. If `git pull` reports a conflict with `CONTEXT.md`, stop and ask.)

- [ ] **Step 2: Write the failing tests** (append before `if __name__ == "__main__":` in `experiments/test_retryguard.py`)

```python
class TestEdgeMeasurement(unittest.TestCase):
    def test_controlled_edges_shape(self):
        self.assertEqual(len(retryguard.CONTROLLED_EDGES), 14)
        for caller, target in retryguard.CONTROLLED_EDGES:
            self.assertIn(target, retryguard.CONTROLLED_SERVICES)
            self.assertNotEqual(caller, "redis-cart")

    def test_rpr_divides_by_first_attempts(self):
        S = retryguard.EdgeSnapshot
        prev = S("2026-01-01T00:00:00Z", total=100, retry=10)
        cur = S("2026-01-01T00:00:01Z", total=160, retry=30)
        # delta total 60, delta retry 20 -> first attempts 40 -> rpr 0.5
        rpr, _ = retryguard.measure_edge_rpr(prev, cur)
        self.assertAlmostEqual(rpr, 0.5)

    def test_no_first_attempts_is_skipped(self):
        S = retryguard.EdgeSnapshot
        prev = S("2026-01-01T00:00:00Z", total=100, retry=10)
        cur = S("2026-01-01T00:00:01Z", total=100, retry=10)
        rpr, _ = retryguard.measure_edge_rpr(prev, cur)
        self.assertIsNone(rpr)

    def test_tailer_keys_by_caller_and_target(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "service_edges.csv"
            p.write_text(
                "timestamp,caller,target,total,2xx,4xx,5xx,retry\n"
                "2026-01-01T00:00:00Z,frontend,adservice,10,10,0,0,2\n",
                encoding="utf-8",
            )
            t = retryguard.EdgesCsvTailer(p)
            t.poll()
            snap = t.latest[("frontend", "adservice")]
            self.assertEqual((snap.total, snap.retry), (10.0, 2.0))
```

- [ ] **Step 3: Run to verify they fail**

Run: `python -m unittest experiments.test_retryguard.TestEdgeMeasurement`
Expected: FAIL, `AttributeError: module 'retryguard' has no attribute 'CONTROLLED_EDGES'`.

- [ ] **Step 4: Implement** in `experiments/retryguard.py`

After `INBOUND_CSV_NAME = ...` add:

```python
EDGES_CSV_NAME = "service_edges.csv"

# The Boutique call graph is fixed, so the controlled edges are a constant.
# HTTP/gRPC edges between Boutique services only: no redis-cart (TCP, no
# VirtualService), nothing into frontend.
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
```

After `InboundSnapshot` add:

```python
@dataclass(frozen=True)
class EdgeSnapshot:
    timestamp: str
    total: float  # every attempt, retries included (the paper's Lambda)
    retry: float
```

After `class InboundCsvTailer` add:

```python
class EdgesCsvTailer(InboundCsvTailer):
    """Same append-only tail as InboundCsvTailer; rows keyed by (caller, target)."""

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
        try:
            snapshot = EdgeSnapshot(
                timestamp=str(row["timestamp"]),
                total=float(row["total"]),
                retry=float(row["retry"]),
            )
            key = (row["caller"], row["target"])
        except (KeyError, TypeError, ValueError):
            return
        self.latest[key] = snapshot


def measure_edge_rpr(
    previous: Optional[EdgeSnapshot],
    current: Optional[EdgeSnapshot],
) -> tuple[Optional[float], Optional[EdgeSnapshot]]:
    """
    Retries per request on one edge: the paper's (Lambda - lambda) / lambda.
    `total` counts every attempt, so first attempts = delta total - delta retry.
    Returns None (skip the tick) when there is no new row or no first attempts.
    """
    if current is None:
        return None, previous
    if previous is None:
        return None, current
    if current.timestamp <= previous.timestamp:
        return None, previous
    delta_retry = current.retry - previous.retry
    first_attempts = (current.total - previous.total) - delta_retry
    if first_attempts <= 0:
        return None, current
    return delta_retry / first_attempts, current
```

- [ ] **Step 5: Run to verify they pass**

Run: `python -m unittest experiments.test_retryguard`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat(retryguard): per-edge retries-per-request measurement"
```

---

### Task 2: Per-edge patch body and EdgeController

**Files:**
- Modify: `experiments/retryguard.py`
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Consumes: `ServiceState`, `apply_algorithm1`, `build_vs_patch_body` (existing).
- Produces:
  - `build_edge_vs_patch_body(route, off_callers, attempts_on, per_try_timeout_ms) -> dict`
  - `patch_virtualservice(api, service_name, attempts, per_try_timeout_ms=500, namespace=..., off_callers=None)`; when `off_callers` is not None it uses the edge body and `attempts` means attempts-on.
  - `Change(service, transition, new_off, metric, lines)` where `lines` is a list of `(name, value, counter)`.
  - `EdgeController(edges, rpr_threshold, rejection_threshold, interval)` with `.step(rpr, rejection) -> list[Change]`, `.commit(change)`, `.off_callers(service)`, `.edge_state`, `.svc_state`.

- [ ] **Step 1: Write the failing tests** (append before `if __name__ == "__main__":`)

```python
class TestEdgePatchBody(unittest.TestCase):
    ROUTE = [{"destination": {"host": "productcatalogservice"}}]

    def test_off_callers_get_match_routes_before_default(self):
        body = retryguard.build_edge_vs_patch_body(
            self.ROUTE, {"frontend", "checkoutservice"}, 3, 500
        )
        http = body["spec"]["http"]
        self.assertEqual(len(http), 3)
        self.assertEqual(
            http[0]["match"], [{"sourceLabels": {"app": "checkoutservice"}}]
        )
        self.assertEqual(http[1]["match"], [{"sourceLabels": {"app": "frontend"}}])
        self.assertEqual(http[0]["retries"], {"attempts": 0})
        self.assertNotIn("match", http[2])
        self.assertEqual(http[2]["retries"]["attempts"], 3)
        self.assertEqual(http[2]["route"], self.ROUTE)

    def test_no_off_callers_is_plain_default(self):
        body = retryguard.build_edge_vs_patch_body(self.ROUTE, set(), 3, 500)
        self.assertEqual(len(body["spec"]["http"]), 1)
        self.assertNotIn("match", body["spec"]["http"][0])


class TestEdgeController(unittest.TestCase):
    EDGE = ("frontend", "recommendationservice")
    EDGES = (EDGE, ("recommendationservice", "productcatalogservice"))

    def make(self):
        return retryguard.EdgeController(self.EDGES, 0.5, 0.2, 30)

    def feed(self, ctrl, ticks, rpr, rejection=None):
        out = []
        for _ in range(ticks):
            out += ctrl.step({self.EDGE: rpr}, rejection or {})
        return out

    def test_streak_of_30_turns_edge_off(self):
        ctrl = self.make()
        self.assertEqual(self.feed(ctrl, 29, 0.9), [])
        changes = self.feed(ctrl, 1, 0.9)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].service, "recommendationservice")
        self.assertEqual(changes[0].transition, "OFF")
        self.assertEqual(changes[0].new_off, frozenset({"frontend"}))
        self.assertEqual(changes[0].metric, "rpr")

    def test_low_tick_resets_streak(self):
        ctrl = self.make()
        self.feed(ctrl, 29, 0.9)
        self.feed(ctrl, 1, 0.1)
        self.assertEqual(self.feed(ctrl, 29, 0.9), [])

    def test_skipped_ticks_change_nothing(self):
        ctrl = self.make()
        self.feed(ctrl, 29, 0.9)
        self.feed(ctrl, 5, None)
        self.assertEqual(len(self.feed(ctrl, 1, 0.9)), 1)

    def test_rejection_fallback_idle_until_an_edge_is_off(self):
        ctrl = self.make()
        rej = {"recommendationservice": 0.0}
        self.assertEqual(self.feed(ctrl, 40, 0.1, rej), [])
        self.assertEqual(ctrl.svc_state, {})

    def test_fallback_reenables_all_off_edges_together(self):
        ctrl = self.make()
        change = self.feed(ctrl, 30, 0.9)[0]
        ctrl.commit(change)
        self.assertEqual(ctrl.off_callers("recommendationservice"), {"frontend"})
        rej = {"recommendationservice": 0.05}
        self.assertEqual(self.feed(ctrl, 29, None, rej), [])
        back = self.feed(ctrl, 1, None, rej)
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0].transition, "ON")
        self.assertEqual(back[0].metric, "rejection")
        self.assertEqual(back[0].new_off, frozenset())
        ctrl.commit(back[0])
        self.assertEqual(ctrl.off_callers("recommendationservice"), frozenset())
        self.assertEqual(ctrl.svc_state, {})
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m unittest experiments.test_retryguard.TestEdgePatchBody experiments.test_retryguard.TestEdgeController`
Expected: FAIL with `AttributeError` (missing `build_edge_vs_patch_body` / `EdgeController`).

- [ ] **Step 3: Implement the patch body** in `experiments/retryguard.py`, directly after `build_vs_patch_body`:

```python
def build_edge_vs_patch_body(
    route: list,
    off_callers,
    attempts_on: int,
    per_try_timeout_ms: int,
) -> dict:
    """
    Per-edge VirtualService body: one match route per OFF caller with bare
    attempts: 0, then the default route with the full retry policy last.
    Match routes must come first, Istio takes the first rule that matches.
    """
    default = build_vs_patch_body(route, attempts_on, per_try_timeout_ms)["spec"][
        "http"
    ][0]
    rules = [
        {
            "match": [{"sourceLabels": {"app": caller}}],
            "route": route,
            "retries": {"attempts": 0},
        }
        for caller in sorted(off_callers)
    ]
    return {"spec": {"http": rules + [default]}}
```

In `patch_virtualservice`, add the parameter `off_callers=None` as the last parameter of the signature, and replace the line `body = build_vs_patch_body(route, attempts, per_try_timeout_ms)` with:

```python
    if off_callers is None:
        body = build_vs_patch_body(route, attempts, per_try_timeout_ms)
    else:
        # Edge mode: `attempts` is the ON policy for callers not in off_callers.
        body = build_edge_vs_patch_body(
            route, off_callers, attempts, per_try_timeout_ms
        )
```

(The route is read from `http_rules[0]["route"]`; match routes carry the same route, so this works after a previous edge patch.)

- [ ] **Step 4: Implement `Change` and `EdgeController`** in `experiments/retryguard.py`, after `apply_algorithm1`:

```python
@dataclass
class Change:
    service: str          # callee whose VirtualService must be patched
    transition: str       # "OFF" (some edges turn OFF) or "ON" (all back ON)
    new_off: frozenset    # callers that should be OFF after the patch
    metric: str           # "rpr" or "rejection"
    lines: list           # [(name, value, counter), ...] for the log


class EdgeController:
    """
    Edge mode state. step() proposes changes without committing retries
    state; the caller patches the VirtualService and then commit()s, so a
    failed patch is retried on the next tick (counters stay >= interval).
    """

    def __init__(self, edges, rpr_threshold, rejection_threshold, interval):
        self.rpr_threshold = rpr_threshold
        self.rejection_threshold = rejection_threshold
        self.interval = interval
        self.edge_state = {e: ServiceState() for e in edges}
        # Per-callee rejection counters; a key exists only while the callee
        # has at least one OFF edge.
        self.svc_state: Dict[str, ServiceState] = {}

    def off_callers(self, service: str) -> frozenset:
        return frozenset(
            c
            for (c, t), st in self.edge_state.items()
            if t == service and st.retries_state == "OFF"
        )

    def step(self, rpr: dict, rejection: dict) -> list:
        changes = []
        handled = set()

        # Fallback: per-service rejection rate while any edge is OFF.
        for service, st in self.svc_state.items():
            value = rejection.get(service)
            if value is None:
                continue
            desired = apply_algorithm1(
                st, value, self.rejection_threshold, self.interval
            )
            if desired == "ON":
                changes.append(
                    Change(
                        service, "ON", frozenset(), "rejection",
                        [(service, value, st.consecutive_low)],
                    )
                )
                handled.add(service)

        # Per-edge retries per request for edges that are still ON.
        turning_off: Dict[str, list] = {}
        for edge, st in self.edge_state.items():
            caller, service = edge
            if st.retries_state != "ON" or service in handled:
                continue
            value = rpr.get(edge)
            if value is None:
                continue
            if (
                apply_algorithm1(st, value, self.rpr_threshold, self.interval)
                == "OFF"
            ):
                turning_off.setdefault(service, []).append(
                    (f"{caller}->{service}", value, st.consecutive_high, caller)
                )
        for service, items in turning_off.items():
            new_off = self.off_callers(service) | {i[3] for i in items}
            changes.append(
                Change(
                    service, "OFF", frozenset(new_off), "rpr",
                    [(n, v, c) for n, v, c, _ in items],
                )
            )
        return changes

    def commit(self, change: Change) -> None:
        if change.transition == "OFF":
            for caller in change.new_off:
                self.edge_state[(caller, change.service)].retries_state = "OFF"
            self.svc_state.setdefault(
                change.service, ServiceState(retries_state="OFF")
            )
        else:
            for (caller, target) in list(self.edge_state):
                if target == change.service:
                    self.edge_state[(caller, target)] = ServiceState()
            self.svc_state.pop(change.service, None)
```

- [ ] **Step 5: Run to verify they pass**

Run: `python -m unittest experiments.test_retryguard`
Expected: all tests PASS (including the earlier `TestVirtualServicePatchBody`, unchanged).

- [ ] **Step 6: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat(retryguard): per-edge patch body and EdgeController"
```

---

### Task 3: Run loop, params, scenario YAML, docs

**Files:**
- Modify: `experiments/retryguard.py` (`run`, new `run_edge_rpr`)
- Modify: `experiments/run_scenario.py` (~line 723)
- Modify: the 11 RetryGuard YAMLs listed in File Structure
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`, `AGENTS.md`

**Interfaces:**
- Consumes: everything from Tasks 1 and 2.
- Produces: params keys `retry_metric` (`rejection` | `edge_rpr`, default `rejection`) and `retries_threshold` (float, required only for `edge_rpr`).

- [ ] **Step 1: Add `run_edge_rpr` and the dispatch** in `experiments/retryguard.py`. Insert `run_edge_rpr` just before `def run(`:

```python
def run_edge_rpr(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    """Edge mode: retries per request per edge, rejection rate per callee as fallback."""
    if "retries_threshold" not in params:
        raise SystemExit("[retryguard] retry_metric=edge_rpr needs retries_threshold")
    sample_interval = int(params["sample_interval_seconds"])
    interval = int(params["interval_samples"])
    rejection_threshold = float(params["rejection_threshold"])
    rpr_threshold = float(params["retries_threshold"])
    attempts_on = int(params["retry_attempts_on"])
    per_try_timeout_ms = int(params["per_try_timeout_ms"])

    wait_for_inbound_csv(record_path)

    ctrl = EdgeController(CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval)
    inbound = InboundCsvTailer(record_path / INBOUND_CSV_NAME)
    edges = EdgesCsvTailer(record_path / EDGES_CSV_NAME)
    prev_in: Dict[str, Optional[InboundSnapshot]] = {s: None for s in CONTROLLED_SERVICES}
    prev_edge: Dict[tuple, Optional[EdgeSnapshot]] = {e: None for e in CONTROLLED_EDGES}
    log.info(
        "%s  START  metric=edge_rpr rpr_threshold=%.2f rejection_threshold=%.2f "
        "sample_interval=%ss interval_samples=%d edges=%d",
        utc_now(), rpr_threshold, rejection_threshold,
        sample_interval, interval, len(CONTROLLED_EDGES),
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break
        inbound.poll()
        edges.poll()

        rpr = {}
        for edge in CONTROLLED_EDGES:
            rpr[edge], prev_edge[edge] = measure_edge_rpr(
                prev_edge[edge], edges.latest.get(edge)
            )
        rejection = {}
        for service in CONTROLLED_SERVICES:
            rejection[service], prev_in[service] = measure_inbound_rejection(
                prev_in[service], inbound.latest.get(service)
            )

        changes = ctrl.step(rpr, rejection)

        for edge, st in ctrl.edge_state.items():
            if st.retries_state == "ON" and rpr.get(edge) is not None:
                log.info(
                    "%s  OBSERVE  %s->%s  rpr=%.4f  low=%d high=%d  state=ON  metric=rpr",
                    utc_now(), edge[0], edge[1], rpr[edge],
                    st.consecutive_low, st.consecutive_high,
                )
        for service, st in ctrl.svc_state.items():
            if rejection.get(service) is not None:
                log.info(
                    "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  state=OFF  metric=rejection",
                    utc_now(), service, rejection[service],
                    st.consecutive_low, st.consecutive_high,
                )

        for change in changes:
            try:
                patch_virtualservice(
                    api, change.service, attempts_on, per_try_timeout_ms,
                    off_callers=change.new_off,
                )
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.info(
                    "%s  PATCH_FAIL  %s  %s  error=%s",
                    utc_now(), change.service, change.transition, exc,
                )
                continue
            old, new = ("ON", "OFF") if change.transition == "OFF" else ("OFF", "ON")
            label = "rpr" if change.metric == "rpr" else "rejection"
            counter = "consecutive_high" if new == "OFF" else "consecutive_low"
            attempts = 0 if new == "OFF" else attempts_on
            for name, value, count in change.lines:
                log.info(
                    "%s  %s  %s→%s   %s=%.2f  %s=%d  attempts=%d  metric=%s",
                    utc_now(), name, old, new, label, value,
                    counter, count, attempts, change.metric,
                )
            ctrl.commit(change)

    log.info("%s  EXIT", utc_now())


```

At the top of `run()` (before `sample_interval = ...`) add:

```python
    metric = params.get("retry_metric", "rejection")
    if metric == "edge_rpr":
        return run_edge_rpr(params, record_path, api)
    if metric != "rejection":
        raise SystemExit(f"[retryguard] unknown retry_metric: {metric!r}")
```

- [ ] **Step 2: Pass the params through** in `experiments/run_scenario.py`. In the `params = {...}` dict in `start_retryguard`, after the `"per_try_timeout_ms"` entry add:

```python
        "retry_metric":            rg_cfg.get("retry_metric", "rejection"),
        "retries_threshold":       rg_cfg.get("retries_threshold", 0.5),
```

- [ ] **Step 3: Opt in on every YAML that starts RetryGuard.** Under each `retryguard:` block that has `enabled: true`, add these two lines and change nothing else (`interval_samples` stays 30, or 10/20/30/60 on Scenario 5):

```yaml
  retry_metric: edge_rpr
  retries_threshold: 0.5
```

Files: `scenario_1_retryguard.yaml`, `scenario_2_retryguard.yaml`, `scenario_2_retryguard_no_topfull.yaml`, `scenario_3_retryguard.yaml`, `scenario_4a_retryguard.yaml`, `scenario_4b_retryguard.yaml`, `scenario_5_interval_10s.yaml`, `scenario_5_interval_20s.yaml`, `scenario_5_interval_30s.yaml`, `scenario_5_interval_60s.yaml`, `scenario_6_recovery_retryguard.yaml`. Baseline and calibration YAMLs have `enabled: false`, so the controller never starts and they stay as they are.

- [ ] **Step 4: Run the full local tests**

Run: `python -m unittest experiments.test_retryguard experiments.test_mentor_charts`
Expected: PASS. Also confirm all 11 files opted in:

```bash
python -c "
import pathlib
files = list(pathlib.Path('experiments/configs').glob('scenario_*retryguard*.yaml')) + list(pathlib.Path('experiments/configs').glob('scenario_5_*.yaml'))
for p in sorted(set(files)):
    text = p.read_text(encoding='utf-8')
    on = 'enabled: true' in text.split('retryguard:')[1].split('\n\n')[0]
    opted = 'retry_metric: edge_rpr' in text
    print(('OK' if on == opted else 'MISMATCH'), p.name)
"
```

Expected: `OK` on every line.

- [ ] **Step 5: Smoke-check the log shape against the parser**

Run:

```bash
python -c "
import sys; sys.path.insert(0,'experiments')
import re
line='2026-10-06T20:00:00Z  frontend->recommendationservice  ON→OFF   rpr=0.62  consecutive_high=30  attempts=0  metric=rpr'
print(bool(re.match(r'^(?P<ts>\S+)\s+(?P<service>\S+)\s+(?P<direction>ON→OFF|OFF→ON)\b', line)))
"
```

Expected: `True`.

- [ ] **Step 6: Docs.** Add a short "Edge mode (`retry_metric: edge_rpr`)" section to `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` (what it measures, 0.5 threshold derived from Fig. 7 and labelled a workshop choice, per-edge disable, per-callee fallback, log format, param names). Add one bullet to `AGENTS.md` §4 with today's date: edge mode is what the 11 RetryGuard YAMLs run (`retry_metric: edge_rpr`); the code default stays `rejection`; unit-tested, not yet run live.

- [ ] **Step 7: Commit**

```bash
git add experiments/retryguard.py experiments/run_scenario.py experiments/configs "Guides and Info/RETRYGUARD-IMPLEMENTATION.md" AGENTS.md
git commit -m "feat(retryguard): edge_rpr run loop, params and S2 config"
```

---

### Task 4: Live verification hold (run 89 mix, RetryGuard on, TopFull off)

A single 600 s hold to check that the edge mode works as intended on the real cluster. It is a mechanism check, not a scored campaign run. Needs the VMs, so it runs only after Tasks 1 to 3 are committed and their tests pass.

**Files:**
- Modify: `experiments/configs/scenario_2_retryguard_no_topfull.yaml` (counts, `run_number`, `log_folder`, `description`)
- Create (by the pull): `experiments/results/campaign_48/S2_sustained_overload/run_retryguard_no_topfull_sustained_overload_run10/`
- Modify: `AGENTS.md` (replace the "not yet run live" wording with the result)

**Setup to match run 89:**
- Locust counts **275 / 90 / 100 / 90 / 5** (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50, 600 s.
- CPU table: Paper-C1. The YAML's `scale_constraints` already hold it (frontend 1150, checkout 800, recommendations 1150, catalog 800, cart 800, currency 770, shipping 770, ad 1150, payment 155, email 120, redis-cart 540). `paper_cpu_reconcile: false` stays.
- Pin, as for runs 85 to 153: frontend HPA min 4 / max 4, catalog HPA min 1 / max 1, every other service at 1 replica, sidecar request 100 m with no `proxyCPULimit` (use 90 m only if the fourth frontend pod stays Pending, as in AGENTS.md §7). Checkout and recommendations are rolled by the YAML's `restart_before_hold`.
- RetryGuard on with `retry_metric: edge_rpr` (from Task 3), TopFull RL off (`topfull_rl.enabled: false`, already set).
- Reference for comparison: `run_retryguard_no_topfull_sustained_overload_run4` (same mix and table, per-service rejection mode: 16× ON→OFF and 16× OFF→ON on checkoutservice, recommendations untouched).

- [ ] **Step 1: Set the YAML.** In `scenario_2_retryguard_no_topfull.yaml` set `locust.user_counts` to `getproduct: 275`, `postcheckout: 90`, `getcart: 100`, `postcart: 90`, `emptycart: 5`; keep `run_number: 10` and `log_folder: run_retryguard_no_topfull_sustained_overload_run10`; update `description` to "Edge-rpr verification hold, run 89 mix". Confirm `retry_metric: edge_rpr` is present from Task 3.

- [ ] **Step 2: Start the VMs and confirm the cluster.** Use the SSH aliases only; refresh `HostName` in `~/.ssh/config` if the IPs changed (CONNECT-VMS.md).

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb
ssh topfull-master "kubectl get nodes; kubectl get pods -n default"
```

Expected: 3 VMs `RUNNING`, nodes Ready, Boutique pods Running.

- [ ] **Step 3: Apply the pin and check it.** Set frontend HPA min/max 4, catalog HPA max 1, sidecar request as above, then confirm frontend ready 4/4 and every other deployment ready 1/1 with pending 0. Cool off 300 s after the last change.

- [ ] **Step 4: Deploy and launch.**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_retryguard_no_topfull.yaml
```

The runner copies the new `retryguard.py` onto master itself. Expected at start: `retryguard.log` shows `START  metric=edge_rpr rpr_threshold=0.50 ... edges=14`.

- [ ] **Step 5: While the hold runs, spot-check live.** After about 2 minutes:

```powershell
ssh topfull-master "tail -n 20 /home/idozacharia/experiments/results/run_retryguard_no_topfull_sustained_overload_run10/retryguard.log"
```

Expected: `OBSERVE  caller->target  rpr=...  metric=rpr` lines for several edges and no traceback or repeated `PATCH_FAIL`. If the tmux session `retryguard` has exited, stop the hold, fix the cause, and relaunch on `run11`.

- [ ] **Step 6: Pull and run the checks.**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_retryguard_no_topfull.yaml
```

Then verify, on the pulled folder:

1. **Gates:** `Locust total.csv` rows ≥ 500, mesh span about 600 s, frontend 4 replicas on every `resource_usage.csv` sample, every other service 1. A failed gate means the hold is not a valid check; keep the folder and relaunch on the next slot.
2. **Log shape:** `retryguard.log` has the `START ... metric=edge_rpr` line and `OBSERVE ... metric=rpr` lines, and no traceback.
3. **Metric matches the CSV:** pick three logged `rpr=` values for `frontend->checkoutservice` and recompute `Δretry / (Δtotal − Δretry)` from consecutive `service_edges.csv` rows at the same timestamps. Expected: equal to two decimals.
4. **Streak rule:** for any `caller->target  ON→OFF` line, the preceding 30 `OBSERVE` lines for that edge all show `rpr` above 0.50, and `consecutive_high=30` on the transition line.
5. **Per-edge effect:** after an edge goes OFF, its `retry` column in `service_edges.csv` stops growing while other callers' edges into the same target keep retrying. (A live Envoy check is optional: `kubectl exec <caller pod> -c istio-proxy -- curl -s localhost:15000/config_dump?resource=dynamic_route_configs` shows no retry policy toward that target for that caller only.)
6. **Fallback:** if an edge went OFF, look for `OFF→ON ... rejection=... metric=rejection` on the same callee, with `consecutive_low=30` and rejection below 0.20 on the 30 preceding `OBSERVE ... metric=rejection` lines, and all of that callee's OFF edges returning in the same second.
7. **Compare with run4:** note which service(s) toggled and how often, against the per-service reference. The result may differ (the metric and scope differ and the latch is bistable); it only has to be explainable from the logged `rpr` values.
8. **If no edge ever goes OFF:** that can be a valid outcome when no edge holds `rpr > 0.5` for 30 s. Check the maximum 30-tick streak of `rpr > 0.5` per edge from `service_edges.csv` and confirm it is under 30. If some edge had a streak of 30 or more and no transition fired, that is a bug: fix it and relaunch.

- [ ] **Step 7: Restore the cluster.** Frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar request 100 m with no limit, paper CPU reconcile. Confirm the VirtualServices are back to a single default rule with 3 retries (no leftover match routes from an OFF edge):

```powershell
ssh topfull-master "kubectl get vs -n default -o jsonpath='{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].match}{\"\n\"}{end}'"
```

Expected: no service prints a `match`. If one does, run `ssh topfull-master "kubectl apply -f <repo>/experiments/virtual-services.yaml"` (copy it up first) and re-check.

- [ ] **Step 8: Record and commit.** Bump the YAML to `run_number: 11` / matching `log_folder`. Replace the AGENTS.md "not yet run live" wording with one bullet giving the run folder, whether any edge went OFF (which edges, how many times), whether the fallback re-enabled, and the checks that passed or failed. Then:

```bash
git add experiments/configs/scenario_2_retryguard_no_topfull.yaml AGENTS.md experiments/results/campaign_48/S2_sustained_overload/run_retryguard_no_topfull_sustained_overload_run10
git commit -m "test(retryguard): live edge-rpr verification hold, run 89 mix, TopFull off"
```

Stop the VMs only if you ask for it (AGENTS.md §7).

---

## Self-Review

- **Spec coverage:** fixed 14 edges (Task 1), rpr formula and skip (Task 1), threshold/streak (Task 2 tests), match-route patch (Task 2), fallback only while an edge is OFF and all-together re-enable (Task 2), `retry_metric` switch with code default `rejection` and all 11 RetryGuard YAMLs set to `edge_rpr` (Task 3), log shape with `metric=` (Task 3, step 5 checks the parser), docs (Task 3).
- **Placeholders:** none. The one prose step is the docs section in Task 3, step 6.
- **Type consistency:** `Change.lines` entries are `(name, value, counter)` in `step()`, `run_edge_rpr()`, and the tests. `patch_virtualservice(..., off_callers=)` takes a `frozenset`, and `build_edge_vs_patch_body` sorts it.
- **Live check:** Task 4 runs one hold (run 89 mix, Paper-C1, RetryGuard on, TopFull off) and checks the log, the metric, the streak rule, the per-edge effect, and the fallback.
- **Not in the plan on purpose:** a traffic floor, plotting edge toggles, a full campaign.
