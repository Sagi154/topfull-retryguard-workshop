# Frontend μ ok-confidence calibration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Also copy this plan to `docs/superpowers/plans/2026-09-19-frontend-mu-ok-confidence.md` at the start of execution (Plan-mode cannot write that file until approved).

**Goal:** Get a frontend frozen `mu_per_millicore` with `n_sat_ticks >= 10` (ok confidence) by repeating the 100m calibration, then running a tighter 50m calibration.

**Architecture:** No estimator changes. Bump the existing 100m YAML to `run2`, add a new 50m YAML (`cpu_limit_fraction: 0.05` → 50m). Run both TopFull-off / RetryGuard-off holds with 300 s cool-offs. Freeze **only** `frontend` from the new folder with the higher `n_sat_ticks` (100m wins a tie — 10× rescale vs 20×).

**Tech Stack:** Existing `run_scenario.py` / `pull_results.py` / `capacity_frozen.py freeze` / `rho_frozen_report.py`. PowerShell on Windows. SSH host aliases.

## Global Constraints

- Do not change `SAT_TAIL_TRIM_TICKS` (5), `SAT_5XX_FRACTION` (0.05), or `LOW_CONFIDENCE_SAT_TICKS` (10). Do not loosen the gate to pass 9 ticks.
- Do not touch `retryguard.py` or any S1–S6 Locust counts.
- Do not re-freeze checkout, payment, or productcatalog. Do not freeze frontend from `calibration_frontend_constrained_run1` again, or from the productcatalog folder.
- Never overwrite `calibration_frontend_constrained_run1`. 100m replay is `run2` / `log_folder: calibration_frontend_constrained_run2`.
- `cluster_shape` stays `topfull-worker-1=e2-standard-16`. Stop if the worker SKU differs.
- SSH aliases only; connect as `idozacharia`.
- Millicore source is `service_capacity.json`.
- **300 s cool-off after Task 0 Ready, before the first Locust run; 300 s after the 100m run exits, before the 50m run.** Clock starts when `run_scenario.py` exits. `pull_results.py` may run during the wait. Do not skip or shorten.
- Always run both calibrations (user choice). Freeze from the new run with the **higher** `n_sat_ticks`. Tie → 100m folder. If both new runs have `n_sat < 9`, keep the current 9-tick freeze and document the miss (do not overwrite with a worse sample). If the winner still has `n_sat < 10` but `>= 9`, freeze it anyway and keep `low_confidence`.
- Best effort: do not add a third load-gen pass, more Locust users, or a lower fraction than 0.05.

## File map

- Modify: [experiments/configs/scenario_calibration_frontend_constrained.yaml](experiments/configs/scenario_calibration_frontend_constrained.yaml) — bump `run_number` / `log_folder` to run2
- Create: [experiments/configs/scenario_calibration_frontend_constrained_50m.yaml](experiments/configs/scenario_calibration_frontend_constrained_50m.yaml) — copy of the 100m config with `cpu_limit_fraction: 0.05`, `scenario_id: 43`, `log_folder: ..._50m_run1`
- After freeze: [experiments/capacity/capacity_frozen.json](experiments/capacity/capacity_frozen.json) (CLI only), [experiments/capacity/README.md](experiments/capacity/README.md), [AGENTS.md](AGENTS.md), S1 run24 / S2 run23 `rho_frozen_report.*`

Task order: Task 1 (YAMLs) → Task 0 (VMs) → Task 2 (100m run2) → Task 3 (50m run) → Task 4 (freeze + docs). Do not start Locust during Task 1.

---

### Task 1: YAML — bump 100m to run2; add 50m config

**Files:**
- Modify: `experiments/configs/scenario_calibration_frontend_constrained.yaml`
- Create: `experiments/configs/scenario_calibration_frontend_constrained_50m.yaml`

**Interfaces:**
- Consumes: existing 100m YAML Locust mix (`getproduct/getcart/postcart 100`, `emptycart 300`, `postcheckout 20`, `spawn_rate 90`, `duration_seconds: 600`), `topfull_rl.enabled: false`, `retryguard.enabled: false`.
- Produces: 100m slot `calibration_frontend_constrained_run2`; 50m slot `calibration_frontend_constrained_50m_run1`. `scenario_id` 41 stays for 100m; 50m uses **43** so `scenario_dir_name()` returns `""` (results under `campaign_48/`). `millicores_from_fraction(1000, 0.05) == 50`.

- [ ] **Step 1: Bump the 100m YAML**

In `experiments/configs/scenario_calibration_frontend_constrained.yaml` set:

```yaml
run_number: 2
log_folder: calibration_frontend_constrained_run2
```

Leave `cpu_limit_fraction: 0.1`. Add a comment that run1 was the 9-tick freeze source and must not be overwritten.

- [ ] **Step 2: Create the 50m YAML**

Copy the 100m file. Change only:

```yaml
scenario_id: 43
scenario_name: calibration_frontend_constrained_50m
run_number: 1
description: >
  Calibration-only run. frontend CPU constrained to 50m (0.05 x paper 1000m).
  TopFull RL off, RetryGuard off. Same Locust mix as the 100m constrained cal.
scale_constraints:
  - deployment: frontend
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.05    # 0.05 x paper 1000m -> 50m
    container: server
log_folder: calibration_frontend_constrained_50m_run1
```

Keep duration 600 s, same Locust counts, same `infra:` block.

- [ ] **Step 3: Sanity-check parse and millicores**

```powershell
python -c "import yaml, pathlib, sys; sys.path.insert(0,'experiments'); import run_scenario as r, topfull_cpu_quotas as q
for p in ['experiments/configs/scenario_calibration_frontend_constrained.yaml','experiments/configs/scenario_calibration_frontend_constrained_50m.yaml']:
 cfg=yaml.safe_load(pathlib.Path(p).read_text(encoding='utf-8')); c=cfg['scale_constraints'][0]; m=q.millicores_from_fraction(q.paper_limit_for('frontend'), float(c['cpu_limit_fraction'])); print(p, 'id', cfg['scenario_id'], 'dir', repr(r.scenario_dir_name(cfg)), 'log', cfg['log_folder'], 'm', m)"
```

Expected: 100m file → id 41, dir `''`, log `..._run2`, m **100**. 50m file → id 43, dir `''`, log `..._50m_run1`, m **50**.

- [ ] **Step 4: Commit**

```powershell
git add experiments/configs/scenario_calibration_frontend_constrained.yaml experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
git commit -m "add frontend 100m run2 slot and 50m calibration config"
```

---

### Task 0: Confirm VMs Ready

**Files:** none. Follow [Guides and Info/CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md). User `idozacharia`.

VMs were left RUNNING after the previous calibration. Still re-verify; start if `TERMINATED`.

- [ ] **Step 1: List instances; require worker `e2-standard-16`**

```powershell
gcloud config set project networks-workshop
gcloud compute instances list --format="table(name,status,machineType.basename(),networkInterfaces[0].accessConfigs[0].natIP)"
```

If not RUNNING: `gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a` then refresh `HostName` in `~/.ssh/config`.

- [ ] **Step 2: SSH + cluster**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami; kubectl get nodes; kubectl get pods -n default"
```

Expected: `whoami` is `idozacharia`; both nodes Ready; Boutique `Running` `2/2`. If pods are `Completed`, `kubectl delete pods -n default --all` and wait.

- [ ] **Step 3: Paper CPU + clear `/tmp`**

```powershell
ssh topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,CPU_LIMIT:.spec.template.spec.containers[0].resources.limits.cpu"
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

Expected before the first run: frontend 1000m (runner will apply 100m then 50m). Cluster Ready. Task 2 still sleeps 300 s after this.

---

### Task 2: 100m run2 (same config, new folder)

**Files:** pulled folder `experiments/results/campaign_48/calibration_frontend_constrained_run2/` (untracked unless the user asks to commit CSVs).

- [ ] **Step 1: Cool-off 300 s after Task 0 Ready**

```powershell
Start-Sleep -Seconds 300
```

- [ ] **Step 2: Clear `/tmp`, run, confirm 100m patch in the log**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained.yaml
```

Expected: exit 0; log line `Applying CPU limit 100m (fraction=0.1) to frontend/server`.

- [ ] **Step 3: Pull during the next cool-off; measure n_sat**

Start the 300 s clock at runner exit (needed before Task 3). Pull may overlap:

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained.yaml --no-report
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_frontend_constrained_run2
python -c "import sys; sys.path.insert(0,'experiments'); import capacity_frozen as cf; from pathlib import Path; p=Path('experiments/results/campaign_48/calibration_frontend_constrained_run2'); print('n_sat', cf.count_sat_ticks(p,'frontend')); import json; print('cpu', json.loads((p/'service_capacity.json').read_text())['frontend']['cpu_limit_millicores'])"
```

Confirm `cpu == 100` and sat ticks exist **before** the last 5 frontend rows (not EOF-only). Record `mu_sat` and `n_sat`. Do **not** freeze yet. Do **not** skip Task 3.

- [ ] **Step 4: Bump the 100m YAML to run3** so a later accident cannot overwrite run2.

```yaml
run_number: 3
log_folder: calibration_frontend_constrained_run3
```

Commit that bump with Task 4 or immediately:

```powershell
git add experiments/configs/scenario_calibration_frontend_constrained.yaml
git commit -m "bump frontend 100m calibration YAML to run3"
```

If you commit here, Task 4 must not revert it.

---

### Task 3: 50m run (tighter CPU)

**When:** After Task 2's 300 s cool-off has finished.

**Files:** `experiments/results/campaign_48/calibration_frontend_constrained_50m_run1/`

- [ ] **Step 1: Clear `/tmp`, run 50m**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml
```

Expected: exit 0; log line `Applying CPU limit 50m (fraction=0.05) to frontend/server`.

- [ ] **Step 2: Pull and measure (no extra cool-off after this — last run)**

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained_50m.yaml --no-report
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_frontend_constrained_50m_run1
python -c "import sys; sys.path.insert(0,'experiments'); import capacity_frozen as cf; from pathlib import Path; p=Path('experiments/results/campaign_48/calibration_frontend_constrained_50m_run1'); print('n_sat', cf.count_sat_ticks(p,'frontend')); import json; print('cpu', json.loads((p/'service_capacity.json').read_text())['frontend']['cpu_limit_millicores'])"
```

Confirm `cpu == 50`, mid-run sat ticks (not only last 5 rows). Record `mu_sat` and `n_sat`. Do not freeze frontend from a folder whose frontend inbound is cascade-only nonsense; this run *is* the frontend bottleneck, so frontend `mu_sat` here is the intended signal.

- [ ] **Step 3: Bump 50m YAML to run2**

```yaml
run_number: 2
log_folder: calibration_frontend_constrained_50m_run2
```

---

### Task 4: Freeze the winner, refresh S1/S2 ρ, docs

**Files:**
- CLI: `experiments/capacity/capacity_frozen.json` (frontend entry only)
- Modify: `experiments/capacity/README.md`, `AGENTS.md`
- Regenerate: S1 `baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.{md,json}` and S2 `..._run23/rho_frozen_report.{md,json}`

**Winner rule:** Let `n100` = Task 2 `count_sat_ticks` and `n50` = Task 3 `count_sat_ticks` (trimmed). Ignore a run with `mu_sat is None` (treat n_sat as 0). Winner = max(n100, n50); if equal and both > 0, winner = 100m folder. If both n_sat < 9, **do not `--force`**; keep `0.37` / 9-tick freeze. If winner n_sat >= 9, freeze that folder with `--force`.

- [ ] **Step 1: Freeze frontend from the winner**

Example if 50m wins:

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_frontend_constrained_50m_run1 --service frontend --force
```

Example if 100m run2 wins:

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_frontend_constrained_run2 --service frontend --force
```

Confirm JSON: `checkoutservice` / `paymentservice` / `productcatalogservice` unchanged; frontend `calibrated_at_cpu_limit_millicores` is 100 or 50 matching the winner; `note` is `null` iff `n_sat_ticks >= 10`.

- [ ] **Step 2: S1/S2 rho**

```powershell
python experiments/rho_frozen_report.py experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24
python experiments/rho_frozen_report.py experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23
```

Record all four services' `rho_hat`. Checkout/payment/productcatalog `rho_hat` must match the previous report if frontend was the only freeze change. Informal S1 0.5–0.8 band is **not** a pass/fail gate.

- [ ] **Step 3: README + AGENTS.md**

Update the frontend row (source run, millicores, `mu_per_millicore`, `n_sat_ticks`, confidence). Mention both new folders and which one won. Keep the 9-tick run1 row as historical (do not reuse). YAML next-free slots: 100m **run3**, 50m **run2**.

- [ ] **Step 4: Commit** (JSON, README, AGENTS, S1/S2 reports, YAML bumps if not already committed). Do not add the calibration CSV folders unless asked.

```powershell
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md AGENTS.md experiments/configs/scenario_calibration_frontend_constrained.yaml experiments/configs/scenario_calibration_frontend_constrained_50m.yaml experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.md experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.json experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.md experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.json
git commit -m "freeze frontend mu from higher-n_sat constrained recalibration"
```

Leave VMs RUNNING unless the user asks to stop them.

## Self-review

- Spec-adjacent: ok confidence = `n_sat >= 10`; this plan never lowers that gate.
- Both runs always happen; freeze rule and 300 s cool-offs are explicit.
- No placeholders; no checkout/payment/productcatalog freeze; no Locust bump.

