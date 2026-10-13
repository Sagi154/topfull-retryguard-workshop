# S2 mode matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These ten holds share one cluster. Run the hold task in order in one session. Do not run two holds at once.

**Goal:** Run the locked S2 configs twice each for five controller cells: RetryGuard-only normal, both-on normal, TopFull-only, RetryGuard-only burst, and both-on burst.

**Architecture:** The five YAMLs under `experiments/configs/final_configs/2/` are already the locked cells on `main` at `4ee1975`. The campaign commits land on branch `s2-mode-matrix` in a linked worktree, so the primary checkout stays on `main`. Each cell is launched twice, back to back. Pull uses the YAML before `bump_final_slot.py` advances it. `bump_final_slot.py` currently refuses an `s2_` filename; Task 2 adds that prefix and nothing else. Results land in `experiments/results/final results/`. One analysis guide covers all ten folders. The three VMs stay RUNNING.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/bump_final_slot.py`, `experiments/s3s4_mode_matrix_gate.py`, PowerShell, `ssh`, `gcloud`. No controller changes. Do not rename the gate script. Do not recreate either helper.

## Global Constraints

- Branch is `s2-mode-matrix`, created from `main` at `4ee1975` (`Merge pull request #9 from Sagi154/runs-analysis2`). All campaign commands run in `c:\Users\sagi1\Projects\Workshop\.worktrees\s2-mode-matrix`. The primary checkout stays on `main`. Do not merge. Do not push. Do not touch `.worktrees/s4-relock-mode-matrix` or `.worktrees/topfull-throttle-collector`.
- Ten holds, 600 s each, `spawn_rate` 50. Wall clock is about 3 hours (about 12 minutes of startup plus load, then a 120 s cool-off, plus scoring). One hold at a time.
- Cell order: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. Two launches of one cell, then the next cell.
- Locked RetryGuard values, already in the YAMLs: `retry_metric` `edge_rpr`, `sample_interval_seconds` 1, `interval_samples` 20, `rejection_threshold` 0.2, `retries_threshold` 0.4, `climb_rpr_1_to_2` 0.16, `climb_rpr_2_to_3` 0.32, `climb_interval_seconds` 10, `reenable_rejection` 0.25. Burst adds `burst_rpr` 2.0, `burst_window_seconds` 5, `burst_min_first_attempts` 20. Normal mode omits those three keys.
- S2 mix `275 / 90 / 100 / 90 / 5` (getproduct / postcheckout / getcart / postcart / emptycart). Paper-C1 is unchanged on every row: checkout 800, recommendations 1150, catalog 800, cart 800, currency 770, shipping 770, ad 1150, payment 155, email 120, redis-cart 540. Frontend 1150 m is the HPA pin and is not a `scale_constraints` row. Source: [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md).
- The only YAML edits on those five files are `run_number` and `log_folder`, and only through `python experiments/bump_final_slot.py <file>`, and only after that launch's pull and gate. `tf_only` contains the three burst keys and keeps them; RetryGuard is off, so its result directory is `normal`.
- Leave `experiments/configs/scenario_*.yaml` and the S1, S3, and S4 files under `final_configs/` at their current slots. Do not run `experiments/make_final_configs.py`. Do not use `run_all_scenarios.py`. Do not delete or rewrite the existing `study*` and `s2_burst20_*` folders under `experiments/results/final results/S2_sustained_overload_normal/` and `S2_sustained_overload_burst/`.
- A failed collector gate keeps its folder. Replay that launch once from a copy under `experiments/configs/replays/` whose `log_folder` has an `_r2` suffix. Then bump the canonical file once. Do not replay a second time. A finished hold with zero `ON→OFF` lines still passes. Toggle count is recorded and is not a gate.
- A throttle **FLAG** (any `fetch failed` WARNING, or any API over 30 s with no fresh threshold or admitted read) is written in the run log. It does not fail the collector gate and does not trigger a replay. Goodput, P95, rejection, and retry numbers stay valid. Cap and admitted-rate numbers from a flagged hold are not used as measured.
- Cool-off is 120 s, starting when `run_scenario.py` exits. Pull, the gate, and scoring of that one folder happen during the wait. Checkout and recommendations stay up. `restart_before_hold` stays absent.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`), Linux user `idozacharia`, project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. The `networks-workshop` project stays stopped. Do not hardcode a public IP.
- Paper-C1 replica pin for the whole campaign: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `sidecar.istio.io/proxyCPU=90m`, `proxyCPULimit` unset. Restore once at the end to frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset. Leave the three VMs RUNNING.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`).
- Commands run from `c:\Users\sagi1\Projects\Workshop\.worktrees\s2-mode-matrix`.

## File Structure

- Modify, before any hold: `experiments/bump_final_slot.py` (allow the `s2_` filename prefix) and `experiments/test_bump_final_slot.py`.
- Read-only, already on `4ee1975`: `experiments/s3s4_mode_matrix_gate.py`, `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/retryguard.py`.
- Modify during the runs, slots only: the five YAMLs in the hold table. After the campaign, each file is `run_number: 3` and `log_folder: final_s2_<variant>_run3`.
- Create on the branch, first commit: this plan, copied into the worktree. `4ee1975` does not contain it.
- Create during the runs: `docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md` — one line per launch, including a failed launch and its single replay.
- Create after the ten pulls: `Guides and Info/2026-10-14-s2-mode-matrix-abc.md`.
- Modify after the VMs are confirmed still RUNNING: `STATUS.md` (one Done bullet; the `final_configs/2/` next-free line) and `AGENTS.md` §4 (replace the three Latest lines).
- Create only if a gate fails: `experiments/configs/replays/final_s2_<variant>_run<N>_r2.yaml`.

`run_scenario.py` `final_results_local_dir` sends a config to `experiments/results/final results/S2_sustained_overload_<normal|burst>/<variant>/<log_folder>/`. Mode is `burst` only when RetryGuard is on and `burst_rpr` is set. TopFull-only is `normal`.

| # | Cell | YAML | `log_folder` rep 1, then rep 2 | Kind | TF | Result mode |
| --- | --- | --- | --- | --- | --- | --- |
| 1–2 | rg only normal | `experiments/configs/final_configs/2/s2_rg_only_normal.yaml` | `final_s2_rg_only_normal_run1`, `_run2` | `normal` | `off` | `normal` |
| 3–4 | both normal | `experiments/configs/final_configs/2/s2_both_normal.yaml` | `final_s2_both_normal_run1`, `_run2` | `normal` | `on` | `normal` |
| 5–6 | tf only | `experiments/configs/final_configs/2/s2_tf_only.yaml` | `final_s2_tf_only_run1`, `_run2` | `tf` | `on` | `normal` |
| 7–8 | rg only burst | `experiments/configs/final_configs/2/s2_rg_only_burst.yaml` | `final_s2_rg_only_burst_run1`, `_run2` | `burst20` | `off` | `burst` |
| 9–10 | both burst | `experiments/configs/final_configs/2/s2_both_burst.yaml` | `final_s2_both_burst_run1`, `_run2` | `burst20` | `on` | `burst` |

Result roots:

- Normal and TopFull-only: `experiments/results/final results/S2_sustained_overload_normal/<rg_only|both|tf_only>/`
- Burst: `experiments/results/final results/S2_sustained_overload_burst/<rg_only|both>/`

---

### Task 1: Cut a worktree from main

**Files:**
- Create: `c:\Users\sagi1\Projects\Workshop\.worktrees\s2-mode-matrix\` (linked worktree; `.worktrees/` is gitignored)
- Create on the new branch: `docs/superpowers/plans/2026-10-14-s2-mode-matrix.md` (this file)

**Interfaces:**
- Consumes: primary checkout `c:\Users\sagi1\Projects\Workshop` on `main` at `4ee1975`. `.gitignore` already contains `.worktrees/`.
- Produces: branch `s2-mode-matrix` checked out only in the worktree. Later tasks run with that directory as the working directory. The primary checkout remains on `main`.

- [ ] **Step 1: Confirm main, a clean ignore rule, and that the branch name is free**

Run from `c:\Users\sagi1\Projects\Workshop`:

```powershell
git branch --show-current
git rev-parse --short HEAD
git check-ignore -q .worktrees/s2-mode-matrix; if ($LASTEXITCODE -eq 0) { "IGNORED" } else { "NOT_IGNORED" }
git branch --list s2-mode-matrix
git worktree list
```

Expected: branch `main`, HEAD `4ee1975`, output `IGNORED`, and `git branch --list` prints nothing. `git worktree list` already shows the primary checkout, `.worktrees/s4-relock-mode-matrix`, and `.worktrees/topfull-throttle-collector`. A dirty primary checkout (uncommitted `AGENTS.md`, `STATUS.md`, or `experiments/graphs_tool.py`) is expected. Do not stash it and do not add those files. Any other HEAD, a missing ignore, or an existing `s2-mode-matrix` branch means stop. Do not add a second worktree for a branch that exists.

- [ ] **Step 2: Create the worktree**

If the harness has a native worktree command, use it to create branch `s2-mode-matrix` from `4ee1975` and then skip the `git worktree add` line. Otherwise:

```powershell
git worktree add -b s2-mode-matrix .worktrees/s2-mode-matrix 4ee1975
git -C .worktrees/s2-mode-matrix branch --show-current
git -C .worktrees/s2-mode-matrix rev-parse --short HEAD
git branch --show-current
```

Expected: the worktree is on `s2-mode-matrix` at `4ee1975`. The last command, run in the primary checkout, still prints `main`.

- [ ] **Step 3: Put this plan on the branch**

`4ee1975` does not contain this plan. From the primary checkout, copy it into the worktree and commit it there:

```powershell
New-Item -ItemType Directory -Force -Path .worktrees/s2-mode-matrix/docs/superpowers/plans | Out-Null
Copy-Item docs/superpowers/plans/2026-10-14-s2-mode-matrix.md .worktrees/s2-mode-matrix/docs/superpowers/plans/2026-10-14-s2-mode-matrix.md
git -C .worktrees/s2-mode-matrix add docs/superpowers/plans/2026-10-14-s2-mode-matrix.md
git -C .worktrees/s2-mode-matrix commit -m @"
Add the S2 mode-matrix plan.

Ten holds use the locked run-89 mix, two repeats of each controller cell.
"@
git -C .worktrees/s2-mode-matrix status --short
git -C .worktrees/s2-mode-matrix log -1 --oneline
```

Expected: worktree status empty, and the new commit's parent is `4ee1975`. Do not commit this file on `main`. Every later command uses working directory `c:\Users\sagi1\Projects\Workshop\.worktrees\s2-mode-matrix`.

---

### Task 2: Let the slot bump accept S2 files

**Files:**
- Modify: `experiments/bump_final_slot.py`
- Test: `experiments/test_bump_final_slot.py`

**Interfaces:**
- Consumes: `bump_text` and `bump_file` as they are on `4ee1975`. `ALLOWED_PREFIXES` is `("s3_", "4a_constrained_", "4a_unconstrained_", "4b_")`. `bump_file` refuses a path whose name does not start with one of those, and refuses a path that does not contain `final_configs`.
- Produces: `ALLOWED_PREFIXES` includes `"s2_"`. `bump_file(Path(".../final_configs/2/s2_rg_only_normal.yaml"))` returns the new run number. A replay copy named `final_s2_rg_only_normal_run1_r2.yaml` is still refused, because its name does not start with `s2_` and its directory is not `final_configs`.

- [ ] **Step 1: Write the failing test**

Add this method to `TestBumpFileGuard` in `experiments/test_bump_final_slot.py`:

```python
    def test_accepts_s2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_configs" / "2" / "s2_rg_only_normal.yaml"
            path.parent.mkdir(parents=True)
            text = SAMPLE.replace(
                "final_s3_rg_only_normal", "final_s2_rg_only_normal"
            ).replace("\n", "\r\n")
            path.write_bytes(text.encode("utf-8"))
            self.assertEqual(bump_final_slot.bump_file(path), 2)
            raw = path.read_bytes()
            self.assertIn(b"log_folder: final_s2_rg_only_normal_run2\r\n", raw)
            self.assertIn(b"run_number: 2\r\n", raw)
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
python experiments/test_bump_final_slot.py TestBumpFileGuard.test_accepts_s2 -v
```

Expected: FAIL. `bump_file` raises `SystemExit` with `not an S3/S4 campaign file`.

- [ ] **Step 3: Write the minimal implementation**

In `experiments/bump_final_slot.py`, change the module docstring's first sentence to `Advance run_number and log_folder on one S2/S3/S4 final_configs YAML.` Change `ALLOWED_PREFIXES` to:

```python
ALLOWED_PREFIXES = (
    "s2_",
    "s3_",
    "4a_constrained_",
    "4a_unconstrained_",
    "4b_",
)
```

Change the refusal line to:

```python
        raise SystemExit(f"refusing {path}: not an S2/S3/S4 campaign file")
```

Leave `bump_text` unchanged. An `s1_` file still fails. A file named `final_s2_rg_only_normal_run1_r2.yaml` still fails the prefix check.

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python experiments/test_bump_final_slot.py -v
```

Expected: every test `ok`, including `test_accepts_s2`, `test_refuses_s1`, and `test_refuses_replay_suffix`. Exit code 0.

- [ ] **Step 5: Commit**

```powershell
git add experiments/bump_final_slot.py experiments/test_bump_final_slot.py
git commit -m @"
Let the slot bump accept the S2 final configs.

The five locked S2 files can advance run_number without a hand edit.
"@
```

---

### Task 3: Confirm the five YAMLs and the free slots

**Files:** none modified. Read the five YAMLs and `experiments/results/final results/`.

**Interfaces:**
- Consumes: the worktree after Task 2. The five files are still `run_number: 1`.
- Produces: a printed `SLOTS_OK` line and ten `ABSENT` lines. Hold tasks start only after both pass. Launch names are `run1` then `run2`.

- [ ] **Step 1: Assert mix, CPU, controllers, and starting slots**

```powershell
python -c @"
import yaml
from pathlib import Path

root = Path('experiments/configs/final_configs/2')
variants = ['rg_only_normal', 'both_normal', 'tf_only', 'rg_only_burst', 'both_burst']
users = {'getproduct': 275, 'postcheckout': 90, 'getcart': 100, 'postcart': 90, 'emptycart': 5}
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
n = 0
for variant in variants:
    path = root / f's2_{variant}.yaml'
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert cfg['run_number'] == 1, path
    assert cfg['log_folder'] == f'final_s2_{variant}_run1', cfg['log_folder']
    assert cfg['scenario_name'] == 'sustained_overload', path
    assert cfg['duration_seconds'] == 600, path
    assert 'restart_before_hold' not in cfg, path
    assert cfg['locust']['user_counts'] == users, path
    assert cfg['locust']['spawn_rate'] == 50, path
    limits = {row['deployment']: row['cpu_limit_millicores'] for row in cfg['scale_constraints']}
    assert limits == cpu, (path, limits)
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
assert n == 5
print('SLOTS_OK')
"@
```

Expected: `SLOTS_OK`. Any `AssertionError` means stop. Do not edit a YAML by hand to make this pass.

- [ ] **Step 2: Confirm the ten new folders are absent**

```powershell
$wantAbsent = @(
  "S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1",
  "S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run2",
  "S2_sustained_overload_normal/both/final_s2_both_normal_run1",
  "S2_sustained_overload_normal/both/final_s2_both_normal_run2",
  "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1",
  "S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2",
  "S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1",
  "S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2",
  "S2_sustained_overload_burst/both/final_s2_both_burst_run1",
  "S2_sustained_overload_burst/both/final_s2_both_burst_run2"
)
foreach ($n in $wantAbsent) {
  $p = "experiments/results/final results/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `ABSENT` ten times. An `EXISTS` line means stop. Older folders such as `s2_burst20_rgtf0` and `study6_s2_normal_rgtf1_rep1` may be present. Leave them.

---

### Task 4: Bring the cluster up and pin Paper-C1 replicas

**Files:** none.

**Interfaces:**
- Consumes: SSH aliases and project `project-76deda76-55f1-42d2-abb`.
- Produces: three VMs `RUNNING`, `kubectl get nodes` Ready, frontend HPA 4/4, catalog HPA 1/1, sidecar `90m` with `proxyCPULimit` empty, four frontend pods `2/2`, and no Locust or master writer already alive. Hold tasks assume this pin is still in place.

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

### Task 5: Ten S2 holds

**Files:**
- Modify: the five `experiments/configs/final_configs/2/s2_*.yaml` files, slots only, via `bump_final_slot.py`
- Create: `docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md`
- Create: `Guides and Info/2026-10-14-s2-mode-matrix-abc.md`
- Create during pulls: the ten `final_s2_*_run1` and `*_run2` folders under `experiments/results/final results/S2_sustained_overload_<normal|burst>/`

**Interfaces:**
- Consumes: the pin from Task 4, `bump_final_slot.py` after Task 2, and `s3s4_mode_matrix_gate.py`.
- Produces: ten pulled folders, five YAMLs at `run_number: 3`, ten run-log lines, and the S2 guide. Task 6 starts only after the cool-off from hold 10.

The files already say `run1`. Rep 1 launches that name. After a pass, or after the single replay, bump once. Rep 2 launches `run2`. The second bump leaves the file at `run3`.

| Hold | YAML | Kind | TF | Folder after pull | Bump print |
| --- | --- | --- | --- | --- | --- |
| 1 | `experiments/configs/final_configs/2/s2_rg_only_normal.yaml` | `normal` | `off` | `experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1` | `run 1 -> 2` |
| 2 | same file after that bump | `normal` | `off` | `.../rg_only/final_s2_rg_only_normal_run2` | `run 2 -> 3` |
| 3 | `experiments/configs/final_configs/2/s2_both_normal.yaml` | `normal` | `on` | `.../both/final_s2_both_normal_run1` | `run 1 -> 2` |
| 4 | same file after that bump | `normal` | `on` | `.../both/final_s2_both_normal_run2` | `run 2 -> 3` |
| 5 | `experiments/configs/final_configs/2/s2_tf_only.yaml` | `tf` | `on` | `.../tf_only/final_s2_tf_only_run1` | `run 1 -> 2` |
| 6 | same file after that bump | `tf` | `on` | `.../tf_only/final_s2_tf_only_run2` | `run 2 -> 3` |
| 7 | `experiments/configs/final_configs/2/s2_rg_only_burst.yaml` | `burst20` | `off` | `experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1` | `run 1 -> 2` |
| 8 | same file after that bump | `burst20` | `off` | `.../rg_only/final_s2_rg_only_burst_run2` | `run 2 -> 3` |
| 9 | `experiments/configs/final_configs/2/s2_both_burst.yaml` | `burst20` | `on` | `.../both/final_s2_both_burst_run1` | `run 1 -> 2` |
| 10 | same file after that bump | `burst20` | `on` | `.../both/final_s2_both_burst_run2` | `run 2 -> 3` |

Repeat Steps 1–7 for each row. The command blocks show hold 1. On later rows, substitute that row's YAML, kind, TF flag, and folder. Bump only after the gate, so the file on disk is still the slot that just ran when a replay copy is made.

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
python experiments/run_scenario.py experiments/configs/final_configs/2/s2_rg_only_normal.yaml
if ($LASTEXITCODE -ne 0) { throw "run_scenario.py exited $LASTEXITCODE" }
$exitAt = Get-Date
```

One process. Wait until it exits. A 600 s hold plus startup is about 12 minutes. `$exitAt` is the cool-off clock and is set only after a zero exit. A non-zero exit stops the campaign: do not pull, do not bump, do not start the next row. On the later rows, pass that row's YAML.

- [ ] **Step 5: Pull, then gate, then bump**

Pull before any bump. The YAML still names the folder that just ran.

```powershell
python experiments/pull_results.py experiments/configs/final_configs/2/s2_rg_only_normal.yaml
python experiments/s3s4_mode_matrix_gate.py "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1" normal off
python experiments/analysis_score.py "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1"
```

The printed pull destination is the folder in the table. `pull_results.py` also writes `timeline.png`. Pass when all of these hold. Catalog CPU during the hold is 800 m; the replica gate stays `catalog_1`.

- `locust_rows` is 540–580.
- `start_missing=none` for `normal` and `burst20`. For `tf`, `start_missing=n/a` and there is no `retryguard.log`. `missing=retryguard.log` is a fail on `normal` and `burst20` only.
- `patch_fail=no`.
- `frontend_4` equals its denominator, and the denominator is at least 1. `catalog_1` equals its denominator, and that denominator is at least 1. A catalog sample whose `replica_count` is not 1 is a fail.
- TF `off`: `live5s_caps=0` and `other=0`. A live 0 is an empty read.
- TF `on`: `live5s_caps` is at least 1.
- No `missing=` line.

`burst_observe` is recorded. It is not a gate. A burst hold can pass with `burst_observe=no`.

Read the scorer's `Throttle data quality` table, and:

```powershell
rg "fetch failed" "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1/topfull_throttle_collector.log"
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
python experiments/bump_final_slot.py experiments/configs/final_configs/2/s2_rg_only_normal.yaml
```

On a fail, do not bump yet. Keep the folder. Copy the YAML that is still at the launched slot:

```powershell
New-Item -ItemType Directory -Force -Path experiments/configs/replays | Out-Null
Copy-Item experiments/configs/final_configs/2/s2_rg_only_normal.yaml experiments/configs/replays/final_s2_rg_only_normal_run1_r2.yaml
```

In the copy, change only the `log_folder` line to `final_s2_rg_only_normal_run1_r2`. Leave `run_number` as the launched slot. Run Steps 1–4 with that copy, then pull and gate the `_r2` folder. Do not bump the replay copy. `bump_final_slot.py` rejects it: the filename starts with `final_s2_`, not `s2_`, and the directory is not under `final_configs`. After the replay, whether it passed or failed, bump the canonical file once. Do not replay a second time. The guide's column is the `_r2` folder when that replay passed, and the canonical folder when the replay failed.

- [ ] **Step 6: Finish the 120 s cool-off**

The clock is the last `run_scenario.py` exit for this row, including a replay.

```powershell
$elapsed = ((Get-Date) - $exitAt).TotalSeconds
if ($elapsed -lt 120) { Start-Sleep -Seconds ([int](120 - $elapsed)) }
```

Then Steps 1–3 again before the next row. After hold 10, leave any remainder for Task 6.

- [ ] **Step 7: Append one line per launch**

Create `docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md` on hold 1:

```markdown
# S2 mode matrix — run log

One line per launch, including a failed launch and its single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; normal or burst_rpr 2.0 or tf; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; catalog_1=N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; throttle clean or throttle FLAG; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines in `retryguard.log`, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. A `tf` launch has no log: write `toggles n/a`.

- [ ] **Step 8: Score and write the guide**

Two calls, because `analysis_score.py` labels a folder by its `runN` suffix and then by the parent directory name. `rg_only/1` would collide between `S2_sustained_overload_normal` and `S2_sustained_overload_burst`. If a replay folder replaced a failed launch, pass that `_r2` path instead of the failed folder and say so in the index.

```powershell
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1" `
  "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run2" `
  "experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run1" `
  "experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run2" `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1" `
  "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2"
python experiments/analysis_score.py --sep 2 `
  "experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1" `
  "experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2" `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run1" `
  "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run2"
```

Write `Guides and Info/2026-10-14-s2-mode-matrix-abc.md` from [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md). Paste scorer tables. Do not type a number that is not in the scorer output or in `retryguard.log`. Column headers are the `log_folder` names, holds 1–10, with a bold bar after every pair. Sections, in the template's order:

1. Setup. 600 s, mix 275 / 90 / 100 / 90 / 5, `spawn_rate` 50, Paper-C1 unchanged (catalog 800 m, email 120 m), frontend HPA 4, catalog HPA 1, sidecar 90 m, cool-off 120 s, the ten folder paths.
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
19. Related links: this plan, the template, the (a)/(b)/(c) reading, [RETRYGUARD-IMPLEMENTATION.md](../../../Guides%20and%20Info/RETRYGUARD-IMPLEMENTATION.md), [ADR 0007](../../adr/0007-burst-mode-sliding-aggregate.md), [ADR 0008](../../adr/0008-locked-retryguard-parameters.md), and [ADR 0009](../../adr/0009-paper-c1-default-cpu-table.md). Older S2 folders (`study*`, `s2_burst20_*`, `campaign_48/`, bar 1.5) are not columns.

- [ ] **Step 9: Commit the ten folders**

Add the five YAMLs, the run log, the guide, and only the ten new `final_s2_*` folders. Do not `git add` the parent `S2_sustained_overload_normal` or `S2_sustained_overload_burst` directories. Those already contain older holds.

```powershell
git add experiments/configs/final_configs/2 docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md "Guides and Info/2026-10-14-s2-mode-matrix-abc.md"
git add -- "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run1" "experiments/results/final results/S2_sustained_overload_normal/rg_only/final_s2_rg_only_normal_run2" "experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run1" "experiments/results/final results/S2_sustained_overload_normal/both/final_s2_both_normal_run2" "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run1" "experiments/results/final results/S2_sustained_overload_normal/tf_only/final_s2_tf_only_run2" "experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run1" "experiments/results/final results/S2_sustained_overload_burst/rg_only/final_s2_rg_only_burst_run2" "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run1" "experiments/results/final results/S2_sustained_overload_burst/both/final_s2_both_burst_run2"
git commit -m @"
Record the S2 mode matrix, two repeats of each cell.

The locked 275/90/100/90/5 mix stays on Paper-C1, in run1 and run2.
"@
```

If a replay YAML or a `_r2` folder was created, `git add` that path as well. Do not push.

---

### Task 6: Restore the unpinned shape

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 4, and a finished hold 10.
- Produces: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, frontend app 1150 m. The three VMs stay `RUNNING`.

- [ ] **Step 1: Stop leftover writers**

If hold 10's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

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

### Task 7: STATUS, AGENTS, and the slot check

**Files:**
- Modify: `STATUS.md` Done (one bullet) and the Next free slots line for `final_configs/2/`
- Modify: `AGENTS.md` §4, the three Latest lines
- Test: the slot assertion below

**Interfaces:**
- Consumes: the run log, the guide, and five YAMLs at `run_number: 3`.
- Produces: STATUS and AGENTS describing this campaign. S1 stays at run 1. S3 stays at run 3. S4A constrained stays at run 3. S4A unconstrained and S4B stay at run 1. Historical `scenario_*.yaml` slots stay as they are.

- [ ] **Step 1: Confirm the five slots**

```powershell
python -c @"
import yaml
from pathlib import Path
s2 = list(Path('experiments/configs/final_configs/2').glob('s2_*.yaml'))
assert len(s2) == 5
for path in s2:
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert cfg['run_number'] == 3, path
    assert cfg['log_folder'].endswith('_run3'), path
s1 = list(Path('experiments/configs/final_configs/1').glob('s1_*.yaml'))
s3 = list(Path('experiments/configs/final_configs/3').glob('s3_*.yaml'))
assert all(yaml.safe_load(p.read_text(encoding='utf-8'))['run_number'] == 1 for p in s1)
assert all(yaml.safe_load(p.read_text(encoding='utf-8'))['run_number'] == 3 for p in s3)
print('slots ok: S2 run 3, S1 still run 1, S3 still run 3')
"@
python experiments/test_bump_final_slot.py
python experiments/test_run_scenario.py TestFinalConfigs
```

Expected: the print line above, then both test modules `OK`.

- [ ] **Step 2: Update Next free slots**

In `STATUS.md`, replace the sentence that says all 30 `final_configs` files are at run 1. The replacement is: `experiments/configs/final_configs/` slots are per folder below. This campaign moved `final_configs/2/` from run 1 to run 3. S1 stays at run 1. S3 stays at run 3. S4A constrained stays at run 3. S4A unconstrained and S4B stay at run 1.

Change this one trailing number and leave every other slot line as it is:

- `experiments/configs/final_configs/2/` — from `1` to `3`

The historical `scenario_*.yaml` list stays as it is. Do not change `scenario_2_baseline.yaml` (41), `scenario_2_retryguard.yaml` (30), or `scenario_2_retryguard_no_topfull.yaml` (22).

- [ ] **Step 3: Append one Done bullet and replace the three Latest lines**

Append one bullet under Done in `STATUS.md`. Name the ten `log_folder` values, the PASS and INVALID counts copied from the run log, any throttle FLAG holds, and the paths of the run log and the guide. Say the five S2 YAMLs were left at run 3, S1 and S3 and S4 final_configs were not moved, the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m, and the three VMs were left RUNNING.

Replace the three Latest lines in `AGENTS.md` §4. Do not append a fourth. On `4ee1975` those three lines are the locked-parameter paragraph, the Scenario 5 exception, and the canonical-table pointer. The replacement is:

1. This matrix: branch `s2-mode-matrix` from `4ee1975`, ten holds, mix 275/90/100/90/5, Paper-C1, `run1` and `run2` of `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, and `both_burst`. Next free slot for those five YAMLs is run 3.
2. The PASS, INVALID, and throttle FLAG counts copied from `docs/superpowers/plans/2026-10-14-s2-mode-matrix-run-log.md`, plus the guide path `Guides and Info/2026-10-14-s2-mode-matrix-abc.md`.
3. The restored cluster and the three VMs left RUNNING.

Keep the Still open list. Add one sentence there that this matrix is the locked S2 set under `final results/`, and that the `study*` folders, the `s2_burst20_*` folders, and `campaign_48/` S2 are not comparable.

- [ ] **Step 4: Commit**

```powershell
git add STATUS.md AGENTS.md
git commit -m @"
Record the S2 mode-matrix slots and the restored cluster.

The five S2 YAMLs sit at run 3, and the VMs were left running.
"@
git status --short
git branch --show-current
git merge-base --is-ancestor 4ee1975 HEAD; if ($LASTEXITCODE -eq 0) { "FROM_MAIN" } else { "NOT_FROM_MAIN" }
```

Expected: branch `s2-mode-matrix`, working tree clean, and `FROM_MAIN`. Do not push. Do not check this branch out in the primary checkout.
