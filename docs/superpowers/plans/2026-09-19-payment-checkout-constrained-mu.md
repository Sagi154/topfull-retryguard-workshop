---
name: payment checkout constrained mu
overview: Recalibrate paymentservice μ at constrained CPU (always 100m then 50m, freeze from the CPU-pegged winner), then measure checkoutservice μ in a separate run at that same millicore count — so payment’s freeze is a real ceiling, not checkout-timeout bleed.
todos:
  - id: yaml
    content: "Task 1: Four constrained YAMLs (payment 100m/50m, checkout 100m/50m) + commit"
    status: in_progress
  - id: vms
    content: "Task 0: Confirm VMs Ready (e2-standard-16, cluster, paper CPU, /tmp)"
    status: pending
  - id: pay100
    content: "Task 2: Payment 100m run + cool-offs + measure, no freeze"
    status: pending
  - id: pay50
    content: "Task 3: Payment 50m run + measure, no freeze"
    status: pending
  - id: payfreeze
    content: "Task 4: Freeze payment from CPU-pegged winner (or skip)"
    status: pending
  - id: chkrun
    content: "Task 5: Checkout run at payment-winner millicores"
    status: pending
  - id: chkfreeze
    content: "Task 6: Freeze checkout if eligible; S1/S2 rho; README/AGENTS; commit"
    status: pending
isProject: false
---

# Payment / checkout constrained-μ calibration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Copy this plan to `docs/superpowers/plans/2026-09-19-payment-checkout-constrained-mu.md` at the start of execution (Plan-mode cannot write that file until approved). Do NOT edit the plan file while executing.

**Goal:** Replace the untrusted paymentservice freeze (`mu_per_millicore=0.0195` from a 1000m run that never pegged payment CPU) with a constrained-CPU `mu_sat`, then separately freeze checkoutservice at the same millicores.

**Architecture:** No estimator changes. Four new TopFull-off / RetryGuard-off YAMLs (payment 100m, payment 50m, checkout 100m, checkout 50m). Always run both payment holds; freeze payment only from a run that **CPU-pegs**. Then run **one** checkout hold at the payment winner’s millicores (default 100m if payment has no eligible freeze). 300 s cool-offs between Locust runs.

**Tech Stack:** Existing `run_scenario.py` / `pull_results.py` / `estimate_service_mu.py` / `capacity_frozen.py freeze` / `rho_frozen_report.py`. PowerShell on Windows. SSH host aliases.

## Global Constraints

- Do not change `SAT_TAIL_TRIM_TICKS` (5), `SAT_5XX_FRACTION` (0.05), or `LOW_CONFIDENCE_SAT_TICKS` (10).
- Do not touch `retryguard.py`, `estimate_service_mu.py`, or any S1–S6 Locust counts.
- Do not add Locust users beyond the existing checkout/payment calibration mix (`postcheckout: 500`).
- Do not freeze from S3 RG run8 (checkout is 100m there, TopFull-on).
- Do not freeze payment from a checkout-constrained folder, or checkout from a payment-constrained folder.
- Do not re-freeze frontend or productcatalog.
- Never overwrite `calibration_checkout_payment_full_cpu_run1` or any existing campaign/checkpoint folder.
- `cluster_shape` stays `topfull-worker-1=e2-standard-16`. Stop if the worker SKU differs.
- SSH aliases only; connect as `idozacharia`.
- Millicore source is `service_capacity.json`.
- **300 s cool-off after Task 0 Ready, before the first Locust run; 300 s after every Locust run except the last.** Clock starts when `run_scenario.py` exits. `pull_results.py` may run during the wait. Do not skip or shorten.
- Payment search (user choice): **always** run 100m then 50m. Winner among **eligible** runs only (see gate below). 100m wins n_sat ties.
- Best effort: no third millicore, no extra load-gen pass if both payment runs fail the CPU-peg gate. Leave payment at 0.0195 and mark it untrusted in docs.

## Why this run, not another 1000m pair

`calibration_checkout_payment_full_cpu_run1` froze payment at 19.5 req/s because inbound resets fired `mu_sat`. Payment CPU was ~5m mean / 65m max of 1000m, W ≈ 3.6 ms, while checkout pegged 1000m (W ≈ 325 ms). Those payment resets are PlaceOrder / 500 ms `perTryTimeout` bleed. Constraining **only** payment, keeping checkout at paper 1000m, is how payment becomes the bottleneck. Checkout then gets its own run with **only** checkout constrained, payment left at 1000m.

## Eligibility / winner (payment)

A payment folder is **eligible** only if all of:

- `service_capacity.json` `paymentservice.cpu_limit_millicores` is 100 or 50 as intended
- `mu_sat` is not None (`estimate_service_mu.py`)
- saturating ticks exist **before** the last 5 payment inbound rows
- **CPU peg:** max `cpu_millicores` for `paymentservice` in `resource_usage.csv` ≥ `0.8 ×` that run’s CPU limit (80m at 100m, 40m at 50m)

This peg gate is what would have rejected the 19.5 freeze (max 65m of 1000m). High `n_sat` without a peg is still checkout bleed — do not freeze.

Winner = eligible run with higher `count_sat_ticks`; if equal, 100m. If neither eligible: do not `--force` payment.

Checkout eligibility is the same gate on `checkoutservice` in the checkout folder. If ineligible, keep the 1000m checkout freeze (`0.1615`) and document the miss.

## File map

- Create: [experiments/configs/scenario_calibration_payment_constrained.yaml](experiments/configs/scenario_calibration_payment_constrained.yaml) — payment 100m, `scenario_id: 44`
- Create: [experiments/configs/scenario_calibration_payment_constrained_50m.yaml](experiments/configs/scenario_calibration_payment_constrained_50m.yaml) — payment 50m, `scenario_id: 45`
- Create: [experiments/configs/scenario_calibration_checkout_constrained.yaml](experiments/configs/scenario_calibration_checkout_constrained.yaml) — checkout 100m, `scenario_id: 46`
- Create: [experiments/configs/scenario_calibration_checkout_constrained_50m.yaml](experiments/configs/scenario_calibration_checkout_constrained_50m.yaml) — checkout 50m, `scenario_id: 47`
- After freeze: [experiments/capacity/capacity_frozen.json](experiments/capacity/capacity_frozen.json) (CLI only), [experiments/capacity/README.md](experiments/capacity/README.md), [AGENTS.md](AGENTS.md), S1 run24 / S2 run23 `rho_frozen_report.*`

Do **not** edit [experiments/configs/scenario_calibration_checkout_payment_full_cpu.yaml](experiments/configs/scenario_calibration_checkout_payment_full_cpu.yaml) beyond leaving it at `run2` (already the next-free full-CPU slot).

Task order: Task 1 (YAMLs) → Task 0 (VMs) → Task 2 (payment 100m) → Task 3 (payment 50m) → Task 4 (payment freeze) → Task 5 (checkout at winner millicores) → Task 6 (checkout freeze + docs). Do not start Locust during Task 1.

Locust mix for all four YAMLs (from the full-CPU checkout/payment cal — the mix that actually reaches payment):

```yaml
duration_seconds: 600
locust:
  user_counts:
    getproduct:   50
    postcheckout: 500
    getcart:      50
    postcart:     50
    emptycart:    50
  spawn_rate: 150
```

`topfull_rl.enabled: false`, `retryguard.enabled: false`, same `retries` / collectors / `infra:` block as [experiments/configs/scenario_calibration_checkout_payment_full_cpu.yaml](experiments/configs/scenario_calibration_checkout_payment_full_cpu.yaml).

---

### Task 1: Four constrained YAMLs

**Files:**
- Create: `experiments/configs/scenario_calibration_payment_constrained.yaml`
- Create: `experiments/configs/scenario_calibration_payment_constrained_50m.yaml`
- Create: `experiments/configs/scenario_calibration_checkout_constrained.yaml`
- Create: `experiments/configs/scenario_calibration_checkout_constrained_50m.yaml`

**Interfaces:**
- Consumes: Locust mix above; `millicores_from_fraction(paper_limit_for('paymentservice'|'checkoutservice'), fraction)` — both paper limits are 1000m.
- Produces: log folders `calibration_payment_constrained_run1`, `calibration_payment_constrained_50m_run1`, `calibration_checkout_constrained_run1`, `calibration_checkout_constrained_50m_run1`. `scenario_id` 44–47 so `scenario_dir_name()` returns `""` (results under `campaign_48/`).

- [ ] **Step 1: Write payment 100m YAML**

Copy the full-CPU checkout/payment cal file. Change to:

```yaml
scenario_id: 44
scenario_name: calibration_payment_constrained
condition: calibration
run_number: 1
description: >
  Calibration-only run. paymentservice CPU constrained to 100m.
  checkoutservice stays paper 1000m. TopFull RL off, RetryGuard off.
scale_constraints:
  - deployment: paymentservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 x paper 1000m -> 100m
    container: server
log_folder: calibration_payment_constrained_run1
```

Duration 600 s. Do **not** put checkout in `scale_constraints`.

- [ ] **Step 2: Write payment 50m YAML**

Same as Step 1 except:

```yaml
scenario_id: 45
scenario_name: calibration_payment_constrained_50m
run_number: 1
scale_constraints:
  - deployment: paymentservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.05    # 0.05 x paper 1000m -> 50m
    container: server
log_folder: calibration_payment_constrained_50m_run1
```

- [ ] **Step 3: Write checkout 100m YAML**

```yaml
scenario_id: 46
scenario_name: calibration_checkout_constrained
condition: calibration
run_number: 1
description: >
  Calibration-only run. checkoutservice CPU constrained to 100m.
  paymentservice stays paper 1000m. TopFull RL off, RetryGuard off.
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 x paper 1000m -> 100m
    container: server
log_folder: calibration_checkout_constrained_run1
```

Same Locust mix / duration / infra. Do **not** put payment in `scale_constraints`.

- [ ] **Step 4: Write checkout 50m YAML**

Same as Step 3 except `scenario_id: 47`, `scenario_name: calibration_checkout_constrained_50m`, `cpu_limit_fraction: 0.05`, `log_folder: calibration_checkout_constrained_50m_run1`.

- [ ] **Step 5: Sanity-check parse and millicores**

```powershell
python -c "import yaml, pathlib, sys; sys.path.insert(0,'experiments'); import run_scenario as r, topfull_cpu_quotas as q
for p in ['experiments/configs/scenario_calibration_payment_constrained.yaml','experiments/configs/scenario_calibration_payment_constrained_50m.yaml','experiments/configs/scenario_calibration_checkout_constrained.yaml','experiments/configs/scenario_calibration_checkout_constrained_50m.yaml']:
 cfg=yaml.safe_load(pathlib.Path(p).read_text(encoding='utf-8')); c=cfg['scale_constraints'][0]; m=q.millicores_from_fraction(q.paper_limit_for(c['deployment']), float(c['cpu_limit_fraction'])); print(p, 'id', cfg['scenario_id'], 'dir', repr(r.scenario_dir_name(cfg)), 'dep', c['deployment'], 'log', cfg['log_folder'], 'm', m, 'n_constraints', len(cfg['scale_constraints']))"
```

Expected: ids 44–47, dir `''`, millicores 100 / 50 / 100 / 50, one constraint each, deps `paymentservice` twice then `checkoutservice` twice.

- [ ] **Step 6: Commit**

```powershell
git add experiments/configs/scenario_calibration_payment_constrained.yaml experiments/configs/scenario_calibration_payment_constrained_50m.yaml experiments/configs/scenario_calibration_checkout_constrained.yaml experiments/configs/scenario_calibration_checkout_constrained_50m.yaml
git commit -m "add constrained-CPU calibration configs for payment and checkout"
```

---

### Task 0: Confirm VMs Ready

**Files:** none. Follow [Guides and Info/CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md). User `idozacharia`.

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

Expected before the first run: `checkoutservice` and `paymentservice` both 1000m (runner applies 100m/50m per YAML, then reconciles). Task 2 still sleeps 300 s after this.

---

### Task 2: Payment 100m

**Files:** pulled folder `experiments/results/campaign_48/calibration_payment_constrained_run1/`

- [ ] **Step 1: Cool-off 300 s after Task 0 Ready**

```powershell
Start-Sleep -Seconds 300
```

- [ ] **Step 2: Clear `/tmp`, run, confirm 100m patch on payment**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_payment_constrained.yaml
```

Expected: exit 0; log line `Applying CPU limit 100m (fraction=0.1) to paymentservice/server`. Checkout must **not** be patched.

- [ ] **Step 3: Pull during the next cool-off; measure (do not freeze)**

Start the 300 s clock at runner exit. Pull may overlap:

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_payment_constrained.yaml --no-report
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_payment_constrained_run1
python -c "
import csv, json, sys
from pathlib import Path
sys.path.insert(0,'experiments')
import capacity_frozen as cf
p=Path('experiments/results/campaign_48/calibration_payment_constrained_run1')
cap=json.loads((p/'service_capacity.json').read_text())
cpu=cap['paymentservice']['cpu_limit_millicores']
rows=[r for r in csv.DictReader((p/'resource_usage.csv').open(encoding='utf-8')) if r['service']=='paymentservice']
mx=max(float(r['cpu_millicores']) for r in rows)
print('cpu_limit', cpu, 'cpu_max', mx, 'peg', mx>=0.8*cpu, 'n_sat', cf.count_sat_ticks(p,'paymentservice'))
"
```

Confirm `cpu_limit == 100`. Record `mu_sat`, `n_sat`, `cpu_max`, peg true/false. Do **not** freeze. Do **not** skip Task 3.

- [ ] **Step 4: Bump payment 100m YAML to run2**

```yaml
run_number: 2
log_folder: calibration_payment_constrained_run2
```

Commit with Task 6 or immediately so an accident cannot overwrite run1.

---

### Task 3: Payment 50m

**When:** After Task 2’s 300 s cool-off has finished.

**Files:** `experiments/results/campaign_48/calibration_payment_constrained_50m_run1/`

- [ ] **Step 1: Clear `/tmp`, run 50m**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_payment_constrained_50m.yaml
```

Expected: exit 0; `Applying CPU limit 50m (fraction=0.05) to paymentservice/server`.

- [ ] **Step 2: Pull and measure (300 s cool-off still required before Task 5)**

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_payment_constrained_50m.yaml --no-report
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_payment_constrained_50m_run1
```

Same CPU-peg one-liner as Task 2, path `..._50m_run1`, expect `cpu_limit == 50`. Record numbers. Do not freeze yet.

- [ ] **Step 3: Bump payment 50m YAML to run2**

```yaml
run_number: 2
log_folder: calibration_payment_constrained_50m_run2
```

---

### Task 4: Freeze payment winner (or skip)

**Files:** CLI only on [experiments/capacity/capacity_frozen.json](experiments/capacity/capacity_frozen.json) — `paymentservice` entry only.

- [ ] **Step 1: Apply the eligibility / winner rule**

Ignore a run with `mu_sat is None` (n_sat = 0) and any run that failed the CPU-peg gate. Winner = max n_sat among eligible; tie → 100m folder.

- [ ] **Step 2: Freeze only if there is a winner**

Example if 50m wins:

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_payment_constrained_50m_run1 --service paymentservice --force
```

Example if 100m wins:

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_payment_constrained_run1 --service paymentservice --force
```

Confirm JSON: frontend / checkout / productcatalog unchanged; payment `calibrated_at_cpu_limit_millicores` is 100 or 50; `note` is `null` iff `n_sat_ticks >= 10`.

If neither eligible: **do not `--force`**. Keep `0.0195`. Record “payment untrusted, no CPU-pegged sat” for Task 6. Checkout millicores default to **100**.

- [ ] **Step 3: Set checkout millicores**

If payment froze: use that `calibrated_at_cpu_limit_millicores` (100 or 50). If not: 100. Write it down; Task 5 runs exactly one YAML.

Do not regenerate S1/S2 ρ yet (checkout freeze still pending).

---

### Task 5: Checkout at payment-winner millicores

**When:** After Task 3’s 300 s cool-off (if Task 4 freeze was fast, still wait out that cool-off). One Locust run only.

**Files:** `experiments/results/campaign_48/calibration_checkout_constrained_run1/` **or** `..._50m_run1/`

- [ ] **Step 1: Cool-off must already have elapsed; clear `/tmp`; run the matching YAML**

If checkout millicores is 100:

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_checkout_constrained.yaml
```

If 50:

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_checkout_constrained_50m.yaml
```

Expected: `Applying CPU limit {100m|50m} ... to checkoutservice/server`. Payment must **not** be patched.

- [ ] **Step 2: Pull and measure (last Locust run — no further cool-off)**

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_checkout_constrained.yaml --no-report
```

Use the `_50m` config path if that is the file you ran. Then `estimate_service_mu.py` on the pulled folder and the CPU-peg one-liner with `service=='checkoutservice'`. Confirm limit 100 or 50. Record `mu_sat`, `n_sat`, peg.

- [ ] **Step 3: Bump the YAML you actually ran** to run2 / `..._run2` so it cannot overwrite. Leave the unused 100m or 50m checkout YAML at run1.

---

### Task 6: Freeze checkout (if eligible), refresh S1/S2 ρ, docs

**Files:**
- CLI: `experiments/capacity/capacity_frozen.json` (checkout entry only if eligible)
- Modify: `experiments/capacity/README.md`, `AGENTS.md`
- Regenerate: S1 `baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.{md,json}` and S2 `..._run23/rho_frozen_report.{md,json}`

- [ ] **Step 1: Freeze checkout if eligible**

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_checkout_constrained_run1 --service checkoutservice --force
```

Swap in the `_50m_run1` path if that was the run. Confirm payment / frontend / productcatalog unchanged except for whatever Task 4 already wrote to payment.

If ineligible: do not `--force`. Keep checkout `0.1615` at 1000m. Document the miss.

- [ ] **Step 2: S1/S2 rho**

```powershell
python experiments/rho_frozen_report.py experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24
python experiments/rho_frozen_report.py experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23
```

Record all four services’ `rho_hat`. Frontend / productcatalog must match the previous report unless you accidentally froze them (do not). Informal S1 0.5–0.8 band is **not** a pass/fail gate. Note checkout μ_per_millicore vs historical 0.1615 (linearity check only — still freeze the constrained value if eligible).

- [ ] **Step 3: README + AGENTS.md**

Update payment and checkout rows (source run, millicores, `mu_per_millicore`, `n_sat_ticks`, peg, confidence). Keep the 1000m payment 0.0195 / checkout 0.1615 rows as historical (do not reuse payment 0.0195). YAML next-free: payment 100m **run2**, payment 50m **run2**, the checkout YAML you ran **run2**, the unused checkout YAML still **run1**. One dated AGENTS.md bullet; do not rewrite §4.

- [ ] **Step 4: Commit** (JSON, README, AGENTS, S1/S2 reports, YAML bumps). Do not add the calibration CSV folders unless asked.

```powershell
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md AGENTS.md experiments/configs/scenario_calibration_payment_constrained.yaml experiments/configs/scenario_calibration_payment_constrained_50m.yaml experiments/configs/scenario_calibration_checkout_constrained.yaml experiments/configs/scenario_calibration_checkout_constrained_50m.yaml experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.md experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.json experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.md experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.json
git commit -m "freeze payment and checkout mu from CPU-pegged constrained calibrations"
```

If payment was not frozen, drop `capacity_frozen.json` from this commit only if it is unchanged; still commit docs explaining the miss.

Leave VMs RUNNING unless the user asks to stop them.

## Self-review

- Payment work is isolated from checkout work (Tasks 2–4 vs Task 5–6). Checkout millicores follow the payment winner (or 100m default).
- CPU-peg gate is the actual fix for the 19.5 freeze; sat gates are unchanged.
- Always both payment CPUs; one checkout run; 300 s cool-offs; no Locust bump; no S3 freeze; no estimator edits.
- No placeholders. Unused checkout YAML is created in Task 1 and simply not executed.
