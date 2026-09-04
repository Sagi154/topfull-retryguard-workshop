# Experiments — Runner and Scenario Configs

This folder contains the experiment runner and per-scenario YAML configs for the TopFull + RetryGuard evaluation.

---

## Prerequisites

```powershell
pip install pyyaml
```

SSH aliases must be configured in `~/.ssh/config`:

```
Host topfull-master
  HostName <master-public-ip>
  User idoza
  IdentityFile ~/.ssh/id_ed25519

Host topfull-load
  HostName <loadgen-public-ip>
  User idoza
  IdentityFile ~/.ssh/id_ed25519
```

---

## Running an experiment

```powershell
# From the repo root
python experiments/run_scenario.py experiments/configs/scenario_2_baseline.yaml
```

The runner will:
1. Check cluster health (SSH to master, verify nodes + pods)
2. Clear previous logs on master
3. Apply topology constraints (`kubectl scale` or CPU limit)
4. Start proxy → deploy_rl → metric_collector in tmux sessions on master
5. Optionally start RetryGuard
6. Start Locust on the loadgen VM
7. Wait for `duration_seconds` with a progress bar
8. Stop everything cleanly
9. Copy logs to `results_base_path/<log_folder>/` on master
10. Restore any topology constraints

---

## Config files

| File | Scenario | Condition | Duration |
|------|----------|-----------|----------|
| `scenario_1_baseline.yaml` | Normal Operation | baseline | 5 min |
| `scenario_1_retryguard.yaml` | Normal Operation | RetryGuard on | 5 min |
| `scenario_2_baseline.yaml` | Sustained Overload | baseline | 10 min |
| `scenario_2_retryguard.yaml` | Sustained Overload | RetryGuard on | 10 min |
| `scenario_3_baseline.yaml` | Targeted Bottleneck (checkout) | baseline | 10 min |
| `scenario_3_retryguard.yaml` | Targeted Bottleneck (checkout) | RetryGuard on | 10 min |
| `scenario_4a_baseline.yaml` | Topology Position A (productcatalog) | baseline | 10 min |
| `scenario_4a_retryguard.yaml` | Topology Position A (productcatalog) | RetryGuard on | 10 min |
| `scenario_4b_baseline.yaml` | Topology Position B (payment) | baseline | 10 min |
| `scenario_4b_retryguard.yaml` | Topology Position B (payment) | RetryGuard on | 10 min |
| `scenario_5_interval_10s.yaml` | Interval Tuning — 10s label (30s wait); **S6 load** | RetryGuard on | 15 min |
| `scenario_5_interval_20s.yaml` | Interval Tuning — 20s label (60s wait); **S6 load** | RetryGuard on | 15 min |
| `scenario_5_interval_30s.yaml` | Interval Tuning — 30s label (90s wait); **S6 load** | RetryGuard on | 15 min |
| `scenario_5_interval_60s.yaml` | Interval Tuning — 60s label (180s wait); **S6 load** | RetryGuard on | 15 min |
| `scenario_6_recovery_baseline.yaml` | Forced Recovery | baseline | 15 min |
| `scenario_6_recovery_retryguard.yaml` | Forced Recovery | RetryGuard on | 15 min |

---

## Repeating runs

Increment `run_number` and update `log_folder` before each repeat:

```yaml
run_number: 2
log_folder: baseline_topfull_no_retryguard_sustained_overload_run2
```

Aim for **3 runs minimum** per scenario/condition. Compare using averages/medians.

**Phase 7 campaign (2026-09-04):** the next 3 repeats are a new 48-run matrix on free slots (S1/S2/S3/S4A/S4B/S6 × both arms × 3, plus S5 × 4 intervals × 3), not a replay of `run1–3`. See [PHASE7-RESOLVE-GAPS-1-3.md](../Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md). Do not use `run_all_scenarios.py` for this — it would overwrite the August folders.

---

## Pulling results to your PC

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1 experiments/results/
```

---

## Config schema reference

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | int | 1–6 |
| `scenario_name` | string | Human-readable name |
| `condition` | string | `baseline` or `retryguard` |
| `run_number` | int | Repeat index (increment per run) |
| `duration_seconds` | int | How long to hold load |
| `locust.user_counts` | map | Per-endpoint target users (**TODO**: not yet wired into create scripts) |
| `locust.scripts` | list | Which create scripts to run on loadgen |
| `scale_constraints` | list | Topology manipulations (see below) |
| `retryguard.enabled` | bool | Whether to start RetryGuard |
| `retryguard.rejection_threshold` | float | Fraction (0–1) to trigger disable counter |
| `retryguard.window_duration_seconds` | int | Length of one observation window |
| `retryguard.disable_windows` | int | Consecutive windows above threshold → disable |
| `retryguard.re_enable_windows` | int | Consecutive windows below threshold → re-enable |
| `retryguard.retry_attempts_on` | int | Istio retries.attempts when enabled |
| `retryguard.retry_attempts_off` | int | Istio retries.attempts when disabled |
| `envoy_retry_collector.enabled` | bool | Whether to scrape Envoy outbound retry counters (default true in all configs) |
| `envoy_retry_collector.poll_interval_seconds` | int | Scrape interval (default 5) |
| `resource_usage_collector.enabled` | bool | Whether to scrape CPU/memory per service (default true in all configs) |
| `resource_usage_collector.poll_interval_seconds` | int | Scrape interval (default 5) |
| `log_folder` | string | Output folder name (on master under `results_base_path`) |
| `infra.*` | map | SSH hosts, paths, venv — override if your setup differs |
| `infra.retryguard_script` | string | Path to `retryguard.py` on master |
| `infra.envoy_retry_collector_script` | string | Path to `envoy_retry_collector.py` on master |
| `infra.resource_usage_collector_script` | string | Path to `resource_usage_collector.py` on master |

### scale_constraints — method: replicas

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: replicas
    replicas: 1          # runner auto-detects original count and restores it
```

### scale_constraints — method: cpu_limit

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit: "100m"    # applied via kubectl patch
    container: server    # container name inside the pod
```

The runner removes the cpu limit after the run via a JSON Patch.

---

## Known limitations / TODOs

- **Retries-per-request in the existing matrix** — the finished 38 folders predate the Envoy collector; only new runs produce `envoy_retries_*.csv`. Close this with the 48-run campaign, not by mixing datasets. See PHASE7-DATA-GAPS.md Gap 3 and PHASE7-RESOLVE-GAPS-1-3.md.
