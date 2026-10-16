# Analysis Runs (60 holds into `analysis_runs_results`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run 60 holds (6 scenario configs x 5 controller variants x 2 repeats) and pull every one into a new folder, `experiments/results/analysis_runs_results/`, which has the same structure as `experiments/results/final results/`.

**Architecture:** Add one optional YAML key, `results_root`, that overrides the root of `final_results_local_dir()` in `experiments/run_scenario.py`. With the key absent the root stays `experiments/results/final results`, so every existing config and test behaves as before. A generator script copies the locked `final_configs/` YAMLs into `experiments/configs/analysis_runs/`, gives each copy a unique `log_folder` (so nothing collides on master or in `final results/`) and the `results_root` key. The holds are then run one at a time with the existing runbook (AGENTS.md section 6).

**Tech Stack:** Python 3 (`unittest`, `pyyaml`), `run_scenario.py` / `pull_results.py` / `analysis_score.py` / `topfull_health.py`, OpenSSH aliases `topfull-master|worker-1|load`, git worktree.

## Global Constraints

- All work happens on a new branch `analysis-runs-results`, cut from `main`, in a separate worktree at `.worktrees/analysis-runs-results` (`.worktrees/` is already git-ignored). Do not touch `main`'s working tree.
- Use the locked configs in `experiments/configs/final_configs/` as the source. Do not edit them. Do not change load mixes, Paper-C1 CPU table, constrained rows, or the locked RetryGuard parameters (AGENTS.md section 5).
- Results go to `experiments/results/analysis_runs_results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. `final results/` and `campaign_48/` are never a target.
- SSH only through the aliases `topfull-master`, `topfull-worker-1`, `topfull-load`. Never hardcode IPs. SSH user stays `idozacharia`.
- Cool-off between holds is **120 s**, counted from when `run_scenario.py` exits. Do the leftover-writer check (AGENTS.md section 6, steps 1-5) before every hold.
- After every hold run `python experiments/analysis_score.py <run_dir>` and `python experiments/topfull_health.py "<run_dir>"` (throttle table + `health:` line). Any flag (throttle FLAGGED, PROXY FD, RL STALL) means the hold is not clean. Record it, do not silently re-run.
- Repeat slots are `run1` and `run2` only. A flagged hold does not get a `run3` unless the user decides so.
- Do not stop the VMs at the end unless the user asks.
- Work run from the worktree directory, so relative `experiments/results/...` paths resolve inside it.

## Assumptions the user should confirm (flagged, not blocking)

1. **"S2 constrained" has no config.** The locked S2 is plain Paper-C1 with no constrained row (AGENTS.md section 5). This plan runs the locked S2 as-is and labels it "S2". If a constrained S2 was meant, say which service and millicores before Task 2, and a constrained S2 group must be added to the generator.
2. **TopFull-only has one variant.** There is one `tf_only` YAML per scenario (mode folder `normal`). "tf only" is run once per repeat, not once per mode. That gives 5 variants per scenario: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`.
3. **S3 and S4B are constrained by definition** (checkout 200m, email 50m). S4A is run in both its constrained (catalog 100m) and unconstrained forms, as requested.
4. **Cap-floor verification still open.** The 2026-10-16 S3 tf_only hold ended `not_clean` (`health: RL STALL`). Some of these 60 holds may flag the same way. The plan records flags and finishes the matrix; the user decides on re-runs.

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

Expected wall time: S1 holds ~10 min each incl. setup, others ~15-20 min each, plus 120 s cool-offs: roughly 15-20 h in total. Split it over several sessions; the order in Task 4 makes each scenario self-contained so a stop between scenarios loses nothing.

## File Structure

- Modify: `experiments/run_scenario.py` (`final_results_local_dir`, ~line 1728) - honour optional `cfg["results_root"]`.
- Modify: `experiments/test_run_scenario.py` (add a test class after `TestFinalResultsDestination`, ~line 1377).
- Create: `experiments/make_analysis_runs_configs.py` - generator for the 60 YAMLs.
- Create: `experiments/test_make_analysis_runs_configs.py` - generator tests.
- Create (generated): `experiments/configs/analysis_runs/<group>/<prefix>_<variant>_run<N>.yaml` x 60.
- Create (generated): `experiments/results/analysis_runs_results/<scenario>_<mode>/<variant>/.gitkeep` mirroring `final results/`, plus `experiments/results/analysis_runs_results/README.md`.
- Modify at the end: `STATUS.md`, `AGENTS.md` (per the repo's update rule).

---

### Task 1: Worktree and branch

**Files:**
- Create: `.worktrees/analysis-runs-results/` (git worktree)
- Create: `.worktrees/analysis-runs-results/docs/superpowers/plans/2026-10-16-analysis-runs-results.md` (copy of this plan)

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

- [ ] **Step 3: Copy this plan into the branch and commit it**

```powershell
Copy-Item ..\..\docs\superpowers\plans\2026-10-16-analysis-runs-results.md docs\superpowers\plans\
git add docs/superpowers/plans/2026-10-16-analysis-runs-results.md
git commit -m "docs: plan 60 analysis-run holds into analysis_runs_results"
```

All later steps run with the working directory `C:\Users\sagi1\Projects\Workshop\.worktrees\analysis-runs-results`.

---

### Task 2: `results_root` override and the `analysis_runs_results` folder (first step of the plan)

**Files:**
- Modify: `experiments/run_scenario.py:1728-1751`
- Test: `experiments/test_run_scenario.py` (new class after `TestFinalResultsDestination`)
- Create: `experiments/results/analysis_runs_results/**` (tree + README)

**Interfaces:**
- Produces: `final_results_local_dir(cfg)` returns `"<root>/<scenario>_<mode>/<variant>/"` where `<root>` is `cfg["results_root"]` (no trailing slash, forward slashes) when present, else `"experiments/results/final results"`. `local_results_dir` and `pull_results.resolve_pull_paths` pick it up unchanged.

- [ ] **Step 1: Write the failing test**

Add after the `TestFinalResultsDestination` class in `experiments/test_run_scenario.py`:

```python
class TestResultsRootOverride(unittest.TestCase):
    ROOT = "experiments/results/analysis_runs_results"

    def _cfg(self):
        import yaml
        path = (Path(__file__).resolve().parent / "configs" / "final_configs"
                / "3" / "s3_both_burst.yaml")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_default_root_is_final_results(self):
        self.assertEqual(
            run_scenario.local_results_dir(self._cfg()),
            "experiments/results/final results/"
            "S3_targeted_bottleneck_burst/both/",
        )

    def test_results_root_overrides_root_only(self):
        cfg = self._cfg()
        cfg["results_root"] = self.ROOT
        self.assertEqual(
            run_scenario.local_results_dir(cfg),
            f"{self.ROOT}/S3_targeted_bottleneck_burst/both/",
        )

    def test_trailing_slash_in_root_is_normalised(self):
        cfg = self._cfg()
        cfg["results_root"] = self.ROOT + "/"
        self.assertEqual(
            run_scenario.local_results_dir(cfg),
            f"{self.ROOT}/S3_targeted_bottleneck_burst/both/",
        )

    def test_pull_results_uses_override(self):
        import pull_results
        cfg = self._cfg()
        cfg["results_root"] = self.ROOT
        _m, _r, local = pull_results.resolve_pull_paths(cfg)
        self.assertEqual(
            local, f"{self.ROOT}/S3_targeted_bottleneck_burst/both/")
```

- [ ] **Step 2: Run it and confirm the override tests fail**

```powershell
python -m unittest experiments.test_run_scenario.TestResultsRootOverride -v
```

Expected: `test_default_root_is_final_results` passes; the other three FAIL (override ignored).

- [ ] **Step 3: Implement the override**

In `experiments/run_scenario.py`, replace the last line of `final_results_local_dir` (the `return f"experiments/results/final results/{scen}_{mode}/{variant}/"` line) with:

```python
    root = str(cfg.get("results_root") or "experiments/results/final results")
    root = root.replace("\\", "/").rstrip("/")
    return f"{root}/{scen}_{mode}/{variant}/"
```

Also extend the docstring's first line to say the root is `cfg["results_root"]` when set. Leave `local_results_dir` as is.

- [ ] **Step 4: Run the tests**

```powershell
python -m unittest experiments.test_run_scenario -q
```

Expected: `OK` (the whole file, including the old `TestFinalResultsDestination`).

- [ ] **Step 5: Create the folder tree with the same structure as `final results/`**

Mirror only the directory structure (scenario_mode and variant folders, no run folders), keep it in git with `.gitkeep`:

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
Get-ChildItem $dst -Recurse -Directory | Measure-Object | Select-Object -ExpandProperty Count
```

Expected on today's `final results/`: 5 scenario folder pairs give 25 `<scenario>_<mode>/<variant>` leaf folders (S1: 5, S2: 5, S3: 5, S4A: 5, S4B: 5) plus the 10 scenario_mode parents = 35. If `final results/` has gained S5/S6 folders by then, those are mirrored too; that is fine.

- [ ] **Step 6: Add a README for the folder**

Create `experiments/results/analysis_runs_results/README.md`:

```markdown
# analysis_runs_results

Pulled results of the 60-hold analysis matrix (S1, S2, S3, S4A constrained, S4A unconstrained, S4B; five variants; two repeats). Same layout as `../final results/`:

`<scenario>_<normal|burst>/<variant>/<log_folder>/`

Configs: `experiments/configs/analysis_runs/` (generated by `experiments/make_analysis_runs_configs.py`). Each carries `results_root: experiments/results/analysis_runs_results`, which `run_scenario.py` and `pull_results.py` honour. `log_folder` is `analysis_<prefix>_<variant>_run<N>`.

Not part of `final results/`, `campaign_48/`, or `august_38/`. Plan: `docs/superpowers/plans/2026-10-16-analysis-runs-results.md`.
```

- [ ] **Step 7: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py experiments/results/analysis_runs_results
git commit -m "feat: results_root override and analysis_runs_results folder"
```

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

    def test_sets_slot_and_root(self):
        cfg = yaml.safe_load(gen.build_text(
            self.src, "analysis_s3_both_burst_run2", 2))
        self.assertEqual(cfg["run_number"], 2)
        self.assertEqual(cfg["log_folder"], "analysis_s3_both_burst_run2")
        self.assertEqual(cfg["results_root"], ROOT)

    def test_everything_else_is_unchanged(self):
        new = yaml.safe_load(gen.build_text(self.src, "x_run1", 1))
        old = yaml.safe_load(self.src)
        for k in ("run_number", "log_folder"):
            old.pop(k)
            new.pop(k)
        new.pop("results_root")
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

Only run_number, log_folder, and one added results_root line differ from the
source. Run: python experiments/make_analysis_runs_configs.py
"""
from __future__ import annotations

import re
from pathlib import Path

CONFIGS = Path(__file__).resolve().parent / "configs"
SRC = CONFIGS / "final_configs"
OUT = CONFIGS / "analysis_runs"
RESULTS_ROOT = "experiments/results/analysis_runs_results"

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
        f"log_folder: {log_folder}\nresults_root: {RESULTS_ROOT}",
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

- [ ] **Step 6: Commit**

```powershell
git add experiments/make_analysis_runs_configs.py experiments/test_make_analysis_runs_configs.py experiments/configs/analysis_runs
git commit -m "feat: generate 60 analysis-run configs"
```

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

---

### Task 5: Run the 60 holds (one block per scenario group)

Every hold uses the same **hold procedure** below. Each scenario block lists its 10 holds in order. Round 1 is `run1` of every variant, round 2 is `run2` with the variant order reversed, so slow drift in the cluster is not aligned with one variant.

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

For long runs start it in the background and poll the terminal file. Expected end of output: `Results saved to (on master): /home/idozacharia/experiments/results/analysis_...`. A non-zero exit or a runner abort (CPU-limit mismatch, missing RL timeout patch) is a failed hold: record it, fix the cause, and re-run **the same config** only after confirming master has no stale `analysis_...` folder for it (the slot is the same, so remove only that folder on master after the user agrees).

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

- [ ] **P6: Commit the pulled folder** (one commit per hold keeps the branch bisectable):

```powershell
git add "experiments/results/analysis_runs_results" docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md
git commit -m "data: <log_folder> (<clean|flagged: reason>)"
```

If the folder is large enough that git objects become a problem, stop and ask before continuing; do not add it to `.gitignore` on your own.

#### 5.1 S1 (group `s1`, 5 min each, 10 holds)

- [ ] Round 1: `s1/s1_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s1/s1_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.2 S2 (group `s2`, 10 min each, 10 holds)

- [ ] Round 1: `s2/s2_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s2/s2_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.3 S3 (group `s3`, checkout 200m, 10 holds)

- [ ] Round 1: `s3/s3_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s3/s3_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

After the last S3 hold confirm the checkout Deployment is back at its table value (the runner restores it; expected `800m`): `ssh topfull-master "kubectl get deploy checkoutservice -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'"`.

#### 5.4 S4A constrained (group `s4a_constrained`, catalog 100m, 10 holds)

- [ ] Round 1: `s4a_constrained/4a_constrained_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4a_constrained/4a_constrained_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

#### 5.5 S4A unconstrained (group `s4a_unconstrained`, 10 holds)

- [ ] Round 1: `s4a_unconstrained/4a_unconstrained_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4a_unconstrained/4a_unconstrained_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

Before the first unconstrained hold confirm catalog is not left at 100m: the runner heals it, and its pre-run live-limit check aborts if not. A abort here is the guard working, not a failed plan.

#### 5.6 S4B (group `s4b`, email 50m, 10 holds)

- [ ] Round 1: `s4b/4b_{rg_only_normal,both_normal,tf_only,rg_only_burst,both_burst}_run1.yaml`
- [ ] Round 2: `s4b/4b_{both_burst,rg_only_burst,tf_only,both_normal,rg_only_normal}_run2.yaml`

**Stop rule inside Task 5:** if three consecutive holds are flagged (PROXY FD or RL STALL), pause and tell the user before running more. Do not change controller code or YAMLs mid-matrix.

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

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/plans/2026-10-16-analysis-runs-results-log.md
git commit -m "docs: summarise the 60 analysis-run holds"
```

---

### Task 7: Update AGENTS.md and STATUS.md (repo rule, single pass at the end)

**Files:**
- Modify: `STATUS.md`, `AGENTS.md` (in the worktree, on the branch)

- [ ] **Step 1: STATUS.md**

Append one Done bullet: date range, "60 analysis-run holds (S1, S2, S3, S4A constrained, S4A unconstrained, S4B x 5 variants x 2) pulled to `experiments/results/analysis_runs_results/`", clean vs flagged counts, the flagged `log_folder`s with reason (throttle stale seconds / PROXY FD / RL STALL), link to the log file and this plan. Add to "Next free slots": `experiments/configs/analysis_runs/` is at run 2 for every file (a repeat needs `run3` in `log_folder` and `run_number`). Say clearly that the assumption "S2 has no constrained config" was used.

- [ ] **Step 2: AGENTS.md**

Replace the three "Latest" lines in section 4 (do not append). Add to section 2 repo layout: `analysis_runs_results/` (under `experiments/results/`), `configs/analysis_runs/`, `make_analysis_runs_configs.py`. Add a short line in section 6 that a config may set `results_root` to redirect the pull. Update "Still open" with the branch `analysis-runs-results` (unmerged) and the flagged-hold re-run decision. State anything unverified as unverified.

- [ ] **Step 3: Commit**

```powershell
git add STATUS.md AGENTS.md
git commit -m "docs: record the analysis-runs matrix in status and agents"
```

- [ ] **Step 4: Hand back**

Do not merge `analysis-runs-results` into `main` and do not remove the worktree. Report the branch name, counts, and flagged holds, and ask whether to merge, open a PR, or keep the branch as is.

---

## Self-Review

- **Spec coverage:** six groups x five variants x two repeats = 60 (Task 3 matrix, Task 5 blocks); results location `analysis_runs_results` with the structure of `final results/` is the first implementation task (Task 2, after the worktree is made in Task 1, which the user's "separate worktree" requirement needs first); new branch from `main` in a separate worktree is Task 1. The "S2 constrained" ambiguity is flagged as an assumption.
- **Placeholders:** none; the `C` and `<...>` tokens in the hold procedure are per-hold substitutions with a worked example given.
- **Name consistency:** `results_root`, `GROUPS`, `VARIANTS`, `REPEATS`, `build_text`, `generate`, `final_results_local_dir`, `local_results_dir` are used the same way in every task.
