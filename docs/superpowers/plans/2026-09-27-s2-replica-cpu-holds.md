# S2 Replica-CPU Holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run four both-off S2 holds on the Replica CPU table with every service pinned at that table's replica count, then write the all-service (a)/(b)/(c) guide with the earlier mix 7, 12, and 26 numbers beside the new ones.

**Architecture:** Per-pod CPU limits live in the both-off YAML so the runner and `service_capacity.json` see them. Replica counts do not: `restore_constraints` scales any `method: replicas` entry back to 1 at the end of each hold. Frontend and catalog are HPA-managed, so they are pinned with `minReplicas = maxReplicas`. The other extra replicas are a one-time `kubectl scale` done before the first hold and left in place until restore. CPU is patched before those replicas are added, because the paper table at these replica counts does not fit the worker.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_abc.py`, kubectl over `ssh topfull-master`.

## Global Constraints

- Mix order is fixed: mix 7, mix 12, mix 26, then the new mix. Counts are getproduct / postcheckout / getcart / postcart / emptycart.
- Slots: `baseline_no_topfull_sustained_overload_run35` (380/100/270/20/20), `run36` (100/150/100/100/5), `run37` (325/100/100/100/5), `run38` (250/150/250/50/50). Do not overwrite run7, run12, run26, run31, run33, or run34.
- Each hold is 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`.
- Cool-off is 360 s after the pin is Ready and before run35, then again after run35, run36, and run37. No cool-off after run38.
- Replica table, millicores per pod, request equals limit: frontend 1150 × 4, checkoutservice 800 × 2, recommendationservice 800 × 3, productcatalogservice 600 × 1, cartservice 600 × 2, currencyservice 650 × 1, shippingservice 400 × 1, adservice 600 × 1, paymentservice 150 × 2, emailservice 150 × 2, redis-cart 500 × 1. Deployment total is 13150 m, under the paper four-frontend ceiling of 13360 m.
- `redis-cart` container name is `redis`. Every other container is `server`. Frontend is not a `scale_constraints` entry (1150 m is already the paper limit).
- `paper_cpu_reconcile: false` on all four launches. Restore paper CPU only after the extra replicas are back at 1.
- Leave replica counts out of `scale_constraints`. Pin them once in Task 2.
- Sidecar: start at `sidecar.istio.io/proxyCPU=100m` with `proxyCPULimit` absent. If any pod stays Pending, set `proxyCPU=70m` and no limit on all 11 Deployments. 20 × 100 m sidecars + 13150 m app + ~1250 m system is about 16400 m, ~430 m over the ~15970 m total that scheduled on the 5-frontend pin. 20 × 70 m brings that sum to 15800 m. A limit on the sidecar is what collapsed latency on earlier holds; a lower request is scheduling only.
- SSH host aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). If SSH fails, refresh `HostName` from [CONNECT-VMS.md](../../../Guides%20and%20Info/CONNECT-VMS.md) before continuing.
- If a hold fails its gate, do not launch the next mix. Restore the cluster, write the guide for the holds that pulled, then still commit, push, and stop the VMs.
- (a) A high sample is `(Δ5xx + Δresets) / Δtotal > 0.20`. A disable is a streak of at least 30. Frontend and redis-cart are reported and are not controlled. Definition: [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md). Do not edit that file.
- (b) Detector bar is `overloaded=1` on at least half of that service's `topfull_detect.csv` rows. Layer A threshold stays at the 10000 passthrough sentinel.
- (c) Retry volume is the sum of positive Envoy `retry` increments on each caller→target edge.
- Comparison folders, already on disk: mix 7 is run7 and run31; mix 12 is run12 and run34; mix 26 is run26 and run33. The new mix has no earlier hold.

---

### Task 1: Lock the Replica table on the both-off YAML

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Consumes: `paper_cpu_reconcile: false` already supported by `run_scenario.paper_cpu_reconcile_enabled`.
- Produces: YAML at run35 / mix 7 with the ten backend `cpu_limit_millicores` entries. Later holds change only `run_number`, `log_folder`, `description`, and `locust.user_counts`.

- [ ] **Step 1: Replace the YAML**

```yaml
# Both-off S2. run35–run38 are the Replica-table series.
# paper_cpu_reconcile stays false until restore.
# Replica counts are pinned with kubectl, not scale_constraints:
# a replicas entry is scaled back to 1 at the end of every hold.
# Frontend stays at its paper 1150m and is not listed here.

scenario_id: 2
scenario_name: sustained_overload
condition: baseline
run_number: 35
description: >
  Both controllers off. Replica CPU table, replicas pinned.
  This slot is mix 7: 380/100/270/20/20.

duration_seconds: 600

locust:
  user_counts:
    getproduct:   380
    postcheckout: 100
    getcart:      270
    postcart:     20
    emptycart:    20
  spawn_rate: 50
  scripts:
    - online_boutique_create_v2.sh

scale_constraints:
  - {deployment: checkoutservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: recommendationservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: productcatalogservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: cartservice,           namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: currencyservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 650}
  - {deployment: shippingservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 400}
  - {deployment: adservice,             namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: paymentservice,        namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 150}
  - {deployment: emailservice,          namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 150}
  - {deployment: redis-cart,            namespace: default, container: redis,  method: cpu_limit, cpu_limit_millicores: 500}

paper_cpu_reconcile: false

retries:
  attempts_on: 3
  attempts_off: 0
  per_try_timeout_ms: 500

topfull_rl:
  enabled: false

retryguard:
  enabled: false
  rejection_threshold: 0.20
  sample_interval_seconds: 1
  interval_samples: 30

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

log_folder: baseline_no_topfull_sustained_overload_run35

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

- [ ] **Step 2: Check the budget**

```powershell
python -c @"
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('experiments/configs/scenario_2_baseline_no_topfull.yaml').read_text(encoding='utf-8'))
assert cfg['paper_cpu_reconcile'] is False
assert cfg['run_number'] == 35
assert cfg['topfull_rl']['enabled'] is False
assert cfg['retryguard']['enabled'] is False
by = {c['deployment']: c['cpu_limit_millicores'] for c in cfg['scale_constraints']}
assert 'frontend' not in by
reps = {'frontend':4,'checkoutservice':2,'recommendationservice':3,'productcatalogservice':1,'cartservice':2,'currencyservice':1,'shippingservice':1,'adservice':1,'paymentservice':2,'emailservice':2,'redis-cart':1}
millis = {'frontend':1150, **by}
assert sum(millis[k]*reps[k] for k in reps) == 13150
print('yaml ok', cfg['log_folder'])
"@
```

Expected: `yaml ok baseline_no_topfull_sustained_overload_run35`.

---

### Task 2: Apply CPU, then pin replicas

**Files:**
- None in the repo. Live cluster only.

**Interfaces:**
- Consumes: the millicore table in Task 1. Cluster is on paper CPU with frontend HPA min 1 / max 4 and catalog HPA max 2 (the run30–34 restore).
- Produces: live CPU equal to the Replica table, replica counts equal to that table, zero Pending pods. Run35 has not started.

- [ ] **Step 1: Confirm the cluster, then patch backend CPU while every backend is still 1 replica**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get hpa -n default"
@'
set -e
patch_cpu() {
  dep="$1"; container="$2"; cpu="$3"
  kubectl patch deployment "$dep" -n default --type strategic -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"$container\",\"resources\":{\"limits\":{\"cpu\":\"${cpu}m\"},\"requests\":{\"cpu\":\"${cpu}m\"}}}]}}}}"
  kubectl rollout status "deployment/$dep" -n default --timeout=180s
}
patch_cpu checkoutservice server 800
patch_cpu recommendationservice server 800
patch_cpu productcatalogservice server 600
patch_cpu cartservice server 600
patch_cpu currencyservice server 650
patch_cpu shippingservice server 400
patch_cpu adservice server 600
patch_cpu paymentservice server 150
patch_cpu emailservice server 150
patch_cpu redis-cart redis 500
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: each rollout completes. Frontend is not patched.

- [ ] **Step 2: Pin HPAs and scale the five deployments**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}"
kubectl scale deployment checkoutservice --replicas=2 -n default
kubectl scale deployment recommendationservice --replicas=3 -n default
kubectl scale deployment cartservice --replicas=2 -n default
kubectl scale deployment paymentservice --replicas=2 -n default
kubectl scale deployment emailservice --replicas=2 -n default
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

- [ ] **Step 3: If any pod is Pending, drop the sidecar request to 70m with no limit**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get pods -n default --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide"
```

When that list is empty, leave sidecars at 100 m. When it is not, run:

```powershell
@'
set -e
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"70m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

- [ ] **Step 4: Wait until ready counts match the table**

```powershell
@'
set -e
for spec in frontend:4 checkoutservice:2 recommendationservice:3 productcatalogservice:1 cartservice:2 currencyservice:1 shippingservice:1 adservice:1 paymentservice:2 emailservice:2 redis-cart:1; do
  dep="${spec%%:*}"; want="${spec##*:}"
  kubectl rollout status "deployment/$dep" -n default --timeout=180s
  got=$(kubectl get deploy "$dep" -n default -o jsonpath="{.status.readyReplicas}")
  echo "$dep ready=$got want=$want"
  test "$got" = "$want"
done
pending=$(kubectl get pods -n default --field-selector=status.phase=Pending --no-headers | wc -l)
echo "pending=$pending"
test "$pending" = "0"
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: every `ready=` line matches `want=`, and `pending=0`.

- [ ] **Step 5: Cool off 360 s**

```powershell
Start-Sleep -Seconds 360
```

---

### Task 3: Four holds, run35 through run38

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (counts and slot only, between holds)
- Pulls into: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run35/` through `run38/`

**Interfaces:**
- Consumes: the pinned cluster from Task 2.
- Produces: four pulled folders that pass the gate. The cluster stays pinned between holds.

Do the steps below once per row. On a gate failure, stop this task and go to Task 5.

| Slot | Mix | getproduct | postcheckout | getcart | postcart | emptycart | Cool-off after |
|---|---|---:|---:|---:|---:|---:|---|
| run35 | 7 | 380 | 100 | 270 | 20 | 20 | 360 s |
| run36 | 12 | 100 | 150 | 100 | 100 | 5 | 360 s |
| run37 | 26 | 325 | 100 | 100 | 100 | 5 | 360 s |
| run38 | new | 250 | 150 | 250 | 50 | 50 | none |

- [ ] **Step 1: Point the YAML at this row**

Set `run_number`, `log_folder: baseline_no_topfull_sustained_overload_runNN`, the description, and `locust.user_counts` from the row. Leave `scale_constraints`, `paper_cpu_reconcile`, and `spawn_rate` alone.

- [ ] **Step 2: Clear stale scripts and launch**

`run_scenario.py` blocks for about 15 minutes. Wait at least 20 minutes.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected log lines: `paper_cpu_reconcile is false`, CPU `already at` skips, `TopFull RL: OFF`, `RetryGuard: OFF`, this row's user counts.

- [ ] **Step 3: Pull and gate**

Replace `run35` with this row's slot.

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python -c @"
import csv, json
from pathlib import Path
p = Path(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run35')
cap = json.loads((p/'service_capacity.json').read_text(encoding='utf-8'))
expect = {'frontend':1150,'checkoutservice':800,'recommendationservice':800,'productcatalogservice':600,'cartservice':600,'currencyservice':650,'shippingservice':400,'adservice':600,'paymentservice':150,'emailservice':150,'redis-cart':500}
reps_want = {'frontend':4,'checkoutservice':2,'recommendationservice':3,'productcatalogservice':1,'cartservice':2,'currencyservice':1,'shippingservice':1,'adservice':1,'paymentservice':2,'emailservice':2,'redis-cart':1}
for name, millis in expect.items():
    assert cap[name]['cpu_limit_millicores']==millis, (name, cap[name])
seen = {name:set() for name in reps_want}
with (p/'resource_usage.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['service'] in seen:
            seen[row['service']].add(int(float(row['replica_count'])))
for name, want in reps_want.items():
    assert seen[name]=={want}, (name, seen[name])
need = ['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','topfull_throttle.csv','total.csv']
missing = [n for n in need if not (p/n).exists()]
assert not missing, missing
rows = sum(1 for _ in (p/'total.csv').open(encoding='utf-8')) - 1
assert rows >= 500, rows
print('capacity ok', 'locust rows', rows)
"@
```

Expected: `capacity ok` and locust rows at least 500.

- [ ] **Step 4: Cool off when the row says so**

```powershell
Start-Sleep -Seconds 360
```

Skip this step after run38.

---

### Task 4: Write the all-service (a)/(b)/(c) guide

**Files:**
- Create: `Guides and Info/2026-09-27-s2-replica-cpu-runs-35-38.md`
- Modify: `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md` (the Replica sentence that says it has no holds yet)
- Modify: `AGENTS.md` (§4 done bullet and the both-off next-free slot)

**Interfaces:**
- Consumes: `python experiments/s2_both_off_abc.py <run_dir> ...` and the pulled folders. The reading doc is the definition of (a)/(b)/(c). Leave `Guides and Info/2026-09-24-s2-both-off-abc-reading.md` unchanged.

- [ ] **Step 1: Score the four new folders and the six earlier ones**

```powershell
python experiments/s2_both_off_abc.py `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run35 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run36 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run37 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run38 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run7 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run31 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run12 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run34 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run26 `
  experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run33
```

- [ ] **Step 2: Write the guide from that output**

`Guides and Info/2026-09-27-s2-replica-cpu-runs-35-38.md`. Setup paragraph: 600 s, both controllers off, `spawn_rate` 50, Replica table, replicas pinned at the table counts, sidecar request actually used (100 m or 70 m) with no CPU limit, 360 s cool-off before run35 and between holds. Link the reading doc and [2026-09-26-s2-cpu-limits-for-spread.md](../../../Guides%20and%20Info/2026-09-26-s2-cpu-limits-for-spread.md).

Three tables, rows = all 11 services. (a) cells are `streak / high`, bold when streak ≥ 30 on a controlled service. (b) cells are `hot/ticks (share)`, bold when share ≥ 0.5. (c) is the retry-edge list per run, largest edge first, plus one column of retry-by-target if the scorer printed it. Columns:

| Mix | This series | Agreed-table replay | Earlier both-off |
|---|---|---|---|
| 7 (380/100/270/20/20) | run35 | run31 | run7 |
| 12 (100/150/100/100/5) | run36 | run34 | run12 |
| 26 (325/100/100/100/5) | run37 | run33 | run26 |
| new (250/150/250/50/50) | run38 | — | — |

State Layer A admitting rows for run35–run38. One sentence per mix: how many controlled services cleared streak 30, and how many cleared an overloaded share of 0.5, next to the same two counts on that mix's earlier folders.

In `2026-09-26-s2-cpu-limits-for-spread.md`, change the Replica sentence so it names runs 35–38 instead of "no holds yet".

In `AGENTS.md` §4, add a done bullet for the holds that pulled (Replica table, pinned replica counts, 360 s cool-offs, the new guide). When all four pulled, set the both-off next-free slot to **run39**. When a hold was skipped, set it to that hold's slot.

---

### Task 5: Restore paper CPU, replicas, HPA, and the YAML

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Consumes: `run_scenario.reconcile_paper_cpu_limits`.
- Produces: backends at 1 replica, frontend HPA min 1 / max 4, catalog HPA min 1 / max 2, sidecar `proxyCPU=100m` and no `proxyCPULimit`, paper CPU, YAML at run39 with `scale_constraints: []` and no `paper_cpu_reconcile`.

Do this even when a hold failed.

- [ ] **Step 1: Scale the extra replicas down before paper CPU**

Paper CPU at 3 recommendations replicas does not fit. Scale down first.

```powershell
@'
set -e
kubectl scale deployment checkoutservice --replicas=1 -n default
kubectl scale deployment recommendationservice --replicas=1 -n default
kubectl scale deployment cartservice --replicas=1 -n default
kubectl scale deployment paymentservice --replicas=1 -n default
kubectl scale deployment emailservice --replicas=1 -n default
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":2}}"
for dep in checkoutservice recommendationservice cartservice paymentservice emailservice productcatalogservice frontend; do
  kubectl rollout status "deployment/$dep" -n default --timeout=180s
done
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

- [ ] **Step 2: Restore paper CPU and the sidecar request**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario; run_scenario.reconcile_paper_cpu_limits({'infra':{'master_ssh_host':'topfull-master'}}, wait=True)"
@'
set -e
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,REPLICAS:.status.readyReplicas,CPU:.spec.template.spec.containers[0].resources.limits.cpu
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: checkout, recommendations, cart, payment, and email ready at 1. Limits back on the paper table (checkout 615m, recommendations 1150m, catalog 1535m, cart 1920m, currency 770m, shipping 770m, ad 1150m, payment 155m, email 155m, redis-cart 540m, frontend 1150m).

- [ ] **Step 3: Point the YAML at the next free slot**

When run35–run38 all passed: `run_number: 39`, `log_folder: baseline_no_topfull_sustained_overload_run39`. When a hold failed the gate: `run_number` and `log_folder` of that hold. Either way, `scale_constraints: []`, delete `paper_cpu_reconcile`, and say the slot is unused. Leave the locust counts as whatever mix was last written.

---

### Task 6: Commit, push, stop the VMs

**Files:**
- Everything this plan changed, plus the four pulled run folders.

- [ ] **Step 1: Three commits on the current branch**

Follow the repo commit protocol (status, diff, log, then commit). Do not amend. Do not commit `.env` or keys.

1. `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run35/` through `run38/`. Message: `Add both-off S2 runs 35-38 on the replica CPU table.`
2. `Guides and Info/2026-09-27-s2-replica-cpu-runs-35-38.md`, the Replica-sentence edit in `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md`, and the `AGENTS.md` §4 bullet that records those runs and the next free slot. Message: `Record (a)/(b)/(c) for replica-table runs 35-38.`
3. `experiments/configs/scenario_2_baseline_no_topfull.yaml` after Task 5 has cleared `scale_constraints` and pointed it at the unused slot, plus this plan if it is still untracked. Message: `Point the both-off YAML at the next free slot.`

- [ ] **Step 2: Push**

```powershell
git push -u origin HEAD
git status
```

Expected: the branch is in sync with origin. Do not force-push.

- [ ] **Step 3: Stop the three VMs**

Only after the push succeeds.

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --project=networks-workshop --zone=us-central1-a
```

Expected: all three `TERMINATED`.
