# S2 Paper-C1 replay holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run nine both-off S2 holds on the disk-copy VMs, all on the Paper-C1 CPU table: three replays of the run 89 mix, three replays of the run 86 mix, and three holds of 275/85/100/90/5, then write the ABC guide and extend the candidate ranking.

**Architecture:** One YAML, `experiments/configs/scenario_2_baseline_no_topfull.yaml`, already carries the Paper-C1 `scale_constraints` and `paper_cpu_reconcile: false`. Each hold changes only `run_number`, `log_folder`, `description`, and `locust.user_counts`. `experiments/run_scenario.py` launches the hold. `experiments/pull_results.py` lands the folder under `campaign_48/`; this plan moves it to `experiments/results/new vms/` so it sits with runs 94–98. Scoring for the ABC guide is `experiments/s2_both_off_abc.py` (no last-5 trim). Scoring for the ranking guide is `experiments/s2_both_off_canon.py`'s streak (last 5 inbound polls dropped). These are live holds, so the per-hold check is the sampling gate below, not a new unit test.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_abc.py`, `experiments/s2_both_off_canon.py`, kubectl over `ssh topfull-master`, `gcloud compute` on project `project-76deda76-55f1-42d2-abb`.

## Global Constraints

- Project is `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start or stop anything in `networks-workshop`. SSH aliases only: `topfull-master`, `topfull-worker-1`, `topfull-load`. User is `idozacharia`.
- Counts are getproduct / postcheckout / getcart / postcart / emptycart. Slots, in this order:

| Slot | Mix name | Counts | Sum |
|---|---|---|---:|
| 99, 100, 101 | run 89 | 275 / 90 / 100 / 90 / 5 | 560 |
| 102, 103, 104 | run 86 | 275 / 80 / 100 / 90 / 5 | 550 |
| 105, 106, 107 | new | 275 / 85 / 100 / 90 / 5 | 555 |

- Every hold is 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`.
- CPU table is Paper-C1 for all nine holds. Do not edit `scale_constraints`. Per-pod millicores, request equals limit: frontend 1150 × 4 (not a `scale_constraints` entry; pinned by HPA), checkoutservice 800, recommendationservice 1150, productcatalogservice 800, cartservice 800, currencyservice 770, shippingservice 770, adservice 1150, paymentservice 155, emailservice 120, redis-cart 540 (container `redis`). Deployment total 11,655 m. `paper_cpu_reconcile: false`. Sidecar annotation `sidecar.istio.io/proxyCPU=100m` on all 11 Deployments. `proxyCPULimit` stays absent. Do not lower the sidecar to 90 m. Do not call `reconcile_paper_cpu_limits`. Do not restore paper CPU or the frontend HPA at the end.
- Cool-off is 360 s after the pin is Ready and before run99, and 360 s between holds. No cool-off after run107. Do not call `Start-Sleep`. Call the AwaitShell tool with no `shell_id` and `block_until_ms: 360000`.
- Do not overwrite run1–run98 in `campaign_48/`, `experiments/results/new vms/`, or `experiments/results/copy verification/`. Do not overwrite run86 or run89 in `campaign_48/` (those are the original mixes, not these replays).
- Local destination after the move: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run<N>/`. `pull_results.py` first writes `experiments/results/campaign_48/S2_sustained_overload/`; move the folder before committing. Nothing from this series stays under `campaign_48/`.
- Before every launch: `ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"`. If a remote command fails with `\r`, reissue it. PowerShell here-strings piped to `ssh ... bash -s` can leave a trailing CR; write the remote script with LF if that happens.
- `duplicate session: envoyretry`: `ssh -o BatchMode=yes topfull-master "tmux kill-session -t envoyretry"`, then relaunch that same slot once. Any other death before Locust: keep whatever folder exists, do not relaunch, stop the series, and continue at Task 11 with the holds that passed the gate.
- A failed gate (missing collector, `total.csv` rows under 500, span outside 480–900, `gap2_pct` over 10, or frontend `rmode` other than 4): keep the folder, do not relaunch that slot, stop further holds, and continue at Task 11. A backend `rzero` above 0 with `rmode` still 1 is an overload symptom: print it and continue.
- Do not edit `experiments/test_topfull_cpu_quotas.py`. `TestBothOffYamlRestored` still expects unused run87 with empty constraints. It already fails against the live Paper-C1 YAML. Leave it. Do not empty `scale_constraints` to make it pass.
- Do not edit `Guides and Info/2026-09-24-s2-both-off-abc-reading.md` or `Guides and Info/2026-10-02-s2-paper-c1-run86-run89-replay.md`.
- Do not commit `.superpowers/` or `s2_canon_*.json`.
- Commit each passing hold before the next cool-off. Push once, in Task 13, after the VMs are stopped.

**Gate.** After the move, from the repo root, with `N` set to the slot. Exit 0 is pass.

```powershell
python -c "import json,os,sys; n=int(sys.argv[1]); p='experiments/results/new vms/baseline_no_topfull_sustained_overload_run%d'%n; cap=json.load(open(p+'/service_capacity.json')); rows=sum(1 for _ in open(p+'/total.csv'))-1; need=['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','total.csv']; missing=[f for f in need if not os.path.exists(p+'/'+f)]; print('rows',rows,'missing',missing,'checkout_m',cap.get('checkoutservice')); sys.exit(1 if missing or rows<500 else 0)" N
python -c "import sys; sys.path.insert(0,'experiments'); import s2_both_off_canon as c; n=int(sys.argv[1]); c.ROOT='experiments/results/new vms/baseline_no_topfull_sustained_overload_run%d'; o=c.score(n); q=o['q']; s=o['svc']; print('span',round(q['span']),'gap2',q['gap2_pct']); print('frontend',s['frontend'].get('rmode'),s['frontend'].get('rzero')); bad=q.get('gap2_pct',100)>10 or not (480<=q.get('span',0)<=900) or s['frontend'].get('rmode')!=4; backends=[k for k in s if k not in ('frontend','__master_node__') and s[k].get('rmode') not in (1,None)]; print('backend_mode_off',backends); print('recs',s['recommendationservice'].get('streak'),s['recommendationservice'].get('ov')); print('checkout',s['checkoutservice'].get('streak'),s['checkoutservice'].get('ov')); print('email_ov',s['emailservice'].get('ov'),'payment_ov',s['paymentservice'].get('ov')); sys.exit(1 if bad or backends else 0)" N
```

Expected: `rows` ≥ 500, `missing` empty, `span` 480–900, `gap2` ≤ 10, frontend `rmode` 4, no backend whose `rmode` is other than 1. `service_capacity.json` checkoutservice limit is 800m (the file stores the Kubernetes limit the runner snapshotted; if the key layout differs, open the file and confirm checkout 800, catalog 800, cart 800, email 120, recommendations 1150).

**Launch.** `run_scenario.py` blocks until the 600 s hold and its teardown finish. Give the Shell tool `block_until_ms` 1200000 (20 minutes). If it backgrounds, poll until the process exits. Then pull and move:

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_runN" "experiments\results\new vms\"
```

Replace `runN` with the slot. If the destination already exists, do not overwrite it; stop.

**Commit one hold.**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_runN" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 runN"
```

Replace `runN` with the slot. Do not `git add` anything else in that commit.

## File map

| File | Role |
|---|---|
| `experiments/configs/scenario_2_baseline_no_topfull.yaml` | The only run config. Tasks 2–10 change `run_number`, `log_folder`, `description`, and `locust.user_counts`. Task 12 leaves it on unused run108. `scale_constraints` stays the Paper-C1 list already in the file. |
| `experiments/results/new vms/baseline_no_topfull_sustained_overload_run99` … `run107` | Created by pull plus move. One data commit each. |
| `Guides and Info/2026-10-03-s2-paper-c1-runs-99-107.md` | Created in Task 11. ABC reading. |
| `Guides and Info/2026-09-30-s2-candidate-ranking-runs-1-79.md` | Task 12 adds a Runs 94–107 section. File name stays. |
| `Guides and Info/2026-10-02-s2-paper-c1-run89-handoff.md` | Task 12 replaces the "next unused slot is run99" sentences so the next session does not relaunch run99. |
| `experiments/results/README.md` | Task 12 adds run99–run107 to the `new vms/` sentence. |
| `AGENTS.md` | Task 12 adds one §4 bullet and changes the both-off next-free slot from run99 to run108. |

---

### Task 1: Start the disk-copy VMs and confirm the Paper-C1 pin

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (only if Step 4 finds run99 already taken)

**Interfaces:**
- Consumes: YAML already at `run_number: 99`, Paper-C1 `scale_constraints`, `paper_cpu_reconcile: false`, counts 275/80/100/90/5 (the unused-slot leftover; Task 2 overwrites the counts).
- Produces: three VMs RUNNING, SSH aliases working, frontend HPA 4/4, catalog HPA 1/1, Paper-C1 limits live, sidecar request 100 m, no `proxyCPULimit`. Slots 99–107 absent on master and on disk.

- [ ] **Step 1: Start the three VMs on the disk-copy project**

```powershell
gcloud config set project project-76deda76-55f1-42d2-abb
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: three rows, status `RUNNING`, each with a natIP. If a start hits `CPUS_ALL_REGIONS`, stop and report that. Do not resize.

- [ ] **Step 2: Refresh SSH, then confirm the API**

Follow [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) "Reconnect after VMs were stopped". `ssh-keygen -R` each previous `HostName` and each new natIP. Change only the three `HostName` lines for `topfull-master`, `topfull-worker-1`, and `topfull-load` in `~/.ssh/config`. Do not edit other Host blocks.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: `topfull-master` and `topfull-worker-1` Ready. If the error is `connection to localhost:8080 refused`, the SSH user has no kubeconfig; this series runs as `idozacharia`, who has one. Retry once after 60 s via AwaitShell `block_until_ms: 60000`. Do not start `networks-workshop`.

- [ ] **Step 3: Confirm slots 99–107 are free**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run(99|10[0-7])$' || echo none"
Get-ChildItem "experiments\results\new vms","experiments\results\campaign_48\S2_sustained_overload" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'run(99|10[0-7])$' } | Select-Object -ExpandProperty FullName
```

Expected: remote prints `none`, and the local `Get-ChildItem` prints nothing. If any name exists, stop. Do not reuse it. Shift every slot in this plan up past the highest existing run and edit the slot table above before Task 2.

- [ ] **Step 4: Confirm the Paper-C1 pin is still what the terminated cluster had**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get hpa frontend-hpa productcatalogservice-hpa -n default; kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas,CPU:.spec.template.spec.containers[0].resources.limits.cpu,PROXY:.spec.template.metadata.annotations.sidecar\\.istio\\.io/proxyCPU,PROXYLIM:.spec.template.metadata.annotations.sidecar\\.istio\\.io/proxyCPULimit"
```

Expected: frontend-hpa min 4 max 4, productcatalogservice-hpa min 1 max 1, checkout `800m`, catalog `800m`, cart `800m`, email `120m`, recommendations `1150m`, payment `155m`, redis-cart `540m`, every PROXY cell `100m`, every PROXYLIM cell `<none>`. Frontend deployment replicas 4, every other Boutique deployment replicas 1.

If the HPA or sidecar drifted, re-apply only this, then re-run the check. Do not reconcile paper CPU.

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}"
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

The millicore limits are applied by `run_scenario.py` from `scale_constraints` at launch. A limit that is still paper (catalog 1535m, cart 1920m, email 155m) is acceptable at this step; run99's launch sets Paper-C1 again. A PROXY of 90m, or a present PROXYLIM, is not acceptable.

- [ ] **Step 5: Wait until pods are Ready**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get pods -n default --no-headers"
```

Expected: four frontend pods `2/2 Running`, one pod `2/2 Running` for each other Boutique service, none Pending. Re-check with AwaitShell `block_until_ms: 30000` until that is true, up to 5 minutes. A Pending pod with `Insufficient cpu`: stop and report `kubectl describe pod`. Do not lower the sidecar.

No commit in this task.

---

### Task 2: Hold run99, mix 89

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run99/`

**Interfaces:**
- Consumes: Paper-C1 pin from Task 1. `scale_constraints` unchanged.
- Produces: run99 folder passing the gate. YAML left at run99 until Task 3 edits it.

- [ ] **Step 1: Cool off 360 s**

Call AwaitShell with no `shell_id` and `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run99 and the run 89 mix**

Set these fields. Leave `scale_constraints`, `paper_cpu_reconcile`, `duration_seconds`, `retries`, `topfull_rl`, `retryguard`, the collectors, and `infra` as they are.

```yaml
run_number: 99
description: >
  Both controllers off. Paper-C1. Replay of the run89 mix. 275/90/100/90/5.
locust:
  user_counts:
    getproduct:   275
    postcheckout: 90
    getcart:      100
    postcart:     90
    emptycart:    5
  spawn_rate: 50
log_folder: baseline_no_topfull_sustained_overload_run99
```

`locust.scripts` stays `- online_boutique_create_v2.sh`. The `locust:` key already exists; replace `user_counts` only, do not duplicate the key.

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000. Expected: the runner prints a completed 600 s hold and an `scp` hint. On `duplicate session: envoyretry`, kill that tmux session once and rerun this step once.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run99" "experiments\results\new vms\"
```

Run the Gate commands from Global Constraints with `N` = 99. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run99" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run99"
```

Expected: commit succeeds. `campaign_48` has no run99 folder.

---

### Task 3: Hold run100, mix 89

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run100/`

**Interfaces:**
- Consumes: run99 committed. Same Paper-C1 `scale_constraints`.
- Produces: run100 folder passing the gate.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run100**

Counts stay 275 / 90 / 100 / 90 / 5. Change only:

```yaml
run_number: 100
description: >
  Both controllers off. Paper-C1. Second replay of the run89 mix. 275/90/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run100
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000. Same `envoyretry` retry rule as Task 2.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run100" "experiments\results\new vms\"
```

Gate with `N` = 100. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run100" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run100"
```

---

### Task 4: Hold run101, mix 89

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run101/`

**Interfaces:**
- Consumes: run100 committed.
- Produces: run101 folder passing the gate. This is the last mix-89 hold.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run101**

Counts stay 275 / 90 / 100 / 90 / 5.

```yaml
run_number: 101
description: >
  Both controllers off. Paper-C1. Third replay of the run89 mix. 275/90/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run101
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run101" "experiments\results\new vms\"
```

Gate with `N` = 101. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run101" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run101"
```

---

### Task 5: Hold run102, mix 86

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run102/`

**Interfaces:**
- Consumes: run101 committed. Paper-C1 `scale_constraints` still unchanged.
- Produces: run102 folder passing the gate.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run102 and the run 86 mix**

```yaml
run_number: 102
description: >
  Both controllers off. Paper-C1. Replay of the run86 mix. 275/80/100/90/5.
locust:
  user_counts:
    getproduct:   275
    postcheckout: 80
    getcart:      100
    postcart:     90
    emptycart:    5
  spawn_rate: 50
log_folder: baseline_no_topfull_sustained_overload_run102
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run102" "experiments\results\new vms\"
```

Gate with `N` = 102. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run102" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run102"
```

---

### Task 6: Hold run103, mix 86

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run103/`

**Interfaces:**
- Consumes: run102 committed.
- Produces: run103 folder passing the gate.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run103**

Counts stay 275 / 80 / 100 / 90 / 5.

```yaml
run_number: 103
description: >
  Both controllers off. Paper-C1. Second replay of the run86 mix. 275/80/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run103
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run103" "experiments\results\new vms\"
```

Gate with `N` = 103. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run103" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run103"
```

---

### Task 7: Hold run104, mix 86

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run104/`

**Interfaces:**
- Consumes: run103 committed.
- Produces: run104 folder passing the gate. This is the last mix-86 hold.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run104**

Counts stay 275 / 80 / 100 / 90 / 5.

```yaml
run_number: 104
description: >
  Both controllers off. Paper-C1. Third replay of the run86 mix. 275/80/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run104
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run104" "experiments\results\new vms\"
```

Gate with `N` = 104. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run104" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run104"
```

---

### Task 8: Hold run105, mix 275/85/100/90/5

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run105/`

**Interfaces:**
- Consumes: run104 committed.
- Produces: run105 folder passing the gate.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run105 and the new mix**

```yaml
run_number: 105
description: >
  Both controllers off. Paper-C1. New mix between run86 and run89. 275/85/100/90/5.
locust:
  user_counts:
    getproduct:   275
    postcheckout: 85
    getcart:      100
    postcart:     90
    emptycart:    5
  spawn_rate: 50
log_folder: baseline_no_topfull_sustained_overload_run105
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run105" "experiments\results\new vms\"
```

Gate with `N` = 105. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run105" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run105"
```

---

### Task 9: Hold run106, mix 275/85/100/90/5

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run106/`

**Interfaces:**
- Consumes: run105 committed.
- Produces: run106 folder passing the gate.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run106**

Counts stay 275 / 85 / 100 / 90 / 5.

```yaml
run_number: 106
description: >
  Both controllers off. Paper-C1. Second hold of 275/85/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run106
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run106" "experiments\results\new vms\"
```

Gate with `N` = 106. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run106" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run106"
```

---

### Task 10: Hold run107, mix 275/85/100/90/5

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Create: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run107/`

**Interfaces:**
- Consumes: run106 committed.
- Produces: run107 folder passing the gate. Last hold. No cool-off after it.

- [ ] **Step 1: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 2: Point the YAML at run107**

Counts stay 275 / 85 / 100 / 90 / 5.

```yaml
run_number: 107
description: >
  Both controllers off. Paper-C1. Third hold of 275/85/100/90/5.
log_folder: baseline_no_topfull_sustained_overload_run107
```

- [ ] **Step 3: Launch**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Shell `block_until_ms`: 1200000.

- [ ] **Step 4: Pull, move, gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
Move-Item "experiments\results\campaign_48\S2_sustained_overload\baseline_no_topfull_sustained_overload_run107" "experiments\results\new vms\"
```

Gate with `N` = 107. Expected: exit 0.

- [ ] **Step 5: Commit**

```powershell
git add "experiments/results/new vms/baseline_no_topfull_sustained_overload_run107" experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 Paper-C1 run107"
```

Do not cool off after this commit.

---

### Task 11: ABC guide for runs 99–107

**Files:**
- Create: `Guides and Info/2026-10-03-s2-paper-c1-runs-99-107.md`

**Interfaces:**
- Consumes: every run99–run107 folder that passed the gate, plus the earlier folders listed in Step 1. `experiments/s2_both_off_abc.py` `score_run(path)` returns `inbound[service].streak` and `.high_samples`, `overloaded[service].overloaded_ticks` and `.ticks`, `retry_by_edge`, `retry_by_target`, `cpu_mean_max`, `layer_a_admitting_rows`.
- Produces: one guide whose section list matches the handoff. Task 12 links it.

- [ ] **Step 1: Score every comparison folder with the ABC scorer**

Paths:

- This series: `experiments/results/new vms/baseline_no_topfull_sustained_overload_run99` through `run107` (skip a slot that never passed the gate).
- Mix 89 earlier holds: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run89`, `..._run92`, and `experiments/results/new vms/baseline_no_topfull_sustained_overload_run94`, `run95`, `run96`, `run97`.
- Mix 86 earlier holds: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run86`, `..._run88`, and `experiments/results/new vms/baseline_no_topfull_sustained_overload_run98`.

```powershell
$env:PYTHONIOENCODING='utf-8'
python experiments/s2_both_off_abc.py `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run99" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run100" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run101" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run102" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run103" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run104" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run105" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run106" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run107" `
  "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run89" `
  "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run92" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run94" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run95" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run96" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run97" `
  "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run86" `
  "experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run88" `
  "experiments/results/new vms/baseline_no_topfull_sustained_overload_run98"
```

Expected: one markdown block per folder. Those cells are the only numbers that go in the guide. The Locust, inbound, and detector tables that `s2_both_off_abc.py` does not print come from the same files the runs 35–38 guide used: the five Locust CSVs, `service_inbound.csv`, `resource_usage.csv`, `topfull_detect.csv`. Read [2026-09-27-s2-replica-cpu-runs-35-38.md](../../../Guides%20and%20Info/2026-09-27-s2-replica-cpu-runs-35-38.md) for the column arithmetic (goodput mean, Fail/RPS, Latency95 mean, arrival as Δtotal/Δt, 5xx fraction, reset fraction, sojourn, share above 500 ms, CPU mean/max over per-pod quota × replicas, detector max utilization). Do not invent a second definition.

- [ ] **Step 2: Write the guide in the handoff's section order**

Copy the section order from [2026-09-27-s2-cpu-variant-handoff.md](../../../Guides%20and%20Info/2026-09-27-s2-cpu-variant-handoff.md) "Post-run analysis", and the table shape from [2026-09-27-s2-replica-cpu-runs-35-38.md](../../../Guides%20and%20Info/2026-09-27-s2-replica-cpu-runs-35-38.md). Title: `# S2 Paper-C1 runs 99–107, all services`. Setup paragraph states 600 s, both controllers off, `spawn_rate` 50, Paper-C1, frontend pinned at 4, sidecar request 100 m with no CPU limit, 360 s cool-off before run99 and between holds, no cool-off after run107. Link the ABC reading and the Paper-C1 pin in [2026-10-02-s2-paper-c1-run89-handoff.md](../../../Guides%20and%20Info/2026-10-02-s2-paper-c1-run89-handoff.md).

Mix index, then one comparison table per section. Column order, left to right, with a `**┃**` bar between mix groups:

| Group | Columns |
|---|---|
| 275/90/100/90/5 | run99, run100, run101, bar, run97, run96, run95, run94, run92, run89 |
| 275/80/100/90/5 | run102, run103, run104, bar, run98, run88, run86 |
| 275/85/100/90/5 | run105, run106, run107 |

Sections, in this order:

1. Setup paragraph and the mix index.
2. **(a)** inbound rejection streak / samples above 0.20. **Bold** is streak ≥ 30 on a controlled service. Frontend and redis-cart stay plain. **(b)** detector overloaded ticks over rows. **Bold** is a share ≥ 0.5. **(c)** retry edges with a positive delta, largest first, then a retry-by-target table.
3. CPU mean / max. Quota column is the per-pod limit. Replicas column is 4 for frontend and 1 for every other service. Mean / max are `cpu_millicores` summed across replicas.
4. Locust goodput, Locust fail rate (`Fail / RPS`), and Locust P95 (`Latency95`), each its own table, per API (getproduct, postcheckout, getcart, postcart, emptycart).
5. Inbound arrival rate, per service.
6. Inbound 5xx fraction and inbound reset fraction, two tables.
7. Inbound sojourn, and the share of inbound requests above 500 ms.
8. CPU use as a fraction of per-pod quota × replicas (mean / max).
9. Detector max utilization.
10. Per-mix prose: for each of the three mixes, state whether each new hold is a blend, a near-miss, or a miss, using the blend bar (recommendations streak ≥ 10 and ov ≥ 10, checkout streak ≥ 10 and ov ≥ 10, email or payment ov ≥ 10). Say whether the three new holds of a mix agreed with each other and with the earlier holds of that mix. Related links: the ranking guide, the run 89 handoff, and [2026-10-02-s2-paper-c1-run86-run89-replay.md](../../../Guides%20and%20Info/2026-10-02-s2-paper-c1-run86-run89-replay.md).

A hold that failed the gate gets a column of blanks and one sentence in the setup paragraph naming the gate it failed. Do not drop its slot number.

- [ ] **Step 3: Check the guide against the section list**

Confirm all ten sections exist, both bold rules are applied, and the three mix groups are separated by `**┃**`. Diff one (a) cell against the Step 1 scorer output for run99 checkout and run99 recommendations. They must match exactly.

No commit in this task. Task 13 commits the guide with the other docs.

---

### Task 12: Ranking, handoff, README, AGENTS, unused run108

**Files:**
- Modify: `Guides and Info/2026-09-30-s2-candidate-ranking-runs-1-79.md`
- Modify: `Guides and Info/2026-10-02-s2-paper-c1-run89-handoff.md` (opening "Where things stand" only)
- Modify: `experiments/results/README.md`
- Modify: `AGENTS.md`
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Consumes: the gate's canon printout (`streak` and `ov` with the last 5 polls dropped) for runs 94–107. Runs 86, 88, 89, 92 stay the numbers already in the ranking guide.
- Produces: ranking section "Runs 94–107", next-free slot run108, YAML on that unused slot with the Paper-C1 constraints still present.

- [ ] **Step 1: Canon-score runs 94–107**

Runs 94–98 are already on disk. Runs 99–107 are the ones Task 2–10 committed. Same `ROOT` override as the gate. Write the JSON under `.superpowers/rank/` and do not commit it. Save this as `.superpowers/rank/score_94_107.py`:

```python
import json, os, sys
sys.path.insert(0, "experiments")
import s2_both_off_canon as c
c.ROOT = "experiments/results/new vms/baseline_no_topfull_sustained_overload_run%d"
res = {}
for n in range(94, 108):
    if os.path.isdir(c.ROOT % n):
        o = c.score(n)
        o["edges"] = {"%s>%s" % k: v for k, v in o["edges"].items()}
        res[str(n)] = o
json.dump(res, open(r".superpowers/rank/s2_canon_94_107.json", "w"))
print("scored", sorted(res, key=int))
```

Run `python .superpowers/rank/score_94_107.py`, then delete the script. Keep the JSON until Task 13 and do not `git add` it.

For each scored run print: span, gap2_pct, recommendations streak/ov, checkout streak/ov, email ov, payment ov, and the largest edge. A run with `gap2_pct` > 10 or span outside 480–900 is excluded from the ranking table and named in the exclusion sentence.

- [ ] **Step 2: Append a section to the ranking guide**

Edit `Guides and Info/2026-09-30-s2-candidate-ranking-runs-1-79.md`. Do not rename the file. In the title and the opening paragraph, change the covered range from 1–93 to 1–107 and add a pointer to the new section.

Add `## Runs 94-107 (added 2026-10-03)` after the Runs 80–93 section. State that these numbers are canon streaks (last 5 inbound polls dropped), so they can differ by a few from [2026-10-03-s2-paper-c1-runs-99-107.md](../../../Guides%20and%20Info/2026-10-03-s2-paper-c1-runs-99-107.md) and from [2026-10-02-s2-paper-c1-run86-run89-replay.md](../../../Guides%20and%20Info/2026-10-02-s2-paper-c1-run86-run89-replay.md), which use `s2_both_off_abc.py`. Folders for 94–107 are `experiments/results/new vms/`.

Table columns, same as the Runs 80–93 table: Run, Table and mix, Recs streak / ov, Checkout streak / ov, Email ov, Payment ov, Verdict, Retries on streaking targets, Replay. Verdict uses the blend bar from the Runs 80–93 section. Retries on streaking targets = summed edges of at least 1000 whose target has streak ≥ 10, taken from the JSON. One row per run 94–107 that passed sampling, plus a sentence listing any that failed it.

Then a short ranking of these rows only: which of 99–101 agreed with run89's blend, which of 102–104 agreed with run86's blend, and whether 105–107 (no earlier hold of 275/85/100/90/5) blended. Do not reorder the Runs 80–93 list. Replace the closing "Where a replay would add information" sentence that says run 86 and run 89 are worth another hold: those replays are runs 99–104, and the new section is where their result lives.

- [ ] **Step 3: Leave the YAML on unused run108**

```yaml
run_number: 108
description: >
  Unused slot. Paper-C1 pin may still be live.
  Counts below are 275/85/100/90/5, already launched as run105-run107.
log_folder: baseline_no_topfull_sustained_overload_run108
```

Leave `locust.user_counts` at 275 / 85 / 100 / 90 / 5. Leave `paper_cpu_reconcile: false` and the Paper-C1 `scale_constraints`. Do not launch run108.

- [ ] **Step 4: Update the handoff opening, the results README, and AGENTS.md**

In `Guides and Info/2026-10-02-s2-paper-c1-run89-handoff.md`, replace the opening claim that the next unused slot is run99. The next unused slot is **run108**. The YAML counts are 275 / 85 / 100 / 90 / 5 and were not launched on run108. VMs are terminated in Task 13. Add one link to `Guides and Info/2026-10-03-s2-paper-c1-runs-99-107.md`. Leave the run 89 / run 92 / run 94 / run 95 history below that opening as it is.

In `experiments/results/README.md`, extend the `new vms/` sentence so it includes run99–run107 as well as run94–run98.

In `AGENTS.md` §4, add one bullet: nine Paper-C1 holds run99–run107 on the disk copy, mixes 275/90/100/90/5 (99–101), 275/80/100/90/5 (102–104), 275/85/100/90/5 (105–107), folders under `experiments/results/new vms/`, ABC guide linked, ranking section linked. Include each slot's blend verdict from Step 1 (blend, near-miss, or miss), not a paraphrase. In the "Next free YAML slots" paragraph, change the both-off slot from run99 to **run108**.

- [ ] **Step 5: Re-read the ranking rows against the JSON**

For run99 and run105, the recs streak, checkout streak, email ov, and payment ov in the new table equal `s2_canon_94_107.json`. Fix any cell that differs.

No commit in this task.

---

### Task 13: Stop the VMs, commit the docs, push

**Files:**
- Commit: the Task 11 guide, the Task 12 edits, and `experiments/configs/scenario_2_baseline_no_topfull.yaml` at run108.

**Interfaces:**
- Consumes: Tasks 11 and 12 done. Holds already have their own commits.
- Produces: VMs `TERMINATED` on `project-76deda76-55f1-42d2-abb`, branch pushed, user-facing summary listing every path committed in this series.

- [ ] **Step 1: Stop the three VMs**

Do this before the doc commit so the summary can say they are terminated. Do not restore paper CPU, the frontend HPA, or the catalog HPA. The cluster stays on the Paper-C1 pin.

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
gcloud compute instances list --project=project-76deda76-55f1-42d2-abb --format="table(name,status)"
```

Expected: three rows, status `TERMINATED`.

- [ ] **Step 2: Commit the docs and the unused slot**

```powershell
git add "Guides and Info/2026-10-03-s2-paper-c1-runs-99-107.md" "Guides and Info/2026-09-30-s2-candidate-ranking-runs-1-79.md" "Guides and Info/2026-10-02-s2-paper-c1-run89-handoff.md" experiments/results/README.md AGENTS.md experiments/configs/scenario_2_baseline_no_topfull.yaml
git status --short
git commit -m "docs: ABC and ranking for Paper-C1 runs 99-107"
```

`git status --short` before the commit must not show `.superpowers/` or `s2_canon_*.json` staged. Expected: one docs commit. If Task 11 or 12 changed nothing else, do not add stray files.

- [ ] **Step 3: Push**

```powershell
git push origin cpu-table-calibration
git status -sb
```

Expected: `## cpu-table-calibration...origin/cpu-table-calibration` with no ahead/behind count.

- [ ] **Step 4: Summary**

The user-facing summary lists every file this series committed: the nine run folders (or fewer, if a gate stopped the series), the YAML, the ABC guide, the ranking guide, the handoff, `experiments/results/README.md`, and `AGENTS.md`. State the three mix verdicts in one line each, the next free slot (run108), and that the VMs are terminated on the Paper-C1 pin.
