# RetryGuard Burst Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in burst mode to RetryGuard's edge controller that sheds an edge to 0 attempts when a sliding 5 s retries-per-request aggregate crosses a bar scaled by the edge's attempt cap, plus a read-only replay script that shows how often it would have fired on finished S2 runs.

**Architecture:** A `BurstWindow` (sliding sums of `Δretry` and `Δfirst attempts` over the last N seconds of row timestamps) lives per edge inside `EdgeController`. It is fed by per-tick deltas computed in `run_edge_rpr`, evaluated before the existing handlers, and cleared on commit. Recovery is untouched. `run_scenario.py` forwards three optional YAML keys and validates them early. `analysis_score.py` and `burst_replay.py` read the new log fields.

**Tech Stack:** Python 3, `unittest` (existing suites stub `kubernetes`), YAML scenario configs, existing log format.

## Global Constraints

- Burst mode is on if and only if the YAML `retryguard` block sets `burst_rpr`. Without it, behaviour is identical to today.
- YAML keys: `burst_rpr` (bar at full attempts, e.g. 1.0 / 1.5 / 2.0), `burst_window_seconds` (default 5), `burst_min_first_attempts` (default 20).
- Effective bar at the edge's current cap: `burst_rpr × attempts / attempts_on`.
- Window is time-based on row timestamps: entries within `burst_window_seconds` of the newest valid tick (a window of 5 holds ticks `t-4 … t` at 1 s sampling). Skipped ticks add nothing.
- Fire test: `ΣΔretry / ΣΔfirst ≥ bar` (`≥`, not `>`) and `ΣΔfirst ≥ burst_min_first_attempts`.
- Runs on every edge with `attempts > 0`. Window is cleared whenever the edge is committed to a new attempt count.
- A burst shed always goes to 0 attempts. No burst-specific recovery; the existing recovery path is unchanged.
- The existing normal handler (rpr > `retries_threshold` for `interval_samples` s, plus ramp logic) is untouched. Whichever fires first sheds.
- Edge mode only (`retry_metric=edge_rpr`). `burst_rpr` with any other `retry_metric` makes `run_scenario.py` fail at startup.
- Log: shed line is `name ON→OFF rpr=<window rpr> ... metric=rpr_burst`. `START` gains `burst_rpr`, `burst_window_seconds`, `burst_min_first_attempts`. `OBSERVE` gains `burst_rpr5=<value>` once the window is evaluable. `analysis_score.py` splits ON→OFF into normal and burst.
- `run_scenario.py` copies only `retryguard.py` to master (`deploy_repo_script`), so all controller code stays inside that single file. No new runtime module.
- Keep tests small. Do not over-test.
- Live run plan is out of scope; it is chosen after implementation.

## File Structure

- Modify `experiments/retryguard.py`: `BurstWindow`, `burst_bar`, `edge_tick_deltas`, `Change.burst_callers`, `EdgeController` burst state and check, `run_edge_rpr` wiring (params, START, deltas, OBSERVE, shed log metric).
- Modify `experiments/test_retryguard.py`: one `TestBurstMode` class.
- Modify `experiments/run_scenario.py`: `burst_params_from_cfg`, early validation in `run`, forward in `start_retryguard`.
- Modify `experiments/test_run_scenario.py`: two tests in `TestStartRetryGuardWiring`.
- Modify `experiments/analysis_score.py`: parse `burst`, split toggle table.
- Modify `experiments/test_analysis_score.py`: one test in `TestLog`.
- Create `experiments/burst_replay.py`: read-only replay over `service_edges.csv`.
- Modify `CONTEXT.md`, create `docs/adr/0007-burst-mode-sliding-aggregate.md`, modify `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`.

Run all commands from the repo root `c:\Users\idoza\topfull-retryguard-workshop` in PowerShell.

---

### Task 1: Burst logic in the controller

**Files:**
- Modify: `experiments/retryguard.py` (imports; new block before `class Change`; `Change`; `EdgeController.__init__`, `step`, `commit`)
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Produces (used by Tasks 2, 5):
  - `BURST_WINDOW_SECONDS_DEFAULT = 5`, `BURST_MIN_FIRST_ATTEMPTS_DEFAULT = 20`
  - `burst_bar(burst_rpr: float, attempts: int, attempts_on: int) -> float`
  - `class BurstWindow(seconds: int, min_first_attempts: int)` with `add(timestamp: str, d_retry: float, d_first: float) -> None`, `clear() -> None`, `rpr() -> Optional[float]`, `span_s() -> int`
  - `edge_tick_deltas(previous: Optional[EdgeSnapshot], current: Optional[EdgeSnapshot]) -> Optional[tuple[float, float]]` returning `(Δretry, Δfirst)`
  - `Change.burst_callers: frozenset` (default empty)
  - `EdgeController(..., burst_rpr=None, burst_window_seconds=5, burst_min_first_attempts=20)`, attributes `burst_rpr`, `burst_windows`, `burst_last`
  - `EdgeController.step(rpr, rejection, rpr_ts=None, rejection_ts=None, edge_deltas=None)`

- [ ] **Step 1: Write the failing tests**

In `experiments/test_retryguard.py`, insert this class immediately above `def test_reenable_rejection_param_overrides_default():`:

```python
class TestBurstMode(unittest.TestCase):
    EDGE = ("frontend", "checkoutservice")

    def make(self, burst_rpr=1.5, min_first=20):
        return retryguard.EdgeController(
            (self.EDGE,), 0.5, 0.2, 30,
            burst_rpr=burst_rpr,
            burst_window_seconds=5,
            burst_min_first_attempts=min_first,
        )

    def tick(self, ctrl, t, d_retry, d_first):
        ts = retryguard.format_row_timestamp(t)
        return ctrl.step(
            {self.EDGE: d_retry / d_first}, {}, {self.EDGE: ts}, {},
            edge_deltas={self.EDGE: (d_retry, d_first)},
        )

    def test_window_aggregate_sheds_before_any_streak(self):
        ctrl = self.make()
        for t in range(3):
            self.assertEqual(self.tick(ctrl, t, 0, 10), [])
        changes = self.tick(ctrl, 3, 60, 10)  # 60 / 40 = 1.5, on the bar
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].transition, "OFF")
        self.assertEqual(changes[0].burst_callers, frozenset({"frontend"}))
        self.assertEqual(changes[0].new_off, frozenset({"frontend"}))
        self.assertAlmostEqual(changes[0].lines[0][3], 1.5)

    def test_volume_floor_blocks_thin_windows(self):
        ctrl = self.make(min_first=20)
        for t in range(5):  # rpr 3.0 per tick but only 5 first attempts total
            self.assertEqual(self.tick(ctrl, t, 3, 1), [])

    def test_bar_scales_with_attempt_cap(self):
        for attempts, fires in ((2, True), (3, False)):
            ctrl = self.make()
            ctrl.edge_state[self.EDGE].attempts = attempts
            self.assertEqual(self.tick(ctrl, 0, 10, 10), [])  # floor not met yet
            changes = self.tick(ctrl, 1, 10, 10)  # rpr 1.0; bar 1.0 at 2, 1.5 at 3
            self.assertEqual(bool(changes), fires)

    def test_commit_clears_the_window(self):
        ctrl = self.make()
        for t in range(3):
            self.tick(ctrl, t, 0, 10)
        change = self.tick(ctrl, 3, 60, 10)[0]
        ctrl.commit(change)
        self.assertIsNone(ctrl.burst_windows[self.EDGE].rpr())

    def test_off_without_burst_rpr(self):
        ctrl = self.make(burst_rpr=None)
        self.assertEqual(ctrl.burst_windows, {})
        for t in range(3):
            self.tick(ctrl, t, 0, 10)
        self.assertEqual(self.tick(ctrl, 3, 60, 10), [])

    def test_edge_tick_deltas_matches_measure_edge_rpr(self):
        prev = retryguard.EdgeSnapshot("2026-10-11T00:00:00Z", 100.0, 10.0)
        cur = retryguard.EdgeSnapshot("2026-10-11T00:00:01Z", 160.0, 30.0)
        self.assertEqual(retryguard.edge_tick_deltas(prev, cur), (20.0, 40.0))
        self.assertIsNone(retryguard.edge_tick_deltas(cur, cur))
        self.assertIsNone(retryguard.edge_tick_deltas(None, cur))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest experiments.test_retryguard.TestBurstMode -v`
Expected: errors such as `TypeError: EdgeController.__init__() got an unexpected keyword argument 'burst_rpr'`.

- [ ] **Step 3: Add the import**

In `experiments/retryguard.py`, replace

```python
import time
from dataclasses import dataclass
```

with

```python
import time
from collections import deque
from dataclasses import dataclass
```

- [ ] **Step 4: Add the burst helpers**

In `experiments/retryguard.py`, insert this block immediately above the line `@dataclass` that precedes `class Change:`:

```python
# --------------------------------------------------------------------------- #
#  Burst mode (opt-in): sliding retries-per-request aggregate
# --------------------------------------------------------------------------- #

BURST_WINDOW_SECONDS_DEFAULT = 5
BURST_MIN_FIRST_ATTEMPTS_DEFAULT = 20


def burst_bar(burst_rpr: float, attempts: int, attempts_on: int) -> float:
    """Burst bar at an edge's current cap: burst_rpr scales with attempts / attempts_on."""
    return float(burst_rpr) * int(attempts) / int(attempts_on)


class BurstWindow:
    """
    Sliding sums of (delta retry, delta first attempts) over the last
    `seconds` of row timestamps. A window of 5 holds ticks t-4 .. t at 1 s
    sampling. A skipped tick adds nothing, so the span never exceeds `seconds`.
    """

    def __init__(self, seconds: int, min_first_attempts: int):
        self.seconds = int(seconds)
        self.min_first_attempts = int(min_first_attempts)
        self._ticks: deque = deque()  # (epoch_s, d_retry, d_first)

    def add(self, timestamp: str, d_retry: float, d_first: float) -> None:
        epoch = parse_row_timestamp(timestamp).timestamp()
        self._ticks.append((epoch, d_retry, d_first))
        while self._ticks and self._ticks[0][0] <= epoch - self.seconds:
            self._ticks.popleft()

    def clear(self) -> None:
        self._ticks.clear()

    def span_s(self) -> int:
        if not self._ticks:
            return 0
        return int(round(self._ticks[-1][0] - self._ticks[0][0]))

    def rpr(self) -> Optional[float]:
        """Window retries per first attempt, or None below the volume floor."""
        first = sum(t[2] for t in self._ticks)
        if first <= 0 or first < self.min_first_attempts:
            return None
        return sum(t[1] for t in self._ticks) / first


def edge_tick_deltas(
    previous: Optional[EdgeSnapshot], current: Optional[EdgeSnapshot],
) -> Optional[tuple]:
    """(delta retry, delta first attempts) for one tick; None where measure_edge_rpr skips."""
    if previous is None or current is None:
        return None
    if current.timestamp <= previous.timestamp:
        return None
    d_retry = current.retry - previous.retry
    d_first = (current.total - previous.total) - d_retry
    if d_first <= 0:
        return None
    return d_retry, d_first


```

- [ ] **Step 5: Add `burst_callers` to `Change`**

Replace

```python
    desired_attempts: dict  # caller → attempts this change sets
    caller_attempts: dict   # caller → attempts for every caller not at attempts_on
```

with

```python
    desired_attempts: dict  # caller → attempts this change sets
    caller_attempts: dict   # caller → attempts for every caller not at attempts_on
    # Callers in this change shed by the burst test (log metric=rpr_burst).
    burst_callers: frozenset = frozenset()
```

- [ ] **Step 6: Extend `EdgeController.__init__`**

Replace

```python
        climb_rpr_2_to_3=None,
        climb_interval_seconds=None,
    ):
        self.rpr_threshold = rpr_threshold
```

with

```python
        climb_rpr_2_to_3=None,
        climb_interval_seconds=None,
        burst_rpr=None,
        burst_window_seconds=BURST_WINDOW_SECONDS_DEFAULT,
        burst_min_first_attempts=BURST_MIN_FIRST_ATTEMPTS_DEFAULT,
    ):
        self.rpr_threshold = rpr_threshold
```

Then replace

```python
        # Per-callee rejection counters; a key exists only while the callee
        # has at least one edge at 0 attempts.
        self.svc_state: Dict[str, ServiceState] = {}
```

with

```python
        # Per-callee rejection counters; a key exists only while the callee
        # has at least one edge at 0 attempts.
        self.svc_state: Dict[str, ServiceState] = {}
        # Burst mode. burst_rpr None means off: no windows, no checks.
        self.burst_rpr = None if burst_rpr is None else float(burst_rpr)
        self.burst_windows: Dict[tuple, BurstWindow] = (
            {}
            if self.burst_rpr is None
            else {
                e: BurstWindow(burst_window_seconds, burst_min_first_attempts)
                for e in edges
            }
        )
        # Window rpr per edge on the latest step, for the OBSERVE log field.
        self.burst_last: Dict[tuple, Optional[float]] = {}
```

- [ ] **Step 7: Add the burst check method**

Insert this method immediately above `def _ramp_tick(`:

```python
    def _burst_check(self, edge, st: ServiceState, timestamp: str, delta):
        """Feed one tick to the edge's window. (window rpr, span_s) when it should shed."""
        if self.burst_rpr is None or delta is None:
            return None
        window = self.burst_windows[edge]
        window.add(timestamp, delta[0], delta[1])
        value = window.rpr()
        self.burst_last[edge] = value
        if value is None:
            return None
        if value >= burst_bar(self.burst_rpr, st.attempts, self.attempts_on):
            return value, window.span_s()
        return None

```

- [ ] **Step 8: Wire `step`**

Replace

```python
        rpr_ts: Optional[dict] = None,
        rejection_ts: Optional[dict] = None,
    ) -> list:
        changes = []
        handled = set()
```

with

```python
        rpr_ts: Optional[dict] = None,
        rejection_ts: Optional[dict] = None,
        edge_deltas: Optional[dict] = None,
    ) -> list:
        changes = []
        handled = set()
        edge_deltas = edge_deltas or {}
        self.burst_last = {}
        burst_callers: Dict[str, set] = {}
```

Replace

```python
            name = f"{caller}->{service}"
            if st.attempts >= self.attempts_on:
```

with

```python
            name = f"{caller}->{service}"
            burst = self._burst_check(edge, st, timestamp, edge_deltas.get(edge))
            if burst is not None:
                window_rpr, span = burst
                pending.setdefault(service, {})[caller] = 0
                burst_callers.setdefault(service, set()).add(caller)
                pending_lines.setdefault(service, []).append(
                    (
                        name, "ON", "OFF", window_rpr, st.consecutive_high, 0,
                        st.attempts, span,
                    )
                )
                continue
            if st.attempts >= self.attempts_on:
```

Replace

```python
            changes.append(
                self._make_change(
                    service, transition, "rpr", pending_lines[service], desired
                )
            )
        return changes
```

with

```python
            change = self._make_change(
                service, transition, "rpr", pending_lines[service], desired
            )
            change.burst_callers = frozenset(burst_callers.get(service, ()))
            changes.append(change)
        return changes
```

- [ ] **Step 9: Clear windows on commit**

Replace

```python
        for caller, attempts in change.desired_attempts.items():
            edge = (caller, change.service)
            prev = self.edge_state[edge]
```

with

```python
        for caller, attempts in change.desired_attempts.items():
            edge = (caller, change.service)
            if edge in self.burst_windows:
                self.burst_windows[edge].clear()
            prev = self.edge_state[edge]
```

- [ ] **Step 10: Run the new tests and the whole file**

Run: `python -m unittest experiments.test_retryguard -v`
Expected: all tests pass, including the 6 in `TestBurstMode`. If an existing test fails, the cause is one of the edits in Steps 6–9. Do not change the test.

- [ ] **Step 11: Commit**

```powershell
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat(retryguard): burst window check in EdgeController"
```

---

### Task 2: Wire burst mode into the live loop

**Files:**
- Modify: `experiments/retryguard.py` (`run_edge_rpr`)

**Interfaces:**
- Consumes: everything Task 1 produced. Params JSON keys `burst_rpr`, `burst_window_seconds`, `burst_min_first_attempts` (written by Task 3).
- Produces: log fields read by Tasks 4 and 5: START `burst_rpr=… burst_window_seconds=… burst_min_first_attempts=…`; OBSERVE `burst_rpr5=…`; shed line `metric=rpr_burst`.

- [ ] **Step 1: Build the controller with burst kwargs**

In `run_edge_rpr`, replace

```python
        climb_rpr_1_to_2=climb_1,
        climb_rpr_2_to_3=climb_2,
        climb_interval_seconds=climb_interval,
    )
```

with

```python
        climb_rpr_1_to_2=climb_1,
        climb_rpr_2_to_3=climb_2,
        climb_interval_seconds=climb_interval,
        burst_rpr=params.get("burst_rpr"),
        burst_window_seconds=int(
            params.get("burst_window_seconds", BURST_WINDOW_SECONDS_DEFAULT)
        ),
        burst_min_first_attempts=int(
            params.get("burst_min_first_attempts", BURST_MIN_FIRST_ATTEMPTS_DEFAULT)
        ),
    )
    burst_start = ""
    if ctrl.burst_rpr is not None:
        first_window = next(iter(ctrl.burst_windows.values()))
        burst_start = (
            f" burst_rpr={ctrl.burst_rpr:.2f}"
            f" burst_window_seconds={first_window.seconds}"
            f" burst_min_first_attempts={first_window.min_first_attempts}"
        )
```

- [ ] **Step 2: Append the burst keys to the START line**

Replace

```python
        "edges=%d attempts_on=%d",
        utc_now(), rpr_threshold, rejection_threshold,
        ctrl.reenable_rejection_threshold,
        ctrl.climb_rpr_1_to_2, ctrl.climb_rpr_2_to_3,
        ctrl.climb_interval_seconds,
        sample_interval, interval, len(CONTROLLED_EDGES), attempts_on,
    )
```

with

```python
        "edges=%d attempts_on=%d%s",
        utc_now(), rpr_threshold, rejection_threshold,
        ctrl.reenable_rejection_threshold,
        ctrl.climb_rpr_1_to_2, ctrl.climb_rpr_2_to_3,
        ctrl.climb_interval_seconds,
        sample_interval, interval, len(CONTROLLED_EDGES), attempts_on,
        burst_start,
    )
```

- [ ] **Step 3: Compute per-tick deltas and pass them to `step`**

Replace

```python
        rpr = {}
        rpr_ts = {}
        for edge in CONTROLLED_EDGES:
            rpr[edge], prev_edge[edge] = measure_edge_rpr(
                prev_edge[edge], edges.latest.get(edge)
            )
```

with

```python
        rpr = {}
        rpr_ts = {}
        edge_deltas = {}
        for edge in CONTROLLED_EDGES:
            delta = edge_tick_deltas(prev_edge[edge], edges.latest.get(edge))
            if delta is not None:
                edge_deltas[edge] = delta
            rpr[edge], prev_edge[edge] = measure_edge_rpr(
                prev_edge[edge], edges.latest.get(edge)
            )
```

Replace

```python
        changes = ctrl.step(rpr, rejection, rpr_ts, rejection_ts)
```

with

```python
        changes = ctrl.step(
            rpr, rejection, rpr_ts, rejection_ts, edge_deltas=edge_deltas,
        )
```

- [ ] **Step 4: Add `burst_rpr5` to OBSERVE**

Replace

```python
                log.info(
                    "%s  OBSERVE  %s->%s  rpr=%.4f  low=%d high=%d  elapsed_s=%d  "
                    "attempts=%d  state=ON  metric=rpr",
                    utc_now(), edge[0], edge[1], rpr[edge],
                    st.consecutive_low, st.consecutive_high, elapsed, st.attempts,
                )
```

with

```python
                burst_value = ctrl.burst_last.get(edge)
                burst_obs = (
                    "" if burst_value is None else f"  burst_rpr5={burst_value:.4f}"
                )
                log.info(
                    "%s  OBSERVE  %s->%s  rpr=%.4f  low=%d high=%d  elapsed_s=%d  "
                    "attempts=%d  state=ON  metric=rpr%s",
                    utc_now(), edge[0], edge[1], rpr[edge],
                    st.consecutive_low, st.consecutive_high, elapsed, st.attempts,
                    burst_obs,
                )
```

- [ ] **Step 5: Tag burst sheds in the transition lines**

Replace

```python
            ) in change.lines:
                counter = "consecutive_high" if new == "OFF" else "consecutive_low"
                log.info(
                    "%s  %s  %s→%s   %s=%.2f  %s=%d  attempts=%d  "
                    "from_attempts=%d  metric=%s  elapsed_s=%d",
                    utc_now(), name, old, new, label, value,
                    counter, count, attempts, from_attempts, change.metric,
                    elapsed_s,
                )
```

with

```python
            ) in change.lines:
                counter = "consecutive_high" if new == "OFF" else "consecutive_low"
                line_metric = (
                    "rpr_burst"
                    if name.split("->")[0] in change.burst_callers
                    else change.metric
                )
                log.info(
                    "%s  %s  %s→%s   %s=%.2f  %s=%d  attempts=%d  "
                    "from_attempts=%d  metric=%s  elapsed_s=%d",
                    utc_now(), name, old, new, label, value,
                    counter, count, attempts, from_attempts, line_metric,
                    elapsed_s,
                )
```

- [ ] **Step 6: Verify nothing broke**

Run: `python -m py_compile experiments/retryguard.py; python -m unittest experiments.test_retryguard -v`
Expected: no compile error; all tests pass. The live loop itself has no unit test. It is covered by the replay (Task 5) and by the first live burst run's log.

- [ ] **Step 7: Commit**

```powershell
git add experiments/retryguard.py
git commit -m "feat(retryguard): feed burst windows from run_edge_rpr and log them"
```

---

### Task 3: YAML keys, forwarding and early validation

**Files:**
- Modify: `experiments/run_scenario.py` (new function above `start_retryguard`; `start_retryguard`; `run`)
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Produces: `burst_params_from_cfg(rg_cfg: dict) -> dict` returning `{}` or `{"burst_rpr", "burst_window_seconds", "burst_min_first_attempts"}`. Raises `SystemExit` on a bad config.

- [ ] **Step 1: Write the failing tests**

In `experiments/test_run_scenario.py`, inside `TestStartRetryGuardWiring`, after `test_climb_interval_seconds_absent_when_not_set`, add:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_burst_keys_forwarded_with_defaults(
        self, mock_deploy, mock_ssh, mock_json, mock_script, mock_wait,
    ):
        cfg = self._cfg(enabled=True)
        cfg["retryguard"]["retry_metric"] = "edge_rpr"
        cfg["retryguard"]["burst_rpr"] = 1.5
        run_scenario.start_retryguard(cfg)
        params = mock_json.call_args[0][2]
        self.assertEqual(params["burst_rpr"], 1.5)
        self.assertEqual(params["burst_window_seconds"], 5)
        self.assertEqual(params["burst_min_first_attempts"], 20)

    def test_burst_rpr_with_non_edge_metric_fails_loudly(self):
        cfg = self._cfg(enabled=True)
        cfg["retryguard"]["burst_rpr"] = 1.5  # retry_metric defaults to rejection
        with self.assertRaises(SystemExit):
            run_scenario.burst_params_from_cfg(cfg["retryguard"])
        self.assertEqual(run_scenario.burst_params_from_cfg({"retry_metric": "edge_rpr"}), {})
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest experiments.test_run_scenario.TestStartRetryGuardWiring -v`
Expected: `AttributeError: module 'run_scenario' has no attribute 'burst_params_from_cfg'` and a `KeyError: 'burst_rpr'`.

- [ ] **Step 3: Add the function**

In `experiments/run_scenario.py`, insert immediately above `def start_retryguard(cfg: dict):`:

```python
def burst_params_from_cfg(rg_cfg: dict) -> dict:
    """Burst-mode params for retryguard_params.json. {} when `burst_rpr` is absent."""
    if "burst_rpr" not in rg_cfg:
        return {}
    metric = rg_cfg.get("retry_metric", "rejection")
    if metric != "edge_rpr":
        raise SystemExit(
            f"retryguard.burst_rpr needs retry_metric=edge_rpr, got {metric!r}"
        )
    burst_rpr = float(rg_cfg["burst_rpr"])
    if burst_rpr <= 0:
        raise SystemExit(f"retryguard.burst_rpr must be > 0, got {burst_rpr}")
    return {
        "burst_rpr": burst_rpr,
        "burst_window_seconds": int(rg_cfg.get("burst_window_seconds", 5)),
        "burst_min_first_attempts": int(rg_cfg.get("burst_min_first_attempts", 20)),
    }


```

- [ ] **Step 4: Forward in `start_retryguard`**

Replace

```python
    if "climb_interval_seconds" in rg_cfg:
        params["climb_interval_seconds"] = int(rg_cfg["climb_interval_seconds"])
    write_remote_json(master, "/tmp/retryguard_params.json", params)
```

with

```python
    if "climb_interval_seconds" in rg_cfg:
        params["climb_interval_seconds"] = int(rg_cfg["climb_interval_seconds"])
    params.update(burst_params_from_cfg(rg_cfg))
    write_remote_json(master, "/tmp/retryguard_params.json", params)
```

- [ ] **Step 5: Validate before any cluster work**

In `run`, replace

```python
    cpu_request_fraction_from_cfg(cfg)

    scenario    = cfg["scenario_name"]
```

with

```python
    cpu_request_fraction_from_cfg(cfg)
    if cfg["retryguard"].get("enabled", False):
        burst_params_from_cfg(cfg["retryguard"])

    scenario    = cfg["scenario_name"]
```

- [ ] **Step 6: Run the file**

Run: `python -m unittest experiments.test_run_scenario -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat(run_scenario): forward and validate burst_rpr keys"
```

---

### Task 4: Score burst sheds separately

**Files:**
- Modify: `experiments/analysis_score.py` (`parse_log` transitions; toggle table near line 876)
- Test: `experiments/test_analysis_score.py`

**Interfaces:**
- Consumes: shed line `metric=rpr_burst` from Task 2.
- Produces: transition dicts gain `"burst": bool`. The toggle table gains an `ON→OFF burst` column only when a label has burst events, so old runs render unchanged.

- [ ] **Step 1: Write the failing test**

In `experiments/test_analysis_score.py`, inside `TestLog`, add:

```python
    def test_burst_shed_is_flagged(self):
        text = "\n".join([
            "2026-10-11T16:00:05Z  frontend->checkoutservice  ON→OFF   rpr=1.62  consecutive_high=3  attempts=0  from_attempts=3  metric=rpr_burst  elapsed_s=4",
            "2026-10-11T16:01:00Z  frontend->checkoutservice  ON→OFF   rpr=1.77  consecutive_high=30  attempts=0  from_attempts=3  metric=rpr  elapsed_s=30",
        ])
        events = score.parse_log(text)["transitions"]
        self.assertEqual([e["burst"] for e in events], [True, False])
        self.assertEqual(events[0]["metric"], "rpr")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest experiments.test_analysis_score.TestLog.test_burst_shed_is_flagged -v`
Expected: `KeyError: 'burst'`.

- [ ] **Step 3: Parse the flag**

In `parse_log`, replace

```python
                    "metric": "rpr" if "rpr" in fields else "rejection",
```

with

```python
                    "metric": "rpr" if "rpr" in fields else "rejection",
                    "burst": fields.get("metric") == "rpr_burst",
```

- [ ] **Step 4: Split the toggle table**

Replace

```python
        counts: dict[str, dict[str, int]] = defaultdict(lambda: {"ON→OFF": 0, "OFF→ON": 0, "1→2": 0, "2→3": 0})
        for event in item["transitions"]:
            step = event["step"]
            if step in counts[event["name"]]:
                counts[event["name"]][step] += 1
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Name | ON→OFF | 0→1 | 1→2 | 2→3 |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for name, count in counts.items():
            lines.append(
                f"| {_edge_label(name)} | {count['ON→OFF']} | {count['OFF→ON']} | {count['1→2']} | {count['2→3']} |"
            )
        lines.append("")
```

with

```python
        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"ON→OFF": 0, "OFF→ON": 0, "1→2": 0, "2→3": 0, "burst": 0}
        )
        for event in item["transitions"]:
            step = event["step"]
            if step in counts[event["name"]]:
                counts[event["name"]][step] += 1
            if event.get("burst") and step == "ON→OFF":
                counts[event["name"]]["burst"] += 1
        has_burst = any(count["burst"] for count in counts.values())
        lines.append(f"### {label}")
        lines.append("")
        lines.append(
            "| Name | ON→OFF | 0→1 | 1→2 | 2→3 |" + (" ON→OFF burst |" if has_burst else "")
        )
        lines.append("| --- | ---: | ---: | ---: | ---: |" + (" ---: |" if has_burst else ""))
        for name, count in counts.items():
            row = (
                f"| {_edge_label(name)} | {count['ON→OFF']} | {count['OFF→ON']} | "
                f"{count['1→2']} | {count['2→3']} |"
            )
            if has_burst:
                row += f" {count['burst']} |"
            lines.append(row)
        lines.append("")
```

Then in the event table below it, replace

```python
                f"| {event['timestamp']} | {_edge_label(event['name'])} | {event['step']} | "
```

with

```python
                f"| {event['timestamp']} | {_edge_label(event['name'])} | "
                f"{event['step']}{' (burst)' if event.get('burst') else ''} | "
```

- [ ] **Step 5: Run the analysis tests**

Run: `python -m unittest experiments.test_analysis_score -v`
Expected: all pass. Existing render tests have no burst events, so their output is unchanged.

- [ ] **Step 6: Commit**

```powershell
git add experiments/analysis_score.py experiments/test_analysis_score.py
git commit -m "feat(analysis_score): split burst sheds in toggle counts"
```

---

### Task 5: Replay script

**Files:**
- Create: `experiments/burst_replay.py`
- Test: `experiments/test_retryguard.py` (one test appended to `TestBurstMode`)

**Interfaces:**
- Consumes: `retryguard.BurstWindow`, `retryguard.edge_tick_deltas`, `retryguard.EdgeSnapshot`, `retryguard.parse_row_timestamp`. Run folders containing `service_edges.csv` (columns `timestamp,caller,target,total,2xx,4xx,5xx,retry,...`, cumulative per edge).
- Produces: `replay_edge(snapshots, burst_rpr, window_s, min_first) -> list[str]` returning timestamps of would-be fires. The window is cleared after each fire (the live commit does the same). Recovery is not modelled, so the edge is assumed to stay at 3 attempts. Only the first fire per edge is a trustworthy live prediction. Later fires assume instant recovery.

- [ ] **Step 1: Write the failing test**

Append inside `TestBurstMode` in `experiments/test_retryguard.py`:

```python
    def test_replay_edge_counts_fires_and_clears_after_each(self):
        import burst_replay
        snaps = []
        total = retry = 0.0
        for t in range(12):
            first = 10.0
            extra = 20.0 if t in (4, 5, 6, 7, 8, 9) else 0.0
            total += first + extra
            retry += extra
            snaps.append(retryguard.EdgeSnapshot(
                retryguard.format_row_timestamp(t), total, retry))
        fires = burst_replay.replay_edge(snaps, 1.5, 5, 20)
        self.assertGreaterEqual(len(fires), 1)
        self.assertEqual(fires[0], retryguard.format_row_timestamp(7))
        self.assertEqual(burst_replay.replay_edge(snaps, 50.0, 5, 20), [])
```

Why t=7: every tick has 10 first attempts, and ticks 4–9 add 20 retries each. At t=6 the window holds ticks 2–6 (retry 60, first 50, rpr 1.2, under the bar). At t=7 it holds ticks 3–7 (retry 80, first 50, rpr 1.6), which is the first crossing of 1.5.

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest experiments.test_retryguard.TestBurstMode.test_replay_edge_counts_fires_and_clears_after_each -v`
Expected: `ModuleNotFoundError: No module named 'burst_replay'`.

- [ ] **Step 3: Write the script**

Create `experiments/burst_replay.py`:

```python
"""
burst_replay.py - read-only replay of RetryGuard burst mode over finished runs.

Reads service_edges.csv from each run folder and counts how often the burst
test (sliding window, volume floor, bar at 3 attempts) would have fired, using
the same BurstWindow code as the live controller. Recovery is not modelled:
the edge is assumed to stay at 3 attempts and the window is cleared after each
fire. Only the FIRST fire per edge predicts a live run; later fires assume
instant recovery.

Usage:
    python experiments/burst_replay.py RUN_DIR [RUN_DIR ...] \
        [--bars 1.0 1.5 2.0] [--window 5] [--min-first 20] [--edge frontend->checkoutservice]
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import types
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # retryguard.py imports kubernetes at module scope; replay never uses it.
    import kubernetes  # noqa: F401
except ImportError:
    _k = types.ModuleType("kubernetes")
    _client = types.ModuleType("kubernetes.client")
    _rest = types.ModuleType("kubernetes.client.rest")
    _config = types.ModuleType("kubernetes.config")
    _client.CustomObjectsApi = type("CustomObjectsApi", (), {})
    _rest.ApiException = type("ApiException", (Exception,), {})
    _k.client, _k.config = _client, _config
    sys.modules.update({
        "kubernetes": _k, "kubernetes.client": _client,
        "kubernetes.client.rest": _rest, "kubernetes.config": _config,
    })

import retryguard  # noqa: E402


def load_edges(run_dir: Path) -> dict:
    """{(caller, target): [EdgeSnapshot, ...]} sorted by time, from service_edges.csv."""
    out: dict = defaultdict(list)
    with open(run_dir / "service_edges.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                snap = retryguard.EdgeSnapshot(
                    row["timestamp"], float(row["total"]), float(row["retry"]),
                )
            except (KeyError, ValueError):
                continue
            out[(row["caller"], row["target"])].append(snap)
    return out


def replay_edge(snapshots, burst_rpr: float, window_s: int, min_first: int) -> list:
    """Timestamps where the burst test would fire at 3 attempts. Window clears after a fire."""
    window = retryguard.BurstWindow(window_s, min_first)
    fires = []
    previous = None
    for current in snapshots:
        delta = retryguard.edge_tick_deltas(previous, current)
        previous = current
        if delta is None:
            continue
        window.add(current.timestamp, delta[0], delta[1])
        value = window.rpr()
        if value is not None and value >= burst_rpr:
            fires.append(current.timestamp)
            window.clear()
    return fires


def window_first_sums(snapshots, window_s: int) -> list:
    """Sum of first attempts per sliding window, to sanity-check the volume floor."""
    window = retryguard.BurstWindow(window_s, 0)
    sums = []
    previous = None
    for current in snapshots:
        delta = retryguard.edge_tick_deltas(previous, current)
        previous = current
        if delta is None:
            continue
        window.add(current.timestamp, delta[0], delta[1])
        sums.append(sum(t[2] for t in window._ticks))
    return sums


def offset_s(first_row: str, ts: str) -> int:
    return int(
        (retryguard.parse_row_timestamp(ts) - retryguard.parse_row_timestamp(first_row))
        .total_seconds()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--bars", nargs="+", type=float, default=[1.0, 1.5, 2.0])
    parser.add_argument("--window", type=int, default=retryguard.BURST_WINDOW_SECONDS_DEFAULT)
    parser.add_argument("--min-first", type=int, default=retryguard.BURST_MIN_FIRST_ATTEMPTS_DEFAULT)
    parser.add_argument("--edge", default=None, help="caller->target; default all edges")
    args = parser.parse_args()

    print(f"window={args.window}s min_first={args.min_first} (bar is at 3 attempts)\n")
    print("| Run | Bar | Edge | Fires | First fire (s from first row) |")
    print("| --- | ---: | --- | ---: | ---: |")
    for run_dir in args.run_dirs:
        edges = load_edges(run_dir)
        for bar in args.bars:
            for (caller, target), snaps in sorted(edges.items()):
                name = f"{caller}->{target}"
                if args.edge and name != args.edge:
                    continue
                fires = replay_edge(snaps, bar, args.window, args.min_first)
                if not fires:
                    continue
                first = offset_s(snaps[0].timestamp, fires[0])
                print(f"| {run_dir.name} | {bar:.1f} | {name} | {len(fires)} | {first} |")

    focus = args.edge or "frontend->checkoutservice"
    print(f"\nWindow first-attempt sums on {focus} (is the floor {args.min_first} sane?)")
    for run_dir in args.run_dirs:
        edges = load_edges(run_dir)
        caller, target = focus.split("->")
        sums = window_first_sums(edges.get((caller, target), []), args.window)
        if sums:
            ordered = sorted(sums)
            p5 = ordered[int(0.05 * (len(ordered) - 1))]
            print(
                f"{run_dir.name}: median={statistics.median(sums):.0f} "
                f"p5={p5:.0f} min={min(sums):.0f}"
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test**

Run: `python -m unittest experiments.test_retryguard.TestBurstMode -v`
Expected: all 7 pass.

- [ ] **Step 5: Replay the four S2 both-on holds**

Run:

```powershell
$base = "experiments/results/campaign_48/S2_sustained_overload"
python experiments/burst_replay.py "$base/study4_s2_tune_rgtf1_rep1" "$base/study4_s2_tune_rgtf1_rep2" "$base/study4_s2_tune_rgtf1_rep3" "$base/study4_s2_tune_rgtf1_rep4" --bars 1.0 1.5 2.0
```

Expected: a markdown table of fires per run, bar and edge, then the window first-attempt sums for `frontend->checkoutservice`. Check two things before continuing:
- If the p5 window first-attempt sum on checkout is below 20, the default floor would blind the controller. Report that and propose a lower floor to the user. Do not change the default silently.
- If `rep1`/`rep2` have no `service_edges.csv`, drop them and say so.

Paste the table into the reply to the user. This is the deliverable that decides which bars to run live.

- [ ] **Step 6: Commit**

```powershell
git add experiments/burst_replay.py experiments/test_retryguard.py
git commit -m "feat: read-only burst replay over finished S2 holds"
```

---

### Task 6: Glossary, ADR and implementation doc

**Files:**
- Modify: `CONTEXT.md` (append after the **Retries per request (rpr)** entry at the end of the file)
- Create: `docs/adr/0007-burst-mode-sliding-aggregate.md`
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` (append a section at the end)

- [ ] **Step 1: Add the glossary terms**

Append to the end of `CONTEXT.md`:

```markdown

**Burst mode**:
An opt-in RetryGuard edge-mode handler, on only in runs that set `retryguard.burst_rpr`. It sheds an edge straight to 0 attempts when its burst window crosses the burst bar, beside the normal streak handler. Recovery is the normal recovery. It exists because with TopFull on, retries arrive as short bursts (checkout rpr median 0, max 3.7–6.6) that never hold a 20 s streak.
_Avoid_: burst recovery (there is none), second RetryGuard

**Burst window**:
The sliding sums of retries and first attempts on one edge over the last `burst_window_seconds` (5) of row timestamps. Its rpr is `ΣΔretry / ΣΔfirst`. It is a single aggregate, not a streak, and it does not count below `burst_min_first_attempts` (20) first attempts.
_Avoid_: burst streak, 5-tick streak

**Burst bar**:
`burst_rpr × attempts / attempts_on`. The window rpr must be at or above it (`≥`) to shed. Scaling by cap keeps the bar reachable at 1 and 2 attempts, where rpr cannot exceed the cap.
_Avoid_: threshold (that is the normal `retries_threshold`, 0.4)
```

- [ ] **Step 2: Write the ADR**

Create `docs/adr/0007-burst-mode-sliding-aggregate.md`:

```markdown
# Burst mode sheds on a sliding aggregate with a volume floor, not a consecutive streak

RetryGuard's normal handler needs rpr above the bar for 20 s of consecutive ticks. With TopFull on, checkout's per-tick rpr has a median of 0 and a max of 3.7–6.6, and its longest ticks-above-0.4 streak is 8–12 s, so the normal handler never fires (zero toggles on `study4_s2_tune_rgtf1_rep1`–`rep4`). Burst mode adds a second handler per edge: the sum of retries over the sum of first attempts across a sliding 5 s window must reach `burst_rpr × attempts / attempts_on`, with at least 20 first attempts in the window.

**Status:** proposed (see [2026-10-11-retryguard-burst-mode.md](../superpowers/plans/2026-10-11-retryguard-burst-mode.md)).

**Considered options:** a consecutive-5-tick streak above the bar (a zero tick between two bursts resets it, so it would almost never fire at 1.0 or more); fixed non-overlapping 5 s blocks (a burst straddling a boundary is split); an absolute bar at every cap (unreachable at 1 and 2 attempts, where rpr cannot exceed the cap); a burst-specific recovery (declined for now: the normal recovery stays).

**Consequences:** Burst sheds go to 0 attempts and recover through the normal path (rejection under the re-enable bar for 20 s, then the 10 s climbs). Checkout rejection is above 0.2 about half the time, so retries may stay off for a long stretch after a burst shed. That risk is accepted. The volume floor protects thin edges (cartservice) from shedding on a handful of requests. The replay script `experiments/burst_replay.py` estimates fires per hold before any cluster time is spent.
```

- [ ] **Step 3: Document the keys**

Append to `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`:

```markdown

## Burst mode (opt-in, edge mode)

Set in the scenario YAML `retryguard` block with `retry_metric: edge_rpr`. Off unless `burst_rpr` is present.

| Key | Default | Meaning |
| --- | --- | --- |
| `burst_rpr` | none (off) | Bar at full attempts, for example 1.0, 1.5 or 2.0. The bar at an edge's current cap is `burst_rpr × attempts / attempts_on`. |
| `burst_window_seconds` | 5 | Sliding window over row timestamps. |
| `burst_min_first_attempts` | 20 | Window volume floor. |

The test is `ΣΔretry / ΣΔfirst ≥ bar` over the window. It runs on every edge with attempts above 0, beside the normal handler. A shed goes straight to 0 and recovers the normal way. Log lines: the shed has `metric=rpr_burst`, `START` carries the three keys, and `OBSERVE` carries `burst_rpr5=`. Replay a finished hold with `python experiments/burst_replay.py RUN_DIR ...`. Decision record: [ADR 0007](../docs/adr/0007-burst-mode-sliding-aggregate.md).
```

- [ ] **Step 4: Full verification**

Run:

```powershell
python -m unittest experiments.test_retryguard experiments.test_run_scenario experiments.test_analysis_score -v
```

Expected: all pass. Report the totals.

- [ ] **Step 5: Commit**

```powershell
git add CONTEXT.md docs/adr/0007-burst-mode-sliding-aggregate.md "Guides and Info/RETRYGUARD-IMPLEMENTATION.md"
git commit -m "docs: burst mode glossary, ADR 0007, implementation notes"
```

---

## Self-Review

**Spec coverage**
- Opt-in per run via `burst_rpr`, three keys, defaults 5 and 20: Task 3, Global Constraints.
- Fail loudly on a non-`edge_rpr` metric, at startup: Task 3 (`run` calls it before any cluster work).
- Time-based sliding window, skipped ticks add nothing: `BurstWindow` and `edge_tick_deltas`, Task 1.
- `≥` test and volume floor: `BurstWindow.rpr`, `_burst_check`, Task 1.
- Bar scaled by cap, runs at attempts above 0: `burst_bar`, `_burst_check`, Task 1 (test `test_bar_scales_with_attempt_cap`).
- Window cleared on commit: Task 1 Step 9.
- Shed to 0, normal handler untouched, existing recovery: Task 1 Step 8 (the burst branch precedes the normal handler and `continue`s only when it fires).
- Logging (shed tag, START keys, OBSERVE field): Task 2. Scorer split: Task 4.
- Replay reusing controller code, no recovery: Task 5.
- Glossary terms and ADR: Task 6.
- Live run plan: deliberately excluded.

**Placeholder scan:** none. Every code step shows the full code.

**Type consistency:** `BurstWindow(seconds, min_first_attempts)`, `burst_windows`, `burst_last`, `burst_callers` (a `frozenset` on `Change`, a `dict[str, set]` local in `step`), `edge_tick_deltas -> (d_retry, d_first)`, and the param keys are spelled the same in every task.

**Known limits:** `run_edge_rpr` has no unit test (Task 2 is verified by compile, the existing suite, and the replay). `window_first_sums` reads `window._ticks` directly, which is acceptable for a read-only tool in the same package.
