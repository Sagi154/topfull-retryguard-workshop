# Phase 5 & Phase 6 — Run List

TopFull + RetryGuard Workshop — TAU Deepness Lab

> **Purpose:** Exact checklist of every run needed to complete Phases 5 and 6. Check off each run as it completes and results are pulled locally.
>
> **Before starting any session:** verify cluster health — `ssh topfull-master "kubectl get nodes; kubectl get pods -n default"`. IPs change after VM restarts; refresh `~/.ssh/config` if SSH fails (see [CONNECT-VMS.md](CONNECT-VMS.md)).
>
> **Progress (2026-08-15):** Full 38-slot matrix finished via `experiments/run_all_scenarios.py --yes --resume 9` (slots 10–38) plus a one-off re-run of **slot 17** (S3 RetryGuard run2; earlier collect failed on a stale `idozacharia`-owned folder). Soft verify warnings about `retryguard.log` missing `START` are false positives (timestamped `START` lines are present).
>
> **Where results live (local, as of 2026-09-06):**
> - **Campaign (Phase 7 primary):** `experiments/results/campaign_48/`
> - **This August 38 matrix (historical):** `experiments/results/august_38/` — all 38 folders, including S1×6 and S2 baseline×3 that used to live only on Ido’s machine / master.

---

## Phase 5 — Baseline (RetryGuard OFF)

Scenarios 1–4, ≥3 runs each. TopFull active, Istio default retries on, RetryGuard not running.

### How to repeat a run

Before each repeat, open the YAML and bump two fields (or use `run_all_scenarios.py`, which patches these automatically):
```yaml
run_number: 2          # was 1
log_folder: baseline_topfull_no_retryguard_sustained_overload_run2   # was _run1
```

---

### Scenario 1 — Normal Operation (5 min each)

Config: `experiments/configs/scenario_1_baseline.yaml` · **run1–run3** (matrix; results on Ido’s machine — copy locally)

- [x] **Run 1** — `baseline_topfull_no_retryguard_normal_op_run1`
- [x] **Run 2** — `baseline_topfull_no_retryguard_normal_op_run2`
- [x] **Run 3** — `baseline_topfull_no_retryguard_normal_op_run3`

---

### Scenario 2 — Sustained Overload (10 min each)

Config: `experiments/configs/scenario_2_baseline.yaml` · **run1–run3** (on master; pull locally if needed)

- [x] **Run 1** — `baseline_topfull_no_retryguard_sustained_overload_run1`
- [x] **Run 2** — `baseline_topfull_no_retryguard_sustained_overload_run2`
- [x] **Run 3** — `baseline_topfull_no_retryguard_sustained_overload_run3`

```powershell
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run1 experiments/results/
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run2 experiments/results/
scp -r topfull-master:/home/idozacharia/experiments/results/baseline_topfull_no_retryguard_sustained_overload_run3 experiments/results/
```

---

### Scenario 3 — Targeted Bottleneck / checkoutservice (10 min each)

Config: `experiments/configs/scenario_3_baseline.yaml` · **run1–run3** (local)

The runner applies and removes the `checkoutservice` CPU limit (`100m`) automatically.

- [x] **Run 1** — `baseline_topfull_no_retryguard_targeted_bottleneck_run1`
- [x] **Run 2** — `baseline_topfull_no_retryguard_targeted_bottleneck_run2`
- [x] **Run 3** — `baseline_topfull_no_retryguard_targeted_bottleneck_run3`

---

### Scenario 4A — Topology: productcatalogservice (10 min each)

Config: `experiments/configs/scenario_4a_baseline.yaml` · **run1–run3** (local)

- [x] **Run 1** — `baseline_topfull_no_retryguard_topology_position_A_run1`
- [x] **Run 2** — `baseline_topfull_no_retryguard_topology_position_A_run2`
- [x] **Run 3** — `baseline_topfull_no_retryguard_topology_position_A_run3`

---

### Scenario 4B — Topology: paymentservice (10 min each)

Config: `experiments/configs/scenario_4b_baseline.yaml` · **run1–run3** (local)

- [x] **Run 1** — `baseline_topfull_no_retryguard_topology_position_B_run1`
- [x] **Run 2** — `baseline_topfull_no_retryguard_topology_position_B_run2`
- [x] **Run 3** — `baseline_topfull_no_retryguard_topology_position_B_run3`

---

### Phase 5 time estimate

| Scenario | Runs | Duration each | Total |
|----------|------|--------------|-------|
| S1 baseline | 3 | 5 min | 15 min |
| S2 baseline | 3 | 10 min | 30 min |
| S3 baseline | 3 | 10 min | 30 min |
| S4A baseline | 3 | 10 min | 30 min |
| S4B baseline | 3 | 10 min | 30 min |
| **Total** | **15** | | **≈2h 15min** |

Add a few minutes per run for startup/teardown and time between runs to let the cluster settle.

---

---

## Phase 6 — RetryGuard ON

Scenarios 1–4 with RetryGuard enabled, ≥3 runs each. Plus Scenario 5 interval sweep (4 configs × ≥2 runs each).

---

### Scenario 1 — Normal Operation + RetryGuard (5 min each)

Config: `experiments/configs/scenario_1_retryguard.yaml` · **run1–run3** (on Ido’s machine — copy locally)

**Expected:** zero VirtualService patches in `retryguard.log`. If any toggle fires, stop — threshold needs investigation.

- [x] **Run 1** — `run_topfull_retryguard_normal_op_run1`
- [x] **Run 2** — `run_topfull_retryguard_normal_op_run2`
- [x] **Run 3** — `run_topfull_retryguard_normal_op_run3`

---

### Scenario 2 — Sustained Overload + RetryGuard (10 min each)

Config: `experiments/configs/scenario_2_retryguard.yaml` · **run1–run3** (local)

Monitor RetryGuard live if you want: `ssh topfull-master "tmux attach -t retryguard"` (Ctrl+B, D to detach).

- [x] **Run 1** — `run_topfull_retryguard_sustained_overload_run1`
- [x] **Run 2** — `run_topfull_retryguard_sustained_overload_run2`
- [x] **Run 3** — `run_topfull_retryguard_sustained_overload_run3`

---

### Scenario 3 — Targeted Bottleneck + RetryGuard (10 min each)

Config: `experiments/configs/scenario_3_retryguard.yaml` · **run1–run3** (local; run2 re-done 2026-08-15 after collect failure)

- [x] **Run 1** — `run_topfull_retryguard_targeted_bottleneck_run1`
- [x] **Run 2** — `run_topfull_retryguard_targeted_bottleneck_run2`
- [x] **Run 3** — `run_topfull_retryguard_targeted_bottleneck_run3`

---

### Scenario 4A — Topology: productcatalogservice + RetryGuard (10 min each)

Config: `experiments/configs/scenario_4a_retryguard.yaml` · **run1–run3** (local)

- [x] **Run 1** — `run_topfull_retryguard_topology_position_A_run1`
- [x] **Run 2** — `run_topfull_retryguard_topology_position_A_run2`
- [x] **Run 3** — `run_topfull_retryguard_topology_position_A_run3`

---

### Scenario 4B — Topology: paymentservice + RetryGuard (10 min each)

Config: `experiments/configs/scenario_4b_retryguard.yaml` · **run1–run3** (local)

- [x] **Run 1** — `run_topfull_retryguard_topology_position_B_run1`
- [x] **Run 2** — `run_topfull_retryguard_topology_position_B_run2`
- [x] **Run 3** — `run_topfull_retryguard_topology_position_B_run3`

---

### Scenario 5 — Re-enable Interval Sweep (10 min each)

RetryGuard only — no separate baseline needed (Scenario 2 baseline is the comparison). Run all 4 interval configs, ≥2 runs each. The `re_enable_windows` value is already set correctly in each config.

| Config | `re_enable_windows` | Effective wait |
|--------|--------------------|--------------------|
| `scenario_5_interval_10s.yaml` | 1 | 30s |
| `scenario_5_interval_20s.yaml` | 2 | 60s |
| `scenario_5_interval_30s.yaml` | 3 | 90s **(paper default)** |
| `scenario_5_interval_60s.yaml` | 6 | 180s |

**10s interval (re_enable_windows: 1):**
- [x] **Run 1** — `run_topfull_retryguard_interval_10s_run1`
- [x] **Run 2** — `run_topfull_retryguard_interval_10s_run2`

**20s interval (re_enable_windows: 2):**
- [x] **Run 1** — `run_topfull_retryguard_interval_20s_run1`
- [x] **Run 2** — `run_topfull_retryguard_interval_20s_run2`

**30s interval — paper default (re_enable_windows: 3):**
- [x] **Run 1** — `run_topfull_retryguard_interval_30s_run1`
- [x] **Run 2** — `run_topfull_retryguard_interval_30s_run2`

**60s interval (re_enable_windows: 6):**
- [x] **Run 1** — `run_topfull_retryguard_interval_60s_run1`
- [x] **Run 2** — `run_topfull_retryguard_interval_60s_run2`

---

### Phase 6 time estimate

| Scenario | Runs | Duration each | Total |
|----------|------|--------------|-------|
| S1 RetryGuard | 3 | 5 min | 15 min |
| S2 RetryGuard | 3 | 10 min | 30 min |
| S3 RetryGuard | 3 | 10 min | 30 min |
| S4A RetryGuard | 3 | 10 min | 30 min |
| S4B RetryGuard | 3 | 10 min | 30 min |
| S5 × 4 intervals | 2 each | 10 min | 80 min |
| **Total** | **23** | | **≈3h 35min** |

---

## Combined totals

| | Runs | VM time |
|--|------|---------|
| Phase 5 | 15 | ≈2h 15min |
| Phase 6 | 23 | ≈3h 35min |
| **Grand total** | **38** | **≈5h 50min** |

**Matrix execution status:** all 38 slots completed (2026-08-11 slots 1–9; 2026-08-15 slots 10–38 + slot 17 re-run).

---

## After each run — quick checklist

1. **Row count:** `wc -l` on the CSVs on master (or after pulling) — should be ≈`duration_seconds`.
2. **RPS > 0:** open any CSV, confirm `RPS` is non-zero after the first ~10 rows.
3. **Pull results** with the `scp` command above before starting the next run.
4. **Bump YAML** (`run_number` + `log_folder`) before the next repeat.
5. **RetryGuard runs only:** check `retryguard.log` exists and contains a `START` line (may be preceded by `WAITING`/`READY`; verifier that requires `START` at line start can false-alarm).

Full verification checklist: [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) §7.

---

*Related: [SCENARIOS-GUIDE.md](SCENARIOS-GUIDE.md) (scenario details + run commands), [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md) (what each run produces), [PHASE5-EXPERIMENTS-GUIDE.md](PHASE5-EXPERIMENTS-GUIDE.md) (runner reference).*
