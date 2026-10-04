# S2 Checkout-Latch Probe Holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run twenty both-off S2 holds on the disk-copy VMs, every one a single change on top of the run 89 mix and the Paper-C1 table, to find out which lever makes the same mix blend (checkout and recommendations both hot) instead of latching checkout. Seven levers get two holds each, the pod-restart lever gets two, and four holds are untouched controls. Then terminate the VMs, commit everything, push, and list every file touched.

**Architecture:** A new helper module `experiments/s2_latch_probe.py` builds one generated config per hold from the run 89 base, prints the kubectl commands that set the cluster to the hold's starting state, gates the pulled folder, and scores it as sticky latch, released, or other. Two small PowerShell scripts (`experiments/latch_hold_pre.ps1`, `experiments/latch_hold_run.ps1`) wrap the per-hold steps so every hold runs the same commands. `experiments/run_scenario.py` gains one optional key, `restart_before_hold`. Holds run in two shuffled blocks of ten (a randomized block design): each block has every lever once, one restart hold, and two controls, so drift over the day hits both halves equally. Each hold saves a t=0 and an end-of-hold cluster snapshot ([2026-10-03-s2-same-mix-replays-differ.md](../../../Guides%20and%20Info/2026-10-03-s2-same-mix-replays-differ.md) check 1). Existing runs 86–107 are retro-scored first (that guide's checks 2 and 3).

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_canon.py`, new `experiments/s2_latch_probe.py`, PowerShell, `unittest`, kubectl over `ssh topfull-master`, `gcloud compute` on project `project-76deda76-55f1-42d2-abb`.

## Global Constraints

- Project is `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start or stop anything in `networks-workshop`. SSH aliases only: `topfull-master`, `topfull-worker-1`, `topfull-load`. User is `idozacharia`.
- **Base (every hold unless its lever says otherwise):** counts getproduct / postcheckout / getcart / postcart / emptycart = **275 / 90 / 100 / 90 / 5** (run 89 mix). Paper-C1 table, per-pod millicores with request equal to limit: frontend 1150 × 4 (HPA pinned min 4 / max 4), checkoutservice 800, recommendationservice 1150, productcatalogservice 800, cartservice 800, currencyservice 770, shippingservice 770, adservice 1150, paymentservice 155, emailservice 120, redis-cart 540 (container `redis`). Every other Deployment has 1 replica. Sidecar annotation `sidecar.istio.io/proxyCPU=100m`, `proxyCPULimit` absent.
- Every hold is 600 s, `spawn_rate` 50 (except `spawn10`), `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`, `paper_cpu_reconcile: false`.
- **One change per hold.** Treatments and slots are fixed in the order table. Do not combine, reorder, or drop one except under the failure rules.
- Slots are run108 to run127. Run1–run107 are taken. Do not overwrite any folder under `campaign_48/`, `experiments/results/new vms/`, or `experiments/results/copy verification/`.
- Local destination: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>/`. `pull_results.py` first writes under `campaign_48/S2_sustained_overload/`; the run script moves the folder. Nothing from this series stays under `campaign_48/`.
- The helper writes the generated config to `experiments/configs/scenario_2_latch_probe.yaml`. Do not edit `scenario_2_baseline_no_topfull.yaml` until the final task moves it to run128.
- **Cluster state is set by `prep`, never by the runner.** `run_scenario.py` patches CPU limits only when the live value differs, and a differing patch rolls that Deployment (a fresh pod), which would silently restart pods in the control holds. `prep` sets checkout and recommendations CPU and checkout replicas to the hold's values *before* the cool-off, so the runner's patch becomes a no-op ("already at …; skipping patch" in its log). If the log shows an applied patch instead, note it in the results guide.
- Cool-off is 360 s after `prep` finishes and before launch, for every hold. Do not call `Start-Sleep`. Call AwaitShell with no `shell_id` and `block_until_ms: 360000`.
- **PowerShell pipes add CRLF to remote bash scripts.** Every remote script in this plan goes through `cmd /c "… | ssh … bash -s"` or `ssh … bash -s < file` (done inside the two `.ps1` scripts). Never pipe a script to ssh directly from PowerShell.
- `duplicate session: envoyretry` in a hold's output: `ssh -o BatchMode=yes topfull-master "tmux kill-session -t envoyretry"`, then rerun that hold's run script once. Any other death before Locust: keep whatever folder exists, do not relaunch, stop the series, go to the final task.
- A failed gate: keep the folder and do not relaunch the slot. A sampling failure (rows under 500, mesh span outside 480–900 s, `gap2_pct` over 10, missing file) lets the series continue. A replica-mode failure (the lever did not apply) stops the series. Record every failure in the results guide. Never commit a failed hold as if it passed; commit it with the message `data: S2 latch probe runN FAILED gate` and a blank row in the guide.
- A Pending pod after `prep` (typically `Insufficient cpu` after adding a checkout replica): stop and report `kubectl describe pod`. Do not lower the sidecar request and do not unpin frontend.
- Do not call `reconcile_paper_cpu_limits`, do not restore the frontend HPA, do not restore paper CPU during the series. The final task returns checkout and recommendations to the Paper-C1 base.
- Do not commit `.superpowers/`. Commit each hold before the next cool-off. Push once, in the final task.
- **Reading the results (honesty rule).** The background rate for this mix on the disk copy is 3 blends and 4 sticky latches in 7 holds (runs 94–97, 99–101). Two holds per lever is a screen, not a proof: if a lever did nothing, two blends in a row still happens about 18% of the time and two latches about 33%. Verdicts are therefore: **moved** (both holds released or blended), **no effect seen** (both sticky), **mixed** (anything else). Only a **moved** lever, or one that changes the mechanism (checkout sojourn below 500 ms in both holds), earns a 3-replay follow-up. The four controls are reported as their own rate beside the 7 earlier holds.

## Hold order (seed 20261003)

Generated with `random.Random(20261003)`, shuffling the ten block entries once for block A and once for block B. Fixed here so the plan is reproducible.

| Slot | Block | Treatment key | What changes from base |
|---|---|---|---|
| 108 | A | `restart` | checkout and recommendations pods rolled before Locust starts, 60 s settle |
| 109 | A | `spawn10` | `spawn_rate` 50 → 10 (every tag reaches full load in 10 s, not 50 s) |
| 110 | A | `recs_cpu1000` | recommendationservice limit and request 1000 m |
| 111 | A | `control` | nothing |
| 112 | A | `ck_rep2` | checkoutservice 2 replicas (800 m each) |
| 113 | A | `ck_cpu1000` | checkoutservice limit and request 1000 m |
| 114 | A | `recs_users310` | getproduct users 275 → 310 |
| 115 | A | `ck_rep2_pc120` | checkout 2 replicas and postcheckout 120 |
| 116 | A | `control` | nothing |
| 117 | A | `pc120` | postcheckout users 90 → 120 |
| 118 | B | `recs_users310` | getproduct 310 |
| 119 | B | `ck_rep2` | checkout 2 replicas |
| 120 | B | `spawn10` | 10 s ramp |
| 121 | B | `control` | nothing |
| 122 | B | `ck_cpu1000` | checkout 1000 m |
| 123 | B | `ck_rep2_pc120` | checkout 2 replicas and postcheckout 120 |
| 124 | B | `restart` | pods rolled before Locust |
| 125 | B | `pc120` | postcheckout 120 |
| 126 | B | `recs_cpu1000` | recommendations 1000 m |
| 127 | B | `control` | nothing |

Between slot 117 and 118 is the block boundary. Keep the VMs up through it. If a stop is unavoidable, record the stop time and expect new pod ages; the results guide must say so.

**Why these facts hold (verified in the repo):** `experiments/loadgen/online_boutique_create_v2.sh` computes Locust `-r` as `count / RATE` (awk float), so `spawn_rate` is a divisor and every tag's ramp lasts `RATE` seconds regardless of its count. `run_scenario.py` `apply_constraints` supports `method: replicas` and records the original count for restore; `topfull_cpu_quotas.validate_scale_constraints` rejects replicas only on HPA-managed Deployments (checkout is not one). `cpu_resources_already_set` makes an identical CPU patch a skip. `discover_service_pod_ips` seeds every Running pod IP per service, so a second checkout pod is scraped. About 25 minutes per hold, so the series is about 8–9 hours.

## File map

| File | Role |
|---|---|
| `experiments/s2_latch_probe.py` | New. `build_config`, `prep_script`, `expected_replicas`, `gate`, `classify`, `is_blend`, `sojourn_window`, CLI (`config`, `prep`, `gate`, `score`). |
| `experiments/test_s2_latch_probe.py` | New. Unit tests for the pure functions. |
| `experiments/latch_snapshot.sh` | New. Read-only kubectl snapshot run on master. |
| `experiments/latch_hold_pre.ps1` | New. Runs `prep` for a treatment and fails on Pending pods. |
| `experiments/latch_hold_run.ps1` | New. Snapshot, config, launch, pull, move, end snapshot, gate, score. |
| `experiments/run_scenario.py` | Modify. Add `restart_before_hold(cfg)` and call it in `run()` after `apply_per_try_timeout(cfg)`, before `start_master_stack(cfg)`. |
| `experiments/test_run_scenario.py` | Modify. Add `TestRestartBeforeHold`. |
| `experiments/configs/scenario_2_latch_probe.yaml` | Generated per hold. Committed with that hold. |
| `experiments/results/new vms/baseline_no_topfull_sustained_overload_run108` … `run127` | Created by pull plus move. One data commit each, with a `state/` subfolder (`t0.txt`, `end.txt`). |
| `Guides and Info/2026-10-03-s2-latch-probe-results.md` | New. Retro-score table (Task 4) and the run 108–127 section (final task). |
| `Guides and Info/2026-10-03-s2-same-mix-replays-differ.md` | Final task appends a short "Probe result" section. Existing text stays. |
| `experiments/results/README.md`, `AGENTS.md`, `experiments/configs/scenario_2_baseline_no_topfull.yaml` | Final task bookkeeping (next free both-off slot becomes run128). |

---

### Task 1: `restart_before_hold` in the runner (TDD)

**Files:**
- Modify: `experiments/run_scenario.py` (new function after `apply_per_try_timeout`, one call in `run()`)
- Modify: `experiments/test_run_scenario.py` (append a test class before the `if __name__` block)

**Interfaces:**
- Consumes: `ssh(host, cmd, check=True)`, `banner`, `step`, `wait_with_progress(seconds, label)` already in `run_scenario.py`.
- Produces: `restart_before_hold(cfg: dict) -> None`. YAML shape:

```yaml
restart_before_hold:
  deployments: [checkoutservice, recommendationservice]
  namespace: default        # optional, default "default"
  settle_seconds: 60        # optional, default 60
```

Absent key means no-op, so every existing YAML is unchanged.

- [ ] **Step 0: Record the starting commit for the final file list**

```powershell
git rev-parse HEAD
```

Write the printed SHA into `.superpowers/latch/base_sha.txt` (create the folder). The final task diffs against it.

```powershell
New-Item -ItemType Directory -Force ".superpowers/latch" | Out-Null
git rev-parse HEAD | Out-File -Encoding ascii ".superpowers/latch/base_sha.txt"
```

- [ ] **Step 1: Write the failing tests**

Append to `experiments/test_run_scenario.py`, above the `if __name__ == "__main__":` line (open the file's tail first and keep its existing runner block last):

```python
class TestRestartBeforeHold(unittest.TestCase):
    def _cfg(self, spec=None):
        cfg = {"infra": {"master_ssh_host": "topfull-master"}}
        if spec is not None:
            cfg["restart_before_hold"] = spec
        return cfg

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.ssh")
    def test_absent_key_is_noop(self, mock_ssh, mock_wait):
        run_scenario.restart_before_hold(self._cfg())
        mock_ssh.assert_not_called()
        mock_wait.assert_not_called()

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.ssh")
    def test_restarts_then_waits_for_rollout_then_settles(self, mock_ssh, mock_wait):
        mock_ssh.return_value = SimpleNamespace(stdout="", returncode=0)
        cfg = self._cfg({"deployments": ["checkoutservice", "recommendationservice"],
                         "settle_seconds": 45})
        run_scenario.restart_before_hold(cfg)
        cmds = [c.args[1] for c in mock_ssh.call_args_list]
        self.assertEqual(cmds[0], "kubectl rollout restart deployment/checkoutservice -n default")
        self.assertEqual(cmds[1], "kubectl rollout restart deployment/recommendationservice -n default")
        self.assertIn("rollout status deployment/checkoutservice -n default --timeout=180s", cmds[2])
        self.assertIn("rollout status deployment/recommendationservice -n default --timeout=180s", cmds[3])
        self.assertEqual(len(cmds), 4)
        mock_wait.assert_called_once()
        self.assertEqual(mock_wait.call_args.args[0], 45)

    @mock.patch("run_scenario.wait_with_progress")
    @mock.patch("run_scenario.ssh")
    def test_default_settle_is_60(self, mock_ssh, mock_wait):
        mock_ssh.return_value = SimpleNamespace(stdout="", returncode=0)
        run_scenario.restart_before_hold(self._cfg({"deployments": ["checkoutservice"]}))
        self.assertEqual(mock_wait.call_args.args[0], 60)
```

- [ ] **Step 2: Run to verify failure**

Run: `python experiments/test_run_scenario.py TestRestartBeforeHold -v`
Expected: three errors, `AttributeError: module 'run_scenario' has no attribute 'restart_before_hold'`.

- [ ] **Step 3: Implement**

In `experiments/run_scenario.py`, directly after the `apply_per_try_timeout` function, add:

```python
def restart_before_hold(cfg: dict) -> None:
    """
    Optional pod-restart treatment. Rolls the listed Deployments, waits for the
    rollout, then lets the cold pods settle before Locust starts. Absent key is
    a no-op. Must run before start_envoy_retry_collector: the collector seeds
    pod IPs once and a restart changes them.
    """
    spec = cfg.get("restart_before_hold")
    if not spec:
        return
    master = cfg["infra"]["master_ssh_host"]
    ns = spec.get("namespace", "default")
    deps = spec["deployments"]
    settle = int(spec.get("settle_seconds", 60))
    banner(f"Restarting before hold: {', '.join(deps)}")
    for dep in deps:
        ssh(master, f"kubectl rollout restart deployment/{dep} -n {ns}")
    for dep in deps:
        ssh(master, f"kubectl rollout status deployment/{dep} -n {ns} --timeout=180s")
    wait_with_progress(settle, "cold pods settle")
```

In `run()`, change

```python
        apply_per_try_timeout(cfg)

        start_master_stack(cfg)
```

to

```python
        apply_per_try_timeout(cfg)
        restart_before_hold(cfg)

        start_master_stack(cfg)
```

- [ ] **Step 4: Run to verify pass, then the whole module**

Run: `python experiments/test_run_scenario.py -v`
Expected: all pass, including the three new tests.

- [ ] **Step 5: Commit**

```powershell
git add experiments/run_scenario.py experiments/test_run_scenario.py
git commit -m "feat: optional restart_before_hold for latch probe"
```

---

### Task 2: `s2_latch_probe.py` helper (TDD)

**Files:**
- Create: `experiments/s2_latch_probe.py`
- Create: `experiments/test_s2_latch_probe.py`

**Interfaces:**
- Consumes: `s2_both_off_canon.score(n)` returning `{"svc": {name: {"streak","high","ov","rmode","rzero"}}, "edges": {(caller, target): retry_delta}, "q": {"span","gap2_pct"}}`; `s2_both_off_canon.ROOT` is a `%d` path pattern.
- Produces (used by every later task):
  - `build_config(base: dict, treatment: str, slot: int) -> dict`
  - `expected_replicas(treatment: str) -> dict[str, int]`
  - `prep_script(treatment: str) -> str` (bash; LF only)
  - `classify(o: dict) -> str` returning `"sticky"`, `"released"`, or `"other"`
  - `is_blend(o: dict) -> bool`
  - `sojourn_window(root: str, n: int, lo: int = 90, hi: int = 150) -> dict`
  - `gate(n: int, treatment: str, root: str = NEW_VMS) -> tuple[bool, list[str]]`
  - CLI: `config <treatment> <slot>`, `prep <treatment>`, `gate <treatment> <slot>`, `score <slot> [--root newvms|campaign]`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/test_s2_latch_probe.py`:

```python
"""Unit tests for s2_latch_probe. No network, no result folders."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s2_latch_probe as p


def base_cfg():
    return {
        "scenario_id": 2, "scenario_name": "sustained_overload", "condition": "baseline",
        "run_number": 1, "description": "x", "duration_seconds": 600,
        "locust": {"user_counts": {"getproduct": 275, "postcheckout": 85, "getcart": 100,
                                   "postcart": 90, "emptycart": 5},
                   "spawn_rate": 50, "scripts": ["online_boutique_create_v2.sh"]},
        "paper_cpu_reconcile": False,
        "scale_constraints": [
            {"deployment": "checkoutservice", "namespace": "default", "container": "server",
             "method": "cpu_limit", "cpu_limit_millicores": 800},
            {"deployment": "recommendationservice", "namespace": "default", "container": "server",
             "method": "cpu_limit", "cpu_limit_millicores": 1150},
        ],
        "log_folder": "old",
    }


def cpu(cfg, dep):
    return next(c["cpu_limit_millicores"] for c in cfg["scale_constraints"]
                if c["deployment"] == dep and c["method"] == "cpu_limit")


class TestBuildConfig(unittest.TestCase):
    def test_control_forces_run89_counts_and_names_the_slot(self):
        c = p.build_config(base_cfg(), "control", 111)
        self.assertEqual(c["locust"]["user_counts"], p.BASE_COUNTS)
        self.assertEqual(c["run_number"], 111)
        self.assertEqual(c["log_folder"], "baseline_no_topfull_sustained_overload_run111")
        self.assertEqual(c["locust"]["spawn_rate"], 50)
        self.assertNotIn("restart_before_hold", c)
        self.assertEqual(cpu(c, "checkoutservice"), 800)

    def test_input_is_not_mutated(self):
        b = base_cfg(); snap = copy.deepcopy(b)
        p.build_config(b, "ck_rep2_pc120", 115)
        self.assertEqual(b, snap)

    def test_each_treatment_changes_exactly_its_field(self):
        c = p.build_config(base_cfg(), "spawn10", 109)
        self.assertEqual(c["locust"]["spawn_rate"], 10)
        c = p.build_config(base_cfg(), "recs_users310", 114)
        self.assertEqual(c["locust"]["user_counts"]["getproduct"], 310)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        c = p.build_config(base_cfg(), "pc120", 117)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(c["locust"]["user_counts"]["getproduct"], 275)
        c = p.build_config(base_cfg(), "recs_cpu1000", 110)
        self.assertEqual(cpu(c, "recommendationservice"), 1000)
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        c = p.build_config(base_cfg(), "ck_cpu1000", 113)
        self.assertEqual(cpu(c, "checkoutservice"), 1000)
        self.assertEqual(cpu(c, "recommendationservice"), 1150)

    def test_replica_treatments_add_replicas_constraint_keeping_cpu(self):
        c = p.build_config(base_cfg(), "ck_rep2", 112)
        reps = [x for x in c["scale_constraints"] if x["method"] == "replicas"]
        self.assertEqual(len(reps), 1)
        self.assertEqual((reps[0]["deployment"], reps[0]["replicas"]), ("checkoutservice", 2))
        self.assertEqual(cpu(c, "checkoutservice"), 800)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 90)
        c = p.build_config(base_cfg(), "ck_rep2_pc120", 115)
        self.assertEqual(c["locust"]["user_counts"]["postcheckout"], 120)
        self.assertEqual(sum(1 for x in c["scale_constraints"] if x["method"] == "replicas"), 1)

    def test_restart_treatment_sets_restart_key_only(self):
        c = p.build_config(base_cfg(), "restart", 108)
        self.assertEqual(c["restart_before_hold"]["deployments"],
                         ["checkoutservice", "recommendationservice"])
        self.assertEqual(c["restart_before_hold"]["settle_seconds"], 60)
        self.assertEqual(c["locust"]["user_counts"], p.BASE_COUNTS)

    def test_unknown_treatment_raises(self):
        with self.assertRaises(KeyError):
            p.build_config(base_cfg(), "nope", 1)


class TestPrepAndExpected(unittest.TestCase):
    def test_expected_replicas(self):
        e = p.expected_replicas("control")
        self.assertEqual((e["frontend"], e["checkoutservice"]), (4, 1))
        self.assertEqual(p.expected_replicas("ck_rep2")["checkoutservice"], 2)
        self.assertEqual(p.expected_replicas("ck_rep2_pc120")["checkoutservice"], 2)

    def test_prep_script_sets_absolute_state_with_lf_only(self):
        s = p.prep_script("ck_cpu1000")
        self.assertNotIn("\r", s)
        self.assertIn('patch_cpu checkoutservice 1000m', s)
        self.assertIn('patch_cpu recommendationservice 1150m', s)
        self.assertIn('--replicas=1', s)
        s = p.prep_script("ck_rep2")
        self.assertIn('--replicas=2', s)
        self.assertIn('patch_cpu checkoutservice 800m', s)
        s = p.prep_script("recs_cpu1000")
        self.assertIn('patch_cpu recommendationservice 1000m', s)
        self.assertIn("status.phase=Pending", s)


class TestClassify(unittest.TestCase):
    def o(self, ck_streak, rc_streak, rc_ret, ck_ov=0, rc_ov=0, em=0, pay=0):
        return {"svc": {"checkoutservice": {"streak": ck_streak, "ov": ck_ov},
                        "recommendationservice": {"streak": rc_streak, "ov": rc_ov},
                        "emailservice": {"ov": em}, "paymentservice": {"ov": pay}},
                "edges": {("frontend", "recommendationservice"): rc_ret}}

    def test_sticky(self):
        self.assertEqual(p.classify(self.o(551, 0, 0)), "sticky")

    def test_released(self):
        self.assertEqual(p.classify(self.o(58, 238, 224314)), "released")

    def test_run101_recommendations_retries_are_released(self):
        # run101 frontend>recommendations retries are 76303, under the old 100k bar.
        self.assertEqual(p.classify(self.o(375, 77, 76303)), "released")

    def test_other(self):
        self.assertEqual(p.classify(self.o(0, 250, 50000)), "other")

    def test_blend_needs_all_four_bars_and_a_leaf(self):
        self.assertTrue(p.is_blend(self.o(58, 238, 224314, ck_ov=164, rc_ov=485, em=23)))
        self.assertFalse(p.is_blend(self.o(58, 238, 224314, ck_ov=164, rc_ov=485)))
        self.assertFalse(p.is_blend(self.o(5, 238, 224314, ck_ov=164, rc_ov=485, em=23)))
        self.assertTrue(p.is_blend(self.o(20, 30, 1, ck_ov=10, rc_ov=10, pay=10)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python experiments/test_s2_latch_probe.py -v`
Expected: `ModuleNotFoundError: No module named 's2_latch_probe'`.

- [ ] **Step 3: Implement the module**

Create `experiments/s2_latch_probe.py`:

```python
"""Helpers for the S2 checkout-latch probe series (runs 108-127).

CLI:
  python experiments/s2_latch_probe.py config <treatment> <slot>   # writes configs/scenario_2_latch_probe.yaml
  python experiments/s2_latch_probe.py prep <treatment>            # prints bash for: ssh topfull-master bash -s
  python experiments/s2_latch_probe.py gate <treatment> <slot>     # exit 0 = pass
  python experiments/s2_latch_probe.py score <slot> [--root newvms|campaign]
"""
import copy
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_both_off_canon as canon  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE_CONFIG = HERE / "configs" / "scenario_2_baseline_no_topfull.yaml"
OUT_CONFIG = HERE / "configs" / "scenario_2_latch_probe.yaml"
NEW_VMS = str(REPO / "experiments" / "results" / "new vms" /
              "baseline_no_topfull_sustained_overload_run%d")
CAMPAIGN = canon.ROOT

BASE_COUNTS = {"getproduct": 275, "postcheckout": 90, "getcart": 100,
               "postcart": 90, "emptycart": 5}
CHECKOUT_MC, RECS_MC = 800, 1150

# treatment -> overrides. Keys: spawn_rate, counts, checkout_cpu, recs_cpu,
# checkout_replicas, restart.
TREATMENTS = {
    "control": {},
    "spawn10": {"spawn_rate": 10},
    "restart": {"restart": True},
    "recs_users310": {"counts": {"getproduct": 310}},
    "recs_cpu1000": {"recs_cpu": 1000},
    "ck_cpu1000": {"checkout_cpu": 1000},
    "ck_rep2": {"checkout_replicas": 2},
    "pc120": {"counts": {"postcheckout": 120}},
    "ck_rep2_pc120": {"checkout_replicas": 2, "counts": {"postcheckout": 120}},
}


def _set_cpu(cfg, dep, mc):
    for c in cfg["scale_constraints"]:
        if c["deployment"] == dep and c["method"] == "cpu_limit":
            c["cpu_limit_millicores"] = mc
            return
    raise KeyError(f"no cpu_limit constraint for {dep}")


def build_config(base: dict, treatment: str, slot: int) -> dict:
    t = TREATMENTS[treatment]
    cfg = copy.deepcopy(base)
    cfg["run_number"] = slot
    cfg["log_folder"] = f"baseline_no_topfull_sustained_overload_run{slot}"
    cfg["description"] = (f"Both controllers off. Paper-C1. Latch probe, treatment "
                          f"{treatment}, run89 mix base.")
    cfg["locust"]["user_counts"] = {**BASE_COUNTS, **t.get("counts", {})}
    cfg["locust"]["spawn_rate"] = t.get("spawn_rate", 50)
    if "checkout_cpu" in t:
        _set_cpu(cfg, "checkoutservice", t["checkout_cpu"])
    if "recs_cpu" in t:
        _set_cpu(cfg, "recommendationservice", t["recs_cpu"])
    if "checkout_replicas" in t:
        cfg["scale_constraints"].append({
            "deployment": "checkoutservice", "namespace": "default",
            "method": "replicas", "replicas": t["checkout_replicas"]})
    if t.get("restart"):
        cfg["restart_before_hold"] = {
            "deployments": ["checkoutservice", "recommendationservice"],
            "settle_seconds": 60}
    return cfg


def expected_replicas(treatment: str) -> dict:
    out = {"frontend": 4}
    out["checkoutservice"] = TREATMENTS[treatment].get("checkout_replicas", 1)
    return out


_PREP = """set -e
patch_cpu() {
  kubectl patch deployment "$1" -n default -p \
    "{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"server\\",\\"resources\\":{\\"limits\\":{\\"cpu\\":\\"$2\\"},\\"requests\\":{\\"cpu\\":\\"$2\\"}}}]}}}}"
}
patch_cpu checkoutservice @CK@m
patch_cpu recommendationservice @RC@m
kubectl scale deployment/checkoutservice -n default --replicas=@REP@
kubectl rollout status deployment/checkoutservice -n default --timeout=240s
kubectl rollout status deployment/recommendationservice -n default --timeout=240s
echo "--- pods"
kubectl get pods -n default -o wide
echo "--- pending"
kubectl get pods -n default --field-selector=status.phase=Pending --no-headers
echo "--- end"
"""


def prep_script(treatment: str) -> str:
    t = TREATMENTS[treatment]
    s = (_PREP.replace("@CK@", str(t.get("checkout_cpu", CHECKOUT_MC)))
              .replace("@RC@", str(t.get("recs_cpu", RECS_MC)))
              .replace("@REP@", str(t.get("checkout_replicas", 1))))
    return s.replace("\r", "")


def is_blend(o: dict) -> bool:
    s = o["svc"]
    g = lambda svc, k: s.get(svc, {}).get(k, 0) or 0  # noqa: E731
    return (g("recommendationservice", "streak") >= 10 and g("recommendationservice", "ov") >= 10
            and g("checkoutservice", "streak") >= 10 and g("checkoutservice", "ov") >= 10
            and (g("emailservice", "ov") >= 10 or g("paymentservice", "ov") >= 10))


def classify(o: dict) -> str:
    s = o["svc"]
    ck = s.get("checkoutservice", {}).get("streak", 0) or 0
    rc = s.get("recommendationservice", {}).get("streak", 0) or 0
    ret = o["edges"].get(("frontend", "recommendationservice"), 0)
    if ck >= 400 and rc == 0:
        return "sticky"
    # 70_000 sits under run 101's 76,303 frontend>recommendations retries and
    # above the 50,000 count that stays "other".
    if ret >= 70000:
        return "released"
    return "other"


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp()


def sojourn_window(root: str, n: int, lo: int = 90, hi: int = 150) -> dict:
    """Checkout inbound mean sojourn (ms) and share of ticks above 500 ms, lo..hi s
    after the first checkout row. Clock is the collector's, not Locust's."""
    path = os.path.join(root % n, "service_inbound.csv")
    rows = [r for r in csv.DictReader(open(path)) if r["service"] == "checkoutservice"]
    if len(rows) < 2:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    t0 = _ts(rows[0]["timestamp"])
    vals = []
    for a, b in zip(rows, rows[1:]):
        t = _ts(b["timestamp"]) - t0
        if not (lo <= t <= hi):
            continue
        dc = float(b["rq_time_count"]) - float(a["rq_time_count"])
        ds = float(b["rq_time_sum_ms"]) - float(a["rq_time_sum_ms"])
        if dc > 0:
            vals.append(ds / dc)
    if not vals:
        return {"mean_ms": None, "share_over_500": None, "ticks": 0}
    return {"mean_ms": round(sum(vals) / len(vals), 1),
            "share_over_500": round(sum(v > 500 for v in vals) / len(vals), 2),
            "ticks": len(vals)}


def gate(n: int, treatment: str, root: str = NEW_VMS):
    canon.ROOT = root
    d = root % n
    problems, notes = [], []
    need = ["service_inbound.csv", "service_edges.csv", "topfull_detect.csv",
            "resource_usage.csv", "total.csv", "service_capacity.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(d, f))]
    if missing:
        return False, [f"missing {missing}"]
    rows = sum(1 for _ in open(os.path.join(d, "total.csv"))) - 1
    o = canon.score(n)
    q, s = o["q"], o["svc"]
    notes.append(f"rows {rows} span {round(q.get('span', 0))} gap2 {q.get('gap2_pct')}")
    if rows < 500:
        problems.append(f"total.csv rows {rows} < 500")
    if not (480 <= q.get("span", 0) <= 900):
        problems.append(f"mesh span {q.get('span')} outside 480-900")
    if q.get("gap2_pct", 100) > 10:
        problems.append(f"gap2_pct {q.get('gap2_pct')} > 10")
    exp = expected_replicas(treatment)
    for svc, v in s.items():
        if svc == "__master_node__" or "rmode" not in v:
            continue
        want = exp.get(svc, 1)
        if v["rmode"] != want:
            problems.append(f"{svc} replica mode {v['rmode']} != {want}")
        if v.get("rzero", 0) > 0 and svc in ("checkoutservice", "recommendationservice"):
            notes.append(f"WARN {svc} rzero {v['rzero']}")
    return not problems, problems + notes


def score_line(n: int, root: str) -> str:
    canon.ROOT = root
    o = canon.score(n)
    s = o["svc"]
    f = lambda svc, k: s.get(svc, {}).get(k)  # noqa: E731
    soj = sojourn_window(root, n)
    ret_r = o["edges"].get(("frontend", "recommendationservice"), 0)
    ret_c = o["edges"].get(("frontend", "checkoutservice"), 0)
    return (f"run{n} {classify(o)} blend={is_blend(o)} "
            f"ck streak/ov {f('checkoutservice','streak')}/{f('checkoutservice','ov')} "
            f"recs streak/ov {f('recommendationservice','streak')}/{f('recommendationservice','ov')} "
            f"email_ov {f('emailservice','ov')} pay_ov {f('paymentservice','ov')} "
            f"retries f>recs {int(ret_r)} f>ck {int(ret_c)} "
            f"ck_sojourn_90_150 {soj['mean_ms']}ms over500 {soj['share_over_500']}")


def main(argv):
    cmd = argv[1]
    if cmd == "config":
        base = yaml.safe_load(open(BASE_CONFIG, encoding="utf-8"))
        cfg = build_config(base, argv[2], int(argv[3]))
        OUT_CONFIG.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        print(f"wrote {OUT_CONFIG} for {argv[2]} run{argv[3]}")
        return 0
    if cmd == "prep":
        sys.stdout.buffer.write(prep_script(argv[2]).encode())
        return 0
    if cmd == "gate":
        ok, lines = gate(int(argv[3]), argv[2])
        print("\n".join(lines))
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    if cmd == "score":
        root = CAMPAIGN if "--root" in argv and argv[argv.index("--root") + 1] == "campaign" else NEW_VMS
        print(score_line(int(argv[2]), root))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run to verify pass**

Run: `python experiments/test_s2_latch_probe.py -v`
Expected: all tests pass. Also run `python experiments/test_run_scenario.py` and `python experiments/test_topfull_cpu_quotas.py`; the latter already has one known failure (`TestBothOffYamlRestored`, see [2026-10-03-s2-paper-c1-replays.md](2026-10-03-s2-paper-c1-replays.md)). Any other new failure is yours; fix it.

- [ ] **Step 5: Commit**

```powershell
git add experiments/s2_latch_probe.py experiments/test_s2_latch_probe.py
git commit -m "feat: s2 latch probe helper (config, prep, gate, score)"
```

---

### Task 3: Per-hold scripts

**Files:**
- Create: `experiments/latch_snapshot.sh` (LF line endings)
- Create: `experiments/latch_hold_pre.ps1`
- Create: `experiments/latch_hold_run.ps1`

**Interfaces:**
- Consumes: `s2_latch_probe.py` CLI from Task 2; `run_scenario.py`; `pull_results.py`.
- Produces: `latch_hold_pre.ps1 -Treatment T [-DryRun]` (prep and Pending check) and `latch_hold_run.ps1 -Treatment T -Slot N [-DryRun]` (everything from t=0 snapshot to score; exit 0 only when the gate passes). Both are called with these exact arguments in every hold task.

- [ ] **Step 1: Write the snapshot script**

Create `experiments/latch_snapshot.sh` (must stay LF; run `git ls-files --eol experiments/latch_snapshot.sh` after adding and confirm `w/lf`):

```bash
echo "### pods"
kubectl get pods -n default -o wide
echo "### nodes"
kubectl get nodes -o wide
echo "### hpa"
kubectl get hpa -n default
echo "### sidecar annotations"
kubectl get deploy -n default -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.metadata.annotations}{"\n"}{end}'
echo "### worker allocated resources"
kubectl describe node topfull-worker-1 | grep -A8 'Allocated resources'
```

- [ ] **Step 2: Write the prep wrapper**

Create `experiments/latch_hold_pre.ps1`:

```powershell
param(
    [Parameter(Mandatory)][string]$Treatment,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($DryRun) {
    python experiments/s2_latch_probe.py prep $Treatment
    exit 0
}

# cmd /c keeps the pipe byte-exact (PowerShell would add CRLF to the bash script).
$out = cmd /c "python experiments\s2_latch_probe.py prep $Treatment | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s" 2>&1
$rc = $LASTEXITCODE
$out | ForEach-Object { Write-Host $_ }
if ($rc -ne 0) { Write-Error "prep failed rc=$rc"; exit 1 }

$text = ($out | ForEach-Object { "$_" }) -join "`n"
if ($text -notmatch "--- end") { Write-Error "prep did not reach '--- end'"; exit 1 }
$m = [regex]::Match($text, '(?s)--- pending\r?\n(.*?)--- end')
if ($m.Success -and $m.Groups[1].Value.Trim().Length -gt 0) {
    Write-Error "Pending pods after prep: $($m.Groups[1].Value.Trim())"
    exit 1
}
Write-Host "PREP OK for $Treatment"
exit 0
```

- [ ] **Step 3: Write the run wrapper**

Create `experiments/latch_hold_run.ps1`:

```powershell
param(
    [Parameter(Mandatory)][string]$Treatment,
    [Parameter(Mandatory)][int]$Slot,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$name = "baseline_no_topfull_sustained_overload_run$Slot"
$src  = "experiments\results\campaign_48\S2_sustained_overload\$name"
$dest = "experiments\results\new vms\$name"
$S    = ".superpowers\latch\state\run$Slot"
$cfg  = "experiments/configs/scenario_2_latch_probe.yaml"

function Step([string]$Label, [scriptblock]$Block) {
    Write-Host "==> $Label"
    if ($DryRun) { Write-Host "    (dry run) $Block"; return }
    $global:LASTEXITCODE = 0
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "$Label failed rc=$LASTEXITCODE" }
}

function Save-Snapshot([string]$File) {
    $m = cmd /c "ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s < experiments\latch_snapshot.sh" 2>&1
    $w = ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "uname -r; uptime -s; nproc" 2>&1
    $lines = @("# captured " + (Get-Date -Format o)) + $m + @("### worker kernel / boot / nproc") + $w
    $lines | ForEach-Object { "$_" } | Out-File -Encoding utf8 $File
}

if ((Test-Path $dest) -or (Test-Path $src)) { throw "$name already exists locally; refusing to overwrite" }

Step "t=0 snapshot" { New-Item -ItemType Directory -Force $S | Out-Null; Save-Snapshot "$S\t0.txt" }
Step "generate config" { python experiments/s2_latch_probe.py config $Treatment $Slot }
Step "clear stale remote scripts" {
    ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
}
Step "run hold (about 17 min)" { python experiments/run_scenario.py $cfg }
Step "pull" { python experiments/pull_results.py $cfg }
Step "move into new vms" { Move-Item $src "experiments\results\new vms\" }
Step "end snapshot" { Save-Snapshot "$S\end.txt" }
Step "copy snapshots into run folder" { Copy-Item $S "$dest\state" -Recurse }

if ($DryRun) { exit 0 }

python experiments/s2_latch_probe.py gate $Treatment $Slot
$gateRc = $LASTEXITCODE
python experiments/s2_latch_probe.py score $Slot
exit $gateRc
```

- [ ] **Step 4: Dry-run both scripts**

```powershell
powershell -NoProfile -File experiments\latch_hold_pre.ps1 -Treatment ck_rep2 -DryRun
powershell -NoProfile -File experiments\latch_hold_run.ps1 -Treatment ck_rep2 -Slot 999 -DryRun
```

Expected: the first prints the bash with `--replicas=2` and `patch_cpu checkoutservice 800m`, no `\r`. The second prints the nine `==>` steps with `(dry run)` and touches nothing (check `git status` shows no new run folder and no `scenario_2_latch_probe.yaml`). If the second throws "already exists", slot 999 collided; pick another unused number.

- [ ] **Step 5: Commit**

```powershell
git add experiments/latch_snapshot.sh experiments/latch_hold_pre.ps1 experiments/latch_hold_run.ps1
git commit -m "feat: per-hold scripts for the latch probe"
```

---

### Task 4: Retro-score runs 86–107 to prove the classifier (no VMs)

**Files:**
- Create: `Guides and Info/2026-10-03-s2-latch-probe-results.md` (retro table only for now)

**Interfaces:**
- Consumes: `s2_latch_probe.py score <slot> [--root campaign]`. Runs 86, 88, 89, 92 are under `campaign_48/S2_sustained_overload/` (use `--root campaign`); runs 94–107 are under `new vms/`.
- Produces: a table of sticky / released / other and the checkout 90–150 s sojourn for the existing holds, used as the baseline in the results guide. This is the replays-differ guide's checks 2 and 3.

- [ ] **Step 1: Score the campaign-root runs**

```powershell
foreach ($n in 86,87,88,89,90,91,92,93) { python experiments/s2_latch_probe.py score $n --root campaign }
```

Expected: one line per run. Run 85 is excluded (sampling gate failed in the handoff). A `FileNotFoundError` means that run is not in this folder: skip it and say so in the table.

- [ ] **Step 2: Score the new-vms runs**

```powershell
foreach ($n in 94..107) { python experiments/s2_latch_probe.py score $n }
```

- [ ] **Step 3: Check the classifier against the known verdicts**

Sticky must be exactly runs 94, 95, 96, 100, 102, 103, 104, 106, 107 (handoff and 99–107 guide). Released must include 86, 88, 89, 92, 97, 99, 101, 105. Run 98 (recommendations only, checkout streak 0) must be `released` or `other`, not `sticky`. If any run disagrees, the thresholds are wrong; stop and fix `classify` (add a failing test first) before any VM starts.

Also record whether the checkout 90–150 s sojourn separates the modes: sticky holds should sit near or above about 480 ms with most ticks over 500 ms; released holds should fall below. If it does not separate cleanly, write that down: it refutes the threshold story in the replays-differ guide and changes how the probe results are read.

- [ ] **Step 4: Write the retro table**

Create `Guides and Info/2026-10-03-s2-latch-probe-results.md` with a title, a one-paragraph purpose ("results of runs 108–127; this section is the retro-scoring of runs 86–107"), and a table: Run, Cluster (original or disk copy), Mix, Class, Blend, Checkout streak/ov, Recs streak/ov, Retries f>recs, Retries f>ck, Checkout sojourn 90–150 s, Over-500 share. Under it, one paragraph stating the sticky and released counts and whether sojourn separated the modes. The run 108–127 section is added in the final task.

- [ ] **Step 5: Commit**

```powershell
git add "Guides and Info/2026-10-03-s2-latch-probe-results.md"
git commit -m "docs: retro-score runs 86-107 as sticky/released"
```

---

### Task 5: Start the VMs and confirm the Paper-C1 base

**Files:** none modified.

**Interfaces:**
- Consumes: Tasks 1–4 committed.
- Produces: three VMs RUNNING, SSH working, frontend HPA 4/4, catalog HPA 1/1, Paper-C1 limits and sidecar request 100 m live, slots 108–127 absent on master and locally.

- [ ] **Step 1: Start the VMs**

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: three rows `RUNNING` with a natIP. A `CPUS_ALL_REGIONS` error: stop and report. Do not resize.

- [ ] **Step 2: Refresh SSH and confirm the API**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) "Reconnect after VMs were stopped": `ssh-keygen -R` each old HostName and each new natIP, change only the three `HostName` lines.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: master and worker Ready. If the API is still starting, wait with AwaitShell `block_until_ms: 60000` and retry once.

- [ ] **Step 3: Confirm the slots are free**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run(10[89]|11[0-9]|12[0-7])$' || echo none"
Get-ChildItem "experiments\results\new vms","experiments\results\campaign_48\S2_sustained_overload" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'run(10[89]|11[0-9]|12[0-7])$' }
```

Expected: `none` and no local output. If anything exists, stop; shift every slot up past the highest existing run and edit the order table before Task 6.

- [ ] **Step 4: Confirm the base pin**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get hpa -n default; kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas,CPU:.spec.template.spec.containers[0].resources.limits.cpu,PROXY:.spec.template.metadata.annotations.sidecar\\.istio\\.io/proxyCPU,PROXYLIM:.spec.template.metadata.annotations.sidecar\\.istio\\.io/proxyCPULimit"
```

Expected: frontend-hpa min 4 max 4; productcatalogservice-hpa min 1 max 1; the Paper-C1 limits from Global Constraints; every PROXY `100m`; every PROXYLIM `<none>`; frontend replicas 4, all others 1. If the HPAs or sidecar annotations drifted, correct them with the patches in Task 1 Step 4 of [2026-10-03-s2-paper-c1-replays.md](2026-10-03-s2-paper-c1-replays.md); do not reconcile paper CPU.

No commit in this task.

---

### Hold task pattern

Tasks 6–25 are the twenty holds, in slot order. Each has the same four steps with that hold's own treatment and slot written into the commands:

1. `.\experiments\latch_hold_pre.ps1 -Treatment <T>` sets the starting state (checkout CPU, recommendations CPU, checkout replicas) and fails on a Pending pod. An unchanged value patches as a no-op and restarts nothing; a changed value rolls only that Deployment.
2. A 360 s cool-off via AwaitShell.
3. `.\experiments\latch_hold_run.ps1 -Treatment <T> -Slot <N>` takes the t=0 snapshot, generates the config, launches the 600 s hold, pulls, moves, takes the end snapshot, copies both into the run folder's `state/`, then prints the gate result and the score line. Shell `block_until_ms: 1200000`. Exit 0 means the gate passed.
4. Commit the run folder and the generated config.

---

### Task 6: Hold run108 — `restart` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run108/`

**Interfaces:**
- Consumes: Task 5 done; Task 1's `restart_before_hold`.
- Produces: run108 folder. The roll happens after the cool-off, so `t0.txt` shows the old pods and `end.txt` shows checkout and recommendations pods only minutes old.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment restart
```

Expected: `PREP OK for restart`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment restart -Slot 108
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `Restarting before hold: checkoutservice, recommendationservice`, both rollouts complete, a 60 s settle, then the hold; the script ends with `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

In `state/end.txt`, only the checkout and recommendations pods should be minutes old; every other pod matches `t0.txt`.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run108" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run108 restart"
```

---

### Task 7: Hold run109 — `spawn10` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run109/`

**Interfaces:**
- Consumes: run108 committed.
- Produces: run109 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment spawn10
```

Expected: `PREP OK for spawn10`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment spawn10 -Slot 109
```

Shell `block_until_ms`: 1200000. Expected: the runner output shows `export RATE=10`; the script ends with `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

In `getproduct.csv` the user count reaches 275 within about 10–15 s of the first non-zero row (other holds take about 50 s). If it does not, the ramp change did not apply; say so in the guide.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run109" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run109 spawn10"
```

---

### Task 8: Hold run110 — `recs_cpu1000` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run110/`

**Interfaces:**
- Consumes: run109 committed.
- Produces: run110 folder. Prep patches recommendations to 1000 m (rolls that pod; the cool-off ages it about 6 minutes).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000
```

Expected: `PREP OK for recs_cpu1000`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000 -Slot 110
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `recommendationservice/server already at 1000m; skipping patch`; the script ends with `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

`service_capacity.json` shows recommendationservice 1000.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run110" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run110 recs_cpu1000"
```

---

### Task 9: Hold run111 — `control` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run111/`

**Interfaces:**
- Consumes: run110 committed. Recommendations is at 1000 m from the last hold; this prep sets it back to 1150 m, which rolls recommendations once.
- Produces: run111 folder; the first control.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 111
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

Same mix and table as runs 89, 92, 94–97, 99–101; the runner log must show no applied CPU patch.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run111" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run111 control"
```

---

### Task 10: Hold run112 — `ck_rep2` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run112/`

**Interfaces:**
- Consumes: run111 committed.
- Produces: run112 folder. Checkout has two 800 m pods; prep scales it so the second pod is Ready and about 6 minutes old at Locust start. The runner records `original_replicas: 2` and leaves 2, so the next hold's prep scales back to 1 (every prep sets `--replicas` explicitly).

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2
```

Expected: `PREP OK for ck_rep2`; two checkoutservice pods `2/2 Running` in the printed pod list. A Pending pod makes the script fail: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2 -Slot 112
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `Scaling checkoutservice (default): 2 -> 2 replicas`; the script ends with `PASS` (checkout replica mode 2) and a score line.

- [ ] **Step 4: Treatment check, then commit**

Record per-pod checkout CPU (summed `cpu_millicores` in `resource_usage.csv` divided by 2, against 800 m) and the checkout 90–150 s sojourn: if it stays below 500 ms the latch loop never formed.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run112" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run112 ck_rep2"
```

---

### Task 11: Hold run113 — `ck_cpu1000` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run113/`

**Interfaces:**
- Consumes: run112 committed (checkout at 2 replicas; this prep scales it back to 1 and patches 1000 m).
- Produces: run113 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000
```

Expected: `PREP OK for ck_cpu1000`; one checkout pod.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000 -Slot 113
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `checkoutservice/server already at 1000m; skipping patch`; the script ends with `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

`service_capacity.json` shows checkoutservice 1000.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run113" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run113 ck_cpu1000"
```

---

### Task 12: Hold run114 — `recs_users310` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run114/`

**Interfaces:**
- Consumes: run113 committed (checkout at 1000 m; this prep sets it back to 800 m).
- Produces: run114 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_users310
```

Expected: `PREP OK for recs_users310`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_users310 -Slot 114
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

Mean getproduct `RPS` should be about 96% of 310 (near 298). Record frontend sojourn and getproduct goodput against the 94–101 range (263–264 sticky, 26–194 released).

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run114" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run114 recs_users310"
```

---

### Task 13: Hold run115 — `ck_rep2_pc120` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run115/`

**Interfaces:**
- Consumes: run114 committed.
- Produces: run115 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120
```

Expected: `PREP OK for ck_rep2_pc120`; two checkout pods.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120 -Slot 115
```

Shell `block_until_ms`: 1200000. Expected: `PASS` (checkout replica mode 2) and a score line.

- [ ] **Step 4: Treatment check, then commit**

Record payment and email overloaded ticks: more checkout throughput should raise their load, which helps the blend leaf. Mean postcheckout `RPS` should be above the 90-user holds' about 86.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run115" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run115 ck_rep2_pc120"
```

---

### Task 14: Hold run116 — `control` (block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run116/`

**Interfaces:**
- Consumes: run115 committed (checkout at 2 replicas; this prep scales it back to 1).
- Produces: run116 folder; the second control.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control`; one checkout pod.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 116
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

The runner log must show no applied CPU patch.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run116" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run116 control"
```

---

### Task 15: Hold run117 — `pc120` (block A, last of block A)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run117/`

**Interfaces:**
- Consumes: run116 committed.
- Produces: run117 folder. Block A ends here; the VMs stay up into block B.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment pc120
```

Expected: `PREP OK for pc120`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment pc120 -Slot 117
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

Mean postcheckout `RPS` should be near 96% of 120 (about 115). Note the clock time of the end of this hold: it is the block boundary.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run117" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run117 pc120"
```

---

### Task 16: Hold run118 — `recs_users310` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run118/`

**Interfaces:**
- Consumes: run117 committed.
- Produces: run118 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_users310
```

Expected: `PREP OK for recs_users310`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_users310 -Slot 118
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

Mean getproduct `RPS` near 298.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run118" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run118 recs_users310"
```

---

### Task 17: Hold run119 — `ck_rep2` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run119/`

**Interfaces:**
- Consumes: run118 committed.
- Produces: run119 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2
```

Expected: `PREP OK for ck_rep2`; two checkout pods. A Pending pod: stop and report.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2 -Slot 119
```

Shell `block_until_ms`: 1200000. Expected: `PASS` (checkout replica mode 2) and a score line.

- [ ] **Step 4: Treatment check, then commit**

Record per-pod checkout CPU and the checkout 90–150 s sojourn, as in run112.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run119" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run119 ck_rep2"
```

---

### Task 18: Hold run120 — `spawn10` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run120/`

**Interfaces:**
- Consumes: run119 committed (checkout at 2 replicas; this prep scales it back to 1).
- Produces: run120 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment spawn10
```

Expected: `PREP OK for spawn10`; one checkout pod.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment spawn10 -Slot 120
```

Shell `block_until_ms`: 1200000. Expected: the runner output shows `export RATE=10`; `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

The `getproduct.csv` user count reaches 275 within about 10–15 s of the first non-zero row.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run120" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run120 spawn10"
```

---

### Task 19: Hold run121 — `control` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run121/`

**Interfaces:**
- Consumes: run120 committed.
- Produces: run121 folder; the third control.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 121
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

The runner log must show no applied CPU patch.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run121" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run121 control"
```

---

### Task 20: Hold run122 — `ck_cpu1000` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run122/`

**Interfaces:**
- Consumes: run121 committed.
- Produces: run122 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_cpu1000
```

Expected: `PREP OK for ck_cpu1000`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_cpu1000 -Slot 122
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `checkoutservice/server already at 1000m; skipping patch`; `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

`service_capacity.json` shows checkoutservice 1000.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run122" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run122 ck_cpu1000"
```

---

### Task 21: Hold run123 — `ck_rep2_pc120` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run123/`

**Interfaces:**
- Consumes: run122 committed (checkout at 1000 m; this prep sets 800 m with 2 replicas).
- Produces: run123 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment ck_rep2_pc120
```

Expected: `PREP OK for ck_rep2_pc120`; two checkout pods.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment ck_rep2_pc120 -Slot 123
```

Shell `block_until_ms`: 1200000. Expected: `PASS` (checkout replica mode 2) and a score line.

- [ ] **Step 4: Treatment check, then commit**

Record payment and email overloaded ticks and mean postcheckout `RPS`, as in run115.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run123" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run123 ck_rep2_pc120"
```

---

### Task 22: Hold run124 — `restart` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run124/`

**Interfaces:**
- Consumes: run123 committed (checkout at 2 replicas; this prep scales it back to 1).
- Produces: run124 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment restart
```

Expected: `PREP OK for restart`; one checkout pod.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment restart -Slot 124
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `Restarting before hold: checkoutservice, recommendationservice`, a 60 s settle, then the hold; `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

In `state/end.txt`, only the checkout and recommendations pods should be minutes old.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run124" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run124 restart"
```

---

### Task 23: Hold run125 — `pc120` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run125/`

**Interfaces:**
- Consumes: run124 committed.
- Produces: run125 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment pc120
```

Expected: `PREP OK for pc120`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment pc120 -Slot 125
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

Mean postcheckout `RPS` near 115.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run125" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run125 pc120"
```

---

### Task 24: Hold run126 — `recs_cpu1000` (block B)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run126/`

**Interfaces:**
- Consumes: run125 committed.
- Produces: run126 folder.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment recs_cpu1000
```

Expected: `PREP OK for recs_cpu1000`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment recs_cpu1000 -Slot 126
```

Shell `block_until_ms`: 1200000. Expected: the runner log shows `recommendationservice/server already at 1000m; skipping patch`; `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

`service_capacity.json` shows recommendationservice 1000.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run126" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run126 recs_cpu1000"
```

---

### Task 25: Hold run127 — `control` (block B, last hold)

**Files:**
- Generate: `experiments/configs/scenario_2_latch_probe.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run127/`

**Interfaces:**
- Consumes: run126 committed (recommendations at 1000 m; this prep sets it back to 1150 m).
- Produces: run127 folder; the fourth control. No cool-off follows it.

- [ ] **Step 1: Prep the starting state**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control`.

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Run the hold**

```powershell
.\experiments\latch_hold_run.ps1 -Treatment control -Slot 127
```

Shell `block_until_ms`: 1200000. Expected: `PASS` and a score line.

- [ ] **Step 4: Treatment check, then commit**

The runner log must show no applied CPU patch.

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run127" experiments/configs/scenario_2_latch_probe.yaml
git commit -m "data: S2 latch probe run127 control"
```

---

### Task 26: Results guide, bookkeeping, terminate the VMs, commit everything, push, list the files

**Files:**
- Modify: `Guides and Info/2026-10-03-s2-latch-probe-results.md` (add the run 108–127 section)
- Modify: `Guides and Info/2026-10-03-s2-same-mix-replays-differ.md` (append a short section)
- Modify: `experiments/results/README.md`
- Modify: `AGENTS.md`
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Commit (already in the working tree, untracked at plan time): `docs/superpowers/plans/2026-10-03-s2-latch-probe-holds.md`, `docs/superpowers/plans/2026-10-03-s2-paper-c1-replays.md`, `Guides and Info/2026-10-03-s2-paper-c1-runs-99-107.md`, and any other file `git status` shows that this series left behind.

**Interfaces:**
- Consumes: the score lines from Tasks 6–25; `.superpowers/latch/base_sha.txt` from Task 1.
- Produces: a results guide, the next free both-off slot **run128**, VMs `TERMINATED`, branch pushed, and a user-facing summary that lists every file touched.

- [ ] **Step 1: Return the cluster to the Paper-C1 base**

```powershell
.\experiments\latch_hold_pre.ps1 -Treatment control
```

Expected: `PREP OK for control`: checkout 800 m × 1, recommendations 1150 m × 1. Frontend HPA stays 4/4 and catalog HPA 1/1 (the series leaves the Paper-C1 pin, as the earlier Paper-C1 series did).

- [ ] **Step 2: Terminate the VMs**

Do this before the doc commit so the summary can say they are terminated.

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: three rows, status `TERMINATED`. If any row is not `TERMINATED`, rerun the stop and check again; do not continue until all three are.

- [ ] **Step 3: Collect the final score table**

```powershell
foreach ($n in 108..127) { python experiments/s2_latch_probe.py score $n }
```

A hold that failed its gate or was not run gets a blank row with one sentence naming the gate.

- [ ] **Step 4: Add the run 108–127 section to the results guide**

Append to `Guides and Info/2026-10-03-s2-latch-probe-results.md`:

1. **Setup paragraph:** base (run 89 mix, Paper-C1), twenty holds in two shuffled blocks (seed 20261003), one change each, prep-before-cool-off rule, any hold where the runner log showed an applied CPU patch instead of `skipping patch`, and the block-boundary time (end of run117).
2. **Per-hold table:** Slot, Block, Treatment, Class (sticky / released / other), Blend (yes/no), checkout streak/ov, recs streak/ov, email ov, payment ov, retries f>recs, retries f>ck, checkout 90–150 s sojourn and over-500 share, getproduct goodput, frontend sojourn, checkout and recommendations pod age at t=0 (from `state/t0.txt`).
3. **Verdict per lever**, using the honesty rule's wording exactly: **moved**, **no effect seen**, or **mixed**. Levers: `pc120`, `recs_users310`, `ck_rep2`, `ck_cpu1000`, `recs_cpu1000`, `ck_rep2_pc120`, `spawn10`, `restart`. For `ck_rep2` and `ck_rep2_pc120`, also report per-pod checkout CPU (summed CPU / 2) and whether sojourn stayed under 500 ms in both holds; if so the extra verdict is "latch avoided", which is not the same as a blend. For `spawn10`, report the ramp length seen in `getproduct.csv`.
4. **Controls:** the four controls (111, 116, 121, 127) as their own sticky/blend counts, next to the 7 earlier holds of this mix on the copy (3 blends, 4 sticky), and a one-line comment on whether block A and block B controls agree.
5. **Replays-differ checks answered:** (a) did sticky holds share a pod placement, restart count, pod age, or kernel pattern in `state/t0.txt`, (b) did the checkout 90–150 s sojourn separate sticky from released across all scored holds (86–127), (c) did block order show any drift.
6. **Follow-up:** for each **moved** lever (or one with "latch avoided"), one line proposing three interleaved replays; drop the rest. Include the sample-size note that about eight holds of one configuration separate a 1-in-5 from a 3-in-5 latch rate.

- [ ] **Step 5: Append to the replays-differ guide**

At the end of `Guides and Info/2026-10-03-s2-same-mix-replays-differ.md`, replace the "Not run" section's text with a "Probe result" section: one paragraph that says runs 108–127 ran the restart, interleave, and snapshot checks described above, with a link to `2026-10-03-s2-latch-probe-results.md` and a one-line answer to "did a restart, or hidden pod state, explain the cluster difference". Leave every earlier section as it is.

- [ ] **Step 6: Bookkeeping**

In `experiments/configs/scenario_2_baseline_no_topfull.yaml` change only these fields:

```yaml
# Both-off S2. Slot run128 is unused.
run_number: 128
description: >
  Unused slot. Paper-C1 pin may still be live.
  Counts below are 275/85/100/90/5, already launched as run105-run107.
log_folder: baseline_no_topfull_sustained_overload_run128
```

Leave counts, `scale_constraints`, and `paper_cpu_reconcile: false` as they are.

In `experiments/results/README.md`, extend the `new vms/` sentence to include run108–run127.

In `AGENTS.md` §4 add one bullet: twenty latch-probe holds run108–run127, base run 89 mix on Paper-C1, one change per hold in two shuffled blocks, folders under `experiments/results/new vms/`, results guide linked, the per-lever verdicts from Step 4, and the new `restart_before_hold` runner key, `s2_latch_probe.py` helper, and `latch_hold_*.ps1` scripts. In the "Next free YAML slots" paragraph, change the both-off slot from run108 to **run128**.

- [ ] **Step 7: Commit everything and push**

```powershell
git status --short
git add -A -- . ":!.superpowers"
git status --short
```

The second `git status --short` must not show `.superpowers/` or `s2_canon_*.json`. It should show the guides, the plan files, the README, `AGENTS.md`, and the YAML as staged. If a file you did not expect is staged (for example a result folder from outside this series), stop and report it instead of committing.

```powershell
git commit -m "docs: S2 latch probe results runs 108-127"
git branch --show-current
git push origin HEAD
git status -sb
```

Expected: one commit; the push succeeds; `git status -sb` shows no ahead/behind count.

- [ ] **Step 8: Build the file list**

```powershell
$base = (Get-Content ".superpowers/latch/base_sha.txt").Trim()
git diff --name-status $base HEAD
```

This is every file added, modified, or deleted since the start of the series, including the earlier untracked guides committed in Step 7.

- [ ] **Step 9: Summary to the user**

The summary must contain:
- the list of files touched, taken from the Step 8 output, grouped as: code and scripts, configs, result folders (one line for `run108`–`run127`, naming any that failed the gate), guides and plans, `AGENTS.md` and `README`;
- the class per hold in one table (slot, treatment, sticky/released/other, blend);
- the verdict per lever (moved / no effect seen / mixed) and the four-control rate;
- whether the sojourn check separated the modes;
- the next free both-off slot (run128);
- that the VMs are terminated and the branch is pushed, with the commit SHA from `git rev-parse HEAD`.

---

## Self-review

**Spec coverage.**
- Two holds each of `pc120` (117, 125), `recs_users310` (114, 118), `ck_rep2` (112, 119), `ck_cpu1000` (113, 122), `recs_cpu1000` (110, 126), `ck_rep2_pc120` (115, 123), `spawn10` (109, 120): the order table and Tasks 6–25.
- My pick from the last answer: blocked order (two shuffled blocks of ten), four controls (111, 116, 121, 127), two restart holds (108, 124).
- End actions: Task 26 Steps 2 (terminate VMs, checked `TERMINATED`), 7 (commit everything, push), 8–9 (file list from the diff against the SHA saved in Task 1 Step 0, shown in the summary).
- Earlier items kept: run 89 base for every hold, the replays-differ guide's snapshots, retro-scoring, and interleaving.

**Placeholder scan.** No TBD. Every code step has code; each hold task spells out its own commands and treatment check.

**Type consistency.** Treatment keys (`control`, `spawn10`, `restart`, `recs_users310`, `recs_cpu1000`, `ck_cpu1000`, `ck_rep2`, `pc120`, `ck_rep2_pc120`) are identical in the `TREATMENTS` dict, the tests, the order table, the two scripts' arguments, and the hold tasks. Slot numbers in the tests (109 for spawn10, 114 for recs_users310, 117 for pc120, 110 for recs_cpu1000, 113 for ck_cpu1000, 112 and 115 for the replica holds, 108 for restart, 111 for control) match the order table.

**Known limits, stated up front.** Two holds per lever is a screen: two blends in a row still happens about 18% of the time by chance. The checkout-collector clock is not Locust's clock, so the 90–150 s window is approximate. Whether the runner tolerates a results folder created on master before launch was not checked, which is why snapshots are saved locally first. If the VMs have to stop between blocks, pod ages reset and the results guide must say so.
