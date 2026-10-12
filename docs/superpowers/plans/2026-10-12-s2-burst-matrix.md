# S2 burst matrix: normal mode, bar 1.5, and bar 2.0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These twelve holds share one cluster. Run the hold tasks in order in one session. Do not run two holds at once.

**Goal:** Run the locked Scenario 2 mix twelve times with RetryGuard on: normal mode, burst bar 1.5, and burst bar 2.0, each with TopFull off and TopFull on, twice.

**Architecture:** Twelve study YAMLs copied from the 2026-10-12 burst bar 1.5 TopFull-off file. Normal-mode files omit `burst_rpr`. Burst files set `burst_rpr` to 1.5 or 2.0 and keep the 5 s window and the volume floor of 20. The runner copies local `experiments/retryguard.py` onto master, so the holds launch from branch `retryguard-burst-mode`. Pin Paper-C1 once, run the twelve holds in the table order with a 120 s cool-off, pull and gate each folder, restore the unpinned shape, stop the three VMs, write one analysis guide, then commit and push.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, PowerShell, `ssh`, `gcloud`. No controller code changes.

## Global Constraints

- Stay on branch `retryguard-burst-mode`. Do not checkout or merge. Do not commit or push until Task 9.
- The message's "TG on" lines are RetryGuard on. All twelve holds set `retryguard.enabled: true`.
- The already-finished pair `study5_s2_burst15_rgtf0` and `study5_s2_burst15_rgtf1` is not one of these twelve. Do not overwrite those folders. Do not skip the new bar-1.5 holds because that pair exists.
- Locked S2 means the run-89 mix and the Paper-C1 pin. It does not mean `experiments/configs/scenario_2_retryguard.yaml`. That locked file is still slot **run30**. Do not edit it. Do not bump it. Do not change "Next free slots" in [STATUS.md](../../../STATUS.md).
- Mix: `getproduct=275, postcheckout=90, getcart=100, postcart=90, emptycart=5`, `spawn_rate` 50, duration 600 s.
- RetryGuard knobs, the same set as the bar-1.5 holds: `retry_metric=edge_rpr`, `rejection_threshold=0.20`, `sample_interval_seconds=1`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`.
- Normal mode omits `burst_rpr`, `burst_window_seconds`, and `burst_min_first_attempts`. Do not set `burst_rpr: 0`. The controller treats a missing `burst_rpr` as off, and `burst_rpr <= 0` makes `run_scenario.py` exit.
- Burst keys, written in the YAML: `burst_window_seconds: 5`, `burst_min_first_attempts: 20`, and `burst_rpr` of `1.5` or `2.0`. The effective bar at the current cap is `burst_rpr × attempts / 3`. A shed goes to 0 attempts and recovers on the existing path.
- `paper_cpu_reconcile: false`. `run_number: 1` on every study YAML. Omit `restart_before_hold`.
- SSH only via host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`); user `idozacharia`; project `project-76deda76-55f1-42d2-abb`; zone `us-central1-a`. Do not start the `networks-workshop` originals. Do not hardcode a public IP.
- Cool-off is **120 s**, starting when `run_scenario.py` exits. Pull and the gate happen during that wait. Checkout and recommendations stay up across the cool-off. The cool-off also applies between Task 3 and Task 4, and between Task 4 and Task 5.
- Paper-C1 pin for these holds: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `proxyCPU=90m`, `proxyCPULimit` unset. The cluster is currently unpinned (frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`). Pin once before hold 1. Restore that unpinned pair once after hold 12, before stopping the VMs.
- CPU quotas are the Paper-C1 table in the YAML `scale_constraints`: checkout 800 m, recommendations 1150 m, catalog 800 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, payment 155 m, email 120 m, redis-cart 540 m. Frontend app container stays 1150 m. The runner applies those constraints at the start of each hold.
- One hold at a time. A failed collector gate keeps its folder and is replayed once with a `_r2` suffix on the YAML and on `log_folder`. Do not overwrite the failed folder. Do not replay a second time.
- A complete hold with zero `ON→OFF` lines is still a pass. Toggle count is recorded and is not a gate. The both-on replay in [2026-10-12-s2-burst-replay.md](../../../Guides%20and%20Info/2026-10-12-s2-burst-replay.md) is a comparison for the burst both-on holds, not a gate.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`). Do not put the patch JSON in the `ssh` argument string.
- After the guide and the STATUS bullet are written, stop `topfull-master`, `topfull-worker-1`, and `topfull-load`. The STATUS bullet says the VMs were left **TERMINATED** only after `gcloud` lists all three as `TERMINATED`.
- Task 9 commits the configs, the result folders, the guide, the run log, this plan, `STATUS.md`, and `AGENTS.md`, then pushes `retryguard-burst-mode`. Do not force-push.
- Do not use `run_all_scenarios.py`.

## File Structure

- Create: twelve YAMLs in `experiments/configs/study_2026_10_12/`, numbered `03` through `14`.
- Create during the runs: `docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md` — one line per hold, including a failed hold and any single replay.
- Create after the pulls: `Guides and Info/2026-10-12-s2-burst-matrix-abc.md` — scorer write-up for the twelve folders.
- Modify after the VMs are `TERMINATED`: `STATUS.md` (one Done bullet; "Next free slots" unchanged) and `AGENTS.md` §4 (replace the three Latest lines; update the burst-bar Still open line).
- Read-only source: `experiments/configs/study_2026_10_12/01_s2_burst15_rgtf0.yaml`.
- Do not modify: `01_s2_burst15_rgtf0.yaml`, `02_s2_burst15_rgtf1.yaml`, or any `scenario_2_*.yaml`.

Results land in `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

| # | Mode | Bar | TopFull | File | `log_folder` |
| --- | --- | --- | --- | --- | --- |
| 1 | normal | omitted | off | `03_s2_normal_rgtf0_rep1.yaml` | `study6_s2_normal_rgtf0_rep1` |
| 2 | normal | omitted | off | `04_s2_normal_rgtf0_rep2.yaml` | `study6_s2_normal_rgtf0_rep2` |
| 3 | normal | omitted | on | `05_s2_normal_rgtf1_rep1.yaml` | `study6_s2_normal_rgtf1_rep1` |
| 4 | normal | omitted | on | `06_s2_normal_rgtf1_rep2.yaml` | `study6_s2_normal_rgtf1_rep2` |
| 5 | burst | 1.5 | off | `07_s2_burst15_rgtf0_rep1.yaml` | `study6_s2_burst15_rgtf0_rep1` |
| 6 | burst | 1.5 | off | `08_s2_burst15_rgtf0_rep2.yaml` | `study6_s2_burst15_rgtf0_rep2` |
| 7 | burst | 2.0 | off | `09_s2_burst20_rgtf0_rep1.yaml` | `study6_s2_burst20_rgtf0_rep1` |
| 8 | burst | 2.0 | off | `10_s2_burst20_rgtf0_rep2.yaml` | `study6_s2_burst20_rgtf0_rep2` |
| 9 | burst | 1.5 | on | `11_s2_burst15_rgtf1_rep1.yaml` | `study6_s2_burst15_rgtf1_rep1` |
| 10 | burst | 1.5 | on | `12_s2_burst15_rgtf1_rep2.yaml` | `study6_s2_burst15_rgtf1_rep2` |
| 11 | burst | 2.0 | on | `13_s2_burst20_rgtf1_rep1.yaml` | `study6_s2_burst20_rgtf1_rep1` |
| 12 | burst | 2.0 | on | `14_s2_burst20_rgtf1_rep2.yaml` | `study6_s2_burst20_rgtf1_rep2` |

Paths are under `experiments/configs/study_2026_10_12/`. `topfull_rl.enabled` is `false` for "off" and `true` for "on".

---

### Task 1: Confirm the branch and write the twelve YAMLs

**Files:**
- Create: the twelve paths in the table above
- Test: `experiments/test_retryguard.py` (`TestBurstMode`), `experiments/test_run_scenario.py` (`TestStartRetryGuardWiring`)

**Interfaces:**
- Consumes: local `experiments/retryguard.py` `burst_bar` and `experiments/run_scenario.py` `burst_params_from_cfg` on branch `retryguard-burst-mode`. A missing `burst_rpr` makes `burst_params_from_cfg` return `{}`.
- Produces: the twelve YAML paths. Later tasks launch those paths and do not edit them, except a single `_r2` copy after a failed gate.

- [ ] **Step 1: Confirm the branch and that burst mode is the code that will be copied**

Run from `c:\Users\sagi1\Projects\Workshop`:

```powershell
git branch --show-current
Select-String -Path experiments/retryguard.py -Pattern "def burst_bar"
Select-String -Path experiments/run_scenario.py -Pattern "def burst_params_from_cfg"
```

Expected: branch `retryguard-burst-mode`, one hit for `def burst_bar`, one hit for `def burst_params_from_cfg`. If the branch name is anything else, stop and ask. Do not checkout.

- [ ] **Step 2: Run the burst unit tests**

```powershell
python -m unittest experiments.test_retryguard.TestBurstMode experiments.test_run_scenario.TestStartRetryGuardWiring.test_burst_keys_forwarded_with_defaults experiments.test_run_scenario.TestStartRetryGuardWiring.test_burst_rpr_with_non_edge_metric_fails_loudly -v
```

Expected: `OK`. A failure here means do not start a hold.

- [ ] **Step 3: Confirm the twelve result names are free**

```powershell
$names = @(
  "study6_s2_normal_rgtf0_rep1","study6_s2_normal_rgtf0_rep2",
  "study6_s2_normal_rgtf1_rep1","study6_s2_normal_rgtf1_rep2",
  "study6_s2_burst15_rgtf0_rep1","study6_s2_burst15_rgtf0_rep2",
  "study6_s2_burst20_rgtf0_rep1","study6_s2_burst20_rgtf0_rep2",
  "study6_s2_burst15_rgtf1_rep1","study6_s2_burst15_rgtf1_rep2",
  "study6_s2_burst20_rgtf1_rep1","study6_s2_burst20_rgtf1_rep2"
)
foreach ($n in $names) {
  $p = "experiments/results/campaign_48/S2_sustained_overload/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `ABSENT` twelve times. An `EXISTS` line means stop and pick a new `log_folder` before writing that YAML.

- [ ] **Step 4: Write hold 1, the canonical normal-mode file**

Create `experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml` with this exact content. It is the bar-1.5 TopFull-off YAML with the three burst keys removed and the description and `log_folder` changed.

```yaml
# Plan: docs/superpowers/plans/2026-10-12-s2-burst-matrix.md
scenario_id: 2
scenario_name: sustained_overload
condition: retryguard
run_number: 1
description: 'Study 2026-10-12 study6_s2_normal_rgtf0_rep1 (275/90/100/90/5): locked S2,
  normal mode, RetryGuard on, TopFull off.'
duration_seconds: 600
locust:
  user_counts:
    getproduct: 275
    postcheckout: 90
    getcart: 100
    postcart: 90
    emptycart: 5
  spawn_rate: 50
  scripts:
  - online_boutique_create_v2.sh
paper_cpu_reconcile: false
scale_constraints:
- deployment: checkoutservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 800
- deployment: recommendationservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 1150
- deployment: productcatalogservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 800
- deployment: cartservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 800
- deployment: currencyservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 770
- deployment: shippingservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 770
- deployment: adservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 1150
- deployment: paymentservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 155
- deployment: emailservice
  namespace: default
  container: server
  method: cpu_limit
  cpu_limit_millicores: 120
- deployment: redis-cart
  namespace: default
  container: redis
  method: cpu_limit
  cpu_limit_millicores: 540
retries:
  attempts_on: 3
  attempts_off: 0
  per_try_timeout_ms: 500
topfull_rl:
  enabled: false
retryguard:
  enabled: true
  rejection_threshold: 0.2
  sample_interval_seconds: 1
  interval_samples: 20
  retry_metric: edge_rpr
  retries_threshold: 0.4
  climb_rpr_1_to_2: 0.16
  climb_rpr_2_to_3: 0.32
  climb_interval_seconds: 10
  reenable_rejection: 0.25
envoy_retry_collector:
  enabled: true
  poll_interval_seconds: 1
  transport: network_prometheus
  max_workers: 4
resource_usage_collector:
  enabled: true
  poll_interval_seconds: 5
topfull_throttle_collector:
  enabled: true
  poll_interval_seconds: 1
log_folder: study6_s2_normal_rgtf0_rep1
infra:
  master_ssh_host: topfull-master
  loadgen_ssh_host: topfull-load
  topfull_src_path: /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src
  topfull_loadgen_path: /home/idozacharia/TopFull/TopFull_loadgen
  venv_activate: /home/idozacharia/TopFull/venv/bin/activate
  results_base_path: /home/idozacharia/experiments/results
  retryguard_script: /home/idozacharia/experiments/retryguard.py
  envoy_retry_collector_script: /home/idozacharia/experiments/envoy_retry_collector.py
  resource_usage_collector_script: /home/idozacharia/experiments/resource_usage_collector.py
  topfull_throttle_collector_script: /home/idozacharia/experiments/topfull_throttle_collector.py
```

- [ ] **Step 5: Write holds 2–12 from that file**

Copy `03_s2_normal_rgtf0_rep1.yaml` to each remaining path. Change only `description`, `topfull_rl.enabled`, `log_folder`, and, on burst files, the three burst keys inserted immediately after `reenable_rejection: 0.25`.

Description text, one line wrapped the same way as hold 1 (`Study 2026-10-12 <log_folder> (275/90/100/90/5): ...`):

| File | `topfull_rl.enabled` | Burst keys after `reenable_rejection` | Description tail |
| --- | --- | --- | --- |
| `04_s2_normal_rgtf0_rep2.yaml` | `false` | omit | `normal mode, RetryGuard on, TopFull off.` |
| `05_s2_normal_rgtf1_rep1.yaml` | `true` | omit | `normal mode, RetryGuard on, TopFull on.` |
| `06_s2_normal_rgtf1_rep2.yaml` | `true` | omit | `normal mode, RetryGuard on, TopFull on.` |
| `07_s2_burst15_rgtf0_rep1.yaml` | `false` | `burst_rpr: 1.5` / window 5 / floor 20 | `burst_rpr 1.5, RetryGuard on, TopFull off.` |
| `08_s2_burst15_rgtf0_rep2.yaml` | `false` | `burst_rpr: 1.5` / window 5 / floor 20 | `burst_rpr 1.5, RetryGuard on, TopFull off.` |
| `09_s2_burst20_rgtf0_rep1.yaml` | `false` | `burst_rpr: 2.0` / window 5 / floor 20 | `burst_rpr 2.0, RetryGuard on, TopFull off.` |
| `10_s2_burst20_rgtf0_rep2.yaml` | `false` | `burst_rpr: 2.0` / window 5 / floor 20 | `burst_rpr 2.0, RetryGuard on, TopFull off.` |
| `11_s2_burst15_rgtf1_rep1.yaml` | `true` | `burst_rpr: 1.5` / window 5 / floor 20 | `burst_rpr 1.5, RetryGuard on, TopFull on.` |
| `12_s2_burst15_rgtf1_rep2.yaml` | `true` | `burst_rpr: 1.5` / window 5 / floor 20 | `burst_rpr 1.5, RetryGuard on, TopFull on.` |
| `13_s2_burst20_rgtf1_rep1.yaml` | `true` | `burst_rpr: 2.0` / window 5 / floor 20 | `burst_rpr 2.0, RetryGuard on, TopFull on.` |
| `14_s2_burst20_rgtf1_rep2.yaml` | `true` | `burst_rpr: 2.0` / window 5 / floor 20 | `burst_rpr 2.0, RetryGuard on, TopFull on.` |

The three burst lines, when the table says to insert them, are exactly:

```yaml
  burst_rpr: 1.5
  burst_window_seconds: 5
  burst_min_first_attempts: 20
```

or, for bar 2.0:

```yaml
  burst_rpr: 2.0
  burst_window_seconds: 5
  burst_min_first_attempts: 20
```

`log_folder` on each file is the name in the hold table. The description's folder token is that same name.

- [ ] **Step 6: Check the twelve files**

```powershell
python -c @'
import yaml
from pathlib import Path
root = Path("experiments/configs/study_2026_10_12")
rows = [
    ("03_s2_normal_rgtf0_rep1.yaml", "study6_s2_normal_rgtf0_rep1", False, None),
    ("04_s2_normal_rgtf0_rep2.yaml", "study6_s2_normal_rgtf0_rep2", False, None),
    ("05_s2_normal_rgtf1_rep1.yaml", "study6_s2_normal_rgtf1_rep1", True, None),
    ("06_s2_normal_rgtf1_rep2.yaml", "study6_s2_normal_rgtf1_rep2", True, None),
    ("07_s2_burst15_rgtf0_rep1.yaml", "study6_s2_burst15_rgtf0_rep1", False, 1.5),
    ("08_s2_burst15_rgtf0_rep2.yaml", "study6_s2_burst15_rgtf0_rep2", False, 1.5),
    ("09_s2_burst20_rgtf0_rep1.yaml", "study6_s2_burst20_rgtf0_rep1", False, 2.0),
    ("10_s2_burst20_rgtf0_rep2.yaml", "study6_s2_burst20_rgtf0_rep2", False, 2.0),
    ("11_s2_burst15_rgtf1_rep1.yaml", "study6_s2_burst15_rgtf1_rep1", True, 1.5),
    ("12_s2_burst15_rgtf1_rep2.yaml", "study6_s2_burst15_rgtf1_rep2", True, 1.5),
    ("13_s2_burst20_rgtf1_rep1.yaml", "study6_s2_burst20_rgtf1_rep1", True, 2.0),
    ("14_s2_burst20_rgtf1_rep2.yaml", "study6_s2_burst20_rgtf1_rep2", True, 2.0),
]
base = yaml.safe_load((root / "03_s2_normal_rgtf0_rep1.yaml").read_text(encoding="utf-8"))
assert base["locust"]["user_counts"] == {"getproduct": 275, "postcheckout": 90, "getcart": 100, "postcart": 90, "emptycart": 5}
assert base["locust"]["spawn_rate"] == 50
assert base["duration_seconds"] == 600
assert base["paper_cpu_reconcile"] is False
assert "restart_before_hold" not in base
rg0 = base["retryguard"]
assert rg0["retry_metric"] == "edge_rpr"
assert rg0["interval_samples"] == 20
assert rg0["retries_threshold"] == 0.4
assert rg0["climb_rpr_1_to_2"] == 0.16
assert rg0["climb_rpr_2_to_3"] == 0.32
assert rg0["climb_interval_seconds"] == 10
assert rg0["reenable_rejection"] == 0.25
assert "burst_rpr" not in rg0
for name, folder, tf, bar in rows:
    cfg = yaml.safe_load((root / name).read_text(encoding="utf-8"))
    assert cfg["log_folder"] == folder, name
    assert cfg["topfull_rl"]["enabled"] is tf, name
    assert cfg["retryguard"]["enabled"] is True, name
    assert folder in cfg["description"], name
    got = cfg["retryguard"].get("burst_rpr")
    assert got == bar, (name, got, bar)
    if bar is None:
        assert "burst_window_seconds" not in cfg["retryguard"], name
        assert "burst_min_first_attempts" not in cfg["retryguard"], name
    else:
        assert cfg["retryguard"]["burst_window_seconds"] == 5, name
        assert cfg["retryguard"]["burst_min_first_attempts"] == 20, name
    rest = dict(cfg)
    rest.pop("description"); rest.pop("log_folder"); rest.pop("topfull_rl"); rest.pop("retryguard")
    base_rest = dict(base)
    base_rest.pop("description"); base_rest.pop("log_folder"); base_rest.pop("topfull_rl"); base_rest.pop("retryguard")
    assert rest == base_rest, name
print("yaml-ok", len(rows))
'@
```

Expected: `yaml-ok 12`. Any assertion failure means fix that file before Task 2.

```powershell
git diff -- experiments/configs/study_2026_10_12/01_s2_burst15_rgtf0.yaml experiments/configs/study_2026_10_12/02_s2_burst15_rgtf1.yaml
```

Expected: no diff.

---

### Task 2: Preflight — cluster healthy and pinned

**Files:** none.

**Interfaces:**
- Consumes: the twelve YAML paths from Task 1. Does not edit them.
- Produces: a Paper-C1 pin (frontend HPA 4/4, catalog HPA 1/1, sidecar `90m`) and an empty live log directory, ready for hold 1.

- [ ] **Step 1: Confirm the three VMs, then SSH**

Last status left them `RUNNING`. List first. Start only a VM whose status is `TERMINATED`.

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

If any of the three is `TERMINATED`:

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Then list again and update `HostName` in `~/.ssh/config` from the new public IPs. Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md). Do not start the `networks-workshop` originals.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
```

Expected user: `idozacharia`. If SSH fails on a stale IP, refresh `HostName` and retry.

- [ ] **Step 2: Confirm the master result folders are absent**

```powershell
ssh topfull-master "for d in study6_s2_normal_rgtf0_rep1 study6_s2_normal_rgtf0_rep2 study6_s2_normal_rgtf1_rep1 study6_s2_normal_rgtf1_rep2 study6_s2_burst15_rgtf0_rep1 study6_s2_burst15_rgtf0_rep2 study6_s2_burst20_rgtf0_rep1 study6_s2_burst20_rgtf0_rep2 study6_s2_burst15_rgtf1_rep1 study6_s2_burst15_rgtf1_rep2 study6_s2_burst20_rgtf1_rep1 study6_s2_burst20_rgtf1_rep2; do if test -d /home/idozacharia/experiments/results/`$d; then echo EXISTS `$d; else echo ABSENT `$d; fi; done"
```

Expected: `ABSENT` twelve times. An `EXISTS` line means stop and pick a new `log_folder`. The runner writes that directory on master and a second launch with the same name overwrites it.

- [ ] **Step 3: Cluster health**

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

All nodes `Ready`. Boutique pods `2/2`. VirtualServices present. If `kubectl` says `connection to localhost:8080 refused`, the SSH user is missing `~/.kube/config` — copy `idozacharia`'s kubeconfig as in [AGENTS.md](../../../AGENTS.md) §7, then retry. Do not start the hold until pods are `2/2`.

- [ ] **Step 4: Paper-C1 pin**

Pipe the script. Do not inline the JSON in the `ssh` argument.

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":4,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"90m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
kubectl rollout status deployment/frontend -n default --timeout=180s
'@ | ssh topfull-master "bash -s"
```

Confirm:

```powershell
@'
kubectl get hpa frontend-hpa productcatalogservice-hpa -n default
kubectl get deployment frontend -n default -o jsonpath="{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}{\"\n\"}{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}{\"\n\"}"
kubectl get pods -n default -l app=frontend --no-headers
'@ | ssh topfull-master "bash -s"
```

Expected: frontend HPA `4/4`, catalog HPA `1/1`, annotation `90m`, `proxyCPULimit` empty, four frontend pods `2/2`.

- [ ] **Step 5: Stop leftover writers once**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

Hold 1 starts at Task 3. If some other `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder only.

---

### Task 3: Run the four normal-mode holds

**Files:**
- Create: `docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md`
- Read: `03` through `06` under `experiments/configs/study_2026_10_12/`

**Interfaces:**
- Consumes: the pinned cluster from Task 2 and holds 1–4.
- Produces: four pulled folders (`study6_s2_normal_rgtf0_rep1`, `study6_s2_normal_rgtf0_rep2`, `study6_s2_normal_rgtf1_rep1`, `study6_s2_normal_rgtf1_rep2`) and four run-log lines. Task 8 scores those folders.

Repeat Steps 1–8 for these YAMLs, in this order:

1. `experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml` — kind `normal`, TopFull `off`
2. `experiments/configs/study_2026_10_12/04_s2_normal_rgtf0_rep2.yaml` — kind `normal`, TopFull `off`
3. `experiments/configs/study_2026_10_12/05_s2_normal_rgtf1_rep1.yaml` — kind `normal`, TopFull `on`
4. `experiments/configs/study_2026_10_12/06_s2_normal_rgtf1_rep2.yaml` — kind `normal`, TopFull `on`

`run_scenario.py` kills leftover master processes and exits before Locust if a required process is missing (`Master processes not running`). That does not replace Steps 1–3. Locust is on the load VM. A collector that is still writing recreates files in `src/logs` after `clear_logs`.

- [ ] **Step 1: Stop leftover writers**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear.** Anything other than the two `-clear` lines means stop and repeat Step 1.

```powershell
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` must print nothing. If a file reappears, a writer is still alive. Repeat Step 1. Do not start the hold.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml
```

Then, after that hold's cool-off and a fresh Steps 1–3, the same command with `04_s2_normal_rgtf0_rep2.yaml`, then `05_s2_normal_rgtf1_rep1.yaml`, then `06_s2_normal_rgtf1_rep2.yaml`.

One process only. A 600 s hold plus startup is about 12 minutes. Do not start the next hold until this process exits. The 120 s cool-off clock starts at that exit. Steps 5 and 6 happen during the wait.

- [ ] **Step 5: Pull**

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml
```

Use the YAML that just finished. The folder is `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

- [ ] **Step 6: Gates.** Keep the folder either way.

Write this checker once, then run it with the folder, the kind, and `off` or `on`:

```powershell
@'
import csv, sys
from pathlib import Path
folder, kind, tf = sys.argv[1:]
root = Path(folder)
total = list(csv.DictReader(root.joinpath("total.csv").open(newline="", encoding="utf-8")))
print(f"locust_rows={len(total)}")
log = root.joinpath("retryguard.log").read_text(encoding="utf-8", errors="replace")
start = next(line for line in log.splitlines() if " START " in line)
print(start)
need = [
    "metric=edge_rpr",
    "interval_samples=20s",
    "rpr_threshold=0.40",
    "climb_rpr_1_to_2=0.16",
    "climb_rpr_2_to_3=0.32",
    "climb_interval_seconds=10s",
    "reenable_rejection=0.25",
]
if kind == "burst15":
    need += ["burst_rpr=1.50", "burst_window_seconds=5", "burst_min_first_attempts=20"]
elif kind == "burst20":
    need += ["burst_rpr=2.00", "burst_window_seconds=5", "burst_min_first_attempts=20"]
missing = [s for s in need if s not in start]
if kind == "normal" and "burst_rpr=" in start:
    missing.append("burst keys present on a normal hold")
print("start_missing=" + (",".join(missing) if missing else "none"))
if kind.startswith("burst"):
    print("burst_observe=" + ("yes" if "burst_rpr5=" in log else "no"))
else:
    print("burst_observe=n/a")
print("patch_fail=" + ("yes" if "PATCH_FAIL" in log or "Traceback" in log else "no"))
ru = list(csv.DictReader(root.joinpath("resource_usage.csv").open(newline="", encoding="utf-8")))
fe = [r for r in ru if r["service"] == "frontend"]
cat = [r for r in ru if r["service"] == "productcatalogservice"]
print(f"frontend_4={sum(r['replica_count']=='4' for r in fe)}/{len(fe)}")
print(f"catalog_1={sum(r['replica_count']=='1' for r in cat)}/{len(cat)}")
th = list(csv.DictReader(root.joinpath("topfull_throttle.csv").open(newline="", encoding="utf-8")))
live = [r for r in th if r["threshold_fresh"] == "1"]
def num(r):
    return float(r["threshold"])
n10000 = sum(num(r) == 10000 for r in live)
nzero = sum(num(r) == 0 for r in live)
ncaps = sum(0 < num(r) < 10000 for r in live)
print(f"live5s_10000={n10000} live5s_caps={ncaps} live5s_zero={nzero} other={len(live) - n10000 - nzero - ncaps}")
'@ | Set-Content -Encoding ascii "$env:TEMP\s2_gate_check.py"
python "$env:TEMP\s2_gate_check.py" experiments/results/campaign_48/S2_sustained_overload/study6_s2_normal_rgtf0_rep1 normal off
```

Pass, all four normal holds:

- `locust_rows` is about 540–580.
- `start_missing=none`. The START line has no `burst_rpr=`.
- `patch_fail=no`.
- `frontend_4` equals its denominator. `catalog_1` equals its denominator. A catalog sample that is missing is allowed; a catalog sample whose `replica_count` is not 1 is a fail.
- TopFull `off` (holds 1 and 2): `live5s_caps=0` and `other=0`. A live 0 is an empty read and does not count as a cap.
- TopFull `on` (holds 3 and 4): `live5s_caps` is at least 1.

Also confirm VirtualServices are back at 3 attempts:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh topfull-master "bash -s"
```

Expected: every printed attempts value is `3`. No route `timeout` was added by the hold; if a VirtualService shows a timeout, that hold fails the gate.

A collector-gate failure is logged, the folder is kept, and the hold is replayed **once**. Copy the YAML to a sibling with `_r2` before `.yaml`, set `log_folder` to the same name plus `_r2`, and set the description's folder token to that new name. Launch that file through Steps 1–6. Do not overwrite the failed folder. Do not replay a second time.

- [ ] **Step 7: Finish the 120 s cool-off** after holds 1, 2, and 3, then Steps 1–3 again, before the next hold. After hold 4, leave the remainder of the 120 s for Task 4. If Steps 5–6 already used the whole 120 s, go straight to Steps 1–3. Otherwise `Start-Sleep -Seconds` for the remainder, measured from the `run_scenario.py` exit.

- [ ] **Step 8: Append one line per hold** to `docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md`. Create the file on hold 1 with this header:

```markdown
# S2 burst matrix — run log

One line per hold, including a failed hold and any single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; normal; TopFull off or on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. On these four holds `burst` is 0 when the gate passed.

---

### Task 4: Run the four TopFull-off burst holds

**Files:**
- Modify: `docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md` (append; do not rewrite the header)
- Read: `07` through `10` under `experiments/configs/study_2026_10_12/`

**Interfaces:**
- Consumes: the cluster still pinned from Task 2, and a finished Task 3 whose last `run_scenario.py` has had its 120 s cool-off.
- Produces: four pulled folders (`study6_s2_burst15_rgtf0_rep1`, `study6_s2_burst15_rgtf0_rep2`, `study6_s2_burst20_rgtf0_rep1`, `study6_s2_burst20_rgtf0_rep2`) and four run-log lines.

Run these four YAMLs, in this order. Write the gate checker in Step 6 before the first gate.

1. `experiments/configs/study_2026_10_12/07_s2_burst15_rgtf0_rep1.yaml` — kind `burst15`, TopFull `off`
2. `experiments/configs/study_2026_10_12/08_s2_burst15_rgtf0_rep2.yaml` — kind `burst15`, TopFull `off`
3. `experiments/configs/study_2026_10_12/09_s2_burst20_rgtf0_rep1.yaml` — kind `burst20`, TopFull `off`
4. `experiments/configs/study_2026_10_12/10_s2_burst20_rgtf0_rep2.yaml` — kind `burst20`, TopFull `off`

- [ ] **Step 1: Cool-off from hold 4, then stop leftover writers**

If hold 4's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear.** Anything other than the two `-clear` lines means stop and repeat Step 1.

```powershell
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` must print nothing. If a file reappears, a writer is still alive. Repeat Step 1. Do not start the hold.

- [ ] **Step 4: Run, one YAML at a time**

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/07_s2_burst15_rgtf0_rep1.yaml
```

After the cool-off and a fresh Steps 1–3: `08_s2_burst15_rgtf0_rep2.yaml`, then `09_s2_burst20_rgtf0_rep1.yaml`, then `10_s2_burst20_rgtf0_rep2.yaml`.

- [ ] **Step 5: Pull the YAML that just finished**

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/07_s2_burst15_rgtf0_rep1.yaml
```

- [ ] **Step 6: Gates**

Write the checker, then run it. Use `burst15` or `burst20`, and the folder that was just pulled.

```powershell
@'
import csv, sys
from pathlib import Path
folder, kind, tf = sys.argv[1:]
root = Path(folder)
total = list(csv.DictReader(root.joinpath("total.csv").open(newline="", encoding="utf-8")))
print(f"locust_rows={len(total)}")
log = root.joinpath("retryguard.log").read_text(encoding="utf-8", errors="replace")
start = next(line for line in log.splitlines() if " START " in line)
print(start)
need = [
    "metric=edge_rpr",
    "interval_samples=20s",
    "rpr_threshold=0.40",
    "climb_rpr_1_to_2=0.16",
    "climb_rpr_2_to_3=0.32",
    "climb_interval_seconds=10s",
    "reenable_rejection=0.25",
]
if kind == "burst15":
    need += ["burst_rpr=1.50", "burst_window_seconds=5", "burst_min_first_attempts=20"]
elif kind == "burst20":
    need += ["burst_rpr=2.00", "burst_window_seconds=5", "burst_min_first_attempts=20"]
missing = [s for s in need if s not in start]
if kind == "normal" and "burst_rpr=" in start:
    missing.append("burst keys present on a normal hold")
print("start_missing=" + (",".join(missing) if missing else "none"))
if kind.startswith("burst"):
    print("burst_observe=" + ("yes" if "burst_rpr5=" in log else "no"))
else:
    print("burst_observe=n/a")
print("patch_fail=" + ("yes" if "PATCH_FAIL" in log or "Traceback" in log else "no"))
ru = list(csv.DictReader(root.joinpath("resource_usage.csv").open(newline="", encoding="utf-8")))
fe = [r for r in ru if r["service"] == "frontend"]
cat = [r for r in ru if r["service"] == "productcatalogservice"]
print(f"frontend_4={sum(r['replica_count']=='4' for r in fe)}/{len(fe)}")
print(f"catalog_1={sum(r['replica_count']=='1' for r in cat)}/{len(cat)}")
th = list(csv.DictReader(root.joinpath("topfull_throttle.csv").open(newline="", encoding="utf-8")))
live = [r for r in th if r["threshold_fresh"] == "1"]
def num(r):
    return float(r["threshold"])
n10000 = sum(num(r) == 10000 for r in live)
nzero = sum(num(r) == 0 for r in live)
ncaps = sum(0 < num(r) < 10000 for r in live)
print(f"live5s_10000={n10000} live5s_caps={ncaps} live5s_zero={nzero} other={len(live) - n10000 - nzero - ncaps}")
'@ | Set-Content -Encoding ascii "$env:TEMP\s2_gate_check.py"
python "$env:TEMP\s2_gate_check.py" experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf0_rep1 burst15 off
```

Use `burst15` or `burst20` to match the hold. Pass, all four:

- `locust_rows` is about 540–580.
- `start_missing=none`. START contains `burst_rpr=1.50` for kind `burst15` and `burst_rpr=2.00` for kind `burst20`, plus `burst_window_seconds=5` and `burst_min_first_attempts=20`.
- `burst_observe=yes`.
- `patch_fail=no`.
- `frontend_4` equals its denominator. `catalog_1` equals its denominator. A missing catalog sample is allowed; a catalog sample whose `replica_count` is not 1 is a fail.
- `live5s_caps=0` and `other=0`. A live 0 is an empty read and does not count as a cap.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh topfull-master "bash -s"
```

Expected: every printed attempts value is `3`. A replay of a failed gate copies the YAML to a sibling with `_r2` before `.yaml`, sets `log_folder` and the description's folder token to that name plus `_r2`, and runs Steps 1–6 once. Do not overwrite the failed folder. Do not replay a second time.

- [ ] **Step 7: 120 s cool-off** between these four holds. After hold 8, leave any remainder for Task 5.

- [ ] **Step 8: Append four lines** to the run log. Create nothing if the file already has the header from Task 3. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; burst_rpr 1.5 or 2.0; TopFull off; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`.

---

### Task 5: Run the four TopFull-on burst holds

**Files:**
- Modify: `docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md` (append)
- Read: `11` through `14` under `experiments/configs/study_2026_10_12/`

**Interfaces:**
- Consumes: the cluster still pinned, and a finished Task 4 whose last exit has had its 120 s cool-off.
- Produces: four pulled folders (`study6_s2_burst15_rgtf1_rep1`, `study6_s2_burst15_rgtf1_rep2`, `study6_s2_burst20_rgtf1_rep1`, `study6_s2_burst20_rgtf1_rep2`) and four run-log lines. These four are the holds compared with the 104–113 s replay window.

Run these four YAMLs, in this order:

1. `experiments/configs/study_2026_10_12/11_s2_burst15_rgtf1_rep1.yaml` — kind `burst15`, TopFull `on`
2. `experiments/configs/study_2026_10_12/12_s2_burst15_rgtf1_rep2.yaml` — kind `burst15`, TopFull `on`
3. `experiments/configs/study_2026_10_12/13_s2_burst20_rgtf1_rep1.yaml` — kind `burst20`, TopFull `on`
4. `experiments/configs/study_2026_10_12/14_s2_burst20_rgtf1_rep2.yaml` — kind `burst20`, TopFull `on`

- [ ] **Step 1: Cool-off from hold 8, then stop leftover writers**

If hold 8's `run_scenario.py` exited less than 120 s ago, `Start-Sleep` for the remainder. Then:

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

- [ ] **Step 2: Confirm clear.** Anything other than the two `-clear` lines means stop and repeat Step 1.

```powershell
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

- [ ] **Step 3: Clear live logs and confirm they stay empty**

```powershell
ssh topfull-master "rm -f /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.csv /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs/*.log; sleep 2; ls /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src/logs"
```

The `ls` must print nothing. If a file reappears, a writer is still alive. Repeat Step 1. Do not start the hold.

- [ ] **Step 4: Run**

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/11_s2_burst15_rgtf1_rep1.yaml
```

Then `12_s2_burst15_rgtf1_rep2.yaml`, `13_s2_burst20_rgtf1_rep1.yaml`, and `14_s2_burst20_rgtf1_rep2.yaml`, each after a 120 s cool-off and a fresh Steps 1–3.

- [ ] **Step 5: Pull**

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/11_s2_burst15_rgtf1_rep1.yaml
```

- [ ] **Step 6: Gates**

Write the checker, then run it. Use `burst15` or `burst20`, and the folder that was just pulled.

```powershell
@'
import csv, sys
from pathlib import Path
folder, kind, tf = sys.argv[1:]
root = Path(folder)
total = list(csv.DictReader(root.joinpath("total.csv").open(newline="", encoding="utf-8")))
print(f"locust_rows={len(total)}")
log = root.joinpath("retryguard.log").read_text(encoding="utf-8", errors="replace")
start = next(line for line in log.splitlines() if " START " in line)
print(start)
need = [
    "metric=edge_rpr",
    "interval_samples=20s",
    "rpr_threshold=0.40",
    "climb_rpr_1_to_2=0.16",
    "climb_rpr_2_to_3=0.32",
    "climb_interval_seconds=10s",
    "reenable_rejection=0.25",
]
if kind == "burst15":
    need += ["burst_rpr=1.50", "burst_window_seconds=5", "burst_min_first_attempts=20"]
elif kind == "burst20":
    need += ["burst_rpr=2.00", "burst_window_seconds=5", "burst_min_first_attempts=20"]
missing = [s for s in need if s not in start]
if kind == "normal" and "burst_rpr=" in start:
    missing.append("burst keys present on a normal hold")
print("start_missing=" + (",".join(missing) if missing else "none"))
if kind.startswith("burst"):
    print("burst_observe=" + ("yes" if "burst_rpr5=" in log else "no"))
else:
    print("burst_observe=n/a")
print("patch_fail=" + ("yes" if "PATCH_FAIL" in log or "Traceback" in log else "no"))
ru = list(csv.DictReader(root.joinpath("resource_usage.csv").open(newline="", encoding="utf-8")))
fe = [r for r in ru if r["service"] == "frontend"]
cat = [r for r in ru if r["service"] == "productcatalogservice"]
print(f"frontend_4={sum(r['replica_count']=='4' for r in fe)}/{len(fe)}")
print(f"catalog_1={sum(r['replica_count']=='1' for r in cat)}/{len(cat)}")
th = list(csv.DictReader(root.joinpath("topfull_throttle.csv").open(newline="", encoding="utf-8")))
live = [r for r in th if r["threshold_fresh"] == "1"]
def num(r):
    return float(r["threshold"])
n10000 = sum(num(r) == 10000 for r in live)
nzero = sum(num(r) == 0 for r in live)
ncaps = sum(0 < num(r) < 10000 for r in live)
print(f"live5s_10000={n10000} live5s_caps={ncaps} live5s_zero={nzero} other={len(live) - n10000 - nzero - ncaps}")
'@ | Set-Content -Encoding ascii "$env:TEMP\s2_gate_check.py"
python "$env:TEMP\s2_gate_check.py" experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf1_rep1 burst15 on
```

Pass, all four:

- `locust_rows` is about 540–580.
- `start_missing=none`. START contains `burst_rpr=1.50` for kind `burst15` and `burst_rpr=2.00` for kind `burst20`, plus `burst_window_seconds=5` and `burst_min_first_attempts=20`.
- `burst_observe=yes`.
- `patch_fail=no`.
- `frontend_4` equals its denominator. `catalog_1` equals its denominator.
- `live5s_caps` is at least 1.

VirtualServices:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh topfull-master "bash -s"
```

Expected: every printed attempts value is `3`. A replay of a failed gate copies the YAML to a sibling with `_r2` before `.yaml`, sets `log_folder` and the description's folder token to that name plus `_r2`, and runs Steps 1–6 once. Do not overwrite the failed folder. Do not replay a second time.

The replay's first-fire window (104–113 s at bars 1.5 and 2.0) is not a gate. Record the first `metric=rpr_burst` time in the run-log note when one exists.

- [ ] **Step 7: No cool-off after hold 12.** Go to Task 6.

- [ ] **Step 8: Append four lines** to the run log. Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; burst_rpr 1.5 or 2.0; TopFull on; toggles N (off N, up N, burst N); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. When a `metric=rpr_burst` line exists, add the seconds from the first `OBSERVE` line to that first burst shed.

---

### Task 6: Restore the unpinned pair

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 2.
- Produces: frontend HPA min 1 / max 4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m. The VMs are still `RUNNING` until Task 7.

- [ ] **Step 1: Final cleanup**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
ssh topfull-load "pgrep -af '[l]ocust' || echo locust-clear"
ssh topfull-master "pgrep -af '[m]etric_collector.py|[d]eploy_rl.py|[p]roxy_online_boutique|[r]etryguard.py|[e]nvoy_retry_collector.py|[r]esource_usage_collector.py|[t]opfull_throttle_collector.py' || echo master-clear"
```

Expected: `locust-clear` and `master-clear`.

- [ ] **Step 2: Restore the unpinned pair**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":4}}'
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p '{"spec":{"minReplicas":1,"maxReplicas":2}}'
kubectl patch deployment frontend -n default --type merge -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/proxyCPU":"100m"}}}}}'
kubectl annotate deployment frontend -n default sidecar.istio.io/proxyCPULimit-
'@ | ssh topfull-master "bash -s"
```

Confirm:

```powershell
@'
kubectl get hpa frontend-hpa productcatalogservice-hpa -n default
kubectl get deployment frontend -n default -o jsonpath="{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPU}{\"\n\"}{.spec.template.metadata.annotations.sidecar\.istio\.io/proxyCPULimit}{\"\n\"}"
kubectl get deployment frontend checkoutservice productcatalogservice emailservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.template.spec.containers[0].resources.limits.cpu}{\"\n\"}{end}"
'@ | ssh topfull-master "bash -s"
```

Expected: frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar annotation `100m` with `proxyCPULimit` absent, app CPU limits frontend `1150m`, checkout `800m`, catalog `800m`, email `120m`. If a limit is still off Paper-C1, patch that deployment's server container requests and limits to the Paper-C1 value and wait for its rollout.

---

### Task 7: Stop the three VMs

**Files:** none.

**Interfaces:**
- Consumes: the unpinned cluster from Task 6, with every hold already pulled. Do not stop the VMs before a failed hold's single replay has been pulled.
- Produces: `topfull-master`, `topfull-worker-1`, and `topfull-load` in status `TERMINATED`.

- [ ] **Step 1: Stop**

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Pass `--project` so a leftover `networks-workshop` gcloud config does not stop the originals.

- [ ] **Step 2: Confirm**

```powershell
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: all three `TERMINATED`. If a row is still `STOPPING`, wait and list again. Do not write the STATUS bullet until this list shows `TERMINATED` three times.

---

### Task 8: Score and write the guide

Do this after all twelve folders are pulled. Numbers come from the scorer. Do not invent a cell. The VMs are already `TERMINATED`; scoring is local.

**Files:**
- Create: `Guides and Info/2026-10-12-s2-burst-matrix-abc.md`
- Modify: `STATUS.md`, `AGENTS.md`
- Read: [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), [2026-10-12-s2-burst-replay.md](../../../Guides%20and%20Info/2026-10-12-s2-burst-replay.md), [2026-10-12-s2-burst15-abc.md](../../../Guides%20and%20Info/2026-10-12-s2-burst15-abc.md)

**Interfaces:**
- Consumes: the twelve pulled folders. If a `_r2` replay exists, score that folder in place of the failed one and name the failed folder in the Gate section.
- Produces: the guide, one STATUS Done bullet, three replacement Latest lines, and one updated Still open line.

- [ ] **Step 1: Score the twelve holds**

Column order is the hold table: normal off ×2, normal on ×2, burst 1.5 off ×2, burst 2.0 off ×2, burst 1.5 on ×2, burst 2.0 on ×2. `--sep 2` draws a bar after each replicate pair.

```powershell
python experiments/analysis_score.py --sep 2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_normal_rgtf0_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_normal_rgtf0_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_normal_rgtf1_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_normal_rgtf1_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf0_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf0_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst20_rgtf0_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst20_rgtf0_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf1_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst15_rgtf1_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst20_rgtf1_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study6_s2_burst20_rgtf1_rep2
```

The scorer labels a folder with its name when the name does not end in `run<N>`. Use those labels as the index columns.

- [ ] **Step 2: Write the guide**

Follow [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md) section order.

Setup states: twelve 600 s holds, mix 275 / 90 / 100 / 90 / 5, `spawn_rate` 50, Paper-C1 pin, RetryGuard on for every hold, 120 s cool-off, tuned knobs from Global Constraints. Normal-mode holds omit `burst_rpr`. Burst holds use window 5 s and volume floor 20. Climb steps are 10 s (`climb_interval_seconds: 10`). The effective burst bar at 3 / 2 / 1 attempts is 1.5 / 1.0 / 0.5 for bar 1.5, and 2.0 / 1.333 / 0.667 for bar 2.0. The scorer's `Burst bars` line is the source for those products; paste it.

Index columns follow the scorer order above, with a bold bar after every pair.

Edge-mode bars: copy the scorer's first line. Normal-mode columns get one sentence that burst mode was off. Burst columns get section 5a from the template. In **Burst vs normal sheds**, normal sheds are `ON→OFF` minus `ON→OFF burst`.

In **RetryGuard toggles**, paste the scorer's count table, including the burst column when it is present, and the timestamp table for every hold that has transition lines. Holds with no transition lines are one sentence.

For each TopFull-on burst hold, one sentence compares the first `metric=rpr_burst` time with the replay's 104–113 s window in [2026-10-12-s2-burst-replay.md](../../../Guides%20and%20Info/2026-10-12-s2-burst-replay.md). Later fire counts in that table assume instant recovery and are not a live forecast. TopFull-off holds have no replay; do not invent a predicted fire time. The four normal-mode columns are the no-burst comparison in this session. The earlier pair `study5_s2_burst15_rgtf0` and `study5_s2_burst15_rgtf1` is named in Related links and is not a column in this table.

- [ ] **Step 3: Record the holds**

Append one bullet under Done in [STATUS.md](../../../STATUS.md). Name the twelve `log_folder` values, the three modes (normal, `burst_rpr` 1.5, `burst_rpr` 2.0), which folders had TopFull on, Locust row counts, burst shed counts, and whether each gate passed. Point at the run log and the new guide. Say the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, and the three VMs were left **TERMINATED**. Leave "Next free slots" unchanged.

Replace the three Latest lines in [AGENTS.md](../../../AGENTS.md) §4. Do not append a fourth line.

- Line 1 names these twelve holds and points at the STATUS bullet and [2026-10-12-s2-burst-matrix-abc.md](Guides%20and%20Info/2026-10-12-s2-burst-matrix-abc.md).
- Line 2 keeps the replay fact: only `frontend → checkoutservice` crosses, first fire **104–113 s** at bars **1.0 / 1.5 / 2.0**, and points at [2026-10-12-s2-burst-replay.md](Guides%20and%20Info/2026-10-12-s2-burst-replay.md).
- Line 3 states the cluster is back on the unpinned pair and the VMs are **TERMINATED**.

Replace the Still open bullet that says burst-mode live bars and repeats are not chosen with: bars 1.5 and 2.0 each have two live reps on both arms, plus two normal-mode reps on both arms, in this matrix; a single bar is not chosen yet; the guide is the new file.

---

### Task 9: Commit and push

**Files:** everything this plan created or modified. Do not commit `.superpowers/`.

**Interfaces:**
- Consumes: Tasks 1–8 finished, `git status` showing the twelve YAMLs, any `_r2` YAMLs, the `study6_s2_*` result folders, the run log, the guide, this plan, `STATUS.md`, and `AGENTS.md`.
- Produces: four commits on `retryguard-burst-mode`, pushed to `origin`.

- [ ] **Step 1: Confirm the branch and that the VMs are stopped**

```powershell
git branch --show-current
git status -sb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: branch `retryguard-burst-mode`, and all three VMs `TERMINATED`. If a VM is not `TERMINATED`, go back to Task 7 before committing the STATUS bullet.

- [ ] **Step 2: Commit the configs**

```powershell
git add experiments/configs/study_2026_10_12/03_s2_normal_rgtf0_rep1.yaml experiments/configs/study_2026_10_12/04_s2_normal_rgtf0_rep2.yaml experiments/configs/study_2026_10_12/05_s2_normal_rgtf1_rep1.yaml experiments/configs/study_2026_10_12/06_s2_normal_rgtf1_rep2.yaml experiments/configs/study_2026_10_12/07_s2_burst15_rgtf0_rep1.yaml experiments/configs/study_2026_10_12/08_s2_burst15_rgtf0_rep2.yaml experiments/configs/study_2026_10_12/09_s2_burst20_rgtf0_rep1.yaml experiments/configs/study_2026_10_12/10_s2_burst20_rgtf0_rep2.yaml experiments/configs/study_2026_10_12/11_s2_burst15_rgtf1_rep1.yaml experiments/configs/study_2026_10_12/12_s2_burst15_rgtf1_rep2.yaml experiments/configs/study_2026_10_12/13_s2_burst20_rgtf1_rep1.yaml experiments/configs/study_2026_10_12/14_s2_burst20_rgtf1_rep2.yaml
git add -- (Get-ChildItem experiments/configs/study_2026_10_12 -Filter "*_r2.yaml" -ErrorAction SilentlyContinue)
git commit -m @"
feat: add the S2 burst matrix configs

"@
```

The second `git add` is a no-op when no replay YAML exists.

- [ ] **Step 3: Commit the result folders**

```powershell
git add -- (Get-ChildItem experiments/results/campaign_48/S2_sustained_overload -Directory -Filter "study6_s2_*")
git commit -m @"
data: add the S2 burst matrix holds

"@
```

This includes a `_r2` folder when one was pulled. Do not add `study5_s2_burst15_rgtf0` or `study5_s2_burst15_rgtf1`; those are already committed.

- [ ] **Step 4: Commit the write-up**

```powershell
git add "Guides and Info/2026-10-12-s2-burst-matrix-abc.md" docs/superpowers/plans/2026-10-12-s2-burst-matrix.md docs/superpowers/plans/2026-10-12-s2-burst-matrix-run-log.md
git commit -m @"
docs: score the S2 burst matrix

"@
```

- [ ] **Step 5: Commit the status**

```powershell
git add AGENTS.md STATUS.md
git commit -m @"
status: record the S2 burst matrix

"@
```

- [ ] **Step 6: Push**

```powershell
git push -u origin HEAD
git status -sb
```

Expected: `## retryguard-burst-mode...origin/retryguard-burst-mode` with no `ahead` and no untracked plan, config, result, or guide files. Do not force-push. Do not merge to `main`.

---

## Time

Twelve YAMLs and the unit tests: a few minutes. Pin and health check: a few minutes if the VMs are already up, longer if a VM has to start and the API server has to come back. Twelve holds: about 12 minutes each, plus 120 s between them, about three hours of cluster time. One replay adds another hold. The guide is written from the scorer after the pulls. Stopping the VMs is a few minutes. The four commits and the push come last.

## Self-review

- The request is twelve locked-S2 holds, each condition twice: RetryGuard on with TopFull off, and RetryGuard on with TopFull on, in normal mode and in burst mode at bars 1.5 and 2.0. Tasks 3–5 run that table in that order. The finished `study5` pair is extra and is not reused as a replicate.
- Locked means the run-89 mix and Paper-C1. The RetryGuard knobs match the tuned set (`interval_samples` 20, `retries_threshold` 0.4, climb 0.16/0.32 at 10 s, `reenable_rejection` 0.25). `scenario_2_retryguard.yaml` stays at slot run 30. Next free slots do not move.
- Normal mode is the absence of `burst_rpr`. Burst mode sets 1.5 or 2.0 with the 5 s window and the floor of 20. Task 1's checker rejects a normal file that still has burst keys and a burst file with the wrong bar.
- A missing shed is a result, recorded in the run log, and is not a failed gate.
- Cool-off, leftover-writer check, and empty-log check match [AGENTS.md](../../../AGENTS.md) §6. `restart_before_hold` stays unset.
- Task 6 restores the unpinned pair before Task 7 stops the VMs, so the next start comes up unpinned. Task 8 writes TERMINATED only after the list confirms it. Task 9 commits in the same four-part order as the bar-1.5 holds and pushes the branch.
