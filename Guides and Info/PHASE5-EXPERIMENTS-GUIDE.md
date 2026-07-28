# Phase 5 & Experiments Guide

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Scope:** This guide covers everything from Phase 5 (TopFull baseline experiment) through the experiment infrastructure we designed and built. It documents what we decided, what was built, and what is still left to do.
>
> **For agents:** This file is the canonical reference for the experiment runner and scenario config system. Read it before making changes to anything in `experiments/`.

---

## 1. What Phase 5 Is

Phase 5 is the **baseline experiment** — the "no RetryGuard" condition for each scenario. It is not a single run but the first half of every scenario comparison. The full picture is:

- **Phase 5** = run each scenario with TopFull only (Istio default retries on, RetryGuard off)
- **Phase 6** = run the same scenario again with RetryGuard active, then compare

Every scenario is run **multiple times** (≥3 per condition) because Locust generates randomised user behaviour — a single run is not sufficient for a reliable comparison.

### Stack startup order (always this sequence)

| Order | Machine | Process | tmux session |
|-------|---------|---------|-------------|
| 1 | master | Go proxy (`proxy_online_boutique.go`) | `proxy` |
| 2 | master | RL controller (`deploy_rl.py`) | `toprl` |
| 3 | master | Metric collector (`metric_collector.py`) | `metrics` |
| 4 | master | RetryGuard (`retryguard.py`) — Phase 6 only | `retryguard` |
| 5 | loadgen | Locust (`online_boutique_create.sh` + `create2.sh`) | `loadgen` |

Order matters: `deploy_rl.py` requires the proxy to be running. `metric_collector.py` needs Locust traffic to be flowing or it crashes on a `KeyError` (the proxy has no metrics for endpoints with zero requests yet).

---

## 2. The Five Scenarios

Each scenario is run under two conditions: **baseline** (RetryGuard off) and **RetryGuard** (on). Scenario 5 is RetryGuard-only.

### Scenario 1 — Normal Operation

- **Load:** Flat, well within capacity (~50% of default user counts)
- **Topology:** No changes
- **Duration:** 5 minutes
- **Goal:** Sanity check. RetryGuard must make **zero** VirtualService patches. If it patches anything, the rejection threshold is miscalibrated.
- **What to look for:** Goodput, latency, and rejection rate statistically identical between baseline and RetryGuard conditions.

### Scenario 2 — Sustained Overload (core experiment)

- **Load:** Ramp to ρ > 1, hold for 10 minutes
- **Topology:** No changes — global cluster overload
- **Duration:** 10 minutes minimum (the disable → recover → re-enable cycle must repeat multiple times)
- **Goal:** Observe the retry storm under TopFull-only. With RetryGuard on, watch it suppress retries per service and allow goodput to recover.
- **Why 10 minutes:** RetryGuard only fires after ~2 consecutive 30-second windows above threshold (~60s). The effect (load drops, TopFull RL re-settles, goodput recovers) takes additional time. The full cycle must repeat to prove stable behaviour.

### Scenario 3 — Targeted Bottleneck

- **Load:** Moderate full-chain load (same user counts as Scenario 2)
- **Topology:** `checkoutservice` constrained with a CPU limit (`100m`) before load starts
- **Duration:** 10 minutes
- **Goal:** Stress a specific known node rather than the whole system. Enables clean attribution — we know exactly which service is the bottleneck. TopFull reacts bluntly (throttles entire entry APIs); RetryGuard acts surgically at the hot spot.
- **Key question:** Does relief at the bottleneck propagate upstream? (e.g., does Frontend latency also improve?)

### Scenario 4 — Topology Position Comparison

Two Targeted Bottleneck runs with different services constrained. Same load, same method — only the bottleneck's position in the call graph changes.

| Run | Constrained service | Position | TopFull's signal |
|-----|--------------------|-----------|--------------------|
| **4A** | `productcatalogservice` | Gateway-adjacent (Frontend → ProductCatalog directly) | Direct — TopFull maps it cleanly to the `getproduct` entry API |
| **4B** | `paymentservice` | Checkout-mediated (Frontend → Checkout → Payment) | Attenuated — TopFull must infer payment via postcheckout |

- **Key question:** Does RetryGuard provide greater relative benefit in Run B, where TopFull's signal is weaker?

### Scenario 5 — Re-enable Interval Tuning

- **Load:** Same as Scenario 2 (sustained overload)
- **RetryGuard:** Always on. Only `re_enable_windows` changes across runs.
- **No separate baseline needed** — Scenario 2 baseline already serves as comparison.

| Config | `re_enable_windows` | Effective wait | Risk |
|--------|--------------------|-----------------|----|
| `interval_10s` | 1 | 30s | Oscillation — retries re-enabled before bottleneck clears |
| `interval_20s` | 2 | 60s | Below paper default |
| `interval_30s` | 3 | 90s | **Paper default** (RetryGuard Sec. 6.2) |
| `interval_60s` | 6 | 180s | Goodput suppressed too long after recovery |

---

## 3. What Changes Between Scenarios

There are exactly **three knobs** — everything else (cluster, VMs, pods, stack processes) is identical across all runs.

| Knob | Controlled by | Scenarios affected |
|------|---------------|--------------------|
| **Load intensity** (user counts) | `locust.user_counts` in config | All (low for S1, high for S2/5, medium for S3/4) |
| **Topology constraint** | `scale_constraints` in config → `kubectl scale` or `kubectl patch` cpu_limit | S3, S4A, S4B only |
| **RetryGuard re-enable interval** | `retryguard.re_enable_windows` in config | S5 only |

Between every run you must:
1. Stop Locust (runner does this automatically)
2. Copy logs to a named folder (runner does this automatically)
3. For Scenarios 3/4: restore the constrained deployment (runner does this automatically)
4. Wait for the cluster to settle before the next run

---

## 4. Data Collection — Same Mechanics Across All Scenarios

The collection tools are identical for every run. What changes is which metrics you **focus on** in analysis.

| Layer | Tool | Output | Always collected? |
|-------|------|--------|------------------|
| API performance | `metric_collector.py` | `logs/*.csv` — goodput (rps), P99 latency, rejection rate per endpoint | Yes |
| Resource usage | `resource_collector.py` (inside deploy_rl) | CPU/memory per pod, `num_instances.csv` via cAdvisor | Yes |
| Controller decisions | RetryGuard script logs | VirtualService patches with timestamps (service, old→new attempts) | Only when RetryGuard is on |
| TopFull state | `overload_detection.py` output | Which APIs flagged as overloaded and at what priority | Yes |

### Primary metric focus per scenario

| Scenario | Focus metric |
|----------|-------------|
| 1 Normal Op | RetryGuard log — confirm **zero** patches |
| 2 Sustained Overload | Goodput over time + retries/request |
| 3 Targeted Bottleneck | Rejection rate at constrained service + upstream callers |
| 4A/4B Topology | Same as S3, **compared across positions A and B** |
| 5 Interval Tuning | Toggle event count (oscillation) + time-to-recovery |

---

## 5. Experiment Infrastructure Built

### File structure

```
experiments/
  configs/                         # 14 scenario YAML files
    scenario_1_baseline.yaml
    scenario_1_retryguard.yaml
    scenario_2_baseline.yaml
    scenario_2_retryguard.yaml
    scenario_3_baseline.yaml
    scenario_3_retryguard.yaml
    scenario_4a_baseline.yaml
    scenario_4a_retryguard.yaml
    scenario_4b_baseline.yaml
    scenario_4b_retryguard.yaml
    scenario_5_interval_10s.yaml
    scenario_5_interval_20s.yaml
    scenario_5_interval_30s.yaml
    scenario_5_interval_60s.yaml
  run_scenario.py                  # orchestrator — runs on Windows, controls VMs over SSH
  README.md                        # quick-start usage
```

### `run_scenario.py` — what it does

Runs on Windows. Reads a YAML config and orchestrates the entire experiment over SSH. Steps in order:

1. **Pre-flight** — verifies SSH reachability to master and loadgen, all K8s nodes Ready, all pods Running
2. **Clear logs** — wipes `logs/*.csv` on master so results don't bleed across runs
3. **Apply constraints** — runs `kubectl scale` or `kubectl patch` cpu_limit on the appropriate deployment; auto-detects and records original replica counts for clean restore
4. **Start master stack** — SCPs LF-safe start scripts to master, launches proxy → deploy_rl → metric_collector into named tmux sessions; verifies `deploy_rl.py` actually started
5. **Start RetryGuard** — if `retryguard.enabled: true`, SCPs `retryguard_params.json` to master and starts `retryguard.py` in its own tmux session
6. **Start Locust** — generates and SCPs a launch script to loadgen, starts create scripts in tmux, verifies Locust processes are running
7. **Progress bar** — updates every 15s; `Ctrl+C` aborts cleanly and still collects partial results
8. **Stop** — stops Locust, kills all master processes (metric_collector, deploy_rl, proxy, RetryGuard, Ray workers, tmux)
9. **Collect** — copies `logs/` to `results_base_path/<log_folder>/` on master; writes a `run_manifest.json` (config snapshot + timestamps) alongside the CSVs
10. **Restore** — puts deployments back to their original state

### Usage

```powershell
# Prerequisite (once)
pip install pyyaml

# Run a scenario from the repo root
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml

# Pull results to your PC after the run
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1 experiments/results/
```

### Repeating runs

Before each repeat, increment `run_number` and update `log_folder` in the config:

```yaml
run_number: 2
log_folder: baseline_topfull_no_retryguard_sustained_overload_run2
```

### YAML config schema

```yaml
scenario_id: 2
scenario_name: sustained_overload
condition: baseline          # baseline | retryguard
run_number: 1
description: "..."
duration_seconds: 600

locust:
  user_counts:               # TODO: not yet wired into create scripts (see §6)
    getproduct:   100
    postcheckout: 20
    getcart:      100
    postcart:     100
    emptycart:    300
  spawn_rate: 90
  scripts:
    - online_boutique_create.sh
    - online_boutique_create2.sh

scale_constraints: []        # empty = no manipulation
# method: replicas
# - deployment: checkoutservice
#   namespace: default
#   method: replicas
#   replicas: 1              # runner auto-detects original count and restores it
# method: cpu_limit
# - deployment: checkoutservice
#   namespace: default
#   method: cpu_limit
#   cpu_limit: "100m"        # applied via kubectl patch; removed after run
#   container: server

retryguard:
  enabled: false
  rejection_threshold: 0.20  # >20% triggers disable counter
  window_duration_seconds: 30
  disable_windows: 2         # consecutive windows above threshold → disable
  re_enable_windows: 3       # consecutive windows below threshold → re-enable
  retry_attempts_on: 3       # Istio VirtualService retries.attempts when enabled
  retry_attempts_off: 0      # Istio VirtualService retries.attempts when disabled

log_folder: baseline_topfull_no_retryguard_sustained_overload_run1

infra:
  master_ssh_host: topfull-master
  loadgen_ssh_host: topfull-load
  topfull_src_path: /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src
  topfull_loadgen_path: /home/idozacharia/TopFull/TopFull_loadgen
  venv_activate: /home/idozacharia/TopFull/venv/bin/activate
  results_base_path: /home/idozacharia/experiments/results
  retryguard_script: /home/idozacharia/experiments/retryguard.py
```

### Constraint methods for Scenarios 3/4

Our setup has all Online Boutique services at **1 replica** (set by `instance_scaling.py`). This means `kubectl scale --replicas=1` would be a no-op. For Scenarios 3 and 4, the configs use `method: cpu_limit` instead — a `100m` CPU cap creates genuine local overload on the target service without touching replica counts.

If you later increase replica counts (e.g. on a bigger worker node), switch to `method: replicas` and set `replicas: 1`.

---

## 6. What Is Left To Do

### 6a. Wire Locust user counts into the create scripts (PENDING)

**Status:** The `locust.user_counts` field in every config is currently **documentation only**. The runner prints a warning but uses the create scripts' hardcoded values.

**What needs to change:**

*On the loadgen VM* — edit both scripts to use env-var-with-default syntax:

```bash
# Before (hardcoded):
GETPRODUCT=100
POSTCHECKOUT=20
GETCART=100
POSTCART=100
CART=300
RATE=90

# After (reads env var, falls back to default):
GETPRODUCT=${GETPRODUCT:-100}
POSTCHECKOUT=${POSTCHECKOUT:-20}
GETCART=${GETCART:-100}
POSTCART=${POSTCART:-100}
CART=${CART:-300}
RATE=${RATE:-90}
```

Files to edit on the loadgen:
```
/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create.sh
/home/idozacharia/TopFull/TopFull_loadgen/online_boutique_create2.sh
```

*In `run_scenario.py`* — replace the TODO block in `start_locust()` with env var injection:

```python
# Build export prefix from config
env_map = {
    "getproduct":   "GETPRODUCT",
    "postcheckout": "POSTCHECKOUT",
    "getcart":      "GETCART",
    "postcart":     "POSTCART",
    "emptycart":    "CART",       # create.sh uses CART for the cart-session workers
}
exports = [f"export {shell_var}={user_counts[k]}"
           for k, shell_var in env_map.items() if k in user_counts]
if "spawn_rate" in lc:
    exports.append(f"export RATE={lc['spawn_rate']}")
env_prefix = "; ".join(exports) + "; " if exports else ""

# Prepend to the launch command in the launch script
launch_script = (
    f"#!/bin/bash\n"
    f"cd {loadgen_path}\n"
    f"{env_prefix}{launch_cmd}\n"
)
```

**Note:** The `CART` variable in the create scripts controls the user count for the `getcart`/`emptycart`/`postcart` combined session (session3) — not a single endpoint. Verify the exact mapping when making this change.

**Important:** When editing the create scripts on the VM, strip CRLF first. The scripts previously had Windows line ending issues. Write with LF only (use `sed -i "s/\r//"` on the VM, or use Python to write the file in binary mode).

### 6b. Implement RetryGuard controller (PENDING — Phase 6)

`retryguard.py` does not exist yet. It must be placed at the path specified in `infra.retryguard_script` on the master before any RetryGuard condition can run.

The script must:
- Accept `--params /tmp/retryguard_params.json` (the runner uploads this JSON before starting)
- Poll per-service rejection rates (from Istio/Envoy sidecar metrics or from `metric_collector.py` output)
- Apply Algorithm 1 from the RetryGuard paper (Sec. 4): count consecutive windows above/below threshold; patch Istio VirtualService via `kubernetes.client.CustomObjectsApi`
- Log every toggle event with timestamp, service name, and old→new retry count

Parameters passed via JSON (all configurable from the YAML):
```json
{
  "rejection_threshold": 0.20,
  "window_duration_seconds": 30,
  "disable_windows": 2,
  "re_enable_windows": 3,
  "retry_attempts_on": 3,
  "retry_attempts_off": 0
}
```

### 6c. Create Istio VirtualService resources (PENDING — Phase 6)

Before any RetryGuard condition run, each Online Boutique service needs an Istio VirtualService resource with a default retry policy. RetryGuard patches these at runtime.

```bash
# Verify VirtualServices exist before running any RetryGuard condition
kubectl get virtualservices -n default
```

If they don't exist, create them (one per microservice) with:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: <service-name>
  namespace: default
spec:
  hosts:
    - <service-name>
  http:
    - retries:
        attempts: 3
        retryOn: "5xx,reset,connect-failure"
      route:
        - destination:
            host: <service-name>
```

### 6d. Validate metric_collector startup timing (KNOWN ISSUE)

`metric_collector.py` crashes with `KeyError: 'getcart'` if it starts before any Locust traffic is flowing — the proxy has no metrics for endpoints with zero requests. The runner starts `metric_collector` before Locust and relies on Locust connecting fast enough.

**Mitigation options:**
1. Move `metric_collector` start to after Locust is verified running (reorder in `start_master_stack` / `start_locust`)
2. Add a retry loop inside `metric_collector.py` itself (wrap the `metric[api]` lookup in a try/except and sleep)

The runner currently starts `metric_collector` during `start_master_stack()` and Locust shortly after. If Locust takes longer than expected to connect workers, `metric_collector` may crash before traffic appears.

---

## 7. Infrastructure Notes (Context for Agents)

### VM layout

| Host alias | Role | Private IP |
|------------|------|-----------|
| `topfull-master` | K8s control plane, proxy, RL, metrics | `10.128.0.3` |
| `topfull-worker-1` | All Online Boutique pods (2/2 with Istio sidecar) | `10.128.0.4` |
| `topfull-load` | Locust only | `10.128.0.2` |

### Cluster topology

- Master is **tainted** (`node-role.kubernetes.io/control-plane:NoSchedule`) — application pods schedule only on worker-1
- All 12 Online Boutique pods run on `topfull-worker-1`, all `2/2 Running` (app + Istio Envoy sidecar)
- Frontend exposed as NodePort `30440` on the master
- TopFull Go proxy runs on master port `8090`; Locust routes all traffic through it

### Key paths on master

```
/home/idozacharia/TopFull/
  TopFull_master/online_boutique_scripts/src/   ← deploy_rl.py, metric_collector.py, global_config.json, logs/
  TopFull_master/online_boutique_scripts/src/proxy/  ← proxy_online_boutique.go
  venv/                                          ← Python virtualenv (Ray, kubernetes client, etc.)
```

### Known fixes already applied

These issues were encountered and fixed during Phase 4 setup. Do not revert them:

- `resource_collector.py` — `getcAdvisorIP()` dynamically fetches cAdvisor pod IPs via `kubectl get pods -n cadvisor` instead of a hardcoded 5-node list
- `locust_online_boutique.py` — event listeners updated from deprecated `events.request_success` / `events.request_failure` to `events.request` (Locust 2.x API)
- `online_boutique_create.sh` / `online_boutique_create2.sh` — CRLF line endings stripped; locust binary path changed from bare `locust` to full venv path `/home/idozacharia/TopFull/venv/bin/locust`
- Python packages pinned to Ray 2.0.0-compatible versions (protobuf, cloudpickle, numpy, pydantic, googleapis-common-protos) — do not upgrade these

### SSH from Windows

Use SSH aliases defined in `~/.ssh/config`. Always use `-o ControlMaster=no` for non-interactive commands (stale multiplexed connections cause hangs). The runner already does this.

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -o ControlMaster=no topfull-master "kubectl get nodes"
```

VMs are stopped between sessions to save cost. After restarting, refresh `HostName` in `~/.ssh/config` if IPs changed:
```powershell
gcloud compute instances list --project=networks-workshop --format="json(name,networkInterfaces[0].accessConfigs[0].natIP)"
```
