# RetryGuard Ramp Step Durations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the edge-mode retry ramp climb on per-step quiet durations: 0→1 after 30 s, 1→2 after 15 s, 2→3 after 15 s.

**Architecture:** Today `EdgeController._ramp_tick` and the 0→1 fallback both use one `self.interval` (30 s, from `interval_samples`). Add a module constant `CLIMB_INTERVAL_SECONDS = 15` and pass it to `streak_met` only for the climb decision at attempts 1 and 2. The 0→1 step keeps `self.interval` (30). The shed decision (rpr > 0.5) keeps `self.interval` (30), so only the *increase* gets faster. Rpr climb bars (0.17 / 0.33), the hold band, and the 0.10 rejection re-enable bar are unchanged. Rejection mode is untouched.

**Tech Stack:** Python 3, `unittest` (`experiments/test_retryguard.py`), markdown docs.

## Global Constraints

- 0→1 needs 30 s of rejection < 0.10 (unchanged; still `interval_samples`, YAML value 30).
- 1→2 needs 15 s of rpr ≤ 0.17.
- 2→3 needs 15 s of rpr ≤ 0.33.
- Shed from any ramp step to 0 still needs 30 s (`self.interval`) of rpr > 0.5. Not changed by this plan.
- Streaks are measured in seconds of row timestamps (`streak_met` / `streak_elapsed_s`), not tick counts.
- Rejection mode (`apply_algorithm1` for `retry_metric: rejection`) is not modified.
- No YAML changes: `interval_samples: 30` stays in all configs; the 15 s value is a code constant.
- Do not touch `experiments/results/`.

## File Structure

- Modify `experiments/retryguard.py` — add constant, per-step interval helper, use it in `_ramp_tick`, update class docstring.
- Modify `experiments/test_retryguard.py` — the ramp test class (around lines 770–880): helper `to_attempts` and the climb/hold tests.
- Modify `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` — edge-mode ramp section.
- Modify `AGENTS.md` — one new §4 bullet (RetryGuard attempt ramp step durations).

---

### Task 1: Per-step climb durations in the controller

**Files:**
- Modify: `experiments/retryguard.py` (near `climb_rpr_limit`, ~line 681; `EdgeController` docstring ~line 705; `_ramp_tick` ~line 764)
- Test: `experiments/test_retryguard.py` (ramp test class, ~lines 770–880)

**Interfaces:**
- Produces: `CLIMB_INTERVAL_SECONDS: int = 15`; `climb_interval_s(attempts: int, reenable_interval: int) -> int` returning `reenable_interval` for `attempts == 0` and `CLIMB_INTERVAL_SECONDS` for `attempts >= 1`.
- Consumes: existing `streak_met(since, now, interval)`, `EdgeController.interval`.

- [x] **Step 1: Update tests to the new durations (failing first)**

In the ramp test class of `experiments/test_retryguard.py`:

1. Change the `to_attempts` helper so climbs feed 16 rows (1 opening row + 15 s) instead of `ctrl.interval + 1`:

```python
    def to_attempts(self, ctrl, attempts):
        # One row to open the streak, then N seconds of 1s rows.
        reenable_span = ctrl.interval + 1                      # 0 -> 1: 30 s
        climb_span = retryguard.CLIMB_INTERVAL_SECONDS + 1     # 1 -> 2, 2 -> 3: 15 s
        if attempts == 0:
            change = self.feed(ctrl, reenable_span, 0.9)[0]
            ctrl.commit(change)
            return
        self.to_attempts(ctrl, 0)
        back = self.feed(ctrl, reenable_span, None, {"checkoutservice": 0.05})[0]
        ctrl.commit(back)
        while ctrl.edge_state[self.EDGE].attempts < attempts:
            climbed = self.feed(ctrl, climb_span, 0.05)[0]
            ctrl.commit(climbed)
```

(Keep the existing shed feed length: shed from attempts >= 1 still needs `ctrl.interval + 1` rows. The `attempts == 0` branch above is the shed from attempts_on and keeps `ctrl.interval + 1`.)

2. Add a test for the interval helper:

```python
    def test_climb_interval_per_step(self):
        self.assertEqual(retryguard.CLIMB_INTERVAL_SECONDS, 15)
        self.assertEqual(retryguard.climb_interval_s(0, 30), 30)
        self.assertEqual(retryguard.climb_interval_s(1, 30), 15)
        self.assertEqual(retryguard.climb_interval_s(2, 30), 15)
```

3. Rewrite `test_quiet_rpr_climbs_one_step_at_a_time` so the climb arrives after 15 s, not 30 s:

```python
    def test_quiet_rpr_climbs_one_step_at_a_time(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        self.assertEqual(self.feed(ctrl, 15, 0.10), [])      # rows 1..15 = 14 s elapsed
        climb = self.feed(ctrl, 1, 0.10)                      # row 16 = 15 s elapsed
        self.assertEqual(climb[0].transition, "RAMP")
        self.assertEqual(climb[0].desired_attempts, {"frontend": 2})
        self.assertEqual(climb[0].lines[0][1:3], ("1", "2"))
        ctrl.commit(climb[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 2)
        self.assertEqual(ctrl.edge_state[self.EDGE].consecutive_low, 0)
        self.assertEqual(self.feed(ctrl, 15, 0.10), [])
        climb3 = self.feed(ctrl, 1, 0.10)
        self.assertEqual(climb3[0].desired_attempts, {"frontend": 3})
        self.assertEqual(climb3[0].caller_attempts, {})
        ctrl.commit(climb3[0])
        self.assertEqual(ctrl.edge_state[self.EDGE].attempts, 3)
        self.assertEqual(self.feed(ctrl, 5, 0.10), [])
```

4. In `test_between_climb_bar_and_0_5_holds`, the pre-break feed `self.feed(ctrl, 2, 0.10)` is still short of 15 s; keep it. Replace the final hold feed length so it still exceeds the old and new bars: `self.feed(ctrl, 5, 0.40)` is already fine (hold band never climbs). No change needed beyond verifying it passes.

5. In `test_above_0_5_sheds_from_a_ramp_step` keep `self.feed(ctrl, 3, 0.90)` (still short of 30 s). Add a regression test that shed stays at 30 s:

```python
    def test_shed_from_ramp_step_still_needs_30_seconds(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        self.assertEqual(self.feed(ctrl, 29, 0.90), [])      # 28 s elapsed
        self.assertEqual(self.feed(ctrl, 1, 0.90), [])       # 29 s elapsed
        shed = self.feed(ctrl, 2, 0.90)                       # reaches 30 s
        self.assertEqual(shed[0].transition, "OFF")
```

6. Update `test_uncommitted_climb_is_proposed_again`: first feed of 4 rows at 0.05 is below 15 s now. Change to:

```python
    def test_uncommitted_climb_is_proposed_again(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 1)
        first = self.feed(ctrl, 16, 0.05)
        self.assertEqual(len(first), 1)
        again = self.feed(ctrl, 1, 0.05)
        self.assertEqual(again[0].desired_attempts, {"frontend": 2})
```

7. Add a 0→1 regression test so the first step stays at 30 s:

```python
    def test_zero_to_one_still_needs_30_seconds(self):
        ctrl = self.make()
        self.to_attempts(ctrl, 0)
        self.assertEqual(self.feed(ctrl, 16, None, {"checkoutservice": 0.05}), [])  # 15 s
        self.assertEqual(self.feed(ctrl, 14, None, {"checkoutservice": 0.05}), [])  # 29 s
        back = self.feed(ctrl, 2, None, {"checkoutservice": 0.05})                  # 30 s
        self.assertEqual(back[0].transition, "ON")
```

- [x] **Step 2: Run tests and confirm they fail**

Run: `python -m unittest experiments.test_retryguard -v 2>&1 | Select-String -Pattern "FAIL|ERROR|AttributeError"`
Expected: failures with `AttributeError: module 'retryguard' has no attribute 'CLIMB_INTERVAL_SECONDS'` (and `climb_interval_s`).

- [x] **Step 3: Implement the constant and helper**

In `experiments/retryguard.py`, directly after `REENABLE_REJECTION_THRESHOLD = 0.10`:

```python
# Quiet time needed for each ramp climb after the first attempt is restored.
# 0 -> 1 keeps the configured interval (interval_samples, 30 s). 1 -> 2 and
# 2 -> 3 use this shorter bar. Shed (rpr above the threshold) keeps the
# configured interval.
CLIMB_INTERVAL_SECONDS = 15


def climb_interval_s(attempts: int, reenable_interval: int) -> int:
    """Seconds of quiet needed to leave `attempts` for the next step up."""
    if int(attempts) <= 0:
        return int(reenable_interval)
    return CLIMB_INTERVAL_SECONDS
```

- [x] **Step 4: Use it in `_ramp_tick`**

Replace the tail of `_ramp_tick`:

```python
        if streak_met(state.high_since, timestamp, self.interval):
            return "shed"
        if streak_met(state.low_since, timestamp, self.interval):
            return "climb"
        return None
```

with:

```python
        if streak_met(state.high_since, timestamp, self.interval):
            return "shed"
        climb_s = climb_interval_s(state.attempts, self.interval)
        if streak_met(state.low_since, timestamp, climb_s):
            return "climb"
        return None
```

Update the `EdgeController` docstring sentence "Further attempts climb one at a time while rpr stays at or under climb_rpr_limit." to add: "Climbs 1→2 and 2→3 each need CLIMB_INTERVAL_SECONDS (15 s) of quiet; 0→1 and shed use the full interval (30 s)."

Also update the comment at `retryguard.py` line ~158 only if it states a duration for ramp steps (check with `Select-String`); do not change anything else.

- [x] **Step 5: Run the full RetryGuard tests**

Run: `python -m unittest experiments.test_retryguard -v`
Expected: all tests PASS, including the three new ones.

- [x] **Step 6: Run the other test modules that import retryguard**

Run: `python -m unittest experiments.test_run_scenario experiments.test_rho_estimate_report experiments.test_estimate_service_mu`
Expected: PASS (no behavior change outside edge-mode ramp).

- [x] **Step 7: Commit**

```bash
git add experiments/retryguard.py experiments/test_retryguard.py
git commit -m "feat(retryguard): climb 1->2 and 2->3 after 15s of quiet, 0->1 stays 30s"
```

---

### Task 2: Docs

**Files:**
- Modify: `Guides and Info/RETRYGUARD-IMPLEMENTATION.md` (edge-mode / attempt-ramp section)
- Modify: `AGENTS.md` (§4, after the "RetryGuard attempt ramp (2026-10-07)" bullet)

- [x] **Step 1: Find the ramp section**

Run: `Select-String -Path "Guides and Info/RETRYGUARD-IMPLEMENTATION.md" -Pattern "ramp|0.17|0.33|full interval"`
Expected: line numbers for the paragraph that says a climb needs "a full interval".

- [x] **Step 2: Edit the guide**

Replace "for a full interval" wording on the climb rules with a table:

```markdown
| Step | Condition | Quiet time |
|---|---|---|
| 0 → 1 | inbound rejection under 0.10 | 30 s (`interval_samples`) |
| 1 → 2 | rpr ≤ 0.17 | 15 s (`CLIMB_INTERVAL_SECONDS`) |
| 2 → 3 | rpr ≤ 0.33 | 15 s (`CLIMB_INTERVAL_SECONDS`) |
| any → 0 (shed) | rpr > 0.5 | 30 s (`interval_samples`) |
```

State that the whole ramp from 0 to 3 now takes at least 60 s (was 90 s), and that the 15 s value is a constant in `retryguard.py`, not a YAML key.

- [x] **Step 3: Add the AGENTS.md bullet**

After the "RetryGuard attempt ramp (2026-10-07)" bullet add:

```markdown
- **RetryGuard ramp step durations (2026-10-08)** — edge-mode climbs now take 30 s for 0→1 (rejection under 0.10), 15 s for 1→2 (rpr ≤ 0.17), and 15 s for 2→3 (rpr ≤ 0.33). Shed above 0.5 still needs 30 s. 15 s is `CLIMB_INTERVAL_SECONDS` in `experiments/retryguard.py`. Holds recorded before this change used 30 s per step. Rejection mode unchanged. Plan: [2026-10-08-retryguard-ramp-step-durations.md](docs/superpowers/plans/2026-10-08-retryguard-ramp-step-durations.md).
```

- [x] **Step 4: Commit**

```bash
git add "Guides and Info/RETRYGUARD-IMPLEMENTATION.md" AGENTS.md
git commit -m "docs: RetryGuard ramp step durations 30/15/15 s"
```

---

### Task 3 (optional, needs the user): live check

Not part of the code change. If the user wants a hold, run RetryGuard-only on the run 89 mix (next free `scenario_2_retryguard_no_topfull.yaml` slot) and check `retryguard.log`: each `0→1` line shows `elapsed_s` ≈ 30, each `1→2` and `2→3` line shows `elapsed_s` ≈ 15. Follow the AGENTS.md §6 pre-run clean-up and the Paper-C1 restore gate.

## Self-Review

- **Spec coverage:** 0→1 30 s (unchanged, regression test added), 1→2 15 s and 2→3 15 s (Task 1 tests and code). Docs updated in Task 2.
- **Open decision flagged:** shed stays at 30 s. If the user wants shed also faster, that is a separate change to `_ramp_tick`'s first `streak_met`.
- **Placeholders:** none. **Names:** `CLIMB_INTERVAL_SECONDS` and `climb_interval_s` are used identically in code and tests.
