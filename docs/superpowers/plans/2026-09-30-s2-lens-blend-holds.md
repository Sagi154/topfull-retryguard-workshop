# S2 Lens-Blend Holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the both-off holds in [2026-09-30-s2-lens-blend-handoff.md](../../../Guides%20and%20Info/2026-09-30-s2-lens-blend-handoff.md) and record whether one CPU table plus one user mix shows a recommendations streak, a checkout streak, and a hot email or payment.

**Architecture:** One YAML, `experiments/configs/scenario_2_baseline_no_topfull.yaml`, drives every hold through `experiments/run_scenario.py`. CPU limits are `scale_constraints` with `paper_cpu_reconcile: false`. Replica counts are HPA pins, never `scale_constraints`. run80 and run81 share the Paper pin. run82 reshapes to Hybrid. run83 and run84 exist only if the decision rule in Task 5 says so. Scoring is `experiments/s2_both_off_canon.py`.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_canon.py`, kubectl over `ssh topfull-master`, `gcloud compute`.

## Global Constraints

- Spec: [2026-09-30-s2-lens-blend-handoff.md](../../../Guides%20and%20Info/2026-09-30-s2-lens-blend-handoff.md). Counts are getproduct / postcheckout / getcart / postcart / emptycart. Every hold is 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`, script `online_boutique_create_v2.sh`.
- Slots start at run80. Do not overwrite any folder `baseline_no_topfull_sustained_overload_run1` through `run79`, including run6, run10, run11, run34, and run69.
- Pass bar, from `s2_canon_*.json` field `svc`: recommendationservice `streak >= 10` and `ov >= 10`; checkoutservice `streak >= 10` and `ov >= 10`; emailservice or paymentservice `ov >= 10` (a leaf `streak >= 10` is better, not required). A hold that clears all three is a **blend**. Two cleared and the missing one at `streak >= 5` or `ov >= 5` is a **near-miss**. Anything else is a **miss**. Retry deltas, goodput, and max utilization do not pass or fail a hold.
- Configured users sum to 600, 555, or 600 on the first three holds. A Task 5 tweak may raise one tag by 50. The sum must stay ≤ 700.
- `paper_cpu_reconcile: false` on every hold. `proxyCPULimit` stays absent. `redis-cart` container is `redis`; every other container is `server`. Frontend is not a `scale_constraints` entry (paper 1150 m). Recommendations is not a `scale_constraints` entry (paper 1150 m).
- Deployment totals (limit × replicas): Paper-C1 (run80) is **11,655 m** and Paper-C3 (run81) is **11,620 m**, with catalog and cart at 800 m (paper 1535 and 1920). Hybrid-C2 (run82) is **10,050 m**. All three are under the 13,360 m ceiling.
- Sidecar request: **100 m** on every hold, annotation `sidecar.istio.io/proxyCPU` on all 11 Deployments, `proxyCPULimit` removed. Do not drop it to 90 m.
- Cool-off is 360 s after the pin is Ready and before the first hold of a table, and 360 s between holds. No cool-off after the last hold. Do not call `Start-Sleep`. Call the AwaitShell tool with no `shell_id` and `block_until_ms: 360000`.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Before every launch: `ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"`. If a remote command fails with `\r`, reissue it.
- Do not edit [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md). Leave the VMs running until Task 6 Step 6, which commits, pushes, and stops them.

**Gate.** After each pull, from the repo root, with `N` set to the slot:

```powershell
python -c "import json,os,sys; n=int(sys.argv[1]); p='experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run%d'%n; cap=json.load(open(p+'/service_capacity.json')); rows=sum(1 for _ in open(p+'/total.csv'))-1; need=['service_inbound.csv','service_edges.csv','topfull_detect.csv','resource_usage.csv','total.csv']; missing=[f for f in need if not os.path.exists(p+'/'+f)]; print('rows',rows,'missing',missing); sys.exit(1 if missing or rows<500 else 0)" N
python experiments/s2_both_off_canon.py N N
python -c "import json,sys; n=sys.argv[1]; o=json.load(open('s2_canon_%s_%s.json'%(n,n)))[n]; q=o['q']; s=o['svc']; print('span',q['span'],'gap2_pct',q['gap2_pct']); print('frontend',s['frontend'].get('rmode'),s['frontend'].get('rzero'));
[print(k,s[k].get('rmode'),s[k].get('rzero'),s[k].get('streak'),s[k].get('ov')) for k in s]; bad=q.get('gap2_pct',100)>10 or not (480<=q.get('span',0)<=900) or s['frontend'].get('rmode')!=4; backends=[k for k in s if k not in ('frontend','__master_node__') and s[k].get('rmode') not in (1,None)]; print('backend_mode_off',backends); sys.exit(1 if bad or backends else 0)" N
```

Expected: exit 0, `gap2_pct` ≤ 10, `span` between 480 and 900, frontend `rmode` 4, every backend `rmode` 1, `total.csv` rows ≥ 500, no missing collector file. A backend `rzero` above 0 with `rmode` still 1 is an overload symptom: print it, keep the folder, continue. `service_capacity.json` millicores are checked per task against that task's table.

A failed Locust-row, collector, span, or sampling gate: keep the folder, do not relaunch that slot, stop the series, and write up what landed (Task 6). A frontend `rmode` other than 4 is the same. `duplicate session: envoyretry`: `ssh topfull-master "tmux kill-session -t envoyretry"`, then relaunch the same slot once.

## File map

| File | Role |
|---|---|
| `experiments/configs/scenario_2_baseline_no_topfull.yaml` | The only run config. Holds change `run_number`, `log_folder`, `description`, `locust.user_counts`, and `scale_constraints`. |
| `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md` | Gains the Paper-C1, Paper-C3, and Hybrid-C2 tables before the first hold. |
| `experiments/s2_both_off_canon.py` | Scorer. `python experiments/s2_both_off_canon.py LO HI` writes `s2_canon_LO_HI.json` in the repo root. |
| `experiments/test_topfull_cpu_quotas.py` | `TestBothOffYamlRestored` is updated only in Task 6, to the unused next slot. |
| `Guides and Info/2026-09-30-s2-lens-blend-results.md` | Created in Task 6. |
| `AGENTS.md` | One §4 bullet and the both-off next-free line, in Task 6. |

---

### Task 1: Paper pin and the run80 YAML

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md`

**Interfaces:**
- Produces: cluster at paper CPU, frontend HPA min=max=4, catalog HPA min=max=1, sidecar request 100 m, YAML at run80 with checkout 800, catalog 800, cart 800, and email 120. Task 2 launches that YAML unchanged.

- [ ] **Step 1: Start any stopped VM, refresh SSH, confirm the API**

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: three nodes Ready. If SSH times out, set `HostName` in `~/.ssh/config` from the `gcloud` natIP column, then retry. Aliases only.

- [ ] **Step 2: Confirm run80–run84 are free**

```powershell
ssh topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run8[0-4]$' || echo none"
```

Expected: `none`. If a name is listed, do not reuse it. Shift every slot in this plan up past the highest existing run and edit the handoff's slot table to match before continuing.

- [ ] **Step 3: Reconcile paper CPU, pin frontend at 4 and catalog at 1, sidecar 100 m**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario; run_scenario.reconcile_paper_cpu_limits({'infra':{'master_ssh_host':'topfull-master'}}, wait=True)"
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}"
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
kubectl get pods -n default --no-headers
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: frontend 4 pods at 2/2 Running, every other Boutique pod 2/2 Running, none Pending. The run80 limits are applied at launch, so a Pending pod here is still on paper CPU. Continue to Step 4; recheck pending after the first launch applies catalog 800 and cart 800. If a pod is still Pending then, stop the series and capture `kubectl describe pod`. Do not lower the sidecar below 100 m.

- [ ] **Step 4: Write the run80 header and the Paper overrides**

Replace `run_number`, `description`, `locust.user_counts`, `scale_constraints`, and `log_folder`. Add `paper_cpu_reconcile: false`. Leave `duration_seconds`, `retries`, `topfull_rl`, `retryguard`, the three collectors, and `infra` as they are.

```yaml
run_number: 80
description: >
  Both controllers off. Paper CPU except checkout 800, catalog 800,
  cart 800, and email 120. Frontend pinned at 4. C1: 325/80/100/90/5.

locust:
  user_counts:
    getproduct:   325
    postcheckout: 80
    getcart:      100
    postcart:     90
    emptycart:    5
  spawn_rate: 50

scale_constraints:
  - {deployment: checkoutservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: productcatalogservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: cartservice,           namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: emailservice,          namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 120}

paper_cpu_reconcile: false
log_folder: baseline_no_topfull_sustained_overload_run80
```

- [ ] **Step 5: Append the three tables to the CPU-limits doc**

Add a section "Lens blend (run80–run82)" to `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md` with this table. Per-pod millicores. Frontends are × 4. Every other replica count is 1.

| Service | Paper-C1 run80 | Paper-C3 run81 | Hybrid-C2 run82 |
|---|---:|---:|---:|
| frontend | 1150 × 4 | 1150 × 4 | 1150 × 4 |
| checkoutservice | 800 | 800 | 800 |
| recommendationservice | 1150 | 1150 | 1150 |
| productcatalogservice | 800 | 800 | 600 |
| cartservice | 800 | 800 | 600 |
| currencyservice | 770 | 770 | 650 |
| shippingservice | 770 | 770 | 400 |
| adservice | 1150 | 1150 | 600 |
| paymentservice | 155 | 120 | 200 |
| emailservice | 120 | 120 | 150 |
| redis-cart | 540 | 540 | 300 |
| **Deployment total** | **11655** | **11620** | **10050** |

Note in that section that catalog and cart are 800 m on C1 and C3 because paper peaks on run6 and run7 were 613 m and 601 m, and that all three totals are under 13,360 m so the sidecar stays at 100 m.

- [ ] **Step 6: Cool off, then commit**

Call AwaitShell with `block_until_ms: 360000`.

```powershell
git add experiments/configs/scenario_2_baseline_no_topfull.yaml "Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md"
git commit -m "chore: S2 lens-blend Paper-C1 YAML at run80"
```

### Task 2: C1 hold (run80)

**Files:**
- Modify: none before launch. The YAML from Task 1 is the hold.

**Interfaces:**
- Consumes: the run80 YAML and the Paper pin.
- Produces: `experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run80/` and `s2_canon_80_80.json`.

- [ ] **Step 1: Launch**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Expected: the process exits after the 600 s hold. Wall clock is about 11–12 minutes. If a pod is Pending `Insufficient cpu` before Locust starts, stop the series. Do not lower the sidecar below 100 m and do not reuse run80.

- [ ] **Step 2: Pull and gate**

```powershell
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Run the Global Constraints gate with `N = 80`. Then confirm capacity:

```powershell
python -c "import json; c=json.load(open(r'experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run80/service_capacity.json')); exp={'frontend':1150,'checkoutservice':800,'recommendationservice':1150,'productcatalogservice':800,'cartservice':800,'currencyservice':770,'shippingservice':770,'adservice':1150,'paymentservice':155,'emailservice':120,'redis-cart':540}; bad={k:c[k]['cpu_limit_millicores'] for k,v in exp.items() if c[k]['cpu_limit_millicores']!=v}; print(bad or 'capacity ok')"
```

Expected: `capacity ok`. Frontend `replica_count` 4, every other service 1.

- [ ] **Step 3: Read the three pass-bar rows**

```powershell
python -c "import json; o=json.load(open('s2_canon_80_80.json'))['80']['svc'];
[print(k, o[k].get('streak'), o[k].get('ov')) for k in ('recommendationservice','checkoutservice','emailservice','paymentservice')]"
```

Write the four numbers into the handoff under a "Landed" note for run80. Do not decide the series here.

- [ ] **Step 4: Commit**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run80
git commit -m "data: S2 lens-blend C1 run80"
```

### Task 3: C3 hold (run81)

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (payment limit, run number, counts, description)

**Interfaces:**
- Consumes: the Paper pin from Task 1. No reshape.
- Produces: the run81 folder and `s2_canon_81_81.json`.

- [ ] **Step 1: Point the YAML at run81**

`run_number: 81`, `log_folder: baseline_no_topfull_sustained_overload_run81`, description names Paper-C3 and the mix 250/100/100/100/5. Counts:

```yaml
    getproduct:   250
    postcheckout: 100
    getcart:      100
    postcart:     100
    emptycart:    5
```

Add one constraint. Leave checkout, catalog, and cart at 800 and email at 120. `paper_cpu_reconcile` stays false.

```yaml
  - {deployment: paymentservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 120}
```

- [ ] **Step 2: Cool off 360 s**

AwaitShell, no `shell_id`, `block_until_ms: 360000`.

- [ ] **Step 3: Launch, pull, gate**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Run the Global Constraints gate with `N = 81`. Capacity must show `paymentservice` 120, `emailservice` 120, `checkoutservice` 800, `productcatalogservice` 800, `cartservice` 800, and the other Paper millicores from the Task 1 table.

- [ ] **Step 4: Print the pass-bar rows and commit**

```powershell
python -c "import json; o=json.load(open('s2_canon_81_81.json'))['81']['svc'];
[print(k, o[k].get('streak'), o[k].get('ov')) for k in ('recommendationservice','checkoutservice','emailservice','paymentservice')]"
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run81 experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 lens-blend C3 run81"
```

### Task 4: Hybrid reshape and C2 (run82)

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`

**Interfaces:**
- Consumes: run80 and run81 already pulled.
- Produces: the run82 folder and `s2_canon_82_82.json`. Frontend stays at 4.

- [ ] **Step 1: Reconcile paper, then set the Hybrid limits and sidecar 100 m**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario; run_scenario.reconcile_paper_cpu_limits({'infra':{'master_ssh_host':'topfull-master'}}, wait=True)"
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":4,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}"
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
kubectl get pods -n default --field-selector=status.phase=Pending --no-headers
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: no Pending pods. Hybrid-C2 is 10,050 m, so a Pending pod here is not the ceiling problem from Task 1. Capture `kubectl describe pod` and stop the series if one stays Pending. Do not drop the frontend replica.

- [ ] **Step 2: Replace `scale_constraints` and point at run82**

```yaml
run_number: 82
description: >
  Both controllers off. Hybrid-C2. Checkout 800 x 1, email 150,
  recommendations 1150 x 1, frontend pinned at 4. Mix 170/210/200/10/10.

locust:
  user_counts:
    getproduct:   170
    postcheckout: 210
    getcart:      200
    postcart:     10
    emptycart:    10
  spawn_rate: 50

scale_constraints:
  - {deployment: checkoutservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: productcatalogservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: cartservice,           namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: currencyservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 650}
  - {deployment: shippingservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 400}
  - {deployment: adservice,             namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: paymentservice,        namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 200}
  - {deployment: emailservice,          namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 150}
  - {deployment: redis-cart,            namespace: default, container: redis,  method: cpu_limit, cpu_limit_millicores: 300}

paper_cpu_reconcile: false
log_folder: baseline_no_topfull_sustained_overload_run82
```

Recommendations stays off this list so the paper reconcile leaves it at 1150.

- [ ] **Step 3: Cool off 360 s, launch, pull, gate**

AwaitShell `block_until_ms: 360000`. Then:

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
```

Gate with `N = 82`. Capacity must match the Hybrid-C2 column (frontend 1150 and replica_count 4, checkout 800 and replica_count 1, recommendations 1150, email 150, payment 200, catalog 600, cart 600, currency 650, shipping 400, ad 600, redis-cart 300).

- [ ] **Step 4: Commit**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run82 experiments/configs/scenario_2_baseline_no_topfull.yaml
git commit -m "data: S2 lens-blend C2 run82"
```

### Task 5: Decide run83 and run84

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` only if a further hold is launched

**Interfaces:**
- Consumes: `s2_canon_80_80.json`, `s2_canon_81_81.json`, `s2_canon_82_82.json`.
- Produces: either a stop, or one or two more pulled folders. The verdict string is what Task 6 quotes.

- [ ] **Step 1: Classify the three holds**

```powershell
python -c "import json
def load(n):
    return json.load(open('s2_canon_%d_%d.json'%(n,n)))[str(n)]['svc']
def cleared_pair(s):
    return s.get('streak',0)>=10 and s.get('ov',0)>=10
def close(s):
    return s.get('streak',0)>=5 or s.get('ov',0)>=5
for n in (80,81,82):
    s=load(n)
    rec=cleared_pair(s['recommendationservice']); co=cleared_pair(s['checkoutservice'])
    leaf=s['emailservice'].get('ov',0)>=10 or s['paymentservice'].get('ov',0)>=10
    missing=[]
    if not rec: missing.append(('recommendationservice',s['recommendationservice']))
    if not co: missing.append(('checkoutservice',s['checkoutservice']))
    if not leaf: missing.append(('leaf',{'streak':max(s['emailservice'].get('streak',0),s['paymentservice'].get('streak',0)),'ov':max(s['emailservice'].get('ov',0),s['paymentservice'].get('ov',0))}))
    nclear=(rec+co+leaf)
    kind='blend' if nclear==3 else ('near' if nclear==2 and all(close(x) for _,x in missing) else 'miss')
    leaf_ov=s['emailservice'].get('ov',0)+s['paymentservice'].get('ov',0)
    print(n,kind,'leaf_ov',leaf_ov,'rec',s['recommendationservice'].get('streak'),s['recommendationservice'].get('ov'),'co',s['checkoutservice'].get('streak'),s['checkoutservice'].get('ov'),'email',s['emailservice'].get('streak'),s['emailservice'].get('ov'),'pay',s['paymentservice'].get('streak'),s['paymentservice'].get('ov'))
"
```

- [ ] **Step 2: Apply one branch**

**Branch blend, exactly one.** Replay that hold as run83 and again as run84. Copy its `scale_constraints`, `user_counts`, sidecar, and HPA pin. Change only `run_number`, `log_folder`, and a description that says `replay of runNN`. Cool off 360 s before each. Launch, pull, and gate with the Global Constraints script. A replay that is not itself a blend means the blend is not stable; say that in Task 6 and do not launch a third replay.

**Branch blend, two or three.** run83 replays the blend with the larger `leaf_ov` (email `ov` + payment `ov`). run84 replays the other blend with the next-larger `leaf_ov`. Same launch rule as the single-blend branch. If run84's source was not launched because only two blended, stop after run83 only when the second blend does not exist; otherwise run both replays.

**Branch no blend, one or more near-misses.** run83 is one tweak of the near-miss with the larger `leaf_ov`. One knob, taken from the missing row only:

| Missing row | Change |
|---|---|
| recommendationservice | add 50 to `getproduct` (run80 becomes 375/80/100/90/5 sum 650; run81 becomes 300/100/100/100/5 sum 605; run82 becomes 220/210/200/10/10 sum 650) |
| checkoutservice | `checkoutservice` `cpu_limit_millicores` 800 → 700. Counts unchanged |
| leaf | `emailservice` 120 → 100 on run80 or run81, or 150 → 130 on run82. Do not go below 100 |

Keep every other limit and count. Description names the source run and the one knob. Cool off 360 s, launch, pull, gate.

run84 then replays whichever of run83 and the source near-miss classified as the better hold: a blend beats a near-miss, a near-miss beats a miss, and a tie goes to the larger `leaf_ov`. If run83 is a miss and the source is a near-miss, run84 replays the source. Cool off, launch, pull, gate.

**Branch all misses.** Do not launch run83 or run84.

- [ ] **Step 3: Commit any new folder**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run83
git commit -m "data: S2 lens-blend run83"
```

Repeat for run84 when that folder exists. Skip the commit when the branch launched nothing.

### Task 6: Restore, test, and the results note

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `experiments/test_topfull_cpu_quotas.py` (`TestBothOffYamlRestored`, the `run_number` and `log_folder` assertions)
- Create: `Guides and Info/2026-09-30-s2-lens-blend-results.md`
- Modify: `AGENTS.md` §4

**Interfaces:**
- Consumes: every folder this plan launched, plus the Task 5 verdict lines.

- [ ] **Step 1: Restore paper CPU, HPAs, and sidecar 100 m**

```powershell
python -c "import sys; sys.path.insert(0,'experiments'); import run_scenario; run_scenario.reconcile_paper_cpu_limits({'infra':{'master_ssh_host':'topfull-master'}}, wait=True)"
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":4}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":2}}"
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
kubectl get hpa,deploy -n default
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Expected: frontend HPA min 1 max 4, catalog HPA min 1 max 2, no `proxyCPULimit` annotation.

- [ ] **Step 2: Point the YAML at the next free slot**

`NEXT` is one past the last slot this plan launched (83 if the series stopped after run82, 84 if only run83 ran, 85 if run84 ran). Set `run_number: NEXT`, `log_folder: baseline_no_topfull_sustained_overload_runNEXT`, `scale_constraints: []`, and delete the `paper_cpu_reconcile` key. Description says the slot is unused. Leave the last hold's counts in place and say they are leftovers, not a scheduled hold.

In `TestBothOffYamlRestored.test_next_slot_is_paper_and_unused`, set the `run_number` assertion to `NEXT` and the `log_folder` assertion to `baseline_no_topfull_sustained_overload_runNEXT`.

```powershell
python -m pytest experiments/test_topfull_cpu_quotas.py::TestBothOffYamlRestored -q
```

Expected: pass.

- [ ] **Step 3: Write the results note**

Create `Guides and Info/2026-09-30-s2-lens-blend-results.md`. Sections, in order:

1. One paragraph: slots launched, sidecar request that scheduled (100 m unless a pod went Pending), VMs stopped at the end of this task.
2. Pass-bar table. One row per launched hold. Columns: slot, table, mix, sum, recommendations streak, recommendations ov, checkout streak, checkout ov, email streak, email ov, payment streak, payment ov, verdict (blend / near / miss). Numbers come from that hold's `s2_canon_N_N.json`. Add reference rows for run10, run11, and run69 with the streaks and overloaded ticks already printed in the ranking guide, labeled as reference, not as this series.
3. The Task 5 branch taken, in one sentence, and whether a replay of a blend also classified as a blend.
4. Sampling line per hold: `gap2_pct` and `span` from the canon JSON.

- [ ] **Step 4: Update AGENTS.md**

Add one §4 bullet: slots, each verdict, whether a blend survived a replay, the next free both-off slot, VMs **TERMINATED**. In the "Not done yet" next-free paragraph, replace the both-off slot `run80` with `NEXT`.

- [ ] **Step 5: Commit everything this series changed**

```powershell
git status
git add experiments/configs/scenario_2_baseline_no_topfull.yaml experiments/test_topfull_cpu_quotas.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run8* "Guides and Info/2026-09-30-s2-lens-blend-results.md" "Guides and Info/2026-09-30-s2-lens-blend-handoff.md" "Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md" "docs/superpowers/plans/2026-09-30-s2-lens-blend-holds.md" AGENTS.md s2_canon_8*_8*.json
git commit -m "docs: S2 lens-blend results, YAML restored"
```

Expected: one commit, or "nothing to commit" if every earlier task commit already included these files. Do not add secrets (`.env`, keys, credentials).

- [ ] **Step 6: Push, then stop the three VMs**

```powershell
git push -u origin HEAD
git status
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
gcloud compute instances list --project=networks-workshop --format="table(name,status)"
```

Expected: the branch is on the remote and not ahead of it. All three instances are `TERMINATED`.

---

## Self-review

- Coverage: the handoff's three first holds are Tasks 2–4 (run80 Paper-C1, run81 Paper-C3, run82 Hybrid-C2). The decision rule and the four tweaks are Task 5. Restore, the test, and the results note are Task 6. Retries are recorded by the canon scorer and are not in the classifier. Mix sums are 600, 555, and 600. Frozen μ is not read.
- Totals: Paper-C1 11,655 m and Paper-C3 11,620 m, with catalog and cart at 800 m. Hybrid-C2 is 10,050 m. Sidecar is 100 m on every hold.
- Cost: three holds at about 16 minutes each plus two cool-offs is about an hour before Task 5. Two replays add about 40 minutes.
- Open at execution time: whether run80 schedules (Task 1 Step 5 / Task 2 Step 1), and which Task 5 branch the three classifications select.
