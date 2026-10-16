# Analysis Runs (60 holds into `analysis_runs_results`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run 60 holds (6 scenario configs x 5 controller variants x 2 repeats) and pull every one into a new folder, `experiments/results/analysis_runs_results/`, which has the same structure as `experiments/results/final results/`.

**Architecture:** **Project rule (user, 2026-10-16): every new run from here on is pulled to `experiments/results/analysis_runs_results/`, not just these 60.** The root is the constant `RESULTS_ROOT` in `experiments/run_scenario.py` (`final_results_local_dir()` uses it), so every config, including the old ones, pulls there. This change is already made in the `main` working tree together with the AGENTS.md / `final_configs/README.md` wording and the updated tests; Task 1 commits it on `main` before branching. A generator script copies the locked `final_configs/` YAMLs into `experiments/configs/analysis_runs/` and gives each copy a unique `log_folder` (so nothing collides on master). The holds are then run one at a time with the existing runbook (AGENTS.md section 6).

**Tech Stack:** Python 3 (`unittest`, `pyyaml`), `run_scenario.py` / `pull_results.py` / `analysis_score.py` / `topfull_health.py`, OpenSSH aliases `topfull-master|worker-1|load`, git worktree.

## Global Constraints

- All work happens on a new branch `analysis-runs-results`, cut from `main`, in a separate worktree at `.worktrees/analysis-runs-results` (`.worktrees/` is already git-ignored). Do not touch `main`'s working tree.
- **Commit and push after every finished task and every finished run (user, 2026-10-16).** This is required. From the worktree, on `analysis-runs-results`: when a task's last step is done, commit that task's files and push with `git push -u origin HEAD`. When a hold finishes (P6), commit the pulled folder and the log line, then push that commit before the next hold starts. A push that does not exit 0 is not done: retry it. Do not start the next task or the next hold until the push succeeds. Push only this branch. Do not push `main`. A task that changes no files (Task 4) has no new commit; still push any commits that are not on the remote before the next task. A hold that aborted before finishing is not committed and not pushed (P3). Tasks 2 and 3 were committed locally before this rule; push them with the commit that adds this rule, before Task 4.
- Use the locked configs in `experiments/configs/final_configs/` as the source. Do not edit them. Do not change load mixes, Paper-C1 CPU table, constrained rows, or the locked RetryGuard parameters (AGENTS.md section 5).
- Results go to `experiments/results/analysis_runs_results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. This holds for every new run in the project from 2026-10-16, not only this matrix. `final results/` and `campaign_48/` are closed and never a target.
- SSH only through the aliases `topfull-master`, `topfull-worker-1`, `topfull-load`. Never hardcode IPs. SSH user stays `idozacharia`.
- Cool-off between holds is **120 s**, counted from when `run_scenario.py` exits. Do the leftover-writer check (AGENTS.md section 6, steps 1-5) before every hold.
- After every hold run `python experiments/analysis_score.py <run_dir>` and `python experiments/topfull_health.py "<run_dir>"` (throttle table + `health:` line). Any flag (throttle FLAGGED, PROXY FD, RL STALL) means the hold is not clean. Record the flag in the log and keep going. Never pause for a flag and never re-run a finished hold: the user decides after all 60 are done. Exception (user, 2026-10-16): a hold that aborted or failed before finishing may be re-run in the same slot (Task 5, P3).
- Repeat slots are `run1` and `run2` only. A flagged hold does not get a `run3` unless the user decides so.
- Do not stop the VMs at the end unless the user asks.
- Work run from the worktree directory, so relative `experiments/results/...` paths resolve inside it.

## Decisions confirmed by the user (2026-10-16)

1. **S2 and S3 are the locked scenarios as they are.** There is no "S2 constrained" or "S3 constrained" variant. S2 is plain Paper-C1; S3 carries its locked checkout 200m row. Only S4A has two forms (constrained and unconstrained).
2. **TopFull-only runs once per repeat.** One `tf_only` YAML per scenario (mode folder `normal`). Five variants per scenario: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`.
3. **Flag, never pause, never re-run a finished hold.** A flagged hold (throttle FLAGGED, PROXY FD, RL STALL) is recorded in the log and the matrix continues. The agent does not re-run any finished hold. A hold that aborted or failed before finishing may be re-run in the same slot (user, 2026-10-16). The user decides how to treat flags, and any re-run, after all 60 are done. The last S3 tf_only hold ended `not_clean` (`RL STALL`), so some flags are expected.
4. **Commit and push after every finished task and every finished run.** Each task ends with a commit of that task's files and a `git push` of `analysis-runs-results`. Each finished hold ends the same way (P6), before the next hold. A failed push blocks the next task and the next hold.

## Run matrix (60 holds)

| Group | Source dir (`final_configs/`) | Prefix | Duration | Mode folders |
|---|---|---|---|---|
| `s1` | `1/` | `s1` | 5 min | `S1_normal_operation_{normal,burst}` |
| `s2` | `2/` | `s2` | 10 min | `S2_sustained_overload_{normal,burst}` |
| `s3` | `3/` | `s3` | 10 min | `S3_targeted_bottleneck_{normal,burst}` |
| `s4a_constrained` | `4/4a_constrained/` | `4a_constrained` | 10 min | `S4A_topology_position_{normal,burst}` |
| `s4a_unconstrained` | `4/4a_unconstrained/` | `4a_unconstrained` | 10 min | `S4A_topology_position_{normal,burst}` |
| `s4b` | `4/4b/` | `4b` | 10 min | `S4B_topology_position_{normal,burst}` |

Variants (suffix of the source file name) and where each lands:

| Variant | RetryGuard | TopFull | Folder |
|---|---|---|---|
| `rg_only_normal` | on, no burst keys | off | `<scen>_normal/rg_only/` |
| `both_normal` | on, no burst keys | on | `<scen>_normal/both/` |
| `tf_only` | off | on | `<scen>_normal/tf_only/` |
| `rg_only_burst` | on, burst keys | off | `<scen>_burst/rg_only/` |
| `both_burst` | on, burst keys | on | `<scen>_burst/both/` |

`log_folder` is `analysis_<prefix>_<variant>_run<N>`, `run_number` is `N` (1 or 2). S4A constrained and unconstrained share a scenario folder and are told apart by `log_folder` (their YAMLs already carry different `scenario_name`s only through the `_A` suffix, so the `4a_constrained` / `4a_unconstrained` token in the name is what separates them).

**Run order (user, 2026-10-16):** S2, S3, S4A constrained, S4A unconstrained, S4B, then S1 last. The table above is the inventory, not the queue.

Expected wall time: S1 holds ~10 min each incl. setup, others ~15-20 min each, plus 120 s cool-offs: roughly 15-20 h in total. Split it over several sessions; the order in Task 5 makes each scenario self-contained so a stop between scenarios loses nothing.

## File Structure

- Already done on `main`'s working tree (committed in Task 1): `experiments/run_scenario.py` (`RESULTS_ROOT`), `experiments/test_run_scenario.py` (expected paths), `AGENTS.md`, `STATUS.md`, `experiments/configs/final_configs/README.md`.
- Create: `experiments/make_analysis_runs_configs.py` - generator for the 60 YAMLs.
- Create: `experiments/test_make_analysis_runs_configs.py` - generator tests.
- Create (generated): `experiments/configs/analysis_runs/<group>/<prefix>_<variant>_run<N>.yaml` x 60.
- Create (generated): `experiments/results/analysis_runs_results/<scenario>_<mode>/<variant>/.gitkeep` mirroring `final results/`, plus `experiments/results/analysis_runs_results/README.md`.
- Modify at the end: `STATUS.md`, `AGENTS.md` (per the repo's update rule).

---

### Task 1: Commit the destination rule on `main`, then worktree and branch

**Files:**
- Create: `.worktrees/analysis-runs-results/` (git worktree)

- [x] **Step 0: Commit the destination-rule change on `main` (needs the user's OK to commit on `main`)**

The worktree branches from `main`, so the rule must be committed there first. Check the diff is only the five files listed in File Structure plus this plan and the status files, run the tests, then commit:

```powershell
git status --short
python -m unittest experiments.test_run_scenario -q
git add experiments/run_scenario.py experiments/test_run_scenario.py AGENTS.md STATUS.md experiments/configs/final_configs/README.md docs/superpowers/plans/2026-10-16-analysis-runs-results.md
git commit -m "feat: pull every new hold into analysis_runs_results"
```

Expected: `Ran 103 tests ... OK`. If the user declines a commit on `main`, create the branch first, move the same edits onto it, and commit there; the rule then reaches `main` only when the branch merges.

- [ ] **Step 1: Create the worktree on a new branch from `main`**

Run from `C:\Users\sagi1\Projects\Workshop`:

```powershell
git fetch origin
git worktree add .worktrees/analysis-runs-results -b analysis-runs-results main
git worktree list
```

Expected: a line `.../.worktrees/analysis-runs-results  <sha> [analysis-runs-results]`. If `main` is behind `origin/main`, stop and ask; do not fast-forward silently.

- [ ] **Step 2: Check the toolchain works inside the worktree**

```powershell
cd .worktrees/analysis-runs-results
python -c "import yaml, plotly; print('ok')"
python -m unittest experiments.test_run_scenario -q
```

Expected: `ok`, then the existing suite passes (`OK`). If a dependency is missing run `pip install -r experiments/requirements.txt` (project convention; no global installs of other packages).

All later steps run with the working directory `C:\Users\sagi1\Projects\Workshop\.worktrees\analysis-runs-results`.

---

### Task 2: Create the `analysis_runs_results` folder (first working step on the branch)

**Files:**
- Create: `experiments/results/analysis_runs_results/**` (tree + README)

The destination code and tests are already done (Task 1, Step 0). This task makes the folder itself, with the same structure as `final results/`.

- [ ] **Step 1: Confirm the runner points at the new folder**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario as r, yaml; c=yaml.safe_load(open('experiments/configs/final_configs/3/s3_both_burst.yaml')); print(r.local_results_dir(c))"
```

Expected: `experiments/results/analysis_runs_results/S3_targeted_bottleneck_burst/both/`.

- [ ] **Step 2: Create the folder tree, mirroring `final results/`**

Mirror only the directory structure (scenario_mode and variant folders, no run folders), kept in git with `.gitkeep`:

```powershell
$src = "experiments/results/final results"
$dst = "experiments/results/analysis_runs_results"
Get-ChildItem $src -Directory | ForEach-Object {
  $s = $_.Name
  Get-ChildItem $_.FullName -Directory | ForEach-Object {
    $d = Join-Path $dst "$s/$($_.Name)"
    New-Item -ItemType Directory -Force $d | Out-Null
    New-Item -ItemType File -Force (Join-Path $d ".gitkeep") | Out-Null
  }
}
(Get-ChildItem $dst -Recurse -Directory).Count
```

Expected today: 35 (10 scenario_mode parents plus 25 variant leaves). If `final results/` has S5/S6 folders by then, those are mirrored too.

- [ ] **Step 3: Add a README**

Create `experiments/results/analysis_runs_results/README.md`:

```markdown
# analysis_runs_results

Where every new hold is pulled, from 2026-10-16 on (project rule; see AGENTS.md section 6). Same layout as `../final results/`, which is closed:

`<scenario>_<normal|burst>/<variant>/<log_folder>/`

First occupant: the 60-hold analysis matrix (S1, S2, S3, S4A constrained, S4A unconstrained, S4B; five variants; two repeats). Configs: `experiments/configs/analysis_runs/`, generated by `experiments/make_analysis_runs_configs.py`. `log_folder` is `analysis_<prefix>_<variant>_run<N>`.

Plan: `docs/superpowers/plans/2026-10-16-analysis-runs-results.md`.
```

- [ ] **Step 4: Commit and push**

```powershell
git add experiments/results/analysis_runs_results
git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "feat: add the analysis_runs_results folder tree"
git push -u origin HEAD
```

Expected: the push exits 0 and `origin/analysis-runs-results` contains this commit. Do not start Task 3 until it does.

---
### Task 3: Generate the 60 configs

**Files:**
- Create: `experiments/make_analysis_runs_configs.py`
- Test: `experiments/test_make_analysis_runs_configs.py`
- Create (generated): `experiments/configs/analysis_runs/**` (60 YAMLs)

**Interfaces:**
- Produces: `GROUPS: list[tuple[str, str, str]]` as `(group, source_subdir, prefix)`; `VARIANTS: list[str]`; `REPEATS = (1, 2)`; `build_text(source_text: str, log_folder: str, run_number: int) -> str`; `generate() -> list[Path]` writing to `experiments/configs/analysis_runs/<group>/<prefix>_<variant>_run<N>.yaml`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_make_analysis_runs_configs.py`:

```python
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_analysis_runs_configs as gen  # noqa: E402
import run_scenario  # noqa: E402

CONFIGS = Path(__file__).resolve().parent / "configs"
OUT = CONFIGS / "analysis_runs"
ROOT = "experiments/results/analysis_runs_results"


class TestBuildText(unittest.TestCase):
    def setUp(self):
        self.src = (CONFIGS / "final_configs" / "3" / "s3_both_burst.yaml"
                    ).read_text(encoding="utf-8")

    def test_sets_slot(self):
        cfg = yaml.safe_load(gen.build_text(
            self.src, "analysis_s3_both_burst_run2", 2))
        self.assertEqual(cfg["run_number"], 2)
        self.assertEqual(cfg["log_folder"], "analysis_s3_both_burst_run2")
    def test_everything_else_is_unchanged(self):
        new = yaml.safe_load(gen.build_text(self.src, "x_run1", 1))
        old = yaml.safe_load(self.src)
        for k in ("run_number", "log_folder"):
            old.pop(k)
            new.pop(k)
        self.assertEqual(new, old)


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(OUT.rglob("*.yaml"))

    def test_sixty_files(self):
        self.assertEqual(len(self.paths), 60)

    def test_unique_log_folders_with_analysis_prefix(self):
        names = [yaml.safe_load(p.read_text(encoding="utf-8"))["log_folder"]
                 for p in self.paths]
        self.assertEqual(len(set(names)), 60)
        self.assertTrue(all(n.startswith("analysis_") for n in names))

    def test_all_resolve_under_analysis_root(self):
        for p in self.paths:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            self.assertTrue(
                run_scenario.local_results_dir(cfg).startswith(ROOT + "/"),
                msg=p.name)

    def test_each_group_has_all_variants_twice(self):
        for group, _src, prefix in gen.GROUPS:
            got = sorted(q.name for q in (OUT / group).glob("*.yaml"))
            want = sorted(f"{prefix}_{v}_run{n}.yaml"
                          for v in gen.VARIANTS for n in gen.REPEATS)
            self.assertEqual(got, want, msg=group)

    def test_variant_destinations(self):
        want = {
            "rg_only_normal": "_normal/rg_only/",
            "both_normal": "_normal/both/",
            "tf_only": "_normal/tf_only/",
            "rg_only_burst": "_burst/rg_only/",
            "both_burst": "_burst/both/",
        }
        for p in self.paths:
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            dest = run_scenario.local_results_dir(cfg)
            variant = next(v for v in want if f"_{v}_run" in p.name)
            self.assertTrue(dest.endswith(want[variant]), msg=p.name)

    def test_constrained_rows(self):
        def limit(p, dep):
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
            return next(r["cpu_limit_millicores"]
                        for r in cfg["scale_constraints"]
                        if r["deployment"] == dep)
        self.assertEqual(
            limit(OUT / "s3" / "s3_tf_only_run1.yaml", "checkoutservice"), 200)
        self.assertEqual(
            limit(OUT / "s4a_constrained" / "4a_constrained_tf_only_run1.yaml",
                  "productcatalogservice"), 100)
        self.assertEqual(
            limit(OUT / "s4b" / "4b_tf_only_run1.yaml", "emailservice"), 50)
        self.assertNotEqual(
            limit(OUT / "s4a_unconstrained" / "4a_unconstrained_tf_only_run1.yaml",
                  "productcatalogservice"), 100)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and confirm it fails**

```powershell
python -m unittest experiments.test_make_analysis_runs_configs -q
```

Expected: `ModuleNotFoundError: No module named 'make_analysis_runs_configs'`.

- [ ] **Step 3: Write the generator**

Create `experiments/make_analysis_runs_configs.py`:

```python
"""Generate the 60 analysis-run YAMLs from the locked final_configs/ copies.

Only run_number and log_folder differ from the source. Run: python experiments/make_analysis_runs_configs.py
"""
from __future__ import annotations

import re
from pathlib import Path

CONFIGS = Path(__file__).resolve().parent / "configs"
SRC = CONFIGS / "final_configs"
OUT = CONFIGS / "analysis_runs"

# (group folder, source dir under final_configs/, file-name prefix)
GROUPS = [
    ("s1", "1", "s1"),
    ("s2", "2", "s2"),
    ("s3", "3", "s3"),
    ("s4a_constrained", "4/4a_constrained", "4a_constrained"),
    ("s4a_unconstrained", "4/4a_unconstrained", "4a_unconstrained"),
    ("s4b", "4/4b", "4b"),
]
VARIANTS = ["rg_only_normal", "both_normal", "tf_only",
            "rg_only_burst", "both_burst"]
REPEATS = (1, 2)


def build_text(source_text: str, log_folder: str, run_number: int) -> str:
    text = re.sub(r"^run_number:\s*\d+", f"run_number: {run_number}",
                  source_text, count=1, flags=re.M)
    text, n = re.subn(
        r"^log_folder:\s*\S+",
        f"log_folder: {log_folder}",
        text, count=1, flags=re.M)
    if n != 1:
        raise ValueError("source has no log_folder line")
    return text


def generate() -> list[Path]:
    written = []
    for group, src_dir, prefix in GROUPS:
        out_dir = OUT / group
        out_dir.mkdir(parents=True, exist_ok=True)
        for variant in VARIANTS:
            src = SRC / src_dir / f"{prefix}_{variant}.yaml"
            source_text = src.read_text(encoding="utf-8")
            for n in REPEATS:
                log_folder = f"analysis_{prefix}_{variant}_run{n}"
                dest = out_dir / f"{prefix}_{variant}_run{n}.yaml"
                dest.write_text(build_text(source_text, log_folder, n),
                                encoding="utf-8", newline="\n")
                written.append(dest)
    return written


if __name__ == "__main__":
    for p in generate():
        print(p)
```

- [ ] **Step 4: Generate, then run the tests**

```powershell
python experiments/make_analysis_runs_configs.py | Measure-Object | Select-Object -ExpandProperty Count
python -m unittest experiments.test_make_analysis_runs_configs -q
python -m unittest experiments.test_run_scenario -q
```

Expected: `60`, then `OK`, then `OK`.

- [ ] **Step 5: Dry-run the pull path for two configs (no network)**

```powershell
python experiments/pull_results.py experiments/configs/analysis_runs/s3/s3_both_burst_run1.yaml --dry-run
python experiments/pull_results.py experiments/configs/analysis_runs/s4a_constrained/4a_constrained_tf_only_run2.yaml --dry-run
```

Expected: the `scp` destinations are `experiments/results/analysis_runs_results/S3_targeted_bottleneck_burst/both` and `.../S4A_topology_position_normal/tf_only`.

- [ ] **Step 6: Commit and push**

```powershell
git add experiments/make_analysis_runs_configs.py experiments/test_make_analysis_runs_configs.py experiments/configs/analysis_runs
git commit -m "feat: generate 60 analysis-run configs"
git push -u origin HEAD
```

Expected: the push exits 0. Do not start Task 4 until it does.

---

### Task 4: Pre-flight on the cluster

**Files:** none changed.

- [ ] **Step 1: Confirm VM state and SSH**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

If any VM is `TERMINATED`, start it with `gcloud compute instances start <names> --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb`, then refresh `HostName` in `~/.ssh/config` per [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md). Check the active gcloud account is one of the three allowed ones.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: user `idozacharia` on both; nodes `Ready`; all Online Boutique pods `2/2 Running`.

- [ ] **Step 2: Confirm cluster baseline matches STATUS.md**

Frontend HPA min 1 max 4, catalog HPA min 1 max 2, frontend `proxyCPU=100m`, `proxyCPULimit` unset (AGENTS.md section 7). The runner resets all eleven Deployments to Paper-C1 itself, so only the HPA and sidecar annotations need a manual look:

```powershell
ssh topfull-master "kubectl get hpa; kubectl get deploy frontend -o jsonpath='{.spec.template.metadata.annotations}'"
```

- [ ] **Step 3: Run the leftover-writer check (AGENTS.md section 6, steps 1-5)**

Clear stale `/tmp` scripts, stop Locust and master processes, confirm both `locust-clear` and `master-clear`, clear the live log dir, wait 2 s and confirm it is empty. Use the exact commands in AGENTS.md section 6.

- [ ] **Step 4: Check master has no folder named `analysis_*` already**

```powershell
ssh topfull-master "ls /home/idozacharia/experiments/results | rg '^analysis_' || echo none"
```

Expected: `none`. If any exist, stop and ask: the runner would overwrite them.

- [ ] **Step 5: Push any commits that are not on the remote**

Task 4 changes no files, so there is no new commit. The branch must still be pushed before Task 5:

```powershell
git push -u origin HEAD
```

Expected: the push exits 0. Do not start the first hold until it does.

---

### Task 5: Run the 60 holds (one block per scenario group)

Every hold uses the same **hold procedure** below. Run the scenario blocks in the order they appear: S2, S3, S4A constrained, S4A unconstrained, S4B, S1. Each block lists its 10 holds in order. Round 1 is `run1` of every variant, round 2 is `run2` with the variant order reversed, so slow drift in the cluster is not aligned with one variant.

**Variant order**

- Round 1 (`run1`): `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`
- Round 2 (`run2`): `both_burst`, `rg_only_burst`, `tf_only`, `both_normal`, `rg_only_normal`

**Hold procedure** (for config `C`, e.g. `experiments/configs/analysis_runs/s3/s3_rg_only_normal_run1.yaml`):

- [ ] **P1: Cool-off.** At least 120 s since the previous `run_scenario.py` exit (none needed before the very first hold).
- [ ] **P2: Leftover-writer check.** AGENTS.md section 6, steps 1-5 (Locust stop, master process stop, both `-clear` lines, clear logs, empty directory after 2 s). Do not continue if anything is alive.
- [ ] **P3: Run.**

```powershell
python experiments/run_scenario.py C
```

For long runs start it in the background and poll the terminal file. Expected end of output: `Results saved to (on master): /home/idozacharia/experiments/results/analysis_...`. A non-zero exit or a runner abort (CPU-limit mismatch, missing RL timeout patch) is a failed hold (it never finished, so it produced no usable data). The user allows re-running a failed hold: record the failure and cause in the log, fix the cause, redo P2 (leftover-writer check) and the 120 s cool-off, and re-run **the same config and slot**. The partial `analysis_...` folder on master is overwritten by the re-run; if a stale folder owned by another user blocks it, say so and ask before using `sudo`. Do not pull or commit the partial data. Retry a given hold at most twice; after that log it `failed` and go on. If the cause blocks every later hold too (VM down, SSH dead, cluster unhealthy), stop and report instead of burning through the list. This permission covers only holds that did not finish. A finished hold that is flagged is never re-run (see Global Constraints).

- [ ] **P4: Pull.**

```powershell
python experiments/pull_results.py C
```

Expected: `Pulled to experiments/results/analysis_runs_results/<scenario>_<mode>/<variant>/<log_folder>` and a timeline PNG. Verify the folder holds `locust_*` CSVs, `run_manifest.json`, `resource_usage.csv`, `service_inbound.csv`, `topfull_throttle.csv` (TopFull-on) and, for RetryGuard-on holds, `retryguard.log`.

- [ ] **P5: Score and health-check.**

```powershell
python experiments/analysis_score.py "experiments/results/analysis_runs_results/<scenario>_<mode>/<variant>/<log_folder>"
python experiments/topfull_health.py "experiments/results/analysis_runs_results/<scenario>_<mode>/<variant>/<log_folder>"
```

Write one line into the working log `docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md` (create it on the first hold, keep appending): `log_folder | exit ok/failed | throttle ok/FLAGGED (stale seconds) / N/A TopFull off | health ok/PROXY FD/RL STALL/not assessable | RG toggle counts`. Only `health: ok` and an unflagged throttle table is clean.

- [ ] **P6: Commit and push the pulled folder** (one commit per hold keeps the branch bisectable). Do not start the next hold until the push exits 0:

```powershell
git add "experiments/results/analysis_runs_results" docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md
git commit -m "data: <log_folder> (<clean|flagged: reason>)"
git push -u origin HEAD
```

If the folder is large enough that git objects become a problem, stop and ask before continuing; do not add it to `.gitignore` on your own. A push failure is the same kind of stop: fix it or report it, and do not launch the next hold.

#### 5.1 S2 (group `s2`, 10 min each, 10 holds)

- [ ] Round 1: `s2/s2_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s2/s2_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.2 S3 (group `s3`, checkout 200m, 10 holds)

- [ ] Round 1: `s3/s3_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s3/s3_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

After the last S3 hold confirm the checkout Deployment is back at its table value (the runner restores it; expected `800m`): `ssh topfull-master "kubectl get deploy checkoutservice -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'"`.

#### 5.3 S4A constrained (group `s4a_constrained`, catalog 100m, 10 holds)

- [ ] Round 1: `s4a_constrained/4a_constrained_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4a_constrained/4a_constrained_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.4 S4A unconstrained (group `s4a_unconstrained`, 10 holds)

- [ ] Round 1: `s4a_unconstrained/4a_unconstrained_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4a_unconstrained/4a_unconstrained_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

Before the first unconstrained hold confirm catalog is not left at 100m: the runner heals it, and its pre-run live-limit check aborts if not. A abort here is the guard working, not a failed plan.

#### 5.5 S4B (group `s4b`, email 50m, 10 holds)

- [ ] Round 1: `s4b/4b_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4b/4b_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.6 S1 (group `s1`, 5 min each, 10 holds)

- [ ] Round 1: `s1/s1_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s1/s1_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

**No stop rule for flags.** Flagged holds do not pause the matrix, however many there are. Do not change controller code or YAMLs mid-matrix.

---

### Task 6: Matrix check

**Files:**
- Create: `docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md` (already appended to in Task 5; this task adds the summary table)

- [ ] **Step 1: Count the pulled folders**

```powershell
(Get-ChildItem "experiments/results/analysis_runs_results" -Recurse -Directory -Filter "analysis_*").Count
```

Expected: `60`. For each scenario_mode/variant folder expect exactly: `rg_only` 2 per mode per group, `tf_only` 2 per group (normal only), `both` 2 per mode per group.

- [ ] **Step 2: Run the throttle audit over the new tree**

```powershell
python experiments/throttle_flags.py audit --help
```

If `audit` accepts a root argument, run it on `experiments/results/analysis_runs_results`; if it does not, rely on the per-hold P5 lines (the tool defaults to `final results/` and is not changed by this plan).

- [ ] **Step 3: Summarise the log**

Append to the log file a table of 60 rows with columns scenario, variant, run, clean/flagged, reason. Count clean vs flagged and list the flagged ones for the user's re-run decision.

- [ ] **Step 4: Commit and push**

```powershell
git add docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md
git commit -m "docs: summarise the 60 analysis-run holds"
git push -u origin HEAD
```

Expected: the push exits 0. Do not start Task 7 until it does.

---

### Task 7: Update AGENTS.md and STATUS.md (repo rule, single pass at the end)

**Files:**
- Modify: `STATUS.md`, `AGENTS.md` (in the worktree, on the branch)

- [ ] **Step 1: STATUS.md**

Append one Done bullet: date range, "60 analysis-run holds (S1, S2, S3, S4A constrained, S4A unconstrained, S4B x 5 variants x 2) pulled to `experiments/results/analysis_runs_results/`", clean vs flagged counts, the flagged `log_folder`s with reason (throttle stale seconds / PROXY FD / RL STALL), link to the log file and this plan. Add to "Next free slots": `experiments/configs/analysis_runs/` is at run 2 for every file (a repeat needs `run3` in `log_folder` and `run_number`). State that no hold was re-run and that flags are left for the user's decision.

- [ ] **Step 2: AGENTS.md**

Replace the three "Latest" lines in section 4 (do not append). Add to section 2 repo layout: `analysis_runs_results/` (under `experiments/results/`), `configs/analysis_runs/`, `make_analysis_runs_configs.py`. Add the 60-hold matrix to the section 6 example. Update "Still open" with the branch `analysis-runs-results` (unmerged) and the flagged-hold re-run decision. State anything unverified as unverified.

- [ ] **Step 3: Commit and push**

```powershell
git add STATUS.md AGENTS.md
git commit -m "docs: record the analysis-runs matrix in status and agents"
git push -u origin HEAD
```

Expected: the push exits 0 before the hand-back.

- [ ] **Step 4: Hand back**

Do not merge `analysis-runs-results` into `main` and do not remove the worktree. Report the branch name, counts, and flagged holds, and ask whether to merge, open a PR, or keep the branch as is.

---

## Self-Review

- **Spec coverage:** six groups x five variants x two repeats = 60 (Task 3 matrix, Task 5 blocks); results location `analysis_runs_results` with the structure of `final results/` is the first implementation task (Task 2, after the worktree is made in Task 1, which the user's "separate worktree" requirement needs first); new branch from `main` in a separate worktree is Task 1. The S2/S3 naming, one tf_only per repeat, and flag-only/no-re-run policy are recorded as user decisions. Commit and push after every finished task and every finished hold is a global constraint and decision 4 (user, 2026-10-16).
- **Placeholders:** none; the `C` and `<...>` tokens in the hold procedure are per-hold substitutions with a worked example given.
- **Name consistency:** `GROUPS`, `VARIANTS`, `REPEATS`, `build_text`, `generate`, `final_results_local_dir`, `local_results_dir` are used the same way in every task.
