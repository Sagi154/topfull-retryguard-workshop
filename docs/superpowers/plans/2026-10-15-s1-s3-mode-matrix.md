# S1 and S3 mode matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These twenty holds share one cluster. Run the hold tasks in order in one session. Do not run two holds at once. Print `COOLOFF_OK` before every launch after the first, including the second repeat of the same cell and any replay. Task 9 merges this branch into `main` and pushes `main` to `origin`.

**Goal:** Run the locked S1 configs twice each and the locked S3 configs twice each, for five controller cells: RetryGuard-only normal, both-on normal, TopFull-only, RetryGuard-only burst, and both-on burst.

**Architecture:** The ten YAMLs under `experiments/configs/final_configs/1/` and `experiments/configs/final_configs/3/` are already the locked cells on `main` at `b36fd63`. S1 and S3 share one cluster, so they stay one plan and run back to back: all ten S1 holds, then all ten S3 holds. The campaign commits land on branch `s1-s3-mode-matrix` in a linked worktree, so the primary checkout stays on `main` until Task 9. Each cell is launched twice, back to back, with a 120 s cool-off after every exit. Task 9 merges the branch into `main` with a merge commit and pushes `origin/main`. Pull uses the YAML before `bump_final_slot.py` advances it. `bump_final_slot.py` currently accepts `s2_` and `s3_` and refuses `s1_`; Task 2 adds the `s1_` prefix and nothing else. Results land in `experiments/results/final results/`. One analysis guide covers the ten S1 folders. A second guide covers the ten S3 folders. The three VMs stay RUNNING.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, PowerShell, `ssh`, `gcloud`. No controller changes. Do not rename the gate script. Do not recreate either helper.

## Global Constraints

- Branch is `s1-s3-mode-matrix`, created from `main` at `b36fd63`. Campaign commands through Task 8 run in `c:\Users\idoza\topfull-retryguard-workshop\.worktrees\s1-s3-mode-matrix`. The primary checkout stays on `main` until Task 9. Do not push until Task 9. Task 9 merges this branch into `main` and pushes `main` to `origin` (`https://github.com/Sagi154/topfull-retryguard-workshop.git`). Do not force-push. Do not touch `.worktrees/info`.
- Twenty holds, one at a time. S1 is 300 s, ten holds, about 90 minutes. S3 is 600 s, ten holds, about 140 minutes. Wall clock is about 4 hours before any replay (startup plus load, then a 120 s cool-off, plus scoring). Cell order inside each scenario: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. Two launches of one cell, then the next cell. Finish S1 before the first S3 launch.
- S1 mix `175 / 30 / 70 / 90 / 5` (getproduct / postcheckout / getcart / postcart / emptycart), `spawn_rate` 50, `duration_seconds` 300. Paper-C1 on every row, including checkout 800. S1 launches are `run1` then `run2`. After both bumps each S1 file is `run_number: 3`.
- S3 mix is the same `175 / 30 / 70 / 90 / 5`, `spawn_rate` 50, `duration_seconds` 600. Paper-C1 on every row except `checkoutservice` at 200. The five S3 files on `b36fd63` are already `run_number: 3` with `log_folder` `final_s3_<variant>_run3`. `final_s3_*_run1` and `final_s3_*_run2` already exist and stay. This campaign launches `run3` then `run4`. After both bumps each S3 file is `run_number: 5`.
- Locked RetryGuard values, already in the YAMLs: `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, `reenable_rejection` 0.25. Burst adds `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20. Normal mode omits those three keys.
- Paper-C1 millicores, unchanged on every unconstrained row: checkout 800 (S3 checkout row is 200), recommendations 1150, catalog 800, cart 800, currency 770, shipping 770, ad 1150, payment 155, email 120, redis-cart 540. Frontend 1150 m is the HPA pin and is not a `scale_constraints` row. Source: [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md). S3's constrained row is [ADR 0006](../../adr/0006-absolute-bottleneck-cap-not-fraction.md).
- The only YAML edits on those ten files are `run_number` and `log_folder`, and only through `python experiments/bump_final_slot.py <file>`, and only after that launch's pull and gate. `tf_only` contains the three burst keys and keeps them; RetryGuard is off, so its result directory is `normal`.
- Leave `experiments/configs/scenario_*.yaml` and the S2 and S4 files under `final_configs/` at their current slots. On `b36fd63` those slots are: S2 run 3, S4A unconstrained run 3, S4B run 3, S4A constrained run 5 except `4a_constrained_rg_only_burst.yaml` at run 7. Do not run `experiments/make_final_configs.py`. Do not use `run_all_scenarios.py`. Do not delete or rewrite existing folders under `experiments/results/final results/S1_normal_operation_normal/`, `S1_normal_operation_burst/`, `S3_targeted_bottleneck_normal/`, or `S3_targeted_bottleneck_burst/`.
- A failed collector gate keeps its folder. Replay that launch once from a copy under `experiments/configs/replays/` whose `log_folder` has an `_r2` suffix. Then bump the canonical file once. Do not replay a second time. A finished hold with zero `ON→OFF` lines still passes. Toggle count is recorded and is not a gate.
- **INVALID is for a broken run.** A hold is INVALID only when the run itself failed: wrong config or CPU limits, a collector or RetryGuard that did not run, Locust rows outside the band below, a TopFull-off hold whose proxy reported caps (`live5s_caps` not 0, or `other` not 0), or a route `timeout`. These never make a hold INVALID and never start a replay: TopFull not capping any API (`live5s_caps=0` with `topfull_rl_ran=yes`), catalog `replica_count` 0 samples (record `catalog_not_ready=N`), a throttle FLAG, or no retry toggles. S1 is inside capacity, so a TopFull-on S1 hold that stays at the 10000 sentinel is a valid result.
- Locust row bands: S1 (300 s) `270–295`. S3 (600 s) `540–580`. The S1 floor is `0.9 × 300`, the same ratio as the 540 floor on a 600 s hold. The S1 ceiling is `300 − 5`, which admits the 2026-10-12 S1 holds (277–289 rows). `540–580` is the locked 600 s band.
- A throttle **FLAG** (any `fetch failed` WARNING, or any API over 30 s with no fresh threshold or admitted read) is written in the run log. It does not fail the collector gate and does not trigger a replay. Goodput, P95, rejection, and retry numbers stay valid. Cap and admitted-rate numbers from a flagged hold are carried, not measured.
- Cool-off is 120 s, starting when `run_scenario.py` exits. The next `run_scenario.py` is forbidden until that 120 s has elapsed and the session has printed `COOLOFF_OK`. This applies between the two repeats of one cell, between cells, between S1 hold 10 and S3 hold 11, and before a replay of a failed launch. Pull, the gate, and scoring of that one folder happen during the wait. If they finish early, sleep the remainder. If they run longer than 120 s, the next launch still has to print `COOLOFF_OK` and then it may start. Checkout and recommendations stay up. `restart_before_hold` stays absent. A fresh PowerShell session does not remember `$exitAt`. If a hold already exited and the clock was lost, `Start-Sleep -Seconds 120` before the next launch, then set `$exitAt = (Get-Date).AddSeconds(-120)`.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`), Linux user `idozacharia`, project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. The `networks-workshop` project stays stopped. Do not hardcode a public IP.
- Paper-C1 replica pin for the whole campaign, set once before S1 hold 1 and left in place through S3 hold 10: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `sidecar.istio.io/proxyCPU=90m`, `proxyCPULimit` unset. Restore once at the end to frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset. Leave the three VMs RUNNING.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`).
- Commands from Task 2 onward run from `c:\Users\idoza\topfull-retryguard-workshop\.worktrees\s1-s3-mode-matrix`.

## File Structure

- Modify, before any hold: `experiments/bump_final_slot.py` (allow the `s1_` filename prefix) and `experiments/test_bump_final_slot.py`.
- Read-only, already on `b36fd63`: `experiments/s3s4_mode_matrix_gate.py`, `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/retryguard.py`.
- Modify during the runs, slots only: the ten YAMLs in the two hold tables. After the campaign, each S1 file is `run_number: 3` and `log_folder: final_s1_<variant>_run3`. Each S3 file is `run_number: 5` and `log_folder: final_s3_<variant>_run5`.
- Create on the branch, first commit: this plan, copied into the worktree. `b36fd63` does not contain it.
- Create during the S1 runs: `docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md`.
- Create during the S3 runs: `docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md`.
- Create after the ten S1 pulls: `Guides and Info/2026-10-15-s1-mode-matrix-abc.md`.
- Create after the ten S3 pulls: `Guides and Info/2026-10-15-s3-mode-matrix-abc.md`.
- Modify after the VMs are confirmed still RUNNING: `STATUS.md` (one Done bullet; the `final_configs/1/` and `final_configs/3/` next-free lines) and `AGENTS.md` §4 (replace the three Latest lines).
- After Task 8, from the primary checkout: merge `s1-s3-mode-matrix` into `main` with `--no-ff` and push `origin/main`. No new campaign files in that step.
- Create only if a gate fails: `experiments/configs/replays/final_s1_<variant>_run<N>_r2.yaml` or `experiments/configs/replays/final_s3_<variant>_run<N>_r2.yaml`.

`run_scenario.py` `final_results_local_dir` sends a config to `experiments/results/final results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. Mode is `burst` only when RetryGuard is on and `burst_rpr` is set. TopFull-only is `normal`.

| # | Cell | Scenario | YAML | `log_folder` first launch, then second | Kind | TF | Result mode |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1–2 | rg only normal | S1 | `experiments/configs/final_configs/1/s1_rg_only_normal.yaml` | `final_s1_rg_only_normal_run1`, `_run2` | `normal` | `off` | `normal` |
| 3–4 | both normal | S1 | `experiments/configs/final_configs/1/s1_both_normal.yaml` | `final_s1_both_normal_run1`, `_run2` | `normal` | `on` | `normal` |
| 5–6 | tf only | S1 | `experiments/configs/final_configs/1/s1_tf_only.yaml` | `final_s1_tf_only_run1`, `_run2` | `tf` | `on` | `normal` |
| 7–8 | rg only burst | S1 | `experiments/configs/final_configs/1/s1_rg_only_burst.yaml` | `final_s1_rg_only_burst_run1`, `_run2` | `burst20` | `off` | `burst` |
| 9–10 | both burst | S1 | `experiments/configs/final_configs/1/s1_both_burst.yaml` | `final_s1_both_burst_run1`, `_run2` | `burst20` | `on` | `burst` |
| 11–12 | rg only normal | S3 | `experiments/configs/final_configs/3/s3_rg_only_normal.yaml` | `final_s3_rg_only_normal_run3`, `_run4` | `normal` | `off` | `normal` |
| 13–14 | both normal | S3 | `experiments/configs/final_configs/3/s3_both_normal.yaml` | `final_s3_both_normal_run3`, `_run4` | `normal` | `on` | `normal` |
| 15–16 | tf only | S3 | `experiments/configs/final_configs/3/s3_tf_only.yaml` | `final_s3_tf_only_run3`, `_run4` | `tf` | `on` | `normal` |
| 17–18 | rg only burst | S3 | `experiments/configs/final_configs/3/s3_rg_only_burst.yaml` | `final_s3_rg_only_burst_run3`, `_run4` | `burst20` | `off` | `burst` |
| 19–20 | both burst | S3 | `experiments/configs/final_configs/3/s3_both_burst.yaml` | `final_s3_both_burst_run3`, `_run4` | `burst20` | `on` | `burst` |

Result roots:

- S1 normal and TopFull-only: `experiments/results/final results/S1_normal_operation_normal/<rg_only|both|tf_only>/`
- S1 burst: `experiments/results/final results/S1_normal_operation_burst/<rg_only|both>/`
- S3 normal and TopFull-only: `experiments/results/final results/S3_targeted_bottleneck_normal/<rg_only|both|tf_only>/`
- S3 burst: `experiments/results/final results/S3_targeted_bottleneck_burst/<rg_only|both>/`

---

### Task 1: Cut a worktree from main

**Files:**
- Create: `c:\Users\idoza\topfull-retryguard-workshop\.worktrees\s1-s3-mode-matrix\` (linked worktree; `.worktrees/` is gitignored)
- Create on the new branch: `docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md` (this file)

**Interfaces:**
- Consumes: primary checkout `c:\Users\idoza\topfull-retryguard-workshop` on `main` at `b36fd63`. `.gitignore` already contains `.worktrees/`.
- Produces: branch `s1-s3-mode-matrix` checked out only in the worktree. Later tasks run with that directory as the working directory. The primary checkout remains on `main`.

- [ ] **Step 1: Confirm main, a clean ignore rule, and that the branch name is free**

Run from `c:\Users\idoza\topfull-retryguard-workshop`:

```powershell
git branch --show-current
git rev-parse --short HEAD
git check-ignore -q .worktrees/s1-s3-mode-matrix; if ($LASTEXITCODE -eq 0) { "IGNORED" } else { "NOT_IGNORED" }
git branch --list s1-s3-mode-matrix
git worktree list
```

Expected: branch `main`, HEAD `b36fd63`, output `IGNORED`, and `git branch --list` prints nothing. `git worktree list` already shows the primary checkout and `.worktrees/info` on `runs-analysis`. A dirty primary checkout is left as it is. Do not stash it and do not add those files. Any other HEAD, a missing ignore, or an existing `s1-s3-mode-matrix` branch means stop. Do not add a second worktree for a branch that exists.

- [ ] **Step 2: Create the worktree**

If the harness has a native worktree command, use it to create branch `s1-s3-mode-matrix` from `b36fd63` and then skip the `git worktree add` line. Otherwise:

```powershell
git worktree add -b s1-s3-mode-matrix .worktrees/s1-s3-mode-matrix b36fd63
git -C .worktrees/s1-s3-mode-matrix branch --show-current
git -C .worktrees/s1-s3-mode-matrix rev-parse --short HEAD
git branch --show-current
```

Expected: the worktree is on `s1-s3-mode-matrix` at `b36fd63`. The last command, run in the primary checkout, still prints `main`.

- [ ] **Step 3: Put this plan on the branch**

`b36fd63` does not contain this plan. From the primary checkout, copy it into the worktree and commit it there:

```powershell
New-Item -ItemType Directory -Force -Path .worktrees/s1-s3-mode-matrix/docs/superpowers/plans | Out-Null
Copy-Item "docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md" ".worktrees/s1-s3-mode-matrix/docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md"
git -C .worktrees/s1-s3-mode-matrix add "docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md"
git -C .worktrees/s1-s3-mode-matrix commit -m @"
Add the S1 and S3 mode-matrix plan.

Twenty holds use the locked mixes, two repeats of each controller cell.
"@
git -C .worktrees/s1-s3-mode-matrix status --short
git -C .worktrees/s1-s3-mode-matrix log -1 --oneline
```

Expected: worktree status empty, and the new commit's parent is `b36fd63`. Do not commit this file on `main`. Every later command uses working directory `c:\Users\idoza\topfull-retryguard-workshop\.worktrees\s1-s3-mode-matrix`.

---

### Task 2: Let the slot bump accept S1 files

**Files:**
- Modify: `experiments/bump_final_slot.py`
- Test: `experiments/test_bump_final_slot.py`

**Interfaces:**
- Consumes: `bump_text` and `bump_file` as they are on `b36fd63`. `ALLOWED_PREFIXES` is `("s2_", "s3_", "4a_constrained_", "4a_unconstrained_", "4b_")`. `bump_file` refuses a path whose name does not start with one of those, and refuses a path that does not contain `final_configs`. `test_refuses_s1` expects `s1_rg_only_normal.yaml` to raise `SystemExit`.
- Produces: `ALLOWED_PREFIXES` includes `"s1_"`. `bump_file(Path(".../final_configs/1/s1_rg_only_normal.yaml"))` returns the new run number. `s5_` is refused. A replay copy named `final_s1_rg_only_normal_run1_r2.yaml` is still refused, because its name does not start with `s1_` and its directory is not `final_configs`. `s3_` stays accepted. `bump_text` is unchanged.

- [ ] **Step 1: Write the failing test**

In `experiments/test_bump_final_slot.py`, replace `test_refuses_s1` with these two methods on `TestBumpFileGuard`:

```python
    def test_accepts_s1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "1" / "s1_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            text = SAMPLE.replace(
                "final_s3_rg_only_normal", "final_s1_rg_only_normal"
            ).replace("\n", "\r\n")
            path.write_bytes(text.encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"log_folder: final_s1_rg_only_normal_run2\r\n", raw)
            self.assertIn(b"run_number: 2\r\n", raw)

    def test_refuses_s5(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "5" / "s5_interval_10s.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(SAMPLE, encoding="utf-8")
            with self.assertRaises(SystemExit):
                bump_final_slot.bump_file(path)
```

Change the module docstring's first sentence to `Slot bump for the S1/S2/S3/S4 mode-matrix YAMLs.`

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python experiments/test_bump_final_slot.py TestBumpFileGuard.test_accepts_s1 -v
```

Expected: FAIL. `bump_file` raises `SystemExit` with `not an S2/S3/S4 campaign file`.

- [ ] **Step 3: Write the minimal implementation**

In `experiments/bump_final_slot.py`, replace the module docstring with:

```python
"""Advance run_number and log_folder on one S1/S2/S3/S4 final_configs YAML.

The campaign file stays the runner input. The first launch of a file uses
the run_number already in it. After that folder is pulled, bump once and
launch again. After the second launch is pulled, bump once more so a later
hold cannot reuse the name on master.

    python experiments/bump_final_slot.py experiments/configs/final_configs/1/s1_rg_only_normal.yaml
"""
```

Change `ALLOWED_PREFIXES` to:

```python
ALLOWED_PREFIXES = (
    "s1_",
    "s2_",
    "s3_",
    "4a_constrained_",
    "4a_unconstrained_",
    "4b_",
)
```

Change the refusal line to:

```python
        raise SystemExit(f"refusing {path}: not an S1/S2/S3/S4 campaign file")
```

Leave `bump_text` unchanged. An `s5_` file still fails. A file named `final_s1_rg_only_normal_run1_r2.yaml` still fails the prefix check.

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python experiments/test_bump_final_slot.py -v
```

Expected: every test `ok`, including `test_accepts_s1`, `test_accepts_s2`, `test_refuses_s5`, and `test_refuses_replay_suffix`. Exit code 0. `test_refuses_s1` is gone.

- [ ] **Step 5: Commit**

```powershell
git add experiments/bump_final_slot.py experiments/test_bump_final_slot.py
git commit -m @"
Let the slot bump accept the S1 final configs.

The five locked S1 files can advance run_number without a hand edit.
"@
```

---

### Task 3: Confirm the ten YAMLs and the free slots

**Files:** none modified. Read the ten YAMLs and `experiments/results/final results/`.

**Interfaces:**
- Consumes: the worktree after Task 2. The five S1 files are still `run_number: 1`. The five S3 files are still `run_number: 3`.
- Produces: a printed `SLOTS_OK` line and twenty `ABSENT` lines. Hold tasks start only after both pass. S1 launch names are `run1` then `run2`. S3 launch names are `run3` then `run4`.

- [ ] **Step 1: Assert mix, CPU, controllers, and starting slots**

```powershell
python -c @"
import yaml
from pathlib import Path

users = {'getproduct': 175, 'postcheckout': 30, 'getcart': 70, 'postcart': 90, 'emptycart': 5}
cpu = {
    'checkoutservice': 800,
    'recommendationservice': 1150,
    'productcatalogservice': 800,
    'cartservice': 800,
    'currencyservice': 770,
    'shippingservice': 770,
    'adservice': 1150,
    'paymentservice': 155,
    'emailservice': 120,
    'redis-cart': 540,
}
burst = {'burst_rpr', 'burst_window_seconds', 'burst_min_first_attempts'}
variants = ['rg_only_normal', 'both_normal', 'tf_only', 'rg_only_burst', 'both_burst']
specs = [
    ('1', 's1', 1, 300, 'normal_operation', 800),
    ('3', 's3', 3, 600, 'targeted_bottleneck', 200),
]
n = 0
for folder, prefix, run, duration, scenario, checkout in specs:
    root = Path('experiments/configs/final_configs') / folder
    for variant in variants:
        path = root / f'{prefix}_{variant}.yaml'
        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        assert cfg['run_number'] == run, path
        assert cfg['log_folder'] == f'final_{prefix}_{variant}_run{run}', cfg['log_folder']
        assert cfg['scenario_name'] == scenario, path
        assert cfg['duration_seconds'] == duration, path
        assert 'restart_before_hold' not in cfg, path
        assert cfg['locust']['user_counts'] == users, path
        assert cfg['locust']['spawn_rate'] == 50, path
        limits = {row['deployment']: row['cpu_limit_millicores'] for row in cfg['scale_constraints']}
        expect = dict(cpu)
        expect['checkoutservice'] = checkout
        assert limits == expect, (path, limits)
        rg = cfg['retryguard']
        want_tf = variant.startswith('both') or variant == 'tf_only'
        assert cfg['topfull_rl']['enabled'] is want_tf, path
        assert rg['enabled'] is (variant != 'tf_only'), path
        assert rg['retry_metric'] == 'edge_rpr', path
        assert rg['interval_samples'] == 20, path
        assert rg['rejection_threshold'] == 0.2, path
        assert rg['retries_threshold'] == 0.4, path
        assert rg['reenable_rejection'] == 0.25, path
        if variant.endswith('normal') and variant != 'tf_only':
            assert burst.isdisjoint(rg), path
        else:
            assert rg['burst_rpr'] == 2.0 and rg['burst_window_seconds'] == 5 and rg['burst_min_first_attempts'] == 20, path
        n += 1
assert n == 10
print('SLOTS_OK')
"@
```

Expected: `SLOTS_OK`. Any `AssertionError` means stop. Do not edit a YAML by hand to make this pass.

- [ ] **Step 2: Confirm the twenty new folders are absent**

```powershell
$wantAbsent = @(
  "S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1",
  "S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run2",
  "S1_normal_operation_normal/both/final_s1_both_normal_run1",
  "S1_normal_operation_normal/both/final_s1_both_normal_run2",
  "S1_normal_operation_normal/tf_only/final_s1_tf_only_run1",
  "S1_normal_operation_normal/tf_only/final_s1_tf_only_run2",
  "S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1",
  "S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run2",
  "S1_normal_operation_burst/both/final_s1_both_burst_run1",
  "S1_normal_operation_burst/both/final_s1_both_burst_run2",
  "S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3",
  "S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run4",
  "S3_targeted_bottleneck_normal/both/final_s3_both_normal_run3",
  "S3_targeted_bottleneck_normal/both/final_s3_both_normal_run4",
  "S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run3",
  "S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run4",
  "S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3",
  "S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run4",
  "S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3",
  "S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4"
)
foreach ($n in $wantAbsent) {
  $p = "experiments/results/final results/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `ABSENT` twenty times. An `EXISTS` line means stop. Older folders may be present. Leave them. That includes `s1_normal_rgtf0_rep1`, `s1_burst20_rgtf1_rep2_r2`, `s3_ck200_rgtf1`, and every `final_s3_*_run1` and `final_s3_*_run2` folder.

---

### Task 4: Bring the cluster up and pin Paper-C1 replicas

**Files:** none.

**Interfaces:**
- Consumes: SSH aliases and project `project-76deda76-55f1-42d2-abb`.
- Produces: three VMs `RUNNING`, `kubectl get nodes` Ready, frontend HPA 4/4, catalog HPA 1/1, sidecar `90m` with `proxyCPULimit` empty, four frontend pods `2/2`, and no Locust or master writer already alive. Hold tasks assume this pin is still in place through S3 hold 10.

- [ ] **Step 1: List the three VMs**

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected names: `topfull-master`, `topfull-worker-1`, `topfull-load`. If a name from `networks-workshop` appears, stop. If all three are `RUNNING`, go to Step 2. If any is `TERMINATED`, start all three:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

For each previous `HostName` in `~/.ssh/config` and each new public IP, run `ssh-keygen -R <ip>`, then set the three `HostName` lines to the new addresses. `User` stays `idozacharia`. Do not commit `~/.ssh/config`.

- [ ] **Step 2: Confirm SSH**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-load "hostname; whoami"
```

Expected: hostname matches the alias and `whoami` is `idozacharia`.

- [ ] **Step 3: Confirm the cluster is idle**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`. Any other line means another campaign is using the cluster. Stop this plan. Do not `pkill` those processes.

- [ ] **Step 4: Confirm the API server**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 -o ControlMaster=no topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`, Online Boutique pods `2/2`, VirtualServices present. `connection to localhost:8080 refused` means `idozacharia` has no `~/.kube/config`. Copy it from `/home/idozacharia/.kube/config` only if that file is missing, then retry. Wait up to five minutes for `Ready` after a start. Do not launch a hold before that.

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

### Task 5: Ten S1 holds

**Files:**
- Modify: the five `experiments/configs/final_configs/1/s1_*.yaml` files, slots only, via `bump_final_slot.py`
- Create: `docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md`
- Create: `Guides and Info/2026-10-15-s1-mode-matrix-abc.md`
- Create during pulls: the ten `final_s1_*_run1` and `*_run2` folders under `experiments/results/final results/S1_normal_operation_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 4, `bump_final_slot.py` after Task 2, and `s3s4_mode_matrix_gate.py`.
- Produces: ten pulled S1 folders, five S1 YAMLs at `run_number: 3`, the S1 run log, and the S1 guide. The five S3 YAMLs are still `run_number: 3`. Task 6 starts only after the cool-off from hold 10.

The files already say `run1`. Hold 1 launches that name. After a pass, or after the single replay, bump once. Hold 2 launches `run2`. The second bump leaves the file at `run3`.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 1 | `experiments/configs/final_configs/1/s1_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1` | `run 1 -> 2` |
| 2 | same file after that bump | `normal` | `off` | `.../rg_only/final_s1_rg_only_normal_run2` | `run 2 -> 3` |
| 3 | `experiments/configs/final_configs/1/s1_both_normal.yaml` | `normal` | `on` | `.../both/final_s1_both_normal_run1` | `run 1 -> 2` |
| 4 | same file after that bump | `normal` | `on` | `.../both/final_s1_both_normal_run2` | `run 2 -> 3` |
| 5 | `experiments/configs/final_configs/1/s1_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_s1_tf_only_run1` | `run 1 -> 2` |
| 6 | same file after that bump | `tf` | `on` | `.../tf_only/final_s1_tf_only_run2` | `run 2 -> 3` |
| 7 | `experiments/configs/final_configs/1/s1_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1` | `run 1 -> 2` |
| 8 | same file after that bump | `burst20` | `off` | `.../rg_only/final_s1_rg_only_burst_run2` | `run 2 -> 3` |
| 9 | `experiments/configs/final_configs/1/s1_both_burst.yaml` | `burst20` | `on` | `.../both/final_s1_both_burst_run1` | `run 1 -> 2` |
| 10 | same file after that bump | `burst20` | `on` | `.../both/final_s1_both_burst_run2` | `run 2 -> 3` |

Repeat Steps 1–7 for each row. The command blocks show hold 1. On later rows, substitute that row's YAML, kind, TF flag, and folder. Bump only after the gate, so the file on disk is still the slot that just ran when a replay copy is made. Before hold 1, set the cool-off clock to empty. Hold 1 is the only launch that may skip the wait.

```powershell
$exitAt = $null
```

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

- [ ] **Step 4: Cool off, then run**

The launch command comes after `COOLOFF_OK`. Hold 1 prints `COOLOFF_OK first launch`. Every later launch, including hold 2 of the same cell and a replay, sleeps until 120 s after `$exitAt`.

```powershell
if ($null -eq $exitAt) {
  "COOLOFF_OK first launch"
} else {
  $elapsed = ((Get-Date) - $exitAt).TotalSeconds
  if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
  "COOLOFF_OK elapsed_before_wait=$([int]$elapsed)"
}
python experiments/run_scenario.py experiments/configs/final_configs/1/s1_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

One process. Wait until it exits. A 300 s hold plus startup is about 7 minutes. `$exitAt` is the cool-off clock and is set only after a zero exit. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row. On the later rows, pass that row's YAML. Do not launch that row until its own Step 4 has printed `COOLOFF_OK`.

- [ ] **Step 5: Pull, then gate, then bump**

Pull before any bump. The YAML still names the folder that just ran.

```powershell
python experiments/pull_results.py experiments/configs/final_configs/1/s1_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1" normal off
python experiments/analysis_score.py "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1"
```

The printed pull destination is the folder in the table. `pull_results.py` also writes `timeline.png`. Catalog CPU during an S1 hold is 800 m. Checkout CPU is 800 m. Pass when all of these hold:

- `locust_rows` is 270–295.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a` and there is no `retryguard.log`. `missing=retryguard.log` is a fail on `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. A catalog denominator of 0 is allowed. A catalog sample with `replica_count` 0 is recorded as `catalog_not_ready=N` and is not a gate. A `replica_count` above 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0.
- No `missing=` line.

`burst_observe` is recorded. It is not a gate. A burst hold can pass with `burst_observe=no`.

Read the scorer's `Throttle data quality` table, and:

```powershell
rg "fetch failed" "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1/topfull_throttle_collector.log"
```

No match, and no API over 30 s without a fresh read, is `throttle clean`. A match or a stretch over 30 s is `throttle FLAG`. A flag does not fail this gate and does not start a replay. On a TopFull-on flag, name it in the run log and in the guide. Cap and admitted-rate numbers from that folder are carried, not measured.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

On a pass, bump the canonical file. Hold 1 prints `run 1 -> 2`. Hold 2 prints `run 2 -> 3`.

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/1/s1_rg_only_normal.yaml
```

On a fail, do not bump yet. Keep the folder. Copy the YAML that is still at the launched slot. Hold 1:

```powershell
New-Item -ItemType Directory -Force -Path experiments/configs/replays | Out-Null
Copy-Item experiments/configs/final_configs/1/s1_rg_only_normal.yaml experiments/configs/replays/final_s1_rg_only_normal_run1_r2.yaml
python -c @"
from pathlib import Path
p = Path('experiments/configs/replays/final_s1_rg_only_normal_run1_r2.yaml')
raw = p.read_bytes()
old = b'log_folder: final_s1_rg_only_normal_run1'
new = b'log_folder: final_s1_rg_only_normal_run1_r2'
if raw.count(old) != 1:
    raise SystemExit('log_folder line missing')
p.write_bytes(raw.replace(old, new, 1))
"@
```

On a later row, the copy's source is that row's YAML, the replay filename is that row's `log_folder` plus `_r2.yaml`, and `old` / `new` use that same `log_folder`. Leave `run_number` as the launched slot. Run Steps 1–4 with that copy. Step 4 sleeps out the 120 s since the failed exit before it launches the replay, and it replaces `$exitAt` only after the replay exits. Then pull and gate the `_r2` folder. Do not bump the replay copy. `bump_final_slot.py` rejects it: the filename starts with `final_s1_`, not `s1_`, and the directory is not under `final_configs`. After the replay, whether it passed or failed, bump the canonical file once. Do not replay a second time. The guide's column is the `_r2` folder when that replay passed, and the canonical folder when the replay failed.

- [ ] **Step 6: Finish the 120 s cool-off**

The clock is the last `run_scenario.py` exit for this row, including a replay. This sleep is the gap before the next row. The next row's Step 4 repeats the same check and prints `COOLOFF_OK` with no further sleep when this step already waited.

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
"COOLOFF_OK ready_for_next_launch"
```

Then Steps 1–3 again before the next row. After hold 10, leave `$exitAt` set. Task 6 hold 11 is not a first launch.

- [ ] **Step 7: Append one line per launch**

Create `docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md` on hold 1:

```markdown
# S1 mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; checkout 800m; users 175/30/70/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; catalog_not_ready=N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; topfull_rl_ran=yes or no; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines in `retryguard.log`, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch has no log: write `toggles n/a`.

- [ ] **Step 8: Score and write the guide**

Two calls, because `analysis_score.py` labels a folder by its `runN` suffix and then by the parent directory name. `rg_only/1` would collide between `S1_normal_operation_normal` and `S1_normal_operation_burst`. If a replay folder replaced a failed launch, pass that `_r2` path instead of the failed folder and say so in the index.

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1" `
  "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run2" `
  "experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run1" `
  "experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run2" `
  "experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run1" `
  "experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1" `
  "experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run2" `
  "experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run1" `
  "experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run2"
```

Write `Guides and Info/2026-10-15-s1-mode-matrix-abc.md` from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers are the `log_folder` names, holds 1–10, with a bold bar after every pair. Sections, in the template's order:

1. Setup. 300 s, mix 175 / 30 / 70 / 90 / 5, `spawn_rate` 50, Paper-C1 unchanged (checkout 800 m, catalog 800 m, email 120 m), frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, the ten folder paths.
2. Index. One row per launch. Column order is holds 1–10.
3. Edge-mode bars. Paste the scorer's first line and its `Burst bars` line. For `burst_rpr` 2.0 that line is `2.00 / 1.33 / 0.67` at 3 / 2 / 1 attempts. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s.
4. (a) Edge rpr. Three tables, only for edges with a tick above the shed bar or a retry delta. Bold when the file streak is at least 30 seconds.
5. 4a Burst on the four burst folders: the scorer's `(a2) Burst window` line and the burst-vs-normal shed split. The six normal and TopFull-only folders get one sentence that burst mode was off.
6. Rejection beside (a), including the HTTP-only tables for the four read callees. Bold when a controlled service's streak is at least 30. Frontend and redis-cart stay plain.
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
17. Throttle data quality, then TopFull live caps. Paste the `Throttle data quality` table. Name every flagged hold. `postcart` and `emptycart` are called out when every live read is no cap.
18. One paragraph per launch: what shed, what climbed, retry volume, `grpc_4`, and which services were detector-hot.
19. Related links: this plan, the template, the (a)/(b)/(c) reading, [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [ADR 0007](../../adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md). Older S1 folders (`s1_normal_*`, `s1_burst20_*`, `campaign_48/`) are not columns.

- [ ] **Step 9: Commit the ten folders**

Add the five S1 YAMLs, the S1 run log, the S1 guide, and only the ten new `final_s1_*` folders. Do not `git add` the parent `S1_normal_operation_normal` or `S1_normal_operation_burst` directories. Those already contain older holds. Do not add the S3 YAMLs.

```powershell
git add experiments/configs/final_configs/1 "docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md" "Guides and Info/2026-10-15-s1-mode-matrix-abc.md"
git add -- "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run1" "experiments/results/final results/S1_normal_operation_normal/rg_only/final_s1_rg_only_normal_run2" "experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run1" "experiments/results/final results/S1_normal_operation_normal/both/final_s1_both_normal_run2" "experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run1" "experiments/results/final results/S1_normal_operation_normal/tf_only/final_s1_tf_only_run2" "experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run1" "experiments/results/final results/S1_normal_operation_burst/rg_only/final_s1_rg_only_burst_run2" "experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run1" "experiments/results/final results/S1_normal_operation_burst/both/final_s1_both_burst_run2"
git commit -m @"
Record the S1 mode matrix, two repeats of each cell.

The locked 175/30/70/90/5 mix stays on Paper-C1, in run1 and run2.
"@
```

If a replay YAML or a `_r2` folder was created, `git add` that path as well. Do not push yet. Task 9 pushes `main`.

---

### Task 6: Ten S3 holds

**Files:**
- Modify: the five `experiments/configs/final_configs/3/s3_*.yaml` files, slots only, via `bump_final_slot.py`
- Create: `docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md`
- Create: `Guides and Info/2026-10-15-s3-mode-matrix-abc.md`
- Create during pulls: the ten `final_s3_*_run3` and `*_run4` folders under `experiments/results/final results/S3_targeted_bottleneck_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 4, still in place, the S1 cool-off clock from Task 5, and `bump_final_slot.py` after Task 2. `s3_` is already an allowed prefix on `b36fd63`.
- Produces: ten pulled S3 folders, five S3 YAMLs at `run_number: 5`, the S3 run log, and the S3 guide. Task 7 starts only after the cool-off from hold 20. The runner sets checkout to 200 m at the start of each S3 hold and restores Paper-C1, including checkout 800 m, when that hold ends.

The files already say `run3`. Hold 11 launches that name. After a pass, or after the single replay, bump once. Hold 12 launches `run4`. The second bump leaves the file at `run5`. Do not launch `run1` or `run2`. Those folders already exist.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 11 | `experiments/configs/final_configs/3/s3_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3` | `run 3 -> 4` |
| 12 | same file after that bump | `normal` | `off` | `.../rg_only/final_s3_rg_only_normal_run4` | `run 4 -> 5` |
| 13 | `experiments/configs/final_configs/3/s3_both_normal.yaml` | `normal` | `on` | `.../both/final_s3_both_normal_run3` | `run 3 -> 4` |
| 14 | same file after that bump | `normal` | `on` | `.../both/final_s3_both_normal_run4` | `run 4 -> 5` |
| 15 | `experiments/configs/final_configs/3/s3_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_s3_tf_only_run3` | `run 3 -> 4` |
| 16 | same file after that bump | `tf` | `on` | `.../tf_only/final_s3_tf_only_run4` | `run 4 -> 5` |
| 17 | `experiments/configs/final_configs/3/s3_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3` | `run 3 -> 4` |
| 18 | same file after that bump | `burst20` | `off` | `.../rg_only/final_s3_rg_only_burst_run4` | `run 4 -> 5` |
| 19 | `experiments/configs/final_configs/3/s3_both_burst.yaml` | `burst20` | `on` | `.../both/final_s3_both_burst_run3` | `run 3 -> 4` |
| 20 | same file after that bump | `burst20` | `on` | `.../both/final_s3_both_burst_run4` | `run 4 -> 5` |

Repeat Steps 1–7 for each row. The command blocks show hold 11. On later rows, substitute that row's YAML, kind, TF flag, and folder. Bump only after the gate, so the file on disk is still the slot that just ran when a replay copy is made.

- [ ] **Step 1: Stop leftover writers**

Hold 11 is not a first launch. If `$exitAt` was lost with the PowerShell session, sleep 120 s and set `$exitAt = (Get-Date).AddSeconds(-120)` before this step. If hold 10's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

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

- [ ] **Step 4: Cool off, then run**

The launch command comes after `COOLOFF_OK`. There is no first-launch exception in this task. Hold 11 waits on hold 10's `$exitAt`. Hold 12 waits on hold 11. A replay waits on the failed exit.

```powershell
if ($null -eq $exitAt) { throw "COOLOFF missing: S3 has no first-launch exception" }
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
"COOLOFF_OK elapsed_before_wait=$([int]$elapsed)"
python experiments/run_scenario.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

One process. Wait until it exits. A 600 s hold plus startup is about 12 minutes. `$exitAt` is the cool-off clock and is set only after a zero exit. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row. On the later rows, pass that row's YAML. Do not launch that row until its own Step 4 has printed `COOLOFF_OK`. The runner aborts before Locust if live CPU limits differ from Paper-C1 plus checkout 200 m. That abort is a non-zero exit. Stop.

- [ ] **Step 5: Pull, then gate, then bump**

Pull before any bump. The YAML still names the folder that just ran.

```powershell
python experiments/pull_results.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3" normal off
python experiments/analysis_score.py "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3"
```

The printed pull destination is the folder in the table. `pull_results.py` also writes `timeline.png`. Catalog CPU during an S3 hold is 800 m. Checkout CPU is 200 m. Pass when all of these hold:

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a` and there is no `retryguard.log`. `missing=retryguard.log` is a fail on `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. A catalog denominator of 0 is allowed. A catalog sample with `replica_count` 0 is recorded as `catalog_not_ready=N` and is not a gate. A `replica_count` above 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0.
- No `missing=` line.

`burst_observe` is recorded. It is not a gate. A burst hold can pass with `burst_observe=no`.

Read the scorer's `Throttle data quality` table, and:

```powershell
rg "fetch failed" "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3/topfull_throttle_collector.log"
```

No match, and no API over 30 s without a fresh read, is `throttle clean`. A match or a stretch over 30 s is `throttle FLAG`. A flag does not fail this gate and does not start a replay. On a TopFull-on flag, name it in the run log and in the guide. Cap and admitted-rate numbers from that folder are carried, not measured.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

On a pass, bump the canonical file. Hold 11 prints `run 3 -> 4`. Hold 12 prints `run 4 -> 5`.

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/3/s3_rg_only_normal.yaml
```

On a fail, do not bump yet. Keep the folder. Copy the YAML that is still at the launched slot. Hold 11:

```powershell
New-Item -ItemType Directory -Force -Path experiments/configs/replays | Out-Null
Copy-Item experiments/configs/final_configs/3/s3_rg_only_normal.yaml experiments/configs/replays/final_s3_rg_only_normal_run3_r2.yaml
python -c @"
from pathlib import Path
p = Path('experiments/configs/replays/final_s3_rg_only_normal_run3_r2.yaml')
raw = p.read_bytes()
old = b'log_folder: final_s3_rg_only_normal_run3'
new = b'log_folder: final_s3_rg_only_normal_run3_r2'
if raw.count(old) != 1:
    raise SystemExit('log_folder line missing')
p.write_bytes(raw.replace(old, new, 1))
"@
```

On a later row, the copy's source is that row's YAML, the replay filename is that row's `log_folder` plus `_r2.yaml`, and `old` / `new` use that same `log_folder`. Leave `run_number` as the launched slot. Run Steps 1–4 with that copy. Step 4 sleeps out the 120 s since the failed exit before it launches the replay, and it replaces `$exitAt` only after the replay exits. Then pull and gate the `_r2` folder. Do not bump the replay copy. `bump_final_slot.py` rejects it: the filename starts with `final_s3_`, not `s3_`, and the directory is not under `final_configs`. After the replay, whether it passed or failed, bump the canonical file once. Do not replay a second time. The guide's column is the `_r2` folder when that replay passed, and the canonical folder when the replay failed.

- [ ] **Step 6: Finish the 120 s cool-off**

The clock is the last `run_scenario.py` exit for this row, including a replay. This sleep is the gap before the next row. The next row's Step 4 repeats the same check and prints `COOLOFF_OK` with no further sleep when this step already waited.

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
"COOLOFF_OK ready_for_next_launch"
```

Then Steps 1–3 again before the next row. After hold 20, leave any remainder for Task 7.

- [ ] **Step 7: Append one line per launch**

Create `docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md` on hold 11:

```markdown
# S3 mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; checkout 200m; users 175/30/70/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; catalog_not_ready=N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; topfull_rl_ran=yes or no; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines in `retryguard.log`, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch has no log: write `toggles n/a`. Hold numbers in this file are 11–20.

- [ ] **Step 8: Score and write the guide**

Two calls. If a replay folder replaced a failed launch, pass that `_r2` path instead of the failed folder and say so in the index. Do not pass `final_s3_*_run1` or `final_s3_*_run2`.

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run4" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run3" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run4" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run3" `
  "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run4"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run4" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3" `
  "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4"
```

Write `Guides and Info/2026-10-15-s3-mode-matrix-abc.md` from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers are the `log_folder` names, holds 11–20, with a bold bar after every pair. Sections, in the template's order:

1. Setup. 600 s, mix 175 / 30 / 70 / 90 / 5, `spawn_rate` 50, Paper-C1 with checkout constrained to 200 m (catalog 800 m, email 120 m), frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, the ten folder paths.
2. Index. One row per launch. Column order is holds 11–20.
3. Edge-mode bars. Paste the scorer's first line and its `Burst bars` line. For `burst_rpr` 2.0 that line is `2.00 / 1.33 / 0.67` at 3 / 2 / 1 attempts. A burst shed goes to 0 and recovers on the normal path. Shed and 0→1 take 20 s. Climbs take 10 s.
4. (a) Edge rpr. Three tables, only for edges with a tick above the shed bar or a retry delta. Bold when the file streak is at least 30 seconds.
5. 4a Burst on the four burst folders: the scorer's `(a2) Burst window` line and the burst-vs-normal shed split. The six normal and TopFull-only folders get one sentence that burst mode was off.
6. Rejection beside (a), including the HTTP-only tables for the four read callees. Bold when a controlled service's streak is at least 30. Frontend and redis-cart stay plain.
7. (b) Detector overloaded fraction. Bold when the share is at least 0.5.
8. (c) Retry volume. Outbound retry delta by target, and inbound resets for all 11 services.
9. RetryGuard toggles. Part 1 is the scorer's count table and timestamp table for each hold that has transition lines. Part 2 is the per-callee table from the template. TopFull-only has no `retryguard.log`: one sentence, no empty table.
10. Locust goodput. Mean `Goodput` while `RPS > 0`, per API.
11. Locust fail rate. Mean `Fail / RPS` while `RPS > 0`, per API.
12. Locust P95. Mean `Latency95` (ms) while `RPS > 0`, per API.
13. Inbound arrival rate. Positive `Δtotal` over the elapsed time of `service_inbound.csv`, per service.
14. Inbound sojourn. `Δrq_time_sum_ms / Δrq_time_count`, milliseconds.
15. Share of inbound requests above 500 ms.
16. CPU. Per-pod quota, replica mode, mean millicores, max millicores. Checkout's quota line is 200 m.
17. Throttle data quality, then TopFull live caps. Paste the `Throttle data quality` table. Name every flagged hold. `postcart` and `emptycart` are called out when every live read is no cap.
18. One paragraph per launch: what shed, what climbed, retry volume, `grpc_4`, and which services were detector-hot.
19. Related links: this plan, the template, the (a)/(b)/(c) reading, [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [ADR 0006](../../adr/0006-absolute-bottleneck-cap-not-fraction.md), [ADR 0007](../../adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md). `final_s3_*_run1`, `final_s3_*_run2`, `s3_ck200_rgtf1`, and `campaign_48/` S3 are not columns.

- [ ] **Step 9: Commit the ten folders**

Add the five S3 YAMLs, the S3 run log, the S3 guide, and only the ten new `final_s3_*_run3` and `*_run4` folders. Do not `git add` the parent `S3_targeted_bottleneck_normal` or `S3_targeted_bottleneck_burst` directories. Those already contain `run1` and `run2`.

```powershell
git add experiments/configs/final_configs/3 "docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md" "Guides and Info/2026-10-15-s3-mode-matrix-abc.md"
git add -- "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run3" "experiments/results/final results/S3_targeted_bottleneck_normal/rg_only/final_s3_rg_only_normal_run4" "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run3" "experiments/results/final results/S3_targeted_bottleneck_normal/both/final_s3_both_normal_run4" "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run3" "experiments/results/final results/S3_targeted_bottleneck_normal/tf_only/final_s3_tf_only_run4" "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run3" "experiments/results/final results/S3_targeted_bottleneck_burst/rg_only/final_s3_rg_only_burst_run4" "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run3" "experiments/results/final results/S3_targeted_bottleneck_burst/both/final_s3_both_burst_run4"
git commit -m @"
Record the S3 mode matrix, two repeats of each cell.

Checkout stays at 200m, and the new slots are run3 and run4.
"@
```

If a replay YAML or a `_r2` folder was created, `git add` that path as well. Do not push yet. Task 9 pushes `main`.

---

### Task 7: Restore the unpinned shape

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 4, and a finished hold 20.
- Produces: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, frontend app 1150 m. The three VMs stay `RUNNING`.

- [ ] **Step 1: Stop leftover writers**

If hold 20's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

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

Expected: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar annotation `100m` with `proxyCPULimit` absent, app CPU limits frontend `1150m`, checkout `800m`, catalog `800m`, email `120m`. The runner restores Paper-C1 after each hold, including after the last S3 hold. If a limit is still off that table, patch that deployment's server container requests and limits to the Paper-C1 value and wait for its rollout.

- [ ] **Step 3: Leave the VMs RUNNING**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are `RUNNING`. Do not stop them.

---

### Task 8: STATUS, AGENTS, and the slot check

**Files:**
- Modify: `STATUS.md` Done (one bullet) and the Next free slots lines for `final_configs/1/` and `final_configs/3/`
- Modify: `AGENTS.md` §4, the three Latest lines
- Test: the slot assertion below

**Interfaces:**
- Consumes: both run logs, both guides, five S1 YAMLs at `run_number: 3`, and five S3 YAMLs at `run_number: 5`.
- Produces: STATUS and AGENTS describing this campaign. S2 stays at run 3. S4A constrained stays at run 5 except `4a_constrained_rg_only_burst.yaml` at run 7. S4A unconstrained and S4B stay at run 3. Historical `scenario_*.yaml` slots stay as they are.

- [ ] **Step 1: Confirm the slots**

```powershell
python -c @"
import yaml
from pathlib import Path

def runs(folder, prefix):
    paths = sorted(Path(f'experiments/configs/final_configs/{folder}').glob(f'{prefix}_*.yaml'))
    assert len(paths) == 5, folder
    return {p.name: yaml.safe_load(p.read_text(encoding='utf-8'))['run_number'] for p in paths}

s1 = runs('1', 's1')
s2 = runs('2', 's2')
s3 = runs('3', 's3')
s4u = runs('4/4a_unconstrained', '4a_unconstrained')
s4c = runs('4/4a_constrained', '4a_constrained')
s4b = runs('4/4b', '4b')
assert all(v == 3 for v in s1.values()), s1
assert all(v == 3 for v in s2.values()), s2
assert all(v == 5 for v in s3.values()), s3
assert all(v == 3 for v in s4u.values()), s4u
assert all(v == 3 for v in s4b.values()), s4b
assert s4c['4a_constrained_rg_only_burst.yaml'] == 7, s4c
assert all(v == 5 for name, v in s4c.items() if name != '4a_constrained_rg_only_burst.yaml'), s4c
for folder, prefix, run in (('1', 's1', 3), ('3', 's3', 5)):
    for path in Path(f'experiments/configs/final_configs/{folder}').glob(f'{prefix}_*.yaml'):
        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        assert cfg['log_folder'].endswith(f'_run{run}'), path
print('slots ok: S1 run 3, S3 run 5, S2 and S4 unchanged')
"@
python experiments/test_bump_final_slot.py
python experiments/test_run_scenario.py TestFinalConfigs
```

Expected: the print line above, then both test modules `OK`.

- [ ] **Step 2: Update Next free slots**

In `STATUS.md`, replace the summary sentence that begins `experiments/configs/final_configs/` slots are per folder below. The replacement is: `experiments/configs/final_configs/` slots are per folder below. This campaign moved `final_configs/1/` from run 1 to run 3 and `final_configs/3/` from run 3 to run 5. S2 stays at run 3. S4A constrained stays at run 5, except `4a_constrained_rg_only_burst.yaml` at run 7. S4A unconstrained and S4B stay at run 3.

Change these two trailing numbers and leave every other slot line as it is:

- `experiments/configs/final_configs/1/` — from `1` to `3`
- `experiments/configs/final_configs/3/` — from `3` to `5`

The historical `scenario_*.yaml` list stays as it is. Do not change `scenario_1_baseline.yaml` (43), `scenario_1_retryguard.yaml` (8), `scenario_3_baseline.yaml` (10), or `scenario_3_retryguard.yaml` (9).

- [ ] **Step 3: Append one Done bullet and replace the three Latest lines**

Append one bullet under Done in `STATUS.md`, after the S2 mode matrix bullet. Name the twenty `log_folder` values, the PASS and INVALID counts copied from the two run logs, any throttle FLAG holds, and the paths of both run logs and both guides. Say the five S1 YAMLs were left at run 3, the five S3 YAMLs were left at run 5, S2 and S4 final_configs were not moved, the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, and the three VMs were left RUNNING.

Replace the three Latest lines in `AGENTS.md` §4. On `b36fd63` those three lines are the S4A constrained burst-rerun paragraph, the `1 INVALID, 2 PASS, 2 throttle FLAG` paragraph, and the cluster-restored paragraph. Do not append a fourth. The replacement is:

1. This matrix: branch `s1-s3-mode-matrix` from `b36fd63`, twenty holds. S1 mix 175/30/70/90/5 at 300 s, Paper-C1, `run1` and `run2` of `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, and `both_burst`. Next free slot for those five YAMLs is run 3. S3 is the same mix at 600 s with checkout 200 m, `run3` and `run4` of the same five cells. Next free slot for those five YAMLs is run 5.
2. The PASS, INVALID, and throttle FLAG counts copied from `docs/superpowers/plans/2026-10-15-s1-mode-matrix-run-log.md` and `docs/superpowers/plans/2026-10-15-s3-mode-matrix-run-log.md`, plus the guide paths `Guides and Info/2026-10-15-s1-mode-matrix-abc.md` and `Guides and Info/2026-10-15-s3-mode-matrix-abc.md`.
3. The restored cluster and the three VMs left RUNNING.

Keep the Still open list. Add one sentence there that this matrix is the locked S1 set under `final results/` (`final_s1_*_run1` and `final_s1_*_run2`) and the next S3 pair (`final_s3_*_run3` and `final_s3_*_run4`). The `s1_normal_*` folders, the `s1_burst20_*` folders, `s3_ck200_rgtf1`, and `campaign_48/` S1 and S3 are not comparable. `final_s3_*_run1` and `final_s3_*_run2` stay on disk and are not columns in this guide.

- [ ] **Step 4: Commit**

```powershell
git add STATUS.md AGENTS.md
git commit -m @"
Record the S1 and S3 mode-matrix slots and the restored cluster.

S1 YAMLs sit at run 3, S3 YAMLs sit at run 5, and the VMs were left running.
"@
git status --short
git branch --show-current
git merge-base --is-ancestor b36fd63 HEAD; if ($LASTEXITCODE -eq 0) { "FROM_MAIN" } else { "NOT_FROM_MAIN" }
```

Expected: branch `s1-s3-mode-matrix`, working tree clean, and `FROM_MAIN`. Do not push yet. Do not check this branch out in the primary checkout. Task 9 merges it into `main` and pushes `origin/main`.

---

### Task 9: Merge into main and push

**Files:** none created. The primary checkout at `c:\Users\idoza\topfull-retryguard-workshop` moves from `b36fd63` to the merge commit. `origin/main` receives that commit.

**Interfaces:**
- Consumes: the worktree on `s1-s3-mode-matrix` after Task 8, working tree clean, `b36fd63` an ancestor of `HEAD`. Remote `origin` is `https://github.com/Sagi154/topfull-retryguard-workshop.git`. Recent history on `main` uses merge commits (`Merge branch 's2-mode-matrix'`, `Merge branch 's4-relock-mode-matrix'`).
- Produces: `origin/main` contains `Merge branch 's1-s3-mode-matrix'`. The primary checkout is on `main` and matches `origin/main`. The worktree stays on `s1-s3-mode-matrix`.

- [ ] **Step 1: Confirm the campaign branch is complete**

Run from the worktree:

```powershell
git status --short
git branch --show-current
git merge-base --is-ancestor b36fd63 HEAD; if ($LASTEXITCODE -eq 0) { "FROM_MAIN" } else { "NOT_FROM_MAIN" }
git log --oneline b36fd63..HEAD
```

Expected: status empty, branch `s1-s3-mode-matrix`, `FROM_MAIN`, and the campaign commits (the plan, the slot-bump change, the S1 record, the S3 record, and the STATUS/AGENTS record). Anything short of that means stop. Do not merge a partial campaign.

- [ ] **Step 2: Confirm main can take a merge**

Run from `c:\Users\idoza\topfull-retryguard-workshop`:

```powershell
git fetch origin
git branch --show-current
git status --short
git rev-parse --short HEAD
git rev-parse --short origin/main
```

Expected: branch `main`. `HEAD` and `origin/main` are the same commit, the commit this branch was cut from (`b36fd63` unless `origin/main` moved and was fast-forwarded below). A dirty tracked file means stop. Do not stash.

If `HEAD` is behind `origin/main` and `git merge-base HEAD origin/main` equals `HEAD`, fast-forward first:

```powershell
git merge --ff-only origin/main
```

If `HEAD` and `origin/main` have diverged, stop. Do not force-push.

The primary checkout may still have an untracked copy of `docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md`. The branch already contains that file. Remove only that untracked path, and only when `git status --short` shows it as `??`:

```powershell
git status --short -- "docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md"
```

If that prints `?? docs/superpowers/plans/2026-10-15-s1-s3-mode-matrix.md`, delete that one untracked file. Leave every other untracked file.

- [ ] **Step 3: Merge and push main**

From the primary checkout:

```powershell
git merge --no-ff s1-s3-mode-matrix -m @"
Merge branch 's1-s3-mode-matrix'

"@
git push origin main
git status --short --branch
git log -1 --oneline
```

Expected: the push updates `origin/main`, status shows `main` up to date with `origin/main`, and the latest subject is `Merge branch 's1-s3-mode-matrix'`. A rejected push means `origin/main` moved. Fetch and stop. Do not force-push. Do not push `s1-s3-mode-matrix` in place of `main`. The worktree stays checked out on `s1-s3-mode-matrix`.
