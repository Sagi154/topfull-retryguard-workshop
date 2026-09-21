# Loadgen Shape Migration (Ron's Swarm Shape) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land decisions 2–3 of [2026-09-21-loadgen-shape-ron-migration-design.md](../specs/2026-09-21-loadgen-shape-ron-migration-design.md) — adopt Ron Nezer's `@task()` weight remix in the shared Locust file, fix `run_scenario.py` so `online_boutique_create_v2.sh`'s independent `EMPTYCART` env var actually works without breaking the 16 scenario YAMLs still on the legacy scripts, wire up automatic deployment of repo-tracked loadgen scripts, and verify all of it live on `topfull-load` — **without** touching any scenario YAML's numbers or `locust.scripts:` list (that stays deferred per the design doc §3/§5).

**Architecture:** Three small, independent code changes to `experiments/run_scenario.py` plus one new one-shot patcher script (`experiments/patch_locust_task_weights.py`, modeled on the existing `experiments/patch_metric_collector.py` pattern but with a testable pure function), followed by a live-cluster verification pass with no code changes. No scenario config, no `TopFull/` submodule file, and no live YAML is modified.

**Tech Stack:** Python 3 (`run_scenario.py`, `topfull_cpu_quotas.py` style conventions), `unittest` + `unittest.mock` (existing `test_run_scenario.py` conventions — SSH/SCP fully mocked, no network in unit tests), Bash (`online_boutique_create_v2.sh`, already committed), SSH/SCP to `topfull-load` for live verification only.

## Global Constraints

- Do not modify any file under `experiments/configs/` (the 16 scenario YAMLs) — loadgen numbers and `locust.scripts:` rewiring are explicitly deferred (design doc §3/§5, decision "shape_only_scope").
- Do not modify `TopFull/` (git submodule) or any file under it.
- Do not modify the legacy `online_boutique_create.sh` / `online_boutique_create2.sh` deployed copies on `topfull-load` — they are hand-patched per `Guides and Info/PHASE5-EXPERIMENTS-GUIDE.md` §7 and are out of scope (design doc decision 5: drop `create2.sh`'s trickle role by *not building an equivalent*, not by editing the legacy files).
- All SSH/SCP in unit tests must be mocked — no test may open a real network connection (matches `test_run_scenario.py`'s existing docstring contract).
- Every live SSH/SCP command in this plan's verification task uses the OpenSSH host alias `topfull-load` (per `.cursor/rules/topfull-ssh.mdc`) — never a hardcoded IP.
- `experiments/loadgen/online_boutique_create_v2.sh` itself is not modified by this plan — it already implements the adopted shape (design doc decision 3); only its *deployment* and the *env vars feeding it* are wired up here.

---

## File Structure

| File | Change |
|---|---|
| `experiments/run_scenario.py` | `_launch_locust()`: dual-export `EMPTYCART` alongside legacy `CART` (Task 1); new `_deploy_local_loadgen_scripts()` helper, called from `_launch_locust()` (Task 3) |
| `experiments/test_run_scenario.py` | New/updated tests for both changes above (Tasks 1 and 3) |
| `experiments/patch_locust_task_weights.py` | **New.** One-shot patcher for the deployed `locust_online_boutique.py`'s five `@task()` weights (Task 2) |
| `experiments/test_patch_locust_task_weights.py` | **New.** Unit tests for the patcher's pure `patch_text()` function (Task 2) |

No new scenario config, no submodule changes, no changes to `experiments/loadgen/online_boutique_create_v2.sh`.

---

### Task 1: Dual-export `EMPTYCART` alongside legacy `CART` in `_launch_locust()`

**Files:**
- Modify: `experiments/run_scenario.py:930-945` (the `ENV_MAP` block inside `_launch_locust`)
- Test: `experiments/test_run_scenario.py` (`TestLaunchLocustWiring`, ~line 168)

**Interfaces:**
- Consumes: nothing new — same `cfg`, `user_counts`, `spawn_rate` signature `_launch_locust(cfg: dict, user_counts: dict, spawn_rate) -> None`.
- Produces: the exported shell env now includes both `CART=<n>` (legacy, unchanged) and `EMPTYCART=<n>` (new) whenever `user_counts["emptycart"]` is set. Task 3 does not depend on this export directly, but the live verification in Task 4 exercises both together.

Today, `run_scenario.py`'s `ENV_MAP` maps YAML key `emptycart` only to shell var `CART`, because the legacy `online_boutique_create.sh`/`create2.sh` only ever read `$CART` for the merged getcart/postcart/emptycart swarm. `online_boutique_create_v2.sh` (already committed) instead reads `$EMPTYCART` directly for its independent emptycart swarm. Per design doc decision 3, we must export **both** — not switch the mapping — so the 16 YAMLs still pointing at the legacy scripts keep working unchanged (design doc §1: switching the mapping outright would silently stop those scripts from receiving any cart-family count at all).

- [ ] **Step 1: Extend the existing test to also assert `EMPTYCART` is exported**

Open `experiments/test_run_scenario.py` and find `test_launch_locust_exports_user_counts_and_spawn_rate` (~line 168). Add one assertion line right after the existing `CART` assertion:

```python
        self.assertIn("export CART=75", written_content)
        self.assertIn("export EMPTYCART=75", written_content)
```

So the full test body reads:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_launch_locust_exports_user_counts_and_spawn_rate(
        self, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="3")
        cfg = self._base_cfg()

        run_scenario._launch_locust(
            cfg,
            user_counts={"getproduct": 25, "emptycart": 75},
            spawn_rate=90,
        )

        written_path, written_content = mock_write_script.call_args[0][1:3]
        self.assertEqual(written_path, "/tmp/rg_locust_launch.sh")
        self.assertIn("export GETPRODUCT=25", written_content)
        self.assertIn("export CART=75", written_content)
        self.assertIn("export EMPTYCART=75", written_content)
        self.assertIn("export RATE=90", written_content)

        kill_calls = [
            c for c in mock_ssh.call_args_list
            if "pkill" in c.args[1] or "kill-server" in c.args[1]
        ]
        self.assertTrue(kill_calls, "expected a Locust kill command before relaunch")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_run_scenario.py::TestLaunchLocustWiring::test_launch_locust_exports_user_counts_and_spawn_rate -v`
Expected: FAIL — `export EMPTYCART=75` not found in `written_content` (current code only ever emits `export CART=75`).

- [ ] **Step 3: Add a second, focused test for the "no emptycart key" case**

Immediately after the test from Step 1, add:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_launch_locust_omits_emptycart_exports_when_key_absent(
        self, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="3")
        cfg = self._base_cfg()

        run_scenario._launch_locust(
            cfg,
            user_counts={"getproduct": 25},
            spawn_rate=90,
        )

        _, written_content = mock_write_script.call_args[0][1:3]
        self.assertNotIn("CART=", written_content)
        self.assertNotIn("EMPTYCART=", written_content)
```

This locks in that both exports are gated on the same `"emptycart"` key being present — no accidental unconditional `EMPTYCART=` export when a scenario doesn't set one.

- [ ] **Step 4: Run both new/changed tests to verify the second one already passes and the first still fails**

Run: `python -m pytest experiments/test_run_scenario.py::TestLaunchLocustWiring -v`
Expected: `test_launch_locust_exports_user_counts_and_spawn_rate` FAILs (same reason as Step 2); `test_launch_locust_omits_emptycart_exports_when_key_absent` PASSes (current code already only exports when the key is present).

- [ ] **Step 5: Implement the dual export in `_launch_locust()`**

In `experiments/run_scenario.py`, find this block (~line 930):

```python
    # Env var mapping: YAML key -> shell variable name in create scripts
    ENV_MAP = {
        "getproduct":   "GETPRODUCT",
        "postcheckout": "POSTCHECKOUT",
        "getcart":      "GETCART",
        "postcart":     "POSTCART",
        "emptycart":    "CART",      # create scripts use CART, not EMPTYCART
    }

    exports = []
    for yaml_key, shell_var in ENV_MAP.items():
        if yaml_key in user_counts:
            exports.append(f"export {shell_var}={user_counts[yaml_key]}")
    if spawn_rate is not None:
        exports.append(f"export RATE={spawn_rate}")
```

Replace it with:

```python
    # Env var mapping: YAML key -> shell variable name in create scripts
    ENV_MAP = {
        "getproduct":   "GETPRODUCT",
        "postcheckout": "POSTCHECKOUT",
        "getcart":      "GETCART",
        "postcart":     "POSTCART",
        "emptycart":    "CART",      # legacy create.sh/create2.sh read CART, not EMPTYCART
    }

    exports = []
    for yaml_key, shell_var in ENV_MAP.items():
        if yaml_key in user_counts:
            exports.append(f"export {shell_var}={user_counts[yaml_key]}")
    # online_boutique_create_v2.sh (2026-09-21 loadgen shape design, decision 3)
    # reads EMPTYCART directly instead of the legacy merged CART variable.
    # Export both: existing scenario YAMLs keep driving the legacy scripts
    # via CART unchanged, and v2 becomes usable once a scenario points a
    # locust.scripts entry at it, with zero YAML schema change required.
    if "emptycart" in user_counts:
        exports.append(f"export EMPTYCART={user_counts['emptycart']}")
    if spawn_rate is not None:
        exports.append(f"export RATE={spawn_rate}")
```

- [ ] **Step 6: Run the full `TestLaunchLocustWiring` class to verify all tests pass**

Run: `python -m pytest experiments/test_run_scenario.py::TestLaunchLocustWiring -v`
Expected: all PASS, including both tests touched in Steps 1–3.

- [ ] **Step 7: Run the full `test_run_scenario.py` suite to check for regressions**

Run: `python -m pytest experiments/test_run_scenario.py -q`
Expected: same pass/fail counts as the pre-existing baseline (one known, pre-existing, unrelated failure: `TestStartRetryGuardWiring::test_start_deploys_retryguard_py` fails on `KeyError: 'attempts_on'` in its own test fixture — this predates this plan and this task must not change that count).

- [ ] **Step 8: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: dual-export EMPTYCART alongside legacy CART in _launch_locust

Per 2026-09-21-loadgen-shape-ron-migration-design.md decision 3:
online_boutique_create_v2.sh reads EMPTYCART directly; legacy
online_boutique_create.sh/create2.sh only ever read CART. Export both
so the 16 scenario YAMLs still on the legacy scripts are unaffected,
while v2 becomes usable once a scenario's locust.scripts points at it."
```

---

### Task 2: One-shot patcher for the deployed locustfile's `@task()` weights

**Files:**
- Create: `experiments/patch_locust_task_weights.py`
- Test: `experiments/test_patch_locust_task_weights.py`

**Interfaces:**
- Consumes: nothing from Task 1/3.
- Produces: `patch_text(text: str) -> str` — a pure function other code/tests can call; `main()` — reads `TARGET`, calls `patch_text`, writes back, prints `PATCHED_OK` or `ALREADY_PATCHED`. Task 4's live verification invokes this script's `main()` remotely via `python3 patch_locust_task_weights.py`.

This ports Ron's `@task()` weight remix (design doc decision 2) onto the **deployed** `locust_online_boutique.py` on `topfull-load` (`/home/idozacharia/TopFull/TopFull_loadgen/locust_online_boutique.py`). That file is not tracked in this repo (it lives only on the remote VM, already carrying unrelated Locust-2.x-API patches per `RON-NEZER-SETUP-VS-WORKSHOP.md` §3) — the same situation `experiments/patch_metric_collector.py` already solves for a different file, via a one-shot Python patcher scp'd and run remotely rather than a full local copy that would risk clobbering those unrelated remote-only fixes. This task follows that same pattern, but factors the substitution logic into a standalone, unit-testable `patch_text()` function (the existing `patch_metric_collector.py` does not have this — a worthwhile small improvement for a **new** file, without touching that existing one).

The five weight changes (verified live against the deployed file, `2026-09-21-loadgen-shape-ron-migration-design.md` §1):

| function | `@tag(...)` | old weight | new weight |
|---|---|---|---|
| `checkout_slow` | `postcheckout` | 50 | 500 |
| `viewCart_slow` | `getcart` | 30 | 100 |
| `addToCart_slow` | `postcart` | 15 | 1 |
| `emptyCart_slow` | `emptycart` | 15 | 1 |
| `browseProduct_slow` | `getproduct` | 150 | 100 |

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_patch_locust_task_weights.py`:

```python
"""
test_patch_locust_task_weights.py — Unit tests for the pure patch_text()
function in patch_locust_task_weights.py. No file I/O, no network.

Run:
    python experiments/test_patch_locust_task_weights.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import patch_locust_task_weights as patcher


# Minimal fixture matching the real locust_online_boutique.py's shape for
# the five decorated task methods this patcher targets (unrelated file
# content omitted — the patcher only ever matches on these anchor lines).
UNPATCHED_TEXT = """\
class OnlineBoutiqueUser(TaskSet):
    @tag('postcheckout')
    @task(50)
    def checkout_slow(self):
        pass

    @tag('getcart')
    @task(30)
    def viewCart_slow(self):
        pass

    @tag('postcart')
    @task(15)
    def addToCart_slow(self):
        pass

    @tag('emptycart')
    @task(15)
    def emptyCart_slow(self):
        pass

    @tag('getproduct')
    @task(150)
    def browseProduct_slow(self):
        pass
"""

PATCHED_TEXT = (
    UNPATCHED_TEXT
    .replace("@task(50)\n    def checkout_slow(self):", "@task(500)\n    def checkout_slow(self):")
    .replace("@task(30)\n    def viewCart_slow(self):", "@task(100)\n    def viewCart_slow(self):")
    .replace("@task(15)\n    def addToCart_slow(self):", "@task(1)\n    def addToCart_slow(self):")
    .replace("@task(15)\n    def emptyCart_slow(self):", "@task(1)\n    def emptyCart_slow(self):")
    .replace("@task(150)\n    def browseProduct_slow(self):", "@task(100)\n    def browseProduct_slow(self):")
)


class TestPatchText(unittest.TestCase):
    def test_patches_all_five_weights(self):
        result = patcher.patch_text(UNPATCHED_TEXT)
        self.assertEqual(result, PATCHED_TEXT)

    def test_idempotent_when_already_fully_patched(self):
        result = patcher.patch_text(PATCHED_TEXT)
        self.assertEqual(result, PATCHED_TEXT)

    def test_idempotent_on_second_call_chained(self):
        once = patcher.patch_text(UNPATCHED_TEXT)
        twice = patcher.patch_text(once)
        self.assertEqual(once, twice)

    def test_partial_prior_patch_is_completed(self):
        # Simulate a file where one weight was already hand-fixed to the
        # new value but the rest are still old — patch_text must finish
        # the job rather than bailing out or double-patching.
        partial = UNPATCHED_TEXT.replace(
            "@task(50)\n    def checkout_slow(self):",
            "@task(500)\n    def checkout_slow(self):",
        )
        result = patcher.patch_text(partial)
        self.assertEqual(result, PATCHED_TEXT)

    def test_missing_anchor_raises_system_exit(self):
        broken = UNPATCHED_TEXT.replace(
            "@task(50)\n    def checkout_slow(self):",
            "@task(999)\n    def checkout_slow(self):",
        )
        with self.assertRaises(SystemExit):
            patcher.patch_text(broken)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails with an import error**

Run: `python -m pytest experiments/test_patch_locust_task_weights.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'patch_locust_task_weights'` (file doesn't exist yet).

- [ ] **Step 3: Write the patcher**

Create `experiments/patch_locust_task_weights.py`:

```python
#!/usr/bin/env python3
"""
One-shot patch for locust_online_boutique.py on the loadgen VM.

Adopts Ron Nezer's @task() weight remix — see
docs/superpowers/specs/2026-09-21-loadgen-shape-ron-migration-design.md,
decision 2: postcheckout 50->500, getcart 30->100, postcart 15->1,
emptycart 15->1, getproduct 150->100.

These weights only matter when several Locust tags share one swarm and
Locust splits users between them by weight. Under this repo's adopted
loadgen shape (one independent single-tag swarm per tag — see
experiments/loadgen/online_boutique_create_v2.sh) they are currently
inert for every scenario we run. They are ported here anyway, for
fidelity with Ron's tree, per the same decision.

Usage (on the loadgen VM, after this file is deployed there):
    python3 patch_locust_task_weights.py
"""
from pathlib import Path

TARGET = Path(
    "/home/idozacharia/TopFull/TopFull_loadgen/locust_online_boutique.py"
)

# (function name, old @task weight, new @task weight)
WEIGHT_CHANGES = [
    ("checkout_slow", 50, 500),        # @tag('postcheckout')
    ("viewCart_slow", 30, 100),        # @tag('getcart')
    ("addToCart_slow", 15, 1),         # @tag('postcart')
    ("emptyCart_slow", 15, 1),         # @tag('emptycart')
    ("browseProduct_slow", 150, 100),  # @tag('getproduct')
]


def patch_text(text: str) -> str:
    """
    Apply the weight remix to `text` and return the result.

    Idempotent: if a function's weight is already at its target value,
    that function is left untouched (handles both "already fully patched"
    and "partially hand-patched" inputs identically). Raises SystemExit
    without changing anything if a function's weight is at neither the old
    nor the new value — that means locust_online_boutique.py's shape
    changed and this patch needs a human to re-check it.
    """
    for func_name, old_weight, new_weight in WEIGHT_CHANGES:
        new_block = f"@task({new_weight})\n    def {func_name}(self):"
        if new_block in text:
            continue
        old_block = f"@task({old_weight})\n    def {func_name}(self):"
        if old_block not in text:
            raise SystemExit(
                f"ERROR: found neither @task({old_weight}) nor "
                f"@task({new_weight}) immediately before 'def {func_name}' — "
                "locust_online_boutique.py may have changed; aborting "
                "without changing anything"
            )
        text = text.replace(old_block, new_block, 1)
    return text


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    patched = patch_text(text)
    if patched == text:
        print("ALREADY_PATCHED")
        return
    TARGET.write_text(patched, encoding="utf-8")
    print("PATCHED_OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_patch_locust_task_weights.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/patch_locust_task_weights.py experiments/test_patch_locust_task_weights.py
git commit -m "feat: add one-shot patcher for Ron's Locust task-weight remix

Ports @task() weight remix onto the deployed (not repo-tracked)
locust_online_boutique.py on topfull-load, per
2026-09-21-loadgen-shape-ron-migration-design.md decision 2. Inert
under our current loadgen shape (independent per-tag swarms), adopted
for fidelity only. Not yet run against the live file — see Task 4."
```

---

### Task 3: Auto-deploy repo-tracked loadgen scripts before every Locust launch

**Files:**
- Modify: `experiments/run_scenario.py` (`_launch_locust`, right after the `scripts = ...` line, ~line 927)
- Test: `experiments/test_run_scenario.py` (new `TestDeployLocalLoadgenScripts` class, plus one assertion added to `TestLaunchLocustWiring`)

**Interfaces:**
- Consumes: `EXPERIMENTS_DIR` (existing module-level `Path` constant), `deploy_repo_script(host: str, filename: str, remote_path: str) -> None` (existing function, unchanged).
- Produces: `_deploy_local_loadgen_scripts(cfg: dict, scripts: list[str]) -> None` — new function, called from `_launch_locust` before it builds `launch_cmd`.

Today, `_launch_locust()` runs whatever `locust.scripts:` names, assuming they already exist at `topfull_loadgen_path` on the loadgen VM — true for the legacy `online_boutique_create.sh`/`create2.sh` (hand-patched there once, not repo-tracked), but `online_boutique_create_v2.sh` lives in this repo (`experiments/loadgen/`) and needs the same "always redeploy from the repo, never trust a stale remote copy" treatment `deploy_repo_script` already gives `retryguard.py`/the collectors on master. This task adds that, generically: any script name that exists locally under `experiments/loadgen/` gets redeployed before launch; anything not tracked locally (the legacy scripts) is left alone.

- [ ] **Step 1: Write the failing tests for the new helper**

In `experiments/test_run_scenario.py`, add this new test class right after `TestLaunchLocustWiring` (after its last method, before the next `class` line — find the exact location by searching for `class TestStartRetryGuardWiring`):

```python
class TestDeployLocalLoadgenScripts(unittest.TestCase):
    def _cfg(self):
        return {
            "infra": {
                "loadgen_ssh_host": "topfull-load",
                "topfull_loadgen_path": "/home/idozacharia/TopFull/TopFull_loadgen",
            },
        }

    @mock.patch("run_scenario.deploy_repo_script")
    def test_deploys_scripts_present_under_experiments_loadgen(self, mock_deploy):
        with tempfile.TemporaryDirectory() as tmp:
            loadgen_dir = Path(tmp) / "loadgen"
            loadgen_dir.mkdir()
            (loadgen_dir / "online_boutique_create_v2.sh").write_text("#!/bin/bash\n")

            with mock.patch.object(run_scenario, "EXPERIMENTS_DIR", Path(tmp)):
                run_scenario._deploy_local_loadgen_scripts(
                    self._cfg(), ["online_boutique_create_v2.sh"]
                )

        mock_deploy.assert_called_once_with(
            "topfull-load",
            "loadgen/online_boutique_create_v2.sh",
            "/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh",
        )

    @mock.patch("run_scenario.deploy_repo_script")
    def test_skips_scripts_not_present_locally(self, mock_deploy):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(run_scenario, "EXPERIMENTS_DIR", Path(tmp)):
                run_scenario._deploy_local_loadgen_scripts(
                    self._cfg(),
                    ["online_boutique_create.sh", "online_boutique_create2.sh"],
                )

        mock_deploy.assert_not_called()

    @mock.patch("run_scenario.deploy_repo_script")
    def test_mixed_list_deploys_only_the_locally_tracked_one(self, mock_deploy):
        with tempfile.TemporaryDirectory() as tmp:
            loadgen_dir = Path(tmp) / "loadgen"
            loadgen_dir.mkdir()
            (loadgen_dir / "online_boutique_create_v2.sh").write_text("#!/bin/bash\n")

            with mock.patch.object(run_scenario, "EXPERIMENTS_DIR", Path(tmp)):
                run_scenario._deploy_local_loadgen_scripts(
                    self._cfg(),
                    ["online_boutique_create.sh", "online_boutique_create_v2.sh"],
                )

        mock_deploy.assert_called_once_with(
            "topfull-load",
            "loadgen/online_boutique_create_v2.sh",
            "/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh",
        )
```

Add the `tempfile` import at the top of the file next to the existing `import json` / `import sys` block:

```python
import json
import sys
import tempfile
import unittest
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_run_scenario.py::TestDeployLocalLoadgenScripts -v`
Expected: FAIL — `AttributeError: module 'run_scenario' has no attribute '_deploy_local_loadgen_scripts'`.

- [ ] **Step 3: Implement `_deploy_local_loadgen_scripts` and wire it into `_launch_locust`**

In `experiments/run_scenario.py`, find `_launch_locust`'s opening (~line 922):

```python
def _launch_locust(cfg: dict, user_counts: dict, spawn_rate) -> None:
    """Kill any running Locust and start it fresh at the given load level."""
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    loadgen_path = cfg["infra"]["topfull_loadgen_path"]
    lc = cfg.get("locust", {})
    scripts = lc.get("scripts", ["online_boutique_create.sh", "online_boutique_create2.sh"])
```

Add the new helper function immediately above `_launch_locust`, and one call inside it, so the block becomes:

```python
def _deploy_local_loadgen_scripts(cfg: dict, scripts: list[str]) -> None:
    """
    Redeploy any of `scripts` that this repo tracks under experiments/loadgen/
    onto the loadgen host before launching — the same "never trust a stale
    remote copy" treatment deploy_repo_script already gives master's
    collectors. Scripts not present locally (the legacy
    online_boutique_create.sh / create2.sh, hand-patched directly on
    topfull-load per PHASE5-EXPERIMENTS-GUIDE.md §7) are left untouched.
    """
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    loadgen_path = cfg["infra"]["topfull_loadgen_path"]
    for s in scripts:
        local = EXPERIMENTS_DIR / "loadgen" / s
        if local.is_file():
            deploy_repo_script(loadgen, f"loadgen/{s}", f"{loadgen_path}/{s}")


def _launch_locust(cfg: dict, user_counts: dict, spawn_rate) -> None:
    """Kill any running Locust and start it fresh at the given load level."""
    loadgen = cfg["infra"]["loadgen_ssh_host"]
    loadgen_path = cfg["infra"]["topfull_loadgen_path"]
    lc = cfg.get("locust", {})
    scripts = lc.get("scripts", ["online_boutique_create.sh", "online_boutique_create2.sh"])
    _deploy_local_loadgen_scripts(cfg, scripts)
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `python -m pytest experiments/test_run_scenario.py::TestDeployLocalLoadgenScripts -v`
Expected: all 3 PASS.

- [ ] **Step 5: Add one assertion to `TestLaunchLocustWiring` confirming the deploy step fires during a normal launch**

Find `test_launch_locust_exports_user_counts_and_spawn_rate` again (now updated by Task 1) and add a `mock.patch` for the new helper plus one assertion. Change its decorators and signature from:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    def test_launch_locust_exports_user_counts_and_spawn_rate(
        self, mock_ssh, mock_write_script, mock_wait
    ):
```

to:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario._deploy_local_loadgen_scripts")
    def test_launch_locust_exports_user_counts_and_spawn_rate(
        self, mock_deploy_scripts, mock_ssh, mock_write_script, mock_wait
    ):
```

and add, right after the existing `self.assertIn("export RATE=90", written_content)` line:

```python
        mock_deploy_scripts.assert_called_once_with(
            cfg, ["online_boutique_create.sh", "online_boutique_create2.sh"]
        )
```

(Note: `mock.patch` decorators apply bottom-up, so the new `mock_deploy_scripts` parameter goes first in the method signature, matching the new topmost `@mock.patch("run_scenario._deploy_local_loadgen_scripts")` line being closest to the function.)

Apply the same two edits (decorator + parameter, no extra assertion needed) to `test_launch_locust_exits_if_no_locust_processes_found` and `test_launch_locust_omits_emptycart_exports_when_key_absent` so they don't break — both currently patch `run_scenario.ssh`/`write_remote_script`/`wait_with_progress` only, and now indirectly call the new (unmocked) `_deploy_local_loadgen_scripts`, which would try to read the real `EXPERIMENTS_DIR` — harmless (it only checks `is_file()` and does nothing for the legacy script names in `_base_cfg()`), but mock it anyway for consistency and speed:

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario._deploy_local_loadgen_scripts")
    def test_launch_locust_exits_if_no_locust_processes_found(
        self, mock_deploy_scripts, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="0")
        cfg = self._base_cfg()

        with self.assertRaises(SystemExit):
            run_scenario._launch_locust(cfg, user_counts={}, spawn_rate=None)
```

```python
    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.write_remote_script")
    @mock.patch("run_scenario.ssh")
    @mock.patch("run_scenario._deploy_local_loadgen_scripts")
    def test_launch_locust_omits_emptycart_exports_when_key_absent(
        self, mock_deploy_scripts, mock_ssh, mock_write_script, mock_wait
    ):
        mock_ssh.return_value = SimpleNamespace(stdout="3")
        cfg = self._base_cfg()

        run_scenario._launch_locust(
            cfg,
            user_counts={"getproduct": 25},
            spawn_rate=90,
        )

        _, written_content = mock_write_script.call_args[0][1:3]
        self.assertNotIn("CART=", written_content)
        self.assertNotIn("EMPTYCART=", written_content)
```

- [ ] **Step 6: Run the full `TestLaunchLocustWiring` and `TestDeployLocalLoadgenScripts` classes**

Run: `python -m pytest experiments/test_run_scenario.py::TestLaunchLocustWiring experiments/test_run_scenario.py::TestDeployLocalLoadgenScripts -v`
Expected: all PASS.

- [ ] **Step 7: Run the full `test_run_scenario.py` suite to check for regressions**

Run: `python -m pytest experiments/test_run_scenario.py -q`
Expected: same baseline as Task 1 Step 7 (one pre-existing, unrelated failure in `TestStartRetryGuardWiring::test_start_deploys_retryguard_py`; nothing else changes).

- [ ] **Step 8: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: auto-deploy repo-tracked loadgen scripts before each Locust launch

_deploy_local_loadgen_scripts() redeploys any locust.scripts entry this
repo tracks under experiments/loadgen/ (currently just
online_boutique_create_v2.sh) before every launch, the same way
deploy_repo_script already keeps master's collectors in sync. Legacy
online_boutique_create.sh/create2.sh (not repo-tracked) are untouched."
```

---

### Task 4: Live verification on `topfull-load` (no code changes, no commit)

**Files:** none (verification only).

**Interfaces:** none — this task exercises Tasks 1–3's code against the real VM.

Confirms, on the live cluster: the weight patcher applies correctly and is idempotent; `online_boutique_create_v2.sh` deploys and actually launches five independent per-tag Locust swarms; and the legacy scripts are unaffected by the new dual `CART`/`EMPTYCART` export. This mirrors how the 2026-09-20 migration plan's Tasks 4/6/7 verified live changes without a full campaign run — small, targeted, and reversible.

- [ ] **Step 1: Confirm SSH reachability**

Run: `ssh -o ConnectTimeout=8 topfull-load "hostname; whoami"`
Expected: prints the loadgen VM's hostname and the `idozacharia` (or your own) account. If this times out, the VM is likely `TERMINATED` or has a stale IP — follow `Guides and Info/CONNECT-VMS.md` before continuing.

- [ ] **Step 2: Deploy and run the weight patcher; verify `PATCHED_OK`**

```powershell
scp -o BatchMode=yes -o ControlMaster=no experiments\patch_locust_task_weights.py topfull-load:/tmp/patch_locust_task_weights.py
ssh topfull-load "cd /home/idozacharia/TopFull/TopFull_loadgen && python3 /tmp/patch_locust_task_weights.py"
```
Expected: `PATCHED_OK`.

- [ ] **Step 3: Verify the five weights live in the deployed file**

```powershell
ssh topfull-load "grep -n -A1 '@task(' /home/idozacharia/TopFull/TopFull_loadgen/locust_online_boutique.py"
```
Expected: the five `@task(N)` lines now read `500`, `100`, `1`, `1`, `100` immediately before `checkout_slow`, `viewCart_slow`, `addToCart_slow`, `emptyCart_slow`, `browseProduct_slow` respectively (matching the table in Task 2), and no other `@task(N)` line in the file changed.

- [ ] **Step 4: Re-run the patcher to confirm idempotency live**

```powershell
ssh topfull-load "cd /home/idozacharia/TopFull/TopFull_loadgen && python3 /tmp/patch_locust_task_weights.py"
```
Expected: `ALREADY_PATCHED`, and the file's content is unchanged (re-run Step 3's `grep` to confirm the same five values, no duplication).

- [ ] **Step 5: Deploy `online_boutique_create_v2.sh` and confirm it exists remotely**

```powershell
scp -o BatchMode=yes -o ControlMaster=no experiments\loadgen\online_boutique_create_v2.sh topfull-load:/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh
ssh topfull-load "test -f /home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create_v2.sh && echo DEPLOYED_OK"
```
Expected: `DEPLOYED_OK`. (This step manually reproduces what Task 3's `_deploy_local_loadgen_scripts` will do automatically the first time any scenario config lists `online_boutique_create_v2.sh` under `locust.scripts:` — no scenario does yet, per this plan's Global Constraints, so this manual deploy is needed to test the script itself right now.)

- [ ] **Step 6: Launch v2 with small test counts and confirm five independent tags actually run**

```powershell
ssh topfull-load "cd /home/idozacharia/TopFull/TopFull_loadgen && tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; sleep 1; GETPRODUCT=5 RATE_GETPRODUCT=5 POSTCHECKOUT=5 RATE_POSTCHECKOUT=5 GETCART=5 POSTCART=5 EMPTYCART=5 RATE=5 WORKERS_GETPRODUCT=1 WORKERS_POSTCHECKOUT=1 bash online_boutique_create_v2.sh"
sleep 10
ssh topfull-load "tmux ls; pgrep -c locust"
```
Expected: `tmux ls` shows 5 distinct sessions (`v2_postcheckout`, `v2_getproduct`, `v2_getcart`, `v2_postcart`, `v2_emptycart`); `pgrep -c locust` reports 6 processes (1 master + 1 worker each for postcheckout and getproduct, plus 1 single process each for getcart/postcart/emptycart — see the script's own header comment for the general formula, reduced here since `WORKERS_GETPRODUCT`/`WORKERS_POSTCHECKOUT` were forced to `1` for a fast/light smoke test rather than the script's own defaults of 4/2).

- [ ] **Step 7: Tear down the smoke-test Locust processes**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-load "pgrep -c locust 2>/dev/null || echo 0"
```
Expected: `0`.

- [ ] **Step 8: Statically confirm the legacy scripts are unaffected by the new dual export**

```powershell
ssh topfull-load "grep -c EMPTYCART /home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create.sh /home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create2.sh"
```
Expected: `0` for both files — neither legacy script references `$EMPTYCART`, so Task 1's added export is inert noise to them, confirming no regression without needing a full scenario/campaign run.

- [ ] **Step 9: Record the outcome**

No file changes or commits result from this task. If any expectation above doesn't hold, stop and treat it as a plan or implementation bug to fix in Tasks 1–3 (re-open this plan's checkboxes) rather than patching the live VM by hand.

---

## Explicitly out of scope (tracked in the design doc, not here)

- Loadgen numbers (`GETPRODUCT`/`POSTCHECKOUT`/`GETCART`/`POSTCART`/`EMPTYCART` per scenario, `RATE`) — deferred to a fresh calibration pass under the Ron-config regime.
- Repointing any of the 16 `experiments/configs/*.yaml` files' `locust.scripts:` at `online_boutique_create_v2.sh`.
- The S1–S6 scenario methodology rework (migration design doc §8).
