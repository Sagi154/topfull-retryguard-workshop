# Analysis-Runs Replay (15 holds) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one new hold for each of the five controller variants of S2, S3, and S4A unconstrained (15 holds) and pull every one into `experiments/results/final_runs_results/`.

**Architecture:** A new generator copies the locked files in `experiments/configs/final_configs/` and changes only `run_number` and `log_folder`. It writes 15 YAMLs under `experiments/configs/analysis_runs_replay/`. The existing runner already pulls to `final_runs_results/` (`RESULTS_ROOT` in `experiments/run_scenario.py`). Holds then run one at a time with the same runbook as the 60-hold matrix (AGENTS.md §5 pin, §6 leftover-writer check). S2 `both_normal` uses run 4 because `analysis_s2_both_normal_run3` is already the clean re-run of the flagged run 1. Every other slot in this replay is run 3.

**Tech Stack:** Python 3 (`unittest`, `pyyaml`), `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, `experiments/topfull_health.py`, OpenSSH aliases `topfull-master`, `topfull-worker-1`, `topfull-load`.

## Global Constraints

- Follow-up to [2026-10-16-analysis-runs-results.md](2026-10-16-analysis-runs-results.md) and [2026-10-16-analysis-runs-results-log.md](2026-10-16-analysis-runs-results-log.md). The 60 pinned holds and the three clean run3 re-runs stay where they are. This plan does not re-run them and does not edit their YAMLs.
- All work happens on branch `analysis-runs-replay` in worktree `.worktrees/analysis-runs-replay` (path `C:\Users\sagi1\Projects\Workshop\.worktrees\analysis-runs-replay`). Create that worktree from `main` if it is missing. Do not create a second worktree. Do not use `.worktrees/analysis-runs-results`. Do not touch `main`'s working tree for holds or generated configs. Do not push `main`. Do not merge this branch unless the user asks.
- **Commit and push after every finished task and every finished hold.** Carried from the user decision on the 60-hold plan (2026-10-16). From the worktree, on `analysis-runs-replay`: when a task's last step is done, commit that task's files and `git push -u origin HEAD`. When a hold finishes (P6), commit the pulled folder and the log line, then push before the next hold. A push that does not exit 0 is not done. Do not start the next task or the next hold until the push exits 0. Push only this branch.
- Work run from the worktree directory, so relative `experiments/results/...` and `experiments/configs/...` paths resolve inside it.
- Use `experiments/configs/final_configs/` as the source. Do not edit those files. Do not edit `experiments/configs/analysis_runs/` (they stay at run 2) or `experiments/configs/analysis_runs_rerun/` (the three run3 replacements stay). Do not change load mixes, the Paper-C1 CPU table, constrained rows, or the locked RetryGuard parameters (AGENTS.md §5).
- Results go to `experiments/results/final_runs_results/<scenario>_<normal|burst>/<variant>/<log_folder>/`. `final results/`, `campaign_48/`, and `analysis_runs_results/` are closed and never a target.
- **Replica pin (AGENTS.md §5) is a gate.** Before Task 3 and before every hold, the live cluster must read: `frontend-hpa` minReplicas 4 and maxReplicas 4, frontend ready replicas 4, `productcatalogservice-hpa` minReplicas 1 and maxReplicas 1, catalog ready replicas 1, frontend `sidecar.istio.io/proxyCPU` `90m`, `proxyCPULimit` absent. Use the check in Task 2 Step 3. If any value differs, patch it back to that lock, wait until the check matches, then continue. Do not start Locust on a failed check. After each pull, `resource_usage.csv` must show frontend `replica_count` only 4 and catalog `replica_count` only 1. Any other value means the hold is not a column: do not commit it, re-apply the pin, and re-run that same slot (at most twice). A third miss stops the campaign.
- SSH only through `topfull-master`, `topfull-worker-1`, `topfull-load`. Never hardcode IPs. SSH user stays `idozacharia`. GCP project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start the `networks-workshop` VMs.
- Cool-off between holds is **120 s**, counted from when `run_scenario.py` exits. Do the leftover-writer check (Task 3, P2) before every hold.
- After every hold run `python experiments/analysis_score.py <run_dir>` and `python experiments/topfull_health.py "<run_dir>"`. Any flag (throttle FLAGGED, PROXY FD, RL STALL) means the hold is not clean. Record the flag in the log and keep going. Do not pause for a flag and do not re-run a finished hold. A hold that aborted or failed before finishing may be re-run in the same slot (P3), at most twice.
- Do not stop the VMs at the end unless the user asks.
- These 15 holds are extra columns beside run 1 and run 2. They do not replace a flagged folder. `analysis_s2_both_normal_run3` stays the clean replacement of `analysis_s2_both_normal_run1` and is not overwritten.

## Decisions this plan locks (2026-10-17)

1. **One replay per variant, three scenario groups.** S2, S3, and S4A unconstrained. Five variants each: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. That is 15 holds. S1, S4B, and S4A constrained are not in this replay.
2. **Slots.** Run 3 for 14 of the 15. S2 `both_normal` is run 4, because `analysis_s2_both_normal_run3` already exists under `final_runs_results/`. Do not reuse that folder.
3. **Same loads and CPU as the locked sources.** S2 mix 275 / 90 / 100 / 90 / 5, plain Paper-C1. S3 mix 175 / 30 / 70 / 90 / 5, checkout 200m. S4A unconstrained mix 50 / 20 / 50 / 600 / 5, plain Paper-C1 (catalog is not 100m). `spawn_rate` 50. Duration 600 s on every hold.
4. **Flag, record, continue.** Same rule as the 60-hold matrix. The user decides later whether a flagged replay needs another slot.
5. **Order.** S2, then S3, then S4A unconstrained. Inside each group: `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`.

Expected wall time: 15 holds at about 15–20 min each, plus 14 cool-offs of 120 s, about 5–6.5 h. A stop between groups loses nothing. The VMs are **TERMINATED** as of 2026-10-17 (STATUS.md), so Task 2 starts them.

## Run matrix (15 holds)

| Group | Source dir (`final_configs/`) | Prefix | Mode folders |
|---|---|---|---|
| `s2` | `2/` | `s2` | `S2_sustained_overload_{normal,burst}` |
| `s3` | `3/` | `s3` | `S3_targeted_bottleneck_{normal,burst}` |
| `s4a_unconstrained` | `4/4a_unconstrained/` | `4a_unconstrained` | `S4A_topology_position_{normal,burst}` |

S4A constrained and unconstrained share `scenario_name: topology_position_A` and the `S4A_topology_position_*` folders. The `4a_unconstrained` token in `log_folder` is what separates this replay from the constrained holds already in those folders. `analysis_4a_constrained_both_normal_run3` is a different name and must stay.

| # | Config under `experiments/configs/analysis_runs_replay/` | `log_folder` | Pull directory under `experiments/results/final_runs_results/` |
|---|---|---|---|
| 1 | `s2/s2_rg_only_normal_run3.yaml` | `analysis_s2_rg_only_normal_run3` | `S2_sustained_overload_normal/rg_only/analysis_s2_rg_only_normal_run3` |
| 2 | `s2/s2_both_normal_run4.yaml` | `analysis_s2_both_normal_run4` | `S2_sustained_overload_normal/both/analysis_s2_both_normal_run4` |
| 3 | `s2/s2_tf_only_run3.yaml` | `analysis_s2_tf_only_run3` | `S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run3` |
| 4 | `s2/s2_rg_only_burst_run3.yaml` | `analysis_s2_rg_only_burst_run3` | `S2_sustained_overload_burst/rg_only/analysis_s2_rg_only_burst_run3` |
| 5 | `s2/s2_both_burst_run3.yaml` | `analysis_s2_both_burst_run3` | `S2_sustained_overload_burst/both/analysis_s2_both_burst_run3` |
| 6 | `s3/s3_rg_only_normal_run3.yaml` | `analysis_s3_rg_only_normal_run3` | `S3_targeted_bottleneck_normal/rg_only/analysis_s3_rg_only_normal_run3` |
| 7 | `s3/s3_both_normal_run3.yaml` | `analysis_s3_both_normal_run3` | `S3_targeted_bottleneck_normal/both/analysis_s3_both_normal_run3` |
| 8 | `s3/s3_tf_only_run3.yaml` | `analysis_s3_tf_only_run3` | `S3_targeted_bottleneck_normal/tf_only/analysis_s3_tf_only_run3` |
| 9 | `s3/s3_rg_only_burst_run3.yaml` | `analysis_s3_rg_only_burst_run3` | `S3_targeted_bottleneck_burst/rg_only/analysis_s3_rg_only_burst_run3` |
| 10 | `s3/s3_both_burst_run3.yaml` | `analysis_s3_both_burst_run3` | `S3_targeted_bottleneck_burst/both/analysis_s3_both_burst_run3` |
| 11 | `s4a_unconstrained/4a_unconstrained_rg_only_normal_run3.yaml` | `analysis_4a_unconstrained_rg_only_normal_run3` | `S4A_topology_position_normal/rg_only/analysis_4a_unconstrained_rg_only_normal_run3` |
| 12 | `s4a_unconstrained/4a_unconstrained_both_normal_run3.yaml` | `analysis_4a_unconstrained_both_normal_run3` | `S4A_topology_position_normal/both/analysis_4a_unconstrained_both_normal_run3` |
| 13 | `s4a_unconstrained/4a_unconstrained_tf_only_run3.yaml` | `analysis_4a_unconstrained_tf_only_run3` | `S4A_topology_position_normal/tf_only/analysis_4a_unconstrained_tf_only_run3` |
| 14 | `s4a_unconstrained/4a_unconstrained_rg_only_burst_run3.yaml` | `analysis_4a_unconstrained_rg_only_burst_run3` | `S4A_topology_position_burst/rg_only/analysis_4a_unconstrained_rg_only_burst_run3` |
| 15 | `s4a_unconstrained/4a_unconstrained_both_burst_run3.yaml` | `analysis_4a_unconstrained_both_burst_run3` | `S4A_topology_position_burst/both/analysis_4a_unconstrained_both_burst_run3` |

## File Structure

- Create: `experiments/make_analysis_runs_replay_configs.py` — the 15-slot table and `generate()`.
- Create: `experiments/test_make_analysis_runs_replay_configs.py` — slot table, source equality, pull paths, no collision with an existing `log_folder`.
- Create: `experiments/configs/analysis_runs_replay/<group>/*.yaml` — 15 files, written by the generator. Only `run_number` and `log_folder` differ from the `final_configs/` source.
- Create during Task 3: `docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md` — one line per finished hold.
- Modify at the end (Task 4): `STATUS.md`, `AGENTS.md`.
- Do not modify: `experiments/make_analysis_runs_configs.py`, `experiments/configs/analysis_runs/**`, `experiments/configs/analysis_runs_rerun/**`, `experiments/configs/final_configs/**`, `experiments/run_scenario.py`.

---

### Task 1: Generate the 15 replay configs

**Files:**
- Create: `experiments/make_analysis_runs_replay_configs.py`
- Create: `experiments/test_make_analysis_runs_replay_configs.py`
- Create: `experiments/configs/analysis_runs_replay/**` (15 YAMLs)

**Interfaces:**
- Consumes: `make_analysis_runs_configs.build_text(source_text: str, log_folder: str, run_number: int) -> str`, `make_analysis_runs_configs.VARIANTS`, `make_analysis_runs_configs.SRC`, and `run_scenario.local_results_dir(cfg: dict) -> str`.
- Produces: `SLOTS: list[tuple[str, str, str, str, int]]` as `(group, source_subdir, prefix, variant, run_number)`; `generate(out_dir: Path | None = None) -> list[Path]`. Default `out_dir` is `experiments/configs/analysis_runs_replay`.

- [ ] **Step 1: Worktree and branch**

From the main repo root (`C:\Users\sagi1\Projects\Workshop`), if `.worktrees/analysis-runs-replay` is missing:

```powershell
git worktree list
git check-ignore -q .worktrees
git worktree add .worktrees/analysis-runs-replay -b analysis-runs-replay main
```

Expected: a new worktree on `analysis-runs-replay` based on `main`. If the branch or path already exists, stop and report. Copy this plan into the worktree if it is not already there (`docs/superpowers/plans/2026-10-17-analysis-runs-replay.md`). All later steps in this plan run with working directory `C:\Users\sagi1\Projects\Workshop\.worktrees\analysis-runs-replay`.

- [ ] **Step 2: Write the failing test**

Create `experiments/test_make_analysis_runs_replay_configs.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_analysis_runs_replay_configs as replay  # noqa: E402
import run_scenario  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results" / "final_runs_results"
CONFIGS = ROOT / "experiments" / "configs"


class TestReplaySlots(unittest.TestCase):
    def test_fifteen_slots_and_the_run4_exception(self):
        self.assertEqual(len(replay.SLOTS), 15)
        by_name = {f"analysis_{p}_{v}_run{n}": (g, n)
                   for g, _s, p, v, n in replay.SLOTS}
        self.assertEqual(len(by_name), 15)
        self.assertEqual(by_name["analysis_s2_both_normal_run4"], ("s2", 4))
        self.assertNotIn("analysis_s2_both_normal_run3", by_name)
        run3 = [name for name, (_g, n) in by_name.items() if n == 3]
        self.assertEqual(len(run3), 14)

    def test_groups_are_only_s2_s3_and_4a_unconstrained(self):
        groups = {g for g, _s, _p, _v, _n in replay.SLOTS}
        self.assertEqual(groups, {"s2", "s3", "s4a_unconstrained"})

    def test_each_built_yaml_matches_its_source(self):
        for group, src_dir, prefix, variant, n in replay.SLOTS:
            src = CONFIGS / "final_configs" / src_dir / f"{prefix}_{variant}.yaml"
            log_folder = f"analysis_{prefix}_{variant}_run{n}"
            built = yaml.safe_load(replay.build_text(
                src.read_text(encoding="utf-8"), log_folder, n))
            old = yaml.safe_load(src.read_text(encoding="utf-8"))
            self.assertEqual(built["run_number"], n)
            self.assertEqual(built["log_folder"], log_folder)
            for key in ("run_number", "log_folder"):
                old.pop(key)
                built.pop(key)
            self.assertEqual(built, old, msg=log_folder)

    def test_locked_mixes_and_constrained_rows(self):
        def cfg(group, prefix, variant, n):
            src = next(s for s in replay.SLOTS
                       if s[0] == group and s[3] == variant)
            text = (CONFIGS / "final_configs" / src[1] / f"{prefix}_{variant}.yaml"
                    ).read_text(encoding="utf-8")
            return yaml.safe_load(replay.build_text(
                text, f"analysis_{prefix}_{variant}_run{n}", n))

        s2 = cfg("s2", "s2", "rg_only_normal", 3)
        s3 = cfg("s3", "s3", "tf_only", 3)
        a = cfg("s4a_unconstrained", "4a_unconstrained", "both_burst", 3)
        self.assertEqual(s2["locust"]["user_counts"], {
            "getproduct": 275, "postcheckout": 90, "getcart": 100,
            "postcart": 90, "emptycart": 5})
        self.assertEqual(s3["locust"]["user_counts"], {
            "getproduct": 175, "postcheckout": 30, "getcart": 70,
            "postcart": 90, "emptycart": 5})
        self.assertEqual(a["locust"]["user_counts"], {
            "getproduct": 50, "postcheckout": 20, "getcart": 50,
            "postcart": 600, "emptycart": 5})
        def limit(doc, dep):
            return next(r["cpu_limit_millicores"] for r in doc["scale_constraints"]
                        if r["deployment"] == dep)
        self.assertEqual(limit(s3, "checkoutservice"), 200)
        self.assertNotEqual(limit(a, "productcatalogservice"), 100)
        self.assertNotIn("burst_rpr", s2["retryguard"])
        self.assertEqual(a["retryguard"]["burst_rpr"], 2.0)

    def test_pull_paths_and_no_collision(self):
        occupied = {p.name for p in RESULTS.rglob("analysis_*") if p.is_dir()}
        self.assertIn("analysis_s2_both_normal_run3", occupied)
        for group, src_dir, prefix, variant, n in replay.SLOTS:
            log_folder = f"analysis_{prefix}_{variant}_run{n}"
            self.assertNotIn(log_folder, occupied, msg=log_folder)
            src = CONFIGS / "final_configs" / src_dir / f"{prefix}_{variant}.yaml"
            built = yaml.safe_load(replay.build_text(
                src.read_text(encoding="utf-8"), log_folder, n))
            dest = run_scenario.local_results_dir(built)
            self.assertTrue(
                dest.startswith("experiments/results/final_runs_results/"),
                msg=log_folder)
            self.assertTrue(dest.endswith("/"), msg=log_folder)

    def test_generate_writes_fifteen_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = replay.generate(Path(tmp))
            self.assertEqual(len(paths), 15)
            names = sorted(p.name for p in paths)
            self.assertIn("s2_both_normal_run4.yaml", names)
            self.assertNotIn("s2_both_normal_run3.yaml", names)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to verify it fails**

```powershell
python -m unittest experiments.test_make_analysis_runs_replay_configs -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'make_analysis_runs_replay_configs'` (or the package import equivalent). Do not write the YAMLs by hand.

- [ ] **Step 4: Write the generator**

Create `experiments/make_analysis_runs_replay_configs.py`:

```python
"""Generate the 15 replay YAMLs from locked final_configs/ copies.

Only run_number and log_folder differ from the source.
S2 both_normal is run 4 because analysis_s2_both_normal_run3 already exists.
Every other slot is run 3.

Run: python experiments/make_analysis_runs_replay_configs.py
"""
from __future__ import annotations

from pathlib import Path

import make_analysis_runs_configs as base

OUT = Path(__file__).resolve().parent / "configs" / "analysis_runs_replay"

# (group, source dir under final_configs/, prefix, variant, run_number)
_GROUPS = [
    ("s2", "2", "s2", {"both_normal": 4}),
    ("s3", "3", "s3", {}),
    ("s4a_unconstrained", "4/4a_unconstrained", "4a_unconstrained", {}),
]
SLOTS = [
    (group, src_dir, prefix, variant, overrides.get(variant, 3))
    for group, src_dir, prefix, overrides in _GROUPS
    for variant in base.VARIANTS
]


def build_text(source_text: str, log_folder: str, run_number: int) -> str:
    return base.build_text(source_text, log_folder, run_number)


def generate(out_dir: Path | None = None) -> list[Path]:
    root = OUT if out_dir is None else out_dir
    written = []
    for group, src_dir, prefix, variant, n in SLOTS:
        src = base.SRC / src_dir / f"{prefix}_{variant}.yaml"
        log_folder = f"analysis_{prefix}_{variant}_run{n}"
        dest = root / group / f"{prefix}_{variant}_run{n}.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            build_text(src.read_text(encoding="utf-8"), log_folder, n),
            encoding="utf-8", newline="\n")
        written.append(dest)
    return written


if __name__ == "__main__":
    for path in generate():
        print(path)
```

`base.VARIANTS` order is `rg_only_normal`, `both_normal`, `tf_only`, `rg_only_burst`, `both_burst`. Keep that order. The run-4 exception is only the `{"both_normal": 4}` entry on the `s2` row.

- [ ] **Step 5: Run the test to verify it passes**

```powershell
python -m unittest experiments.test_make_analysis_runs_replay_configs -v
```

Expected: `OK`. Then write the 15 files into the repo:

```powershell
python experiments/make_analysis_runs_replay_configs.py
```

Expected: 15 paths under `experiments/configs/analysis_runs_replay/`, including `s2\s2_both_normal_run4.yaml` and not `s2_both_normal_run3.yaml`.

- [ ] **Step 6: Commit and push**

```powershell
git add experiments/make_analysis_runs_replay_configs.py experiments/test_make_analysis_runs_replay_configs.py experiments/configs/analysis_runs_replay docs/superpowers/plans/2026-10-17-analysis-runs-replay.md AGENTS.md STATUS.md
git commit -m "feat: add the 15-hold analysis-runs replay configs"
git push -u origin HEAD
```

Before that commit, edit the STATUS.md Done bullet that introduces this plan: replace the sentence `Configs are not generated until Task 1` with `Task 1 wrote the 15 YAMLs under experiments/configs/analysis_runs_replay/. Holds have not started.` Leave the rest of that bullet. `AGENTS.md` and `STATUS.md` belong in this commit when they still have uncommitted edits that only record this plan.

Expected: the push exits 0. Do not start Task 2 until the push exits 0.

---

### Task 2: Start the cluster and confirm the replica pin

**Files:**
- Read: [Guides and Info/CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md)

No YAML edits in this task. The three VMs were stopped on 2026-10-17.

- [ ] **Step 1: Start the three VMs and refresh SSH**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

If any of `topfull-master`, `topfull-worker-1`, `topfull-load` is `TERMINATED`, start those three only:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Refresh `HostName` in `~/.ssh/config` from the new public IPs, following CONNECT-VMS.md. Do not write the IPs into the repo. Confirm the active gcloud account is `yoavnm98@gmail.com`, `idozacharia@gmail.com`, or `sagi151ps@gmail.com`.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: user `idozacharia` on both SSH hosts; both nodes `Ready`; Online Boutique pods `2/2 Running`. If `kubectl` says `connection to localhost:8080 refused`, that is a missing kubeconfig for the SSH user (AGENTS.md §7), not a reason to rebuild the cluster. If SSH to `idozacharia` is `Permission denied`, follow CONNECT-VMS.md §Key install. Do not continue while nodes are not `Ready`.

- [ ] **Step 2: Clear stale runner scripts**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/rg_proxy_fd.sh /tmp/proxy_fd_params.json"
```

- [ ] **Step 3: Verify the replica pin, then stop if it does not match**

The four lines must be exactly the expected block. `kubectl get hpa` alone is not this check. The runner resets CPU limits and does not patch these HPAs or the frontend annotation.

```powershell
@'
import json, subprocess
def get(args):
    return json.loads(subprocess.check_output(["kubectl", *args]))
fe = get(["get", "hpa", "frontend-hpa", "-n", "default", "-o", "json"])
ca = get(["get", "hpa", "productcatalogservice-hpa", "-n", "default", "-o", "json"])
fd = get(["get", "deploy", "frontend", "-n", "default", "-o", "json"])
cd = get(["get", "deploy", "productcatalogservice", "-n", "default", "-o", "json"])
ann = fd["spec"]["template"]["metadata"].get("annotations", {})
print("frontend_hpa", fe["spec"]["minReplicas"], fe["spec"]["maxReplicas"], fd["status"].get("readyReplicas"))
print("catalog_hpa", ca["spec"]["minReplicas"], ca["spec"]["maxReplicas"], cd["status"].get("readyReplicas"))
print("proxyCPU", ann.get("sidecar.istio.io/proxyCPU"))
print("proxyCPULimit", ann.get("sidecar.istio.io/proxyCPULimit"))
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master python3 -
```

Expected:

```text
frontend_hpa 4 4 4
catalog_hpa 1 1 1
proxyCPU 90m
proxyCPULimit None
```

`proxyCPULimit None` means the annotation is absent. Any other output: apply the lock, wait until the same check matches, and run it again. Do not start Task 3 while it still differs.

```powershell
@'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"90m"}}}}}'
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

A frontend rollout can take a couple of minutes. If the check still does not match after that, stop and report. Do not launch a hold.

- [ ] **Step 4: Push if the branch is ahead, then stop**

This task changes no files, so there is no new commit. If `git status -sb` shows the branch ahead of `origin/analysis-runs-replay`, push before Task 3:

```powershell
git push -u origin HEAD
```

Expected: the push exits 0, or the branch is already even with the remote.

---

### Task 3: Run the 15 holds

**Files:**
- Read-only: the 15 YAMLs from Task 1
- Create: `docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md` on the first finished hold
- Create: one pulled folder per hold, at the pull directory in the matrix table

**Interfaces:**
- Consumes: the 15 config paths and pull directories in the matrix table. `run_scenario.local_results_dir` is how a pull path is derived; the table is the list to run.
- Produces: 15 run directories and one log line each.

Run the rows in order, 1 through 15. Every row uses the hold procedure below. A session that stops after a pushed hold resumes at the next unchecked row, after repeating Task 2 Step 3.

**Hold procedure** for config `C` and pull directory `D` (both are in the matrix table; `D` is the path under `experiments/results/final_runs_results/`):

- [ ] **P0: Replica pin.** Run Task 2 Step 3. The four lines must match before Locust starts. If they do not, apply that step's patch, wait, and check again. Do not run P3 until they match. A check that still fails stops the campaign.

- [ ] **P1: Cool-off.** At least 120 s since the previous `run_scenario.py` exit. The first hold of a session has no cool-off.

```powershell
Start-Sleep -Seconds 120
```

- [ ] **P2: Leftover-writer check.** Do not continue if any of these checks fail. If the pin was patched during the cool-off, run P0 again before P3.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; pkill -f '[p]roxy_fd_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py|[p]roxy_fd_collector.py' || echo master-clear"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

Expected: a line `locust-clear`, a line `master-clear`, and an empty `ls` (no `.csv` or `.log` came back). Any other output means a writer is still alive. Do not start the hold.

- [ ] **P3: Run.**

```powershell
python experiments/run_scenario.py C
```

Wait until it exits. A 600 s hold plus setup is about 15–20 min. Expected end of output includes `Results saved to (on master): /home/idozacharia/experiments/results/<log_folder>`. A non-zero exit or a runner abort (CPU-limit mismatch, missing RL timeout patch, replica pin the runner does not own) is a hold that did not finish. Record the failure and the cause in the log, fix the cause, redo P2 and the 120 s cool-off, and re-run the same `C`. Do not pull and do not commit the partial data. The re-run overwrites that `log_folder` on master. If a stale folder owned by another user blocks the copy, stop and ask before using `sudo`. Retry a given hold at most twice; after that write `exit failed` and go on to the next row. If the cause blocks every later hold (VM down, SSH dead, nodes not Ready), stop the campaign and report.

A finished hold that is flagged is not re-run.

- [ ] **P4: Pull and check replicas.**

```powershell
python experiments/pull_results.py C
```

Expected: a line that the folder was pulled under `experiments/results/final_runs_results/`, and `D` exists. The folder must contain `run_manifest.json`, `resource_usage.csv`, Locust CSVs, and `service_inbound.csv`. TopFull-on holds (`both_normal`, `tf_only`, `both_burst`) must also contain `topfull_throttle.csv`. RetryGuard-on holds must also contain `retryguard.log`.

```powershell
python -c "import csv,sys; from collections import defaultdict; d=defaultdict(set)
for row in csv.DictReader(open(sys.argv[1], newline='')):
    if row['service'] in ('frontend','productcatalogservice'):
        d[row['service']].add(int(float(row['replica_count'])))
print(dict(d))" "experiments/results/final_runs_results/D/resource_usage.csv"
```

Replace `D` with the pull directory from the matrix table (the argument is one path). Expected: `{'frontend': {4}, 'productcatalogservice': {1}}`. Any other set: do not commit. Re-apply Task 2 Step 3, redo P0–P2 and the 120 s cool-off, and re-run the same `C`. Twice at most. A third miss stops the campaign. The re-run overwrites `D`.

- [ ] **P5: Score, and append one log line.**

```powershell
python experiments/analysis_score.py "experiments/results/final_runs_results/D"
python experiments/topfull_health.py "experiments/results/final_runs_results/D"
```

Create `docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md` on the first hold. Header:

```markdown
# Analysis-runs replay log

One line per finished hold. A flagged hold is recorded and the campaign continues. These holds do not replace run 1 or run 2. `analysis_s2_both_normal_run4` does not replace `analysis_s2_both_normal_run3`.

`log_folder | exit | throttle | health | replicas | RetryGuard toggles`
```

Append: `log_folder | exit ok/failed | throttle ok/FLAGGED (<reason>) / N/A TopFull off | health ok/PROXY FD/RL STALL/not assessable | replicas frontend=4 catalog=1 | RG toggles`.

For the toggle clause, run this on `D/retryguard.log` when RetryGuard was on. When RetryGuard was off (`tf_only`), write `RG off` and skip the script.

```powershell
python -c "import collections,re,sys
p=sys.argv[1]
try:
    lines=open(p,encoding='utf-8',errors='replace').read().splitlines()
except FileNotFoundError:
    print('no retryguard.log'); raise SystemExit
counts=collections.Counter()
for line in lines:
    m=re.search(r'(\S+)\s+(ON→OFF|OFF→ON)', line)
    if not m: continue
    edge, step=m.group(1), m.group(2)
    counts[(edge, step)] += 1
    if 'burst' in line: counts[(edge, 'burst')] += 1
    if '1→2' in line or '1->2' in line: counts[(edge, '1→2')] += 1
    if '2→3' in line or '2->3' in line: counts[(edge, '2→3')] += 1
print('no transition lines' if not counts else '; '.join(f'{e} {s} {n}' for (e,s),n in sorted(counts.items())))" "experiments/results/final_runs_results/D/retryguard.log"
```

Clean means all of: `health: ok`, throttle table not FLAGGED, and the replica sets from P4. A TopFull-off hold (`rg_only_normal`, `rg_only_burst`) is `throttle N/A TopFull off`, which is not a flag.

- [ ] **P6: Commit and push this hold.** Do not start the next row until the push exits 0.

```powershell
git add "experiments/results/final_runs_results/D" docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md
git commit -m "data: <log_folder> (<clean|flagged: reason>)"
git push -u origin HEAD
```

`D` is the pull directory from the matrix table. If git objects from a folder become a problem, stop and ask. Do not add the folder to `.gitignore`.

#### Rows

- [ ] **1.** `C` = `experiments/configs/analysis_runs_replay/s2/s2_rg_only_normal_run3.yaml`. `D` = `S2_sustained_overload_normal/rg_only/analysis_s2_rg_only_normal_run3`.
- [ ] **2.** `C` = `experiments/configs/analysis_runs_replay/s2/s2_both_normal_run4.yaml`. `D` = `S2_sustained_overload_normal/both/analysis_s2_both_normal_run4`. Do not write into `analysis_s2_both_normal_run3`.
- [ ] **3.** `C` = `experiments/configs/analysis_runs_replay/s2/s2_tf_only_run3.yaml`. `D` = `S2_sustained_overload_normal/tf_only/analysis_s2_tf_only_run3`.
- [ ] **4.** `C` = `experiments/configs/analysis_runs_replay/s2/s2_rg_only_burst_run3.yaml`. `D` = `S2_sustained_overload_burst/rg_only/analysis_s2_rg_only_burst_run3`.
- [ ] **5.** `C` = `experiments/configs/analysis_runs_replay/s2/s2_both_burst_run3.yaml`. `D` = `S2_sustained_overload_burst/both/analysis_s2_both_burst_run3`.

- [ ] **6.** `C` = `experiments/configs/analysis_runs_replay/s3/s3_rg_only_normal_run3.yaml`. `D` = `S3_targeted_bottleneck_normal/rg_only/analysis_s3_rg_only_normal_run3`.
- [ ] **7.** `C` = `experiments/configs/analysis_runs_replay/s3/s3_both_normal_run3.yaml`. `D` = `S3_targeted_bottleneck_normal/both/analysis_s3_both_normal_run3`.
- [ ] **8.** `C` = `experiments/configs/analysis_runs_replay/s3/s3_tf_only_run3.yaml`. `D` = `S3_targeted_bottleneck_normal/tf_only/analysis_s3_tf_only_run3`.
- [ ] **9.** `C` = `experiments/configs/analysis_runs_replay/s3/s3_rg_only_burst_run3.yaml`. `D` = `S3_targeted_bottleneck_burst/rg_only/analysis_s3_rg_only_burst_run3`.
- [ ] **10.** `C` = `experiments/configs/analysis_runs_replay/s3/s3_both_burst_run3.yaml`. `D` = `S3_targeted_bottleneck_burst/both/analysis_s3_both_burst_run3`.

After row 10, the live checkout limit must be back at the Paper-C1 checkout row (the S2 source, not S3's 200m row):

```powershell
python -c "import yaml; c=yaml.safe_load(open(r'experiments/configs/final_configs/2/s2_both_normal.yaml',encoding='utf-8')); print(next(r['cpu_limit_millicores'] for r in c['scale_constraints'] if r['deployment']=='checkoutservice'))"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy checkoutservice -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'"
```

Expected: the printed millicores and the live limit are the same value (the live string is that number plus `m`). If they differ, stop and report. Do not hand-edit the Deployment.

- [ ] **11.** Before this row, the live catalog limit must equal the Paper-C1 catalog row in the S2 source, not the constrained 100m row:

```powershell
python -c "import yaml; c=yaml.safe_load(open(r'experiments/configs/final_configs/2/s2_both_normal.yaml',encoding='utf-8')); print(next(r['cpu_limit_millicores'] for r in c['scale_constraints'] if r['deployment']=='productcatalogservice'))"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get deploy productcatalogservice -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}'"
```

If the live value is `100m`, do not patch it by hand. Launching row 11 is still correct: the runner reconciles to the unconstrained YAML and aborts before Locust if the live limit does not match. An abort here is P3 (same slot, after the leftover-writer check), not a reason to skip the row.

`C` = `experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_rg_only_normal_run3.yaml`. `D` = `S4A_topology_position_normal/rg_only/analysis_4a_unconstrained_rg_only_normal_run3`.

- [ ] **12.** `C` = `experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_both_normal_run3.yaml`. `D` = `S4A_topology_position_normal/both/analysis_4a_unconstrained_both_normal_run3`. Do not write into `analysis_4a_constrained_both_normal_run3`.
- [ ] **13.** `C` = `experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_tf_only_run3.yaml`. `D` = `S4A_topology_position_normal/tf_only/analysis_4a_unconstrained_tf_only_run3`.
- [ ] **14.** `C` = `experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_rg_only_burst_run3.yaml`. `D` = `S4A_topology_position_burst/rg_only/analysis_4a_unconstrained_rg_only_burst_run3`.
- [ ] **15.** `C` = `experiments/configs/analysis_runs_replay/s4a_unconstrained/4a_unconstrained_both_burst_run3.yaml`. `D` = `S4A_topology_position_burst/both/analysis_4a_unconstrained_both_burst_run3`.

After row 15, repeat the catalog comparison from row 11. The live catalog limit must equal the S2 source's `productcatalogservice` millicores.

---

### Task 4: Summarise the replay and update status

**Files:**
- Modify: `docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md`
- Modify: `STATUS.md`, `AGENTS.md`

- [ ] **Step 1: Confirm the 15 folders**

```powershell
python -c "from pathlib import Path; root=Path('experiments/results/final_runs_results'); names=['analysis_s2_rg_only_normal_run3','analysis_s2_both_normal_run4','analysis_s2_tf_only_run3','analysis_s2_rg_only_burst_run3','analysis_s2_both_burst_run3','analysis_s3_rg_only_normal_run3','analysis_s3_both_normal_run3','analysis_s3_tf_only_run3','analysis_s3_rg_only_burst_run3','analysis_s3_both_burst_run3','analysis_4a_unconstrained_rg_only_normal_run3','analysis_4a_unconstrained_both_normal_run3','analysis_4a_unconstrained_tf_only_run3','analysis_4a_unconstrained_rg_only_burst_run3','analysis_4a_unconstrained_both_burst_run3']; found={p.name for p in root.rglob('analysis_*') if p.is_dir()}; missing=[n for n in names if n not in found]; print('missing', missing or 'none'); print('run3_both_normal_s2_still_there', 'analysis_s2_both_normal_run3' in found)"
```

Expected: `missing none` and `run3_both_normal_s2_still_there True`. A `failed` row that was never pulled is listed in `missing`. Say so in the summary. Do not invent a folder for it.

- [ ] **Step 2: Append the summary to the replay log**

Count clean vs flagged from the 15 lines. List every flagged `log_folder` with the reason already on its line (throttle stale seconds, PROXY FD, or RL STALL). State that `analysis_s2_both_normal_run3` was not replaced. Do not edit [2026-10-16-final-runs-results-log.md](2026-10-16-final-runs-results-log.md); that file stays the 60-hold record plus the three earlier run3 re-runs.

- [ ] **Step 3: STATUS.md and AGENTS.md**

Append one STATUS.md Done bullet: date range, "15 replay holds (S2, S3, S4A unconstrained x 5 variants) pulled to `experiments/results/final_runs_results/`", clean vs flagged counts, the flagged `log_folder`s with reason, and that every committed hold had frontend replicas 4 and catalog replicas 1. Link this plan and `2026-10-17-analysis-runs-replay-log.md`. Under Next free slots, add that `experiments/configs/analysis_runs_replay/` is the replay set: S2 `both_normal` is run 4 and the other 14 files are run 3. `experiments/configs/analysis_runs/` stays at run 2. `experiments/configs/analysis_runs_rerun/` stays at run 3. A further repeat needs a new file with the next free `run_number` for that variant (S2 `both_normal` would be run 5; the other 14 would be run 4).

Replace the three Latest lines in AGENTS.md §4. Do not append. Point at this plan and the replay log, the clean vs flagged counts, and that the VMs were left in whatever state Task 3 ended in (do not stop them in this task). Update Still open: this replay is done, and any flagged replay hold is waiting on the user. Leave the unpinned-20 bullet and the three earlier flagged folders as they are.

- [ ] **Step 4: Commit and push**

```powershell
git add docs/superpowers/plans/2026-10-17-analysis-runs-replay-log.md STATUS.md AGENTS.md
git commit -m "docs: record the 15-hold analysis-runs replay"
git push -u origin HEAD
```

Expected: the push exits 0.

- [ ] **Step 5: Hand back**

Do not merge `analysis-runs-replay`. Report the branch, the 15 `log_folder`s, clean vs flagged, and any row that failed before finishing. Ask whether to open a PR.

---

## Self-Review

- **Spec coverage:** 5 variants × S2, S3, and S4A unconstrained = 15 (matrix table and Task 3 rows). S2 `both_normal` is run 4 so `analysis_s2_both_normal_run3` is kept (decision 2, row 2, Task 4 Step 1). Pull root stays `final_runs_results` (global constraint; Task 1 test). Replica pin is Task 2 Step 3 and P0, plus the `resource_usage.csv` check in P4. Locked mixes and the S3 200m / unconstrained catalog rows are Task 1 tests. S1, S4B, and S4A constrained are out of the queue. Commit-and-push after each hold is a global constraint and P6.
- **Placeholders:** none. `C` and `D` in the hold procedure are the per-row paths written under Rows.
- **Name consistency:** `SLOTS` entries are `(group, source_subdir, prefix, variant, run_number)`. `build_text` and `generate(out_dir)` match Task 1's test. `log_folder` is `analysis_<prefix>_<variant>_run<N>` in the generator, the test, and the matrix table.
