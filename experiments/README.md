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

**Phase 7 campaign (COMPLETE 2026-09-06):** 48-run matrix on free slots, all collectors on. Local copies: `experiments/results/campaign_48/`, organized into 7 scenario subfolders (`S1_normal_op/` … `S6_forced_recovery/` — see [experiments/results/campaign_48/README.md](results/campaign_48/README.md)). Historical August 38: `experiments/results/august_38/` (still flat). See [PHASE7-RESOLVE-GAPS-1-3.md](../Guides%20and%20Info/PHASE7-RESOLVE-GAPS-1-3.md). Do not use `run_all_scenarios.py` — it would overwrite the August folders **on master**.

---

## Pulling results to your PC

The runner prints the exact `scp` command after each run, already pointed at the correct scenario subfolder:

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1 experiments/results/campaign_48/S2_sustained_overload/
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
| `retryguard.sample_interval_seconds` | int | Loop cadence — seconds between raw samples (paper default: 1) |
| `retryguard.interval_samples` | int | Paper's `Interval` — consecutive samples required to transition, applied symmetrically to both ON and OFF (paper default: 30, i.e. 30s at a 1s sample interval) |
| `retryguard.retry_attempts_on` | int | Istio retries.attempts when enabled |
| `retryguard.retry_attempts_off` | int | Istio retries.attempts when disabled |
| `envoy_retry_collector.enabled` | bool | Whether to scrape Envoy outbound retry counters (default true in all configs) |
| `envoy_retry_collector.poll_interval_seconds` | int | Scrape interval (default 1) |
| `envoy_retry_collector.transport` | string | `network_prometheus` (master HTTP GET to each pod `:15020`). YAMLs default to this; the only supported value |
| `envoy_retry_collector.max_workers` | int | Thread-pool size for parallel HTTP GET+parse (default 4) |
| `resource_usage_collector.enabled` | bool | Whether to scrape CPU/memory per service (default true in all configs) |
| `resource_usage_collector.poll_interval_seconds` | int | Scrape interval (default 5) |
| `topfull_throttle_collector.enabled` | bool | Whether to scrape TopFull cap/admitted + detector reconstruction (default true in all configs) |
| `topfull_throttle_collector.poll_interval_seconds` | int | Scrape interval (default 1) |
| `log_folder` | string | Output folder name (on master under `results_base_path`) |
| `infra.*` | map | SSH hosts, paths, venv — override if your setup differs |
| `infra.retryguard_script` | string | Path to `retryguard.py` on master |
| `infra.envoy_retry_collector_script` | string | Path to `envoy_retry_collector.py` on master |
| `infra.resource_usage_collector_script` | string | Path to `resource_usage_collector.py` on master |
| `infra.topfull_throttle_collector_script` | string | Path to `topfull_throttle_collector.py` on master |

### scale_constraints — method: replicas

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: replicas
    replicas: 1          # runner auto-detects original count and restores it
```

### scale_constraints — method: cpu_limit

Bottlenecks use a **fraction of the TopFull paper CPU quota** (not a hard-coded millicore string). Paper baselines live in `topfull_cpu_quotas.py` (e.g. checkout/payment **1000m**, productcatalog **500m**, default **1000m**). Absolute `cpu_limit: "…"` in YAML is rejected at run start.

```yaml
scale_constraints:
  - deployment: checkoutservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1   # 0.1 × paper → K8s limit AND Detector quota for this run
    container: server         # container name inside the pod
```

With fraction `0.1`: S3 checkout → **100m**, S4A productcatalog → **50m** (not comparable to `campaign_48/`’s absolute 100m), S4B payment → **100m**. Before load, the runner reconciles every Boutique service to paper limits, applies the fraction on the bottleneck, writes `topfull_run_quotas.json`, and patches Detector to load it. Teardown deletes the JSON and reconciles K8s back to paper (not “remove the limit”).

---

## Known limitations / TODOs

- **Offline per-service μ̂** — `python experiments/estimate_service_mu.py <run_dir>` prints λ / μ̂ / ρ from `service_inbound.csv` + `topfull_detect.csv` (stdlib only; no Locust / throttle inputs).
- **Retries-per-request in the existing matrix** — the finished 38 folders predate the Envoy collector; only new runs produce `envoy_retries_*.csv`. Close this with the 48-run campaign, not by mixing datasets. See PHASE7-DATA-GAPS.md Gap 3 and PHASE7-RESOLVE-GAPS-1-3.md.
