# S2 Run 89 Four-Arm Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the run 89 user mix and Paper-C1 CPU table twice on each of the four controller arms, then commit, push, and stop the VMs.

**Architecture:** The four scenario YAMLs already hold the mix and the CPU table, each pointed at the next free slot. Launch them in arm order, pull after every hold, bump that YAML before its second launch, and cool off 360 s between holds. No controller code changes.

**Tech Stack:** `experiments/run_scenario.py`, `experiments/pull_results.py`, the Paper-C1 pin scripts, OpenSSH aliases, gcloud.

## Global Constraints

- Mix, every hold: getproduct 275 / postcheckout 90 / getcart 100 / postcart 90 / emptycart 5. `spawn_rate` 50. Duration 600 s.
- CPU table is Paper-C1, already in each YAML's `scale_constraints`. `paper_cpu_reconcile: false`. Per-pod millicores, request equals limit: frontend 1150 × 4, checkout 800 × 1, recommendations 1150 × 1, productcatalog 800 × 1, cart 800 × 1, currency 770 × 1, shipping 770 × 1, ad 1150 × 1, payment 155 × 1, email 120 × 1, redis-cart 540 × 1.
- Pin: frontend HPA min 4 / max 4, catalog HPA min 1 / max 1, sidecar `proxyCPU=100m`, `proxyCPULimit` absent. Each YAML already rolls checkout and recommendations before the hold (`restart_before_hold`, settle 60 s).
- Cool-off is 360 s after a hold ends and before the next launch. Seven cool-offs. No cool-off after the eighth hold.
- RetryGuard-on YAMLs stay on `retry_metric: edge_rpr` and `retries_threshold: 0.5`. Leave the controller code alone.
- New folders only. Slots already used stay as they are: both-off 155–159, RetryGuard-only 11–19, TopFull-only 37–38, both-on 22–23.
- A hold counts only if `total.csv` has at least 500 lines, frontend `replica_count` is 4 on every `resource_usage.csv` sample, every other Boutique deployment is 1, no `replica_count` of 0, and the mesh span is about 10–15 minutes. A failed gate keeps its folder. Bump to the next free number and launch that arm again. That relaunch is the one that fills the "twice" count.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Project `project-76deda76-55f1-42d2-abb`, zone `us-central1-a`. Do not start the `networks-workshop` VMs.
- Wall clock is about 2.5–3 hours: eight 600 s holds, seven 360 s cool-offs, plus pulls and the pin check.

## File map

| Arm | Config | First slot | Second slot | After both |
|---|---|---|---|---|
| RetryGuard off, TopFull off | `experiments/configs/scenario_2_baseline_no_topfull.yaml` | 160 | 161 | 162 |
| RetryGuard on, TopFull off | `experiments/configs/scenario_2_retryguard_no_topfull.yaml` | 20 | 21 | 22 |
| RetryGuard off, TopFull on | `experiments/configs/scenario_2_baseline.yaml` | 39 | 40 | 41 |
| RetryGuard on, TopFull on | `experiments/configs/scenario_2_retryguard.yaml` | 24 | 25 | 26 |

Local pulls land in `experiments/results/campaign_48/S2_sustained_overload/<log_folder>/`.

---

### Task 1: Cluster up, Paper-C1 pin confirmed

**Files:**
- Read: `experiments/latch_restore_check.sh`
- Read: `experiments/latch_restore_fix.sh`
- Read: `Guides and Info/CONNECT-VMS.md`

- [ ] **Step 1: Start the three VMs if they are stopped**

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Refresh `HostName` in `~/.ssh/config` from the new public IPs. Confirm:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes"
```

Expected: both nodes `Ready`.

- [ ] **Step 2: Confirm the Paper-C1 pin**

```powershell
Get-Content -Raw experiments/latch_restore_check.sh | ssh topfull-master bash -s
```

Expected: `RESTORE GATE PASS`.

If it fails, re-apply the HPA and sidecar pin, wait until frontend is 4/4 ready and nothing is Pending, then run the check again:

```powershell
Get-Content -Raw experiments/latch_restore_fix.sh | ssh topfull-master bash -s
```

CPU limits are applied by `run_scenario.py` from each YAML's `scale_constraints` at launch. The check must pass before the first hold.

---

### Task 2: Eight holds

**Files:**
- Modify, between the two launches of each arm: the YAML in the table above (`run_number`, `log_folder`, and the one-line `description`)

**Interfaces:**
- Consumes: Paper-C1 pin from Task 1. Each YAML already has the mix, the CPU table, and the controller flags.
- Produces: eight pulled folders under `experiments/results/campaign_48/S2_sustained_overload/`.

Launch order:

1. `scenario_2_baseline_no_topfull.yaml` (160, then 161)
2. `scenario_2_retryguard_no_topfull.yaml` (20, then 21)
3. `scenario_2_baseline.yaml` (39, then 40)
4. `scenario_2_retryguard.yaml` (24, then 25)

- [ ] **Step 1: For each of the eight slots, clear stale runner scripts, launch, and pull**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_*.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/<yaml>
python experiments/pull_results.py experiments/configs/<yaml>
```

Replace `<yaml>` with the arm's file. The file's `run_number` and `log_folder` must already be the slot being launched.

- [ ] **Step 2: Gate the pulled folder**

Pass: `total.csv` ≥ 500 lines, frontend replicas 4 on every resource sample, every other service at 1, no zero replica count, mesh span about 10–15 minutes, `service_capacity.json` millicores match Paper-C1.

Fail: keep the folder. Set `run_number` and `log_folder` to the next unused number for that arm (161 becomes 162, and so on). Launch again. That new folder is the repeat.

- [ ] **Step 3: Bump the YAML before the second launch of the same arm**

Change only `run_number`, `log_folder`, and `description`. Leave `locust.user_counts`, `scale_constraints`, `paper_cpu_reconcile`, and the `topfull_rl` / `retryguard` flags as they are.

`log_folder` names:

- both-off: `baseline_no_topfull_sustained_overload_run<N>`
- RetryGuard-only: `run_retryguard_no_topfull_sustained_overload_run<N>`
- TopFull-only: `baseline_topfull_no_retryguard_sustained_overload_run<N>`
- both-on: `run_topfull_retryguard_sustained_overload_run<N>`

- [ ] **Step 4: Cool off 360 s before the next launch**

```powershell
Start-Sleep -Seconds 360
```

Do this seven times. Skip it after the eighth hold.

---

### Task 3: Short readout and next-free YAML slots

**Files:**
- Create: `Guides and Info/2026-10-08-s2-run89-four-arms-replay.md`
- Modify: `AGENTS.md` §4 (one status bullet and the next-free slot sentence)

- [ ] **Step 1: Write the readout**

One page. Setup line (mix, Paper-C1, 600 s, 360 s cool-offs). Then one row per hold: slot, arm, Locust lines, total goodput, failure fraction, P95, frontend replica samples, longest controlled rejection streak, largest retry edge and its delta, and for the two RetryGuard-on arms the ON→OFF / OFF→ON counts with the edge name. Say which gates passed. Point at the 2026-10-07 four-arm note as the previous pair of the same mix. No new scoring script.

- [ ] **Step 2: Leave the YAMLs on the next free slots**

After two passing holds per arm the files point at both-off **162**, RetryGuard-only **22**, TopFull-only **41**, both-on **26**. If a gate failure consumed an extra number, the next free slot is one past the last folder kept. Counts and `scale_constraints` stay on the run 89 numbers. Leave the cluster on the Paper-C1 pin.

- [ ] **Step 3: Update AGENTS.md**

Add one §4 bullet naming the eight folders and the next-free slots. Update the "next free YAML slots" sentence to those same numbers.

---

### Task 4: Commit, push, stop the VMs

- [ ] **Step 1: Commit the eight result folders, the four YAML bumps, the readout, and AGENTS.md**

Leave `_tmp_*` files untracked. Message:

```text
Record two more holds of the run 89 mix on each controller arm.
```

- [ ] **Step 2: Push**

```powershell
git push
```

- [ ] **Step 3: Stop the three VMs**

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a --project=project-76deda76-55f1-42d2-abb
```

Confirm the list shows `TERMINATED` for all three.
