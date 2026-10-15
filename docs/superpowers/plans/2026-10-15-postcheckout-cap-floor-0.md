# Cap Floor 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let TopFull write an admission cap of 0 req/s for every entry API, and keep that cap in force.

**Architecture:** The hold does not run the `TopFull/` submodule. It runs `/home/idozacharia/TopFull/...` on master, which `run_scenario.py` already patches in place (the CPU-quota overlay). This change adds one tested patcher module. At the start of each hold, before the proxy and the RL process start, the runner rewrites three live files: the Python write path that currently lifts every threshold `<= 10` up to 10, the RL loop that treats a summed threshold of 0 as "drop the cap and reset to 10000", and the Go limiter so a rate in `(0, 1)` can still admit. The rule itself is a pure function. The text inserted on the VM is generated from that same function, and a test executes the inserted Python.

**Tech Stack:** Python 3, unittest, the existing `run_scenario.py` SSH helpers. No new dependency. The Go change is a source rewrite compiled by the existing `go run proxy_online_boutique.go`.

**Branch:** All implementation commits go on `cap-floor-0`, created from `main` in Task 0. The current checkout stays in place. Do not create a worktree.

## Global Constraints

- Do not commit on `main`. Before every commit in Tasks 1–4, `git branch --show-current` must print `cap-floor-0`. If it prints `main`, stop.
- Do not push the branch. Do not open a pull request in this plan.

- Every entry API has a minimum written cap of `0`: `getproduct`, `postcheckout`, `getcart`, `postcart`, `emptycart`. The same floor applies to any other API `apply_threshold_proxy` writes. There is no remaining floor of 10.
- A non-positive threshold is written as 0, including the value present when an agent starts. The RL can raise it afterward.
- Do not edit anything under `TopFull/`. That tree is the upstream submodule. The files that run live on master.
- Do not change the fresh-0 rule in `experiments/run_timeline.py`, `experiments/analysis_score.py`, `experiments/graphs_tool.py`, or `experiments/multi_graphs_tool.py`. A fresh threshold of 0 is still an empty read on the graphs and in the scorer. A real cap of 0 is confirmed in `topfull_throttle.csv` (`threshold` `0.0`, `threshold_fresh` `1`), not on the cap line.
- Do not change `transfer_learning.py`, `deploy_mimd.py`, `deploy_without_cluster.py`, or `changeLimitDelta`. The live agent is `deploy_rl.py`. The live limiter signal is `SIGUSR1` → `changeLimitAbs`.
- Do not change the `All APIs clean` reset in `deploy_rl.py`.
- Remove the `zero threshold` branch. A summed cap of 0 must not call `stop(reset=True)`. That branch sets every API in the agent back to `10000`.
- When the summed threshold is 0, the goodput ratio passed to the RL is `0.0`. Do not divide by zero.
- Proxy burst in `changeLimitAbs`: rate `0` keeps burst `0` (reject every request). Rate in `(0, 1)` uses burst `1`. Rate `>= 1` keeps burst `int(rate)`. This applies to every API.
- The runner applies the patch before `start_overlapped_services`, which is what launches `go run` and `deploy_rl.py`.
- If a patch site is missing or appears more than once, the run aborts. Do not start the hold on the old floor of 10.

---

## File structure

- `experiments/topfull_cap_floor.py` — the floor rule, the goodput ratio, and the three source rewrites. Creates the text that lands on master.
- `experiments/test_topfull_cap_floor.py` — the rule, the rewrites against the submodule sources (read-only), and the guide sentence.
- `experiments/run_scenario.py` — `write_remote_text` and `ensure_cap_floor`, called once per hold.
- `experiments/test_run_scenario.py` — the runner uploads a patched file and skips a file that is already patched. No network.
- `Guides and Info/TOPFULL-THROTTLE-METRICS.md` — one paragraph on the new floor and on the fact that the cap line still omits a fresh 0.

## Task 0: Branch

**Files:**
- Commit on the new branch: `docs/superpowers/plans/2026-10-15-postcheckout-cap-floor-0.md`
- Do not add `_tmp_topfull_paper.txt`

**Interfaces:**
- Consumes: current `HEAD` of `main` (`578451d` at the time this plan was written; branch from whatever `main` is when Task 0 runs).
- Produces: local branch `cap-floor-0` checked out in this working tree. Later tasks commit only there.

- [ ] **Step 1: Confirm the starting branch**

Run: `git branch --show-current`

Expected: `main`

If the output is already `cap-floor-0`, skip to Step 4. If it is any other name, stop and ask before creating a branch.

- [ ] **Step 2: Create and check out the branch**

Run: `git checkout -b cap-floor-0`

Expected: `Switched to a new branch 'cap-floor-0'`

- [ ] **Step 3: Confirm the branch**

Run: `git branch --show-current`

Expected: `cap-floor-0`

Run: `git status -sb`

Expected: the first line is `## cap-floor-0`. `main` has no new commit.

- [ ] **Step 4: Commit the plan on the new branch**

```bash
git add docs/superpowers/plans/2026-10-15-postcheckout-cap-floor-0.md
git commit -m "$(cat <<'EOF'
docs: plan an admission-cap floor of 0 on its own branch

EOF
)"
git status -sb
git branch --show-current
```

Expected: the commit succeeds, `git branch --show-current` prints `cap-floor-0`, and `git status -sb` does not list the plan file.

## Task 1: Floor rule

**Files:**
- Create: `experiments/topfull_cap_floor.py`
- Create: `experiments/test_topfull_cap_floor.py`
- Test: `experiments/test_topfull_cap_floor.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `MIN_THRESHOLD: int` = `0`
  - `floor_threshold(threshold: float) -> float`
  - `goodput_ratio(goodput: float, threshold: float) -> float`
  - `overload_floor_new() -> str` — the block inserted into `apply_threshold_proxy`
  - `deploy_rl_zero_block() -> str` — replaces the reset-on-zero branch with a comment
  - `deploy_rl_ratio_block() -> str`
  - `proxy_burst_new() -> str`

- [ ] **Step 1: Write the failing test**

Create `experiments/test_topfull_cap_floor.py`:

```python
"""Floor rule for the TopFull admission cap. Every API may be 0."""
import unittest
from pathlib import Path

import topfull_cap_floor as floor


ROOT = Path(__file__).resolve().parents[1]
APIS = ("getproduct", "postcheckout", "getcart", "postcart", "emptycart")


class TestFloorThreshold(unittest.TestCase):
    def test_every_api_can_sit_at_zero(self):
        for name in APIS:
            for value, expected in ((0, 0), (-3, 0), (0.4, 0.4), (10, 10), (15.4, 15.4)):
                with self.subTest(name=name, value=value):
                    self.assertEqual(floor.floor_threshold(value), expected)

    def test_inlined_floor_matches_helper(self):
        src = "def apply(api):\n" + floor.overload_floor_new() + "    return api['threshold']\n"
        ns = {}
        exec(src, ns)
        for name in APIS:
            for value in (0, -3, 0.4, 10, 15.4):
                api = {"name": name, "threshold": value}
                self.assertEqual(ns["apply"](api), floor.floor_threshold(value))

    def test_zero_threshold_ratio_is_zero(self):
        self.assertEqual(floor.goodput_ratio(22.0, 0), 0.0)
        self.assertEqual(floor.goodput_ratio(22.0, 10), 2.2)

    def test_generated_blocks_use_the_floor(self):
        block = floor.overload_floor_new()
        self.assertIn("TOPFULL_CAP_FLOOR", block)
        self.assertIn("if api['threshold'] <= 0:", block)
        self.assertIn("api['threshold'] = 0", block)
        self.assertNotIn("10", block)
        zero = floor.deploy_rl_zero_block()
        self.assertIn("TOPFULL_CAP_FLOOR", zero)
        self.assertNotIn("stop(reset=True)", zero)
        self.assertNotIn("zero threshold", zero)
        ratio = floor.deploy_rl_ratio_block()
        self.assertEqual(
            ratio,
            "        state = 0.0 if self.threshold == 0 else goodput / self.threshold\n",
        )
        proxy = floor.proxy_burst_new()
        self.assertIn("if newRate > 0 && burst < 1", proxy)
        self.assertIn("targetLimiter.SetBurst(burst)", proxy)
        self.assertNotIn("SetBurst(int(newRate))", proxy)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_topfull_cap_floor.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'topfull_cap_floor'`

- [ ] **Step 3: Write the rule**

Create `experiments/topfull_cap_floor.py`:

```python
"""Admission-cap floor applied to the live TopFull sources on master.

Every API may be written as 0. The strings from the *_new() helpers are
what run_scenario.py inserts.
"""

MIN_THRESHOLD = 0

OVERLOAD_FLOOR_OLD = (
    "        if api['threshold'] <= 10:\n"
    "            api['threshold'] = 10\n"
)

DEPLOY_RL_ZERO_OLD = (
    "        if self.threshold == 0:\n"
    "            self.stop(reset=True)\n"
    '            print("zero threshold")\n'
    "            return\n"
)

DEPLOY_RL_RATIO_OLD = "        state = goodput / self.threshold\n"

PROXY_BURST_OLD = (
    "\t\ttargetLimiter.SetLimit(rate.Limit(float64(newRate)))\n"
    "\t\ttargetLimiter.SetBurst(int(newRate))\n"
    '\t\tprintln("Apply threshold to ", api, " : ", newRate)\n'
)


def floor_threshold(threshold: float) -> float:
    if threshold <= MIN_THRESHOLD:
        return MIN_THRESHOLD
    return threshold


def goodput_ratio(goodput: float, threshold: float) -> float:
    if threshold == 0:
        return 0.0
    return goodput / threshold


def overload_floor_new() -> str:
    return (
        "        # TOPFULL_CAP_FLOOR\n"
        "        if api['threshold'] <= 0:\n"
        "            api['threshold'] = 0\n"
    )


def deploy_rl_zero_block() -> str:
    return "        # TOPFULL_CAP_FLOOR: a summed threshold of 0 is a real cap.\n"


def deploy_rl_ratio_block() -> str:
    return "        state = 0.0 if self.threshold == 0 else goodput / self.threshold\n"


def proxy_burst_new() -> str:
    return (
        "\t\t// TOPFULL_CAP_FLOOR\n"
        "\t\tburst := int(newRate)\n"
        "\t\tif newRate > 0 && burst < 1 {\n"
        "\t\t\tburst = 1\n"
        "\t\t}\n"
        "\t\ttargetLimiter.SetLimit(rate.Limit(float64(newRate)))\n"
        "\t\ttargetLimiter.SetBurst(burst)\n"
        '\t\tprintln("Apply threshold to ", api, " : ", newRate)\n'
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest experiments/test_topfull_cap_floor.py -v`

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add experiments/topfull_cap_floor.py experiments/test_topfull_cap_floor.py
git commit -m "$(cat <<'EOF'
feat: define an admission-cap floor of 0 for every API

EOF
)"
```

## Task 2: Rewrite the three live sources

**Files:**
- Modify: `experiments/topfull_cap_floor.py` (add `_replace_once`, `patch_overload_detection`, `patch_deploy_rl`, `patch_proxy_burst`)
- Modify: `experiments/test_topfull_cap_floor.py` (add `TestPatchSources`)
- Test: `experiments/test_topfull_cap_floor.py`

**Interfaces:**
- Consumes: `OVERLOAD_FLOOR_OLD`, `DEPLOY_RL_ZERO_OLD`, `DEPLOY_RL_RATIO_OLD`, `PROXY_BURST_OLD`, and the block helpers from Task 1.
- Produces:
  - `patch_overload_detection(source: str) -> str`
  - `patch_deploy_rl(source: str) -> str`
  - `patch_proxy_burst(source: str) -> str`
  - Each returns `source` unchanged when its new block is already present.
  - Each raises `RuntimeError` when the old site is missing or appears more than once.

The read-only fixtures are the submodule copies. They still contain the upstream sites: `TopFull/TopFull_master/online_boutique_scripts/src/overload_detection.py` lines 54–55, `deploy_rl.py` lines 128–131 and 152, and `proxy/proxy_online_boutique.go` lines 205–207. Do not write those files.

- [ ] **Step 1: Write the failing test**

Append this class to `experiments/test_topfull_cap_floor.py` before the `if __name__` block:

```python
class TestPatchSources(unittest.TestCase):
    SRC = ROOT / "TopFull" / "TopFull_master" / "online_boutique_scripts" / "src"

    def test_overload_detection_floors_every_api_at_zero(self):
        source = (self.SRC / "overload_detection.py").read_text(encoding="utf-8")
        patched = floor.patch_overload_detection(source)
        self.assertNotIn(floor.OVERLOAD_FLOOR_OLD, patched)
        self.assertIn(floor.overload_floor_new(), patched)
        self.assertEqual(floor.patch_overload_detection(patched), patched)

    def test_deploy_rl_keeps_a_zero_cap(self):
        source = (self.SRC / "deploy_rl.py").read_text(encoding="utf-8")
        patched = floor.patch_deploy_rl(source)
        self.assertNotIn(floor.DEPLOY_RL_ZERO_OLD, patched)
        self.assertNotIn('print("zero threshold")', patched)
        self.assertNotIn(floor.DEPLOY_RL_RATIO_OLD, patched)
        self.assertIn(floor.deploy_rl_zero_block(), patched)
        self.assertIn(floor.deploy_rl_ratio_block(), patched)
        self.assertIn('print("All APIs clean")', patched)
        self.assertEqual(floor.patch_deploy_rl(patched), patched)

    def test_proxy_burst_allows_a_fraction_and_rejects_zero(self):
        source = (self.SRC / "proxy" / "proxy_online_boutique.go").read_text(encoding="utf-8")
        patched = floor.patch_proxy_burst(source)
        self.assertNotIn(floor.PROXY_BURST_OLD, patched)
        self.assertIn(floor.proxy_burst_new(), patched)
        self.assertIn("SetBurst(int(newRateFloat))", patched)
        self.assertEqual(floor.patch_proxy_burst(patched), patched)

    def test_missing_site_aborts(self):
        with self.assertRaises(RuntimeError):
            floor.patch_overload_detection("no floor here\n")
        with self.assertRaises(RuntimeError):
            floor.patch_deploy_rl("no zero check\n")
        with self.assertRaises(RuntimeError):
            floor.patch_proxy_burst("package main\n")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_topfull_cap_floor.py::TestPatchSources -v`

Expected: FAIL with `AttributeError: module 'topfull_cap_floor' has no attribute 'patch_overload_detection'`

- [ ] **Step 3: Write the rewrites**

Append this to `experiments/topfull_cap_floor.py`:

```python
def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 site, found {count}")
    return source.replace(old, new, 1)


def patch_overload_detection(source: str) -> str:
    return _replace_once(
        source, OVERLOAD_FLOOR_OLD, overload_floor_new(), "overload_detection floor"
    )


def patch_deploy_rl(source: str) -> str:
    source = _replace_once(
        source, DEPLOY_RL_ZERO_OLD, deploy_rl_zero_block(), "deploy_rl zero threshold"
    )
    return _replace_once(
        source, DEPLOY_RL_RATIO_OLD, deploy_rl_ratio_block(), "deploy_rl goodput ratio"
    )


def patch_proxy_burst(source: str) -> str:
    return _replace_once(
        source, PROXY_BURST_OLD, proxy_burst_new(), "proxy changeLimitAbs burst"
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest experiments/test_topfull_cap_floor.py -v`

Expected: PASS, 8 tests. `test_proxy_burst_allows_a_fraction_and_rejects_zero` still sees `SetBurst(int(newRateFloat))` because that line belongs to `changeLimitDelta`, which this patch leaves alone.

- [ ] **Step 5: Commit**

```bash
git add experiments/topfull_cap_floor.py experiments/test_topfull_cap_floor.py
git commit -m "$(cat <<'EOF'
feat: rewrite TopFull so a cap of 0 is kept for every API

EOF
)"
```

## Task 3: Install the patch before each hold

**Files:**
- Modify: `experiments/run_scenario.py` (add `write_remote_text` beside `write_remote_json`; add `ensure_cap_floor`; call it immediately after `ensure_detector_quota_overlay(cfg)`)
- Modify: `experiments/test_run_scenario.py` (add `TestCapFloor`)
- Test: `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: `patch_overload_detection`, `patch_deploy_rl`, `patch_proxy_burst` from `experiments/topfull_cap_floor.py`. `ssh`, `scp_to`, and `step` already exist in `run_scenario.py`.
- Produces: `write_remote_text(host: str, remote_path: str, content: str) -> None` and `ensure_cap_floor(cfg: dict) -> None`.

`cfg["infra"]["topfull_src_path"]` is the live `.../online_boutique_scripts/src` directory. The three remote paths are:

- `{src}/overload_detection.py`
- `{src}/deploy_rl.py`
- `{src}/proxy/proxy_online_boutique.go`

- [ ] **Step 1: Write the failing test**

Append this class to `experiments/test_run_scenario.py`. `mock`, `SimpleNamespace`, and `run_scenario` are already imported.

```python
class TestCapFloor(unittest.TestCase):
    def test_patches_three_files_then_skips_them(self):
        import topfull_cap_floor as floor
        src = "/home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src"
        cfg = {"infra": {"master_ssh_host": "topfull-master", "topfull_src_path": src}}
        repo = Path(__file__).resolve().parents[1] / "TopFull" / "TopFull_master" / "online_boutique_scripts" / "src"
        files = {
            f"{src}/overload_detection.py": (repo / "overload_detection.py").read_text(encoding="utf-8"),
            f"{src}/deploy_rl.py": (repo / "deploy_rl.py").read_text(encoding="utf-8"),
            f"{src}/proxy/proxy_online_boutique.go": (repo / "proxy" / "proxy_online_boutique.go").read_text(encoding="utf-8"),
        }
        written = {}
        backups = []

        def fake_ssh(host, cmd, check=True):
            self.assertEqual(host, "topfull-master")
            if cmd.startswith("cat "):
                path = cmd[len("cat "):]
                return SimpleNamespace(stdout=files[path], returncode=0)
            if cmd.startswith("cp -n "):
                backups.append(cmd)
                return SimpleNamespace(stdout="", returncode=0)
            raise AssertionError(cmd)

        def fake_write(host, remote_path, content):
            written[remote_path] = content
            files[remote_path] = content

        with mock.patch.object(run_scenario, "ssh", fake_ssh), \
             mock.patch.object(run_scenario, "write_remote_text", fake_write), \
             mock.patch.object(run_scenario, "step", lambda *a, **k: None):
            run_scenario.ensure_cap_floor(cfg)
            self.assertEqual(set(written), set(files))
            self.assertIn(floor.overload_floor_new(), written[f"{src}/overload_detection.py"])
            self.assertIn(floor.deploy_rl_zero_block(), written[f"{src}/deploy_rl.py"])
            self.assertIn(floor.proxy_burst_new(), written[f"{src}/proxy/proxy_online_boutique.go"])
            self.assertEqual(len(backups), 3)
            written.clear()
            run_scenario.ensure_cap_floor(cfg)
            self.assertEqual(written, {})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_run_scenario.py::TestCapFloor -v`

Expected: FAIL with `AttributeError: module 'run_scenario' has no attribute 'ensure_cap_floor'`

- [ ] **Step 3: Install on the hold path**

Add this import next to the other `experiments` imports at the top of `experiments/run_scenario.py` (the file already imports `topfull_cpu_quotas` the same way; follow that import style):

```python
import topfull_cap_floor
```

Add `write_remote_text` immediately after `write_remote_json`:

```python
def write_remote_text(host: str, remote_path: str, content: str) -> None:
    """Write a text file to a remote host with LF line endings."""
    payload = content.replace("\r\n", "\n").replace("\r", "\n")
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
        f.write(payload.encode("utf-8"))
        tmp = f.name
    try:
        scp_to(tmp, host, remote_path)
    finally:
        os.unlink(tmp)
```

Add this function immediately after `ensure_detector_quota_overlay`:

```python
def ensure_cap_floor(cfg: dict) -> None:
    """
    Let every API's admission cap be 0 on the live TopFull tree. Idempotent.
    """
    master = cfg["infra"]["master_ssh_host"]
    src = cfg["infra"]["topfull_src_path"]
    targets = [
        (f"{src}/overload_detection.py", topfull_cap_floor.patch_overload_detection),
        (f"{src}/deploy_rl.py", topfull_cap_floor.patch_deploy_rl),
        (f"{src}/proxy/proxy_online_boutique.go", topfull_cap_floor.patch_proxy_burst),
    ]
    for remote, patcher in targets:
        result = ssh(master, f"cat {remote}")
        original = (result.stdout or "").replace("\r\n", "\n").replace("\r", "\n")
        patched = patcher(original)
        if patched == original:
            step(f"cap floor already in {remote}")
            continue
        ssh(master, f"cp -n {remote} {remote}.bak.cap-floor", check=False)
        write_remote_text(master, remote, patched)
        step(f"Patched {remote} for cap floor 0")
```

In the `try` block of the hold, the call sits on the next line after `ensure_detector_quota_overlay(cfg)` and before `apply_per_try_timeout(cfg)`:

```python
        ensure_detector_quota_overlay(cfg)
        ensure_cap_floor(cfg)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest experiments/test_run_scenario.py::TestCapFloor experiments/test_topfull_cap_floor.py -v`

Expected: PASS. The runner test writes three files on the first call and writes nothing on the second.

- [ ] **Step 5: Commit**

```bash
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "$(cat <<'EOF'
feat: install the admission-cap floor of 0 before each hold

EOF
)"
```

## Task 4: Record the floor where the cap is documented

**Files:**
- Modify: `Guides and Info/TOPFULL-THROTTLE-METRICS.md` (one paragraph after the status table, before the sentence that starts `Layers A and B are collected`)
- Modify: `experiments/test_topfull_cap_floor.py` (one test on `TestFloorThreshold`)
- Test: `experiments/test_topfull_cap_floor.py`

**Interfaces:**
- Consumes: the floor value from Task 1. No new functions.
- Produces: the paragraph below, verbatim.

- [ ] **Step 1: Write the failing test**

Add this method to `TestFloorThreshold` in `experiments/test_topfull_cap_floor.py`:

```python
    def test_guide_records_the_cap_floor(self):
        text = (ROOT / "Guides and Info" / "TOPFULL-THROTTLE-METRICS.md").read_text(encoding="utf-8")
        self.assertIn("floors every entry API at 0 req/s", text)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest experiments/test_topfull_cap_floor.py::TestFloorThreshold::test_guide_records_the_cap_floor -v`

Expected: FAIL with `AssertionError` because the guide does not yet contain that sentence.

- [ ] **Step 3: Add the paragraph**

In `Guides and Info/TOPFULL-THROTTLE-METRICS.md`, immediately after the status table (the row that says a live 0 is an empty read) and before `Layers A and B are collected`, insert:

```markdown
**Cap floor.** The live TopFull write path floors every entry API at 0 req/s. The runner installs that rule into master's `overload_detection.py`, `deploy_rl.py`, and `proxy/proxy_online_boutique.go` before the proxy starts. A fresh threshold of 0 in `topfull_throttle.csv` (`threshold_fresh` 1) means that floor is in force: burst is 0, so the limiter rejects every request for that API. The graphs and `analysis_score.py` still treat a fresh 0 as an empty read and do not draw it. A rate written in (0, 1) uses a burst of 1 so the fractional cap can admit. Rate 0 keeps burst 0.
```

Leave the table row unchanged. A fresh 0 is still omitted from the cap line.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest experiments/test_topfull_cap_floor.py experiments/test_run_scenario.py::TestCapFloor -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add "Guides and Info/TOPFULL-THROTTLE-METRICS.md" experiments/test_topfull_cap_floor.py
git commit -m "$(cat <<'EOF'
docs: record the admission-cap floor of 0

EOF
)"
```

---

## Self-review

Spec coverage:

- Implementation commits land on `cap-floor-0`, not on `main` — Task 0. Tasks 1–4 each stop if `git branch --show-current` is not `cap-floor-0`.
- Floor of 0 for every entry API, with no remaining floor of 10 — Task 1 `floor_threshold` and Task 2 `patch_overload_detection`. The inserted block has no per-API branch.
- A written 0 stays a cap. The RL must not reset any API to 10000 because the sum is 0 — Task 2 `patch_deploy_rl` deletes the `zero threshold` branch.
- The RL must not crash on `goodput / 0` — Task 2 ratio block.
- A fractional cap below 1 req/s can admit, and 0 rejects every request, for every API — Task 2 `patch_proxy_burst` on `changeLimitAbs`.
- The next hold actually runs the patched files — Task 3, called before the proxy and `deploy_rl.py` start.
- Someone reading the cap docs can see the new floor, and can see that the graph still hides a fresh 0 — Task 4.

Placeholder scan: no TBD, no "handle edge cases", no "similar to Task N". Each rewrite's old and new text is in Task 1 and applied in Task 2.

Type consistency: `floor_threshold`, `goodput_ratio`, `overload_floor_new`, `deploy_rl_zero_block`, `deploy_rl_ratio_block`, `proxy_burst_new`, `patch_overload_detection`, `patch_deploy_rl`, `patch_proxy_burst`, `write_remote_text`, and `ensure_cap_floor` use the same names in the task that defines them and in the later tasks. `MIN_THRESHOLD` is the only copy of the floor value.

Out of scope, on purpose: drawing a fresh 0 on the cap line. That rule also hides empty reads. Changing it is a separate measurement change.
