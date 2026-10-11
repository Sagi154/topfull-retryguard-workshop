# S2 RetryGuard tuning + S3/S4A/S4B topology holds

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `climb_interval_seconds` RetryGuard override, then run 14 holds: 4 on the locked S2 mix with a new RetryGuard parameter set (`reenable_rejection=0.25`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`), and 10 on the locked S1 mix across Scenario 3 (checkout 300 m) and Scenario 4A/4B topology variants, all RetryGuard-on (TopFull off, then TopFull on), using that same tuned parameter set.

**Architecture:** `experiments/retryguard.py`'s `EdgeController` currently hard-codes the 1→2 and 2→3 climb quiet time at `CLIMB_INTERVAL_SECONDS = 15`, independent of `interval_samples`. Add an optional per-instance override (`climb_interval_seconds`), sourced from a new optional YAML key under `retryguard:`, forwarded by `run_scenario.py` exactly like the existing `climb_rpr_1_to_2`/`climb_rpr_2_to_3` keys. Every existing YAML that omits the key keeps the 15 s default — no behavior change for historical runs. Then generate 14 scenario YAMLs from the existing locked templates (same pattern as `experiments/make_study_configs.py`), and run them one at a time on the live cluster with the 120 s cool-off and leftover-writer check in [AGENTS.md](../../../AGENTS.md) §6. Checkout and recommendations stay up. The YAMLs omit `restart_before_hold`.

**Tech Stack:** `experiments/retryguard.py`, `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/test_retryguard.py`, `experiments/test_run_scenario.py`, PowerShell + `ssh`/`gcloud` for the live-cluster steps.

## Global Constraints

- Stay on branch `study-reenable-rejection-s3-s4`. Do not branch from `main`.
- SSH only via host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`); user `idozacharia`; project `project-76deda76-55f1-42d2-abb`; zone `us-central1-a`. Do not start `networks-workshop`.
- Locked S2 mix: `getproduct=275, postcheckout=90, getcart=100, postcart=90, emptycart=5`, `spawn_rate` 50, Paper-C1.
- Locked S1 mix: `getproduct=175, postcheckout=30, getcart=70, postcart=90, emptycart=5`, `spawn_rate` 50, Paper-C1.
- New tuned RetryGuard parameter set, used on **every** hold in this plan: `retry_metric=edge_rpr`, `rejection_threshold=0.20`, `sample_interval_seconds=1`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`.
- Every hold is 600 s. Omit `restart_before_hold`. Checkout and recommendations stay up across the cool-off. The key remains opt-in; these 14 YAMLs do not set it.
- Cluster stays pinned at Paper-C1 shape for the whole study: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `proxyCPU=90m` with `proxyCPULimit` unset. Pin once before hold 1, restore once after hold 14.
- Cool-off is **120 s**. The clock starts when `run_scenario.py` exits. Pulling the folder and the gate check are fine during the wait. After 120 s, do the leftover-writer check, then launch. If no `run_scenario.py` has just exited, hold 1 starts after that check with no extra idle wait. Leave the three VMs running through Task 8. Task 9 stops them and confirms `TERMINATED`.
- Read [STATUS.md](../../../STATUS.md) before hold 1. These YAMLs use their own `study4_*` `log_folder` values and `run_number: 1`. Do not bump the locked scenario slots under "Next free slots". After the study, append one Done bullet there, leave Next free slots alone unless a locked YAML's `run_number` actually changed, and replace the three Latest lines in [AGENTS.md](../../../AGENTS.md) §4. Do not append a fourth Latest line.
- One hold at a time. Never reuse a `log_folder`. A failed gate keeps its folder and is replayed once with a `_r2` suffix on both the file name and `log_folder`.
- Do not touch `experiments/results/campaign_48/` folders from earlier studies (S3 `run8`/`run7`/`run9`, S1 `run22`/`run24`, S2 locked-mix folders, `august_38/`, etc.).

---

## Hold order

Results land in `experiments/results/campaign_48/<scenario_subfolder>/<log_folder>/` (`S2_sustained_overload/`, `S3_targeted_bottleneck/`, `S4A_topology_position_A/`, `S4B_topology_position_B/`).

| # | File | Scenario | Mix change | CPU change | TopFull | `log_folder` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `01_s2_tune_rgtf0_rep1.yaml` | S2 | locked S2 mix | none (Paper-C1) | off | `study4_s2_tune_rgtf0_rep1` |
| 2 | `02_s2_tune_rgtf1_rep1.yaml` | S2 | locked S2 mix | none | on | `study4_s2_tune_rgtf1_rep1` |
| 3 | `03_s2_tune_rgtf0_rep2.yaml` | S2 | locked S2 mix | none | off | `study4_s2_tune_rgtf0_rep2` |
| 4 | `04_s2_tune_rgtf1_rep2.yaml` | S2 | locked S2 mix | none | on | `study4_s2_tune_rgtf1_rep2` |
| 5 | `05_s3_ck300_rgtf0.yaml` | S3 | locked S1 mix | checkoutservice 300 m | off | `study4_s3_ck300_rgtf0` |
| 6 | `06_s3_ck300_rgtf1.yaml` | S3 | locked S1 mix | checkoutservice 300 m | on | `study4_s3_ck300_rgtf1` |
| 7 | `07_s4a_pc400_u140_rgtf0.yaml` | S4A | postcart 90→140 | productcatalogservice 400 m | off | `study4_s4a_pc400_u140_rgtf0` |
| 8 | `08_s4a_pc400_u140_rgtf1.yaml` | S4A | postcart 90→140 | productcatalogservice 400 m | on | `study4_s4a_pc400_u140_rgtf1` |
| 9 | `09_s4a_pc400_u190_rgtf0.yaml` | S4A | postcart 90→190 | productcatalogservice 400 m | off | `study4_s4a_pc400_u190_rgtf0` |
| 10 | `10_s4a_pc400_u190_rgtf1.yaml` | S4A | postcart 90→190 | productcatalogservice 400 m | on | `study4_s4a_pc400_u190_rgtf1` |
| 11 | `11_s4b_em50_rgtf0.yaml` | S4B | locked S1 mix | emailservice 50 m | off | `study4_s4b_em50_rgtf0` |
| 12 | `12_s4b_em50_rgtf1.yaml` | S4B | locked S1 mix | emailservice 50 m | on | `study4_s4b_em50_rgtf1` |
| 13 | `13_s4b_em60_rgtf0.yaml` | S4B | locked S1 mix | emailservice 60 m | off | `study4_s4b_em60_rgtf0` |
| 14 | `14_s4b_em60_rgtf1.yaml` | S4B | locked S1 mix | emailservice 60 m | on | `study4_s4b_em60_rgtf1` |

All 14 have `retryguard.enabled: true` and the tuned parameter set from Global Constraints. "TopFull off/on" is `topfull_rl.enabled`.

---

### Task 1: `climb_interval_seconds` override in `retryguard.py`

**Files:**
- Modify: `experiments/retryguard.py:685-696` (new function), `experiments/retryguard.py:756-780` (`EdgeController.__init__`), `experiments/retryguard.py:810-827` (`_ramp_tick`), `experiments/retryguard.py:979-998` (`run_edge_rpr` construction + START log)
- Test: `experiments/test_retryguard.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `climb_interval_from_params(params: dict) -> Optional[int]`; `EdgeController.__init__(..., climb_interval_seconds=None)` storing `self.climb_interval_seconds: int`.

- [ ] **Step 1: Write the failing tests**

Open `experiments/test_retryguard.py`. Find `class TestAttemptRamp` and its existing `test_climb_interval_per_step` method (tests the standalone `climb_interval_s` function directly — leave that test untouched). Immediately after that method, insert three new test methods:

```python
    def test_climb_interval_seconds_defaults_to_the_constant(self):
        ctrl = retryguard.EdgeController((self.EDGE,), 0.5, 0.2, 3)
        self.assertEqual(ctrl.climb_interval_seconds, retryguard.CLIMB_INTERVAL_SECONDS)

    def test_climb_interval_seconds_override_shortens_the_climb(self):
        ctrl = retryguard.EdgeController(
            (self.EDGE,), 0.5, 0.2, 3, climb_interval_seconds=2,
        )
        self.assertEqual(ctrl.climb_interval_seconds, 2)
        self.to_attempts(ctrl, 1)
        # 2 quiet rows is not yet 2 s elapsed from the opening row: holds at 1.
        self.assertEqual(self.feed(ctrl, 2, 0.10), [])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 1)
        # A third quiet row reaches 2 s elapsed and climbs.
        climb = self.feed(ctrl, 1, 0.10)
        self.assertEqual(climb[0].desired_attempts, {"frontend": 2})

    def test_climb_interval_from_params(self):
        self.assertIsNone(retryguard.climb_interval_from_params({}))
        self.assertEqual(
            retryguard.climb_interval_from_params({"climb_interval_seconds": 10}), 10,
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
cd experiments
python -m unittest test_retryguard -v 2>&1 | Select-String -Pattern "climb_interval_seconds|FAILED|ERROR"
```

Expected: `AttributeError: 'EdgeController' object has no attribute 'climb_interval_seconds'` on the first two new tests, and `AttributeError: module 'retryguard' has no attribute 'climb_interval_from_params'` on the third.

- [ ] **Step 3: Add `climb_interval_from_params`**

In `experiments/retryguard.py`, find this block (currently lines 685-696):

```python
def climb_interval_s(attempts: int, reenable_interval: int) -> int:
    """Seconds of quiet needed to leave `attempts` for the next step up."""
    if int(attempts) <= 0:
        return int(reenable_interval)
    return CLIMB_INTERVAL_SECONDS
```

Leave it exactly as-is (existing tests call it directly) and add this new function immediately after it, before `def climb_rpr_limit(...)`:

```python
def climb_interval_from_params(params: dict) -> Optional[int]:
    """
    YAML override for the 1->2 and 2->3 climb quiet time, in seconds. None
    means the caller should keep CLIMB_INTERVAL_SECONDS (15 s), the
    long-standing default — a YAML that omits the key is unaffected.
    """
    value = params.get("climb_interval_seconds")
    return int(value) if value is not None else None
```

- [ ] **Step 4: Add the constructor parameter**

Find `EdgeController.__init__` (currently lines 756-780):

```python
    def __init__(
        self, edges, rpr_threshold, rejection_threshold, interval, attempts_on=3,
        reenable_rejection_threshold=REENABLE_REJECTION_THRESHOLD,
        climb_rpr_1_to_2=None,
        climb_rpr_2_to_3=None,
    ):
        self.rpr_threshold = rpr_threshold
        self.rejection_threshold = rejection_threshold
        self.reenable_rejection_threshold = reenable_rejection_threshold
        self.interval = interval
        self.attempts_on = int(attempts_on)
        self.climb_rpr_1_to_2 = (
            climb_rpr_limit(1, self.attempts_on, rpr_threshold)
            if climb_rpr_1_to_2 is None else float(climb_rpr_1_to_2)
        )
        self.climb_rpr_2_to_3 = (
            climb_rpr_limit(2, self.attempts_on, rpr_threshold)
            if climb_rpr_2_to_3 is None else float(climb_rpr_2_to_3)
        )
        self.edge_state = {
            e: ServiceState(attempts=self.attempts_on) for e in edges
        }
```

Replace it with:

```python
    def __init__(
        self, edges, rpr_threshold, rejection_threshold, interval, attempts_on=3,
        reenable_rejection_threshold=REENABLE_REJECTION_THRESHOLD,
        climb_rpr_1_to_2=None,
        climb_rpr_2_to_3=None,
        climb_interval_seconds=None,
    ):
        self.rpr_threshold = rpr_threshold
        self.rejection_threshold = rejection_threshold
        self.reenable_rejection_threshold = reenable_rejection_threshold
        self.interval = interval
        self.attempts_on = int(attempts_on)
        self.climb_rpr_1_to_2 = (
            climb_rpr_limit(1, self.attempts_on, rpr_threshold)
            if climb_rpr_1_to_2 is None else float(climb_rpr_1_to_2)
        )
        self.climb_rpr_2_to_3 = (
            climb_rpr_limit(2, self.attempts_on, rpr_threshold)
            if climb_rpr_2_to_3 is None else float(climb_rpr_2_to_3)
        )
        self.climb_interval_seconds = (
            CLIMB_INTERVAL_SECONDS
            if climb_interval_seconds is None else int(climb_interval_seconds)
        )
        self.edge_state = {
            e: ServiceState(attempts=self.attempts_on) for e in edges
        }
```

- [ ] **Step 5: Use the override in `_ramp_tick`**

Find (currently lines 810-827):

```python
    def _ramp_tick(
        self, state: ServiceState, value: float, timestamp: str
    ) -> Optional[str]:
        """One tick at 1..attempts_on-1. Returns 'shed', 'climb', or None."""
        limit = self._climb_limit(state.attempts)
        if value <= limit:
            _open_low(state, timestamp)
        elif value > self.rpr_threshold:
            _open_high(state, timestamp)
        else:
            # Above the climb bar and at or under the shed bar: hold.
            _clear_streaks(state)
        if streak_met(state.high_since, timestamp, self.interval):
            return "shed"
        climb_s = climb_interval_s(state.attempts, self.interval)
        if streak_met(state.low_since, timestamp, climb_s):
            return "climb"
        return None
```

Replace the `climb_s = ...` line only:

```python
    def _ramp_tick(
        self, state: ServiceState, value: float, timestamp: str
    ) -> Optional[str]:
        """One tick at 1..attempts_on-1. Returns 'shed', 'climb', or None."""
        limit = self._climb_limit(state.attempts)
        if value <= limit:
            _open_low(state, timestamp)
        elif value > self.rpr_threshold:
            _open_high(state, timestamp)
        else:
            # Above the climb bar and at or under the shed bar: hold.
            _clear_streaks(state)
        if streak_met(state.high_since, timestamp, self.interval):
            return "shed"
        climb_s = self.climb_interval_seconds
        if streak_met(state.low_since, timestamp, climb_s):
            return "climb"
        return None
```

(`_ramp_tick` is only ever called with `state.attempts >= 1`, so the `attempts <= 0` branch of the standalone `climb_interval_s` function was already unreachable from this call site — this change does not alter the 0→1 step, which stays on `self.interval`.)

- [ ] **Step 6: Wire the override into `run_edge_rpr`**

Find (currently lines 979-998):

```python
    climb_1, climb_2 = climb_limits_from_params(params)
    ctrl = EdgeController(
        CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval, attempts_on,
        reenable_rejection_threshold=reenable_threshold_from_params(params),
        climb_rpr_1_to_2=climb_1,
        climb_rpr_2_to_3=climb_2,
    )
    inbound = InboundCsvTailer(record_path / INBOUND_CSV_NAME)
    edges = EdgesCsvTailer(record_path / EDGES_CSV_NAME)
    prev_in: Dict[str, Optional[InboundSnapshot]] = {s: None for s in CONTROLLED_SERVICES}
    prev_edge: Dict[tuple, Optional[EdgeSnapshot]] = {e: None for e in CONTROLLED_EDGES}
    log.info(
        "%s  START  metric=edge_rpr rpr_threshold=%.2f rejection_threshold=%.2f "
        "reenable_rejection=%.2f climb_rpr_1_to_2=%.2f climb_rpr_2_to_3=%.2f "
        "sample_interval=%ss interval_samples=%ds edges=%d attempts_on=%d",
        utc_now(), rpr_threshold, rejection_threshold,
        ctrl.reenable_rejection_threshold,
        ctrl.climb_rpr_1_to_2, ctrl.climb_rpr_2_to_3,
        sample_interval, interval, len(CONTROLLED_EDGES), attempts_on,
    )
```

Replace it with:

```python
    climb_1, climb_2 = climb_limits_from_params(params)
    climb_interval = climb_interval_from_params(params)
    ctrl = EdgeController(
        CONTROLLED_EDGES, rpr_threshold, rejection_threshold, interval, attempts_on,
        reenable_rejection_threshold=reenable_threshold_from_params(params),
        climb_rpr_1_to_2=climb_1,
        climb_rpr_2_to_3=climb_2,
        climb_interval_seconds=climb_interval,
    )
    inbound = InboundCsvTailer(record_path / INBOUND_CSV_NAME)
    edges = EdgesCsvTailer(record_path / EDGES_CSV_NAME)
    prev_in: Dict[str, Optional[InboundSnapshot]] = {s: None for s in CONTROLLED_SERVICES}
    prev_edge: Dict[tuple, Optional[EdgeSnapshot]] = {e: None for e in CONTROLLED_EDGES}
    log.info(
        "%s  START  metric=edge_rpr rpr_threshold=%.2f rejection_threshold=%.2f "
        "reenable_rejection=%.2f climb_rpr_1_to_2=%.2f climb_rpr_2_to_3=%.2f "
        "climb_interval_seconds=%ds sample_interval=%ss interval_samples=%ds "
        "edges=%d attempts_on=%d",
        utc_now(), rpr_threshold, rejection_threshold,
        ctrl.reenable_rejection_threshold,
        ctrl.climb_rpr_1_to_2, ctrl.climb_rpr_2_to_3,
        ctrl.climb_interval_seconds,
        sample_interval, interval, len(CONTROLLED_EDGES), attempts_on,
    )
```

- [ ] **Step 7: Run the tests to verify they pass**

```powershell
python -m unittest test_retryguard -v 2>&1 | Select-String -Pattern "climb_interval|FAILED|ERROR|OK"
```

Expected: the three new tests pass, and the full suite still reports `OK` (run `python -m unittest test_retryguard -v` without the filter to confirm no other test broke).

- [ ] **Step 8: Commit**

```powershell
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat: add optional climb_interval_seconds override to RetryGuard edge mode"
```

---

### Task 2: Forward `climb_interval_seconds` from `run_scenario.py`

**Files:**
- Modify: `experiments/run_scenario.py:707-754` (`start_retryguard`)
- Test: `experiments/test_run_scenario.py:306-341` (`TestStartRetryGuardWiring`)

**Interfaces:**
- Consumes: `cfg["retryguard"].get("climb_interval_seconds")` (optional int, new YAML key).
- Produces: `params["climb_interval_seconds"]` present only when the YAML key is set, in the JSON uploaded to master.

- [ ] **Step 1: Fix the pre-existing broken fixture and write the failing tests**

`TestStartRetryGuardWiring._cfg()` is currently missing a top-level `"retries"` key, which makes `test_start_deploys_retryguard_py` fail today with `KeyError: 'attempts_on'` (confirmed by running the suite before this change). Open `experiments/test_run_scenario.py`, find `class TestStartRetryGuardWiring` (currently lines 306-323):

```python
class TestStartRetryGuardWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "retryguard_script": "/home/idozacharia/experiments/retryguard.py",
            },
            "retryguard": {
                "enabled": enabled,
                "rejection_threshold": 0.20,
                "sample_interval_seconds": 1,
                "interval_samples": 30,
                "retry_attempts_on": 3,
                "retry_attempts_off": 0,
            },
        }
```

Replace it with (adds the missing `"retries"` block; keeps the unused `retryguard.retry_attempts_on`/`retry_attempts_off` keys as-is so no other test that reads this fixture breaks):

```python
class TestStartRetryGuardWiring(unittest.TestCase):
    def _cfg(self, enabled=True):
        return {
            "infra": {
                "master_ssh_host": "topfull-master",
                "venv_activate": "/home/idozacharia/TopFull/venv/bin/activate",
                "retryguard_script": "/home/idozacharia/experiments/retryguard.py",
            },
            "retries": {
                "attempts_on": 3,
                "attempts_off": 0,
                "per_try_timeout_ms": 500,
            },
            "retryguard": {
                "enabled": enabled,
                "rejection_threshold": 0.20,
                "sample_interval_seconds": 1,
                "interval_samples": 30,
                "retry_attempts_on": 3,
                "retry_attempts_off": 0,
            },
        }
```

Then, immediately after `test_start_noop_when_disabled` (currently ends at line 341, right before `class TestEnvoyRetryCollectorWiring`), add two new test methods:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_climb_interval_seconds_is_forwarded_when_present(
        self, mock_deploy, mock_ssh, mock_json, mock_script, mock_wait,
    ):
        cfg = self._cfg(enabled=True)
        cfg["retryguard"]["climb_interval_seconds"] = 10
        run_scenario.start_retryguard(cfg)
        params = mock_json.call_args[0][2]
        self.assertEqual(params["climb_interval_seconds"], 10)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.write_remote_json")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario.deploy_repo_script")
    def test_climb_interval_seconds_absent_when_not_set(
        self, mock_deploy, mock_ssh, mock_json, mock_script, mock_wait,
    ):
        run_scenario.start_retryguard(self._cfg(enabled=True))
        params = mock_json.call_args[0][2]
        self.assertNotIn("climb_interval_seconds", params)
```

- [ ] **Step 2: Run the tests to verify the new ones fail (and the old fixture bug is now fixed)**

```powershell
python -m unittest test_run_scenario -k TestStartRetryGuardWiring -v
```

Expected: `test_start_deploys_retryguard_py` and `test_start_noop_when_disabled` now pass (fixture fix). `test_climb_interval_seconds_is_forwarded_when_present` fails with `AssertionError: 'climb_interval_seconds' not found in {...}` (the key is not in `params` yet). `test_climb_interval_seconds_absent_when_not_set` already passes (nothing to forward yet) — that is expected; its job is to stay green after Step 3.

- [ ] **Step 3: Forward the key in `start_retryguard`**

In `experiments/run_scenario.py`, find (currently lines 722-744):

```python
    # Upload RetryGuard runtime parameters as JSON
    retries_cfg = cfg.get("retries", {})
    attempts_on = int(retries_cfg["attempts_on"])
    rpr_threshold = float(rg_cfg.get("retries_threshold", 0.5))
    params = {
        "rejection_threshold":     rg_cfg["rejection_threshold"],
        "sample_interval_seconds": rg_cfg["sample_interval_seconds"],
        "interval_samples":        rg_cfg["interval_samples"],
        "retry_attempts_on":       attempts_on,
        "retry_attempts_off":      retries_cfg["attempts_off"],
        "per_try_timeout_ms":      retries_cfg["per_try_timeout_ms"],
        "retry_metric":            rg_cfg.get("retry_metric", "rejection"),
        "retries_threshold":       rpr_threshold,
        "reenable_rejection":      rg_cfg.get("reenable_rejection", 0.10),
        "climb_rpr_1_to_2":        float(rg_cfg.get(
            "climb_rpr_1_to_2", round(rpr_threshold * 1 / attempts_on, 2)
        )),
        "climb_rpr_2_to_3":        float(rg_cfg.get(
            "climb_rpr_2_to_3", round(rpr_threshold * 2 / attempts_on, 2)
        )),
    }
    write_remote_json(master, "/tmp/retryguard_params.json", params)
```

Replace it with:

```python
    # Upload RetryGuard runtime parameters as JSON
    retries_cfg = cfg.get("retries", {})
    attempts_on = int(retries_cfg["attempts_on"])
    rpr_threshold = float(rg_cfg.get("retries_threshold", 0.5))
    params = {
        "rejection_threshold":     rg_cfg["rejection_threshold"],
        "sample_interval_seconds": rg_cfg["sample_interval_seconds"],
        "interval_samples":        rg_cfg["interval_samples"],
        "retry_attempts_on":       attempts_on,
        "retry_attempts_off":      retries_cfg["attempts_off"],
        "per_try_timeout_ms":      retries_cfg["per_try_timeout_ms"],
        "retry_metric":            rg_cfg.get("retry_metric", "rejection"),
        "retries_threshold":       rpr_threshold,
        "reenable_rejection":      rg_cfg.get("reenable_rejection", 0.10),
        "climb_rpr_1_to_2":        float(rg_cfg.get(
            "climb_rpr_1_to_2", round(rpr_threshold * 1 / attempts_on, 2)
        )),
        "climb_rpr_2_to_3":        float(rg_cfg.get(
            "climb_rpr_2_to_3", round(rpr_threshold * 2 / attempts_on, 2)
        )),
    }
    if "climb_interval_seconds" in rg_cfg:
        params["climb_interval_seconds"] = int(rg_cfg["climb_interval_seconds"])
    write_remote_json(master, "/tmp/retryguard_params.json", params)
```

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python -m unittest test_run_scenario -k TestStartRetryGuardWiring -v
```

Expected: all four tests pass. Then run the full file to confirm nothing else broke:

```powershell
python -m unittest test_run_scenario -v 2>&1 | Select-String -Pattern "FAILED|ERROR|^OK|Ran "
```

- [ ] **Step 5: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: forward climb_interval_seconds to RetryGuard, fix broken wiring-test fixture"
```

---

### Task 3: Document the new key

**Files:**
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md`

- [ ] **Step 1: Add a paragraph after the climb-bar table**

Find this sentence (near the end of the "Edge mode" section, right after the step table):

```
The whole ramp from 0 to 3 now takes at least 60 s (was 90 s). The 15 s value is a constant in `retryguard.py`, not a YAML key. The two rpr bars are YAML keys.
```

Replace it with:

```
The whole ramp from 0 to 3 now takes at least 60 s (was 90 s). The 15 s value is `CLIMB_INTERVAL_SECONDS` in `retryguard.py`. As of 2026-10-11 it has an optional YAML override, `climb_interval_seconds` under `retryguard:`. A scenario that omits the key still climbs at 15 s. The two rpr bars are YAML keys, same as before.
```

- [ ] **Step 2: Commit**

```powershell
git add "Guides and Info/RETRYGUARD-IMPLEMENTATION.md"
git commit -m "docs: document the optional climb_interval_seconds override"
```

---

### Task 4: Generate the 14 scenario YAMLs

**Files:**
- Create: `experiments/make_study_2026_10_11_configs.py`
- Create (by running the script): `experiments/configs/study_2026_10_11/01_s2_tune_rgtf0_rep1.yaml` through `14_s4b_em60_rgtf1.yaml`

**Interfaces:**
- Consumes: `experiments/configs/scenario_2_retryguard_no_topfull.yaml` as the template (same template `experiments/make_study_configs.py` uses).
- Produces: 14 YAML files plus a printed order table.

- [ ] **Step 1: Write the generator script**

```python
#!/usr/bin/env python3
"""Generate the 2026-10-11 S2-tuning (4 holds) and S3/S4A/S4B topology (10
holds) study YAMLs.

Template is the locked Paper-C1 RetryGuard-only Scenario 2 config. Each cell
is a deep copy with the study overrides applied: scenario id/name, Locust
user counts, one scale_constraints CPU override (S3/S4A/S4B only), the tuned
RetryGuard parameter set, topfull_rl.enabled, log_folder, and description.
`restart_before_hold` is dropped if the template still has it. Checkout and
recommendations stay up.

    python experiments/make_study_2026_10_11_configs.py --write
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml

TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "configs" / "scenario_2_retryguard_no_topfull.yaml"
)
OUT_DIR = Path(__file__).resolve().parent / "configs" / "study_2026_10_11"
PLAN_FILE = "docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-holds.md"

S2_COUNTS = {
    "getproduct": 275,
    "postcheckout": 90,
    "getcart": 100,
    "postcart": 90,
    "emptycart": 5,
}
S1_COUNTS = {
    "getproduct": 175,
    "postcheckout": 30,
    "getcart": 70,
    "postcart": 90,
    "emptycart": 5,
}

# Tuned RetryGuard parameter set, shared by all 14 holds in this study.
TUNED_RETRYGUARD = {
    "interval_samples": 20,
    "retries_threshold": 0.4,
    "climb_rpr_1_to_2": 0.16,
    "climb_rpr_2_to_3": 0.32,
    "climb_interval_seconds": 10,
    "reenable_rejection": 0.25,
}

CELLS = [
    # (order, file, scenario_id, scenario_name, user_counts, limits, topfull, log_folder, note)
    (1, "01_s2_tune_rgtf0_rep1.yaml", 2, "sustained_overload", S2_COUNTS, [],
     False, "study4_s2_tune_rgtf0_rep1", "S2 tuned RetryGuard params, repeat 1, TopFull off."),
    (2, "02_s2_tune_rgtf1_rep1.yaml", 2, "sustained_overload", S2_COUNTS, [],
     True, "study4_s2_tune_rgtf1_rep1", "S2 tuned RetryGuard params, repeat 1, TopFull on."),
    (3, "03_s2_tune_rgtf0_rep2.yaml", 2, "sustained_overload", S2_COUNTS, [],
     False, "study4_s2_tune_rgtf0_rep2", "S2 tuned RetryGuard params, repeat 2, TopFull off."),
    (4, "04_s2_tune_rgtf1_rep2.yaml", 2, "sustained_overload", S2_COUNTS, [],
     True, "study4_s2_tune_rgtf1_rep2", "S2 tuned RetryGuard params, repeat 2, TopFull on."),
    (5, "05_s3_ck300_rgtf0.yaml", 3, "targeted_bottleneck", S1_COUNTS,
     [("checkoutservice", 300)], False, "study4_s3_ck300_rgtf0",
     "S3 checkoutservice 300m, tuned RetryGuard params, TopFull off."),
    (6, "06_s3_ck300_rgtf1.yaml", 3, "targeted_bottleneck", S1_COUNTS,
     [("checkoutservice", 300)], True, "study4_s3_ck300_rgtf1",
     "S3 checkoutservice 300m, tuned RetryGuard params, TopFull on."),
    (7, "07_s4a_pc400_u140_rgtf0.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 140}, [("productcatalogservice", 400)], False,
     "study4_s4a_pc400_u140_rgtf0",
     "S4A productcatalogservice 400m, postcart 90->140, TopFull off."),
    (8, "08_s4a_pc400_u140_rgtf1.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 140}, [("productcatalogservice", 400)], True,
     "study4_s4a_pc400_u140_rgtf1",
     "S4A productcatalogservice 400m, postcart 90->140, TopFull on."),
    (9, "09_s4a_pc400_u190_rgtf0.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 190}, [("productcatalogservice", 400)], False,
     "study4_s4a_pc400_u190_rgtf0",
     "S4A productcatalogservice 400m, postcart 90->190, TopFull off."),
    (10, "10_s4a_pc400_u190_rgtf1.yaml", 4, "topology_position_A",
     {**S1_COUNTS, "postcart": 190}, [("productcatalogservice", 400)], True,
     "study4_s4a_pc400_u190_rgtf1",
     "S4A productcatalogservice 400m, postcart 90->190, TopFull on."),
    (11, "11_s4b_em50_rgtf0.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 50)], False, "study4_s4b_em50_rgtf0",
     "S4B emailservice 50m, tuned RetryGuard params, TopFull off."),
    (12, "12_s4b_em50_rgtf1.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 50)], True, "study4_s4b_em50_rgtf1",
     "S4B emailservice 50m, tuned RetryGuard params, TopFull on."),
    (13, "13_s4b_em60_rgtf0.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 60)], False, "study4_s4b_em60_rgtf0",
     "S4B emailservice 60m, tuned RetryGuard params, TopFull off."),
    (14, "14_s4b_em60_rgtf1.yaml", 4, "topology_position_B", S1_COUNTS,
     [("emailservice", 60)], True, "study4_s4b_em60_rgtf1",
     "S4B emailservice 60m, tuned RetryGuard params, TopFull on."),
]


def _load_template() -> dict:
    with TEMPLATE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _replace_cpu_limit(cfg: dict, deployment: str, millicores: int) -> None:
    matches = [row for row in cfg["scale_constraints"] if row["deployment"] == deployment]
    if len(matches) != 1:
        raise KeyError(f"{deployment} appears {len(matches)} times in scale_constraints")
    matches[0]["cpu_limit_millicores"] = millicores


def _materialize(template: dict, cell: tuple) -> dict:
    order, fname, scenario_id, scenario_name, user_counts, limits, topfull, log_folder, note = cell
    cfg = copy.deepcopy(template)
    cfg.pop("restart_before_hold", None)
    cfg["scenario_id"] = scenario_id
    cfg["scenario_name"] = scenario_name
    cfg["run_number"] = 1
    cfg["condition"] = "retryguard"
    cfg["locust"]["user_counts"] = dict(user_counts)
    cfg["topfull_rl"]["enabled"] = topfull
    rg = cfg["retryguard"]
    rg["enabled"] = True
    for key, value in TUNED_RETRYGUARD.items():
        rg[key] = value
    for deployment, millicores in limits:
        _replace_cpu_limit(cfg, deployment, millicores)
    cfg["log_folder"] = log_folder
    mix = "/".join(
        str(user_counts[k])
        for k in ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")
    )
    cfg["description"] = f"Study 2026-10-11 {log_folder} ({mix}): {note}"
    return {"path": OUT_DIR / fname, "order": order, "cfg": cfg}


def build_configs() -> list[dict]:
    template = _load_template()
    return [_materialize(template, cell) for cell in CELLS]


def write_configs(items: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = f"# Generated by experiments/make_study_2026_10_11_configs.py\n# Plan: {PLAN_FILE}\n"
    for item in items:
        text = header + yaml.safe_dump(item["cfg"], sort_keys=False, default_flow_style=False)
        Path(item["path"]).write_text(text, encoding="utf-8", newline="\n")


def format_order_table(items: list[dict]) -> str:
    rows = sorted(items, key=lambda c: c["order"])
    lines = [
        f"{'order':>5}  {'log_folder':<32}  {'sid':>3} {'scenario_name':<20}  {'tf':<5}  user_counts",
    ]
    for item in rows:
        cfg = item["cfg"]
        counts = cfg["locust"]["user_counts"]
        mix = "/".join(str(counts[k]) for k in
                        ("getproduct", "postcheckout", "getcart", "postcart", "emptycart"))
        lines.append(
            f"{item['order']:>5}  {cfg['log_folder']:<32}  {cfg['scenario_id']:>3} "
            f"{cfg['scenario_name']:<20}  {str(cfg['topfull_rl']['enabled']):<5}  {mix}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 2026-10-11 study configs.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write YAMLs under experiments/configs/study_2026_10_11/ and print the order table.",
    )
    args = parser.parse_args()
    items = build_configs()
    if not args.write:
        parser.error("pass --write to emit the study YAMLs")
    write_configs(items)
    print(format_order_table(items))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

```powershell
cd experiments
python make_study_2026_10_11_configs.py --write
cd ..
```

Expected: 14 lines printed, `order` 1 through 14, matching the Hold order table above.

- [ ] **Step 3: Check the generated files**

```powershell
python -c "import yaml, pathlib; p=pathlib.Path('experiments/configs/study_2026_10_11'); [print(f.name, c['scenario_id'], c['scenario_name'], c['topfull_rl']['enabled'], c['retryguard']['interval_samples'], c['retryguard']['retries_threshold'], c['retryguard']['climb_rpr_1_to_2'], c['retryguard']['climb_rpr_2_to_3'], c['retryguard']['climb_interval_seconds'], c['retryguard']['reenable_rejection'], c['log_folder'], c['locust']['user_counts']) for f in sorted(p.glob('*.yaml')) for c in [yaml.safe_load(f.read_text())]]"
```

Expected: 14 lines. Every line shows `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`. `scenario_id`/`scenario_name` match the Hold order table (2/sustained_overload for files 1-4, 3/targeted_bottleneck for 5-6, 4/topology_position_A for 7-10, 4/topology_position_B for 11-14). `topfull_rl.enabled` alternates `False`/`True` within each pair. User counts: files 1-6 and 11-14 have `postcart: 90`; file 7-8 have `postcart: 140`; files 9-10 have `postcart: 190`. None of the 14 files contains a `restart_before_hold` key:

```powershell
python -c "import yaml, pathlib; p=pathlib.Path('experiments/configs/study_2026_10_11'); bad=[f.name for f in p.glob('*.yaml') if 'restart_before_hold' in yaml.safe_load(f.read_text())]; assert not bad, bad; print('no restart_before_hold')"
```

Expected: `no restart_before_hold`.

Separately confirm the CPU overrides landed:

```powershell
python -c "
import yaml, pathlib
p = pathlib.Path('experiments/configs/study_2026_10_11')
targets = {
    '05_s3_ck300_rgtf0.yaml': ('checkoutservice', 300),
    '06_s3_ck300_rgtf1.yaml': ('checkoutservice', 300),
    '07_s4a_pc400_u140_rgtf0.yaml': ('productcatalogservice', 400),
    '08_s4a_pc400_u140_rgtf1.yaml': ('productcatalogservice', 400),
    '09_s4a_pc400_u190_rgtf0.yaml': ('productcatalogservice', 400),
    '10_s4a_pc400_u190_rgtf1.yaml': ('productcatalogservice', 400),
    '11_s4b_em50_rgtf0.yaml': ('emailservice', 50),
    '12_s4b_em50_rgtf1.yaml': ('emailservice', 50),
    '13_s4b_em60_rgtf0.yaml': ('emailservice', 60),
    '14_s4b_em60_rgtf1.yaml': ('emailservice', 60),
}
for name, (dep, expect) in targets.items():
    cfg = yaml.safe_load((p / name).read_text())
    rows = [r for r in cfg['scale_constraints'] if r['deployment'] == dep]
    assert len(rows) == 1, (name, dep, rows)
    assert rows[0]['cpu_limit_millicores'] == expect, (name, rows[0])
print('all 10 CPU overrides match')
"
```

Expected: `all 10 CPU overrides match`.

- [ ] **Step 4: Commit**

```powershell
git add experiments/make_study_2026_10_11_configs.py experiments/configs/study_2026_10_11 docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-holds.md
git commit -m "feat: generate 14 S2-tuning and S3/S4A/S4B topology study configs"
```

---

### Task 5: Preflight — cluster up, healthy, pinned

- [ ] **Step 1: Start the three VMs if stopped, then refresh SSH**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md).

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update `HostName` in `~/.ssh/config` from that table, then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
```

Expected user: `idozacharia`.

- [ ] **Step 2: Cluster health**

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default"
```

All nodes `Ready`. Boutique pods `2/2`.

- [ ] **Step 3: Paper-C1 pin**

```powershell
ssh topfull-master "kubectl patch hpa frontend-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}'; kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}'; kubectl patch deployment frontend -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"90m\"}}}}}'; kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit- ; kubectl rollout status deployment/frontend -n default --timeout=180s"
```

Confirm: `kubectl get hpa frontend-hpa productcatalogservice-hpa` shows `4/4` and `1/1`, and the frontend Deployment template's annotation is `proxyCPU=90m` with `proxyCPULimit` absent. Wait until frontend is 4 ready pods.

- [ ] **Step 4: Stop leftover writers once**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

Do not add an idle wait here. Hold 1 starts at Task 6 after Steps 1-3. If some other `run_scenario.py` exited less than 120 s ago, wait out the rest of that 120 s first (`Start-Sleep -Seconds` for the remainder only).

---

### Task 6: Run the fourteen holds

Repeat Steps 1-8 below for holds 1 through 14, in the Hold order table above. `CFG` is `experiments/configs/study_2026_10_11/<file>`.

`run_scenario.py` kills leftover master processes, starts the proxy, collectors, and RetryGuard together, and exits before Locust if a required process is missing (`Master processes not running`). That does not replace Steps 1-3. Locust is on the load VM, and a collector that is still writing recreates files in `src/logs` after `clear_logs`.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear.** Anything other than the two `-clear` lines means stop.

```powershell
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` must print nothing. If a file reappears, a writer is still alive — stop and re-run Step 1.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_11/<file>
```

One process only. A 600 s hold plus the overlapped startup is about 12 minutes. Do not start the next hold until this process exits. The 120 s cool-off clock starts at that exit. Steps 5 and 6 happen during the wait.

- [ ] **Step 5: Pull**

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_11/<file>
```

- [ ] **Step 6: Gates.** Keep the folder either way.

Pass when all of these are true:

- `total.csv` has roughly 540-580 data rows for holds 1-4 (S2, 600 s) and holds 5-14 (S1 mix, 600 s) alike.
- `retryguard.log` START line contains `metric=edge_rpr`, `interval_samples=20`, `retries_threshold=0.40`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`. No `PATCH_FAIL` and no traceback.
- `resource_usage.csv`: frontend `replica_count` is 4 on every sample.
- `service_capacity.json` matches this hold's intended CPU table (Paper-C1, except the one overridden deployment on holds 5-14).
- TopFull off holds (odd-numbered in each pair): live `topfull_throttle.csv` thresholds stay at the 10000 passthrough. TopFull on holds (even-numbered): some live cap is below 10000.
- VirtualServices are back to `attempts: 3` with no route `timeout` after the run.

A failure is logged, the folder is kept, and the hold is replayed **once** by copying the YAML to a sibling `*_r2.yaml` with `log_folder` suffixed `_r2`. Do not overwrite the failed folder. Do not replay a second time.

- [ ] **Step 7: Finish the 120 s cool-off**, then Steps 1-3 again, before the next hold. Skip this after hold 14. If Steps 5-6 already used the whole 120 s, go straight to Steps 1-3. Otherwise `Start-Sleep -Seconds` for the remainder, measured from the `run_scenario.py` exit.

- [ ] **Step 8: Append one line** to `docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md` (create it on hold 1 with a one-line header, same shape as `docs/superpowers/plans/2026-10-10-s2-rr025-climb-run-log.md`):

`hold N | log_folder | PASS or INVALID | locust rows | note (CPU override, user counts, TopFull on/off, any toggle count)`

---

### Task 7: Restore, commit, push

- [ ] **Step 1: Final cleanup** — Task 6 Steps 1-2, so Locust and the master writers are stopped.

- [ ] **Step 2: Restore the unpinned pair**

```powershell
ssh topfull-master "kubectl patch hpa frontend-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":4}}'; kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{\"spec\":{\"minReplicas\":1,\"maxReplicas\":2}}'; kubectl patch deployment frontend -n default --type merge -p '{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}'; kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-"
```

Confirm with `kubectl get hpa frontend-hpa productcatalogservice-hpa` and the frontend annotation.

- [ ] **Step 3: Restore Paper-C1 CPU on the three overridden deployments**

S3/S4A/S4B holds leave `checkoutservice`/`productcatalogservice`/`emailservice` at their overridden millicores (300/400/60) after hold 14 exits, because `paper_cpu_reconcile: false` on every config in this study. Put them back at the Paper-C1 defaults used elsewhere in the campaign (`checkoutservice` 800m, `productcatalogservice` 800m, `emailservice` 120m):

```powershell
ssh topfull-master "kubectl patch deployment checkoutservice -n default --type merge -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"800m\"},\"requests\":{\"cpu\":\"800m\"}}}]}}}}'; kubectl patch deployment productcatalogservice -n default --type merge -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"800m\"},\"requests\":{\"cpu\":\"800m\"}}}]}}}}'; kubectl patch deployment emailservice -n default --type merge -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"server\",\"resources\":{\"limits\":{\"cpu\":\"120m\"},\"requests\":{\"cpu\":\"120m\"}}}]}}}}'; kubectl rollout status deployment/checkoutservice -n default --timeout=120s; kubectl rollout status deployment/productcatalogservice -n default --timeout=120s; kubectl rollout status deployment/emailservice -n default --timeout=120s"
```

Confirm with `kubectl get deployment checkoutservice productcatalogservice emailservice -n default -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[0].resources.limits.cpu}{"\n"}{end}'` (run against each name individually if the range form errors on this `kubectl` version) — expect `800m`, `800m`, `120m`.

- [ ] **Step 4: One Done bullet in `STATUS.md`, then replace Latest in `AGENTS.md`**

Append one bullet under Done in [STATUS.md](../../../STATUS.md), dated 2026-10-11. Name the 14 `study4_*` folders, the tuned RetryGuard parameter set (`reenable_rejection=0.25`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`), the new optional `climb_interval_seconds` key, and which of the 10 S3/S4A/S4B holds toggled RetryGuard (from the run log). Point at the run log and, once written, the analysis guide(s) from Task 8. These folders do not move a locked scenario YAML, so leave "Next free slots" unchanged unless a locked YAML's `run_number` actually changed.

Replace the three Latest lines in [AGENTS.md](../../../AGENTS.md) §4. Do not append a fourth line. One of the three should name this study and point at the STATUS.md bullet.

- [ ] **Step 5: Commit everything left**

```powershell
git status -sb
git add experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf0_rep1 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep1 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf0_rep2 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep2 experiments/results/campaign_48/S3_targeted_bottleneck/study4_s3_ck300_rgtf0 experiments/results/campaign_48/S3_targeted_bottleneck/study4_s3_ck300_rgtf1 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u140_rgtf0 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u140_rgtf1 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u190_rgtf0 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u190_rgtf1 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em50_rgtf0 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em50_rgtf1 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em60_rgtf0 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em60_rgtf1 docs/superpowers/plans/2026-10-11-s2-tuning-and-s3-s4-topology-run-log.md STATUS.md AGENTS.md
```

If a replay folder with a `_r2` suffix exists, add that folder too. If `git status` shows a secret (`.env`, a key, `credentials.json`), unstage it and stop.

```powershell
git commit -m "data: 14 S2-tuning and S3/S4A/S4B topology holds"
git status -sb
```

Skip the commit if the tree is already clean.

- [ ] **Step 6: Push**

```powershell
git push -u origin study-reenable-rejection-s3-s4
git status -sb
```

Expected: the branch matches `origin/study-reenable-rejection-s3-s4` and the working tree is clean.

---

### Task 8: Score and write the two analysis guides

This task reads real data produced by Task 6 and cannot be pre-written. Do it after Task 7.

**Files:**
- Create: `Guides and Info/2026-10-11-s2-tuning-abc.md` (holds 1-4)
- Create: `Guides and Info/2026-10-11-s3-s4-topology-abc.md` (holds 5-14)

- [ ] **Step 1: Score each group**

```powershell
python experiments/analysis_score.py --sep 2 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf0_rep1 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep1 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf0_rep2 experiments/results/campaign_48/S2_sustained_overload/study4_s2_tune_rgtf1_rep2 > /tmp/study4_s2_tune.txt

python experiments/analysis_score.py --sep 2 experiments/results/campaign_48/S3_targeted_bottleneck/study4_s3_ck300_rgtf0 experiments/results/campaign_48/S3_targeted_bottleneck/study4_s3_ck300_rgtf1 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u140_rgtf0 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u140_rgtf1 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u190_rgtf0 experiments/results/campaign_48/S4A_topology_position_A/study4_s4a_pc400_u190_rgtf1 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em50_rgtf0 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em50_rgtf1 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em60_rgtf0 experiments/results/campaign_48/S4B_topology_position_B/study4_s4b_em60_rgtf1 > /tmp/study4_s3_s4.txt
```

- [ ] **Step 2: Write the two guides**

Follow [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md) section order and the (a)/(b)/(c) definitions in [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md). Use the four already-written 2026-10-10 guides as the closest style reference (`Guides and Info/2026-10-10-s2-rr025-climb-analysis.md` and the three `2026-10-10-set-b-*.md` files) — same Setup/Gate/Edge-mode-bars/(a)/(b)/(c)/toggle/Locust/CPU/Per-hold section order, filled from the real scored output in Step 1, not invented numbers.

- [ ] **Step 3: Commit**

```powershell
git add "Guides and Info/2026-10-11-s2-tuning-abc.md" "Guides and Info/2026-10-11-s3-s4-topology-abc.md"
git commit -m "docs: analysis for S2-tuning and S3/S4A/S4B topology holds"
git push
```

---

### Task 9: Confirm the branch is pushed, then stop the VMs

Do this only after Task 8 is committed. Do not stop the VMs while `git status` is dirty or the branch is ahead of origin.

- [ ] **Step 1: Working tree is clean, and the branch matches origin**

```powershell
git status -sb
git status --porcelain
git rev-parse HEAD
git rev-parse "@{u}"
```

Expected: `git status -sb` is exactly `## study-reenable-rejection-s3-s4...origin/study-reenable-rejection-s3-s4` with no ahead/behind marker. `git status --porcelain` prints nothing. The two `rev-parse` hashes are identical.

If porcelain is not empty, inspect it. A secret (`.env`, a key, `credentials.json`) means stop and do not commit it. Otherwise add the leftover study files (results, the run log, `STATUS.md`, `AGENTS.md`, the two analysis guides, this plan), commit, and `git push`. Then run this step again.

If the branch is ahead of origin, `git push` and run this step again. If it is behind, stop and do not force-push.

- [ ] **Step 2: Stop the three VMs**

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Pass `--project` so a leftover `networks-workshop` config does not stop the original VMs. Do not start those originals.

- [ ] **Step 3: Confirm all three are `TERMINATED`**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are each `TERMINATED`.

- [ ] **Step 4: Record the stop, then re-check the push**

In the 2026-10-11 Done bullet in [STATUS.md](../../../STATUS.md), the last sentence is `VMs left TERMINATED`. If that sentence is missing, add it, commit, and `git push`. Then repeat Step 1. Step 1 must pass again after this edit.

## Time

Code change and tests: under an hour. Config generation: a few minutes. Fourteen holds: about 12 minutes run plus pull during the wait, and 120 s cool-off between holds, roughly 4 hours total. Both analysis guides together: about half an hour once the score files exist. `analysis_score.py` produces the numbers, and the section order is already fixed by the template. The holds are the long part.

## Self-review

- Task 1-2 add exactly one optional, additive YAML key (`climb_interval_seconds`); every existing YAML and historical run is unaffected because the default path is unchanged (`None` → `CLIMB_INTERVAL_SECONDS` = 15).
- Task 2 also fixes a pre-existing broken test fixture discovered while implementing (confirmed failing before the fix, in scope since it's the exact function being touched).
- 14 holds match the user's request exactly: Set 1 is 2 reps × {RG-on/TF-off, RG-on/TF-on} on the locked S2 mix; Set 2 is S3 (1 CPU variant × 2 arms) + S4A (2 user-count variants × 2 arms) + S4B (2 CPU variants × 2 arms) on the locked S1 mix, all with the same tuned RetryGuard parameters.
- Every hold uses the 120 s cool-off and leftover-writer check in AGENTS.md §6. The YAMLs omit `restart_before_hold`, so checkout and recommendations stay up. The runner's overlapped startup does not replace that pre-run check.
- Cluster pin happens once before hold 1 and is restored once after hold 14; the three CPU overrides unique to Set 2 are explicitly restored in Task 7 Step 3 since `paper_cpu_reconcile: false` does not undo them.
- Task 9 confirms the working tree is clean and `HEAD` matches `origin/study-reenable-rejection-s3-s4`, then stops the three VMs and checks that each status is `TERMINATED`.
