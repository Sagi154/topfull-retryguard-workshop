# RetryGuard Paper-Fidelity Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace RetryGuard's current asymmetric, window-averaged controller (`window_duration_seconds` / `disable_windows` / `re_enable_windows`) with a literal reproduction of the paper's Algorithm 1: a 1-second sampling loop reading the raw (unaveraged) rejection rate, with a single symmetric `Interval` (in samples) used for both the disable and re-enable transitions.

**Architecture:** Two new params (`sample_interval_seconds`, `interval_samples`) replace the three old ones everywhere they appear: `experiments/retryguard.py` (the controller), `experiments/run_scenario.py` (the orchestrator that uploads params JSON to master), all 16 `experiments/configs/scenario_*.yaml` files, and the docs that describe this mechanism (`RETRYGUARD-IMPLEMENTATION.md`, `experiments/README.md`, `PHASE5-EXPERIMENTS-GUIDE.md`, `SCENARIOS-GUIDE.md`, `METRICS-COLLECTION-GUIDE.md`).

**Tech Stack:** Python 3 (stdlib `unittest`, no pytest available in this environment — run tests with `python -m unittest`), PyYAML, Kubernetes Python client (not installed locally — must be stubbed via `sys.modules` for local unit tests to import `retryguard.py`).

## Global Constraints

- Match RetryGuard paper (`context/RetryGuard.pdf`) Algorithm 1 **exactly**: one `Interval` parameter used symmetrically for both `Consecutive_low ≥ Interval → ON` (line 13) and `Consecutive_high ≥ Interval → OFF` (line 14). No averaging/smoothing of the per-sample metric — `measure_value()` reads the latest raw sample only.
- `sample_interval_seconds` is the loop's sleep/sampling cadence (paper's implicit per-iteration measurement period) — will be set to `1` everywhere per this redesign.
- `interval_samples` is the paper's `Interval` — number of consecutive samples required before a transition fires. At `sample_interval_seconds=1`, `interval_samples` seconds are needed for a transition (e.g. `interval_samples: 30` → 30 consecutive 1-second samples → 30s to react).
- Do not touch `experiments/results/campaign_48/` or `experiments/results/august_38/` — historical data, explicitly out of scope per user instruction ("ignore campaign_48, it's out of date... we'll do a new run later").
- Do not rewrite historical/checklist docs that describe *already-completed* runs under the old scheme (`PHASE5-PHASE6-RUNLIST.md`, `PHASE7-DATA-GAPS.md`, `EXPERIMENT-READINESS-WORKPLAN.md`) — those are accurate historical records of what was actually run and must stay as-is. Only update forward-looking/prescriptive docs (implementation reference, config schema, "how to run" instructions).
- No unit tests for `experiments/retryguard.py` exist today. `kubernetes` is not `pip install`-able / available in this dev environment, and `retryguard.py` does `import kubernetes` unconditionally at module scope — new tests must stub `sys.modules["kubernetes"]`, `sys.modules["kubernetes.client"]`, `sys.modules["kubernetes.client.rest"]` *before* importing `retryguard`, following the same `sys.path.insert` + local import pattern already used in `experiments/test_run_scenario.py`.
- Test runner in this repo is plain `unittest`, not `pytest` (confirmed: `pytest` is not installed; `python -m unittest experiments.test_run_scenario -v` is what actually works). Use `python -m unittest experiments.test_retryguard -v` and `python -m unittest experiments.test_run_scenario -v` to verify.

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `experiments/retryguard.py` | The controller itself — `read_rejection_rate`/`service_rejection_rate` (raw single-sample metric read), `apply_algorithm1` (symmetric single-interval state machine), `run()` (1s-cadence loop) |
| `experiments/test_retryguard.py` (**new**) | Unit tests for the pure-logic functions above (no network/K8s) |
| `experiments/run_scenario.py` | `start_retryguard()` builds the params JSON uploaded to master; `run()`'s printed summary of RetryGuard settings |
| `experiments/test_run_scenario.py` | `TestStartRetryGuardWiring` — update fixture config + assertions to new param names |
| `experiments/configs/scenario_*.yaml` (16 files) | Each has a `retryguard:` block using the old 3-key scheme; all become the new 2-key scheme |
| `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` | Canonical algorithm-mapping reference — update table, example JSON, log example, remove the now-obsolete "asymmetric interval" deviation entry |
| `experiments/README.md` | Config schema reference table |
| `Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md` | Scenario 5 section + example annotated YAML snippet |
| `Guides and Info/SCENARIOS-GUIDE.md` | Scenario 5 "Intervals to test" table + "How to run" commands + Scenario 6 cross-reference |
| `Guides and Info/METRICS-COLLECTION-GUIDE.md` | Example RetryGuard log line |
| `AGENTS.md` | §4 "Current status" — record this redesign per the always-applied rule to keep it current |

---

### Task 1: Failing tests for the raw single-sample rejection-rate reader

**Files:**
- Create: `experiments/test_retryguard.py`
- Read (for reference, no changes yet): `experiments/retryguard.py`

**Interfaces:**
- Consumes: nothing new yet.
- Produces: a test module importable as `experiments.test_retryguard`, establishing the `sys.modules` kubernetes-stub pattern that every later test in this file reuses. Defines `read_rejection_rate(csv_path: Path) -> Optional[float]` and `service_rejection_rate(service: str, endpoints: List[str], record_path: Path) -> Optional[float]` as the target signatures (both **drop** the `window_rows` parameter — later tasks implement this).

- [ ] **Step 1: Write the test file with the kubernetes stub + first two tests**

```python
"""
test_retryguard.py — Unit tests for the pure-logic parts of retryguard.py
(Algorithm 1 state machine + raw single-sample rejection-rate reader).
No network/K8s access; retryguard.py's `kubernetes` import is stubbed out
because the `kubernetes` package is not installed in this dev environment
and is never exercised by these tests.

Run:
    python -m unittest experiments.test_retryguard -v
"""
import csv
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

# --- Stub the kubernetes package before importing retryguard --------------- #
# retryguard.py does `import kubernetes`, `from kubernetes import client,
# config`, and `from kubernetes.client.rest import ApiException` at module
# scope. None of these are exercised by the tests below (they only cover
# metric-reading and the Algorithm 1 state machine), so a minimal stub is
# enough to let the module import.
if "kubernetes" not in sys.modules:
    kubernetes_stub = types.ModuleType("kubernetes")
    client_stub = types.ModuleType("kubernetes.client")
    client_rest_stub = types.ModuleType("kubernetes.client.rest")

    class _CustomObjectsApi:  # pragma: no cover - not exercised by these tests
        pass

    class _ConfigException(Exception):
        pass

    class _ApiException(Exception):
        def __init__(self, status=0, reason=""):
            super().__init__(reason)
            self.status = status
            self.reason = reason

    client_stub.CustomObjectsApi = _CustomObjectsApi
    client_rest_stub.ApiException = _ApiException
    config_stub = types.ModuleType("kubernetes.config")
    config_stub.ConfigException = _ConfigException
    config_stub.load_kube_config = lambda: None
    config_stub.load_incluster_config = lambda: None

    kubernetes_stub.client = client_stub
    kubernetes_stub.config = config_stub

    sys.modules["kubernetes"] = kubernetes_stub
    sys.modules["kubernetes.client"] = client_stub
    sys.modules["kubernetes.client.rest"] = client_rest_stub
    sys.modules["kubernetes.config"] = config_stub

import retryguard  # noqa: E402  (import after sys.modules stubbing above)


def _write_csv(path: Path, rows):
    """rows: list of (rps, fail) tuples. Writes a metric_collector-style CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["RPS", "Fail"])
        writer.writeheader()
        for rps, fail in rows:
            writer.writerow({"RPS": rps, "Fail": fail})


class TestReadRejectionRateSingleSample(unittest.TestCase):
    """
    Paper Algorithm 1's measure_value() reads one raw sample per iteration —
    no averaging. read_rejection_rate must therefore return the rejection
    rate of only the LATEST CSV row, regardless of how many rows precede it.
    """

    def test_returns_latest_row_rejection_rate_ignoring_earlier_rows(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            # Earlier rows are 100% rejection; latest row is 10% — if this
            # were averaged over multiple rows the result would be > 0.10.
            _write_csv(csv_path, [(100, 100), (100, 100), (100, 10)])
            rate = retryguard.read_rejection_rate(csv_path)
            self.assertAlmostEqual(rate, 0.10)

    def test_zero_rps_row_contributes_zero_not_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            _write_csv(csv_path, [(100, 50), (0, 0)])
            rate = retryguard.read_rejection_rate(csv_path)
            self.assertEqual(rate, 0.0)

    def test_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "does_not_exist.csv"
            self.assertIsNone(retryguard.read_rejection_rate(csv_path))

    def test_empty_csv_returns_none(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "getproduct.csv"
            _write_csv(csv_path, [])
            self.assertIsNone(retryguard.read_rejection_rate(csv_path))


class TestServiceRejectionRateSingleSample(unittest.TestCase):
    """service_rejection_rate aggregates (max) across the endpoints mapped
    to one K8s service, each read as a single latest-row sample."""

    def test_takes_max_across_endpoints_latest_rows(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            _write_csv(record_path / "getcart.csv", [(100, 5)])       # 0.05
            _write_csv(record_path / "postcart.csv", [(100, 40)])     # 0.40
            _write_csv(record_path / "emptycart.csv", [(100, 10)])    # 0.10
            rate = retryguard.service_rejection_rate(
                "cartservice",
                ["getcart", "postcart", "emptycart"],
                record_path,
            )
            self.assertAlmostEqual(rate, 0.40)

    def test_missing_all_endpoint_csvs_returns_none(self):
        with TemporaryDirectory() as tmp:
            record_path = Path(tmp)
            rate = retryguard.service_rejection_rate(
                "cartservice", ["getcart", "postcart", "emptycart"], record_path
            )
            self.assertIsNone(rate)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: `TypeError: read_rejection_rate() missing 1 required positional argument: 'window_rows'` (or similar) — the current signature still requires `window_rows`. This confirms the test is exercising the target (not-yet-implemented) signature.

- [ ] **Step 3: Commit**

```bash
git add experiments/test_retryguard.py
git commit -m "test: add failing tests for raw single-sample rejection rate reader"
```

---

### Task 2: Implement the raw single-sample rejection-rate reader

**Files:**
- Modify: `experiments/retryguard.py:143-194`

**Interfaces:**
- Consumes: nothing new.
- Produces: `read_rejection_rate(csv_path: Path) -> Optional[float]` and `service_rejection_rate(service: str, endpoints: List[str], record_path: Path) -> Optional[float]` — both used by `run()` (updated in Task 5).

- [ ] **Step 1: Replace the averaging logic with single-latest-row logic**

Replace this block (`experiments/retryguard.py:143-194`):

```python
def read_rejection_rate(csv_path: Path, window_rows: int) -> Optional[float]:
    """
    Mean(Fail / RPS) over the last window_rows data rows.
    Returns None if the file is missing or has no usable data rows.
    Rows with RPS == 0 contribute rejection rate 0 (no load ≠ overload).
    """
    if not csv_path.is_file():
        return None

    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except OSError:
        return None

    if not rows:
        return None

    window = rows[-window_rows:]
    rates = []
    for row in window:
        try:
            rps = float(row["RPS"])
            fail = float(row["Fail"])
        except (KeyError, TypeError, ValueError):
            continue
        if rps <= 0:
            rates.append(0.0)
        else:
            rates.append(fail / rps)

    if not rates:
        return None
    return sum(rates) / len(rates)


def service_rejection_rate(
    service: str,
    endpoints: List[str],
    record_path: Path,
    window_rows: int,
) -> Optional[float]:
    """Max rejection rate across endpoints mapped to this service."""
    rates = []
    for ep in endpoints:
        rate = read_rejection_rate(record_path / f"{ep}.csv", window_rows)
        if rate is not None:
            rates.append(rate)
    if not rates:
        return None
    return max(rates)
```

with:

```python
def read_rejection_rate(csv_path: Path) -> Optional[float]:
    """
    Fail / RPS of the single most recent data row (paper Algorithm 1's
    measure_value() — one raw sample per iteration, no averaging).
    Returns None if the file is missing or has no usable data rows.
    A row with RPS == 0 contributes rejection rate 0 (no load ≠ overload).
    """
    if not csv_path.is_file():
        return None

    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except OSError:
        return None

    if not rows:
        return None

    row = rows[-1]
    try:
        rps = float(row["RPS"])
        fail = float(row["Fail"])
    except (KeyError, TypeError, ValueError):
        return None

    if rps <= 0:
        return 0.0
    return fail / rps


def service_rejection_rate(
    service: str,
    endpoints: List[str],
    record_path: Path,
) -> Optional[float]:
    """Max rejection rate (latest sample) across endpoints mapped to this service."""
    rates = []
    for ep in endpoints:
        rate = read_rejection_rate(record_path / f"{ep}.csv")
        if rate is not None:
            rates.append(rate)
    if not rates:
        return None
    return max(rates)
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: `TestReadRejectionRateSingleSample` and `TestServiceRejectionRateSingleSample` all `PASS` (5 tests).

- [ ] **Step 3: Commit**

```bash
git add experiments/retryguard.py
git commit -m "feat: read_rejection_rate reads a single raw sample, no averaging"
```

---

### Task 3: Failing tests for the symmetric single-`Interval` state machine

**Files:**
- Modify: `experiments/test_retryguard.py` (append new test class)

**Interfaces:**
- Consumes: `retryguard.ServiceState` (existing dataclass, unchanged).
- Produces: target signature `apply_algorithm1(state: ServiceState, rejection: float, threshold: float, interval: int) -> Optional[str]` (drops `re_enable_windows` / `disable_windows`, single `interval` param used symmetrically) — used by `run()` (updated in Task 5).

- [ ] **Step 1: Append the failing tests**

Add to `experiments/test_retryguard.py` (before the `if __name__ == "__main__":` line):

```python
class TestApplyAlgorithm1Symmetric(unittest.TestCase):
    """
    Paper Algorithm 1 uses ONE Interval for both transitions:
        13: if Consecutive_low >= Interval then Retries <- ON
        14: else if Consecutive_high >= Interval then Retries <- OFF
    apply_algorithm1 must take a single `interval` argument applied
    symmetrically to both directions.
    """

    def _state(self, initial="ON"):
        state = retryguard.ServiceState()
        state.retries_state = initial
        return state

    def test_no_transition_below_interval_low(self):
        state = self._state(initial="OFF")
        for _ in range(2):
            result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_low, 2)

    def test_turns_on_after_interval_consecutive_low_samples(self):
        state = self._state(initial="OFF")
        result = None
        for _ in range(3):
            result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)
        self.assertEqual(result, "ON")

    def test_turns_off_after_interval_consecutive_high_samples(self):
        state = self._state(initial="ON")
        result = None
        for _ in range(3):
            result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        self.assertEqual(result, "OFF")

    def test_same_interval_value_governs_both_directions(self):
        # A single dip resets the high-streak (paper lines 9-10), so with
        # interval=2, two highs then one low then two highs never reaches 2
        # consecutive highs until the streak restarts cleanly.
        state = self._state(initial="ON")
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=2)  # high=1
        result = retryguard.apply_algorithm1(state, 0.05, 0.20, interval=2)  # resets to low=1
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 0)
        self.assertEqual(state.consecutive_low, 1)

    def test_single_dip_resets_consecutive_high_streak(self):
        state = self._state(initial="ON")
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=1
        retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=2
        retryguard.apply_algorithm1(state, 0.05, 0.20, interval=3)  # dip -> high resets to 0
        result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)  # high=1 again
        self.assertIsNone(result)
        self.assertEqual(state.consecutive_high, 1)

    def test_no_repeat_transition_once_already_in_target_state(self):
        state = self._state(initial="OFF")
        for _ in range(3):
            retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        # already OFF and still above threshold: no further transition fires
        result = retryguard.apply_algorithm1(state, 0.50, 0.20, interval=3)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: `TypeError: apply_algorithm1() got an unexpected keyword argument 'interval'` — current signature takes `re_enable_windows`/`disable_windows` positionally, not `interval`.

- [ ] **Step 3: Commit**

```bash
git add experiments/test_retryguard.py
git commit -m "test: add failing tests for symmetric single-Interval state machine"
```

---

### Task 4: Implement the symmetric single-`Interval` state machine

**Files:**
- Modify: `experiments/retryguard.py:297-330`

**Interfaces:**
- Consumes: `ServiceState` (unchanged).
- Produces: `apply_algorithm1(state, rejection, threshold, interval) -> Optional[str]`, called by `run()` (Task 5).

- [ ] **Step 1: Replace the function**

Replace (`experiments/retryguard.py:297-330`):

```python
def apply_algorithm1(
    state: ServiceState,
    rejection: float,
    threshold: float,
    re_enable_windows: int,
    disable_windows: int,
) -> Optional[str]:
    """
    One Algorithm 1 iteration. Mutates state counters.
    Returns desired retries state ("ON"/"OFF") if a transition should fire,
    otherwise None (keep current state).
    """
    # Lines 5–12
    if rejection < threshold:
        state.consecutive_low += 1
        state.consecutive_high = 0
    elif rejection > threshold:
        state.consecutive_high += 1
        state.consecutive_low = 0
    else:
        # Exactly == Threshold (float rarity): reset both counters
        state.consecutive_low = 0
        state.consecutive_high = 0

    # Lines 13–14 (asymmetric Interval: re_enable vs disable)
    desired = state.retries_state
    if state.consecutive_low >= re_enable_windows:
        desired = "ON"
    elif state.consecutive_high >= disable_windows:
        desired = "OFF"

    if desired != state.retries_state:
        return desired
    return None
```

with:

```python
def apply_algorithm1(
    state: ServiceState,
    rejection: float,
    threshold: float,
    interval: int,
) -> Optional[str]:
    """
    One Algorithm 1 iteration. Mutates state counters.
    `interval` is the paper's single `Interval` parameter, applied
    symmetrically to both the ON (line 13) and OFF (line 14) transitions.
    Returns desired retries state ("ON"/"OFF") if a transition should fire,
    otherwise None (keep current state).
    """
    # Lines 5–12
    if rejection < threshold:
        state.consecutive_low += 1
        state.consecutive_high = 0
    elif rejection > threshold:
        state.consecutive_high += 1
        state.consecutive_low = 0
    else:
        # Exactly == Threshold (float rarity): reset both counters
        state.consecutive_low = 0
        state.consecutive_high = 0

    # Lines 13–14 (single symmetric Interval, per the paper)
    desired = state.retries_state
    if state.consecutive_low >= interval:
        desired = "ON"
    elif state.consecutive_high >= interval:
        desired = "OFF"

    if desired != state.retries_state:
        return desired
    return None
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: all tests in `TestApplyAlgorithm1Symmetric` `PASS` (6 tests); full file total 11 tests passing.

- [ ] **Step 3: Commit**

```bash
git add experiments/retryguard.py
git commit -m "feat: apply_algorithm1 uses one symmetric Interval, matching the paper"
```

---

### Task 5: Wire the new params through `retryguard.py`'s `run()` / `main()` / constants

**Files:**
- Modify: `experiments/retryguard.py:1-11` (docstring), `:60-67` (`REQUIRED_PARAMS`), `:333-441` (`run()`), `:455` (`--params` help text)
- Modify: `experiments/test_retryguard.py` (append `TestLoadParams` class)

**Interfaces:**
- Consumes: `read_rejection_rate`/`service_rejection_rate`/`apply_algorithm1` from Tasks 2 and 4.
- Produces: `REQUIRED_PARAMS = ("rejection_threshold", "sample_interval_seconds", "interval_samples", "retry_attempts_on", "retry_attempts_off")`, consumed by `run_scenario.py::start_retryguard` (Task 6) via the params JSON contract.

- [ ] **Step 1: Write the failing test for `REQUIRED_PARAMS` / `load_params`**

Append to `experiments/test_retryguard.py` (before `if __name__ == "__main__":`):

```python
class TestLoadParamsRequiredKeys(unittest.TestCase):
    def test_new_param_names_are_required(self):
        self.assertIn("sample_interval_seconds", retryguard.REQUIRED_PARAMS)
        self.assertIn("interval_samples", retryguard.REQUIRED_PARAMS)

    def test_old_param_names_are_no_longer_required(self):
        self.assertNotIn("window_duration_seconds", retryguard.REQUIRED_PARAMS)
        self.assertNotIn("disable_windows", retryguard.REQUIRED_PARAMS)
        self.assertNotIn("re_enable_windows", retryguard.REQUIRED_PARAMS)

    def test_load_params_rejects_missing_new_keys(self):
        import json
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            params_path = Path(tmp) / "params.json"
            with open(params_path, "w") as f:
                json.dump(
                    {
                        "rejection_threshold": 0.2,
                        "retry_attempts_on": 3,
                        "retry_attempts_off": 0,
                        # sample_interval_seconds / interval_samples deliberately missing
                    },
                    f,
                )
            with self.assertRaises(SystemExit):
                retryguard.load_params(str(params_path))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: `AssertionError` — `REQUIRED_PARAMS` still contains `window_duration_seconds`/`disable_windows`/`re_enable_windows` and not the new names.

- [ ] **Step 3: Update `REQUIRED_PARAMS`, docstring, `run()`, and CLI help text**

Replace (`experiments/retryguard.py:60-67`):

```python
REQUIRED_PARAMS = (
    "rejection_threshold",
    "window_duration_seconds",
    "disable_windows",
    "re_enable_windows",
    "retry_attempts_on",
    "retry_attempts_off",
)
```

with:

```python
REQUIRED_PARAMS = (
    "rejection_threshold",
    "sample_interval_seconds",
    "interval_samples",
    "retry_attempts_on",
    "retry_attempts_off",
)
```

Replace the module docstring line (`experiments/retryguard.py:10`):

```python
retries.attempts when consecutive windows cross the threshold.
```

with:

```python
retries.attempts when Interval consecutive samples cross the threshold
(RetryGuard paper Algorithm 1, applied literally: 1 raw sample per second,
one symmetric Interval for both the disable and re-enable transitions).
```

Replace `run()` (`experiments/retryguard.py:333-441`):

```python
def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    svc_map = service_endpoint_map()
    endpoints = list(ENDPOINT_SERVICE_MAP.keys())
    window_rows = int(params["window_duration_seconds"])
    threshold = float(params["rejection_threshold"])
    re_enable_windows = int(params["re_enable_windows"])
    disable_windows = int(params["disable_windows"])
    attempts_on = int(params["retry_attempts_on"])
    attempts_off = int(params["retry_attempts_off"])

    wait_for_csvs(record_path, endpoints)

    states = {svc: ServiceState() for svc in svc_map}
    log.info(
        "%s  START  threshold=%.2f window=%ss disable_windows=%d "
        "re_enable_windows=%d services=%s",
        utc_now(),
        threshold,
        window_rows,
        disable_windows,
        re_enable_windows,
        sorted(svc_map.keys()),
    )

    while not _shutdown:
        time.sleep(window_rows)
        if _shutdown:
            break

        for service, eps in sorted(svc_map.items()):
            rejection = service_rejection_rate(
                service, eps, record_path, window_rows
            )
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this window",
                    utc_now(),
                    service,
                )
                continue

            state = states[service]
            desired = apply_algorithm1(
                state,
                rejection,
                threshold,
                re_enable_windows,
                disable_windows,
            )

            log.info(
                "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  state=%s",
                utc_now(),
                service,
                rejection,
                state.consecutive_low,
                state.consecutive_high,
                state.retries_state,
            )

            if desired is None:
                continue

            attempts = attempts_on if desired == "ON" else attempts_off
            old = state.retries_state
            try:
                patch_virtualservice(api, service, attempts)
            except ApiException as exc:
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  attempts=%d  "
                    "http=%s  reason=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    attempts,
                    exc.status,
                    exc.reason,
                )
                continue
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  error=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    exc,
                )
                continue

            counter = (
                f"consecutive_low={state.consecutive_low}"
                if desired == "ON"
                else f"consecutive_high={state.consecutive_high}"
            )
            log.info(
                "%s  %s  %s→%s   rejection=%.2f  %s  attempts=%d",
                utc_now(),
                service,
                old,
                desired,
                rejection,
                counter,
                attempts,
            )
            state.retries_state = desired

    log.info("%s  EXIT", utc_now())
```

with:

```python
def run(params: dict, record_path: Path, api: client.CustomObjectsApi) -> None:
    svc_map = service_endpoint_map()
    endpoints = list(ENDPOINT_SERVICE_MAP.keys())
    sample_interval = int(params["sample_interval_seconds"])
    interval = int(params["interval_samples"])
    threshold = float(params["rejection_threshold"])
    attempts_on = int(params["retry_attempts_on"])
    attempts_off = int(params["retry_attempts_off"])

    wait_for_csvs(record_path, endpoints)

    states = {svc: ServiceState() for svc in svc_map}
    log.info(
        "%s  START  threshold=%.2f sample_interval=%ss interval_samples=%d "
        "(%ds) services=%s",
        utc_now(),
        threshold,
        sample_interval,
        interval,
        sample_interval * interval,
        sorted(svc_map.keys()),
    )

    while not _shutdown:
        time.sleep(sample_interval)
        if _shutdown:
            break

        for service, eps in sorted(svc_map.items()):
            rejection = service_rejection_rate(service, eps, record_path)
            if rejection is None:
                log.info(
                    "%s  SKIP  %s  no metric data this sample",
                    utc_now(),
                    service,
                )
                continue

            state = states[service]
            desired = apply_algorithm1(state, rejection, threshold, interval)

            log.info(
                "%s  OBSERVE  %s  rejection=%.4f  low=%d high=%d  state=%s",
                utc_now(),
                service,
                rejection,
                state.consecutive_low,
                state.consecutive_high,
                state.retries_state,
            )

            if desired is None:
                continue

            attempts = attempts_on if desired == "ON" else attempts_off
            old = state.retries_state
            try:
                patch_virtualservice(api, service, attempts)
            except ApiException as exc:
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  attempts=%d  "
                    "http=%s  reason=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    attempts,
                    exc.status,
                    exc.reason,
                )
                continue
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                log.info(
                    "%s  PATCH_FAIL  %s  %s→%s  error=%s",
                    utc_now(),
                    service,
                    old,
                    desired,
                    exc,
                )
                continue

            counter = (
                f"consecutive_low={state.consecutive_low}"
                if desired == "ON"
                else f"consecutive_high={state.consecutive_high}"
            )
            log.info(
                "%s  %s  %s→%s   rejection=%.2f  %s  attempts=%d",
                utc_now(),
                service,
                old,
                desired,
                rejection,
                counter,
                attempts,
            )
            state.retries_state = desired

    log.info("%s  EXIT", utc_now())
```

Replace the CLI help text (`experiments/retryguard.py:455`):

```python
        help="Path to RetryGuard params JSON "
        "(rejection_threshold, window_duration_seconds, ...)",
```

with:

```python
        help="Path to RetryGuard params JSON "
        "(rejection_threshold, sample_interval_seconds, interval_samples, ...)",
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest experiments.test_retryguard -v`

Expected: all tests `PASS` (14 tests total).

- [ ] **Step 5: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat: retryguard.py run() loop uses sample_interval_seconds + interval_samples"
```

---

### Task 6: Update `run_scenario.py` wiring + its tests

**Files:**
- Modify: `experiments/run_scenario.py:637-648` (`start_retryguard` params dict + log line), `:1096-1102` (`run()`'s printed summary)
- Modify: `experiments/test_run_scenario.py:222-257` (`TestStartRetryGuardWiring`)

**Interfaces:**
- Consumes: `retryguard:` YAML block (Task 7) with keys `enabled`, `rejection_threshold`, `sample_interval_seconds`, `interval_samples`, `retry_attempts_on`, `retry_attempts_off`.
- Produces: the params JSON uploaded to `/tmp/retryguard_params.json`, consumed by `retryguard.py::load_params` (Task 5).

- [ ] **Step 1: Update the failing test fixture first**

In `experiments/test_run_scenario.py`, replace (`:230-237`):

```python
            "retryguard": {
                "enabled": enabled,
                "rejection_threshold": 0.20,
                "window_duration_seconds": 30,
                "disable_windows": 2,
                "re_enable_windows": 3,
                "retry_attempts_on": 3,
                "retry_attempts_off": 0,
            },
```

with:

```python
            "retryguard": {
                "enabled": enabled,
                "rejection_threshold": 0.20,
                "sample_interval_seconds": 1,
                "interval_samples": 30,
                "retry_attempts_on": 3,
                "retry_attempts_off": 0,
            },
```

- [ ] **Step 2: Run to verify wiring tests still pass against the old code (sanity check the fixture didn't break anything unrelated)**

Run: `python -m unittest experiments.test_run_scenario -v 2>&1`

Expected: `TestStartRetryGuardWiring` tests still `PASS` — they only assert `deploy_repo_script`/`deploy_not_called`, not the params dict contents, so the fixture change alone doesn't fail them yet. This step is a safety check before touching production code.

- [ ] **Step 3: Update `start_retryguard()` in `run_scenario.py`**

Replace (`experiments/run_scenario.py:637-648`):

```python
    # Upload RetryGuard runtime parameters as JSON
    params = {
        "rejection_threshold":    rg_cfg["rejection_threshold"],
        "window_duration_seconds": rg_cfg["window_duration_seconds"],
        "disable_windows":        rg_cfg["disable_windows"],
        "re_enable_windows":      rg_cfg["re_enable_windows"],
        "retry_attempts_on":      rg_cfg["retry_attempts_on"],
        "retry_attempts_off":     rg_cfg["retry_attempts_off"],
    }
    write_remote_json(master, "/tmp/retryguard_params.json", params)
    step(f"Uploaded RetryGuard params: re_enable_windows={params['re_enable_windows']} "
         f"({params['re_enable_windows'] * params['window_duration_seconds']}s)")
```

with:

```python
    # Upload RetryGuard runtime parameters as JSON
    params = {
        "rejection_threshold":      rg_cfg["rejection_threshold"],
        "sample_interval_seconds": rg_cfg["sample_interval_seconds"],
        "interval_samples":        rg_cfg["interval_samples"],
        "retry_attempts_on":       rg_cfg["retry_attempts_on"],
        "retry_attempts_off":      rg_cfg["retry_attempts_off"],
    }
    write_remote_json(master, "/tmp/retryguard_params.json", params)
    step(f"Uploaded RetryGuard params: interval_samples={params['interval_samples']} "
         f"({params['interval_samples'] * params['sample_interval_seconds']}s)")
```

- [ ] **Step 4: Update the printed run summary in `run()`**

Replace (`experiments/run_scenario.py:1096-1102`):

```python
    if rg_enabled:
        rg = cfg["retryguard"]
        rew = rg["re_enable_windows"]
        wd  = rg["window_duration_seconds"]
        print(f"    threshold      : {rg['rejection_threshold']*100:.0f}%")
        print(f"    disable_windows: {rg['disable_windows']}  ({rg['disable_windows']*wd}s)")
        print(f"    re_enable_windows: {rew}  ({rew*wd}s)")
```

with:

```python
    if rg_enabled:
        rg = cfg["retryguard"]
        sample_interval = rg["sample_interval_seconds"]
        interval = rg["interval_samples"]
        print(f"    threshold      : {rg['rejection_threshold']*100:.0f}%")
        print(f"    sample_interval_seconds: {sample_interval}s")
        print(f"    interval_samples: {interval}  ({interval*sample_interval}s, symmetric ON/OFF)")
```

- [ ] **Step 5: Run the full test_run_scenario.py suite to verify everything passes**

Run: `python -m unittest experiments.test_run_scenario -v`

Expected: all tests `PASS`, no references to `re_enable_windows`/`window_duration_seconds`/`disable_windows` remain.

- [ ] **Step 6: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: run_scenario.py wires sample_interval_seconds + interval_samples to RetryGuard"
```

---

### Task 7: Update all 16 scenario YAML configs

**Files:**
- Modify: `experiments/configs/scenario_1_baseline.yaml`, `scenario_1_retryguard.yaml`, `scenario_2_baseline.yaml`, `scenario_2_retryguard.yaml`, `scenario_3_baseline.yaml`, `scenario_3_retryguard.yaml`, `scenario_4a_baseline.yaml`, `scenario_4a_retryguard.yaml`, `scenario_4b_baseline.yaml`, `scenario_4b_retryguard.yaml`, `scenario_6_recovery_baseline.yaml`, `scenario_6_recovery_retryguard.yaml` (12 files: same edit in each)
- Modify: `experiments/configs/scenario_5_interval_10s.yaml`, `scenario_5_interval_20s.yaml`, `scenario_5_interval_30s.yaml`, `scenario_5_interval_60s.yaml` (4 files: swept value + header rewrite)

**Interfaces:**
- Consumes: nothing (leaf config files).
- Produces: the `retryguard:` YAML block consumed by `run_scenario.py::start_retryguard` (Task 6).

- [ ] **Step 1: Update the 12 non-S5 configs — mechanical key replacement**

In each of `scenario_1_baseline.yaml`, `scenario_1_retryguard.yaml`, `scenario_2_baseline.yaml`, `scenario_2_retryguard.yaml`, `scenario_3_baseline.yaml`, `scenario_3_retryguard.yaml`, `scenario_4a_baseline.yaml`, `scenario_4a_retryguard.yaml`, `scenario_4b_baseline.yaml`, `scenario_4b_retryguard.yaml`, `scenario_6_recovery_baseline.yaml`, `scenario_6_recovery_retryguard.yaml`, find the `retryguard:` block and replace the three old keys with the two new ones. For example, in `scenario_1_baseline.yaml`:

Replace:

```yaml
retryguard:
  enabled: false
  rejection_threshold: 0.20
  window_duration_seconds: 30  # one observation window = 30 s
  disable_windows: 2           # 2 consecutive windows above threshold → disable
  re_enable_windows: 3         # 3 consecutive windows below threshold → re-enable
  retry_attempts_on: 3
  retry_attempts_off: 0
```

with:

```yaml
retryguard:
  enabled: false
  rejection_threshold: 0.20
  sample_interval_seconds: 1   # loop cadence — 1 raw sample/sec (paper Algorithm 1)
  interval_samples: 30         # paper's Interval — 30 consecutive samples = 30s, symmetric ON/OFF
  retry_attempts_on: 3
  retry_attempts_off: 0
```

Apply the equivalent replacement (same two new lines, keep `enabled:`/`retry_attempts_*` unchanged) to the other 11 files. Every one of them currently has:

```yaml
  window_duration_seconds: 30
  disable_windows: 2
  re_enable_windows: 3
```

(possibly with trailing `#` comments like `# 2 windows × 30s = 60s above threshold → disable` — drop those comments too, they describe the old asymmetric scheme) — replace with:

```yaml
  sample_interval_seconds: 1
  interval_samples: 30         # paper default (Sec. 6.2), symmetric ON/OFF
```

Also fix cross-references inside these same files that name the old params in prose comments:
- `scenario_2_retryguard.yaml` header comment (top of file): `"After ~20% rejection persists across 2 consecutive 30-second windows"` → `"After ~20% rejection persists across 30 consecutive 1-second samples"`.
- `scenario_6_recovery_retryguard.yaml` header comment: `"Paper-default re_enable_windows: 3 (90s effective)."` → `"Paper-default interval_samples: 30 (30s, symmetric ON/OFF)."`; and the `description:` field `"re-enable interval = paper default (3 windows × 30s = 90s)"` → `"re-enable interval = paper default (30 consecutive 1s samples = 30s)"`; and the inline comment `# paper default — same as scenario_5_interval_30s.yaml` stays valid (no change needed there — S5's 30s config now literally matches by same `interval_samples: 30` value, see Step 2).

- [ ] **Step 2: Update the 4 Scenario 5 configs — swept value + header rewrite**

The old scheme mislabeled these files (`interval_10s.yaml` actually meant `re_enable_windows: 1` × `window_duration_seconds: 30` = 30s, not 10s — a "historical" mislabel called out in the file's own comments). The new symmetric scheme makes the filenames literally accurate: `sample_interval_seconds: 1` + `interval_samples: 10/20/30/60` gives exactly 10s/20s/30s/60s, applied symmetrically to both disable and re-enable.

In `scenario_5_interval_10s.yaml`, replace the header comment block:

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5 — Re-enable Interval Tuning  |  Interval: 10s (aggressive)
#
# Same load as Scenario 6 (forced recovery), NOT Scenario 2. RetryGuard ALWAYS ON.
# Only the re_enable_windows parameter changes across the four S5 configs.
#
# re_enable_windows: 1  →  1 × 30s = 30s effective wait
# (RetryGuard re-enables retries after just 1 window below threshold.
#  Folder label "10s" is historical; see PHASE5-EXPERIMENTS-GUIDE.md §2 table.)
#
# Risk: re-enables too fast. Retries restart before bottleneck is truly clear.
# Likely outcome: oscillation — disable/re-enable cycles repeat rapidly.
# Watch for: number of toggle events per run (too many = instability).
#
# Gap 1: flat S2 never produced OFF→ON. This file uses Scenario 6's 900s
# load-drop profile so re_enable_windows can fire. Load must stay
# byte-identical to scenario_6_recovery_{baseline,retryguard}.yaml and the
# other three scenario_5_interval_*.yaml files — only re_enable_windows
# differs across the four S5 files. Compare against S6 baseline, not S2.
# ─────────────────────────────────────────────────────────────────────────────
```

with:

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5 — Interval Tuning  |  Interval: 10s (aggressive)
#
# Same load as Scenario 6 (forced recovery), NOT Scenario 2. RetryGuard ALWAYS ON.
# Only interval_samples changes across the four S5 configs — applied
# symmetrically to both the disable and re-enable transitions (paper
# Algorithm 1 uses one Interval for both, not separate disable/re-enable
# values). sample_interval_seconds is fixed at 1 across all four.
#
# interval_samples: 10  →  10 consecutive 1s samples = 10s, both directions.
#
# Risk: re-enables (and disables) too fast. Retries restart before bottleneck
# is truly clear. Likely outcome: oscillation — disable/re-enable cycles
# repeat rapidly. Watch for: number of toggle events per run (too many =
# instability).
#
# Gap 1: flat S2 never produced OFF→ON. This file uses Scenario 6's 900s
# load-drop profile so re-enable can fire. Load must stay byte-identical to
# scenario_6_recovery_{baseline,retryguard}.yaml and the other three
# scenario_5_interval_*.yaml files — only interval_samples differs across
# the four S5 files. Compare against S6 baseline, not S2.
# ─────────────────────────────────────────────────────────────────────────────
```

and the `retryguard:` block:

```yaml
retryguard:
  enabled: true
  rejection_threshold: 0.20
  window_duration_seconds: 30
  disable_windows: 2
  re_enable_windows: 1         # ← THE VARIABLE: 1 window × 30s = 30s effective
  retry_attempts_on: 3
  retry_attempts_off: 0
```

with:

```yaml
retryguard:
  enabled: true
  rejection_threshold: 0.20
  sample_interval_seconds: 1
  interval_samples: 10         # ← THE VARIABLE: 10 consecutive 1s samples = 10s, symmetric ON/OFF
  retry_attempts_on: 3
  retry_attempts_off: 0
```

Also update the `description:` field's `"re-enable interval = 10s (aggressive)"` line to `"interval = 10s (aggressive), symmetric ON/OFF"`.

Apply the analogous edits to `scenario_5_interval_20s.yaml` (`interval_samples: 20`, header says "Interval: 20s (below paper default)"), `scenario_5_interval_30s.yaml` (`interval_samples: 30`, header says "Interval: 30s (PAPER DEFAULT)"), and `scenario_5_interval_60s.yaml` (`interval_samples: 60`, header says "Interval: 60s (conservative)") — each following the same header-rewrite pattern (replace "re_enable_windows"/"window" language with "interval_samples"/"symmetric" language, replace the `N windows × 30s = Xs effective` line with `N consecutive 1s samples = Ns, symmetric ON/OFF`).

- [ ] **Step 3: Sanity-check no old param names remain in any config**

Run (PowerShell):

```powershell
Select-String -Path "experiments\configs\*.yaml" -Pattern "window_duration_seconds|disable_windows|re_enable_windows"
```

Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add experiments/configs/*.yaml
git commit -m "feat: all 16 scenario configs use sample_interval_seconds + interval_samples"
```

---

### Task 8: Update `RETRYGUARD-IMPLEMENTATION.md`

**Files:**
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update the example params JSON**

Replace:

```json
{
  "rejection_threshold": 0.20,
  "window_duration_seconds": 30,
  "disable_windows": 2,
  "re_enable_windows": 3,
  "retry_attempts_on": 3,
  "retry_attempts_off": 0
}
```

with:

```json
{
  "rejection_threshold": 0.20,
  "sample_interval_seconds": 1,
  "interval_samples": 30,
  "retry_attempts_on": 3,
  "retry_attempts_off": 0
}
```

- [ ] **Step 2: Update the algorithm-mapping table**

Replace:

```markdown
| Algorithm 1 variable | Our param / behavior |
|----------------------|----------------------|
| `Failures` (`measure_value()`) | Mean(`Fail / RPS`) over last `window_duration_seconds` CSV rows |
| `Threshold` | `rejection_threshold` (e.g. 0.20) |
| `Interval` (line 13, re-enable) | `re_enable_windows` (asymmetric extension of the paper's single Interval) |
| `Interval` (line 14, disable) | `disable_windows` |
| `Retries ← ON` | Patch VirtualService `retries.attempts` → `retry_attempts_on` |
| `Retries ← OFF` | Disable retries on the VirtualService (see patch note below) |
```

with:

```markdown
| Algorithm 1 variable | Our param / behavior |
|----------------------|----------------------|
| `Failures` (`measure_value()`) | Raw `Fail / RPS` of the single most recent CSV row (no averaging) |
| Loop cadence (implicit 1 measurement/iteration) | `sample_interval_seconds` (=1, one sample per second) |
| `Threshold` | `rejection_threshold` (e.g. 0.20) |
| `Interval` (lines 13 and 14 — symmetric, same value both directions) | `interval_samples` |
| `Retries ← ON` | Patch VirtualService `retries.attempts` → `retry_attempts_on` |
| `Retries ← OFF` | Disable retries on the VirtualService (see patch note below) |
```

- [ ] **Step 3: Update the metric-source section**

Replace:

```markdown
Columns used: `RPS`, `Fail`. Rejection rate for a window = mean(`Fail/RPS`) over the last N rows where N = `window_duration_seconds`. Rows with `RPS == 0` contribute 0 (no load ≠ overload). If a CSV is missing for a window, that service is **skipped** (counters unchanged).
```

with:

```markdown
Columns used: `RPS`, `Fail`. Rejection rate for a sample = `Fail/RPS` of the single most recent CSV row — no averaging, matching the paper's Algorithm 1 literally. Rows with `RPS == 0` contribute 0 (no load ≠ overload). If a CSV is missing for a sample, that service is **skipped** (counters unchanged).
```

- [ ] **Step 4: Update the log-format example**

Replace:

```
2026-08-04T18:30:00Z  START  threshold=0.20 window=30s ...
2026-08-04T18:30:30Z  OBSERVE  checkoutservice  rejection=0.3100  low=0 high=1  state=ON
2026-08-04T18:33:32Z  cartservice  ON→OFF   rejection=0.31  consecutive_high=2  attempts=0
2026-08-04T18:35:02Z  checkoutservice  OFF→ON   rejection=0.08  consecutive_low=3  attempts=3
```

with:

```
2026-08-04T18:30:00Z  START  threshold=0.20 sample_interval=1s interval_samples=30 (30s) ...
2026-08-04T18:30:01Z  OBSERVE  checkoutservice  rejection=0.3100  low=0 high=1  state=ON
2026-08-04T18:30:30Z  cartservice  ON→OFF   rejection=0.31  consecutive_high=30  attempts=0
2026-08-04T18:31:15Z  checkoutservice  OFF→ON   rejection=0.08  consecutive_low=30  attempts=3
```

- [ ] **Step 5: Remove the now-obsolete "Asymmetric Interval" deviation and renumber**

Replace:

```markdown
## Deviations from the paper pseudocode

1. **Initial state `ON`** — Algorithm 1 initializes `Retries ← OFF`. We start `ON` so the controller matches the default VirtualService (`attempts: 3`) and Scenario 1 (healthy load) produces **zero** patches. Documented in code on `ServiceState.retries_state`.
2. **Asymmetric Interval** — paper uses one `Interval` for both directions; YAML splits it into `disable_windows` / `re_enable_windows` (workshop extension used by Scenario 5).
3. **Rejection metric from Locust CSVs**, not Istio Prometheus — same signal class as the paper's rejection-based controller; chosen because `metric_collector.py` already writes these files on our stack.
```

with:

```markdown
## Deviations from the paper pseudocode

1. **Initial state `ON`** — Algorithm 1 initializes `Retries ← OFF`. We start `ON` so the controller matches the default VirtualService (`attempts: 3`) and Scenario 1 (healthy load) produces **zero** patches. Documented in code on `ServiceState.retries_state`.
2. **Rejection metric from Locust CSVs**, not Istio Prometheus — same signal class as the paper's rejection-based controller; chosen because `metric_collector.py` already writes these files on our stack.

As of 2026-09-10, the `Interval` parameter is symmetric (single `interval_samples` value for both ON and OFF transitions, `sample_interval_seconds=1`) — a literal match to Algorithm 1. The previous `disable_windows`/`re_enable_windows` asymmetric split and `window_duration_seconds`-based averaging (a workshop extension) were removed; Scenario 5 now sweeps the single `interval_samples` value (10/20/30/60) symmetrically.
```

- [ ] **Step 6: Commit**

```bash
git add "Guides and Info/RETRYGUARD-IMPLEMENTATION.md"
git commit -m "docs: RETRYGUARD-IMPLEMENTATION.md reflects symmetric single-Interval design"
```

---

### Task 9: Update `experiments/README.md` config schema table

**Files:**
- Modify: `experiments/README.md:110-114`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Replace the schema rows**

Replace:

```markdown
| `retryguard.enabled` | bool | Whether to start RetryGuard |
| `retryguard.rejection_threshold` | float | Fraction (0–1) to trigger disable counter |
| `retryguard.window_duration_seconds` | int | Length of one observation window |
| `retryguard.disable_windows` | int | Consecutive windows above threshold → disable |
| `retryguard.re_enable_windows` | int | Consecutive windows below threshold → re-enable |
```

with:

```markdown
| `retryguard.enabled` | bool | Whether to start RetryGuard |
| `retryguard.rejection_threshold` | float | Fraction (0–1) to trigger disable counter |
| `retryguard.sample_interval_seconds` | int | Loop cadence — seconds between raw samples (paper default: 1) |
| `retryguard.interval_samples` | int | Paper's `Interval` — consecutive samples required to transition, applied symmetrically to both ON and OFF (paper default: 30, i.e. 30s at a 1s sample interval) |
```

- [ ] **Step 2: Commit**

```bash
git add experiments/README.md
git commit -m "docs: README.md config schema reflects sample_interval_seconds + interval_samples"
```

---

### Task 10: Update `PHASE5-EXPERIMENTS-GUIDE.md`

**Files:**
- Modify: `Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md` (Scenario 5 section ~lines 78-95, annotated YAML snippet ~lines 263-269, config-variable table ~line 107)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update the Scenario 5 section**

Replace:

```markdown
- **Load:** Same as Scenario 6 (forced recovery: 300s peak, then ~25% for 600s). **Not** Scenario 2's flat hold.
- **RetryGuard:** Always on. Only `re_enable_windows` changes across runs.
- **Comparison baseline:** Scenario 6 baseline (`scenario_6_recovery_baseline.yaml`). Do not use Scenario 2 baseline — different offered load.

| Config | `re_enable_windows` | Effective wait | Risk |
|--------|--------------------|-----------------|----|
| `interval_10s` | 1 | 30s | Oscillation — retries re-enabled before bottleneck clears |
```

with:

```markdown
- **Load:** Same as Scenario 6 (forced recovery: 300s peak, then ~25% for 600s). **Not** Scenario 2's flat hold.
- **RetryGuard:** Always on. Only `interval_samples` changes across runs (applied symmetrically to both disable and re-enable — paper Algorithm 1 uses one `Interval` for both).
- **Comparison baseline:** Scenario 6 baseline (`scenario_6_recovery_baseline.yaml`). Do not use Scenario 2 baseline — different offered load.

| Config | `interval_samples` | Effective interval (both directions) | Risk |
|--------|--------------------|----------------------------------------|----|
| `interval_10s` | 10 | 10s | Oscillation — retries disabled/re-enabled before bottleneck clears |
```

(Keep the remaining three table rows — `interval_20s`/`interval_30s`/`interval_60s` — same shape, updating each `Effective wait` column to the plain seconds value: 20s/30s/60s, and updating each row's "risk" text to mention both directions rather than only re-enable.)

- [ ] **Step 2: Update the config-variable table**

Replace:

```markdown
| **RetryGuard re-enable interval** | `retryguard.re_enable_windows` in config | S5 only (S6 RetryGuard uses paper default = 3) |
```

with:

```markdown
| **RetryGuard interval** | `retryguard.interval_samples` in config | S5 only (S6 RetryGuard uses paper default = 30) |
```

- [ ] **Step 3: Update the Scenario 6 section**

Replace:

```markdown
- **Goal:** Elicit `OFF→ON` by reducing offered load after disable has fired. Canonical baseline for Scenario 5. `scenario_6_recovery_retryguard.yaml` uses paper-default `re_enable_windows: 3`.
```

with:

```markdown
- **Goal:** Elicit `OFF→ON` by reducing offered load after disable has fired. Canonical baseline for Scenario 5. `scenario_6_recovery_retryguard.yaml` uses paper-default `interval_samples: 30`.
```

- [ ] **Step 4: Update the annotated example YAML snippet**

Replace:

```yaml
retryguard:
  enabled: false
  rejection_threshold: 0.20  # >20% triggers disable counter
  window_duration_seconds: 30
  disable_windows: 2         # consecutive windows above threshold → disable
  re_enable_windows: 3       # consecutive windows below threshold → re-enable
  retry_attempts_on: 3       # Istio VirtualService retries.attempts when enabled
  retry_attempts_off: 0      # Istio VirtualService retries.attempts when disabled
```

with:

```yaml
retryguard:
  enabled: false
  rejection_threshold: 0.20     # >20% triggers disable counter
  sample_interval_seconds: 1    # loop cadence — 1 raw sample/sec (paper Algorithm 1)
  interval_samples: 30          # paper's Interval — symmetric ON/OFF, 30 samples = 30s
  retry_attempts_on: 3          # Istio VirtualService retries.attempts when enabled
  retry_attempts_off: 0         # Istio VirtualService retries.attempts when disabled
```

- [ ] **Step 5: Commit**

```bash
git add "Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md"
git commit -m "docs: PHASE5-EXPERIMENTS-GUIDE.md reflects symmetric single-Interval design"
```

---

### Task 11: Update `SCENARIOS-GUIDE.md`

**Files:**
- Modify: `Guides and Info/SCENARIOS-GUIDE.md` (Scenario 5 "Intervals to test" table, "How to run" section, Scenario 6 cross-reference)

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update the "How to run" prose and commands**

Replace:

```markdown
The `re_enable_windows` parameter is already set correctly in each config — no manual script editing needed. There is no separate `scenario_5_baseline.yaml`; use **Scenario 6 baseline** as the comparison (same 900s load-drop). Do not compare S5 to Scenario 2 — S2 is a different offered-load shape.

```powershell
# 10s effective wait (re_enable_windows: 1) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_10s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_10s_run1 experiments/results/

# 20s effective wait (re_enable_windows: 2) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_20s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_20s_run1 experiments/results/

# 30s effective wait (re_enable_windows: 3) — paper default — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_30s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_30s_run1 experiments/results/

# 60s effective wait (re_enable_windows: 6) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_60s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_60s_run1 experiments/results/
```
```

with:

```markdown
The `interval_samples` parameter is already set correctly in each config (applied symmetrically to both disable and re-enable) — no manual script editing needed. There is no separate `scenario_5_baseline.yaml`; use **Scenario 6 baseline** as the comparison (same 900s load-drop). Do not compare S5 to Scenario 2 — S2 is a different offered-load shape.

```powershell
# 10s interval, both directions (interval_samples: 10) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_10s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_10s_run1 experiments/results/

# 20s interval, both directions (interval_samples: 20) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_20s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_20s_run1 experiments/results/

# 30s interval, both directions (interval_samples: 30) — paper default — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_30s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_30s_run1 experiments/results/

# 60s interval, both directions (interval_samples: 60) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_60s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_60s_run1 experiments/results/
```
```

- [ ] **Step 2: Update the Scenario 6 cross-reference**

Replace:

```markdown
`scenario_6_recovery_retryguard.yaml` uses `re_enable_windows: 3` — the same experiment as `scenario_5_interval_30s.yaml`. Keep both: S6 is the canonical pair; S5-30s is the default point on the interval sweep.
```

with:

```markdown
`scenario_6_recovery_retryguard.yaml` uses `interval_samples: 30` — the same experiment as `scenario_5_interval_30s.yaml`. Keep both: S6 is the canonical pair; S5-30s is the default point on the interval sweep.
```

- [ ] **Step 3: Update the remaining `re_enable_windows` mentions in the Scenario 6 section**

Replace:

```markdown
Scenario 6 keeps the same peak for 5 minutes (enough to trigger disable), then **drops Locust to ~25% of peak** for 10 minutes so rejection can fall under 20% and `re_enable_windows` can accumulate.
```

with:

```markdown
Scenario 6 keeps the same peak for 5 minutes (enough to trigger disable), then **drops Locust to ~25% of peak** for 10 minutes so rejection can fall under 20% and `interval_samples` consecutive low samples can accumulate.
```

- [ ] **Step 4: Commit**

```bash
git add "Guides and Info/SCENARIOS-GUIDE.md"
git commit -m "docs: SCENARIOS-GUIDE.md reflects symmetric single-Interval design"
```

---

### Task 12: Update `METRICS-COLLECTION-GUIDE.md` example log line

**Files:**
- Modify: `Guides and Info/METRICS-COLLECTION-GUIDE.md:145-147`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update the example log line**

Replace:

```
2026-08-04T13:20:00Z  START  threshold=0.20 window=30s disable_windows=2 re_enable_windows=3 services=['cartservice', 'checkoutservice', 'productcatalogservice']
2026-08-04T13:20:30Z  OBSERVE  cartservice         rejection=0.0100  low=1 high=0  state=ON
```

with:

```
2026-08-04T13:20:00Z  START  threshold=0.20 sample_interval=1s interval_samples=30 (30s) services=['cartservice', 'checkoutservice', 'productcatalogservice']
2026-08-04T13:20:01Z  OBSERVE  cartservice         rejection=0.0100  low=1 high=0  state=ON
```

- [ ] **Step 2: Commit**

```bash
git add "Guides and Info/METRICS-COLLECTION-GUIDE.md"
git commit -m "docs: METRICS-COLLECTION-GUIDE.md example log line reflects new controller"
```

---

### Task 13: Update `AGENTS.md` §4 status + final verification sweep

**Files:**
- Modify: `AGENTS.md` (§4 "Current status" — insert a new dated bullet)

**Interfaces:** none (documentation only), but this task is required by the always-applied workspace rule: "When you complete meaningful work..., update §4 ('Current status') so the next agent doesn't have to re-derive it."

- [ ] **Step 1: Add a new bullet to §4 "✅ Done"**

Insert (near the end of the "✅ Done" list, after the "TopFull quota↔K8s sync" bullet):

```markdown
- **RetryGuard controller made paper-exact (2026-09-10)** — `experiments/retryguard.py`'s Algorithm 1 implementation now matches the paper literally: `sample_interval_seconds` (=1, raw 1s samples, no averaging) + a single symmetric `interval_samples` (paper default 30) applied to both the disable and re-enable transitions, replacing the old `window_duration_seconds`/`disable_windows`/`re_enable_windows` asymmetric-and-averaged workshop extension. Updated everywhere the old params appeared: `run_scenario.py`, all 16 scenario YAMLs, `RETRYGUARD-IMPLEMENTATION.md`, `experiments/README.md`, `PHASE5-EXPERIMENTS-GUIDE.md`, `SCENARIOS-GUIDE.md`, `METRICS-COLLECTION-GUIDE.md`. New unit tests in `experiments/test_retryguard.py` cover the state machine and metric reader. **`campaign_48/` predates this change and does not reflect it** — per explicit instruction, it is left as-is (out of date, to be superseded by a new campaign run later); do not use it to validate the new controller's behavior.
```

- [ ] **Step 2: Final repo-wide sweep for leftover old param names**

Run (PowerShell):

```powershell
Select-String -Path "experiments\*.py","experiments\configs\*.yaml","Guides and Info\*.md","experiments\README.md","AGENTS.md" -Pattern "window_duration_seconds|disable_windows|re_enable_windows"
```

Expected: **no matches** except inside `Guides and Info/PHASE5-PHASE6-RUNLIST.md`, `Guides and Info/PHASE7-DATA-GAPS.md`, and `Guides and Info/EXPERIMENT-READINESS-WORKPLAN.md` (explicitly out of scope per Global Constraints — these describe already-completed historical runs under the old scheme and must not be rewritten) and inside `experiments/results/**/run_manifest.json` (historical run manifests, also out of scope).

- [ ] **Step 3: Run the full test suite one last time**

Run:

```powershell
python -m unittest experiments.test_retryguard -v
python -m unittest experiments.test_run_scenario -v
```

Expected: both suites fully `PASS`.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md records the RetryGuard paper-fidelity redesign"
```

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** every old-param call site found via repo-wide grep (`experiments/retryguard.py`, `experiments/run_scenario.py`, `experiments/test_run_scenario.py`, all 16 configs, `RETRYGUARD-IMPLEMENTATION.md`, `experiments/README.md`, `PHASE5-EXPERIMENTS-GUIDE.md`, `SCENARIOS-GUIDE.md`, `METRICS-COLLECTION-GUIDE.md`) has a corresponding task. Historical docs (`PHASE5-PHASE6-RUNLIST.md`, `PHASE7-DATA-GAPS.md`, `EXPERIMENT-READINESS-WORKPLAN.md`) and `experiments/results/**` are explicitly excluded per Global Constraints.
- **Placeholder scan:** no TBD/TODO/"handle appropriately" — every step shows the literal before/after text or code.
- **Type consistency:** `apply_algorithm1(state, rejection, threshold, interval)` and `read_rejection_rate(csv_path)` / `service_rejection_rate(service, endpoints, record_path)` signatures are introduced once (Tasks 1/3) and reused identically in every later task (Tasks 2/4/5) and by the test file.
