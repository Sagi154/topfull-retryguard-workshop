# S2 Hybrid-1 Holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the six both-off holds in [2026-09-29-s2-hybrid1-candidates.md](../../../Guides%20and%20Info/2026-09-29-s2-hybrid1-candidates.md) and record whether checkout and recommendations were both hot.

**Architecture:** One YAML, `experiments/configs/scenario_2_baseline_no_topfull.yaml`, drives every hold. CPU limits are `scale_constraints`. Frontend is pinned with the HPA (`minReplicas = maxReplicas = 6`), not with `scale_constraints`. H3 is the only hold that changes a limit (checkout 800 → 1000). Scoring is `experiments/s2_both_off_abc.py`.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, `experiments/s2_both_off_abc.py`, kubectl over `ssh topfull-master`.

## Global Constraints

- Counts are getproduct / postcheckout / getcart / postcart / emptycart. Each hold is 600 s, `spawn_rate` 50, `topfull_rl.enabled: false`, `retryguard.enabled: false`, Istio `attempts: 3`, `per_try_timeout_ms: 500`.
- Slots: run74 H1 `300/300/200/10/10`, run75 H2 `250/350/150/10/10`, run76 H3 same mix as H2 with checkout 1000 m, run77 H4 `340/100/240/10/10`, run78 H5 `320/120/200/10/10`, run79 H6 `320/150/220/10/10`. Do not overwrite run73 or anything earlier.
- Hybrid-1, millicores per pod, request equals limit: frontend 1150 × 6, checkout 800 × 1 (1000 × 1 on H3 only), recommendations 1150 × 1, catalog 600, cart 600, currency 650, shipping 400, ad 600, payment 200, email 200, redis-cart 300. Totals 12,400 m and 12,600 m on H3. Both are under 13,360 m.
- `paper_cpu_reconcile: false`. Frontend is not a `scale_constraints` entry. `redis-cart` container is `redis`; every other container is `server`.
- Sidecar: `sidecar.istio.io/proxyCPU=100m` on all 11 Deployments, `proxyCPULimit` absent.
- Cool-off 360 s after the pin is Ready and before run74, then 360 s between holds. No cool-off after run79.
- Gate: `total.csv` rows ≥ 500, `service_capacity.json` checkout millicores match the hold (800, or 1000 on run76), frontend `replica_count` is 6 on every `resource_usage.csv` sample, collector files present (`service_inbound.csv`, `service_edges.csv`, `topfull_detect.csv`, `resource_usage.csv`). A leaf `replica_count` of 0 on a few samples is an overload symptom; keep the folder and continue.
- If a hold fails the Locust-row or collector gate, do not reuse that slot. Bump to the next free number, note it in the candidates doc, and continue the remaining holds. The series runs all six mixes.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Before every launch: `ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"`.
- Do not edit [2026-09-24-s2-both-off-abc-reading.md](../../../Guides%20and%20Info/2026-09-24-s2-both-off-abc-reading.md). Do not stop the VMs.

---

### Task 1: Pin Hybrid-1 and point the YAML at run74

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md` (append the Hybrid-1 table)

**Interfaces:**
- Produces: YAML at run74 with the ten backend limits below. Later holds change `run_number`, `log_folder`, `description`, `locust.user_counts`, and on run76 the checkout millicores.

- [ ] **Step 1: Start the VMs if they are stopped, refresh SSH, confirm the cluster**

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=networks-workshop
gcloud compute instances list --project=networks-workshop --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: three nodes Ready. If SSH times out, update `HostName` in `~/.ssh/config` from the `gcloud` list, then retry.

- [ ] **Step 2: Confirm run74–run79 do not exist**

```powershell
ssh topfull-master "ls /home/idozacharia/experiments/results | grep -E 'baseline_no_topfull_sustained_overload_run7[4-9]$' || echo none"
```

Expected: `none`. If a slot exists, shift the map up and edit the candidates doc before launching.

- [ ] **Step 3: Replace `scale_constraints` and the run74 header in the YAML**

```yaml
run_number: 74
description: >
  Both controllers off. Hybrid-1. Frontend pinned at 6.
  H1: 300/300/200/10/10.

locust:
  user_counts:
    getproduct:   300
    postcheckout: 300
    getcart:      200
    postcart:     10
    emptycart:    10
  spawn_rate: 50

scale_constraints:
  - {deployment: checkoutservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 800}
  - {deployment: recommendationservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 1150}
  - {deployment: productcatalogservice, namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: cartservice,           namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: currencyservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 650}
  - {deployment: shippingservice,       namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 400}
  - {deployment: adservice,             namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 600}
  - {deployment: paymentservice,        namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 200}
  - {deployment: emailservice,          namespace: default, container: server, method: cpu_limit, cpu_limit_millicores: 200}
  - {deployment: redis-cart,            namespace: default, container: redis,  method: cpu_limit, cpu_limit_millicores: 300}

paper_cpu_reconcile: false
log_folder: baseline_no_topfull_sustained_overload_run74
```

Leave `duration_seconds`, `retries`, `topfull_rl`, `retryguard`, the three collectors, and `infra` as they are.

- [ ] **Step 4: Append the Hybrid-1 table** (frontend 1150 × 6, checkout 800 × 1, recommendations 1150 × 1, the eight backends above, total 12,400 m; H3 checkout 1000 m, total 12,600 m) to `Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md`.

- [ ] **Step 5: Pin frontend at 6 and the sidecar at 100 m**

```powershell
@'
set -e
kubectl patch hpa frontend-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":6,\"maxReplicas\":6}}"
kubectl patch hpa productcatalogservice-hpa -n default --type merge -p "{\"spec\":{\"minReplicas\":1,\"maxReplicas\":1}}"
for dep in frontend checkoutservice recommendationservice productcatalogservice cartservice currencyservice shippingservice adservice paymentservice emailservice redis-cart; do
  kubectl patch deployment "$dep" -n default --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"sidecar.istio.io/proxyCPU\":\"100m\"}}}}}"
  kubectl patch deployment "$dep" -n default --type json -p "[{\"op\":\"remove\",\"path\":\"/spec/template/metadata/annotations/sidecar.istio.io~1proxyCPULimit\"}]" || true
done
'@ | ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master bash -s
```

Wait until frontend ready is 6/6 and no pod is Pending. Then cool off 360 s. If a pod stays Pending with `Insufficient cpu`, lower `sidecar.istio.io/proxyCPU` on all 11 Deployments to 90 m, and if still Pending to 70 m, until 6/6 is Ready. Record the request that scheduled in the candidates doc. Do not drop a frontend replica. Then cool off and continue.

- [ ] **Step 6: Commit**

```powershell
git add experiments/configs/scenario_2_baseline_no_topfull.yaml "Guides and Info/2026-09-26-s2-cpu-limits-for-spread.md"
git commit -m "chore: Hybrid-1 both-off YAML at run74"
```

### Task 2: Holds at checkout 800 m (run74, run75, run77, run78, run79)

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (only `run_number`, `log_folder`, `description`, `locust.user_counts` between holds)

**Interfaces:**
- Consumes: the run74 YAML and the pin from Task 1.
- Produces: five pulled folders. Checkout stays at 800 m.

- [ ] **Step 1: Launch, pull, and gate run74**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/pull_results.py experiments/configs/scenario_2_baseline_no_topfull.yaml
python experiments/s2_both_off_abc.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run74
```

Expected: the run finishes, the pull lands in `S2_sustained_overload/`, and the score prints. Check the gate in Global Constraints before the next hold.

- [ ] **Step 2: Repeat for the other four 800 m holds.** Cool off 360 s before each. Set counts, `run_number`, and `log_folder` to:

| Slot | getproduct | postcheckout | getcart | postcart | emptycart |
|---|---:|---:|---:|---:|---:|
| run75 | 250 | 350 | 150 | 10 | 10 |
| run77 | 340 | 100 | 240 | 10 | 10 |
| run78 | 320 | 120 | 200 | 10 | 10 |
| run79 | 320 | 150 | 220 | 10 | 10 |

run76 is not in this task. After run75, skip to run77. Checkout `cpu_limit_millicores` stays 800.

- [ ] **Step 3: Commit the five folders**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run74 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run75 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run77 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run78 experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run79
git commit -m "data: Hybrid-1 holds run74 run75 run77-run79"
```

### Task 3: H3, checkout at 1000 m (run76)

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml` (checkout millicores, run number, counts)

- [ ] **Step 1: Set checkout to 1000 and the H2 mix**

`cpu_limit_millicores: 1000` on `checkoutservice` only. `run_number: 76`, `log_folder: baseline_no_topfull_sustained_overload_run76`, counts 250 / 350 / 150 / 10 / 10.

- [ ] **Step 2: Cool off 360 s, clear `/tmp/rg_*.sh`, launch, pull, gate, score** with the same three commands as Task 2 Step 1, pointed at run76. `service_capacity.json` must show checkout at 1000 m.

- [ ] **Step 3: Commit**

```powershell
git add experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run76
git commit -m "data: Hybrid-1 H3 run76 checkout 1000m"
```

### Task 4: Restore, and write the six-line result

**Files:**
- Modify: `experiments/configs/scenario_2_baseline_no_topfull.yaml`
- Modify: `experiments/test_topfull_cpu_quotas.py` (`TestBothOffYamlRestored` log_folder assertion)
- Modify: `Guides and Info/2026-09-29-s2-hybrid1-candidates.md` (append a Results section)
- Modify: `AGENTS.md` (one status bullet, and the both-off next-free slot)

- [ ] **Step 1: Restore paper CPU, the HPAs, and the sidecar**

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

- [ ] **Step 2: Point the YAML at run80** with `scale_constraints: []` and no `paper_cpu_reconcile` key. Update `TestBothOffYamlRestored` to `baseline_no_topfull_sustained_overload_run80`.

```powershell
python -m pytest experiments/test_topfull_cpu_quotas.py::TestBothOffYamlRestored -q
```

Expected: pass.

- [ ] **Step 3: Append a Results section** to the candidates doc. One row per hold: checkout streak, recommendations streak, checkout overloaded share, recommendations overloaded share, largest retry edge. Say whether any hold had both checkout and recommendations at streak ≥ 30. Numbers come from `s2_both_off_abc.py` on the six folders. Add one AGENTS.md bullet naming run74–run79 and the next free slot run80.

- [ ] **Step 4: Commit**

```powershell
git add experiments/configs/scenario_2_baseline_no_topfull.yaml experiments/test_topfull_cpu_quotas.py "Guides and Info/2026-09-29-s2-hybrid1-candidates.md" AGENTS.md
git commit -m "docs: Hybrid-1 results, YAML restored at run80"
```
