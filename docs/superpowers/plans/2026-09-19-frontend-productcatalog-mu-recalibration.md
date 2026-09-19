# Frontend / productcatalog μ recalibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop treating run-shutdown reset bursts as saturation, then re-calibrate `frontend` and `productcatalogservice` at constrained CPU so today's Locust load produces a real mid-run `mu_sat` with preferably ≥10 ticks (ok-or-better confidence).

**Architecture:** One shared helper in `estimate_service_mu.py` drops the last 5 ticks of every service series from `mu_sat` candidacy; `capacity_frozen.py` counts the same trimmed set. Two new TopFull-off / RetryGuard-off calibration YAMLs reuse existing load profiles but set `cpu_limit_fraction: 0.1` (frontend → 100m, productcatalog → 50m). Freeze only those two services from the new folders; leave checkout/payment's existing freeze alone.

**Tech Stack:** Python 3 stdlib (`unittest`), existing `run_scenario.py` / `pull_results.py` over SSH, PowerShell on this Windows workstation.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-19-frontend-productcatalog-mu-recalibration-design.md`
- `SAT_TAIL_TRIM_TICKS = 5`, unconditional, every service. Position-in-series only — no shutdown-log heuristic.
- `SAT_5XX_FRACTION` stays `0.05`. Do not retune it to force ticks.
- `LOW_CONFIDENCE_SAT_TICKS` stays `10`. If a new freeze still has `n_sat_ticks < 10`, keep the `low_confidence` note; do not loosen the gate.
- Do not touch `retryguard.py`.
- Do not change Locust user counts / spawn rate / workers on any existing S1–S6 YAML. The CPU-constraint lever is the load-intensity change.
- Do not re-freeze `checkoutservice` or `paymentservice`. Do not freeze from S3 RG run8.
- Never overwrite an existing results folder. New calibration configs start at `run1` with new `log_folder` names. Do not bump/reuse `baseline_no_topfull_sustained_overload_run2` or `calibration_productcatalog_full_cpu_run1`.
- `cluster_shape` must stay `topfull-worker-1=e2-standard-16`. Stop if the worker is a different SKU.
- SSH aliases only (`topfull-master`, `topfull-worker-1`, `topfull-load`). Connect as `idozacharia`.
- Millicore source is `service_capacity.json`, never `topfull_run_quotas.json`.
- **300 s cool-off after Task 0 declares Ready, before the first Locust run; 300 s cool-off after the first calibration run exits, before the second starts.** Clock starts when `run_scenario.py` exits. `pull_results.py` may run *during* that wait (local `scp`, not extra cluster load). Do not skip or shorten this.
- Best effort, one attempt per service. If mid-run `mu_sat` is still `None` after one constrained run, record that honestly. Do not add a second load-gen pass or lower the trim.

## File map

| File | Role |
|---|---|
| `experiments/estimate_service_mu.py` | `SAT_TAIL_TRIM_TICKS`, `saturating_ticks()`, `summarize_service` uses it |
| `experiments/test_estimate_service_mu.py` | Tail-trim tests; pad existing 1-tick sat tests with 5 healthy trailing ticks |
| `experiments/capacity_frozen.py` | `count_sat_ticks` uses `saturating_ticks` |
| `experiments/test_capacity_frozen.py` | Freeze inbound CSVs get a 5-tick healthy tail so sat is not in the trimmed window |
| `experiments/configs/scenario_calibration_frontend_constrained.yaml` | New. S2 no-TopFull load, frontend 100m |
| `experiments/configs/scenario_calibration_productcatalog_constrained.yaml` | New. Existing productcatalog cal load, productcatalog 50m |
| `experiments/capacity/capacity_frozen.json` | Written by freeze CLI in Task 4, not by hand |
| `experiments/capacity/README.md`, `AGENTS.md` | After freeze + S1/S2 `rho_hat` re-check |

Do **not** edit `scenario_2_baseline_no_topfull.yaml` or `scenario_calibration_productcatalog_full_cpu.yaml` — those remain the historical full-CPU attempts.

Task order: Task 1 (local code) → Task 2 (YAMLs) → Task 0 (VMs) → Task 3 (runs + cool-offs) → Task 4 (freeze + docs). Do not start VMs during Task 1 or Task 2.

---

### Task 1: Estimator — drop the last 5 ticks from `mu_sat`

**Files:**
- Modify: `experiments/estimate_service_mu.py`
- Modify: `experiments/test_estimate_service_mu.py`
- Modify: `experiments/capacity_frozen.py`
- Modify: `experiments/test_capacity_frozen.py`

**Interfaces:**
- Consumes: existing `List[Tick]` (time-ordered per service).
- Produces: `SAT_TAIL_TRIM_TICKS: int = 5`; `saturating_ticks(ticks: List[Tick]) -> List[Tick]`; `summarize_service` `mu_sat` from that list; `count_sat_ticks` = `len(saturating_ticks(...))`.

Existing tests that currently pass a **single** saturating tick (`test_high_five_xx_uses_sat_mu_independent_of_latency`, `test_high_resets_zero_5xx_uses_sat_mu`, `test_missing_resets_column_diffs_as_zero`, and the freeze tests that write two CSV rows) would go `mu_sat=None` after the trim. Pad them with 5 healthy trailing ticks **in this task**, in the same edit as the new tests. Do not special-case short series in production code.

- [ ] **Step 1: Write the failing tests and pad the existing sat tests**

In `experiments/test_estimate_service_mu.py`, add a helper next to `_tick` and two tests on `TestSummarizeService`. Also append 5 healthy ticks to the existing sat cases so they stay valid after the trim.

```python
def _healthy_tail(n=5):
    return [_tick(80.0, 0.02) for _ in range(n)]
```

Change `test_high_five_xx_uses_sat_mu_independent_of_latency` to:

```python
    def test_high_five_xx_uses_sat_mu_independent_of_latency(self):
        sat = _tick(100.0, 0.01, dtotal=100, d2xx=90, d5xx=10)
        est = mu.summarize_service(
            "checkoutservice", [sat] + _healthy_tail(),
        )
        self.assertEqual(est.mu_sat, 90.0)
        self.assertAlmostEqual(est.w_mean_ms, (10.0 + 20.0 * 5) / 6)
```

Change `test_high_resets_zero_5xx_uses_sat_mu` to:

```python
    def test_high_resets_zero_5xx_uses_sat_mu(self):
        sat = _tick(100.0, 0.01, dtotal=100, d2xx=80, d5xx=0, dresets=20)
        est = mu.summarize_service(
            "checkoutservice", [sat] + _healthy_tail(),
        )
        self.assertEqual(est.mu_sat, 80.0)
        self.assertEqual(est.inbound_5xx_fraction, 0.0)
        self.assertAlmostEqual(est.inbound_failure_fraction, 20 / 600)
```

(`inbound_failure_fraction` is over the **whole** series, including the healthy tail: `(0+20)/ (100*6) = 20/600`.)

In `test_missing_resets_column_diffs_as_zero`, after the saturating second row, append five healthy rows (`total`/`2xx` increment by 100 each second, `5xx` stays 10) so the 5xx tick is not in the trimmed tail.

Add these two tests to `TestSummarizeService`:

```python
    def test_sat_only_in_last_five_ticks_is_ignored(self):
        # 10 healthy + 2 shutdown-style reset bursts at the end — the
        # frontend/productcatalog failure mode.
        healthy = [_tick(500.0, 0.02, dtotal=500, d2xx=500) for _ in range(10)]
        shutdown = [
            _tick(470.0, 0.02, dtotal=470, d2xx=238, dresets=339),
            _tick(52.0, 0.02, dtotal=52, d2xx=52, dresets=134),
        ]
        est = mu.summarize_service("frontend", healthy + shutdown)
        self.assertIsNone(est.mu_sat)

    def test_mid_series_sat_survives_tail_trim(self):
        healthy = [_tick(80.0, 0.02) for _ in range(5)]
        sat = [_tick(100.0, 0.01, dtotal=100, d2xx=80, d5xx=0, dresets=20)
               for _ in range(10)]
        tail = [_tick(80.0, 0.02) for _ in range(5)]
        est = mu.summarize_service("checkoutservice", healthy + sat + tail)
        self.assertEqual(est.mu_sat, 80.0)
```

In `experiments/test_capacity_frozen.py`, add a helper that writes a saturating tick **plus** 5 healthy trailing seconds, and use it in every freeze test that currently expects a successful freeze (`test_freeze_mu_sat_divides_by_millicores`, `test_freeze_succeeds_on_reset_only_saturation`, `test_refuses_overwrite_without_force`). Leave `test_refuses_when_mu_sat_missing` as a 1-tick healthy series (trim makes that even more clearly `None`).

```python
def _saturating_then_healthy_tail(
    service: str, *, two="50", five="50", resets="0",
) -> list[dict]:
    """One saturating second at t=1, then 5 healthy seconds so the sat
    tick is not in SAT_TAIL_TRIM_TICKS."""
    rows = [
        {"timestamp": "2026-09-17T00:00:00Z", "service": service,
         "total": "0", "2xx": "0", "4xx": "0", "5xx": "0", "resets": "0",
         "rq_time_sum_ms": "0", "rq_time_count": "0"},
        {"timestamp": "2026-09-17T00:00:01Z", "service": service,
         "total": "100", "2xx": two, "4xx": "0", "5xx": five, "resets": resets,
         "rq_time_sum_ms": "0", "rq_time_count": "0"},
    ]
    total, two_i, five_i, reset_i = 100, int(two), int(five), int(resets)
    for i in range(5):
        total += 100
        two_i += 100
        rows.append({
            "timestamp": f"2026-09-17T00:00:{i + 2:02d}Z",
            "service": service,
            "total": str(total),
            "2xx": str(two_i),
            "4xx": "0",
            "5xx": str(five_i),
            "resets": str(reset_i),
            "rq_time_sum_ms": "0",
            "rq_time_count": "0",
        })
    return rows
```

Replace the two-row inbound lists in the three successful-freeze tests with `_saturating_then_healthy_tail("checkoutservice")` (and `_saturating_then_healthy_tail("checkoutservice", five="0", resets="50")` for the reset-only test). `n_sat_ticks` must equal 1 after the trim (the shutdown-style extra ticks are gone).

- [ ] **Step 2: Run the new tail test and confirm it fails**

```powershell
python -m unittest experiments.test_estimate_service_mu.TestSummarizeService.test_sat_only_in_last_five_ticks_is_ignored -v
```

Expected: FAIL. `mu_sat` is currently the median of the two shutdown ticks (not `None`).

- [ ] **Step 3: Implement `saturating_ticks` and wire it**

In `experiments/estimate_service_mu.py`, immediately after `SAT_5XX_FRACTION = 0.05`:

```python
SAT_TAIL_TRIM_TICKS = 5
```

Add this function next to `summarize_service` (before it is fine too):

```python
def saturating_ticks(ticks: List[Tick]) -> List[Tick]:
    """Ticks eligible for mu_sat: failure_fraction gate, last SAT_TAIL_TRIM_TICKS excluded.

    Run teardown produces a reset burst on the last few inbound rows. Those
    are not saturation. If the series is shorter than the trim, nothing is
    eligible.
    """
    if len(ticks) <= SAT_TAIL_TRIM_TICKS:
        return []
    eligible = ticks[:-SAT_TAIL_TRIM_TICKS]
    return [
        t for t in eligible
        if t.delta_total > 0 and t.failure_fraction >= SAT_5XX_FRACTION
    ]
```

Replace the `sat_samples = [...]` block in `summarize_service` with:

```python
    sat = saturating_ticks(ticks)
    sat_samples = [t.delta_2xx / t.dt_seconds for t in sat]
    mu_sat = median(sat_samples) if sat_samples else None
```

In `experiments/capacity_frozen.py`, replace `count_sat_ticks`'s sum with:

```python
    ticks = mu.ticks_from_rows(rows)
    return len(mu.saturating_ticks(ticks))
```

Do not re-implement the filter inline. Do not change `SAT_5XX_FRACTION`.

- [ ] **Step 4: Run the unit tests**

```powershell
python -m unittest experiments.test_estimate_service_mu experiments.test_capacity_frozen -v
```

Expected: all PASS, including `test_sat_only_in_last_five_ticks_is_ignored` and `test_mid_series_sat_survives_tail_trim`.

- [ ] **Step 5: Local verify against already-pulled folders**

```powershell
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_checkout_payment_full_cpu_run1
python experiments/estimate_service_mu.py experiments/results/campaign_48/S2_sustained_overload/baseline_no_topfull_sustained_overload_run2
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_productcatalog_full_cpu_run1
```

Expected:
- checkout/payment still have a real `mu_sat`. `n_sat` via `count_sat_ticks` stays 34 / 20, or drops by at most the sat ticks that happened to sit in the last 5 rows (not a rewrite of those freezes).
- frontend on `baseline_no_topfull_sustained_overload_run2`: `mu_sat` is now `n/a` / `None` (the two shutdown ticks are trimmed).
- productcatalog on `calibration_productcatalog_full_cpu_run1`: `mu_sat` is now `n/a` / `None`.

Do **not** run `capacity_frozen.py freeze` in this task.

- [ ] **Step 6: Commit**

```powershell
git add experiments/estimate_service_mu.py experiments/test_estimate_service_mu.py experiments/capacity_frozen.py experiments/test_capacity_frozen.py
git commit -m "fix: ignore last 5 inbound ticks when sampling mu_sat"
```

---

### Task 2: Constrained-CPU calibration configs

**Files:**
- Create: `experiments/configs/scenario_calibration_frontend_constrained.yaml`
- Create: `experiments/configs/scenario_calibration_productcatalog_constrained.yaml`

**Interfaces:**
- Consumes: `run_scenario.py` `scale_constraints` `method: cpu_limit` + `cpu_limit_fraction` (same shape as `experiments/configs/scenario_4a_baseline.yaml`). Paper limits: frontend 1000m → 100m at 0.1; productcatalog 500m → 50m at 0.1.
- Produces: two YAMLs for Task 3. `scenario_id` 41 and 42 so `scenario_dir_name()` returns `""` and results land under `experiments/results/campaign_48/` (not inside an S1–S6 subfolder).

Copy the `infra:` block verbatim from `experiments/configs/scenario_2_baseline_no_topfull.yaml`. `topfull_rl.enabled: false`, `retryguard.enabled: false`, all three collectors on. Do not change Locust counts relative to the historical full-CPU attempts.

- [ ] **Step 1: Write the frontend constrained config**

`experiments/configs/scenario_calibration_frontend_constrained.yaml`:

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Calibration — frontend, CONSTRAINED CPU (100m), TopFull+RG OFF
#
# Not part of the S1-S6 scenario matrix. Full-CPU frontend never saturated
# (steady ~500 req/s, zero 5xx/resets; the only mu_sat ticks were shutdown
# tail). Constrain to cpu_limit_fraction 0.1 × paper 1000m → 100m so the
# existing S2 Locust mix actually overloads frontend. Do not reuse
# scenario_2_baseline_no_topfull.yaml (that file stays the full-CPU control).
# ─────────────────────────────────────────────────────────────────────────────

scenario_id: 41
scenario_name: calibration_frontend_constrained
condition: calibration
run_number: 1
description: >
  Calibration-only run. frontend CPU constrained to 100m. TopFull RL off,
  RetryGuard off. Same Locust mix as S2 / no-TopFull control.

duration_seconds: 600

locust:
  user_counts:
    getproduct:   100
    postcheckout: 20
    getcart:      100
    postcart:     100
    emptycart:    300
  spawn_rate: 90
  scripts:
    - online_boutique_create.sh
    - online_boutique_create2.sh

scale_constraints:
  - deployment: frontend
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 × paper 1000m → 100m
    container: server

retries:
  attempts_on: 3
  attempts_off: 0
  per_try_timeout_ms: 500

topfull_rl:
  enabled: false

retryguard:
  enabled: false
  rejection_threshold: 0.20
  sample_interval_seconds: 1
  interval_samples: 30

envoy_retry_collector:
  enabled: true
  poll_interval_seconds: 1
  transport: network_prometheus
  max_workers: 4

resource_usage_collector:
  enabled: true
  poll_interval_seconds: 5

topfull_throttle_collector:
  enabled: true
  poll_interval_seconds: 1

log_folder: calibration_frontend_constrained_run1

infra:
  master_ssh_host: topfull-master
  loadgen_ssh_host: topfull-load
  topfull_src_path: /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src
  topfull_loadgen_path: /home/idozacharia/TopFull/TopFull_loadgen
  venv_activate: /home/idozacharia/TopFull/venv/bin/activate
  results_base_path: /home/idozacharia/experiments/results
  retryguard_script: /home/idozacharia/experiments/retryguard.py
  envoy_retry_collector_script: /home/idozacharia/experiments/envoy_retry_collector.py
  resource_usage_collector_script: /home/idozacharia/experiments/resource_usage_collector.py
  topfull_throttle_collector_script: /home/idozacharia/experiments/topfull_throttle_collector.py
```

- [ ] **Step 2: Write the productcatalog constrained config**

`experiments/configs/scenario_calibration_productcatalog_constrained.yaml`:

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Calibration — productcatalogservice, CONSTRAINED CPU (50m), TopFull+RG OFF
#
# Not part of the S1-S6 scenario matrix. Full-CPU productcatalog never
# saturated (~2400–2900 req/s, zero 5xx/resets; mu_sat ticks were shutdown
# tail). Constrain to cpu_limit_fraction 0.1 × paper 500m → 50m (same as
# Scenario 4A). Same Locust mix as calibration_productcatalog_full_cpu.
# ─────────────────────────────────────────────────────────────────────────────

scenario_id: 42
scenario_name: calibration_productcatalog_constrained
condition: calibration
run_number: 1
description: >
  Calibration-only run. productcatalogservice CPU constrained to 50m.
  TopFull RL off, RetryGuard off. Heavy getproduct load.

duration_seconds: 900

locust:
  user_counts:
    getproduct:   800
    postcheckout: 20
    getcart:      50
    postcart:     50
    emptycart:    50
  spawn_rate: 150
  scripts:
    - online_boutique_create.sh
    - online_boutique_create2.sh

scale_constraints:
  - deployment: productcatalogservice
    namespace: default
    method: cpu_limit
    cpu_limit_fraction: 0.1    # 0.1 × paper 500m → 50m (same as S4A)
    container: server

retries:
  attempts_on: 3
  attempts_off: 0
  per_try_timeout_ms: 500

topfull_rl:
  enabled: false

retryguard:
  enabled: false
  rejection_threshold: 0.20
  sample_interval_seconds: 1
  interval_samples: 30

envoy_retry_collector:
  enabled: true
  poll_interval_seconds: 1
  transport: network_prometheus
  max_workers: 4

resource_usage_collector:
  enabled: true
  poll_interval_seconds: 5

topfull_throttle_collector:
  enabled: true
  poll_interval_seconds: 1

log_folder: calibration_productcatalog_constrained_run1

infra:
  master_ssh_host: topfull-master
  loadgen_ssh_host: topfull-load
  topfull_src_path: /home/idozacharia/TopFull/TopFull_master/online_boutique_scripts/src
  topfull_loadgen_path: /home/idozacharia/TopFull/TopFull_loadgen
  venv_activate: /home/idozacharia/TopFull/venv/bin/activate
  results_base_path: /home/idozacharia/experiments/results
  retryguard_script: /home/idozacharia/experiments/retryguard.py
  envoy_retry_collector_script: /home/idozacharia/experiments/envoy_retry_collector.py
  resource_usage_collector_script: /home/idozacharia/experiments/resource_usage_collector.py
  topfull_throttle_collector_script: /home/idozacharia/experiments/topfull_throttle_collector.py
```

- [ ] **Step 3: Sanity-check the YAMLs parse and map to no S1–S6 subfolder**

```powershell
python -c "import yaml, pathlib, sys; sys.path.insert(0,'experiments'); import run_scenario as r; 
for p in ['experiments/configs/scenario_calibration_frontend_constrained.yaml','experiments/configs/scenario_calibration_productcatalog_constrained.yaml']:
 cfg=yaml.safe_load(pathlib.Path(p).read_text(encoding='utf-8')); print(p, 'id', cfg['scenario_id'], 'dir', repr(r.scenario_dir_name(cfg)), 'log', cfg['log_folder'], 'frac', cfg['scale_constraints'][0]['cpu_limit_fraction'])"
```

Expected: both `dir` print as `''`; log folders are the `_run1` names above; fraction is `0.1`.

- [ ] **Step 4: Commit**

```powershell
git add experiments/configs/scenario_calibration_frontend_constrained.yaml experiments/configs/scenario_calibration_productcatalog_constrained.yaml
git commit -m "add constrained-CPU calibration configs for frontend and productcatalog"
```

---

### Task 0: Start the VMs and confirm they are ready

**When to run:** After Task 1 and Task 2 are committed. Task 3 must not start until these health checks pass.

**Files:** none created/modified. Follow [CONNECT-VMS.md](Guides%20and%20Info/CONNECT-VMS.md) short path ("Reconnect after VMs were stopped"). Always `User: idozacharia` on all three VMs.

**Interfaces:**
- Consumes: none.
- Produces: three `RUNNING` VMs with current IPs in `~/.ssh/config`, Ready Kubernetes, Boutique pods `Running` `2/2` at paper CPU limits, worker SKU `e2-standard-16`.

- [ ] **Step 1: Confirm gcloud project and list instances**

```powershell
gcloud config set project networks-workshop
gcloud compute instances list --format="table(name,status,machineType.basename(),networkInterfaces[0].accessConfigs[0].natIP)"
```

Expected: `topfull-master`, `topfull-worker-1`, `topfull-load` listed. `topfull-worker-1` must be `e2-standard-16`. If it is a different SKU, **stop** — do not calibrate on the wrong shape.

- [ ] **Step 2: Start any VM that is not `RUNNING`**

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
gcloud compute instances list --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Require `STATUS=RUNNING` and a non-empty NAT IP for each.

- [ ] **Step 3: Refresh `HostName` in `~/.ssh/config`**

Update only the three `Host topfull-*` blocks. Then:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
```

Expected: `whoami` is `idozacharia` on every VM. If `Permission denied`, follow CONNECT-VMS.md §Key install. If timeout, IPs are still stale.

- [ ] **Step 4: Wait until Kubernetes is Ready**

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "kubectl get nodes; kubectl get pods -n default; kubectl get virtualservices -n default"
```

Expected: both nodes `Ready`; Boutique pods `Running` `2/2`; VirtualServices present. If pods are `Completed` after a reboot, `kubectl delete pods -n default --all` and wait for Deployments to recreate them. If `connection to localhost:8080 refused` and kubelet is up, copy kubeconfig from `idozacharia` per AGENTS.md §7.

- [ ] **Step 5: Confirm paper CPU limits (no leftover constraint)**

```powershell
ssh topfull-master "kubectl get deploy -n default -o custom-columns=NAME:.metadata.name,CPU_LIMIT:.spec.template.spec.containers[0].resources.limits.cpu"
```

Expected before the first run: `frontend` 1000m, `productcatalogservice` 500m, `checkoutservice` 1000m. The runner will apply 100m/50m at run start and reconcile back after. If leftovers are already 100m/50m from a crashed prior run, still proceed — `run_scenario.py` reconciles to paper then re-applies the YAML constraint.

- [ ] **Step 6: Clear stale `/tmp` runner scripts**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
```

- [ ] **Step 7: Cluster is ready.** Hand off to Task 3. Task 3 still sleeps 300 s of idle **after this step** before the first Locust run.

---

### Task 3: Two calibration runs with 300 s cool-off

**Files:** none in git except the pulled result folders under `experiments/results/campaign_48/`. Do not overwrite `baseline_no_topfull_sustained_overload_run2` or `calibration_productcatalog_full_cpu_run1`.

**Interfaces:**
- Consumes: Task 2 YAMLs, Task 0 Ready cluster, Task 1 trimmed estimator (so shutdown ticks will not poison the new `mu_sat`).
- Produces: `experiments/results/campaign_48/calibration_frontend_constrained_run1/` and `experiments/results/campaign_48/calibration_productcatalog_constrained_run1/` (full METRICS-GATHERED file set, including `service_inbound.csv` and `service_capacity.json`).

Order: **frontend first** (600 s), then productcatalog (900 s). Cool-off is mandatory in the three places below.

- [ ] **Step 1: Cool-off 300 s after Task 0 Ready, before the first run**

```powershell
Start-Sleep -Seconds 300
```

Do not skip. Boot leftover / prior-session traffic must drain.

- [ ] **Step 2: Clear `/tmp` again, then run frontend constrained**

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_frontend_constrained.yaml
```

Expected: runner applies frontend CPU 100m; TopFull RL is skipped; RetryGuard is off; run lasts ~600 s plus setup/teardown. Confirm the live log shows the CPU-limit patch on `frontend`. If the run aborts, stop and fix — do not start productcatalog.

- [ ] **Step 3: Cool-off 300 s. Pull frontend results during the wait**

Start the sleep and the pull in that order. The pull is local `scp` and must not be treated as a reason to shorten the sleep.

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_frontend_constrained.yaml --no-report
Start-Sleep -Seconds 300
```

If `pull_results.py` finishes before 300 s, the `Start-Sleep` still runs the remainder. If you pull first and it takes 40 s, still sleep 300 s after `run_scenario.py` exited — easiest: sleep 300 unconditionally, then pull, if you do not want to overlap. Overlap is allowed only if the 300 s clock started at runner exit.

Confirm locally:

```powershell
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_frontend_constrained_run1
```

Look at the `frontend` row. Prefer `mu_sat` populated from mid-run ticks. Spot-check `service_inbound.csv`: saturating ticks (`failure_fraction >= 0.05`) must exist **before** the last 5 frontend rows, not only at EOF. Also confirm `service_capacity.json` has `frontend.cpu_limit_millicores` == 100.

If `mu_sat` is still `None` for frontend: still continue to productcatalog (best effort, one attempt). Do not change Locust counts. Do not lower `SAT_TAIL_TRIM_TICKS`.

- [ ] **Step 4: Clear `/tmp`, run productcatalog constrained**

The 300 s from Step 3 must have finished.

```powershell
ssh topfull-master "sudo rm -f /tmp/rg_proxy.sh /tmp/rg_rl.sh /tmp/rg_mc.sh /tmp/rg_retryguard.sh /tmp/rg_envoy_retry.sh /tmp/rg_resource_usage.sh /tmp/rg_topfull_throttle.sh /tmp/rg_locust_launch.sh /tmp/envoy_retry_params.json"
python experiments/run_scenario.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml
```

Expected: runner applies productcatalog CPU 50m; ~900 s Locust. Confirm the live log shows the CPU-limit patch on `productcatalogservice`.

- [ ] **Step 5: Pull productcatalog results**

No further calibration run follows, so no extra 300 s cool-off is required after this pull.

```powershell
python experiments/pull_results.py experiments/configs/scenario_calibration_productcatalog_constrained.yaml --no-report
python experiments/estimate_service_mu.py experiments/results/campaign_48/calibration_productcatalog_constrained_run1
```

Look at the `productcatalogservice` row. Confirm `service_capacity.json` has `productcatalogservice.cpu_limit_millicores` == 50. Saturating ticks must exist before the last 5 rows of that service.

- [ ] **Step 6: Do not commit result CSVs unless the user asks.** Hand the two folder paths and the two `mu_sat` / rough `n_sat` readings to Task 4.

---

### Task 4: Freeze frontend + productcatalog, re-check S1/S2 ρ, update docs

**Files:**
- Modify (via CLI, not by hand): `experiments/capacity/capacity_frozen.json` — only the `frontend` and `productcatalogservice` entries
- Modify: `experiments/capacity/README.md`
- Modify: `AGENTS.md` §4
- Write into existing run folders (already the report's job): `experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.md` and `experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.md`

**Interfaces:**
- Consumes: Task 3 folders; existing checkout/payment freeze (leave them).
- Produces: updated `mu_per_millicore` for frontend and productcatalog; S1 run24 / S2 run23 `rho_hat` table.

- [ ] **Step 1: Freeze frontend, then productcatalog, `--force`**

Only freeze a service if Task 3's `estimate_service_mu.py` showed a real `mu_sat` for it. If `mu_sat` is `None`, skip that service and leave the previous (poisoned, now-known-wrong) value **or** set it back to `not_yet_calibrated` — prefer leaving a `note` in README that the old 2-tick freeze is invalid and the constrained run did not replace it. Do not `--force` a shutdown-poisoned old folder.

```powershell
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_frontend_constrained_run1 --service frontend --force
python experiments/capacity_frozen.py freeze experiments/results/campaign_48/calibration_productcatalog_constrained_run1 --service productcatalogservice --force
```

Expected stdout: `froze frontend mu_per_millicore=...` and `froze productcatalogservice mu_per_millicore=...`.

Open `experiments/capacity/capacity_frozen.json` and confirm:
- `frontend.calibrated_at_cpu_limit_millicores` is `100`
- `productcatalogservice.calibrated_at_cpu_limit_millicores` is `50`
- `checkoutservice` / `paymentservice` entries are unchanged (1000m, 0.1615 / 0.0195)
- `n_sat_ticks` ≥ 10 → `note` is `null`. If still `< 10`, `note` stays `low_confidence: n_sat_ticks=N < 10` — that is a valid outcome, do not edit it by hand.

`mu_per_millicore` for frontend should be **higher** than the poisoned 0.238 if the constrained run's admitted 2xx at 100m is not a shutdown dip. Do not hard-code an expected number.

- [ ] **Step 2: Re-run frozen ρ on S1 run24 and S2 run23**

```powershell
python experiments/rho_frozen_report.py experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24
python experiments/rho_frozen_report.py experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23
```

Read `rho_hat` for the four minimum-set services from those two `rho_frozen_report.md` files. Expect frontend and productcatalog `rho_hat` to drop versus 1.632 / 2.546 (S1) and 2.316 / 3.466 (S2), because μ should be higher. Checkout/payment `rho_hat` stay the same. Record the eight numbers in README / AGENTS.md. Do not treat the informal S1-entry 0.5–0.8 band as a pass/fail gate for this task.

- [ ] **Step 3: Update `experiments/capacity/README.md`**

Replace the 2026-09-19 calibration-status table so frontend and productcatalog cite the new constrained folders, millicores 100 / 50, new `mu_per_millicore`, and actual `n_sat_ticks`. Keep checkout/payment rows as they are. Add one sentence that the previous full-CPU 2-tick freezes were shutdown-tail artifacts and must not be reused.

- [ ] **Step 4: Update `AGENTS.md` §4**

Add a dated 2026-09-19 (or today) bullet: tail trim of 5 ticks; constrained-CPU recals; freeze numbers; S1/S2 `rho_hat`; YAML next-free slots (`calibration_frontend_constrained` / `calibration_productcatalog_constrained` stay at run1 unless you bumped after a failed attempt). Do not rewrite the whole status section. Do not claim high confidence if `n_sat_ticks < 10`.

- [ ] **Step 5: Commit**

```powershell
git add experiments/capacity/capacity_frozen.json experiments/capacity/README.md AGENTS.md experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.md experiments/results/campaign_48/S1_normal_op/baseline_topfull_no_retryguard_normal_op_run24/rho_frozen_report.json experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.md experiments/results/campaign_48/S2_sustained_overload/baseline_topfull_no_retryguard_sustained_overload_run23/rho_frozen_report.json
git commit -m "freeze constrained-CPU mu for frontend and productcatalog"
```

Add the two new result folders only if the user wants campaign results in git; otherwise leave them untracked. Do not commit `august_38/` or overwrite S3 run8.

---

## Self-review

1. **Spec coverage:** §2a trim → Task 1. §2b constrained CPU + same load/duration → Task 2 + Task 3. §4.1 unit tests + checkout/payment local verify → Task 1 steps 1–5. §4.2 VM health + 300 s cool-off + two runs → Task 0 + Task 3. §4.3 freeze millicores 100/50 + honest low_confidence → Task 4 step 1. §4.4 S1/S2 rho → Task 4 step 2. §4.5 README/AGENTS → Task 4 steps 3–4.
2. **Cool-off:** Task 0 step 7 defers to Task 3; Task 3 step 1 is 300 s before first run; Task 3 step 3 is 300 s after frontend / before productcatalog; pull allowed during the wait; no skip language.
3. **No placeholders:** CPU fractions, scenario_ids, log_folder names, exact test code, exact freeze CLI, exact SSH health commands.
4. **Out of scope held:** no `retryguard.py`, no `SAT_5XX_FRACTION` change, no Locust bump, no checkout/payment refreeze, no shutdown-log heuristic.
