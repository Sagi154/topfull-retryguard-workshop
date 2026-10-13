# S3 and S4 mode matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These forty holds share one cluster. Run the hold tasks in order in one session. Do not run two holds at once.

**Goal:** Run the locked S3, S4A-constrained, S4A-unconstrained, and S4B configs twice each for five controller cells: RetryGuard-only normal, both-on normal, TopFull-only, RetryGuard-only burst, and both-on burst.

**Architecture:** The twenty YAMLs under `experiments/configs/final_configs/` are already the locked cells, each at `run_number: 1`. Each cell is launched twice, back to back, from branch `s3-s4-mode-matrix` cut from `main`. The first launch uses the `run1` folder already written in the file. After that folder is pulled, `bump_final_slot.py` advances that file to `run2` for the second launch, then to `run3` so the next campaign cannot overwrite either folder on master. Results land in `experiments/results/final results/`. One analysis guide is written per scenario. The three VMs stay RUNNING.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, PowerShell, `ssh`, `gcloud`. No controller changes.

## Global Constraints

- Branch is `s3-s4-mode-matrix`, created from `main`. Stay on it. Do not merge. Do not push.
- Forty holds, 600 s each, `spawn_rate` 50. Wall clock is about 10–11 hours (about 12 minutes of startup plus load, then a 120 s cool-off). One hold at a time.
- Cell order inside each scenario: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. Two launches of one cell, then the next cell. Scenario order: S3, S4A constrained, S4A unconstrained, S4B.
- Locked RetryGuard values, already in the YAMLs: `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, `reenable_rejection` 0.25. Burst adds `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20. Normal mode omits those three keys.
- S3 mix `175 / 30 / 70 / 90 / 5`, `checkoutservice` 200 m, Paper-C1 on every other row. S4A mix `10 / 10 / 10 / 600 / 5`; constrained sets `productcatalogservice` to 50 m; unconstrained leaves catalog at 800 m. S4B mix `175 / 30 / 70 / 90 / 5`, `emailservice` 50 m. Paper-C1 is [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md).
- The only YAML edits on those twenty files are `run_number` and `log_folder`, and only through `python experiments/bump_final_slot.py <file>`, and only after that launch's pull. Pull uses the YAML before the bump. `tf_only` files contain the three burst keys and keep them; RetryGuard is off, so their result directory is `normal`.
- Leave `experiments/configs/scenario_*.yaml` and the S1 and S2 files under `final_configs/` at their current slots. Do not run `experiments/make_final_configs.py` (it rewrites every copy back to `run1`). Do not use `run_all_scenarios.py`.
- A failed gate keeps its folder. Replay that launch once from a copy under `experiments/configs/replays/` whose `log_folder` has an `_r2` suffix. Then bump the canonical file once. Do not replay a second time. A finished hold with zero `ON→OFF` lines still passes. Toggle count is recorded and is not a gate.
- Cool-off is 120 s, starting when `run_scenario.py` exits. Pull and the gate happen during that wait. Checkout and recommendations stay up. `restart_before_hold` stays absent.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`), Linux user `idozacharia`, project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. The `networks-workshop` project stays stopped. Do not hardcode a public IP.
- Paper-C1 replica pin for the whole campaign: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `sidecar.istio.io/proxyCPU=90m`, `proxyCPULimit` unset. Restore once at the end to frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset. Leave the three VMs RUNNING.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`).
- Commands run from `c:\Users\idoza\topfull-retryguard-workshop`.

## File Structure

- Create: `experiments/bump_final_slot.py` — advances `run_number` and the trailing `runN` in `log_folder` by 1. Refuses S1, S2, and any path outside `final_configs/`.
- Create: `experiments/test_bump_final_slot.py` — unit tests for that helper.
- Create: `experiments/s3s4_mode_matrix_gate.py` — prints the collector gate for one pulled folder. `start_problems()` is the pure check.
- Create: `experiments/test_s3s4_mode_matrix_gate.py` — unit tests for `start_problems`.
- Modify: `experiments/test_run_scenario.py` `TestFinalConfigs.test_mix_cpu_and_controllers` — `log_folder` must be `final_<prefix>_<variant>_run<run_number>`. The pin at `run1` goes away so the campaign can advance slots.
- Create during the runs: `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md` — one line per launch, including a failed launch and its single replay.
- Create after each scenario's pulls: `Guides and Info/2026-10-13-s3-mode-matrix-abc.md`, `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`, `Guides and Info/2026-10-13-s4a-unconstrained-mode-matrix-abc.md`, `Guides and Info/2026-10-13-s4b-mode-matrix-abc.md`.
- Modify after the VMs are confirmed still RUNNING: `STATUS.md` (one Done bullet; next-free slots for the four touched groups become 3) and `AGENTS.md` §4 (replace the three Latest lines).
- Modify during the runs, slots only: the twenty YAMLs listed in the hold tables. After the campaign each of those files is `run_number: 3` and `log_folder: final_<prefix>_<variant>_run3`.
- Read-only: `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/retryguard.py`.
- Create only if a gate fails: `experiments/configs/replays/<log_folder>_r2.yaml`.

`run_scenario.py` `final_results_local_dir` sends a config to `experiments/results/final results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. Scenario directories: `S3_targeted_bottleneck`, `S4A_topology_position` (both S4A variants; `log_folder` tells them apart), `S4B_topology_position`. Mode is `burst` only when RetryGuard is on and `burst_rpr` is set. TopFull-only is `normal`.

| # | Scenario | Cell | YAML | `log_folder` rep 1, then rep 2 | Kind | TF |
| --- | --- | --- | --- | --- | --- | --- |
| 1–2 | S3 | rg only normal | `experiments/configs/final_configs/3/s3_rg_only_normal.yaml` | `final_s3_rg_only_normal_run1`, `_run2` | `normal` | `off` |
| 3–4 | S3 | both normal | `experiments/configs/final_configs/3/s3_both_normal.yaml` | `final_s3_both_normal_run1`, `_run2` | `normal` | `on` |
| 5–6 | S3 | tf only | `experiments/configs/final_configs/3/s3_tf_only.yaml` | `final_s3_tf_only_run1`, `_run2` | `tf` | `on` |
| 7–8 | S3 | rg only burst | `experiments/configs/final_configs/3/s3_rg_only_burst.yaml` | `final_s3_rg_only_burst_run1`, `_run2` | `burst20` | `off` |
| 9–10 | S3 | both burst | `experiments/configs/final_configs/3/s3_both_burst.yaml` | `final_s3_both_burst_run1`, `_run2` | `burst20` | `on` |
| 11–12 | S4A constrained | rg only normal | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml` | `final_4a_constrained_rg_only_normal_run1`, `_run2` | `normal` | `off` |
| 13–14 | S4A constrained | both normal | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_normal.yaml` | `final_4a_constrained_both_normal_run1`, `_run2` | `normal` | `on` |
| 15–16 | S4A constrained | tf only | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_tf_only.yaml` | `final_4a_constrained_tf_only_run1`, `_run2` | `tf` | `on` |
| 17–18 | S4A constrained | rg only burst | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_burst.yaml` | `final_4a_constrained_rg_only_burst_run1`, `_run2` | `burst20` | `off` |
| 19–20 | S4A constrained | both burst | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_burst.yaml` | `final_4a_constrained_both_burst_run1`, `_run2` | `burst20` | `on` |
| 21–22 | S4A unconstrained | rg only normal | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml` | `final_4a_unconstrained_rg_only_normal_run1`, `_run2` | `normal` | `off` |
| 23–24 | S4A unconstrained | both normal | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_normal.yaml` | `final_4a_unconstrained_both_normal_run1`, `_run2` | `normal` | `on` |
| 25–26 | S4A unconstrained | tf only | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_tf_only.yaml` | `final_4a_unconstrained_tf_only_run1`, `_run2` | `tf` | `on` |
| 27–28 | S4A unconstrained | rg only burst | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_burst.yaml` | `final_4a_unconstrained_rg_only_burst_run1`, `_run2` | `burst20` | `off` |
| 29–30 | S4A unconstrained | both burst | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_burst.yaml` | `final_4a_unconstrained_both_burst_run1`, `_run2` | `burst20` | `on` |
| 31–32 | S4B | rg only normal | `experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml` | `final_4b_rg_only_normal_run1`, `_run2` | `normal` | `off` |
| 33–34 | S4B | both normal | `experiments/configs/final_configs/4/4b/4b_both_normal.yaml` | `final_4b_both_normal_run1`, `_run2` | `normal` | `on` |
| 35–36 | S4B | tf only | `experiments/configs/final_configs/4/4b/4b_tf_only.yaml` | `final_4b_tf_only_run1`, `_run2` | `tf` | `on` |
| 37–38 | S4B | rg only burst | `experiments/configs/final_configs/4/4b/4b_rg_only_burst.yaml` | `final_4b_rg_only_burst_run1`, `_run2` | `burst20` | `off` |
| 39–40 | S4B | both burst | `experiments/configs/final_configs/4/4b/4b_both_burst.yaml` | `final_4b_both_burst_run1`, `_run2` | `burst20` | `on` |

Result roots:

- S3: `experiments/results/final results/S3_targeted_bottleneck_<normal|burst>/<rg_only|both|tf_only>/`
- S4A (constrained and unconstrained): `experiments/results/final results/S4A_topology_position_<normal|burst>/<rg_only|both|tf_only>/`
- S4B: `experiments/results/final results/S4B_topology_position_<normal|burst>/<rg_only|both|tf_only>/`

---

### Task 1: Cut the branch from main

**Files:** none.

**Interfaces:**
- Consumes: local `main` at `0f50fb9` (`Update RetryGuard parameters and configuration descriptions`). That commit is the branch point. It only changes RetryGuard fallback defaults and the RetryGuard-only YAML descriptions. The locked keys, mixes, CPU rows, and `run1` slots are already the ones this plan launches.
- Produces: branch `s3-s4-mode-matrix` whose first parent is `0f50fb9`. Later tasks commit only on this branch.

- [ ] **Step 1: Confirm main is `0f50fb9` and the tree is otherwise clean**

```powershell
git branch --show-current
git status --short
git log -1 --oneline
```

Expected: branch `main`, and `git log -1` is `0f50fb9 Update RetryGuard parameters and configuration descriptions`. `git status --short` is empty, or the only path is `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix.md` (staged or untracked). Any other path, or any other HEAD, means stop. Do not branch from `1c2532b`.

- [ ] **Step 2: Create the branch at that commit**

```powershell
git checkout -b s3-s4-mode-matrix
git branch --show-current
git rev-parse --short HEAD
```

Expected: branch `s3-s4-mode-matrix`, HEAD `0f50fb9`. Do not commit yet.

---

### Task 2: Let final_configs slots advance

**Files:**
- Create: `experiments/bump_final_slot.py`
- Create: `experiments/test_bump_final_slot.py`
- Modify: `experiments/test_run_scenario.py:1203-1206`
- Test: `experiments/test_bump_final_slot.py`, `experiments/test_run_scenario.py`

**Interfaces:**
- Consumes: a UTF-8 YAML whose `run_number` is an integer and whose `log_folder` matches `^final_.+_run<digits>$`.
- Produces: `bump_text(text: str) -> str` and `bump_file(path: Path) -> int` (returns the new run number). CLI: `python experiments/bump_final_slot.py <yaml>` prints `<path>: run N -> N+1` and rewrites the file in place, preserving its newline bytes. Hold tasks call this only after a pull.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_bump_final_slot.py`:

```python
"""Slot bump for the S3/S4 mode-matrix YAMLs.

Run:
    python experiments/test_bump_final_slot.py
"""
import tempfile
import unittest
from pathlib import Path

import bump_final_slot


SAMPLE = """\
run_number: 1
log_folder: final_s3_rg_only_normal_run1
"""


class TestBumpText(unittest.TestCase):
    def test_advances_run_number_and_log_folder(self):
        out = bump_final_slot.bump_text(SAMPLE)
        self.assertIn("run_number: 2\n", out)
        self.assertIn("log_folder: final_s3_rg_only_normal_run2\n", out)
        self.assertNotIn("run1", out)

    def test_second_bump_reaches_run3(self):
        out = bump_final_slot.bump_text(bump_final_slot.bump_text(SAMPLE))
        self.assertIn("run_number: 3\n", out)
        self.assertIn("log_folder: final_s3_rg_only_normal_run3\n", out)

    def test_keeps_crlf(self):
        src = SAMPLE.replace("\n", "\r\n")
        out = bump_final_slot.bump_text(src)
        self.assertIn("\r\n", out)
        self.assertNotIn("\n\n", out.replace("\r\n", ""))

    def test_refuses_replay_suffix(self):
        src = SAMPLE.replace("run1", "run1_r2")
        with self.assertRaises(SystemExit):
            bump_final_slot.bump_text(src)


class TestBumpFileGuard(unittest.TestCase):
    def test_file_keeps_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "3" / "s3_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            path.write_bytes(SAMPLE.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\n\n", raw.replace(b"\r\n", b""))
            self.assertIn(b"log_folder: final_s3_rg_only_normal_run2\r\n", raw)

    def test_refuses_s1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "1" / "s1_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(SAMPLE.replace("s3_rg_only_normal", "s1_rg_only_normal"), encoding="utf-8")
            with self.assertRaises(SystemExit):
                bump_final_slot.bump_file(path)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python experiments/test_bump_final_slot.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'bump_final_slot'`.

- [ ] **Step 3: Write the helper**

Create `experiments/bump_final_slot.py`:

```python
"""Advance run_number and log_folder on one S3/S4 final_configs YAML.

The campaign file stays the runner input. Rep 1 uses the run1 name already
in the file. After that folder is pulled, bump to run2 and launch again.
After rep 2 is pulled, bump to run3 so a later hold cannot reuse the name
on master.

    python experiments/bump_final_slot.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_PREFIXES = (
    "s3_",
    "4a_constrained_",
    "4a_unconstrained_",
    "4b_",
)


def _ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def bump_text(text: str) -> str:
    """Advance the two slot lines. The final_configs tree is CRLF; keep each line's ending."""
    lines = text.splitlines(keepends=True)
    current = None
    for line in lines:
        match = re.fullmatch(r"run_number:[ \t]*(\d+)[ \t]*", line.rstrip("\r\n"))
        if match:
            current = int(match.group(1))
            break
    if current is None:
        raise SystemExit("run_number missing")
    nxt = current + 1
    found_folder = False
    out: list[str] = []
    for line in lines:
        ending = _ending(line)
        stripped = line.rstrip("\r\n")
        if re.fullmatch(r"run_number:[ \t]*\d+[ \t]*", stripped):
            out.append(f"run_number: {nxt}{ending}")
            continue
        match = re.fullmatch(r"log_folder:[ \t]*(\S+_run)\d+[ \t]*", stripped)
        if match:
            out.append(f"log_folder: {match.group(1)}{nxt}{ending}")
            found_folder = True
            continue
        out.append(line)
    if not found_folder:
        raise SystemExit("log_folder missing or not final_*_runN")
    return "".join(out)


def bump_file(path: Path) -> int:
    resolved = path if path.is_absolute() else Path.cwd() / path
    parts = resolved.parts
    if "final_configs" not in parts:
        raise SystemExit(f"refusing {path}: not under final_configs")
    if not any(path.name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise SystemExit(f"refusing {path}: not an S3/S4 campaign file")
    original = path.read_bytes().decode("utf-8")
    updated = bump_text(original)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
    match = re.search(r"(?m)^run_number:[ \t]*(\d+)[ \t]*\r?$", updated)
    return int(match.group(1))


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit("usage: python experiments/bump_final_slot.py <yaml>")
    path = Path(argv[1])
    new_run = bump_file(path)
    print(f"{path}: run {new_run - 1} -> {new_run}")


if __name__ == "__main__":
    main(sys.argv)
```

The test file imports `bump_final_slot` from `experiments/` because `python experiments/test_bump_final_slot.py` puts `experiments/` on `sys.path[0]`.

- [ ] **Step 4: Relax the run1 pin in TestFinalConfigs**

In `experiments/test_run_scenario.py`, replace:

```python
            self.assertEqual(cfg["run_number"], 1, msg=path.name)
            self.assertEqual(
                cfg["log_folder"], f"final_{prefix}_{variant}_run1", msg=path.name,
            )
```

with:

```python
            self.assertIsInstance(cfg["run_number"], int, msg=path.name)
            self.assertGreaterEqual(cfg["run_number"], 1, msg=path.name)
            self.assertEqual(
                cfg["log_folder"],
                f"final_{prefix}_{variant}_run{cfg['run_number']}",
                msg=path.name,
            )
```

- [ ] **Step 5: Run the tests**

```powershell
python experiments/test_bump_final_slot.py
python experiments/test_run_scenario.py TestFinalConfigs
```

Expected: both end `OK`. `TestFinalConfigs` still sees thirty files at `run1`.

- [ ] **Step 6: Commit**

```powershell
git add experiments/bump_final_slot.py experiments/test_bump_final_slot.py experiments/test_run_scenario.py docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix.md
git commit -m @"
Let S3/S4 final_configs slots advance past run 1.

The mode matrix launches each locked cell twice and must not reuse log_folder on master.
"@
git status --short
```

Expected: the commit succeeds on `s3-s4-mode-matrix`. Do not push.

---

### Task 3: Gate printer

**Files:**
- Create: `experiments/s3s4_mode_matrix_gate.py`
- Create: `experiments/test_s3s4_mode_matrix_gate.py`
- Test: `experiments/test_s3s4_mode_matrix_gate.py`

**Interfaces:**
- Consumes: a pulled run directory and two arguments, `kind` (`normal`, `burst20`, or `tf`) and `tf` (`off` or `on`).
- Produces: `start_problems(start: str, kind: str) -> list[str]`. CLI prints `locust_rows`, `start_missing`, `patch_fail`, replica counts, and `live5s_*` counts. Exit code is 0 when the files can be read; a missing file prints `missing=<name>` and exits 0. The hold task decides PASS or INVALID from the rules below. Later hold tasks call `python experiments/s3s4_mode_matrix_gate.py <folder> <kind> <tf>`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_s3s4_mode_matrix_gate.py`:

```python
"""START-line checks for the S3/S4 mode matrix.

Run:
    python experiments/test_s3s4_mode_matrix_gate.py
"""
import unittest

import s3s4_mode_matrix_gate

NORMAL = (
    "2026-10-13T00:00:00Z  START  metric=edge_rpr rpr_threshold=0.40 "
    "rejection_threshold=0.20 reenable_rejection=0.25 "
    "climb_rpr_1_to_2=0.16 climb_rpr_2_to_3=0.32 "
    "climb_interval_seconds=10s sample_interval=1s interval_samples=20s "
    "edges=8 attempts_on=3"
)
BURST = (
    NORMAL
    + " burst_rpr=2.00 burst_window_seconds=5 burst_min_first_attempts=20"
)


class TestStartProblems(unittest.TestCase):
    def test_normal_ok(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems(NORMAL, "normal"), [])

    def test_normal_rejects_burst_keys(self):
        problems = s3s4_mode_matrix_gate.start_problems(BURST, "normal")
        self.assertIn("burst keys present on a normal hold", problems)

    def test_burst20_ok(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems(BURST, "burst20"), [])

    def test_burst20_requires_bar_2(self):
        problems = s3s4_mode_matrix_gate.start_problems(NORMAL, "burst20")
        self.assertIn("burst_rpr=2.00", problems)

    def test_tf_ignores_the_start_line(self):
        self.assertEqual(s3s4_mode_matrix_gate.start_problems("", "tf"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python experiments/test_s3s4_mode_matrix_gate.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 's3s4_mode_matrix_gate'`.

- [ ] **Step 3: Write the gate**

Create `experiments/s3s4_mode_matrix_gate.py`:

```python
"""Print collector facts for one pulled S3/S4 mode-matrix folder.

    python experiments/s3s4_mode_matrix_gate.py <folder> <normal|burst20|tf> <off|on>
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

NEED = (
    "metric=edge_rpr",
    "rpr_threshold=0.40",
    "rejection_threshold=0.20",
    "reenable_rejection=0.25",
    "climb_rpr_1_to_2=0.16",
    "climb_rpr_2_to_3=0.32",
    "climb_interval_seconds=10s",
    "sample_interval=1s",
    "interval_samples=20s",
)
BURST_NEED = (
    "burst_rpr=2.00",
    "burst_window_seconds=5",
    "burst_min_first_attempts=20",
)


def start_problems(start: str, kind: str) -> list[str]:
    if kind == "tf":
        return []
    missing = [token for token in NEED if token not in start]
    if kind == "normal" and "burst_rpr=" in start:
        missing.append("burst keys present on a normal hold")
    if kind == "burst20":
        missing.extend(token for token in BURST_NEED if token not in start)
    return missing


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise SystemExit(
            "usage: python experiments/s3s4_mode_matrix_gate.py "
            "<folder> <normal|burst20|tf> <off|on>"
        )
    root = Path(argv[1])
    kind = argv[2]
    if kind not in ("normal", "burst20", "tf"):
        raise SystemExit(f"kind must be normal, burst20, or tf, got {kind}")
    total_path = root / "total.csv"
    if not total_path.is_file():
        print("missing=total.csv")
        return
    print(f"locust_rows={len(_rows(total_path))}")
    log_path = root / "retryguard.log"
    if kind == "tf":
        print("start_missing=n/a")
        print("burst_observe=n/a")
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    elif not log_path.is_file():
        print("missing=retryguard.log")
        return
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        start = next((line for line in log_text.splitlines() if " START " in line), "")
        print(start)
        problems = start_problems(start, kind)
        print("start_missing=" + (",".join(problems) if problems else "none"))
        if kind == "burst20":
            print("burst_observe=" + ("yes" if "burst_rpr5=" in log_text else "no"))
        else:
            print("burst_observe=n/a")
    print("patch_fail=" + ("yes" if "PATCH_FAIL" in log_text or "Traceback" in log_text else "no"))
    usage_path = root / "resource_usage.csv"
    throttle_path = root / "topfull_throttle.csv"
    if not usage_path.is_file():
        print("missing=resource_usage.csv")
        return
    if not throttle_path.is_file():
        print("missing=topfull_throttle.csv")
        return
    usage = _rows(usage_path)
    frontend = [row for row in usage if row["service"] == "frontend"]
    catalog = [row for row in usage if row["service"] == "productcatalogservice"]
    print(f"frontend_4={sum(row['replica_count'] == '4' for row in frontend)}/{len(frontend)}")
    print(f"catalog_1={sum(row['replica_count'] == '1' for row in catalog)}/{len(catalog)}")
    throttle = _rows(throttle_path)
    live = [row for row in throttle if row["threshold_fresh"] == "1"]

    def as_float(row: dict[str, str]) -> float:
        return float(row["threshold"])

    n10000 = sum(as_float(row) == 10000 for row in live)
    nzero = sum(as_float(row) == 0 for row in live)
    ncaps = sum(0 < as_float(row) < 10000 for row in live)
    other = len(live) - n10000 - nzero - ncaps
    print(f"live5s_10000={n10000} live5s_caps={ncaps} live5s_zero={nzero} other={other}")


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run the tests**

```powershell
python experiments/test_s3s4_mode_matrix_gate.py
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```powershell
git add experiments/s3s4_mode_matrix_gate.py experiments/test_s3s4_mode_matrix_gate.py
git commit -m @"
Add the S3/S4 mode-matrix collector gate.

Hold tasks read its printed facts and keep a failed folder for one replay.
"@
```

Expected: the commit succeeds. Do not push.

---

### Task 4: Bring the cluster up and pin Paper-C1 replicas

**Files:** none.

**Interfaces:**
- Consumes: SSH aliases and project `project-76deda76-55f1-42d2-abb`.
- Produces: three VMs `RUNNING`, `kubectl get nodes` Ready, frontend HPA 4/4, catalog HPA 1/1, sidecar `90m` with `proxyCPULimit` empty, four frontend pods `2/2`. Hold tasks assume this pin is still in place.

- [ ] **Step 1: List the three VMs**

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected names: `topfull-master`, `topfull-worker-1`, `topfull-load`. If a name from `networks-workshop` appears, stop. If all three are `RUNNING`, go to Step 3. If any is `TERMINATED`, start all three:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

For each previous `HostName` in `~/.ssh/config` and each new public IP, run `ssh-keygen -R <ip>`, then set the three `HostName` lines to the new addresses. `User` stays `idozacharia`.

- [ ] **Step 2: Confirm SSH**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-load "hostname; whoami"
```

Expected: hostname matches the alias and `whoami` is `idozacharia`.

- [ ] **Step 3: Confirm the API server**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`, Online Boutique pods `2/2`, VirtualServices present. `connection to localhost:8080 refused` means `idozacharia` has no `~/.kube/config`. Copy it from the kubeadm user and retry. Wait up to five minutes for `Ready` after a start. Do not launch a hold before that.

- [ ] **Step 4: Confirm the forty result folders are absent**

```powershell
$names = @(
  "S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1",
  "S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run2",
  "S3_targeted_bottleneck_normal/both/final_s3_both_normal_run1",
  "S3_targeted_bottleneck_normal/both/final_s3_both_normal_run2",
  "S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run1",
  "S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run2",
  "S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run1",
  "S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run2",
  "S3_targeted_bottleneck_burst/both/final_s3_both_burst_run1",
  "S3_targeted_bottleneck_burst/both/final_s3_both_burst_run2",
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1",
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2",
  "S4A_topology_position_normal/both/final_4a_constrained_both_normal_run1",
  "S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2",
  "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1",
  "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2",
  "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1",
  "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2",
  "S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1",
  "S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2",
  "S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1",
  "S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2",
  "S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1",
  "S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2",
  "S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1",
  "S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2",
  "S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1",
  "S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run2",
  "S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1",
  "S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2",
  "S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1",
  "S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run2",
  "S4B_topology_position_normal/both/final_4b_both_normal_run1",
  "S4B_topology_position_normal/both/final_4b_both_normal_run2",
  "S4B_topology_position_normal/tf_only/final_4b_tf_only_run1",
  "S4B_topology_position_normal/tf_only/final_4b_tf_only_run2",
  "S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1",
  "S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run2",
  "S4B_topology_position_burst/both/final_4b_both_burst_run1",
  "S4B_topology_position_burst/both/final_4b_both_burst_run2"
)
foreach ($n in $names) {
  $p = "experiments/results/final results/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `ABSENT` forty times. An `EXISTS` line means stop and pick a new `log_folder` before any launch.

- [ ] **Step 5: Pin replicas and the frontend sidecar**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"90m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Wait until four frontend pods are `2/2` and one catalog pod is `2/2`:

```powershell
@'
set -e
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  fe=$(kubectl get pods -n default -l app=frontend --no-headers | awk '$2=="2/2" && $3=="Running"' | wc -l)
  cat=$(kubectl get pods -n default -l app=productcatalogservice --no-headers | awk '$2=="2/2" && $3=="Running"' | wc -l)
  echo "frontend_ready=$fe catalog_ready=$cat"
  if [ "$fe" -ge 4 ] && [ "$cat" -eq 1 ]; then exit 0; fi
  sleep 15
done
echo "PIN_NOT_READY"
exit 1
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Then confirm the spec:

```powershell
@'
kubectl get hpa frontend-hpa productcatalogservice-hpa -n default
kubectl get deployment frontend -n default -o jsonpath="{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}{\"\n\"}{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}{\"\n\"}"
kubectl get pods -n default -l app=frontend --no-headers
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: frontend HPA `4/4`, catalog HPA `1/1`, annotation `90m`, `proxyCPULimit` empty, four frontend pods `2/2`. `PIN_NOT_READY` means stop. Do not start hold 1.

---

### Task 5: S3, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/3/s3_*.yaml` files, slots only, via `bump_final_slot.py`
- Create: `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md`
- Create: `Guides and Info/2026-10-13-s3-mode-matrix-abc.md`
- Create during pulls: ten folders under `experiments/results/final results/S3_targeted_bottleneck_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 4, `bump_final_slot.py`, and `s3s4_mode_matrix_gate.py`.
- Produces: ten pulled folders (`run1` and `run2` for each of the five S3 cells), five YAMLs sitting at `run_number: 3`, ten run-log lines, and the S3 guide. Task 6 starts only after the cool-off from hold 10.

Launches, in order. Rep 1 uses the `run1` name already in the file. Rep 2 uses `run2` after the bump.

| Hold | YAML | Kind | TF | Folder after pull |
| --- | --- | --- | --- | --- |
| 1 | `experiments/configs/final_configs/3/s3_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1` |
| 2 | same file after bump | `normal` | `off` | `.../rg_only/final_s3_rg_only_normal_run2` |
| 3 | `experiments/configs/final_configs/3/s3_both_normal.yaml` | `normal` | `on` | `.../both/final_s3_both_normal_run1` |
| 4 | same file after bump | `normal` | `on` | `.../both/final_s3_both_normal_run2` |
| 5 | `experiments/configs/final_configs/3/s3_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_s3_tf_only_run1` |
| 6 | same file after bump | `tf` | `on` | `.../tf_only/final_s3_tf_only_run2` |
| 7 | `experiments/configs/final_configs/3/s3_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run1` |
| 8 | same file after bump | `burst20` | `off` | `.../rg_only/final_s3_rg_only_burst_run2` |
| 9 | `experiments/configs/final_configs/3/s3_both_burst.yaml` | `burst20` | `on` | `.../both/final_s3_both_burst_run1` |
| 10 | same file after bump | `burst20` | `on` | `.../both/final_s3_both_burst_run2` |

Repeat Steps 1–8 for each row. The first command block shows hold 1. Substitute the row's YAML, kind, TF flag, and folder.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear**

Anything other than the two `-clear` lines means repeat Step 1. Do not continue.

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` prints nothing. A reappearing `.csv` or `.log` means a writer is alive. Repeat Step 1.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

One process. Wait until it exits. A 600 s hold plus startup is about 12 minutes. `$exitAt` is the cool-off clock and is set only after a zero exit. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row. On the later rows, pass that row's YAML.

- [ ] **Step 5: Pull, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
```

The printed destination is the folder in the table. Pull before the bump. Then:

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
```

Expected after hold 1: `run 1 -> 2`. Expected after hold 2: `run 2 -> 3`. Same for each file: the first launch of that file bumps 1→2, the second bumps 2→3.

- [ ] **Step 6: Gate**

```powershell
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1" normal off
```

Pass when all of these hold:

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a` and `retryguard.log` is absent (`missing=retryguard.log` is a fail on `normal` and `burst20` only).
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. `catalog_1` equals its denominator. A catalog denominator of 0 is allowed. A catalog sample whose `replica_count` is not 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.

`burst_observe` is recorded. It is not a gate. A burst hold can pass with `burst_observe=no`.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

A failed gate keeps the folder. Copy the YAML that was just launched to `experiments/configs/replays/<log_folder>_r2.yaml`, change only its `log_folder` line to that same name plus `_r2`, and run Steps 1–6 once with that copy. Do not bump the replay copy (`bump_final_slot.py` rejects a name ending in `_r2`). After the replay, bump the canonical file once if Step 5 did not already bump it. Do not replay a second time.

- [ ] **Step 7: Finish the 120 s cool-off**

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 10, leave any remainder for Task 6.

- [ ] **Step 8: Append one line per launch**

Create `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md` on hold 1:

```markdown
# S3 and S4 mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; checkout 200m; users 175/30/70/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines in `retryguard.log`, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch has no log: write `toggles n/a`.

- [ ] **Step 9: Score S3 and write the guide**

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run1" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run2" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run1" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run2" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run1" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run1" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run2" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run1" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run2"
```

Two calls, because `analysis_score.py` labels a folder by its `runN` suffix and then by the parent directory name. `rg_only/1` would collide between `S3_targeted_bottleneck_normal` and `S3_targeted_bottleneck_burst`. Inside each call the labels are unique. If a replay folder replaced a failed launch, pass that `_r2` path instead of the failed folder and say so in the index.

Write `Guides and Info/2026-10-13-s3-mode-matrix-abc.md` from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers in the guide are the `log_folder` names, in the hold-table order, with a bold bar after every pair. Sections, in this order:

1. Setup. 600 s, mix 175 / 30 / 70 / 90 / 5, `spawn_rate` 50, Paper-C1 with checkout 200 m, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, the ten folder paths.
2. Index. One row per launch. Column order is holds 1–10.
3. Edge-mode bars. Paste the scorer's first line and its `Burst bars` line. For `burst_rpr` 2.0 that line is `2.00 / 1.33 / 0.67` at 3 / 2 / 1 attempts. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s.
4. (a) Edge rpr. Three tables, only for edges with a tick above the shed bar or a retry delta. Bold when the file streak is at least 30 seconds.
5. 4a Burst on the four burst folders: the scorer's `(a2) Burst window` line and the burst-vs-normal shed split. The six normal and TopFull-only folders get one sentence that burst mode was off.
6. Rejection beside (a). Bold when a controlled service's streak is at least 30. Frontend and redis-cart stay plain.
7. (b) Detector overloaded fraction. Bold when the share is at least 0.5.
8. (c) Retry volume. Outbound retry delta by target, and inbound resets for all 11 services.
9. RetryGuard toggles. Part 1 is the scorer's count table and timestamp table for each hold that has transition lines. Part 2 is the per-callee table from the template. TopFull-only has no `retryguard.log`: one sentence, no empty table.
10. Locust goodput. Mean `Goodput` while `RPS > 0`, per API.
11. Locust fail rate. Mean `Fail / RPS` while `RPS > 0`, per API.
12. Locust P95. Mean `Latency95` (ms) while `RPS > 0`, per API.
13. Inbound arrival rate. Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service.
14. Inbound sojourn. `Δrq_time_sum_ms / Δrq_time_count`, milliseconds.
15. Share of inbound requests above 500 ms.
16. CPU. Per-pod quota, replica mode, mean millicores, max millicores.
17. Detector max utilization.
18. TopFull live caps. `postcart` and `emptycart` are called out when every live read is no cap.
19. One paragraph per launch: what shed, what climbed, retry volume, `grpc_4`, and which services were detector-hot.
20. Related links: this plan, the template, the (a)/(b)/(c) reading, [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [ADR 0007](../../adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../adr/0008-locked-retryguard-parameters.md), [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md). Earlier S3 holds, including the Set B checkout 200/100 pair, used a different CPU table and are not columns in this guide.

- [ ] **Step 10: Commit the S3 slice**

```powershell
git add experiments/configs/final_configs/3 docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md "Guides and Info/2026-10-13-s3-mode-matrix-abc.md" "experiments/results/final results/S3_targeted_bottleneck_normal" "experiments/results/final results/S3_targeted_bottleneck_burst"
git commit -m @"
Record the S3 mode matrix, two repeats of each cell.

Checkout stays at 200m on Paper-C1, and each cell keeps its own run1 and run2 folder.
"@
```

If a replay YAML was created, `git add experiments/configs/replays` as well. Do not push.

---

### Task 6: S4A constrained, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4a_constrained/4a_constrained_*.yaml` files, slots only
- Modify: `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md` (append)
- Create: `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`
- Create during pulls: ten folders under `experiments/results/final results/S4A_topology_position_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 4, a finished Task 5, and the same two helpers.
- Produces: ten `final_4a_constrained_*` folders, five YAMLs at `run_number: 3`, ten run-log lines, and the constrained guide.

| Hold | YAML | Kind | TF | Folder after pull |
| --- | --- | --- | --- | --- |
| 11 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1` |
| 12 | same file after bump | `normal` | `off` | `.../final_4a_constrained_rg_only_normal_run2` |
| 13 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_normal.yaml` | `normal` | `on` | `.../both/final_4a_constrained_both_normal_run1` |
| 14 | same file after bump | `normal` | `on` | `.../both/final_4a_constrained_both_normal_run2` |
| 15 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4a_constrained_tf_only_run1` |
| 16 | same file after bump | `tf` | `on` | `.../tf_only/final_4a_constrained_tf_only_run2` |
| 17 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1` |
| 18 | same file after bump | `burst20` | `off` | `.../final_4a_constrained_rg_only_burst_run2` |
| 19 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_burst.yaml` | `burst20` | `on` | `.../both/final_4a_constrained_both_burst_run1` |
| 20 | same file after bump | `burst20` | `on` | `.../both/final_4a_constrained_both_burst_run2` |

- [ ] **Step 1: Cool-off from hold 10, then stop leftover writers**

If hold 10's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`. Any other output means repeat Step 1.

- [ ] **Step 3: Clear live logs**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` prints nothing. A reappearing file means repeat Step 1.

- [ ] **Step 4: Run hold 11, then the other nine the same way**

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

Wait for the process. About 12 minutes. A non-zero exit stops the campaign: do not pull and do not bump. Do not start the next row until this process exits.

- [ ] **Step 5: Pull, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
```

Pull first. Hold 11 prints `run 1 -> 2`. Hold 12 prints `run 2 -> 3`. Use the row's YAML for the other cells. Constrained and unconstrained S4A share `scenario_name: topology_position_A`, so both land under `S4A_topology_position_*`. The `log_folder` prefix `final_4a_constrained_` is what separates them.

- [ ] **Step 6: Gate**

```powershell
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1" normal off
```

Pass when all of these hold. Catalog CPU during the hold is 50 m; the replica gate stays `catalog_1`.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a`. `missing=retryguard.log` fails `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. `catalog_1` equals its denominator. A catalog denominator of 0 is allowed. A catalog sample whose `replica_count` is not 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.
- `burst_observe` is recorded and is not a gate.

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

A failed gate keeps the folder. Copy the YAML that was just launched to `experiments/configs/replays/<log_folder>_r2.yaml`, change only its `log_folder` line to that same name plus `_r2`, and run Steps 1–6 once with that copy. Do not bump the replay copy. After the replay, bump the canonical file once if Step 5 did not already bump it. Do not replay a second time.

- [ ] **Step 7: Finish the 120 s cool-off, then the next row**

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 20, leave any remainder for Task 7.

- [ ] **Step 8: Append ten lines to the run log**

Append to `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md`. Do not rewrite the header. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; catalog 50m; users 10/10/10/600/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch writes `toggles n/a`.

- [ ] **Step 9: Score and write the guide**

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1" `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run1" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run2" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run1" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run1" `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run2" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run1" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run2"
```

Write `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md` by following every section in [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), in that file's order. Paste scorer tables. Column headers are the `log_folder` names, holds 11–20, with a bold bar after every pair. Setup: 600 s, mix 10 / 10 / 10 / 600 / 5, `spawn_rate` 50, Paper-C1 with `productcatalogservice` 50 m, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s. Burst bars from the scorer are `2.00 / 1.33 / 0.67`. Earlier S4A holds at 100 m or another mix are named in Related links and are not columns.

- [ ] **Step 10: Commit**

```powershell
git add experiments/configs/final_configs/4/4a_constrained docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md" "experiments/results/final results/S4A_topology_position_normal" "experiments/results/final results/S4A_topology_position_burst"
git commit -m @"
Record the S4A constrained mode matrix, two repeats of each cell.

Catalog stays at 50m, and the unconstrained S4A folders are a later commit.
"@
```

`S4A_topology_position_*` contains only the constrained `log_folder`s at this commit. Do not push.

---

### Task 7: S4A unconstrained, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_*.yaml` files, slots only
- Modify: `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md` (append)
- Create: `Guides and Info/2026-10-13-s4a-unconstrained-mode-matrix-abc.md`
- Create during pulls: ten `final_4a_unconstrained_*` folders beside the constrained ones

**Interfaces:**
- Consumes: the pin, a finished Task 6, and the same helpers.
- Produces: ten unconstrained folders, five YAMLs at `run_number: 3`, ten run-log lines, and the unconstrained guide.

| Hold | YAML | Kind | TF | Folder after pull |
| --- | --- | --- | --- | --- |
| 21 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1` |
| 22 | same file after bump | `normal` | `off` | `.../final_4a_unconstrained_rg_only_normal_run2` |
| 23 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_normal.yaml` | `normal` | `on` | `.../both/final_4a_unconstrained_both_normal_run1` |
| 24 | same file after bump | `normal` | `on` | `.../both/final_4a_unconstrained_both_normal_run2` |
| 25 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4a_unconstrained_tf_only_run1` |
| 26 | same file after bump | `tf` | `on` | `.../tf_only/final_4a_unconstrained_tf_only_run2` |
| 27 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1` |
| 28 | same file after bump | `burst20` | `off` | `.../final_4a_unconstrained_rg_only_burst_run2` |
| 29 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_burst.yaml` | `burst20` | `on` | `.../both/final_4a_unconstrained_both_burst_run1` |
| 30 | same file after bump | `burst20` | `on` | `.../both/final_4a_unconstrained_both_burst_run2` |

- [ ] **Step 1: Cool-off from hold 20, then stop leftover writers**

If hold 20's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`. Any other output means repeat Step 1.

- [ ] **Step 3: Clear live logs**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` prints nothing. A reappearing file means repeat Step 1.

- [ ] **Step 4: Run hold 21, then the other nine**

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

Wait for the process. About 12 minutes. A non-zero exit stops the campaign: do not pull and do not bump. One process.

- [ ] **Step 5: Pull, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
```

Hold 21 prints `run 1 -> 2`. Hold 22 prints `run 2 -> 3`. These folders sit next to `final_4a_constrained_*` in the same variant directory. Do not delete the constrained folders.

- [ ] **Step 6: Gate**

```powershell
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1" normal off
```

Pass when all of these hold. Catalog CPU during the hold is 800 m.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a`. `missing=retryguard.log` fails `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. `catalog_1` equals its denominator. A catalog denominator of 0 is allowed. A catalog sample whose `replica_count` is not 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.
- `burst_observe` is recorded and is not a gate.

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

A failed gate keeps the folder. Copy the YAML that was just launched to `experiments/configs/replays/<log_folder>_r2.yaml`, change only its `log_folder` line to that same name plus `_r2`, and run Steps 1–6 once with that copy. Do not bump the replay copy. After the replay, bump the canonical file once if Step 5 did not already bump it. Do not replay a second time.

- [ ] **Step 7: Cool-off, then the next row**

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 30, leave any remainder for Task 8.

- [ ] **Step 8: Append ten lines**

Append to `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md`. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; catalog 800m; users 10/10/10/600/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch writes `toggles n/a`.

- [ ] **Step 9: Score and write the guide**

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1" `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1" `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run2" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2"
```

Write `Guides and Info/2026-10-13-s4a-unconstrained-mode-matrix-abc.md` by following every section in [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), in that file's order. Paste scorer tables. Column headers are the `log_folder` names, holds 21–30, with a bold bar after every pair. Setup: 600 s, mix 10 / 10 / 10 / 600 / 5, `spawn_rate` 50, plain Paper-C1 (catalog 800 m), frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s. Burst bars from the scorer are `2.00 / 1.33 / 0.67`. The constrained guide is a related link, not a column.

- [ ] **Step 10: Commit**

```powershell
git add experiments/configs/final_configs/4/4a_unconstrained docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4a-unconstrained-mode-matrix-abc.md" "experiments/results/final results/S4A_topology_position_normal" "experiments/results/final results/S4A_topology_position_burst"
git commit -m @"
Record the S4A unconstrained mode matrix, two repeats of each cell.

Plain Paper-C1 catalog at 800m, pulled beside the constrained folders.
"@
```

Do not push.

---

### Task 8: S4B, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4b/4b_*.yaml` files, slots only
- Modify: `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md` (append)
- Create: `Guides and Info/2026-10-13-s4b-mode-matrix-abc.md`
- Create during pulls: ten folders under `experiments/results/final results/S4B_topology_position_<normal|burst>/`

**Interfaces:**
- Consumes: the pin, a finished Task 7, and the same helpers.
- Produces: ten `final_4b_*` folders, five YAMLs at `run_number: 3`, ten run-log lines, and the S4B guide.

| Hold | YAML | Kind | TF | Folder after pull |
| --- | --- | --- | --- | --- |
| 31 | `experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1` |
| 32 | same file after bump | `normal` | `off` | `.../final_4b_rg_only_normal_run2` |
| 33 | `experiments/configs/final_configs/4/4b/4b_both_normal.yaml` | `normal` | `on` | `.../both/final_4b_both_normal_run1` |
| 34 | same file after bump | `normal` | `on` | `.../both/final_4b_both_normal_run2` |
| 35 | `experiments/configs/final_configs/4/4b/4b_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4b_tf_only_run1` |
| 36 | same file after bump | `tf` | `on` | `.../tf_only/final_4b_tf_only_run2` |
| 37 | `experiments/configs/final_configs/4/4b/4b_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1` |
| 38 | same file after bump | `burst20` | `off` | `.../final_4b_rg_only_burst_run2` |
| 39 | `experiments/configs/final_configs/4/4b/4b_both_burst.yaml` | `burst20` | `on` | `.../both/final_4b_both_burst_run1` |
| 40 | same file after bump | `burst20` | `on` | `.../both/final_4b_both_burst_run2` |

- [ ] **Step 1: Cool-off from hold 30, then stop leftover writers**

If hold 30's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`. Any other output means repeat Step 1.

- [ ] **Step 3: Clear live logs**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` prints nothing. A reappearing file means repeat Step 1.

- [ ] **Step 4: Run hold 31, then the other nine**

```powershell
python experiments/run_scenario.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

Wait for the process. About 12 minutes. A non-zero exit stops the campaign: do not pull and do not bump. One process.

- [ ] **Step 5: Pull, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
```

Hold 31 prints `run 1 -> 2`. Hold 32 prints `run 2 -> 3`.

- [ ] **Step 6: Gate**

```powershell
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1" normal off
```

Pass when all of these hold. Email CPU during the hold is 50 m.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a`. `missing=retryguard.log` fails `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. `catalog_1` equals its denominator. A catalog denominator of 0 is allowed. A catalog sample whose `replica_count` is not 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.
- `burst_observe` is recorded and is not a gate.

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

A failed gate keeps the folder. Copy the YAML that was just launched to `experiments/configs/replays/<log_folder>_r2.yaml`, change only its `log_folder` line to that same name plus `_r2`, and run Steps 1–6 once with that copy. Do not bump the replay copy. After the replay, bump the canonical file once if Step 5 did not already bump it. Do not replay a second time.

- [ ] **Step 7: Cool-off between rows**

After holds 31–39:

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 40, go to Step 8. Task 9 does not need a cool-off.

- [ ] **Step 8: Append ten lines**

Append to `docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md`. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; email 50m; users 175/30/70/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch writes `toggles n/a`.

- [ ] **Step 9: Score and write the guide**

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1" `
  "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run2" `
  "experiments/results/final results/S4B_topology_position_normal/both/final_4b_both_normal_run1" `
  "experiments/results/final results/S4B_topology_position_normal/both/final_4b_both_normal_run2" `
  "experiments/results/final results/S4B_topology_position_normal/tf_only/final_4b_tf_only_run1" `
  "experiments/results/final results/S4B_topology_position_normal/tf_only/final_4b_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1" `
  "experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run2" `
  "experiments/results/final results/S4B_topology_position_burst/both/final_4b_both_burst_run1" `
  "experiments/results/final results/S4B_topology_position_burst/both/final_4b_both_burst_run2"
```

Write `Guides and Info/2026-10-13-s4b-mode-matrix-abc.md` by following every section in [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), in that file's order. Paste scorer tables. Column headers are the `log_folder` names, holds 31–40, with a bold bar after every pair. Setup: 600 s, mix 175 / 30 / 70 / 90 / 5, `spawn_rate` 50, Paper-C1 with `emailservice` 50 m, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s. Burst bars from the scorer are `2.00 / 1.33 / 0.67`. `campaign_48/` S4B used paymentservice; name it in Related links and do not add it as a column.

- [ ] **Step 10: Commit**

```powershell
git add experiments/configs/final_configs/4/4b docs/superpowers/plans/2026-10-13-s3-s4-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4b-mode-matrix-abc.md" "experiments/results/final results/S4B_topology_position_normal" "experiments/results/final results/S4B_topology_position_burst"
git commit -m @"
Record the S4B mode matrix, two repeats of each cell.

Email stays at 50m on the S1 mix, with run1 and run2 kept apart.
"@
```

Do not push.

---

### Task 9: Restore the unpinned shape

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 4, and a finished hold 40.
- Produces: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, frontend app 1150 m. The three VMs stay `RUNNING`.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
ssh -o BatchMode=yes -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`.

- [ ] **Step 2: Restore HPA and the sidecar**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":2}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"100m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Confirm:

```powershell
@'
kubectl get hpa frontend-hpa productcatalogservice-hpa -n default
kubectl get deployment frontend -n default -o jsonpath="{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}{\"\n\"}{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}{\"\n\"}"
kubectl get deployment frontend checkoutservice productcatalogservice emailservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.template.spec.containers[0].resources.limits.cpu}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar annotation `100m` with `proxyCPULimit` absent, app CPU limits frontend `1150m`, checkout `800m`, catalog `800m`, email `120m`. The runner restores Paper-C1 after each hold. If a limit is still off that table, patch that deployment's server container requests and limits to the Paper-C1 value and wait for its rollout.

- [ ] **Step 3: Leave the VMs RUNNING**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are `RUNNING`. Do not stop them.

---

### Task 10: STATUS, AGENTS, and the slot check

**Files:**
- Modify: `STATUS.md` Done (one bullet) and the four Next free slots lines for groups 3, 4a_unconstrained, 4a_constrained, and 4b
- Modify: `AGENTS.md` §4, the three Latest lines
- Test: `experiments/test_run_scenario.py` `TestFinalConfigs`, `experiments/test_bump_final_slot.py`

**Interfaces:**
- Consumes: the run log, the four guides, and twenty YAMLs at `run_number: 3`.
- Produces: STATUS and AGENTS describing this campaign. S1 and S2 final_configs stay at run 1. Historical `scenario_*.yaml` slots stay as they are.

- [ ] **Step 1: Confirm the twenty slots**

```powershell
python -c @"
import yaml
from pathlib import Path
root = Path('experiments/configs/final_configs')
touched = list(root.joinpath('3').glob('s3_*.yaml'))
touched += list(root.joinpath('4').rglob('4a_*.yaml'))
touched += list(root.joinpath('4/4b').glob('4b_*.yaml'))
assert len(touched) == 20, len(touched)
for path in touched:
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert cfg['run_number'] == 3, path
    assert cfg['log_folder'].endswith('_run3'), path
print('twenty files at run 3')
"@
python experiments/test_run_scenario.py TestFinalConfigs
python experiments/test_bump_final_slot.py
```

Expected: `twenty files at run 3`, then both test files `OK`. S1 and S2 files are still `run1`, which `TestFinalConfigs` allows.

- [ ] **Step 2: Update Next free slots**

In `STATUS.md`, the four lines for `final_configs/3/`, `4/4a_unconstrained/`, `4/4a_constrained/`, and `4/4b/` change their trailing slot from `1` to `3`. The `final_configs/1/` and `final_configs/2/` lines stay at `1`. The historical `scenario_*.yaml` list stays as it is.

- [ ] **Step 3: Append one Done bullet and replace the three Latest lines**

Append one bullet under Done in `STATUS.md`. Name the forty `log_folder` values, which gates passed, Locust row counts, and where the run log and the four guides are. Say the twenty touched YAMLs were left at run 3, S1 and S2 final_configs stayed at run 1, the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, and the three VMs were left **RUNNING**.

Replace the three Latest lines in `AGENTS.md` §4. Do not append a fourth. The three lines are: this matrix (branch, forty holds, result root, slots at run 3); the pass/fail counts taken from the run log; the restored cluster and RUNNING VMs. Keep the Still open list. Add one sentence there that this matrix is the first locked S3/S4A/S4B set under `final results/` and that earlier S3/S4 folders are not comparable.

- [ ] **Step 4: Commit**

```powershell
git add STATUS.md AGENTS.md
git commit -m @"
Record the S3/S4 mode-matrix slots and the restored cluster.

The twenty campaign YAMLs sit at run 3, and the three VMs were left running.
"@
git status --short
git branch --show-current
```

Expected: branch `s3-s4-mode-matrix`, working tree clean. Do not push.
