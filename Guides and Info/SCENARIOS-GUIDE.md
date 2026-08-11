# Experiment Scenarios Guide

RetryGuard on TopFull — TAU Communication Networks Workshop

---

## Overview

This guide describes the five experiment scenarios we run to measure RetryGuard's impact on the TopFull + Online Boutique stack. Each scenario is run under two conditions:

- **TopFull only** — TopFull overload control active, Istio default retries on, RetryGuard **off**.
- **TopFull + RetryGuard** — identical load and topology; only addition is RetryGuard **on**.

Because Locust generates randomized user behavior (non-deterministic), **every scenario must be run multiple times** under each condition. Compare results using averages/medians across runs, not single-run numbers.

### Folder naming convention

```
baseline_topfull_no_retryguard_<scenario>_run<N>/
run_topfull_retryguard_<scenario>_run<N>/
```

### Shared infrastructure — used in all scenarios

| Component | What it does |
|-----------|-------------|
| `online_boutique_create.sh` + `online_boutique_create2.sh` | Start Locust workers on the load-gen VM |
| `deploy_rl.py` | TopFull RL rate controller on master |
| `proxy_online_boutique.go` | TopFull Go proxy on master (port 8090 / 30440) |
| `metric_collector.py` | Writes goodput, latency, rejection CSVs to `logs/` |
| `resource_collector.py` | Writes CPU/memory/pod count via cAdvisor |
| RetryGuard script | Reads Istio/Envoy rejection rates, patches VirtualService CRDs |

---

## How to Run — Automated Runner

All scenarios are executed through `experiments/run_scenario.py`, which runs on Windows and orchestrates everything (pre-flight, constraints, stack startup, Locust, results collection, restore) over SSH. The manual tmux steps in each scenario below are kept for reference but are **no longer needed** — the runner does all of them.

### Prerequisites (one-time)

```powershell
pip install pyyaml
```

SSH host aliases (`topfull-master`, `topfull-load`) must be configured in `~/.ssh/config`. See [CONNECT-VMS.md](CONNECT-VMS.md).

### General pattern

```powershell
# 0. Clear stale /tmp runner scripts (required if a previous run by a different
#    Linux user left them — /tmp sticky bit prevents overwriting another user's files)
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_locust_launch.sh"

# 1. Verify cluster is healthy before any run
ssh topfull-master "kubectl get nodes; kubectl get pods -n default"

# 2. Run a scenario (runner handles everything end-to-end)
python experiments/run_scenario.py experiments/configs/<config_file>.yaml

# 3. Pull results to your PC after the run completes
scp -r topfull-master:/home/idozacharia/experiments/results/<log_folder> experiments/results/

# 4. To repeat: bump run_number and log_folder in the YAML before the next run
#    e.g. run_number: 1 → 2, log_folder: ...run1 → ...run2
```

### Full experiment matrix — commands at a glance

Run each scenario **≥3 times per condition** (≥2 for Scenario 5 intervals). Bump `run_number` and `log_folder` in the YAML for each repeat.

| Scenario | Baseline config | RetryGuard config | Starting run# |
|----------|----------------|-------------------|---------------|
| 1 — Normal Op | `scenario_1_baseline.yaml` | `scenario_1_retryguard.yaml` | baseline→run3, RG→run2 (smoke used earlier runs) |
| 2 — Sustained Overload | `scenario_2_baseline.yaml` | `scenario_2_retryguard.yaml` | both→run1 |
| 3 — Targeted Bottleneck | `scenario_3_baseline.yaml` | `scenario_3_retryguard.yaml` | both→run2 (smoke used run1) |
| 4A — Topology (ProductCatalog) | `scenario_4a_baseline.yaml` | `scenario_4a_retryguard.yaml` | both→run1 |
| 4B — Topology (Payment) | `scenario_4b_baseline.yaml` | `scenario_4b_retryguard.yaml` | both→run1 |
| 5 — Interval tuning | — (no baseline) | `scenario_5_interval_{10,20,30,60}s.yaml` | all→run1 |

---

## Quick Reference — Experiment Matrix

| # | Scenario | Load shape | RetryGuard condition | Primary questions answered |
|---|----------|-----------|---------------------|---------------------------|
| 1 | Normal Operation | Flat RPS within capacity | Baseline + RetryGuard | Sanity check — non-intrusive under healthy load |
| 2 | Sustained Overload | Ramp to ρ > 1, hold 5–10 min | Baseline + RetryGuard | System-level gains, topology beneficiaries, chain propagation, controller interaction |
| 3 | Targeted Bottleneck | Full call-chain + one constrained service | Baseline + RetryGuard | Topology beneficiaries, chain propagation, controller interaction |
| 4 | Topology Position Comparison | Same as Targeted Bottleneck ×2 (different service) | Baseline + RetryGuard | Topology position sensitivity, topology beneficiaries, chain propagation |
| 5 | Re-enable Interval Tuning | Sustained Overload × {10s, 20s, 30s, 60s} | RetryGuard only, vary re-enable interval | Interval parameter sensitivity, combined equilibrium |

---

## Scenario 1 — Normal Operation

### What it tests

Does RetryGuard stay completely non-intrusive when the system is healthy? Under light, sustainable load the rejection rates at every service should stay well below the ~20% threshold. RetryGuard should detect this, make zero changes to any Istio VirtualService, and the two conditions (TopFull only vs TopFull + RetryGuard) should produce identical results.

This is a **required sanity check** before the core experiments. If RetryGuard modifies anything here, something is wrong with the threshold calibration.

### Open question answered

- **System-level gains** (non-overload side) — establishes the clean baseline where both conditions behave the same.

### Load setup

- Launch Locust with a **flat RPS target well within capacity** — no ramp, no overload.
- Use the standard `online_boutique_create.sh` / `online_boutique_create2.sh` scripts; reduce user count to a comfortable level.
- Run duration: 5 minutes is sufficient; the system should never approach ρ > 1.

### How to run

```powershell
# Baseline (RetryGuard off) — starts at run3 (run1+run2 were smoke runs)
python experiments/run_scenario.py experiments/configs/scenario_1_baseline.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_normal_op_run3 experiments/results/

# RetryGuard — starts at run2 (run1 was a smoke run)
python experiments/run_scenario.py experiments/configs/scenario_1_retryguard.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_normal_op_run2 experiments/results/
```

For each repeat: edit the YAML to bump `run_number` and update `log_folder` (e.g. `...run3` → `...run4`). Run ≥3 times per condition.

### What to look for

- RetryGuard log shows **zero VirtualService patches** — retries were never disabled.
- Goodput, latency, and rejection rate in both conditions are statistically identical.
- Any divergence signals a threshold or metrics-wiring problem.

---

## Scenario 2 — Sustained Overload (core experiment)

### What it tests

This is the main experiment. Start from normal load, then ramp Locust RPS until offered load exceeds system capacity (ρ > 1) and **hold that level for 5–10 minutes**. Once overloaded:

- TopFull's Go proxy throttles how many requests enter the cluster.
- Requests that do get through may still fail downstream (503/429).
- Istio then retries those failed calls internally — invisible to TopFull's rate limiter.
- This internal retry traffic creates a **retry storm**: one user request generates multiple backend attempts, keeping services overloaded even after TopFull has cut the entry rate.

RetryGuard watches per-service rejection rates. After rejections stay above ~20% for several consecutive ~30-second windows, it disables retries for that service by patching its Istio VirtualService. Load at the bottleneck drops; TopFull's 1-second RL loop detects the improved signals and may admit more traffic. The cycle repeats.

### Why the run must be 5–10 minutes, not 1–2

| Reason | Detail |
|--------|--------|
| Triggering alone takes ~1–2 min | Rejections must exceed ~20% for several consecutive ~30s windows before RetryGuard fires — a short test measures detection latency, not effect |
| Effect appears after suppression | Load drops, TopFull's RL re-settles, goodput recovers — this takes time |
| Cycle must repeat | 5–10 min lets the disable → recover → re-enable cycle fire multiple times, proving stable not one-off behavior |
| Matches RetryGuard's design target | RetryGuard is built for prolonged miscoordination, not brief spikes that default backoff/retry budgets already absorb |

### Open questions answered

- System-level gains
- Topology beneficiaries
- Chain propagation
- Controller interaction

### Load setup

- Ramp Locust user count up until goodput plateaus and rejection rates climb above 20%.
- Hold at that level for **at least 5 minutes** (10 minutes preferred for full cycle coverage).
- Use the standard `online_boutique_create.sh` / `online_boutique_create2.sh` scripts at high user counts.

### How to run

```powershell
# Baseline — run1 (never run before)
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1 experiments/results/

# RetryGuard — run1
python experiments/run_scenario.py experiments/configs/scenario_2_retryguard.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_sustained_overload_run1 experiments/results/
```

For each repeat: bump `run_number` and `log_folder` in the YAML. Run ≥3 times per condition.

To monitor RetryGuard live while the run is in progress:
```bash
ssh topfull-master "tmux attach -t retryguard"   # Ctrl+B, D to detach without killing
```

### What to look for

- In TopFull only: rejection rates stay elevated; retry counts per request > 0.
- In TopFull + RetryGuard: RetryGuard fires (VirtualService patches logged); retries/request drop; goodput may improve or hold steady with lower resource usage.
- TopFull's RL controller may increase admission rate after RetryGuard suppresses retries — watch for this interaction in the CSV metrics.

---

## Scenario 3 — Targeted Bottleneck

### What it tests

Instead of flooding the whole system, engineer a bottleneck at **one specific downstream service** (e.g., Checkout or a mid-chain service) by reducing its replica count or applying a CPU limit. The overall offered load need not exceed total cluster capacity — only this one service reaches ρ > 1 even under TopFull's throttled entry rate.

**How this differs from Sustained Overload:** Sustained Overload saturates everything (global ρ > 1), making it hard to attribute the effect to any single service. Here the stress is at one known node. This enables:
- **Clean attribution** — we know exactly which service is the bottleneck.
- **Surgical comparison** — TopFull's only lever is to throttle entire entry APIs that route through the bottleneck (blunt, indirect); RetryGuard acts directly at the hot spot.
- **Propagation tracing** — we can watch whether reduced load at the bottleneck propagates upward through the call chain.

This scenario is directly analogous to the RetryGuard Bookinfo case study in the paper (Sec. 6.2 — Reviews service with slow HPA vs. Product service with fast HPA).

### Open questions answered

- Topology beneficiaries
- Chain propagation
- Controller interaction

### Load setup

- Normal-to-moderate Locust load that exercises the full call chain (all 5 APIs: `getcart`, `getproduct`, `postcheckout`, `postcart`, `emptycart`).
- Constrain one service **before** starting load — either:
  - Scale down replicas: `kubectl scale deployment <svc> --replicas=1`
  - Or apply a CPU limit via a resource patch on the deployment.

**Suggested bottleneck service:** `checkoutservice` (sits in a critical path: Frontend → Checkout → Cart, Shipping, Currency, ProductCatalog, Email, Payment).

### How to run

The runner automatically applies the `checkoutservice` CPU limit (`100m`) before load starts and removes it after the run — no manual `kubectl` needed.

```powershell
# Baseline — starts at run2 (smoke used run1)
python experiments/run_scenario.py experiments/configs/scenario_3_baseline.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_targeted_bottleneck_run2 experiments/results/

# RetryGuard — starts at run2 (smoke used run1)
python experiments/run_scenario.py experiments/configs/scenario_3_retryguard.yaml
# Pull results:
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_targeted_bottleneck_run2 experiments/results/
```

For each repeat: bump `run_number` and `log_folder` in the YAML. Run ≥3 times per condition.

After all runs, verify the constraint was fully restored:
```bash
ssh topfull-master "kubectl get deployment checkoutservice -o jsonpath='{.spec.template.spec.containers[0].resources}'"
# Should show no cpu limit (or the original value before the experiment)
```

### What to look for

- TopFull throttles entry APIs routing through the constrained service (blunt/indirect).
- RetryGuard detects the bottleneck service's rejection rate directly and suppresses retries at that exact node.
- Check whether reduced load at the bottleneck propagates upward: does the service that calls the bottleneck (e.g., Frontend → Checkout) also see improved metrics?

---

## Scenario 4 — Topology Position Comparison

### What it tests

Two Targeted Bottleneck runs using identical load and the same constraint method, differing **only in which service is constrained**. This isolates the effect of the bottleneck's structural position in the call graph.

**Why this is a separate scenario from Scenario 3:** Scenario 3 establishes *that* per-service suppression helps. This scenario holds that result constant and varies only position — changing one variable at a time so the position effect is attributable.

| Run | Service constrained | Position description | TopFull's entry signal |
|-----|--------------------|-----------------------|------------------------|
| **Run A** | `productcatalogservice` | Gateway-adjacent, directly controlled | Frontend calls ProductCatalog directly on many product-browse paths; TopFull maps and throttles this bottleneck most directly at entry |
| **Run B** | `paymentservice` | Indirect, Checkout-mediated | Reachable only via Frontend → Checkout → Payment; TopFull's signal is mediated by Checkout and most attenuated; Istio retries stack at Checkout→Payment |

**Scope note:** Online Boutique is a shallow topology. This contrasts the *directness* of TopFull's control (direct vs Checkout-mediated) and fan-in (many direct entry APIs vs one mediated path), not literal chain depth. State this as a limitation in the report.

### Open questions answered

- Topology position sensitivity
- Topology beneficiaries
- Chain propagation

### Load setup

Same as Scenario 3 — normal-to-moderate Locust load, full call chain exercised.

### How to run

The runner applies and removes the CPU constraint automatically for both 4A and 4B. Finish all runs for one position before starting the other.

**Run 4A — ProductCatalog bottleneck (gateway-adjacent):**

```powershell
# Baseline — run1
python experiments/run_scenario.py experiments/configs/scenario_4a_baseline.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_topology_position_A_run1 experiments/results/

# RetryGuard — run1
python experiments/run_scenario.py experiments/configs/scenario_4a_retryguard.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_topology_position_A_run1 experiments/results/
```

**Run 4B — Payment bottleneck (Checkout-mediated):**

```powershell
# Baseline — run1
python experiments/run_scenario.py experiments/configs/scenario_4b_baseline.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_topology_position_B_run1 experiments/results/

# RetryGuard — run1
python experiments/run_scenario.py experiments/configs/scenario_4b_retryguard.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_topology_position_B_run1 experiments/results/
```

For each repeat: bump `run_number` and `log_folder` in the YAML. Run ≥3 times per condition per position.

### What to look for

- Does RetryGuard's benefit differ between Run A and Run B?
- In Run A: TopFull detects ProductCatalog overload quickly via direct entry API mapping. Does RetryGuard add meaningful value on top of that?
- In Run B: TopFull's signal must travel through Checkout before reaching the Payment path. Does RetryGuard's per-service suppression at Payment provide greater relative benefit here?
- Compare: retries/request, rejection rate, and goodput for the constrained service and its upstream callers across both positions.

---

## Scenario 5 — Re-enable Interval Tuning

### What it tests

RetryGuard's re-enable interval controls how long rejection rates must stay below ~20% before retries are turned back on. The paper's default is 30 seconds, tuned without a co-running top-down overload controller. Since TopFull's RL adjusts admission every ~1 second, the recovery dynamics after overload may be faster or more oscillatory than in the original experiments.

**What happens:** After RetryGuard disables retries, overload eases. TopFull's RL may then admit more traffic because goodput/latency signals improve. If RetryGuard re-enables retries **too soon**, internal retries restart before the bottleneck has truly cleared and overload returns. If it waits **too long**, the system stays retry-free after recovery and goodput remains artificially suppressed.

This scenario finds the interval that gives the best combined goodput and stability when both systems run together.

### Open questions answered

- Interval parameter sensitivity
- Combined equilibrium

### Load setup

Same as Scenario 2 (Sustained Overload) — ramp to ρ > 1, hold for 5–10 minutes. Keep load, replica counts, and RetryGuard threshold (~20%) **fixed**. Only the re-enable interval changes between runs.

### Intervals to test

| Interval | Description |
|----------|-------------|
| 10s | Aggressive — re-enables fast; risk of oscillation |
| 20s | Below paper default |
| **30s** | Paper default (Sec. 6.2) |
| 60s | Conservative — slower recovery of goodput |

### How to run

The `re_enable_windows` parameter is already set correctly in each config — no manual script editing needed. There is no separate baseline for Scenario 5; use Scenario 2's baseline runs as the comparison.

```powershell
# 10s effective wait (re_enable_windows: 1) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_10s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_10s_run1 experiments/results/

# 20s effective wait (re_enable_windows: 2) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_20s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_20s_run1 experiments/results/

# 30s effective wait (re_enable_windows: 3) — paper default — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_30s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_30s_run1 experiments/results/

# 60s effective wait (re_enable_windows: 6) — run1
python experiments/run_scenario.py experiments/configs/scenario_5_interval_60s.yaml
scp -r topfull-master:/home/idozacharia/experiments/results/run_topfull_retryguard_interval_60s_run1 experiments/results/
```

For each repeat: bump `run_number` and `log_folder` in the YAML. Run ≥2 times per interval.

After all four intervals are done, compare:
- Goodput over time (does it recover after RetryGuard fires?)
- Number of toggle events logged (too many = oscillation)
- Time-to-recovery after first disable event

### What to look for

- Which interval avoids oscillation while allowing the fastest goodput recovery?
- Does the 30s paper default perform well, or does TopFull's 1s RL loop change the optimal point?
- Log the exact timestamps of every disable and re-enable event to reconstruct the full cycle timeline.

---

## Metrics Checklist — Collect for Every Run

| Layer | Tool | What to collect |
|-------|------|----------------|
| System & API performance | `metric_collector.py` → `logs/*.csv` | Goodput (rps), P99 latency, rejection rate per API |
| Retries | `metric_collector.py` | Retries per request — the most direct measure of RetryGuard's effect |
| Resource usage | `resource_collector.py` (cAdvisor) | CPU, memory per pod; pod replica counts (`num_instances.csv`) |
| Controller state | RetryGuard script logs | Which services had retries toggled, and when; time between disable and re-enable |
| TopFull state | `overload_detection.py` logs | Which APIs were flagged as overloaded and at what priority |

Cross-reference Layer 3 (RetryGuard decisions) with Layer 1 (API-level metrics) and Layer 2 (resource usage) when interpreting results. RetryGuard reads Istio/Envoy sidecar metrics directly — a separate measurement point from TopFull's entry-proxy collectors.

---

## Key RetryGuard Parameters (from paper Sec. 6.2)

| Parameter | Default | Notes |
|-----------|---------|-------|
| Rejection threshold | ~20% | `rejection_rate > 0.20` triggers the disable window counter |
| Measurement window | ~30s | One window = one observation period |
| Windows to disable | N consecutive windows above threshold | Prevents single-spike false positives |
| Windows to re-enable | N consecutive windows below threshold | Scenario 5 varies this |
| Retry attempts when disabled | 0 | Patched into Istio VirtualService |
| Retry attempts when enabled | 3 | Default Istio retry count; restore on re-enable |

---

*Sources: `PRESENTATION-GUIDE.md` §5–7, `WORKPLAN.md` Phases 5–6 and Experiment Matrix, `NOTEBOOKLM-PROMPT.md` §Slides 13–18, RetryGuard paper Sec. 4 and Sec. 6.2.*
