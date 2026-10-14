# S4 relock mode matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These thirty holds share one cluster. Run the hold tasks in order in one session. Do not run two holds at once.

**Goal:** Run the locked S4A-constrained, S4A-unconstrained, and S4B configs twice each for five controller cells: RetryGuard-only normal, both-on normal, TopFull-only, RetryGuard-only burst, and both-on burst.

**Architecture:** The fifteen YAMLs under `experiments/configs/final_configs/4/` are already the locked cells on `main` at `e26f05c`. The campaign commits land on branch `s4-relock-mode-matrix` in a linked worktree, so the primary checkout stays on `main`. Each cell is launched twice, back to back. Pull uses the YAML before `bump_final_slot.py` advances it. S4A constrained is already at `run_number: 3` because run 1 and run 2 are the 2026-10-13 catalog-50m matrix; those folders stay on disk and are not launched again. S4A unconstrained and S4B are at `run_number: 1`. Results land in `experiments/results/final results/`. One analysis guide is written per scenario. The three VMs stay RUNNING through the holds. Task 9 stops them, pushes `s4-relock-mode-matrix`, and merges that branch into local `main`.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, PowerShell, `ssh`, `gcloud`. No controller changes. Those two helpers already exist; do not recreate them.

## Global Constraints

- Branch is `s4-relock-mode-matrix`, created from `main` at `e26f05c` (`Merge pull request #8 from Sagi154/runs-analysis`). All campaign commands run in `c:\Users\sagi1\Projects\Workshop\.worktrees\s4-relock-mode-matrix`. The primary checkout stays on `main` until Task 9. Do not merge and do not push before Task 9. Task 9 stops the three VMs, commits anything still uncommitted on `s4-relock-mode-matrix`, pushes that branch, and merges it into local `main`. Do not push `main`.
- Thirty holds, 600 s each, `spawn_rate` 50. Wall clock is about 7–8 hours (about 12 minutes of startup plus load, then a 120 s cool-off, plus scoring). One hold at a time.
- Scenario order: S4A constrained, S4A unconstrained, S4B. Cell order inside each scenario: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. Two launches of one cell, then the next cell.
- Locked RetryGuard values, already in the YAMLs: `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, `reenable_rejection` 0.25. Burst adds `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20. Normal mode omits those three keys.
- S4A mix `50 / 20 / 50 / 600 / 5` (getproduct / postcheckout / getcart / postcart / emptycart). Constrained sets `productcatalogservice` to 100 m. Unconstrained leaves catalog at 800 m. S4B mix `175 / 30 / 70 / 90 / 5`, `emailservice` 50 m. Paper-C1 is [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md).
- The only YAML edits on those fifteen files are `run_number` and `log_folder`, and only through `python experiments/bump_final_slot.py <file>`, and only after that launch's pull and gate. `tf_only` files contain the three burst keys and keep them; RetryGuard is off, so their result directory is `normal`.
- Do not launch, delete, or rewrite the catalog-50m folders `final_4a_constrained_*_run1`, `*_run2`, and their `_r2` replays. Do not edit `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`. That guide is the old mix `10 / 10 / 10 / 600 / 5` at catalog 50 m.
- Leave `experiments/configs/scenario_*.yaml` and the S1, S2, and S3 files under `final_configs/` at their current slots. Do not run `experiments/make_final_configs.py`. Do not use `run_all_scenarios.py`.
- A failed collector gate keeps its folder. Replay that launch once from a copy under `experiments/configs/replays/` whose `log_folder` has an `_r2` suffix. Then bump the canonical file once. Do not replay a second time. A finished hold with zero `ON→OFF` lines still passes. Toggle count is recorded and is not a gate.
- A throttle **FLAG** (any `fetch failed` WARNING, or any API over 30 s with no fresh threshold or admitted read) is written in the run log. It does not fail the collector gate and does not trigger a replay. Goodput, P95, rejection, and retry numbers stay valid. Cap and admitted-rate numbers from a flagged hold are not used as measured.
- **INVALID is for a broken run, not for a surprising result.** A hold is INVALID only when the run itself failed: wrong config or CPU limits, a collector or RetryGuard that did not run, Locust rows outside 540–580, a TopFull-off hold whose proxy reported caps, or a route `timeout`. These never make a hold INVALID and never start a replay: TopFull not capping any API (`live5s_caps=0` with `topfull_rl_ran=yes`), catalog `replica_count` 0 samples (record `catalog_not_ready=N`), a throttle FLAG, or no retry toggles. The runner now clears `proxy/rate_config` before each proxy start, aborts before Locust if the proxy limits are not all 10000, and widens the catalog probe (timeout 5 s, 6 failures) while the catalog CPU is constrained.
- Cool-off is 120 s, starting when `run_scenario.py` exits. Pull, the gate, and scoring of that one folder happen during the wait. Checkout and recommendations stay up. `restart_before_hold` stays absent.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`), Linux user `idozacharia`, project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. The `networks-workshop` project stays stopped. Do not hardcode a public IP.
- Paper-C1 replica pin for the whole campaign: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `sidecar.istio.io/proxyCPU=90m`, `proxyCPULimit` unset. Restore once at the end to frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset. Leave the three VMs RUNNING until Task 9, which stops them after that restore.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`).
- Commands run from `c:\Users\sagi1\Projects\Workshop\.worktrees\s4-relock-mode-matrix`.

## File Structure

- Read-only, already on `e26f05c`: `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/retryguard.py`.
- Modify during the runs, slots only: the fifteen YAMLs in the hold tables. After the campaign, each constrained file is `run_number: 5` and `log_folder: final_4a_constrained_<variant>_run5`. Each unconstrained file and each S4B file is `run_number: 3` and `log_folder: final_<prefix>_<variant>_run3`.
- Create on the branch, first commit: this plan, copied into the worktree if `e26f05c` does not contain it.
- Create during the runs: `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md` — one line per launch, including a failed launch and its single replay.
- Create after each scenario's pulls: `Guides and Info/2026-10-13-s4a-constrained-relock-abc.md`, `Guides and Info/2026-10-13-s4a-unconstrained-relock-abc.md`, `Guides and Info/2026-10-13-s4b-relock-abc.md`.
- Modify while the VMs are still RUNNING: `STATUS.md` (one Done bullet; next-free slots) and `AGENTS.md` §4 (replace the three Latest lines). Task 9 replaces the "still RUNNING" clause in those two files after the stop.
- Create only if a gate fails: `experiments/configs/replays/<log_folder>_r2.yaml`.

`run_scenario.py` `final_results_local_dir` sends a config to `experiments/results/final results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. Both S4A variants use `S4A_topology_position` (`scenario_name: topology_position_A`); `log_folder` tells them apart. S4B uses `S4B_topology_position`. Mode is `burst` only when RetryGuard is on and `burst_rpr` is set. TopFull-only is `normal`.

| # | Scenario | Cell | YAML | `log_folder` rep 1, then rep 2 | Kind | TF | Result mode |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1–2 | S4A constrained | rg only normal | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml` | `final_4a_constrained_rg_only_normal_run3`, `_run4` | `normal` | `off` | `normal` |
| 3–4 | S4A constrained | both normal | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_normal.yaml` | `final_4a_constrained_both_normal_run3`, `_run4` | `normal` | `on` | `normal` |
| 5–6 | S4A constrained | tf only | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_tf_only.yaml` | `final_4a_constrained_tf_only_run3`, `_run4` | `tf` | `on` | `normal` |
| 7–8 | S4A constrained | rg only burst | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_burst.yaml` | `final_4a_constrained_rg_only_burst_run3`, `_run4` | `burst20` | `off` | `burst` |
| 9–10 | S4A constrained | both burst | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_burst.yaml` | `final_4a_constrained_both_burst_run3`, `_run4` | `burst20` | `on` | `burst` |
| 11–12 | S4A unconstrained | rg only normal | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml` | `final_4a_unconstrained_rg_only_normal_run1`, `_run2` | `normal` | `off` | `normal` |
| 13–14 | S4A unconstrained | both normal | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_normal.yaml` | `final_4a_unconstrained_both_normal_run1`, `_run2` | `normal` | `on` | `normal` |
| 15–16 | S4A unconstrained | tf only | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_tf_only.yaml` | `final_4a_unconstrained_tf_only_run1`, `_run2` | `tf` | `on` | `normal` |
| 17–18 | S4A unconstrained | rg only burst | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_burst.yaml` | `final_4a_unconstrained_rg_only_burst_run1`, `_run2` | `burst20` | `off` | `burst` |
| 19–20 | S4A unconstrained | both burst | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_burst.yaml` | `final_4a_unconstrained_both_burst_run1`, `_run2` | `burst20` | `on` | `burst` |
| 21–22 | S4B | rg only normal | `experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml` | `final_4b_rg_only_normal_run1`, `_run2` | `normal` | `off` | `normal` |
| 23–24 | S4B | both normal | `experiments/configs/final_configs/4/4b/4b_both_normal.yaml` | `final_4b_both_normal_run1`, `_run2` | `normal` | `on` | `normal` |
| 25–26 | S4B | tf only | `experiments/configs/final_configs/4/4b/4b_tf_only.yaml` | `final_4b_tf_only_run1`, `_run2` | `tf` | `on` | `normal` |
| 27–28 | S4B | rg only burst | `experiments/configs/final_configs/4/4b/4b_rg_only_burst.yaml` | `final_4b_rg_only_burst_run1`, `_run2` | `burst20` | `off` | `burst` |
| 29–30 | S4B | both burst | `experiments/configs/final_configs/4/4b/4b_both_burst.yaml` | `final_4b_both_burst_run1`, `_run2` | `burst20` | `on` | `burst` |

Result roots:

- S4A (constrained and unconstrained): `experiments/results/final results/S4A_topology_position_<normal|burst>/<rg_only|both|tf_only>/`
- S4B: `experiments/results/final results/S4B_topology_position_<normal|burst>/<rg_only|both|tf_only>/`

---

### Task 1: Cut a worktree from main

**Files:**
- Create: `c:\Users\sagi1\Projects\Workshop\.worktrees\s4-relock-mode-matrix\` (linked worktree; `.worktrees/` is gitignored)
- Create on the new branch: `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md` (this file, if `e26f05c` does not already contain it)

**Interfaces:**
- Consumes: primary checkout `c:\Users\sagi1\Projects\Workshop` on `main` at `e26f05c`. `.gitignore` already contains `.worktrees/`.
- Produces: branch `s4-relock-mode-matrix` checked out only in the worktree. Later tasks run with that directory as the working directory. The primary checkout remains on `main`.

- [ ] **Step 1: Confirm main, a clean ignore rule, and that the branch name is free**

Run from `c:\Users\sagi1\Projects\Workshop`:

```powershell
git branch --show-current
git rev-parse --short HEAD
git check-ignore -q .worktrees/s4-relock-mode-matrix; if ($LASTEXITCODE -eq 0) { "IGNORED" } else { "NOT_IGNORED" }
git branch --list s4-relock-mode-matrix
git worktree list
```

Expected: branch `main`, HEAD `e26f05c`, output `IGNORED`, and `git branch --list` prints nothing. `git worktree list` already shows the primary checkout and `.worktrees/topfull-throttle-collector`. Any other HEAD, a missing ignore, or an existing `s4-relock-mode-matrix` branch means stop. Do not add a second worktree for a branch that exists.

- [ ] **Step 2: Create the worktree**

If the harness has a native worktree command, use it to create branch `s4-relock-mode-matrix` from `e26f05c` and then skip the `git worktree add` line. Otherwise:

```powershell
git worktree add -b s4-relock-mode-matrix .worktrees/s4-relock-mode-matrix e26f05c
git -C .worktrees/s4-relock-mode-matrix branch --show-current
git -C .worktrees/s4-relock-mode-matrix rev-parse --short HEAD
git branch --show-current
```

Expected: the worktree is on `s4-relock-mode-matrix` at `e26f05c`. The last command, run in the primary checkout, still prints `main`.

- [ ] **Step 3: Put this plan on the branch**

`e26f05c` does not contain this plan. From the primary checkout, copy it into the worktree and commit it there:

```powershell
New-Item -ItemType Directory -Force -Path .worktrees/s4-relock-mode-matrix/docs/superpowers/plans | Out-Null
Copy-Item docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md .worktrees/s4-relock-mode-matrix/docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md
git -C .worktrees/s4-relock-mode-matrix add docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix.md
git -C .worktrees/s4-relock-mode-matrix commit -m @"
Add the S4 relock mode-matrix plan.

Thirty holds use the locked 100m catalog mix, starting past the catalog-50m slots.
"@
git -C .worktrees/s4-relock-mode-matrix status --short
git -C .worktrees/s4-relock-mode-matrix log -1 --oneline
```

Expected: worktree status empty, and the new commit's parent is `e26f05c`. Do not commit this file on `main`. Every later command uses working directory `c:\Users\sagi1\Projects\Workshop\.worktrees\s4-relock-mode-matrix`.

---

### Task 2: Confirm the fifteen YAMLs and the free slots

**Files:** none modified. Read the fifteen YAMLs and `experiments/results/final results/`.

**Interfaces:**
- Consumes: the worktree at `e26f05c` plus the plan commit.
- Produces: a printed `SLOTS_OK` line. Hold tasks start only after this passes. Constrained launch names are `run3` then `run4`. Unconstrained and S4B launch names are `run1` then `run2`.

- [ ] **Step 1: Assert mix, CPU, controllers, and starting slots**

```powershell
python -c @"
import yaml
from pathlib import Path

root = Path('experiments/configs/final_configs/4')
cells = [
    ('4a_constrained', '4a_constrained', 3, {'getproduct': 50, 'postcheckout': 20, 'getcart': 50, 'postcart': 600, 'emptycart': 5}, {'productcatalogservice': 100, 'emailservice': 120}),
    ('4a_unconstrained', '4a_unconstrained', 1, {'getproduct': 50, 'postcheckout': 20, 'getcart': 50, 'postcart': 600, 'emptycart': 5}, {'productcatalogservice': 800, 'emailservice': 120}),
    ('4b', '4b', 1, {'getproduct': 175, 'postcheckout': 30, 'getcart': 70, 'postcart': 90, 'emptycart': 5}, {'productcatalogservice': 800, 'emailservice': 50}),
]
variants = ['rg_only_normal', 'both_normal', 'tf_only', 'rg_only_burst', 'both_burst']
burst = {'burst_rpr', 'burst_window_seconds', 'burst_min_first_attempts'}
n = 0
for folder, prefix, slot, users, cpu in cells:
    for variant in variants:
        path = root / folder / f'{prefix}_{variant}.yaml'
        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        assert cfg['run_number'] == slot, path
        assert cfg['log_folder'] == f'final_{prefix}_{variant}_run{slot}', cfg['log_folder']
        assert cfg['duration_seconds'] == 600, path
        assert cfg['locust']['user_counts'] == users, path
        assert cfg['locust']['spawn_rate'] == 50, path
        limits = {row['deployment']: row['cpu_limit_millicores'] for row in cfg['scale_constraints']}
        for dep, milli in cpu.items():
            assert limits[dep] == milli, (path, dep, limits[dep])
        rg = cfg['retryguard']
        want_tf = variant.startswith('both') or variant == 'tf_only'
        assert cfg['topfull_rl']['enabled'] is want_tf, path
        assert rg['enabled'] is (variant != 'tf_only'), path
        if variant.endswith('normal') and variant != 'tf_only':
            assert burst.isdisjoint(rg), path
        else:
            assert rg['burst_rpr'] == 2.0 and rg['burst_window_seconds'] == 5 and rg['burst_min_first_attempts'] == 20, path
        n += 1
assert n == 15
print('SLOTS_OK')
"@
```

Expected: `SLOTS_OK`. Any `AssertionError` means stop. Do not edit a YAML by hand to make this pass.

- [ ] **Step 2: Confirm the thirty new folders are absent and the catalog-50m folders are still present**

```powershell
$wantAbsent = @(
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3",
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4",
  "S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3",
  "S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4",
  "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3",
  "S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4",
  "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3",
  "S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4",
  "S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3",
  "S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4",
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
$wantPresent = @(
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run1",
  "S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run2"
)
foreach ($n in $wantAbsent) {
  $p = "experiments/results/final results/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
foreach ($n in $wantPresent) {
  $p = "experiments/results/final results/$n"
  if (Test-Path $p) { "PRESENT $n" } else { "MISSING $n" }
}
```

Expected: `ABSENT` thirty times and `PRESENT` twice. An `EXISTS` line means stop. A `MISSING` line means the catalog-50m history is not in this worktree; stop and do not recreate it by launching run 1.

---

### Task 3: Bring the cluster up and pin Paper-C1 replicas

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

For each previous `HostName` in `~/.ssh/config` and each new public IP, run `ssh-keygen -R <ip>`, then set the three `HostName` lines to the new addresses. `User` stays `idozacharia`. Do not commit `~/.ssh/config`.

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

Expected: both nodes `Ready`, Online Boutique pods `2/2`, VirtualServices present. `connection to localhost:8080 refused` means `idozacharia` has no `~/.kube/config`. Copy it from `/home/idozacharia/.kube/config` only if that file is missing, then retry. Wait up to five minutes for `Ready` after a start. Do not launch a hold before that.

- [ ] **Step 4: Pin replicas and the frontend sidecar**

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

### Task 4: S4A constrained, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4a_constrained/4a_constrained_*.yaml` files, slots only, via `bump_final_slot.py`
- Create: `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md`
- Create: `Guides and Info/2026-10-13-s4a-constrained-relock-abc.md`
- Create during pulls: `final_4a_constrained_*_run3` and `*_run4` under `experiments/results/final results/S4A_topology_position_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 3, `bump_final_slot.py`, and `s3s4_mode_matrix_gate.py`.
- Produces: ten pulled folders, five YAMLs at `run_number: 5`, ten run-log lines, and the constrained relock guide. Task 5 starts only after the cool-off from hold 10.

The files already say `run3`. Rep 1 launches that name. After a pass, or after the single replay, bump once. Rep 2 launches `run4`. The second bump leaves the file at `run5`.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 1 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3` | `run 3 -> 4` |
| 2 | same file after that bump | `normal` | `off` | `.../rg_only/final_4a_constrained_rg_only_normal_run4` | `run 4 -> 5` |
| 3 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_normal.yaml` | `normal` | `on` | `.../both/final_4a_constrained_both_normal_run3` | `run 3 -> 4` |
| 4 | same file after that bump | `normal` | `on` | `.../both/final_4a_constrained_both_normal_run4` | `run 4 -> 5` |
| 5 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4a_constrained_tf_only_run3` | `run 3 -> 4` |
| 6 | same file after that bump | `tf` | `on` | `.../tf_only/final_4a_constrained_tf_only_run4` | `run 4 -> 5` |
| 7 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3` | `run 3 -> 4` |
| 8 | same file after that bump | `burst20` | `off` | `.../rg_only/final_4a_constrained_rg_only_burst_run4` | `run 4 -> 5` |
| 9 | `experiments/configs/final_configs/4/4a_constrained/4a_constrained_both_burst.yaml` | `burst20` | `on` | `.../both/final_4a_constrained_both_burst_run3` | `run 3 -> 4` |
| 10 | same file after that bump | `burst20` | `on` | `.../both/final_4a_constrained_both_burst_run4` | `run 4 -> 5` |

Repeat Steps 1–8 for each row. The command blocks show hold 1. On later rows, substitute that row's YAML, kind, TF flag, and folder. Bump only after the gate, so the file on disk is still the slot that just ran when a replay copy is made.

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
python experiments/run_scenario.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

One process. Wait until it exits. A 600 s hold plus startup is about 12 minutes. `$exitAt` is the cool-off clock and is set only after a zero exit. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row. On the later rows, pass that row's YAML.

- [ ] **Step 5: Pull, then gate, then bump**

Pull before any bump. The YAML still names the folder that just ran.

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3" normal off
python experiments/analysis_score.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3"
```

The printed pull destination is the folder in the table. `pull_results.py` also writes `timeline.png`. Pass when all of these hold. Catalog CPU during the hold is 100 m; the replica gate stays `catalog_1`.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a` and there is no `retryguard.log`. `missing=retryguard.log` is a fail on `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. A catalog denominator of 0 is allowed. A catalog sample with `replica_count` 0 is a Not Ready flap (the pod is up and pinned at its CPU limit). Record the gate's `catalog_not_ready=N` in the run log. It is not a gate and never starts a replay. A `replica_count` above 1 is still a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0. A hold where TopFull never capped an API is a valid result, not a failure: unconstrained holds are the reference for the constrained ones and TopFull is not expected to act in them.
- No `missing=` line.

`burst_observe` is recorded. It is not a gate. A burst hold can pass with `burst_observe=no`.

Read the scorer's `Throttle data quality` table, and:

```powershell
rg "fetch failed" "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3/topfull_throttle_collector.log"
```

No match, and no API over 30 s without a fresh read, is `throttle clean`. A match or a stretch over 30 s is `throttle FLAG`. A flag does not fail this gate and does not start a replay. On a TopFull-on flag, name it in the run log and in the guide. Cap and admitted-rate numbers from that folder are carried, not measured.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

On a pass, bump the canonical file. Hold 1 prints `run 3 -> 4`. Hold 2 prints `run 4 -> 5`.

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml
```

On a fail, do not bump yet. Keep the folder. Copy the YAML that is still at the launched slot:

```powershell
New-Item -ItemType Directory -Force -Path experiments/configs/replays | Out-Null
Copy-Item experiments/configs/final_configs/4/4a_constrained/4a_constrained_rg_only_normal.yaml experiments/configs/replays/final_4a_constrained_rg_only_normal_run3_r2.yaml
```

In the copy, change only the `log_folder` line to `final_4a_constrained_rg_only_normal_run3_r2`. Leave `run_number` as the launched slot. Run Steps 1–4 with that copy, then pull and gate the `_r2` folder. Do not bump the replay copy (`bump_final_slot.py` rejects a filename that does not start with `4a_constrained_`, `4a_unconstrained_`, `4b_`, or `s3_`). After the replay, whether it passed or failed, bump the canonical file once. Do not replay a second time. The guide's column is the `_r2` folder when that replay passed, and the canonical folder when the replay failed.

- [ ] **Step 6: Finish the 120 s cool-off**

The clock is the last `run_scenario.py` exit for this row, including a replay.

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 10, leave any remainder for Task 5.

- [ ] **Step 7: Append one line per launch**

Create `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md` on hold 1:

```markdown
# S4 relock mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; catalog 100m; users 50/20/50/600/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines in `retryguard.log`, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch has no log: write `toggles n/a`.

- [ ] **Step 8: Score and write the guide**

Two calls, because `analysis_score.py` labels a folder by its `runN` suffix and then by the parent directory name. `rg_only/3` would collide between `S4A_topology_position_normal` and `S4A_topology_position_burst`. If a replay folder replaced a failed launch, pass that `_r2` path instead of the failed folder and say so in the index.

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3" `
  "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3" `
  "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3" `
  "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3" `
  "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3" `
  "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4"
```

Write `Guides and Info/2026-10-13-s4a-constrained-relock-abc.md` from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Do not edit `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`. Column headers are the `log_folder` names, holds 1–10, with a bold bar after every pair. Sections, in the template's order:

1. Setup. 600 s, mix 50 / 20 / 50 / 600 / 5, `spawn_rate` 50, Paper-C1 with catalog 100 m, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, the ten folder paths.
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
19. Related links: this plan, the template, the (a)/(b)/(c) reading, [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [ADR 0007](../../adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../adr/0008-locked-retryguard-parameters.md), [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md), and `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`. That older guide is catalog 50 m and mix 10 / 10 / 10 / 600 / 5. It is not a column here.

- [ ] **Step 9: Commit the constrained slice**

Add the five YAMLs, the run log, the new guide, and only the new `run3` and `run4` folders (plus any `_r2` replay of those names). Do not `git add` the `run1` and `run2` catalog-50m folders.

```powershell
git add experiments/configs/final_configs/4/4a_constrained docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4a-constrained-relock-abc.md"
git add -- "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run3" "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_constrained_rg_only_normal_run4" "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run3" "experiments/results/final results/S4A_topology_position_normal/both/final_4a_constrained_both_normal_run4" "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run3" "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_constrained_tf_only_run4" "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run3" "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_constrained_rg_only_burst_run4" "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run3" "experiments/results/final results/S4A_topology_position_burst/both/final_4a_constrained_both_burst_run4"
git commit -m @"
Record the S4A constrained relock matrix, two repeats of each cell.

Catalog stays at 100m on mix 50/20/50/600/5, in run3 and run4.
"@
```

If a replay YAML or a `_r2` folder was created, `git add` that path as well. Do not push.

---

### Task 5: S4A unconstrained, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_*.yaml` files, slots only
- Modify: `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md` (append)
- Create: `Guides and Info/2026-10-13-s4a-unconstrained-relock-abc.md`
- Create during pulls: ten `final_4a_unconstrained_*` folders beside the constrained ones

**Interfaces:**
- Consumes: the pin from Task 3, a finished Task 4, and the same two helpers.
- Produces: ten unconstrained folders (`run1` and `run2`), five YAMLs at `run_number: 3`, ten run-log lines, and the unconstrained guide. Task 6 starts only after the cool-off from hold 20.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 11 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1` | `run 1 -> 2` |
| 12 | same file after that bump | `normal` | `off` | `.../rg_only/final_4a_unconstrained_rg_only_normal_run2` | `run 2 -> 3` |
| 13 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_normal.yaml` | `normal` | `on` | `.../both/final_4a_unconstrained_both_normal_run1` | `run 1 -> 2` |
| 14 | same file after that bump | `normal` | `on` | `.../both/final_4a_unconstrained_both_normal_run2` | `run 2 -> 3` |
| 15 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4a_unconstrained_tf_only_run1` | `run 1 -> 2` |
| 16 | same file after that bump | `tf` | `on` | `.../tf_only/final_4a_unconstrained_tf_only_run2` | `run 2 -> 3` |
| 17 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1` | `run 1 -> 2` |
| 18 | same file after that bump | `burst20` | `off` | `.../rg_only/final_4a_unconstrained_rg_only_burst_run2` | `run 2 -> 3` |
| 19 | `experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_both_burst.yaml` | `burst20` | `on` | `.../both/final_4a_unconstrained_both_burst_run1` | `run 1 -> 2` |
| 20 | same file after that bump | `burst20` | `on` | `.../both/final_4a_unconstrained_both_burst_run2` | `run 2 -> 3` |

Constrained and unconstrained S4A share `scenario_name: topology_position_A`, so both land under `S4A_topology_position_*`. The `log_folder` prefix `final_4a_unconstrained_` is what separates them. TopFull-only still lands in `S4A_topology_position_normal/tf_only/` because RetryGuard is off.

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
python experiments/run_scenario.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

Wait for the process. About 12 minutes. A non-zero exit stops the campaign: do not pull and do not bump. Do not start the next row until this process exits. One process.

- [ ] **Step 5: Pull, then gate, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1" normal off
python experiments/analysis_score.py "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1"
rg "fetch failed" "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1/topfull_throttle_collector.log"
```

Pass when all of these hold. Catalog CPU during the hold is 800 m. The replica gate stays `catalog_1` because the HPA pin is min=max=1.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a`. `missing=retryguard.log` fails `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. A catalog denominator of 0 is allowed. A catalog sample with `replica_count` 0 is a Not Ready flap (the pod is up and pinned at its CPU limit). Record the gate's `catalog_not_ready=N` in the run log. It is not a gate and never starts a replay. A `replica_count` above 1 is still a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0. A hold where TopFull never capped an API is a valid result, not a failure: unconstrained holds are the reference for the constrained ones and TopFull is not expected to act in them.
- No `missing=` line.
- `burst_observe` is recorded and is not a gate.
- `throttle FLAG` is recorded and is not a gate. No `fetch failed` line, and no API over 30 s without a fresh read, is `throttle clean`.

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

On a pass:

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4a_unconstrained/4a_unconstrained_rg_only_normal.yaml
```

Hold 11 prints `run 1 -> 2`. Hold 12 prints `run 2 -> 3`.

On a fail, keep the folder. Copy the still-unbumped YAML to `experiments/configs/replays/final_4a_unconstrained_rg_only_normal_run1_r2.yaml` and change only its `log_folder` line to `final_4a_unconstrained_rg_only_normal_run1_r2`. Run Steps 1–4, pull, and gate once. Then bump the canonical file once. Do not bump the replay copy. Do not replay a second time. The guide's column is the `_r2` folder when that replay passed, and the canonical folder when the replay failed.

- [ ] **Step 6: Finish the 120 s cool-off, then the next row**

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 20, leave any remainder for Task 6.

- [ ] **Step 7: Append ten lines to the run log**

Append to `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md`. Do not rewrite the header. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; catalog 800m; users 50/20/50/600/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch writes `toggles n/a`.

- [ ] **Step 8: Score and write the guide**

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

Write `Guides and Info/2026-10-13-s4a-unconstrained-relock-abc.md` by following items 1–19 of [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), in that file's order. Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers are the `log_folder` names, holds 11–20, with a bold bar after every pair. Setup: 600 s, mix 50 / 20 / 50 / 600 / 5, `spawn_rate` 50, plain Paper-C1 (catalog 800 m, no constrained row), frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s. Burst bars from the scorer are `2.00 / 1.33 / 0.67`. Bold rules, the HTTP-only rejection tables, the throttle FLAG sentence, and the per-callee toggle rows are the ones in the template. Related links name this plan, the template, the constrained relock guide, and `Guides and Info/2026-10-13-s4a-constrained-mode-matrix-abc.md`. That older guide is catalog 50 m and is not a column.

- [ ] **Step 9: Commit**

```powershell
git add experiments/configs/final_configs/4/4a_unconstrained docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4a-unconstrained-relock-abc.md"
git add -- "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run1" "experiments/results/final results/S4A_topology_position_normal/rg_only/final_4a_unconstrained_rg_only_normal_run2" "experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run1" "experiments/results/final results/S4A_topology_position_normal/both/final_4a_unconstrained_both_normal_run2" "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run1" "experiments/results/final results/S4A_topology_position_normal/tf_only/final_4a_unconstrained_tf_only_run2" "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run1" "experiments/results/final results/S4A_topology_position_burst/rg_only/final_4a_unconstrained_rg_only_burst_run2" "experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run1" "experiments/results/final results/S4A_topology_position_burst/both/final_4a_unconstrained_both_burst_run2"
git commit -m @"
Record the S4A unconstrained relock matrix, two repeats of each cell.

Catalog stays at 800m on the same postcart mix, in run1 and run2.
"@
```

Add a replay path if one was created. Do not push.

---

### Task 6: S4B, ten holds

**Files:**
- Modify: the five `experiments/configs/final_configs/4/4b/4b_*.yaml` files, slots only
- Modify: `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md` (append)
- Create: `Guides and Info/2026-10-13-s4b-relock-abc.md`
- Create during pulls: ten folders under `experiments/results/final results/S4B_topology_position_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 3, a finished Task 5, and the same two helpers.
- Produces: ten `final_4b_*` folders (`run1` and `run2`), five YAMLs at `run_number: 3`, ten run-log lines, and the S4B guide.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 21 | `experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1` | `run 1 -> 2` |
| 22 | same file after that bump | `normal` | `off` | `.../rg_only/final_4b_rg_only_normal_run2` | `run 2 -> 3` |
| 23 | `experiments/configs/final_configs/4/4b/4b_both_normal.yaml` | `normal` | `on` | `.../both/final_4b_both_normal_run1` | `run 1 -> 2` |
| 24 | same file after that bump | `normal` | `on` | `.../both/final_4b_both_normal_run2` | `run 2 -> 3` |
| 25 | `experiments/configs/final_configs/4/4b/4b_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_4b_tf_only_run1` | `run 1 -> 2` |
| 26 | same file after that bump | `tf` | `on` | `.../tf_only/final_4b_tf_only_run2` | `run 2 -> 3` |
| 27 | `experiments/configs/final_configs/4/4b/4b_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S4B_topology_position_burst/rg_only/final_4b_rg_only_burst_run1` | `run 1 -> 2` |
| 28 | same file after that bump | `burst20` | `off` | `.../rg_only/final_4b_rg_only_burst_run2` | `run 2 -> 3` |
| 29 | `experiments/configs/final_configs/4/4b/4b_both_burst.yaml` | `burst20` | `on` | `.../both/final_4b_both_burst_run1` | `run 1 -> 2` |
| 30 | same file after that bump | `burst20` | `on` | `.../both/final_4b_both_burst_run2` | `run 2 -> 3` |

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
python experiments/run_scenario.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

Wait for the process. About 12 minutes. A non-zero exit stops the campaign: do not pull and do not bump. One process.

- [ ] **Step 5: Pull, then gate, then bump**

```powershell
python experiments/pull_results.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1" normal off
python experiments/analysis_score.py "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1"
rg "fetch failed" "experiments/results/final results/S4B_topology_position_normal/rg_only/final_4b_rg_only_normal_run1/topfull_throttle_collector.log"
```

Pass when all of these hold. Email CPU during the hold is 50 m. Catalog stays at the Paper-C1 800 m, and the replica gate stays `catalog_1`.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a`. `missing=retryguard.log` fails `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. A catalog denominator of 0 is allowed. A catalog sample with `replica_count` 0 is a Not Ready flap (the pod is up and pinned at its CPU limit). Record the gate's `catalog_not_ready=N` in the run log. It is not a gate and never starts a replay. A `replica_count` above 1 is still a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `topfull_rl_ran=yes`. `live5s_caps` is recorded and may be 0. A hold where TopFull never capped an API is a valid result, not a failure: unconstrained holds are the reference for the constrained ones and TopFull is not expected to act in them.
- No `missing=` line.
- `burst_observe` is recorded and is not a gate.
- `throttle FLAG` is recorded and is not a gate.

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh -o BatchMode=yes -o ControlMaster=no topfull-master "bash -s"
```

Expected: every attempts value is `3`. A route `timeout` fails the gate.

On a pass:

```powershell
python experiments/bump_final_slot.py experiments/configs/final_configs/4/4b/4b_rg_only_normal.yaml
```

Hold 21 prints `run 1 -> 2`. Hold 22 prints `run 2 -> 3`.

On a fail, keep the folder. Copy the still-unbumped YAML to `experiments/configs/replays/final_4b_rg_only_normal_run1_r2.yaml` and change only its `log_folder` line to `final_4b_rg_only_normal_run1_r2`. Run Steps 1–4, pull, and gate once. Then bump the canonical file once. Do not bump the replay copy. Do not replay a second time.

- [ ] **Step 6: Cool-off between rows**

After holds 21–29:

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 30, go to Step 7. Task 7 does not need a cool-off.

- [ ] **Step 7: Append ten lines**

Append to `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md`. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; email 50m; users 175/30/70/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch writes `toggles n/a`.

- [ ] **Step 8: Score and write the guide**

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

Write `Guides and Info/2026-10-13-s4b-relock-abc.md` by following items 1–19 of [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), in that file's order. Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers are the `log_folder` names, holds 21–30, with a bold bar after every pair. Setup: 600 s, mix 175 / 30 / 70 / 90 / 5, `spawn_rate` 50, Paper-C1 with `emailservice` 50 m, frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s. Burst bars from the scorer are `2.00 / 1.33 / 0.67`. Bold rules, the HTTP-only rejection tables, the throttle FLAG sentence, and the per-callee toggle rows are the ones in the template. Related links name this plan, the template, and `campaign_48/` S4B. That campaign used paymentservice. Do not add it as a column.

- [ ] **Step 9: Commit**

```powershell
git add experiments/configs/final_configs/4/4b docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md "Guides and Info/2026-10-13-s4b-relock-abc.md" "experiments/results/final results/S4B_topology_position_normal" "experiments/results/final results/S4B_topology_position_burst"
git commit -m @"
Record the S4B relock matrix, two repeats of each cell.

Email stays at 50m on the S1 mix, with run1 and run2 kept apart.
"@
```

Add a replay path if one was created. Do not push.

---

### Task 7: Restore the unpinned shape

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 3, and a finished hold 30.
- Produces: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, frontend app 1150 m. The three VMs are still `RUNNING`. Task 9 stops them.

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

- [ ] **Step 3: Confirm the VMs are still RUNNING**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are `RUNNING`. Do not stop them here. Task 9 stops them after the STATUS commit.

---

### Task 8: STATUS, AGENTS, and the slot check

**Files:**
- Modify: `STATUS.md` Done (one bullet) and the Next free slots lines for `4/4a_constrained/`, `4/4a_unconstrained/`, and `4/4b/`
- Modify: `AGENTS.md` §4, the three Latest lines
- Test: the slot assertion below

**Interfaces:**
- Consumes: the run log, the three guides, five constrained YAMLs at `run_number: 5`, and ten unconstrained plus S4B YAMLs at `run_number: 3`.
- Produces: STATUS and AGENTS describing this campaign. S1, S2, and S3 final_configs stay at their current slots (S1 and S2 at run 1, S3 at run 3). Historical `scenario_*.yaml` slots stay as they are.

- [ ] **Step 1: Confirm the fifteen slots**

```powershell
python -c @"
import yaml
from pathlib import Path
root = Path('experiments/configs/final_configs/4')
constrained = list((root / '4a_constrained').glob('4a_constrained_*.yaml'))
unconstrained = list((root / '4a_unconstrained').glob('4a_unconstrained_*.yaml'))
s4b = list((root / '4b').glob('4b_*.yaml'))
assert len(constrained) == 5 and len(unconstrained) == 5 and len(s4b) == 5
for path in constrained:
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert cfg['run_number'] == 5, path
    assert cfg['log_folder'].endswith('_run5'), path
for path in unconstrained + s4b:
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert cfg['run_number'] == 3, path
    assert cfg['log_folder'].endswith('_run3'), path
s3 = list(Path('experiments/configs/final_configs/3').glob('s3_*.yaml'))
assert all(yaml.safe_load(p.read_text(encoding='utf-8'))['run_number'] == 3 for p in s3)
print('slots ok: constrained run 5, unconstrained and S4B run 3, S3 still run 3')
"@
python experiments/test_bump_final_slot.py
python experiments/test_run_scenario.py TestFinalConfigs
```

Expected: the print line above, then both test modules `OK`.

- [ ] **Step 2: Update Next free slots**

In `STATUS.md`, replace the sentence that says all 30 `final_configs` files are at run 1. The replacement is: `experiments/configs/final_configs/` slots are per folder below. S1 and S2 are run 1. S3 is run 3. S4A constrained is run 5. S4A unconstrained and S4B are run 3.

Change these three trailing numbers and leave every other slot line as it is:

- `experiments/configs/final_configs/4/4a_constrained/` — from `3` to `5`
- `experiments/configs/final_configs/4/4a_unconstrained/` — from `1` to `3`
- `experiments/configs/final_configs/4/4b/` — from `1` to `3`

`final_configs/1/` and `final_configs/2/` stay at `1`. `final_configs/3/` stays at `3`. The historical `scenario_*.yaml` list stays as it is.

- [ ] **Step 3: Append one Done bullet and replace the three Latest lines**

Append one bullet under Done in `STATUS.md`. Name the thirty `log_folder` values, the PASS and INVALID counts copied from the run log, any throttle FLAG holds, and the paths of the run log and the three guides. Say constrained YAMLs were left at run 5, unconstrained and S4B YAMLs at run 3, S1–S3 final_configs were not moved, the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, and the three VMs were still RUNNING. Task 9 replaces that clause after it stops them.

Replace the three Latest lines in `AGENTS.md` §4. Do not append a fourth. The three lines are:

1. This matrix: branch `s4-relock-mode-matrix` from `e26f05c`, thirty holds, S4A constrained catalog 100 m on mix 50/20/50/600/5 in `run3` and `run4`, S4A unconstrained catalog 800 m on that mix in `run1` and `run2`, S4B email 50 m on mix 175/30/70/90/5 in `run1` and `run2`. Next free slots: constrained run 5, unconstrained run 3, S4B run 3.
2. The PASS, INVALID, and throttle FLAG counts copied from `docs/superpowers/plans/2026-10-13-s4-relock-mode-matrix-run-log.md`, plus the three guide paths.
3. The restored cluster and the three VMs still RUNNING. Task 9 replaces that clause after it stops them.

Keep the Still open list. Add one sentence there that this matrix is the locked S4A/S4B set under `final results/`, and that the catalog-50m mode matrix and `campaign_48/` S4A/S4B are not comparable.

- [ ] **Step 4: Commit**

```powershell
git add STATUS.md AGENTS.md
git commit -m @"
Record the S4 relock slots and the restored cluster.

Constrained YAMLs sit at run 5, unconstrained and S4B at run 3, and the VMs were left running.
"@
git status --short
git branch --show-current
git rev-parse --abbrev-ref HEAD
git merge-base --is-ancestor e26f05c HEAD; if ($LASTEXITCODE -eq 0) { "FROM_MAIN" } else { "NOT_FROM_MAIN" }
```

Expected: branch `s4-relock-mode-matrix`, working tree clean, and `FROM_MAIN`. Do not push in this task. Do not check this branch out in the primary checkout. Task 9 pushes and merges.

---

### Task 9: Stop the VMs, push, and merge into local main

**Files:**
- Modify: the "still RUNNING" clause in the `STATUS.md` Done bullet and in `AGENTS.md` §4 Latest line 3

**Interfaces:**
- Consumes: a finished Task 8. Branch `s4-relock-mode-matrix` contains every campaign commit. The HPA restore from Task 7 is already done.
- Produces: the three VMs `TERMINATED`, `origin/s4-relock-mode-matrix` matching this branch, and local `main` in the primary checkout containing the merge. `main` is not pushed.

- [ ] **Step 1: Commit anything still uncommitted on the branch**

Run from the worktree:

```powershell
git branch --show-current
git status --short
```

Expected: branch `s4-relock-mode-matrix`. A clean status means go to Step 2. If the status lists campaign files (the run log, a guide, the fifteen S4 YAMLs, a `final_4a_*` or `final_4b_*` folder, a replay YAML, `STATUS.md`, or `AGENTS.md`), commit those files with a message that names what was left out. Do not commit unrelated files. Do not add the catalog-50m `run1` and `run2` folders. Any other dirty path means stop.

- [ ] **Step 2: Stop the three VMs**

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: `topfull-master`, `topfull-worker-1`, and `topfull-load` are `TERMINATED`. Pass `--project` so a leftover `networks-workshop` config cannot stop the original VMs. Do not start those originals. Do not stop any other instance.

- [ ] **Step 3: Record the stop, then confirm the branch is fully committed**

In the `STATUS.md` Done bullet and in `AGENTS.md` §4 Latest line 3, replace the clause that says the three VMs were still RUNNING. The replacement says the three VMs were stopped (`topfull-master`, `topfull-worker-1`, `topfull-load` `TERMINATED`).

```powershell
git add STATUS.md AGENTS.md
git commit -m @"
Record that the S4 relock VMs were stopped.

The three campaign VMs are TERMINATED after the HPA restore.
"@
git status --short
```

Expected: `git status --short` prints nothing. If it prints anything, commit the remaining campaign files or stop. Do not push a dirty tree.

- [ ] **Step 4: Push the branch**

```powershell
git push -u origin HEAD
git status -sb
```

Expected: `s4-relock-mode-matrix` tracks `origin/s4-relock-mode-matrix` and the short status has no `ahead`. Do not push `main`. Do not force-push.

- [ ] **Step 5: Merge into local main**

Run from the primary checkout `c:\Users\sagi1\Projects\Workshop`, not from the worktree:

```powershell
git branch --show-current
git status --short
git merge s4-relock-mode-matrix
git log -1 --oneline
```

Expected: the current branch is `main` before the merge, and after it `HEAD` is the merge of `s4-relock-mode-matrix`. Do not check `s4-relock-mode-matrix` out in the primary checkout. If `git status --short` lists uncommitted files, do not stash them, do not discard them, and do not add them. Merge only when those files do not overlap the branch. If the merge would touch them, stop and report. Do not push `main`.
