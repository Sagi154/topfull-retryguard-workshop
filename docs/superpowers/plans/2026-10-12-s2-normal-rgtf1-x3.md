# S2 normal mode, RetryGuard on, TopFull on — three holds

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. These three holds share one cluster. Run them in order in one session. Do not run two holds at once.

**Goal:** Run the locked Scenario 2 mix three times with RetryGuard in normal mode, RetryGuard on, and TopFull on.

**Architecture:** Three study YAMLs copied from `experiments/configs/study_2026_10_12/05_s2_normal_rgtf1_rep1.yaml`. Normal mode is the absence of `burst_rpr`. The runner copies local `experiments/retryguard.py` onto master at the start of each hold, so the holds launch from branch `retryguard-burst-mode`. Start the three terminated VMs, refresh SSH, pin Paper-C1 once, run the three holds with a 120 s cool-off, pull and gate each folder, restore the unpinned shape, write one analysis guide, then commit and push. Leave the VMs running.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/analysis_score.py`, PowerShell, `ssh`, `gcloud`. No controller code changes.

## Global Constraints

- Stay on branch `retryguard-burst-mode`. Do not checkout or merge. Do not commit or push until Task 6.
- Working directory for every local command is `c:\Users\idoza\topfull-retryguard-workshop`.
- All three holds set `retryguard.enabled: true` and `topfull_rl.enabled: true`.
- Normal mode omits `burst_rpr`, `burst_window_seconds`, and `burst_min_first_attempts`. Do not set `burst_rpr: 0`. The controller treats a missing `burst_rpr` as off, and `burst_rpr <= 0` makes `run_scenario.py` exit.
- The finished pair `study6_s2_normal_rgtf1_rep1` and `study6_s2_normal_rgtf1_rep2` is not one of these three. Do not overwrite those folders. Do not skip a new hold because that pair exists.
- Locked S2 means the run-89 mix and the Paper-C1 pin. It does not mean `experiments/configs/scenario_2_retryguard.yaml`. That locked file is still slot **run30**. Do not edit it. Do not bump it. Do not change "Next free slots" in [STATUS.md](../../../STATUS.md).
- Mix: `getproduct=275, postcheckout=90, getcart=100, postcart=90, emptycart=5`, `spawn_rate` 50, duration 600 s.
- RetryGuard knobs, the same set as `05_s2_normal_rgtf1_rep1.yaml`: `retry_metric=edge_rpr`, `rejection_threshold=0.20`, `sample_interval_seconds=1`, `interval_samples=20`, `retries_threshold=0.4`, `climb_rpr_1_to_2=0.16`, `climb_rpr_2_to_3=0.32`, `climb_interval_seconds=10`, `reenable_rejection=0.25`.
- `paper_cpu_reconcile: false`. `run_number: 1` on every study YAML. Omit `restart_before_hold`.
- SSH only via host aliases (`topfull-master`, `topfull-worker-1`, `topfull-load`); user `idozacharia`; project `project-76deda76-55f1-42d2-abb`; zone `us-central1-a`. Do not start the `networks-workshop` originals. Do not hardcode a public IP.
- Cool-off is **120 s**, starting when `run_scenario.py` exits. Pull and the gate happen during that wait. Checkout and recommendations stay up across the cool-off. The cool-off applies between hold 1 and hold 2, and between hold 2 and hold 3.
- Paper-C1 pin for these holds: frontend HPA min=max=4, `productcatalogservice-hpa` min=max=1, frontend sidecar `proxyCPU=90m`, `proxyCPULimit` unset. Last status left the cluster unpinned (frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`) and the three VMs **TERMINATED**. Pin once before hold 1. Restore that unpinned pair once after hold 3.
- CPU quotas are the Paper-C1 table in the YAML `scale_constraints`: checkout 800 m, recommendations 1150 m, catalog 800 m, cart 800 m, currency 770 m, shipping 770 m, ad 1150 m, payment 155 m, email 120 m, redis-cart 540 m. Frontend app container stays 1150 m. The runner applies those constraints at the start of each hold.
- One hold at a time. A failed collector gate keeps its folder and is replayed once with a `_r2` suffix on the YAML and on `log_folder`. Do not overwrite the failed folder. Do not replay a second time.
- A complete hold with zero `ON→OFF` lines is still a pass. Toggle count is recorded and is not a gate.
- PowerShell eats backslashes inside `ssh "..."` JSON. Send `kubectl patch` and `kubectl annotate` as a bash script on stdin (`bash -s`). Do not put the patch JSON in the `ssh` argument string.
- Do not stop the three VMs. Stopping is out of scope for this plan.
- Do not use `run_all_scenarios.py`.

## File Structure

- Create: three YAMLs in `experiments/configs/study_2026_10_12/`, numbered `15` through `17`.
- Create during the runs: `docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md` — one line per hold, including a failed hold and any single replay.
- Create after the pulls: `Guides and Info/2026-10-12-s2-normal-rgtf1-x3-abc.md` — scorer write-up for the three folders.
- Modify after the unpinned pair is restored: `STATUS.md` (one Done bullet; "Next free slots" unchanged) and `AGENTS.md` §4 (replace the three Latest lines).
- Read-only source: `experiments/configs/study_2026_10_12/05_s2_normal_rgtf1_rep1.yaml`.
- Do not modify: `05_s2_normal_rgtf1_rep1.yaml`, `06_s2_normal_rgtf1_rep2.yaml`, or any `scenario_2_*.yaml`.

Results land in `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

| # | Mode | TopFull | File | `log_folder` |
| --- | --- | --- | --- | --- |
| 1 | normal | on | `15_s2_normal_rgtf1_rep1.yaml` | `study7_s2_normal_rgtf1_rep1` |
| 2 | normal | on | `16_s2_normal_rgtf1_rep2.yaml` | `study7_s2_normal_rgtf1_rep2` |
| 3 | normal | on | `17_s2_normal_rgtf1_rep3.yaml` | `study7_s2_normal_rgtf1_rep3` |

Paths are under `experiments/configs/study_2026_10_12/`. `study7` is this session. `study6_s2_normal_rgtf1_rep1` and `rep2` stay the earlier pair.

---

### Task 1: Confirm the branch and write the three YAMLs

**Files:**
- Create: `experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml`
- Create: `experiments/configs/study_2026_10_12/16_s2_normal_rgtf1_rep2.yaml`
- Create: `experiments/configs/study_2026_10_12/17_s2_normal_rgtf1_rep3.yaml`
- Read: `experiments/configs/study_2026_10_12/05_s2_normal_rgtf1_rep1.yaml`

**Interfaces:**
- Consumes: `05_s2_normal_rgtf1_rep1.yaml` as the canonical both-on normal-mode file. A missing `burst_rpr` is normal mode.
- Produces: the three YAML paths. Later tasks launch those paths and do not edit them, except a single `_r2` copy after a failed gate.

- [ ] **Step 1: Confirm the branch**

```powershell
git branch --show-current
```

Expected: `retryguard-burst-mode`. If the branch name is anything else, stop and ask. Do not checkout.

- [ ] **Step 2: Confirm the three result names are free**

```powershell
$names = @(
  "study7_s2_normal_rgtf1_rep1",
  "study7_s2_normal_rgtf1_rep2",
  "study7_s2_normal_rgtf1_rep3"
)
foreach ($n in $names) {
  $p = "experiments/results/campaign_48/S2_sustained_overload/$n"
  if (Test-Path $p) { "EXISTS $n" } else { "ABSENT $n" }
}
```

Expected: `ABSENT` three times. An `EXISTS` line means stop and pick a new `log_folder` before writing that YAML.

- [ ] **Step 3: Write hold 1**

Create `experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml` with this exact content. It is `05_s2_normal_rgtf1_rep1.yaml` with the plan comment, description, and `log_folder` changed. `topfull_rl.enabled` stays `true`. No burst keys.

```yaml
# Plan: docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3.md
scenario_id: 2
scenario_name: sustained_overload
condition: retryguard
run_number: 1
description: 'Study 2026-10-12 study7_s2_normal_rgtf1_rep1 (275/90/100/90/5): locked S2,
  normal mode, RetryGuard on, TopFull on.'
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
  enabled: true
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
log_folder: study7_s2_normal_rgtf1_rep1
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

- [ ] **Step 4: Write holds 2 and 3 from hold 1**

```powershell
$src = Get-Content -Raw "experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml"
$rep2 = $src.Replace("study7_s2_normal_rgtf1_rep1", "study7_s2_normal_rgtf1_rep2")
$rep3 = $src.Replace("study7_s2_normal_rgtf1_rep1", "study7_s2_normal_rgtf1_rep3")
$utf8 = New-Object System.Text.UTF8Encoding $false
$dir = (Resolve-Path "experiments/configs/study_2026_10_12").Path
[System.IO.File]::WriteAllText((Join-Path $dir "16_s2_normal_rgtf1_rep2.yaml"), $rep2, $utf8)
[System.IO.File]::WriteAllText((Join-Path $dir "17_s2_normal_rgtf1_rep3.yaml"), $rep3, $utf8)
```

The only replacements are the two occurrences of the folder token (description and `log_folder`).

- [ ] **Step 5: Check the three files**

```powershell
python -c @"
from pathlib import Path
import yaml
root = Path('experiments/configs/study_2026_10_12')
names = [
    '15_s2_normal_rgtf1_rep1.yaml',
    '16_s2_normal_rgtf1_rep2.yaml',
    '17_s2_normal_rgtf1_rep3.yaml',
]
canon = yaml.safe_load((root / '05_s2_normal_rgtf1_rep1.yaml').read_text(encoding='utf-8'))
burst = ('burst_rpr', 'burst_window_seconds', 'burst_min_first_attempts')
for i, name in enumerate(names, start=1):
    doc = yaml.safe_load((root / name).read_text(encoding='utf-8'))
    folder = f'study7_s2_normal_rgtf1_rep{i}'
    assert doc['log_folder'] == folder, name
    assert folder in doc['description'], name
    assert doc['topfull_rl']['enabled'] is True, name
    assert doc['retryguard']['enabled'] is True, name
    assert doc['retryguard']['retry_metric'] == 'edge_rpr', name
    assert doc['retryguard']['interval_samples'] == 20, name
    assert doc['retryguard']['retries_threshold'] == 0.4, name
    assert doc['retryguard']['reenable_rejection'] == 0.25, name
    assert doc['retryguard']['climb_interval_seconds'] == 10, name
    assert all(k not in doc['retryguard'] for k in burst), name
    assert 'restart_before_hold' not in doc, name
    assert doc['run_number'] == 1, name
    assert doc['paper_cpu_reconcile'] is False, name
    assert doc['locust']['user_counts'] == canon['locust']['user_counts'], name
    assert doc['scale_constraints'] == canon['scale_constraints'], name
    print(f'OK {name} {folder}')
"@
```

Expected: three `OK` lines. Any `AssertionError` means fix that YAML before Task 2. Do not start a hold.

---

### Task 2: Preflight — start the VMs, then pin

**Files:** none. `~/.ssh/config` HostName lines for the three aliases are updated in place. Do not commit that file.

**Interfaces:**
- Consumes: the three YAML paths from Task 1. Does not edit them.
- Produces: SSH as `idozacharia`, a Paper-C1 pin (frontend HPA 4/4, catalog HPA 1/1, sidecar `90m`), and an empty live log directory, ready for hold 1.

- [ ] **Step 1: Start the three VMs**

Last status left them `TERMINATED`. Confirm the project, then start.

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Start only if a workshop VM is `TERMINATED`. Do not start anything whose name is outside `topfull-master`, `topfull-worker-1`, and `topfull-load`.

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: all three `RUNNING`, each with a public IP. If a row is still `STAGING`, list again until it is `RUNNING`.

- [ ] **Step 2: Refresh HostName, then SSH**

Read the three old `HostName` values from `$env:USERPROFILE\.ssh\config` before editing. For each old IP and each new natIP from Step 1:

```powershell
ssh-keygen -R <ip>
```

Change only the `HostName` line inside the `Host topfull-master`, `Host topfull-worker-1`, and `Host topfull-load` blocks. Leave `User idozacharia` and every other Host block as they are.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
```

Expected user on all three: `idozacharia`. If SSH fails on a stale IP, refresh `HostName` and retry. Do not hardcode an IP into a later command.

- [ ] **Step 3: Confirm the master result folders are absent**

```powershell
ssh topfull-master "for d in study7_s2_normal_rgtf1_rep1 study7_s2_normal_rgtf1_rep2 study7_s2_normal_rgtf1_rep3; do if test -d /home/idozacharia/experiments/results/`$d; then echo EXISTS `$d; else echo ABSENT `$d; fi; done"
```

Expected: `ABSENT` three times. An `EXISTS` line means stop and pick a new `log_folder`. The runner writes that directory on master and a second launch with the same name overwrites it.

- [ ] **Step 4: Cluster health**

The API server can take a few minutes after a start. Retry this until the nodes answer, up to about 5 minutes:

```powershell
ssh topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

All nodes `Ready`. Boutique pods `2/2`. VirtualServices present. If `kubectl` still says `connection to localhost:8080 refused` after those retries, the SSH user is missing `~/.kube/config` — copy `idozacharia`'s kubeconfig as in [AGENTS.md](../../../AGENTS.md) §7, then retry. Do not start the hold until pods are `2/2`.

- [ ] **Step 5: Paper-C1 pin**

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

- [ ] **Step 6: Stop leftover writers once**

```powershell
ssh topfull-load "tmux kill-server 2>/dev/null; pkill -9 -f '[l]ocust' 2>/dev/null; true"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json /tmp/retryguard_params.json; pkill -f '[m]etric_collector.py' 2>/dev/null; pkill -f '[d]eploy_rl.py' 2>/dev/null; pkill -f '[p]roxy_online_boutique' 2>/dev/null; pkill -f '[r]etryguard.py' 2>/dev/null; pkill -f '[e]nvoy_retry_collector.py' 2>/dev/null; pkill -f '[r]esource_usage_collector.py' 2>/dev/null; pkill -f '[t]opfull_throttle_collector.py' 2>/dev/null; sleep 2; pkill -9 -f '[r]ay::|[r]aylet|[g]cs_server' 2>/dev/null; tmux kill-server 2>/dev/null; true"
```

Hold 1 starts at Task 3.

---

### Task 3: Run the three holds

**Files:**
- Create: `docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md`
- Read: `15`, `16`, and `17` under `experiments/configs/study_2026_10_12/`

**Interfaces:**
- Consumes: the pinned cluster from Task 2 and the three YAMLs.
- Produces: three pulled folders (`study7_s2_normal_rgtf1_rep1`, `study7_s2_normal_rgtf1_rep2`, `study7_s2_normal_rgtf1_rep3`) and three run-log lines. Task 5 scores those folders.

Repeat Steps 1–7 for these YAMLs, in this order:

1. `experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml`
2. `experiments/configs/study_2026_10_12/16_s2_normal_rgtf1_rep2.yaml`
3. `experiments/configs/study_2026_10_12/17_s2_normal_rgtf1_rep3.yaml`

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

Hold 1:

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml
```

Hold 2, after hold 1's cool-off and a fresh Steps 1–3:

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/16_s2_normal_rgtf1_rep2.yaml
```

Hold 3, after hold 2's cool-off and a fresh Steps 1–3:

```powershell
python experiments/run_scenario.py experiments/configs/study_2026_10_12/17_s2_normal_rgtf1_rep3.yaml
```

One process only. A 600 s hold plus startup is about 12 minutes. Do not start the next hold until this process exits. The 120 s cool-off clock starts at that exit. Steps 5 and 6 happen during the wait.

- [ ] **Step 5: Pull**

Use the YAML that just finished.

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml
```

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/16_s2_normal_rgtf1_rep2.yaml
```

```powershell
python experiments/pull_results.py experiments/configs/study_2026_10_12/17_s2_normal_rgtf1_rep3.yaml
```

The folder is `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

- [ ] **Step 6: Gates.** Keep the folder either way.

Write this checker once, then run it on the folder that just finished:

```powershell
@'
import csv, sys
from pathlib import Path
folder = sys.argv[1]
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
missing = [s for s in need if s not in start]
if "burst_rpr=" in start:
    missing.append("burst keys present on a normal hold")
print("start_missing=" + (",".join(missing) if missing else "none"))
print("patch_fail=" + ("yes" if "PATCH_FAIL" in log or "Traceback" in log else "no"))
off = sum(1 for line in log.splitlines() if "ON→OFF" in line or "ON->OFF" in line)
up = sum(1 for line in log.splitlines() if any(tok in line for tok in ("OFF→ON", "OFF->ON", "1→2", "1->2", "2→3", "2->3")))
burst = sum(1 for line in log.splitlines() if "metric=rpr_burst" in line and ("ON→OFF" in line or "ON->OFF" in line))
print(f"toggles_off={off} toggles_up={up} toggles_burst={burst}")
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
'@ | Set-Content -Encoding ascii "$env:TEMP\s2_normal_rgtf1_gate.py"
python "$env:TEMP\s2_normal_rgtf1_gate.py" experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep1
```

Swap the folder argument for rep2 and rep3. Pass, all three holds:

- `locust_rows` is about 540–580.
- `start_missing=none`. The START line has no `burst_rpr=`.
- `patch_fail=no`.
- `toggles_burst=0`.
- `frontend_4` equals its denominator. `catalog_1` equals its denominator. A catalog sample that is missing is allowed; a catalog sample whose `replica_count` is not 1 is a fail.
- `live5s_caps` is at least 1. TopFull is on. A live 0 is an empty read and does not count as a cap. `other=0`.

Also confirm VirtualServices are back at 3 attempts:

```powershell
@'
kubectl get virtualservice -n default -o jsonpath="{range .items[*]}{.metadata.name}{\" \"}{.spec.http[*].retries.attempts}{\"\n\"}{end}"
'@ | ssh topfull-master "bash -s"
```

Expected: every printed attempts value is `3`. No route `timeout` was added by the hold; if a VirtualService shows a timeout, that hold fails the gate.

A collector-gate failure is logged, the folder is kept, and the hold is replayed **once**. Copy the YAML to a sibling with `_r2` before `.yaml`, set `log_folder` to the same name plus `_r2`, and set the description's folder token to that new name. Launch that file through Steps 1–6. Do not overwrite the failed folder. Do not replay a second time.

- [ ] **Step 7: Finish the 120 s cool-off** after holds 1 and 2, then Steps 1–3 again, before the next hold. After hold 3, the cool-off is not required before Task 4. If Steps 5–6 already used the whole 120 s, go straight to Steps 1–3. Otherwise `Start-Sleep -Seconds` for the remainder, measured from the `run_scenario.py` exit.

- [ ] **Step 8: Append one line per hold** to `docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md`. Create the file on hold 1 with this header:

```markdown
# S2 normal mode, RetryGuard on, TopFull on — run log

One line per hold, including a failed hold and any single replay.

`hold N | log_folder | PASS or INVALID | locust rows | note`
```

Line shape:

`hold N | log_folder | PASS or INVALID | locust rows | Paper-C1; users 275/90/100/90/5; normal; TopFull on; toggles N (off N, up N, burst 0); frontend 4 on N/N; TF live5s_10000=N live5s_caps=N live5s_zero=N other=N; VS attempts 3; START ok or the failure`

Count `off` as `ON→OFF` lines, `up` as `OFF→ON` plus `1→2` plus `2→3`, and `burst` as sheds whose line contains `metric=rpr_burst`. On a passed hold `burst` is 0.

---

### Task 4: Restore the unpinned pair

**Files:** none.

**Interfaces:**
- Consumes: the cluster left pinned by Task 2, and three pulled folders from Task 3. Do not restore before a failed hold's single replay has been pulled.
- Produces: frontend HPA min 1 / max 4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, checkout 800 m, catalog 800 m, email 120 m. The VMs stay `RUNNING`.

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

Do not run `gcloud compute instances stop`.

---

### Task 5: Score and write the guide

Do this after all three folders are pulled and Task 4 has restored the unpinned pair. Numbers come from the scorer. Do not invent a cell.

**Files:**
- Create: `Guides and Info/2026-10-12-s2-normal-rgtf1-x3-abc.md`
- Modify: `STATUS.md`, `AGENTS.md`
- Read: [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md), [2026-10-12-s2-burst-matrix-abc.md](../../../Guides%20and%20Info/2026-10-12-s2-burst-matrix-abc.md)

**Interfaces:**
- Consumes: the three pulled folders. If a `_r2` replay exists, score that folder in place of the failed one and name the failed folder in the Gate section.
- Produces: the guide, one STATUS Done bullet, and three replacement Latest lines.

- [ ] **Step 1: Score the three holds**

```powershell
python experiments/analysis_score.py `
  experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep1 `
  experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep2 `
  experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep3
```

The scorer labels a folder with its name when the name does not end in `run<N>`. Use those labels as the index columns. Column order is rep1, rep2, rep3. No `--sep`.

- [ ] **Step 2: Write the guide**

Follow [ANALYSIS-TEMPLATE.md](../../../Guides%20and%20Info/ANALYSIS-TEMPLATE.md) section order.

Setup states: three 600 s holds, mix 275 / 90 / 100 / 90 / 5, `spawn_rate` 50, Paper-C1 pin, RetryGuard on, TopFull on, normal mode (no `burst_rpr`), 120 s cool-off, tuned knobs from Global Constraints. Climb steps are 10 s (`climb_interval_seconds: 10`).

Index is one row, three columns, no bold bar.

Edge-mode bars: copy the scorer's first line. One sentence says burst mode was off. Skip the burst window table. In **RetryGuard toggles**, paste the scorer's count table and the timestamp table for every hold that has transition lines. Holds with no transition lines are one sentence.

The earlier pair `study6_s2_normal_rgtf1_rep1` and `study6_s2_normal_rgtf1_rep2` is named in Related links and is not a column in this table. Point at [2026-10-12-s2-burst-matrix-abc.md](../../../Guides%20and%20Info/2026-10-12-s2-burst-matrix-abc.md).

- [ ] **Step 3: Record the holds**

Append one bullet under Done in [STATUS.md](../../../STATUS.md). Name the three `log_folder` values, say normal mode with RetryGuard on and TopFull on, and fill Locust row counts, toggle counts, and pass/fail from the run log. Point at the run log and the new guide. Say the cluster was restored to frontend HPA 1–4, catalog HPA max 2, sidecar `proxyCPU=100m`, `proxyCPULimit` unset, and the three VMs were left **RUNNING**. Leave "Next free slots" unchanged.

Replace the three Latest lines in [AGENTS.md](../../../AGENTS.md) §4. Do not append a fourth line.

- Line 1 names these three holds, says all three PASS or names any INVALID, and points at the STATUS bullet and [2026-10-12-s2-normal-rgtf1-x3-abc.md](Guides%20and%20Info/2026-10-12-s2-normal-rgtf1-x3-abc.md).
- Line 2 keeps the replay fact: only `frontend → checkoutservice` crosses, first fire **104–113 s** at bars **1.0 / 1.5 / 2.0**, and points at [2026-10-12-s2-burst-replay.md](Guides%20and%20Info/2026-10-12-s2-burst-replay.md).
- Line 3 states the cluster is back on the unpinned pair and the VMs are **RUNNING**.

Leave the Still open bullet that points at the burst-matrix guide as it is. These three holds do not choose a burst bar.

---

### Task 6: Commit and push

**Files:** everything this plan created or modified. Do not commit `.superpowers/` or `~/.ssh/config`.

**Interfaces:**
- Consumes: Tasks 1–5 finished, `git status` showing the three YAMLs, any `_r2` YAMLs, the `study7_s2_normal_rgtf1_*` result folders, the run log, the guide, this plan, `STATUS.md`, and `AGENTS.md`.
- Produces: four commits on `retryguard-burst-mode`, pushed to `origin`.

- [ ] **Step 1: Confirm the branch and that the VMs are still running**

```powershell
git branch --show-current
git status -sb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: branch `retryguard-burst-mode`, and all three VMs `RUNNING`. If a VM is `TERMINATED`, do not rewrite the STATUS bullet to say RUNNING.

- [ ] **Step 2: Commit the configs**

```powershell
git add experiments/configs/study_2026_10_12/15_s2_normal_rgtf1_rep1.yaml experiments/configs/study_2026_10_12/16_s2_normal_rgtf1_rep2.yaml experiments/configs/study_2026_10_12/17_s2_normal_rgtf1_rep3.yaml
git add -- (Get-ChildItem experiments/configs/study_2026_10_12 -Filter "*_r2.yaml" -ErrorAction SilentlyContinue)
git commit -m @"
feat: add three S2 normal-mode both-on configs

"@
```

The second `git add` is a no-op when no replay YAML exists. Do not add a `_r2` file from an older session if one is already tracked; `git status` before this step is the check. Add only paths this plan created.

- [ ] **Step 3: Commit the result folders**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep1 experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep2 experiments/results/campaign_48/S2_sustained_overload/study7_s2_normal_rgtf1_rep3
git add -- (Get-ChildItem experiments/results/campaign_48/S2_sustained_overload -Directory -Filter "study7_s2_normal_rgtf1_*_r2" -ErrorAction SilentlyContinue)
git commit -m @"
data: add three S2 normal-mode both-on holds

"@
```

Do not add `study6_s2_*`. Those are already committed.

- [ ] **Step 4: Commit the write-up**

```powershell
git add "Guides and Info/2026-10-12-s2-normal-rgtf1-x3-abc.md" docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3.md docs/superpowers/plans/2026-10-12-s2-normal-rgtf1-x3-run-log.md
git commit -m @"
docs: score three S2 normal-mode both-on holds

"@
```

- [ ] **Step 5: Commit the status**

```powershell
git add AGENTS.md STATUS.md
git commit -m @"
status: record three S2 normal-mode both-on holds

"@
```

- [ ] **Step 6: Push**

```powershell
git push -u origin HEAD
git status -sb
```

Expected: `## retryguard-burst-mode...origin/retryguard-burst-mode` with no `ahead` and no untracked plan, config, result, or guide files from this session. Do not force-push. Do not merge to `main`.

---

## Time

Three YAMLs: a few minutes. Start, HostName refresh, and the pin: several minutes, because the VMs are `TERMINATED` and the API server has to come back. Three holds: about 12 minutes each, plus 120 s between them, about 40 minutes of cluster time. One replay adds another hold. The guide is written from the scorer after the pulls. The four commits and the push come last. The VMs stay up.

## Self-review

- The request is three locked-S2 holds: normal mode, RetryGuard on, TopFull on. Task 3 runs that table in order. The finished `study6` normal both-on pair is extra and is not reused as a replicate. The new folders are `study7_s2_normal_rgtf1_rep1`, `rep2`, and `rep3`.
- Locked means the run-89 mix and Paper-C1. The RetryGuard knobs match the tuned set (`interval_samples` 20, `retries_threshold` 0.4, climb 0.16/0.32 at 10 s, `reenable_rejection` 0.25). `scenario_2_retryguard.yaml` stays at slot run 30. Next free slots do not move.
- Normal mode is the absence of `burst_rpr`. Task 1's checker rejects a file that still has burst keys or has TopFull off.
- A missing shed is a result, recorded in the run log, and is not a failed gate. `live5s_caps >= 1` is a gate because TopFull is on.
- Cool-off, leftover-writer check, and empty-log check match [AGENTS.md](../../../AGENTS.md) §6. `restart_before_hold` stays unset.
- Task 4 restores the unpinned pair and does not stop the VMs. Task 5 writes the STATUS bullet as RUNNING. Task 6 Step 1 lists the three VMs before the status commit; if one is not `RUNNING`, edit that bullet before committing it. Task 6 commits in four parts and pushes the branch.
